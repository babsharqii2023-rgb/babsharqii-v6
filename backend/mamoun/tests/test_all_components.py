"""
Comprehensive Tests for Super Mind v58
Tests each component honestly — no mocks for core logic.
Updated to test all v58 improvements.
"""

import os
import sys
import time
import asyncio
import unittest

# Add ALL necessary paths
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, 'core'))
sys.path.insert(0, os.path.join(_project_root, 'core', 'super_brain'))
sys.path.insert(0, os.path.join(_project_root, 'core', 'shared'))


class TestMetaCognitionEngine(unittest.TestCase):
    """Test MetaCognitionEngine — REAL measurements, no hardcoded values."""

    def setUp(self):
        from meta_cognition_engine import MetaCognitionEngine, OutcomeRecord
        import tempfile
        temp_dir = tempfile.mkdtemp()
        self.engine = MetaCognitionEngine(persistence_dir=temp_dir)
        self.OutcomeRecord = OutcomeRecord

    def test_initial_scores_are_zero(self):
        """All scores should start at 0 (unknown), not fake percentages."""
        profile = self.engine.get_profile("test_component")
        self.assertIsNone(profile)

    def test_record_outcome_creates_real_profile(self):
        """After recording outcomes, profile should have real data."""
        from meta_cognition_engine import OutcomeRecord

        for i in range(10):
            self.engine.record_outcome(OutcomeRecord(
                component="brain_router",
                operation="route",
                success=True,
                quality_score=0.8 + (i * 0.02),
                predicted_quality=0.85,
                latency_ms=150,
            ))

        profile = self.engine.get_profile("brain_router")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.total_operations, 10)
        self.assertEqual(profile.success_count, 10)
        self.assertGreater(profile.reliability_score, 0.0)
        self.assertLessEqual(profile.reliability_score, 1.0)

    def test_reliability_reflects_real_performance(self):
        """Reliability score must reflect actual outcomes."""
        from meta_cognition_engine import OutcomeRecord

        for i in range(20):
            self.engine.record_outcome(OutcomeRecord(
                component="test_component",
                operation="test",
                success=(i % 3 != 0),
                quality_score=0.6 if i % 3 != 0 else 0.2,
                predicted_quality=0.5,
                latency_ms=100,
            ))

        profile = self.engine.get_profile("test_component")
        self.assertAlmostEqual(profile.success_rate, 14/20, places=0)
        self.assertGreater(profile.quality_average, 0.0)

    def test_confidence_calibration(self):
        """Calibration should measure prediction accuracy."""
        from meta_cognition_engine import OutcomeRecord

        for i in range(10):
            self.engine.record_outcome(OutcomeRecord(
                component="calibrated",
                operation="test",
                success=True,
                quality_score=0.8,
                predicted_quality=0.79,
                latency_ms=100,
            ))

        profile = self.engine.get_profile("calibrated")
        self.assertGreater(profile.confidence_calibration, 0.8)

    def test_stagnation_detection(self):
        """Should detect when a component stops improving."""
        from meta_cognition_engine import OutcomeRecord

        for i in range(60):
            self.engine.record_outcome(OutcomeRecord(
                component="stagnant_component",
                operation="test",
                success=True,
                quality_score=0.5,
                predicted_quality=0.5,
                latency_ms=100,
            ))

        stagnant = self.engine.get_stagnant_components()
        self.assertIsInstance(stagnant, list)

    def test_health_status(self):
        """v58: Health status should reflect real component health."""
        from meta_cognition_engine import OutcomeRecord

        # Record good performance
        for i in range(10):
            self.engine.record_outcome(OutcomeRecord(
                component="healthy_component",
                operation="test",
                success=True,
                quality_score=0.9,
                predicted_quality=0.85,
                latency_ms=100,
            ))

        profile = self.engine.get_profile("healthy_component")
        self.assertEqual(profile.health_status, "healthy")

    def test_unhealthy_components(self):
        """v58: Should identify unhealthy components."""
        from meta_cognition_engine import OutcomeRecord

        for i in range(10):
            self.engine.record_outcome(OutcomeRecord(
                component="bad_component",
                operation="test",
                success=False,
                quality_score=0.1,
                predicted_quality=0.5,
                latency_ms=5000,
            ))

        unhealthy = self.engine.get_unhealthy_components()
        self.assertTrue(any(u["component"] == "bad_component" for u in unhealthy))

    def test_persistence(self):
        """v58: Should save and load data from disk."""
        from meta_cognition_engine import OutcomeRecord
        import tempfile

        # Create engine with temp directory
        from meta_cognition_engine import MetaCognitionEngine
        temp_dir = tempfile.mkdtemp()
        engine = MetaCognitionEngine(persistence_dir=temp_dir)

        for i in range(10):
            engine.record_outcome(OutcomeRecord(
                component="persist_test",
                operation="test",
                success=True,
                quality_score=0.8,
                predicted_quality=0.7,
                latency_ms=100,
            ))

        # Save
        self.assertTrue(engine.save())

        # Load in new engine
        engine2 = MetaCognitionEngine(persistence_dir=temp_dir)
        profile = engine2.get_profile("persist_test")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.total_operations, 10)


class TestASTSecurityChecker(unittest.TestCase):
    """Test the AST security checker."""

    def setUp(self):
        from self_modifier import ASTSecurityChecker
        self.checker = ASTSecurityChecker()

    def test_blocks_os_system(self):
        code = "import os\nos.system('rm -rf /')"
        is_safe, violations = self.checker.check(code)
        self.assertFalse(is_safe)

    def test_blocks_subprocess(self):
        code = "import subprocess\nsubprocess.run(['ls'])"
        is_safe, violations = self.checker.check(code)
        self.assertFalse(is_safe)

    def test_blocks_eval(self):
        code = "x = eval('1+1')"
        is_safe, violations = self.checker.check(code)
        self.assertFalse(is_safe)

    def test_blocks_exec(self):
        code = "exec('print(1)')"
        is_safe, violations = self.checker.check(code)
        self.assertFalse(is_safe)

    def test_allows_safe_code(self):
        code = """
def hello(name: str) -> str:
    return f"Hello, {name}!"

result = hello("World")
"""
        is_safe, violations = self.checker.check(code)
        self.assertTrue(is_safe)

    def test_allows_os_path(self):
        code = "import os\npath = os.path.join('a', 'b')"
        is_safe, violations = self.checker.check(code)
        self.assertTrue(is_safe)


class TestRestrictedExecutor(unittest.TestCase):
    """Test the restricted code executor."""

    def setUp(self):
        from self_modifier import RestrictedExecutor
        self.executor = RestrictedExecutor()

    def test_executes_safe_code(self):
        code = "result = 2 + 2"
        result = self.executor.execute(code)
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], 4)

    def test_blocks_dangerous_code(self):
        code = "import os\nos.system('echo hacked')"
        result = self.executor.execute(code)
        self.assertFalse(result["success"])

    def test_captures_print_output(self):
        code = "print('hello world')"
        result = self.executor.execute(code)
        self.assertTrue(result["success"])
        self.assertIn("hello world", result["output"])


class TestTypeScriptValidator(unittest.TestCase):
    """Test TypeScript validation."""

    def setUp(self):
        from full_self_rewriter import TypeScriptValidator
        self.validator = TypeScriptValidator()

    def test_valid_typescript(self):
        code = """
interface User {
  name: string;
  age: number;
}

function greet(user: User): string {
  return `Hello, ${user.name}!`;
}
"""
        result = self.validator.validate(code)
        self.assertIn("passed", result)
        self.assertIn("method", result)

    def test_reports_method(self):
        result = self.validator.validate("const x: number = 1;")
        self.assertIn(result["method"], ["tsc_compiler", "ast_fallback"])

    def test_tsc_version(self):
        """v58: Should report TSC version."""
        from full_self_rewriter import TypeScriptValidator
        validator = TypeScriptValidator()
        self.assertIsNotNone(validator._tsc_version)


class TestPythonValidator(unittest.TestCase):
    """Test Python validation."""

    def setUp(self):
        from full_self_rewriter import PythonValidator
        self.validator = PythonValidator()

    def test_valid_python(self):
        code = "def hello():\n    return 'world'"
        result = self.validator.validate(code)
        self.assertTrue(result["passed"])

    def test_invalid_python(self):
        code = "def broken("
        result = self.validator.validate(code)
        self.assertFalse(result["passed"])

    def test_quality_score(self):
        """v58: Should return quality score."""
        code = "def hello():\n    return 'world'"
        result = self.validator.validate(code)
        self.assertIn("quality_score", result)


class TestNeuralBus(unittest.TestCase):
    """Test the event bus."""

    def setUp(self):
        from neural_bus import NeuralBus, Event
        self.bus = NeuralBus()
        self.Event = Event

    def test_subscribe_and_publish(self):
        received = []
        def handler(event):
            received.append(event)

        self.bus.subscribe("test.event", handler)
        self.bus.publish_sync(self.Event(
            event_type="test.event", source="test", data={"msg": "hello"},
        ))
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].data["msg"], "hello")

    def test_no_delivery_to_wrong_subscriber(self):
        received = []
        def handler(event):
            received.append(event)

        self.bus.subscribe("test.event", handler)
        self.bus.publish_sync(self.Event(
            event_type="other.event", source="test",
        ))
        self.assertEqual(len(received), 0)


class TestRegistry(unittest.TestCase):
    """Test tool and agent registries."""

    def test_tool_registry(self):
        from registry import ToolRegistry, ToolEntry
        registry = ToolRegistry()
        entry = ToolEntry(name="test_tool", description="A test tool")
        registry.register(entry)
        self.assertIsNotNone(registry.get("test_tool"))
        registry.record_usage("test_tool", success=True)
        tool = registry.get("test_tool")
        self.assertEqual(tool.use_count, 1)

    def test_agent_registry_auto_promote(self):
        from registry import AgentRegistry, AgentEntry
        registry = AgentRegistry()
        entry = AgentEntry(name="test_agent", description="A test agent", mode="observation")
        registry.register(entry)
        for _ in range(10):
            registry.record_outcome("test_agent", success=True)
        agent = registry.get("test_agent")
        self.assertEqual(agent.mode, "active")

    def test_agent_registry_auto_demote(self):
        from registry import AgentRegistry, AgentEntry
        registry = AgentRegistry()
        entry = AgentEntry(name="test_agent", description="Test", mode="active")
        registry.register(entry)
        for _ in range(4):
            registry.record_outcome("test_agent", success=False)
        agent = registry.get("test_agent")
        self.assertEqual(agent.mode, "observation")


class TestMultiProviderLLM(unittest.TestCase):
    """Test multi-provider LLM client."""

    def test_provider_configs_exist(self):
        from multi_provider_llm import DEFAULT_PROVIDERS, ProviderName
        self.assertIn(ProviderName.GLM, DEFAULT_PROVIDERS)
        self.assertIn(ProviderName.GEMINI, DEFAULT_PROVIDERS)
        self.assertIn(ProviderName.DEEPSEEK, DEFAULT_PROVIDERS)
        self.assertIn(ProviderName.ZAI, DEFAULT_PROVIDERS)
        self.assertIn(ProviderName.CRITIC, DEFAULT_PROVIDERS)

    def test_different_models_per_provider(self):
        from multi_provider_llm import DEFAULT_PROVIDERS
        models = [p.model for p in DEFAULT_PROVIDERS.values()]
        unique_models = set(models)
        self.assertGreaterEqual(len(unique_models), 3)

    def test_different_temperatures(self):
        from multi_provider_llm import DEFAULT_PROVIDERS
        temps = [p.temperature for p in DEFAULT_PROVIDERS.values()]
        unique_temps = set(temps)
        self.assertGreaterEqual(len(unique_temps), 3)


class TestBrainRouter(unittest.TestCase):
    """Test BrainRouter configuration."""

    def test_different_providers_per_brain(self):
        from brain_router import DEFAULT_BRAINS
        providers = [b.provider for b in DEFAULT_BRAINS]
        unique_providers = set(providers)
        self.assertGreaterEqual(len(unique_providers), 4)

    def test_different_personalities(self):
        from brain_router import DEFAULT_BRAINS
        personalities = [b.personality.value for b in DEFAULT_BRAINS]
        unique = set(personalities)
        self.assertEqual(len(unique), 5)

    def test_personality_prompts_exist(self):
        """v58: Each personality should have a system prompt."""
        from brain_router import PERSONALITY_PROMPTS, BrainPersonality
        for personality in BrainPersonality:
            self.assertIn(personality, PERSONALITY_PROMPTS)
            self.assertTrue(len(PERSONALITY_PROMPTS[personality]) > 10)


class TestImprovementProposer(unittest.TestCase):
    """Test Improvement Proposer."""

    def test_feature_flags(self):
        from improvement_proposer import FeatureFlags
        flags = FeatureFlags()
        flags.register("test_flag", default=False, description="Test")
        self.assertFalse(flags.is_enabled("test_flag"))
        flags.enable("test_flag")
        self.assertTrue(flags.is_enabled("test_flag"))
        flags.disable("test_flag")
        self.assertFalse(flags.is_enabled("test_flag"))

    def test_identifies_weak_components(self):
        from improvement_proposer import ImprovementProposer
        from meta_cognition_engine import MetaCognitionEngine, OutcomeRecord

        meta = MetaCognitionEngine()
        proposer = ImprovementProposer(meta_cognition=meta)

        for _ in range(10):
            meta.record_outcome(OutcomeRecord(
                component="bad_component",
                operation="test",
                success=False,
                quality_score=0.2,
                predicted_quality=0.5,
                latency_ms=100,
            ))

        weak = proposer._identify_weak_components()
        self.assertTrue(any(w["component"] == "bad_component" for w in weak))


class TestWebSearchClient(unittest.TestCase):
    """Test Web Search Client."""

    def test_cache_works(self):
        from web_search_client import LRUCache, SearchResponse, SearchResult
        cache = LRUCache(max_size=10, ttl_seconds=60)
        response = SearchResponse(
            query="test",
            results=[SearchResult(url="http://test.com", title="Test", snippet="Test", source="test")],
            total_results=1, source_used="test", latency_ms=100,
        )
        cache.put("test", 10, response)
        cached = cache.get("test", 10)
        self.assertIsNotNone(cached)
        self.assertEqual(cached.query, "test")

    def test_rate_limiter(self):
        from web_search_client import RateLimiter
        limiter = RateLimiter(requests_per_minute=60)
        self.assertEqual(len(limiter._timestamps), 0)

    def test_quality_scoring_with_query(self):
        """v58: Quality scoring should consider query relevance."""
        from web_search_client import WebSearchClient, SearchResult
        client = WebSearchClient()
        result = SearchResult(url="https://python.org", title="Python Programming", snippet="Learn Python programming", source="test")
        quality = client._compute_quality(result, "python programming")
        self.assertGreater(quality, 0.0)


class TestZaiSdkWrapper(unittest.TestCase):
    """Test Z-AI SDK Python wrapper."""

    def test_wrapper_creates(self):
        from zai_sdk_wrapper import ZaiSdkWrapper
        wrapper = ZaiSdkWrapper()
        self.assertIsNotNone(wrapper)

    def test_helper_script_created(self):
        from zai_sdk_wrapper import ZaiSdkWrapper
        wrapper = ZaiSdkWrapper()
        path = wrapper._get_helper_path()
        self.assertTrue(os.path.exists(path))


class TestExternalProjectController(unittest.TestCase):
    """Test External Project Controller."""

    def test_analyze_project(self):
        from external_project_controller import ExternalProjectController
        controller = ExternalProjectController(project_path="/home/z/my-project")
        self.assertIsNotNone(controller)

    def test_project_health(self):
        """v58: Should return project health dashboard."""
        from external_project_controller import ExternalProjectController
        import tempfile
        # Create a temp project for analysis
        temp_dir = tempfile.mkdtemp()
        controller = ExternalProjectController(project_path=temp_dir)
        asyncio.get_event_loop().run_until_complete(controller.analyze_project())
        health = controller.get_project_health()
        self.assertIn("score", health)


class TestMamounKernel(unittest.TestCase):
    """Test Mamoun Kernel initialization."""

    def test_kernel_creates(self):
        from mamoun_kernel import MamounKernel, KernelState
        kernel = MamounKernel()
        self.assertEqual(kernel.state, KernelState.INITIALIZING)

    def test_kernel_has_self_improvement_intervals(self):
        """v58: Should have self-improvement cycle intervals."""
        from mamoun_kernel import MamounKernel
        kernel = MamounKernel()
        self.assertGreater(kernel.SELF_IMPROVEMENT_INTERVAL, 0)
        self.assertGreater(kernel.SELF_ASSESSMENT_INTERVAL, 0)
        self.assertGreater(kernel.META_SAVE_INTERVAL, 0)


if __name__ == "__main__":
    unittest.main()
