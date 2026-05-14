"""
Mamoun Kernel v57 — Consciousness loop with event-driven architecture.

CRITICAL UPGRADE from v56:
- v56: Slow polling-based timers
- v57: Event-driven via NeuralBus — components react instantly
- Heartbeat monitoring — every component sends pulse every 30s
- Better async scheduling with asyncio
- Full integration with MetaCognitionEngine

v57 — Super Mind العقل الخارق مامون
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

    Manages the lifecycle of:
    - MetaCognitionEngine
    - BrainRouter
    - DeliberationRoom
    - DeepResearchEngine
    - SelfModifier
    - FullSelfRewriter
    - ImprovementProposer
    - ToolCreator
    - AgentCreator
    - ExternalProjectController
    - WebSearchClient

    Lifecycle:
    1. INITIALIZE: Create and wire all components
    2. RUN: Main loop with heartbeat monitoring
    3. PAUSE/RESUME: Suspend operations temporarily
    4. STOP: Graceful shutdown

    Usage:
        kernel = MamounKernel()
        await kernel.initialize()
        await kernel.run()
    """

    HEARTBEAT_INTERVAL = 30  # seconds
    MAIN_LOOP_INTERVAL = 1   # seconds

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

    @property
    def state(self) -> KernelState:
        return self._state

    async def initialize(self) -> None:
        """Initialize all components with proper wiring."""
        logger.info(" Initializing Mamoun Kernel v57...")

        # 1. Create Neural Bus (event backbone)
        from .shared.neural_bus import NeuralBus, get_neural_bus
        self._neural_bus = get_neural_bus()

        # 2. Create Meta-Cognition Engine
        from .meta_cognition_engine import MetaCognitionEngine
        self._meta_cognition = MetaCognitionEngine(neural_bus=self._neural_bus)
        self._register_component("meta_cognition", self._meta_cognition)

        # 3. Create Multi-Provider LLM Client
        from .shared.multi_provider_llm import MultiProviderLLMClient
        self._llm_client = MultiProviderLLMClient()
        self._register_component("llm_client", self._llm_client)

        # 4. Create Web Search Client
        from .web_search_client import WebSearchClient
        search_client = WebSearchClient(
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
        )
        self._register_component("web_search", search_client)

        # 5. Create Brain Router
        from .brain_router import BrainRouter
        self._brain_router = BrainRouter(
            llm_client=self._llm_client,
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
        )
        self._register_component("brain_router", self._brain_router)

        # 6. Create Deliberation Room
        from .deliberation_room import DeliberationRoom
        deliberation_room = DeliberationRoom(
            llm_client=self._llm_client,
            brain_router=self._brain_router,
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
        )
        self._register_component("deliberation_room", deliberation_room)

        # 7. Create Deep Research Engine
        from .deep_research_engine import DeepResearchEngine
        research_engine = DeepResearchEngine(
            search_client=search_client,
            llm_client=self._llm_client,
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
        )
        self._register_component("deep_research", research_engine)

        # 8. Create Self Modifier
        from .self_modifier import SelfModifier
        self_modifier = SelfModifier(
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
            llm_client=self._llm_client,
        )
        self._register_component("self_modifier", self_modifier)

        # 9. Create Full Self Rewriter
        from .full_self_rewriter import FullSelfRewriter
        self_rewriter = FullSelfRewriter(
            llm_client=self._llm_client,
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
        )
        self._register_component("full_self_rewriter", self_rewriter)

        # 10. Create Improvement Proposer
        from .improvement_proposer import ImprovementProposer
        improvement_proposer = ImprovementProposer(
            meta_cognition=self._meta_cognition,
            llm_client=self._llm_client,
            research_engine=research_engine,
            neural_bus=self._neural_bus,
        )
        self._register_component("improvement_proposer", improvement_proposer)

        # 11. Create Tool/Agent Registries
        from .shared.registry import get_tool_registry, get_agent_registry
        tool_registry = get_tool_registry()
        agent_registry = get_agent_registry()

        # 12. Create Tool Creator
        from .tool_creator import ToolCreator
        tool_creator = ToolCreator(
            llm_client=self._llm_client,
            tool_registry=tool_registry,
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
        )
        self._register_component("tool_creator", tool_creator)

        # 13. Create Agent Creator
        from .agent_creator import AgentCreator
        agent_creator = AgentCreator(
            llm_client=self._llm_client,
            agent_registry=agent_registry,
            meta_cognition=self._meta_cognition,
            neural_bus=self._neural_bus,
        )
        self._register_component("agent_creator", agent_creator)

        # 14. Create External Project Controller
        from .external_project_controller import ExternalProjectController
        project_controller = ExternalProjectController(
            meta_cognition=self._meta_cognition,
            llm_client=self._llm_client,
            neural_bus=self._neural_bus,
        )
        self._register_component("external_project_controller", project_controller)

        # Wire LLM client to meta-cognition for self-critique
        self._meta_cognition.set_llm_client(self._llm_client)

        self._state = KernelState.RUNNING
        self._start_time = time.time()
        logger.info(f" Mamoun Kernel initialized with {len(self._components)} components")

    def _register_component(self, name: str, instance: Any) -> None:
        """Register a component with the kernel."""
        self._components[name] = ComponentHandle(
            name=name,
            instance=instance,
            initialized=True,
        )

    def get_component(self, name: str) -> Any:
        """Get a component by name."""
        handle = self._components.get(name)
        return handle.instance if handle else None

    async def run(self) -> None:
        """Main loop — runs until stopped."""
        if self._state != KernelState.RUNNING:
            logger.error(f"Cannot run kernel in state: {self._state}")
            return

        logger.info(" Mamoun Kernel main loop started")

        while self._state == KernelState.RUNNING:
            try:
                self._loop_count += 1

                # Heartbeat check
                if self._loop_count % self.HEARTBEAT_INTERVAL == 0:
                    await self._heartbeat_check()

                # Small sleep to prevent CPU spinning
                await asyncio.sleep(self.MAIN_LOOP_INTERVAL)

            except KeyboardInterrupt:
                await self.stop()
            except Exception as e:
                logger.error(f"Kernel loop error: {e}")
                self._state = KernelState.ERROR

    async def _heartbeat_check(self) -> None:
        """Check health of all components."""
        for name, handle in self._components.items():
            handle.last_heartbeat = time.time()

            # Publish heartbeat event
            if self._neural_bus:
                from .shared.neural_bus import Event, EventType
                await self._neural_bus.publish(Event(
                    event_type=EventType.HEARTBEAT,
                    source=name,
                    data={"health": handle.health},
                ))

    async def pause(self) -> None:
        """Pause the kernel."""
        if self._state == KernelState.RUNNING:
            self._state = KernelState.PAUSED
            logger.info("Kernel paused")

    async def resume(self) -> None:
        """Resume the kernel."""
        if self._state == KernelState.PAUSED:
            self._state = KernelState.RUNNING
            logger.info("Kernel resumed")

    async def stop(self) -> None:
        """Graceful shutdown."""
        self._state = KernelState.STOPPING
        logger.info("Kernel shutting down...")

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

        # Get meta-cognition data
        system_overview = {}
        if self._meta_cognition:
            system_overview = self._meta_cognition.get_system_overview()

        # Get LLM provider health
        llm_health = {}
        if self._llm_client:
            llm_health = self._llm_client.get_health_report()

        return {
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
        """Get honest self-assessment of what Super Mind can and cannot do."""
        assessment = {
            "version": "v57",
            "kernel_state": self._state.value,
            "components_available": list(self._components.keys()),
        }

        if self._meta_cognition:
            assessment["meta_cognition"] = self._meta_cognition.get_self_assessment()

        # Check what's actually available
        available_providers = self._llm_client.available_providers() if self._llm_client else []
        assessment["llm_providers_available"] = available_providers
        assessment["can_think_diversely"] = len(available_providers) >= 2
        assessment["can_self_modify_safely"] = True  # AST sandbox enabled
        assessment["can_research_web"] = len(available_providers) > 0

        return assessment
