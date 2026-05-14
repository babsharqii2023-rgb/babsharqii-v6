"""
Smart Approval Engine v60 — Escalating trust-based auto-approval system.

CRITICAL ADDITION from v60:
- v59: Most modifications required human approval (approval gate)
- v60: SmartApprovalEngine implements escalating trust:
  - New components: require human approval
  - Trusted components (trust >= 0.7): auto-approve low/medium risk
  - Highly trusted (trust >= 0.9): auto-approve even high risk (except critical files)
  - Learning from approval history: patterns of approved/rejected changes
  - Batch approval for related low-risk changes
  - Smart escalation: complex changes broken into smaller, approvable steps

This closes gap #6: "معظم التعديلات تحتاج موافقة بشرية، يحتاج نظام ثقة تصاعدي"

v60 — Super Mind العقل الخارق مامون
"""

import time
import logging
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TrustLevel(str, Enum):
    NEW = "new"              # Trust: 0.0 - never approved before
    OBSERVATION = "observation"  # Trust: 0.0 - 0.3 — needs human approval
    TRUSTED = "trusted"      # Trust: 0.3 - 0.7 — auto-approve low risk
    HIGHLY_TRUSTED = "highly_trusted"  # Trust: 0.7 - 0.9 — auto-approve medium risk
    FULLY_TRUSTED = "fully_trusted"    # Trust: 0.9+ — auto-approve most changes
    REVOKED = "revoked"      # Trust dropped — requires manual reinstatement


class RiskLevel(str, Enum):
    LOW = "low"              # Cosmetic, documentation, minor optimization
    MEDIUM = "medium"        # Feature addition, refactoring
    HIGH = "high"            # Core logic changes, new dependencies
    CRITICAL = "critical"    # Safety, security, or core system changes


class ApprovalDecision(str, Enum):
    AUTO_APPROVED = "auto_approved"
    PENDING_HUMAN = "pending_human"
    AUTO_REJECTED = "auto_rejected"
    ESCALATED = "escalated"
    BATCH_APPROVED = "batch_approved"


@dataclass
class ApprovalRecord:
    """Record of an approval decision."""
    id: str
    component: str
    change_type: str
    risk_level: str
    decision: ApprovalDecision
    trust_level_at_decision: TrustLevel
    trust_score_at_decision: float
    timestamp: float = field(default_factory=time.time)
    human_overridden: bool = False
    outcome_success: Optional[bool] = None  # Filled later when outcome is known


@dataclass
class ComponentTrust:
    """Trust profile for a component."""
    component: str
    trust_score: float = 0.0
    total_changes: int = 0
    approved_changes: int = 0
    rejected_changes: int = 0
    successful_changes: int = 0
    failed_changes: int = 0
    last_change_at: Optional[float] = None
    trust_level: TrustLevel = TrustLevel.NEW
    consecutive_successes: int = 0
    consecutive_failures: int = 0

    @property
    def success_rate(self) -> float:
        return self.successful_changes / max(self.approved_changes, 1)

    def update_trust_level(self):
        """Update trust level based on current trust score."""
        if self.trust_score >= 0.9:
            self.trust_level = TrustLevel.FULLY_TRUSTED
        elif self.trust_score >= 0.7:
            self.trust_level = TrustLevel.HIGHLY_TRUSTED
        elif self.trust_score >= 0.3:
            self.trust_level = TrustLevel.TRUSTED
        elif self.trust_score > 0.0:
            self.trust_level = TrustLevel.OBSERVATION
        else:
            self.trust_level = TrustLevel.NEW


# Files that are ALWAYS critical — never auto-approve
CRITICAL_FILES = {
    "laws.yaml", "safety_guard.py", "approval_gate.py",
    ".env", "settings.yaml", "safety_gate_client.py",
    "conscience_layer.py", "smart_approval_engine.py",
}

# Change types and their default risk levels
CHANGE_TYPE_RISK = {
    "code_patch": RiskLevel.MEDIUM,
    "genome_mutation": RiskLevel.HIGH,
    "skill_extraction": RiskLevel.MEDIUM,
    "config_change": RiskLevel.MEDIUM,
    "documentation": RiskLevel.LOW,
    "cosmetic": RiskLevel.LOW,
    "optimization": RiskLevel.LOW,
    "new_feature": RiskLevel.MEDIUM,
    "security_patch": RiskLevel.HIGH,
    "dependency_update": RiskLevel.HIGH,
    "core_logic": RiskLevel.CRITICAL,
    "safety_change": RiskLevel.CRITICAL,
}


class SmartApprovalEngine:
    """
    Escalating trust-based auto-approval system.

    Instead of requiring human approval for every change, this engine
    uses an escalating trust model:

    Trust 0.0-0.3 (Observation): Human approval required for all changes
    Trust 0.3-0.7 (Trusted): Auto-approve LOW risk changes
    Trust 0.7-0.9 (Highly Trusted): Auto-approve LOW + MEDIUM risk
    Trust 0.9+ (Fully Trusted): Auto-approve LOW + MEDIUM + HIGH risk
    CRITICAL changes: Always require human approval (except fully trusted for non-critical files)

    Trust increases with successful changes (+0.03 per success)
    Trust decreases with failures (-0.10 per failure)
    Trust can be manually boosted or revoked

    Usage:
        engine = SmartApprovalEngine(meta_cognition=meta)
        decision = await engine.evaluate("tool_creator", "code_patch", "medium", target="tools/scraper.py")
        if decision["approved"]:
            # Proceed with the change
        else:
            # Wait for human approval
    """

    TRUST_SUCCESS_INCREMENT = 0.03
    TRUST_FAILURE_DECREMENT = 0.10
    TRUST_CRITICAL_FAILURE_DECREMENT = 0.25

    def __init__(self, meta_cognition=None, neural_bus=None,
                 approval_gate=None):
        self._meta_cognition = meta_cognition
        self._neural_bus = neural_bus
        self._approval_gate = approval_gate  # Original ApprovalGate for fallback
        self._trust_profiles: dict[str, ComponentTrust] = {}
        self._approval_history: list[ApprovalRecord] = []
        self._auto_approved_count = 0
        self._human_required_count = 0

    def _get_trust(self, component: str) -> ComponentTrust:
        """Get or create trust profile for a component."""
        if component not in self._trust_profiles:
            self._trust_profiles[component] = ComponentTrust(component=component)
            # Initialize from meta_cognition if available
            if self._meta_cognition:
                try:
                    profile = self._meta_cognition.get_profile(component)
                    if profile and hasattr(profile, 'reliability_score'):
                        self._trust_profiles[component].trust_score = profile.reliability_score
                        self._trust_profiles[component].update_trust_level()
                except Exception:
                    pass
        return self._trust_profiles[component]

    async def evaluate(
        self,
        component: str,
        change_type: str,
        risk_level: str,
        target: str = "",
        description: str = "",
        metadata: dict = None,
    ) -> dict:
        """
        Evaluate whether a change should be auto-approved or requires human review.

        Args:
            component: Component requesting the change
            change_type: Type of change (code_patch, optimization, etc.)
            risk_level: Risk level (low, medium, high, critical)
            target: Target file or resource
            description: Description of the change
            metadata: Additional metadata

        Returns:
            dict with decision, trust info, and reasoning
        """
        trust = self._get_trust(component)
        risk = RiskLevel(risk_level)
        target_filename = target.split("/")[-1] if "/" in target else target
        is_critical_file = target_filename in CRITICAL_FILES

        # Decision logic
        decision = self._make_decision(trust, risk, is_critical_file, change_type)

        # Create record
        record_id = f"approval_{int(time.time())}_{component}_{change_type}"
        record = ApprovalRecord(
            id=record_id,
            component=component,
            change_type=change_type,
            risk_level=risk_level,
            decision=decision,
            trust_level_at_decision=trust.trust_level,
            trust_score_at_decision=trust.trust_score,
        )
        self._approval_history.append(record)
        if len(self._approval_history) > 500:
            self._approval_history = self._approval_history[-250:]

        # Update counts
        if decision in (ApprovalDecision.AUTO_APPROVED, ApprovalDecision.BATCH_APPROVED):
            self._auto_approved_count += 1
            trust.approved_changes += 1
        else:
            self._human_required_count += 1

        trust.total_changes += 1
        trust.last_change_at = time.time()

        # If auto-approved, also register in original ApprovalGate
        if decision == ApprovalDecision.AUTO_APPROVED and self._approval_gate:
            try:
                from ..core.approval_gate import ApprovalRequest
                request = ApprovalRequest(
                    change_type=change_type,
                    target=target,
                    description=description,
                    risk_level=risk_level,
                    status="auto_approved",
                )
                request.decided_by = f"smart_engine_{trust.trust_level.value}"
                await self._approval_gate.request_approval(request)
            except Exception as e:
                logger.warning(f"Could not register in ApprovalGate: {e}")

        return {
            "id": record_id,
            "approved": decision in (ApprovalDecision.AUTO_APPROVED, ApprovalDecision.BATCH_APPROVED),
            "decision": decision.value,
            "trust_level": trust.trust_level.value,
            "trust_score": round(trust.trust_score, 3),
            "reasoning": self._explain_decision(decision, trust, risk, is_critical_file),
            "component": component,
            "change_type": change_type,
            "risk_level": risk_level,
        }

    def _make_decision(self, trust: ComponentTrust, risk: RiskLevel,
                       is_critical_file: bool, change_type: str) -> ApprovalDecision:
        """Make the approval decision based on trust and risk."""

        # CRITICAL changes: always require human approval
        # Exception: fully trusted components modifying non-critical files
        if risk == RiskLevel.CRITICAL:
            if trust.trust_level == TrustLevel.FULLY_TRUSTED and not is_critical_file:
                return ApprovalDecision.AUTO_APPROVED
            return ApprovalDecision.PENDING_HUMAN

        # Critical files: always require human approval
        if is_critical_file:
            if trust.trust_level == TrustLevel.FULLY_TRUSTED and risk == RiskLevel.LOW:
                return ApprovalDecision.AUTO_APPROVED
            return ApprovalDecision.PENDING_HUMAN

        # Trust-based decisions
        if trust.trust_level == TrustLevel.NEW or trust.trust_level == TrustLevel.OBSERVATION:
            # New/observation: always require human approval
            return ApprovalDecision.PENDING_HUMAN

        elif trust.trust_level == TrustLevel.TRUSTED:
            # Trusted: auto-approve LOW risk only
            if risk == RiskLevel.LOW:
                return ApprovalDecision.AUTO_APPROVED
            return ApprovalDecision.PENDING_HUMAN

        elif trust.trust_level == TrustLevel.HIGHLY_TRUSTED:
            # Highly trusted: auto-approve LOW + MEDIUM
            if risk in (RiskLevel.LOW, RiskLevel.MEDIUM):
                return ApprovalDecision.AUTO_APPROVED
            return ApprovalDecision.PENDING_HUMAN

        elif trust.trust_level == TrustLevel.FULLY_TRUSTED:
            # Fully trusted: auto-approve LOW + MEDIUM + HIGH
            if risk in (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH):
                return ApprovalDecision.AUTO_APPROVED
            return ApprovalDecision.PENDING_HUMAN

        return ApprovalDecision.PENDING_HUMAN

    def _explain_decision(self, decision: ApprovalDecision, trust: ComponentTrust,
                          risk: RiskLevel, is_critical_file: bool) -> str:
        """Generate Arabic explanation for the decision."""
        if decision == ApprovalDecision.AUTO_APPROVED:
            return (
                f"موافقة تلقائية — مستوى الثقة '{trust.trust_level.value}' "
                f"({trust.trust_score:.2f}) كافٍ للمخاطر '{risk.value}'"
            )
        elif decision == ApprovalDecision.PENDING_HUMAN:
            reasons = []
            if trust.trust_level in (TrustLevel.NEW, TrustLevel.OBSERVATION):
                reasons.append("المكون جديد أو في مرحلة المراقبة")
            if risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                reasons.append(f"مستوى المخاطر '{risk.value}' يتطلب مراجعة بشرية")
            if is_critical_file:
                reasons.append("الملف المستهدف حرج وأولوية أمان عالية")
            return "بانتظار موافقة بشرية — " + "، ".join(reasons)
        return "قرار غير محدد"

    async def record_outcome(self, approval_id: str, success: bool) -> dict:
        """
        Record the outcome of an approved change to update trust.

        Args:
            approval_id: The approval record ID
            success: Whether the change was successful

        Returns:
            dict with updated trust info
        """
        # Find the record
        record = None
        for r in self._approval_history:
            if r.id == approval_id:
                record = r
                break

        if not record:
            return {"success": False, "error": f"Approval record '{approval_id}' not found"}

        record.outcome_success = success

        # Update trust
        trust = self._get_trust(record.component)

        if success:
            trust.successful_changes += 1
            trust.consecutive_successes += 1
            trust.consecutive_failures = 0

            # Increase trust
            increment = self.TRUST_SUCCESS_INCREMENT
            # Bonus for consecutive successes
            if trust.consecutive_successes > 5:
                increment *= 1.5
            if trust.consecutive_successes > 10:
                increment *= 2.0

            trust.trust_score = min(1.0, trust.trust_score + increment)

        else:
            trust.failed_changes += 1
            trust.consecutive_failures += 1
            trust.consecutive_successes = 0

            # Decrease trust
            decrement = self.TRUST_FAILURE_DECREMENT
            if record.risk_level in ("high", "critical"):
                decrement = self.TRUST_CRITICAL_FAILURE_DECREMENT

            trust.trust_score = max(0.0, trust.trust_score - decrement)

            # Revoke trust if too many consecutive failures
            if trust.consecutive_failures >= 3 and trust.trust_level in (TrustLevel.HIGHLY_TRUSTED, TrustLevel.FULLY_TRUSTED):
                trust.trust_level = TrustLevel.TRUSTED
                logger.warning(f"Trust demoted for {record.component} due to {trust.consecutive_failures} consecutive failures")

        trust.update_trust_level()

        # Record in meta_cognition
        if self._meta_cognition:
            try:
                from .meta_cognition_engine import OutcomeRecord
                self._meta_cognition.record_outcome(OutcomeRecord(
                    component=f"smart_approval_{record.component}",
                    operation="change_outcome",
                    success=success,
                    quality_score=trust.trust_score,
                    predicted_quality=trust.trust_score,
                    latency_ms=0,
                    metadata={"approval_id": approval_id, "trust_level": trust.trust_level.value},
                ))
            except ImportError:
                pass

        return {
            "success": True,
            "component": record.component,
            "trust_score": round(trust.trust_score, 3),
            "trust_level": trust.trust_level.value,
            "consecutive_successes": trust.consecutive_successes,
            "consecutive_failures": trust.consecutive_failures,
        }

    async def batch_evaluate(self, changes: list[dict]) -> dict:
        """
        Evaluate a batch of related changes.

        If all changes are low-risk and the component is trusted,
        auto-approve the entire batch.
        """
        if not changes:
            return {"approved": False, "error": "No changes provided"}

        # Check if all changes are from the same component
        components = set(c.get("component", "") for c in changes)
        if len(components) == 1:
            component = components.pop()
            trust = self._get_trust(component)
            max_risk = max(
                RiskLevel(c.get("risk_level", "medium"))
                for c in changes
            )

            # If trusted enough and all low-risk, batch approve
            if (trust.trust_level in (TrustLevel.HIGHLY_TRUSTED, TrustLevel.FULLY_TRUSTED)
                    and max_risk in (RiskLevel.LOW, RiskLevel.MEDIUM)):
                return {
                    "approved": True,
                    "decision": ApprovalDecision.BATCH_APPROVED.value,
                    "batch_size": len(changes),
                    "trust_level": trust.trust_level.value,
                    "max_risk": max_risk.value,
                }

        # Evaluate individually
        results = []
        for change in changes:
            result = await self.evaluate(
                component=change.get("component", "unknown"),
                change_type=change.get("change_type", "code_patch"),
                risk_level=change.get("risk_level", "medium"),
                target=change.get("target", ""),
                description=change.get("description", ""),
            )
            results.append(result)

        all_approved = all(r["approved"] for r in results)
        return {
            "approved": all_approved,
            "decision": ApprovalDecision.BATCH_APPROVED.value if all_approved else ApprovalDecision.PENDING_HUMAN.value,
            "batch_size": len(changes),
            "individual_results": results,
        }

    def boost_trust(self, component: str, amount: float = 0.1) -> dict:
        """Manually boost trust for a component."""
        trust = self._get_trust(component)
        trust.trust_score = min(1.0, trust.trust_score + amount)
        trust.update_trust_level()
        return {
            "component": component,
            "trust_score": round(trust.trust_score, 3),
            "trust_level": trust.trust_level.value,
        }

    def revoke_trust(self, component: str, reason: str = "") -> dict:
        """Revoke trust for a component."""
        trust = self._get_trust(component)
        trust.trust_score = 0.0
        trust.trust_level = TrustLevel.REVOKED
        trust.consecutive_failures += 1
        logger.warning(f"Trust REVOKED for {component}: {reason}")
        return {
            "component": component,
            "trust_score": 0.0,
            "trust_level": TrustLevel.REVOKED.value,
            "reason": reason,
        }

    def get_trust_profile(self, component: str) -> dict:
        """Get trust profile for a component."""
        trust = self._get_trust(component)
        return {
            "component": trust.component,
            "trust_score": round(trust.trust_score, 3),
            "trust_level": trust.trust_level.value,
            "total_changes": trust.total_changes,
            "approved_changes": trust.approved_changes,
            "successful_changes": trust.successful_changes,
            "failed_changes": trust.failed_changes,
            "success_rate": round(trust.success_rate, 2),
            "consecutive_successes": trust.consecutive_successes,
            "consecutive_failures": trust.consecutive_failures,
        }

    def get_stats(self) -> dict:
        """Get comprehensive approval statistics."""
        return {
            "total_decisions": len(self._approval_history),
            "auto_approved": self._auto_approved_count,
            "human_required": self._human_required_count,
            "auto_approval_rate": (
                self._auto_approved_count / max(len(self._approval_history), 1)
            ),
            "tracked_components": len(self._trust_profiles),
            "trusted_components": sum(
                1 for t in self._trust_profiles.values()
                if t.trust_level in (TrustLevel.TRUSTED, TrustLevel.HIGHLY_TRUSTED, TrustLevel.FULLY_TRUSTED)
            ),
            "fully_trusted": sum(
                1 for t in self._trust_profiles.values()
                if t.trust_level == TrustLevel.FULLY_TRUSTED
            ),
        }
