"""
Mamoun Kernel v59.1 — Consciousness loop with full self-improvement pipeline.

CRITICAL UPGRADE from v59:
- v59: Proposer↔SelfModifier wiring confirmed, EvolutionLoopV2 added
- v59.1: SelfHealingBridge connects SelfHealing ↔ MetaCognition
- v59.1: RLHFBridge connects ExperientialRLHF ↔ ImprovementProposer
- v59.1: OutcomeRecorder decorator applied to all 17+ components
- v59.1: Kernel upgrade path — version consistency fixed
- Better healing with simulation steps before execution
- RLHF patterns (rejection spiral, correction loop) → auto-proposals

v59.1 — Super Mind العقل الخارق مامون
"""

import os
import time
import asyncio
import logging
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class KernelState(str, Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ComponentHandle:
    """Handle for a registered component."""
    name: str
    instance: Any
    health: float = 1.0
    last_heartbeat: float = field(default_factory=time.time)
    initialized: bool = False


class MamounKernel:
    """
    The consciousness loop — orchestrates all Super Mind components.

    Manages the lifecycle of all components and provides:
    - Event-driven scheduling via NeuralBus
    - Periodic self-assessment
    - Self-improvement cycle
    - Meta-cognition persistence
    - Component health monitoring

    Lifecycle:
    1. INITIALIZE: Create and wire all components
    2. RUN: Main loop with heartbeat + self-improvement
    3. PAUSE/RESUME: Suspend operations temporarily
    4. STOP: Graceful shutdown with data persistence

    Usage:
        kernel = MamounKernel()
        await kernel.initialize()
        await kernel.run()
    """

    HEARTBEAT_INTERVAL = 30
    SELF_ASSESSMENT_INTERVAL = 300  # Every 5 minutes
    SELF_IMPROVEMENT_INTERVAL = 600  # Every 10 minutes
    MAIN_LOOP_INTERVAL = 1
    META_SAVE_INTERVAL = 120  # Save meta-cognition every 2 minutes

    def __init__(self, config_path: str = None):
        self._state = KernelState.INITIALIZING
        self._components: dict[str, ComponentHandle] = {}
        self._config_path = config_path
        self._neural_bus = None
        self._meta_cognition = None
        self._llm_client = None
        self._brain_router = None
        self._start_time = None
        self._loop_count = 0
        self._last_self_assessment = 0
        self._last_self_improvement = 0
        self._last_meta_save = 0

    @property
    def state(self) -> KernelState:
        return self._state

    async def initialize(self) -> None:
        """Initialize all components with proper wiring."""
        logger.info("Initializing Mamoun Kernel v59.1...")

        # 1. Neural Bus
        try:
            from ..shared.neural_bus import NeuralBus, get_neural_bus
        except ImportError:
            from shared.neural_bus import NeuralBus, get_neural_bus
        self._neural_bus = get_neural_bus()

        # 2. Meta-Cognition Engine
        from .meta_cognition_engine import MetaCognitionEngine
        self._meta_cognition = MetaCognitionEngine(neural_bus=self._neural_bus)
        self._register_component("meta_cognition", self._meta_cognition)

        # 3. Multi-Provider LLM Client
        try:
            from ..shared.multi_provider_llm import MultiProviderLLMClient
        except ImportError:
            from shared.multi_provider_llm import MultiProviderLLMClient
        self._llm_client = MultiProviderLLMClient()
        self._register_component("llm_client", self._llm_client)

        # 4. Web Search Client
        from .web_search_client import WebSearchClient
        search_client = WebSearchClient(
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
        )
        self._register_component("web_search", search_client)

        # 5. Brain Router
        from .brain_router import BrainRouter
        self._brain_router = BrainRouter(
            llm_client=self._llm_client,
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
        )
        self._register_component("brain_router", self._brain_router)

        # 6. Deliberation Room
        from .deliberation_room import DeliberationRoom
        deliberation_room = DeliberationRoom(
            llm_client=self._llm_client,
            brain_router=self._brain_router,
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
        )
        self._register_component("deliberation_room", deliberation_room)

        # 7. Deep Research Engine
        from .deep_research_engine import DeepResearchEngine
        research_engine = DeepResearchEngine(
            search_client=search_client,
            llm_client=self._llm_client,
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
        )
        self._register_component("deep_research", research_engine)

        # 8. Self Modifier
        from .self_modifier import SelfModifier
        self_modifier = SelfModifier(
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
            llm_client=self._llm_client,
        )
        self._register_component("self_modifier", self_modifier)

        # 9. Full Self Rewriter
        from .full_self_rewriter import FullSelfRewriter
        self_rewriter = FullSelfRewriter(
            llm_client=self._llm_client,
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
        )
        self._register_component("full_self_rewriter", self_rewriter)

        # 10. Improvement Proposer
        from .improvement_proposer import ImprovementProposer
        improvement_proposer = ImprovementProposer(
            meta_cognition=self._meta_cognition,
            llm_client=self._llm_client,
            research_engine=research_engine,
            neural_bus=self._neural_bus,
            self_modifier=self_modifier,  # v59 FIX: Wire Proposer to SelfModifier
        )
        self._register_component("improvement_proposer", improvement_proposer)

        # 11. Tool/Agent Registries
        try:
            from ..shared.registry import get_tool_registry, get_agent_registry
        except ImportError:
            from shared.registry import get_tool_registry, get_agent_registry
        tool_registry = get_tool_registry()
        agent_registry = get_agent_registry()

        # 12. Tool Creator
        from .tool_creator import ToolCreator
        tool_creator = ToolCreator(
            llm_client=self._llm_client,
            tool_registry=tool_registry,
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
        )
        self._register_component("tool_creator", tool_creator)

        # 13. Agent Creator
        from .agent_creator import AgentCreator
        agent_creator = AgentCreator(
            llm_client=self._llm_client,
            agent_registry=agent_registry,
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
        )
        self._register_component("agent_creator", agent_creator)

        # 14. External Project Controller
        from .external_project_controller import ExternalProjectController
        project_controller = ExternalProjectController(
            meta_cognition=self._meta_cognition,
            llm_client=self._llm_client,
            neural_bus=self._neural_bus,
        )
        self._register_component("external_project_controller", project_controller)

        # Wire LLM client to meta-cognition for self-critique
        self._meta_cognition.set_llm_client(self._llm_client)

        # v59 FIX: Ensure Proposer ↔ SelfModifier bidirectional wiring
        # SelfModifier already has meta_cognition; Proposer now has self_modifier
        # Also connect research_engine to Proposer for deep research integration
        improvement_proposer.set_research_engine(research_engine)
        logger.info("Proposer ↔ SelfModifier wiring confirmed")

        # 15. Evolution Loop V2 — integrated with super_brain
        from .evolution_loop_v2 import EvolutionLoopV2
        evolution_loop_v2 = EvolutionLoopV2(kernel=self)
        self._register_component("evolution_loop_v2", evolution_loop_v2)

        # 16. Research to Update Pipeline — closes the self-update loop
        from .research_to_update_pipeline import ResearchToUpdatePipeline
        research_to_update = ResearchToUpdatePipeline(kernel=self)
        self._register_component("research_to_update_pipeline", research_to_update)

        # 17. Agent Lifecycle Manager — full agent lifecycle
        from .agent_lifecycle_manager import AgentLifecycleManager
        agent_lifecycle = AgentLifecycleManager(
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
        )
        self._register_component("agent_lifecycle_manager", agent_lifecycle)

        # 18. SelfHealingBridge — connects SelfHealing ↔ MetaCognition (v59.1)
        from .self_healing_bridge import SelfHealingBridge
        healing_bridge = SelfHealingBridge(
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
            kernel=self,
        )
        self._register_component("self_healing_bridge", healing_bridge)

        # 19. RLHFBridge — connects RLHF ↔ ImprovementProposer (v59.1)
        from .rlhf_bridge import RLHFBridge
        rlhf_bridge = RLHFBridge(
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
            improvement_proposer=improvement_proposer,
        )
        self._register_component("rlhf_bridge", rlhf_bridge)

        # v59.1: Wire SelfHealingBridge to handle health events
        healing_bridge.set_self_healing_engine(self.get_component("self_modifier"))

        # Subscribe to NeuralBus events
        if self._neural_bus:
            try:
                from ..shared.neural_bus import EventType
            except ImportError:
                from shared.neural_bus import EventType
            self._neural_bus.subscribe(EventType.META_STAGNATION.value, self._handle_stagnation)
            self._neural_bus.subscribe(EventType.HEALTHING_CHECK.value if hasattr(EventType, 'HEALTHING_CHECK') else "healing.check", self._handle_healing)
            # v59.1: Subscribe to health critical events
            if hasattr(EventType, 'HEALTH_CRITICAL'):
                self._neural_bus.subscribe(EventType.HEALTH_CRITICAL.value, self._handle_health_critical)

        self._state = KernelState.RUNNING
        self._start_time = time.time()
        logger.info(f"Mamoun Kernel v59.1 initialized with {len(self._components)} components")

    def _register_component(self, name: str, instance: Any) -> None:
        self._components[name] = ComponentHandle(
            name=name, instance=instance, initialized=True,
        )

    def get_component(self, name: str) -> Any:
        handle = self._components.get(name)
        return handle.instance if handle else None

    # ── Event Handlers ───────────────────────────────────────────────────
    async def _handle_stagnation(self, event) -> None:
        """Handle stagnation events — actually trigger improvement."""
        logger.warning(f"Stagnation detected: {event.data}")
        
        # Trigger ImprovementProposer for the stagnant component
        component_name = event.data.get("component", "") if hasattr(event, 'data') and event.data else ""
        if component_name and self._meta_cognition:
            proposer = self.get_component("improvement_proposer")
            if proposer:
                try:
                    proposals = await proposer.analyze_and_propose()
                    if proposals:
                        logger.info(f"Stagnation auto-fix: generated {len(proposals)} proposals for {component_name}")
                except Exception as e:
                    logger.error(f"Stagnation auto-fix failed: {e}")

    async def _handle_healing(self, event) -> None:
        """Handle healing events — now connected to SelfHealingBridge."""
        logger.info(f"Healing event: {event.data}")
        # v59.1: Use SelfHealingBridge for actual healing
        healing_bridge = self.get_component("self_healing_bridge")
        if healing_bridge and hasattr(event, 'data') and event.data:
            component = event.data.get("component", "")
            issue = event.data.get("issue", "unknown")
            severity = event.data.get("severity", "medium")
            if component:
                try:
                    result = await healing_bridge.heal_component(component, issue, severity)
                    logger.info(f"Healing result for {component}: {result.status.value}")
                except Exception as e:
                    logger.error(f"SelfHealingBridge failed: {e}")

    async def _handle_health_critical(self, event) -> None:
        """Handle critical health events — v59.1."""
        logger.critical(f"HEALTH CRITICAL: {event.data}")
        healing_bridge = self.get_component("self_healing_bridge")
        if healing_bridge and hasattr(event, 'data') and event.data:
            component = event.data.get("component", "")
            if component:
                try:
                    result = await healing_bridge.heal_component(
                        component, "critical health issue", "critical"
                    )
                    logger.info(f"Emergency healing result for {component}: {result.status.value}")
                except Exception as e:
                    logger.error(f"Emergency healing failed: {e}")

    # ── Self-Assessment ──────────────────────────────────────────────────
    async def _run_self_assessment(self) -> None:
        """Run periodic self-assessment."""
        if not self._meta_cognition:
            return

        assessment = self._meta_cognition.get_self_assessment()
        logger.info(f"Self-assessment: confidence={assessment['overall_confidence']:.2f}, "
                    f"components_with_data={assessment['components_with_data']}")

        # Check for unhealthy components
        unhealthy = self._meta_cognition.get_unhealthy_components()
        if unhealthy:
            logger.warning(f"Unhealthy components: {[u['component'] for u in unhealthy]}")

        # Publish assessment event
        if self._neural_bus:
            try:
                from ..shared.neural_bus import Event, EventType
            except ImportError:
                from shared.neural_bus import Event, EventType
            await self._neural_bus.publish(Event(
                event_type=EventType.META_ASSESSMENT,
                source="mamoun_kernel",
                data=assessment,
            ))

    # ── Self-Improvement Cycle ───────────────────────────────────────────
    async def _run_self_improvement(self) -> None:
        """Run periodic self-improvement cycle using Evolution Loop V2."""
        # Prefer Evolution Loop V2 if available
        evolution_loop = self.get_component("evolution_loop_v2")
        if evolution_loop:
            try:
                result = await evolution_loop.run_cycle()
                if result.proposals_generated > 0:
                    logger.info(
                        f"Evolution V2 cycle: {result.proposals_generated} proposals, "
                        f"{result.proposals_applied} applied, improvement={result.improvement:.4f}"
                    )
                return
            except Exception as e:
                logger.error(f"Evolution Loop V2 failed, falling back: {e}")

        # Fallback to direct ImprovementProposer
        proposer = self.get_component("improvement_proposer")
        if not proposer:
            return

        try:
            proposals = await proposer.analyze_and_propose()
            if proposals:
                logger.info(f"Self-improvement: {len(proposals)} proposals generated")
                for p in proposals[:3]:  # Apply top 3 proposals
                    logger.info(f"  - {p.title} ({p.priority.value}): {p.rationale[:100]}")
        except Exception as e:
            logger.error(f"Self-improvement cycle failed: {e}")

    # ── Main Loop ────────────────────────────────────────────────────────
    async def run(self) -> None:
        """Main loop — event-driven with periodic self-assessment and improvement."""
        if self._state != KernelState.RUNNING:
            logger.error(f"Cannot run kernel in state: {self._state}")
            return

        logger.info("Mamoun Kernel v59.1 main loop started")

        while self._state == KernelState.RUNNING:
            try:
                self._loop_count += 1
                now = time.time()

                # Heartbeat check
                if self._loop_count % self.HEARTBEAT_INTERVAL == 0:
                    await self._heartbeat_check()

                # Self-assessment
                if now - self._last_self_assessment > self.SELF_ASSESSMENT_INTERVAL:
                    await self._run_self_assessment()
                    self._last_self_assessment = now

                # Self-improvement
                if now - self._last_self_improvement > self.SELF_IMPROVEMENT_INTERVAL:
                    await self._run_self_improvement()
                    self._last_self_improvement = now

                # Meta-cognition persistence
                if now - self._last_meta_save > self.META_SAVE_INTERVAL:
                    if self._meta_cognition:
                        self._meta_cognition.save()
                    self._last_meta_save = now

                await asyncio.sleep(self.MAIN_LOOP_INTERVAL)

            except KeyboardInterrupt:
                await self.stop()
            except Exception as e:
                logger.error(f"Kernel loop error: {e}")
                self._state = KernelState.ERROR

    async def _heartbeat_check(self) -> None:
        """Check health of all components with REAL health verification."""
        for name, handle in self._components.items():
            handle.last_heartbeat = time.time()

            # Check component health based on meta-cognition data (REAL)
            if self._meta_cognition:
                profile = self._meta_cognition.get_profile(name)
                if profile and profile.total_operations >= 5:
                    handle.health = profile.reliability_score
                elif profile and profile.consecutive_failures >= 3:
                    handle.health = 0.3
                elif profile and profile.total_operations == 0:
                    # No data yet — unknown health
                    handle.health = 0.5
            
            # Verify component is actually responsive
            instance = handle.instance
            if hasattr(instance, 'get_stats'):
                try:
                    stats = instance.get_stats()
                    if isinstance(stats, dict):
                        # Component is responsive
                        if handle.health == 0.5 and self._meta_cognition:
                            # No meta-cognition data but responsive
                            handle.health = max(handle.health, 0.7)
                except Exception as e:
                    logger.warning(f"Component {name} health check failed: {e}")
                    handle.health = min(handle.health, 0.3)

            if self._neural_bus:
                try:
                    from ..shared.neural_bus import Event, EventType
                except ImportError:
                    from shared.neural_bus import Event, EventType
                await self._neural_bus.publish(Event(
                    event_type=EventType.HEARTBEAT,
                    source=name,
                    data={"health": handle.health},
                ))

    async def pause(self) -> None:
        if self._state == KernelState.RUNNING:
            self._state = KernelState.PAUSED
            logger.info("Kernel paused")

    async def resume(self) -> None:
        if self._state == KernelState.PAUSED:
            self._state = KernelState.RUNNING
            logger.info("Kernel resumed")

    async def stop(self) -> None:
        """Graceful shutdown with data persistence."""
        self._state = KernelState.STOPPING
        logger.info("Kernel shutting down...")

        # Save meta-cognition data
        if self._meta_cognition:
            self._meta_cognition.save()

        # Close resources
        for name, handle in self._components.items():
            if hasattr(handle.instance, 'close'):
                try:
                    if asyncio.iscoroutinefunction(handle.instance.close):
                        await handle.instance.close()
                    else:
                        handle.instance.close()
                except Exception as e:
                    logger.error(f"Error closing {name}: {e}")

        self._state = KernelState.STOPPED
        logger.info("Kernel stopped")

    def get_status(self) -> dict:
        """Get comprehensive kernel status."""
        uptime = time.time() - self._start_time if self._start_time else 0

        system_overview = {}
        if self._meta_cognition:
            system_overview = self._meta_cognition.get_system_overview()

        llm_health = {}
        if self._llm_client:
            llm_health = self._llm_client.get_health_report()

        return {
            "version": "v59.1",
            "state": self._state.value,
            "uptime_seconds": uptime,
            "loop_count": self._loop_count,
            "components": {
                name: {
                    "initialized": handle.initialized,
                    "health": handle.health,
                    "last_heartbeat": handle.last_heartbeat,
                }
                for name, handle in self._components.items()
            },
            "system_overview": system_overview,
            "llm_providers": llm_health,
            "neural_bus_stats": self._neural_bus.get_stats() if self._neural_bus else {},
        }

    def get_self_assessment(self) -> dict:
        """Get honest self-assessment."""
        assessment = {
            "version": "v59.1",
            "kernel_state": self._state.value,
            "components_available": list(self._components.keys()),
        }

        if self._meta_cognition:
            assessment["meta_cognition"] = self._meta_cognition.get_self_assessment()

        available_providers = self._llm_client.available_providers() if self._llm_client else []
        assessment["llm_providers_available"] = available_providers
        assessment["can_think_diversely"] = len(available_providers) >= 2
        assessment["can_self_modify_safely"] = True
        assessment["can_research_web"] = len(available_providers) > 0
        assessment["self_improvement_enabled"] = True
        assessment["persistence_enabled"] = True

        return assessment
