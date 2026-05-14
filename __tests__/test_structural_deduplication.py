"""
Test Suite: Structural De-duplication Verification

These tests ensure that:
1. All core/ modules properly redirect to super_brain/ or shared/
2. No duplicate implementations exist outside legacy/
3. The legacy/ directory is not imported by any production code
4. All super_brain components are accessible via core/ package
5. Backward compatibility is maintained for old import paths
"""

import pytest
import importlib
import sys
import os
from pathlib import Path


# ── Test 1: core/ adapters delegate to super_brain/shared ───────────────

class TestAdapterRedirection:
    """Verify that core/ modules delegate to super_brain/ or shared/."""

    def test_metacognitive_engine_redirects_to_super_brain(self):
        """core/metacognitive_engine should import from super_brain."""
        from mamoun.core.metacognitive_engine import MetaCognitionEngine
        from mamoun.core.super_brain.meta_cognition_engine import MetaCognitionEngine as NewEngine
        assert MetaCognitionEngine is NewEngine, "metacognitive_engine should redirect to super_brain"

    def test_improvement_engine_redirects_to_super_brain(self):
        """core/improvement_engine should import from super_brain."""
        from mamoun.core.improvement_engine import ImprovementEngine
        from mamoun.core.super_brain.improvement_proposer import ImprovementProposer
        assert ImprovementEngine is ImprovementProposer, "improvement_engine should redirect to super_brain"

    def test_deep_research_engine_redirects_to_super_brain(self):
        """core/deep_research_engine should import from super_brain."""
        from mamoun.core.deep_research_engine import DeepResearchEngine
        from mamoun.core.super_brain.deep_research_engine import DeepResearchEngine as NewEngine
        assert DeepResearchEngine is NewEngine, "deep_research_engine should redirect to super_brain"

    def test_web_search_client_redirects_to_super_brain(self):
        """core/web_search_client should import from super_brain."""
        from mamoun.core.web_search_client import WebSearchClient
        from mamoun.core.super_brain.web_search_client import WebSearchClient as NewClient
        assert WebSearchClient is NewClient, "web_search_client should redirect to super_brain"


# ── Test 2: Backward-compatible API preservation ────────────────────────

class TestBackwardCompatibility:
    """Verify that old import paths still work."""

    def test_llm_client_import(self):
        """Old import: from mamoun.core.llm_client import LLMClient, get_llm_client"""
        from mamoun.core.llm_client import LLMClient, get_llm_client, LLMResponse, LLMMessage
        assert LLMClient is not None
        assert callable(get_llm_client)

    def test_mamoun_kernel_import(self):
        """Old import: from mamoun.core.mamoun_kernel import get_kernel"""
        from mamoun.core.mamoun_kernel import MamounKernel, get_kernel, GlobalWorkspace, ReflexionEngine, EscalationLadder
        assert MamounKernel is not None
        assert callable(get_kernel)
        assert GlobalWorkspace is not None
        assert ReflexionEngine is not None
        assert EscalationLadder is not None

    def test_neural_bus_import(self):
        """Old import: from mamoun.core.neural_bus import neural_bus"""
        from mamoun.core.neural_bus import NeuralBusCompat, get_neural_bus, SignalType, NeuralSignal
        assert NeuralBusCompat is not None
        assert callable(get_neural_bus)

    def test_self_modifier_import(self):
        """Old import: from mamoun.core.self_modifier import SelfModifier, get_self_modifier"""
        from mamoun.core.self_modifier import SelfModifier, get_self_modifier, ModificationProposal, ValidationResult
        assert SelfModifier is not None
        assert callable(get_self_modifier)

    def test_self_healing_import(self):
        """Old import: from mamoun.core.self_healing import self_healing"""
        from mamoun.core.self_healing import SelfHealingEngine, get_self_healing, HealingActionType
        assert SelfHealingEngine is not None
        assert callable(get_self_healing)

    def test_external_project_import(self):
        """Old import: from mamoun.core.external_project_controller import ExternalProjectController"""
        from mamoun.core.external_project_controller import ExternalProjectController
        assert ExternalProjectController is not None

    def test_experiential_rlhf_import(self):
        """Old import: from mamoun.core.experiential_rlhf import ExperientialRLHF"""
        from mamoun.core.experiential_rlhf import ExperientialRLHF
        assert ExperientialRLHF is not None


# ── Test 3: core/__init__.py exports super_brain components ─────────────

class TestInitExports:
    """Verify that core/__init__.py exports new super_brain components."""

    def test_meta_cognition_exported(self):
        """MetaCognitionEngine should be accessible via core package."""
        from mamoun.core import MetaCognitionEngine
        assert MetaCognitionEngine is not None

    def test_self_healing_bridge_exported(self):
        """SelfHealingBridge should be accessible via core package."""
        from mamoun.core import SelfHealingBridge
        assert SelfHealingBridge is not None

    def test_rlhf_bridge_exported(self):
        """RLHFBridge should be accessible via core package."""
        from mamoun.core import RLHFBridge
        assert RLHFBridge is not None

    def test_variant_archive_exported(self):
        """VariantArchive should be accessible via core package."""
        from mamoun.core import VariantArchive
        assert VariantArchive is not None

    def test_notification_engine_exported(self):
        """NotificationEngine should be accessible via core package."""
        from mamoun.core import NotificationEngine
        assert NotificationEngine is not None

    def test_health_monitor_exported(self):
        """HealthMonitor should be accessible via core package."""
        from mamoun.core import HealthMonitor
        assert HealthMonitor is not None

    def test_evolution_loop_v2_exported(self):
        """EvolutionLoopV2 should be accessible via core package."""
        from mamoun.core import EvolutionLoopV2
        assert EvolutionLoopV2 is not None

    def test_outcome_recorder_exported(self):
        """OutcomeRecorder should be accessible via core package."""
        from mamoun.core import OutcomeRecorder, record_outcome
        assert OutcomeRecorder is not None
        assert callable(record_outcome)


# ── Test 4: Legacy directory isolation ──────────────────────────────────

class TestLegacyIsolation:
    """Verify that legacy/ is properly isolated."""

    def test_legacy_not_in_production_imports(self):
        """No production code should import from core.legacy."""
        backend_path = Path(__file__).parent.parent / "backend" / "mamoun"
        if not backend_path.exists():
            pytest.skip("Backend path not found")

        # Check all Python files (excluding legacy/ itself)
        for py_file in backend_path.rglob("*.py"):
            if "legacy" in str(py_file):
                continue
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            assert "from mamoun.core.legacy" not in content, \
                f"{py_file} imports from core.legacy — forbidden!"
            assert "from .legacy" not in content, \
                f"{py_file} imports from .legacy — forbidden!"

    def test_legacy_has_old_files(self):
        """Legacy directory should contain the old implementations."""
        legacy_dir = Path(__file__).parent.parent / "backend" / "mamoun" / "core" / "legacy"
        if not legacy_dir.exists():
            pytest.skip("Legacy directory not found")

        expected_files = [
            "llm_client.py",
            "mamoun_kernel.py",
            "neural_bus.py",
            "self_modifier.py",
            "self_healing.py",
        ]
        actual_files = [f.name for f in legacy_dir.glob("*.py") if f.name != "__init__.py"]
        for expected in expected_files:
            assert expected in actual_files, f"Missing legacy file: {expected}"


# ── Test 5: No duplicate implementations ────────────────────────────────

class TestNoDuplicates:
    """Verify no duplicate implementations outside legacy/."""

    def test_no_duplicate_mamoun_kernel(self):
        """core/mamoun_kernel.py should be an adapter, not a full implementation."""
        kernel_path = Path(__file__).parent.parent / "backend" / "mamoun" / "core" / "mamoun_kernel.py"
        if not kernel_path.exists():
            pytest.skip("kernel file not found")
        content = kernel_path.read_text(encoding="utf-8")
        assert "BACKWARD-COMPATIBLE ADAPTER" in content or "ENHANCED ADAPTER" in content, \
            "core/mamoun_kernel.py should be an adapter, not a standalone implementation"

    def test_no_duplicate_llm_client(self):
        """core/llm_client.py should delegate to shared/multi_provider_llm.py."""
        llm_path = Path(__file__).parent.parent / "backend" / "mamoun" / "core" / "llm_client.py"
        if not llm_path.exists():
            pytest.skip("llm_client file not found")
        content = llm_path.read_text(encoding="utf-8")
        assert "BACKWARD-COMPATIBLE ADAPTER" in content, \
            "core/llm_client.py should be an adapter"
        assert "MultiProviderLLMClient" in content, \
            "core/llm_client.py should reference MultiProviderLLMClient"

    def test_no_duplicate_neural_bus(self):
        """core/neural_bus.py should delegate to shared/neural_bus.py."""
        bus_path = Path(__file__).parent.parent / "backend" / "mamoun" / "core" / "neural_bus.py"
        if not bus_path.exists():
            pytest.skip("neural_bus file not found")
        content = bus_path.read_text(encoding="utf-8")
        assert "BACKWARD-COMPATIBLE ADAPTER" in content, \
            "core/neural_bus.py should be an adapter"
        assert "shared.neural_bus" in content, \
            "core/neural_bus.py should reference shared/neural_bus"

    def test_no_three_copies_of_improvement(self):
        """There should NOT be three active copies of ImprovementProposer."""
        # Only core/improvement_engine.py (adapter) and super_brain/improvement_proposer.py (real)
        # The evolution/improvement_proposer.py should be moved to legacy
        backend_path = Path(__file__).parent.parent / "backend" / "mamoun"
        if not backend_path.exists():
            pytest.skip("Backend path not found")

        active_copies = 0
        for py_file in backend_path.rglob("improvement*.py"):
            if "legacy" in str(py_file) or "__pycache__" in str(py_file):
                continue
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            if "class ImprovementEngine" in content or "class ImprovementProposer" in content:
                if "ADAPTER" not in content and "redirected" not in content:
                    active_copies += 1
        # Should be at most 1 (the real one in super_brain)
        assert active_copies <= 1, \
            f"Found {active_copies} active copies of ImprovementProposer — should be 1"


# ── Test 6: Functional tests ────────────────────────────────────────────

class TestFunctional:
    """Verify that adapted components actually work."""

    def test_global_workspace_competition(self):
        """GlobalWorkspace should still work for brain competition."""
        from mamoun.core.mamoun_kernel import GlobalWorkspace
        workspace = GlobalWorkspace()
        proposals = {
            "brain_a": {"response": "إجابة أ", "confidence": 0.8, "relevance": 0.7},
            "brain_b": {"response": "إجابة ب", "confidence": 0.6, "relevance": 0.9},
        }
        entry = workspace.compete_and_broadcast(proposals, {})
        assert entry.winning_brain in ("brain_a", "brain_b")
        assert entry.confidence > 0

    def test_escalation_ladder(self):
        """EscalationLadder should still work."""
        from mamoun.core.mamoun_kernel import EscalationLadder, EscalationLevel
        level = EscalationLadder.determine_level(confidence=0.9, risk_level="low")
        assert level == EscalationLevel.DIRECT_RESPONSE

        level = EscalationLadder.determine_level(confidence=0.2, risk_level="high")
        assert level == EscalationLevel.HUMAN_APPROVAL

    def test_neural_bus_publish(self):
        """NeuralBus adapter should support old publish API."""
        from mamoun.core.neural_bus import get_neural_bus
        bus = get_neural_bus()
        signal = bus.publish("perception", "test", {"data": "test"})
        assert signal.signal_type == "perception"
        assert signal.source == "test"

    def test_self_healing_engine(self):
        """SelfHealingEngine should support old diagnose/heal API."""
        from mamoun.core.self_healing import SelfHealingEngine, HealingActionType
        engine = SelfHealingEngine()
        actions = engine.diagnose("test_component", "timeout error")
        assert len(actions) > 0
        assert any(a.action_type == HealingActionType.RETRY_WITH_BACKOFF for a in actions)

    def test_llm_client_adapter(self):
        """LLMClient adapter should have old API methods."""
        from mamoun.core.llm_client import LLMClient
        client = LLMClient()
        assert hasattr(client, 'chat')
        assert hasattr(client, 'think')
        assert hasattr(client, 'think_json')
        assert hasattr(client, 'available_providers')
        assert hasattr(client, 'get_health_report')

    def test_reflexion_engine(self):
        """ReflexionEngine should still work."""
        from mamoun.core.mamoun_kernel import ReflexionEngine
        engine = ReflexionEngine(llm_client=None)
        # Should use heuristic fallback without LLM
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            engine.review("test action", {"risk_level": "low"}, 0.95)
        )
        assert result["approved"] == True
        assert result["review_type"] == "fast_pass"
