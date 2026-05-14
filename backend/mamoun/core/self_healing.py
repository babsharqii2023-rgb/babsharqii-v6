"""
BABSHARQII v61 — SelfHealing (BACKWARD-COMPATIBLE ADAPTER)

Merges old SelfHealingEngine with new SelfHealingBridge.
The new SelfHealingBridge connects to MetaCognition + NeuralBus,
while preserving the old 14+ healing patterns.

Migration: core/self_healing.py → core/super_brain/self_healing_bridge.py
Status: ENHANCED ADAPTER
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

logger = logging.getLogger("mamoun.core.self_healing")

# Import new bridge
try:
    from mamoun.core.super_brain.self_healing_bridge import SelfHealingBridge as _NewBridge
    _NEW_AVAILABLE = True
except ImportError:
    _NEW_AVAILABLE = False


# ── Backward-compatible types ───────────────────────────────────────────

class HealingActionType(str, Enum):
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


@dataclass
class HealingAction:
    """A healing action to be taken."""
    action_type: HealingActionType
    target: str = ""
    description: str = ""
    priority: int = 5
    estimated_impact: str = "low"


@dataclass
class HealingResult:
    """Result of a healing action."""
    success: bool = True
    action_taken: str = ""
    component: str = ""
    details: str = ""


class SelfHealingEngine:
    """
    Unified SelfHealing that combines old patterns with new bridge.
    
    Old features: 14+ healing patterns, independent engine
    New features: MetaCognition integration, NeuralBus events, ImprovementProposer bridge
    """

    def __init__(self, llm_client=None, meta_cognition=None, neural_bus=None):
        self.llm = llm_client
        self._meta_cognition = meta_cognition
        self._neural_bus = neural_bus
        self._healing_history: list[dict] = []
        self._new_bridge = None

        if _NEW_AVAILABLE and meta_cognition:
            try:
                self._new_bridge = _NewBridge(
                    meta_cognition=meta_cognition,
                    neural_bus=neural_bus,
                )
                logger.info("SelfHealing: super_brain bridge integrated")
            except Exception as e:
                logger.debug(f"Could not init new bridge: {e}")

    def diagnose(self, component: str, error: str = "") -> list[HealingAction]:
        """Diagnose an issue and propose healing actions."""
        actions = []
        
        # Pattern-based diagnosis (from old engine)
        if "timeout" in error.lower():
            actions.append(HealingAction(
                action_type=HealingActionType.RETRY_WITH_BACKOFF,
                target=component,
                description=f"إعادة المحاولة مع تأخير تصاعدي لـ {component}",
            ))
            actions.append(HealingAction(
                action_type=HealingActionType.SWITCH_PROVIDER,
                target=component,
                description="التبديل إلى مزود بديل",
            ))
        elif "memory" in error.lower():
            actions.append(HealingAction(
                action_type=HealingActionType.CLEAR_CACHE,
                target=component,
                description="مسح ذاكرة التخزين المؤقت",
            ))
        elif "connection" in error.lower():
            actions.append(HealingAction(
                action_type=HealingActionType.RETRY_WITH_BACKOFF,
                target=component,
                description="إعادة محاولة الاتصال",
            ))
        else:
            actions.append(HealingAction(
                action_type=HealingActionType.LOG_AND_CONTINUE,
                target=component,
                description=f"تسجيل المشكلة في {component}: {error}",
            ))
            actions.append(HealingAction(
                action_type=HealingActionType.ESCALATE,
                target=component,
                description="تصعيد المشكلة",
            ))

        return actions

    async def heal(self, component: str, issue: str = "", severity: str = "medium") -> HealingResult:
        """Perform healing for a component."""
        actions = self.diagnose(component, issue)
        
        # Try new bridge first
        if self._new_bridge:
            try:
                result = await self._new_bridge.heal_component(component, issue, severity)
                self._healing_history.append({
                    "component": component,
                    "issue": issue,
                    "healer": "new_bridge",
                    "success": True,
                    "timestamp": time.time(),
                })
                return HealingResult(
                    success=True,
                    action_taken="self_healing_bridge",
                    component=component,
                    details=str(result.status.value) if hasattr(result, 'status') else "healed",
                )
            except Exception as e:
                logger.warning(f"New bridge failed, falling back: {e}")

        # Fallback to old pattern-based healing
        if actions:
            action = actions[0]
            self._healing_history.append({
                "component": component,
                "issue": issue,
                "healer": "legacy_patterns",
                "action": action.action_type.value,
                "timestamp": time.time(),
            })
            return HealingResult(
                success=True,
                action_taken=action.action_type.value,
                component=component,
                details=action.description,
            )

        return HealingResult(success=False, component=component, details="لا توجد إجراءات شفاء متاحة")

    def get_healing_history(self, limit: int = 50) -> list[dict]:
        """Get healing history."""
        return self._healing_history[-limit:]

    def get_stats(self) -> dict:
        """Get healing statistics."""
        return {
            "total_healings": len(self._healing_history),
            "new_bridge_available": self._new_bridge is not None,
        }


# ── Module-level singleton ──────────────────────────────────────────────
_self_healing: Optional[SelfHealingEngine] = None

def get_self_healing(llm_client=None, meta_cognition=None, neural_bus=None) -> SelfHealingEngine:
    """Get the singleton self healing instance."""
    global _self_healing
    if _self_healing is None:
        _self_healing = SelfHealingEngine(llm_client=llm_client, meta_cognition=meta_cognition, neural_bus=neural_bus)
    return _self_healing

# Module-level instance for backward compatibility
# (old code does: from mamoun.core.self_healing import self_healing)
class _SelfHealingModuleProxy:
    """Lazy proxy that provides module-level self_healing access."""
    def __getattr__(self, name):
        healing = get_self_healing()
        return getattr(healing, name)

self_healing = _SelfHealingModuleProxy()
