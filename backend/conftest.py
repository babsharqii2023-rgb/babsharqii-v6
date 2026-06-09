"""
conftest.py — إعدادات pytest العامة
حماية sys.modules من التلوث + إصلاح async loop
"""
import sys
import asyncio
import pytest

# ═══════════════════════════════════════════════════════════════
# sys.modules Protection — يمنع تلوث الوحدات بين الاختبارات
# ═══════════════════════════════════════════════════════════════

_PROTECTED_MODULES = [
    "mamoun",
    "mamoun.core",
    "mamoun.agi",
    "mamoun.brains",
    "mamoun.api",
    "mamoun.memory",
    "mamoun.neural",
    "mamoun.awareness",
    "mamoun.evolution",
    "mamoun.learning",
    "mamoun.creative",
    "mamoun.reasoning",
    "mamoun.human",
    "mamoun.emotion",
    "mamoun.instincts",
    "mamoun.deliberation",
    "mamoun.planning",
    "mamoun.preference",
    "mamoun.physical",
    "mamoun.ml",
    "mamoun.notifications",
    "mamoun.agents",
    "mamoun.hyperagent",
    "mamoun.approval",
    "mamoun.a2ui",
    "mamoun.core.llm_client",
    "mamoun.core.neural_bus",
    "mamoun.core.mamoun_kernel",
    "mamoun.core.triple_memory",
    "mamoun.core.unified_db",
    "mamoun.core.agi_orchestrator",
    "mamoun.brains.brain_router",
    "mamoun.agi.fluid_reasoner",
    "mamoun.agi.common_sense",
    "mamoun.agi.hallucination_detector",
    "mamoun.agi.privacy_guard",
    "mamoun.agi.skill_discovery",
    "mamoun.agi.social_perception",
    "mamoun.agi.cultural_alignment",
    "mamoun.agi.specialized_pipeline",
    "mamoun.agi.swarm_intelligence",
    "mamoun.agi.theory_of_mind",
    "mamoun.agi.intent_drift",
    "mamoun.core.absolute_executor",
    "mamoun.core.self_healing",
    "mamoun.core.capabilities_engine",
    "mamoun.core.consciousness_loop",
    "mamoun.core.autonomic_system",
    "mamoun.core.integration_layer",
    "mamoun.core.fused_core",
    "mamoun.core.legacy_bridge",
    "mamoun.core.project_scaffolder",
    "mamoun.core.project_registry",
    "mamoun.core.session_context",
    "mamoun.core.monitoring",
    "mamoun.core.reflexes",
    "mamoun.core.selective_attention",
    "mamoun.core.hierarchical_planner",
    "mamoun.core.causal_graph",
]

_saved_modules = {}


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """حفظ نسخة من الوحدات المحمية قبل كل اختبار"""
    for mod_name in _PROTECTED_MODULES:
        if mod_name in sys.modules:
            _saved_modules[mod_name] = sys.modules[mod_name]


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item, nextitem):
    """استعادة الوحدات المحمية بعد كل اختبار"""
    for mod_name, original_mod in _saved_modules.items():
        if mod_name in sys.modules and sys.modules[mod_name] is not original_mod:
            sys.modules[mod_name] = original_mod
    _saved_modules.clear()


# ═══════════════════════════════════════════════════════════════
# Async Event Loop Fix — يضمن وجود event loop للاختبارات
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def event_loop_policy():
    """سياسة event loop للاختبارات"""
    return asyncio.DefaultEventLoopPolicy()
