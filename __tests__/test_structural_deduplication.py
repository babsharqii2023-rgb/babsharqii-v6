"""
Test Suite: Comprehensive Structural De-duplication Verification v61

These tests ensure that:
1. All core/ modules properly redirect to super_brain/ or shared/
2. No duplicate implementations exist outside legacy/
3. The legacy/ directory is not imported by any production code
4. All super_brain components are accessible via core/ package
5. Backward compatibility is maintained for old import paths
6. All adapters are thin (no duplicated logic)
7. Evolution modules properly delegate to super_brain
8. Functional tests verify the adapters actually work
"""

import pytest
import importlib
import sys
import os
import asyncio
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

    def test_self_modifier_redirects_to_super_brain(self):
        """core/self_modifier should import SelfModifier from super_brain."""
        from mamoun.core.self_modifier import SelfModifier
        from mamoun.core.super_brain.self_modifier import SelfModifier as NewSM
        assert SelfModifier is NewSM, "self_modifier should redirect to super_brain"

    def test_experiential_rlhf_redirects_to_super_brain(self):
        """core/experiential_rlhf should import from super_brain."""
        from mamoun.core.experiential_rlhf import ExperientialRLHF
        from mamoun.core.super_brain.rlhf_bridge import RLHFBridge
        assert ExperientialRLHF is RLHFBridge, "experiential_rlhf should redirect to super_brain"

    def test_evolution_loop_redirects_to_super_brain(self):
        """evolution/evolution_loop should import from super_brain."""
        from mamoun.evolution.evolution_loop import EvolutionLoop, EvolutionLoopV2
        assert EvolutionLoop is EvolutionLoopV2, "EvolutionLoop should be EvolutionLoopV2"


# ── Test 2: Backward-compatible API preservation ────────────────────────

class TestBackwardCompatibility:
    """Verify that old import paths still work."""

    def test_llm_client_import(self):
        from mamoun.core.llm_client import LLMClient, get_llm_client, LLMResponse, LLMMessage
        assert LLMClient is not None
        assert callable(get_llm_client)

    def test_mamoun_kernel_import(self):
        from mamoun.core.mamoun_kernel import MamounKernel, get_kernel, GlobalWorkspace, ReflexionEngine, EscalationLadder
        assert MamounKernel is not None
        assert callable(get_kernel)
        assert GlobalWorkspace is not None
        assert ReflexionEngine is not None
        assert EscalationLadder is not None

    def test_neural_bus_import(self):
        from mamoun.core.neural_bus import NeuralBusCompat, get_neural_bus, SignalType, NeuralSignal
        assert NeuralBusCompat is not None
        assert callable(get_neural_bus)

    def test_self_modifier_import(self):
        from mamoun.core.self_modifier import SelfModifier, get_self_modifier, ModificationProposal, SelfAnalysis
        assert SelfModifier is not None
        assert callable(get_self_modifier)

    def test_self_healing_import(self):
        from mamoun.core.self_healing import SelfHealingEngine, get_self_healing, HealingActionType
        assert SelfHealingEngine is not None
        assert callable(get_self_healing)

    def test_external_project_import(self):
        from mamoun.core.external_project_controller import ExternalProjectController
        assert ExternalProjectController is not None

    def test_evolution_loop_import(self):
        from mamoun.evolution.evolution_loop import EvolutionLoop
        assert EvolutionLoop is not None

    def test_evolution_agent_creator_import(self):
        from mamoun.evolution.agent_creator import AgentCreator, AgentSpecification
        assert AgentCreator is not None
        assert AgentSpecification is not None


# ── Test 3: core/__init__.py exports super_brain components ─────────────

class TestInitExports:
    """Verify that core/__init__.py exports new super_brain components."""

    def test_meta_cognition_exported(self):
        from mamoun.core import MetaCognitionEngine
        assert MetaCognitionEngine is not None

    def test_self_healing_bridge_exported(self):
        from mamoun.core import SelfHealingBridge
        assert SelfHealingBridge is not None

    def test_rlhf_bridge_exported(self):
        from mamoun.core import RLHFBridge
        assert RLHFBridge is not None

    def test_variant_archive_exported(self):
        from mamoun.core import VariantArchive
        assert VariantArchive is not None

    def test_notification_engine_exported(self):
        from mamoun.core import NotificationEngine
        assert NotificationEngine is not None

    def test_health_monitor_exported(self):
        from mamoun.core import HealthMonitor
        assert HealthMonitor is not None

    def test_evolution_loop_v2_exported(self):
        from mamoun.core import EvolutionLoopV2
        assert EvolutionLoopV2 is not None

    def test_outcome_recorder_exported(self):
        from mamoun.core import OutcomeRecorder, record_outcome
        assert OutcomeRecorder is not None
        assert callable(record_outcome)


# ── Test 4: Legacy directory isolation ──────────────────────────────────

class TestLegacyIsolation:
    """Verify that legacy/ is properly isolated."""

    def test_legacy_not_in_production_imports(self):
        backend_path = Path(__file__).parent.parent / "backend" / "mamoun"
        if not backend_path.exists():
            pytest.skip("Backend path not found")

        for py_file in backend_path.rglob("*.py"):
            if "legacy" in str(py_file):
                continue
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            assert "from mamoun.core.legacy" not in content, \
                f"{py_file} imports from core.legacy — forbidden!"
            assert "from .legacy" not in content, \
                f"{py_file} imports from .legacy — forbidden!"

    def test_legacy_has_old_files(self):
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
        kernel_path = Path(__file__).parent.parent / "backend" / "mamoun" / "core" / "mamoun_kernel.py"
        if not kernel_path.exists():
            pytest.skip("kernel file not found")
        content = kernel_path.read_text(encoding="utf-8")
        assert "ADAPTER" in content or "delegates to super_brain" in content, \
            "core/mamoun_kernel.py should be an adapter"

    def test_no_duplicate_llm_client(self):
        llm_path = Path(__file__).parent.parent / "backend" / "mamoun" / "core" / "llm_client.py"
        if not llm_path.exists():
            pytest.skip("llm_client file not found")
        content = llm_path.read_text(encoding="utf-8")
        assert "ADAPTER" in content, "core/llm_client.py should be an adapter"
        assert "MultiProviderLLMClient" in content, "should reference MultiProviderLLMClient"

    def test_no_duplicate_neural_bus(self):
        bus_path = Path(__file__).parent.parent / "backend" / "mamoun" / "core" / "neural_bus.py"
        if not bus_path.exists():
            pytest.skip("neural_bus file not found")
        content = bus_path.read_text(encoding="utf-8")
        assert "ADAPTER" in content, "core/neural_bus.py should be an adapter"
        assert "shared.neural_bus" in content, "should reference shared/neural_bus"

    def test_no_duplicate_self_modifier(self):
        sm_path = Path(__file__).parent.parent / "backend" / "mamoun" / "core" / "self_modifier.py"
        if not sm_path.exists():
            pytest.skip("self_modifier file not found")
        content = sm_path.read_text(encoding="utf-8")
        assert "ADAPTER" in content or "redirected" in content, \
            "core/self_modifier.py should be an adapter/redirect"

    def test_no_duplicate_self_healing(self):
        sh_path = Path(__file__).parent.parent / "backend" / "mamoun" / "core" / "self_healing.py"
        if not sh_path.exists():
            pytest.skip("self_healing file not found")
        content = sh_path.read_text(encoding="utf-8")
        assert "ADAPTER" in content or "redirected" in content, \
            "core/self_healing.py should be an adapter/redirect"

    def test_no_three_copies_of_improvement(self):
        """There should NOT be three active copies of ImprovementProposer."""
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
        assert active_copies <= 1, \
            f"Found {active_copies} active copies of ImprovementProposer — should be 1"

    def test_evolution_improvement_proposer_is_adapter(self):
        """evolution/improvement_proposer.py should be an adapter."""
        ip_path = Path(__file__).parent.parent / "backend" / "mamoun" / "evolution" / "improvement_proposer.py"
        if not ip_path.exists():
            pytest.skip("File not found")
        content = ip_path.read_text(encoding="utf-8")
        assert "ADAPTER" in content or "redirected" in content, \
            "evolution/improvement_proposer.py should be an adapter"

    def test_evolution_loop_is_adapter(self):
        """evolution/evolution_loop.py should be an adapter."""
        el_path = Path(__file__).parent.parent / "backend" / "mamoun" / "evolution" / "evolution_loop.py"
        if not el_path.exists():
            pytest.skip("File not found")
        content = el_path.read_text(encoding="utf-8")
        assert "ADAPTER" in content or "redirected" in content, \
            "evolution/evolution_loop.py should be an adapter"

    def test_evolution_agent_creator_is_adapter(self):
        """evolution/agent_creator.py should be an adapter."""
        ac_path = Path(__file__).parent.parent / "backend" / "mamoun" / "evolution" / "agent_creator.py"
        if not ac_path.exists():
            pytest.skip("File not found")
        content = ac_path.read_text(encoding="utf-8")
        assert "ADAPTER" in content or "redirected" in content, \
            "evolution/agent_creator.py should be an adapter"


# ── Test 6: Functional tests ────────────────────────────────────────────

class TestFunctional:
    """Verify that adapted components actually work."""

    def test_global_workspace_competition(self):
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
        from mamoun.core.mamoun_kernel import EscalationLadder, EscalationLevel
        level = EscalationLadder.determine_level(confidence=0.9, risk_level="low")
        assert level == EscalationLevel.DIRECT_RESPONSE

        level = EscalationLadder.determine_level(confidence=0.2, risk_level="high")
        assert level == EscalationLevel.HUMAN_APPROVAL

    def test_reflexion_engine(self):
        from mamoun.core.mamoun_kernel import ReflexionEngine
        engine = ReflexionEngine(llm_client=None)
        result = asyncio.get_event_loop().run_until_complete(
            engine.review("test action", {"risk_level": "low"}, 0.95)
        )
        assert result["approved"] == True
        assert result["review_type"] == "fast_pass"

    def test_neural_bus_publish(self):
        from mamoun.core.neural_bus import get_neural_bus
        bus = get_neural_bus()
        signal = bus.publish("perception", "test", {"data": "test"})
        assert signal.signal_type == "perception"
        assert signal.source == "test"

    def test_self_healing_engine_diagnose(self):
        from mamoun.core.self_healing import SelfHealingEngine, HealingActionType
        engine = SelfHealingEngine()
        actions = engine.diagnose("test_component", "timeout error")
        assert len(actions) > 0

    def test_llm_client_adapter(self):
        from mamoun.core.llm_client import LLMClient
        client = LLMClient()
        assert hasattr(client, 'chat')
        assert hasattr(client, 'think')
        assert hasattr(client, 'available_providers')
        assert hasattr(client, 'get_health_report')

    def test_mamoun_kernel_adapter(self):
        from mamoun.core.mamoun_kernel import MamounKernel
        kernel = MamounKernel(llm_client=None)
        assert hasattr(kernel, 'workspace')
        assert hasattr(kernel, 'reflexion')
        assert hasattr(kernel, 'escalation')
        assert hasattr(kernel, 'get_status')
        assert hasattr(kernel, 'register_brain')

    def test_self_modifier_adapter(self):
        from mamoun.core.self_modifier import SelfModifier, SelfAnalysis
        assert SelfModifier is not None
        assert SelfAnalysis is not None

    def test_kernel_status(self):
        from mamoun.core.mamoun_kernel import MamounKernel, get_kernel
        kernel = get_kernel(llm_client=None)
        status = kernel.get_status()
        assert "version" in status
        assert "running" in status
        assert "brains_registered" in status


# ── Test 7: Adapter thin-ness verification ─────────────────────────────

class TestAdapterThinness:
    """Verify that adapter files are reasonably thin (no duplicated logic)."""

    THIN_ADAPTER_MAX_LINES = 60  # Pure redirects should be < 60 lines
    ADAPTER_MAX_LINES = 450      # Enhanced adapters with backward-compat types

    def test_metacognitive_engine_is_thin(self):
        path = Path(__file__).parent.parent / "backend" / "mamoun" / "core" / "metacognitive_engine.py"
        lines = len(path.read_text().strip().split('\n'))
        assert lines <= self.THIN_ADAPTER_MAX_LINES, \
            f"metacognitive_engine.py has {lines} lines — should be a thin redirect"

    def test_improvement_engine_is_thin(self):
        path = Path(__file__).parent.parent / "backend" / "mamoun" / "core" / "improvement_engine.py"
        lines = len(path.read_text().strip().split('\n'))
        assert lines <= self.THIN_ADAPTER_MAX_LINES, \
            f"improvement_engine.py has {lines} lines — should be a thin redirect"

    def test_deep_research_engine_is_thin(self):
        path = Path(__file__).parent.parent / "backend" / "mamoun" / "core" / "deep_research_engine.py"
        lines = len(path.read_text().strip().split('\n'))
        assert lines <= self.THIN_ADAPTER_MAX_LINES, \
            f"deep_research_engine.py has {lines} lines — should be a thin redirect"

    def test_web_search_client_is_thin(self):
        path = Path(__file__).parent.parent / "backend" / "mamoun" / "core" / "web_search_client.py"
        lines = len(path.read_text().strip().split('\n'))
        assert lines <= self.THIN_ADAPTER_MAX_LINES, \
            f"web_search_client.py has {lines} lines — should be a thin redirect"

    def test_experiential_rlhf_is_thin(self):
        path = Path(__file__).parent.parent / "backend" / "mamoun" / "core" / "experiential_rlhf.py"
        lines = len(path.read_text().strip().split('\n'))
        assert lines <= self.THIN_ADAPTER_MAX_LINES, \
            f"experiential_rlhf.py has {lines} lines — should be a thin redirect"

    def test_evolution_improvement_proposer_is_thin(self):
        path = Path(__file__).parent.parent / "backend" / "mamoun" / "evolution" / "improvement_proposer.py"
        lines = len(path.read_text().strip().split('\n'))
        assert lines <= self.THIN_ADAPTER_MAX_LINES, \
            f"evolution/improvement_proposer.py has {lines} lines — should be a thin redirect"

    def test_evolution_loop_is_thin(self):
        path = Path(__file__).parent.parent / "backend" / "mamoun" / "evolution" / "evolution_loop.py"
        lines = len(path.read_text().strip().split('\n'))
        assert lines <= self.THIN_ADAPTER_MAX_LINES, \
            f"evolution/evolution_loop.py has {lines} lines — should be a thin redirect"

    def test_evolution_agent_creator_is_thin(self):
        path = Path(__file__).parent.parent / "backend" / "mamoun" / "evolution" / "agent_creator.py"
        lines = len(path.read_text().strip().split('\n'))
        assert lines <= self.THIN_ADAPTER_MAX_LINES, \
            f"evolution/agent_creator.py has {lines} lines — should be a thin redirect"

    def test_self_modifier_is_adapter(self):
        path = Path(__file__).parent.parent / "backend" / "mamoun" / "core" / "self_modifier.py"
        lines = len(path.read_text().strip().split('\n'))
        assert lines <= self.ADAPTER_MAX_LINES, \
            f"self_modifier.py has {lines} lines — should be a thin adapter"

    def test_self_healing_is_adapter(self):
        path = Path(__file__).parent.parent / "backend" / "mamoun" / "core" / "self_healing.py"
        lines = len(path.read_text().strip().split('\n'))
        assert lines <= self.ADAPTER_MAX_LINES, \
            f"self_healing.py has {lines} lines — should be a thin adapter"

    def test_mamoun_kernel_is_adapter(self):
        path = Path(__file__).parent.parent / "backend" / "mamoun" / "core" / "mamoun_kernel.py"
        content = path.read_text()
        assert "ADAPTER" in content or "delegates to super_brain" in content, \
            "mamoun_kernel.py should be an adapter"
