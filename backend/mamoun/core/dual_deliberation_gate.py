"""
Dual Deliberation Gate — غرفة المداولة المزدوجة
v16.0

Separates modification requests into two streams:
1. AUTOMATIC: Low-risk improvements (parameter tuning, prompt adjustments, UI tweaks)
   - Auto-approved if confidence > threshold
   - Still logged for audit
   - Can be rolled back within 24 hours

2. HUMAN: High-risk changes (code modifications, deployments, architecture changes)
   - Always require human approval
   - Time-bounded: auto-rejected after 48 hours if no response
   - Escalation path for urgent changes

Based on: "Safety by construction, not detection"
and auto_approval_policy.yaml from v40.0
"""

import json
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path
from enum import Enum

logger = logging.getLogger("mamoun.core.dual_gate")


class DeliberationPath(str, Enum):
    AUTOMATIC = "automatic"    # مسار تلقائي — تحسينات منخفضة المخاطر
    HUMAN = "human"            # مسار بشري — تغييرات مصيرية


class GateDecision(str, Enum):
    AUTO_APPROVED = "auto_approved"
    PENDING_HUMAN = "pending_human"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ESCALATED = "escalated"


class ModificationRequest:
    """A request for modification that goes through the Dual Deliberation Gate."""
    
    def __init__(
        self,
        description: str,
        modification_type: str,
        risk_level: str,
        scope: str,
        proposed_changes: dict,
        confidence: float = 0.5,
        domain: str = "general",
        curriculum_phase: str = "phase_1_parameter_tuning",
    ):
        self.id = f"gate_{int(time.time())}_{modification_type[:3]}"
        self.description = description
        self.modification_type = modification_type
        self.risk_level = risk_level  # safe, low, medium, high, critical
        self.scope = scope  # local, module, system
        self.proposed_changes = proposed_changes
        self.confidence = confidence
        self.domain = domain
        self.curriculum_phase = curriculum_phase
        self.path: DeliberationPath = DeliberationPath.HUMAN  # Default to human
        self.decision: GateDecision = GateDecision.PENDING_HUMAN
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.expires_at = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
        self.reviewed_at: Optional[str] = None
        self.reviewed_by: Optional[str] = None  # "system" or user_id
        self.rollback_before: Optional[dict] = None  # State before modification
        self.auto_rollback_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "modification_type": self.modification_type,
            "risk_level": self.risk_level,
            "scope": self.scope,
            "proposed_changes": self.proposed_changes,
            "confidence": self.confidence,
            "domain": self.domain,
            "curriculum_phase": self.curriculum_phase,
            "path": self.path.value,
            "decision": self.decision.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "reviewed_at": self.reviewed_at,
            "reviewed_by": self.reviewed_by,
        }


class DualDeliberationGate:
    """
    The Dual Deliberation Gate — two paths for modification requests.
    """
    
    # Auto-approval rules
    AUTO_APPROVE_RULES = {
        # Phase 1 (Parameter Tuning): auto-approve low risk
        "phase_1_parameter_tuning": {
            "auto_approve_risk": ["safe", "low"],
            "min_confidence": 0.3,
            "auto_rollback_hours": 24,
        },
        # Phase 2 (Prompt Optimization): auto-approve safe only
        "phase_2_prompt_optimization": {
            "auto_approve_risk": ["safe"],
            "min_confidence": 0.5,
            "auto_rollback_hours": 24,
        },
        # Phase 3+: ALWAYS require human approval
        "phase_3_code_patches": {
            "auto_approve_risk": [],
            "min_confidence": 1.0,  # Impossible — always needs approval
        },
        "phase_4_structural_changes": {
            "auto_approve_risk": [],
            "min_confidence": 1.0,
        },
        "phase_5_meta_modification": {
            "auto_approve_risk": [],
            "min_confidence": 1.0,
        },
    }
    
    # Never auto-approve these modification types
    NEVER_AUTO_APPROVE = [
        "code_patch", "deployment", "architecture_change",
        "database_migration", "security_policy_change",
        "api_route_change", "env_variable_change",
    ]
    
    def __init__(self, data_dir: str = "backend/data/dual_gate"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.requests_path = self.data_dir / "gate_requests.jsonl"
        self.requests: list[ModificationRequest] = self._load_requests()
    
    def _load_requests(self) -> list:
        requests = []
        if self.requests_path.exists():
            with open(self.requests_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            req = ModificationRequest(
                                description=data["description"],
                                modification_type=data["modification_type"],
                                risk_level=data["risk_level"],
                                scope=data["scope"],
                                proposed_changes=data.get("proposed_changes", {}),
                                confidence=data.get("confidence", 0.5),
                                domain=data.get("domain", "general"),
                                curriculum_phase=data.get("curriculum_phase", "phase_1_parameter_tuning"),
                            )
                            req.id = data["id"]
                            req.path = DeliberationPath(data.get("path", "human"))
                            req.decision = GateDecision(data.get("decision", "pending_human"))
                            req.created_at = data.get("created_at", "")
                            requests.append(req)
                        except Exception:
                            continue
        return requests
    
    def _save_request(self, req: ModificationRequest):
        with open(self.requests_path, "a") as f:
            f.write(json.dumps(req.to_dict(), ensure_ascii=False) + "\n")
    
    def submit(self, request: ModificationRequest) -> dict:
        """
        Submit a modification request through the Dual Deliberation Gate.
        Determines which path (automatic or human) it should take.
        """
        # Determine the path
        rules = self.AUTO_APPROVE_RULES.get(
            request.curriculum_phase,
            self.AUTO_APPROVE_RULES["phase_3_code_patches"],
        )
        
        can_auto_approve = (
            request.risk_level in rules.get("auto_approve_risk", [])
            and request.confidence >= rules.get("min_confidence", 1.0)
            and request.modification_type not in self.NEVER_AUTO_APPROVE
        )
        
        if can_auto_approve:
            request.path = DeliberationPath.AUTOMATIC
            request.decision = GateDecision.AUTO_APPROVED
            request.reviewed_by = "system"
            request.reviewed_at = datetime.now(timezone.utc).isoformat()
            
            # Set auto-rollback timer
            rollback_hours = rules.get("auto_rollback_hours", 24)
            request.auto_rollback_at = (
                datetime.now(timezone.utc) + timedelta(hours=rollback_hours)
            ).isoformat()
            
            logger.info("Auto-approved: %s (%s)", request.id, request.description[:50])
        else:
            request.path = DeliberationPath.HUMAN
            request.decision = GateDecision.PENDING_HUMAN
            
            logger.info("Pending human approval: %s (%s)", request.id, request.description[:50])
        
        self._save_request(request)
        self.requests.append(request)
        
        return {
            "request_id": request.id,
            "path": request.path.value,
            "decision": request.decision.value,
            "expires_at": request.expires_at,
            "auto_rollback_at": request.auto_rollback_at,
            "message": (
                f"تمت الموافقة التلقائية على: {request.description}"
                if can_auto_approve
                else f"بانتظار موافقة بشرية على: {request.description}"
            ),
        }
    
    def approve(self, request_id: str, reviewer: str = "user") -> bool:
        """Manually approve a pending request."""
        for req in self.requests:
            if req.id == request_id and req.decision == GateDecision.PENDING_HUMAN:
                req.decision = GateDecision.AUTO_APPROVED  # Reuse for approved
                req.reviewed_by = reviewer
                req.reviewed_at = datetime.now(timezone.utc).isoformat()
                self._save_request(req)
                return True
        return False
    
    def reject(self, request_id: str, reviewer: str = "user") -> bool:
        """Reject a pending request."""
        for req in self.requests:
            if req.id == request_id and req.decision == GateDecision.PENDING_HUMAN:
                req.decision = GateDecision.REJECTED
                req.reviewed_by = reviewer
                req.reviewed_at = datetime.now(timezone.utc).isoformat()
                self._save_request(req)
                return True
        return False
    
    def check_expired(self) -> list[str]:
        """Check for and expire old pending requests."""
        expired = []
        now = datetime.now(timezone.utc)
        
        for req in self.requests:
            if req.decision == GateDecision.PENDING_HUMAN:
                expires = datetime.fromisoformat(req.expires_at)
                if now > expires:
                    req.decision = GateDecision.EXPIRED
                    expired.append(req.id)
                    self._save_request(req)
        
        return expired
    
    def get_pending(self) -> list[dict]:
        """Get all pending human-approval requests."""
        return [
            req.to_dict()
            for req in self.requests
            if req.decision == GateDecision.PENDING_HUMAN
        ]
    
    def get_recent(self, limit: int = 20) -> list[dict]:
        return [req.to_dict() for req in self.requests[-limit:]]
    
    def get_statistics(self) -> dict:
        decisions = {}
        for req in self.requests:
            d = req.decision.value
            decisions[d] = decisions.get(d, 0) + 1
        
        return {
            "total_requests": len(self.requests),
            "decisions": decisions,
            "auto_approval_rate": (
                decisions.get("auto_approved", 0) / len(self.requests)
                if self.requests else 0
            ),
            "pending_count": decisions.get("pending_human", 0),
        }
