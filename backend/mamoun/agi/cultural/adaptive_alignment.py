"""
BABSHARQII v10.0 — Adaptive Cultural Alignment Engine
محرك المحاذاة الثقافية التكيفية — يكتشف ثقافة المستخدم ويضبط الردود ديناميكياً

Detects user culture from conversation context and adapts
the moral filter dynamically. Supports 5 cultures:
Arabic/Islamic, East Asian, African, South Asian, Latin American.

Feature Flag: MAMOUN_CULTURAL_ADAPTIVE (default: false)
"""

from __future__ import annotations

import os
import yaml
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CULTURAL_ADAPTIVE_ENABLED: bool = os.environ.get(
    "MAMOUN_CULTURAL_ADAPTIVE", "false"
).lower() in ("true", "1", "yes")


@dataclass
class CultureDetectionResult:
    """نتيجة كشف الثقافة"""
    detected_culture: str = "arabic_islamic"
    confidence: float = 0.0
    language_clues: list[str] = field(default_factory=list)
    cultural_clues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "detected_culture": self.detected_culture,
            "confidence": round(self.confidence, 4),
            "language_clues": self.language_clues,
            "cultural_clues": self.cultural_clues,
        }


# Culture detection patterns
CULTURE_INDICATORS = {
    "arabic_islamic": {
        "language": ["العربية", "عربي", "سلام", "الحمد", "إن شاء", "يا أخي", "جزاك"],
        "cultural": ["ضيافة", "إسلام", "قرآن", "صلاة", "رمضان", "حلال", "حرام"],
        "greetings": ["السلام عليكم", "أهلاً وسهلاً", "مرحبا"],
    },
    "east_asian": {
        "language": ["こんにちは", "안녕하세요", "你好", "さん", "せんせい", "先生"],
        "cultural": ["harmony", "wa", "和", "insam", "sensei", "guanxi"],
        "greetings": ["konnichiwa", "annyeonghaseyo", "nihao"],
    },
    "african": {
        "language": ["jambo", "sawubona", "ubuntu", "asante", "habari"],
        "cultural": ["ubuntu", "community", "ancestors", "proverb", "griot"],
        "greetings": ["jambo", "sawubona", "habari"],
    },
    "south_asian": {
        "language": ["नमस्ते", "namaste", "ji", "acha", "theek", "shukriya"],
        "cultural": ["dharma", "karma", "temple", "mosque", "family duty", "atithi"],
        "greetings": ["namaste", "sat sri akal", "vanakkam"],
    },
    "latin_american": {
        "language": ["hola", "buenos", "amigo", "familia", "gracias", "por favor"],
        "cultural": ["familismo", "simpatia", "fiesta", "carnaval", "tango"],
        "greetings": ["hola", "buenos dias", "que tal"],
    },
}


class AdaptiveAlignmentEngine:
    """
    محرك المحاذاة الثقافية التكيفية
    
    Detects user culture and adapts responses:
    1. Analyze message for language and cultural indicators
    2. Load culture-specific values from values_multi_culture.yaml
    3. Apply cultural filter to response
    """

    def __init__(self, values_path: Optional[str] = None):
        if values_path is None:
            values_path = str(
                Path(__file__).parent / "values_multi_culture.yaml"
            )
        self._values_path = values_path
        self._values_cache: Optional[dict] = None
        self._detection_count = 0

    def detect_culture(
        self, user_message: str, conversation_context: Optional[dict] = None
    ) -> CultureDetectionResult:
        """
        كشف ثقافة المستخدم من رسالته.
        """
        if not CULTURAL_ADAPTIVE_ENABLED:
            return CultureDetectionResult(
                detected_culture="arabic_islamic",
                confidence=1.0,
                language_clues=["default"],
            )

        self._detection_count += 1
        message_lower = user_message.lower()

        # Score each culture
        scores: dict[str, float] = {}
        clues: dict[str, dict] = {}

        for culture_id, indicators in CULTURE_INDICATORS.items():
            score = 0.0
            lang_clues = []
            cult_clues = []

            for kw in indicators.get("language", []):
                if kw.lower() in message_lower:
                    score += 2.0
                    lang_clues.append(kw)

            for kw in indicators.get("cultural", []):
                if kw.lower() in message_lower:
                    score += 1.5
                    cult_clues.append(kw)

            for kw in indicators.get("greetings", []):
                if kw.lower() in message_lower:
                    score += 3.0
                    lang_clues.append(kw)

            scores[culture_id] = score
            clues[culture_id] = {
                "language": lang_clues,
                "cultural": cult_clues,
            }

        # Find best culture
        if not scores or max(scores.values()) == 0:
            return CultureDetectionResult(
                detected_culture="arabic_islamic",
                confidence=0.3,
                language_clues=["no_specific_indicators"],
            )

        best_culture = max(scores, key=lambda k: scores[k])
        best_score = scores[best_culture]
        total_score = sum(scores.values())

        confidence = best_score / total_score if total_score > 0 else 0.3
        confidence = min(0.95, confidence)

        return CultureDetectionResult(
            detected_culture=best_culture,
            confidence=confidence,
            language_clues=clues[best_culture]["language"],
            cultural_clues=clues[best_culture]["cultural"],
        )

    def load_culture_values(self, culture_id: str) -> dict:
        """حمّل قيم ثقافة محددة من YAML"""
        if self._values_cache is None:
            self._values_cache = self._load_yaml()

        if self._values_cache and culture_id in self._values_cache.get("cultures", {}):
            return self._values_cache["cultures"][culture_id]

        return {}

    def apply_cultural_filter(self, response_text: str, culture_id: str) -> str:
        """
        طبّق مرشح ثقافي على الرد.
        """
        if not CULTURAL_ADAPTIVE_ENABLED:
            return response_text

        values = self.load_culture_values(culture_id)
        if not values:
            return response_text

        modified = response_text
        forbidden = values.get("forbidden_topics", [])

        # Check for forbidden topics
        for topic in forbidden:
            if topic.lower() in modified.lower():
                # Add a caution note
                modified = f"⚠️ يُحذّر من ذكر هذا الموضوع في بعض الثقافات: {modified}"

        # Add cultural greeting if appropriate
        greetings = values.get("preferred_greetings", [])
        if greetings and not any(g in modified for g in greetings):
            # Don't force greetings, just note availability
            pass

        # Culture-specific adjustments
        if culture_id == "arabic_islamic":
            # Emphasize community, avoid individualistic framing
            if "فرد" in modified and "مجتمع" not in modified:
                modified = modified.replace("فرد", "فرد في المجتمع")

        elif culture_id == "east_asian":
            # Soften directness, emphasize harmony
            pass  # Already handled by tone

        elif culture_id == "african":
            # Emphasize community
            pass

        elif culture_id == "south_asian":
            # Respect spiritual references
            pass

        elif culture_id == "latin_american":
            # Warm, family-oriented
            pass

        return modified

    def get_supported_cultures(self) -> list[str]:
        """احصل على قائمة الثقافات المدعومة"""
        return list(CULTURE_INDICATORS.keys())

    def _load_yaml(self) -> dict:
        """حمّل ملف القيم"""
        try:
            with open(self._values_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load multi-culture values: {e}")
            return {}

    @property
    def stats(self) -> dict:
        """إحصائيات المحرك"""
        return {
            "total_detections": self._detection_count,
            "supported_cultures": self.get_supported_cultures(),
            "enabled": CULTURAL_ADAPTIVE_ENABLED,
        }
