"""
Integration Bridge v61 — Adapter layer connecting super_brain components with old core modules.

Provides:
- get_supermind_context(): Aggregates data from both old (core/) and new (super_brain/) systems
- Adapter functions that allow API routes to use super_brain components alongside old core components
- Fallback handling when super_brain components are not initialized
- Centralized initialization of all super_brain components with proper wiring

This bridge ensures that:
1. Existing endpoints continue working with old core modules
2. New SuperMind endpoints can use super_brain components
3. Both systems share state where appropriate (NeuralBus, MetaCognition, etc.)
4. Graceful degradation when super_brain components are unavailable

v61 — Super Mind العقل الخارق مامون
"""

import logging
import time
from typing import Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── Singleton Registry ──────────────────────────────────────────────────────

_super_brain_components: dict[str, Any] = {}
_initialized = False


def get_component(name: str) -> Any:
    """Get a super_brain component by name, or None if not initialized."""
    return _super_brain_components.get(name)


def set_component(name: str, component: Any) -> None:
    """Register a super_brain component."""
    _super_brain_components[name] = component


def is_initialized() -> bool:
    """Check if super_brain components have been initialized."""
    return _initialized


def set_initialized(value: bool = True) -> None:
    """Mark super_brain components as initialized."""
    global _initialized
    _initialized = value


def get_all_components() -> dict[str, Any]:
    """Get all registered super_brain components."""
    return dict(_super_brain_components)


# ── Context Aggregation ─────────────────────────────────────────────────────

@dataclass
class SuperMindContext:
    """Aggregated context from both old core and new super_brain systems."""
    # Old core systems
    living_state: dict = field(default_factory=dict)
    emotional_memory: dict = field(default_factory=dict)
    deep_bonding: dict = field(default_factory=dict)
    reflexes: dict = field(default_factory=dict)
    autonomic: dict = field(default_factory=dict)
    neural_bus: dict = field(default_factory=dict)
    self_healing: dict = field(default_factory=dict)
    inner_monologue: dict = field(default_factory=dict)
    kernel: dict = field(default_factory=dict)

    # New super_brain systems
    meta_cognition: dict = field(default_factory=dict)
    health_monitor: dict = field(default_factory=dict)
    health_dashboard: dict = field(default_factory=dict)
    notification_engine: dict = field(default_factory=dict)
    variant_archive: dict = field(default_factory=dict)
    agent_lifecycle: dict = field(default_factory=dict)
    improvement_proposer: dict = field(default_factory=dict)
    brain_router: dict = field(default_factory=dict)
    deliberation_room: dict = field(default_factory=dict)
    tool_creator: dict = field(default_factory=dict)
    agent_creator: dict = field(default_factory=dict)
    deep_research: dict = field(default_factory=dict)
    self_modifier: dict = field(default_factory=dict)
    evolution_loop: dict = field(default_factory=dict)
    auto_deploy: dict = field(default_factory=dict)

    # Meta
    timestamp: float = field(default_factory=time.time)
    super_brain_initialized: bool = False
    version: str = "v61"


def get_supermind_context(kernel=None) -> SuperMindContext:
    """
    Aggregate data from BOTH old core and new super_brain systems.

    This is the main function that API endpoints should use to gather
    comprehensive system state. It gracefully handles missing components
    by returning empty dicts for unavailable systems.

    Args:
        kernel: Optional MamounKernel instance (if None, tries to get it)

    Returns:
        SuperMindContext with aggregated data from all systems
    """
    ctx = SuperMindContext()

    # Try to get kernel if not provided
    if kernel is None:
        try:
            from mamoun.api.deps import get_kernel
            kernel = get_kernel()
        except Exception:
            pass

    # ── Old core systems ──
    if kernel:
        try:
            if hasattr(kernel, '_living_state') and kernel._living_state:
                ctx.living_state = kernel._living_state.get_vitals_snapshot()
        except Exception:
            pass

        try:
            if hasattr(kernel, '_emotional_memory') and kernel._emotional_memory:
                ctx.emotional_memory = kernel._emotional_memory.get_status()
        except Exception:
            pass

        try:
            if hasattr(kernel, '_deep_bonding') and kernel._deep_bonding:
                ctx.deep_bonding = kernel._deep_bonding.get_status()
        except Exception:
            pass

        try:
            if hasattr(kernel, '_reflexes_engine') and kernel._reflexes_engine:
                ctx.reflexes = kernel._reflexes_engine.get_status()
        except Exception:
            pass

        try:
            if hasattr(kernel, '_autonomic_system') and kernel._autonomic_system:
                ctx.autonomic = kernel._autonomic_system.get_status()
        except Exception:
            pass

        try:
            if hasattr(kernel, '_self_healing') and kernel._self_healing:
                ctx.self_healing = kernel._self_healing.get_stats()
        except Exception:
            pass

        try:
            if hasattr(kernel, '_inner_monologue') and kernel._inner_monologue:
                ctx.inner_monologue = {"active": True}
        except Exception:
            pass

        try:
            ctx.kernel = {
                "running": getattr(kernel, '_running', False),
                "brains_count": len(getattr(kernel, '_brains', {})),
                "living_systems_initialized": getattr(kernel, '_living_systems_initialized', False),
            }
        except Exception:
            pass

    # NeuralBus — shared between old and new
    try:
        from mamoun.core.neural_bus import neural_bus
        ctx.neural_bus = neural_bus.get_stats() if hasattr(neural_bus, 'get_stats') else {}
    except Exception:
        pass

    # ── New super_brain systems ──
    ctx.super_brain_initialized = _initialized

    meta_cognition = get_component("meta_cognition")
    if meta_cognition:
        try:
            ctx.meta_cognition = meta_cognition.get_system_overview()
        except Exception:
            pass

    health_monitor = get_component("health_monitor")
    if health_monitor:
        try:
            ctx.health_monitor = health_monitor.get_health()
        except Exception:
            pass

    health_dashboard = get_component("health_dashboard")
    if health_dashboard:
        try:
            ctx.health_dashboard = health_dashboard.get_dashboard_data()
        except Exception:
            pass

    notification_engine = get_component("notification_engine")
    if notification_engine:
        try:
            ctx.notification_engine = notification_engine.get_stats()
        except Exception:
            pass

    variant_archive = get_component("variant_archive")
    if variant_archive:
        try:
            ctx.variant_archive = variant_archive.get_stats()
        except Exception:
            pass

    agent_lifecycle = get_component("agent_lifecycle_manager")
    if agent_lifecycle:
        try:
            ctx.agent_lifecycle = agent_lifecycle.get_stats()
        except Exception:
            pass

    improvement_proposer = get_component("improvement_proposer")
    if improvement_proposer:
        try:
            ctx.improvement_proposer = improvement_proposer.get_stats()
        except Exception:
            pass

    brain_router = get_component("brain_router")
    if brain_router:
        try:
            ctx.brain_router = brain_router.get_stats()
        except Exception:
            pass

    deliberation_room = get_component("deliberation_room")
    if deliberation_room:
        try:
            ctx.deliberation_room = deliberation_room.get_stats()
        except Exception:
            pass

    tool_creator = get_component("tool_creator")
    if tool_creator:
        try:
            ctx.tool_creator = tool_creator.get_stats()
        except Exception:
            pass

    agent_creator = get_component("agent_creator")
    if agent_creator:
        try:
            ctx.agent_creator = agent_creator.get_stats()
        except Exception:
            pass

    deep_research = get_component("deep_research_engine")
    if deep_research:
        try:
            ctx.deep_research = deep_research.get_stats()
        except Exception:
            pass

    self_modifier = get_component("self_modifier")
    if self_modifier:
        try:
            ctx.self_modifier = self_modifier.get_stats()
        except Exception:
            pass

    evolution_loop = get_component("evolution_loop_v2")
    if evolution_loop:
        try:
            ctx.evolution_loop = evolution_loop.get_stats()
        except Exception:
            pass

    auto_deploy = get_component("auto_deploy_engine")
    if auto_deploy:
        try:
            ctx.auto_deploy = auto_deploy.get_stats()
        except Exception:
            pass

    return ctx


# ── Adapter Functions ───────────────────────────────────────────────────────

def get_or_create_meta_cognition(neural_bus=None) -> Any:
    """Get existing MetaCognitionEngine or create a new one with fallback."""
    existing = get_component("meta_cognition")
    if existing:
        return existing

    try:
        from mamoun.core.super_brain.meta_cognition_engine import MetaCognitionEngine
        engine = MetaCognitionEngine(neural_bus=neural_bus)
        set_component("meta_cognition", engine)
        return engine
    except Exception as e:
        logger.warning(f"Failed to create MetaCognitionEngine: {e}")
        return None


def get_or_create_health_monitor(meta_cognition=None, kernel=None,
                                  notification_engine=None, neural_bus=None) -> Any:
    """Get existing HealthMonitor or create a new one with fallback."""
    existing = get_component("health_monitor")
    if existing:
        return existing

    try:
        from mamoun.core.super_brain.health_monitor import HealthMonitor
        monitor = HealthMonitor(
            meta_cognition=meta_cognition,
            kernel=kernel,
            notification_engine=notification_engine,
            neural_bus=neural_bus,
        )
        set_component("health_monitor", monitor)
        return monitor
    except Exception as e:
        logger.warning(f"Failed to create HealthMonitor: {e}")
        return None


def get_or_create_notification_engine(neural_bus=None, meta_cognition=None) -> Any:
    """Get existing NotificationEngine or create a new one with fallback."""
    existing = get_component("notification_engine")
    if existing:
        return existing

    try:
        from mamoun.core.super_brain.notification_engine import NotificationEngine
        engine = NotificationEngine(neural_bus=neural_bus, meta_cognition=meta_cognition)
        set_component("notification_engine", engine)
        return engine
    except Exception as e:
        logger.warning(f"Failed to create NotificationEngine: {e}")
        return None


def get_or_create_brain_router(llm_client=None, meta_cognition=None, neural_bus=None) -> Any:
    """Get existing BrainRouter or create a new one with fallback."""
    existing = get_component("brain_router")
    if existing:
        return existing

    try:
        from mamoun.core.super_brain.brain_router import BrainRouter
        router = BrainRouter(
            llm_client=llm_client,
            meta_cognition=meta_cognition,
            neural_bus=neural_bus,
        )
        set_component("brain_router", router)
        return router
    except Exception as e:
        logger.warning(f"Failed to create BrainRouter: {e}")
        return None


def get_or_create_deliberation_room(llm_client=None, brain_router=None,
                                     meta_cognition=None, neural_bus=None) -> Any:
    """Get existing DeliberationRoom or create a new one with fallback."""
    existing = get_component("deliberation_room")
    if existing:
        return existing

    try:
        from mamoun.core.super_brain.deliberation_room import DeliberationRoom
        room = DeliberationRoom(
            llm_client=llm_client,
            brain_router=brain_router,
            meta_cognition=meta_cognition,
            neural_bus=neural_bus,
        )
        set_component("deliberation_room", room)
        return room
    except Exception as e:
        logger.warning(f"Failed to create DeliberationRoom: {e}")
        return None


def get_or_create_tool_creator(llm_client=None, meta_cognition=None,
                                neural_bus=None) -> Any:
    """Get existing ToolCreator or create a new one with fallback."""
    existing = get_component("tool_creator")
    if existing:
        return existing

    try:
        from mamoun.core.super_brain.tool_creator import ToolCreator
        creator = ToolCreator(
            llm_client=llm_client,
            meta_cognition=meta_cognition,
            neural_bus=neural_bus,
        )
        set_component("tool_creator", creator)
        return creator
    except Exception as e:
        logger.warning(f"Failed to create ToolCreator: {e}")
        return None


def get_or_create_agent_creator(llm_client=None, meta_cognition=None,
                                 neural_bus=None) -> Any:
    """Get existing AgentCreator or create a new one with fallback."""
    existing = get_component("agent_creator")
    if existing:
        return existing

    try:
        from mamoun.core.super_brain.agent_creator import AgentCreator
        creator = AgentCreator(
            llm_client=llm_client,
            meta_cognition=meta_cognition,
            neural_bus=neural_bus,
        )
        set_component("agent_creator", creator)
        return creator
    except Exception as e:
        logger.warning(f"Failed to create AgentCreator: {e}")
        return None


def get_or_create_improvement_proposer(meta_cognition=None, llm_client=None,
                                        neural_bus=None) -> Any:
    """Get existing ImprovementProposer or create a new one with fallback."""
    existing = get_component("improvement_proposer")
    if existing:
        return existing

    try:
        from mamoun.core.super_brain.improvement_proposer import ImprovementProposer
        proposer = ImprovementProposer(
            meta_cognition=meta_cognition,
            llm_client=llm_client,
            neural_bus=neural_bus,
        )
        set_component("improvement_proposer", proposer)
        return proposer
    except Exception as e:
        logger.warning(f"Failed to create ImprovementProposer: {e}")
        return None


def get_or_create_deep_research(llm_client=None, meta_cognition=None,
                                 neural_bus=None) -> Any:
    """Get existing DeepResearchEngine or create a new one with fallback."""
    existing = get_component("deep_research_engine")
    if existing:
        return existing

    try:
        from mamoun.core.super_brain.deep_research_engine import DeepResearchEngine
        engine = DeepResearchEngine(
            llm_client=llm_client,
            meta_cognition=meta_cognition,
            neural_bus=neural_bus,
        )
        set_component("deep_research_engine", engine)
        return engine
    except Exception as e:
        logger.warning(f"Failed to create DeepResearchEngine: {e}")
        return None


def get_or_create_variant_archive(meta_cognition=None, neural_bus=None) -> Any:
    """Get existing VariantArchive or create a new one with fallback."""
    existing = get_component("variant_archive")
    if existing:
        return existing

    try:
        from mamoun.core.super_brain.variant_archive import VariantArchive
        archive = VariantArchive(
            meta_cognition=meta_cognition,
            neural_bus=neural_bus,
        )
        set_component("variant_archive", archive)
        return archive
    except Exception as e:
        logger.warning(f"Failed to create VariantArchive: {e}")
        return None


def get_or_create_agent_lifecycle(meta_cognition=None, neural_bus=None) -> Any:
    """Get existing AgentLifecycleManager or create a new one with fallback."""
    existing = get_component("agent_lifecycle_manager")
    if existing:
        return existing

    try:
        from mamoun.core.super_brain.agent_lifecycle_manager import AgentLifecycleManager
        manager = AgentLifecycleManager(
            meta_cognition=meta_cognition,
            neural_bus=neural_bus,
        )
        set_component("agent_lifecycle_manager", manager)
        return manager
    except Exception as e:
        logger.warning(f"Failed to create AgentLifecycleManager: {e}")
        return None


def get_or_create_self_modifier(meta_cognition=None, neural_bus=None,
                                 llm_client=None) -> Any:
    """Get existing SelfModifier or create a new one with fallback."""
    existing = get_component("self_modifier")
    if existing:
        return existing

    try:
        from mamoun.core.super_brain.self_modifier import SelfModifier
        modifier = SelfModifier(
            meta_cognition=meta_cognition,
            neural_bus=neural_bus,
            llm_client=llm_client,
        )
        set_component("self_modifier", modifier)
        return modifier
    except Exception as e:
        logger.warning(f"Failed to create SelfModifier: {e}")
        return None


def get_or_create_auto_deploy(meta_cognition=None, neural_bus=None) -> Any:
    """Get existing AutoDeployEngine or create a new one with fallback."""
    existing = get_component("auto_deploy_engine")
    if existing:
        return existing

    try:
        from mamoun.core.super_brain.auto_deploy_engine import AutoDeployEngine
        engine = AutoDeployEngine(
            meta_cognition=meta_cognition,
            neural_bus=neural_bus,
        )
        set_component("auto_deploy_engine", engine)
        return engine
    except Exception as e:
        logger.warning(f"Failed to create AutoDeployEngine: {e}")
        return None


def get_or_create_evolution_loop(kernel=None) -> Any:
    """Get existing EvolutionLoopV2 or create a new one with fallback."""
    existing = get_component("evolution_loop_v2")
    if existing:
        return existing

    try:
        from mamoun.core.super_brain.evolution_loop_v2 import EvolutionLoopV2
        loop = EvolutionLoopV2(kernel=kernel)
        set_component("evolution_loop_v2", loop)
        return loop
    except Exception as e:
        logger.warning(f"Failed to create EvolutionLoopV2: {e}")
        return None


def get_or_create_health_dashboard(meta_cognition=None, kernel=None,
                                    notification_engine=None) -> Any:
    """Get existing HealthDashboard or create a new one with fallback."""
    existing = get_component("health_dashboard")
    if existing:
        return existing

    try:
        from mamoun.core.super_brain.health_dashboard import HealthDashboard
        dashboard = HealthDashboard(
            meta_cognition=meta_cognition,
            kernel=kernel,
            notification_engine=notification_engine,
        )
        set_component("health_dashboard", dashboard)
        return dashboard
    except Exception as e:
        logger.warning(f"Failed to create HealthDashboard: {e}")
        return None


# ── Full Initialization ─────────────────────────────────────────────────────

async def initialize_super_brain(kernel=None, llm_client=None, neural_bus=None) -> dict:
    """
    Initialize ALL super_brain components with proper wiring.

    This should be called during application startup (in main.py lifespan).
    It creates and wires together all super_brain components, connecting them
    to both the NeuralBus and the kernel.

    Args:
        kernel: MamounKernel instance
        llm_client: Multi-provider LLM client
        neural_bus: NeuralBus instance

    Returns:
        dict with initialization results for each component
    """
    results = {}

    # 1. MetaCognitionEngine — foundation for all other components
    meta_cognition = get_or_create_meta_cognition(neural_bus=neural_bus)
    if meta_cognition and llm_client:
        try:
            meta_cognition.set_llm_client(llm_client)
            results["meta_cognition"] = "initialized"
        except Exception as e:
            results["meta_cognition"] = f"partial: {e}"
    elif meta_cognition:
        results["meta_cognition"] = "initialized (no LLM)"
    else:
        results["meta_cognition"] = "failed"

    # 2. NotificationEngine
    notification_engine = get_or_create_notification_engine(
        neural_bus=neural_bus,
        meta_cognition=meta_cognition,
    )
    results["notification_engine"] = "initialized" if notification_engine else "failed"

    # 3. HealthMonitor
    health_monitor = get_or_create_health_monitor(
        meta_cognition=meta_cognition,
        kernel=kernel,
        notification_engine=notification_engine,
        neural_bus=neural_bus,
    )
    if health_monitor:
        results["health_monitor"] = "initialized"
    else:
        results["health_monitor"] = "failed"

    # 4. HealthDashboard
    health_dashboard = get_or_create_health_dashboard(
        meta_cognition=meta_cognition,
        kernel=kernel,
        notification_engine=notification_engine,
    )
    results["health_dashboard"] = "initialized" if health_dashboard else "failed"

    # 5. VariantArchive
    variant_archive = get_or_create_variant_archive(
        meta_cognition=meta_cognition,
        neural_bus=neural_bus,
    )
    results["variant_archive"] = "initialized" if variant_archive else "failed"

    # 6. AgentLifecycleManager
    agent_lifecycle = get_or_create_agent_lifecycle(
        meta_cognition=meta_cognition,
        neural_bus=neural_bus,
    )
    results["agent_lifecycle_manager"] = "initialized" if agent_lifecycle else "failed"

    # 7. BrainRouter
    brain_router = get_or_create_brain_router(
        llm_client=llm_client,
        meta_cognition=meta_cognition,
        neural_bus=neural_bus,
    )
    results["brain_router"] = "initialized" if brain_router else "failed"

    # 8. DeliberationRoom
    deliberation_room = get_or_create_deliberation_room(
        llm_client=llm_client,
        brain_router=brain_router,
        meta_cognition=meta_cognition,
        neural_bus=neural_bus,
    )
    results["deliberation_room"] = "initialized" if deliberation_room else "failed"

    # 9. ToolCreator
    tool_creator = get_or_create_tool_creator(
        llm_client=llm_client,
        meta_cognition=meta_cognition,
        neural_bus=neural_bus,
    )
    results["tool_creator"] = "initialized" if tool_creator else "failed"

    # 10. AgentCreator
    agent_creator = get_or_create_agent_creator(
        llm_client=llm_client,
        meta_cognition=meta_cognition,
        neural_bus=neural_bus,
    )
    results["agent_creator"] = "initialized" if agent_creator else "failed"

    # 11. ImprovementProposer
    improvement_proposer = get_or_create_improvement_proposer(
        meta_cognition=meta_cognition,
        llm_client=llm_client,
        neural_bus=neural_bus,
    )
    if improvement_proposer and health_monitor:
        try:
            # Wire improvement proposer with self_modifier for apply capability
            self_modifier = get_or_create_self_modifier(
                meta_cognition=meta_cognition,
                neural_bus=neural_bus,
                llm_client=llm_client,
            )
            if self_modifier:
                improvement_proposer.set_self_modifier(self_modifier)
                results["self_modifier"] = "initialized"
            else:
                results["self_modifier"] = "failed"
        except Exception as e:
            results["self_modifier"] = f"partial: {e}"
    results["improvement_proposer"] = "initialized" if improvement_proposer else "failed"

    # 12. DeepResearchEngine
    deep_research = get_or_create_deep_research(
        llm_client=llm_client,
        meta_cognition=meta_cognition,
        neural_bus=neural_bus,
    )
    if deep_research:
        try:
            search_client = get_or_create_web_search_client()
            if search_client:
                deep_research.set_search_client(search_client)
                results["web_search_client"] = "initialized"
            else:
                results["web_search_client"] = "unavailable"
        except Exception as e:
            results["web_search_client"] = f"partial: {e}"
    results["deep_research_engine"] = "initialized" if deep_research else "failed"

    # 13. AutoDeployEngine
    auto_deploy = get_or_create_auto_deploy(
        meta_cognition=meta_cognition,
        neural_bus=neural_bus,
    )
    results["auto_deploy_engine"] = "initialized" if auto_deploy else "failed"

    # 14. EvolutionLoopV2
    evolution_loop = get_or_create_evolution_loop(kernel=kernel)
    results["evolution_loop_v2"] = "initialized" if evolution_loop else "failed"

    # Start HealthMonitor background monitoring
    if health_monitor:
        try:
            await health_monitor.start_monitoring()
            results["health_monitor"] = "initialized + monitoring"
        except Exception as e:
            results["health_monitor"] = f"initialized but monitoring failed: {e}"

    set_initialized(True)

    # Count successes
    successes = sum(1 for v in results.values() if "initialized" in str(v))
    total = len(results)

    logger.info(f"SuperBrain initialization complete: {successes}/{total} components initialized")

    return results


def get_or_create_web_search_client():
    """Get or create a web search client for deep research."""
    existing = get_component("web_search_client")
    if existing:
        return existing

    try:
        from mamoun.core.super_brain.web_search_client import WebSearchClient
        client = WebSearchClient()
        set_component("web_search_client", client)
        return client
    except Exception:
        # Fallback to old core web search
        try:
            from mamoun.core.web_search_client import WebSearchClient
            client = WebSearchClient()
            set_component("web_search_client", client)
            return client
        except Exception:
            return None
