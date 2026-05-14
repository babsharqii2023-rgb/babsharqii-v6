"""
BABSHARQII v40.0 — Approval Gate
Any proposed change (patch, mutation, skill) must pass through this gate.
Initially requires human approval; can be relaxed after explicit user consent.
"""

import time
import json
import uuid
import logging
import aiosqlite
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# v35 FIX: logger was missing — any approval/rollback would crash with NameError
logger = logging.getLogger("mamoun.approval_gate")


@dataclass
class ApprovalRequest:
    """A change proposal awaiting human approval."""
    id: str = ""
    change_type: str = ""  # code_patch, genome_mutation, skill_extraction, config_change
    target: str = ""
    description: str = ""
    risk_level: str = "medium"
    details: str = "{}"  # JSON
    status: str = "pending"  # pending, approved, rejected, expired, auto_approved
    requested_at: float = 0.0
    decided_at: float = 0.0
    decided_by: str = ""  # "human", "auto_low_risk", "auto_timeout"
    rejection_reason: str = ""
    auto_deploy_enabled: bool = False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "change_type": self.change_type,
            "target": self.target,
            "description": self.description,
            "risk_level": self.risk_level,
            "status": self.status,
            "requested_at": self.requested_at,
            "decided_at": self.decided_at,
            "decided_by": self.decided_by,
            "auto_deploy_enabled": self.auto_deploy_enabled,
        }


class ApprovalGate:
    """
    Human Approval Gate for all self-modification proposals.
    
    Rules:
    - Initially ALL changes require human approval
    - User can enable auto-deploy for low-risk changes
    - High-risk changes ALWAYS require human approval
    - Changes expire after 24 hours if not approved
    - Any rejection is final for that specific proposal
    """
    
    REQUEST_EXPIRY_SECONDS = 86400  # 24 hours
    
    def __init__(self, db_path: str = "", auto_deploy_low_risk: bool = False, semi_auto_mode: bool = False):
        self._db_path = db_path or str(Path(__file__).parent.parent.parent / "data" / "mamoun.db")
        self._auto_deploy_low_risk = auto_deploy_low_risk
        self._semi_auto_mode = semi_auto_mode
        self._initialized = False
        self._request_counter = 0
        self._notifications: list[dict] = []  # v10: notification log
    
    async def initialize(self):
        if self._initialized:
            return
        
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS approval_requests (
                    id TEXT PRIMARY KEY,
                    change_type TEXT NOT NULL,
                    target TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    risk_level TEXT DEFAULT 'medium',
                    details TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'pending',
                    requested_at REAL DEFAULT 0.0,
                    decided_at REAL DEFAULT 0.0,
                    decided_by TEXT DEFAULT '',
                    rejection_reason TEXT DEFAULT '',
                    auto_deploy_enabled INTEGER DEFAULT 0
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_approval_status ON approval_requests(status)")
            await db.commit()
        self._initialized = True
    
    async def request_approval(self, request: ApprovalRequest) -> dict:
        """
        Submit a change for approval.
        Returns the decision: approved, pending (waiting for human), or rejected.
        """
        await self.initialize()
        
        if not request.requested_at:
            request.requested_at = time.time()
        
        self._request_counter += 1
        request.id = f"approval_{int(time.time())}_{self._request_counter}_{uuid.uuid4().hex[:6]}"
        
        # Auto-approve low-risk changes if auto-deploy is enabled
        if self._auto_deploy_low_risk and request.risk_level == "low":
            request.status = "auto_approved"
            request.decided_at = time.time()
            request.decided_by = "auto_low_risk"
        
        # High-risk changes ALWAYS require human approval
        if request.risk_level == "high":
            request.status = "pending"
        
        # Save to database
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                INSERT INTO approval_requests 
                (id, change_type, target, description, risk_level, details,
                 status, requested_at, decided_at, decided_by, rejection_reason,
                 auto_deploy_enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.id, request.change_type, request.target,
                request.description, request.risk_level, request.details,
                request.status, request.requested_at, request.decided_at,
                request.decided_by, request.rejection_reason,
                1 if request.auto_deploy_enabled else 0,
            ))
            await db.commit()
        
        return {
            "id": request.id,
            "status": request.status,
            "message": self._status_message(request),
        }
    
    async def approve(self, request_id: str) -> bool:
        """Human approves a pending request."""
        await self.initialize()
        
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                UPDATE approval_requests 
                SET status = 'approved', decided_at = ?, decided_by = 'human'
                WHERE id = ? AND status = 'pending'
            """, (time.time(), request_id))
            await db.commit()
            return True
    
    async def reject(self, request_id: str, reason: str = "") -> bool:
        """Human rejects a pending request."""
        await self.initialize()
        
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                UPDATE approval_requests 
                SET status = 'rejected', decided_at = ?, decided_by = 'human',
                    rejection_reason = ?
                WHERE id = ? AND status = 'pending'
            """, (time.time(), reason, request_id))
            await db.commit()
            return True
    
    async def get_pending(self, limit: int = 20) -> list[dict]:
        """Get all pending approval requests."""
        await self.initialize()
        
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM approval_requests 
                WHERE status = 'pending'
                ORDER BY requested_at DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in await cursor.fetchall()]
    
    async def get_recent(self, limit: int = 50) -> list[dict]:
        """Get recent approval requests (all statuses)."""
        await self.initialize()
        
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM approval_requests 
                ORDER BY requested_at DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in await cursor.fetchall()]
    
    async def expire_old_requests(self) -> int:
        """Expire requests older than 24 hours."""
        await self.initialize()
        
        cutoff = time.time() - self.REQUEST_EXPIRY_SECONDS
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("""
                UPDATE approval_requests 
                SET status = 'expired', decided_at = ?, decided_by = 'auto_timeout'
                WHERE status = 'pending' AND requested_at < ?
            """, (time.time(), cutoff))
            await db.commit()
            return cursor.rowcount
    
    async def set_auto_deploy(self, enabled: bool):
        """Enable or disable auto-deploy for low-risk changes."""
        self._auto_deploy_low_risk = enabled

    # ═══════════════════════════════════════════════════════════════════════════
    # v10 Additions: Semi-Auto Mode, Notification, Rollback
    # ═══════════════════════════════════════════════════════════════════════════

    async def notify_approval(self, request_id: str, details: str = "") -> bool:
        """
        أرسل إشعاراً بعد الموافقة التلقائية (وضع شبه تلقائي).
        
        In semi-auto mode, the user is notified after an auto-approval
        but the decision is already in effect.
        """
        notification = {
            "request_id": request_id,
            "details": details,
            "notified_at": time.time(),
            "type": "auto_approval_notification",
        }
        self._notifications.append(notification)
        logger.info(f"Auto-approval notification sent for {request_id}: {details}")
        return True

    async def rollback(self, request_id: str) -> bool:
        """
        تراجع عن موافقة تلقائية (v10).
        
        Reverses an auto-approved change. The request status changes
        from 'auto_approved' to 'rolled_back'.
        """
        await self.initialize()

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("""
                UPDATE approval_requests 
                SET status = 'rolled_back', decided_at = ?, decided_by = 'human_rollback'
                WHERE id = ? AND status = 'auto_approved'
            """, (time.time(), request_id))
            await db.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Rolled back auto-approval for {request_id}")
                return True
            return False

    def _check_auto_approval_policy(self, request: ApprovalRequest) -> bool:
        """
        تحقق من سياسة الموافقة التلقائية (v10).
        
        Checks auto_approval_policy.yaml to determine if a request
        can be auto-approved based on its risk level and target.
        """
        # Load policy (simplified - in production, load from YAML)
        # High risk and critical are never auto-approved
        if request.risk_level in ("high", "critical"):
            return False

        # Protected targets are never auto-approved
        protected = {
            "laws.yaml", "safety_guard.py", "approval_gate.py",
            ".env", "settings.yaml", "safety_gate_client.py",
        }
        target_filename = request.target.split("/")[-1] if "/" in request.target else request.target
        if target_filename in protected:
            return False

        # Low risk with auto_deploy enabled → auto-approve
        if self._auto_deploy_low_risk and request.risk_level == "low":
            return True

        return False
    
    def _status_message(self, request: ApprovalRequest) -> str:
        """Generate a human-readable status message in Arabic."""
        if request.status == "auto_approved":
            return f"تمت الموافقة تلقائياً (مخاطر منخفضة): {request.description}"
        elif request.status == "pending":
            return f"بانتظار موافقتك: {request.description}"
        elif request.status == "rejected":
            return f"مرفوض: {request.description}"
        return request.description
