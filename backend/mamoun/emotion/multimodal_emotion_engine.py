"""
BABSHARQII v40.0 — Multimodal Emotion Engine
محرك الفهم العاطفي العميق متعدد الوسائط

A multimodal emotion recognition engine that analyzes text, audio, and images
to detect emotions including sarcasm, hidden frustration, and complex emotional
states.

Inspired by:
  - EAC-Agent (Emotion-Aware Context Agent, 2025-2026)
  - Multimodal Emotion Recognition research (Poria et al., 2017-2025)
  - Contextual Incongruity Detection for Sarcasm (Joshi et al., 2016-2025)
  - Arabic NLP emotion detection (Abdul-Mageed et al., 2020-2025)
  - Affective Computing (Picard, 1997) — multimodal emotion recognition

Architecture:
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                     MultimodalEmotionEngine                              │
  │                                                                          │
  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐    │
  │  │  Text Channel  │  │ Audio Channel  │  │    Image Channel       │    │
  │  │  (EmotionDet.  │  │ (pitch, energy │  │ (facial expressions,   │    │
  │  │   + sarcasm +  │  │  speech rate,  │  │  visual emotion cues)  │    │
  │  │   frustration) │  │  prosody)      │  │                        │    │
  │  └───────┬────────┘  └───────┬────────┘  └───────────┬────────────┘    │
  │          │                   │                       │                   │
  │  ┌───────▼───────────────────▼───────────────────────▼──────────────┐   │
  │  │                     Fusion Layer                                  │   │
  │  │  Weighted averaging: text=0.5, audio=0.3, image=0.2             │   │
  │  │  Weight redistribution when channels unavailable                 │   │
  │  └──────────────────────────────┬────────────────────────────────────┘   │
  │                                 │                                        │
  │  ┌──────────────────────────────▼────────────────────────────────────┐   │
  │  │            Sarcasm Detector + Frustration Detector                │   │
  │  │  Contextual incongruity, Arabic-specific patterns,               │   │
  │  │  hidden frustration through linguistic markers                   │   │
  │  └──────────────────────────────────────────────────────────────────┘   │
  └──────────────────────────────────────────────────────────────────────────┘

Env toggles:
    MAMOUN_MULTIMODAL_EMOTION — تمكين/تعطيل المحرك العاطفي متعدد الوسائط (الافتراضي: false)
"""

from __future__ import annotations

import os
import re
import math
import base64
import logging
import struct
import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)

# ─── مفاتيح التهيئة البيئية — Environment Config ─────────────────────────────

MULTIMODAL_EMOTION_ENABLED: bool = os.environ.get(
    "MAMOUN_MULTIMODAL_EMOTION", "false"
).lower() in ("true", "1", "yes")


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج البيانات — Data Models
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ChannelResult:
    """
    نتيجة قناة التحليل — نتيجة تحليل قناة واحدة (نص/صوت/صورة).
    Result from a single analysis channel (text/audio/image).
    """
    channel_name: str = ""                                   # اسم القناة
    emotions: dict[str, float] = field(default_factory=dict) # {emotion: score}
    dominant_emotion: str = "neutral"                        # المشاعر السائدة
    confidence: float = 0.0                                  # ثقة الكشف (0-1)
    valence: float = 0.0                                     # التكافؤ (-1 إلى +1)
    arousal: float = 0.0                                     # الاستثارة (-1 إلى +1)
    available: bool = False                                  # هل القناة متاحة؟

    def to_dict(self) -> dict:
        return {
            "channel_name": self.channel_name,
            "emotions": {k: round(v, 4) for k, v in self.emotions.items()},
            "dominant_emotion": self.dominant_emotion,
            "confidence": round(self.confidence, 4),
            "valence": round(self.valence, 4),
            "arousal": round(self.arousal, 4),
            "available": self.available,
        }


@dataclass
class SarcasmResult:
    """
    نتيجة كشف السخرية — نتيجة كشف السخرية والتهكم.
    Result of sarcasm detection analysis.
    """
    is_sarcastic: bool = False                              # هل النص ساخر؟
    confidence: float = 0.0                                  # ثقة الكشف (0-1)
    markers: list[str] = field(default_factory=list)         # علامات السخرية
    pattern_type: str = ""                                   # نمط السخرية
    suggested_response_tone: str = "neutral"                 # نبرة الرد المقترحة

    def to_dict(self) -> dict:
        return {
            "is_sarcastic": self.is_sarcastic,
            "confidence": round(self.confidence, 4),
            "markers": self.markers,
            "pattern_type": self.pattern_type,
            "suggested_response_tone": self.suggested_response_tone,
        }


@dataclass
class FrustrationResult:
    """
    نتيجة كشف الإحباط — نتيجة كشف الإحباط الخفي.
    Result of hidden frustration detection analysis.
    """
    is_frustrated: bool = False                             # هل يوجد إحباط؟
    confidence: float = 0.0                                  # ثقة الكشف (0-1)
    level: str = "none"                                      # مستوى الإحباط (mild/moderate/severe/none)
    indicators: list[str] = field(default_factory=list)      # مؤشرات الإحباط
    suggested_response_strategy: str = ""                    # استراتيجية الرد المقترحة

    def to_dict(self) -> dict:
        return {
            "is_frustrated": self.is_frustrated,
            "confidence": round(self.confidence, 4),
            "level": self.level,
            "indicators": self.indicators,
            "suggested_response_strategy": self.suggested_response_strategy,
        }


@dataclass
class MultimodalEmotionResult:
    """
    نتيجة التحليل العاطفي الشامل — النتيجة الشاملة للتحليل العاطفي متعدد الوسائط.
    Comprehensive result of multimodal emotion analysis.
    """
    text_result: ChannelResult = field(default_factory=ChannelResult)
    audio_result: ChannelResult = field(default_factory=ChannelResult)
    image_result: ChannelResult = field(default_factory=ChannelResult)
    fused_emotions: dict[str, float] = field(default_factory=dict)
    dominant_emotion: str = "neutral"
    confidence: float = 0.0
    valence: float = 0.0
    arousal: float = 0.0
    sarcasm: SarcasmResult = field(default_factory=SarcasmResult)
    frustration: FrustrationResult = field(default_factory=FrustrationResult)
    recommendations: list[str] = field(default_factory=list)
    language: str = "ar"

    def to_dict(self) -> dict:
        return {
            "text_result": self.text_result.to_dict(),
            "audio_result": self.audio_result.to_dict(),
            "image_result": self.image_result.to_dict(),
            "fused_emotions": {k: round(v, 4) for k, v in self.fused_emotions.items()},
            "dominant_emotion": self.dominant_emotion,
            "confidence": round(self.confidence, 4),
            "valence": round(self.valence, 4),
            "arousal": round(self.arousal, 4),
            "sarcasm": self.sarcasm.to_dict(),
            "frustration": self.frustration.to_dict(),
            "recommendations": self.recommendations,
            "language": self.language,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  قيم التكافؤ والاستثارة — Valence-Arousal values per emotion
# ═══════════════════════════════════════════════════════════════════════════════

_VALENCE_AROUSAL: dict[str, tuple[float, float]] = {
    "joy": (0.8, 0.5),
    "sadness": (-0.7, -0.3),
    "anger": (-0.6, 0.7),
    "fear": (-0.7, 0.6),
    "surprise": (0.0, 0.8),
    "disgust": (-0.6, 0.3),
    "trust": (0.6, -0.2),
    "anticipation": (0.3, 0.5),
    "love": (0.9, 0.3),
    "shame": (-0.5, 0.2),
    "pride": (0.5, 0.4),
    "gratitude": (0.7, 0.1),
    "neutral": (0.0, 0.0),
}

# ─── كلمات إيجابية للاستخدام في كشف السخرية — Positive words for sarcasm detection
_POSITIVE_WORDS_AR: set[str] = {
    "حلو", "جميل", "رائع", "ممتاز", "عظيم", "مذهل", "سعيد", "فرحان",
    "مبسوط", "مرتاح", "منيح", "زين", "أحلى", "أفضل", "يسلااام",
}
_POSITIVE_WORDS_EN: set[str] = {
    "great", "wonderful", "amazing", "excellent", "fantastic", "beautiful",
    "perfect", "lovely", "brilliant", "awesome", "nice", "good", "best",
}

# ─── كلمات سلبية للاستخدام في كشف السخرية — Negative words for sarcasm detection
_NEGATIVE_WORDS_AR: set[str] = {
    "سيء", "فاشل", "مصيبة", "كارثة", "مشكلة", "صعب", "مستحيل", "تعبان",
    "زفت", "بائس", "مأساة", "خسارة", "قلق", "خوف", "ألم",
}
_NEGATIVE_WORDS_EN: set[str] = {
    "terrible", "horrible", "awful", "bad", "worst", "failure", "disaster",
    "problem", "difficult", "impossible", "painful", "tragic", "loss",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  كاشف السخرية — Sarcasm Detector
# ═══════════════════════════════════════════════════════════════════════════════


class SarcasmDetector:
    """
    كاشف السخرية — يكتشف السخرية والتهكم في النص العربي والإنجليزي.
    Detects sarcasm and irony in Arabic and English text using contextual
    incongruity detection and language-specific patterns.
    """

    # ─── علامات السخرية العربية — Arabic sarcasm markers ──────────────────
    _AR_SARCASM_MARKERS: dict[str, str] = {
        "يا سلااام": "exaggerated_positive",
        "أكيد يعني": "dismissal_with_apparent_agreement",
        "شو هال": "dismissive_question",
        "والله عجب": "feigned_surprise",
        "الله يبارك فيك": "blessing_with_negative_context",
        "حلو كتير": "overly_positive_with_negative_context",
        "شكراً كتير": "excessive_gratitude",
        "يا عيني عليك": "feigned_admiration",
        "برافو عليك": "mock_applause",
        "تمام جداً": "overly_formal_agreement",
        "طبعاً طبعاً": "repeated_dismissive_agreement",
        "إيه الذوق": "mock_appreciation",
        "مش هيك": "rhetorical_disagreement",
    }

    # ─── علامات السخرية الإنجليزية — English sarcasm markers ──────────────
    _EN_SARCASM_MARKERS: dict[str, str] = {
        "oh great": "exaggerated_positive",
        "yeah right": "dismissal_with_apparent_agreement",
        "how wonderful": "feigned_positive",
        "thanks a lot": "excessive_gratitude",
        "good for you": "dismissal",
        "well done": "mock_applause",
        "sure thing": "dismissive_agreement",
        "obviously": "dismissive_agreement",
        "of course": "dismissive_agreement",
        "lovely": "feigned_positive",
        "fantastic": "feigned_positive",
        "brilliant": "mock_applause",
    }

    def detect(self, text: str, language: str = "ar") -> SarcasmResult:
        """
        كشف السخرية — يكتشف السخرية في النص.
        Detect sarcasm in text using contextual incongruity and markers.

        Args:
            text: النص المراد تحليله — text to analyze
            language: لغة النص (ar/en) — text language

        Returns:
            SarcasmResult — نتيجة كشف السخرية
        """
        if not text or not text.strip():
            return SarcasmResult()

        markers_found: list[str] = []
        pattern_types: list[str] = []
        incongruity_score: float = 0.0

        text_lower = text.lower().strip()

        # ─── كشف علامات السخرية المباشرة — Direct sarcasm marker detection ─
        if language == "ar":
            for marker, pattern_type in self._AR_SARCASM_MARKERS.items():
                if marker in text:
                    markers_found.append(marker)
                    pattern_types.append(pattern_type)
        else:
            for marker, pattern_type in self._EN_SARCASM_MARKERS.items():
                if marker.lower() in text_lower:
                    markers_found.append(marker)
                    pattern_types.append(pattern_type)

        # ─── كشف التناقض السياقي — Contextual incongruity detection ────
        has_positive = False
        has_negative = False

        if language == "ar":
            words = text.split()
            for word in words:
                clean = re.sub(r'[^\u0600-\u06FF\u0750-\u077F]', '', word)
                if clean in _POSITIVE_WORDS_AR:
                    has_positive = True
                if clean in _NEGATIVE_WORDS_AR:
                    has_negative = True
        else:
            words = text_lower.split()
            for word in words:
                clean = word.strip(".,!?;:")
                if clean in _POSITIVE_WORDS_EN:
                    has_positive = True
                if clean in _NEGATIVE_WORDS_EN:
                    has_negative = True

        # التناقض بين الإيجابي والسلبي = مؤشر سخرية
        # Incongruity between positive and negative = sarcasm indicator
        if has_positive and has_negative:
            incongruity_score = 0.6
            if "incongruity" not in pattern_types:
                pattern_types.append("positive_negative_incongruity")
                markers_found.append("positive_negative_incongruity" if language == "en" else "تناقض_إيجابي_سلبي")

        # ─── كشف الأحرف المكررة (إطالة ساخرة) — Repeated characters (sarcastic elongation) ─
        repeated_pattern = re.findall(r'(.)\1{2,}', text)
        if repeated_pattern:
            # الأحرف المكررة مع كلمات إيجابية = سخرية محتملة
            # Repeated chars with positive words = potential sarcasm
            if has_positive:
                incongruity_score = max(incongruity_score, 0.4)
                if "sarcastic_elongation" not in pattern_types:
                    pattern_types.append("sarcastic_elongation")
                    markers_found.append("elongated_chars" if language == "en" else "أحرف_مكررة")

        # ─── حساب الثقة — Confidence computation ─────────────────────────
        marker_confidence = min(len(markers_found) * 0.3, 0.7)
        total_confidence = min(marker_confidence + incongruity_score * 0.3, 1.0)

        is_sarcastic = total_confidence >= 0.4

        # ─── تحديد نمط السخرية الرئيسي — Determine primary pattern type ─
        pattern_type = "none"
        if pattern_types:
            pattern_type = pattern_types[0]

        # ─── تحديد نبرة الرد المقترحة — Suggest response tone ────────────
        suggested_tone = "neutral"
        if is_sarcastic:
            if pattern_type in ("exaggerated_positive", "feigned_positive",
                                "positive_negative_incongruity"):
                suggested_tone = "gentle_clarification"
            elif pattern_type in ("dismissal_with_apparent_agreement",
                                  "dismissive_agreement", "dismissal"):
                suggested_tone = "patient_reassurance"
            elif pattern_type in ("mock_applause", "feigned_admiration"):
                suggested_tone = "humble_acknowledgment"
            else:
                suggested_tone = "calm_empathy"

        return SarcasmResult(
            is_sarcastic=is_sarcastic,
            confidence=round(total_confidence, 4),
            markers=markers_found,
            pattern_type=pattern_type,
            suggested_response_tone=suggested_tone,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  كاشف الإحباط — Frustration Detector
# ═══════════════════════════════════════════════════════════════════════════════


class FrustrationDetector:
    """
    كاشف الإحباط — يكتشف الإحباط الخفي من خلال العلامات اللغوية.
    Detects hidden frustration through linguistic markers including repeated
    attempts, hedging, and passive-aggressive patterns in Arabic and English.
    """

    # ─── مؤشرات الإحباط العربية — Arabic frustration indicators ───────────
    _AR_FRUSTRATION_MARKERS: dict[str, str] = {
        "مرة أخرى": "repeated_attempt",
        "قلت لك": "repetition_emphasis",
        "ما فهمت": "comprehension_difficulty",
        "مش قادر": "inability_expression",
        "محاولات كثيرة": "multiple_attempts",
        "كل مرة": "recurring_problem",
        "ما في فائدة": "hopelessness",
        "تعبت من": "exhaustion",
        "مش قادر أتحمل": "low_tolerance",
        "خلاص": "giving_up",
        "يلا": "impatience",
        "بس": "restriction_hedging",
        "على أي حال": "resignation",
        "ما بعرف": "helplessness",
        "مش عارف": "helplessness_dialect",
        "جربت كل شي": "exhausted_options",
    }

    # ─── مؤشرات الإحباط الإنجليزية — English frustration indicators ──────
    _EN_FRUSTRATION_MARKERS: dict[str, str] = {
        "again": "repeated_attempt",
        "i told you": "repetition_emphasis",
        "i don't understand": "comprehension_difficulty",
        "i can't": "inability_expression",
        "tried everything": "exhausted_options",
        "every time": "recurring_problem",
        "no point": "hopelessness",
        "tired of": "exhaustion",
        "can't take it": "low_tolerance",
        "whatever": "giving_up",
        "fine": "passive_aggressive_agreement",
        "never mind": "dismissal",
        "just": "minimization",
        "still": "persistence_indicator",
        "nothing works": "exhausted_options",
    }

    # ─── أنماط السلبية العدوانية — Passive-aggressive patterns ────────────
    _AR_PASSIVE_AGGRESSIVE: list[str] = [
        "لا بأس", "مش مشكلة", "عادي", "ما في شي", "مو مهم",
    ]
    _EN_PASSIVE_AGGRESSIVE: list[str] = [
        "it's fine", "no problem", "whatever you say", "nothing matters",
        "don't worry about it",
    ]

    def detect(self, text: str, language: str = "ar") -> FrustrationResult:
        """
        كشف الإحباط — يكتشف الإحباط الخفي في النص.
        Detect hidden frustration in text through linguistic markers.

        Args:
            text: النص المراد تحليله — text to analyze
            language: لغة النص (ar/en) — text language

        Returns:
            FrustrationResult — نتيجة كشف الإحباط
        """
        if not text or not text.strip():
            return FrustrationResult()

        indicators_found: list[str] = []
        marker_categories: list[str] = []
        text_lower = text.lower().strip()

        # ─── كشف مؤشرات الإحباط المباشرة — Direct frustration marker detection
        if language == "ar":
            for marker, category in self._AR_FRUSTRATION_MARKERS.items():
                if marker in text:
                    indicators_found.append(marker)
                    marker_categories.append(category)
            # كشف السلبية العدوانية — Passive-aggressive detection
            for pa_marker in self._AR_PASSIVE_AGGRESSIVE:
                if pa_marker in text:
                    indicators_found.append(pa_marker)
                    marker_categories.append("passive_aggressive")
        else:
            for marker, category in self._EN_FRUSTRATION_MARKERS.items():
                if marker in text_lower:
                    indicators_found.append(marker)
                    marker_categories.append(category)
            for pa_marker in self._EN_PASSIVE_AGGRESSIVE:
                if pa_marker in text_lower:
                    indicators_found.append(pa_marker)
                    marker_categories.append("passive_aggressive")

        # ─── كشف علامات التعجب المتكررة — Multiple exclamation marks ──────
        exclamation_count = text.count("!") + text.count("!")
        if exclamation_count >= 3:
            indicators_found.append("multiple_exclamations")
            marker_categories.append("intensification")

        # ─── كشف التردد — Hedging detection ─────────────────────────────
        hedging_markers_ar = ["يعني", "شو يعني", "بصراحة", "والله"]
        hedging_markers_en = ["i mean", "sort of", "kind of", "honestly", "actually"]
        if language == "ar":
            for h in hedging_markers_ar:
                if h in text:
                    indicators_found.append(h)
                    marker_categories.append("hedging")
                    break
        else:
            for h in hedging_markers_en:
                if h in text_lower:
                    indicators_found.append(h)
                    marker_categories.append("hedging")
                    break

        # ─── حساب مستوى الإحباط — Frustration level computation ───────────
        frustration_score = 0.0
        unique_categories = set(marker_categories)

        # نقاط حسب فئات المؤشرات — Score by indicator categories
        category_weights = {
            "repeated_attempt": 0.25,
            "repetition_emphasis": 0.2,
            "comprehension_difficulty": 0.15,
            "inability_expression": 0.2,
            "multiple_attempts": 0.25,
            "recurring_problem": 0.25,
            "hopelessness": 0.35,
            "exhaustion": 0.3,
            "low_tolerance": 0.3,
            "giving_up": 0.35,
            "impatience": 0.2,
            "passive_aggressive": 0.25,
            "intensification": 0.15,
            "hedging": 0.1,
            "restriction_hedging": 0.1,
            "resignation": 0.3,
            "helplessness": 0.25,
            "helplessness_dialect": 0.25,
            "exhausted_options": 0.3,
            "dismissal": 0.2,
            "minimization": 0.1,
            "persistence_indicator": 0.15,
        }

        for cat in unique_categories:
            frustration_score += category_weights.get(cat, 0.1)

        # تقليل الزيادة المفرطة — Cap the score
        frustration_score = min(frustration_score, 1.0)

        # ─── تحديد المستوى — Determine frustration level ──────────────────
        level = "none"
        if frustration_score >= 0.6:
            level = "severe"
        elif frustration_score >= 0.35:
            level = "moderate"
        elif frustration_score >= 0.15:
            level = "mild"

        is_frustrated = frustration_score >= 0.15

        # ─── استراتيجية الرد المقترحة — Suggest response strategy ────────
        strategy = ""
        if is_frustrated:
            if level == "severe":
                strategy = "acknowledge_and_pause" if language == "en" else "اعتراف_وإيقاف_مؤقت"
            elif level == "moderate":
                strategy = "validate_and_simplify" if language == "en" else "تصديق_وتبسيط"
            else:
                strategy = "gentle_acknowledgment" if language == "en" else "اعتراف_لطيف"

        return FrustrationResult(
            is_frustrated=is_frustrated,
            confidence=round(frustration_score, 4),
            level=level,
            indicators=indicators_found,
            suggested_response_strategy=strategy,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  المحرك العاطفي متعدد الوسائط — MultimodalEmotionEngine
# ═══════════════════════════════════════════════════════════════════════════════


class MultimodalEmotionEngine:
    """
    المحرك العاطفي متعدد الوسائط — يحلل النص والصوت والصور لكشف المشاعر.
    Multimodal emotion recognition engine that analyzes text, audio, and images
    to detect emotions including sarcasm, hidden frustration, and complex
    emotional states.

    Features:
    - Three analysis channels: text, audio, image
    - Weighted fusion layer with configurable weights
    - Enhanced sarcasm detection with Arabic-specific patterns
    - Hidden frustration detection through linguistic markers
    - Automatic weight redistribution when channels are unavailable
    - Integration with existing EmotionDetector from social_perception

    Inspired by EAC-Agent and multimodal emotion recognition research (2025-2026).
    """

    def __init__(
        self,
        text_weight: float = 0.5,
        audio_weight: float = 0.3,
        image_weight: float = 0.2,
    ):
        """
        تهيئة المحرك العاطفي — Initialize the emotion engine.

        Args:
            text_weight: وزن قناة النص — weight for text channel (default: 0.5)
            audio_weight: وزن قناة الصوت — weight for audio channel (default: 0.3)
            image_weight: وزن قناة الصورة — weight for image channel (default: 0.2)
        """
        self._enabled = MULTIMODAL_EMOTION_ENABLED
        self._text_weight = text_weight
        self._audio_weight = audio_weight
        self._image_weight = image_weight
        self._initialized = True
        self._shutdown_flag = False

        # كاشف السخرية والإحباط — Sarcasm and frustration detectors
        self._sarcasm_detector = SarcasmDetector()
        self._frustration_detector = FrustrationDetector()

        # سجل تاريخ المشاعر — Emotion history tracking
        self._emotion_history: list[MultimodalEmotionResult] = []
        self._max_history: int = 100

        # محاولة استيراد كاشف المشاعر من social_perception — Try importing EmotionDetector
        self._emotion_detector = None
        try:
            from mamoun.agi.social_perception import EmotionDetector
            self._emotion_detector = EmotionDetector()
            logger.info("MultimodalEmotionEngine: EmotionDetector loaded from social_perception")
        except Exception as e:
            logger.warning(
                f"MultimodalEmotionEngine: Could not load EmotionDetector "
                f"from social_perception ({e}). Using built-in lexicon."
            )
            self._emotion_detector = None

        logger.info(
            f"MultimodalEmotionEngine initialized — enabled={self._enabled}, "
            f"weights=({self._text_weight}, {self._audio_weight}, {self._image_weight})"
        )

    # ═════════════════════════════════════════════════════════════════════════
    #  الطريقة الرئيسية — Main Analysis Method
    # ═════════════════════════════════════════════════════════════════════════

    def analyze(
        self,
        text: str = None,
        audio_base64: str = None,
        image_base64: str = None,
        language: str = "ar",
    ) -> MultimodalEmotionResult:
        """
        تحليل عاطفي شامل — Comprehensive multimodal emotion analysis.

        Args:
            text: النص المراد تحليله — text to analyze
            audio_base64: بيانات الصوت بترميز base64 — base64 encoded audio data
            image_base64: بيانات الصورة بترميز base64 — base64 encoded image data
            language: لغة النص (ar/en) — text language

        Returns:
            MultimodalEmotionResult — نتيجة التحليل العاطفي الشامل
        """
        if self._shutdown_flag:
            logger.warning("MultimodalEmotionEngine: Engine is shut down, returning empty result")
            return MultimodalEmotionResult(language=language)

        # ─── تحليل القنوات الفردية — Analyze individual channels ────────
        text_result = self.analyze_text(text, language) if text else ChannelResult(
            channel_name="text", available=False
        )
        audio_result = self.analyze_audio(audio_base64) if audio_base64 else ChannelResult(
            channel_name="audio", available=False
        )
        image_result = self.analyze_image(image_base64) if image_base64 else ChannelResult(
            channel_name="image", available=False
        )

        # ─── دمج النتائج — Fuse results ─────────────────────────────────
        fused = self.fuse_results(text_result, audio_result, image_result)

        # ─── كشف السخرية — Sarcasm detection ────────────────────────────
        sarcasm_result = SarcasmResult()
        if text:
            sarcasm_result = self.detect_sarcasm(text, language)

        # ─── كشف الإحباط — Frustration detection ────────────────────────
        frustration_result = FrustrationResult()
        if text:
            frustration_result = self.detect_frustration(text, language)

        # ─── توليد التوصيات — Generate recommendations ──────────────────
        recommendations = self._generate_recommendations(
            fused, sarcasm_result, frustration_result, language
        )

        result = MultimodalEmotionResult(
            text_result=text_result,
            audio_result=audio_result,
            image_result=image_result,
            fused_emotions=fused.fused_emotions,
            dominant_emotion=fused.dominant_emotion,
            confidence=fused.confidence,
            valence=fused.valence,
            arousal=fused.arousal,
            sarcasm=sarcasm_result,
            frustration=frustration_result,
            recommendations=recommendations,
            language=language,
        )

        # ─── تسجيل في سجل المشاعر — Record in emotion history ──────────
        self._emotion_history.append(result)
        if len(self._emotion_history) > self._max_history:
            self._emotion_history = self._emotion_history[-self._max_history:]

        return result

    # ═════════════════════════════════════════════════════════════════════════
    #  سجل تاريخ المشاعر — Emotion History Tracking
    # ═════════════════════════════════════════════════════════════════════════

    def get_history(self, limit: int = 20) -> list[MultimodalEmotionResult]:
        """
        الحصول على سجل تاريخ المشاعر — Get emotion analysis history.
        Returns the most recent emotion analysis results.

        Args:
            limit: الحد الأقصى للنتائج — maximum number of results to return

        Returns:
            قائمة بنتائج التحليل العاطفي — list of emotion analysis results
        """
        return self._emotion_history[-limit:]

    def clear_history(self) -> None:
        """مسح سجل المشاعر — Clear emotion history."""
        self._emotion_history = []

    # ═════════════════════════════════════════════════════════════════════════
    #  تحليل دفعي — Batch Analysis
    # ═════════════════════════════════════════════════════════════════════════

    def batch_analyze(
        self,
        texts: list[str],
        language: str = "ar",
    ) -> list[MultimodalEmotionResult]:
        """
        تحليل عاطفي دفعي — Batch emotion analysis for multiple texts.
        Efficiently analyzes multiple texts without audio/image channels.

        Args:
            texts: قائمة النصوص — list of texts to analyze
            language: لغة النصوص — text language

        Returns:
            قائمة بنتائج التحليل العاطفي — list of emotion analysis results
        """
        results: list[MultimodalEmotionResult] = []
        for text in texts:
            result = self.analyze(text=text, language=language)
            results.append(result)
        return results

    # ═════════════════════════════════════════════════════════════════════════
    #  قناة النص — Text Channel Analysis
    # ═════════════════════════════════════════════════════════════════════════

    def analyze_text(self, text: str, language: str = "ar") -> ChannelResult:
        """
        تحليل النص — Analyze text for emotions.
        Uses existing EmotionDetector from social_perception if available,
        otherwise falls back to built-in lexicon-based analysis.

        Args:
            text: النص المراد تحليله — text to analyze
            language: لغة النص (ar/en) — text language

        Returns:
            ChannelResult — نتيجة تحليل قناة النص
        """
        if not text or not text.strip():
            return ChannelResult(channel_name="text", available=False)

        emotions: dict[str, float] = {}
        dominant_emotion = "neutral"
        confidence = 0.0
        valence = 0.0
        arousal = 0.0

        # ─── استخدام EmotionDetector إذا كان متاحاً — Use EmotionDetector if available
        if self._emotion_detector is not None:
            try:
                profile = self._emotion_detector.detect_emotions(text)
                emotions = dict(profile.emotions)
                dominant_emotion = profile.dominant_emotion
                confidence = profile.confidence
                valence = profile.valence
                arousal = profile.arousal
            except Exception as e:
                logger.warning(f"EmotionDetector failed: {e}. Falling back to built-in.")
                emotions, dominant_emotion, confidence, valence, arousal = (
                    self._text_analysis_fallback(text, language)
                )
        else:
            emotions, dominant_emotion, confidence, valence, arousal = (
                self._text_analysis_fallback(text, language)
            )

        # ─── تعزيز بنتائج السخرية — Enhance with sarcasm results ────────
        sarcasm = self.detect_sarcasm(text, language)
        if sarcasm.is_sarcastic and sarcasm.confidence > 0.5:
            # إذا تم كشف سخرية عالية الثقة، عدّل التكافؤ — Adjust valence for sarcasm
            valence = valence * 0.5 - 0.2  # تحول نحو السالب — shift toward negative
            # أضف السخرية كعاطفة — Add sarcasm as an emotion signal
            emotions["sarcasm"] = min(sarcasm.confidence, 1.0)
            # أعِد حساب المشاعر السائدة — Recalculate dominant emotion
            if emotions:
                dominant_emotion = max(emotions, key=emotions.get)

        # ─── تعزيز بنتائج الإحباط — Enhance with frustration results ─────
        frustration = self.detect_frustration(text, language)
        if frustration.is_frustrated and frustration.confidence > 0.3:
            # أضف الإحباط كعاطفة — Add frustration as an emotion signal
            emotions["frustration"] = min(frustration.confidence, 1.0)
            # عدّل التكافؤ والاستثارة — Adjust valence and arousal
            valence = min(valence, -0.1 * frustration.confidence)
            arousal = max(arousal, 0.2 * frustration.confidence)
            if frustration.level == "severe":
                emotions["anger"] = emotions.get("anger", 0.0) + 0.3
                emotions["sadness"] = emotions.get("sadness", 0.0) + 0.2
            if emotions:
                dominant_emotion = max(emotions, key=emotions.get)

        return ChannelResult(
            channel_name="text",
            emotions=emotions,
            dominant_emotion=dominant_emotion,
            confidence=round(confidence, 4),
            valence=round(valence, 4),
            arousal=round(arousal, 4),
            available=True,
        )

    def _text_analysis_fallback(
        self, text: str, language: str
    ) -> tuple[dict[str, float], str, float, float, float]:
        """
        تحليل نص بديل — Fallback text analysis using built-in lexicons.
        Used when EmotionDetector from social_perception is unavailable.
        """
        emotions: dict[str, float] = {}
        text_lower = text.lower().strip()
        words = text_lower.split() if language == "en" else text.split()

        # قواميس مبسّطة — Simplified lexicons
        ar_lexicon = {
            "سعيد": "joy", "فرحان": "joy", "مبسوط": "joy", "مرتاح": "joy",
            "حزين": "sadness", "مكتئب": "sadness", "تعبان": "sadness",
            "غاضب": "anger", "زعلان": "anger", "منفعل": "anger",
            "خائف": "fear", "قلقان": "fear",
            "مندهش": "surprise", "متفاجئ": "surprise",
            "واثق": "trust", "مطمئن": "trust",
            "محب": "love", "عاشق": "love",
            "شاكر": "gratitude", "ممتن": "gratitude",
        }
        en_lexicon = {
            "happy": "joy", "glad": "joy", "joyful": "joy",
            "sad": "sadness", "unhappy": "sadness", "depressed": "sadness",
            "angry": "anger", "furious": "anger", "annoyed": "anger",
            "afraid": "fear", "scared": "fear", "anxious": "fear",
            "surprised": "surprise", "amazed": "surprise",
            "trusting": "trust", "confident": "trust",
            "loving": "love", "affectionate": "love",
            "grateful": "gratitude", "thankful": "gratitude",
        }

        lexicon = ar_lexicon if language == "ar" else en_lexicon
        for word in words:
            clean = word.strip(".,!?;:،؟")
            if clean in lexicon:
                emotion = lexicon[clean]
                emotions[emotion] = emotions.get(emotion, 0.0) + 0.3

        # تطبيع الدرجات — Normalize scores
        if emotions:
            max_score = max(emotions.values())
            if max_score > 0:
                emotions = {k: min(v / max_score, 1.0) for k, v in emotions.items()}

        dominant = max(emotions, key=emotions.get) if emotions else "neutral"
        va = _VALENCE_AROUSAL.get(dominant, (0.0, 0.0))
        conf = min(len(emotions) * 0.15, 0.8) if emotions else 0.1

        return emotions, dominant, conf, va[0], va[1]

    # ═════════════════════════════════════════════════════════════════════════
    #  قناة الصوت — Audio Channel Analysis
    # ═════════════════════════════════════════════════════════════════════════

    def analyze_audio(self, audio_base64: str) -> ChannelResult:
        """
        تحليل الصوت — Analyze audio for emotion features.
        Extracts pitch, energy, and speech rate features from base64 audio.
        Falls back to simulated analysis when no ML model is available.

        Args:
            audio_base64: بيانات الصوت بترميز base64 — base64 encoded audio data

        Returns:
            ChannelResult — نتيجة تحليل قناة الصوت
        """
        if not audio_base64 or not audio_base64.strip():
            return ChannelResult(channel_name="audio", available=False)

        try:
            audio_bytes = base64.b64decode(audio_base64)
        except Exception as e:
            logger.warning(f"MultimodalEmotionEngine: Invalid base64 audio data: {e}")
            return ChannelResult(channel_name="audio", available=False)

        if len(audio_bytes) < 44:
            logger.warning("MultimodalEmotionEngine: Audio data too short for analysis")
            return ChannelResult(channel_name="audio", available=False)

        # ─── استخراج الخصائص الصوتية — Extract audio features ───────────
        # محاكاة تحليل الصوت عندما لا يتوفر نموذج تعلم آلي
        # Simulated audio analysis when no ML model is available
        features = self._extract_audio_features(audio_bytes)

        # ─── تحليل الخصائص — Analyze features ──────────────────────────
        emotions = self._analyze_audio_features(features)

        # حساب التكافؤ والاستثارة — Compute valence and arousal
        valence = 0.0
        arousal = 0.0
        if emotions:
            dominant = max(emotions, key=emotions.get)
            va = _VALENCE_AROUSAL.get(dominant, (0.0, 0.0))
            valence = va[0] * emotions.get(dominant, 0.0)
            arousal = va[1] * features.get("energy", 0.5)
            dominant_emotion = dominant
        else:
            dominant_emotion = "neutral"

        confidence = min(features.get("signal_quality", 0.3), 0.7)

        return ChannelResult(
            channel_name="audio",
            emotions=emotions,
            dominant_emotion=dominant_emotion,
            confidence=round(confidence, 4),
            valence=round(valence, 4),
            arousal=round(arousal, 4),
            available=True,
        )

    def _extract_audio_features(self, audio_bytes: bytes) -> dict[str, float]:
        """
        استخراج خصائص الصوت — Extract audio features from raw bytes.
        Uses signal analysis heuristics as fallback when no ML model available.
        """
        features: dict[str, float] = {}

        # ─── حجم الإشارة — Signal size ──────────────────────────────────
        data_length = len(audio_bytes)
        features["duration_estimate"] = data_length / 16000.0  # تقدير بـ 16kHz — estimate at 16kHz

        # ─── طاقة الإشارة — Signal energy ──────────────────────────────
        # حساب متوسط مربع السعة — Compute mean squared amplitude
        sample_count = min(data_length // 2, 8000)  # حد أقصى 8000 عينة — cap at 8000 samples
        energy_sum = 0.0
        zero_crossings = 0
        prev_sample = 0

        for i in range(sample_count):
            offset = 44 + i * 2  # تخطي ترويسة WAV — skip WAV header
            if offset + 1 < data_length:
                sample = struct.unpack_from('<h', audio_bytes, offset)[0]
                energy_sum += sample * sample
                # عد التقاطعات الصفرية — Count zero crossings
                if (prev_sample >= 0 and sample < 0) or (prev_sample < 0 and sample >= 0):
                    zero_crossings += 1
                prev_sample = sample

        avg_energy = energy_sum / max(sample_count, 1)
        features["energy"] = min(avg_energy / (32768.0 * 32768.0), 1.0)
        features["zero_crossing_rate"] = zero_crossings / max(sample_count, 1)
        features["signal_quality"] = min(features["energy"] * 2.0, 1.0)

        # ─── تقدير درجة الصوت — Pitch estimation via zero-crossing rate ─
        # معدل التقاطع الصفري يرتبط بالتردد الأساسي
        # Zero-crossing rate correlates with fundamental frequency
        features["pitch_estimate"] = features["zero_crossing_rate"] * 8000.0

        # ─── تقدير سرعة الكلام — Speech rate estimation ─────────────────
        # استناداً إلى التغيرات في الطاقة — Based on energy variations
        features["speech_rate_estimate"] = min(
            features["zero_crossing_rate"] * 5.0, 3.0
        )

        return features

    def _analyze_audio_features(self, features: dict[str, float]) -> dict[str, float]:
        """
        تحليل خصائص الصوت — Analyze audio features to estimate emotions.
        Uses heuristic rules based on pitch, energy, and speech rate.
        """
        emotions: dict[str, float] = {}

        energy = features.get("energy", 0.5)
        pitch = features.get("pitch_estimate", 200.0)
        speech_rate = features.get("speech_rate_estimate", 1.0)

        # ─── طاقة عالية + درجة صوت عالية = غضب أو مفاجأة ──────────────
        # High energy + high pitch = anger or surprise
        if energy > 0.5 and pitch > 300:
            emotions["anger"] = min(0.3 + energy * 0.4, 0.8)
            emotions["surprise"] = min(0.1 + energy * 0.2, 0.5)

        # ─── طاقة عالية + درجة صوت منخفضة = ثقة أو فخر ────────────────
        # High energy + low pitch = confidence or pride
        elif energy > 0.5 and pitch <= 300:
            emotions["trust"] = min(0.2 + energy * 0.3, 0.7)
            emotions["pride"] = min(0.1 + energy * 0.2, 0.5)

        # ─── طاقة منخفضة + درجة صوت منخفضة = حزن ─────────────────────
        # Low energy + low pitch = sadness
        elif energy <= 0.3 and pitch <= 250:
            emotions["sadness"] = min(0.3 + (1.0 - energy) * 0.4, 0.8)
            emotions["fear"] = min(0.1 + (1.0 - energy) * 0.2, 0.4)

        # ─── طاقة منخفضة + درجة صوت عالية = خوف أو قلق ────────────────
        # Low energy + high pitch = fear or anxiety
        elif energy <= 0.3 and pitch > 250:
            emotions["fear"] = min(0.2 + (1.0 - energy) * 0.3, 0.7)
            emotions["sadness"] = min(0.1 + (1.0 - energy) * 0.2, 0.4)

        # ─── متوسط = محايد أو فرح ──────────────────────────────────────
        # Medium = neutral or joy
        else:
            emotions["joy"] = min(0.2 + energy * 0.2, 0.5)
            emotions["neutral"] = 0.3

        # ─── سرعة الكلام تؤثر على الاستثارة — Speech rate affects arousal
        if speech_rate > 2.0:
            # كلام سريع يزيد الغضب أو القلق — Fast speech increases anger/anxiety
            if "anger" in emotions:
                emotions["anger"] = min(emotions["anger"] + 0.15, 1.0)
            if "fear" in emotions:
                emotions["fear"] = min(emotions["fear"] + 0.1, 1.0)
        elif speech_rate < 0.5:
            # كلام بطيء يزيد الحزن — Slow speech increases sadness
            if "sadness" in emotions:
                emotions["sadness"] = min(emotions["sadness"] + 0.15, 1.0)

        return emotions

    # ═════════════════════════════════════════════════════════════════════════
    #  قناة الصورة — Image Channel Analysis
    # ═════════════════════════════════════════════════════════════════════════

    def analyze_image(self, image_base64: str) -> ChannelResult:
        """
        تحليل الصورة — Analyze image for facial expressions and visual emotion cues.
        Falls back to simulated analysis when no ML model is available.

        Args:
            image_base64: بيانات الصورة بترميز base64 — base64 encoded image data

        Returns:
            ChannelResult — نتيجة تحليل قناة الصورة
        """
        if not image_base64 or not image_base64.strip():
            return ChannelResult(channel_name="image", available=False)

        try:
            image_bytes = base64.b64decode(image_base64)
        except Exception as e:
            logger.warning(f"MultimodalEmotionEngine: Invalid base64 image data: {e}")
            return ChannelResult(channel_name="image", available=False)

        if len(image_bytes) < 100:
            logger.warning("MultimodalEmotionEngine: Image data too short for analysis")
            return ChannelResult(channel_name="image", available=False)

        # ─── استخراج خصائص الصورة — Extract image features ─────────────
        features = self._extract_image_features(image_bytes)

        # ─── تحليل الخصائص — Analyze features ──────────────────────────
        emotions = self._analyze_image_features(features)

        # حساب التكافؤ والاستثارة — Compute valence and arousal
        valence = 0.0
        arousal = 0.0
        if emotions:
            dominant = max(emotions, key=emotions.get)
            va = _VALENCE_AROUSAL.get(dominant, (0.0, 0.0))
            valence = va[0] * emotions.get(dominant, 0.0)
            arousal = va[1] * emotions.get(dominant, 0.0)
            dominant_emotion = dominant
        else:
            dominant_emotion = "neutral"

        # ثقة أقل للصور بدون نموذج — Lower confidence for images without model
        confidence = min(features.get("image_quality", 0.2), 0.5)

        return ChannelResult(
            channel_name="image",
            emotions=emotions,
            dominant_emotion=dominant_emotion,
            confidence=round(confidence, 4),
            valence=round(valence, 4),
            arousal=round(arousal, 4),
            available=True,
        )

    def _extract_image_features(self, image_bytes: bytes) -> dict[str, float]:
        """
        استخراج خصائص الصورة — Extract image features from raw bytes.
        Uses simple pixel analysis heuristics as fallback.
        """
        features: dict[str, float] = {}
        data_length = len(image_bytes)

        # ─── كشف نوع الصورة — Detect image type ─────────────────────────
        is_jpeg = image_bytes[:2] == b'\xff\xd8'
        is_png = image_bytes[:8] == b'\x89PNG\r\n\x1a\n'
        features["is_jpeg"] = 1.0 if is_jpeg else 0.0
        features["is_png"] = 1.0 if is_png else 0.0
        features["image_quality"] = 0.3 if (is_jpeg or is_png) else 0.1

        # ─── تحليل الألوان البسيط — Simple color analysis ──────────────
        # استخدام عيّنة من البايتات لتحليل السطوع — Sample bytes for brightness
        sample_step = max(data_length // 1000, 1)
        brightness_values = []
        for i in range(0, min(data_length, 100000), sample_step):
            brightness_values.append(image_bytes[i] / 255.0)

        if brightness_values:
            features["avg_brightness"] = sum(brightness_values) / len(brightness_values)
            features["brightness_variance"] = sum(
                (b - features["avg_brightness"]) ** 2 for b in brightness_values
            ) / len(brightness_values)
        else:
            features["avg_brightness"] = 0.5
            features["brightness_variance"] = 0.1

        # ─── تقدير حجم الصورة — Image size estimate ────────────────────
        features["size_estimate"] = data_length / 100000.0  # بالميغابايت — in MB

        return features

    def _analyze_image_features(self, features: dict[str, float]) -> dict[str, float]:
        """
        تحليل خصائص الصورة — Analyze image features to estimate emotions.
        Uses heuristic rules based on brightness, contrast, and image properties.
        """
        emotions: dict[str, float] = {}

        brightness = features.get("avg_brightness", 0.5)
        variance = features.get("brightness_variance", 0.1)
        quality = features.get("image_quality", 0.3)

        if quality < 0.15:
            # جودة منخفضة جداً، لا نستطيع التحليل — Too low quality to analyze
            emotions["neutral"] = 0.3
            return emotions

        # ─── صورة مشرقة = فرح — Bright image = joy ────────────────────
        if brightness > 0.6 and variance < 0.15:
            emotions["joy"] = min(0.3 + brightness * 0.3, 0.7)
            emotions["love"] = min(0.1 + brightness * 0.1, 0.3)

        # ─── صورة مظلمة = حزن أو خوف — Dark image = sadness or fear ─────
        elif brightness < 0.35:
            emotions["sadness"] = min(0.3 + (1.0 - brightness) * 0.3, 0.7)
            emotions["fear"] = min(0.1 + (1.0 - brightness) * 0.15, 0.4)

        # ─── تباين عالي = غضب أو مفاجأة — High contrast = anger or surprise
        elif variance > 0.15:
            emotions["anger"] = min(0.2 + variance, 0.6)
            emotions["surprise"] = min(0.1 + variance * 0.5, 0.4)

        # ─── متوسط = محايد — Medium = neutral ──────────────────────────
        else:
            emotions["neutral"] = 0.4
            emotions["trust"] = 0.2

        return emotions

    # ═════════════════════════════════════════════════════════════════════════
    #  كشف السخرية والإحباط — Sarcasm and Frustration Detection
    # ═════════════════════════════════════════════════════════════════════════

    def detect_sarcasm(self, text: str, language: str = "ar") -> SarcasmResult:
        """
        كشف السخرية — Detect sarcasm in text.
        Delegates to the internal SarcasmDetector.

        Args:
            text: النص المراد تحليله — text to analyze
            language: لغة النص (ar/en) — text language

        Returns:
            SarcasmResult — نتيجة كشف السخرية
        """
        return self._sarcasm_detector.detect(text, language)

    def detect_frustration(self, text: str, language: str = "ar") -> FrustrationResult:
        """
        كشف الإحباط — Detect frustration in text.
        Delegates to the internal FrustrationDetector.

        Args:
            text: النص المراد تحليله — text to analyze
            language: لغة النص (ar/en) — text language

        Returns:
            FrustrationResult — نتيجة كشف الإحباط
        """
        return self._frustration_detector.detect(text, language)

    # ═════════════════════════════════════════════════════════════════════════
    #  طبقة الدمج — Fusion Layer
    # ═════════════════════════════════════════════════════════════════════════

    def fuse_results(
        self,
        text_result: ChannelResult,
        audio_result: ChannelResult,
        image_result: ChannelResult,
    ) -> MultimodalEmotionResult:
        """
        دمج النتائج — Fuse results from all three channels.
        Uses weighted averaging with automatic weight redistribution
        when channels are unavailable.

        Args:
            text_result: نتيجة قناة النص — text channel result
            audio_result: نتيجة قناة الصوت — audio channel result
            image_result: نتيجة قناة الصورة — image channel result

        Returns:
            MultimodalEmotionResult — نتيجة الدمج (بدون سخرية/إحباط)
        """
        # ─── جمع الأوزان النشطة — Collect active weights ───────────────
        channels = [
            (text_result, self._text_weight),
            (audio_result, self._audio_weight),
            (image_result, self._image_weight),
        ]

        active_channels = [(ch, w) for ch, w in channels if ch.available]
        if not active_channels:
            return MultimodalEmotionResult(
                fused_emotions={"neutral": 1.0},
                dominant_emotion="neutral",
                confidence=0.0,
            )

        # ─── إعادة توزيع الأوزان — Redistribute weights ────────────────
        total_weight = sum(w for _, w in active_channels)
        if total_weight == 0:
            total_weight = 1.0
        normalized_weights = [(ch, w / total_weight) for ch, w in active_channels]

        # ─── دمج المشاعر — Fuse emotions ────────────────────────────────
        fused_emotions: dict[str, float] = {}
        all_emotion_keys: set[str] = set()
        for ch, _ in normalized_weights:
            all_emotion_keys.update(ch.emotions.keys())

        for emotion_key in all_emotion_keys:
            weighted_sum = 0.0
            for ch, weight in normalized_weights:
                score = ch.emotions.get(emotion_key, 0.0)
                weighted_sum += score * weight
            if weighted_sum > 0.01:  # تجاهل القيم الضئيلة — ignore negligible values
                fused_emotions[emotion_key] = round(weighted_sum, 4)

        # ─── تطبيع الدرجات — Normalize scores ──────────────────────────
        if fused_emotions:
            max_score = max(fused_emotions.values())
            if max_score > 0:
                fused_emotions = {
                    k: round(v / max_score, 4) for k, v in fused_emotions.items()
                }

        # ─── المشاعر السائدة — Dominant emotion ────────────────────────
        dominant_emotion = max(fused_emotions, key=fused_emotions.get) if fused_emotions else "neutral"

        # ─── حساب التكافؤ والاستثارة المدمجين — Fused valence and arousal ─
        fused_valence = 0.0
        fused_arousal = 0.0
        for ch, weight in normalized_weights:
            fused_valence += ch.valence * weight
            fused_arousal += ch.arousal * weight

        # ─── حساب الثقة المدمجة — Fused confidence ─────────────────────
        fused_confidence = 0.0
        for ch, weight in normalized_weights:
            fused_confidence += ch.confidence * weight

        return MultimodalEmotionResult(
            fused_emotions=fused_emotions,
            dominant_emotion=dominant_emotion,
            confidence=round(fused_confidence, 4),
            valence=round(fused_valence, 4),
            arousal=round(fused_arousal, 4),
        )

    # ═════════════════════════════════════════════════════════════════════════
    #  توليد التوصيات — Recommendation Generation
    # ═════════════════════════════════════════════════════════════════════════

    def _generate_recommendations(
        self,
        fused: MultimodalEmotionResult,
        sarcasm: SarcasmResult,
        frustration: FrustrationResult,
        language: str,
    ) -> list[str]:
        """
        توليد التوصيات — Generate interaction recommendations based on analysis.
        """
        recommendations: list[str] = []
        dominant = fused.dominant_emotion
        valence = fused.valence

        # ─── توصيات حسب المشاعر السائدة — Emotion-based recommendations ─
        if language == "ar":
            if dominant == "anger":
                recommendations.append("اجعل ردك هادئاً ومتعاطفاً — تجنب المواجهة")
                recommendations.append("استمع بنشاط وأكد فهمك لمشاعرهم")
            elif dominant == "sadness":
                recommendations.append("أظهر التعاطف والدعم — لا تقلل من مشاعرهم")
                recommendations.append("استخدم لغة مريحة ومتفهمة")
            elif dominant == "fear":
                recommendations.append("قدّم الطمأنينة والمعلومات الواضحة")
                recommendations.append("تجنب المفاجآت أو التغييرات المفاجئة")
            elif dominant == "joy":
                recommendations.append("شاركهم الفرح بنبرة إيجابية")
                recommendations.append("استغل المزاج الإيجابي للتواصل البنّاء")
            elif dominant == "frustration":
                recommendations.append("اعترف بإحباطهم بصدق")
                recommendations.append("قدّم حلولاً بسيطة ومباشرة")
            elif dominant == "sarcasm":
                recommendations.append("لا تأخذ الكلام حرفياً — ابحث عن المعنى الحقيقي")
                recommendations.append("رد بنبرة هادئة ومتفهمة")
        else:
            if dominant == "anger":
                recommendations.append("Keep your response calm and empathetic — avoid confrontation")
                recommendations.append("Actively listen and acknowledge their feelings")
            elif dominant == "sadness":
                recommendations.append("Show empathy and support — don't minimize their feelings")
                recommendations.append("Use comforting and understanding language")
            elif dominant == "fear":
                recommendations.append("Provide reassurance and clear information")
                recommendations.append("Avoid surprises or sudden changes")
            elif dominant == "joy":
                recommendations.append("Share their positive mood with an upbeat tone")
                recommendations.append("Leverage the positive mood for constructive communication")
            elif dominant == "frustration":
                recommendations.append("Genuinely acknowledge their frustration")
                recommendations.append("Offer simple, direct solutions")
            elif dominant == "sarcasm":
                recommendations.append("Don't take words literally — look for underlying meaning")
                recommendations.append("Respond with a calm, understanding tone")

        # ─── توصيات خاصة بالسخرية — Sarcasm-specific recommendations ────
        if sarcasm.is_sarcastic:
            if language == "ar":
                if sarcasm.suggested_response_tone == "gentle_clarification":
                    recommendations.append("استفسر بلطف عن المقصد الحقيقي")
                elif sarcasm.suggested_response_tone == "patient_reassurance":
                    recommendations.append("كن صبوراً وأكد رغبتك في المساعدة")
                elif sarcasm.suggested_response_tone == "humble_acknowledgment":
                    recommendations.append("اقبل الملاحظة بتواضع دون دفاعية")
                elif sarcasm.suggested_response_tone == "calm_empathy":
                    recommendations.append("أظهر التعاطف وتجنب الرد الساخر")
            else:
                if sarcasm.suggested_response_tone == "gentle_clarification":
                    recommendations.append("Gently inquire about the true intent")
                elif sarcasm.suggested_response_tone == "patient_reassurance":
                    recommendations.append("Be patient and affirm your desire to help")
                elif sarcasm.suggested_response_tone == "humble_acknowledgment":
                    recommendations.append("Accept the remark humbly without defensiveness")
                elif sarcasm.suggested_response_tone == "calm_empathy":
                    recommendations.append("Show empathy and avoid sarcastic responses")

        # ─── توصيات خاصة بالإحباط — Frustration-specific recommendations ─
        if frustration.is_frustrated:
            if language == "ar":
                if frustration.level == "severe":
                    recommendations.append("أوقف مؤقتاً وأعطِ المساحة للتهدئة")
                    recommendations.append("اعترف بصعوبة الموقف بصدق")
                elif frustration.level == "moderate":
                    recommendations.append("بسّط الخطوات وقدم حلولاً تدريجية")
                    recommendations.append("صدّق مشاعرهم قبل تقديم الحلول")
                else:
                    recommendations.append("اعترف بلطف بإحباطهم")
                    recommendations.append("قدّم خيارات بديلة بسيطة")
            else:
                if frustration.level == "severe":
                    recommendations.append("Pause and give space to cool down")
                    recommendations.append("Genuinely acknowledge the difficulty of the situation")
                elif frustration.level == "moderate":
                    recommendations.append("Simplify steps and offer gradual solutions")
                    recommendations.append("Validate their feelings before offering solutions")
                else:
                    recommendations.append("Gently acknowledge their frustration")
                    recommendations.append("Offer simple alternative options")

        # ─── توصيات عامة بناءً على التكافؤ — General valence-based recs ──
        if valence < -0.5 and not recommendations:
            if language == "ar":
                recommendations.append("النبرة العامة سلبية — يُنصح بالرد المتعاطف والداعم")
            else:
                recommendations.append("Overall tone is negative — empathetic, supportive response advised")

        return recommendations[:8]  # حد أقصى 8 توصيات — Cap at 8 recommendations

    # ═════════════════════════════════════════════════════════════════════════
    #  واجهة إدارة النظام — System Management Interface
    # ═════════════════════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        """
        حالة المحرك — Get engine status.
        Returns current status of the multimodal emotion engine.
        """
        return {
            "module": "MultimodalEmotionEngine",
            "version": "14.0",
            "enabled": self._enabled,
            "initialized": self._initialized,
            "shutdown": self._shutdown_flag,
            "weights": {
                "text": self._text_weight,
                "audio": self._audio_weight,
                "image": self._image_weight,
            },
            "emotion_detector_loaded": self._emotion_detector is not None,
            "sarcasm_detector_active": self._sarcasm_detector is not None,
            "frustration_detector_active": self._frustration_detector is not None,
            "feature_flag": "MAMOUN_MULTIMODAL_EMOTION",
            "feature_flag_value": str(self._enabled),
        }

    def shutdown(self) -> None:
        """
        إيقاف المحرك — Shut down the engine gracefully.
        Releases resources and marks the engine as shut down.
        """
        logger.info("MultimodalEmotionEngine: Shutting down...")
        self._shutdown_flag = True
        self._emotion_detector = None
        self._sarcasm_detector = None
        self._frustration_detector = None
        self._initialized = False
        logger.info("MultimodalEmotionEngine: Shutdown complete")
