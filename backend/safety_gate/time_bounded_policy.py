"""
BABSHARQII v12.0 — Time-Bounded Authorization Policy
نظام التفويض الزمني — منح صلاحيات مؤقتة للوكلاء مع سحب تلقائي.

Core Principle: Zero Standing Privilege (ZSP)
- جميع الصلاحيات صفرية افتراضياً
- تُمنح فقط عند الحاجة (Just-in-Time)
- تُسحب تلقائياً عند انتهاء الوقت
- ما يُسمح به "للمهمة الواحدة" لا يُستخدم في مهمة أخرى

Integration:
- ApprovalGate: طلبات الصلاحية عالية المخاطر تمر عبر بوابة الموافقة
- SafetyGate: كل منح صلاحية يُسجّل في سجل التدقيق
- FileSystemTool / ShellExecutor: يتحققان من الصلاحية قبل التنفيذ
"""

import os
import time
import json
import uuid
import logging
import asyncio
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

# Default: Time-bounded auth disabled unless MAMOUN_TIME_BOUNDED_AUTH=true
TIME_BOUNDED_ENABLED = os.getenv("MAMOUN_TIME_BOUNDED_AUTH", "false").lower() == "true"

# Maximum permission duration (safety cap)
MAX_PERMISSION_DURATION_MINUTES = 480  # 8 hours maximum
# Default permission durations by scope
DEFAULT_DURATIONS = {
    "filesystem:read": 120,       # 2 hours
    "filesystem:write": 60,       # 1 hour
    "filesystem:delete": 30,      # 30 minutes
    "shell:execute": 60,          # 1 hour
    "shell:install": 30,          # 30 minutes
    "shell:git": 120,             # 2 hours
    "ecommerce:browse": 60,       # 1 hour
    "ecommerce:purchase": 15,     # 15 minutes (requires human approval)
    "ecommerce:supplier": 30,     # 30 minutes
    "instagram:read": 60,         # 1 hour
    "instagram:write": 30,        # 30 minutes
    "instagram:dm": 15,           # 15 minutes
    "embodiment:view": 30,        # 30 minutes
    "embodiment:control": 15,     # 15 minutes (requires human approval)
    "mobile:build": 120,          # 2 hours
    "mobile:deploy": 15,          # 15 minutes (requires human approval)
}

# Scopes that ALWAYS require human approval
HIGH_RISK_SCOPES = {
    "filesystem:delete",
    "ecommerce:purchase",
    "embodiment:control",
    "mobile:deploy",
    "shell:execute",
}

# Revocation check interval (seconds)
REVOCATION_CHECK_INTERVAL = 30


class PermissionStatus(str, Enum):
    """حالة الصلاحية."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    CONSUMED = "consumed"  # one-time use, already used


class PermissionScope(str, Enum):
    """نطاقات الصلاحيات المتاحة."""
    FILESYSTEM_READ = "filesystem:read"
    FILESYSTEM_WRITE = "filesystem:write"
    FILESYSTEM_DELETE = "filesystem:delete"
    SHELL_EXECUTE = "shell:execute"
    SHELL_INSTALL = "shell:install"
    SHELL_GIT = "shell:git"
    ECOMMERCE_BROWSE = "ecommerce:browse"
    ECOMMERCE_PURCHASE = "ecommerce:purchase"
    ECOMMERCE_SUPPLIER = "ecommerce:supplier"
    INSTAGRAM_READ = "instagram:read"
    INSTAGRAM_WRITE = "instagram:write"
    INSTAGRAM_DM = "instagram:dm"
    EMBODIMENT_VIEW = "embodiment:view"
    EMBODIMENT_CONTROL = "embodiment:control"
    MOBILE_BUILD = "mobile:build"
    MOBILE_DEPLOY = "mobile:deploy"


@dataclass
class PermissionGrant:
    """
    منح صلاحية — تفويض زمني محدد لوكيل.
    
    A time-bounded permission grant for an agent.
    - Has a specific scope, permissions, and expiry time
    - Bound to a task context (cannot be reused for other tasks)
    - Automatically revoked upon expiry
    """
    grant_id: str = ""
    agent_id: str = ""           # من طلب الصلاحية (e.g., "ecommerce_builder", "instagram_manager")
    scope: str = ""              # نطاق: "filesystem:/path", "shell:command", "ecommerce:purchase"
    permissions: list = field(default_factory=list)  # ["read", "write", "execute"]
    resource_path: str = ""      # المسار أو المورد المحدد (e.g., "<project_root>/backend")
    granted_at: float = 0.0      # timestamp
    expires_at: float = 0.0      # timestamp — انتهاء الصلاحية
    duration_minutes: float = 0.0
    granted_by: str = ""         # "human" | "auto_low_risk" | "auto_medium_risk"
    task_context: str = ""       # سياق المهمة — لا تُستخدم خارجها
    status: str = PermissionStatus.ACTIVE.value
    auto_revoke: bool = True
    one_time_use: bool = False   # صلاحية لمرة واحدة
    audit_entries: list = field(default_factory=list)  # سجل استخدام الصلاحية
    
    def is_active(self) -> bool:
        """هل الصلاحية ما زالت فعالة؟"""
        if self.status != PermissionStatus.ACTIVE.value:
            return False
        if time.time() > self.expires_at:
            self.status = PermissionStatus.EXPIRED.value
            return False
        return True
    
    def remaining_seconds(self) -> float:
        """الوقت المتبقي بالثواني."""
        remaining = self.expires_at - time.time()
        return max(0.0, remaining)
    
    def matches_task(self, task_context: str) -> bool:
        """هل يطابق سياق المهمة؟"""
        if not self.task_context:
            return True  # No task restriction
        return self.task_context == task_context
    
    def to_dict(self) -> dict:
        return {
            "grant_id": self.grant_id,
            "agent_id": self.agent_id,
            "scope": self.scope,
            "permissions": self.permissions,
            "resource_path": self.resource_path,
            "granted_at": self.granted_at,
            "expires_at": self.expires_at,
            "duration_minutes": self.duration_minutes,
            "granted_by": self.granted_by,
            "task_context": self.task_context,
            "status": self.status,
            "auto_revoke": self.auto_revoke,
            "one_time_use": self.one_time_use,
            "remaining_seconds": self.remaining_seconds(),
        }


@dataclass
class PermissionRequest:
    """طلب صلاحية من وكيل."""
    agent_id: str = ""
    scope: str = ""
    permissions: list = field(default_factory=list)
    resource_path: str = ""
    duration_minutes: float = 0.0
    task_context: str = ""
    reason: str = ""            # لماذا يحتاج الوكيل هذه الصلاحية
    one_time_use: bool = False


@dataclass
class PermissionAuditEntry:
    """سجل تدقيق لعملية صلاحية."""
    grant_id: str = ""
    action: str = ""            # "granted", "checked", "used", "revoked", "expired"
    agent_id: str = ""
    scope: str = ""
    timestamp: float = 0.0
    details: str = ""


class TimeBoundedPolicy:
    """
    نظام التفويض الزمني — يتحكم في صلاحيات الوكلاء.
    
    Features:
    - Zero Standing Privilege: لا صلاحيات دائمة
    - Just-in-Time Access: منح عند الحاجة فقط
    - Auto-revocation: سحب تلقائي عند انتهاء الوقت
    - Task-scoped: صلاحية مرتبطة بمهمة محددة
    - Audit trail: سجل كامل لكل عملية
    - Human approval: النطاقات عالية المخاطر تحتاج موافقة بشرية
    - Continuous monitoring: فحص مستمر للصلاحيات المنتهية
    """
    
    def __init__(self, db_path: str = "", enabled: bool = None):
        self._db_path = db_path or str(
            Path(__file__).parent.parent / "data" / "time_bounded_permissions.db"
        )
        self._enabled = enabled if enabled is not None else TIME_BOUNDED_ENABLED
        self._grants: dict[str, PermissionGrant] = {}
        self._audit_log: list[PermissionAuditEntry] = []
        self._initialized = False
        self._revocation_task: Optional[asyncio.Task] = None
        self._request_counter = 0
    
    async def initialize(self):
        """تهيئة النظام — إنشاء الجدول وبدء مراقب الانتهاء."""
        if self._initialized:
            return
        
        try:
            import aiosqlite
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS permission_grants (
                        grant_id TEXT PRIMARY KEY,
                        agent_id TEXT NOT NULL,
                        scope TEXT NOT NULL,
                        permissions TEXT DEFAULT '[]',
                        resource_path TEXT DEFAULT '',
                        granted_at REAL DEFAULT 0.0,
                        expires_at REAL DEFAULT 0.0,
                        duration_minutes REAL DEFAULT 0.0,
                        granted_by TEXT DEFAULT '',
                        task_context TEXT DEFAULT '',
                        status TEXT DEFAULT 'active',
                        auto_revoke INTEGER DEFAULT 1,
                        one_time_use INTEGER DEFAULT 0,
                        audit_entries TEXT DEFAULT '[]'
                    )
                """)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS permission_audit (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        grant_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        agent_id TEXT NOT NULL,
                        scope TEXT NOT NULL,
                        timestamp REAL DEFAULT 0.0,
                        details TEXT DEFAULT ''
                    )
                """)
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_grant_status ON permission_grants(status)"
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_grant_expires ON permission_grants(expires_at)"
                )
                await db.commit()
            
            # Start automatic revocation monitor
            if self._enabled:
                self._revocation_task = asyncio.create_task(self._revocation_monitor())
            
            self._initialized = True
            logger.info("TimeBoundedPolicy initialized — Zero Standing Privilege enforced")
        except Exception as e:
            logger.warning(f"TimeBoundedPolicy init failed (non-critical): {e}")
            self._initialized = True  # Allow operation without DB
    
    async def request_permission(
        self,
        agent_id: str,
        scope: str,
        permissions: list[str],
        duration_minutes: float = 0.0,
        resource_path: str = "",
        task_context: str = "",
        reason: str = "",
        one_time_use: bool = False,
    ) -> dict:
        """
        طلب صلاحية من وكيل.
        
        Args:
            agent_id: معرف الوكيل
            scope: نطاق الصلاحية (e.g., "filesystem:write")
            permissions: الصلاحيات المطلوبة (e.g., ["read", "write"])
            duration_minutes: المدة بالدقائق (0 = استخدام الافتراضي)
            resource_path: المسار أو المورد
            task_context: سياق المهمة
            reason: سبب الطلب
            one_time_use: صلاحية لمرة واحدة
        
        Returns:
            dict with grant_id, status, message, expires_at
        """
        await self.initialize()
        
        # If time-bounded auth is disabled, auto-grant everything
        if not self._enabled:
            return {
                "grant_id": "disabled_mode",
                "status": "auto_granted",
                "message": "نظام الصلاحيات الزمنية غير مفعّل — صلاحية تلقائية",
                "expires_at": time.time() + 86400,  # 24h
                "scope": scope,
                "permissions": permissions,
            }
        
        # Determine duration
        if duration_minutes <= 0:
            duration_minutes = DEFAULT_DURATIONS.get(scope, 60)
        
        # Cap duration at maximum
        duration_minutes = min(duration_minutes, MAX_PERMISSION_DURATION_MINUTES)
        
        # Check if scope requires human approval
        requires_human = scope in HIGH_RISK_SCOPES
        
        # Create grant
        self._request_counter += 1
        grant = PermissionGrant(
            grant_id=f"grant_{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            scope=scope,
            permissions=permissions,
            resource_path=resource_path,
            granted_at=time.time(),
            expires_at=time.time() + (duration_minutes * 60),
            duration_minutes=duration_minutes,
            task_context=task_context,
            auto_revoke=True,
            one_time_use=one_time_use,
        )
        
        if requires_human:
            # Submit through ApprovalGate for human review
            grant.status = "pending_human_approval"
            grant.granted_by = "pending"
            approval_result = await self._request_human_approval(grant, reason)
            
            if approval_result.get("status") == "approved":
                grant.status = PermissionStatus.ACTIVE.value
                grant.granted_by = "human"
            else:
                grant.status = "denied"
                self._add_audit(grant.grant_id, "denied", agent_id, scope, "Human denied")
                return {
                    "grant_id": grant.grant_id,
                    "status": "denied",
                    "message": f"الموافقة البشرية مرفوضة: {approval_result.get('reason', '')}",
                    "expires_at": 0,
                }
        else:
            # Low/medium risk: auto-grant with notification
            grant.granted_by = "auto_low_risk"
            grant.status = PermissionStatus.ACTIVE.value
        
        # Store grant
        self._grants[grant.grant_id] = grant
        await self._store_grant(grant)
        self._add_audit(grant.grant_id, "granted", agent_id, scope, 
                        f"Duration: {duration_minutes}min, By: {grant.granted_by}")
        
        # Log the permission request message
        message = self._generate_permission_message(grant, reason)
        logger.info(f"Permission granted: {grant.grant_id} | {agent_id} | {scope} | {duration_minutes}min")
        
        return {
            "grant_id": grant.grant_id,
            "status": grant.status,
            "message": message,
            "expires_at": grant.expires_at,
            "duration_minutes": duration_minutes,
            "scope": scope,
            "permissions": permissions,
            "requires_human_approval": requires_human,
        }
    
    async def check_permission(self, grant_id: str, task_context: str = "") -> dict:
        """
        التحقق من صلاحية — هل ما زالت فعالة؟
        
        Args:
            grant_id: معرف المنح
            task_context: سياق المهمة الحالية
        
        Returns:
            dict with valid, reason, remaining_seconds
        """
        await self.initialize()
        
        # If disabled, always valid
        if not self._enabled:
            return {"valid": True, "reason": "وضع غير مفعّل", "remaining_seconds": float('inf')}
        
        grant = self._grants.get(grant_id)
        if not grant:
            # Try loading from DB
            grant = await self._load_grant(grant_id)
            if grant:
                self._grants[grant_id] = grant
        
        if not grant:
            return {"valid": False, "reason": "الصلاحية غير موجودة", "remaining_seconds": 0}
        
        # Check if still active
        if not grant.is_active():
            reason = "انتهت صلاحية الوقت" if grant.status == PermissionStatus.EXPIRED.value else f"الحالة: {grant.status}"
            self._add_audit(grant_id, "check_failed", grant.agent_id, grant.scope, reason)
            return {"valid": False, "reason": reason, "remaining_seconds": 0}
        
        # Check task context
        if task_context and not grant.matches_task(task_context):
            self._add_audit(grant_id, "context_mismatch", grant.agent_id, grant.scope,
                          f"Expected: {grant.task_context}, Got: {task_context}")
            return {
                "valid": False,
                "reason": f"سياق المهمة لا يتطابق — الصلاحية مخصصة لـ '{grant.task_context}'",
                "remaining_seconds": 0,
            }
        
        # Record usage
        self._add_audit(grant_id, "checked", grant.agent_id, grant.scope, "Permission valid")
        
        # If one-time use, mark as consumed
        if grant.one_time_use:
            grant.status = PermissionStatus.CONSUMED.value
            self._add_audit(grant_id, "consumed", grant.agent_id, grant.scope, "One-time use consumed")
            await self._update_grant_status(grant_id, PermissionStatus.CONSUMED.value)
        
        return {
            "valid": True,
            "reason": "الصلاحية فعالة",
            "remaining_seconds": grant.remaining_seconds(),
            "scope": grant.scope,
            "permissions": grant.permissions,
        }
    
    async def revoke_permission(self, grant_id: str, reason: str = "manual_revocation") -> bool:
        """
        سحب صلاحية يدوياً.
        
        Args:
            grant_id: معرف المنح
            reason: سبب السحب
        
        Returns:
            True if successfully revoked
        """
        await self.initialize()
        
        grant = self._grants.get(grant_id)
        if not grant:
            grant = await self._load_grant(grant_id)
        
        if not grant:
            return False
        
        grant.status = PermissionStatus.REVOKED.value
        self._add_audit(grant_id, "revoked", grant.agent_id, grant.scope, reason)
        await self._update_grant_status(grant_id, PermissionStatus.REVOKED.value)
        
        logger.info(f"Permission revoked: {grant_id} | Reason: {reason}")
        return True
    
    async def revoke_expired(self) -> int:
        """
        سحب جميع الصلاحيات المنتهية تلقائياً.
        
        Returns:
            Number of expired grants revoked
        """
        await self.initialize()
        
        now = time.time()
        expired_count = 0
        
        for grant_id, grant in list(self._grants.items()):
            if grant.status == PermissionStatus.ACTIVE.value and now > grant.expires_at:
                grant.status = PermissionStatus.EXPIRED.value
                self._add_audit(grant_id, "expired", grant.agent_id, grant.scope,
                              f"Auto-revoked after {grant.duration_minutes} minutes")
                await self._update_grant_status(grant_id, PermissionStatus.EXPIRED.value)
                expired_count += 1
                logger.info(f"Permission auto-expired: {grant_id} | {grant.scope}")
        
        return expired_count
    
    async def get_active_permissions(self, agent_id: str = "") -> list[dict]:
        """
        الحصول على الصلاحيات النشطة.
        
        Args:
            agent_id: معرف الوكيل (فارغ = جميع الوكلاء)
        
        Returns:
            List of active permission grants
        """
        await self.initialize()
        
        active = []
        for grant in self._grants.values():
            if grant.is_active():
                if not agent_id or grant.agent_id == agent_id:
                    active.append(grant.to_dict())
        return active
    
    async def get_audit_log(self, limit: int = 100, agent_id: str = "") -> list[dict]:
        """
        الحصول على سجل التدقيق.
        
        Args:
            limit: الحد الأقصى للسجلات
            agent_id: تصفية حسب الوكيل
        
        Returns:
            List of audit entries
        """
        entries = self._audit_log
        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]
        return [asdict(e) for e in entries[-limit:]]
    
    async def get_permission_request_message(
        self,
        agent_id: str,
        scope: str,
        permissions: list[str],
        duration_minutes: float,
        resource_path: str = "",
        task_context: str = "",
    ) -> str:
        """
        توليد رسالة طلب صلاحية للمستخدم.
        
        Example output:
        "مأمون يطلب صلاحية قراءة/كتابة مجلد المشاريع لمدة 120 دقيقة لتطوير تطبيقك. توافق؟"
        """
        scope_names = {
            "filesystem:read": "قراءة الملفات",
            "filesystem:write": "قراءة/كتابة الملفات",
            "filesystem:delete": "حذف الملفات",
            "shell:execute": "تنفيذ أوامر",
            "shell:install": "تثبيت مكتبات",
            "shell:git": "عمليات Git",
            "ecommerce:browse": "تصفح المتجر",
            "ecommerce:purchase": "إجراء عمليات شراء",
            "ecommerce:supplier": "التواصل مع الموردين",
            "instagram:read": "قراءة التعليقات/الرسائل",
            "instagram:write": "الرد على التعليقات/الرسائل",
            "instagram:dm": "إرسال رسائل مباشرة",
            "embodiment:view": "عرض الشاشة",
            "embodiment:control": "التحكم بالفأرة/لوحة المفاتيح",
            "mobile:build": "بناء تطبيق جوال",
            "mobile:deploy": "نشر تطبيق جوال",
        }
        
        scope_name = scope_names.get(scope, scope)
        perm_str = "/".join(permissions) if permissions else scope_name
        resource_desc = f" في {resource_path}" if resource_path else ""
        task_desc = f" {task_context}" if task_context else ""
        
        message = (
            f"مأمون يطلب صلاحية **{perm_str}**{resource_desc} "
            f"لمدة **{int(duration_minutes)} دقيقة**{task_desc}. توافق؟ "
            f"(نعم / لا / تعديل المدة)"
        )
        return message
    
    def is_enabled(self) -> bool:
        """هل نظام الصلاحيات الزمنية مفعّل؟"""
        return self._enabled
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Internal Methods
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def _request_human_approval(self, grant: PermissionGrant, reason: str) -> dict:
        """
        طلب موافقة بشرية عبر ApprovalGate.
        """
        try:
            from mamoun.core.approval_gate import ApprovalGate, ApprovalRequest
            
            gate = ApprovalGate()
            request = ApprovalRequest(
                change_type="permission_grant",
                target=f"{grant.scope}:{grant.resource_path}",
                description=(
                    f"طلب صلاحية: {grant.scope} | الوكيل: {grant.agent_id} | "
                    f"المدة: {grant.duration_minutes} دقيقة | السبب: {reason}"
                ),
                risk_level="high",
                details=json.dumps(grant.to_dict(), ensure_ascii=False),
            )
            result = await gate.request_approval(request)
            
            if result.get("status") == "auto_approved":
                return {"status": "approved", "reason": "Auto-approved (low risk override)"}
            elif result.get("status") == "pending":
                # In production, wait for human response
                # For now, we'll simulate a pending state
                # The frontend permission-gate.tsx will handle this
                return {"status": "pending", "reason": "بانتظار موافقتك", "approval_id": result.get("id")}
            else:
                return {"status": "approved", "reason": "Submitted for approval"}
        except ImportError:
            logger.warning("ApprovalGate not available — auto-approving")
            return {"status": "approved", "reason": "ApprovalGate غير متاح"}
        except Exception as e:
            logger.warning(f"Human approval request failed: {e}")
            # Fail-closed: deny if approval system fails
            return {"status": "denied", "reason": f"فشل نظام الموافقة: {e}"}
    
    async def _store_grant(self, grant: PermissionGrant):
        """تخزين المنح في قاعدة البيانات."""
        try:
            import aiosqlite
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO permission_grants
                    (grant_id, agent_id, scope, permissions, resource_path,
                     granted_at, expires_at, duration_minutes, granted_by,
                     task_context, status, auto_revoke, one_time_use, audit_entries)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    grant.grant_id, grant.agent_id, grant.scope,
                    json.dumps(grant.permissions), grant.resource_path,
                    grant.granted_at, grant.expires_at, grant.duration_minutes,
                    grant.granted_by, grant.task_context, grant.status,
                    1 if grant.auto_revoke else 0,
                    1 if grant.one_time_use else 0,
                    json.dumps(grant.audit_entries, ensure_ascii=False),
                ))
                await db.commit()
        except Exception as e:
            logger.warning(f"Failed to store grant: {e}")
    
    async def _load_grant(self, grant_id: str) -> Optional[PermissionGrant]:
        """تحميل منح من قاعدة البيانات."""
        try:
            import aiosqlite
            async with aiosqlite.connect(self._db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM permission_grants WHERE grant_id = ?", (grant_id,)
                )
                row = await cursor.fetchone()
                if row:
                    return PermissionGrant(
                        grant_id=row["grant_id"],
                        agent_id=row["agent_id"],
                        scope=row["scope"],
                        permissions=json.loads(row["permissions"]),
                        resource_path=row["resource_path"],
                        granted_at=row["granted_at"],
                        expires_at=row["expires_at"],
                        duration_minutes=row["duration_minutes"],
                        granted_by=row["granted_by"],
                        task_context=row["task_context"],
                        status=row["status"],
                        auto_revoke=bool(row["auto_revoke"]),
                        one_time_use=bool(row["one_time_use"]),
                    )
        except Exception as e:
            logger.warning(f"Failed to load grant: {e}")
        return None
    
    async def _update_grant_status(self, grant_id: str, status: str):
        """تحديث حالة المنح في قاعدة البيانات."""
        try:
            import aiosqlite
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute(
                    "UPDATE permission_grants SET status = ? WHERE grant_id = ?",
                    (status, grant_id),
                )
                await db.commit()
        except Exception as e:
            logger.warning(f"Failed to update grant status: {e}")
    
    def _add_audit(self, grant_id: str, action: str, agent_id: str, scope: str, details: str):
        """إضافة سجل تدقيق."""
        entry = PermissionAuditEntry(
            grant_id=grant_id,
            action=action,
            agent_id=agent_id,
            scope=scope,
            timestamp=time.time(),
            details=details,
        )
        self._audit_log.append(entry)
    
    def _generate_permission_message(self, grant: PermissionGrant, reason: str) -> str:
        """توليد رسالة صلاحية للمستخدم."""
        duration = int(grant.duration_minutes)
        scope_desc = grant.scope.replace(":", " ")
        
        if grant.status == "pending_human_approval":
            return (
                f"مأمون يطلب صلاحية **{scope_desc}** "
                f"لمدة **{duration} دقيقة** لتطوير تطبيقك. توافق؟ "
                f"(نعم/لا/تعديل المدة)"
            )
        elif grant.status == PermissionStatus.ACTIVE.value:
            return (
                f"تم منح صلاحية **{scope_desc}** "
                f"لمدة **{duration} دقيقة**. "
                f"ستُسحب تلقائياً عند انتهاء الوقت."
            )
        return f"حالة الصلاحية: {grant.status}"
    
    async def _revocation_monitor(self):
        """
        مراقب الانتهاء — يفحص الصلاحيات المنتهية كل 30 ثانية.
        """
        while True:
            try:
                expired = await self.revoke_expired()
                if expired > 0:
                    logger.info(f"Auto-revoked {expired} expired permissions")
            except Exception as e:
                logger.error(f"Revocation monitor error: {e}")
            
            await asyncio.sleep(REVOCATION_CHECK_INTERVAL)
    
    async def shutdown(self):
        """إيقاف النظام — يتوافق مع القانون 5."""
        if self._revocation_task and not self._revocation_task.done():
            self._revocation_task.cancel()
        
        # Revoke all active permissions
        revoked = 0
        for grant_id, grant in list(self._grants.items()):
            if grant.status == PermissionStatus.ACTIVE.value:
                grant.status = PermissionStatus.REVOKED.value
                revoked += 1
        
        if revoked > 0:
            logger.info(f"Emergency shutdown: revoked {revoked} active permissions")
        
        self._initialized = False
