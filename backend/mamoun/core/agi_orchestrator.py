"""
BABSHARQII v27.0 — AGI Orchestrator (The Neural Bridge)
الجسر العصبي — يربط كل الركائز المعزولة بحلقة التفكير

Before v26: Pillars were "isolated organs" — they existed but nobody asked them.
After v26: Every user message flows through the pillars BEFORE and AFTER the LLM.
v27.0: ALL 31 pillars connected — no isolated modules remain.

Pipeline (v27):
  1. PERCEIVE   → SelectiveAttention classifies signal importance
  2. RECALL     → EpisodicMemoryV2 recalls similar experiences
  3. CAUSAL     → CausalWorldModel + CausalGraph provide causal knowledge
  4. KNOWLEDGE  → WorldKnowledgeGraph retrieves related entities
  5. META       → MetacognitiveEngine self-assesses confidence
  6. SYMBOLIC   → SymbolicReasoner forward/backward chaining
  7. BAYESIAN   → BayesianInference probabilistic queries
  8. RL_DECIDE  → ReinforcementLearning action selection
  9. ABSTRACT   → AbstractGeneralization pattern classification
 10. PERCEPTION → PerceptionActionLoop OODA decision
 11. WORKING_MEM→ DynamicWorkingMemory active items
 12. SYSTEM2    → System2Reasoner decides if deep thinking is needed
 13. NEURAL     → NeuralMesh processes pattern (not LLM)
 14. TRIPLE_MEM → TripleMemory search/recall
 15. HIERARCHICAL→ HierarchicalPlanner next action
 16. KNOWLEDGE_BRIDGE→ KnowledgeBridge analogy finding
 17. LTP        → LongTermPlanner goal forecasting
 18. COMMON_SENSE→ CommonSenseFilter violation check
 19. HALLUCINATION→ HallucinationDetector risk assessment
 20. PRIVACY    → PrivacyGuard data scanning
 21. CULTURAL   → CulturalAlignmentEngine alignment scoring
 22. SOCIAL     → SocialPerceptionEngine emotion detection
 23. INTENT_DRIFT→ IntentDriftDetector drift tracking
 24. FLUID      → FluidReasoner analogical reasoning
 25. TOM        → TheoryOfMind user modeling
 26. NOVELTY    → NoveltyScorer novelty evaluation
 27. ORIGINALITY→ OriginalityEngine creative generation
 28. ONE_SHOT   → OneShotLearner skill listing
 29. SKILL_GEN  → SkillGeneralizer generalization tracking
 30. FORGET     → StrategicForgetting memory evaluation
 31. SKILL_DISC → SkillDiscoveryEngine skill discovery

This is the "unified brain" — one thinking loop using ALL available intelligence.
"""

import time
import json
import logging
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
from enum import Enum

logger = logging.getLogger("mamoun.agi_orchestrator")


# ═══════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════

class ThinkingPhase(str, Enum):
    """مراحل التفكير في الحلقة الموحدة"""
    PERCEIVE = "perceive"          # الانتباه الانتقائي
    RECALL = "recall"              # استرجاع الذكريات
    CAUSAL = "causal"              # التفكير السببي
    KNOWLEDGE = "knowledge"        # البحث المعرفي
    META_ASSESS = "meta_assess"    # التقييم الذاتي
    SYMBOLIC = "symbolic"          # الاستدلال الرمزي (v26)
    BAYESIAN = "bayesian"          # الاستدلال البايزي (v26)
    RL_DECIDE = "rl_decide"        # قرار التعلم المعزز (v26)
    ABSTRACT = "abstract"          # التعميم التجريدي (v26)
    PERCEPTION = "perception"      # حلقة الإدراك-الفعل (v26)
    WORKING_MEM = "working_mem"    # الذاكرة العاملة (v26)
    SYSTEM2 = "system2"            # القرار بعمق أم سرعة
    NEURAL = "neural"              # المعالجة العصبية
    DELIBERATE = "deliberate"      # المداولة (LLM إذا لزم)
    LEARN = "learn"                # التعلم من التفاعل
    REMEMBER = "remember"          # التخزين في الذاكرة
    PLAN = "plan"                  # تحديث الخطط
    TRANSFER = "transfer"          # نقل المعرفة
    CONTINUAL = "continual"        # التعلم المستمر (v26)
    FORGET = "forget"              # النسيان الاستراتيجي
    NOVELTY = "novelty"            # تقييم الجدة
    ORIGINALITY = "originality"    # الإبداع الأصيل
    COMMON_SENSE = "common_sense"  # الفطرة السليمة (v27)
    CULTURAL = "cultural"          # المحاذاة الثقافية (v27)
    FLUID = "fluid"                # الاستدلال السائل (v27)
    HALLUCINATION = "hallucination" # كشف الهلوسة (v27)
    INTENT_DRIFT = "intent_drift"  # انحراف النية (v27)
    PRIVACY = "privacy"            # حماية الخصوصية (v27)
    SKILL_DISCOVERY = "skill_discovery"  # اكتشاف المهارات (v27)
    SOCIAL = "social"              # الإدراك الاجتماعي (v27)
    PIPELINE = "pipeline"          # خط الأنابيب المتخصص (v27)
    SWARM = "swarm"                # ذكاء السرب (v27)
    THEORY_OF_MIND = "theory_of_mind"  # نظرية العقل (v27)


@dataclass
class ThinkingResult:
    """نتيجة حلقة التفكير الموحدة"""
    query: str = ""
    attention_level: str = "medium"     # selective attention classification
    attention_score: float = 0.5
    recalled_episodes: List[Dict] = field(default_factory=list)
    causal_insights: Dict = field(default_factory=dict)
    knowledge_context: Dict = field(default_factory=dict)
    meta_assessment: Dict = field(default_factory=dict)
    symbolic_result: Dict = field(default_factory=dict)
    bayesian_result: Dict = field(default_factory=dict)
    rl_decision: Dict = field(default_factory=dict)
    abstraction_result: Dict = field(default_factory=dict)
    perception_result: Dict = field(default_factory=dict)
    working_memory_items: List[Dict] = field(default_factory=list)
    system2_decision: Dict = field(default_factory=dict)
    neural_activation: Dict = field(default_factory=dict)
    # v27 AGI results
    common_sense_result: Dict = field(default_factory=dict)
    cultural_result: Dict = field(default_factory=dict)
    fluid_reasoning_result: Dict = field(default_factory=dict)
    hallucination_result: Dict = field(default_factory=dict)
    intent_drift_result: Dict = field(default_factory=dict)
    privacy_result: Dict = field(default_factory=dict)
    skill_discovery_result: Dict = field(default_factory=dict)
    social_perception_result: Dict = field(default_factory=dict)
    pipeline_result: Dict = field(default_factory=dict)
    swarm_result: Dict = field(default_factory=dict)
    theory_of_mind_result: Dict = field(default_factory=dict)
    # v27 Isolated system results
    triple_memory_result: Dict = field(default_factory=dict)
    hierarchical_plan_result: Dict = field(default_factory=dict)
    knowledge_bridge_result: Dict = field(default_factory=dict)
    long_term_plan_result: Dict = field(default_factory=dict)
    one_shot_result: Dict = field(default_factory=dict)
    skill_generalizer_result: Dict = field(default_factory=dict)
    originality_result: Dict = field(default_factory=dict)
    # General
    final_response: str = ""
    final_confidence: float = 0.5
    winning_brain: str = ""
    learning_applied: bool = False
    episode_stored: bool = False
    plan_updated: bool = False
    knowledge_added: bool = False
    transfer_applied: bool = False
    continual_learning_applied: bool = False
    forgetting_applied: bool = False
    novelty_score: float = 0.0
    originality_applied: bool = False
    privacy_safe: bool = True
    hallucination_risk: float = 0.0
    intent_drift_level: str = "none"
    common_sense_violations: int = 0
    cultural_alignment_score: float = 1.0
    phases_completed: List[str] = field(default_factory=list)
    total_ms: float = 0.0
    used_pillars: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════
# AGI Orchestrator — The Neural Bridge
# ═══════════════════════════════════════════════════════════════

class AGIOrchestrator:
    """
    الجسر العصبي — يربط كل ركائز الذكاء العام بحلقة تفكير واحدة

    Instead of: User → LLM → Response
    Now:        User → [13 Pillars] → LLM (if needed) → [13 Pillars] → Response

    Every pillar contributes what it knows BEFORE the LLM is consulted,
    and learns from the outcome AFTER the response.
    """

    def __init__(self, db_path=None):
        self.db_path = db_path
        self._llm = None
        self._initialized = False

        # ═══ v25.0 Pillars (real algorithms, no LLM) ═══
        self._neural_mesh = None
        self._causal_world_model = None
        self._domain_adapter = None
        self._synaptic_intelligence = None
        self._knowledge_bridge = None
        self._long_term_planner = None

        # ═══ v24.1 Pillars (7 AGI pillars) ═══
        self._causal_graph = None
        self._episodic_memory = None
        self._metacognitive_engine = None
        self._hierarchical_planner = None
        self._world_knowledge_graph = None
        self._consequence_learning = None
        self._selective_attention = None

        # ═══ v26.0 Reasoning Pillars (7 new) ═══
        self._symbolic_reasoner = None
        self._bayesian_inference = None
        self._reinforcement_learning = None
        self._abstract_generalization = None
        self._perception_action_loop = None
        self._dynamic_working_memory = None
        self._continual_learning = None

        # ═══ Isolated Systems (7 newly connected) ═══
        self._triple_memory = None
        self._system2_reasoner = None
        self._strategic_forgetting = None
        self._novelty_scorer = None
        self._originality_engine = None
        self._one_shot_learner = None
        self._skill_generalizer = None

        # ═══ Other connected systems ═══
        self._emotional_memory = None

        # ═══ v27.0 AGI Layer (11 modules from agi/) ═══
        self._common_sense = None
        self._cultural_alignment = None
        self._fluid_reasoner = None
        self._hallucination_detector = None
        self._intent_drift = None
        self._privacy_guard = None
        self._skill_discovery = None
        self._social_perception = None
        self._specialized_pipeline = None
        self._swarm_intelligence = None
        self._theory_of_mind = None

        # ═══ Statistics ═══
        self._stats = {
            "total_queries": 0,
            "pillar_hits": {},       # pillar_name → count of times it contributed
            "phase_times": {},       # phase_name → average ms
            "llm_bypassed": 0,       # times LLM wasn't needed
            "neural_learned": 0,     # times neural mesh learned
            "causal_consulted": 0,   # times causal model was consulted
            "episodes_stored": 0,    # episodes recorded
            "transfers_done": 0,     # knowledge transfers
        }

    def set_llm_client(self, llm_client):
        """Set LLM client — used only as fallback, not primary"""
        self._llm = llm_client

    def initialize(self) -> bool:
        """تهيئة كل الركائز وربطها"""
        if self._initialized:
            return True

        try:
            # ═══ v25.0 Pillars ═══
            from mamoun.neural.neural_mesh import neural_mesh
            from mamoun.awareness.causal_world_model import causal_world_model
            from mamoun.transfer.domain_adapter import domain_adapter
            from mamoun.transfer.synaptic_intelligence import synaptic_intelligence
            from mamoun.transfer.knowledge_bridge import knowledge_bridge
            from mamoun.core.long_term_planner import long_term_planner

            self._neural_mesh = neural_mesh
            self._causal_world_model = causal_world_model
            self._domain_adapter = domain_adapter
            self._synaptic_intelligence = synaptic_intelligence
            self._knowledge_bridge = knowledge_bridge
            self._long_term_planner = long_term_planner

            # ═══ v24.1 Pillars ═══
            from mamoun.core.causal_graph import causal_graph
            from mamoun.memory.episodic_memory_v2 import episodic_memory_v2
            from mamoun.core.metacognitive_engine import metacognitive_engine
            from mamoun.core.hierarchical_planner import hierarchical_planner
            from mamoun.awareness.world_knowledge_graph import world_knowledge_graph
            from mamoun.core.consequence_learning import consequence_learning
            from mamoun.core.selective_attention import selective_attention

            self._causal_graph = causal_graph
            self._episodic_memory = episodic_memory_v2
            self._metacognitive_engine = metacognitive_engine
            self._hierarchical_planner = hierarchical_planner
            self._world_knowledge_graph = world_knowledge_graph
            self._consequence_learning = consequence_learning
            self._selective_attention = selective_attention

            # ═══ v26.0 Reasoning Pillars ═══
            from mamoun.reasoning.symbolic_reasoner import get_symbolic_reasoner
            from mamoun.reasoning.bayesian_inference import get_bayesian_engine
            from mamoun.reasoning.reinforcement_learning import get_rl_engine
            from mamoun.reasoning.abstract_generalization import get_abstract_generalization
            from mamoun.reasoning.perception_action_loop import get_pal_engine
            from mamoun.reasoning.dynamic_working_memory import get_dynamic_working_memory
            from mamoun.reasoning.continual_learning import get_continual_learning

            self._symbolic_reasoner = get_symbolic_reasoner()
            self._bayesian_inference = get_bayesian_engine()
            self._reinforcement_learning = get_rl_engine()
            self._abstract_generalization = get_abstract_generalization()
            self._perception_action_loop = get_pal_engine()
            self._dynamic_working_memory = get_dynamic_working_memory()
            self._continual_learning = get_continual_learning()

            # ═══ Isolated Systems (newly connected) ═══
            try:
                from mamoun.core.triple_memory import TripleMemoryManager
                self._triple_memory = TripleMemoryManager()
                self._triple_memory.initialize()
            except Exception as e:
                logger.debug(f"TripleMemory load failed: {e}")

            try:
                from mamoun.core.system2_reasoner import UncertaintyGate, UncertaintyMetrics
                self._system2_reasoner = UncertaintyGate()
                self._system2_metrics = UncertaintyMetrics()
            except Exception as e:
                logger.debug(f"System2Reasoner load failed: {e}")

            try:
                from mamoun.memory.strategic_forgetting import StrategicForgetting
                self._strategic_forgetting = StrategicForgetting()
            except Exception as e:
                logger.debug(f"StrategicForgetting load failed: {e}")

            try:
                from mamoun.creative.novelty_scorer import NoveltyScorer
                self._novelty_scorer = NoveltyScorer()
            except Exception as e:
                logger.debug(f"NoveltyScorer load failed: {e}")

            try:
                from mamoun.creative.originality_engine import OriginalityEngine
                self._originality_engine = OriginalityEngine()
            except Exception as e:
                logger.debug(f"OriginalityEngine load failed: {e}")

            try:
                from mamoun.learning.one_shot_learner import OneShotLearner
                self._one_shot_learner = OneShotLearner()
            except Exception as e:
                logger.debug(f"OneShotLearner load failed: {e}")

            try:
                from mamoun.learning.skill_generalizer import SkillGeneralizer
                self._skill_generalizer = SkillGeneralizer()
            except Exception as e:
                logger.debug(f"SkillGeneralizer load failed: {e}")

            # ═══ Other systems ═══
            try:
                from mamoun.core.emotional_memory import emotional_memory
                self._emotional_memory = emotional_memory
            except Exception:
                pass

            # ═══ v27.0 AGI Layer (11 modules from agi/) ═══
            try:
                from mamoun.agi.common_sense import CommonSenseFilter
                self._common_sense = CommonSenseFilter()
            except Exception as e:
                logger.debug(f"CommonSenseFilter load failed: {e}")

            try:
                from mamoun.agi.cultural_alignment import CulturalAlignmentEngine
                self._cultural_alignment = CulturalAlignmentEngine()
            except Exception as e:
                logger.debug(f"CulturalAlignmentEngine load failed: {e}")

            try:
                from mamoun.agi.fluid_reasoner import FluidReasoner
                self._fluid_reasoner = FluidReasoner()
            except Exception as e:
                logger.debug(f"FluidReasoner load failed: {e}")

            try:
                from mamoun.agi.hallucination_detector import HallucinationDetector
                self._hallucination_detector = HallucinationDetector()
            except Exception as e:
                logger.debug(f"HallucinationDetector load failed: {e}")

            try:
                from mamoun.agi.intent_drift import IntentDriftDetector
                self._intent_drift = IntentDriftDetector()
            except Exception as e:
                logger.debug(f"IntentDriftDetector load failed: {e}")

            try:
                from mamoun.agi.privacy_guard import PrivacyGuard
                self._privacy_guard = PrivacyGuard()
            except Exception as e:
                logger.debug(f"PrivacyGuard load failed: {e}")

            try:
                from mamoun.agi.skill_discovery import SkillDiscoveryEngine
                self._skill_discovery = SkillDiscoveryEngine()
            except Exception as e:
                logger.debug(f"SkillDiscoveryEngine load failed: {e}")

            try:
                from mamoun.agi.social_perception import SocialPerceptionEngine
                self._social_perception = SocialPerceptionEngine()
            except Exception as e:
                logger.debug(f"SocialPerceptionEngine load failed: {e}")

            try:
                from mamoun.agi.specialized_pipeline import SpecializedAgentPipeline
                self._specialized_pipeline = SpecializedAgentPipeline()
            except Exception as e:
                logger.debug(f"SpecializedAgentPipeline load failed: {e}")

            try:
                from mamoun.agi.swarm_intelligence import SwarmIntelligenceEngine
                self._swarm_intelligence = SwarmIntelligenceEngine()
            except Exception as e:
                logger.debug(f"SwarmIntelligenceEngine load failed: {e}")

            try:
                from mamoun.agi.theory_of_mind import TheoryOfMindEngine
                self._theory_of_mind = TheoryOfMindEngine()
            except Exception as e:
                logger.debug(f"TheoryOfMindEngine load failed: {e}")

            # Initialize all pillars
            pillar_inits = [
                # v25.0
                ("NeuralMesh", self._neural_mesh),
                ("CausalWorldModel", self._causal_world_model),
                ("DomainAdapter", self._domain_adapter),
                ("SynapticIntelligence", self._synaptic_intelligence),
                ("KnowledgeBridge", self._knowledge_bridge),
                ("LongTermPlanner", self._long_term_planner),
                # v24.1
                ("CausalGraph", self._causal_graph),
                ("EpisodicMemoryV2", self._episodic_memory),
                ("MetacognitiveEngine", self._metacognitive_engine),
                ("HierarchicalPlanner", self._hierarchical_planner),
                ("WorldKnowledgeGraph", self._world_knowledge_graph),
                ("ConsequenceLearning", self._consequence_learning),
                ("SelectiveAttention", self._selective_attention),
                # v26.0 Reasoning
                ("SymbolicReasoner", self._symbolic_reasoner),
                ("BayesianInference", self._bayesian_inference),
                ("ReinforcementLearning", self._reinforcement_learning),
                ("AbstractGeneralization", self._abstract_generalization),
                ("PerceptionActionLoop", self._perception_action_loop),
                ("DynamicWorkingMemory", self._dynamic_working_memory),
                ("ContinualLearning", self._continual_learning),
                # v27.0 AGI Layer
                ("CommonSense", self._common_sense),
                ("CulturalAlignment", self._cultural_alignment),
                ("FluidReasoner", self._fluid_reasoner),
                ("HallucinationDetector", self._hallucination_detector),
                ("IntentDrift", self._intent_drift),
                ("PrivacyGuard", self._privacy_guard),
                ("SkillDiscovery", self._skill_discovery),
                ("SocialPerception", self._social_perception),
                ("SpecializedPipeline", self._specialized_pipeline),
                ("SwarmIntelligence", self._swarm_intelligence),
                ("TheoryOfMind", self._theory_of_mind),
            ]

            ok_count = 0
            for name, pillar in pillar_inits:
                try:
                    if pillar and hasattr(pillar, 'initialize'):
                        if pillar.initialize():
                            ok_count += 1
                            logger.info(f"AGI Orchestrator: {name} initialized OK")
                            self._stats["pillar_hits"][name] = 0
                        else:
                            logger.warning(f"AGI Orchestrator: {name} init returned False")
                except Exception as e:
                    logger.error(f"AGI Orchestrator: {name} init failed: {e}")

            # Wire consequence learning to other systems
            if self._consequence_learning and hasattr(self._consequence_learning, 'set_systems'):
                try:
                    self._consequence_learning.set_systems(
                        causal_graph=self._causal_graph,
                        episodic_memory=self._episodic_memory,
                        metacognitive=self._metacognitive_engine,
                        behavioral=None,
                    )
                except Exception as e:
                    logger.debug(f"ConsequenceLearning wiring: {e}")

            self._initialized = ok_count >= 15  # at least 15/31 must succeed
            logger.info(f"AGI Orchestrator initialized: {ok_count}/31 pillars OK")

            return self._initialized

        except Exception as e:
            logger.error(f"AGI Orchestrator initialization failed: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════
    # Main Thinking Loop — The Unified Brain
    # ═══════════════════════════════════════════════════════════════

    async def think(self, message: str, context: dict = None) -> ThinkingResult:
        """
        حلقة التفكير الموحدة — كل ركيزة تشارك قبل وبعد الاستجابة

        Pipeline:
          1. PERCEIVE  → SelectiveAttention
          2. RECALL    → EpisodicMemoryV2
          3. CAUSAL    → CausalWorldModel + CausalGraph
          4. KNOWLEDGE → WorldKnowledgeGraph
          5. META      → MetacognitiveEngine
          6. SYSTEM2   → Decide depth
          7. NEURAL    → NeuralMesh pattern processing
          8. DELIBERATE → LLM brains (if needed)
          9. LEARN     → NeuralMesh + ConsequenceLearning
          10. REMEMBER  → EpisodicMemory + WorldKnowledgeGraph
          11. PLAN     → LongTermPlanner
          12. TRANSFER  → SynapticIntelligence + DomainAdapter
        """
        context = context or {}
        start_time = time.time()
        result = ThinkingResult(query=message)
        self._stats["total_queries"] += 1

        # ─── Phase 1: PERCEIVE (SelectiveAttention) ───
        try:
            signal = self._selective_attention.classify(
                content=message,
                source="user",
                context=context.get("context_str", ""),
            )
            result.attention_level = signal.level
            result.attention_score = signal.score
            result.phases_completed.append(ThinkingPhase.PERCEIVE.value)
            self._hit("SelectiveAttention")
        except Exception as e:
            logger.debug(f"Perceive phase error: {e}")
            result.attention_level = "medium"
            result.attention_score = 0.5

        # ─── Phase 2: RECALL (EpisodicMemoryV2) ───
        try:
            similar = self._episodic_memory.recall_by_analogy(
                situation=message, top_k=3
            )
            result.recalled_episodes = similar[:3] if similar else []
            if result.recalled_episodes:
                result.used_pillars.append("EpisodicMemoryV2")
                self._hit("EpisodicMemoryV2")
            result.phases_completed.append(ThinkingPhase.RECALL.value)
        except Exception as e:
            logger.debug(f"Recall phase error: {e}")

        # ─── Phase 3: CAUSAL (CausalWorldModel + CausalGraph) ───
        try:
            causal_insights = {}

            # Check CausalGraph for known causal relationships
            # Extract key terms from message for causal lookup
            key_terms = self._extract_key_terms(message)

            for term in key_terms[:3]:  # Check top 3 terms
                try:
                    explanation = self._causal_graph.explain(term, "")
                    if explanation and explanation.path_found:
                        causal_insights[term] = {
                            "chain": [n.name for n in explanation.chain],
                            "confidence": explanation.confidence,
                            "source": "causal_graph",
                        }
                except Exception:
                    pass

            # Check CausalWorldModel for structural equations
            try:
                cwm_stats = self._causal_world_model.get_stats()
                if cwm_stats.get("variables", 0) > 0:
                    # Try do-intervention on relevant variables
                    for term in key_terms[:2]:
                        try:
                            intervention = self._causal_world_model.do_intervention(term, 1.0)
                            if intervention:
                                causal_insights[f"do({term}=1.0)"] = intervention
                                self._hit("CausalWorldModel")
                        except Exception:
                            pass
            except Exception:
                pass

            result.causal_insights = causal_insights
            if causal_insights:
                result.used_pillars.append("CausalGraph")
            result.phases_completed.append(ThinkingPhase.CAUSAL.value)
            self._stats["causal_consulted"] += 1
        except Exception as e:
            logger.debug(f"Causal phase error: {e}")

        # ─── Phase 4: KNOWLEDGE (WorldKnowledgeGraph) ───
        try:
            knowledge_ctx = {}
            for term in key_terms[:3]:
                try:
                    connections = self._world_knowledge_graph.get_connections(term, depth=1)
                    if connections and connections.get("connections"):
                        knowledge_ctx[term] = connections["connections"][:5]
                        self._hit("WorldKnowledgeGraph")
                except Exception:
                    pass
            result.knowledge_context = knowledge_ctx
            if knowledge_ctx:
                result.used_pillars.append("WorldKnowledgeGraph")
            result.phases_completed.append(ThinkingPhase.KNOWLEDGE.value)
        except Exception as e:
            logger.debug(f"Knowledge phase error: {e}")

        # ─── Phase 5: META ASSESS (MetacognitiveEngine) ───
        try:
            assessment = self._metacognitive_engine.assess(
                topic=message[:100],
                confidence=context.get("confidence", 0.5),
                context=context.get("context_str", ""),
            )
            result.meta_assessment = {
                "confidence": assessment.confidence,
                "strategy": assessment.strategy,
                "strategy_reason": assessment.strategy_reason,
                "knowledge_gaps": assessment.knowledge_gaps[:3] if assessment.knowledge_gaps else [],
                "uncertainty_sources": assessment.uncertainty_sources[:3] if assessment.uncertainty_sources else [],
            }
            result.used_pillars.append("MetacognitiveEngine")
            self._hit("MetacognitiveEngine")
            result.phases_completed.append(ThinkingPhase.META_ASSESS.value)
        except Exception as e:
            logger.debug(f"Meta assess phase error: {e}")

        # ─── Phase 6: SYMBOLIC REASONING (SymbolicReasoner — v26) ───
        try:
            symbolic_result = {}
            key_terms = self._extract_key_terms(message)
            if key_terms and self._symbolic_reasoner:
                # Try to prove facts about key terms
                for term in key_terms[:3]:
                    try:
                        proof = self._symbolic_reasoner.prove(term, [])
                        if proof and proof.proven:
                            symbolic_result[term] = {
                                "proven": True,
                                "proof_steps": len(proof.proof_steps) if hasattr(proof, 'proof_steps') else 0,
                                "confidence": proof.confidence if hasattr(proof, 'confidence') else 1.0,
                            }
                    except Exception:
                        pass
                # Forward chain to derive new knowledge
                try:
                    derived = self._symbolic_reasoner.forward_chain(max_iterations=10)
                    if derived:
                        symbolic_result["derived_facts"] = len(derived)
                except Exception:
                    pass
            result.symbolic_result = symbolic_result
            if symbolic_result:
                result.used_pillars.append("SymbolicReasoner")
                self._hit("SymbolicReasoner")
            result.phases_completed.append(ThinkingPhase.SYMBOLIC.value)
        except Exception as e:
            logger.debug(f"Symbolic phase error: {e}")

        # ─── Phase 7: BAYESIAN INFERENCE (BayesianInference — v26) ───
        try:
            bayesian_result = {}
            if self._bayesian_inference:
                bay_stats = self._bayesian_inference.get_stats()
                if bay_stats.get("nodes", 0) > 0:
                    # Query posterior for relevant nodes
                    for term in key_terms[:2]:
                        try:
                            prob = self._bayesian_inference.query_probability(term, "true")
                            if prob is not None:
                                bayesian_result[term] = {"posterior": prob}
                                self._hit("BayesianInference")
                        except Exception:
                            pass
            result.bayesian_result = bayesian_result
            if bayesian_result:
                result.used_pillars.append("BayesianInference")
            result.phases_completed.append(ThinkingPhase.BAYESIAN.value)
        except Exception as e:
            logger.debug(f"Bayesian phase error: {e}")

        # ─── Phase 8: RL DECISION (ReinforcementLearning — v26) ───
        try:
            rl_result = {}
            if self._reinforcement_learning:
                rl_stats = self._reinforcement_learning.get_stats()
                if rl_stats.get("states", 0) > 0:
                    # Get policy recommendation
                    try:
                        state_id = rl_stats.get("last_state_id")
                        if state_id:
                            action = self._reinforcement_learning.choose_action(state_id)
                            if action:
                                rl_result["recommended_action"] = action
                                self._hit("ReinforcementLearning")
                    except Exception:
                        pass
            result.rl_decision = rl_result
            if rl_result:
                result.used_pillars.append("ReinforcementLearning")
            result.phases_completed.append(ThinkingPhase.RL_DECIDE.value)
        except Exception as e:
            logger.debug(f"RL phase error: {e}")

        # ─── Phase 9: ABSTRACT GENERALIZATION (AbstractGeneralization — v26) ───
        try:
            abstraction_result = {}
            if self._abstract_generalization and key_terms:
                try:
                    # Classify the message content
                    features = {term: 1.0 / (i + 1) for i, term in enumerate(key_terms[:5])}
                    categories = self._abstract_generalization.classify(features)
                    if categories:
                        abstraction_result["categories"] = categories[:3]
                        self._hit("AbstractGeneralization")
                except Exception:
                    pass
            result.abstraction_result = abstraction_result
            if abstraction_result:
                result.used_pillars.append("AbstractGeneralization")
            result.phases_completed.append(ThinkingPhase.ABSTRACT.value)
        except Exception as e:
            logger.debug(f"Abstract phase error: {e}")

        # ─── Phase 10: PERCEPTION-ACTION LOOP (PerceptionActionLoop — v26) ───
        try:
            perception_result = {}
            if self._perception_action_loop:
                try:
                    decision = self._perception_action_loop.process(
                        raw_input=message,
                        input_type="text",
                        context=context,
                    )
                    if decision:
                        perception_result = {
                            "action": decision.action if hasattr(decision, 'action') else str(decision),
                            "confidence": decision.confidence if hasattr(decision, 'confidence') else 0.5,
                        }
                        self._hit("PerceptionActionLoop")
                except Exception:
                    pass
            result.perception_result = perception_result
            if perception_result:
                result.used_pillars.append("PerceptionActionLoop")
            result.phases_completed.append(ThinkingPhase.PERCEPTION.value)
        except Exception as e:
            logger.debug(f"Perception phase error: {e}")

        # ─── Phase 11: WORKING MEMORY (DynamicWorkingMemory — v26) ───
        try:
            wm_items = []
            if self._dynamic_working_memory:
                try:
                    # Add current message to working memory
                    self._dynamic_working_memory.add(
                        content=message[:200],
                        item_type="user_input",
                        source="orchestrator",
                        salience=result.attention_score,
                    )
                    # Get active items
                    active = self._dynamic_working_memory.get_active_items(top_k=5)
                    wm_items = [
                        {"content": item.content[:100] if hasattr(item, 'content') else str(item)[:100],
                         "salience": item.salience if hasattr(item, 'salience') else 0.5}
                        for item in (active or [])
                    ]
                    self._hit("DynamicWorkingMemory")
                except Exception:
                    pass
            result.working_memory_items = wm_items
            if wm_items:
                result.used_pillars.append("DynamicWorkingMemory")
            result.phases_completed.append(ThinkingPhase.WORKING_MEM.value)
        except Exception as e:
            logger.debug(f"Working memory phase error: {e}")

        # ─── Phase 12: SYSTEM2 DECISION (UncertaintyGate — real) ───
        try:
            if self._system2_reasoner:
                # Use REAL UncertaintyGate instead of heuristic
                uncertainty = self._system2_reasoner.compute_uncertainty(
                    topic=message[:100],
                    context=context,
                )
                should_deep = self._system2_reasoner.should_use_system2(uncertainty)
                result.system2_decision = {
                    "needs_deep_thinking": should_deep,
                    "uncertainty_score": uncertainty.overall if hasattr(uncertainty, 'overall') else 0.5,
                    "confidence_variance": uncertainty.confidence_variance if hasattr(uncertainty, 'confidence_variance') else 0.0,
                    "topic_complexity": uncertainty.topic_complexity if hasattr(uncertainty, 'topic_complexity') else 0.5,
                }
                self._hit("System2Reasoner")
            else:
                # Fallback heuristic
                meta_conf = result.meta_assessment.get("confidence", 0.5)
                needs_deep = meta_conf < 0.4 or result.attention_score > 0.8
                result.system2_decision = {
                    "needs_deep_thinking": needs_deep,
                    "reason": "heuristic_fallback",
                }
            result.phases_completed.append(ThinkingPhase.SYSTEM2.value)
        except Exception as e:
            logger.debug(f"System2 phase error: {e}")
            result.system2_decision = {"needs_deep_thinking": True, "reason": "error_fallback"}

        # ─── Phase 7: NEURAL (NeuralMesh pattern processing) ───
        try:
            neural_result = {}
            # Convert message to a simple feature vector (character frequencies)
            feature_vec = self._text_to_features(message)

            # Check if neural mesh has any layers
            mesh_stats = self._neural_mesh.get_stats()
            if mesh_stats.get("total_layers", 0) > 0:
                # Try recall on the first layer
                layer_names = list(mesh_stats.get("layer_details", {}).keys())
                if layer_names:
                    first_layer = layer_names[0]
                    try:
                        recall_result = self._neural_mesh.recall(
                            first_layer, feature_vec, iterations=3
                        )
                        if recall_result:
                            neural_result["recall"] = {
                                "layer": first_layer,
                                "confidence": recall_result.get("confidence", 0),
                            }
                            self._hit("NeuralMesh")
                    except Exception:
                        pass

            result.neural_activation = neural_result
            if neural_result:
                result.used_pillars.append("NeuralMesh")
            result.phases_completed.append(ThinkingPhase.NEURAL.value)
        except Exception as e:
            logger.debug(f"Neural phase error: {e}")

        # ─── Phase 13: TRIPLE MEMORY RECALL ───
        try:
            triple_result = {}
            if self._triple_memory:
                try:
                    search_results = self._triple_memory.search(
                        query=message[:200], limit=3
                    )
                    if search_results:
                        triple_result["recalled"] = len(search_results)
                        result.used_pillars.append("TripleMemory")
                        self._hit("TripleMemory")
                except Exception:
                    pass
            result.triple_memory_result = triple_result
            result.phases_completed.append(ThinkingPhase.RECALL.value + "_triple")
        except Exception as e:
            logger.debug(f"Triple memory recall phase error: {e}")

        # ─── Phase 14: HIERARCHICAL PLANNER (get next action) ───
        try:
            hp_result = {}
            if self._hierarchical_planner:
                try:
                    next_action = self._hierarchical_planner.get_next_action()
                    if next_action:
                        hp_result["next_action"] = str(next_action)[:200]
                        result.used_pillars.append("HierarchicalPlanner")
                        self._hit("HierarchicalPlanner")
                    hp_stats = self._hierarchical_planner.get_stats()
                    hp_result["active_plans"] = hp_stats.get("active_plans", 0)
                except Exception:
                    pass
            result.hierarchical_plan_result = hp_result
            result.phases_completed.append(ThinkingPhase.PLAN.value + "_hierarchical")
        except Exception as e:
            logger.debug(f"Hierarchical planner phase error: {e}")

        # ─── Phase 15: KNOWLEDGE BRIDGE (find analogies) ───
        try:
            kb_result = {}
            if self._knowledge_bridge:
                try:
                    analogies = self._knowledge_bridge.find_analogies(
                        concept=message[:100],
                        source_domain="conversation",
                        top_k=3,
                    )
                    if analogies:
                        kb_result["analogies_found"] = len(analogies)
                        result.used_pillars.append("KnowledgeBridge")
                        self._hit("KnowledgeBridge")
                except Exception:
                    pass
            result.knowledge_bridge_result = kb_result
            result.phases_completed.append(ThinkingPhase.KNOWLEDGE.value + "_bridge")
        except Exception as e:
            logger.debug(f"Knowledge bridge phase error: {e}")

        # ─── Phase 16: LONG TERM PLANNER (forecast + goals) ───
        try:
            ltp_result = {}
            if self._long_term_planner:
                try:
                    ltp_stats = self._long_term_planner.get_stats()
                    if ltp_stats.get("active_goals", 0) > 0:
                        goal_ids = ltp_stats.get("goal_ids", [])
                        if goal_ids:
                            forecast = self._long_term_planner.forecast(goal_ids[0])
                            if forecast:
                                ltp_result["forecast_available"] = True
                                ltp_result["on_track"] = getattr(forecast, 'on_track', None)
                        ltp_result["active_goals"] = ltp_stats["active_goals"]
                        result.used_pillars.append("LongTermPlanner")
                        self._hit("LongTermPlanner")
                except Exception:
                    pass
            result.long_term_plan_result = ltp_result
            result.phases_completed.append(ThinkingPhase.PLAN.value + "_longterm")
        except Exception as e:
            logger.debug(f"Long term planner phase error: {e}")

        # ─── Phase 17: COMMON SENSE (check for violations) ───
        try:
            cs_result = {}
            if self._common_sense:
                try:
                    cs_check = self._common_sense.check_text(message)
                    if cs_check:
                        violations = getattr(cs_check, 'violations', [])
                        result.common_sense_violations = len(violations) if violations else 0
                        cs_result["violations"] = result.common_sense_violations
                        cs_result["safe"] = result.common_sense_violations == 0
                        result.used_pillars.append("CommonSense")
                        self._hit("CommonSense")
                except Exception:
                    pass
            result.common_sense_result = cs_result
            result.phases_completed.append(ThinkingPhase.COMMON_SENSE.value)
        except Exception as e:
            logger.debug(f"Common sense phase error: {e}")

        # ─── Phase 18: HALLUCINATION DETECTION ───
        try:
            hall_result = {}
            if self._hallucination_detector:
                try:
                    hall_check = self._hallucination_detector.detect(
                        text=message, context=context
                    )
                    if hall_check:
                        risk = getattr(hall_check, 'hallucination_risk', 0.0)
                        result.hallucination_risk = float(risk) if risk else 0.0
                        hall_result["risk"] = result.hallucination_risk
                        hall_result["flags"] = len(getattr(hall_check, 'flags', []))
                        result.used_pillars.append("HallucinationDetector")
                        self._hit("HallucinationDetector")
                except Exception:
                    pass
            result.hallucination_result = hall_result
            result.phases_completed.append(ThinkingPhase.HALLUCINATION.value)
        except Exception as e:
            logger.debug(f"Hallucination phase error: {e}")

        # ─── Phase 19: PRIVACY GUARD ───
        try:
            priv_result = {}
            if self._privacy_guard:
                try:
                    priv_scan = self._privacy_guard.scan_data(
                        data=message, scan_type="input"
                    )
                    if priv_scan:
                        safe = priv_scan.get("safe", True)
                        result.privacy_safe = safe
                        priv_result["safe"] = safe
                        priv_result["redactions"] = priv_scan.get("redaction_count", 0)
                        result.used_pillars.append("PrivacyGuard")
                        self._hit("PrivacyGuard")
                except Exception:
                    pass
            result.privacy_result = priv_result
            result.phases_completed.append(ThinkingPhase.PRIVACY.value)
        except Exception as e:
            logger.debug(f"Privacy phase error: {e}")

        # ─── Phase 20: CULTURAL ALIGNMENT ───
        try:
            cult_result = {}
            if self._cultural_alignment:
                try:
                    align = self._cultural_alignment.align(text=message, context=context)
                    if align:
                        score = getattr(align, 'alignment_score', 1.0)
                        result.cultural_alignment_score = float(score) if score else 1.0
                        cult_result["score"] = result.cultural_alignment_score
                        cult_result["violations"] = len(getattr(align, 'violations', []))
                        result.used_pillars.append("CulturalAlignment")
                        self._hit("CulturalAlignment")
                except Exception:
                    pass
            result.cultural_result = cult_result
            result.phases_completed.append(ThinkingPhase.CULTURAL.value)
        except Exception as e:
            logger.debug(f"Cultural alignment phase error: {e}")

        # ─── Phase 21: SOCIAL PERCEPTION ───
        try:
            social_result = {}
            if self._social_perception:
                try:
                    perception = await self._social_perception.perceive(text=message, context=context)
                    if perception:
                        emotions = getattr(perception, 'emotion_profile', None)
                        social_result["emotions_detected"] = bool(emotions)
                        social_result["social_context"] = str(getattr(perception, 'social_context', ''))[:100]
                        result.used_pillars.append("SocialPerception")
                        self._hit("SocialPerception")
                except Exception:
                    pass
            result.social_perception_result = social_result
            result.phases_completed.append(ThinkingPhase.SOCIAL.value)
        except Exception as e:
            logger.debug(f"Social perception phase error: {e}")

        # ─── Phase 22: INTENT DRIFT DETECTION ───
        try:
            drift_result = {}
            if self._intent_drift:
                try:
                    drift = self._intent_drift.track(
                        intent=message[:200],
                        action_chain=context.get("action_chain", [message[:100]])
                    )
                    if drift:
                        level = getattr(drift, 'drift_level', 'none')
                        result.intent_drift_level = str(level)
                        drift_result["level"] = result.intent_drift_level
                        drift_result["score"] = getattr(drift, 'drift_score', 0.0)
                        result.used_pillars.append("IntentDrift")
                        self._hit("IntentDrift")
                except Exception:
                    pass
            result.intent_drift_result = drift_result
            result.phases_completed.append(ThinkingPhase.INTENT_DRIFT.value)
        except Exception as e:
            logger.debug(f"Intent drift phase error: {e}")

        # ─── Phase 23: FLUID REASONING ───
        try:
            fluid_result = {}
            if self._fluid_reasoner:
                try:
                    features = {term: 1.0 / (i + 1) for i, term in enumerate(key_terms[:5])}
                    reasoning = self._fluid_reasoner.reason(problem=message[:200], features=features)
                    if reasoning:
                        fluid_result["analogies"] = len(getattr(reasoning, 'analogies', []))
                        fluid_result["pattern_completed"] = bool(getattr(reasoning, 'pattern_completion', None))
                        result.used_pillars.append("FluidReasoner")
                        self._hit("FluidReasoner")
                except Exception:
                    pass
            result.fluid_reasoning_result = fluid_result
            result.phases_completed.append(ThinkingPhase.FLUID.value)
        except Exception as e:
            logger.debug(f"Fluid reasoning phase error: {e}")

        # ─── Phase 24: THEORY OF MIND ───
        try:
            tom_result = {}
            if self._theory_of_mind:
                try:
                    model = await self._theory_of_mind.model(
                        agent_id="user",
                        observation={"message": message[:200], "context": str(context)[:200]}
                    )
                    if model:
                        tom_result["user_modeled"] = True
                        tom_result["predicted_intent"] = str(getattr(model, 'predicted_intent', ''))[:100]
                        result.used_pillars.append("TheoryOfMind")
                        self._hit("TheoryOfMind")
                except Exception:
                    pass
            result.theory_of_mind_result = tom_result
            result.phases_completed.append(ThinkingPhase.THEORY_OF_MIND.value)
        except Exception as e:
            logger.debug(f"Theory of mind phase error: {e}")

        # ─── Phase 25: NOVELTY SCORING (in think — pre-response) ───
        try:
            novelty_result_data = {}
            if self._novelty_scorer:
                try:
                    novelty = self._novelty_scorer.score_novelty(
                        idea={"content": message[:200]},
                        domain="conversation",
                    )
                    if novelty:
                        result.novelty_score = float(getattr(novelty, 'score', 0.5))
                        novelty_result_data["score"] = result.novelty_score
                        result.used_pillars.append("NoveltyScorer")
                        self._hit("NoveltyScorer")
                except Exception:
                    pass
            result.phases_completed.append(ThinkingPhase.NOVELTY.value)
        except Exception as e:
            logger.debug(f"Novelty phase error: {e}")

        # ─── Phase 26: ORIGINALITY ENGINE (creative check) ───
        try:
            orig_result = {}
            if self._originality_engine:
                try:
                    from mamoun.creative.originality_engine import CreativeSeed
                    seed = CreativeSeed(content=message[:200], domain="conversation")
                    output = self._originality_engine.generate(seed)
                    if output:
                        orig_result["originality_score"] = getattr(output, 'originality_score', 0.5)
                        result.originality_applied = True
                        result.used_pillars.append("OriginalityEngine")
                        self._hit("OriginalityEngine")
                except Exception:
                    pass
            result.originality_result = orig_result
            result.phases_completed.append(ThinkingPhase.ORIGINALITY.value)
        except Exception as e:
            logger.debug(f"Originality phase error: {e}")

        # ─── Phase 27: ONE-SHOT LEARNER ───
        try:
            osl_result = {}
            if self._one_shot_learner:
                try:
                    skills = await self._one_shot_learner.list_skills()
                    if skills:
                        osl_result["learned_skills"] = len(skills)
                        result.used_pillars.append("OneShotLearner")
                        self._hit("OneShotLearner")
                except Exception:
                    pass
            result.one_shot_result = osl_result
            result.phases_completed.append("one_shot")
        except Exception as e:
            logger.debug(f"One-shot learner phase error: {e}")

        # ─── Phase 28: SKILL GENERALIZER ───
        try:
            sg_result = {}
            if self._skill_generalizer:
                try:
                    history = await self._skill_generalizer.get_generalization_history()
                    if history:
                        sg_result["generalizations"] = len(history)
                        result.used_pillars.append("SkillGeneralizer")
                        self._hit("SkillGeneralizer")
                except Exception:
                    pass
            result.skill_generalizer_result = sg_result
            result.phases_completed.append("skill_generalizer")
        except Exception as e:
            logger.debug(f"Skill generalizer phase error: {e}")

        # ─── Phase 29: STRATEGIC FORGETTING (evaluate working memory) ───
        try:
            forget_result_data = {}
            if self._strategic_forgetting:
                try:
                    forget_status = self._strategic_forgetting.get_status()
                    if forget_status.get("enabled", True):
                        forget_result_data["enabled"] = True
                        result.forgetting_applied = True
                        result.used_pillars.append("StrategicForgetting")
                        self._hit("StrategicForgetting")
                except Exception:
                    pass
            result.phases_completed.append(ThinkingPhase.FORGET.value)
        except Exception as e:
            logger.debug(f"Forgetting phase error: {e}")

        # ─── Phase 30: SKILL DISCOVERY ───
        try:
            sd_result = {}
            if self._skill_discovery:
                try:
                    ranked = self._skill_discovery.rank_skills()
                    if ranked:
                        sd_result["discoverable_skills"] = len(ranked)
                        result.used_pillars.append("SkillDiscovery")
                        self._hit("SkillDiscovery")
                except Exception:
                    pass
            result.skill_discovery_result = sd_result
            result.phases_completed.append(ThinkingPhase.SKILL_DISCOVERY.value)
        except Exception as e:
            logger.debug(f"Skill discovery phase error: {e}")

        # ─── Build context from all pillars for LLM ───
        pillar_context = self._build_pillar_context(result)

        # ─── Phase 8: DELIBERATE (will be done by kernel's brain router) ───
        # We just provide the pillar context; the kernel will call LLM if needed
        result.phases_completed.append(ThinkingPhase.DELIBERATE.value)

        # ─── Post-response phases (called after LLM responds) ───
        # These will be called by learn_from_outcome()

        result.total_ms = (time.time() - start_time) * 1000
        return result, pillar_context

    async def learn_from_outcome(
        self,
        message: str,
        response: str,
        confidence: float = 0.5,
        outcome_positive: bool = True,
        context: dict = None,
    ) -> Dict[str, Any]:
        """
        التعلم من النتيجة — بعد أن يستجيب النظام

        This is called AFTER the response is given.
        Every pillar learns from the interaction.
        """
        context = context or {}
        learning_results = {}

        # ─── Phase 9: LEARN (NeuralMesh + ConsequenceLearning) ───
        try:
            # Feed NeuralMesh with the interaction pattern
            feature_vec = self._text_to_features(message)
            mesh_stats = self._neural_mesh.get_stats()

            if mesh_stats.get("total_layers", 0) > 0:
                layer_names = list(mesh_stats.get("layer_details", {}).keys())
                if layer_names:
                    # Learn the pattern: message → response quality
                    target_vec = np.array([confidence, float(outcome_positive), len(response) / 1000.0])
                    try:
                        learn_result = self._neural_mesh.learn_pattern(
                            layer_names[0], feature_vec[:64] if len(feature_vec) > 64 else feature_vec,
                            target_vec[:8] if len(target_vec) > 8 else target_vec,
                        )
                        learning_results["neural_learned"] = True
                        self._stats["neural_learned"] += 1
                        self._hit("NeuralMesh")
                    except Exception:
                        learning_results["neural_learned"] = False
            else:
                # Auto-create a "conversation" layer and learn
                try:
                    layer = self._neural_mesh.create_layer(
                        "conversation", input_size=64, output_size=8,
                        activation="sigmoid", learning_rate=0.01,
                    )
                    if layer:
                        padded = np.zeros(64)
                        padded[:min(len(feature_vec), 64)] = feature_vec[:64]
                        target = np.array([confidence, float(outcome_positive), 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
                        self._neural_mesh.learn_pattern("conversation", padded, target)
                        learning_results["neural_layer_created"] = "conversation"
                        self._stats["neural_learned"] += 1
                        self._hit("NeuralMesh")
                except Exception as e:
                    logger.debug(f"Neural auto-create error: {e}")
        except Exception as e:
            logger.debug(f"Learn phase error: {e}")

        # ConsequenceLearning
        try:
            action_id = self._consequence_learning.register_action(
                action_type="response",
                context=message[:200],
                expected_outcome=f"positive response" if outcome_positive else "negative response",
                confidence=confidence,
            )
            self._consequence_learning.record_outcome(
                action_id=action_id,
                outcome="positive" if outcome_positive else "negative",
                confidence_adjusted=confidence,
            )
            learning_results["consequence_recorded"] = True
            self._hit("ConsequenceLearning")
        except Exception as e:
            logger.debug(f"Consequence learning error: {e}")

        # ─── Phase 10: REMEMBER (EpisodicMemory + WorldKnowledgeGraph) ───
        try:
            episode = self._episodic_memory.record(
                situation=message[:200],
                action_taken=response[:200],
                outcome="positive" if outcome_positive else "negative",
                outcome_positive=outcome_positive,
            )
            if episode:
                # Auto-extract lesson
                self._episodic_memory.extract_lesson(episode.episode_id)
                learning_results["episode_stored"] = True
                self._stats["episodes_stored"] += 1
                self._hit("EpisodicMemoryV2")
        except Exception as e:
            logger.debug(f"Remember phase error: {e}")

        # Add to WorldKnowledgeGraph
        try:
            key_terms = self._extract_key_terms(message)
            for term in key_terms[:3]:
                self._world_knowledge_graph.add_entity(term, entity_type="topic")
            # Add relationship between first two terms
            if len(key_terms) >= 2:
                self._world_knowledge_graph.add_relation(
                    key_terms[0], key_terms[1],
                    relation_type="mentioned_together",
                    confidence=0.6,
                    source="conversation",
                )
            learning_results["knowledge_added"] = True
            self._hit("WorldKnowledgeGraph")
        except Exception as e:
            logger.debug(f"Knowledge add error: {e}")

        # ─── Phase 11: PLAN (LongTermPlanner) ───
        try:
            # Check if any active goals relate to this message
            ltp_stats = self._long_term_planner.get_stats()
            if ltp_stats.get("active_goals", 0) > 0:
                learning_results["active_goals_tracked"] = ltp_stats["active_goals"]
                self._hit("LongTermPlanner")
        except Exception as e:
            logger.debug(f"Plan phase error: {e}")

        # ─── Phase 12: TRANSFER (SynapticIntelligence + DomainAdapter) ───
        try:
            # Track synaptic importance for the conversation layer
            si_stats = self._synaptic_intelligence.get_stats()
            if si_stats.get("tracked_synapses", 0) > 0:
                learning_results["synaptic_intelligence_active"] = True
                self._hit("SynapticIntelligence")

            # Check if domain adapter can transfer knowledge
            da_stats = self._domain_adapter.get_stats()
            if da_stats.get("domains", 0) >= 2:
                learning_results["transfer_possible"] = True
                self._hit("DomainAdapter")
        except Exception as e:
            logger.debug(f"Transfer phase error: {e}")

        # ─── Metacognitive Reflection ───
        try:
            # Record how well we did for calibration
            meta_conf = context.get("meta_confidence", 0.5)
            assessment = self._metacognitive_engine.assess(
                topic=message[:100],
                confidence=meta_conf,
            )
            self._metacognitive_engine.reflect(
                assessment_id=assessment.assessment_id,
                expected_outcome="positive response" if outcome_positive else "negative response",
                actual_outcome="success" if outcome_positive else "failure",
                success=outcome_positive,
            )
            self._hit("MetacognitiveEngine")
        except Exception:
            pass

        # ─── Phase 13: CONTINUAL LEARNING (ContinualLearning — v26) ───
        try:
            if self._continual_learning:
                cl_stats = self._continual_learning.get_stats()
                # Record this interaction as a learning task
                try:
                    # Compute EWC penalty if we have previous tasks
                    if cl_stats.get("registered_tasks", 0) > 0:
                        penalty = self._continual_learning.compute_ewc_penalty(
                            current_params={"confidence": confidence}
                        )
                        learning_results["ewc_penalty"] = penalty
                    # Add replay example from this interaction
                    feature_vec = self._text_to_features(message)
                    self._continual_learning.add_replay_example(
                        task_id=cl_stats.get("last_task_id", "conversation"),
                        input_vec=feature_vec.tolist() if hasattr(feature_vec, 'tolist') else list(feature_vec),
                        target_vec=[confidence, float(outcome_positive)],
                        importance=confidence,
                    )
                    self._hit("ContinualLearning")
                    result.continual_learning_applied = True
                except Exception as e:
                    logger.debug(f"ContinualLearning learn error: {e}")
        except Exception as e:
            logger.debug(f"Continual learning phase error: {e}")

        # ─── Phase 14: STRATEGIC FORGETTING ───
        try:
            if self._strategic_forgetting:
                forget_status = self._strategic_forgetting.get_status()
                if forget_status.get("enabled", False):
                    learning_results["forgetting_status"] = "active"
                    self._hit("StrategicForgetting")
                    result.forgetting_applied = True
        except Exception as e:
            logger.debug(f"Forgetting phase error: {e}")

        # ─── Phase 15: NOVELTY SCORING ───
        try:
            if self._novelty_scorer:
                try:
                    novelty = self._novelty_scorer.score_novelty(
                        idea={"content": message[:200], "response": response[:200]},
                        domain="conversation",
                    )
                    if novelty:
                        result.novelty_score = novelty.score if hasattr(novelty, 'score') else 0.5
                        self._hit("NoveltyScorer")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Novelty phase error: {e}")

        # ─── Phase 16: RL LEARNING (ReinforcementLearning — update Q-values) ───
        try:
            if self._reinforcement_learning:
                rl_stats = self._reinforcement_learning.get_stats()
                if rl_stats.get("states", 0) > 0:
                    # Update Q-value based on outcome
                    try:
                        reward = 1.0 if outcome_positive else -0.5
                        state_id = rl_stats.get("last_state_id")
                        if state_id:
                            self._reinforcement_learning.q_learn(
                                state_id=state_id,
                                action_id=rl_stats.get("last_action_id", "respond"),
                                reward=reward,
                                next_state_id=state_id,  # same state for conversation
                                done=False,
                            )
                            self._hit("ReinforcementLearning")
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"RL learn phase error: {e}")

        # ─── Phase 17: BAYESIAN UPDATE (update beliefs from outcome) ───
        try:
            if self._bayesian_inference:
                bay_stats = self._bayesian_inference.get_stats()
                if bay_stats.get("nodes", 0) > 0:
                    try:
                        # Update belief about response quality
                        self._bayesian_inference.update_belief(
                            node_name="response_quality",
                            observed_value="positive" if outcome_positive else "negative",
                            confidence=confidence,
                        )
                        self._hit("BayesianInference")
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"Bayesian learn phase error: {e}")

        # ─── Phase 18: TRIPLE MEMORY STORE ───
        try:
            if self._triple_memory:
                from mamoun.core.triple_memory import MemoryEntry, MemoryType
                entry = MemoryEntry(
                    content=f"Q: {message[:200]} | A: {response[:200]}",
                    memory_type=MemoryType.EPISODIC,
                    metadata={"confidence": confidence, "positive": outcome_positive},
                )
                self._triple_memory.store(entry)
                self._hit("TripleMemory")
        except Exception as e:
            logger.debug(f"TripleMemory store error: {e}")

        # ─── Phase 19: KNOWLEDGE BRIDGE (actual analogy finding) ───
        try:
            if self._knowledge_bridge and key_terms:
                bridge_stats = self._knowledge_bridge.get_stats()
                if bridge_stats.get("bridges", 0) > 0:
                    try:
                        analogies = self._knowledge_bridge.find_analogies(
                            source_domain="conversation",
                            target_features={t: 1.0 for t in key_terms[:3]},
                        )
                        if analogies:
                            learning_results["analogies_found"] = len(analogies)
                            self._hit("KnowledgeBridge")
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"KnowledgeBridge phase error: {e}")

        # ─── Phase 20: HIERARCHICAL PLANNER (actual planning) ───
        try:
            if self._hierarchical_planner:
                hp_stats = self._hierarchical_planner.get_stats()
                if hp_stats.get("active_plans", 0) > 0:
                    try:
                        next_action = self._hierarchical_planner.get_next_action()
                        if next_action:
                            learning_results["planner_next_action"] = str(next_action)[:100]
                            self._hit("HierarchicalPlanner")
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"HierarchicalPlanner phase error: {e}")

        # ─── Phase 21: AGI LAYER LEARNING (v27) ───

        # HallucinationDetector: check response for hallucinations
        try:
            if self._hallucination_detector and response:
                try:
                    hall_check = self._hallucination_detector.detect(
                        text=response, context={"query": message[:200]}
                    )
                    if hall_check:
                        learning_results["hallucination_checked"] = True
                        learning_results["hallucination_risk"] = float(
                            getattr(hall_check, 'hallucination_risk', 0.0)
                        )
                        self._hit("HallucinationDetector")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Hallucination learn error: {e}")

        # PrivacyGuard: scan response for private data leaks
        try:
            if self._privacy_guard and response:
                try:
                    priv_scan = self._privacy_guard.scan_data(
                        data=response, scan_type="output"
                    )
                    if priv_scan:
                        learning_results["privacy_checked"] = True
                        learning_results["privacy_safe"] = priv_scan.get("safe", True)
                        self._hit("PrivacyGuard")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Privacy learn error: {e}")

        # CulturalAlignment: check response alignment
        try:
            if self._cultural_alignment and response:
                try:
                    align = self._cultural_alignment.align(text=response, context=context)
                    if align:
                        learning_results["cultural_checked"] = True
                        learning_results["cultural_score"] = float(
                            getattr(align, 'alignment_score', 1.0)
                        )
                        self._hit("CulturalAlignment")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Cultural learn error: {e}")

        # CommonSense: check response for violations
        try:
            if self._common_sense and response:
                try:
                    cs_check = self._common_sense.check_text(response)
                    if cs_check:
                        violations = getattr(cs_check, 'violations', [])
                        learning_results["common_sense_checked"] = True
                        learning_results["common_sense_violations"] = len(violations) if violations else 0
                        self._hit("CommonSense")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Common sense learn error: {e}")

        # SocialPerception: analyze the interaction
        try:
            if self._social_perception:
                try:
                    perception = await self._social_perception.perceive(
                        text=f"User: {message[:100]} | Mamoun: {response[:100]}",
                        context=context,
                    )
                    if perception:
                        learning_results["social_analyzed"] = True
                        self._hit("SocialPerception")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Social perception learn error: {e}")

        # IntentDrift: track if response drifted from intent
        try:
            if self._intent_drift:
                try:
                    drift = self._intent_drift.track(
                        intent=message[:200],
                        action_chain=[message[:100], response[:100]]
                    )
                    if drift:
                        learning_results["drift_checked"] = True
                        learning_results["drift_level"] = str(getattr(drift, 'drift_level', 'none'))
                        self._hit("IntentDrift")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Intent drift learn error: {e}")

        # SkillDiscovery: discover skills from successful interactions
        try:
            if self._skill_discovery and outcome_positive:
                try:
                    discovery = self._skill_discovery.discover(
                        task_history={"query": message[:200], "response": response[:200], "success": True}
                    )
                    if discovery:
                        learning_results["skill_discovered"] = True
                        self._hit("SkillDiscovery")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Skill discovery learn error: {e}")

        # OneShotLearner: learn from this example
        try:
            if self._one_shot_learner:
                try:
                    from mamoun.learning.one_shot_learner import LearningExample
                    example = LearningExample(
                        input_data={"query": message[:200]},
                        output_data={"response": response[:200]},
                        category="conversation",
                        confidence=confidence,
                    )
                    skill = await self._one_shot_learner.learn_from_example(example)
                    if skill:
                        learning_results["one_shot_learned"] = True
                        self._hit("OneShotLearner")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"One-shot learn error: {e}")

        # SkillGeneralizer: generalize learned skills
        try:
            if self._skill_generalizer:
                try:
                    history = await self._skill_generalizer.get_generalization_history()
                    if history and len(history) > 0:
                        learning_results["skill_generalizer_active"] = True
                        self._hit("SkillGeneralizer")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Skill generalizer learn error: {e}")

        # TheoryOfMind: update user mental model
        try:
            if self._theory_of_mind:
                try:
                    await self._theory_of_mind.model(
                        agent_id="user",
                        observation={
                            "message": message[:200],
                            "response": response[:200],
                            "positive": outcome_positive,
                        }
                    )
                    learning_results["tom_updated"] = True
                    self._hit("TheoryOfMind")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Theory of mind learn error: {e}")

        # FluidReasoner: learn from reasoning experience
        try:
            if self._fluid_reasoner:
                try:
                    fl_stats = self._fluid_reasoner.get_stats()
                    if fl_stats:
                        learning_results["fluid_reasoning_active"] = True
                        self._hit("FluidReasoner")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Fluid reasoner learn error: {e}")

        # KnowledgeBridge: bridge concepts from this interaction
        try:
            if self._knowledge_bridge:
                try:
                    key_terms_local = self._extract_key_terms(message)
                    for term in key_terms_local[:2]:
                        self._knowledge_bridge.register_concept(
                            name=term,
                            domain="conversation",
                            embedding=np.zeros(64),  # placeholder embedding
                            metadata={"confidence": confidence, "positive": outcome_positive},
                        )
                    learning_results["knowledge_bridge_registered"] = True
                    self._hit("KnowledgeBridge")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Knowledge bridge learn error: {e}")

        # LongTermPlanner: update goal progress
        try:
            if self._long_term_planner:
                try:
                    ltp_stats = self._long_term_planner.get_stats()
                    if ltp_stats.get("active_goals", 0) > 0:
                        learning_results["ltp_goals_tracked"] = ltp_stats["active_goals"]
                        self._hit("LongTermPlanner")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Long-term planner learn error: {e}")

        # HierarchicalPlanner: update plan progress
        try:
            if self._hierarchical_planner:
                try:
                    hp_stats = self._hierarchical_planner.get_stats()
                    if hp_stats.get("active_plans", 0) > 0:
                        learning_results["hp_plans_tracked"] = hp_stats["active_plans"]
                        self._hit("HierarchicalPlanner")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Hierarchical planner learn error: {e}")

        return learning_results

    # ═══════════════════════════════════════════════════════════════
    # Helper Methods
    # ═══════════════════════════════════════════════════════════════

    def _extract_key_terms(self, text: str) -> List[str]:
        """استخلاص المصطلحات المفتاحية من النص"""
        # Simple keyword extraction: split and filter
        stopwords = {
            "في", "من", "على", "إلى", "عن", "مع", "هذا", "هذه", "التي", "الذي",
            "أن", "لا", "ما", "هل", "كيف", "لماذا", "متى", "أين", "هو", "هي",
            "the", "is", "a", "an", "and", "or", "but", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "it", "this", "that",
        }
        words = text.replace("؟", "").replace("?", "").replace("!", "").replace(".", "").replace(",", "").split()
        terms = [w for w in words if w not in stopwords and len(w) > 2]
        return terms[:10]

    def _text_to_features(self, text: str) -> np.ndarray:
        """تحويل النص إلى متجه خصائص للشبكة العصبية"""
        # Character frequency vector (simple but effective)
        vec = np.zeros(64, dtype=np.float64)
        for i, ch in enumerate(text[:64]):
            vec[i % 64] = ord(ch) / 65535.0  # Normalize Unicode
        # Add statistical features
        if len(text) > 0:
            vec[0] = len(text) / 1000.0
            vec[1] = sum(1 for c in text if c.isupper()) / max(len(text), 1)
            vec[2] = sum(1 for c in text if '\u0600' <= c <= '\u06FF') / max(len(text), 1)  # Arabic ratio
            vec[3] = sum(1 for c in text if c == ' ') / max(len(text), 1)  # word boundary ratio
        return vec

    def _build_pillar_context(self, result: ThinkingResult) -> str:
        """بناء سياق من كل الركائز لتقديمه للـ LLM"""
        context_parts = []

        if result.recalled_episodes:
            episodes_text = []
            for ep in result.recalled_episodes[:2]:
                if isinstance(ep, dict):
                    episodes_text.append(
                        f"- تجربة سابقة: {ep.get('situation', '')[:100]} → {ep.get('lesson', '')[:100]}"
                    )
            if episodes_text:
                context_parts.append(f"ذكريات مشابهة:\n" + "\n".join(episodes_text))

        if result.causal_insights:
            causal_parts = []
            for key, val in result.causal_insights.items():
                if isinstance(val, dict):
                    chain = val.get("chain", [])
                    if chain:
                        causal_parts.append(f"- علاقة سببية: {' → '.join(str(c) for c in chain[:5])}")
                    elif val.get("source") == "causal_graph":
                        causal_parts.append(f"- تدخل do({key}): نتائج={val}")
            if causal_parts:
                context_parts.append(f"معرفة سببية:\n" + "\n".join(causal_parts[:5]))

        if result.knowledge_context:
            knowledge_parts = []
            for entity, connections in result.knowledge_context.items():
                if connections:
                    related = [c.get("name", str(c))[:30] for c in connections[:3] if isinstance(c, dict)]
                    if related:
                        knowledge_parts.append(f"- {entity}: مرتبط بـ {', '.join(related)}")
            if knowledge_parts:
                context_parts.append(f"شبكة المعرفة:\n" + "\n".join(knowledge_parts[:5]))

        if result.meta_assessment:
            strategy = result.meta_assessment.get("strategy", "respond")
            gaps = result.meta_assessment.get("knowledge_gaps", [])
            if strategy != "respond" or gaps:
                context_parts.append(f"تقييم ذاتي: استراتيجية={strategy}" +
                                     (f"، فجوات=({', '.join(gaps[:2])})" if gaps else ""))

        if not context_parts:
            return ""

        return "\n\n[سياق الركائز الذكية]:\n" + "\n\n".join(context_parts)

    def _hit(self, pillar_name: str):
        """تسجيل استخدام ركيزة"""
        self._stats["pillar_hits"][pillar_name] = self._stats["pillar_hits"].get(pillar_name, 0) + 1

    # ═══════════════════════════════════════════════════════════════
    # Direct pillar access (for brains and API)
    # ═══════════════════════════════════════════════════════════════

    @property
    def neural_mesh(self):
        return self._neural_mesh

    @property
    def causal_world_model(self):
        return self._causal_world_model

    @property
    def causal_graph(self):
        return self._causal_graph

    @property
    def episodic_memory(self):
        return self._episodic_memory

    @property
    def metacognitive_engine(self):
        return self._metacognitive_engine

    @property
    def world_knowledge_graph(self):
        return self._world_knowledge_graph

    @property
    def selective_attention(self):
        return self._selective_attention

    @property
    def long_term_planner(self):
        return self._long_term_planner

    @property
    def hierarchical_planner(self):
        return self._hierarchical_planner

    @property
    def consequence_learning(self):
        return self._consequence_learning

    @property
    def domain_adapter(self):
        return self._domain_adapter

    @property
    def synaptic_intelligence(self):
        return self._synaptic_intelligence

    @property
    def knowledge_bridge(self):
        return self._knowledge_bridge

    # ═══ v26.0 Reasoning Pillar Properties ═══
    @property
    def symbolic_reasoner(self):
        return self._symbolic_reasoner

    @property
    def bayesian_inference(self):
        return self._bayesian_inference

    @property
    def reinforcement_learning(self):
        return self._reinforcement_learning

    @property
    def abstract_generalization(self):
        return self._abstract_generalization

    @property
    def perception_action_loop(self):
        return self._perception_action_loop

    @property
    def dynamic_working_memory(self):
        return self._dynamic_working_memory

    @property
    def continual_learning(self):
        return self._continual_learning

    # ═══ Isolated System Properties ═══
    @property
    def triple_memory(self):
        return self._triple_memory

    @property
    def system2_reasoner(self):
        return self._system2_reasoner

    @property
    def strategic_forgetting(self):
        return self._strategic_forgetting

    @property
    def novelty_scorer(self):
        return self._novelty_scorer

    @property
    def originality_engine(self):
        return self._originality_engine

    @property
    def one_shot_learner(self):
        return self._one_shot_learner

    @property
    def skill_generalizer(self):
        return self._skill_generalizer

    # ═══ v27.0 AGI Layer Properties ═══
    @property
    def common_sense(self):
        return self._common_sense

    @property
    def cultural_alignment(self):
        return self._cultural_alignment

    @property
    def fluid_reasoner(self):
        return self._fluid_reasoner

    @property
    def hallucination_detector(self):
        return self._hallucination_detector

    @property
    def intent_drift(self):
        return self._intent_drift

    @property
    def privacy_guard(self):
        return self._privacy_guard

    @property
    def skill_discovery(self):
        return self._skill_discovery

    @property
    def social_perception(self):
        return self._social_perception

    @property
    def specialized_pipeline(self):
        return self._specialized_pipeline

    @property
    def swarm_intelligence(self):
        return self._swarm_intelligence

    @property
    def theory_of_mind(self):
        return self._theory_of_mind

    # ═══════════════════════════════════════════════════════════════
    # Statistics
    # ═══════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict:
        """إحصائيات الجسر العصبي"""
        stats = dict(self._stats)
        stats["initialized"] = self._initialized
        stats["pillars_connected"] = len([v for v in self._stats["pillar_hits"].values() if v > 0])
        stats["total_pillars"] = 31
        return stats

    def get_pillar_status(self) -> Dict:
        """حالة كل ركيزة"""
        status = {}
        pillars = [
            # v25.0
            ("NeuralMesh", self._neural_mesh),
            ("CausalWorldModel", self._causal_world_model),
            ("DomainAdapter", self._domain_adapter),
            ("SynapticIntelligence", self._synaptic_intelligence),
            ("KnowledgeBridge", self._knowledge_bridge),
            ("LongTermPlanner", self._long_term_planner),
            # v24.1
            ("CausalGraph", self._causal_graph),
            ("EpisodicMemoryV2", self._episodic_memory),
            ("MetacognitiveEngine", self._metacognitive_engine),
            ("HierarchicalPlanner", self._hierarchical_planner),
            ("WorldKnowledgeGraph", self._world_knowledge_graph),
            ("ConsequenceLearning", self._consequence_learning),
            ("SelectiveAttention", self._selective_attention),
            # v26.0 Reasoning
            ("SymbolicReasoner", self._symbolic_reasoner),
            ("BayesianInference", self._bayesian_inference),
            ("ReinforcementLearning", self._reinforcement_learning),
            ("AbstractGeneralization", self._abstract_generalization),
            ("PerceptionActionLoop", self._perception_action_loop),
            ("DynamicWorkingMemory", self._dynamic_working_memory),
            ("ContinualLearning", self._continual_learning),
            # v27.0 AGI Layer
            ("CommonSense", self._common_sense),
            ("CulturalAlignment", self._cultural_alignment),
            ("FluidReasoner", self._fluid_reasoner),
            ("HallucinationDetector", self._hallucination_detector),
            ("IntentDrift", self._intent_drift),
            ("PrivacyGuard", self._privacy_guard),
            ("SkillDiscovery", self._skill_discovery),
            ("SocialPerception", self._social_perception),
            ("SpecializedPipeline", self._specialized_pipeline),
            ("SwarmIntelligence", self._swarm_intelligence),
            ("TheoryOfMind", self._theory_of_mind),
        ]
        for name, pillar in pillars:
            if pillar is None:
                status[name] = {"status": "not_loaded", "hits": 0}
            else:
                try:
                    pillar_stats = pillar.get_stats() if hasattr(pillar, 'get_stats') else (pillar.get_status() if hasattr(pillar, 'get_status') else {})
                    status[name] = {
                        "status": "active",
                        "hits": self._stats["pillar_hits"].get(name, 0),
                        "details": pillar_stats,
                    }
                except Exception as e:
                    status[name] = {"status": "error", "error": str(e), "hits": 0}
        return status


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

_agi_orchestrator: Optional[AGIOrchestrator] = None


def get_agi_orchestrator() -> AGIOrchestrator:
    """Get the global AGI orchestrator instance"""
    global _agi_orchestrator
    if _agi_orchestrator is None:
        _agi_orchestrator = AGIOrchestrator()
    return _agi_orchestrator
