"""
BABSHARQII v61 — Integration Layer

This module provides the integration layer that bridges the old production code
with the new super_brain components. It ensures that ALL super_brain features
are properly connected and accessible from the production API.

Solves: "مكونات super_brain معزولة عن النظام الإنتاجي الفعلي"
Before: 164+ imports from old paths, 0 from super_brain
After: All core/ imports delegate to super_brain/ or shared/
"""

import time
import logging
from typing import Optional, Any

logger = logging.getLogger("mamoun.core.integration_layer")


class IntegrationLayer:
    """
    طبقة الربط — تضمن اتصال جميع مكونات super_brain بالنظام الإنتاجي.
    
    Features connected:
    1. SelfHealingBridge → MetaCognition (errors → learning)
    2. RLHFBridge → ImprovementProposer (feedback → improvement)
    3. OutcomeRecorder → all components (outcome tracking)
    4. NotificationEngine → NeuralBus (alerts)
    5. HealthMonitor → MetaCognition + EvolutionLoop (health → improvement)
    6. VariantArchive → EvolutionLoop (DGM-inspired rollback)
    """

    def __init__(self, kernel=None):
        self._kernel = kernel
        self._connected = False
        self._components = {}

    async def connect_all(self) -> dict:
        """Connect all super_brain components to the production system."""
        results = {}

        # 1. Connect SelfHealing → MetaCognition
        try:
            from mamoun.core.super_brain.self_healing_bridge import SelfHealingBridge
            from mamoun.core.super_brain.meta_cognition_engine import MetaCognitionEngine
            from mamoun.core.shared.neural_bus import get_neural_bus
            neural_bus = get_neural_bus()
            meta_cognition = MetaCognitionEngine(neural_bus=neural_bus)
            healing_bridge = SelfHealingBridge(
                meta_cognition=meta_cognition,
                neural_bus=neural_bus,
            )
            self._components["self_healing_bridge"] = healing_bridge
            self._components["meta_cognition"] = meta_cognition
            results["self_healing_meta_cognition"] = "connected"
        except Exception as e:
            results["self_healing_meta_cognition"] = f"failed: {e}"

        # 2. Connect RLHF → ImprovementProposer
        try:
            from mamoun.core.super_brain.rlhf_bridge import RLHFBridge
            from mamoun.core.super_brain.improvement_proposer import ImprovementProposer
            meta_cognition = self._components.get("meta_cognition")
            neural_bus = self._components.get("neural_bus")
            if meta_cognition:
                proposer = ImprovementProposer(
                    meta_cognition=meta_cognition,
                    neural_bus=neural_bus,
                )
                rlhf_bridge = RLHFBridge(
                    meta_cognition=meta_cognition,
                    neural_bus=neural_bus,
                    improvement_proposer=proposer,
                )
                self._components["rlhf_bridge"] = rlhf_bridge
                self._components["improvement_proposer"] = proposer
                results["rlhf_improvement_proposer"] = "connected"
            else:
                results["rlhf_improvement_proposer"] = "skipped: no meta_cognition"
        except Exception as e:
            results["rlhf_improvement_proposer"] = f"failed: {e}"

        # 3. Connect OutcomeRecorder
        try:
            from mamoun.core.super_brain.outcome_recorder import OutcomeRecorder
            recorder = OutcomeRecorder()
            self._components["outcome_recorder"] = recorder
            results["outcome_recorder"] = "connected"
        except Exception as e:
            results["outcome_recorder"] = f"failed: {e}"

        # 4. Connect NotificationEngine → NeuralBus
        try:
            from mamoun.core.super_brain.notification_engine import NotificationEngine
            from mamoun.core.shared.neural_bus import get_neural_bus
            neural_bus = get_neural_bus()
            meta_cognition = self._components.get("meta_cognition")
            notification_engine = NotificationEngine(
                neural_bus=neural_bus,
                meta_cognition=meta_cognition,
            )
            notification_engine.set_neural_bus(neural_bus)
            self._components["notification_engine"] = notification_engine
            results["notification_engine"] = "connected"
        except Exception as e:
            results["notification_engine"] = f"failed: {e}"

        # 5. Connect HealthMonitor
        try:
            from mamoun.core.super_brain.health_monitor import HealthMonitor
            meta_cognition = self._components.get("meta_cognition")
            notification_engine = self._components.get("notification_engine")
            healing_bridge = self._components.get("self_healing_bridge")
            from mamoun.core.shared.neural_bus import get_neural_bus
            neural_bus = get_neural_bus()
            health_monitor = HealthMonitor(
                meta_cognition=meta_cognition,
                neural_bus=neural_bus,
                notification_engine=notification_engine,
                healing_bridge=healing_bridge,
            )
            self._components["health_monitor"] = health_monitor
            results["health_monitor"] = "connected"
        except Exception as e:
            results["health_monitor"] = f"failed: {e}"

        # 6. Connect VariantArchive
        try:
            from mamoun.core.super_brain.variant_archive import VariantArchive
            meta_cognition = self._components.get("meta_cognition")
            from mamoun.core.shared.neural_bus import get_neural_bus
            neural_bus = get_neural_bus()
            variant_archive = VariantArchive(
                meta_cognition=meta_cognition,
                neural_bus=neural_bus,
            )
            self._components["variant_archive"] = variant_archive
            results["variant_archive"] = "connected"
        except Exception as e:
            results["variant_archive"] = f"failed: {e}"

        self._connected = True
        logger.info(f"Integration Layer: {sum(1 for v in results.values() if v == 'connected')}/6 components connected")
        return results

    def get_component(self, name: str) -> Any:
        """Get a connected component by name."""
        return self._components.get(name)

    def get_status(self) -> dict:
        """Get integration status."""
        return {
            "connected": self._connected,
            "components": list(self._components.keys()),
            "component_count": len(self._components),
        }


# ── Singleton ───────────────────────────────────────────────────────────
_integration_layer: Optional[IntegrationLayer] = None

def get_integration_layer(kernel=None) -> IntegrationLayer:
    """Get the singleton integration layer."""
    global _integration_layer
    if _integration_layer is None:
        _integration_layer = IntegrationLayer(kernel=kernel)
    return _integration_layer
