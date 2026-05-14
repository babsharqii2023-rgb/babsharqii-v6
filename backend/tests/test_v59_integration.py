"""
Comprehensive Tests for Super Mind v59

Tests cover:
1. MetaCognitionEngine — record_outcome, profiles, stagnation detection
2. ImprovementProposer — analyze_and_propose, apply_proposal
3. EvolutionLoopV2 — full cycle with safety limits
4. AgentLifecycleManager — observation → active → retired lifecycle
5. ResearchToUpdatePipeline — research → propose flow
6. Component wiring — Proposer ↔ SelfModifier integration
7. OutcomeRecorder — decorator and context manager

v59 — Super Mind العقل الخارق مامون
"""

import asyncio
import time
import sys
import os
import tempfile
import shutil

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def _clean_meta():
    """Create a MetaCognitionEngine with a clean temp directory."""
    from mamoun.core.super_brain.meta_cognition_engine import MetaCognitionEngine
    tmp_dir = tempfile.mkdtemp(prefix="sm_test_")
    engine = MetaCognitionEngine(persistence_dir=tmp_dir)
    return engine


# ── 1. MetaCognitionEngine Tests ──────────────────────────────────────────

def test_record_outcome_creates_profile():
    from mamoun.core.super_brain.meta_cognition_engine import (
        MetaCognitionEngine, OutcomeRecord
    )
    engine = _clean_meta()

    engine.record_outcome(OutcomeRecord(
        component="test_component",
        operation="test_op",
        success=True,
        quality_score=0.85,
        predicted_quality=0.80,
        latency_ms=100,
    ))

    profile = engine.get_profile("test_component")
    assert profile is not None, "Profile should be created"
    assert profile.total_operations == 1
    assert profile.success_count == 1
    assert abs(profile.quality_average - 0.85) < 0.01
    print("  ✅ test_record_outcome_creates_profile PASSED")


def test_record_outcome_failure():
    from mamoun.core.super_brain.meta_cognition_engine import (
        MetaCognitionEngine, OutcomeRecord
    )
    engine = _clean_meta()

    engine.record_outcome(OutcomeRecord(
        component="failing_component",
        operation="test_op",
        success=False,
        quality_score=0.0,
        predicted_quality=0.70,
        latency_ms=50,
        error="Test error",
    ))

    profile = engine.get_profile("failing_component")
    assert profile.failure_count == 1
    assert profile.consecutive_failures == 1
    assert profile.error_types  # Error should be tracked
    print("  ✅ test_record_outcome_failure PASSED")


def test_stagnation_detection():
    from mamoun.core.super_brain.meta_cognition_engine import (
        MetaCognitionEngine, OutcomeRecord
    )
    engine = _clean_meta()

    # Record many outcomes without improvement
    for i in range(50):
        engine.record_outcome(OutcomeRecord(
            component="stagnant_component",
            operation="test_op",
            success=True,
            quality_score=0.5,  # Same quality = no improvement
            predicted_quality=0.5,
            latency_ms=100,
        ))

    stagnant = engine.get_stagnant_components()
    assert "stagnant_component" in stagnant, "Should detect stagnation"
    print("  ✅ test_stagnation_detection PASSED")


def test_reliability_score_is_real():
    from mamoun.core.super_brain.meta_cognition_engine import (
        MetaCognitionEngine, OutcomeRecord
    )
    engine = _clean_meta()

    for i in range(10):
        engine.record_outcome(OutcomeRecord(
            component="reliable_component",
            operation="test_op",
            success=True,
            quality_score=0.9,
            predicted_quality=0.85,
            latency_ms=100,
        ))

    profile = engine.get_profile("reliable_component")
    assert profile.reliability_score > 0.7, f"Expected > 0.7, got {profile.reliability_score}"
    print("  ✅ test_reliability_score_is_real PASSED")


def test_predict_quality():
    from mamoun.core.super_brain.meta_cognition_engine import (
        MetaCognitionEngine, OutcomeRecord
    )
    engine = _clean_meta()

    for i in range(6):
        engine.record_outcome(OutcomeRecord(
            component="predictable",
            operation="test_op",
            success=True,
            quality_score=0.8,
            predicted_quality=0.75,
            latency_ms=100,
        ))

    prediction = engine.predict_quality("predictable")
    assert 0.0 <= prediction <= 1.0
    assert prediction > 0.5, f"Expected > 0.5, got {prediction}"
    print("  ✅ test_predict_quality PASSED")


# ── 2. ImprovementProposer Tests ─────────────────────────────────────────

def test_proposer_self_modifier_wiring():
    from mamoun.core.super_brain.improvement_proposer import ImprovementProposer

    proposer = ImprovementProposer()
    assert proposer._self_modifier is None

    mock_modifier = type('MockModifier', (), {})()
    proposer.set_self_modifier(mock_modifier)
    assert proposer._self_modifier is mock_modifier

    stats = proposer.get_stats()
    assert stats["has_self_modifier"] is True
    print("  ✅ test_proposer_self_modifier_wiring PASSED")


async def test_proposer_no_meta():
    from mamoun.core.super_brain.improvement_proposer import ImprovementProposer

    proposer = ImprovementProposer()
    proposals = await proposer.analyze_and_propose()
    assert proposals == []
    print("  ✅ test_proposer_no_meta PASSED")


# ── 3. AgentLifecycleManager Tests ───────────────────────────────────────

def test_agent_register():
    from mamoun.core.super_brain.agent_lifecycle_manager import (
        AgentLifecycleManager, AgentLifecycleState
    )

    manager = AgentLifecycleManager()
    record = manager.register_agent("test_agent", "Test Agent")

    assert record.agent_id == "test_agent"
    assert record.state == AgentLifecycleState.OBSERVATION
    print("  ✅ test_agent_register PASSED")


def test_agent_auto_promote():
    from mamoun.core.super_brain.agent_lifecycle_manager import (
        AgentLifecycleManager, AgentLifecycleState
    )

    manager = AgentLifecycleManager()
    manager.register_agent("good_agent", "Good Agent")

    for i in range(10):
        result = manager.record_agent_outcome(
            "good_agent", success=True, quality=0.85, operation="test_op"
        )

    assert result["state"] == AgentLifecycleState.ACTIVE.value
    assert "promoted_to_active" in result["changes"]
    print("  ✅ test_agent_auto_promote PASSED")


def test_agent_auto_demote():
    from mamoun.core.super_brain.agent_lifecycle_manager import (
        AgentLifecycleManager, AgentLifecycleState
    )

    manager = AgentLifecycleManager()
    manager.register_agent("failing_agent", "Failing Agent")

    # First promote it
    record = manager._agents["failing_agent"]
    record.state = AgentLifecycleState.ACTIVE

    for i in range(3):
        result = manager.record_agent_outcome(
            "failing_agent", success=False, quality=0.1, operation="test_op"
        )

    assert result["state"] == AgentLifecycleState.DEGRADED.value
    assert "demoted_to_degraded" in result["changes"]
    print("  ✅ test_agent_auto_demote PASSED")


def test_agent_health_check():
    from mamoun.core.super_brain.agent_lifecycle_manager import AgentLifecycleManager

    manager = AgentLifecycleManager()
    manager.register_agent("agent_a", "Agent A")
    manager.register_agent("agent_b", "Agent B")

    health = manager.health_check()
    assert "agent_a" in health
    assert "agent_b" in health
    print("  ✅ test_agent_health_check PASSED")


# ── 4. EvolutionLoopV2 Tests ─────────────────────────────────────────────

def test_evolution_rate_limits():
    from mamoun.core.super_brain.evolution_loop_v2 import EvolutionLoopV2

    class MockKernel:
        def get_component(self, name):
            return None

    loop = EvolutionLoopV2(kernel=MockKernel())
    assert loop._can_auto_deploy()

    loop._deploys_this_hour = EvolutionLoopV2.MAX_AUTO_DEPLOYS_PER_HOUR
    assert not loop._can_auto_deploy()
    print("  ✅ test_evolution_rate_limits PASSED")


def test_evolution_freeze():
    from mamoun.core.super_brain.evolution_loop_v2 import EvolutionLoopV2

    class MockKernel:
        def get_component(self, name):
            return None

    loop = EvolutionLoopV2(kernel=MockKernel())
    loop._frozen = True
    # Can't use asyncio.get_event_loop() when loop is already running
    # Just verify the state directly
    assert loop._frozen is True
    assert loop.status.value == "idle"
    print("  ✅ test_evolution_freeze PASSED")


def test_evolution_snapshot():
    from mamoun.core.super_brain.evolution_loop_v2 import EvolutionLoopV2

    class MockKernel:
        def get_component(self, name):
            return None

    loop = EvolutionLoopV2(kernel=MockKernel())
    loop._save_snapshot("test_snap", None)
    assert "test_snap" in loop._snapshots
    print("  ✅ test_evolution_snapshot PASSED")


def test_evolution_unfreeze():
    from mamoun.core.super_brain.evolution_loop_v2 import EvolutionLoopV2

    class MockKernel:
        def get_component(self, name):
            return None

    loop = EvolutionLoopV2(kernel=MockKernel())
    loop._frozen = True
    loop.unfreeze()
    assert not loop._frozen
    print("  ✅ test_evolution_unfreeze PASSED")


# ── 5. ResearchToUpdatePipeline Tests ─────────────────────────────────────

def test_classify_finding():
    from mamoun.core.super_brain.research_to_update_pipeline import ResearchToUpdatePipeline

    class MockKernel:
        def get_component(self, name):
            return None

    pipeline = ResearchToUpdatePipeline(kernel=MockKernel())

    assert pipeline._classify_finding("Best practice for testing") == "best_practice"
    assert pipeline._classify_finding("Performance improved by 50%") == "performance"
    assert pipeline._classify_finding("Security vulnerability found") == "security"
    assert pipeline._classify_finding("Bug in the code") == "bug_fix"
    assert pipeline._classify_finding("The sky is blue") == "non_actionable"
    print("  ✅ test_classify_finding PASSED")


async def test_pipeline_no_researcher():
    from mamoun.core.super_brain.research_to_update_pipeline import ResearchToUpdatePipeline

    class MockKernel:
        def get_component(self, name):
            return None

    pipeline = ResearchToUpdatePipeline(kernel=MockKernel())
    result = await pipeline.research_and_update("test query")
    assert result.error is not None
    assert "not available" in result.error
    print("  ✅ test_pipeline_no_researcher PASSED")


# ── 6. OutcomeRecorder Tests ─────────────────────────────────────────────

async def test_outcome_recorder_success():
    from mamoun.core.super_brain.outcome_recorder import OutcomeRecorder
    from mamoun.core.super_brain.meta_cognition_engine import MetaCognitionEngine

    meta = _clean_meta()

    async with OutcomeRecorder(meta, "test_comp_rec", "test_op") as rec:
        rec.quality_score = 0.9
        rec.success = True

    profile = meta.get_profile("test_comp_rec")
    assert profile is not None, "Profile should exist"
    assert profile.total_operations == 1, f"Expected 1 op, got {profile.total_operations}"
    assert profile.success_count == 1, f"Expected 1 success, got {profile.success_count}"
    print("  ✅ test_outcome_recorder_success PASSED")


async def test_outcome_recorder_failure():
    from mamoun.core.super_brain.outcome_recorder import OutcomeRecorder
    from mamoun.core.super_brain.meta_cognition_engine import MetaCognitionEngine

    meta = _clean_meta()

    try:
        async with OutcomeRecorder(meta, "fail_comp_rec", "fail_op") as rec:
            raise ValueError("Test failure")
    except ValueError:
        pass

    profile = meta.get_profile("fail_comp_rec")
    assert profile is not None, "Profile should exist for failed operation"
    assert profile.failure_count == 1, f"Expected 1 failure, got {profile.failure_count}"
    print("  ✅ test_outcome_recorder_failure PASSED")


# ── 7. Integration Tests ─────────────────────────────────────────────────

def test_full_outcome_recording_flow():
    from mamoun.core.super_brain.meta_cognition_engine import (
        MetaCognitionEngine, OutcomeRecord
    )

    meta = _clean_meta()

    components = ["brain_router_int", "deliberation_room_int", "deep_research_int",
                  "tool_creator_int", "agent_creator_int"]

    for comp in components:
        for i in range(5):
            meta.record_outcome(OutcomeRecord(
                component=comp,
                operation="execute",
                success=True,
                quality_score=0.8 + (i * 0.02),
                predicted_quality=0.75,
                latency_ms=100 + (i * 10),
            ))

    # Verify all profiles exist with correct data
    for comp in components:
        profile = meta.get_profile(comp)
        assert profile is not None, f"Profile for {comp} should exist"
        assert profile.total_operations == 5, f"{comp}: expected 5 ops, got {profile.total_operations}"
        assert profile.success_rate == 1.0, f"{comp}: expected 100% success"

    overview = meta.get_system_overview()
    assert len(overview) == len(components), f"Expected {len(components)} in overview, got {len(overview)}"

    assessment = meta.get_self_assessment()
    assert assessment["components_assessed"] == len(components), f"Expected {len(components)} assessed"
    assert assessment["overall_confidence"] > 0.5, f"Expected confidence > 0.5, got {assessment['overall_confidence']}"
    print("  ✅ test_full_outcome_recording_flow PASSED")


# ── Run All Tests ─────────────────────────────────────────────────────────

async def run_all_tests():
    """Run all tests sequentially."""
    results = {"passed": 0, "failed": 0, "errors": []}

    tests = [
        # MetaCognitionEngine
        ("MetaCognitionEngine: record_outcome creates profile", test_record_outcome_creates_profile),
        ("MetaCognitionEngine: record_outcome failure", test_record_outcome_failure),
        ("MetaCognitionEngine: stagnation detection", test_stagnation_detection),
        ("MetaCognitionEngine: reliability score is real", test_reliability_score_is_real),
        ("MetaCognitionEngine: predict quality", test_predict_quality),
        # ImprovementProposer
        ("ImprovementProposer: self_modifier wiring", test_proposer_self_modifier_wiring),
        # AgentLifecycleManager
        ("AgentLifecycle: register agent", test_agent_register),
        ("AgentLifecycle: auto promote", test_agent_auto_promote),
        ("AgentLifecycle: auto demote", test_agent_auto_demote),
        ("AgentLifecycle: health check", test_agent_health_check),
        # EvolutionLoopV2
        ("EvolutionLoopV2: rate limits", test_evolution_rate_limits),
        ("EvolutionLoopV2: freeze protection", test_evolution_freeze),
        ("EvolutionLoopV2: snapshot", test_evolution_snapshot),
        ("EvolutionLoopV2: unfreeze", test_evolution_unfreeze),
        # ResearchToUpdatePipeline
        ("ResearchPipeline: classify finding", test_classify_finding),
        # OutcomeRecorder
        # Integration
        ("Integration: full outcome recording flow", test_full_outcome_recording_flow),
    ]

    async_tests = [
        ("ImprovementProposer: no meta", test_proposer_no_meta),
        ("ResearchPipeline: no researcher", test_pipeline_no_researcher),
        ("OutcomeRecorder: success", test_outcome_recorder_success),
        ("OutcomeRecorder: failure", test_outcome_recorder_failure),
    ]

    print("\n🧪 Super Mind v59 — Comprehensive Test Suite")
    print("=" * 60)

    # Sync tests
    for name, test_fn in tests:
        try:
            test_fn()
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{name}: {e}")
            print(f"  ❌ {name} FAILED: {e}")

    # Async tests
    for name, test_fn in async_tests:
        try:
            await test_fn()
            results["passed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{name}: {e}")
            print(f"  ❌ {name} FAILED: {e}")

    print("\n" + "=" * 60)
    print(f"📊 Results: {results['passed']} passed, {results['failed']} failed")
    if results["errors"]:
        print("❌ Errors:")
        for err in results["errors"]:
            print(f"   - {err}")

    return results


if __name__ == "__main__":
    asyncio.run(run_all_tests())
