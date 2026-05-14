"""
CognitiveFeedbackLoop v43 — حلقة التغذية الراجعة المعرفية
تصل جودة المخرجات بمعالجة المدخلات — كل استجابة تُحسّن التالية

الآلية:
  1. تتبع جودة الاستجابات (response_quality_scores)
  2. تتبع دقة كل دماغ حسب المجال (brain_accuracy_per_domain)
  3. تتبع اتجاه رضا المستخدم (user_satisfaction_trend)
  4. تعديل أوزان الأدمغة بناءً على الدقة (brain_weights)
  5. تعديل تفضيلات التوجيه (routing_preferences)
  6. تعديل عتبات الثقة (confidence_thresholds)
  7. استخدام المتوسط المتحرك الأسي (EMA) للتحديثات

التكامل:
  - MetaCognitionEngine: بيانات موثوقية المكونات
  - BrainRouter: أوزان وتفضيلات التوجيه

v43 — Super Mind العقل الخارق مامون
"""

import time
import math
import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج البيانات — Data Models
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FeedbackRecord:
    """سجل تغذية راجعة واحدة"""
    query: str
    response: str
    user_feedback: float  # -1.0 (سيء جداً) إلى +1.0 (ممتاز)
    brain_used: str = ""
    domain: str = "general"
    timestamp: float = 0.0
    response_quality: float = 0.0  # تُحسب تلقائياً

    def to_dict(self) -> dict:
        return {
            "query": self.query[:100],
            "response": self.response[:100],
            "user_feedback": round(self.user_feedback, 3),
            "brain_used": self.brain_used,
            "domain": self.domain,
            "timestamp": self.timestamp,
            "response_quality": round(self.response_quality, 3),
        }


@dataclass
class BrainWeights:
    """أوزان الأدمغة — تُعدَّل بناءً على الدقة"""
    neural: float = 0.25
    causal: float = 0.20
    symbolic: float = 0.20
    bayesian: float = 0.15
    world_model: float = 0.20

    def to_dict(self) -> dict:
        return {
            "neural": round(self.neural, 4),
            "causal": round(self.causal, 4),
            "symbolic": round(self.symbolic, 4),
            "bayesian": round(self.bayesian, 4),
            "world_model": round(self.world_model, 4),
        }

    def normalize(self):
        """تطبيع الأوزان لكي يكون المجموع = 1.0"""
        total = self.neural + self.causal + self.symbolic + self.bayesian + self.world_model
        if total > 0:
            self.neural /= total
            self.causal /= total
            self.symbolic /= total
            self.bayesian /= total
            self.world_model /= total


@dataclass
class RoutingPreferences:
    """تفضيلات التوجيه — أي دماغ يُفضَّل لأي مجال"""
    preferences: dict = field(default_factory=dict)  # domain → brain_name

    def to_dict(self) -> dict:
        return dict(self.preferences)


@dataclass
class ConfidenceThresholds:
    """عتبات الثقة — متى نقبل الاستجابة ومتى نطلب مراجعة"""
    auto_accept: float = 0.8      # فوق هذه الثقة → قبول تلقائي
    review_required: float = 0.5  # بين هذه و auto_accept → مراجعة
    reject_below: float = 0.3     # تحت هذه → رفض وإعادة محاولة

    def to_dict(self) -> dict:
        return {
            "auto_accept": round(self.auto_accept, 3),
            "review_required": round(self.review_required, 3),
            "reject_below": round(self.reject_below, 3),
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  حلقة التغذية الراجعة المعرفية — CognitiveFeedbackLoop
# ═══════════════════════════════════════════════════════════════════════════════

class CognitiveFeedbackLoop:
    """
    حلقة التغذية الراجعة المعرفية — تصل المخرجات بالمدخلات

    المسؤوليات:
    1. معالجة تغذية المستخدم الراجعة وتعديل المعلمات
    2. تتبع جودة الاستجابات عبر الزمن
    3. تعديل أوزان الأدمغة بناءً على الدقة لكل مجال
    4. تعديل تفضيلات التوجيه
    5. تعديل عتبات الثقة
    6. استخدام المتوسط المتحرك الأسي (EMA) لتحديثات سلسة

    Formula (EMA):
    new_value = alpha * new_observation + (1 - alpha) * old_value
    alpha = 0.1 (بطيء — لا يتغير كثيراً من ملاحظة واحدة)
    """

    EMA_ALPHA = 0.1       # معامل المتوسط المتحرك الأسي
    MAX_HISTORY = 200     # أقصى عدد لسجلات التغذية الراجعة
    BRAIN_NAMES = ["neural", "causal", "symbolic", "bayesian", "world_model"]

    def __init__(self, meta_cognition=None, brain_router=None):
        self._meta_cognition = meta_cognition
        self._brain_router = brain_router

        # ── حالة التتبع ──
        self._response_quality_scores: list[float] = []
        self._brain_accuracy_per_domain: dict[str, dict[str, float]] = defaultdict(
            lambda: {brain: 0.5 for brain in self.BRAIN_NAMES}
        )
        self._user_satisfaction_trend: list[float] = []

        # ── المعلمات القابلة للتعديل ──
        self._brain_weights = BrainWeights()
        self._routing_preferences = RoutingPreferences()
        self._confidence_thresholds = ConfidenceThresholds()

        # ── سجلات التغذية الراجعة ──
        self._feedback_history: list[FeedbackRecord] = []

        # ── إحصائيات ──
        self._total_feedback_processed: int = 0
        self._last_adjustment_time: float = 0.0

    def set_meta_cognition(self, mc):
        """تعيين محرك ما فوق الإدراك"""
        self._meta_cognition = mc

    def set_brain_router(self, br):
        """تعيين موجه الأدمغة"""
        self._brain_router = br

    # ── معالجة التغذية الراجعة ───────────────────────────────────────────
    def process_feedback(
        self,
        query: str,
        response: str,
        user_feedback: float,
        brain_used: str = "",
        domain: str = "general",
    ) -> dict:
        """
        معالجة تغذية راجعة وتعديل المعلمات

        Args:
            query: الاستعلام الأصلي
            response: الاستجابة المُقدَّمة
            user_feedback: تقييم المستخدم من -1.0 (سيء) إلى +1.0 (ممتاز)
            brain_used: الدماغ المستخدم (اختياري)
            domain: مجال الاستعلام (اختياري)

        Returns:
            dict — التعديلات التي تمت
        """
        now = time.time()
        self._total_feedback_processed += 1

        # تحويل التقييم إلى مقياس جودة (0.0 إلى 1.0)
        response_quality = max(0.0, min(1.0, (user_feedback + 1.0) / 2.0))

        # إنشاء السجل
        record = FeedbackRecord(
            query=query,
            response=response,
            user_feedback=user_feedback,
            brain_used=brain_used,
            domain=domain,
            timestamp=now,
            response_quality=response_quality,
        )
        self._feedback_history.append(record)
        if len(self._feedback_history) > self.MAX_HISTORY:
            self._feedback_history = self._feedback_history[-self.MAX_HISTORY:]

        # ── تحديث جودة الاستجابات (EMA) ──
        if self._response_quality_scores:
            old_avg = self._response_quality_scores[-1]
            new_avg = self._ema_update(old_avg, response_quality)
        else:
            new_avg = response_quality
        self._response_quality_scores.append(new_avg)
        if len(self._response_quality_scores) > self.MAX_HISTORY:
            self._response_quality_scores = self._response_quality_scores[-self.MAX_HISTORY:]

        # ── تحديث اتجاه رضا المستخدم (EMA) ──
        satisfaction = max(0.0, min(1.0, (user_feedback + 1.0) / 2.0))
        if self._user_satisfaction_trend:
            old_sat = self._user_satisfaction_trend[-1]
            new_sat = self._ema_update(old_sat, satisfaction)
        else:
            new_sat = satisfaction
        self._user_satisfaction_trend.append(new_sat)
        if len(self._user_satisfaction_trend) > self.MAX_HISTORY:
            self._user_satisfaction_trend = self._user_satisfaction_trend[-self.MAX_HISTORY:]

        # ── تحديث دقة الدماغ حسب المجال ──
        adjustments = {}
        if brain_used and brain_used in self.BRAIN_NAMES:
            old_accuracy = self._brain_accuracy_per_domain[domain][brain_used]
            new_accuracy = self._ema_update(old_accuracy, response_quality)
            self._brain_accuracy_per_domain[domain][brain_used] = new_accuracy

            # ── تعديل أوزان الأدمغة ──
            weight_adjustment = self._adjust_brain_weights(brain_used, response_quality)
            adjustments["brain_weights"] = weight_adjustment

            # ── تعديل تفضيلات التوجيه ──
            routing_adjustment = self._adjust_routing_preferences(domain, brain_used, response_quality)
            adjustments["routing"] = routing_adjustment

        # ── تعديل عتبات الثقة ──
        threshold_adjustment = self._adjust_confidence_thresholds(user_feedback)
        adjustments["thresholds"] = threshold_adjustment

        # ── تسجيل في MetaCognition ──
        if self._meta_cognition:
            try:
                from mamoun.core.super_brain.meta_cognition_engine import OutcomeRecord
                self._meta_cognition.record_outcome(OutcomeRecord(
                    component="cognitive_feedback_loop",
                    operation="process_feedback",
                    success=user_feedback > -0.3,
                    quality_score=response_quality,
                    predicted_quality=0.5,  # تنبؤ محايد
                    latency_ms=0,
                ))
            except (ImportError, Exception) as e:
                logger.debug(f"MetaCognition record failed: {e}")

        self._last_adjustment_time = now

        logger.info(
            f"Feedback processed: quality={response_quality:.2f}, "
            f"satisfaction_trend={new_sat:.2f}, brain={brain_used}, domain={domain}"
        )

        return {
            "status": "processed",
            "response_quality": round(response_quality, 3),
            "satisfaction_trend": round(new_sat, 3),
            "adjustments": adjustments,
            "total_processed": self._total_feedback_processed,
        }

    # ── الحصول على التعديلات الحالية ─────────────────────────────────────
    def get_adjustments(self) -> dict:
        """
        الحصول على المعلمات المعدَّلة الحالية

        Returns:
            dict — الأوزان والتفضيلات والعتبات الحالية
        """
        return {
            "brain_weights": self._brain_weights.to_dict(),
            "routing_preferences": self._routing_preferences.to_dict(),
            "confidence_thresholds": self._confidence_thresholds.to_dict(),
            "last_adjustment": self._last_adjustment_time,
        }

    # ── إحصائيات التغذية الراجعة ─────────────────────────────────────────
    def get_feedback_stats(self) -> dict:
        """
        إحصائيات التغذية الراجعة

        Returns:
            dict — إحصائيات شاملة
        """
        avg_quality = (
            sum(self._response_quality_scores) / len(self._response_quality_scores)
            if self._response_quality_scores
            else 0.0
        )
        avg_satisfaction = (
            sum(self._user_satisfaction_trend) / len(self._user_satisfaction_trend)
            if self._user_satisfaction_trend
            else 0.0
        )

        # اتجاه الرضا (آخر 10 مقارنة بالـ 10 قبلهم)
        satisfaction_direction = "stable"
        if len(self._user_satisfaction_trend) >= 10:
            recent = self._user_satisfaction_trend[-10:]
            older = self._user_satisfaction_trend[-20:-10] if len(self._user_satisfaction_trend) >= 20 else self._user_satisfaction_trend[:10]
            if older:
                recent_avg = sum(recent) / len(recent)
                older_avg = sum(older) / len(older)
                if recent_avg > older_avg + 0.05:
                    satisfaction_direction = "improving"
                elif recent_avg < older_avg - 0.05:
                    satisfaction_direction = "declining"

        # أفضل دماغ لكل مجال
        best_brain_per_domain = {}
        for domain, accuracies in self._brain_accuracy_per_domain.items():
            if accuracies:
                best_brain = max(accuracies, key=accuracies.get)
                best_brain_per_domain[domain] = {
                    "brain": best_brain,
                    "accuracy": round(accuracies[best_brain], 3),
                }

        return {
            "total_feedback_processed": self._total_feedback_processed,
            "avg_response_quality": round(avg_quality, 3),
            "avg_satisfaction": round(avg_satisfaction, 3),
            "satisfaction_direction": satisfaction_direction,
            "quality_history_size": len(self._response_quality_scores),
            "feedback_history_size": len(self._feedback_history),
            "best_brain_per_domain": best_brain_per_domain,
            "last_adjustment": self._last_adjustment_time,
        }

    # ── المتوسط المتحرك الأسي (EMA) ─────────────────────────────────────
    def _ema_update(self, old_value: float, new_observation: float) -> float:
        """
        تحديث المتوسط المتحرك الأسي

        Formula: new = alpha * observation + (1 - alpha) * old
        alpha = 0.1 → تحديث بطيء وسلس
        """
        return self.EMA_ALPHA * new_observation + (1 - self.EMA_ALPHA) * old_value

    # ── تعديل أوزان الأدمغة ──────────────────────────────────────────────
    def _adjust_brain_weights(self, brain_used: str, quality: float) -> dict:
        """
        تعديل أوزان الأدمغة بناءً على جودة الاستجابة

        لو الدماغ أتى بجودة عالية → وزنه يزيد
        لو الجودة منخفضة → وزنه ينقص
        """
        if brain_used not in self.BRAIN_NAMES:
            return {"changed": False}

        weights = self._brain_weights
        delta = (quality - 0.5) * 0.02  # تغيير صغير

        current = getattr(weights, brain_used, 0.2)
        new_weight = max(0.05, min(0.5, current + delta))  # حد أدنى وأقصى
        setattr(weights, brain_used, new_weight)

        # تطبيع
        weights.normalize()

        return {
            "changed": True,
            "brain": brain_used,
            "delta": round(delta, 4),
            "new_weights": weights.to_dict(),
        }

    # ── تعديل تفضيلات التوجيه ────────────────────────────────────────────
    def _adjust_routing_preferences(self, domain: str, brain_used: str, quality: float) -> dict:
        """
        تعديل تفضيلات التوجيه بناءً على أداء الدماغ في المجال

        لو الدماغ جيد في مجال معين → يُفضَّل لهذا المجال
        """
        if quality > 0.7:
            # أداء جيد — سجّل التفضيل
            self._routing_preferences.preferences[domain] = brain_used
            return {
                "changed": True,
                "domain": domain,
                "preferred_brain": brain_used,
                "reason": "high_quality",
            }
        elif quality < 0.3:
            # أداء ضعيف — أزل التفضيل إن كان مسجلاً
            if self._routing_preferences.preferences.get(domain) == brain_used:
                del self._routing_preferences.preferences[domain]
            return {
                "changed": True,
                "domain": domain,
                "removed_brain": brain_used,
                "reason": "low_quality",
            }

        return {"changed": False}

    # ── تعديل عتبات الثقة ────────────────────────────────────────────────
    def _adjust_confidence_thresholds(self, user_feedback: float) -> dict:
        """
        تعديل عتبات الثقة بناءً على رضا المستخدم

        لو المستخدم راضي باستمرار → يمكن خفض العتبات (ثقة أكبر)
        لو المستخدم غير راضي → نرفع العتبات (حذر أكبر)
        """
        thresholds = self._confidence_thresholds
        adjustment = 0.01 * user_feedback  # تغيير طفيف

        old = thresholds.to_dict()

        thresholds.auto_accept = max(0.6, min(0.95, thresholds.auto_accept + adjustment))
        thresholds.review_required = max(0.3, min(0.7, thresholds.review_required + adjustment * 0.5))
        thresholds.reject_below = max(0.1, min(0.5, thresholds.reject_below + adjustment * 0.3))

        return {
            "changed": True,
            "old": old,
            "new": thresholds.to_dict(),
        }

    # ── الإحصائيات ────────────────────────────────────────────────────────
    def get_stats(self) -> dict:
        """إحصائيات حلقة التغذية الراجعة المعرفية"""
        return {
            "version": "v43",
            "total_feedback_processed": self._total_feedback_processed,
            "feedback_history_size": len(self._feedback_history),
            "quality_scores_tracked": len(self._response_quality_scores),
            "satisfaction_trend_size": len(self._user_satisfaction_trend),
            "domains_tracked": len(self._brain_accuracy_per_domain),
            "routing_preferences_count": len(self._routing_preferences.preferences),
            "ema_alpha": self.EMA_ALPHA,
            "last_adjustment": self._last_adjustment_time,
            "has_meta_cognition": self._meta_cognition is not None,
            "has_brain_router": self._brain_router is not None,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton
# ═══════════════════════════════════════════════════════════════════════════════

cognitive_feedback_loop = CognitiveFeedbackLoop()
