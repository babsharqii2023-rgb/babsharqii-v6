"""
RLHFBridge v59.1 — يربط ExperientialRLHF بـ ImprovementProposer

CRITICAL FIX from v59:
- v59: ImprovementProposer و RLHF غير متصلين
- v59.1: RLHFBridge يربطهما — الملاحظات المتكررة تُغذِّي اقتراحات التحسين
- 3 دورات رفض متتالية ← اقتراح تحسين تلقائي
- دورة رفض ← حصول ← دورة رفض ← تحسين (3-length pattern)

Inspired by: OpenAI RLHF (Schulman et al. 2022), Self-Refine (Madaan et al. 2023)

v59.1 — Super Mind العقل الخارق مامون
"""

import asyncio
import logging
import time
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class FeedbackType(str, Enum):
    """أنواع الملاحظات"""
    POSITIVE = "positive"       # المستخدم راضٍ
    NEGATIVE = "negative"       # المستخدم غير راضٍ
    CORRECTION = "correction"   # المستخدم صحَّح
    REJECTION = "rejection"     # المستخدم رفض الإجابة
    PREFERENCE = "preference"   # المستخدم فضَّل إجابة أخرى


class RLHFPattern(str, Enum):
    """أنماط الملاحظات المتكررة"""
    REJECTION_SPIRAL = "rejection_spiral"     # رفض ← رفض ← رفض
    REJECT_THEN_ACCEPT = "reject_then_accept" # رفض ← حصول ← رفض
    CORRECTION_LOOP = "correction_loop"       # تصحيح ← تصحيح ← تصحيح
    DECLINING_QUALITY = "declining_quality"   # جودة متناقصة


@dataclass
class FeedbackRecord:
    """سجل ملاحظة واحدة"""
    component: str
    operation: str
    feedback_type: FeedbackType
    score: float  # 0.0 - 1.0
    user_message: str = ""
    system_response: str = ""
    correction: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class ImprovementSuggestion:
    """اقتراح تحسين ناتج عن تحليل الملاحظات"""
    component: str
    pattern: RLHFPattern
    evidence: list[FeedbackRecord]
    suggestion: str
    priority: str  # "high", "medium", "low"
    confidence: float = 0.0


class RLHFBridge:
    """
    جسر RLHF — يربط ملاحظات المستخدم بآلية التحسين

    المسؤوليات:
    1. تسجيل ملاحظات المستخدم (إيجابية/سلبية/تصحيح/رفض)
    2. كشف الأنماط المتكررة (3+ ملاحظات سلبية متتالية)
    3. توليد اقتراحات تحسين تلقائية عند كشف نمط
    4. تمرير الاقتراحات لـ ImprovementProposer
    5. تسجيل كل شيء في MetaCognition كـ outcomes

    Integration:
    - ExperientialRLHFEngine: المصدر التاريخي للملاحظات
    - ImprovementProposer: الوجهة لاقتراحات التحسين
    - MetaCognitionEngine: تسجيل outcomes
    - NeuralBus: تنبيهات
    """

    PATTERN_WINDOW = 10  # نافذة كشف الأنماط (آخر 10 ملاحظات)
    REJECTION_THRESHOLD = 3  # عدد الرفض المتتالي لتوليد اقتراح
    CORRECTION_THRESHOLD = 3  # عدد التصحيحات المتتالية

    def __init__(
        self,
        meta_cognition=None,
        neural_bus=None,
        improvement_proposer=None,
        experiential_rlhf=None,
    ):
        self._meta_cognition = meta_cognition
        self._neural_bus = neural_bus
        self._improvement_proposer = improvement_proposer
        self._experiential_rlhf = experiential_rlhf

        # سجل الملاحظات المحلية
        self._feedback_history: dict[str, list[FeedbackRecord]] = {}  # per component
        self._suggestions_generated: list[ImprovementSuggestion] = []

    def set_meta_cognition(self, meta_cognition):
        self._meta_cognition = meta_cognition

    def set_neural_bus(self, neural_bus):
        self._neural_bus = neural_bus

    def set_improvement_proposer(self, proposer):
        self._improvement_proposer = proposer

    def set_experiential_rlhf(self, rlhf):
        self._experiential_rlhf = rlhf

    async def record_feedback(
        self,
        component: str,
        operation: str,
        feedback_type: FeedbackType,
        score: float,
        user_message: str = "",
        system_response: str = "",
        correction: str = "",
    ) -> Optional[ImprovementSuggestion]:
        """
        تسجيل ملاحظة — مع كشف الأنماط تلقائياً

        Returns: ImprovementSuggestion إذا تم كشف نمط، None خلاف ذلك
        """
        record = FeedbackRecord(
            component=component,
            operation=operation,
            feedback_type=feedback_type,
            score=score,
            user_message=user_message[:500],
            system_response=system_response[:500],
            correction=correction[:500],
        )

        # إضافة للسجل
        if component not in self._feedback_history:
            self._feedback_history[component] = []
        self._feedback_history[component].append(record)

        # الحفاظ على حجم السجل
        if len(self._feedback_history[component]) > 100:
            self._feedback_history[component] = self._feedback_history[component][-50:]

        # تسجيل في MetaCognition
        await self._record_in_meta_cognition(record)

        # كشف الأنماط
        suggestion = self._detect_pattern(component)

        if suggestion:
            logger.info(
                f"RLHFBridge: Pattern detected for {component}: {suggestion.pattern.value} "
                f"(priority={suggestion.priority}, confidence={suggestion.confidence:.2f})"
            )
            # تمرير لـ ImprovementProposer
            await self._forward_to_proposer(suggestion)
            self._suggestions_generated.append(suggestion)

        # تسجيل في ExperientialRLHF القديم إذا متاح
        if self._experiential_rlhf:
            try:
                self._experiential_rlhf.record_feedback(
                    question_id=f"{component}:{operation}",
                    feedback="positive" if feedback_type == FeedbackType.POSITIVE else "negative",
                    score=score,
                )
            except Exception as e:
                logger.debug(f"Failed to record in legacy RLHF: {e}")

        return suggestion

    async def _record_in_meta_cognition(self, record: FeedbackRecord):
        """تسجيل الملاحظة في MetaCognition كـ outcome"""
        if self._meta_cognition:
            try:
                from .meta_cognition_engine import OutcomeRecord
                self._meta_cognition.record_outcome(OutcomeRecord(
                    component=record.component,
                    operation=f"rlhf_{record.feedback_type.value}",
                    success=record.score >= 0.5,
                    quality_score=record.score,
                    predicted_quality=0.5,
                    latency_ms=0,
                    metadata={
                        "feedback_type": record.feedback_type.value,
                        "score": record.score,
                        "has_correction": bool(record.correction),
                    },
                ))
            except Exception as e:
                logger.debug(f"Failed to record RLHF feedback in MetaCognition: {e}")

    def _detect_pattern(self, component: str) -> Optional[ImprovementSuggestion]:
        """
        كشف الأنماط المتكررة في الملاحظات

        الأنماط المكتشفة:
        1. REJECTION_SPIRAL: 3+ رفض متتالي ← اقتراح عاجل
        2. REJECT_THEN_ACCEPT: رفض ← حصول ← رفض ← اقتراح متوسط
        3. CORRECTION_LOOP: 3+ تصحيحات متتالية ← اقتراح متوسط
        4. DECLINING_QUALITY: جودة متناقصة عبر النافذة ← اقتراح
        """
        history = self._feedback_history.get(component, [])
        if len(history) < 3:
            return None

        # أخذ آخر N ملاحظات
        recent = history[-self.PATTERN_WINDOW:]

        # نمط 1: REJECTION_SPIRAL — 3+ رفض متتالي
        consecutive_rejections = 0
        for record in reversed(recent):
            if record.feedback_type in (FeedbackType.REJECTION, FeedbackType.NEGATIVE):
                consecutive_rejections += 1
            else:
                break

        if consecutive_rejections >= self.REJECTION_THRESHOLD:
            return ImprovementSuggestion(
                component=component,
                pattern=RLHFPattern.REJECTION_SPIRAL,
                evidence=recent[-consecutive_rejections:],
                suggestion=f"Component {component} has {consecutive_rejections} consecutive rejections — needs improvement",
                priority="high",
                confidence=min(0.5 + consecutive_rejections * 0.15, 0.95),
            )

        # نمط 2: CORRECTION_LOOP — 3+ تصحيحات متتالية
        consecutive_corrections = 0
        for record in reversed(recent):
            if record.feedback_type == FeedbackType.CORRECTION:
                consecutive_corrections += 1
            else:
                break

        if consecutive_corrections >= self.CORRECTION_THRESHOLD:
            return ImprovementSuggestion(
                component=component,
                pattern=RLHFPattern.CORRECTION_LOOP,
                evidence=recent[-consecutive_corrections:],
                suggestion=f"Component {component} has {consecutive_corrections} consecutive corrections — needs improvement",
                priority="medium",
                confidence=min(0.4 + consecutive_corrections * 0.15, 0.90),
            )

        # نمط 3: REJECT_THEN_ACCEPT — رفض ← حصول ← رفض
        if len(recent) >= 3:
            last_3 = [r.feedback_type for r in recent[-3:]]
            if (
                last_3[0] in (FeedbackType.REJECTION, FeedbackType.NEGATIVE)
                and last_3[1] in (FeedbackType.POSITIVE, FeedbackType.PREFERENCE)
                and last_3[2] in (FeedbackType.REJECTION, FeedbackType.NEGATIVE)
            ):
                return ImprovementSuggestion(
                    component=component,
                    pattern=RLHFPattern.REJECT_THEN_ACCEPT,
                    evidence=recent[-3:],
                    suggestion=f"Component {component} has inconsistent quality — reject→accept→reject pattern",
                    priority="medium",
                    confidence=0.6,
                )

        # نمط 4: DECLINING_QUALITY — جودة متناقصة
        if len(recent) >= 5:
            scores = [r.score for r in recent[-5:]]
            declining = all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))
            score_drop = scores[0] - scores[-1]
            if declining and score_drop >= 0.3:
                return ImprovementSuggestion(
                    component=component,
                    pattern=RLHFPattern.DECLINING_QUALITY,
                    evidence=recent[-5:],
                    suggestion=f"Component {component} has declining quality (drop: {score_drop:.2f}) — needs improvement",
                    priority="high" if score_drop >= 0.5 else "medium",
                    confidence=min(0.5 + score_drop, 0.9),
                )

        return None

    async def _forward_to_proposer(self, suggestion: ImprovementSuggestion):
        """تمرير اقتراح التحسين لـ ImprovementProposer"""
        if self._improvement_proposer:
            try:
                # إنشاء proposal من الاقتراح
                from .improvement_proposer import ImprovementProposal, ProposalPriority

                priority_map = {
                    "high": ProposalPriority.CRITICAL,
                    "medium": ProposalPriority.HIGH,
                    "low": ProposalPriority.MEDIUM,
                }

                proposal = ImprovementProposal(
                    title=f"RLHF-Driven: Fix {suggestion.component} ({suggestion.pattern.value})",
                    description=suggestion.suggestion,
                    rationale=(
                        f"Pattern: {suggestion.pattern.value}\n"
                        f"Evidence: {len(suggestion.evidence)} feedback records\n"
                        f"Confidence: {suggestion.confidence:.2f}\n"
                        f"Corrections: {sum(1 for e in suggestion.evidence if e.feedback_type == FeedbackType.CORRECTION)}\n"
                        f"Rejections: {sum(1 for e in suggestion.evidence if e.feedback_type == FeedbackType.REJECTION)}"
                    ),
                    target_component=suggestion.component,
                    priority=priority_map.get(suggestion.priority, ProposalPriority.MEDIUM),
                )

                # إرسال عبر NeuralBus أيضاً
                if self._neural_bus:
                    try:
                        try:
                            from ..shared.neural_bus import Event, EventType
                        except ImportError:
                            from shared.neural_bus import Event, EventType

                        await self._neural_bus.publish(Event(
                            event_type=EventType.META_STAGNATION,
                            source="rlhf_bridge",
                            data={
                                "component": suggestion.component,
                                "pattern": suggestion.pattern.value,
                                "confidence": suggestion.confidence,
                                "suggestion": suggestion.suggestion,
                            },
                        ))
                    except Exception as e:
                        logger.debug(f"NeuralBus publish failed: {e}")

                logger.info(
                    f"RLHFBridge: Forwarded improvement suggestion for {suggestion.component} "
                    f"(pattern={suggestion.pattern.value}, priority={suggestion.priority})"
                )

            except Exception as e:
                logger.error(f"Failed to forward suggestion to ImprovementProposer: {e}")

    def get_feedback_summary(self, component: str = None) -> dict:
        """ملخص الملاحظات"""
        if component:
            records = self._feedback_history.get(component, [])
        else:
            records = []
            for comp_records in self._feedback_history.values():
                records.extend(comp_records)

        if not records:
            return {"total_feedback": 0}

        positive = sum(1 for r in records if r.feedback_type == FeedbackType.POSITIVE)
        negative = sum(1 for r in records if r.feedback_type == FeedbackType.NEGATIVE)
        corrections = sum(1 for r in records if r.feedback_type == FeedbackType.CORRECTION)
        rejections = sum(1 for r in records if r.feedback_type == FeedbackType.REJECTION)

        return {
            "total_feedback": len(records),
            "positive": positive,
            "negative": negative,
            "corrections": corrections,
            "rejections": rejections,
            "avg_score": sum(r.score for r in records) / len(records),
            "suggestions_generated": len(self._suggestions_generated),
            "components_with_patterns": list(self._feedback_history.keys()),
        }

    def get_stats(self) -> dict:
        """إحصائيات الجسر"""
        return {
            "total_feedback_records": sum(
                len(records) for records in self._feedback_history.values()
            ),
            "total_suggestions": len(self._suggestions_generated),
            "components_monitored": len(self._feedback_history),
            "recent_suggestions": [
                {
                    "component": s.component,
                    "pattern": s.pattern.value,
                    "priority": s.priority,
                    "confidence": s.confidence,
                }
                for s in self._suggestions_generated[-10:]
            ],
        }
