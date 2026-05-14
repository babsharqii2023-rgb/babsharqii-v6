"""
BABSHARQII v61 — SelfHealing (BACKWARD-COMPATIBLE ADAPTER)

Redirects to super_brain/self_healing_bridge.py.
Old: core/self_healing.py → New: core/super_brain/self_healing_bridge.py

The old SelfHealingEngine implementation (with pattern-based diagnosis)
has been moved to core/legacy/self_healing.py.
All functionality now delegates to the canonical super_brain SelfHealingBridge.

Migration: core/self_healing.py → core/super_brain/self_healing_bridge.py
Status: ADAPTER — all calls forwarded to super_brain SelfHealingBridge
"""

import logging
from typing import Optional
from enum import Enum

logger = logging.getLogger("mamoun.core.self_healing")

# Re-export everything from the new module
from mamoun.core.super_brain.self_healing_bridge import (
    HealingAction,
    HealingResultStatus,
    HealingResult,
    SelfHealingBridge,
)


# Backward-compatible HealingActionType enum
# Maps old action type names to the new HealingAction enum values
class HealingActionType(str, Enum):
    """Backward-compatible healing action types."""
    RESTART_COMPONENT = "restart_component"
    CLEAR_CACHE = "clear_cache"
    RESET_STATE = "reset_state"
    ROLLBACK_CODE = "rollback_code"
    ESCALATE = "escalate"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    SWITCH_PROVIDER = "switch_provider"
    REDUCE_LOAD = "reduce_load"
    FREEZE_COMPONENT = "freeze_component"
    RECONFIGURE = "reconfigure"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"
    LOG_AND_CONTINUE = "log_and_continue"
    FALLBACK_TO_SAFE = "fallback_to_safe"
    NOTIFY_HUMAN = "notify_human"


class SelfHealingEngine:
    """
    Backward-compatible SelfHealingEngine that delegates to SelfHealingBridge.

    Old API: diagnose(component, error) → list[HealingAction]
    Old API: heal(component, issue, severity) → HealingResult
    New API: heal_component(component, issue, severity) → HealingResult (super_brain)

    This adapter translates between the two.
    """

    def __init__(self, llm_client=None, meta_cognition=None, neural_bus=None):
        self._bridge = SelfHealingBridge(
            meta_cognition=meta_cognition,
            neural_bus=neural_bus,
        )
        self._healing_history: list[dict] = []

    def diagnose(self, component: str, error: str = "") -> list[HealingAction]:
        """Diagnose an issue — delegates to SelfHealingBridge."""
        # Map old error patterns to new HealingAction values
        if "timeout" in error.lower():
            return [
                HealingAction.RETRY_WITH_BACKOFF,
                HealingAction.SWITCH_PROVIDER,
            ]
        elif "memory" in error.lower():
            return [HealingAction.CLEAR_CACHE]
        elif "connection" in error.lower():
            return [HealingAction.RETRY_WITH_BACKOFF]
        else:
            return [HealingAction.LOG_AND_CONTINUE, HealingAction.ESCALATE]

    async def heal(self, component: str, issue: str = "", severity: str = "medium") -> HealingResult:
        """Perform healing — delegates to SelfHealingBridge."""
        result = await self._bridge.heal_component(component, issue, severity)
        self._healing_history.append({
            "component": component,
            "issue": issue,
            "success": result.status == HealingResultStatus.SUCCESS,
            "timestamp": result.timestamp if hasattr(result, 'timestamp') else 0.0,
        })
        return result

    def get_healing_history(self, limit: int = 50) -> list[dict]:
        """Get healing history."""
        return self._healing_history[-limit:]

    def get_stats(self) -> dict:
        """Get healing statistics."""
        bridge_stats = self._bridge.get_stats() if hasattr(self._bridge, 'get_stats') else {}
        return {
            "total_healings": len(self._healing_history),
            "bridge_stats": bridge_stats,
        }


# ── Module-level singleton ──────────────────────────────────────────────
_self_healing: Optional[SelfHealingEngine] = None

def get_self_healing(llm_client=None, meta_cognition=None, neural_bus=None) -> SelfHealingEngine:
    """Get the singleton self healing instance."""
    global _self_healing
    if _self_healing is None:
        _self_healing = SelfHealingEngine(
            llm_client=llm_client,
            meta_cognition=meta_cognition,
            neural_bus=neural_bus,
        )
    return _self_healing


# Module-level instance for backward compatibility
# (old code does: from mamoun.core.self_healing import self_healing)
class _SelfHealingModuleProxy:
    """Lazy proxy that provides module-level self_healing access."""
    def __getattr__(self, name):
        healing = get_self_healing()
        return getattr(healing, name)

self_healing = _SelfHealingModuleProxy()

logger.info("self_healing → redirected to super_brain/self_healing_bridge")
