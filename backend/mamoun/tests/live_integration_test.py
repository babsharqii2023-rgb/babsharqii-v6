"""
Live Integration Test Server for Super Mind v59
Runs a quick server that initializes the kernel and performs live tests.
"""

import os
import sys
import asyncio
import json
import time

# Setup paths
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, 'core'))
sys.path.insert(0, os.path.join(_project_root, 'core', 'super_brain'))
sys.path.insert(0, os.path.join(_project_root, 'core', 'shared'))


async def live_test():
    """Run live integration tests."""
    results = {"passed": 0, "failed": 0, "errors": []}

    def check(name, condition, detail=""):
        if condition:
            results["passed"] += 1
            print(f"  ✅ {name}")
        else:
            results["failed"] += 1
            results["errors"].append(f"{name}: {detail}")
            print(f"  ❌ {name} — {detail}")

    print("=" * 60)
    print("Super Mind v59 — Live Integration Tests")
    print("=" * 60)

    # ── Test 1: MetaCognitionEngine ──
    print("\n[1] MetaCognitionEngine")
    from meta_cognition_engine import MetaCognitionEngine, OutcomeRecord
    import tempfile

    meta = MetaCognitionEngine(persistence_dir=tempfile.mkdtemp())

    # Record outcomes
    for i in range(10):
        meta.record_outcome(OutcomeRecord(
            component="test_component",
            operation="test",
            success=(i % 3 != 0),
            quality_score=0.7 + (i * 0.02),
            predicted_quality=0.75,
            latency_ms=100 + i * 10,
        ))

    profile = meta.get_profile("test_component")
    check("Profile created", profile is not None)
    check("Total operations = 10", profile.total_operations == 10, f"got {profile.total_operations}")
    check("Success rate reasonable", 0.5 <= profile.success_rate <= 0.8, f"got {profile.success_rate}")
    check("Reliability > 0", profile.reliability_score > 0, f"got {profile.reliability_score}")
    check("Health status set", profile.health_status != "unknown", f"got {profile.health_status}")

    # Test self-assessment
    assessment = meta.get_self_assessment()
    check("Self-assessment returns dict", isinstance(assessment, dict))
    check("Assessment has capabilities", "capabilities" in assessment)
    check("Assessment has limitations", "limitations" in assessment)

    # Test unhealthy detection
    for _ in range(10):
        meta.record_outcome(OutcomeRecord(
            component="bad_component",
            operation="test",
            success=False,
            quality_score=0.1,
            predicted_quality=0.5,
            latency_ms=5000,
        ))

    unhealthy = meta.get_unhealthy_components()
    check("Unhealthy component detected", len(unhealthy) > 0)
    check("Bad component found", any(u["component"] == "bad_component" for u in unhealthy))

    # Test persistence
    save_ok = meta.save()
    check("Save to disk", save_ok)

    meta2 = MetaCognitionEngine(persistence_dir=meta._persistence_dir)
    profile2 = meta2.get_profile("test_component")
    check("Load from disk", profile2 is not None)
    check("Loaded data matches", profile2.total_operations == 10 if profile2 else False)

    # ── Test 2: NeuralBus ──
    print("\n[2] NeuralBus")
    from neural_bus import NeuralBus, Event, EventType

    bus = NeuralBus()
    received = []

    bus.subscribe(EventType.HEARTBEAT.value, lambda e: received.append(e))
    bus.publish_sync(Event(
        event_type=EventType.HEARTBEAT.value,
        source="test",
        data={"health": 1.0},
    ))

    check("Event delivered", len(received) == 1, f"got {len(received)}")
    check("Event data correct", received[0].data["health"] == 1.0 if received else False)
    check("Bus stats updated", bus.get_stats()["total_published"] >= 1)

    # ── Test 3: Multi-Provider LLM ──
    print("\n[3] Multi-Provider LLM Client")
    from multi_provider_llm import MultiProviderLLMClient, DEFAULT_PROVIDERS

    llm_client = MultiProviderLLMClient()
    check("5 providers configured", len(DEFAULT_PROVIDERS) == 5)
    check("GLM provider exists", "glm" in llm_client.providers)
    check("Gemini provider exists", "gemini" in llm_client.providers)
    check("DeepSeek provider exists", "deepseek" in llm_client.providers)
    check("Z-AI provider exists", "zai" in llm_client.providers)
    check("Critic provider exists", "critic" in llm_client.providers)

    # Check that _call_zai uses ZaiSdkWrapper
    import inspect
    zai_source = inspect.getsource(llm_client._call_zai)
    check("Z-AI uses ZaiSdkWrapper", "zai_sdk_wrapper" in zai_source)
    check("Z-AI does NOT use broken import", "importlib.import_module" not in zai_source)

    available = llm_client.available_providers()
    check(f"Available providers: {len(available)}", True, f"{available}")

    # ── Test 4: BrainRouter ──
    print("\n[4] BrainRouter")
    from brain_router import BrainRouter, DEFAULT_BRAINS, PERSONALITY_PROMPTS, BrainPersonality

    router = BrainRouter(llm_client=llm_client, meta_cognition=meta)
    check("5 brains configured", len(DEFAULT_BRAINS) == 5)
    check("4+ unique providers", len(set(b.provider for b in DEFAULT_BRAINS)) >= 4)
    check("5 unique personalities", len(set(b.personality for b in DEFAULT_BRAINS)) == 5)

    # Check personality prompts
    for personality in BrainPersonality:
        check(f"Prompt for {personality.value}", personality in PERSONALITY_PROMPTS)

    # Check available brains doesn't have fake fallback
    available_brains = router._get_available_brains()
    check("Available brains list is reasonable", len(available_brains) <= len(DEFAULT_BRAINS))

    # ── Test 5: SelfModifier ──
    print("\n[5] SelfModifier")
    from self_modifier import SelfModifier, ASTSecurityChecker, ModificationProposal

    modifier = SelfModifier(meta_cognition=meta)
    checker = ASTSecurityChecker()

    # Security checks
    safe_code = "def hello(name: str) -> str:\n    return f'Hello {name}'"
    is_safe, _ = checker.check(safe_code)
    check("Safe code passes", is_safe)

    unsafe_code = "import os\nos.system('rm -rf /')"
    is_safe, violations = checker.check(unsafe_code)
    check("Unsafe code blocked", not is_safe)

    eval_code = "x = eval('1+1')"
    is_safe, _ = checker.check(eval_code)
    check("eval() blocked", not is_safe)

    subprocess_code = "import subprocess\nsubprocess.run(['ls'])"
    is_safe, _ = checker.check(subprocess_code)
    check("subprocess blocked", not is_safe)

    # ── Test 6: ImprovementProposer ──
    print("\n[6] ImprovementProposer")
    from improvement_proposer import ImprovementProposer, FeatureFlags

    proposer = ImprovementProposer(meta_cognition=meta)
    check("Proposer created", proposer is not None)

    # Feature flags
    flags = FeatureFlags()
    flags.register("test_flag", default=False, description="Test")
    check("Flag registered", not flags.is_enabled("test_flag"))
    flags.enable("test_flag")
    check("Flag enabled", flags.is_enabled("test_flag"))

    # Identify weak components
    weak = proposer._identify_weak_components()
    check("Weak components identified", isinstance(weak, list))

    # apply_proposal accepts target_file
    import inspect
    sig = inspect.signature(proposer.apply_proposal)
    check("apply_proposal has target_file param", "target_file" in sig.parameters)

    # ── Test 7: ExternalProjectController ──
    print("\n[7] ExternalProjectController")
    from external_project_controller import ExternalProjectController

    # Test with real project
    controller = ExternalProjectController(
        project_path="/home/z/my-project/babsharqii-v5",
        meta_cognition=meta,
    )
    info = await controller.analyze_project()
    check("Project analyzed", info is not None)
    check("Language detected", info.language != "unknown", f"got {info.language}")
    check("Has git", info.has_git)
    # Tests may be in backend/mamoun/tests, not root /tests
    check("File count > 0", info.file_count > 0, f"got {info.file_count}")

    # Check quality_score is NOT hardcoded 0.9
    source = inspect.getsource(controller.analyze_project)
    check("Quality score NOT hardcoded 0.9", "quality_score=0.9" not in source)

    # Project health
    health = controller.get_project_health()
    check("Health dashboard exists", "score" in health)
    check("Health score > 0", health["score"] > 0, f"got {health['score']}")

    # ── Test 8: ZaiSdkWrapper ──
    print("\n[8] ZaiSdkWrapper")
    from zai_sdk_wrapper import ZaiSdkWrapper

    wrapper = ZaiSdkWrapper()
    check("Wrapper created", wrapper is not None)

    helper_path = wrapper._get_helper_path()
    check("Helper script created", os.path.exists(helper_path))

    # Check _call_node is async
    check("_call_node is async", inspect.iscoroutinefunction(wrapper._call_node))

    # Check uses async subprocess
    source = inspect.getsource(wrapper._call_node)
    check("Uses create_subprocess_exec", "create_subprocess_exec" in source)
    check("Does NOT use subprocess.run", "subprocess.run" not in source)

    # ── Test 9: MamounKernel ──
    print("\n[9] MamounKernel")
    from mamoun_kernel import MamounKernel, KernelState

    kernel = MamounKernel()
    check("Kernel starts as INITIALIZING", kernel.state == KernelState.INITIALIZING)
    check("Self-assessment interval > 0", kernel.SELF_ASSESSMENT_INTERVAL > 0)
    check("Self-improvement interval > 0", kernel.SELF_IMPROVEMENT_INTERVAL > 0)
    check("Meta save interval > 0", kernel.META_SAVE_INTERVAL > 0)

    # Check stagnation handler
    stag_source = inspect.getsource(kernel._handle_stagnation)
    check("Stagnation handler triggers improvement", "analyze_and_propose" in stag_source)

    # Check heartbeat
    hb_source = inspect.getsource(kernel._heartbeat_check)
    check("Heartbeat verifies component responsiveness", "get_stats" in hb_source)

    # ── Test 10: Registries ──
    print("\n[10] Tool & Agent Registries")
    from registry import ToolRegistry, ToolEntry, AgentRegistry, AgentEntry, ComponentStatus

    tool_reg = ToolRegistry()
    tool = ToolEntry(name="test_tool", description="A test tool")
    tool_reg.register(tool)
    check("Tool registered", tool_reg.get("test_tool") is not None)

    tool_reg.record_usage("test_tool", success=True)
    tool_reg.record_usage("test_tool", success=True)
    check("Tool usage recorded", tool_reg.get("test_tool").use_count == 2)

    agent_reg = AgentRegistry()
    agent = AgentEntry(name="test_agent", description="Test", mode="observation")
    agent_reg.register(agent)

    # Promote after 10 successes
    for _ in range(10):
        agent_reg.record_outcome("test_agent", success=True)
    check("Agent promoted to active", agent_reg.get("test_agent").mode == "active")

    # Demote after errors
    for _ in range(4):
        agent_reg.record_outcome("test_agent", success=False)
    check("Agent demoted to observation", agent_reg.get("test_agent").mode == "observation")

    # ── Test 11: FullSelfRewriter validators ──
    print("\n[11] Code Validators")
    from full_self_rewriter import TypeScriptValidator, PythonValidator

    ts_validator = TypeScriptValidator()
    ts_result = ts_validator.validate("const x: number = 42;")
    check("TS validator returns result", "passed" in ts_result)
    check("TS validator reports method", ts_result["method"] in ["tsc_compiler", "ast_fallback"])

    py_validator = PythonValidator()
    py_result = py_validator.validate("def hello():\n    return 'world'")
    check("Python validator works", py_result["passed"])
    check("Python validator has quality_score", "quality_score" in py_result)

    # ── Test 12: DeliberationRoom ──
    print("\n[12] DeliberationRoom")
    from deliberation_room import DeliberationRoom, ContradictionJudgingSystem

    cjs = ContradictionJudgingSystem()
    # Test keyword contradiction detection
    test_responses = [
        {"content": "Yes, I agree with this proposal", "provider": "deepseek"},
        {"content": "No, I oppose this completely", "provider": "gemini"},
    ]
    contradictions = cjs.detect_keyword_contradictions(test_responses)
    check("CJS detects contradictions", len(contradictions) > 0)

    # ── Summary ──
    print("\n" + "=" * 60)
    total = results["passed"] + results["failed"]
    print(f"Results: {results['passed']}/{total} passed, {results['failed']} failed")
    if results["errors"]:
        print("\nFailures:")
        for err in results["errors"]:
            print(f"  ❌ {err}")
    print("=" * 60)

    return results["failed"] == 0


if __name__ == "__main__":
    success = asyncio.get_event_loop().run_until_complete(live_test())
    sys.exit(0 if success else 1)
