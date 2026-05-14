"""
BABSHARQII v36.0 — Alias module
يُعيد توجيه إلى self_evolution_scheduler
Fixes: ModuleNotFoundError: No module named 'mamoun.evolution.self_evolution'
"""

from dataclasses import dataclass, field

from .self_evolution_scheduler import (
    SelfEvolutionScheduler,
    EvolutionPhase,
    EvolutionCycle,
    SELF_PROGRAMMING_ENABLED,
    EVOLUTION_CYCLE_DAYS,
    EVOLUTION_CHECK_INTERVAL,
)

# Singleton instance — lazy creation
_self_evolution_scheduler = None

def self_evolution_scheduler():
    """Get the global SelfEvolutionScheduler singleton."""
    global _self_evolution_scheduler
    if _self_evolution_scheduler is None:
        _self_evolution_scheduler = SelfEvolutionScheduler()
    return _self_evolution_scheduler


# ─── Backward-compatible aliases ───────────────────────────────────────────
# These classes existed in older versions and may be referenced elsewhere.

try:
    from mamoun.evolution.live_self_modifier import Weakness
except ImportError:
    @dataclass
    class Weakness:
        """نقطة ضعف — backward-compatible alias."""
        name: str = ""
        severity: str = "medium"
        description: str = ""


@dataclass
class AccuracyMetric:
    """مقياس دقة — backward-compatible data class."""
    name: str = ""
    current: float = 0.0
    target: float = 1.0
    unit: str = ""


@dataclass
class AccuracyRecord:
    """سجل دقة — backward-compatible data class."""
    metric_name: str = ""
    value: float = 0.0
    timestamp: float = 0.0


@dataclass
class VersionRecord:
    """سجل إصدار — backward-compatible data class."""
    version: str = ""
    timestamp: float = 0.0
    changes: list = field(default_factory=list)


# Alias for backward compatibility
EVOLUTION_INTERVAL_HOURS = EVOLUTION_CYCLE_DAYS * 24


__all__ = [
    "SelfEvolutionScheduler",
    "self_evolution_scheduler",
    "EvolutionPhase",
    "EvolutionCycle",
    "SELF_PROGRAMMING_ENABLED",
    "EVOLUTION_CYCLE_DAYS",
    "EVOLUTION_CHECK_INTERVAL",
    "EVOLUTION_INTERVAL_HOURS",
    "AccuracyMetric",
    "AccuracyRecord",
    "Weakness",
    "VersionRecord",
]
