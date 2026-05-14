"""
BABSHARQII v28.0-stable — ML Layer
طبقة التعلم الآلي لتصنيف المشاعر وتقييم الجدة وتصنيف النوايا
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class EmotionClassifier:
    """تصنيف المشاعر متعدد الأبعاد مع دعم السخرية والإحباط"""

    EMOTION_KEYWORDS = {
        "سعادة": ["سعيد", "فرح", "حب", "ممتاز", "رائع", "مبدع", "أحسنت"],
        "حزن": ["حزين", "بكاء", "ألم", "فقدان", "وحيد", "يائس"],
        "غضب": ["غاضب", "كره", "احتقار", "ظلم", "غضب", "انفجار"],
        "فضول": ["فضول", "استكشاف", "اكتشاف", "معرفة", "تساؤل", "كيف"],
        "خوف": ["خوف", "قلق", "توتر", "رعب", "خطر", "هروب"],
        "مفاجأة": ["مفاجأة", "صدمة", "غير متوقع", "عجيب", "واو"],
        "حياد": [],
    }

    SARCASM_PATTERNS = [
        r"أكيد\b.*\bيا سلام",
        r"شكراً\s*جزيلاً.*\b(لا|بدون)",
        r"يا سلام.*\b(ما\s)?أروع",
        r"بالتأكيد.*\b(لا|لم|لن)",
    ]

    FRUSTRATION_PATTERNS = [
        r"\b(لماذا|ليش)\s.*\b(لا|لم|لن)",
        r"\b(مزعج|منهك|متعب)\b",
        r"\b(لن|لم)\s.*\b(يعمل|يشتغل|ينجح)",
        r"\b(فشل|فاشل)\b",
    ]

    def classify(self, text: str) -> dict:
        """Classify emotions in the given Arabic text"""
        text_lower = text.lower()

        # Score each emotion
        scores = {}
        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            scores[emotion] = score

        # Find primary emotion
        primary = max(scores, key=scores.get) if any(scores.values()) else "حياد"
        confidence = min(0.95, 0.5 + scores.get(primary, 0) * 0.15) if primary != "حياد" else 0.6

        # Detect sarcasm and frustration
        sarcasm_detected = any(re.search(p, text) for p in self.SARCASM_PATTERNS)
        frustration_detected = any(re.search(p, text) for p in self.FRUSTRATION_PATTERNS)

        # VAD (Valence-Arousal-Dominance)
        valence = 0.5
        arousal = 0.5
        if primary in ("سعادة", "فضول", "مفاجأة"):
            valence = 0.7 + (0.1 * scores.get(primary, 0))
        elif primary in ("حزن", "غضب", "خوف"):
            valence = 0.2 - (0.05 * scores.get(primary, 0))
        if primary in ("غضب", "خوف", "مفاجأة"):
            arousal = 0.8
        elif primary == "حياد":
            arousal = 0.3

        # Secondary emotions
        secondary = [e for e, s in scores.items() if s > 0 and e != primary]

        return {
            "primary_emotion": primary,
            "confidence": min(confidence, 1.0),
            "valence": max(-1, min(1, valence)),
            "arousal": max(0, min(1, arousal)),
            "sarcasm_detected": sarcasm_detected,
            "frustration_detected": frustration_detected,
            "secondary_emotions": secondary[:3],
            "explanation": f"تم اكتشاف مشاعر {primary} بناءً على تحليل النص",
        }


class NoveltyScorer:
    """تقييم مدى جدة الأفكار والمقترحات"""

    def score(self, text: str, context: Optional[list] = None) -> dict:
        """Score the novelty of the given text"""
        # Simple heuristic-based scoring
        text_words = set(text.split())
        novelty_indicators = [
            "جديد", "مبتكر", "غير مسبوق", "أصيل", "فريد",
            "إبداع", "اختراع", "اكتشاف", "ابتكار", "تطوير",
        ]

        novelty_count = sum(1 for ind in novelty_indicators if ind in text)

        # Base novelty score
        base_score = 30 + (novelty_count * 15)

        # Check against context (if available)
        if context:
            overlap = sum(1 for w in text_words if any(w in c for c in context))
            if len(text_words) > 0:
                context_similarity = overlap / len(text_words)
                base_score = base_score * (1 - context_similarity * 0.5)

        score = min(100, max(0, base_score))

        return {
            "novelty_score": score,
            "level": "عالي" if score >= 70 else "متوسط" if score >= 40 else "منخفض",
            "indicators_found": novelty_count,
        }


class IntentClassifier:
    """تصنيف نوايا المستخدم لتوجيه الردود المناسبة"""

    INTENT_PATTERNS = {
        "question": [r"هل\b", r"ما\b", r"كيف\b", r"لماذا\b", r"أين\b", r"متى\b", r"من\b", r"\?"],
        "command": [r"افعل\b", r"قم\b", r"أنشئ\b", r"احذف\b", r"عدّل\b", r"شغّل\b", r"أوقف\b"],
        "request": [r"أريد\b", r"أحتاج\b", r"ارجو\b", r"ساعدني\b", r"هل يمكنك\b"],
        "complaint": [r"لا يعمل\b", r"مشكلة\b", r"خطأ\b", r"فشل\b", r"سيء\b"],
        "greeting": [r"مرحبا\b", r"السلام\b", r"أهلا\b", r"صباح\b", r"مساء\b"],
        "feedback": [r"شكرا\b", r"ممتاز\b", r"رائع\b", r"جيد\b", r"سيء\b"],
    }

    def classify(self, text: str) -> dict:
        """Classify the intent of the given text"""
        scores = {}
        matched_patterns = {}

        for intent, patterns in self.INTENT_PATTERNS.items():
            count = 0
            matched = []
            for pattern in patterns:
                matches = re.findall(pattern, text)
                if matches:
                    count += len(matches)
                    matched.extend(matches)
            scores[intent] = count
            matched_patterns[intent] = matched

        primary_intent = max(scores, key=scores.get) if any(scores.values()) else "question"
        confidence = min(0.95, 0.6 + scores.get(primary_intent, 0) * 0.1)

        return {
            "primary_intent": primary_intent,
            "confidence": confidence,
            "all_scores": scores,
            "matched_patterns": matched_patterns.get(primary_intent, []),
        }


# Export all classifiers
__all__ = ["EmotionClassifier", "NoveltyScorer", "IntentClassifier"]
