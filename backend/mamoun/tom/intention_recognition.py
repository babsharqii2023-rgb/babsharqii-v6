"""
BABSHARQII v10.0 — Intention Recognition
متعرف النوايا — يتنبأ بنوايا المستخدم من سياق المحادثة

Predicts user intentions from conversation context using:
1. Keyword pattern matching (Arabic and English)
2. Contextual analysis (repeated questions, tone changes)
3. Implicit intention detection

Target: Prediction accuracy > 75% on 100 examples

Feature Flag: MAMOUN_TOM_ADVANCED (default: false)
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

TOM_ADVANCED_ENABLED: bool = os.environ.get(
    "MAMOUN_TOM_ADVANCED", "false"
).lower() in ("true", "1", "yes")


@dataclass
class IntentionPrediction:
    """تنبؤ بالنية"""
    intention: str = ""           # نوع النية (seek_information, obtain_resource, etc.)
    intention_ar: str = ""        # وصف النية بالعربية
    confidence: float = 0.0       # ثقة التنبؤ
    evidence: list[str] = field(default_factory=list)   # الأدلة الداعمة
    is_explicit: bool = True      # هل النية صريحة أم ضمنية؟

    def to_dict(self) -> dict:
        return {
            "intention": self.intention,
            "intention_ar": self.intention_ar,
            "confidence": round(self.confidence, 4),
            "evidence": self.evidence,
            "is_explicit": self.is_explicit,
        }


# Intention patterns: (keywords, intention_id, arabic_name, is_primary)
INTENTION_PATTERNS = [
    # Arabic patterns
    (["سؤال", "ماذا", "كيف", "لماذا", "متى", "أين", "من", "هل", "كم"], "seek_information", "البحث عن معلومات", True),
    (["استفسار", "أريد أن أعرف", "أخبرني", "اشرح"], "seek_information", "البحث عن معلومات", True),
    (["طلب", "أريد", "احتاج", "أرجو", "هل يمكنك"], "obtain_resource", "الحصول على مورد", True),
    (["شكراً", "شكرا", "جزاك الله", "ممتاز", "رائع"], "express_gratitude", "التعبير عن الامتنان", False),
    (["شكوى", "مشكلة", "لا يعمل", "خطأ", "سيء"], "express_dissatisfaction", "التعبير عن عدم الرضا", False),
    (["اقتراح", "أقترح", "ما رأيك", "هل يمكن"], "collaborate", "التعاون", False),
    (["رفض", "لا أريد", "لا أحب", "ممنوع"], "resist", "المقاومة", False),
    (["مساعدة", "ساعدني", "ساعد"], "seek_help", "طلب المساعدة", True),
    (["تعلم", "علمني", "كيف أتعلم"], "learn", "التعلم", True),
    # English patterns
    (["what", "how", "why", "when", "where", "who", "which"], "seek_information", "البحث عن معلومات", True),
    (["please", "can you", "i want", "i need", "give me"], "obtain_resource", "الحصول على مورد", True),
    (["thanks", "thank you", "great", "excellent"], "express_gratitude", "التعبير عن الامتنان", False),
    (["complaint", "problem", "bug", "error", "bad"], "express_dissatisfaction", "التعبير عن عدم الرضا", False),
    (["suggest", "propose", "what if", "could we"], "collaborate", "التعاون", False),
    (["no", "refuse", "don't want", "stop"], "resist", "المقاومة", False),
    (["help", "assist", "support"], "seek_help", "طلب المساعدة", True),
    (["teach", "learn", "explain", "show me how"], "learn", "التعلم", True),
]

# Implicit intention indicators
IMPLICIT_INDICATORS = {
    "verify_understanding": {
        "triggers": ["سؤال متكرر", "repeated_question", "إعادة صياغة"],
        "intention_ar": "التحقق من الفهم",
    },
    "build_trust": {
        "triggers": ["شكر متكرر", "repeated_thanks", "مجاملة"],
        "intention_ar": "بناء الثقة",
    },
    "test_boundaries": {
        "triggers": ["سؤال تحدي", "challenge", "اختبرك"],
        "intention_ar": "اختبار الحدود",
    },
}


class IntentionRecognizer:
    """
    متعرف النوايا
    
    Predicts user intentions from conversation messages using:
    1. Explicit keyword matching
    2. Contextual analysis
    3. Implicit intention detection
    
    Target: >75% accuracy on 100 examples
    """

    def __init__(self, min_confidence: float = 0.4):
        self.min_confidence = min_confidence
        self._recognition_count = 0
        self._intention_history: list[IntentionPrediction] = []

    def recognize(
        self, user_message: str, conversation_context: Optional[dict] = None
    ) -> list[IntentionPrediction]:
        """
        تعرّف على نوايا المستخدم من رسالته.
        
        Args:
            user_message: رسالة المستخدم
            conversation_context: سياق المحادثة (previous_messages, user_profile, etc.)
        
        Returns:
            قائمة بالتنبؤات مرتبة حسب الثقة
        """
        if not TOM_ADVANCED_ENABLED:
            return []

        self._recognition_count += 1
        predictions: list[IntentionPrediction] = []

        # Step 1: Explicit intention recognition
        explicit = self._recognize_explicit(user_message)
        predictions.extend(explicit)

        # Step 2: Implicit intention recognition
        if conversation_context:
            implicit = self._recognize_implicit(user_message, conversation_context)
            predictions.extend(implicit)

        # Sort by confidence
        predictions.sort(key=lambda p: p.confidence, reverse=True)

        # Filter by minimum confidence
        predictions = [p for p in predictions if p.confidence >= self.min_confidence]

        # Store in history
        self._intention_history.extend(predictions)

        return predictions[:5]  # Top 5 predictions

    def predict_next_intention(
        self, intentions_history: Optional[list[IntentionPrediction]] = None
    ) -> IntentionPrediction:
        """
        تنبأ بالنية التالية بناءً على تاريخ النوايا.
        
        Uses pattern detection in intention sequences.
        """
        if not TOM_ADVANCED_ENABLED:
            return IntentionPrediction()

        history = intentions_history or self._intention_history

        if not history:
            return IntentionPrediction(
                intention="seek_information",
                intention_ar="البحث عن معلومات",
                confidence=0.3,
                is_explicit=False,
            )

        # Pattern: seek_information → obtain_resource → express_gratitude
        recent = [p.intention for p in history[-3:]]

        if len(recent) >= 2 and recent[-1] == "seek_information" and recent[-2] == "seek_information":
            return IntentionPrediction(
                intention="verify_understanding",
                intention_ar="التحقق من الفهم",
                confidence=0.6,
                evidence=["أسئلة متكررة تشير للتحقق"],
                is_explicit=False,
            )

        if len(recent) >= 2 and recent[-1] == "express_gratitude":
            return IntentionPrediction(
                intention="seek_information",
                intention_ar="البحث عن معلومات جديدة",
                confidence=0.5,
                evidence=["بعد الشكر عادةً يُتبع بسؤال جديد"],
                is_explicit=False,
            )

        # Default: continue the same pattern
        if history:
            last = history[-1]
            return IntentionPrediction(
                intention=last.intention,
                intention_ar=last.intention_ar,
                confidence=0.4,
                is_explicit=False,
            )

        return IntentionPrediction(
            intention="seek_information",
            intention_ar="البحث عن معلومات",
            confidence=0.3,
            is_explicit=False,
        )

    # ═══════════════════════════════════════════════════════════════════════

    def _recognize_explicit(self, message: str) -> list[IntentionPrediction]:
        """تعرّف على النوايا الصريحة من الكلمات المفتاحية"""
        predictions = []
        message_lower = message.lower()

        for keywords, intention_id, arabic_name, is_primary in INTENTION_PATTERNS:
            match_count = sum(1 for kw in keywords if kw in message_lower)
            if match_count > 0:
                confidence = min(0.95, 0.5 + match_count * 0.15)
                if is_primary:
                    confidence = min(0.95, confidence + 0.1)

                predictions.append(IntentionPrediction(
                    intention=intention_id,
                    intention_ar=arabic_name,
                    confidence=confidence,
                    evidence=[f"كلمة مفتاحية: {kw}" for kw in keywords if kw in message_lower],
                    is_explicit=True,
                ))

        # Deduplicate by intention
        seen = set()
        unique = []
        for p in predictions:
            if p.intention not in seen:
                seen.add(p.intention)
                unique.append(p)

        return unique

    def _recognize_implicit(
        self, message: str, context: dict
    ) -> list[IntentionPrediction]:
        """تعرّف على النوايا الضمنية من السياق"""
        predictions = []
        previous_messages = context.get("previous_messages", [])

        # Check for repeated questions → verify_understanding
        if len(previous_messages) >= 2:
            last_two = [m.lower() for m in previous_messages[-2:]]
            message_lower = message.lower()

            # Simple similarity check
            for prev in last_two:
                overlap = len(set(message_lower.split()) & set(prev.split()))
                total = len(set(message_lower.split()) | set(prev.split()))
                if total > 0 and overlap / total > 0.5:
                    predictions.append(IntentionPrediction(
                        intention="verify_understanding",
                        intention_ar="التحقق من الفهم",
                        confidence=0.6,
                        evidence=["سؤال مشابه لسؤال سابق"],
                        is_explicit=False,
                    ))
                    break

        # Check for challenge/test patterns
        challenge_words = ["اختبر", "تحدي", "هل تستطيع", "test", "challenge", "can you"]
        message_lower = message.lower()
        for word in challenge_words:
            if word in message_lower:
                predictions.append(IntentionPrediction(
                    intention="test_boundaries",
                    intention_ar="اختبار الحدود",
                    confidence=0.7,
                    evidence=[f"كلمة تحدي: {word}"],
                    is_explicit=False,
                ))
                break

        return predictions

    @property
    def stats(self) -> dict:
        """إحصائيات المتعرف"""
        return {
            "total_recognitions": self._recognition_count,
            "history_size": len(self._intention_history),
            "enabled": TOM_ADVANCED_ENABLED,
        }
