"""
BABSHARQII v62 — ImprovementEngine (BACKWARD-COMPATIBLE ADAPTER)

Redirects to super_brain/improvement_proposer.py.
Old: core/improvement_engine.py → New: core/super_brain/improvement_proposer.py

v62 FIX: Added ALL missing exports called by update.py endpoints:
- get_improvement_engine(), ImprovementRecord, ImpactLevel
- get_quality_summary(), detect_stagnation() on the engine adapter
"""

import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger("mamoun.core.improvement_engine")

# Re-export from new module with backward-compatible names
from mamoun.core.super_brain.improvement_proposer import (
    ProposalPriority,
    ProposalStatus,
    ImprovementProposal,
    FeatureFlags,
    ImprovementProposer as _ImprovementProposer,
)


# ── Backward-compatible types ───────────────────────────────────────────────

class ImpactLevel(str, Enum):
    """Impact classification levels (backward-compatible with old ImprovementEngine)."""
    L0_COSMETIC = "L0"       # formatting, comments, renames — AUTO-REJECT
    L1_OPTIMIZATION = "L1"   # algorithm, performance — needs metric_proof
    L2_STRUCTURAL = "L2"     # architecture, coupling — needs dependency_analysis
    L3_CAPABILITY = "L3"     # new features, integrations — needs human_approval


@dataclass
class ImprovementRecord:
    """سجل تحسين واحد (backward-compatible with old ImprovementEngine)."""
    id: str = ""
    impact_level: str = ""
    diff_summary: str = ""
    files_changed: list = field(default_factory=list)
    before_metrics: dict = field(default_factory=dict)
    after_metrics: dict = field(default_factory=dict)
    delta: dict = field(default_factory=dict)
    verified: bool = False
    rejected: bool = False
    rejection_reason: str = ""
    timestamp: float = 0.0
    elapsed_seconds: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.id:
            self.id = f"imp_{int(self.timestamp)}_{hash(self.diff_summary) % 10000:04d}"


class ImprovementEngine(_ImprovementProposer):
    """
    Backward-compatible ImprovementEngine that extends ImprovementProposer
    with the 7-guards pipeline API used by update.py endpoints.

    Delegates core functionality to ImprovementProposer while providing
    the old API (get_quality_summary, detect_stagnation, etc.).
    """

    def __init__(self, meta_cognition=None, llm_client=None,
                 research_engine=None, neural_bus=None, self_modifier=None):
        super().__init__(
            meta_cognition=meta_cognition,
            llm_client=llm_client,
            research_engine=research_engine,
            neural_bus=neural_bus,
            self_modifier=self_modifier,
        )
        self._history: list[ImprovementRecord] = []
        self._initialized = False

    def initialize(self):
        """Initialize the engine (backward-compatible)."""
        self._initialized = True
        logger.info("ImprovementEngine initialized — 7 guards ready")

    async def get_quality_summary(self) -> dict:
        """Get a summary of improvement quality (backward-compatible)."""
        if not self._history:
            return {"total": 0, "message": "لا يوجد سجل تحسينات بعد"}

        by_level = {}
        for level in ImpactLevel:
            records = [r for r in self._history if r.impact_level == level.value]
            verified = sum(1 for r in records if r.verified)
            by_level[level.value] = {
                "total": len(records),
                "verified": verified,
                "rejected": sum(1 for r in records if r.rejected),
                "success_rate": round(verified / max(len(records), 1) * 100, 1),
            }

        return {
            "total": len(self._history),
            "by_level": by_level,
            "last_10": [
                {
                    "id": r.id,
                    "level": r.impact_level,
                    "verified": r.verified,
                    "rejected": r.rejected,
                    "reason": r.rejection_reason[:100] if r.rejection_reason else "",
                    "time": r.timestamp,
                }
                for r in self._history[-10:]
            ],
        }

    async def detect_stagnation(self) -> dict:
        """Detect improvement stagnation (backward-compatible)."""
        recent = self._history[-10:]
        if len(recent) < 3:
            return {"stagnation_level": "NONE", "consecutive_shallow": 0, "recommendation": "لا يوجد ركود"}

        consecutive_shallow = 0
        for r in reversed(recent):
            if r.impact_level == ImpactLevel.L0_COSMETIC.value or r.rejected:
                consecutive_shallow += 1
            else:
                break

        if consecutive_shallow >= 5:
            level = "CRITICAL"
            recommendation = "فحص معمّق مطلوب — 5+ تحسينات شكلية متتالية"
        elif consecutive_shallow >= 3:
            level = "WARNING"
            recommendation = "بداية ركود — التزم بتغييرات L2/L3 فقط"
        else:
            level = "NONE"
            recommendation = "لا يوجد ركود"

        return {
            "stagnation_level": level,
            "consecutive_shallow": consecutive_shallow,
            "recommendation": recommendation,
            "total_improvements": len(self._history),
            "verified_count": sum(1 for r in self._history if r.verified),
            "rejected_count": sum(1 for r in self._history if r.rejected),
        }

    async def update_quality_model(self, record: ImprovementRecord):
        """Update the quality model with a new record (backward-compatible)."""
        self._history.append(record)
        logger.info(
            f"Quality model updated: {record.id} level={record.impact_level} "
            f"verified={record.verified} rejected={record.rejected}"
        )


# ── Singleton ───────────────────────────────────────────────────────────
_improvement_engine: Optional[ImprovementEngine] = None

def get_improvement_engine() -> ImprovementEngine:
    """Get the global improvement engine singleton."""
    global _improvement_engine
    if _improvement_engine is None:
        _improvement_engine = ImprovementEngine()
    return _improvement_engine


# Module-level singleton for backward compatibility
improvement_engine = None

def _get_improvement_engine_module():
    """Lazy initialization of module-level improvement_engine."""
    global improvement_engine
    if improvement_engine is None:
        improvement_engine = get_improvement_engine()
    return improvement_engine

logger.info("improvement_engine → redirected to super_brain/improvement_proposer (v62 full adapter)")
