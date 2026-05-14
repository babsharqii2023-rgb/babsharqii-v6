"""
BABSHARQII v6.0 — System 2 Reasoner (PRIME-inspired)
وحدة الاستدلال من النظام الثاني — مستوحاة من PRIME (AAAI 2026, arXiv:2509.22315)

تنفذ معمارية النظام المزدوج مع بوابة عدم اليقين للانتقال من النظام 1 إلى النظام 2.

النظام 1 (سريع): مطابقة الأنماط والاستجابة السريعة عبر غرفة المداولة الموجودة
النظام 2 (عميق): خط أنابيب متعدد المراحل مع التحسين التكراري

المبدأ الأساسي من PRIME: استخدام عدم اليقين كبوابة.
  - عدم يقين منخفض ← النظام 1 (سريع، اقتصادي)
  - عدم يقين مرتفع ← النظام 2 (بطيء، مكلف، لكن دقيق)

الدمج التراكمي — لا يكسر أي ميزة موجودة:
  - يُفعّل عبر MAMOUN_SYSTEM2_ENABLED (الافتراضي: "false")
  - يتكامل مع DeliberationRoom و WorldModelV2 و CausalReasoner
  - يتراجع بأمان إلى النظام 1 عند التعطيل أو عند الفشل
"""

from __future__ import annotations

import os
import math
import time
import logging
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any, Callable

from mamoun.core.causal_reasoner import CausalReasoner, CausalRule

logger = logging.getLogger(__name__)

# ─── مفتاح التبديل البيئي — Env toggle ──────────────────────────────────────
# الإعداد الافتراضي "false" للسلامة التراكمية — لن يتغير السلوك الحالي
SYSTEM2_ENABLED: bool = os.environ.get(
    "MAMOUN_SYSTEM2_ENABLED", "false"
).lower() in ("true", "1", "yes")

# عتبة عدم اليقين الافتراضية للانتقال من النظام 1 إلى النظام 2
DEFAULT_UNCERTAINTY_THRESHOLD: float = float(
    os.environ.get("MAMOUN_SYSTEM2_THRESHOLD", "0.55")
)

# الحد الأقصى لمرات التحسين التكراري في النظام 2
MAX_REFINEMENT_ITERATIONS: int = int(
    os.environ.get("MAMOUN_SYSTEM2_MAX_REFINEMENTS", "3")
)


# ═══════════════════════════════════════════════════════════════════════════════
# أنواع البيانات الأساسية — Core Data Types
# ═══════════════════════════════════════════════════════════════════════════════


class SystemChoice(Enum):
    """اختيار النظام — System routing choice."""
    SYSTEM_1 = "system_1"  # سريع — مطابقة الأنماط
    SYSTEM_2 = "system_2"  # عميق — استدلال متعدد المراحل


class PipelineStage(Enum):
    """مراحل خط أنابيب النظام الثاني — System 2 pipeline stages."""
    PLANNING = "planning"               # التخطيط — تحليل المشكلة
    HYPOTHESIS = "hypothesis"           # الفرضيات — توليد الفرضيات
    RETRIEVAL = "retrieval"             # الاسترجاع — جلب المعرفة
    SYNTHESIS = "synthesis"             # التركيب — دمج النتائج
    DECISION = "decision"               # القرار — اتخاذ القرار النهائي


@dataclass
class UncertaintyScore:
    """
    نقاط عدم اليقين — نتيجة حساب عدم اليقين.
    
    مركبة من أربعة عوامل كما هو موضح في PRIME:
    1. تباين الثقة عبر الأدمغة (confidence variance)
    2. تعقيد الموضوع (topic complexity)
    3. اكتمال السياق (context completeness)
    4. الفجوات المعرفية (knowledge gaps)
    """
    # العوامل الفردية
    confidence_variance: float = 0.0     # تباين الثقة بين الأدمغة [0, 1]
    topic_complexity: float = 0.0        # تعقيد الموضوع [0, 1]
    context_completeness: float = 1.0    # اكتمال السياق [0, 1] (1 = كامل)
    knowledge_gap_factor: float = 1.0    # عامل الفجوة المعرفية [0, 1] (1 = لا فجوات)

    # النتيجة المركبة
    composite: float = 0.0               # عدم اليقين المركب [0, 1]

    # أوزان العوامل
    WEIGHT_VARIANCE: float = field(default=0.35, init=False)
    WEIGHT_COMPLEXITY: float = field(default=0.25, init=False)
    WEIGHT_COMPLETENESS: float = field(default=0.25, init=False)
    WEIGHT_KNOWLEDGE_GAP: float = field(default=0.15, init=False)

    def compute_composite(self) -> float:
        """
        حساب عدم اليقين المركب — Composite uncertainty.
        
        الصيغة:
          uncertainty = w1 * variance + w2 * complexity
                      + w3 * (1 - completeness) + w4 * (1 - knowledge_gap)
        
        لاحظ: اكتمال السياق والفجوات المعرفية تُعكس (1 - value)
        لأن القيم العالية تعني يقينًا أعلى (أقل عدم يقين).
        """
        self.composite = (
            self.WEIGHT_VARIANCE * self.confidence_variance
            + self.WEIGHT_COMPLEXITY * self.topic_complexity
            + self.WEIGHT_COMPLETENESS * (1.0 - self.context_completeness)
            + self.WEIGHT_KNOWLEDGE_GAP * (1.0 - self.knowledge_gap_factor)
        )
        # تقييد النطاق [0, 1]
        self.composite = max(0.0, min(1.0, self.composite))
        return self.composite

    def to_dict(self) -> dict:
        return {
            "confidence_variance": round(self.confidence_variance, 4),
            "topic_complexity": round(self.topic_complexity, 4),
            "context_completeness": round(self.context_completeness, 4),
            "knowledge_gap_factor": round(self.knowledge_gap_factor, 4),
            "composite": round(self.composite, 4),
        }


@dataclass
class RoutingDecision:
    """
    قرار التوجيه — ناتج توجيه النظام المزدوج.
    
    يسجل أي نظام تم اختياره ولماذا، مع تفاصيل عدم اليقين.
    """
    system: SystemChoice = SystemChoice.SYSTEM_1
    uncertainty: Optional[UncertaintyScore] = None
    threshold: float = DEFAULT_UNCERTAINTY_THRESHOLD
    topic: str = ""
    timestamp: float = 0.0
    duration_ms: float = 0.0
    metadata: dict = field(default_factory=dict)

    @property
    def is_deep(self) -> bool:
        """هل تم توجيه المهمة إلى النظام العميق؟"""
        return self.system == SystemChoice.SYSTEM_2

    def to_dict(self) -> dict:
        return {
            "system": self.system.value,
            "uncertainty": self.uncertainty.to_dict() if self.uncertainty else None,
            "threshold": round(self.threshold, 4),
            "topic": self.topic[:100],
            "is_deep": self.is_deep,
            "timestamp": self.timestamp,
            "duration_ms": round(self.duration_ms, 1),
            "metadata": self.metadata,
        }


@dataclass
class System1Result:
    """نتيجة النظام الأول — System 1 output."""
    response: str = ""
    confidence: float = 0.0
    consensus_level: float = 0.0
    brain_count: int = 0
    duration_ms: float = 0.0
    deliberation_cjs: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "system": "system_1",
            "response": self.response,
            "confidence": round(self.confidence, 4),
            "consensus_level": round(self.consensus_level, 4),
            "brain_count": self.brain_count,
            "duration_ms": round(self.duration_ms, 1),
            "deliberation_cjs": round(self.deliberation_cjs, 4),
            "metadata": self.metadata,
        }


@dataclass
class PipelineStageResult:
    """نتيجة مرحلة خط الأنابيب — Single pipeline stage output."""
    stage: PipelineStage = PipelineStage.PLANNING
    output: dict = field(default_factory=dict)
    confidence: float = 0.0
    duration_ms: float = 0.0
    iteration: int = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "stage": self.stage.value,
            "confidence": round(self.confidence, 4),
            "duration_ms": round(self.duration_ms, 1),
            "iteration": self.iteration,
            "metadata": self.metadata,
            "output_keys": list(self.output.keys()),
        }


@dataclass
class System2Result:
    """نتيجة النظام الثاني — System 2 output."""
    response: str = ""
    confidence: float = 0.0
    stages: list[PipelineStageResult] = field(default_factory=list)
    refinement_iterations: int = 0
    duration_ms: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "system": "system_2",
            "response": self.response,
            "confidence": round(self.confidence, 4),
            "stages": [s.to_dict() for s in self.stages],
            "refinement_iterations": self.refinement_iterations,
            "duration_ms": round(self.duration_ms, 1),
            "metadata": self.metadata,
        }


@dataclass
class ReasoningOutcome:
    """
    نتيجة الاستدلال النهائية — Final reasoning outcome.
    
    يتضمن نتيجة النظام المستخدم وقرار التوجيه.
    """
    decision: RoutingDecision = field(default_factory=RoutingDecision)
    system1_result: Optional[System1Result] = None
    system2_result: Optional[System2Result] = None
    duration_ms: float = 0.0

    @property
    def response(self) -> str:
        """الاستجابة النهائية من أي نظام تم استخدامه."""
        if self.system2_result:
            return self.system2_result.response
        if self.system1_result:
            return self.system1_result.response
        return ""

    @property
    def confidence(self) -> float:
        """مستوى الثقة النهائي."""
        if self.system2_result:
            return self.system2_result.confidence
        if self.system1_result:
            return self.system1_result.confidence
        return 0.0

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.to_dict(),
            "system1_result": self.system1_result.to_dict() if self.system1_result else None,
            "system2_result": self.system2_result.to_dict() if self.system2_result else None,
            "response": self.response[:200],
            "confidence": round(self.confidence, 4),
            "duration_ms": round(self.duration_ms, 1),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# بوابة عدم اليقين — UncertaintyGate
# ═══════════════════════════════════════════════════════════════════════════════


class UncertaintyGate:
    """
    بوابة عدم اليقين — تحدد ما إذا كانت المهمة تحتاج استدلالًا عميقًا.
    
    تحسب نقاط عدم اليقين المركبة من أربعة عوامل:
    
    1. تباين الثقة: مدى اختلاف مستويات ثقة الأدمغة.
       - تباين عالي = الأدمغة غير متفقة = عدم يقين أعلى
       - الصيغة: var(confidences) مُطبّعة إلى [0, 1]
    
    2. تعقيد الموضوع: مدى تعقيد السؤال أو المهمة.
       - أسئلة أطول، متعددة الأجزاء، أو تتضمن مفاهيم مجردة = أعلى
       - يُحسب من: طول النص، عدد الأقسام، تنوع المفردات
    
    3. اكتمال السياق: هل السياق المقدم كافٍ للإجابة؟
       - مفاتيح مفقودة، بيانات ناقصة = اكتمال أقل = عدم يقين أعلى
    
    4. الفجوات المعرفية: هل يفتقر النظام إلى معرفة ضرورية؟
       - من WorldModelV2.detect_knowledge_gap()
       - فجوات عالية = عدم يقين أعلى
    
    القرار:
      - إذا عدم اليقين > العتبة ← النظام 2
      - إذا عدم اليقين ≤ العتبة ← النظام 1
    """

    def __init__(
        self,
        threshold: float = DEFAULT_UNCERTAINTY_THRESHOLD,
        *,
        variance_weight: float = 0.35,
        complexity_weight: float = 0.25,
        completeness_weight: float = 0.25,
        knowledge_gap_weight: float = 0.15,
    ):
        """
        تهيئة بوابة عدم اليقين.
        
        المعاملات:
            threshold: عتبة عدم اليقين للانتقال إلى النظام 2
            variance_weight: وزن تباين الثقة
            complexity_weight: وزن تعقيد الموضوع
            completeness_weight: وزن اكتمال السياق
            knowledge_gap_weight: وزن الفجوات المعرفية
        """
        self.threshold = threshold
        self._weights = {
            "variance": variance_weight,
            "complexity": complexity_weight,
            "completeness": completeness_weight,
            "knowledge_gap": knowledge_gap_weight,
        }

    def compute_uncertainty(
        self,
        topic: str,
        brain_responses: list[dict] | None = None,
        context: dict | None = None,
        knowledge_gaps: list[dict] | None = None,
    ) -> UncertaintyScore:
        """
        حساب عدم اليقين المركب — Compute composite uncertainty.
        
        المعاملات:
            topic: الموضوع أو السؤال المطروح
            brain_responses: استجابات الأدمغة (من DeliberationRoom)
            context: السياق المتاح للمهمة
            knowledge_gaps: الفجوات المعرفية (من WorldModelV2)
        
        النتيجة:
            UncertaintyScore مع العوامل الفردية والمركبة
        """
        brain_responses = brain_responses or []
        context = context or {}
        knowledge_gaps = knowledge_gaps or []

        # ─── العامل 1: تباين الثقة عبر الأدمغة ─────────────────────────
        confidence_variance = self._compute_confidence_variance(brain_responses)

        # ─── العامل 2: تعقيد الموضوع ─────────────────────────────────────
        topic_complexity = self._compute_topic_complexity(topic)

        # ─── العامل 3: اكتمال السياق ────────────────────────────────────
        context_completeness = self._compute_context_completeness(context)

        # ─── العامل 4: الفجوات المعرفية ─────────────────────────────────
        knowledge_gap_factor = self._compute_knowledge_gap_factor(knowledge_gaps)

        score = UncertaintyScore(
            confidence_variance=confidence_variance,
            topic_complexity=topic_complexity,
            context_completeness=context_completeness,
            knowledge_gap_factor=knowledge_gap_factor,
        )

        # تطبيق الأوزان المخصصة
        score.WEIGHT_VARIANCE = self._weights["variance"]
        score.WEIGHT_COMPLEXITY = self._weights["complexity"]
        score.WEIGHT_COMPLETENESS = self._weights["completeness"]
        score.WEIGHT_KNOWLEDGE_GAP = self._weights["knowledge_gap"]

        score.compute_composite()
        return score

    def should_use_system2(self, uncertainty: UncertaintyScore) -> bool:
        """
        هل يجب استخدام النظام الثاني؟ — Should we engage deep reasoning?
        
        إذا عدم اليقين المركب > العتبة، ننتقل إلى النظام 2.
        """
        return uncertainty.composite > self.threshold

    def route(self, uncertainty: UncertaintyScore) -> SystemChoice:
        """
        توجيه المهمة — Route based on uncertainty.
        
        النتيجة:
            SystemChoice.SYSTEM_1 أو SystemChoice.SYSTEM_2
        """
        if self.should_use_system2(uncertainty):
            return SystemChoice.SYSTEM_2
        return SystemChoice.SYSTEM_1

    # ─── طرق حساب العوامل الفردية ──────────────────────────────────────────

    def _compute_confidence_variance(self, responses: list[dict]) -> float:
        """
        حساب تباين الثقة — Confidence variance across brains.
        
        تباين عالي يعني أن الأدمغة غير متفقة → عدم يقين أعلى.
        يُطبّع إلى [0, 1] باستخدام دالة سيجمويدية.
        """
        if not responses:
            return 0.7  # لا توجد استجابات = عدم يقين مرتفع

        confidences = [r.get("confidence", 0.5) for r in responses]

        if len(confidences) < 2:
            # دماغ واحد فقط — لا يمكن حساب التباين بدقة
            return 0.3

        avg = sum(confidences) / len(confidences)
        variance = sum((c - avg) ** 2 for c in confidences) / len(confidences)
        std_dev = math.sqrt(variance)

        # تطبيع: الانحراف المعياري في النطاق [0, 0.5] تقريباً
        # نستخدم دالة سيجمويدية للتحويل إلى [0, 1]
        normalized = 1.0 - 1.0 / (1.0 + std_dev * 4.0)

        return max(0.0, min(1.0, normalized))

    def _compute_topic_complexity(self, topic: str) -> float:
        """
        حساب تعقيد الموضوع — Topic complexity estimation.
        
        العوامل:
        - طول النص (أطول = أعقد احتمالاً)
        - عدد الجمل/الأقسام (محدد بـ .؟!،)
        - تنوع المفردات (نسبة الكلمات الفريدة)
        - وجود مصطلحات تقنية/مجردة
        """
        if not topic or not topic.strip():
            return 0.0

        text = topic.strip()

        # عامل 1: الطول — تطبيع باستخدام لوغاريتم
        # النصوص القصيرة (< 20 حرف) = 0.1، المتوسطة = 0.4، الطويلة (> 500) = 0.8
        length_factor = min(1.0, math.log1p(len(text)) / math.log1p(500))

        # عامل 2: عدد الجمل/الأقسام
        # نحسب علامات الترقيم العربية والإنجليزية
        sentence_markers = sum(
            1 for ch in text
            if ch in ".؟!،;,؛\n"
        )
        sentence_factor = min(1.0, sentence_markers / 10.0)

        # عامل 3: تنوع المفردات (type-token ratio)
        words = text.split()
        if words:
            unique_ratio = len(set(w.lower() for w in words)) / len(words)
            # تنوع عالي (0.8+) يعني مفردات متنوعة = تعقيد أعلى
            diversity_factor = unique_ratio * 0.5
        else:
            diversity_factor = 0.0

        # عامل 4: مصطلحات تقنية/مجردة
        # كلمات مفتاحية تدل على تعقيد (عربي وإنجليزي)
        complexity_keywords = {
            # إنجليزي
            "analyze", "compare", "evaluate", "synthesize", "why", "how",
            "explain", "derive", "prove", "optimize", "trade-off",
            "contradiction", "paradox", "implication", "consequence",
            # عربي
            "حلل", "قارن", "قيّم", "ركّب", "لماذا", "كيف",
            "اشرح", "استنتج", "أثبت", "حسّن", "تنازع",
            "مفارقة", "تضمين", "نتيجة", "علاقة سببية",
        }
        text_lower = text.lower()
        keyword_hits = sum(1 for kw in complexity_keywords if kw in text_lower)
        keyword_factor = min(1.0, keyword_hits / 3.0)

        # المركب المرجح
        complexity = (
            length_factor * 0.25
            + sentence_factor * 0.25
            + diversity_factor * 0.25
            + keyword_factor * 0.25
        )

        return max(0.0, min(1.0, complexity))

    def _compute_context_completeness(self, context: dict) -> float:
        """
        حساب اكتمال السياق — Context completeness score.
        
        يفحص المفاتيح المتوقعة في السياق:
        - goal: الهدف المطلوب
        - state: الحالة الحالية
        - history: السجل السابق
        - domain: المجال
        - constraints: القيود
        
        كل مفتاح متوفر يزيد الاكتمال.
        القيم الفارغة تُحسب كنصف نقطة.
        """
        if not context:
            return 0.1  # لا سياق = اكتمال منخفض جداً

        # المفاتيح الأساسية المتوقعة
        primary_keys = {"goal", "state", "history"}
        # المفاتيح الثانوية المفيدة
        secondary_keys = {"domain", "constraints", "errors", "preferences", "metadata"}

        primary_score = 0.0
        for key in primary_keys:
            if key in context:
                value = context[key]
                if value and value not in ("", [], {}, None):
                    primary_score += 1.0  # قيمة حقيقية
                else:
                    primary_score += 0.4  # مفتاح موجود لكن فارغ

        secondary_score = 0.0
        for key in secondary_keys:
            if key in context:
                value = context[key]
                if value and value not in ("", [], {}, None):
                    secondary_score += 0.5
                else:
                    secondary_score += 0.2

        # تطبيع: 3 مفاتيح أساسية × 1.0 + 5 ثانوية × 0.5 = 5.5 كحد أقصى
        max_possible = len(primary_keys) * 1.0 + len(secondary_keys) * 0.5
        completeness = (primary_score + secondary_score) / max_possible

        return max(0.0, min(1.0, completeness))

    def _compute_knowledge_gap_factor(self, knowledge_gaps: list[dict]) -> float:
        """
        حساب عامل الفجوة المعرفية — Knowledge gap factor.
        
        كل فجوة تقلل العامل. الفجوات عالية الخطورة تقلل أكثر.
        العامل 1.0 = لا فجوات (يقين عالي)
        العامل 0.0 = فجوات كثيرة وحرجة (عدم يقين عالي)
        
        يُعاد استخدام المنطق من DeliberationRoom._calculate_knowledge_gap_factor
        مع تعديلات للتكامل.
        """
        if not knowledge_gaps:
            return 1.0  # لا فجوات = ثقة كاملة

        # تصنيف حسب الخطورة
        high_severity = sum(
            1 for g in knowledge_gaps
            if isinstance(g, dict) and g.get("severity") == "high"
        )
        medium_severity = sum(
            1 for g in knowledge_gaps
            if isinstance(g, dict) and g.get("severity") == "medium"
        )
        low_severity = sum(
            1 for g in knowledge_gaps
            if isinstance(g, dict) and g.get("severity") == "low"
        )
        # فجوات بدون تصنيف خطورة
        unclassified = len(knowledge_gaps) - high_severity - medium_severity - low_severity

        # نقاط مرجحة: خطورة عالية = تأثير أكبر
        gap_score = (
            high_severity * 0.5
            + medium_severity * 0.3
            + low_severity * 0.1
            + unclassified * 0.2
        )

        # تحويل إلى عامل عكسي باستخدام دالة تناقصية
        # كلما زادت الفجوات، قلّ العامل
        factor = 1.0 / (1.0 + gap_score)

        return max(0.0, min(1.0, factor))


# ═══════════════════════════════════════════════════════════════════════════════
# مقاييس عدم اليقين — UncertaintyMetrics
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class UncertaintyRecord:
    """سجل عدم يقين واحد — Single uncertainty tracking record."""
    timestamp: float = 0.0
    uncertainty_composite: float = 0.0
    system_choice: SystemChoice = SystemChoice.SYSTEM_1
    outcome_confidence: float = 0.0  # ثقة النتيجة الفعلية (للمعايرة)
    topic_hash: str = ""              # تجزئة الموضوع (للخصوصية)


class UncertaintyMetrics:
    """
    مقاييس عدم اليقين — تتبع عدم اليقين عبر الزمن ومعايرة العتبة.
    
    يوفر:
    1. تتبع تاريخ عدم اليقين وتوجيه النظام
    2. معايرة العتبة بناءً على نتائج التغذية الراجعة
    3. إحصائيات استخدام النظام 1 مقابل النظام 2
    4. كشف الانحراف في عدم اليقين (هل يتحسن أو يتفاقم؟)
    
    آلية المعايرة:
    - إذا النظام 1 ينتج ثقة منخفضة بشكل متكرر → زيادة العتبة (المزيد → النظام 2)
    - إذا النظام 2 ينتج ثقة عالية بشكل متكرر → تقليل العتبة (أقل → النظام 2)
    - يستخدم المتوسط المتحرك الأسي (EMA) للتحديث التدريجي
    """

    # حدود المعايرة
    THRESHOLD_MIN = 0.3    # لا تقل العتبة عن هذا (لا نريد كل شيء ← النظام 2)
    THRESHOLD_MAX = 0.8    # لا تزيد العتبة عن هذا (لا نريد إهمال النظام 2)
    CALIBRATION_RATE = 0.05  # معدل تحديث EMA (بطيء = مستقر)

    def __init__(
        self,
        initial_threshold: float = DEFAULT_UNCERTAINTY_THRESHOLD,
        max_history: int = 5000,
        calibration_enabled: bool = True,
    ):
        """
        تهيئة مقاييس عدم اليقين.
        
        المعاملات:
            initial_threshold: العتبة الابتدائية
            max_history: الحد الأقصى لسجلات التاريخ
            calibration_enabled: تفعيل المعايرة التلقائية
        """
        self._threshold = initial_threshold
        self._max_history = max_history
        self._calibration_enabled = calibration_enabled
        self._history: list[UncertaintyRecord] = []

        # عدادات الإحصائيات
        self._system1_count: int = 0
        self._system2_count: int = 0
        self._system1_low_confidence_count: int = 0  # نظام 1 بثقة منخفضة
        self._system2_high_confidence_count: int = 0  # نظام 2 بثقة عالية

        # EMA لمتوسط عدم اليقين
        self._uncertainty_ema: float = 0.0
        self._ema_alpha: float = 0.1

    @property
    def threshold(self) -> float:
        """العتبة الحالية (قد تتغير مع المعايرة)."""
        return self._threshold

    @property
    def history_size(self) -> int:
        """عدد السجلات المخزنة."""
        return len(self._history)

    def record(
        self,
        uncertainty: UncertaintyScore,
        system_choice: SystemChoice,
        outcome_confidence: float,
        topic: str = "",
    ) -> None:
        """
        تسجيل قرار توجيه ونتيجته — Record a routing decision and its outcome.
        
        المعاملات:
            uncertainty: نقاط عدم اليقين
            system_choice: النظام المختار
            outcome_confidence: ثقة النتيجة الفعلية
            topic: الموضوع (يُخزن كتجزئة فقط)
        """
        # تجزئة الموضوع للخصوصية
        topic_hash = hashlib.sha256(
            topic.encode("utf-8")
        ).hexdigest()[:16] if topic else ""

        record_obj = UncertaintyRecord(
            timestamp=time.time(),
            uncertainty_composite=uncertainty.composite,
            system_choice=system_choice,
            outcome_confidence=outcome_confidence,
            topic_hash=topic_hash,
        )
        self._history.append(record_obj)

        # تحديث العدادات
        if system_choice == SystemChoice.SYSTEM_1:
            self._system1_count += 1
            if outcome_confidence < 0.4:
                self._system1_low_confidence_count += 1
        else:
            self._system2_count += 1
            if outcome_confidence > 0.7:
                self._system2_high_confidence_count += 1

        # تحديث EMA لعدم اليقين
        if self._uncertainty_ema == 0.0:
            self._uncertainty_ema = uncertainty.composite
        else:
            self._uncertainty_ema = (
                self._ema_alpha * uncertainty.composite
                + (1.0 - self._ema_alpha) * self._uncertainty_ema
            )

        # تقليم التاريخ
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # معايرة العتبة
        if self._calibration_enabled:
            self._calibrate_threshold()

    def _calibrate_threshold(self) -> None:
        """
        معايرة العتبة — Calibrate threshold based on recent outcomes.
        
        المنطق:
        - إذا النظام 1 ينتج ثقة منخفضة بشكل متكرر (> 30% من الحالات)
          → العتبة مرتفعة جداً → ننقصها قليلاً ← المزيد ← النظام 2
        - إذا النظام 2 ينتج ثقة عالية بشكل متكرر (> 70% من الحالات)
          → العتبة منخفضة جداً → نزيدها قليلاً ← أقل ← النظام 2
        """
        min_samples = 10  # لا نعاير قبل هذا العدد من العينات

        if self._system1_count < min_samples and self._system2_count < min_samples:
            return

        adjustment = 0.0

        # فحص أداء النظام 1
        if self._system1_count >= min_samples:
            s1_low_ratio = self._system1_low_confidence_count / self._system1_count
            if s1_low_ratio > 0.3:
                # نظام 1 يفشل كثيراً — نخفض العتبة لإرسال المزيد ← النظام 2
                adjustment -= self.CALIBRATION_RATE * (s1_low_ratio - 0.3)

        # فحص أداء النظام 2
        if self._system2_count >= min_samples:
            s2_high_ratio = self._system2_high_confidence_count / self._system2_count
            if s2_high_ratio > 0.7:
                # نظام 2 ينجح كثيراً — ربما نستخدمه أكثر من اللازم
                # نرفع العتبة لإرسال أقل ← النظام 2
                adjustment += self.CALIBRATION_RATE * (s2_high_ratio - 0.7)

        # تطبيق التعديل مع التقييد
        self._threshold = max(
            self.THRESHOLD_MIN,
            min(self.THRESHOLD_MAX, self._threshold + adjustment),
        )

    def get_statistics(self) -> dict:
        """
        الحصول على إحصائيات — Get current metrics and statistics.
        """
        total = self._system1_count + self._system2_count
        recent_uncertainties = [
            r.uncertainty_composite
            for r in self._history[-100:]
        ]
        avg_recent = (
            sum(recent_uncertainties) / len(recent_uncertainties)
            if recent_uncertainties
            else 0.0
        )

        return {
            "threshold": round(self._threshold, 4),
            "system1_count": self._system1_count,
            "system2_count": self._system2_count,
            "total_decisions": total,
            "system1_ratio": round(self._system1_count / max(1, total), 4),
            "system2_ratio": round(self._system2_count / max(1, total), 4),
            "system1_low_confidence_rate": round(
                self._system1_low_confidence_count / max(1, self._system1_count), 4
            ),
            "system2_high_confidence_rate": round(
                self._system2_high_confidence_count / max(1, self._system2_count), 4
            ),
            "uncertainty_ema": round(self._uncertainty_ema, 4),
            "avg_recent_uncertainty": round(avg_recent, 4),
            "calibration_enabled": self._calibration_enabled,
            "history_size": len(self._history),
        }

    def detect_uncertainty_drift(self, window: int = 100) -> dict:
        """
        كشف انحراف عدم اليقين — Detect if uncertainty is trending.
        
        يقارن متوسط عدم اليقين في النافذة الأخيرة مع الفترة السابقة.
        
        النتيجة:
            dict يحتوي على اتجاه عدم اليقين ومقداره
        """
        if len(self._history) < window * 2:
            return {
                "drift": 0.0,
                "direction": "insufficient_data",
                "description": "بيانات غير كافية لكشف الانحراف",
            }

        recent = self._history[-window:]
        previous = self._history[-(window * 2):-window]

        avg_recent = sum(r.uncertainty_composite for r in recent) / len(recent)
        avg_previous = sum(r.uncertainty_composite for r in previous) / len(previous)

        drift = avg_recent - avg_previous

        if drift > 0.05:
            direction = "increasing"
            description = "عدم اليقين في ازدياد — قد يحتاج النظام لتعديل العتبة"
        elif drift < -0.05:
            direction = "decreasing"
            description = "عدم اليقين في تناقص — النظام يتحسن"
        else:
            direction = "stable"
            description = "عدم اليقين مستقر"

        return {
            "drift": round(drift, 4),
            "direction": direction,
            "description": description,
            "avg_recent": round(avg_recent, 4),
            "avg_previous": round(avg_previous, 4),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# وكلاء خط الأنابيب — Pipeline Agents
# ═══════════════════════════════════════════════════════════════════════════════


class PipelineAgent(ABC):
    """
    وكيل خط أنابيب أساسي — Base class for System 2 pipeline agents.
    
    كل وكيل يقوم بمرحلة واحدة من خط الأنابيب الخماسي:
    مخطط ← مولد فرضيات ← مسترجع ← مركّب ← صانع قرار
    """

    def __init__(self, name: str, arabic_name: str):
        self.name = name
        self.arabic_name = arabic_name

    @abstractmethod
    async def process(
        self,
        topic: str,
        context: dict,
        previous_stages: list[PipelineStageResult],
    ) -> PipelineStageResult:
        """
        معالجة المرحلة — Process this pipeline stage.
        
        المعاملات:
            topic: الموضوع الأصلي
            context: السياق المشترك
            previous_stages: نتائج المراحل السابقة
        
        النتيجة:
            PipelineStageResult مع مخرجات هذه المرحلة
        """
        ...

    def _build_stage_result(
        self,
        stage: PipelineStage,
        output: dict,
        confidence: float,
        duration_ms: float,
        iteration: int = 0,
        metadata: dict | None = None,
    ) -> PipelineStageResult:
        """بناء نتيجة مرحلة موحدة."""
        return PipelineStageResult(
            stage=stage,
            output=output,
            confidence=max(0.0, min(1.0, confidence)),
            duration_ms=duration_ms,
            iteration=iteration,
            metadata=metadata or {},
        )


class PlannerAgent(PipelineAgent):
    """
    وكيل التخطيط — المرحلة 1: تحليل المشكلة وتفكيكها.
    
    يقوم بـ:
    - تحليل الموضوع وتحديد نوع المشكلة
    - تفكيك المشكلة إلى أجزاء فرعية
    - تحديد الاستراتيجية المناسبة
    - تقدير الموارد المطلوبة
    """

    def __init__(self):
        super().__init__("Planner", "المخطط")

    async def process(
        self,
        topic: str,
        context: dict,
        previous_stages: list[PipelineStageResult],
    ) -> PipelineStageResult:
        """تحليل المشكلة وتفكيكها."""
        start_time = time.time()

        # تحليل نوع المشكلة
        problem_type = self._classify_problem(topic)

        # تفكيك المشكلة
        sub_problems = self._decompose_problem(topic, context)

        # تحديد الاستراتيجية
        strategy = self._select_strategy(problem_type, sub_problems)

        # تقدير الموارد
        resource_estimate = self._estimate_resources(sub_problems, strategy)

        confidence = self._compute_planning_confidence(
            problem_type, sub_problems, context
        )

        duration_ms = (time.time() - start_time) * 1000

        return self._build_stage_result(
            stage=PipelineStage.PLANNING,
            output={
                "problem_type": problem_type,
                "sub_problems": sub_problems,
                "strategy": strategy,
                "resource_estimate": resource_estimate,
            },
            confidence=confidence,
            duration_ms=duration_ms,
            metadata={"arabic_name": self.arabic_name},
        )

    def _classify_problem(self, topic: str) -> str:
        """تصنيف المشكلة — Classify problem type."""
        topic_lower = topic.lower()

        # أنواع المشاكل مع كلمات مفتاحية
        problem_types = {
            "factual": ["ما هو", "ما هي", "who", "what", "where", "when", "كم"],
            "analytical": ["لماذا", "كيف", "why", "how", "تحليل", "analyze"],
            "evaluative": ["أفضل", "أي", "which", "best", "compare", "قارن", "قيّم"],
            "creative": ["اقترح", "صمّم", "ابتكر", "suggest", "design", "create"],
            "causal": ["سبب", "نتيجة", "because", "therefore", "بسبب", "لذلك"],
        }

        scores: dict[str, int] = {}
        for ptype, keywords in problem_types.items():
            scores[ptype] = sum(1 for kw in keywords if kw in topic_lower)

        best_type = max(scores, key=scores.get) if scores else "analytical"
        return best_type

    def _decompose_problem(self, topic: str, context: dict) -> list[dict]:
        """تفكيك المشكلة — Decompose into sub-problems."""
        sub_problems: list[dict] = []

        # تقسيم حسب علامات الترقيم والروابط
        separators = [" و", " و", "،", " ثم ", " بعد ذلك ", " and ", ", ", " then "]
        parts = [topic]
        for sep in separators:
            new_parts: list[str] = []
            for part in parts:
                new_parts.extend(part.split(sep))
            parts = new_parts

        # تصفية الأجزاء الفارغة وإنشاء مشاكل فرعية
        for i, part in enumerate(parts):
            part = part.strip()
            if part and len(part) > 3:
                sub_problems.append({
                    "id": f"sub_{i}",
                    "description": part,
                    "priority": 1.0 / (i + 1),  # الأولوية تناقصية
                    "status": "pending",
                })

        # إذا لم نجد أجزاء، الموضوع كامل كمشكلة واحدة
        if not sub_problems:
            sub_problems.append({
                "id": "sub_0",
                "description": topic,
                "priority": 1.0,
                "status": "pending",
            })

        return sub_problems[:10]  # حد أقصى 10 مشاكل فرعية

    def _select_strategy(self, problem_type: str, sub_problems: list[dict]) -> dict:
        """تحديد الاستراتيجية — Select reasoning strategy."""
        strategies = {
            "factual": {
                "approach": "retrieval_first",
                "description": "استرجاع المعلومات أولاً ثم التحقق",
                "stages_priority": ["retrieval", "synthesis", "decision"],
            },
            "analytical": {
                "approach": "hypothesis_driven",
                "description": "توليد فرضيات ثم اختبارها",
                "stages_priority": ["hypothesis", "retrieval", "synthesis", "decision"],
            },
            "evaluative": {
                "approach": "comparative",
                "description": "مقارنة البدائل وتقييمها",
                "stages_priority": ["hypothesis", "retrieval", "synthesis", "decision"],
            },
            "creative": {
                "approach": "exploratory",
                "description": "استكشاف الفضاء الإبداعي",
                "stages_priority": ["hypothesis", "synthesis", "decision"],
            },
            "causal": {
                "approach": "causal_chain",
                "description": "تتبع السلاسل السببية",
                "stages_priority": ["hypothesis", "retrieval", "synthesis", "decision"],
            },
        }

        return strategies.get(problem_type, strategies["analytical"])

    def _estimate_resources(self, sub_problems: list[dict], strategy: dict) -> dict:
        """تقدير الموارد — Estimate resources needed."""
        return {
            "estimated_stages": len(strategy.get("stages_priority", [])),
            "sub_problem_count": len(sub_problems),
            "estimated_complexity": min(1.0, len(sub_problems) / 5.0),
        }

    def _compute_planning_confidence(
        self, problem_type: str, sub_problems: list[dict], context: dict
    ) -> float:
        """حساب ثقة التخطيط."""
        # قاعدة الثقة
        confidence = 0.6

        # تحسين بناءً على وضوح المشكلة
        if len(sub_problems) == 1:
            confidence += 0.1  # مشكلة واحدة واضحة
        elif len(sub_problems) <= 3:
            confidence += 0.05  # مشاكل قليلة manageable

        # تحسين بناءً على وجود سياق
        if context.get("goal"):
            confidence += 0.1
        if context.get("domain"):
            confidence += 0.05

        # تقليل بناءً على كثرة المشاكل الفرعية
        if len(sub_problems) > 5:
            confidence -= 0.1

        return max(0.0, min(1.0, confidence))


class HypothesisGeneratorAgent(PipelineAgent):
    """
    وكيل توليد الفرضيات — المرحلة 2: توليد فرضيات متعددة.
    
    يقوم بـ:
    - توليد فرضيات متعددة للإجابة
    - تقييم أولي لكل فرضية
    - تحديد الفرضيات الأكثر قابلية للاختبار
    - استخدام الاستدلال السببي إذا توفر
    """

    def __init__(self, causal_reasoner: CausalReasoner | None = None):
        super().__init__("HypothesisGenerator", "مولد الفرضيات")
        self._causal_reasoner = causal_reasoner

    async def process(
        self,
        topic: str,
        context: dict,
        previous_stages: list[PipelineStageResult],
    ) -> PipelineStageResult:
        """توليد فرضيات متعددة."""
        start_time = time.time()

        # استخراج معلومات التخطيط
        planning_output: dict = {}
        if previous_stages:
            planning_output = previous_stages[0].output

        sub_problems = planning_output.get("sub_problems", [])
        strategy = planning_output.get("strategy", {})

        # توليد الفرضيات
        hypotheses = self._generate_hypotheses(topic, sub_problems, context)

        # تقييم أولي للفرضيات
        evaluated = self._evaluate_hypotheses(hypotheses, context)

        # تحسين بالاستدلال السببي
        if self._causal_reasoner:
            evaluated = await self._enhance_with_causality(evaluated, context)

        confidence = self._compute_hypothesis_confidence(evaluated)

        duration_ms = (time.time() - start_time) * 1000

        return self._build_stage_result(
            stage=PipelineStage.HYPOTHESIS,
            output={
                "hypotheses": evaluated,
                "strategy_approach": strategy.get("approach", "unknown"),
                "total_hypotheses": len(evaluated),
                "top_hypothesis": evaluated[0] if evaluated else None,
            },
            confidence=confidence,
            duration_ms=duration_ms,
            metadata={"arabic_name": self.arabic_name},
        )

    def _generate_hypotheses(
        self,
        topic: str,
        sub_problems: list[dict],
        context: dict,
    ) -> list[dict]:
        """توليد الفرضيات — Generate multiple hypotheses."""
        hypotheses: list[dict] = []

        # فرضية مباشرة: الإجابة الأكثر وضوحاً
        hypotheses.append({
            "id": "h_direct",
            "type": "direct",
            "description": f"الإجابة المباشرة: {topic[:80]}",
            "priority": 0.7,
            "testable": True,
        })

        # فرضية بديلة: منظور مختلف
        hypotheses.append({
            "id": "h_alternative",
            "type": "alternative",
            "description": f"منظور بديل: ماذا لو كان العكس صحيحاً؟",
            "priority": 0.5,
            "testable": True,
        })

        # فرضية تركيبية: دمج الأجزاء
        if len(sub_problems) > 1:
            hypotheses.append({
                "id": "h_synthesis",
                "type": "synthesis",
                "description": f"تركيب من {len(sub_problems)} أجزاء فرعية",
                "priority": 0.6,
                "testable": True,
            })

        # فرضيات خاصة بكل مشكلة فرعية
        for i, sub in enumerate(sub_problems[:3]):
            hypotheses.append({
                "id": f"h_sub_{i}",
                "type": "sub_problem",
                "description": f"فرضية للمشكلة الفرعية: {sub.get('description', '')[:60]}",
                "priority": sub.get("priority", 0.3),
                "testable": True,
            })

        # فرضية سببية إذا كان السياق يحتوي أخطاء
        if context.get("errors"):
            hypotheses.append({
                "id": "h_causal",
                "type": "causal",
                "description": "فرضية سببية بناءً على أنماط الأخطاء",
                "priority": 0.4,
                "testable": True,
            })

        return hypotheses

    def _evaluate_hypotheses(
        self, hypotheses: list[dict], context: dict
    ) -> list[dict]:
        """تقييم أولي للفرضيات — Evaluate hypotheses."""
        evaluated: list[dict] = []

        for h in hypotheses:
            score = h.get("priority", 0.3)

            # تحسين بناءً على السياق
            if context.get("goal") and h["type"] == "direct":
                score += 0.1

            if context.get("errors") and h["type"] == "causal":
                score += 0.15

            # تطبيع
            score = max(0.0, min(1.0, score))

            evaluated.append({
                **h,
                "initial_score": round(score, 4),
            })

        # ترتيب حسب النقاط
        evaluated.sort(key=lambda x: x["initial_score"], reverse=True)
        return evaluated

    async def _enhance_with_causality(
        self, hypotheses: list[dict], context: dict
    ) -> list[dict]:
        """تحسين الفرضيات بالاستدلال السببي — Enhance with causal reasoning."""
        errors = context.get("errors", [])
        if not errors or not self._causal_reasoner:
            return hypotheses

        try:
            rules = await self._causal_reasoner.analyze_root_cause(errors)
            for h in hypotheses:
                if h["type"] == "causal" and rules:
                    # تحسين نقاط الفرضية السببية بناءً على القواعد المكتشفة
                    max_rule_conf = max(r.confidence for r in rules) if rules else 0.0
                    h["initial_score"] = min(1.0, h.get("initial_score", 0.3) + max_rule_conf * 0.2)
                    h["causal_rules_count"] = len(rules)
        except Exception as e:
            logger.warning(f"فشل تحسين الفرضيات بالسببية: {e}")

        return hypotheses

    def _compute_hypothesis_confidence(self, hypotheses: list[dict]) -> float:
        """حساب ثقة مرحلة الفرضيات."""
        if not hypotheses:
            return 0.2  # لا فرضيات = ثقة منخفضة

        # متوسط نقاط الفرضيات
        avg_score = sum(h.get("initial_score", 0.3) for h in hypotheses) / len(hypotheses)

        # تنوع الفرضيات يعطي ثقة أعلى
        unique_types = len(set(h.get("type", "") for h in hypotheses))
        diversity_bonus = min(0.15, unique_types * 0.03)

        return max(0.0, min(1.0, avg_score + diversity_bonus))


class RetrieverAgent(PipelineAgent):
    """
    وكيل الاسترجاع — المرحلة 3: جلب المعرفة ذات الصلة.
    
    يقوم بـ:
    - البحث في الذاكرة الثلاثية عن معرفة ذات صلة
    - استرجاع الفجوات المعرفية من WorldModelV2
    - تجميع الأدلة المؤيدة والمعارضة
    - تحديد مدى كفاية المعلومات
    """

    def __init__(self):
        super().__init__("Retriever", "المسترجع")

    async def process(
        self,
        topic: str,
        context: dict,
        previous_stages: list[PipelineStageResult],
    ) -> PipelineStageResult:
        """جلب المعرفة ذات الصلة."""
        start_time = time.time()

        # استخراج معلومات الفرضيات
        hypothesis_output: dict = {}
        for stage in previous_stages:
            if stage.stage == PipelineStage.HYPOTHESIS:
                hypothesis_output = stage.output
                break

        hypotheses = hypothesis_output.get("hypotheses", [])

        # استرجاع المعرفة من السياق والذاكرة
        knowledge = self._retrieve_knowledge(topic, context)

        # تجميع الأدلة
        evidence = self._gather_evidence(hypotheses, knowledge, context)

        # تحديد كفاية المعلومات
        information_sufficiency = self._assess_sufficiency(evidence, context)

        confidence = information_sufficiency

        duration_ms = (time.time() - start_time) * 1000

        return self._build_stage_result(
            stage=PipelineStage.RETRIEVAL,
            output={
                "knowledge_items": knowledge,
                "evidence": evidence,
                "information_sufficiency": round(information_sufficiency, 4),
                "gaps_remaining": context.get("knowledge_gaps", []),
            },
            confidence=confidence,
            duration_ms=duration_ms,
            metadata={"arabic_name": self.arabic_name},
        )

    def _retrieve_knowledge(self, topic: str, context: dict) -> list[dict]:
        """استرجاع المعرفة — Retrieve relevant knowledge."""
        knowledge: list[dict] = []

        # من السياق المباشر
        if context.get("history"):
            knowledge.append({
                "source": "context_history",
                "relevance": 0.8,
                "content_type": "historical",
            })

        if context.get("state"):
            knowledge.append({
                "source": "context_state",
                "relevance": 0.7,
                "content_type": "state",
            })

        if context.get("domain"):
            knowledge.append({
                "source": "context_domain",
                "relevance": 0.6,
                "content_type": "domain_knowledge",
            })

        # من الأخطاء السابقة
        if context.get("errors"):
            knowledge.append({
                "source": "error_patterns",
                "relevance": 0.5,
                "content_type": "error_knowledge",
                "error_count": len(context["errors"]),
            })

        return knowledge

    def _gather_evidence(
        self,
        hypotheses: list[dict],
        knowledge: list[dict],
        context: dict,
    ) -> dict:
        """تجميع الأدلة — Gather supporting and opposing evidence."""
        supporting: list[dict] = []
        opposing: list[dict] = []

        for item in knowledge:
            if item.get("relevance", 0) > 0.6:
                supporting.append(item)
            else:
                opposing.append(item)

        # إضافة فجوات كأدلة معارضة
        for gap in context.get("knowledge_gaps", []):
            opposing.append({
                "source": "knowledge_gap",
                "relevance": 0.3,
                "content_type": "gap",
                "gap": gap,
            })

        return {
            "supporting_count": len(supporting),
            "opposing_count": len(opposing),
            "supporting": supporting,
            "opposing": opposing,
            "balance": (
                len(supporting) / max(1, len(supporting) + len(opposing))
            ),
        }

    def _assess_sufficiency(self, evidence: dict, context: dict) -> float:
        """تحديد كفاية المعلومات — Assess information sufficiency."""
        # قاعدة: كفاية الأدلة
        balance = evidence.get("balance", 0.5)

        # عوامل مخفضة
        gaps = context.get("knowledge_gaps", [])
        gap_penalty = min(0.3, len(gaps) * 0.05)

        # عوامل محسنة
        supporting = evidence.get("supporting_count", 0)
        support_bonus = min(0.2, supporting * 0.05)

        sufficiency = balance - gap_penalty + support_bonus
        return max(0.1, min(1.0, sufficiency))


class SynthesizerAgent(PipelineAgent):
    """
    وكيل التركيب — المرحلة 4: دمج النتائج من جميع المراحل.
    
    يقوم بـ:
    - دمج الفرضيات مع الأدلة المسترجعة
    - تحديد التناقضات و حلها
    - بناء صورة شاملة
    - تقييم قوة كل استنتاج
    """

    def __init__(self):
        super().__init__("Synthesizer", "المركّب")

    async def process(
        self,
        topic: str,
        context: dict,
        previous_stages: list[PipelineStageResult],
    ) -> PipelineStageResult:
        """دمج النتائج من جميع المراحل السابقة."""
        start_time = time.time()

        # تجميع المخرجات من المراحل السابقة
        planning: dict = {}
        hypotheses: dict = {}
        retrieval: dict = {}

        for stage in previous_stages:
            if stage.stage == PipelineStage.PLANNING:
                planning = stage.output
            elif stage.stage == PipelineStage.HYPOTHESIS:
                hypotheses = stage.output
            elif stage.stage == PipelineStage.RETRIEVAL:
                retrieval = stage.output

        # دمج الفرضيات مع الأدلة
        synthesis = self._synthesize(
            topic, planning, hypotheses, retrieval, context
        )

        # تحديد التناقضات
        contradictions = self._detect_contradictions(synthesis)

        # حل التناقضات
        resolved = self._resolve_contradictions(synthesis, contradictions)

        # حساب ثقة التركيب
        confidence = self._compute_synthesis_confidence(
            resolved, previous_stages
        )

        duration_ms = (time.time() - start_time) * 1000

        return self._build_stage_result(
            stage=PipelineStage.SYNTHESIS,
            output={
                "synthesis": resolved,
                "contradictions_found": len(contradictions),
                "contradictions_resolved": len(contradictions) - sum(
                    1 for c in contradictions if c.get("unresolved", False)
                ),
                "key_findings": resolved.get("key_findings", []),
            },
            confidence=confidence,
            duration_ms=duration_ms,
            metadata={"arabic_name": self.arabic_name},
        )

    def _synthesize(
        self,
        topic: str,
        planning: dict,
        hypotheses: dict,
        retrieval: dict,
        context: dict,
    ) -> dict:
        """دمج النتائج — Synthesize all findings."""
        top_hypothesis = hypotheses.get("top_hypothesis", {})
        evidence = retrieval.get("evidence", {})
        sub_problems = planning.get("sub_problems", [])

        key_findings: list[str] = []

        # نتائج من الفرضيات
        if top_hypothesis:
            key_findings.append(
                f"الفرضية الأقوى: {top_hypothesis.get('description', 'غير محدد')[:80]}"
            )

        # نتائج من الأدلة
        supporting = evidence.get("supporting_count", 0)
        opposing = evidence.get("opposing_count", 0)
        if supporting + opposing > 0:
            key_findings.append(
                f"الأدلة: {supporting} مؤيدة، {opposing} معارضة"
            )

        # نتائج من المشاكل الفرعية
        if sub_problems:
            key_findings.append(
                f"عدد المشاكل الفرعية: {len(sub_problems)}"
            )

        # بناء التركيب
        return {
            "topic": topic,
            "problem_type": planning.get("problem_type", "unknown"),
            "top_hypothesis_id": top_hypothesis.get("id", ""),
            "evidence_balance": evidence.get("balance", 0.5),
            "information_sufficiency": retrieval.get("information_sufficiency", 0.3),
            "key_findings": key_findings,
            "sub_problem_count": len(sub_problems),
        }

    def _detect_contradictions(self, synthesis: dict) -> list[dict]:
        """كشف التناقضات — Detect contradictions in synthesis."""
        contradictions: list[dict] = []

        # تناقض: أدلة معارضة أكثر من المؤيدة
        balance = synthesis.get("evidence_balance", 0.5)
        if balance < 0.3:
            contradictions.append({
                "type": "evidence_imbalance",
                "description": "الأدلة المعارضة تفوق المؤيدة بشكل كبير",
                "severity": "high",
            })

        # تناقض: كفاية معلومات منخفضة مع فرضيات عالية الثقة
        sufficiency = synthesis.get("information_sufficiency", 0.3)
        if sufficiency < 0.4:
            contradictions.append({
                "type": "insufficient_evidence",
                "description": "معلومات غير كافية لدعم الاستنتاج",
                "severity": "medium",
            })

        return contradictions

    def _resolve_contradictions(
        self, synthesis: dict, contradictions: list[dict]
    ) -> dict:
        """حل التناقضات — Resolve detected contradictions."""
        resolved = dict(synthesis)

        for c in contradictions:
            if c["type"] == "evidence_imbalance":
                # تخفيض الثقة في حالة عدم توازن الأدلة
                resolved["evidence_balance_adjusted"] = max(
                    0.1, resolved.get("evidence_balance", 0.5) * 0.7
                )
                c["unresolved"] = False
            elif c["type"] == "insufficient_evidence":
                # تسجيل عدم اليقين
                resolved["insufficient_evidence_flag"] = True
                c["unresolved"] = True  # لا يمكن حله بدون بيانات إضافية

        resolved["contradictions"] = contradictions
        return resolved

    def _compute_synthesis_confidence(
        self,
        synthesis: dict,
        previous_stages: list[PipelineStageResult],
    ) -> float:
        """حساب ثقة التركيب — Compute synthesis confidence."""
        # متوسط ثقة المراحل السابقة
        if previous_stages:
            avg_prev_confidence = sum(
                s.confidence for s in previous_stages
            ) / len(previous_stages)
        else:
            avg_prev_confidence = 0.3

        # تعديلات بناءً على التركيب
        balance = synthesis.get("evidence_balance", 0.5)
        sufficiency = synthesis.get("information_sufficiency", 0.3)

        # الثقة المركبة
        confidence = avg_prev_confidence * 0.4 + balance * 0.3 + sufficiency * 0.3

        # تخفيض إذا كانت هناك تناقضات غير محلولة
        contradictions = synthesis.get("contradictions", [])
        unresolved = sum(1 for c in contradictions if c.get("unresolved", False))
        if unresolved > 0:
            confidence *= 0.85

        return max(0.0, min(1.0, confidence))


class DecisionMakerAgent(PipelineAgent):
    """
    وكيل اتخاذ القرار — المرحلة 5: اتخاذ القرار النهائي.
    
    يقوم بـ:
    - مراجعة التركيب النهائي
    - اتخاذ قرار مبنى على الأدلة
    - تقييم المخاطر المرتبطة بالقرار
    - تقديم توصيات للمراجعة البشرية إذا لزم
    """

    def __init__(self):
        super().__init__("DecisionMaker", "صانع القرار")

    async def process(
        self,
        topic: str,
        context: dict,
        previous_stages: list[PipelineStageResult],
    ) -> PipelineStageResult:
        """اتخاذ القرار النهائي."""
        start_time = time.time()

        # تجميع مخرجات التركيب
        synthesis: dict = {}
        for stage in previous_stages:
            if stage.stage == PipelineStage.SYNTHESIS:
                synthesis = stage.output
                break

        # اتخاذ القرار
        decision = self._make_decision(topic, synthesis, context)

        # تقييم المخاطر
        risk_assessment = self._assess_risks(decision, synthesis)

        # بناء الاستجابة النهائية
        response = self._build_response(decision, synthesis, risk_assessment)

        # حساب الثقة النهائية
        confidence = self._compute_final_confidence(
            decision, synthesis, previous_stages
        )

        duration_ms = (time.time() - start_time) * 1000

        return self._build_stage_result(
            stage=PipelineStage.DECISION,
            output={
                "decision": decision,
                "risk_assessment": risk_assessment,
                "response": response,
                "needs_human_review": risk_assessment.get("level") == "high",
            },
            confidence=confidence,
            duration_ms=duration_ms,
            metadata={"arabic_name": self.arabic_name},
        )

    def _make_decision(
        self, topic: str, synthesis: dict, context: dict
    ) -> dict:
        """اتخاذ القرار — Make the decision."""
        # تحديد نوع القرار
        evidence_balance = synthesis.get("evidence_balance", 0.5)
        sufficiency = synthesis.get("information_sufficiency", 0.3)
        top_hyp_id = synthesis.get("top_hypothesis_id", "")

        if evidence_balance > 0.6 and sufficiency > 0.5:
            decision_type = "confident"
            rationale = "أدلة كافية ومتوازنة تدعم الاستنتاج"
        elif evidence_balance > 0.4:
            decision_type = "tentative"
            rationale = "أدلة جزئية — القرار مبدئي ويحتاج تحقق"
        else:
            decision_type = "deferred"
            rationale = "أدلة غير كافية — يُنصح بتأجيل القرار وجمع معلومات أكثر"

        return {
            "type": decision_type,
            "rationale": rationale,
            "selected_hypothesis": top_hyp_id,
            "evidence_balance": evidence_balance,
            "information_sufficiency": sufficiency,
        }

    def _assess_risks(self, decision: dict, synthesis: dict) -> dict:
        """تقييم المخاطر — Assess risks of the decision."""
        decision_type = decision.get("type", "deferred")
        sufficiency = decision.get("information_sufficiency", 0.3)

        # مستوى المخاطر
        if decision_type == "confident" and sufficiency > 0.6:
            risk_level = "low"
            risk_description = "مخاطر منخفضة — قرار مدعوم بأدلة قوية"
        elif decision_type == "tentative":
            risk_level = "medium"
            risk_description = "مخاطر متوسطة — قرار مبني على أدلة جزئية"
        else:
            risk_level = "high"
            risk_description = "مخاطر عالية — أدلة غير كافية أو متعارضة"

        # فجوات معرفية تزيد المخاطر
        contradictions = synthesis.get("contradictions", [])
        if contradictions:
            high_severity = sum(
                1 for c in contradictions
                if c.get("severity") == "high"
            )
            if high_severity > 0:
                risk_level = "high"
                risk_description += " — توجد تناقضات خطيرة"

        return {
            "level": risk_level,
            "description": risk_description,
            "factors": {
                "decision_type": decision_type,
                "sufficiency": sufficiency,
                "contradiction_count": len(contradictions),
            },
        }

    def _build_response(
        self, decision: dict, synthesis: dict, risk_assessment: dict
    ) -> str:
        """بناء الاستجابة النهائية — Build final response text."""
        parts: list[str] = []

        # قرار
        if decision["type"] == "confident":
            parts.append(f"✅ {decision['rationale']}")
        elif decision["type"] == "tentative":
            parts.append(f"⚡ {decision['rationale']}")
        else:
            parts.append(f"⚠️ {decision['rationale']}")

        # نتائج مفتاحية
        key_findings = synthesis.get("key_findings", [])
        if key_findings:
            parts.append("النتائج الرئيسية:")
            for finding in key_findings[:3]:
                parts.append(f"  • {finding}")

        # المخاطر
        parts.append(f"مستوى المخاطر: {risk_assessment['description']}")

        return "\n".join(parts)

    def _compute_final_confidence(
        self,
        decision: dict,
        synthesis: dict,
        previous_stages: list[PipelineStageResult],
    ) -> float:
        """حساب الثقة النهائية — Compute final decision confidence."""
        # ثقة المراحل السابقة
        if previous_stages:
            stage_confidences = {s.stage: s.confidence for s in previous_stages}
        else:
            stage_confidences = {}

        # ثقة التخطيط والفرضيات (أساسيات)
        planning_conf = stage_confidences.get(PipelineStage.PLANNING, 0.4)
        hypothesis_conf = stage_confidences.get(PipelineStage.HYPOTHESIS, 0.4)

        # ثقة الاسترجاع والتركيب (تأييدية)
        retrieval_conf = stage_confidences.get(PipelineStage.RETRIEVAL, 0.4)
        synthesis_conf = stage_confidences.get(PipelineStage.SYNTHESIS, 0.4)

        # مركب مرجح
        confidence = (
            planning_conf * 0.15
            + hypothesis_conf * 0.25
            + retrieval_conf * 0.25
            + synthesis_conf * 0.35
        )

        # تعديل بناءً على نوع القرار
        decision_type = decision.get("type", "deferred")
        if decision_type == "confident":
            confidence = min(1.0, confidence * 1.1)
        elif decision_type == "deferred":
            confidence *= 0.7

        return max(0.0, min(1.0, confidence))


# ═══════════════════════════════════════════════════════════════════════════════
# وكلاء النظام — System Agents
# ═══════════════════════════════════════════════════════════════════════════════


class System1Agent:
    """
    وكيل النظام الأول — استجابة سريعة عبر غرفة المداولة الموجودة.
    
    يستخدم DeliberationRoom الموجودة لإجراء مداولة سريعة بين الأدمغة.
    هذا هو المسار السريع: مطابقة الأنماط، الإجابات المباشرة،
    الحالات ذات اليقين العالي.
    
    التكامل: يعيد استخدام DeliberationRoom.calculate_cjs() و
    DeliberationRoom.calculate_enhanced_cjs() بالكامل.
    """

    def __init__(self, deliberation_room: Any | None = None):
        """
        تهيئة وكيل النظام الأول.
        
        المعاملات:
            deliberation_room: غرفة المداولة الموجودة (اختياري)
        """
        self._deliberation_room = deliberation_room

    async def respond(
        self,
        topic: str,
        brain_responses: list[dict],
        context: dict | None = None,
    ) -> System1Result:
        """
        استجابة سريعة — Fast response via deliberation.
        
        المعاملات:
            topic: الموضوع
            brain_responses: استجابات الأدمغة
            context: سياق إضافي
        
        النتيجة:
            System1Result مع استجابة سريعة
        """
        start_time = time.time()
        context = context or {}

        # إجراء مداولة عبر الغرفة الموجودة
        if self._deliberation_room and brain_responses:
            deliberation = await self._deliberation_room.deliberate(
                topic=topic,
                brains_responses=brain_responses,
            )

            # محاولة استخدام CJS المحسّن إذا توفرت فجوات معرفية
            knowledge_gaps = context.get("knowledge_gaps", [])
            if knowledge_gaps and hasattr(
                self._deliberation_room, "calculate_enhanced_cjs"
            ):
                enhanced_cjs = self._deliberation_room.calculate_enhanced_cjs(
                    brain_responses, knowledge_gaps
                )
            else:
                enhanced_cjs = deliberation.critical_junction_score

            # بناء الاستجابة من التوصيات
            response_parts: list[str] = []
            if deliberation.recommendations:
                response_parts.extend(deliberation.recommendations[:3])

            # تحديد الثقة
            confidence = deliberation.consensus_level
            cjs = enhanced_cjs

            result = System1Result(
                response="\n".join(response_parts) if response_parts else "إجماع سريع",
                confidence=confidence,
                consensus_level=deliberation.consensus_level,
                brain_count=deliberation.brain_count,
                deliberation_cjs=cjs,
                duration_ms=(time.time() - start_time) * 1000,
                metadata={
                    "deliberation_needs_intervention": deliberation.needs_human_intervention,
                    "agreement_ratio": deliberation.agreement_ratio,
                    "dissent_ratio": deliberation.dissent_ratio,
                },
            )
        else:
            # بدون غرفة مداولة — استجابة أساسية
            avg_confidence = (
                sum(r.get("confidence", 0.5) for r in brain_responses)
                / max(1, len(brain_responses))
                if brain_responses
                else 0.3
            )

            result = System1Result(
                response="استجابة سريعة بدون مداولة",
                confidence=avg_confidence,
                consensus_level=avg_confidence,
                brain_count=len(brain_responses),
                duration_ms=(time.time() - start_time) * 1000,
            )

        return result


class System2Pipeline:
    """
    خط أنابيب النظام الثاني — استدلال عميق متعدد المراحل مع تحسين تكراري.
    
    المراحل الخمسة:
    1. المخطط (Planner): تحليل المشكلة وتفكيكها
    2. مولد الفرضيات (HypothesisGenerator): توليد فرضيات متعددة
    3. المسترجع (Retriever): جلب المعرفة ذات الصلة
    4. المركّب (Synthesizer): دمج النتائج وحل التناقضات
    5. صانع القرار (DecisionMaker): اتخاذ القرار النهائي
    
    التحسين التكراري:
    - إذا كانت ثقة النتيجة أقل من العتبة، يعاد تشغيل المراحل
      مع المعلومات المكتسبة من التكرار السابق
    - الحد الأقصى للمرات: MAX_REFINEMENT_ITERATIONS
    
    التكامل:
    - يستخدم CausalReasoner في مولد الفرضيات
    - يأخذ الفجوات المعرفية من WorldModelV2 عبر السياق
    - يُغذي نتائجه مرة أخرى في UncertaintyMetrics
    """

    # عتبة ثقة التحسين التكراري — إذا الثقة أقل، نُكرر
    REFINEMENT_CONFIDENCE_THRESHOLD = 0.5

    def __init__(
        self,
        causal_reasoner: CausalReasoner | None = None,
        max_iterations: int = MAX_REFINEMENT_ITERATIONS,
    ):
        """
        تهيئة خط أنابيب النظام الثاني.
        
        المعاملات:
            causal_reasoner: محرك الاستدلال السببي (اختياري)
            max_iterations: الحد الأقصى لمرات التحسين التكراري
        """
        self._agents: dict[PipelineStage, PipelineAgent] = {
            PipelineStage.PLANNING: PlannerAgent(),
            PipelineStage.HYPOTHESIS: HypothesisGeneratorAgent(causal_reasoner),
            PipelineStage.RETRIEVAL: RetrieverAgent(),
            PipelineStage.SYNTHESIS: SynthesizerAgent(),
            PipelineStage.DECISION: DecisionMakerAgent(),
        }
        self._max_iterations = max_iterations

    async def execute(
        self,
        topic: str,
        context: dict | None = None,
    ) -> System2Result:
        """
        تنفيذ خط أنابيب النظام الثاني — Execute System 2 pipeline.
        
        المعاملات:
            topic: الموضوع أو السؤال
            context: السياق المتاح
        
        النتيجة:
            System2Result مع نتائج جميع المراحل
        """
        start_time = time.time()
        context = context or {}

        all_stage_results: list[PipelineStageResult] = []
        final_confidence = 0.0
        iterations = 0

        for iteration in range(self._max_iterations):
            iterations = iteration + 1
            iteration_results: list[PipelineStageResult] = []

            # إضافة سياق من التكرارات السابقة
            enriched_context = dict(context)
            if iteration > 0:
                enriched_context["_previous_iterations"] = iteration
                enriched_context["_previous_confidence"] = final_confidence

            # تنفيذ المراحل الخمسة بالترتيب
            stage_order = [
                PipelineStage.PLANNING,
                PipelineStage.HYPOTHESIS,
                PipelineStage.RETRIEVAL,
                PipelineStage.SYNTHESIS,
                PipelineStage.DECISION,
            ]

            for stage in stage_order:
                agent = self._agents[stage]
                try:
                    result = await agent.process(
                        topic=topic,
                        context=enriched_context,
                        previous_stages=iteration_results,
                    )
                    result.iteration = iteration
                    iteration_results.append(result)
                except Exception as e:
                    logger.error(
                        f"فشل في مرحلة {stage.value} (تكرار {iteration}): {e}"
                    )
                    # إنشاء نتيجة بديلة
                    result = PipelineStageResult(
                        stage=stage,
                        output={"error": str(e)},
                        confidence=0.1,
                        duration_ms=0.0,
                        iteration=iteration,
                        metadata={"error": True},
                    )
                    iteration_results.append(result)

            all_stage_results.extend(iteration_results)

            # استخراج الثقة النهائية من مرحلة القرار
            decision_result = next(
                (r for r in iteration_results if r.stage == PipelineStage.DECISION),
                None,
            )
            final_confidence = (
                decision_result.confidence if decision_result else 0.1
            )

            # التحقق من الحاجة إلى تحسين تكراري
            if final_confidence >= self.REFINEMENT_CONFIDENCE_THRESHOLD:
                break  # ثقة كافية — لا حاجة لمزيد من التحسين

            logger.info(
                f"تحسين تكراري {iteration + 1}: ثقة = {final_confidence:.4f} "
                f"← أقل من {self.REFINEMENT_CONFIDENCE_THRESHOLD} — متابعة التحسين"
            )

        # بناء الاستجابة النهائية من مرحلة القرار الأخيرة
        last_decision = next(
            (
                r for r in reversed(all_stage_results)
                if r.stage == PipelineStage.DECISION
            ),
            None,
        )

        response = ""
        if last_decision and last_decision.output.get("response"):
            response = last_decision.output["response"]

        duration_ms = (time.time() - start_time) * 1000

        return System2Result(
            response=response,
            confidence=final_confidence,
            stages=all_stage_results,
            refinement_iterations=iterations,
            duration_ms=duration_ms,
            metadata={
                "max_iterations": self._max_iterations,
                "refinement_threshold": self.REFINEMENT_CONFIDENCE_THRESHOLD,
            },
        )


# ═══════════════════════════════════════════════════════════════════════════════
# موجّه النظام المزدوج — DualSystemRouter
# ═══════════════════════════════════════════════════════════════════════════════


class DualSystemRouter:
    """
    موجّه النظام المزدوج — يوجه المهام إلى النظام 1 أو النظام 2.
    
    هذا هو المكون الرئيسي لوحدة الاستدلال من النظام الثاني.
    ينفذ معمارية PRIME:
    
    1. يحسب عدم اليقين عبر UncertaintyGate
    2. يوجّه المهمة إلى النظام المناسب
    3. ينفذ الاستدلال عبر System1Agent أو System2Pipeline
    4. يسجل النتائج في UncertaintyMetrics
    5. يُرجع ReasoningOutcome شامل
    
    التكامل:
    - DeliberationRoom: يُستخدم في النظام 1 للمداولة السريعة
    - WorldModelV2: يوفر الفجوات المعرفية عبر السياق
    - CausalReasoner: يُستخدم في النظام 2 لتحسين الفرضيات
    - MetaAnalyzer: يمكن استخدامه لتحسين العتبة
    
    الأمان التراكمي:
    - إذا MAMOUN_SYSTEM2_ENABLED = "false" (الافتراضي)، كل شيء ← النظام 1
    - لا يُغيّر أي سلوك موجود عند التعطيل
    - التراجع الآمن عند فشل النظام 2
    """

    def __init__(
        self,
        deliberation_room: Any | None = None,
        causal_reasoner: CausalReasoner | None = None,
        *,
        uncertainty_threshold: float = DEFAULT_UNCERTAINTY_THRESHOLD,
        max_refinement_iterations: int = MAX_REFINEMENT_ITERATIONS,
        calibration_enabled: bool = True,
    ):
        """
        تهيئة موجّه النظام المزدوج.
        
        المعاملات:
            deliberation_room: غرفة المداولة الموجودة
            causal_reasoner: محرك الاستدلال السببي
            uncertainty_threshold: عتبة عدم اليقين
            max_refinement_iterations: الحد الأقصى للتحسين التكراري
            calibration_enabled: تفعيل معايرة العتبة التلقائية
        """
        # المكونات الأساسية
        self._uncertainty_gate = UncertaintyGate(
            threshold=uncertainty_threshold,
        )
        self._uncertainty_metrics = UncertaintyMetrics(
            initial_threshold=uncertainty_threshold,
            calibration_enabled=calibration_enabled,
        )
        self._system1 = System1Agent(deliberation_room=deliberation_room)
        self._system2 = System2Pipeline(
            causal_reasoner=causal_reasoner,
            max_iterations=max_refinement_iterations,
        )

        # مراجع خارجية
        self._deliberation_room = deliberation_room
        self._causal_reasoner = causal_reasoner

        # إحصائيات
        self._total_requests: int = 0
        self._fallback_count: int = 0

    @property
    def uncertainty_metrics(self) -> UncertaintyMetrics:
        """الوصول لمقاييس عدم اليقين."""
        return self._uncertainty_metrics

    @property
    def uncertainty_gate(self) -> UncertaintyGate:
        """الوصول لبوابة عدم اليقين."""
        return self._uncertainty_gate

    async def reason(
        self,
        topic: str,
        brain_responses: list[dict] | None = None,
        context: dict | None = None,
    ) -> ReasoningOutcome:
        """
        الاستدلال الرئيسي — Main reasoning entry point.
        
        يحسب عدم اليقين ويوجّه المهمة إلى النظام المناسب.
        
        المعاملات:
            topic: الموضوع أو السؤال المطروح
            brain_responses: استجابات الأدمغة من DeliberationRoom
            context: سياق إضافي (يحتوي goal, state, knowledge_gaps, إلخ)
        
        النتيجة:
            ReasoningOutcome مع نتيجة الاستدلال الكاملة
        """
        start_time = time.time()
        self._total_requests += 1
        brain_responses = brain_responses or []
        context = context or {}

        # ─── فحص التبديل البيئي ──────────────────────────────────────────
        # إذا النظام الثاني معطّل، كل شيء ← النظام 1 (سلوك موجود)
        if not SYSTEM2_ENABLED:
            outcome = await self._route_to_system1(
                topic, brain_responses, context
            )
            return outcome

        # ─── حساب عدم اليقين ────────────────────────────────────────────
        uncertainty = self._uncertainty_gate.compute_uncertainty(
            topic=topic,
            brain_responses=brain_responses,
            context=context,
            knowledge_gaps=context.get("knowledge_gaps", []),
        )

        # ─── التوجيه ─────────────────────────────────────────────────────
        system_choice = self._uncertainty_gate.route(uncertainty)

        # تحديث العتبة من المقاييس المعايرة
        self._uncertainty_gate.threshold = self._uncertainty_metrics.threshold

        decision = RoutingDecision(
            system=system_choice,
            uncertainty=uncertainty,
            threshold=self._uncertainty_gate.threshold,
            topic=topic,
            timestamp=time.time(),
            duration_ms=(time.time() - start_time) * 1000,
            metadata={
                "system2_enabled": SYSTEM2_ENABLED,
                "brain_count": len(brain_responses),
                "context_keys": list(context.keys())[:10],
            },
        )

        # ─── التنفيذ ─────────────────────────────────────────────────────
        outcome = ReasoningOutcome(decision=decision)

        if system_choice == SystemChoice.SYSTEM_1:
            # النظام الأول: سريع
            try:
                s1_result = await self._system1.respond(
                    topic=topic,
                    brain_responses=brain_responses,
                    context=context,
                )
                outcome.system1_result = s1_result
                outcome_confidence = s1_result.confidence
            except Exception as e:
                logger.error(f"فشل النظام الأول: {e}")
                outcome.system1_result = System1Result(
                    response="فشل في الاستجابة السريعة",
                    confidence=0.1,
                )
                outcome_confidence = 0.1
        else:
            # النظام الثاني: عميق مع تراجع آمن
            try:
                s2_result = await self._system2.execute(
                    topic=topic,
                    context=context,
                )
                outcome.system2_result = s2_result
                outcome_confidence = s2_result.confidence
            except Exception as e:
                logger.error(
                    f"فشل النظام الثاني — تراجع إلى النظام الأول: {e}"
                )
                self._fallback_count += 1
                # تراجع آمن إلى النظام 1
                try:
                    s1_result = await self._system1.respond(
                        topic=topic,
                        brain_responses=brain_responses,
                        context=context,
                    )
                    outcome.system1_result = s1_result
                    outcome.system2_result = System2Result(
                        response="تراجع إلى النظام الأول بسبب خطأ",
                        confidence=s1_result.confidence * 0.8,
                        metadata={"fallback_reason": str(e)},
                    )
                    outcome_confidence = s1_result.confidence * 0.8
                    decision.metadata["fallback"] = True
                    decision.metadata["fallback_reason"] = str(e)
                except Exception as e2:
                    logger.critical(f"فشل التراجع أيضاً: {e2}")
                    outcome_confidence = 0.0

        # ─── تسجيل المقاييس ────────────────────────────────────────────
        self._uncertainty_metrics.record(
            uncertainty=uncertainty,
            system_choice=system_choice,
            outcome_confidence=outcome_confidence,
            topic=topic,
        )

        outcome.duration_ms = (time.time() - start_time) * 1000
        return outcome

    async def _route_to_system1(
        self,
        topic: str,
        brain_responses: list[dict],
        context: dict,
    ) -> ReasoningOutcome:
        """
        توجيه مباشر إلى النظام الأول — Direct System 1 routing.
        
        يُستخدم عندما يكون النظام الثاني معطّلاً.
        لا يُغيّر أي سلوك موجود — يعمل كما كان.
        """
        start_time = time.time()

        # حساب عدم اليقين للتسجيل فقط (لا يُستخدم للتوجيه)
        uncertainty = self._uncertainty_gate.compute_uncertainty(
            topic=topic,
            brain_responses=brain_responses,
            context=context,
            knowledge_gaps=context.get("knowledge_gaps", []),
        )

        decision = RoutingDecision(
            system=SystemChoice.SYSTEM_1,
            uncertainty=uncertainty,
            threshold=self._uncertainty_gate.threshold,
            topic=topic,
            timestamp=time.time(),
            duration_ms=(time.time() - start_time) * 1000,
            metadata={
                "system2_enabled": False,
                "forced_system1": True,
            },
        )

        outcome = ReasoningOutcome(decision=decision)

        # تنفيذ عبر النظام الأول
        try:
            s1_result = await self._system1.respond(
                topic=topic,
                brain_responses=brain_responses,
                context=context,
            )
            outcome.system1_result = s1_result
        except Exception as e:
            logger.error(f"فشل النظام الأول: {e}")
            outcome.system1_result = System1Result(
                response="فشل في الاستجابة",
                confidence=0.1,
            )

        outcome.duration_ms = (time.time() - start_time) * 1000
        return outcome

    def get_status(self) -> dict:
        """
        الحصول على حالة الموجّه — Get router status and statistics.
        """
        return {
            "system2_enabled": SYSTEM2_ENABLED,
            "total_requests": self._total_requests,
            "fallback_count": self._fallback_count,
            "fallback_rate": round(
                self._fallback_count / max(1, self._total_requests), 4
            ),
            "uncertainty_threshold": round(self._uncertainty_gate.threshold, 4),
            "uncertainty_metrics": self._uncertainty_metrics.get_statistics(),
            "uncertainty_drift": self._uncertainty_metrics.detect_uncertainty_drift(),
            "pipeline_agents": {
                stage.value: {
                    "name": agent.name,
                    "arabic_name": agent.arabic_name,
                }
                for stage, agent in self._system2._agents.items()
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# مصنع الموجّه — Router Factory
# ═══════════════════════════════════════════════════════════════════════════════


def create_system2_router(
    deliberation_room: Any | None = None,
    world_model_v2: Any | None = None,
    causal_reasoner: CausalReasoner | None = None,
    *,
    threshold: float | None = None,
    max_iterations: int | None = None,
) -> DualSystemRouter:
    """
    إنشاء موجّه النظام المزدوج — Factory function for DualSystemRouter.
    
    يُنشئ موجّهًا مُكوّنًا بالكامل مع التكاملات المناسبة.
    
    المعاملات:
        deliberation_room: غرفة المداولة الموجودة
        world_model_v2: نموذج العالم المتقدم (للفجوات المعرفية)
        causal_reasoner: محرك الاستدلال السببي
        threshold: عتبة عدم اليقين (الافتراضي من البيئة)
        max_iterations: الحد الأقصى للتحسين التكراري
    
    النتيجة:
        DualSystemRouter جاهز للاستخدام
    
    مثال:
        router = create_system2_router(
            deliberation_room=room,
            world_model_v2=wm_v2,
        )
        outcome = await router.reason(
            topic="كيف نحسّن الأداء؟",
            brain_responses=responses,
            context={"goal": "تحسين", "knowledge_gaps": gaps},
        )
    """
    _threshold = threshold if threshold is not None else DEFAULT_UNCERTAINTY_THRESHOLD
    _max_iter = max_iterations if max_iterations is not None else MAX_REFINEMENT_ITERATIONS

    return DualSystemRouter(
        deliberation_room=deliberation_room,
        causal_reasoner=causal_reasoner,
        uncertainty_threshold=_threshold,
        max_refinement_iterations=_max_iter,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# نقطة الدخول للاختبار السريع — Quick test entry point
# ═══════════════════════════════════════════════════════════════════════════════


async def _demo() -> None:
    """
    عرض توضيحي سريع — Quick demo of System 2 Reasoner.
    يُشغّل بـ: python -m mamoun.core.system2_reasoner
    """
    import asyncio

    print("=" * 70)
    print("BABSHARQII v6.0 — System 2 Reasoner Demo")
    print("عرض توضيحي لوحدة الاستدلال من النظام الثاني")
    print("=" * 70)
    print(f"\nMAMOUN_SYSTEM2_ENABLED = {SYSTEM2_ENABLED}")
    print(f"DEFAULT_UNCERTAINTY_THRESHOLD = {DEFAULT_UNCERTAINTY_THRESHOLD}")

    # إنشاء الموجّه
    router = create_system2_router()

    # اختبار 1: سؤال بسيط (من المتوقع ← النظام 1)
    print("\n" + "─" * 50)
    print("اختبار 1: سؤال بسيط")
    outcome1 = await router.reason(
        topic="ما هو لون السماء؟",
        brain_responses=[
            {"brain_id": "neural", "response": "أزرق", "confidence": 0.95},
            {"brain_id": "bayesian", "response": "أزرق", "confidence": 0.90},
        ],
        context={"goal": "إجابة مباشرة", "domain": "general"},
    )
    print(f"  النظام: {outcome1.decision.system.value}")
    print(f"  عدم اليقين: {outcome1.decision.uncertainty.composite:.4f}")
    print(f"  الثقة: {outcome1.confidence:.4f}")

    # اختبار 2: سؤال معقد (من المتوقع ← النظام 2)
    print("\n" + "─" * 50)
    print("اختبار 2: سؤال معقد")
    outcome2 = await router.reason(
        topic="لماذا يختلف أداء النظام في أوقات مختلفة، وكيف يمكن تحسينه؟",
        brain_responses=[
            {"brain_id": "neural", "response": "يعتمد على الحمل", "confidence": 0.5},
            {"brain_id": "bayesian", "response": "عوامل متعددة", "confidence": 0.3},
            {"brain_id": "causal", "response": "أسباب سببية محتملة", "confidence": 0.6},
        ],
        context={
            "goal": "تحليل شامل",
            "errors": [{"root_cause": "timeout", "summary": "تأخر الاستجابة"}],
            "knowledge_gaps": [
                {"type": "high_uncertainty", "severity": "high"},
            ],
        },
    )
    print(f"  النظام: {outcome2.decision.system.value}")
    print(f"  عدم اليقين: {outcome2.decision.uncertainty.composite:.4f}")
    print(f"  الثقة: {outcome2.confidence:.4f}")

    # إحصائيات
    print("\n" + "─" * 50)
    print("إحصائيات الموجّه:")
    status = router.get_status()
    metrics = status["uncertainty_metrics"]
    print(f"  إجمالي الطلبات: {status['total_requests']}")
    print(f"  نظام 1: {metrics['system1_count']} ({metrics['system1_ratio']:.1%})")
    print(f"  نظام 2: {metrics['system2_count']} ({metrics['system2_ratio']:.1%})")
    print(f"  معدل التراجع: {status['fallback_rate']:.1%}")
    print(f"  اتجاه عدم اليقين: {status['uncertainty_drift']['direction']}")

    print("\n" + "=" * 70)
    print("انتهى العرض التوضيحي — Demo complete")


if __name__ == "__main__":
    import asyncio as _asyncio
    _asyncio.run(_demo())
