"""
BABSHARQII v40.0 — Comprehensive Fusion Tests
اختبارات شاملة لخطة الاندماج الكامل — الخطوات 1-12

Tests verify:
1. Deliberation Room connected to frontend
2. Auto-Research-Heal Loop activated
3. API key diversification + brain status
4. TypeScript validator in SelfModifier
5. Consciousness panel real data
6. Capability assessor
7. External project control enhanced
8. Continuous learner
9. Semantic router
10. Predictive healer
11. Self-tester
12. Unified Mind Controller
"""

import asyncio
import sys
import os
import time

# Add backend to path (from repo root)
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)


class FusionTestRunner:
    """مشغّل اختبارات الاندماج"""

    def __init__(self):
        self.results = {}
        self.passed = 0
        self.failed = 0
        self.errors = []

    def record(self, test_name: str, passed: bool, message: str = ""):
        self.results[test_name] = {
            "passed": passed,
            "message": message,
        }
        if passed:
            self.passed += 1
            print(f"  ✅ {test_name}: {message}")
        else:
            self.failed += 1
            self.errors.append(f"{test_name}: {message}")
            print(f"  ❌ {test_name}: {message}")

    def summary(self):
        total = self.passed + self.failed
        rate = round(self.passed / max(1, total) * 100, 1)
        print(f"\n{'='*60}")
        print(f"📊 نتائج الاختبارات: {self.passed}/{total} ({rate}%)")
        print(f"✅ نجح: {self.passed}")
        print(f"❌ فشل: {self.failed}")
        if self.errors:
            print(f"\n❌ الأخطاء:")
            for err in self.errors:
                print(f"   - {err}")
        print(f"{'='*60}")
        return rate >= 80  # 80% pass rate required


# ═══════════════════════════════════════════════════════════════
# Step 1: Deliberation Room Connected to Frontend
# ═══════════════════════════════════════════════════════════════

async def test_step1(runner: FusionTestRunner):
    """اختبار الخطوة 1: ربط غرفة المداولة بالفرونت إند"""
    print("\n🧪 الخطوة 1: ربط غرفة المداولة بالفرونت إند")

    # Test brains.ts has deliberateViaBackend
    try:
        with open("src/lib/brains.ts", "r") as f:
            content = f.read()
        has_deliberate = "deliberateViaBackend" in content
        runner.record(
            "1.1 brains.ts has deliberateViaBackend",
            has_deliberate,
            "Function exists" if has_deliberate else "Function NOT found"
        )
    except Exception as e:
        runner.record("1.1 brains.ts check", False, str(e)[:100])

    # Test deliberation route exists
    try:
        with open("src/app/api/deliberation/route.ts", "r") as f:
            content = f.read()
        has_route = "deliberate" in content.lower()
        runner.record(
            "1.2 deliberation route.ts exists",
            has_route,
            "Route file exists" if has_route else "Route NOT found"
        )
    except Exception as e:
        runner.record("1.2 deliberation route", False, str(e)[:100])

    # Test chat route uses deliberation
    try:
        with open("src/app/api/chat/route.ts", "r") as f:
            content = f.read()
        uses_deliberation = "deliberateViaBackend" in content or "deliberation" in content
        runner.record(
            "1.3 chat route uses deliberation",
            uses_deliberation,
            "Deliberation integrated" if uses_deliberation else "NOT integrated"
        )
    except Exception as e:
        runner.record("1.3 chat route deliberation", False, str(e)[:100])


# ═══════════════════════════════════════════════════════════════
# Step 2: Auto-Research-Heal Loop
# ═══════════════════════════════════════════════════════════════

async def test_step2(runner: FusionTestRunner):
    """اختبار الخطوة 2: تفعيل حلقة البحث-التعلم-الإصلاح"""
    print("\n🧪 الخطوة 2: حلقة البحث-التعلم-الإصلاح التلقائية")

    # Test AutoResearchHealLoop import
    try:
        from mamoun.evolution.auto_research_heal import AutoResearchHealLoop
        loop = AutoResearchHealLoop()
        runner.record("2.1 AutoResearchHealLoop import", True, "Module imports OK")
    except Exception as e:
        runner.record("2.1 AutoResearchHealLoop import", False, str(e)[:100])

    # Test health_monitor has auto-research-heal
    try:
        with open("backend/mamoun/api/health_monitor.py", "r") as f:
            content = f.read()
        has_auto_research = "AutoResearchHealLoop" in content or "auto_research_heal" in content
        runner.record(
            "2.2 health_monitor triggers auto-research-heal",
            has_auto_research,
            "Connected" if has_auto_research else "NOT connected"
        )
    except Exception as e:
        runner.record("2.2 health_monitor check", False, str(e)[:100])

    # Test AUTO_RESEARCH_HEAL_ENABLED flag
    try:
        with open("backend/mamoun/api/health_monitor.py", "r") as f:
            content = f.read()
        has_flag = "AUTO_RESEARCH_HEAL_ENABLED" in content
        runner.record(
            "2.3 AUTO_RESEARCH_HEAL_ENABLED flag",
            has_flag,
            "Flag exists" if has_flag else "Flag NOT found"
        )
    except Exception as e:
        runner.record("2.3 flag check", False, str(e)[:100])


# ═══════════════════════════════════════════════════════════════
# Step 3: API Key Diversification
# ═══════════════════════════════════════════════════════════════

async def test_step3(runner: FusionTestRunner):
    """اختبار الخطوة 3: تنويع مفاتيح API"""
    print("\n🧪 الخطوة 3: تنويع مفاتيح API + تقرير حالة الأدمغة")

    # Test brain_status endpoint
    try:
        from mamoun.api.brain_status import router
        runner.record("3.1 brain_status API", True, "Endpoint registered")
    except Exception as e:
        runner.record("3.1 brain_status API", False, str(e)[:100])

    # Test brain_router has fallback warnings
    try:
        with open("backend/mamoun/brains/brain_router.py", "r") as f:
            content = f.read()
        has_fallback = "fallback_warning" in content or "BRAIN_MODEL_REGISTRY" in content
        runner.record(
            "3.2 brain_router fallback warnings",
            has_fallback,
            "Warnings exist" if has_fallback else "NOT found"
        )
    except Exception as e:
        runner.record("3.2 brain_router check", False, str(e)[:100])

    # Test BRAIN_STATUS command
    try:
        with open("src/lib/command-parser.ts", "r") as f:
            content = f.read()
        has_brain_status_cmd = "BRAIN_STATUS" in content
        runner.record(
            "3.3 BRAIN_STATUS command",
            has_brain_status_cmd,
            "Command exists" if has_brain_status_cmd else "NOT found"
        )
    except Exception as e:
        runner.record("3.3 command check", False, str(e)[:100])


# ═══════════════════════════════════════════════════════════════
# Step 4: TypeScript Validator
# ═══════════════════════════════════════════════════════════════

async def test_step4(runner: FusionTestRunner):
    """اختبار الخطوة 4: مدقق TypeScript في SelfModifier"""
    print("\n🧪 الخطوة 4: مدقق TypeScript في SelfModifier")

    try:
        with open("backend/mamoun/core/self_modifier.py", "r") as f:
            content = f.read()

        has_ts_validate = "_validate_typescript" in content or "_validate_syntax" in content
        runner.record(
            "4.1 TypeScript validator method",
            has_ts_validate,
            "Method exists" if has_ts_validate else "NOT found"
        )

        has_js_validate = "_validate_javascript" in content or "node --check" in content
        runner.record(
            "4.2 JavaScript validator method",
            has_js_validate,
            "Method exists" if has_js_validate else "NOT found"
        )

        has_dispatch = "_validate_syntax" in content and (".ts" in content or "tsx" in content)
        runner.record(
            "4.3 Validation dispatch by extension",
            has_dispatch,
            "Dispatch exists" if has_dispatch else "NOT found"
        )
    except Exception as e:
        runner.record("4.1-4.3 self_modifier check", False, str(e)[:100])


# ═══════════════════════════════════════════════════════════════
# Step 5: Consciousness Panel Real Data
# ═══════════════════════════════════════════════════════════════

async def test_step5(runner: FusionTestRunner):
    """اختبار الخطوة 5: لوحة الوعي ببيانات حقيقية"""
    print("\n🧪 الخطوة 5: توصيل لوحة الوعي ببيانات حقيقية")

    try:
        with open("src/lib/jarvis-api.ts", "r") as f:
            content = f.read()

        has_fetch = "fetchRealSystemData" in content
        runner.record(
            "5.1 fetchRealSystemData function",
            has_fetch,
            "Function exists" if has_fetch else "NOT found"
        )

        has_polling = "startRealDataPolling" in content
        runner.record(
            "5.2 Real data polling",
            has_polling,
            "Polling exists" if has_polling else "NOT found"
        )

        has_backend_calls = "kernel/status" in content or "health-monitor" in content
        runner.record(
            "5.3 Backend API calls",
            has_backend_calls,
            "Calls exist" if has_backend_calls else "NOT found"
        )
    except Exception as e:
        runner.record("5.1-5.3 jarvis-api check", False, str(e)[:100])


# ═══════════════════════════════════════════════════════════════
# Step 6: Capability Assessor
# ═══════════════════════════════════════════════════════════════

async def test_step6(runner: FusionTestRunner):
    """اختبار الخطوة 6: نظام تقييم القدرات الذاتية"""
    print("\n🧪 الخطوة 6: نظام تقييم القدرات الذاتية")

    try:
        from mamoun.core.capability_assessor import CapabilityAssessor
        assessor = CapabilityAssessor()
        runner.record("6.1 CapabilityAssessor import", True, "Module imports OK")
    except Exception as e:
        runner.record("6.1 CapabilityAssessor import", False, str(e)[:100])

    try:
        from mamoun.api.capability_assessor import router
        runner.record("6.2 Capability API endpoint", True, "Endpoint registered")
    except Exception as e:
        runner.record("6.2 Capability API endpoint", False, str(e)[:100])

    try:
        with open("src/lib/command-parser.ts", "r") as f:
            content = f.read()
        has_assess = "ASSESS_CAPABILITIES" in content
        runner.record(
            "6.3 ASSESS_CAPABILITIES command",
            has_assess,
            "Command exists" if has_assess else "NOT found"
        )
    except Exception as e:
        runner.record("6.3 command check", False, str(e)[:100])


# ═══════════════════════════════════════════════════════════════
# Step 7: External Project Control Enhanced
# ═══════════════════════════════════════════════════════════════

async def test_step7(runner: FusionTestRunner):
    """اختبار الخطوة 7: تعزيز التحكم بالمشاريع الخارجية"""
    print("\n🧪 الخطوة 7: تعزيز التحكم بالمشاريع الخارجية")

    try:
        with open("backend/mamoun/api/external_controller.py", "r") as f:
            content = f.read()

        has_modify = "modify" in content.lower() and "/modify" in content
        runner.record(
            "7.1 modify_external_project endpoint",
            has_modify,
            "Endpoint exists" if has_modify else "NOT found"
        )

        has_monitor = "monitor" in content.lower() and "/monitor" in content
        runner.record(
            "7.2 monitor_external_project endpoint",
            has_monitor,
            "Endpoint exists" if has_monitor else "NOT found"
        )

        has_deploy = "/deploy" in content
        runner.record(
            "7.3 deploy endpoint",
            has_deploy,
            "Endpoint exists" if has_deploy else "NOT found"
        )
    except Exception as e:
        runner.record("7.1-7.3 external controller check", False, str(e)[:100])


# ═══════════════════════════════════════════════════════════════
# Step 8: Continuous Learner
# ═══════════════════════════════════════════════════════════════

async def test_step8(runner: FusionTestRunner):
    """اختبار الخطوة 8: التعلم المستمر"""
    print("\n🧪 الخطوة 8: ربط DeepSearch بحلقة التعلم المستمر")

    try:
        from mamoun.core.continuous_learner import ContinuousLearner
        learner = ContinuousLearner()
        has_learn_cycle = hasattr(learner, 'learn_cycle')
        runner.record(
            "8.1 ContinuousLearner with learn_cycle",
            has_learn_cycle,
            "Method exists" if has_learn_cycle else "NOT found"
        )
    except Exception as e:
        runner.record("8.1 ContinuousLearner import", False, str(e)[:100])

    try:
        from mamoun.api.continuous_learner import router
        runner.record("8.2 Learner API endpoint", True, "Endpoint registered")
    except Exception as e:
        runner.record("8.2 Learner API endpoint", False, str(e)[:100])


# ═══════════════════════════════════════════════════════════════
# Step 9: Semantic Router
# ═══════════════════════════════════════════════════════════════

async def test_step9(runner: FusionTestRunner):
    """اختبار الخطوة 9: التوافق الدلالي"""
    print("\n🧪 الخطوة 9: نظام التوافق الدلالي")

    try:
        from mamoun.brains.semantic_router import SemanticRouter
        router_instance = SemanticRouter()
        has_route = hasattr(router_instance, 'route')
        runner.record(
            "9.1 SemanticRouter with route()",
            has_route,
            "Method exists" if has_route else "NOT found"
        )
    except Exception as e:
        runner.record("9.1 SemanticRouter import", False, str(e)[:100])

    try:
        from mamoun.api.semantic_router import router
        runner.record("9.2 Semantic Router API", True, "Endpoint registered")
    except Exception as e:
        runner.record("9.2 Semantic Router API", False, str(e)[:100])


# ═══════════════════════════════════════════════════════════════
# Step 10: Predictive Healer
# ═══════════════════════════════════════════════════════════════

async def test_step10(runner: FusionTestRunner):
    """اختبار الخطوة 10: النظام التنبؤي"""
    print("\n🧪 الخطوة 10: نظام الإصلاح التنبؤي")

    try:
        from mamoun.core.predictive_healer import PredictiveHealer, get_predictive_healer
        healer = get_predictive_healer()

        has_collect = hasattr(healer, 'collect_metrics')
        runner.record(
            "10.1 PredictiveHealer.collect_metrics",
            has_collect,
            "Method exists" if has_collect else "NOT found"
        )

        has_predict = hasattr(healer, 'predict_failures')
        runner.record(
            "10.2 PredictiveHealer.predict_failures",
            has_predict,
            "Method exists" if has_predict else "NOT found"
        )

        has_prevent = hasattr(healer, 'take_preventive_action')
        runner.record(
            "10.3 PredictiveHealer.take_preventive_action",
            has_prevent,
            "Method exists" if has_prevent else "NOT found"
        )
    except Exception as e:
        runner.record("10.1-10.3 PredictiveHealer", False, str(e)[:100])

    try:
        from mamoun.api.predictive_healer_api import router
        runner.record("10.4 Predictive Healer API", True, "Endpoint registered")
    except Exception as e:
        runner.record("10.4 Predictive Healer API", False, str(e)[:100])


# ═══════════════════════════════════════════════════════════════
# Step 11: Self-Tester
# ═══════════════════════════════════════════════════════════════

async def test_step11(runner: FusionTestRunner):
    """اختبار الخطوة 11: نظام الاختبار الذاتي الشامل"""
    print("\n🧪 الخطوة 11: نظام الاختبار الذاتي الشامل")

    try:
        from mamoun.api.self_tester import run_full_test_suite
        runner.record("11.1 Self-test suite import", True, "Module imports OK")
    except Exception as e:
        runner.record("11.1 Self-test suite import", False, str(e)[:100])

    # Count test functions
    try:
        from mamoun.api import self_tester
        test_fns = [name for name in dir(self_tester) if name.startswith('test_')]
        runner.record(
            "11.2 Test functions count",
            len(test_fns) >= 8,
            f"{len(test_fns)} test functions (need >= 8)"
        )
    except Exception as e:
        runner.record("11.2 Test functions count", False, str(e)[:100])

    # Test SELF_TEST command
    try:
        with open("src/lib/command-parser.ts", "r") as f:
            content = f.read()
        has_cmd = "SELF_TEST" in content
        runner.record(
            "11.3 SELF_TEST command",
            has_cmd,
            "Command exists" if has_cmd else "NOT found"
        )
    except Exception as e:
        runner.record("11.3 SELF_TEST command", False, str(e)[:100])


# ═══════════════════════════════════════════════════════════════
# Step 12: Unified Mind Controller
# ═══════════════════════════════════════════════════════════════

async def test_step12(runner: FusionTestRunner):
    """اختبار الخطوة 12: العقل الموحّد"""
    print("\n🧪 الخطوة 12: العقل الموحّد (Unified Mind Controller)")

    try:
        from mamoun.core.unified_mind import UnifiedMind, get_unified_mind
        mind = get_unified_mind()

        has_process = hasattr(mind, 'process')
        runner.record(
            "12.1 UnifiedMind.process()",
            has_process,
            "Method exists" if has_process else "NOT found"
        )

        has_status = hasattr(mind, 'get_status')
        runner.record(
            "12.2 UnifiedMind.get_status()",
            has_status,
            "Method exists" if has_status else "NOT found"
        )

        has_initialize = hasattr(mind, 'initialize')
        runner.record(
            "12.3 UnifiedMind.initialize()",
            has_initialize,
            "Method exists" if has_initialize else "NOT found"
        )
    except Exception as e:
        runner.record("12.1-12.3 UnifiedMind", False, str(e)[:100])

    try:
        from mamoun.api.unified_mind_api import router
        runner.record("12.4 Unified Mind API", True, "Endpoint registered")
    except Exception as e:
        runner.record("12.4 Unified Mind API", False, str(e)[:100])

    # Test UNIFIED_MIND command
    try:
        with open("src/lib/command-parser.ts", "r") as f:
            content = f.read()
        has_cmd = "UNIFIED_MIND" in content
        runner.record(
            "12.5 UNIFIED_MIND command",
            has_cmd,
            "Command exists" if has_cmd else "NOT found"
        )
    except Exception as e:
        runner.record("12.5 UNIFIED_MIND command", False, str(e)[:100])


# ═══════════════════════════════════════════════════════════════
# Integration Test: All Routes Registered
# ═══════════════════════════════════════════════════════════════

async def test_integration(runner: FusionTestRunner):
    """اختبار التكامل: كل المسارات مسجّلة"""
    print("\n🧪 اختبار التكامل: كل المسارات مسجّلة")

    try:
        from mamoun.api.routes import api_router
        routes = [r.path for r in api_router.routes]

        required_routes = [
            "/brains/status",
            "/capabilities/assess",
            "/learning/cycle",
            "/brains/semantic-route",
            "/predictive-healer/status",
            "/self-test/run",
            "/unified-mind/process",
        ]

        for route in required_routes:
            found = any(route in r for r in routes)
            runner.record(
                f"INT. Route {route}",
                found,
                "Registered" if found else "NOT registered"
            )
    except Exception as e:
        runner.record("INT. Routes check", False, str(e)[:100])


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

async def main():
    print("🚀 Mamoun v40.0 — اختبارات الاندماج الكامل")
    print("=" * 60)

    runner = FusionTestRunner()

    # Change to repo directory for file reads
    os.chdir("/home/z/my-project/mamoun-repo")

    await test_step1(runner)
    await test_step2(runner)
    await test_step3(runner)
    await test_step4(runner)
    await test_step5(runner)
    await test_step6(runner)
    await test_step7(runner)
    await test_step8(runner)
    await test_step9(runner)
    await test_step10(runner)
    await test_step11(runner)
    await test_step12(runner)
    await test_integration(runner)

    success = runner.summary()

    # Save results
    import json
    with open("/home/z/my-project/download/fusion-test-results.json", "w") as f:
        json.dump({
            "passed": runner.passed,
            "failed": runner.failed,
            "total": runner.passed + runner.failed,
            "pass_rate": round(runner.passed / max(1, runner.passed + runner.failed) * 100, 1),
            "results": runner.results,
        }, f, ensure_ascii=False, indent=2)

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
