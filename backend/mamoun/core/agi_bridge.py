"""
BABSHARQII v10.0 — AGI Bridge
جسر AGI الموحد — يربط System2 + Causal World Models + جميع قدرات AGI في جسم واحد

Provides a unified entry point that:
1. Routes queries through UncertaintyGate → System1/System2
2. Connects System2 → CausalReasoner → WorldModelV2
3. Dispatches to AGI capabilities (12 modules)
4. Runs DeliberationRoom for multi-brain consensus
5. Returns unified AGI-enhanced results

Architecture:
  User Query
      │
      ▼
  ┌─────────────────┐
  │  UncertaintyGate │ ─── computes uncertainty score
  └────────┬────────┘
           │
     ┌─────┴─────┐
     │  Route?   │
     └─────┬─────┘
      low  │  high
           │
  ┌────────┴────────┐
  │                  │
  ▼                  ▼
System1            System2
(Deliberation)    (Pipeline)
  │                  │
  │          ┌───────┴───────┐
  │          ▼               ▼
  │    CausalReasoner   WorldModelV2
  │          │               │
  │          └───────┬───────┘
  │                  ▼
  │          AGI Capabilities
  │          (12 modules)
  │                  │
  └────────┬─────────┘
           ▼
     ┌───────────┐
     │  Unified  │
     │  Result   │
     └───────────┘
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

from mamoun.core.system2_reasoner import (
    DualSystemRouter,
    UncertaintyGate,
    UncertaintyScore,
    UncertaintyMetrics,
    SystemChoice,
    RoutingDecision,
    System1Result,
    System2Result,
    ReasoningOutcome,
    PipelineStage,
)
from mamoun.core.causal_reasoner import CausalReasoner, CausalRule
from mamoun.brains.world_model_v2 import WorldModelV2
from mamoun.deliberation.room import DeliberationRoom

logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════════════════════
# AGI Capability Status Tracking
# ═════════════════════════════════════════════════════════════════════════════════


@dataclass
class AGICapabilityStatus:
    """حالة قدرة AGI — Status of a single AGI capability."""
    key: str = ""
    name_ar: str = ""
    name_en: str = ""
    enabled: bool = False
    ready: bool = False
    last_used: float = 0.0
    call_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name_ar": self.name_ar,
            "name_en": self.name_en,
            "enabled": self.enabled,
            "ready": self.ready,
            "last_used": self.last_used,
            "call_count": self.call_count,
            "error_count": self.error_count,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
        }


@dataclass
class UnifiedAGIResult:
    """
    نتيجة AGI الموحدة — Unified result from the AGI Bridge.
    
    Combines outputs from System1/System2, Causal World Models,
    DeliberationRoom, and all activated AGI capabilities.
    """
    # Core reasoning
    response: str = ""
    confidence: float = 0.0
    system_used: str = "system_1"  # "system_1" or "system_2"
    
    # Routing
    routing_decision: Optional[dict] = None
    uncertainty: Optional[dict] = None
    
    # Deliberation
    deliberation: Optional[dict] = None
    cjs: float = 0.0
    
    # Causal analysis
    causal_rules: list[dict] = field(default_factory=list)
    causal_graph_nodes: int = 0
    
    # World model
    knowledge_gaps: list[dict] = field(default_factory=list)
    state_prediction: Optional[dict] = None
    
    # AGI capabilities activated
    capabilities_used: list[str] = field(default_factory=list)
    capability_results: dict = field(default_factory=dict)
    
    # Meta
    duration_ms: float = 0.0
    timestamp: float = 0.0
    version: str = "10.0.0"
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "response": self.response,
            "confidence": round(self.confidence, 4),
            "system_used": self.system_used,
            "routing_decision": self.routing_decision,
            "uncertainty": self.uncertainty,
            "deliberation": self.deliberation,
            "cjs": round(self.cjs, 4),
            "causal_rules": self.causal_rules,
            "causal_graph_nodes": self.causal_graph_nodes,
            "knowledge_gaps": self.knowledge_gaps,
            "state_prediction": self.state_prediction,
            "capabilities_used": self.capabilities_used,
            "capability_results": self.capability_results,
            "duration_ms": round(self.duration_ms, 1),
            "timestamp": self.timestamp,
            "version": self.version,
            "errors": self.errors,
        }


# ═════════════════════════════════════════════════════════════════════════════════
# AGI Bridge — الجسر الموحد
# ═════════════════════════════════════════════════════════════════════════════════


class AGIBridge:
    """
    جسر AGI الموحد — يربط System2 + Causal World Models + جميع قدرات AGI.
    
    The unified AGI Bridge is the single entry point for all intelligent
    reasoning in BABSHARQII. It orchestrates:
    
    1. Uncertainty-based routing (System 1 vs System 2)
    2. Causal world model integration
    3. Multi-brain deliberation
    4. AGI capability dispatch (12 modules)
    5. Unified result composition
    
    Usage:
        bridge = AGIBridge()
        result = await bridge.process("لماذا يفشل النظام؟", context={...})
    """

    # AGI capability registry — maps keys to module/class info
    CAPABILITY_REGISTRY = {
        "fluid_reasoning": {
            "module": "mamoun.agi.fluid_reasoner",
            "class": "FluidReasoner",
            "env_toggle": "MAMOUN_FLUID_REASONER_ENABLED",
            "name_ar": "الاستدلال السائب",
            "name_en": "Fluid Reasoning",
        },
        "common_sense": {
            "module": "mamoun.agi.common_sense",
            "class": "CommonSenseFilter",
            "env_toggle": "MAMOUN_COMMON_SENSE_ENABLED",
            "name_ar": "المنطق العام",
            "name_en": "Common Sense Reasoning",
        },
        "hallucination_detection": {
            "module": "mamoun.agi.hallucination_detector",
            "class": "HallucinationDetector",
            "env_toggle": "MAMOUN_HALLUCINATION_DETECTION_ENABLED",
            "name_ar": "كشف الهلوسة",
            "name_en": "Hallucination Detection",
        },
        "intent_drift": {
            "module": "mamoun.agi.intent_drift",
            "class": "IntentDriftDetector",
            "env_toggle": "MAMOUN_INTENT_DRIFT_ENABLED",
            "name_ar": "كشف انحراف النية",
            "name_en": "Intent Drift Detection",
        },
        "theory_of_mind": {
            "module": "mamoun.agi.theory_of_mind",
            "class": "TheoryOfMindEngine",
            "env_toggle": "MAMOUN_THEORY_OF_MIND_ENABLED",
            "name_ar": "نظرية العقل",
            "name_en": "Theory of Mind",
        },
        "continual_learning": {
            "module": "mamoun.agi.continual_learning",
            "class": "ContinualLearningEngine",
            "env_toggle": "MAMOUN_CONTINUAL_LEARNING_ENABLED",
            "name_ar": "التعلم المستمر",
            "name_en": "Continual Learning",
        },
        "privacy_guard": {
            "module": "mamoun.agi.privacy_guard",
            "class": "PrivacyGuard",
            "env_toggle": "MAMOUN_PRIVACY_GUARD_ENABLED",
            "name_ar": "حارس الخصوصية",
            "name_en": "Privacy Guard",
        },
        "skill_discovery": {
            "module": "mamoun.agi.skill_discovery",
            "class": "SkillDiscoveryEngine",
            "env_toggle": "MAMOUN_SKILL_DISCOVERY_ENABLED",
            "name_ar": "اكتشاف المهارات",
            "name_en": "Skill Discovery",
        },
        "swarm_intelligence": {
            "module": "mamoun.agi.swarm_intelligence",
            "class": "SwarmIntelligenceEngine",
            "env_toggle": "MAMOUN_SWARM_INTELLIGENCE_ENABLED",
            "name_ar": "ذكاء السرب",
            "name_en": "Swarm Intelligence",
        },
        "cultural_alignment": {
            "module": "mamoun.agi.cultural_alignment",
            "class": "CulturalAlignmentEngine",
            "env_toggle": "MAMOUN_CULTURAL_ALIGNMENT_ENABLED",
            "name_ar": "المواءمة الثقافية",
            "name_en": "Cultural Value Alignment",
        },
        "specialized_pipeline": {
            "module": "mamoun.agi.specialized_pipeline",
            "class": "SpecializedAgentPipeline",
            "env_toggle": "MAMOUN_SPECIALIZED_PIPELINE_ENABLED",
            "name_ar": "خط أنابيب الوكلاء المتخصصين",
            "name_en": "Specialized Agent Pipeline",
        },
        "social_perception": {
            "module": "mamoun.agi.social_perception",
            "class": "SocialPerceptionEngine",
            "env_toggle": "MAMOUN_SOCIAL_PERCEPTION_ENABLED",
            "name_ar": "الإدراك الاجتماعي",
            "name_en": "Social Perception",
        },
        # ═══ v10.0 Advanced Capabilities (disabled by default) ═══
        "fluid_reasoning_advanced": {
            "module": "mamoun.agi.fluid_reasoner.arc_adapter",
            "class": "ARCAdapter",
            "env_toggle": "MAMOUN_FLUID_ADVANCED_MODE",
            "name_ar": "الاستدلال السائب المتقدم",
            "name_en": "Advanced Fluid Reasoning (ARC-AGI-3)",
        },
        "theory_of_mind_advanced": {
            "module": "mamoun.tom.nested_beliefs",
            "class": "NestedBeliefEngine",
            "env_toggle": "MAMOUN_TOM_ADVANCED",
            "name_ar": "نظرية العقل المستوى 3",
            "name_en": "Advanced Theory of Mind Level 3",
        },
        "auto_evolution": {
            "module": "mamoun.evolution.evolution_loop_auto",
            "class": "AutoEvolutionLoop",
            "env_toggle": "MAMOUN_AUTO_EVOLVE",
            "name_ar": "التطور التلقائي الآمن",
            "name_en": "Safe Auto-Evolution",
        },
        "cultural_adaptive": {
            "module": "mamoun.agi.cultural.adaptive_alignment",
            "class": "AdaptiveAlignmentEngine",
            "env_toggle": "MAMOUN_CULTURAL_ADAPTIVE",
            "name_ar": "المحاذاة الثقافية التكيفية",
            "name_en": "Adaptive Cultural Alignment",
        },
    }

    def __init__(
        self,
        uncertainty_threshold: float = 0.55,
        enable_system2: bool = True,
        enable_causal: bool = True,
        enable_deliberation: bool = True,
        enable_agi_capabilities: bool = True,
    ):
        """
        تهيئة جسر AGI الموحد.
        
        Args:
            uncertainty_threshold: عتبة عدم اليقين للانتقال إلى النظام 2
            enable_system2: تفعيل النظام الثاني
            enable_causal: تفعيل الاستدلال السببي
            enable_deliberation: تفعيل المداولة متعددة الأدمغة
            enable_agi_capabilities: تفعيل قدرات AGI
        """
        # ─── Core Components ─────────────────────────────────────────────
        self._causal_reasoner = CausalReasoner()
        self._deliberation_room = DeliberationRoom()
        self._uncertainty_gate = UncertaintyGate(threshold=uncertainty_threshold)
        self._uncertainty_metrics = UncertaintyMetrics(
            initial_threshold=uncertainty_threshold
        )
        self._world_model = WorldModelV2()
        self._system2 = DualSystemRouter(
            deliberation_room=self._deliberation_room,
            causal_reasoner=self._causal_reasoner,
            uncertainty_threshold=uncertainty_threshold,
        )
        
        # ─── Configuration ───────────────────────────────────────────────
        self._system2_enabled = enable_system2 and os.environ.get(
            "MAMOUN_SYSTEM2_ENABLED", "false"
        ).lower() in ("true", "1", "yes")
        
        self._causal_enabled = enable_causal and os.environ.get(
            "MAMOUN_CAUSAL_ENABLED", "true"
        ).lower() in ("true", "1", "yes")
        
        self._deliberation_enabled = enable_deliberation
        self._agi_capabilities_enabled = enable_agi_capabilities
        
        # ─── Capability Status Tracking ──────────────────────────────────
        self._capability_status: dict[str, AGICapabilityStatus] = {}
        self._capability_instances: dict[str, object] = {}
        
        for key, info in self.CAPABILITY_REGISTRY.items():
            env_val = os.environ.get(info["env_toggle"], "false").lower()
            is_enabled = env_val in ("true", "1", "yes")
            self._capability_status[key] = AGICapabilityStatus(
                key=key,
                name_ar=info["name_ar"],
                name_en=info["name_en"],
                enabled=is_enabled,
                ready=False,
            )
        
        # ─── Statistics ──────────────────────────────────────────────────
        self._total_queries: int = 0
        self._system1_queries: int = 0
        self._system2_queries: int = 0
        self._capability_calls: int = 0
        self._start_time: float = time.time()
        
        logger.info(
            f"[AGIBridge] Initialized — System2: {self._system2_enabled}, "
            f"Causal: {self._causal_enabled}, "
            f"Capabilities: {sum(1 for s in self._capability_status.values() if s.enabled)}/12"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # Main Processing Pipeline
    # ═══════════════════════════════════════════════════════════════════════════

    async def process(
        self,
        query: str,
        context: dict | None = None,
        brains_responses: list[dict] | None = None,
    ) -> UnifiedAGIResult:
        """
        معالجة استعلام موحدة — Unified query processing through the AGI Bridge.
        
        This is the main entry point. It:
        1. Computes uncertainty → routes to System 1 or System 2
        2. If System 2: runs causal analysis + world model
        3. Runs multi-brain deliberation
        4. Dispatches to enabled AGI capabilities
        5. Composes a unified result
        
        Args:
            query: الاستعلام أو السؤال
            context: سياق إضافي
            brains_responses: استجابات الأدمغة السابقة (إن وجدت)
        
        Returns:
            UnifiedAGIResult with all analysis combined
        """
        start_time = time.time()
        context = context or {}
        brains_responses = brains_responses or []
        
        result = UnifiedAGIResult(timestamp=start_time)
        self._total_queries += 1
        
        try:
            # ─── Step 1: Compute Uncertainty ─────────────────────────────
            knowledge_gaps = self._world_model.detect_knowledge_gap(context)
            
            uncertainty = self._uncertainty_gate.compute_uncertainty(
                topic=query,
                brain_responses=brains_responses,
                context=context,
                knowledge_gaps=knowledge_gaps,
            )
            
            result.uncertainty = uncertainty.to_dict()
            result.knowledge_gaps = knowledge_gaps
            
            # ─── Step 2: Route to System 1 or System 2 ───────────────────
            system_choice = self._uncertainty_gate.route(uncertainty)
            
            routing_decision = RoutingDecision(
                system=system_choice,
                uncertainty=uncertainty,
                threshold=self._uncertainty_gate.threshold,
                topic=query[:100],
                timestamp=start_time,
            )
            result.routing_decision = routing_decision.to_dict()
            
            if system_choice == SystemChoice.SYSTEM_2 and self._system2_enabled:
                # ─── System 2: Deep Reasoning Path ──────────────────────
                self._system2_queries += 1
                result.system_used = "system_2"
                
                s2_outcome = await self._run_system2(
                    query, context, brains_responses, knowledge_gaps
                )
                
                result.response = s2_outcome.response
                result.confidence = s2_outcome.confidence
                
                if s2_outcome.system2_result:
                    result.capability_results["system2_stages"] = [
                        s.to_dict() for s in s2_outcome.system2_result.stages
                    ]
                    result.capabilities_used.append("system2")
                
                # Record in uncertainty metrics
                self._uncertainty_metrics.record(
                    uncertainty=uncertainty,
                    system_choice=system_choice,
                    outcome_confidence=result.confidence,
                    topic=query,
                )
                
            else:
                # ─── System 1: Fast Path (Deliberation) ─────────────────
                self._system1_queries += 1
                result.system_used = "system_1"
                
                if brains_responses and self._deliberation_enabled:
                    deliberation_result = await self._deliberation_room.deliberate(
                        topic=query,
                        brains_responses=brains_responses,
                    )
                    result.deliberation = deliberation_result.to_dict()
                    result.cjs = deliberation_result.critical_junction_score
                    
                    # Use deliberation consensus as confidence
                    result.confidence = deliberation_result.consensus_level
                    result.response = (
                        deliberation_result.recommendations[0]
                        if deliberation_result.recommendations
                        else ""
                    )
                else:
                    # No brain responses — basic confidence
                    result.confidence = 1.0 - uncertainty.composite
                    result.response = ""
                
                # Record in uncertainty metrics
                self._uncertainty_metrics.record(
                    uncertainty=uncertainty,
                    system_choice=SystemChoice.SYSTEM_1,
                    outcome_confidence=result.confidence,
                    topic=query,
                )
            
            # ─── Step 3: Causal World Model Analysis ─────────────────────
            if self._causal_enabled:
                causal_result = await self._run_causal_analysis(
                    query, context
                )
                result.causal_rules = causal_result.get("rules", [])
                result.causal_graph_nodes = causal_result.get("graph_nodes", 0)
                
                if causal_result.get("rules"):
                    result.capabilities_used.append("causal_reasoner")
            
            # ─── Step 4: World Model State Prediction ────────────────────
            state_prediction = await self._world_model.predict_state(
                current_state=context,
                action=query,
            )
            result.state_prediction = state_prediction.to_dict()
            
            # ─── Step 5: Dispatch AGI Capabilities ───────────────────────
            if self._agi_capabilities_enabled:
                agi_results = await self._dispatch_agi_capabilities(
                    query, context, result
                )
                result.capability_results.update(agi_results)
                
                for cap_key in agi_results:
                    if cap_key not in result.capabilities_used:
                        result.capabilities_used.append(cap_key)
            
        except Exception as e:
            logger.error(f"[AGIBridge] Error processing query: {e}")
            result.errors.append(str(e))
            result.confidence = max(0.0, result.confidence - 0.1)
        
        # ─── Finalize ────────────────────────────────────────────────────
        result.duration_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"[AGIBridge] Query processed: system={result.system_used}, "
            f"confidence={result.confidence:.3f}, "
            f"capabilities={len(result.capabilities_used)}, "
            f"duration={result.duration_ms:.1f}ms"
        )
        
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # System 2 Deep Reasoning
    # ═══════════════════════════════════════════════════════════════════════════

    async def _run_system2(
        self,
        query: str,
        context: dict,
        brains_responses: list[dict],
        knowledge_gaps: list[dict],
    ) -> ReasoningOutcome:
        """
        تشغيل النظام الثاني — Run System 2 deep reasoning pipeline.
        
        Connects System2Reasoner → CausalReasoner → WorldModelV2
        for deep, deliberate reasoning.
        """
        try:
            # Run System 2 reasoning
            outcome = await self._system2.reason(
                topic=query,
                context=context,
                brain_responses=brains_responses,
                knowledge_gaps=knowledge_gaps,
            )
            return outcome
        except Exception as e:
            logger.error(f"[AGIBridge] System 2 error: {e}")
            # Fallback to System 1 result
            return ReasoningOutcome(
                decision=RoutingDecision(system=SystemChoice.SYSTEM_1),
                system1_result=System1Result(
                    response="",
                    confidence=0.3,
                ),
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # Causal World Model Analysis
    # ═══════════════════════════════════════════════════════════════════════════

    async def _run_causal_analysis(
        self,
        query: str,
        context: dict,
    ) -> dict:
        """
        تشغيل التحليل السببي — Run causal analysis with World Model.
        
        Integrates CausalReasoner with WorldModelV2 for:
        - Root cause analysis from error patterns
        - Causal graph building
        - Intervention suggestions
        - Knowledge gap detection
        """
        errors = context.get("errors", [])
        rules = []
        graph_nodes = 0
        
        try:
            # Analyze root causes if errors available
            if errors:
                rules = await self._causal_reasoner.analyze_root_cause(errors)
                
                # Build causal graph
                graph = await self._causal_reasoner.build_causal_graph(errors)
                graph_nodes = len(graph)
                
                # Propose abstract rules from causality
                proposed = await self._causal_reasoner.propose_rules_from_causality()
                
                # Feed proposed rules back to WorldModelV2
                if proposed:
                    self._world_model._knowledge_gaps = (
                        self._world_model.detect_knowledge_gap(context)
                    )
            
        except Exception as e:
            logger.error(f"[AGIBridge] Causal analysis error: {e}")
        
        return {
            "rules": [r.to_dict() for r in rules[:10]],
            "graph_nodes": graph_nodes,
            "interventions": [
                r.intervention for r in rules[:3] if r.intervention
            ],
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # AGI Capability Dispatch
    # ═══════════════════════════════════════════════════════════════════════════

    async def _dispatch_agi_capabilities(
        self,
        query: str,
        context: dict,
        current_result: UnifiedAGIResult,
    ) -> dict:
        """
        توزيع قدرات AGI — Dispatch to enabled AGI capabilities.
        
        Runs enabled capabilities in sequence, collecting results.
        Each capability is lazy-loaded on first use.
        """
        results = {}
        
        for key, status in self._capability_status.items():
            if not status.enabled:
                continue
            
            try:
                cap_start = time.time()
                
                # Lazy-load capability instance
                instance = self._get_capability_instance(key)
                if instance is None:
                    continue
                
                # Dispatch based on capability type
                cap_result = await self._invoke_capability(
                    key, instance, query, context, current_result
                )
                
                cap_duration = (time.time() - cap_start) * 1000
                
                # Update status tracking
                status.call_count += 1
                status.last_used = time.time()
                status.ready = True
                # Running average of latency
                if status.avg_latency_ms == 0:
                    status.avg_latency_ms = cap_duration
                else:
                    status.avg_latency_ms = (
                        0.8 * status.avg_latency_ms + 0.2 * cap_duration
                    )
                
                results[key] = cap_result
                self._capability_calls += 1
                
            except Exception as e:
                logger.warning(f"[AGIBridge] Capability '{key}' error: {e}")
                status.error_count += 1
                results[key] = {
                    "status": "error",
                    "error": str(e)[:200],
                    "key": key,
                }
        
        return results

    def _get_capability_instance(self, key: str):
        """
        تحميل كسول لقدرة AGI — Lazy-load an AGI capability instance.
        """
        if key in self._capability_instances:
            return self._capability_instances[key]
        
        info = self.CAPABILITY_REGISTRY.get(key)
        if not info:
            return None
        
        try:
            import importlib
            module = importlib.import_module(info["module"])
            cls = getattr(module, info["class"])
            instance = cls()
            self._capability_instances[key] = instance
            self._capability_status[key].ready = True
            logger.info(f"[AGIBridge] Loaded capability: {key}")
            return instance
        except ImportError as e:
            logger.warning(f"[AGIBridge] Cannot import capability '{key}': {e}")
            self._capability_status[key].ready = False
            return None
        except Exception as e:
            logger.warning(f"[AGridge] Cannot instantiate capability '{key}': {e}")
            self._capability_status[key].ready = False
            return None

    async def _invoke_capability(
        self,
        key: str,
        instance: object,
        query: str,
        context: dict,
        current_result: UnifiedAGIResult,
    ) -> dict:
        """
        استدعاء قدرة AGI — Invoke a specific AGI capability.
        
        Each capability has a different interface, so we dispatch
        based on the capability key.
        """
        result = {"status": "ok", "key": key}
        import asyncio
        
        async def _safe_call(func, *args, **kwargs):
            """Call a function that may be sync or async."""
            out = func(*args, **kwargs)
            if asyncio.iscoroutine(out):
                out = await out
            return out
        
        if key == "fluid_reasoning":
            if hasattr(instance, "think"):
                out = await _safe_call(instance.think, query, context=context)
                result["output"] = out if isinstance(out, dict) else {"result": str(out)}
        
        elif key == "common_sense":
            if hasattr(instance, "filter"):
                out = await _safe_call(instance.filter, query)
                result["output"] = out if isinstance(out, dict) else {"filtered": str(out)}
        
        elif key == "hallucination_detection":
            if hasattr(instance, "detect"):
                out = await _safe_call(instance.detect, query, context=context)
                result["output"] = out if isinstance(out, dict) else {"detection": str(out)}
        
        elif key == "intent_drift":
            if hasattr(instance, "check"):
                original = context.get("goal", query)
                out = await _safe_call(instance.check, original, query)
                result["output"] = out if isinstance(out, dict) else {"drift": str(out)}
        
        elif key == "theory_of_mind":
            if hasattr(instance, "infer"):
                out = await _safe_call(instance.infer, query, context=context)
                result["output"] = out if isinstance(out, dict) else {"inference": str(out)}
        
        elif key == "continual_learning":
            if hasattr(instance, "learn"):
                out = await _safe_call(instance.learn, query, feedback=context)
                result["output"] = out if isinstance(out, dict) else {"learning": str(out)}
        
        elif key == "privacy_guard":
            if hasattr(instance, "scan_data"):
                out = await _safe_call(instance.scan_data, query)
                result["output"] = out if isinstance(out, dict) else {"scan": str(out)}
        
        elif key == "skill_discovery":
            if hasattr(instance, "discover"):
                out = await _safe_call(instance.discover, query, context=context)
                result["output"] = out if isinstance(out, dict) else {"discovery": str(out)}
        
        elif key == "swarm_intelligence":
            if hasattr(instance, "optimize"):
                out = await _safe_call(instance.optimize, query, agents=context.get("agents", []))
                result["output"] = out if isinstance(out, dict) else {"optimization": str(out)}
        
        elif key == "cultural_alignment":
            if hasattr(instance, "align"):
                out = await _safe_call(instance.align, query, context=context)
                result["output"] = out if isinstance(out, dict) else {"alignment": str(out)}
        
        elif key == "specialized_pipeline":
            if hasattr(instance, "route"):
                out = await _safe_call(instance.route, query, context=context)
                result["output"] = out if isinstance(out, dict) else {"routing": str(out)}
        
        elif key == "social_perception":
            if hasattr(instance, "perceive"):
                out = await _safe_call(instance.perceive, query, context=context)
                result["output"] = out if isinstance(out, dict) else {"perception": str(out)}
        
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # Status & Metrics
    # ═══════════════════════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        """
        الحصول على حالة الجسر — Get AGI Bridge status.
        """
        uptime = time.time() - self._start_time
        
        enabled_caps = sum(
            1 for s in self._capability_status.values() if s.enabled
        )
        ready_caps = sum(
            1 for s in self._capability_status.values() if s.ready
        )
        
        return {
            "version": "10.0.0",
            "uptime_seconds": round(uptime, 1),
            "total_queries": self._total_queries,
            "system1_queries": self._system1_queries,
            "system2_queries": self._system2_queries,
            "capability_calls": self._capability_calls,
            "system2_enabled": self._system2_enabled,
            "causal_enabled": self._causal_enabled,
            "deliberation_enabled": self._deliberation_enabled,
            "capabilities_enabled": enabled_caps,
            "capabilities_ready": ready_caps,
            "capabilities_total": len(self.CAPABILITY_REGISTRY),
            "uncertainty_metrics": self._uncertainty_metrics.get_statistics(),
            "uncertainty_drift": self._uncertainty_metrics.detect_uncertainty_drift(),
            "capabilities": {
                k: v.to_dict() for k, v in self._capability_status.items()
            },
        }

    def get_capability_status(self, key: str) -> dict | None:
        """الحصول على حالة قدرة محددة."""
        status = self._capability_status.get(key)
        return status.to_dict() if status else None

    def enable_capability(self, key: str) -> bool:
        """تفعيل قدرة AGI — Enable an AGI capability."""
        if key not in self.CAPABILITY_REGISTRY:
            return False
        
        # Update env var
        info = self.CAPABILITY_REGISTRY[key]
        os.environ[info["env_toggle"]] = "true"
        self._capability_status[key].enabled = True
        
        logger.info(f"[AGIBridge] Enabled capability: {key}")
        return True

    def disable_capability(self, key: str) -> bool:
        """تعطيل قدرة AGI — Disable an AGI capability."""
        if key not in self.CAPABILITY_REGISTRY:
            return False
        
        info = self.CAPABILITY_REGISTRY[key]
        os.environ[info["env_toggle"]] = "false"
        self._capability_status[key].enabled = False
        
        logger.info(f"[AGIBridge] Disabled capability: {key}")
        return True

    def get_uncertainty_stats(self) -> dict:
        """إحصائيات عدم اليقين."""
        return self._uncertainty_metrics.get_statistics()

    def get_uncertainty_drift(self) -> dict:
        """كشف انحراف عدم اليقين."""
        return self._uncertainty_metrics.detect_uncertainty_drift()


# ═════════════════════════════════════════════════════════════════════════════════
# Global Singleton — for easy access from routes
# ═════════════════════════════════════════════════════════════════════════════════

_agi_bridge_instance: AGIBridge | None = None


def get_agi_bridge() -> AGIBridge:
    """الحصول على مثيل جسر AGI — Get or create the global AGI Bridge instance."""
    global _agi_bridge_instance
    if _agi_bridge_instance is None:
        _agi_bridge_instance = AGIBridge()
    return _agi_bridge_instance
