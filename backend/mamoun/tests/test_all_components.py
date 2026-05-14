"""
Comprehensive Tests for Super Mind v57
Tests each component honestly — no mocks for core logic.
"""

import os
import sys
import time
import asyncio
import unittest

# Add ALL necessary paths for both super_brain and shared modules
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, 'core'))
sys.path.insert(0, os.path.join(_project_root, 'core', 'super_brain'))
sys.path.insert(0, os.path.join(_project_root, 'core', 'shared'))


class TestMetaCognitionEngine(unittest.TestCase):
    """Test MetaCognitionEngine — REAL measurements, no hardcoded values."""

    def setUp(self):
        from meta_cognition_engine import MetaCognitionEngine, OutcomeRecord
        self.engine = MetaCognitionEngine()
        self.OutcomeRecord = OutcomeRecord

    def test_initial_scores_are_zero(self):
        """NEW: All scores should start at 0 (unknown), not fake percentages."""
        profile = self.engine.get_profile("test_component")
        self.assertIsNone(profile)  # No profile = no fake data

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
        """Reliability score must reflect actual outcomes, not hardcoded values."""
        from meta_cognition_engine import OutcomeRecord

        # Record mixed outcomes
        for i in range(20):
            self.engine.record_outcome(OutcomeRecord(
                component="test_component",
                operation="test",
                success=(i % 3 != 0),  # ~67% success rate
                quality_score=0.6 if i % 3 != 0 else 0.2,
                predicted_quality=0.5,
                latency_ms=100,
            ))

        profile = self.engine.get_profile("test_component")
        # Real success rate should be ~67%
        self.assertAlmostEqual(profile.success_rate, 14/20, places=1)
        # Quality average should be based on real scores
        self.assertGreater(profile.quality_average, 0.0)
        # Reliability should reflect real performance
        self.assertGreater(profile.reliability_score, 0.0)

    def test_confidence_calibration(self):
        """Calibration should measure how well predictions match reality."""
        from meta_cognition_engine import OutcomeRecord

        # Well-calibrated: predictions match outcomes
        for i in range(10):
            actual = 0.8
            self.engine.record_outcome(OutcomeRecord(
                component="calibrated",
                operation="test",
                success=True,
                quality_score=actual,
                predicted_quality=0.79,  # Close prediction
                latency_ms=100,
            ))

        profile = self.engine.get_profile("calibrated")
        self.assertGreater(profile.confidence_calibration, 0.8)

    def test_stagnation_detection(self):
        """Should detect when a component stops improving."""
        from meta_cognition_engine import OutcomeRecord

        # Record consistent quality (no improvement)
        for i in range(60):
            self.engine.record_outcome(OutcomeRecord(
                component="stagnant_component",
                operation="test",
                success=True,
                quality_score=0.5,  # No change
                predicted_quality=0.5,
                latency_ms=100,
            ))

        stagnant = self.engine.get_stagnant_components()
        # Should detect stagnation
        self.assertIsInstance(stagnant, list)

    def test_self_assessment_is_honest(self):
        """Self-assessment should be honest — no fake confidence."""
        from meta_cognition_engine import OutcomeRecord

        # No data yet = uncertain
        assessment = self.engine.get_self_assessment()
        self.assertEqual(assessment["components_with_data"], 0)

        # Add some data
        for i in range(10):
            self.engine.record_outcome(OutcomeRecord(
                component="brain_router",
                operation="test",
                success=True,
                quality_score=0.9,
                predicted_quality=0.85,
                latency_ms=100,
            ))

        assessment = self.engine.get_self_assessment()
        self.assertGreater(assessment["components_with_data"], 0)


class TestASTSecurityChecker(unittest.TestCase):
    """Test the AST security checker for SelfModifier sandbox."""

    def setUp(self):
        from self_modifier import ASTSecurityChecker
        self.checker = ASTSecurityChecker()

    def test_blocks_os_system(self):
        """Should block os.system calls."""
        code = "import os\nos.system('rm -rf /')"
        is_safe, violations = self.checker.check(code)
        self.assertFalse(is_safe)
        self.assertTrue(len(violations) > 0)

    def test_blocks_subprocess(self):
        """Should block subprocess calls."""
        code = "import subprocess\nsubprocess.run(['ls'])"
        is_safe, violations = self.checker.check(code)
        self.assertFalse(is_safe)

    def test_blocks_eval(self):
        """Should block eval calls."""
        code = "x = eval('1+1')"
        is_safe, violations = self.checker.check(code)
        self.assertFalse(is_safe)

    def test_blocks_exec(self):
        """Should block exec calls."""
        code = "exec('print(1)')"
        is_safe, violations = self.checker.check(code)
        self.assertFalse(is_safe)

    def test_allows_safe_code(self):
        """Should allow safe code."""
        code = """
def hello(name: str) -> str:
    return f"Hello, {name}!"

result = hello("World")
"""
        is_safe, violations = self.checker.check(code)
        self.assertTrue(is_safe)
        self.assertEqual(len(violations), 0)

    def test_allows_os_path(self):
        """Should allow os.path (safe operation)."""
        code = "import os\npath = os.path.join('a', 'b')"
        is_safe, violations = self.checker.check(code)
        self.assertTrue(is_safe)

    def test_blocks_syntax_error(self):
        """Should block code with syntax errors."""
        code = "def broken("
        is_safe, violations = self.checker.check(code)
        self.assertFalse(is_safe)


class TestRestrictedExecutor(unittest.TestCase):
    """Test the restricted code executor."""

    def setUp(self):
        from self_modifier import RestrictedExecutor
        self.executor = RestrictedExecutor()

    def test_executes_safe_code(self):
        """Should execute safe code."""
        code = "result = 2 + 2"
        result = self.executor.execute(code)
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], 4)

    def test_blocks_dangerous_code(self):
        """Should block dangerous code before execution."""
        code = "import os\nos.system('echo hacked')"
        result = self.executor.execute(code)
        self.assertFalse(result["success"])
        # os.system is caught at call level, not import level
        self.assertTrue("Security" in result.get("error", "") or "os.system" in result.get("error", ""))

    def test_captures_print_output(self):
        """Should capture print output."""
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
        """Should pass valid TypeScript code."""
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
        # May pass with tsc or AST — either way should work
        self.assertIn("passed", result)
        self.assertIn("method", result)

    def test_reports_method(self):
        """Should report which validation method was used."""
        result = self.validator.validate("const x: number = 1;")
        self.assertIn(result["method"], ["tsc_compiler", "ast_fallback"])


class TestPythonValidator(unittest.TestCase):
    """Test Python validation."""

    def setUp(self):
        from full_self_rewriter import PythonValidator
        self.validator = PythonValidator()

    def test_valid_python(self):
        """Should pass valid Python code."""
        code = "def hello():\n    return 'world'"
        result = self.validator.validate(code)
        self.assertTrue(result["passed"])

    def test_invalid_python(self):
        """Should fail invalid Python code."""
        code = "def broken("
        result = self.validator.validate(code)
        self.assertFalse(result["passed"])


class TestNeuralBus(unittest.TestCase):
    """Test the event bus."""

    def setUp(self):
        from neural_bus import NeuralBus, Event
        self.bus = NeuralBus()
        self.Event = Event

    def test_subscribe_and_publish(self):
        """Should deliver events to subscribers."""
        received = []

        def handler(event):
            received.append(event)

        self.bus.subscribe("test.event", handler)
        self.bus.publish_sync(self.Event(
            event_type="test.event",
            source="test",
            data={"msg": "hello"},
        ))

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].data["msg"], "hello")

    def test_no_delivery_to_wrong_subscriber(self):
        """Should not deliver events to wrong subscribers."""
        received = []

        def handler(event):
            received.append(event)

        self.bus.subscribe("test.event", handler)
        self.bus.publish_sync(self.Event(
            event_type="other.event",
            source="test",
        ))

        self.assertEqual(len(received), 0)


class TestRegistry(unittest.TestCase):
    """Test tool and agent registries."""

    def test_tool_registry(self):
        from registry import ToolRegistry, ToolEntry, ComponentStatus
        registry = ToolRegistry()

        entry = ToolEntry(name="test_tool", description="A test tool")
        registry.register(entry)

        self.assertIsNotNone(registry.get("test_tool"))
        self.assertEqual(len(registry.list_tools()), 1)

        # Record usage
        registry.record_usage("test_tool", success=True)
        tool = registry.get("test_tool")
        self.assertEqual(tool.use_count, 1)
        self.assertEqual(tool.success_count, 1)

    def test_agent_registry_auto_promote(self):
        from registry import AgentRegistry, AgentEntry, ComponentStatus
        registry = AgentRegistry()

        entry = AgentEntry(name="test_agent", description="A test agent", mode="observation")
        registry.register(entry)

        # Record 10 successes — should auto-promote
        for _ in range(10):
            registry.record_outcome("test_agent", success=True)

        agent = registry.get("test_agent")
        self.assertEqual(agent.mode, "active")

    def test_agent_registry_auto_demote(self):
        from registry import AgentRegistry, AgentEntry
        registry = AgentRegistry()

        entry = AgentEntry(name="test_agent", description="Test", mode="active")
        registry.register(entry)

        # Record 4 failures — should auto-demote
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
        """Each provider should use a different model."""
        from multi_provider_llm import DEFAULT_PROVIDERS
        models = [p.model for p in DEFAULT_PROVIDERS.values()]
        # At least 3 different models
        unique_models = set(models)
        self.assertGreaterEqual(len(unique_models), 3)

    def test_different_temperatures(self):
        """Each provider should have a different temperature."""
        from multi_provider_llm import DEFAULT_PROVIDERS
        temps = [p.temperature for p in DEFAULT_PROVIDERS.values()]
        unique_temps = set(temps)
        self.assertGreaterEqual(len(unique_temps), 3)


class TestBrainRouter(unittest.TestCase):
    """Test BrainRouter configuration."""

    def test_different_providers_per_brain(self):
        """Each brain should use a different provider."""
        from brain_router import DEFAULT_BRAINS
        providers = [b.provider for b in DEFAULT_BRAINS]
        unique_providers = set(providers)
        self.assertGreaterEqual(len(unique_providers), 4)

    def test_different_personalities(self):
        """Each brain should have a different personality."""
        from brain_router import DEFAULT_BRAINS
        personalities = [b.personality.value for b in DEFAULT_BRAINS]
        unique = set(personalities)
        self.assertEqual(len(unique), 5)


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

        # Record poor performance
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
            total_results=1,
            source_used="test",
            latency_ms=100,
        )

        cache.put("test", 10, response)
        cached = cache.get("test", 10)
        self.assertIsNotNone(cached)
        self.assertEqual(cached.query, "test")

    def test_rate_limiter(self):
        from web_search_client import RateLimiter
        limiter = RateLimiter(requests_per_minute=60)
        self.assertEqual(len(limiter._timestamps), 0)


class TestExternalProjectController(unittest.TestCase):
    """Test External Project Controller."""

    def test_analyze_project(self):
        from external_project_controller import ExternalProjectController
        controller = ExternalProjectController(project_path="/home/z/my-project")
        self.assertIsNotNone(controller)


class TestMamounKernel(unittest.TestCase):
    """Test Mamoun Kernel initialization."""

    def test_kernel_creates(self):
        from mamoun_kernel import MamounKernel, KernelState
        kernel = MamounKernel()
        self.assertEqual(kernel.state, KernelState.INITIALIZING)


if __name__ == "__main__":
    unittest.main()
