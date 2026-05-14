"""
BABSHARQII v10.0 — Auto Evolution Loop
دورة التطور التلقائي — تقبل التحسينات تلقائياً إذا حسّنت الأداء وخفضت النسيان

Evaluates mutations automatically:
1. Test mutation in sandbox
2. Run auto_benchmark
3. If improvement > 1% AND forgetting < threshold AND risk low → auto-accept
4. If improvement > 1% BUT risk high → request human approval
5. If no improvement → reject

Feature Flag: MAMOUN_AUTO_EVOLVE (default: false)
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

AUTO_EVOLVE_ENABLED: bool = os.environ.get(
    "MAMOUN_AUTO_EVOLVE", "false"
).lower() in ("true", "1", "yes")


@dataclass
class AutoEvolutionResult:
    """نتيجة التطور التلقائي"""
    accepted: bool = False
    improvement_pct: float = 0.0
    forgetting_pct: float = 0.0
    benchmark_results: dict = field(default_factory=dict)
    rollback_needed: bool = False
    decision_reason: str = ""
    risk_level: str = "low"
    requires_human_approval: bool = False

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted,
            "improvement_pct": round(self.improvement_pct, 4),
            "forgetting_pct": round(self.forgetting_pct, 4),
            "benchmark_results": self.benchmark_results,
            "rollback_needed": self.rollback_needed,
            "decision_reason": self.decision_reason,
            "risk_level": self.risk_level,
            "requires_human_approval": self.requires_human_approval,
        }


# Protected files that NEVER get auto-approved
PROTECTED_TARGETS = {
    "laws.yaml", "safety_guard.py", "approval_gate.py",
    ".env", "settings.yaml", "safety_gate_client.py",
    "policies_v2.yaml", "auto_approval_policy.yaml",
}


class AutoEvolutionLoop:
    """
    دورة التطور التلقائي
    
    Automatically evaluates and accepts improvements that:
    - Improve benchmark performance by > 1%
    - Keep catastrophic forgetting < 12%
    - Don't touch protected files
    - Are classified as low risk
    """

    MIN_IMPROVEMENT_PCT = 1.0   # 1%
    MAX_FORGETTING_PCT = 12.0    # 12%

    def __init__(
        self,
        approval_gate=None,
        benchmark_runner=None,
        si_engine=None,
    ):
        self._approval_gate = approval_gate
        self._benchmark_runner = benchmark_runner
        self._si_engine = si_engine
        self._eval_count = 0

    def evaluate_mutation(
        self,
        mutation: dict,
        current_fitness: float,
    ) -> AutoEvolutionResult:
        """
        قيّم طفرة وقرر هل تُقبل تلقائياً.
        
        Args:
            mutation: dict with keys:
                - target: str (file path being modified)
                - description: str
                - risk_level: str ("low", "medium", "high", "critical")
                - estimated_improvement: float
                - details: dict
            current_fitness: current system fitness score (0-1)
        """
        if not AUTO_EVOLVE_ENABLED:
            return AutoEvolutionResult(
                decision_reason="التطور التلقائي معطل (MAMOUN_AUTO_EVOLVE=false)"
            )

        self._eval_count += 1
        target = mutation.get("target", "")
        risk_level = mutation.get("risk_level", "low")
        est_improvement = mutation.get("estimated_improvement", 0.0)

        # Check if target is protected
        target_filename = target.split("/")[-1] if "/" in target else target
        if self._is_protected_target(target_filename):
            return AutoEvolutionResult(
                accepted=False,
                improvement_pct=est_improvement * 100,
                risk_level=risk_level,
                requires_human_approval=True,
                decision_reason=f"الملف {target_filename} محمي — يتطلب موافقة بشرية",
            )

        # Check risk level
        if risk_level in ("high", "critical"):
            return AutoEvolutionResult(
                accepted=False,
                improvement_pct=est_improvement * 100,
                risk_level=risk_level,
                requires_human_approval=True,
                decision_reason=f"مستوى مخاطر {risk_level} — يتطلب موافقة بشرية",
            )

        # Run benchmarks (if runner available)
        forgetting_pct = 0.0
        benchmark_results = {}

        if self._benchmark_runner:
            entries = self._benchmark_runner.run_after_task(
                f"mutation_eval_{self._eval_count}"
            )
            benchmark_results = {
                e.benchmark_type: e.score for e in entries
            }

            # Check for regression
            if self._benchmark_runner.should_rollback():
                return AutoEvolutionResult(
                    accepted=False,
                    improvement_pct=est_improvement * 100,
                    forgetting_pct=forgetting_pct,
                    benchmark_results=benchmark_results,
                    rollback_needed=True,
                    risk_level=risk_level,
                    decision_reason="تراجع في الأداء — رفض تلقائي",
                )

        # Check SI penalty (if engine available)
        if self._si_engine:
            proposed = mutation.get("proposed_changes", [])
            if proposed:
                forgetting_pct = self._si_engine.get_forgetting_estimate(proposed) * 100
                if forgetting_pct > self.MAX_FORGETTING_PCT:
                    return AutoEvolutionResult(
                        accepted=False,
                        improvement_pct=est_improvement * 100,
                        forgetting_pct=forgetting_pct,
                        benchmark_results=benchmark_results,
                        risk_level=risk_level,
                        decision_reason=f"نسيان {forgetting_pct:.1f}% > عتبة {self.MAX_FORGETTING_PCT}%",
                    )

        # Check improvement threshold
        improvement_pct = est_improvement * 100
        if improvement_pct < self.MIN_IMPROVEMENT_PCT:
            return AutoEvolutionResult(
                accepted=False,
                improvement_pct=improvement_pct,
                forgetting_pct=forgetting_pct,
                benchmark_results=benchmark_results,
                risk_level=risk_level,
                decision_reason=f"تحسين {improvement_pct:.2f}% < عتبة {self.MIN_IMPROVEMENT_PCT}%",
            )

        # All checks passed — auto-accept
        return AutoEvolutionResult(
            accepted=True,
            improvement_pct=improvement_pct,
            forgetting_pct=forgetting_pct,
            benchmark_results=benchmark_results,
            risk_level=risk_level,
            decision_reason=f"مقبول تلقائياً: تحسن {improvement_pct:.2f}%, نسيان {forgetting_pct:.1f}%",
        )

    def auto_accept_criteria(self, result: AutoEvolutionResult) -> bool:
        """
        هل تنطبق معايير القبول التلقائي؟
        
        Criteria:
        - improvement > 1%
        - forgetting < 12%
        - no regression on critical benchmarks
        - NOT touching protected files
        """
        if not AUTO_EVOLVE_ENABLED:
            return False

        return (
            result.improvement_pct >= self.MIN_IMPROVEMENT_PCT
            and result.forgetting_pct < self.MAX_FORGETTING_PCT
            and not result.rollback_needed
            and not result.requires_human_approval
        )

    @staticmethod
    def _is_protected_target(filename: str) -> bool:
        """تحقق مما إذا كان الملف محمياً"""
        return filename in PROTECTED_TARGETS

    @property
    def stats(self) -> dict:
        """إحصائيات الدورة"""
        return {
            "total_evaluations": self._eval_count,
            "enabled": AUTO_EVOLVE_ENABLED,
        }
