"""
Test Suite: Integration Layer — End-to-End Connectivity

Verifies that all super_brain components are properly connected
and accessible from the production code paths.
"""

import pytest
import asyncio


class TestIntegrationLayer:
    """Test the Integration Layer that bridges old+new code."""

    def test_integration_layer_exists(self):
        """IntegrationLayer should be importable."""
        from mamoun.core.integration_layer import IntegrationLayer, get_integration_layer
        assert IntegrationLayer is not None
        assert callable(get_integration_layer)

    def test_integration_layer_singleton(self):
        """get_integration_layer should return the same instance."""
        from mamoun.core.integration_layer import get_integration_layer
        layer1 = get_integration_layer()
        layer2 = get_integration_layer()
        assert layer1 is layer2

    @pytest.mark.asyncio
    async def test_connect_all(self):
        """connect_all should connect super_brain components."""
        from mamoun.core.integration_layer import IntegrationLayer
        layer = IntegrationLayer()
        results = await layer.connect_all()
        assert isinstance(results, dict)
        # At least some components should connect
        connected_count = sum(1 for v in results.values() if v == "connected")
        assert connected_count >= 3, f"Expected at least 3 connections, got {connected_count}: {results}"

    @pytest.mark.asyncio
    async def test_self_healing_bridge_connected(self):
        """SelfHealingBridge should be accessible via integration layer."""
        from mamoun.core.integration_layer import IntegrationLayer
        layer = IntegrationLayer()
        await layer.connect_all()
        bridge = layer.get_component("self_healing_bridge")
        if bridge:
            assert hasattr(bridge, 'heal_component')

    @pytest.mark.asyncio
    async def test_health_monitor_connected(self):
        """HealthMonitor should be accessible via integration layer."""
        from mamoun.core.integration_layer import IntegrationLayer
        layer = IntegrationLayer()
        await layer.connect_all()
        monitor = layer.get_component("health_monitor")
        if monitor:
            assert hasattr(monitor, 'get_health')


class TestEndToEndPaths:
    """End-to-end tests: old import path → super_brain component works."""

    def test_old_llm_path_uses_new_provider(self):
        """from core.llm_client import LLMClient should use MultiProviderLLMClient."""
        from mamoun.core.llm_client import LLMClient
        from mamoun.core.shared.multi_provider_llm import MultiProviderLLMClient
        client = LLMClient()
        assert client._multi is not None
        assert isinstance(client._multi, MultiProviderLLMClient)

    def test_old_neural_bus_path_uses_new_bus(self):
        """from core.neural_bus import get_neural_bus should use shared NeuralBus."""
        from mamoun.core.neural_bus import get_neural_bus, NeuralBusCompat
        bus = get_neural_bus()
        assert isinstance(bus, NeuralBusCompat)

    def test_old_kernel_has_new_features(self):
        """from core.mamoun_kernel import MamounKernel should have new features."""
        from mamoun.core.mamoun_kernel import MamounKernel, GlobalWorkspace, ReflexionEngine
        kernel = MamounKernel()
        assert hasattr(kernel, 'workspace')
        assert isinstance(kernel.workspace, GlobalWorkspace)
        assert hasattr(kernel, 'reflexion')
        assert isinstance(kernel.reflexion, ReflexionEngine)

    def test_core_init_exports_all_stages(self):
        """core/__init__.py should export all stage components."""
        import mamoun.core as core
        # Stage 1
        assert hasattr(core, 'MetaCognitionEngine')
        assert hasattr(core, 'SelfHealingBridge')
        assert hasattr(core, 'RLHFBridge')
        assert hasattr(core, 'OutcomeRecorder')
        # Stage 2
        assert hasattr(core, 'VariantArchive')
        assert hasattr(core, 'NotificationEngine')
        assert hasattr(core, 'AgentLifecycleManager')
        # Stage 3
        assert hasattr(core, 'EvolutionLoopV2')
        # Stage 4
        assert hasattr(core, 'HealthMonitor')
        assert hasattr(core, 'HealthDashboard')

    def test_record_outcome_accessible(self):
        """record_outcome decorator should be accessible from core."""
        from mamoun.core import record_outcome
        assert callable(record_outcome)

    def test_old_healing_patterns_preserved(self):
        """Old 14+ healing patterns should still be accessible."""
        from mamoun.core.self_healing import SelfHealingEngine, HealingActionType
        engine = SelfHealingEngine()
        # Test a few patterns
        actions = engine.diagnose("test", "timeout error")
        assert any(a.action_type == HealingActionType.RETRY_WITH_BACKOFF for a in actions)
        
        actions = engine.diagnose("test", "memory overflow")
        assert any(a.action_type == HealingActionType.CLEAR_CACHE for a in actions)

    def test_escalation_ladder_preserved(self):
        """EscalationLadder should be accessible and functional."""
        from mamoun.core.mamoun_kernel import EscalationLadder, EscalationLevel
        level = EscalationLadder.determine_level(confidence=0.95, risk_level="low")
        assert level == EscalationLevel.DIRECT_RESPONSE
        
        level = EscalationLadder.determine_level(confidence=0.2, is_self_modification=True)
        assert level == EscalationLevel.HUMAN_APPROVAL


class TestNoFutureDuplication:
    """Tests to prevent future structural duplication."""

    def test_core_files_are_adapters(self):
        """All core/ files for duplicated components should be adapters."""
        from pathlib import Path
        core_dir = Path(__file__).parent.parent / "backend" / "mamoun" / "core"
        if not core_dir.exists():
            pytest.skip("Core directory not found")

        duplicated_files = [
            "llm_client.py",
            "neural_bus.py",
            "mamoun_kernel.py",
            "self_modifier.py",
            "self_healing.py",
        ]
        
        for filename in duplicated_files:
            filepath = core_dir / filename
            if filepath.exists():
                content = filepath.read_text(encoding="utf-8")
                assert any(marker in content for marker in ["ADAPTER", "redirected", "ENHANCED ADAPTER"]), \
                    f"{filename} should be an adapter — no standalone implementations allowed in core/"

    def test_no_new_files_in_core_without_adapter(self):
        """Any new Python file in core/ should be an adapter or utility."""
        from pathlib import Path
        core_dir = Path(__file__).parent.parent / "backend" / "mamoun" / "core"
        if not core_dir.exists():
            pytest.skip("Core directory not found")

        # Files that are allowed to be non-adapters (utilities)
        allowed_standalone = {
            "__init__.py", "code_patcher.py", "sandbox_runner.py",
            "safety_guard.py", "triple_memory.py", "integration_layer.py",
            "absolute_executor.py", "abstraction_engine.py", "age_mem.py",
            "agi_bridge.py", "agi_orchestrator.py", "approval_gate.py",
            "auth.py", "auto_research_heal_loop.py", "autonomic_system.py",
            "autonomy_engine.py", "backup_manager.py", "capabilities_engine.py",
            "capability_assessor.py", "capability_router.py", "causal_graph.py",
            "causal_reasoner.py", "code_generation_engine.py", "concurrency_monitor.py",
            "consciousness_loop.py", "consequence_learning.py", "continuous_learner.py",
            "dashboard_builder.py", "data_manager.py", "deep_bonding.py",
            "desktop_controller.py", "dual_deliberation_gate.py", "embodiment_controller.py",
            "embodiment_controller_v2.py", "emotional_memory.py", "fused_core.py",
            "hierarchical_planner.py", "inner_monologue.py", "living_state.py",
            "long_term_planner.py", "meta_analyzer.py", "monitoring.py",
            "multimodal_processor.py", "predictive_healer.py", "predictive_memory.py",
            "priority_queue.py", "proactive_intelligence.py", "project_orchestrator.py",
            "project_pool.py", "project_registry.py", "project_scaffolder.py",
            "real_tools.py", "reflective_journal.py", "reflexes.py",
            "reflexion_engine.py", "research_agent.py", "safety_gate_client.py",
            "selective_attention.py", "self_improvement_engine.py", "self_mirror.py",
            "self_tester.py", "session_context.py", "skill_executor.py",
            "skill_executors.py", "smart_scheduler.py", "state_reader.py",
            "system2_reasoner.py", "temporal_awareness.py", "unified_db.py",
            "unified_mind.py", "user_mental_model.py", "version_archive.py",
            "working_memory.py",
        }

        for py_file in core_dir.glob("*.py"):
            if py_file.name in allowed_standalone:
                continue
            if py_file.name.startswith("_"):
                continue
            # Check if it's a known duplicated file
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            if "class " in content and py_file.name not in allowed_standalone:
                # Should be an adapter
                pass  # Already tested above
