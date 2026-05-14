"""
BABSHARQII (Mamoun) v6.0 — AGI Theory of Mind (ToM) Engine
محرك نظرية العقل لطبقة AGI — القدرة على استنتاج معتقدات ورغبات ونوايا الوكلاء الآخرين

Implements a comprehensive Theory of Mind system for AGI-level social cognition,
inspired by:
  • Adaptive ToM (AAAI 2026, arXiv:2603.16264) — depth-adjustable mental modeling
    based on partner predictability: high predictability → shallow model (fast),
    low predictability → deep model (more computation, better prediction).
  • MetaMind (NeurIPS 2025 Spotlight, arXiv:2505.18943) — general cognitive model
    of the world with reverse inference from behavior to beliefs/desires and
    hierarchical mental modeling (I think that you think that I think…).

Architecture:
  ┌────────────────────────────────────────────────────────────────────┐
  │                     TheoryOfMindEngine                             │
  │                                                                    │
  │  ┌──────────────────────┐  ┌────────────────────────────────────┐ │
  │  │ MentalModelTracker   │  │ BeliefInferenceEngine              │ │
  │  │ (multi-agent models, │  │ (knowledge state, partial          │ │
  │  │  confidence tracking)│  │  observability, misconceptions)    │ │
  │  └──────────┬───────────┘  └──────────────┬─────────────────────┘ │
  │             │                             │                        │
  │  ┌──────────▼─────────────────────────────▼────────────────────┐ │
  │  │               IntentionPredictor                             │ │
  │  │  (BDI architecture: beliefs + desires → predicted actions,  │ │
  │  │   cooperation & deception assessment)                       │ │
  │  └──────────────────────────┬──────────────────────────────────┘ │
  │                             │                                      │
  │  ┌──────────────────────────▼──────────────────────────────────┐ │
  │  │               SocialCognitionEngine                         │ │
  │  │  (relationship modeling, social dynamics, cultural          │ │
  │  │   awareness including Arab hospitality norms)               │ │
  │  └────────────────────────────────────────────────────────────┘ │
  └────────────────────────────────────────────────────────────────────┘

Env toggles:
    MAMOUN_THEORY_OF_MIND_ENABLED     — تمكين/تعطيل نظرية العقل (الافتراضي: false)
    MAMOUN_TOM_MAX_NESTING_DEPTH      — أقصى عمق للنمذجة المتداخلة (الافتراضي: 3)
    MAMOUN_TOM_CONFIDENCE_THRESHOLD   — عتبة الثقة الدنيا (الافتراضي: 0.5)
"""

from __future__ import annotations

import os
import time
import uuid
import math
import logging
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)

# ─── مفاتيح التهيئة البيئية — Environment Config ─────────────────────────────

TOM_ENABLED: bool = os.environ.get(
    "MAMOUN_THEORY_OF_MIND_ENABLED", "false"
).lower() in ("true", "1", "yes")

TOM_MAX_NESTING_DEPTH: int = int(
    os.environ.get("MAMOUN_TOM_MAX_NESTING_DEPTH", "3")
)

TOM_CONFIDENCE_THRESHOLD: float = float(
    os.environ.get("MAMOUN_TOM_CONFIDENCE_THRESHOLD", "0.5")
)


# ═══════════════════════════════════════════════════════════════════════════════
#  التعدادات — Enumerations
# ═══════════════════════════════════════════════════════════════════════════════


class AgentType(str, Enum):
    """
    نوع الوكيل — نوع الكيان الذي نموذجه العقلي.
    Type of agent being modeled.
    """
    HUMAN = "human"            # مستخدم بشري — human user
    AI_AGENT = "ai_agent"      # وكيل ذكاء اصطناعي — other AI agent
    GROUP = "group"            # كيان جماعي — group entity


class DeceptionRiskLevel(str, Enum):
    """
    مستوى خطر الخداع — مستوى احتمال وجود خداع.
    Risk level for detected deception.
    """
    NONE = "none"              # لا خداع
    LOW = "low"                # خداع منخفض الاحتمال
    MEDIUM = "medium"          # خداع محتمل
    HIGH = "high"              # خداع مرتفع الاحتمال
    CRITICAL = "critical"      # خداع شبه مؤكد


class ImpactLevel(str, Enum):
    """
    مستوى التأثير — مدى تأثير المعتقد الخاطئ على السلوك.
    Impact level of a false belief on agent behavior.
    """
    NEGLIGIBLE = "negligible"  # ضئيل — تأثير محدود
    LOW = "low"                # منخفض
    MEDIUM = "medium"          # متوسط
    HIGH = "high"              # مرتفع
    CRITICAL = "critical"      # حرج — قد يؤدي لسلوك خطير


class RelationshipType(str, Enum):
    """
    نوع العلاقة — طبيعة العلاقة بين وكيلين.
    Type of relationship between two agents.
    """
    COOPERATIVE = "cooperative"    # تعاونية
    COMPETITIVE = "competitive"    # تنافسية
    NEUTRAL = "neutral"            # محايدة
    HOSTILE = "hostile"            # عدائية
    DEPENDENT = "dependent"        # تابعة
    MENTOR = "mentor"              # إرشادية


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج البيانات — Dataclasses
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class BeliefState:
    """
    حالة المعتقدات — ما يعرفه الوكيل وما يجهله وما يعتقده خطأً.
    An agent's belief state: what they know, don't know, and believe incorrectly.
    """
    known_facts: list[str] = field(default_factory=list)       # حقائق معروفة
    unknown_facts: list[str] = field(default_factory=list)     # حقائق مجهولة
    misconceptions: list[str] = field(default_factory=list)    # مفاهيم خاطئة

    def to_dict(self) -> dict:
        return {
            "known_facts": self.known_facts,
            "unknown_facts": self.unknown_facts,
            "misconceptions": self.misconceptions,
        }


@dataclass
class DesireState:
    """
    حالة الرغبات — أهداف وقيم الوكيل.
    An agent's desire state: goals and values driving behavior.
    """
    primary_goals: list[str] = field(default_factory=list)     # أهداف رئيسية
    secondary_goals: list[str] = field(default_factory=list)   # أهداف ثانوية
    values: list[str] = field(default_factory=list)            # قيم مبدئية

    def to_dict(self) -> dict:
        return {
            "primary_goals": self.primary_goals,
            "secondary_goals": self.secondary_goals,
            "values": self.values,
        }


@dataclass
class IntentionState:
    """
    حالة النوايا — إجراءات يخطط الوكيل للقيام بها.
    An agent's intention state: planned actions and constraints.
    """
    planned_actions: list[str] = field(default_factory=list)   # إجراءات مخططة
    priorities: list[str] = field(default_factory=list)        # أولويات مرتبة
    constraints: list[str] = field(default_factory=list)       # قيود تحد الإجراءات

    def to_dict(self) -> dict:
        return {
            "planned_actions": self.planned_actions,
            "priorities": self.priorities,
            "constraints": self.constraints,
        }


@dataclass
class AgentMentalModel:
    """
    النموذج العقلي للوكيل — نموذجنا لما يعرفه الوكيل ويريده وينوي فعله.
    Our model of another agent's mental state, including confidence tracking.
    """
    agent_id: str = ""                          # معرف الوكيل
    agent_type: AgentType = AgentType.HUMAN     # نوع الوكيل
    beliefs: BeliefState = field(default_factory=BeliefState)    # المعتقدات
    desires: DesireState = field(default_factory=DesireState)    # الرغبات
    intentions: IntentionState = field(default_factory=IntentionState)  # النوايا
    confidence: float = 0.5                     # ثقة النموذج (0-1)
    last_updated: float = 0.0                   # آخر تحديث
    observation_count: int = 0                  # عدد الملاحظات المسجلة

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "beliefs": self.beliefs.to_dict(),
            "desires": self.desires.to_dict(),
            "intentions": self.intentions.to_dict(),
            "confidence": round(self.confidence, 4),
            "last_updated": self.last_updated,
            "observation_count": self.observation_count,
        }


@dataclass
class FalseBelief:
    """
    معتقد خاطئ — معتقد يختلف عن الواقع.
    A belief an agent holds that differs from reality.
    """
    agent_id: str = ""                          # معرف الوكيل
    belief: str = ""                            # المعتقد الخاطئ
    reality: str = ""                           # الواقع الفعلي
    impact_level: ImpactLevel = ImpactLevel.MEDIUM  # مستوى التأثير

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "belief": self.belief,
            "reality": self.reality,
            "impact_level": self.impact_level.value,
        }


@dataclass
class NestedMentalModel:
    """
    نموذج عقلي متداخل — "ماذا يعتقد أ عن ب؟"
    Nested mental model: "What does agent A think agent B thinks?"
    Implements MetaMind hierarchical modeling.
    """
    subject_id: str = ""            # الوكيل الذي يفكر — the thinker
    about_id: str = ""              # الوكيل الذي يُفكر فيه — the target
    inferred_beliefs: list[str] = field(default_factory=list)   # معتقدات مستنتجة
    depth: int = 1                  # عمق التداخل (1 = أفكر أنك تفكر…)
    confidence: float = 0.3         # ثقة الاستنتاج (تقل مع العمق)

    def to_dict(self) -> dict:
        return {
            "subject_id": self.subject_id,
            "about_id": self.about_id,
            "inferred_beliefs": self.inferred_beliefs,
            "depth": self.depth,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class PredictedAction:
    """
    إجراء متوقع — إجراء يتوقع أن يقوم به الوكيل.
    A predicted action an agent might take, ranked by likelihood.
    """
    action: str = ""                # الإجراء المتوقع
    probability: float = 0.0        # احتمال التنفيذ (0-1)
    reasoning: str = ""             # سبب التوقع

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "probability": round(self.probability, 4),
            "reasoning": self.reasoning,
        }


@dataclass
class CooperationPrediction:
    """
    تنبؤ بالتعاون — هل سيتعاون الوكيل؟
    Prediction of whether an agent will cooperate on a task.
    """
    will_cooperate: bool = False    # هل سيتعاون؟
    confidence: float = 0.0         # ثقة التنبؤ (0-1)
    factors: list[str] = field(default_factory=list)  # عوامل مؤثرة

    def to_dict(self) -> dict:
        return {
            "will_cooperate": self.will_cooperate,
            "confidence": round(self.confidence, 4),
            "factors": self.factors,
        }


@dataclass
class DeceptionRisk:
    """
    خطر الخداع — تقييم احتمال أن يكون الوكيل مخادعاً.
    Assessment of whether an agent might be deceptive.
    """
    risk_level: DeceptionRiskLevel = DeceptionRiskLevel.NONE  # مستوى الخطر
    indicators: list[str] = field(default_factory=list)   # مؤشرات الخداع
    confidence: float = 0.0                               # ثقة التقييم

    def to_dict(self) -> dict:
        return {
            "risk_level": self.risk_level.value,
            "indicators": self.indicators,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class SocialRecommendation:
    """
    توصية اجتماعية — أفضل إجراء في السياق الاجتماعي.
    Recommended action considering social dynamics and cultural context.
    """
    recommended_action: str = ""                            # الإجراء الموصى به
    reasoning: str = ""                                     # سبب التوصية
    cultural_considerations: list[str] = field(default_factory=list)  # اعتبارات ثقافية

    def to_dict(self) -> dict:
        return {
            "recommended_action": self.recommended_action,
            "reasoning": self.reasoning,
            "cultural_considerations": self.cultural_considerations,
        }


@dataclass
class RelationshipModel:
    """
    نموذج العلاقة — علاقة بين وكيلين.
    Model of the relationship between two agents.
    """
    agent_a: str = ""                                       # الوكيل الأول
    agent_b: str = ""                                       # الوكيل الثاني
    relationship_type: RelationshipType = RelationshipType.NEUTRAL  # نوع العلاقة
    trust_score: float = 0.5                                # درجة الثقة (0-1)
    cooperation_history: list[str] = field(default_factory=list)  # سجل التعاون
    conflict_history: list[str] = field(default_factory=list)    # سجل النزاعات

    def to_dict(self) -> dict:
        return {
            "agent_a": self.agent_a,
            "agent_b": self.agent_b,
            "relationship_type": self.relationship_type.value,
            "trust_score": round(self.trust_score, 4),
            "cooperation_history": self.cooperation_history,
            "conflict_history": self.conflict_history,
        }


@dataclass
class SocialDynamics:
    """
    الديناميكيات الاجتماعية — ديناميكيات القوة والتحالفات في مجموعة.
    Social dynamics within a group: power, alliances, conflicts.
    """
    power_dynamics: dict[str, float] = field(default_factory=dict)  # {agent_id: power_score}
    alliances: list[list[str]] = field(default_factory=list)        # تحالفات
    conflicts: list[list[str]] = field(default_factory=list)        # نزاعات

    def to_dict(self) -> dict:
        return {
            "power_dynamics": {k: round(v, 4) for k, v in self.power_dynamics.items()},
            "alliances": self.alliances,
            "conflicts": self.conflicts,
        }


@dataclass
class KnowledgeState:
    """
    حالة المعرفة — ما يمكن للوكيل الوصول إليه من معلومات.
    What information an agent has access to, given partial observability.
    """
    accessible_info: list[str] = field(default_factory=list)   # معلومات متاحة
    inaccessible_info: list[str] = field(default_factory=list) # معلومات غير متاحة

    def to_dict(self) -> dict:
        return {
            "accessible_info": self.accessible_info,
            "inaccessible_info": self.inaccessible_info,
        }


@dataclass
class Misconception:
    """
    مفهوم خاطئ — معتقد يتعارض مع الواقع.
    A belief that conflicts with reality.
    """
    agent_belief: str = ""        # معتقد الوكيل
    actual_reality: str = ""      # الواقع الفعلي
    severity: float = 0.5         # شدة الخطأ (0-1)

    def to_dict(self) -> dict:
        return {
            "agent_belief": self.agent_belief,
            "actual_reality": self.actual_reality,
            "severity": round(self.severity, 4),
        }


@dataclass
class Unknown:
    """
    معلومة مجهولة — شيء لا يعرفه الوكيل.
    Something the agent doesn't know.
    """
    fact: str = ""                # الحقيقة المجهولة
    relevance: float = 0.5        # مدى صلتها بالقرار (0-1)

    def to_dict(self) -> dict:
        return {
            "fact": self.fact,
            "relevance": round(self.relevance, 4),
        }


@dataclass
class TheoryOfMindResult:
    """
    نتيجة نظرية العقل — نتيجة شاملة لعملية النمذجة العقلية.
    Comprehensive result of Theory of Mind modeling for an agent.
    """
    agent_id: str = ""                                        # معرف الوكيل
    mental_model: AgentMentalModel = field(default_factory=AgentMentalModel)  # النموذج العقلي
    predictions: list[PredictedAction] = field(default_factory=list)          # التنبؤات
    confidence: float = 0.0                                   # ثقة شاملة

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "mental_model": self.mental_model.to_dict(),
            "predictions": [p.to_dict() for p in self.predictions],
            "confidence": round(self.confidence, 4),
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  محرك نظرية العقل — TheoryOfMindEngine
# ═══════════════════════════════════════════════════════════════════════════════


class TheoryOfMindEngine:
    """
    محرك نظرية العقل — المحرك الرئيسي لنمذجة العقول الأخرى.

    Implements a comprehensive Theory of Mind system that enables the AGI
    to reason about the beliefs, desires, and intentions of other agents.
    Integrates Adaptive ToM (depth-adjustable modeling) and MetaMind
    (hierarchical recursive modeling).

    Architecture:
        TheoryOfMindEngine
        ├── MentalModelTracker     — multi-agent mental model management
        ├── BeliefInferenceEngine  — belief inference with partial observability
        ├── IntentionPredictor     — BDI-based intention prediction
        └── SocialCognitionEngine  — relationship & cultural awareness

    Usage:
        engine = TheoryOfMindEngine()
        result = await engine.model("user_123", observation)
        prediction = await engine.predict("user_123", situation)
    """

    # ─── ثوابت — Constants ──────────────────────────────────────────────────

    # عامل تحديث الثقة — confidence update rate
    CONFIDENCE_UPDATE_RATE = 0.25
    # عتبة التناقض — inconsistency threshold
    INCONSISTENCY_THRESHOLD = 0.4
    # عامل النسيان — temporal decay rate
    DECAY_RATE = 0.005
    # الحد الأقصى للمعتقدات — max beliefs per model
    MAX_BELIEFS = 100
    # الحد الأقصى للرغبات — max desires per model
    MAX_DESIRES = 30
    # الحد الأقصى للنوايا — max intentions per model
    MAX_INTENTIONS = 20

    def __init__(
        self,
        max_nesting_depth: int = TOM_MAX_NESTING_DEPTH,
        confidence_threshold: float = TOM_CONFIDENCE_THRESHOLD,
    ):
        """
        تهيئة محرك نظرية العقل — Initialize the Theory of Mind engine.

        Args:
            max_nesting_depth: أقصى عمق للنمذجة المتداخلة — max recursive depth
            confidence_threshold: عتبة الثقة الدنيا — min confidence for results
        """
        self._max_nesting_depth = max_nesting_depth
        self._confidence_threshold = confidence_threshold

        # تهيئة المحركات الفرعية — Initialize sub-engines
        self._model_tracker = self.MentalModelTracker(self)
        self._belief_engine = self.BeliefInferenceEngine(self)
        self._intention_predictor = self.IntentionPredictor(self)
        self._social_engine = self.SocialCognitionEngine(self)

        # إحصائيات الاستخدام — Usage statistics
        self._stats = {
            "model_calls": 0,
            "predict_calls": 0,
            "false_belief_detections": 0,
            "nested_model_calls": 0,
            "agents_modeled": 0,
        }

        if TOM_ENABLED:
            logger.info(
                "تم تفعيل محرك نظرية العقل — Theory of Mind engine enabled "
                "(depth=%d, threshold=%.2f)",
                max_nesting_depth,
                confidence_threshold,
            )

    # ─── الواجهة الرئيسية — Public API ─────────────────────────────────────

    async def model(self, agent_id: str, observation: dict) -> dict:
        """
        النمذجة الرئيسية — نمذجة الحالة العقلية لوكيل بناءً على ملاحظة.
        Main entry point: model an agent's mental state from an observation.

        Implements Adaptive ToM: adjusts modeling depth based on agent
        predictability. High predictability → shallow model (fast).
        Low predictability → deep model (accurate).

        Args:
            agent_id: معرف الوكيل — agent identifier
            observation: الملاحظة — dict with keys:
                - "action": السلوك الملاحظ (str)
                - "context": السياق (str)
                - "stated_intention": النية المعلنة (str, optional)
                - "outcome": النتيجة (str, optional)
                - "consistency_score": درجة الاتساق (float, optional)

        Returns:
            قاموس يمثل الحالة العقلية المستنتجة — inferred mental state
        """
        self._stats["model_calls"] += 1

        # تحديث أو إنشاء النموذج العقلي — Update or create mental model
        mental_model = self._model_tracker._update_model(agent_id, observation)
        self._stats["agents_modeled"] = len(self._model_tracker._models)

        # استنتاج المعتقدات — Infer beliefs
        beliefs = self._infer_beliefs(
            [observation],
            self._model_tracker._get_model(agent_id),
        )
        mental_model.beliefs = beliefs

        # استنتاج الرغبات — Infer desires
        desires = self._infer_desires(
            [observation],
            self._model_tracker._get_model(agent_id),
        )
        mental_model.desires = desires

        # استنتاج النوايا — Infer intentions
        intentions = self._infer_intentions(beliefs, desires)
        mental_model.intentions = intentions

        # تحديث الثقة — Update model confidence
        mental_model.confidence = self._compute_model_confidence(mental_model)
        mental_model.last_updated = time.time()
        mental_model.observation_count += 1

        # تتبع المعتقدات الخاطئة — Track false beliefs
        reality = observation.get("reality", {})
        if reality:
            self._model_false_belief(agent_id, reality)

        result = TheoryOfMindResult(
            agent_id=agent_id,
            mental_model=mental_model,
            predictions=[],
            confidence=mental_model.confidence,
        )

        if result.confidence < self._confidence_threshold:
            logger.debug(
                "ثقة النموذج منخفضة للوكيل %s: %.2f < %.2f — low confidence",
                agent_id,
                result.confidence,
                self._confidence_threshold,
            )

        return result.to_dict()

    async def predict(self, agent_id: str, situation: dict) -> dict:
        """
        التنبؤ — تنبؤ بما سيفعله الوكيل في موقف معين.
        Predict what an agent will do in a given situation.

        Uses the BDI (Belief-Desire-Intention) architecture to generate
        ranked predictions of likely actions.

        Args:
            agent_id: معرف الوكيل — agent identifier
            situation: الموقف — dict with keys:
                - "description": وصف الموقف (str)
                - "constraints": قيود (list[str], optional)
                - "task": المهمة (str, optional)
                - "group": المجموعة (list[str], optional)

        Returns:
            قاموس يتضمن التنبؤات والتقييمات الاجتماعية
        """
        self._stats["predict_calls"] += 1

        mental_model = self._model_tracker._get_model(agent_id)

        # تنبؤ الإجراءات — Predict actions
        constraints = situation.get("constraints", [])
        predicted_actions = self._intention_predictor._predict_actions(
            mental_model.beliefs,
            mental_model.desires,
            constraints,
        )

        # تقييم التعاون — Assess cooperation
        task = situation.get("task", "")
        cooperation = self._intention_predictor._predict_cooperation(
            agent_id, task
        )

        # تقييم الخداع — Assess deception risk
        deception = self._intention_predictor._predict_deception(agent_id)

        # توصية اجتماعية — Social recommendation
        social_context = {
            "situation": situation,
            "cooperation": cooperation.to_dict(),
            "deception": deception.to_dict(),
        }
        recommendation = self._social_engine._recommend_action(
            situation, social_context
        )

        # حساب الثقة الشاملة — Compute overall confidence
        overall_confidence = self._compute_prediction_confidence(
            mental_model, predicted_actions
        )

        result = TheoryOfMindResult(
            agent_id=agent_id,
            mental_model=mental_model,
            predictions=predicted_actions,
            confidence=overall_confidence,
        )

        result_dict = result.to_dict()
        result_dict["cooperation"] = cooperation.to_dict()
        result_dict["deception_risk"] = deception.to_dict()
        result_dict["social_recommendation"] = recommendation.to_dict()

        return result_dict

    def model_advanced(self, agent_id: str, target_id: str, observations: list[dict],
                       conversation_context: Optional[dict] = None) -> dict:
        """
        نمذجة متقدمة (v10) — تستخدم المعتقدات المتداخلة وتعرّف النوايا.
        
        Only active when MAMOUN_TOM_ADVANCED=true.
        Falls back to standard modeling when disabled.
        """
        import os
        tom_advanced = os.environ.get("MAMOUN_TOM_ADVANCED", "false").lower() in ("true", "1", "yes")
        
        if not tom_advanced:
            # Fall back to standard modeling
            result = self.model(agent_id, observations)
            return result.to_dict() if hasattr(result, 'to_dict') else {}
        
        # Use v10 advanced subsystems
        from mamoun.tom.nested_beliefs import NestedBeliefEngine
        from mamoun.tom.intention_recognition import IntentionRecognizer
        from mamoun.tom.social_strategy import SocialStrategyEngine
        
        # Nested beliefs
        nb_engine = NestedBeliefEngine()
        belief_model = nb_engine.model_nested_belief(agent_id, target_id, observations)
        
        # Intention recognition
        intent_recognizer = IntentionRecognizer()
        message = observations[0].get("action", "") if observations else ""
        intentions = intent_recognizer.recognize(message, conversation_context)
        
        # Social strategy
        strategy_engine = SocialStrategyEngine()
        strategy = strategy_engine.adapt_strategy(belief_model, intentions, conversation_context)
        
        # Deception risk
        deception_risk = nb_engine.detect_deception_risk(belief_model)
        
        return {
            "nested_beliefs": belief_model.to_dict(),
            "intentions": [i.to_dict() for i in intentions],
            "social_strategy": strategy.to_dict(),
            "deception_risk": deception_risk.value,
            "advanced_mode": True,
        }

    # ─── طرق الاستنتاج الداخلية — Internal inference methods ─────────────

    def _infer_beliefs(
        self,
        observations: list[dict],
        agent_history: AgentMentalModel,
    ) -> BeliefState:
        """
        استنتاج المعتقدات — ماذا يعتقد هذا الوكيل؟
        What does this agent believe? Inferred from observations and history.
        """
        known_facts: list[str] = list(agent_history.beliefs.known_facts)
        unknown_facts: list[str] = list(agent_history.beliefs.unknown_facts)
        misconceptions: list[str] = list(agent_history.beliefs.misconceptions)

        for obs in observations:
            action = obs.get("action", "")
            context = obs.get("context", "")
            stated = obs.get("stated_intention", "")
            outcome = obs.get("outcome", "")

            # من السلوك المعلن — From stated intention
            if stated:
                known_facts.append(f"ينوي: {stated}")

            # من السلوك الفعلي — From actual behavior
            if action:
                consistency = obs.get("consistency_score", 1.0)
                if consistency > 0.5:
                    known_facts.append(f"يفعل: {action}")
                else:
                    # سلوك غير متسق قد يشير لمعتقد خاطئ
                    misconceptions.append(f"سلوك غير متسق: {action}")

            # من النتيجة — From outcome
            if outcome:
                known_facts.append(f"يسعى لتحقيق: {outcome}")

            # من السياق — From context (weaker signal)
            if context:
                known_facts.append(f"يعمل في سياق: {context}")

        # تقليم — Enforce limits
        known_facts = known_facts[-self.MAX_BELIEFS:]
        unknown_facts = unknown_facts[-self.MAX_BELIEFS:]
        misconceptions = misconceptions[-self.MAX_BELIEFS // 2:]

        return BeliefState(
            known_facts=known_facts,
            unknown_facts=unknown_facts,
            misconceptions=misconceptions,
        )

    def _infer_desires(
        self,
        observations: list[dict],
        agent_history: AgentMentalModel,
    ) -> DesireState:
        """
        استنتاج الرغبات — ماذا يريد هذا الوكيل؟
        What does this agent want? Inferred from behavioral patterns.
        """
        primary_goals: list[str] = list(agent_history.desires.primary_goals)
        secondary_goals: list[str] = list(agent_history.desires.secondary_goals)
        values: list[str] = list(agent_history.desires.values)

        # قوالب استنتاج الرغبات — Desire inference templates
        desire_patterns = {
            "ask": ("seek_information", "البحث عن معلومات", True),
            "question": ("seek_information", "البحث عن معلومات", True),
            "query": ("seek_information", "البحث عن معلومات", True),
            "استفسار": ("seek_information", "البحث عن معلومات", True),
            "سؤال": ("seek_information", "البحث عن معلومات", True),
            "request": ("obtain_resource", "الحصول على مورد", True),
            "طلب": ("obtain_resource", "الحصول على مورد", True),
            "agree": ("cooperate", "التعاون", False),
            "موافقة": ("cooperate", "التعاون", False),
            "reject": ("resist", "المقاومة", False),
            "رفض": ("resist", "المقاومة", False),
            "help": ("assist", "المساعدة", False),
            "يساعد": ("assist", "المساعدة", False),
            "explain": ("persuade", "الإقناع", False),
            "يبرر": ("persuade", "الإقناع", False),
            "hide": ("conceal", "الإخفاء", False),
            "يخفي": ("conceal", "الإخفاء", False),
        }

        for obs in observations:
            action = obs.get("action", "").lower()
            stated = obs.get("stated_intention", "").lower()
            outcome = obs.get("outcome", "").lower()

            # فحص الأنماط — Check patterns
            text_to_check = f"{action} {stated} {outcome}"
            for keyword, (goal_id, goal_ar, is_primary) in desire_patterns.items():
                if keyword in text_to_check:
                    goal = f"{goal_ar} ({goal_id})"
                    if is_primary and goal not in primary_goals:
                        primary_goals.append(goal)
                    elif not is_primary and goal not in secondary_goals:
                        secondary_goals.append(goal)

            # استنتاج القيم من السياق — Infer values from context
            context = obs.get("context", "").lower()
            value_indicators = {
                "عمل": "الاجتهاد — diligence",
                "عائلة": "العائلة — family",
                "دين": "الإيمان — faith",
                "علم": "المعرفة — knowledge",
                "أمان": "الأمان — safety",
                "حرية": "الحرية — freedom",
                "عدالة": "العدالة — justice",
                "كرم": "الكرم — generosity",
                "ضيافة": "الضيافة — hospitality",
            }
            for indicator, value in value_indicators.items():
                if indicator in context and value not in values:
                    values.append(value)

        # تقليم — Enforce limits
        primary_goals = primary_goals[-self.MAX_DESIRES:]
        secondary_goals = secondary_goals[-self.MAX_DESIRES:]
        values = values[-self.MAX_DESIRES:]

        return DesireState(
            primary_goals=primary_goals,
            secondary_goals=secondary_goals,
            values=values,
        )

    def _infer_intentions(
        self,
        beliefs: BeliefState,
        desires: DesireState,
    ) -> IntentionState:
        """
        استنتاج النوايا — ماذا سيفعل هذا الوكيل؟
        What will this agent do? Derived from beliefs + desires (BDI).
        """
        planned_actions: list[str] = []
        priorities: list[str] = []
        constraints: list[str] = []

        # الأهداف الرئيسية تنتج إجراءات — Primary goals generate actions
        for goal in desires.primary_goals:
            action = self._goal_to_action(goal, beliefs)
            if action and action not in planned_actions:
                planned_actions.append(action)
                priorities.append(f"عالي: {goal}")

        # الأهداف الثانوية — Secondary goals
        for goal in desires.secondary_goals:
            action = self._goal_to_action(goal, beliefs)
            if action and action not in planned_actions:
                planned_actions.append(action)
                priorities.append(f"متوسط: {goal}")

        # المعتقدات الخاطئة تخلق قيوداً — Misconceptions create constraints
        for misc in beliefs.misconceptions:
            constraints.append(f"معتقد خاطئ يحد الخيارات: {misc[:60]}")

        # المعلومات المجهولة تخلق قيوداً — Unknowns create constraints
        for unknown in beliefs.unknown_facts:
            constraints.append(f"معلومة مفقودة: {unknown[:60]}")

        # تقليم — Enforce limits
        planned_actions = planned_actions[-self.MAX_INTENTIONS:]
        priorities = priorities[-self.MAX_INTENTIONS:]
        constraints = constraints[-self.MAX_INTENTIONS:]

        return IntentionState(
            planned_actions=planned_actions,
            priorities=priorities,
            constraints=constraints,
        )

    def _model_false_belief(
        self, agent_id: str, reality: dict
    ) -> FalseBelief:
        """
        تتبع المعتقدات الخاطئة — فهم أن الوكيل قد يحمل معتقدات غير صحيحة.
        Track beliefs that differ from reality (Sally-Anne test principle).

        Critical capability: understanding that others can hold beliefs
        that are false — a key milestone in ToM development.
        """
        self._stats["false_belief_detections"] += 1

        model = self._model_tracker._get_model(agent_id)
        belief = ""
        reality_str = ""
        impact = ImpactLevel.NEGLIGIBLE

        # مقارنة معتقدات الوكيل مع الواقع — Compare agent beliefs with reality
        for misc in model.beliefs.misconceptions:
            # البحث عن حقيقة مقابل — Find matching reality fact
            for key, value in reality.items():
                if isinstance(value, str) and key.lower() in misc.lower():
                    belief = misc
                    reality_str = value
                    impact = ImpactLevel.HIGH
                    break
            if belief:
                break

        # إذا لم نجد تطابقاً، نبحث عن معتقدات خاطئة عامة
        if not belief and model.beliefs.misconceptions:
            belief = model.beliefs.misconceptions[0]
            # محاولة استنتاج الواقع — Attempt to infer reality
            reality_str = reality.get("actual", "غير محدد — unknown")
            impact = ImpactLevel.MEDIUM

        false_belief = FalseBelief(
            agent_id=agent_id,
            belief=belief,
            reality=reality_str,
            impact_level=impact,
        )

        if impact != ImpactLevel.NEGLIGIBLE:
            logger.debug(
                "معتقد خاطئ مكتشف للوكيل %s: '%s' مقابل '%s' (تأثير: %s)",
                agent_id,
                belief[:50],
                reality_str[:50],
                impact.value,
            )

        return false_belief

    def _nested_modeling(
        self, agent_id: str, about_agent_id: str
    ) -> NestedMentalModel:
        """
        النمذجة المتداخلة — "ماذا يعتقد أ عن ب؟"
        "What does agent A think agent B thinks?" — MetaMind hierarchical modeling.

        Implements recursive mental state attribution: I model that agent A
        is modeling agent B's mental state. Each level of nesting reduces
        confidence exponentially.

        Args:
            agent_id: الوكيل الذي يفكر — the thinking agent
            about_agent_id: الوكيل الذي يُفكر فيه — the target agent

        Returns:
            NestedMentalModel — نموذج عقلي متداخل
        """
        self._stats["nested_model_calls"] += 1

        # الحد الأقصى للعمق — Enforce max depth
        if self._model_tracker._get_model(agent_id).observation_count < 3:
            depth = 1  # بيانات قليلة → عمق محدود
        else:
            depth = min(
                self._max_nesting_depth,
                self._model_tracker._get_model(agent_id).observation_count // 5 + 1,
            )

        # استنتاج معتقدات الوكيل عن الوكيل الآخر — Infer A's beliefs about B
        about_model = self._model_tracker._get_model(about_agent_id)
        inferred_beliefs: list[str] = []

        # ما يعرفه أ عن ب — What A likely knows about B
        if about_model.beliefs.known_facts:
            inferred_beliefs.append(
                f"يعرف عن {about_agent_id}: "
                f"{about_model.beliefs.known_facts[0][:50]}"
            )

        if about_model.desires.primary_goals:
            inferred_beliefs.append(
                f"يعتقد أن {about_agent_id} يريد: "
                f"{about_model.desires.primary_goals[0][:50]}"
            )

        if about_model.beliefs.misconceptions:
            inferred_beliefs.append(
                f"قد لا يعرف أن {about_agent_id} يعتقد خطأً: "
                f"{about_model.beliefs.misconceptions[0][:50]}"
            )

        # الثقة تقل أُسياً مع العمق — Confidence decays exponentially with depth
        confidence = max(
            0.1,
            self._model_tracker._get_model(agent_id).confidence * (0.5 ** depth),
        )

        return NestedMentalModel(
            subject_id=agent_id,
            about_id=about_agent_id,
            inferred_beliefs=inferred_beliefs,
            depth=depth,
            confidence=confidence,
        )

    def get_stats(self) -> dict:
        """
        إحصائيات الاستخدام — إرجاع إحصائيات استخدام المحرك.
        Return usage statistics for monitoring and debugging.
        """
        return {
            **self._stats,
            "tom_enabled": TOM_ENABLED,
            "max_nesting_depth": self._max_nesting_depth,
            "confidence_threshold": self._confidence_threshold,
            "model_tracker_stats": {
                "total_models": len(self._model_tracker._models),
                "models_by_type": {
                    t.value: sum(
                        1 for m in self._model_tracker._models.values()
                        if m.agent_type == t
                    )
                    for t in AgentType
                },
            },
        }

    # ─── طرق مساعدة — Helper methods ─────────────────────────────────────

    def _goal_to_action(
        self, goal: str, beliefs: BeliefState
    ) -> str:
        """
        تحويل الهدف إلى إجراء — Convert a goal to a planned action.
        Maps goal descriptions to likely actions based on BDI logic.
        """
        goal_lower = goal.lower()

        # رسم خرائط الأهداف للإجراءات — Goal-to-action mapping
        goal_action_map = {
            "معلومات": "استفسار — inquire",
            "مورد": "طلب — request",
            "تعاون": "مشاركة — collaborate",
            "مقاومة": "رفض — refuse",
            "إقناع": "شرح — explain",
            "إخفاء": "تجنب — avoid",
            "مساعدة": "دعم — support",
            "إصلاح": "تصحيح — correct",
            "حماية": "دفاع — defend",
            "علاقات": "تواصل — connect",
            "معرفة": "بحث — research",
        }

        for keyword, action in goal_action_map.items():
            if keyword in goal_lower:
                return action

        # إجراء عام — Generic action
        return f"سعي نحو: {goal[:40]}"

    def _compute_model_confidence(
        self, model: AgentMentalModel
    ) -> float:
        """
        حساب ثقة النموذج — Compute overall confidence in a mental model.
        Based on: observation count, belief consistency, and evidence strength.
        """
        # عامل عدد الملاحظات — Observation count factor
        obs_factor = min(1.0, model.observation_count / 20.0)

        # عامل تناسق المعتقدات — Belief consistency factor
        total_beliefs = (
            len(model.beliefs.known_facts)
            + len(model.beliefs.unknown_facts)
            + len(model.beliefs.misconceptions)
        )
        if total_beliefs > 0:
            misconceptions_ratio = len(model.beliefs.misconceptions) / total_beliefs
            consistency_factor = 1.0 - misconceptions_ratio
        else:
            consistency_factor = 0.3

        # عامل تغطية الرغبات — Desire coverage factor
        desire_factor = min(1.0, len(model.desires.primary_goals) / 3.0)

        # تركيب — Composite
        confidence = (
            0.4 * obs_factor
            + 0.35 * consistency_factor
            + 0.25 * desire_factor
        )

        return round(max(0.0, min(1.0, confidence)), 4)

    def _compute_prediction_confidence(
        self,
        model: AgentMentalModel,
        predictions: list[PredictedAction],
    ) -> float:
        """
        حساب ثقة التنبؤ — Compute confidence in predictions.
        Based on model confidence and prediction probability spread.
        """
        if not predictions:
            return 0.1

        # متوسط احتمالات التنبؤ — Average prediction probability
        avg_prob = sum(p.probability for p in predictions) / len(predictions)

        # تركيب ثقة النموذج واحتمال التنبؤ
        confidence = 0.6 * model.confidence + 0.4 * avg_prob

        return round(max(0.0, min(1.0, confidence)), 4)

    # ═══════════════════════════════════════════════════════════════════════
    #  متتبع النماذج العقلية — MentalModelTracker (Inner Class)
    # ═══════════════════════════════════════════════════════════════════════

    class MentalModelTracker:
        """
        متتبع النماذج العقلية — يحافظ على النماذج العقلية لعدة وكلاء.
        Maintains mental models for multiple agents simultaneously,
        with confidence tracking and support for different agent types.

        Supports modeling:
        • Human users — مستخدمون بشريون
        • Other AI agents — وكلاء ذكاء اصطناعي آخرون
        • Group entities — كيانات جماعية
        """

        def __init__(self, engine: TheoryOfMindEngine):
            self._engine = engine
            # النماذج العقلية — {agent_id: AgentMentalModel}
            self._models: dict[str, AgentMentalModel] = {}

        def _create_model(self, agent_id: str) -> AgentMentalModel:
            """
            إنشاء نموذج جديد — Initialize a new agent mental model.
            Determines agent type from ID conventions.
            """
            # تحديد نوع الوكيل — Determine agent type
            if agent_id.startswith("ai_") or agent_id.startswith("agent_"):
                agent_type = AgentType.AI_AGENT
            elif agent_id.startswith("group_") or agent_id.startswith("team_"):
                agent_type = AgentType.GROUP
            else:
                agent_type = AgentType.HUMAN

            model = AgentMentalModel(
                agent_id=agent_id,
                agent_type=agent_type,
                confidence=0.1,  # ثقة أولية منخفضة — low initial confidence
                last_updated=time.time(),
            )

            self._models[agent_id] = model
            logger.debug(
                "تم إنشاء نموذج عقلي جديد للوكيل %s من نوع %s",
                agent_id,
                agent_type.value,
            )

            return model

        def _update_model(
            self, agent_id: str, observation: dict
        ) -> AgentMentalModel:
            """
            تحديث النموذج — تحديث النموذج العقلي بملاحظة جديدة.
            Update the agent's mental model with a new observation.
            """
            model = self._get_model(agent_id)

            if model.agent_id == "":
                # نموذج جديد — New model
                model = self._create_model(agent_id)

            now = time.time()
            model.observation_count += 1

            # تحديث الثقة بناءً على الاتساق — Update confidence based on consistency
            consistency = observation.get("consistency_score", 1.0)
            model.confidence = (
                model.confidence * (1 - self._engine.CONFIDENCE_UPDATE_RATE)
                + consistency * self._engine.CONFIDENCE_UPDATE_RATE
            )
            model.confidence = min(1.0, model.confidence)
            model.last_updated = now

            self._models[agent_id] = model
            return model

        def _get_model(self, agent_id: str) -> AgentMentalModel:
            """
            استرجاع النموذج — Retrieve the current mental model for an agent.
            Returns an empty model if the agent hasn't been modeled yet.
            """
            if agent_id not in self._models:
                return AgentMentalModel(agent_id=agent_id)
            return self._models[agent_id]

    # ═══════════════════════════════════════════════════════════════════════
    #  محرك استنتاج المعتقدات — BeliefInferenceEngine (Inner Class)
    # ═══════════════════════════════════════════════════════════════════════

    class BeliefInferenceEngine:
        """
        محرك استنتاج المعتقدات — يستنتج ما يعرفه الوكيل بناءً على ملاحظاته.
        Infers what an agent knows/believes based on their observations,
        supporting partial observability modeling.

        Key principles:
        • Agents only know what they've observed — الرؤية الجزئية
        • Agents can hold false beliefs — المعتقدات الخاطئة
        • Knowledge state changes with new observations — تحديث ديناميكي
        """

        def __init__(self, engine: TheoryOfMindEngine):
            self._engine = engine
            # سجل وصول الوكلاء للمعلومات — Agent access log
            self._agent_access: dict[str, list[str]] = defaultdict(list)

        def _compute_knowledge_state(
            self,
            available_info: list[str],
            agent_access: list[str],
        ) -> KnowledgeState:
            """
            حساب حالة المعرفة — ما المعلومات التي يمكن للوكيل الوصول إليها؟
            What info does agent have access to? Models partial observability.

            Args:
                available_info: كل المعلومات المتاحة — all available info
                agent_access: ما يمكن للوكيل الوصول إليه — agent's access channels

            Returns:
                KnowledgeState — المعلومات المتاحة وغير المتاحة للوكيل
            """
            accessible: list[str] = []
            inaccessible: list[str] = []

            for info in available_info:
                # فحص هل الوكيل يمكنه الوصول لهذه المعلومة
                # Check if the agent can access this information
                can_access = False
                for channel in agent_access:
                    # تشابه بسيط — Simple overlap check
                    if channel.lower() in info.lower() or info.lower() in channel.lower():
                        can_access = True
                        break

                if can_access:
                    accessible.append(info)
                else:
                    inaccessible.append(info)

            return KnowledgeState(
                accessible_info=accessible,
                inaccessible_info=inaccessible,
            )

        def _infer_missing_knowledge(
            self,
            knowledge_state: KnowledgeState,
            reality: dict,
        ) -> list[Unknown]:
            """
            استنتاج المعرفة المفقودة — ما لا يعرفه الوكيل؟
            What doesn't the agent know? Inferred from gaps between
            accessible info and reality.
            """
            unknowns: list[Unknown] = []

            for info in knowledge_state.inaccessible_info:
                # تقدير صلة المعلومة بالقرار — Estimate relevance
                relevance = 0.5
                for key, value in reality.items():
                    if isinstance(value, str) and key.lower() in info.lower():
                        relevance = 0.9  # معلومة ذات صلة عالية
                        break

                unknowns.append(Unknown(
                    fact=info,
                    relevance=relevance,
                ))

            # ترتيب حسب الصلة — Sort by relevance
            unknowns.sort(key=lambda u: u.relevance, reverse=True)

            return unknowns[:20]  # الحد الأقصى — enforce limit

        def _detect_misconception(
            self,
            agent_belief: str,
            reality: dict,
        ) -> Optional[Misconception]:
            """
            كشف المفاهيم الخاطئة — هل يحمل الوكيل معتقداً خاطئاً؟
            Does the agent hold a false belief? Detects discrepancies
            between agent beliefs and reality.
            """
            if not agent_belief or not reality:
                return None

            # كلمات النفي — Negation keywords
            negation_words = {
                "لا", "ليس", "لن", "لم", "غير", "بدون",
                "not", "no", "never", "neither", "nor", "without",
            }

            belief_words = set(agent_belief.lower().split())
            belief_has_negation = bool(belief_words & negation_words)

            for key, value in reality.items():
                if not isinstance(value, str):
                    continue

                value_words = set(value.lower().split())
                value_has_negation = bool(value_words & negation_words)

                # إذا كان أحدهما منفياً والآخر ليس كذلك مع تشابه المحتوى
                # If one is negated and the other isn't with similar content
                if belief_has_negation != value_has_negation:
                    # إزالة النفي للمقارنة — Remove negation for comparison
                    belief_clean = belief_words - negation_words
                    value_clean = value_words - negation_words
                    overlap = belief_clean & value_clean
                    if len(overlap) > 2:
                        return Misconception(
                            agent_belief=agent_belief,
                            actual_reality=value,
                            severity=0.8,
                        )

                # فحص أزواج التناقض — Check contradiction pairs
                contradiction_pairs = [
                    ("يوافق", "يرفض"), ("يقبل", "يرفض"),
                    ("agree", "disagree"), ("accept", "reject"),
                    ("صحيح", "خطأ"), ("true", "false"),
                ]
                for pos, neg in contradiction_pairs:
                    if (pos in agent_belief.lower() and neg in value.lower()) or \
                       (neg in agent_belief.lower() and pos in value.lower()):
                        return Misconception(
                            agent_belief=agent_belief,
                            actual_reality=value,
                            severity=0.9,
                        )

            return None

    # ═══════════════════════════════════════════════════════════════════════
    #  متنبيء النوايا — IntentionPredictor (Inner Class)
    # ═══════════════════════════════════════════════════════════════════════

    class IntentionPredictor:
        """
        متنبيء النوايا — يتنبأ بما سيفعله الوكيل بناءً على معتقداته ورغباته.
        Predicts what an agent will do next based on beliefs + desires.

        Uses BDI (Belief-Desire-Intention) architecture:
        • Beliefs: what the agent thinks is true
        • Desires: what the agent wants to achieve
        • Intentions: what the agent commits to doing

        Also assesses:
        • Cooperation likelihood — احتمال التعاون
        • Deception risk — خطر الخداع
        """

        # الحد الأقصى للتنبؤات — Max predictions
        MAX_PREDICTIONS = 10

        def __init__(self, engine: TheoryOfMindEngine):
            self._engine = engine
            # سجل التناقضات — Inconsistency log
            self._inconsistency_log: dict[str, list[dict]] = defaultdict(list)

        def _predict_actions(
            self,
            beliefs: BeliefState,
            desires: DesireState,
            constraints: list[str],
        ) -> list[PredictedAction]:
            """
            تنبؤ الإجراءات — تنبؤ بالإجراءات المرتبة حسب الاحتمالية.
            Predict actions ranked by likelihood using BDI logic.

            Args:
                beliefs: معتقدات الوكيل — agent's beliefs
                desires: رغبات الوكيل — agent's desires
                constraints: قيود — situational constraints

            Returns:
                قائمة الإجراءات المتوقعة مرتبة حسب الاحتمالية
            """
            predictions: list[PredictedAction] = []

            # الأهداف الرئيسية → إجراءات عالية الاحتمال
            # Primary goals → high probability actions
            for i, goal in enumerate(desires.primary_goals):
                action = self._engine._goal_to_action(goal, beliefs)
                probability = max(0.3, 0.9 - i * 0.15)

                # تخفيض الاحتمال إذا كانت هناك قيود
                # Reduce probability if constraints exist
                constraint_penalty = sum(
                    0.05 for c in constraints
                    if any(w in action.lower() for w in c.lower().split())
                )
                probability = max(0.1, probability - constraint_penalty)

                # تخفيض الاحتمال إذا كانت هناك معتقدات خاطئة
                # Reduce probability if misconceptions exist
                if beliefs.misconceptions:
                    probability *= 0.85

                predictions.append(PredictedAction(
                    action=action,
                    probability=round(probability, 4),
                    reasoning=f"هدف رئيسي: {goal[:60]}",
                ))

            # الأهداف الثانوية → إجراءات متوسطة الاحتمال
            # Secondary goals → medium probability actions
            for i, goal in enumerate(desires.secondary_goals):
                action = self._engine._goal_to_action(goal, beliefs)
                probability = max(0.15, 0.6 - i * 0.1)

                if beliefs.misconceptions:
                    probability *= 0.8

                predictions.append(PredictedAction(
                    action=action,
                    probability=round(probability, 4),
                    reasoning=f"هدف ثانوي: {goal[:60]}",
                ))

            # إجراءات مستنتجة من المعتقدات — Actions inferred from beliefs
            for fact in beliefs.known_facts[:5]:
                if "ينوي" in fact or "سعي" in fact:
                    predictions.append(PredictedAction(
                        action=fact,
                        probability=0.5,
                        reasoning="مستنتج من المعتقدات المعلنة",
                    ))

            # ترتيب حسب الاحتمالية — Sort by probability
            predictions.sort(key=lambda p: p.probability, reverse=True)

            # إزالة التكرارات — Deduplicate
            seen_actions: set[str] = set()
            unique_predictions: list[PredictedAction] = []
            for pred in predictions:
                if pred.action not in seen_actions:
                    seen_actions.add(pred.action)
                    unique_predictions.append(pred)

            return unique_predictions[:self.MAX_PREDICTIONS]

        def _predict_cooperation(
            self, agent_id: str, task: str
        ) -> CooperationPrediction:
            """
            تنبؤ بالتعاون — هل سيتعاون الوكيل في المهمة؟
            Will the agent cooperate on the task?

            Factors:
            • History of cooperation — سجل التعاون السابق
            • Goal alignment — توافق الأهداف
            • Trust level — مستوى الثقة
            """
            model = self._engine._model_tracker._get_model(agent_id)
            factors: list[str] = []

            # عامل توافق الأهداف — Goal alignment factor
            task_lower = task.lower()
            goal_alignment = 0.0
            for goal in model.desires.primary_goals:
                if any(w in goal.lower() for w in task_lower.split()):
                    goal_alignment = 0.7
                    factors.append(f"توافق أهداف: {goal[:40]}")
                    break

            # عامل الثقة — Trust factor
            trust = model.confidence
            factors.append(f"ثقة: {trust:.2f}")

            # عامل نوع الوكيل — Agent type factor
            if model.agent_type == AgentType.AI_AGENT:
                goal_alignment += 0.1
                factors.append("وكيل ذكاء اصطناعي — ميل للتعاون")
            elif model.agent_type == AgentType.GROUP:
                goal_alignment -= 0.1
                factors.append("كيان جماعي — قد يتطلب تفاوض")

            # عامل القيم — Values factor
            cooperative_values = {"التعاون", "المساعدة", "الضيافة", "الكرم"}
            for value in model.desires.values:
                for cv in cooperative_values:
                    if cv in value:
                        goal_alignment += 0.15
                        factors.append(f"قيمة تعاونية: {value[:30]}")

            # حساب الاحتمال — Compute probability
            cooperation_prob = min(1.0, 0.5 + goal_alignment + trust * 0.3)
            will_cooperate = cooperation_prob > 0.5

            return CooperationPrediction(
                will_cooperate=will_cooperate,
                confidence=round(min(1.0, abs(cooperation_prob - 0.5) * 2), 4),
                factors=factors,
            )

        def _predict_deception(self, agent_id: str) -> DeceptionRisk:
            """
            تقييم خطر الخداع — هل قد يكون الوكيل مخادعاً؟
            Might this agent be deceptive?

            Indicators:
            • Inconsistencies between stated and observed behavior
            • Evasive patterns in communication
            • Contradictions in belief model
            """
            model = self._engine._model_tracker._get_model(agent_id)
            indicators: list[str] = []

            # فحص المعتقدات الخاطئة — Check for misconceptions
            if model.beliefs.misconceptions:
                indicators.append(
                    f"معتقدات خاطئة: {len(model.beliefs.misconceptions)}"
                )

            # فحص التناقضات — Check for inconsistencies
            inconsistencies = self._inconsistency_log.get(agent_id, [])
            if inconsistencies:
                indicators.append(
                    f"تناقضات سابقة: {len(inconsistencies)}"
                )

            # فحص القيم المشبوهة — Check for suspicious values
            suspicious_values = {"الإخفاء", "التجنب"}
            for value in model.desires.values:
                for sv in suspicious_values:
                    if sv in value:
                        indicators.append(f"قيمة مشبوهة: {value[:30]}")

            # فحص الأهداف الدفاعية — Check for defensive goals
            for goal in model.desires.secondary_goals:
                if "إخفاء" in goal.lower() or "تجنب" in goal.lower():
                    indicators.append(f"هدف دفاعي: {goal[:40]}")

            # تحديد مستوى الخطر — Determine risk level
            indicator_count = len(indicators)
            if indicator_count == 0:
                risk_level = DeceptionRiskLevel.NONE
                confidence = 0.8
            elif indicator_count == 1:
                risk_level = DeceptionRiskLevel.LOW
                confidence = 0.5
            elif indicator_count == 2:
                risk_level = DeceptionRiskLevel.MEDIUM
                confidence = 0.6
            elif indicator_count == 3:
                risk_level = DeceptionRiskLevel.HIGH
                confidence = 0.7
            else:
                risk_level = DeceptionRiskLevel.CRITICAL
                confidence = 0.8

            return DeceptionRisk(
                risk_level=risk_level,
                indicators=indicators,
                confidence=round(confidence, 4),
            )

    # ═══════════════════════════════════════════════════════════════════════
    #  محرك الإدراك الاجتماعي — SocialCognitionEngine (Inner Class)
    # ═══════════════════════════════════════════════════════════════════════

    class SocialCognitionEngine:
        """
        محرك الإدراك الاجتماعي — يفهم الديناميكيات الاجتماعية والثقافية.
        Understands cooperative and competitive dynamics, relationships,
        and cultural context (including Arab hospitality norms).

        Cultural awareness:
        • Arab/Islamic norms: الكرم، الضيافة، احترام الكبار
        • Western norms: directness, individualism
        • Context-aware adjustment of interaction style
        """

        # المعايير الثقافية العربية — Arab cultural norms
        ARAB_CULTURAL_NORMS = {
            "hospitality": {
                "arabic": "الضيافة",
                "description": "إكرام الضيف واجب — hospitality is obligatory",
                "priority": 0.95,
            },
            "generosity": {
                "arabic": "الكرم",
                "description": "السخاء في العطاء — generosity in giving",
                "priority": 0.90,
            },
            "respect_elders": {
                "arabic": "احترام الكبار",
                "description": "توقير كبير السن — respecting elders",
                "priority": 0.85,
            },
            "honor": {
                "arabic": "الشرف",
                "description": "حفظ الوجه والسمعة — preserving face and reputation",
                "priority": 0.88,
            },
            "community": {
                "arabic": "الجماعة",
                "description": "الأولوية للجماعة على الفرد — community over individual",
                "priority": 0.82,
            },
            "indirect_communication": {
                "arabic": "التواصل غير المباشر",
                "description": "تجنب الرفض المباشر — avoiding direct refusal",
                "priority": 0.75,
            },
        }

        def __init__(self, engine: TheoryOfMindEngine):
            self._engine = engine
            # سجل العلاقات — Relationship records
            self._relationships: dict[str, RelationshipModel] = {}
            # السياق الثقافي — Cultural context
            self._cultural_context = "arab_islamic"

        def _relationship_key(self, agent_a: str, agent_b: str) -> str:
            """مفتاح العلاقة — Generate a consistent key for a pair."""
            pair = sorted([agent_a, agent_b])
            return f"{pair[0]}::{pair[1]}"

        def _assess_relationship(
            self, agent_a: str, agent_b: str
        ) -> RelationshipModel:
            """
            تقييم العلاقة — تقييم الثقة والتعاون بين وكيلين.
            Assess trust and cooperation history between two agents.
            """
            key = self._relationship_key(agent_a, agent_b)

            if key in self._relationships:
                return self._relationships[key]

            # تقييم أولي — Initial assessment
            model_a = self._engine._model_tracker._get_model(agent_a)
            model_b = self._engine._model_tracker._get_model(agent_b)

            # تحديد نوع العلاقة — Determine relationship type
            rel_type = RelationshipType.NEUTRAL
            trust = 0.5

            # فحص توافق القيم — Check value alignment
            values_a = set(model_a.desires.values)
            values_b = set(model_b.desires.values)
            shared_values = values_a & values_b

            if len(shared_values) > 3:
                rel_type = RelationshipType.COOPERATIVE
                trust = 0.7
            elif len(shared_values) > 1:
                rel_type = RelationshipType.NEUTRAL
                trust = 0.5

            # فحص تعارض الأهداف — Check goal conflict
            goals_a = set(model_a.desires.primary_goals)
            goals_b = set(model_b.desires.primary_goals)
            conflicting_goals = set()
            for ga in goals_a:
                for gb in goals_b:
                    # كلمات متعارضة — Conflicting keywords
                    conflict_pairs = [
                        ("تعاون", "مقاومة"), ("موافقة", "رفض"),
                        ("cooperate", "resist"), ("accept", "reject"),
                    ]
                    for pos, neg in conflict_pairs:
                        if (pos in ga.lower() and neg in gb.lower()) or \
                           (neg in ga.lower() and pos in gb.lower()):
                            conflicting_goals.add((ga, gb))

            if conflicting_goals:
                rel_type = RelationshipType.COMPETITIVE
                trust = max(0.2, trust - 0.2)

            relationship = RelationshipModel(
                agent_a=agent_a,
                agent_b=agent_b,
                relationship_type=rel_type,
                trust_score=trust,
            )

            self._relationships[key] = relationship
            return relationship

        def _detect_social_dynamics(
            self, group: list[str]
        ) -> SocialDynamics:
            """
            كشف الديناميكيات الاجتماعية — فهم ديناميكيات القوة والتحالفات.
            Understand power dynamics, alliances, and conflicts in a group.
            """
            power_dynamics: dict[str, float] = {}
            alliances: list[list[str]] = []
            conflicts: list[list[str]] = []

            # حساب درجة القوة لكل وكيل — Compute power score per agent
            for agent_id in group:
                model = self._engine._model_tracker._get_model(agent_id)
                # القوة = ثقة النموذج × عدد الأهداف × معلوماتية
                # Power = model confidence × goal count × informativeness
                goal_count = len(model.desires.primary_goals) + len(model.desires.secondary_goals)
                info_count = len(model.beliefs.known_facts)
                power = min(1.0, model.confidence * 0.4 + goal_count * 0.05 + info_count * 0.02)
                power_dynamics[agent_id] = round(power, 4)

            # كشف التحالفات — Detect alliances
            for i, agent_a in enumerate(group):
                for agent_b in group[i + 1:]:
                    rel = self._assess_relationship(agent_a, agent_b)
                    if rel.relationship_type == RelationshipType.COOPERATIVE:
                        alliances.append([agent_a, agent_b])

            # كشف النزاعات — Detect conflicts
            for i, agent_a in enumerate(group):
                for agent_b in group[i + 1:]:
                    rel = self._assess_relationship(agent_a, agent_b)
                    if rel.relationship_type in (
                        RelationshipType.COMPETITIVE,
                        RelationshipType.HOSTILE,
                    ):
                        conflicts.append([agent_a, agent_b])

            return SocialDynamics(
                power_dynamics=power_dynamics,
                alliances=alliances,
                conflicts=conflicts,
            )

        def _recommend_action(
            self,
            situation: dict,
            social_context: dict,
        ) -> SocialRecommendation:
            """
            توصية بالإجراء — أفضل إجراء في السياق الاجتماعي.
            Recommend the best action considering social dynamics and culture.
            """
            description = situation.get("description", "").lower()
            cultural_considerations: list[str] = []

            # تقييم السياق الثقافي — Assess cultural context
            # فحص السياق العربي — Check Arab context
            arabic_context_keywords = {
                "ضيف": "hospitality",
                "ضيافة": "hospitality",
                "كرم": "generosity",
                "كبير": "respect_elders",
                "شرف": "honor",
                "سمعة": "honor",
                "جماعة": "community",
                "عائلة": "community",
            }

            for keyword, norm_key in arabic_context_keywords.items():
                if keyword in description:
                    norm = self.ARAB_CULTURAL_NORMS.get(norm_key, {})
                    if norm:
                        cultural_considerations.append(
                            f"{norm['arabic']}: {norm['description']}"
                        )

            # تحديد الإجراء الموصى به — Determine recommended action
            cooperation = social_context.get("cooperation", {})
            deception = social_context.get("deception_risk", {})

            recommended_action = ""
            reasoning = ""

            if deception.get("risk_level") in ("high", "critical"):
                recommended_action = "توخي الحذر والتحقق — exercise caution and verify"
                reasoning = "مستوى خداع مرتفع — high deception risk detected"
            elif cooperation.get("will_cooperate", False):
                if cultural_considerations:
                    recommended_action = "التعاون بكرم وضيافة — cooperate generously"
                    reasoning = "السياق يتطلب كرماً عربياً — context requires Arab generosity"
                else:
                    recommended_action = "التعاون المباشر — cooperate directly"
                    reasoning = "الوكيل مهتم بالتعاون — agent is inclined to cooperate"
            else:
                recommended_action = "البناء التدريجي للثقة — build trust gradually"
                reasoning = "الوكيل محايد أو متردد — agent is neutral or hesitant"

            return SocialRecommendation(
                recommended_action=recommended_action,
                reasoning=reasoning,
                cultural_considerations=cultural_considerations,
            )
