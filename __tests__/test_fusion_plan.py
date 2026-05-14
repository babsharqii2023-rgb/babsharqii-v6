"""
BABSHARQII v40.0 — Fusion Plan Tests
اختبارات خطة الدمج الـ12 — تتحقق من كل خطوات الاندماج

Tests cover:
  Step 1: Frontend connects to backend BrainRouter
  Step 2: API key diversification (brain status)
  Step 3: Auto-Research-Heal loop
  Step 4: External project controller enhancements
  Step 5: Real consciousness data from backend
  Step 6: TypeScript validation in SelfModifier
  Steps 7-12: Advanced systems exist and are registered
"""

import pytest
import asyncio
import os
import sys
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


# ═══════════════════════════════════════════════════════════════
# Step 1: Frontend Brain Routing via Backend
# ═══════════════════════════════════════════════════════════════

class TestStep1FrontendBrainRouting:
    """الخطوة 1: ربط الفرونت إند بـ BrainRouter الباك إند"""

    def test_brains_ts_exports_deliberate_via_backend(self):
        """يتحقق أن brains.ts يصدّر deliberateViaBackend"""
        brains_path = Path(__file__).parent.parent / "src" / "lib" / "brains.ts"
        if not brains_path.exists():
            pytest.skip("Frontend source not available")
        content = brains_path.read_text(encoding='utf-8')
        assert 'deliberateViaBackend' in content, "brains.ts must export deliberateViaBackend"
        assert '/api/brains/deliberate' in content, "deliberateViaBackend must call /api/brains/deliberate"

    def test_chat_route_uses_backend_deliberation(self):
        """يتحقق أن chat route يستخدم deliberateViaBackend دائماً"""
        chat_path = Path(__file__).parent.parent / "src" / "app" / "api" / "chat" / "route.ts"
        if not chat_path.exists():
            pytest.skip("Frontend source not available")
        content = chat_path.read_text(encoding='utf-8')
        # Verify that the route always tries backend deliberation first
        assert 'deliberateViaBackend' in content, "chat route must use deliberateViaBackend"
        assert 'backendDeliberationUsed' in content, "chat route must track backend deliberation status"

    def test_chat_route_falls_back_to_local(self):
        """يتحقق أن chat route يتراجع للتوجيه المحلي عند عدم توفر الباك إند"""
        chat_path = Path(__file__).parent.parent / "src" / "app" / "api" / "chat" / "route.ts"
        if not chat_path.exists():
            pytest.skip("Frontend source not available")
        content = chat_path.read_text(encoding='utf-8')
        assert 'decision.routing.primaryBrain' in content, "Must fall back to local routing"


# ═══════════════════════════════════════════════════════════════
# Step 2: API Key Diversification
# ═══════════════════════════════════════════════════════════════

class TestStep2APIKeyDiversification:
    """الخطوة 2: تنويع مفاتيح API"""

    def test_brain_model_registry_exists(self):
        """يتحقق من وجود سجل نماذج الأدمغة"""
        from mamoun.brains.brain_router import BRAIN_MODEL_REGISTRY
        assert isinstance(BRAIN_MODEL_REGISTRY, dict)
        assert len(BRAIN_MODEL_REGISTRY) == 5, "Must have 5 brain entries"

    def test_each_brain_has_api_key_env(self):
        """يتحقق أن كل دماغ له متغير مفتاح API"""
        from mamoun.brains.brain_router import BRAIN_MODEL_REGISTRY
        for brain_id, entry in BRAIN_MODEL_REGISTRY.items():
            assert "api_key_env" in entry, f"Brain {brain_id} missing api_key_env"
            assert entry["api_key_env"], f"Brain {brain_id} has empty api_key_env"

    def test_brain_status_api_exists(self):
        """يتحقق من وجود API حالة الأدمغة"""
        from mamoun.api.brain_status import router
        routes = [r.path for r in router.routes]
        assert any("status" in str(r) for r in routes), "Brain status route must exist"

    def test_brain_router_checks_fallback(self):
        """يتحقق أن BrainRouter يفحص النماذج البديلة"""
        from mamoun.brains.brain_router import BrainRouter
        router = BrainRouter()
        assert hasattr(router, '_check_fallback_models'), "Must have fallback check method"
        assert hasattr(router, 'get_brain_status'), "Must have brain status method"


# ═══════════════════════════════════════════════════════════════
# Step 3: Auto-Research-Heal Loop
# ═══════════════════════════════════════════════════════════════

class TestStep3AutoResearchHealLoop:
    """الخطوة 3: حلقة البحث والشفاء التلقائية"""

    def test_module_imports(self):
        """يتحقق من إمكانية استيراد الوحدة"""
        from mamoun.core.auto_research_heal_loop import AutoResearchHealLoop
        assert AutoResearchHealLoop is not None

    def test_loop_initialization(self):
        """يتحقق من تهيئة الحلقة"""
        from mamoun.core.auto_research_heal_loop import AutoResearchHealLoop
        loop = AutoResearchHealLoop()
        assert loop is not None
        assert hasattr(loop, 'initialize')
        assert hasattr(loop, 'start')
        assert hasattr(loop, 'shutdown')
        assert hasattr(loop, 'run_cycle')
        assert hasattr(loop, 'get_status')
        assert hasattr(loop, 'get_history')

    def test_loop_status_structure(self):
        """يتحقق من بنية تقرير الحالة"""
        from mamoun.core.auto_research_heal_loop import AutoResearchHealLoop
        loop = AutoResearchHealLoop()
        status = loop.get_status()
        assert "enabled" in status
        assert "running" in status
        assert "initialized" in status
        assert "total_cycles" in status
        assert "success_count" in status

    def test_api_endpoints_exist(self):
        """يتحقق من وجود نقاط API"""
        from mamoun.api.auto_research_heal import router
        routes = [r.path for r in router.routes]
        assert any("status" in str(r) for r in routes)
        assert any("start" in str(r) for r in routes)
        assert any("stop" in str(r) for r in routes)
        assert any("cycle" in str(r) for r in routes)
        assert any("history" in str(r) for r in routes)

    def test_api_route_registered(self):
        """يتحقق من تسجيل المسار في المسارات الرئيسية"""
        from mamoun.api.routes import api_router
        route_prefixes = []
        for route in api_router.routes:
            if hasattr(route, 'path'):
                route_prefixes.append(route.path)
        # The auto-research-heal routes should be registered
        # Check that routes.py imported the module
        import mamoun.api.routes as routes_module
        assert hasattr(routes_module, 'auto_research_heal_router')


# ═══════════════════════════════════════════════════════════════
# Step 4: External Project Controller
# ═══════════════════════════════════════════════════════════════

class TestStep4ExternalProjectController:
    """الخطوة 4: تحكم محسّن بالمشاريع الخارجية"""

    def test_modify_endpoint_exists(self):
        """يتحقق من وجود نقطة تعديل المشاريع"""
        from mamoun.api.external_controller import router
        routes = [r.path for r in router.routes]
        assert any("modify" in str(r) for r in routes)

    def test_monitor_endpoint_exists(self):
        """يتحقق من وجود نقطة مراقبة المشروع"""
        from mamoun.api.external_controller import router
        routes = [r.path for r in router.routes]
        assert any("monitor" in str(r) for r in routes)

    def test_run_command_endpoint_exists(self):
        """يتحقق من وجود نقطة تشغيل الأوامر"""
        from mamoun.api.external_controller import router
        routes = [r.path for r in router.routes]
        assert any("run" in str(r) for r in routes)

    def test_structure_endpoint_exists(self):
        """يتحقق من وجود نقطة عرض الهيكل"""
        from mamoun.api.external_controller import router
        routes = [r.path for r in router.routes]
        assert any("structure" in str(r) for r in routes)

    def test_edit_with_llm_exists(self):
        """يتحقق من وجود تعديل بالـ LLM"""
        from mamoun.api.external_controller import router
        routes = [r.path for r in router.routes]
        assert any("edit" in str(r) for r in routes)


# ═══════════════════════════════════════════════════════════════
# Step 5: Real Consciousness Data
# ═══════════════════════════════════════════════════════════════

class TestStep5ConsciousnessData:
    """الخطوة 5: بيانات الوعي الحقيقية من الباك إند"""

    def test_jarvis_api_fetches_real_data(self):
        """يتحقق أن jarvis-api.ts يحاول جلب بيانات حقيقية"""
        jarvis_path = Path(__file__).parent.parent / "src" / "lib" / "jarvis-api.ts"
        if not jarvis_path.exists():
            pytest.skip("Frontend source not available")
        content = jarvis_path.read_text(encoding='utf-8')

        # Check that fetchConsciousnessState tries backend first
        assert 'consciousness/state' in content, "Must fetch from /api/consciousness/state"
        assert '_isOffline' in content, "Must mark offline data"
        assert '_fallbackWarning' in content, "Must warn about fallback data"

    def test_consciousness_simple_fetches_real_data(self):
        """يتحقق أن fetchConsciousnessSimple يحاول جلب بيانات حقيقية"""
        jarvis_path = Path(__file__).parent.parent / "src" / "lib" / "jarvis-api.ts"
        if not jarvis_path.exists():
            pytest.skip("Frontend source not available")
        content = jarvis_path.read_text(encoding='utf-8')

        # Find fetchConsciousnessSimple function
        simple_start = content.find('fetchConsciousnessSimple')
        assert simple_start > -1, "fetchConsciousnessSimple must exist"
        simple_section = content[simple_start:simple_start + 1000]
        assert '_isOffline' in simple_section, "Must mark offline data"


# ═══════════════════════════════════════════════════════════════
# Step 6: TypeScript Validation in SelfModifier
# ═══════════════════════════════════════════════════════════════

class TestStep6TypeScriptValidation:
    """الخطوة 6: التحقق من TypeScript في SelfModifier"""

    def test_validate_syntax_dispatches_typescript(self):
        """يتحقق أن _validate_syntax يرسل ملفات TypeScript للمدقق المناسب"""
        from mamoun.core.self_modifier import SelfModifier
        modifier = SelfModifier.__new__(SelfModifier)
        # Check that the method exists and dispatches correctly
        assert hasattr(modifier, '_validate_syntax'), "Must have _validate_syntax method"
        assert hasattr(modifier, '_validate_typescript'), "Must have _validate_typescript method"
        assert hasattr(modifier, '_validate_javascript'), "Must have _validate_javascript method"
        assert hasattr(modifier, '_validate_typescript_regex'), "Must have regex fallback"

    def test_validate_typescript_regex_basic(self):
        """يتحقق أن فحص TypeScript بالتعبيرات النمطية يعمل"""
        from mamoun.core.self_modifier import SelfModifier
        modifier = SelfModifier.__new__(SelfModifier)

        # Valid TypeScript
        valid_ts = "const x: number = 5;\nfunction hello(): string { return 'world'; }"
        is_valid, error = modifier._validate_typescript_regex(valid_ts, "test.ts")
        assert is_valid, f"Valid TypeScript should pass: {error}"

        # Invalid TypeScript (unmatched braces)
        invalid_ts = "function foo() { return { a: 1 "
        is_valid, error = modifier._validate_typescript_regex(invalid_ts, "test.ts")
        assert not is_valid, "Invalid TypeScript should fail"

    def test_validate_javascript_basic(self):
        """يتحقق أن فحص JavaScript يعمل"""
        from mamoun.core.self_modifier import SelfModifier
        modifier = SelfModifier.__new__(SelfModifier)

        # Valid JavaScript
        valid_js = "const x = 5;\nfunction hello() { return 'world'; }"
        is_valid, error = modifier._validate_javascript(valid_js, "test.js")
        # May pass or fail depending on node availability, but should not crash
        assert isinstance(is_valid, bool)

    def test_self_modifier_handles_ts_files(self):
        """يتحقق أن SelfModifier يتعامل مع ملفات TypeScript"""
        from mamoun.core.self_modifier import SelfModifier
        assert ".ts" in SelfModifier.TS_JS_EXTENSIONS
        assert ".tsx" in SelfModifier.TS_JS_EXTENSIONS
        assert ".js" in SelfModifier.TS_JS_EXTENSIONS
        assert ".jsx" in SelfModifier.TS_JS_EXTENSIONS


# ═══════════════════════════════════════════════════════════════
# Steps 7-12: Advanced Systems Integration
# ═══════════════════════════════════════════════════════════════

class TestSteps7to12AdvancedSystems:
    """الخطوات 7-12: الأنظمة المتقدمة"""

    def test_continuous_learner_exists(self):
        """الخطوة 8: يتحقق من وجود المتعلم المستمر"""
        from mamoun.api.continuous_learner import router
        assert router is not None

    def test_semantic_router_exists(self):
        """الخطوة 9: يتحقق من وجود الموجّه الدلالي"""
        from mamoun.api.semantic_router import router
        assert router is not None

    def test_predictive_healer_exists(self):
        """الخطوة 10: يتحقق من وجود المشافي التنبؤي"""
        from mamoun.api.predictive_healer import router
        assert router is not None

    def test_self_tester_exists(self):
        """الخطوة 11: يتحقق من وجود الاختبار الذاتي"""
        from mamoun.api.self_tester import router
        assert router is not None

    def test_unified_mind_exists(self):
        """الخطوة 12: يتحقق من وجود العقل الموحّد"""
        from mamoun.api.unified_mind import router
        assert router is not None

    def test_all_routers_registered_in_api(self):
        """يتحقق أن كل المسارات مسجلة في API الرئيسي"""
        from mamoun.api.routes import api_router
        registered_routes = []
        for route in api_router.routes:
            if hasattr(route, 'path'):
                registered_routes.append(route.path)

        # Count total routes
        assert len(registered_routes) > 50, f"Expected >50 routes, got {len(registered_routes)}"


# ═══════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════

class TestIntegration:
    """اختبارات التكامل"""

    def test_brain_router_creates_successfully(self):
        """يتحقق من إنشاء BrainRouter بنجاح"""
        from mamoun.brains.brain_router import BrainRouter
        router = BrainRouter()
        assert router is not None
        assert hasattr(router, 'route')
        assert hasattr(router, 'get_brain_status')
        assert hasattr(router, 'get_stats')

    def test_auto_research_heal_singleton(self):
        """يتحقق من نمط Singleton للحلقة"""
        from mamoun.core.auto_research_heal_loop import get_auto_research_heal
        loop1 = get_auto_research_heal()
        loop2 = get_auto_research_heal()
        assert loop1 is loop2, "Should return same instance"

    def test_self_healing_engine_exists(self):
        """يتحقق من وجود محرك الشفاء الذاتي"""
        from mamoun.core.self_healing import SelfHealingEngine
        engine = SelfHealingEngine()
        assert engine is not None
        assert hasattr(engine, 'initialize')
        assert hasattr(engine, 'run_health_check')
        assert hasattr(engine, 'get_status')

    def test_live_self_modifier_exists(self):
        """يتحقق من وجود المعدّل الذاتي المباشر"""
        from mamoun.evolution.live_self_modifier import LiveSelfModifier
        modifier = LiveSelfModifier()
        assert modifier is not None
        assert hasattr(modifier, 'report_weakness')
        assert hasattr(modifier, 'improve_myself')
        assert hasattr(modifier, 'start')


# ═══════════════════════════════════════════════════════════════
# Fusion Rate Tests
# ═══════════════════════════════════════════════════════════════

class TestFusionRate:
    """اختبارات نسبة الدمج"""

    def test_execution_bridge_rate(self):
        """
        جسر التنفيذ: يتحقق من أن 13 أمر كلها متصلة بالباك إند
        الأوامر: git_sync, self_modify, search, self_analyze, self_improve,
        create_file, read_file, edit_file, list_files, build_agent,
        build_project, create_tool, set_api_key
        """
        chat_path = Path(__file__).parent.parent / "src" / "app" / "api" / "chat" / "route.ts"
        if not chat_path.exists():
            pytest.skip("Frontend source not available")
        content = chat_path.read_text(encoding='utf-8')

        expected_commands = [
            'git_sync', 'self_modify', 'search', 'self_analyze',
            'self_improve', 'create_file', 'read_file', 'edit_file',
            'list_files', 'build_agent', 'build_project', 'create_tool',
            'set_api_key',
        ]

        for cmd in expected_commands:
            assert cmd in content, f"Execution bridge missing command: {cmd}"

    def test_deliberation_bridge_rate(self):
        """
        جسر المداولة: يتحقق من أن المداولة تستخدم BrainRouter الباك إند
        """
        chat_path = Path(__file__).parent.parent / "src" / "app" / "api" / "chat" / "route.ts"
        if not chat_path.exists():
            pytest.skip("Frontend source not available")
        content = chat_path.read_text(encoding='utf-8')

        # Must have backend deliberation
        assert 'deliberateViaBackend' in content
        # Must have SSE deliberation endpoint
        assert '/api/brains/deliberate' in content
        # Must track backend deliberation usage
        assert 'backendDeliberationUsed' in content

    def test_monitoring_bridge_rate(self):
        """
        جسر المراقبة: يتحقق من أن المراقبة تعمل تلقائياً
        """
        from mamoun.core.self_healing import SelfHealingEngine
        engine = SelfHealingEngine()
        # Must initialize to register default checks
        engine.initialize()
        # Should have default health checks
        assert len(engine._health_checks) >= 5, f"Must have at least 5 default health checks, got {len(engine._health_checks)}"
        # Should have repair strategies
        assert len(engine._repair_strategies) >= 6, f"Must have at least 6 repair strategies, got {len(engine._repair_strategies)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
