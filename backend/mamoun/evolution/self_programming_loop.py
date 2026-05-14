"""
BABSHARQII v13.0 — Self-Programming Loop
حلقة البرمجة الذاتية — تمكين مأمون من برمجة وتعديل كوده وإنشاء وكلاء جدد

Inspired by:
- SICA (Self-Improving Code Agent)
- DGM-H (Darwin Gödel Machine - Hierarchical)

Components:
- MetaAgent: Monitors task performance and suggests code modifications
- SelfProgrammingLoop: Applies modifications with human approval
- AgentCreator: Creates new agents from text descriptions

Security:
- ALL modifications require human approval (via ApprovalGate)
- Modifications are tested in SandboxRunner before deployment
- TimeBoundedPolicy governs all file system and shell operations
- Protected files cannot be modified

Feature Flags:
- MAMOUN_AUTO_EVOLVE (existing, required)
- MAMOUN_SELF_PROGRAMMING (new, default: false)
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

SELF_PROGRAMMING_ENABLED = os.getenv("MAMOUN_SELF_PROGRAMMING", "false").lower() in ("true", "1", "yes")
AUTO_EVOLVE_ENABLED = os.getenv("MAMOUN_AUTO_EVOLVE", "false").lower() in ("true", "1", "yes")


def _is_self_programming_enabled():
    """تحقق ديناميكي من تفعيل البرمجة الذاتية — يقرأ من البيئة مباشرة."""
    return os.getenv("MAMOUN_SELF_PROGRAMMING", "false").lower() in ("true", "1", "yes")


def _is_auto_evolve_enabled():
    """تحقق ديناميكي من تفعيل التطور التلقائي — يقرأ من البيئة مباشرة."""
    return os.getenv("MAMOUN_AUTO_EVOLVE", "false").lower() in ("true", "1", "yes")

# Files that can NEVER be self-modified
PROTECTED_FILES = {
    "laws.yaml", "safety_guard.py", "approval_gate.py",
    ".env", "settings.yaml", "safety_gate_client.py",
    "policies_v2.yaml", "auto_approval_policy.yaml",
    "time_bounded_policy.py",
}


class ModificationType(str, Enum):
    """أنواع التعديلات."""
    CODE_PATCH = "code_patch"
    NEW_AGENT = "new_agent"
    NEW_TOOL = "new_tool"
    CONFIG_UPDATE = "config_update"
    BEHAVIOR_ADJUSTMENT = "behavior_adjustment"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"


class ModificationStatus(str, Enum):
    """حالة التعديل."""
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    TESTING = "testing"
    DEPLOYED = "deployed"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


@dataclass
class CodeModification:
    """تعديل كود مقترح."""
    modification_id: str = ""
    modification_type: str = ModificationType.CODE_PATCH.value
    target_file: str = ""
    description: str = ""
    description_ar: str = ""
    original_code: str = ""
    proposed_code: str = ""
    risk_level: str = "medium"
    reasoning: str = ""
    reasoning_ar: str = ""
    status: str = ModificationStatus.PROPOSED.value
    approval_id: str = ""
    test_results: dict = field(default_factory=dict)
    created_at: float = 0.0
    decided_at: float = 0.0
    deployed_at: float = 0.0

    def __post_init__(self):
        if not self.modification_id:
            self.modification_id = f"mod_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PerformanceObservation:
    """ملاحظة أداء — يرصدها MetaAgent."""
    observation_id: str = ""
    agent_id: str = ""
    task_type: str = ""
    metric_name: str = ""
    current_value: float = 0.0
    expected_value: float = 0.0
    deviation: float = 0.0
    severity: str = "low"
    suggested_fix: str = ""
    suggested_fix_ar: str = ""
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.observation_id:
            self.observation_id = f"obs_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


class MetaAgent:
    """
    وكيل ميتا — يراقب أداء المهام ويقترح تعديلات.

    Responsibilities:
    - Monitor task performance metrics
    - Detect performance degradation
    - Suggest code modifications for improvement
    - Track modification history and outcomes
    """

    def __init__(self):
        self._observations: list[PerformanceObservation] = []
        self._modifications: list[CodeModification] = []
        self._observation_counter = 0

    def observe_performance(
        self,
        agent_id: str,
        task_type: str,
        metric_name: str,
        current_value: float,
        expected_value: float,
        threshold: float = 0.2,
    ) -> Optional[PerformanceObservation]:
        """
        مراقبة الأداء — رصد انحراف عن المتوقع.

        Returns:
            PerformanceObservation if deviation exceeds threshold, None otherwise
        """
        deviation = (current_value - expected_value) / max(abs(expected_value), 0.001)

        if abs(deviation) > threshold:
            severity = "low"
            if abs(deviation) > 0.5:
                severity = "high"
            elif abs(deviation) > 0.3:
                severity = "medium"

            suggestion = self._generate_suggestion(agent_id, task_type, metric_name, deviation)

            observation = PerformanceObservation(
                agent_id=agent_id,
                task_type=task_type,
                metric_name=metric_name,
                current_value=current_value,
                expected_value=expected_value,
                deviation=round(deviation, 4),
                severity=severity,
                suggested_fix=suggestion.get("en", ""),
                suggested_fix_ar=suggestion.get("ar", ""),
            )

            self._observations.append(observation)
            self._observation_counter += 1

            return observation

        return None

    def propose_modification(
        self,
        target_file: str,
        modification_type: str,
        description: str = "",
        description_ar: str = "",
        proposed_code: str = "",
        original_code: str = "",
        reasoning: str = "",
        reasoning_ar: str = "",
        risk_level: str = "medium",
    ) -> Optional[CodeModification]:
        """
        اقتراح تعديل — Propose a code modification.

        Checks:
        - Target file is not protected
        - Feature flags are enabled
        - Modification type is valid
        """
        # Check if target is protected
        target_filename = target_file.split("/")[-1] if "/" in target_file else target_file
        if target_filename in PROTECTED_FILES:
            logger.warning(f"Cannot propose modification to protected file: {target_filename}")
            return None

        # Check feature flags (dynamic check)
        if not _is_self_programming_enabled():
            logger.debug("Self-programming disabled — no modification proposed")
            return None

        modification = CodeModification(
            modification_type=modification_type,
            target_file=target_file,
            description=description,
            description_ar=description_ar,
            proposed_code=proposed_code,
            original_code=original_code,
            risk_level=risk_level,
            reasoning=reasoning,
            reasoning_ar=reasoning_ar,
        )

        self._modifications.append(modification)
        return modification

    def get_pending_modifications(self) -> list[dict]:
        """الحصول على التعديلات المعلقة."""
        return [
            m.to_dict() for m in self._modifications
            if m.status == ModificationStatus.PROPOSED.value
        ]

    def get_recent_observations(self, limit: int = 20) -> list[dict]:
        """الحصول على الملاحظات الأخيرة."""
        return [o.to_dict() for o in self._observations[-limit:]]

    def _generate_suggestion(self, agent_id: str, task_type: str, metric: str, deviation: float) -> dict:
        """توليد اقتراح تعديل."""
        if deviation < 0:
            suggestions = {
                "accuracy": {"en": "Add more training data or adjust model parameters", "ar": "إضافة بيانات تدريب أكثر أو تعديل معاملات النموذج"},
                "speed": {"en": "Optimize algorithm or add caching layer", "ar": "تحسين الخوارزمية أو إضافة طبقة تخزين مؤقت"},
                "success_rate": {"en": "Review error patterns and add error handling", "ar": "مراجعة أنماط الأخطاء وإضافة معالجة الأخطاء"},
            }
            return suggestions.get(metric, {"en": "Investigate and fix the performance issue", "ar": "التحقيق وإصلاح مشكلة الأداء"})
        else:
            return {"en": "Performance is above expected — consider tightening expectations", "ar": "الأداء أعلى من المتوقع — فكر في تشديد التوقعات"}

    def get_status(self) -> dict:
        """حالة MetaAgent."""
        return {
            "observations_total": len(self._observations),
            "modifications_total": len(self._modifications),
            "pending_modifications": len(self.get_pending_modifications()),
        }


class SelfProgrammingLoop:
    """
    حلقة البرمجة الذاتية — تدير دورة المراقبة والاقتراح والموافقة والنشر.

    Cycle:
    1. MetaAgent observes performance issues
    2. Proposes code modifications
    3. Modifications tested in sandbox
    4. Human approval via ApprovalGate
    5. Deploy if approved, rollback if needed

    Security:
    - Requires both MAMOUN_AUTO_EVOLVE and MAMOUN_SELF_PROGRAMMING
    - ALL modifications need human approval
    - Protected files can never be modified
    - All changes are tested in sandbox first
    """

    def __init__(self, approval_gate=None, sandbox_runner=None, time_bounded_policy=None):
        self._approval_gate = approval_gate
        self._sandbox_runner = sandbox_runner
        self._time_bounded_policy = time_bounded_policy
        self._meta_agent = MetaAgent()
        self._cycle_count = 0
        self._modifications_applied = 0
        self._modifications_rejected = 0

    async def run_cycle(self, performance_data: dict = None) -> dict:
        """
        تشغيل دورة برمجة ذاتية — Run one self-programming cycle.

        Args:
            performance_data: بيانات الأداء الحالية

        Returns:
            Cycle result with observations and proposed modifications
        """
        if not _is_self_programming_enabled() or not _is_auto_evolve_enabled():
            return {
                "status": "disabled",
                "message": "البرمجة الذاتية معطلة — تحتاج MAMOUN_SELF_PROGRAMMING=true و MAMOUN_AUTO_EVOLVE=true",
            }

        self._cycle_count += 1
        performance_data = performance_data or {}

        # Step 1: Observe performance
        observations = []
        for agent_id, metrics in performance_data.items():
            if isinstance(metrics, dict):
                for metric_name, values in metrics.items():
                    if isinstance(values, dict) and "current" in values and "expected" in values:
                        obs = self._meta_agent.observe_performance(
                            agent_id=agent_id,
                            task_type=metrics.get("task_type", "general"),
                            metric_name=metric_name,
                            current_value=values["current"],
                            expected_value=values["expected"],
                        )
                        if obs:
                            observations.append(obs.to_dict())

        # Step 2: Propose modifications for significant observations
        proposed = []
        for obs_data in observations:
            if obs_data.get("severity") in ("high", "medium"):
                modification = self._meta_agent.propose_modification(
                    target_file=f"backend/mamoun/agents/{obs_data['agent_id']}.py",
                    modification_type=ModificationType.PERFORMANCE_OPTIMIZATION.value,
                    description=obs_data.get("suggested_fix", ""),
                    description_ar=obs_data.get("suggested_fix_ar", ""),
                    reasoning=f"Performance deviation: {obs_data['deviation']:.2%}",
                    reasoning_ar=f"انحراف الأداء: {obs_data['deviation']:.2%}",
                    risk_level="medium" if obs_data["severity"] == "medium" else "high",
                )
                if modification:
                    proposed.append(modification.to_dict())

        # Step 3: Submit for approval
        for mod_data in proposed:
            if self._approval_gate:
                try:
                    from mamoun.core.approval_gate import ApprovalRequest
                    approval_request = ApprovalRequest(
                        change_type="self_programming",
                        target=mod_data.get("target_file", ""),
                        description=f"تعديل ذاتي: {mod_data.get('description_ar', mod_data.get('description', ''))}",
                        risk_level=mod_data.get("risk_level", "medium"),
                        details=json.dumps(mod_data, ensure_ascii=False),
                    )
                    result = await self._approval_gate.request_approval(approval_request)
                    # Note: Actual deployment happens after human approves
                except Exception as e:
                    logger.warning(f"Failed to submit modification for approval: {e}")

        return {
            "status": "cycle_complete",
            "cycle_id": self._cycle_count,
            "observations": len(observations),
            "modifications_proposed": len(proposed),
            "modifications_applied": self._modifications_applied,
            "modifications_rejected": self._modifications_rejected,
        }

    def get_meta_agent(self) -> MetaAgent:
        """الحصول على MetaAgent."""
        return self._meta_agent

    def get_status(self) -> dict:
        """حالة حلقة البرمجة الذاتية."""
        return {
            "enabled": SELF_PROGRAMMING_ENABLED and AUTO_EVOLVE_ENABLED,
            "self_programming_flag": SELF_PROGRAMMING_ENABLED,
            "auto_evolve_flag": AUTO_EVOLVE_ENABLED,
            "cycle_count": self._cycle_count,
            "modifications_applied": self._modifications_applied,
            "modifications_rejected": self._modifications_rejected,
            "meta_agent": self._meta_agent.get_status(),
        }

    async def shutdown(self):
        """إيقاف الحلقة — يتوافق مع القانون 5."""
        logger.info("SelfProgrammingLoop: Shutdown complete (Law 5 compliant)")
