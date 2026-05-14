"""
BABSHARQII (Mamoun) v40.0 — AGI Social Perception Engine
محرك الإدراك الاجتماعي لطبقة AGI — القدرة على إدراك وتفسير الاستجابات للإشارات الاجتماعية والمشاعر وديناميكيات المجموعة

Implements a comprehensive Social Perception system for AGI-level social
cognition, complementing Theory of Mind by focusing on real-time perception
and interpretation rather than deep mental modeling.

Social Perception is the ability to:
  • Detect and interpret emotions from linguistic cues (Arabic + English)
  • Analyze social context: formality, power dynamics, group identity
  • Track conversational dynamics: turn-taking, engagement, topic shifts
  • Evaluate adherence to social norms (Arab/Islamic + universal)
  • Provide culturally-aware recommendations for social interaction

Inspired by:
  • Social Intelligence Theory (Bar-On, 2006) — understanding and managing
    people through situational awareness
  • Affective Computing (Picard, 1997) — emotion recognition and response
  • Intercultural Communication (Hall, 1976; Hofstede, 1980) — high-context
    vs low-context cultures, power distance in social interaction
  • Arab/Islamic social ethics: Adab (أدب), Ihsan (إحسان), Birr (بر),
    Silat al-Rahm (صلة الرحم), Karam (كرم), Diyafa (ضيافة)

Architecture:
  ┌────────────────────────────────────────────────────────────────────────┐
  │                     SocialPerceptionEngine                             │
  │                                                                        │
  │  ┌──────────────────────┐  ┌────────────────────────────────────────┐ │
  │  │ EmotionDetector      │  │ SocialContextAnalyzer                  │ │
  │  │ (Arabic/English      │  │ (formality, power dynamics,           │ │
  │  │  emotion lexicons,   │  │  group identity, cultural markers)    │ │
  │  │  valence-arousal)    │  │                                       │ │
  │  └──────────┬───────────┘  └──────────────┬─────────────────────────┘ │
  │             │                             │                            │
  │  ┌──────────▼─────────────────────────────▼────────────────────────┐ │
  │  │            ConversationalDynamicsTracker                        │ │
  │  │  (turn-taking patterns, conversational leads, engagement,      │ │
  │  │   topic shifts, flow analysis)                                 │ │
  │  └──────────────────────────┬─────────────────────────────────────┘ │
  │                             │                                        │
  │  ┌──────────────────────────▼─────────────────────────────────────┐ │
  │  │            SocialNormEvaluator                                  │ │
  │  │  (politeness, respect, appropriateness; Arab/Islamic norms:    │ │
  │  │   hospitality, elder respect, honorifics; universal norms:     │ │
  │  │   empathy, active listening, inclusivity)                      │ │
  │  └────────────────────────────────────────────────────────────────┘ │
  └────────────────────────────────────────────────────────────────────────┘

Env toggles:
    MAMOUN_SOCIAL_PERCEPTION_ENABLED — تمكين/تعطيل الإدراك الاجتماعي (الافتراضي: false)
"""

from __future__ import annotations

import os
import re
import time
import math
import logging
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)

# ─── مفاتيح التهيئة البيئية — Environment Config ─────────────────────────────

SOCIAL_PERCEPTION_ENABLED: bool = os.environ.get(
    "MAMOUN_SOCIAL_PERCEPTION_ENABLED", "false"
).lower() in ("true", "1", "yes")


# ═══════════════════════════════════════════════════════════════════════════════
#  التعدادات — Enumerations
# ═══════════════════════════════════════════════════════════════════════════════


class FormalityLevel(str, Enum):
    """
    مستوى الرسمية — مستوى الرسمية في التفاعل الاجتماعي.
    Level of formality in social interaction.
    """
    FORMAL = "formal"              # رسمي — formal/institutional
    SEMI_FORMAL = "semi_formal"    # شبه رسمي — semi-formal/professional
    INFORMAL = "informal"          # غير رسمي — informal/casual
    INTIMATE = "intimate"          # حميم — intimate/familial


class PowerDirection(str, Enum):
    """
    اتجاه القوة — اتجاه ديناميكية القوة في التفاعل.
    Direction of power dynamics in interaction.
    """
    SUPERIOR = "superior"          # المتحدث في موقف أعلى — speaker is superior
    EQUAL = "equal"                # متساوٍ — equal standing
    SUBORDINATE = "subordinate"    # المتحدث في موقف أدنى — speaker is subordinate
    UNCLEAR = "unclear"            # غير واضح — unclear power relation


class EmotionCategory(str, Enum):
    """
    فئة المشاعر — تصنيف المشاعر الأساسية.
    Basic emotion categories following Ekman's model with cultural extensions.
    """
    JOY = "joy"                    # فرح
    SADNESS = "sadness"            # حزن
    ANGER = "anger"                # غضب
    FEAR = "fear"                  # خوف
    SURPRISE = "surprise"          # مفاجأة
    DISGUST = "disgust"            # اشمئزاز
    TRUST = "trust"                # ثقة
    ANTICIPATION = "anticipation"  # ترقب
    LOVE = "love"                  # حب
    SHAME = "shame"                # خجل/حياء
    PRIDE = "pride"                # فخر
    GRATITUDE = "gratitude"        # امتنان
    NEUTRAL = "neutral"            # محايد


class MarkerType(str, Enum):
    """
    نوع العلامة الثقافية — نوع العلامة الثقافية المكتشفة.
    Type of detected cultural marker.
    """
    RELIGIOUS = "religious"              # دينية
    HOSPITALITY = "hospitality"          # ضيافة
    HONORIFIC = "honorific"              # ألقاب/تكريم
    FAMILY = "family"                    # عائلية
    GENDER = "gender"                    # جندرية
    TRIBAL = "tribal"                    # قبلية/عشائرية
    REGIONAL = "regional"                # إقليمية
    ETIQUETTE = "etiquette"              # آداب/إتيكيت
    IDIOMATIC = "idiomatic"              # تعبيرية
    TEMPORAL = "temporal"                # زمنية (رمضان، عيد، إلخ)


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج البيانات — Dataclasses
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ValenceArousal:
    """
    التكافؤ والاستثارة — نموذج التكافؤ-الاستثارة للمشاعر.
    Valence (negative-positive) and Arousal (calm-excited) emotion model.
    """
    valence: float = 0.0    # التكافؤ: سالب (-1) إلى إيجابي (+1)
    arousal: float = 0.0    # الاستثارة: هادئ (-1) إلى مثاب (+1)

    def to_dict(self) -> dict:
        return {
            "valence": round(self.valence, 4),
            "arousal": round(self.arousal, 4),
        }


@dataclass
class EmotionProfile:
    """
    ملف المشاعر — الملف الشامل للمشاعر المكتشفة في النص.
    Comprehensive emotion profile detected from text input.
    """
    emotions: dict[str, float] = field(default_factory=dict)   # {emotion: score}
    dominant_emotion: str = "neutral"                          # المشاعر السائدة
    valence: float = 0.0                                       # التكافؤ الإيجابي/السلبي
    arousal: float = 0.0                                       # الاستثارة الهادئة/المثارة
    confidence: float = 0.0                                    # ثقة الكشف (0-1)

    def to_dict(self) -> dict:
        return {
            "emotions": {k: round(v, 4) for k, v in self.emotions.items()},
            "dominant_emotion": self.dominant_emotion,
            "valence": round(self.valence, 4),
            "arousal": round(self.arousal, 4),
            "confidence": round(self.confidence, 4),
        }


@dataclass
class CulturalMarker:
    """
    علامة ثقافية — علامة ثقافية مكتشفة في النص.
    A cultural marker detected in text, indicating cultural context.
    """
    marker_type: MarkerType = MarkerType.ETIQUETTE   # نوع العلامة
    description: str = ""                             # وصف العلامة
    confidence: float = 0.0                           # ثقة الكشف (0-1)

    def to_dict(self) -> dict:
        return {
            "marker_type": self.marker_type.value,
            "description": self.description,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class PowerDynamics:
    """
    ديناميكية القوة — تقييم ديناميكية القوة بين المشاركين.
    Assessment of power dynamics between participants in interaction.
    """
    direction: PowerDirection = PowerDirection.UNCLEAR  # اتجاه القوة
    score: float = 0.0                                   # درجة القوة (0-1)
    indicators: list[str] = field(default_factory=list)  # مؤشرات القوة

    def to_dict(self) -> dict:
        return {
            "direction": self.direction.value,
            "score": round(self.score, 4),
            "indicators": self.indicators,
        }


@dataclass
class GroupIdentity:
    """
    الهوية الجماعية — الهوية الجماعية المكتشفة في التفاعل.
    Group identity detected in social interaction.
    """
    group_type: str = ""                                # نوع المجموعة
    markers: list[str] = field(default_factory=list)    # علامات الهوية
    in_group_language: bool = False                     # استخدام لغة المجموعة
    solidarity_score: float = 0.0                       # درجة التضامن (0-1)

    def to_dict(self) -> dict:
        return {
            "group_type": self.group_type,
            "markers": self.markers,
            "in_group_language": self.in_group_language,
            "solidarity_score": round(self.solidarity_score, 4),
        }


@dataclass
class SocialContext:
    """
    السياق الاجتماعي — السياق الاجتماعي الشامل للتفاعل.
    Comprehensive social context of an interaction.
    """
    formality: FormalityLevel = FormalityLevel.SEMI_FORMAL   # مستوى الرسمية
    power_dynamics: PowerDynamics = field(default_factory=PowerDynamics)    # ديناميكية القوة
    group_identity: GroupIdentity = field(default_factory=GroupIdentity)    # الهوية الجماعية
    cultural_markers: list[CulturalMarker] = field(default_factory=list)    # العلامات الثقافية

    def to_dict(self) -> dict:
        return {
            "formality": self.formality.value,
            "power_dynamics": self.power_dynamics.to_dict(),
            "group_identity": self.group_identity.to_dict(),
            "cultural_markers": [m.to_dict() for m in self.cultural_markers],
        }


@dataclass
class ConversationTurn:
    """
    دور محادثة — دور واحد في المحادثة.
    A single turn in a conversation.
    """
    speaker: str = ""                # المتحدث
    content: str = ""                # المحتوى
    timestamp: float = 0.0           # الوقت
    emotion: str = "neutral"         # المشاعر

    def to_dict(self) -> dict:
        return {
            "speaker": self.speaker,
            "content": self.content,
            "timestamp": self.timestamp,
            "emotion": self.emotion,
        }


@dataclass
class TurnPattern:
    """
    نمط أدوار الكلام — نمط تناوب الأدوار في المحادثة.
    Pattern of turn-taking in conversation.
    """
    pattern_type: str = "balanced"          # نوع النمط (balanced/dominant/interrupting)
    balance_score: float = 0.5              # درجة التوازن (0-1)
    avg_turn_length: float = 0.0            # متوسط طول الدور

    def to_dict(self) -> dict:
        return {
            "pattern_type": self.pattern_type,
            "balance_score": round(self.balance_score, 4),
            "avg_turn_length": round(self.avg_turn_length, 2),
        }


@dataclass
class LeadEvent:
    """
    حدث قيادة — حدث يُظهر قيادة المحادثة.
    An event indicating conversational leadership.
    """
    speaker: str = ""              # المتحدث القائد
    event_type: str = ""           # نوع القيادة (topic_initiative/question/directive)
    confidence: float = 0.0        # ثقة الكشف

    def to_dict(self) -> dict:
        return {
            "speaker": self.speaker,
            "event_type": self.event_type,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class TopicShift:
    """
    تحول الموضوع — تحول في موضوع المحادثة.
    A detected shift in conversation topic.
    """
    from_topic: str = ""           # الموضوع السابق
    to_topic: str = ""             # الموضوع الجديد
    turn_index: int = 0            # فهرس الدور الذي حدث فيه التحول
    abruptness: float = 0.0        # درجة المفاجأة (0-1)

    def to_dict(self) -> dict:
        return {
            "from_topic": self.from_topic,
            "to_topic": self.to_topic,
            "turn_index": self.turn_index,
            "abruptness": round(self.abruptness, 4),
        }


@dataclass
class DynamicsUpdate:
    """
    تحديث الديناميكيات — تحديث ديناميكيات المحادثة.
    Updated conversational dynamics after tracking a turn.
    """
    engagement: float = 0.0                                # مستوى المشاركة (0-1)
    turn_pattern: TurnPattern = field(default_factory=TurnPattern)     # نمط الأدوار
    leads: list[LeadEvent] = field(default_factory=list)               # أحداث القيادة
    shifts: list[TopicShift] = field(default_factory=list)             # تحولات الموضوع

    def to_dict(self) -> dict:
        return {
            "engagement": round(self.engagement, 4),
            "turn_pattern": self.turn_pattern.to_dict(),
            "leads": [l.to_dict() for l in self.leads],
            "shifts": [s.to_dict() for s in self.shifts],
        }


@dataclass
class PolitenessScore:
    """
    درجة الأدب — درجة الالتزام بقواعد الأدب.
    Score measuring adherence to politeness norms.
    """
    score: float = 0.0                             # الدرجة (0-1)
    indicators: list[str] = field(default_factory=list)    # مؤشرات الأدب
    violations: list[str] = field(default_factory=list)    # انتهاكات الأدب

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 4),
            "indicators": self.indicators,
            "violations": self.violations,
        }


@dataclass
class RespectScore:
    """
    درجة الاحترام — درجة إظهار الاحترام.
    Score measuring respect shown in interaction.
    """
    score: float = 0.0                             # الدرجة (0-1)
    indicators: list[str] = field(default_factory=list)    # مؤشرات الاحترام
    violations: list[str] = field(default_factory=list)    # انتهاكات الاحترام

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 4),
            "indicators": self.indicators,
            "violations": self.violations,
        }


@dataclass
class AppropriatenessScore:
    """
    درجة الملاءمة — درقة ملاءمة الكلام للسياق.
    Score measuring appropriateness of speech in context.
    """
    score: float = 0.0                             # الدرجة (0-1)
    indicators: list[str] = field(default_factory=list)    # مؤشرات الملاءمة
    violations: list[str] = field(default_factory=list)    # انتهاكات الملاءمة

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 4),
            "indicators": self.indicators,
            "violations": self.violations,
        }


@dataclass
class NormEvaluation:
    """
    تقييم المعايير — تقييم شامل للالتزام بالمعايير الاجتماعية.
    Comprehensive evaluation of adherence to social norms.
    """
    politeness: PolitenessScore = field(default_factory=PolitenessScore)        # الأدب
    respect: RespectScore = field(default_factory=RespectScore)                 # الاحترام
    appropriateness: AppropriatenessScore = field(default_factory=AppropriatenessScore)  # الملاءمة
    overall: float = 0.0                            # الدرجة الإجمالية (0-1)
    suggestions: list[str] = field(default_factory=list)    # اقتراحات للتحسين

    def to_dict(self) -> dict:
        return {
            "politeness": self.politeness.to_dict(),
            "respect": self.respect.to_dict(),
            "appropriateness": self.appropriateness.to_dict(),
            "overall": round(self.overall, 4),
            "suggestions": self.suggestions,
        }


@dataclass
class SocialPerceptionResult:
    """
    نتيجة الإدراك الاجتماعي — النتيجة الشاملة لعملية الإدراك الاجتماعي.
    Comprehensive result of social perception analysis.
    """
    emotions: EmotionProfile = field(default_factory=EmotionProfile)         # المشاعر
    social_context: SocialContext = field(default_factory=SocialContext)      # السياق الاجتماعي
    dynamics: DynamicsUpdate = field(default_factory=DynamicsUpdate)          # الديناميكيات
    norms: NormEvaluation = field(default_factory=NormEvaluation)             # المعايير
    recommendations: list[str] = field(default_factory=list)                  # التوصيات

    def to_dict(self) -> dict:
        return {
            "emotions": self.emotions.to_dict(),
            "social_context": self.social_context.to_dict(),
            "dynamics": self.dynamics.to_dict(),
            "norms": self.norms.to_dict(),
            "recommendations": self.recommendations,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج بيانات جديدة — New Data Models (v40.0)
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class SarcasmIndicator:
    """
    مؤشر السخرية — مؤشر على وجود سخرية أو تهكم في النص.
    Indicator for sarcasm/irony detected in text.
    """
    is_sarcastic: bool = False            # هل النص ساخر؟ — is text sarcastic?
    confidence: float = 0.0               # ثقة الكشف (0-1) — detection confidence
    markers_found: list[str] = field(default_factory=list)  # علامات السخرية — sarcasm markers
    pattern_type: str = ""                # نمط السخرية — sarcasm pattern type

    def to_dict(self) -> dict:
        return {
            "is_sarcastic": self.is_sarcastic,
            "confidence": round(self.confidence, 4),
            "markers_found": self.markers_found,
            "pattern_type": self.pattern_type,
        }


@dataclass
class ProsodicIndicators:
    """
    المؤشرات الإعرابية — المؤشرات الصوتية والكتابية التي تدل على النبرة.
    Prosodic and typographic indicators that signal tone and emphasis.
    """
    exclamation_count: int = 0            # عدد علامات التعجب — exclamation mark count
    question_count: int = 0               # عدد علامات الاستفهام — question mark count
    has_all_caps: bool = False            # هل يوجد نص بأحرف كبيرة؟ — ALL CAPS present?
    repeated_chars: int = 0               # عدد الأحرف المكررة — repeated character instances
    repeated_words: list[str] = field(default_factory=list)  # كلمات مكررة — repeated words
    arousal_modifier: float = 0.0         # تعديل الاستثارة — arousal modification factor
    anticipation_modifier: float = 0.0    # تعديل الترقب — anticipation modification factor

    def to_dict(self) -> dict:
        return {
            "exclamation_count": self.exclamation_count,
            "question_count": self.question_count,
            "has_all_caps": self.has_all_caps,
            "repeated_chars": self.repeated_chars,
            "repeated_words": self.repeated_words,
            "arousal_modifier": round(self.arousal_modifier, 4),
            "anticipation_modifier": round(self.anticipation_modifier, 4),
        }


@dataclass
class SocialRole:
    """
    الدور الاجتماعي — الدور الاجتماعي المكتشف للمتحدث.
    Detected social role of the speaker in the conversation.
    """
    role: str = ""                        # الدور — role name
    confidence: float = 0.0              # ثقة الكشف — detection confidence
    markers: list[str] = field(default_factory=list)  # علامات الدور — role markers

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "confidence": round(self.confidence, 4),
            "markers": self.markers,
        }


@dataclass
class ConversationMemoryEntry:
    """
    سجل الذاكرة — سجل واحد في ذاكرة المحادثة.
    A single entry in conversation memory.
    """
    text: str = ""                        # النص — text
    emotion_profile: EmotionProfile = field(default_factory=EmotionProfile)  # المشاعر
    timestamp: float = 0.0               # الوقت — timestamp
    social_role: str = ""                # الدور الاجتماعي — social role

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "emotion_profile": self.emotion_profile.to_dict(),
            "timestamp": round(self.timestamp, 4),
            "social_role": self.social_role,
        }


@dataclass
class EmotionShift:
    """
    تحول المشاعر — تحول في المشاعر بين أدوار المحادثة.
    A detected shift in emotions between conversation turns.
    """
    from_emotion: str = ""               # المشاعر السابقة — previous emotion
    to_emotion: str = ""                 # المشاعر الجديدة — new emotion
    shift_magnitude: float = 0.0         # حجم التحول (0-1) — shift magnitude
    is_sudden: bool = False              # هل التحول مفاجئ؟ — is shift sudden?

    def to_dict(self) -> dict:
        return {
            "from_emotion": self.from_emotion,
            "to_emotion": self.to_emotion,
            "shift_magnitude": round(self.shift_magnitude, 4),
            "is_sudden": self.is_sudden,
        }


@dataclass
class SocialPerceptionReport:
    """
    تقرير الإدراك الاجتماعي — التقرير الشامل لعملية الإدراك الاجتماعي.
    Comprehensive report combining all social perception analysis results.
    يجمع كل نتائج تحليل الإدراك الاجتماعي في تقرير واحد منظم.
    """
    emotions: EmotionProfile = field(default_factory=EmotionProfile)         # المشاعر
    social_context: SocialContext = field(default_factory=SocialContext)      # السياق الاجتماعي
    dynamics: DynamicsUpdate = field(default_factory=DynamicsUpdate)          # الديناميكيات
    norms: NormEvaluation = field(default_factory=NormEvaluation)             # المعايير
    sarcasm: SarcasmIndicator = field(default_factory=SarcasmIndicator)       # السخرية
    prosodic: ProsodicIndicators = field(default_factory=ProsodicIndicators)  # المؤشرات الإعرابية
    social_role: SocialRole = field(default_factory=SocialRole)               # الدور الاجتماعي
    emotion_shifts: list[EmotionShift] = field(default_factory=list)          # تحولات المشاعر
    recommendations: list[str] = field(default_factory=list)                  # التوصيات
    dialect_detected: str = ""                                                # اللهجة المكتشفة
    negation_applied: bool = False                                            # هل تم تطبيق النفي؟
    intensity_modifier: float = 1.0                                           # معدّل الشدة

    def to_dict(self) -> dict:
        return {
            "emotions": self.emotions.to_dict(),
            "social_context": self.social_context.to_dict(),
            "dynamics": self.dynamics.to_dict(),
            "norms": self.norms.to_dict(),
            "sarcasm": self.sarcasm.to_dict(),
            "prosodic": self.prosodic.to_dict(),
            "social_role": self.social_role.to_dict(),
            "emotion_shifts": [s.to_dict() for s in self.emotion_shifts],
            "recommendations": self.recommendations,
            "dialect_detected": self.dialect_detected,
            "negation_applied": self.negation_applied,
            "intensity_modifier": round(self.intensity_modifier, 4),
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  كاشف المشاعر — EmotionDetector
# ═══════════════════════════════════════════════════════════════════════════════


class EmotionDetector:
    """
    كاشف المشاعر — يكتشف المشاعر من النص باستخدام قواميس عربية وإنجليزية.
    Detects emotions from text using Arabic and English emotion lexicons.

    Features:
    - 50+ Arabic emotion words mapped to emotion categories
    - 50+ English emotion words mapped to emotion categories
    - Valence-arousal computation for dimensional emotion representation
    - Confidence scoring based on lexical coverage
    - Negation detection (Arabic + English)
    - Intensity modifiers (amplifiers + diminishers)
    - Emoji emotion detection
    - Dialectal Arabic emotion words (Egyptian, Levantine, Gulf)
    """

    # ─── كلمات النفي العربية — Arabic negation words ─────────────────────
    _ARABIC_NEGATION: list[str] = [
        "ليس", "لست", "لستُ", "لستَ", "لستِ", "ليست", "لن", "لا", "لم",
        "ما", "غير", "بدون", "دون", "لا أحد", "لا شيء",
    ]

    # ─── كلمات النفي الإنجليزية — English negation words ─────────────────
    _ENGLISH_NEGATION: list[str] = [
        "not", "isn't", "aren't", "don't", "doesn't", "won't", "can't",
        "never", "barely", "hardly", "no", "neither", "nor", "nobody",
        "nothing", "nowhere", "without",
    ]

    # ─── معدّلات الشدة — Intensity modifiers ──────────────────────────────
    _ARABIC_AMPLIFIERS: list[str] = [
        "جداً", "كثيراً", "للغاية", "شدة", "بشدة", "غاية", "أقصى",
        "تماماً", "حقاً", "فعلاً", "أبداً", "كل", "أكثر",
    ]
    _ARABIC_DIMINISHERS: list[str] = [
        "قليلاً", "نسبياً", "بعض", "تقريباً", "شبه", "أقل",
        "قليل", "هكذا", "تمام",
    ]
    _ENGLISH_AMPLIFIERS: list[str] = [
        "very", "extremely", "incredibly", "absolutely", "totally",
        "completely", "utterly", "deeply", "highly", "super",
        "really", "truly", "so", "terribly", "awfully",
    ]
    _ENGLISH_DIMINISHERS: list[str] = [
        "slightly", "somewhat", "a bit", "a little", "fairly",
        "rather", "mildly", "moderately", "kind of", "sort of",
        "partly", "scarcely", "barely",
    ]

    # ─── خريطة الرموز التعبيرية — Emoji emotion mapping ──────────────────
    _EMOJI_EMOTIONS: dict[str, str] = {
        # فرح/حب — Joy/Love
        "😊": "joy", "😄": "joy", "😍": "love", "🥰": "love",
        "💕": "love", "❤️": "love", "💖": "love", "💗": "love",
        "😘": "love", "🤗": "joy", "😁": "joy", "😂": "joy",
        "🤩": "joy", "😃": "joy", "😆": "joy",
        # حزن — Sadness
        "😢": "sadness", "😭": "sadness", "💔": "sadness",
        "😞": "sadness", "😔": "sadness", "😟": "sadness",
        "😥": "sadness", "😓": "sadness",
        # غضب — Anger
        "😡": "anger", "😤": "anger", "🔥": "anger",
        "😠": "anger", "🤬": "anger", "💢": "anger",
        # خوف — Fear
        "😱": "fear", "😨": "fear", "😰": "fear",
        "😳": "fear", "😵": "fear",
        # مفاجأة — Surprise
        "😲": "surprise", "😮": "surprise", "😯": "surprise",
        "🙀": "surprise", "😮‍💨": "surprise",
        # اشمئزاز — Disgust
        "🤢": "disgust", "💩": "disgust", "🤮": "disgust",
        "恶心": "disgust",
        # امتنان — Gratitude
        "🙏": "gratitude", "🤝": "trust",
        # ثقة — Trust
        "👍": "trust", "💪": "trust", "👏": "trust",
    }

    # ─── كلمات المشاعر العامية المصرية — Egyptian dialect emotion words ──
    _EGYPTIAN_DIALECT: dict[str, str] = {
        "قشطة": "joy", "هتموت": "joy", "جامد": "joy", "تحفة": "joy",
        "بضان": "joy", "هايل": "joy", "عظمة": "joy", "فشر": "joy",
        "معلش": "sadness", "وحشة": "sadness", "زهقان": "sadness",
        "مخنوق": "sadness", "نرفزة": "anger", "متنرفز": "anger",
        "هتجن": "anger", "مصدوم": "surprise", "عفريت": "surprise",
    }

    # ─── كلمات المشاعر العامية الشامية — Levantine dialect emotion words ─
    _LEVANTINE_DIALECT: dict[str, str] = {
        "كتير": "joy", "له": "sadness", "شو": "surprise",
        "هيدا": "surprise", "منيح": "joy", "كتير_منيح": "joy",
        "مو_منيح": "sadness", "بيخزي": "shame", "عاطل": "sadness",
        "فاشل": "sadness", "مبسوط": "joy", "متأفف": "anger",
    }

    # ─── كلمات المشاعر العامية الخليجية — Gulf dialect emotion words ────
    _GULF_DIALECT: dict[str, str] = {
        "زين": "joy", "عاد": "anger", "يبه": "sadness",
        "سيدتي": "trust", "وايد": "joy", "مو_زين": "sadness",
        "خقه": "anger", "يمعلق": "surprise", "غثيث": "anger",
        "نونو": "love", "قهر": "sadness",
    }

    # ─── قاموس المشاعر العربية — Arabic Emotion Lexicon ──────────────────
    _ARABIC_EMOTIONS: dict[str, str] = {
        # فرح — Joy
        "سعيد": "joy", "فرحان": "joy", "مبسوط": "joy", "مرتاح": "joy",
        "مسرور": "joy", "بهيج": "joy", "فَرِح": "joy", "مبتسم": "joy",
        "مسرور": "joy", "منشرح": "joy",
        # حزن — Sadness
        "حزين": "sadness", "مكتئب": "sadness", "تعبان": "sadness",
        "مهموم": "sadness", "كئيب": "sadness", "مجروح": "sadness",
        "قلقان": "sadness", "متضايق": "sadness", "يائس": "sadness",
        "بائس": "sadness",
        # غضب — Anger
        "غاضب": "anger", "زعلان": "anger", "مستفز": "anger", "منفعل": "anger",
        "غضبان": "anger", "ثائر": "anger", "محتد": "anger", "مثار": "anger",
        "هائج": "anger", "ناقم": "anger",
        # خوف — Fear
        "خائف": "fear", "مرعوب": "fear", "فزع": "fear", "خشية": "fear",
        "مرتاع": "fear", "وجل": "fear", "فَزِع": "fear", "مرتعب": "fear",
        "مشفق": "fear", "حذِر": "fear",
        # مفاجأة — Surprise
        "متفاجئ": "surprise", "مندهش": "surprise", "مذهول": "surprise",
        "مأخوذ": "surprise", "مبغوت": "surprise", "مذهول": "surprise",
        "مستغرب": "surprise", "صُدم": "surprise", "مبهور": "surprise",
        "مدهوش": "surprise",
        # ثقة — Trust
        "واثق": "trust", "مطمئن": "trust", "موثوق": "trust", "مؤتمن": "trust",
        "صادق": "trust", "أمين": "trust", "معتمد": "trust", "مُوَثَّق": "trust",
        "راسخ": "trust", "ثابت": "trust",
        # ترقب — Anticipation
        "منتظر": "anticipation", "مترقب": "anticipation", "متشوق": "anticipation",
        "متحمس": "anticipation", "مستعد": "anticipation", "متهيئ": "anticipation",
        "متطلع": "anticipation", "مؤمل": "anticipation", "راغب": "anticipation",
        "طامع": "anticipation",
        # حب — Love
        "محب": "love", "عاشق": "love", "ولهان": "love", "مشوق": "love",
        "متيم": "love", "هائم": "love", "مغرَم": "love", "مفتون": "love",
        "معجب": "love", "مُحِب": "love",
        # خجل/حياء — Shame
        "خجول": "shame", "مستحي": "shame", "حيي": "shame", "محرج": "shame",
        "مختلط": "shame", "مندهش": "shame", "مخنوع": "shame", "مقروع": "shame",
        "متواضع": "shame", "خاشع": "shame",
        # فخر — Pride
        "فخور": "pride", "معتز": "pride", "مفتخر": "pride", "معتز": "pride",
        "منتصف": "pride", "مباهٍ": "pride", "صلف": "pride", "متكبر": "pride",
        "متعالي": "pride", "مغرور": "pride",
        # امتنان — Gratitude
        "شاكر": "gratitude", "ممتن": "gratitude", "حامد": "gratitude",
        "شاكرٍ": "gratitude", "مقدِّر": "gratitude", "مُعترِف": "gratitude",
        "مدين": "gratitude", "مُمتَنّ": "gratitude", "مُقِرّ": "gratitude",
        "شكور": "gratitude",
        # اشمئزاز — Disgust
        "متقزز": "disgust", "مشمئز": "disgust", "نافر": "disgust",
        "كاره": "disgust", "مستقذر": "disgust",
    }

    # ─── مفتاح عكس المشاعر عند النفي — Emotion flip map for negation ───
    _EMOTION_FLIP: dict[str, str] = {
        "joy": "sadness",
        "sadness": "joy",
        "anger": "trust",
        "fear": "trust",
        "trust": "fear",
        "love": "disgust",
        "disgust": "love",
        "surprise": "anticipation",
        "anticipation": "surprise",
        "pride": "shame",
        "shame": "pride",
        "gratitude": "anger",
        "neutral": "neutral",
    }

    # ─── قاموس المشاعر الإنجليزية — English Emotion Lexicon ─────────────
    _ENGLISH_EMOTIONS: dict[str, str] = {
        # Joy
        "happy": "joy", "glad": "joy", "joyful": "joy", "delighted": "joy",
        "cheerful": "joy", "pleased": "joy", "thrilled": "joy", "ecstatic": "joy",
        "elated": "joy", "content": "joy", "blissful": "joy", "jubilant": "joy",
        # Sadness
        "sad": "sadness", "unhappy": "sadness", "depressed": "sadness",
        "miserable": "sadness", "sorrowful": "sadness", "gloomy": "sadness",
        "melancholy": "sadness", "heartbroken": "sadness", "despondent": "sadness",
        "woeful": "sadness", "dismal": "sadness", "forlorn": "sadness",
        # Anger
        "angry": "anger", "furious": "anger", "enraged": "anger", "irate": "anger",
        "outraged": "anger", "livid": "anger", "incensed": "anger", "irate": "anger",
        "indignant": "anger", "infuriated": "anger", "aggravated": "anger",
        "annoyed": "anger",
        # Fear
        "afraid": "fear", "scared": "fear", "terrified": "fear", "fearful": "fear",
        "anxious": "fear", "panicked": "fear", "dreadful": "fear", "alarmed": "fear",
        "petrified": "fear", "horrified": "fear", "apprehensive": "fear",
        # Surprise
        "surprised": "surprise", "amazed": "surprise", "astonished": "surprise",
        "stunned": "surprise", "shocked": "surprise", "dumbfounded": "surprise",
        "flabbergasted": "surprise", "startled": "surprise", "awestruck": "surprise",
        "taken_aback": "surprise",
        # Disgust
        "disgusted": "disgust", "repulsed": "disgust", "revolted": "disgust",
        "nauseated": "disgust", "appalled": "disgust", "sickened": "disgust",
        # Trust
        "trusting": "trust", "confident": "trust", "secure": "trust",
        "reliable": "trust", "faithful": "trust", "assured": "trust",
        "certain": "trust", "believing": "trust", "dependable": "trust",
        # Anticipation
        "expectant": "anticipation", "eager": "anticipation", "hopeful": "anticipation",
        "excited": "anticipation", "anticipating": "anticipation", "prepared": "anticipation",
        "looking_forward": "anticipation", "enthused": "anticipation", "keen": "anticipation",
        # Love
        "loving": "love", "affectionate": "love", "devoted": "love",
        "adoring": "love", "tender": "love", "fond": "love", "caring": "love",
        "passionate": "love", "infatuated": "love", "enchanted": "love",
        # Shame
        "ashamed": "shame", "embarrassed": "shame", "guilty": "shame",
        "humiliated": "shame", "mortified": "shame", "sheepish": "shame",
        "abashed": "shame", "chagrined": "shame",
        # Pride
        "proud": "pride", "dignified": "pride", "honored": "pride",
        "triumphant": "pride", "victorious": "pride", "exultant": "pride",
        # Gratitude
        "grateful": "gratitude", "thankful": "gratitude", "appreciative": "gratitude",
        "indebted": "gratitude", "obliged": "gratitude", "beholden": "gratitude",
    }

    # ─── قيم التكافؤ والاستثارة — Valence-Arousal values per emotion ─────
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

    def detect_emotions(self, text: str) -> EmotionProfile:
        """
        كشف المشاعر — يكتشف المشاعر من النص.
        Detect emotions from text using both Arabic and English lexicons,
        with support for negation, intensity modifiers, emojis, and dialects.

        كشف المشاعر من النص مع دعم النفي ومعدّلات الشدة والرموز التعبيرية واللهجات.

        Args:
            text: النص المراد تحليله — text to analyze

        Returns:
            EmotionProfile — ملف المشاعر المكتشفة
        """
        if not text or not text.strip():
            return EmotionProfile(
                emotions={"neutral": 1.0},
                dominant_emotion="neutral",
                valence=0.0,
                arousal=0.0,
                confidence=0.0,
            )

        # كشف المشاعر العربية والإنجليزية — Detect from both lexicons
        ar_emotions, ar_negated = self._detect_arabic_emotions(text)
        en_emotions, en_negated = self._detect_english_emotions(text)

        # كشف المشاعر من الرموز التعبيرية — Detect from emojis
        emoji_emotions = self._detect_emoji_emotions(text)

        # كشف المشاعر من اللهجات — Detect from dialectal words
        dialect_emotions, dialect_name = self._detect_dialectal_emotions(text)

        # دمج النتائج — Merge results
        merged: dict[str, float] = defaultdict(float)
        for emotion, score in ar_emotions.items():
            merged[emotion] += score
        for emotion, score in en_emotions.items():
            merged[emotion] += score
        for emotion, score in emoji_emotions.items():
            merged[emotion] += score
        for emotion, score in dialect_emotions.items():
            merged[emotion] += score

        # تطبيق معدّل الشدة — Apply intensity modifier
        intensity_mod = self._compute_intensity_modifier(text)
        for emotion in merged:
            merged[emotion] *= intensity_mod

        # ملاحظة: النفي تم تطبيقه بالفعل في طرق الكشف — Note: negation already applied in detection methods
        negation_applied = ar_negated or en_negated

        # تطبيع الدرجات — Normalize scores
        total = sum(merged.values())
        if total > 0:
            merged = {k: v / total for k, v in merged.items()}
        else:
            merged = {"neutral": 1.0}

        # تحديد المشاعر السائدة — Determine dominant emotion
        dominant = max(merged, key=lambda k: merged[k]) if merged else "neutral"

        # حساب التكافؤ والاستثارة — Compute valence-arousal
        va = self._compute_valence_arousal(merged)

        # حساب الثقة — Compute confidence
        confidence = min(1.0, total / 3.0) if total > 0 else 0.0

        logger.debug(
            "كاشف المشاعر: مشاعر مكتشفة — Emotions detected | "
            "dominant=%s, valence=%.2f, arousal=%.2f, confidence=%.2f, "
            "negation=%s, intensity=%.2f, dialect=%s",
            dominant, va.valence, va.arousal, confidence,
            negation_applied, intensity_mod, dialect_name,
        )

        return EmotionProfile(
            emotions=dict(merged),
            dominant_emotion=dominant,
            valence=va.valence,
            arousal=va.arousal,
            confidence=confidence,
        )

    def detect_dialect(self, text: str) -> str:
        """
        كشف اللهجة — يكشف اللهجة العربية المستخدمة في النص.
        Detects which Arabic dialect is used in the text.

        Args:
            text: النص — text to analyze

        Returns:
            str — اسم اللهجة: egyptian, levantine, gulf, أو standard
        """
        _, dialect_name = self._detect_dialectal_emotions(text)
        return dialect_name

    def _detect_arabic_emotions(self, text: str) -> tuple[dict[str, float], bool]:
        """
        كشف المشاعر العربية — Detect emotions from Arabic text.
        يبحث عن كلمات المشاعر العربية في النص مع دعم النفي.

        Detects emotions from Arabic text with negation support.
        When a negation word precedes an emotion word, the emotion is flipped.
        Arabic diacritics (tashkeel) are stripped before matching.

        Args:
            text: النص العربي — Arabic text

        Returns:
            tuple — (emotions dict, negation_applied bool)
        """
        emotions: dict[str, float] = defaultdict(float)
        words = re.findall(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+", text)
        negation_applied = False

        for i, word in enumerate(words):
            # إزالة التشكيل — Strip diacritics (tashkeel)
            stripped = self._strip_arabic_diacritics(word)

            # فحص النفي — Check for negation
            is_negated = False
            # Check if any of the previous 3 words is a negation word
            for j in range(max(0, i - 3), i):
                stripped_prev = self._strip_arabic_diacritics(words[j])
                if stripped_prev in self._ARABIC_NEGATION or words[j] in self._ARABIC_NEGATION:
                    is_negated = True
                    break

            # مطابقة الكلمة مع أو بدون تشكيل — Match with or without diacritics
            category = self._match_arabic_emotion_word(word, stripped)
            if category:
                if is_negated:
                    # عكس المشاعر عند النفي — Flip emotion on negation
                    flipped = self._EMOTION_FLIP.get(category, category)
                    emotions[flipped] += 1.0
                    negation_applied = True
                else:
                    emotions[category] += 1.0

        return dict(emotions), negation_applied

    def _detect_english_emotions(self, text: str) -> tuple[dict[str, float], bool]:
        """
        كشف المشاعر الإنجليزية — Detect emotions from English text.
        يبحث عن كلمات المشاعر الإنجليزية في النص مع دعم النفي.

        Detects emotions from English text with negation support.
        When a negation word precedes an emotion word, the emotion is flipped.

        Args:
            text: النص الإنجليزي — English text

        Returns:
            tuple — (emotions dict, negation_applied bool)
        """
        emotions: dict[str, float] = defaultdict(float)
        words = re.findall(r"\b[a-zA-Z']+\b", text.lower())
        negation_applied = False

        for i, word in enumerate(words):
            # فحص النفي — Check for negation
            is_negated = False
            for j in range(max(0, i - 3), i):
                if words[j] in self._ENGLISH_NEGATION:
                    is_negated = True
                    break

            if word in self._ENGLISH_EMOTIONS:
                category = self._ENGLISH_EMOTIONS[word]
                if is_negated:
                    # عكس المشاعر عند النفي — Flip emotion on negation
                    flipped = self._EMOTION_FLIP.get(category, category)
                    emotions[flipped] += 1.0
                    negation_applied = True
                else:
                    emotions[category] += 1.0

        return dict(emotions), negation_applied

    def _detect_emoji_emotions(self, text: str) -> dict[str, float]:
        """
        كشف المشاعر من الرموز التعبيرية — Detect emotions from emojis.
        يبحث عن الرموز التعبيرية في النص ويحدد المشاعر المقابلة.

        Detects emotions from emoji characters in text.

        Args:
            text: النص — text containing possible emojis

        Returns:
            dict — {emotion_category: score}
        """
        emotions: dict[str, float] = defaultdict(float)

        for emoji_char, category in self._EMOJI_EMOTIONS.items():
            count = text.count(emoji_char)
            if count > 0:
                emotions[category] += float(count)

        return dict(emotions)

    def _detect_dialectal_emotions(self, text: str) -> tuple[dict[str, float], str]:
        """
        كشف المشاعر اللهجية — Detect emotions from dialectal Arabic words.
        يبحث عن كلمات المشاعر باللهجات العربية المختلفة.

        Detects emotions from Egyptian, Levantine, and Gulf dialect words.

        Args:
            text: النص — text to analyze

        Returns:
            tuple — (emotions dict, dialect_name str)
        """
        emotions: dict[str, float] = defaultdict(float)
        dialect_counts: dict[str, int] = {"egyptian": 0, "levantine": 0, "gulf": 0}

        # فحص اللهجة المصرية — Check Egyptian dialect
        for word, category in self._EGYPTIAN_DIALECT.items():
            if word in text:
                emotions[category] += 1.0
                dialect_counts["egyptian"] += 1

        # فحص اللهجة الشامية — Check Levantine dialect
        for word, category in self._LEVANTINE_DIALECT.items():
            if word in text:
                emotions[category] += 1.0
                dialect_counts["levantine"] += 1

        # فحص اللهجة الخليجية — Check Gulf dialect
        for word, category in self._GULF_DIALECT.items():
            if word in text:
                emotions[category] += 1.0
                dialect_counts["gulf"] += 1

        # تحديد اللهجة السائدة — Determine dominant dialect
        best_dialect = "standard"
        best_count = 0
        for dialect, count in dialect_counts.items():
            if count > best_count:
                best_count = count
                best_dialect = dialect

        return dict(emotions), best_dialect

    def _compute_intensity_modifier(self, text: str) -> float:
        """
        حساب معدّل الشدة — Compute intensity modifier for the text.
        يحسب معدّل الشدة بناءً على معدّلات الشدة (المكبّرات والمخفّضات).

        Amplifiers (very, extremely, جداً, كثيراً) multiply by 1.5.
        Diminishers (slightly, somewhat, قليلاً, نسبياً) multiply by 0.5.

        Args:
            text: النص — text to analyze

        Returns:
            float — معدّل الشدة (0.5, 1.0, or 1.5)
        """
        modifier = 1.0

        # فحص المكبّرات العربية — Check Arabic amplifiers
        for amp in self._ARABIC_AMPLIFIERS:
            if amp in text:
                modifier *= 1.5
                break  # تطبيق مرة واحدة فقط — apply once

        # فحص المكبّرات الإنجليزية — Check English amplifiers
        text_lower = text.lower()
        for amp in self._ENGLISH_AMPLIFIERS:
            if amp in text_lower:
                modifier *= 1.5
                break  # تطبيق مرة واحدة فقط — apply once

        # فحص المخفّضات العربية — Check Arabic diminishers
        for dim in self._ARABIC_DIMINISHERS:
            if dim in text:
                modifier *= 0.5
                break  # تطبيق مرة واحدة فقط — apply once

        # فحص المخفّضات الإنجليزية — Check English diminishers
        for dim in self._ENGLISH_DIMINISHERS:
            if dim in text_lower:
                modifier *= 0.5
                break  # تطبيق مرة واحدة فقط — apply once

        return modifier

    @staticmethod
    def _strip_arabic_diacritics(word: str) -> str:
        """
        إزالة التشكيل العربي — Strip Arabic diacritics (tashkeel) from a word.
        يزيل الحركات والتشكيل من الكلمة العربية لتسهيل المطابقة.

        Args:
            word: الكلمة العربية — Arabic word

        Returns:
            str — الكلمة بدون تشكيل — word without diacritics
        """
        # Unicode range for Arabic diacritics: Fatha(َ)=064E, Damma(ُ)=064F,
        # Kasra(ِ)=0650, Shadda(ّ)=0651, Sukun(ْ)=0652,
        # Tanwin Fath(ً)=064B, Tanwin Damm(ٌ)=064C, Tanwin Kasr(ٍ)=064D
        return re.sub(r"[\u064B-\u0652\u0670]", "", word)

    def _match_arabic_emotion_word(self, raw_word: str, stripped_word: str) -> str:
        """
        مطابقة كلمة عربية مع قاموس المشاعر — Match an Arabic word against the emotion lexicon.
        يطابق الكلمة العربية مع قاموس المشاعر، مع دعم الصيغ المختلفة للكلمة
        (مع أو بدون تشكيل، مع أو بدون ألف التنوين).

        Matches Arabic words against the emotion lexicon with support for
        different word forms (with/without diacritics, with/without tanwin alif).

        Args:
            raw_word: الكلمة الخام — raw word as extracted
            stripped_word: الكلمة بدون تشكيل — word with diacritics stripped

        Returns:
            str — فئة المشاعر أو سلسلة فارغة — emotion category or empty string
        """
        # مطابقة مباشرة — Direct match
        if raw_word in self._ARABIC_EMOTIONS:
            return self._ARABIC_EMOTIONS[raw_word]
        if stripped_word in self._ARABIC_EMOTIONS:
            return self._ARABIC_EMOTIONS[stripped_word]

        # إزالة ألف التنوين — Remove tanwin alif (ا at end after stripping)
        # e.g., سعيداً -> سعيدا -> سعيد
        if stripped_word.endswith("ا") and len(stripped_word) > 2:
            without_alif = stripped_word[:-1]
            if without_alif in self._ARABIC_EMOTIONS:
                return self._ARABIC_EMOTIONS[without_alif]

        # إزالة تاء التأنيث — Remove taa marbuta
        # e.g., سعيدة -> سعيد
        if stripped_word.endswith("ة") and len(stripped_word) > 2:
            without_taa = stripped_word[:-1]
            if without_taa in self._ARABIC_EMOTIONS:
                return self._ARABIC_EMOTIONS[without_taa]

        return ""

    def _compute_valence_arousal(self, emotions: dict[str, float]) -> ValenceArousal:
        """
        حساب التكافؤ والاستثارة — Compute valence and arousal from emotion scores.
        يحسب قيم التكافؤ (الإيجابي/السلبي) والاستثارة (الهادئ/المثار).

        Args:
            emotions: قاموس المشاعر ودرجاتها — emotion scores dict

        Returns:
            ValenceArousal — قيم التكافؤ والاستثارة
        """
        total_weight = sum(emotions.values())
        if total_weight == 0:
            return ValenceArousal(valence=0.0, arousal=0.0)

        weighted_valence = 0.0
        weighted_arousal = 0.0

        for emotion, score in emotions.items():
            va = self._VALENCE_AROUSAL.get(emotion, (0.0, 0.0))
            weight = score / total_weight
            weighted_valence += va[0] * weight
            weighted_arousal += va[1] * weight

        return ValenceArousal(
            valence=max(-1.0, min(1.0, weighted_valence)),
            arousal=max(-1.0, min(1.0, weighted_arousal)),
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  محلل السياق الاجتماعي — SocialContextAnalyzer
# ═══════════════════════════════════════════════════════════════════════════════


class SocialContextAnalyzer:
    """
    محلل السياق الاجتماعي — يحلل السياق الاجتماعي للتفاعلات.
    Analyzes social context of interactions including formality, power,
    group identity, and cultural markers.
    """

    # ─── مؤشرات الرسمية العربية — Arabic formality indicators ───────────
    _AR_FORMAL_MARKERS: list[str] = [
        "سيدي", "سيدتي", "حضرة", "معالي", "سعادة", "فضيلة", "دولة",
        "أستاذ", "دكتور", "مهندس", "شيخ", "سماحة", "السيد", "السيدة",
        "الآنسة", "المكرم", "المكرمة", "المحترم", "المحترمة",
    ]

    _AR_INFORMAL_MARKERS: list[str] = [
        "يا أخي", "يا أختي", "يا صاحبي", "يا حلوي", "حبيبي", "حبيبتي",
        "يا عيني", "يا روحي", "يا ناسي", "يا والله", "شوف", "هات",
        "تعال", "يلا", "هيا", "بلا", "خلاص",
    ]

    # ─── مؤشرات الرسمية الإنجليزية — English formality indicators ───────
    _EN_FORMAL_MARKERS: list[str] = [
        "sir", "madam", "mr.", "mrs.", "ms.", "dr.", "professor",
        "your honor", "your excellency", "distinguished", "respectfully",
        "sincerely", "regards", "yours truly",
    ]

    _EN_INFORMAL_MARKERS: list[str] = [
        "hey", "yo", "sup", "what's up", "dude", "bro", "sis",
        "gonna", "wanna", "gotta", "kinda", "lol", "omg", "btw",
    ]

    # ─── مؤشرات القوة — Power dynamics indicators ────────────────────────
    _SUPERIORITY_MARKERS_AR: list[str] = [
        "أمرتك", "يجب عليك", "لا بد أن", "أطعني", "نفّذ", "أريد منك",
        "ممنوع", "لا تجرؤ", "اسمع كلامي", "أنا المسؤول",
    ]

    _SUBORDINATION_MARKERS_AR: list[str] = [
        "لو سمحت", "عذراً", "أعتذر", "تكرم", "تفضل", "سمحلي",
        "أرجو", "أتوسل", "لو تسمحلي", "على راسي",
    ]

    _SUPERIORITY_MARKERS_EN: list[str] = [
        "you must", "i order", "do this", "don't question", "because i said",
        "i demand", "you will", "mandatory", "required",
    ]

    _SUBORDINATION_MARKERS_EN: list[str] = [
        "please", "if you don't mind", "i beg", "kindly", "may i",
        "would you", "could you", "i humbly", "with respect",
    ]

    # ─── علامات الهوية الجماعية — Group identity markers ────────────────
    _GROUP_MARKERS: dict[str, list[str]] = {
        "arab": [
            "يا أخي", "والله", "تكرم", "عيني", "يا عيني",
            "والعهد", "شرف", "كرم", "ضيافة", "عشيرة", "قبيلة",
        ],
        "family": [
            "يا عم", "يا خال", "يا ابن عمي", "يا أختي", "يا أمي",
            "يا أبي", "uncle", "aunt", "cousin", "brother", "sister",
        ],
        "professional": [
            "زميل", "مدير", "فريق", "مشروع", "colleague", "team",
            "project", "meeting", "deadline", "budget",
        ],
        "religious": [
            "ما شاء الله", "سبحان الله", "الحمد لله", "إن شاء الله",
            "بسم الله", "الله أكبر", "jazakallah", "mashallah", "inshallah",
        ],
    }

    # ─── العلامات الثقافية — Cultural markers ────────────────────────────
    _CULTURAL_PATTERNS: list[tuple[MarkerType, str, list[str]]] = [
        (MarkerType.RELIGIOUS, "علامة دينية إسلامية", [
            "الحمد لله", "إن شاء الله", "ما شاء الله", "سبحان الله",
            "الله أكبر", "بسم الله", "صلى الله عليه وسلم",
            "jazakallah", "mashallah", "inshallah", "alhamdulillah",
            "subhanallah", "allahu akbar", "bismillah",
        ]),
        (MarkerType.HOSPITALITY, "علامة ضيافة عربية", [
            "أهلاً وسهلاً", "تفضل", "يسعدنا", "بيتك", "عندك",
            "كرم", "ضيافة", "نور", "يا ضيف", "حياك الله",
            "welcome", "make yourself at home", "hospitality",
        ]),
        (MarkerType.HONORIFIC, "علامة ألقاب وتكريم", [
            "سيدي", "سيدتي", "حضرة", "معالي", "سعادة", "فضيلة",
            "شيخ", "أستاذ", "دكتور", "your excellency", "sir", "madam",
        ]),
        (MarkerType.FAMILY, "علامة عائلية", [
            "يا عم", "يا خال", "يا أبي", "يا أمي", "ابن عمي",
            "صلة الرحم", "العائلة", "uncle", "aunt", "cousin",
        ]),
        (MarkerType.TRIBAL, "علامة قبلية/عشائرية", [
            "عشيرة", "قبيلة", "عاقل العشيرة", "شيخ القبيلة",
            "وجاهة", "شرف", "حمولة", "فخذ",
        ]),
        (MarkerType.TEMPORAL, "علامة زمنية ثقافية", [
            "رمضان", "عيد الفطر", "عيد الأضحى", "المولد النبوي",
            "ليلة القدر", "رمضان كريم", "كل عام وأنتم بخير",
            "ramadan", "eid", "mawlid",
        ]),
        (MarkerType.GENDER, "علامة جندرية", [
            "يا أخي", "يا أختي", "حبيبي", "حبيبتي", "سيدي", "سيدتي",
        ]),
        (MarkerType.ETIQUETTE, "علامة آداب", [
            "لو سمحت", "شكراً", "عفواً", "تفضل", "من فضلك",
            "please", "thank you", "excuse me", "pardon",
        ]),
        (MarkerType.IDIOMATIC, "تعبير ثقافي", [
            "يا عيني", "والله", "تكرم عينك", "على راسي",
            "والعهد بالله", "يا ساتر", "الله يعين",
        ]),
    ]

    def analyze_interaction(
        self, text: str, participants: list[str] | None = None
    ) -> SocialContext:
        """
        تحليل التفاعل — يحلل السياق الاجتماعي للتفاعل.
        Analyze the social context of an interaction.

        Args:
            text: نص التفاعل — interaction text
            participants: قائمة المشاركين — list of participant identifiers

        Returns:
            SocialContext — السياق الاجتماعي المكتشف
        """
        participants = participants or []

        # كشف مستوى الرسمية — Detect formality level
        formality = self._detect_formality_level(text)

        # كشف ديناميكية القوة — Detect power dynamics
        power = self._detect_power_dynamics(text, participants)

        # كشف الهوية الجماعية — Detect group identity
        group = self._detect_group_identity(text)

        # كشف العلامات الثقافية — Detect cultural markers
        markers = self._detect_cultural_markers(text)

        logger.debug(
            "محلل السياق: تحليل مكتمل — Context analysis complete | "
            "formality=%s, power=%s, markers=%d",
            formality.value, power.direction.value, len(markers),
        )

        return SocialContext(
            formality=formality,
            power_dynamics=power,
            group_identity=group,
            cultural_markers=markers,
        )

    def _detect_formality_level(self, text: str) -> FormalityLevel:
        """
        كشف مستوى الرسمية — Detect formality level of text.
        يحدد مستوى الرسمية بناءً على المؤشرات اللغوية.

        Args:
            text: النص — text to analyze

        Returns:
            FormalityLevel — مستوى الرسمية
        """
        if not text:
            return FormalityLevel.SEMI_FORMAL

        formal_count = 0
        informal_count = 0

        # فحص المؤشرات العربية — Check Arabic markers
        for marker in self._AR_FORMAL_MARKERS:
            if marker in text:
                formal_count += 1

        for marker in self._AR_INFORMAL_MARKERS:
            if marker in text:
                informal_count += 1

        # فحص المؤشرات الإنجليزية — Check English markers
        text_lower = text.lower()
        for marker in self._EN_FORMAL_MARKERS:
            if marker in text_lower:
                formal_count += 1

        for marker in self._EN_INFORMAL_MARKERS:
            if marker in text_lower:
                informal_count += 1

        # تحديد المستوى — Determine level
        total = formal_count + informal_count
        if total == 0:
            # استخدام إشارات أخرى — use other signals
            if any(c in text for c in "،؛"):
                return FormalityLevel.SEMI_FORMAL
            return FormalityLevel.SEMI_FORMAL

        ratio = formal_count / total

        if ratio >= 0.7:
            return FormalityLevel.FORMAL
        elif ratio >= 0.4:
            return FormalityLevel.SEMI_FORMAL
        elif ratio >= 0.15:
            return FormalityLevel.INFORMAL
        else:
            return FormalityLevel.INTIMATE

    def _detect_power_dynamics(
        self, text: str, participants: list[str]
    ) -> PowerDynamics:
        """
        كشف ديناميكية القوة — Detect power dynamics in interaction.
        يحلل علاقات القوة بين المتحدث والمستمع.

        Args:
            text: النص — text to analyze
            participants: المشاركون — participant identifiers

        Returns:
            PowerDynamics — ديناميكية القوة المكتشفة
        """
        if not text:
            return PowerDynamics()

        superiority_score = 0.0
        subordination_score = 0.0
        indicators: list[str] = []

        # فحص مؤشرات التفوق العربي — Check Arabic superiority markers
        for marker in self._SUPERIORITY_MARKERS_AR:
            if marker in text:
                superiority_score += 0.2
                indicators.append(f"مؤشر تفوق: {marker}")

        # فحص مؤشرات الخضوع العربي — Check Arabic subordination markers
        for marker in self._SUBORDINATION_MARKERS_AR:
            if marker in text:
                subordination_score += 0.2
                indicators.append(f"مؤشر خضوع: {marker}")

        # فحص المؤشرات الإنجليزية — Check English markers
        text_lower = text.lower()
        for marker in self._SUPERIORITY_MARKERS_EN:
            if marker in text_lower:
                superiority_score += 0.2
                indicators.append(f"superiority marker: {marker}")

        for marker in self._SUBORDINATION_MARKERS_EN:
            if marker in text_lower:
                subordination_score += 0.2
                indicators.append(f"subordination marker: {marker}")

        # تحديد الاتجاه — Determine direction
        score = min(1.0, abs(superiority_score - subordination_score))

        if superiority_score > subordination_score + 0.2:
            direction = PowerDirection.SUPERIOR
        elif subordination_score > superiority_score + 0.2:
            direction = PowerDirection.SUBORDINATE
        elif superiority_score > 0.1 or subordination_score > 0.1:
            direction = PowerDirection.EQUAL
        else:
            direction = PowerDirection.UNCLEAR

        return PowerDynamics(
            direction=direction,
            score=score,
            indicators=indicators[:10],
        )

    def _detect_group_identity(self, text: str) -> GroupIdentity:
        """
        كشف الهوية الجماعية — Detect group identity from text.
        يحدد الهوية الجماعية من العلامات اللغوية.

        Args:
            text: النص — text to analyze

        Returns:
            GroupIdentity — الهوية الجماعية المكتشفة
        """
        if not text:
            return GroupIdentity()

        best_group = ""
        best_markers: list[str] = []
        best_score = 0.0

        for group_name, markers in self._GROUP_MARKERS.items():
            found_markers = [m for m in markers if m in text]
            score = len(found_markers) / max(1, len(markers))
            if score > best_score:
                best_score = score
                best_group = group_name
                best_markers = found_markers

        # كشف لغة المجموعة الداخلية — Detect in-group language
        in_group = best_score > 0.1

        return GroupIdentity(
            group_type=best_group,
            markers=best_markers,
            in_group_language=in_group,
            solidarity_score=min(1.0, best_score * 2),
        )

    def _detect_cultural_markers(self, text: str) -> list[CulturalMarker]:
        """
        كشف العلامات الثقافية — Detect cultural markers in text.
        يبحث عن العلامات الثقافية في النص العربي والإنجليزي.

        Args:
            text: النص — text to analyze

        Returns:
            list[CulturalMarker] — العلامات الثقافية المكتشفة
        """
        markers: list[CulturalMarker] = []

        for marker_type, description, patterns in self._CULTURAL_PATTERNS:
            found = [p for p in patterns if p in text]
            if found:
                confidence = min(1.0, len(found) * 0.3)
                markers.append(CulturalMarker(
                    marker_type=marker_type,
                    description=f"{description}: {', '.join(found[:3])}",
                    confidence=confidence,
                ))

        return markers


# ═══════════════════════════════════════════════════════════════════════════════
#  متتبع ديناميكيات المحادثة — ConversationalDynamicsTracker
# ═══════════════════════════════════════════════════════════════════════════════


class ConversationalDynamicsTracker:
    """
    متتبع ديناميكيات المحادثة — يتتبع تدفق المحادثة وديناميكياتها.
    Tracks conversation flow, turn-taking, engagement, and topic shifts.

    Maintains a history of conversation turns and computes dynamics
    metrics in real-time as new turns are added.
    """

    # ─── ثوابت — Constants ───────────────────────────────────────────────
    MAX_HISTORY_TURNS = 200     # الحد الأقصى للأدوار المحفوظة
    ENGAGEMENT_WINDOW = 10      # نافذة حساب المشاركة
    MIN_TURNS_FOR_PATTERN = 3   # الحد الأدنى لحساب الأنماط

    def __init__(self) -> None:
        """
        تهيئة متتبع الديناميكيات — Initialize the dynamics tracker.
        """
        self._turns: list[ConversationTurn] = []
        self._topic_keywords: dict[int, list[str]] = {}  # turn_index -> keywords

    def track_turn(self, turn: ConversationTurn) -> DynamicsUpdate:
        """
        تتبع دور — يتتبع دوراً جديداً في المحادثة.
        Track a new conversation turn and update dynamics.

        Args:
            turn: الدور الجديد — the new conversation turn

        Returns:
            DynamicsUpdate — تحديث الديناميكيات
        """
        # إضافة الدور — Add the turn
        self._turns.append(turn)

        # تقليم السجل — Trim history
        if len(self._turns) > self.MAX_HISTORY_TURNS:
            self._turns = self._turns[-self.MAX_HISTORY_TURNS:]

        # حساب مقاييس الديناميكيات — Compute dynamics metrics
        engagement = self._compute_engagement_level(self._turns)
        turn_pattern = self._compute_turn_taking_pattern(self._turns)
        leads = self._detect_conversational_leads(self._turns)
        shifts = self._detect_topic_shifts(self._turns)

        logger.debug(
            "متتبع الديناميكيات: دور مُتتبع — Turn tracked | "
            "speaker=%s, engagement=%.2f, leads=%d, shifts=%d",
            turn.speaker, engagement, len(leads), len(shifts),
        )

        return DynamicsUpdate(
            engagement=engagement,
            turn_pattern=turn_pattern,
            leads=leads,
            shifts=shifts,
        )

    def _compute_turn_taking_pattern(self, turns: list[ConversationTurn]) -> TurnPattern:
        """
        حساب نمط أدوار الكلام — Compute turn-taking pattern.
        يحلل كيف يتناوب المشاركون على الكلام.

        Args:
            turns: أدوار المحادثة — conversation turns

        Returns:
            TurnPattern — نمط الأدوار
        """
        if len(turns) < self.MIN_TURNS_FOR_PATTERN:
            return TurnPattern(pattern_type="insufficient_data")

        # حساب أطوال الأدوار — Compute turn lengths
        lengths = [len(t.content.split()) for t in turns]
        avg_length = sum(lengths) / len(lengths) if lengths else 0.0

        # حساب توزيع الأدوار بين المتحدثين — Compute turn distribution
        speaker_counts: dict[str, int] = defaultdict(int)
        for turn in turns:
            speaker_counts[turn.speaker] += 1

        # حساب درجة التوازن — Compute balance score
        if len(speaker_counts) <= 1:
            balance_score = 0.0
            pattern_type = "dominant"
        else:
            counts = list(speaker_counts.values())
            total_turns = sum(counts)
            expected = total_turns / len(counts)
            variance = sum((c - expected) ** 2 for c in counts) / len(counts)
            max_variance = expected ** 2
            balance_score = max(0.0, 1.0 - (variance / max(1.0, max_variance)))

            if balance_score >= 0.7:
                pattern_type = "balanced"
            elif balance_score >= 0.4:
                pattern_type = "semi_balanced"
            else:
                pattern_type = "dominant"

        return TurnPattern(
            pattern_type=pattern_type,
            balance_score=balance_score,
            avg_turn_length=avg_length,
        )

    def _detect_conversational_leads(self, turns: list[ConversationTurn]) -> list[LeadEvent]:
        """
        كشف قيادة المحادثة — Detect conversational leadership events.
        يحدد من يقود المحادثة من خلال المبادرة بطرح المواضيع والأسئلة.

        Args:
            turns: أدوار المحادثة — conversation turns

        Returns:
            list[LeadEvent] — أحداث القيادة المكتشفة
        """
        leads: list[LeadEvent] = []

        if len(turns) < 2:
            return leads

        for i, turn in enumerate(turns):
            content = turn.content.strip()

            # كشف الأسئلة — Detect questions
            question_markers_ar = ["هل", "ماذا", "كيف", "لماذا", "أين", "متى", "من"]
            question_markers_en = ["what", "how", "why", "when", "where", "who", "which"]
            is_question = (
                content.endswith("?")
                or content.endswith("؟")
                or any(content.startswith(m) for m in question_markers_ar)
                or any(content.lower().startswith(m) for m in question_markers_en)
            )

            if is_question:
                leads.append(LeadEvent(
                    speaker=turn.speaker,
                    event_type="question",
                    confidence=0.7,
                ))

            # كشف تغيير الموضوع — Detect topic changes
            topic_change_markers = [
                "بالمناسبة", "على فكرة", "changing the subject",
                "by the way", "anyway", "moving on",
            ]
            content_lower = content.lower()
            if any(m in content_lower for m in topic_change_markers):
                leads.append(LeadEvent(
                    speaker=turn.speaker,
                    event_type="topic_initiative",
                    confidence=0.6,
                ))

            # كشف التوجيهات — Detect directives
            directive_markers = [
                "دعنا", "هيا بنا", "let's", "we should",
                "i suggest", "أقترح", "يُفضل",
            ]
            if any(m in content_lower for m in directive_markers):
                leads.append(LeadEvent(
                    speaker=turn.speaker,
                    event_type="directive",
                    confidence=0.5,
                ))

        return leads[-20:]  # آخر 20 حدث — last 20 events

    def _compute_engagement_level(self, turns: list[ConversationTurn]) -> float:
        """
        حساب مستوى المشاركة — Compute engagement level.
        يقدر مستوى تفاعل المشاركين في المحادثة.

        Args:
            turns: أدوار المحادثة — conversation turns

        Returns:
            float — مستوى المشاركة (0-1)
        """
        if not turns:
            return 0.0

        # استخدام نافذة الأخيرة — Use recent window
        recent = turns[-self.ENGAGEMENT_WINDOW:]

        if len(recent) < 2:
            return 0.3

        # عامل 1: متوسط طول الدور — Factor 1: average turn length
        avg_len = sum(len(t.content.split()) for t in recent) / len(recent)
        length_score = min(1.0, avg_len / 15.0)  # 15 كلمات = مشاركة عالية

        # عامل 2: تنوع المتحدثين — Factor 2: speaker diversity
        speakers = set(t.speaker for t in recent)
        diversity_score = min(1.0, len(speakers) / 3.0)

        # عامل 3: التوقيت بين الأدوار — Factor 3: timing between turns
        timing_score = 0.5
        if len(recent) >= 2:
            gaps = []
            for i in range(1, len(recent)):
                gap = recent[i].timestamp - recent[i - 1].timestamp
                if gap > 0:
                    gaps.append(gap)
            if gaps:
                avg_gap = sum(gaps) / len(gaps)
                # فجوة مثالية: 2-10 ثوانٍ — ideal gap: 2-10 seconds
                if 2.0 <= avg_gap <= 10.0:
                    timing_score = 1.0
                elif avg_gap < 2.0:
                    timing_score = 0.8  # سريع — fast
                else:
                    timing_score = max(0.1, 1.0 - (avg_gap - 10.0) / 60.0)

        # عامل 4: تنوع المشاعر — Factor 4: emotion diversity
        emotions = set(t.emotion for t in recent if t.emotion != "neutral")
        emotion_score = min(1.0, len(emotions) / 3.0)

        # حساب المعدل المرجح — Compute weighted average
        engagement = (
            length_score * 0.30
            + diversity_score * 0.25
            + timing_score * 0.25
            + emotion_score * 0.20
        )

        return max(0.0, min(1.0, engagement))

    def _detect_topic_shifts(self, turns: list[ConversationTurn]) -> list[TopicShift]:
        """
        كشف تحولات الموضوع — Detect topic shifts in conversation.
        يحدد التحولات في موضوع المحادثة بناءً على تغيير الكلمات المفتاحية.

        Args:
            turns: أدوار المحادثة — conversation turns

        Returns:
            list[TopicShift] — التحولات المكتشفة
        """
        shifts: list[TopicShift] = []

        if len(turns) < 4:
            return shifts

        # استخراج الكلمات المفتاحية لكل دور — Extract keywords per turn
        for i, turn in enumerate(turns):
            words = re.findall(r"[\u0600-\u06FF]+|[a-zA-Z]+", turn.content.lower())
            # تصفية الكلمات الشائعة — Filter common words
            stopwords = {
                "the", "a", "an", "is", "are", "was", "were", "be", "been",
                "have", "has", "had", "do", "does", "did", "will", "would",
                "من", "في", "على", "إلى", "عن", "مع", "هذا", "هذه", "التي",
                "الذي", "التي", "كان", "يكون", "هل", "أن", "لا", "نعم",
            }
            self._topic_keywords[i] = [w for w in words if w not in stopwords and len(w) > 2]

        # كشف التحولات — Detect shifts
        for i in range(3, len(turns)):
            current_kw = set(self._topic_keywords.get(i, []))
            prev_kw = set()
            for j in range(max(0, i - 3), i):
                prev_kw.update(self._topic_keywords.get(j, []))

            if not current_kw or not prev_kw:
                continue

            # حساب التداخل — Compute overlap
            overlap = len(current_kw & prev_kw) / max(1, len(current_kw | prev_kw))

            if overlap < 0.15:  # تحول واضح — clear shift
                shifts.append(TopicShift(
                    from_topic=", ".join(list(prev_kw)[:3]) if prev_kw else "غير محدد",
                    to_topic=", ".join(list(current_kw)[:3]) if current_kw else "غير محدد",
                    turn_index=i,
                    abruptness=1.0 - overlap,
                ))

        return shifts[-10:]  # آخر 10 تحولات — last 10 shifts


# ═══════════════════════════════════════════════════════════════════════════════
#  مقيّم المعايير الاجتماعية — SocialNormEvaluator
# ═══════════════════════════════════════════════════════════════════════════════


class SocialNormEvaluator:
    """
    مقيّم المعايير الاجتماعية — يقيّم الالتزام بالمعايير الاجتماعية.
    Evaluates adherence to social norms, including:
    - Arab/Islamic-specific norms: hospitality, respect for elders, honorifics
    - Universal norms: politeness, empathy, active listening
    """

    # ─── علامات الأدب العربي — Arabic politeness indicators ──────────────
    _AR_POLITENESS_POSITIVE: list[str] = [
        "لو سمحت", "من فضلك", "تفضل", "شكراً", "جزاك الله خيراً",
        "عفواً", "المعذرة", "يسعدني", "تشرفت", "أرجو",
        "تكرم", "حياك الله", "الله يعطيك العافية", "مشكور",
        "يعطيك ألف عافية", "ما قصرت",
    ]

    _AR_POLITENESS_NEGATIVE: list[str] = [
        "اسكت", "اطلع", "روح", "خلاص", "وش تبي",
        "ما عندك سالفة", "انطّ", "بلا لف ودوران",
    ]

    # ─── علامات الأدب الإنجليزية — English politeness indicators ────────
    _EN_POLITENESS_POSITIVE: list[str] = [
        "please", "thank you", "thanks", "excuse me", "pardon",
        "kindly", "may i", "would you", "could you", "i appreciate",
        "you're welcome", "my pleasure", "i'm grateful",
    ]

    _EN_POLITENESS_NEGATIVE: list[str] = [
        "shut up", "get out", "whatever", "i don't care",
        "none of your business", "leave me alone", "buzz off",
    ]

    # ─── علامات الاحترام العربي/Islamic — Arab/Islamic respect indicators
    _AR_RESPECT_POSITIVE: list[str] = [
        "سيدي", "سيدتي", "يا شيخ", "يا أستاذ", "حضرة",
        "معالي", "سعادة", "فضيلة", "يا عم", "يا خال",
        "صلة الرحم", "بر الوالدين", "احترام الكبير",
        "رحم الله والديك", "طاع الله", "يا طويل العمر",
    ]

    _AR_RESPECT_NEGATIVE: list[str] = [
        "يا جاهل", "يا غبي", "ما عندك عقل", "إنت ما تفهم",
        "كبر دماغك", "لا تتفلسف",
    ]

    # ─── علامات الاحترام الإنجليزية — English respect indicators ────────
    _EN_RESPECT_POSITIVE: list[str] = [
        "with all due respect", "i respectfully", "if i may",
        "honored to", "it's a privilege", "sir", "madam",
    ]

    _EN_RESPECT_NEGATIVE: list[str] = [
        "you don't know", "you're wrong", "that's stupid",
        "how dare you", "you have no idea",
    ]

    # ─── معايير الضيافة العربية — Arab hospitality norms ────────────────
    _HOSPITALITY_MARKERS: list[str] = [
        "أهلاً وسهلاً", "تفضل", "بيتك بيتك", "نورت",
        "يسعدنا وجودك", "على الراس والعين", "حياك الله",
        "يا ضيفنا", "أكرمك الله", "غمرتنا بكرمك",
        "make yourself at home", "welcome", "our pleasure",
        "honored to have you",
    ]

    # ─── معايير احترام الكبار — Elder respect norms ─────────────────────
    _ELDER_RESPECT_MARKERS: list[str] = [
        "يا عم", "يا خال", "يا والدي", "يا أمي", "شيخنا",
        "أستاذنا", "يا طويل العمر", "رحم الله والديك",
        "uncle", "respected elder", "with respect to your experience",
    ]

    def evaluate(self, text: str, context: SocialContext | None = None) -> NormEvaluation:
        """
        تقييم المعايير — يقيّم الالتزام بالمعايير الاجتماعية.
        Evaluate adherence to social norms in the given text.

        Args:
            text: النص — text to evaluate
            context: السياق الاجتماعي — social context (optional)

        Returns:
            NormEvaluation — تقييم المعايير
        """
        if not text or not text.strip():
            return NormEvaluation(
                overall=0.5,
                suggestions=["لا يوجد نص كافٍ للتقييم — insufficient text for evaluation"],
            )

        context = context or SocialContext()

        # تقييم الأدب — Evaluate politeness
        politeness = self._check_politeness(text, context.formality)

        # تقييم الاحترام — Evaluate respect
        respect = self._check_respect(text, context)

        # تقييم الملاءمة — Evaluate appropriateness
        appropriateness = self._check_appropriateness(text, context)

        # حساب الدرجة الإجمالية — Compute overall score
        overall = (
            politeness.score * 0.35
            + respect.score * 0.35
            + appropriateness.score * 0.30
        )

        # توليد الاقتراحات — Generate suggestions
        suggestions = self._generate_suggestions(
            politeness, respect, appropriateness, context
        )

        logger.debug(
            "مقيّم المعايير: تقييم مكتمل — Evaluation complete | "
            "politeness=%.2f, respect=%.2f, appropriateness=%.2f, overall=%.2f",
            politeness.score, respect.score, appropriateness.score, overall,
        )

        return NormEvaluation(
            politeness=politeness,
            respect=respect,
            appropriateness=appropriateness,
            overall=overall,
            suggestions=suggestions,
        )

    def _check_politeness(
        self, text: str, formality: FormalityLevel
    ) -> PolitenessScore:
        """
        فحص الأدب — Check politeness level in text.
        يفحص مستوى الأدب واللباقة في النص.

        Args:
            text: النص — text to check
            formality: مستوى الرسمية — formality level

        Returns:
            PolitenessScore — درجة الأدب
        """
        positive_indicators: list[str] = []
        negative_indicators: list[str] = []

        # فحص المؤشرات العربية — Check Arabic indicators
        for marker in self._AR_POLITENESS_POSITIVE:
            if marker in text:
                positive_indicators.append(marker)

        for marker in self._AR_POLITENESS_NEGATIVE:
            if marker in text:
                negative_indicators.append(marker)

        # فحص المؤشرات الإنجليزية — Check English indicators
        text_lower = text.lower()
        for marker in self._EN_POLITENESS_POSITIVE:
            if marker in text_lower:
                positive_indicators.append(marker)

        for marker in self._EN_POLITENESS_NEGATIVE:
            if marker in text_lower:
                negative_indicators.append(marker)

        # حساب الدرجة — Compute score
        base_score = 0.5
        base_score += len(positive_indicators) * 0.1
        base_score -= len(negative_indicators) * 0.2

        # تعديل حسب الرسمية — Adjust for formality
        if formality == FormalityLevel.FORMAL:
            # في السياق الرسمي، الأدب مهم أكثر — politeness matters more
            if not positive_indicators and len(text.split()) > 5:
                base_score -= 0.1

        score = max(0.0, min(1.0, base_score))

        return PolitenessScore(
            score=score,
            indicators=positive_indicators[:10],
            violations=negative_indicators[:10],
        )

    def _check_respect(self, text: str, context: SocialContext) -> RespectScore:
        """
        فحص الاحترام — Check respect level in text.
        يفحص مستوى الاحترام المبدي في النص، بما في ذلك
        المعايير العربية/الإسلامية: احترام الكبار، الضيافة، الألقاب.

        Args:
            text: النص — text to check
            context: السياق الاجتماعي — social context

        Returns:
            RespectScore — درجة الاحترام
        """
        positive_indicators: list[str] = []
        negative_indicators: list[str] = []

        # فحص مؤشرات الاحترام العربي/Islamic — Check Arabic/Islamic respect markers
        for marker in self._AR_RESPECT_POSITIVE:
            if marker in text:
                positive_indicators.append(marker)

        for marker in self._AR_RESPECT_NEGATIVE:
            if marker in text:
                negative_indicators.append(marker)

        # فحص مؤشرات الاحترام الإنجليزية — Check English respect markers
        text_lower = text.lower()
        for marker in self._EN_RESPECT_POSITIVE:
            if marker in text_lower:
                positive_indicators.append(marker)

        for marker in self._EN_RESPECT_NEGATIVE:
            if marker in text_lower:
                negative_indicators.append(marker)

        # فحص معايير الضيافة — Check hospitality norms
        for marker in self._HOSPITALITY_MARKERS:
            if marker in text or marker in text_lower:
                positive_indicators.append(f"ضيافة: {marker}")

        # فحص احترام الكبار — Check elder respect norms
        for marker in self._ELDER_RESPECT_MARKERS:
            if marker in text or marker in text_lower:
                positive_indicators.append(f"احترام كبار: {marker}")

        # حساب الدرجة — Compute score
        base_score = 0.5
        base_score += len(positive_indicators) * 0.08
        base_score -= len(negative_indicators) * 0.2

        # تعزيز درجة احترام الكبار في السياق العربي/Islamic
        # Boost elder respect score in Arab/Islamic context
        has_cultural_religious = any(
            m.marker_type == MarkerType.RELIGIOUS
            for m in context.cultural_markers
        )
        if has_cultural_religious and positive_indicators:
            base_score += 0.05

        score = max(0.0, min(1.0, base_score))

        return RespectScore(
            score=score,
            indicators=positive_indicators[:10],
            violations=negative_indicators[:10],
        )

    def _check_appropriateness(
        self, text: str, context: SocialContext
    ) -> AppropriatenessScore:
        """
        فحص الملاءمة — Check appropriateness of text in context.
        يفحص مدى ملاءمة النص للسياق الاجتماعي.

        Args:
            text: النص — text to check
            context: السياق الاجتماعي — social context

        Returns:
            AppropriatenessScore — درجة الملاءمة
        """
        positive_indicators: list[str] = []
        negative_indicators: list[str] = []

        # فحص ملاءمة الرسمية — Check formality appropriateness
        text_lower = text.lower()

        # في السياق الرسمي، يجب تجنب اللغة العامية
        # In formal context, colloquial language should be avoided
        if context.formality == FormalityLevel.FORMAL:
            informal_found = [
                m for m in SocialContextAnalyzer._AR_INFORMAL_MARKERS
                + SocialContextAnalyzer._EN_INFORMAL_MARKERS
                if m in text or m in text_lower
            ]
            if informal_found:
                negative_indicators.append(
                    f"لغة غير رسمية في سياق رسمي: {', '.join(informal_found[:3])}"
                )

        # في السياق الحميم، الرسمية المفرطة قد تكون غير ملائمة
        # In intimate context, excessive formality may be inappropriate
        if context.formality == FormalityLevel.INTIMATE:
            formal_found = [
                m for m in SocialContextAnalyzer._AR_FORMAL_MARKERS
                + SocialContextAnalyzer._EN_FORMAL_MARKERS
                if m in text or m in text_lower
            ]
            if formal_found:
                negative_indicators.append(
                    f"رسمية مفرطة في سياق حميم: {', '.join(formal_found[:3])}"
                )

        # فحص الملاءمة الثقافية — Check cultural appropriateness
        # احترام المقدسات — Respect for the sacred
        sacred_violations = [
            pat for pat in [
                r"لعن[ةٍ]\s*الله",
                r"سب\s*(الله|الدين|الرسول|النبي)",
                r"استهزاء\s*(بـ|بال)\s*(دين|مقدس)",
            ]
            if re.search(pat, text)
        ]
        if sacred_violations:
            negative_indicators.append("محتوى مسيء للمقدسات — sacred content violation")

        # الترحيب بالضيوف — Welcoming guests
        hospitality_found = [
            m for m in self._HOSPITALITY_MARKERS
            if m in text or m in text_lower
        ]
        if hospitality_found:
            positive_indicators.append("تعبير ضيافة — hospitality expression")

        # احترام الكبار — Respect for elders
        elder_found = [
            m for m in self._ELDER_RESPECT_MARKERS
            if m in text or m in text_lower
        ]
        if elder_found:
            positive_indicators.append("احترام الكبار — elder respect")

        # حساب الدرجة — Compute score
        base_score = 0.6
        base_score += len(positive_indicators) * 0.08
        base_score -= len(negative_indicators) * 0.25

        score = max(0.0, min(1.0, base_score))

        return AppropriatenessScore(
            score=score,
            indicators=positive_indicators[:10],
            violations=negative_indicators[:10],
        )

    def _generate_suggestions(
        self,
        politeness: PolitenessScore,
        respect: RespectScore,
        appropriateness: AppropriatenessScore,
        context: SocialContext,
    ) -> list[str]:
        """
        توليد الاقتراحات — Generate improvement suggestions.
        يولّد اقتراحات لتحسين الالتزام بالمعايير الاجتماعية.

        Args:
            politeness: درجة الأدب
            respect: درجة الاحترام
            appropriateness: درجة الملاءمة
            context: السياق الاجتماعي

        Returns:
            list[str] — قائمة الاقتراحات
        """
        suggestions: list[str] = []

        # اقتراحات الأدب — Politeness suggestions
        if politeness.score < 0.5:
            suggestions.append(
                "يُنصح باستخدام عبارات الأدب مثل 'لو سمحت' و'شكراً' "
                "— Consider using polite expressions like 'please' and 'thank you'"
            )
        if politeness.violations:
            suggestions.append(
                "تجنب العبارات الفظة — Avoid rude expressions"
            )

        # اقتراحات الاحترام — Respect suggestions
        if respect.score < 0.5:
            suggestions.append(
                "يُنصح بإظهار الاحترام باستخدام الألقاب المناسبة "
                "— Consider showing respect with appropriate honorifics"
            )

        # اقتراحات الضيافة — Hospitality suggestions (Arab/Islamic context)
        has_hospitality_marker = any(
            m.marker_type == MarkerType.HOSPITALITY
            for m in context.cultural_markers
        )
        if context.formality in (FormalityLevel.FORMAL, FormalityLevel.SEMI_FORMAL):
            if not has_hospitality_marker and respect.score < 0.7:
                suggestions.append(
                    "في السياق العربي، يُقدَّر الترحيب بالضيوف والكرم "
                    "— In Arab context, welcoming guests and generosity are valued"
                )

        # اقتراحات احترام الكبار — Elder respect suggestions
        if respect.score < 0.6:
            suggestions.append(
                "احترام الكبار من القيم الأساسية في الثقافة العربية والإسلامية "
                "— Respecting elders is a core value in Arab/Islamic culture"
            )

        # اقتراحات الملاءمة — Appropriateness suggestions
        if appropriateness.violations:
            suggestions.append(
                "يُنصح بتعديل نبرة الحديث لتناسب السياق الاجتماعي "
                "— Consider adjusting tone to match the social context"
            )

        # اقتراحات التعاطف — Empathy suggestions
        if politeness.score < 0.6 and respect.score < 0.6:
            suggestions.append(
                "إظهار التعاطف والاستماع الفعال يعزز التواصل الاجتماعي "
                "— Showing empathy and active listening enhances social communication"
            )

        return suggestions[:8]  # الحد الأقصى 8 اقتراحات — max 8 suggestions


# ═══════════════════════════════════════════════════════════════════════════════
#  كاشف السخرية — SarcasmDetector
# ═══════════════════════════════════════════════════════════════════════════════


class SarcasmDetector:
    """
    كاشف السخرية — يكشف أنماط السخرية والتهكم في النص.
    Detects sarcasm and irony patterns in text using rule-based heuristics.

    Patterns detected:
    - Positive word + negative context marker (e.g., "Great, another bug")
    - Excessive positive words + exclamation (e.g., "Wonderful!!! Just wonderful!!!")
    - Arabic sarcasm patterns: "يا سلام", "أكيد يا سيدي", "شكراً كتير" in negative context
    أنماط السخرية المكتشفة:
    - كلمة إيجابية + علامة سياق سلبي
    - كلمات إيجابية مفرطة + علامة تعجب
    - أنماط سخرية عربية
    """

    # ─── أنماط السخرية الإنجليزية — English sarcasm patterns ─────────────
    _EN_SARCASM_PATTERNS: list[tuple[str, str]] = [
        # (pattern_regex, pattern_type)
        (r"\b(oh\s+)?great\b.*\b(bug|problem|issue|error|fail|broken)\b", "positive_negative_context"),
        (r"\bwonderful\W*!.*\bwonderful\W*!", "excessive_positive"),
        (r"\b(oh\s+)?(?:great|perfect|lovely|fantastic|brilliant)\b[,.]?\s*(?:another|yet\s+another|just\s+what)\b", "positive_negative_context"),
        (r"\byeah\s+right\b", "direct_sarcasm"),
        (r"\bsure[,\.]?\s*(?:that|it)\b", "minimal_agreement"),
        (r"\bthanks\s+a\s+lot\b", "insincere_gratitude"),
        (r"\bhow\s+nice\b", "insincere_praise"),
    ]

    # ─── أنماط السخرية العربية — Arabic sarcasm patterns ─────────────────
    _AR_SARCASM_MARKERS: list[tuple[str, str]] = [
        # (marker, pattern_type)
        ("يا سلام", "arabic_sarcastic_exclamation"),
        ("أكيد يا سيدي", "arabic_mock_agreement"),
        ("شكراً كتير", "arabic_insincere_gratitude"),
        ("يا سلام عليك", "arabic_sarcastic_exclamation"),
        ("شكراً جزيلاً", "arabic_insincere_gratitude"),
        ("أكيد طبعاً", "arabic_mock_agreement"),
        ("الله يبارك فيك", "arabic_sarcastic_blessing"),
        ("مش عايز حاجة", "arabic_rejection"),
        ("يا حلاوة", "arabic_sarcastic_exclamation"),
        ("عظيم جداً", "arabic_excessive_positive"),
    ]

    # ─── كلمات إيجابية محتملة للسخرية — Potential sarcasm positive words ─
    _SARCASM_POSITIVE_WORDS_EN: list[str] = [
        "great", "wonderful", "perfect", "lovely", "fantastic",
        "brilliant", "excellent", "amazing", "superb", "terrific",
    ]
    _SARCASM_NEGATIVE_CONTEXT_WORDS_EN: list[str] = [
        "bug", "problem", "issue", "error", "fail", "broken",
        "crash", "wrong", "mess", "disaster", "terrible", "awful",
    ]

    def detect_sarcasm(self, text: str) -> SarcasmIndicator:
        """
        كشف السخرية — يكشف السخرية والتهكم في النص.
        Detects sarcasm and irony in text.

        Args:
            text: النص — text to analyze

        Returns:
            SarcasmIndicator — مؤشر السخرية
        """
        if not text or not text.strip():
            return SarcasmIndicator()

        markers_found: list[str] = []
        confidence = 0.0
        pattern_type = ""

        # فحص أنماط السخرية الإنجليزية — Check English sarcasm patterns
        for pattern, ptype in self._EN_SARCASM_PATTERNS:
            if re.search(pattern, text.lower()):
                markers_found.append(f"en_pattern: {ptype}")
                confidence += 0.3
                pattern_type = ptype

        # فحص علامات السخرية العربية — Check Arabic sarcasm markers
        for marker, ptype in self._AR_SARCASM_MARKERS:
            if marker in text:
                markers_found.append(f"ar_marker: {marker}")
                confidence += 0.35
                pattern_type = ptype

        # فحص السياق الإيجابي + السلبي — Check positive + negative context
        text_lower = text.lower()
        has_positive = any(w in text_lower for w in self._SARCASM_POSITIVE_WORDS_EN)
        has_negative = any(w in text_lower for w in self._SARCASM_NEGATIVE_CONTEXT_WORDS_EN)
        if has_positive and has_negative:
            markers_found.append("positive_negative_mixed")
            confidence += 0.25
            if not pattern_type:
                pattern_type = "positive_negative_context"

        # فحص الإيجابية المفرطة مع علامات التعجب — Check excessive positive + exclamation
        positive_count = sum(1 for w in self._SARCASM_POSITIVE_WORDS_EN if w in text_lower)
        exclamation_count = text.count("!")
        if positive_count >= 2 and exclamation_count >= 2:
            markers_found.append("excessive_positive_with_exclamation")
            confidence += 0.2
            if not pattern_type:
                pattern_type = "excessive_positive"

        # تحديد النتيجة — Determine result
        confidence = min(1.0, confidence)
        is_sarcastic = confidence >= 0.3

        return SarcasmIndicator(
            is_sarcastic=is_sarcastic,
            confidence=confidence,
            markers_found=markers_found[:10],
            pattern_type=pattern_type,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  محلل المؤشرات الإعرابية — ProsodicAnalyzer
# ═══════════════════════════════════════════════════════════════════════════════


class ProsodicAnalyzer:
    """
    محلل المؤشرات الإعرابية — يحلل المؤشرات الصوتية والكتابية في النص.
    Analyzes prosodic and typographic indicators in text.

    Detects:
    - Exclamation marks (!) → high arousal
    - Question marks (?) → anticipation/curiosity
    - ALL CAPS text → emphasis (high arousal, often anger or excitement)
    - Repeated characters ("!!!" or "???") → intensifier
    - Repeated words → emphasis

    يكشف:
    - علامات التعجب → استثارة عالية
    - علامات الاستفهام → ترقب/فضول
    - النص بأحرف كبيرة → تأكيد
    - الأحرف المكررة → مكثّف
    - الكلمات المكررة → تأكيد
    """

    # ─── الحد الأدنى لنسبة الأحرف الكبيرة — Min ratio for ALL CAPS ──────
    _ALL_CAPS_MIN_RATIO = 0.5
    _ALL_CAPS_MIN_LENGTH = 4

    def analyze(self, text: str) -> ProsodicIndicators:
        """
        تحليل المؤشرات الإعرابية — Analyze prosodic indicators in text.
        يحلل المؤشرات الصوتية والكتابية في النص.

        Args:
            text: النص — text to analyze

        Returns:
            ProsodicIndicators — المؤشرات الإعرابية
        """
        if not text or not text.strip():
            return ProsodicIndicators()

        # حساب علامات التعجب — Count exclamation marks
        exclamation_count = text.count("!") + text.count("！")

        # حساب علامات الاستفهام — Count question marks
        question_count = text.count("?") + text.count("؟")

        # كشف النص بأحرف كبيرة — Detect ALL CAPS
        has_all_caps = self._detect_all_caps(text)

        # كشف الأحرف المكررة — Detect repeated characters
        repeated_chars = len(re.findall(r"([!?؟\u0600-\u06FF])\1{2,}", text))

        # كشف الكلمات المكررة — Detect repeated words
        repeated_words = self._detect_repeated_words(text)

        # حساب معدّلات الاستثارة والترقب — Compute arousal and anticipation modifiers
        arousal_modifier = 0.0
        anticipation_modifier = 0.0

        # علامات التعجب تزيد الاستثارة — Exclamation marks increase arousal
        if exclamation_count > 0:
            arousal_modifier += min(0.3, exclamation_count * 0.1)

        # النص بأحرف كبيرة يزيد الاستثارة — ALL CAPS increases arousal
        if has_all_caps:
            arousal_modifier += 0.3

        # الأحرف المكررة تزيد الاستثارة — Repeated characters increase arousal
        if repeated_chars > 0:
            arousal_modifier += min(0.2, repeated_chars * 0.05)

        # الكلمات المكررة تزيد الاستثارة — Repeated words increase arousal
        if repeated_words:
            arousal_modifier += min(0.2, len(repeated_words) * 0.1)

        # علامات الاستفهام تزيد الترقب — Question marks increase anticipation
        if question_count > 0:
            anticipation_modifier += min(0.3, question_count * 0.1)

        return ProsodicIndicators(
            exclamation_count=exclamation_count,
            question_count=question_count,
            has_all_caps=has_all_caps,
            repeated_chars=repeated_chars,
            repeated_words=repeated_words,
            arousal_modifier=arousal_modifier,
            anticipation_modifier=anticipation_modifier,
        )

    def _detect_all_caps(self, text: str) -> bool:
        """
        كشف النص بأحرف كبيرة — Detect if text contains ALL CAPS words.
        يبحث عن كلمات إنجليزية بأحرف كبيرة فقط.

        Args:
            text: النص — text to analyze

        Returns:
            bool — هل يوجد نص بأحرف كبيرة؟
        """
        # استخراج الكلمات الإنجليزية — Extract English words
        en_words = re.findall(r"\b[A-Za-z]+\b", text)

        if not en_words:
            return False

        # حساب نسبة الكلمات بأحرف كبيرة — Compute ratio of ALL CAPS words
        all_caps_words = [
            w for w in en_words
            if len(w) >= self._ALL_CAPS_MIN_LENGTH and w.isupper()
        ]

        return len(all_caps_words) >= 1

    def _detect_repeated_words(self, text: str) -> list[str]:
        """
        كشف الكلمات المكررة — Detect repeated words in text.
        يبحث عن الكلمات المتكررة المتتالية.

        Args:
            text: النص — text to analyze

        Returns:
            list[str] — الكلمات المكررة
        """
        repeated: list[str] = []
        # البحث عن كلمات مكررة متتالية — Find consecutive repeated words
        pattern = r"\b(\w+)\s+\1\b"
        matches = re.findall(pattern, text.lower())
        repeated.extend(matches)

        # البحث عن كلمات عربية مكررة — Find consecutive repeated Arabic words
        ar_pattern = r"([\u0600-\u06FF]+)\s+\1"
        ar_matches = re.findall(ar_pattern, text)
        repeated.extend(ar_matches)

        return list(set(repeated))[:10]


# ═══════════════════════════════════════════════════════════════════════════════
#  مستنتج الدور الاجتماعي — SocialRoleInference
# ═══════════════════════════════════════════════════════════════════════════════


class SocialRoleInference:
    """
    مستنتج الدور الاجتماعي — يستنتج دور المتحدث في المحادثة.
    Infers the social role of the speaker based on linguistic markers.

    Roles detected:
    - teacher, student, boss, employee, parent, child,
      host, guest, customer, service_provider

    الأدوار المكتشفة:
    - معلم، طالب، مدير، موظف، والد، طفل، مضيف، ضيف، عميل، مزوّد خدمة
    """

    # ─── علامات الأدوار الاجتماعية — Social role markers ─────────────────
    _ROLE_MARKERS: dict[str, list[str]] = {
        "teacher": [
            "اسمعوا", "انتبهوا", "دعوني أشرح", "الدرس اليوم", "كما تعلمون",
            "الواجب", "الامتحان", "listen class", "let me explain",
            "today's lesson", "homework", "as you know", "pay attention",
        ],
        "student": [
            "يا أستاذ", "سؤال يا دكتور", "ما فهمت", "ممكن توضح",
            "professor", "i have a question", "i don't understand",
            "can you explain", "could you clarify",
        ],
        "boss": [
            "أريد التقرير", "يجب أن تنتهي", "الموعد النهائي", "اجتمعوا",
            "i need the report", "this needs to be done", "deadline",
            "meeting in my office", "as your manager",
        ],
        "employee": [
            "سيدي", "حضرة المدير", "تم الانتهاء", "كما طلبت",
            "boss", "sir", "as requested", "i've completed",
            "for your review", "as discussed",
        ],
        "parent": [
            "يا بني", "يا بنتي", "لا تفعل هذا", "اسمع كلامي", "من أجل مستقبلك",
            "my child", "don't do that", "listen to me", "for your own good",
            "because i said so", "i'm your father", "i'm your mother",
        ],
        "child": [
            "يا أمي", "يا أبي", "ماما", "بابا", "أريد", "لماذا",
            "mommy", "daddy", "i want", "why can't i", "but mom",
        ],
        "host": [
            "أهلاً وسهلاً", "تفضل بالدخول", "بيتك بيتك", "ماذا تشرب",
            "welcome", "come in", "make yourself at home", "can i get you",
            "please sit down", "our house is your house",
        ],
        "guest": [
            "شكراً على الدعوة", "أعتذر عن الإزعاج", "مكان جميل",
            "thank you for inviting", "sorry to bother", "lovely place",
            "i appreciate the invitation", "you're too kind",
        ],
        "customer": [
            "أريد", "كم السعر", "هل يوجد خصم", "أريد استرجاع",
            "i'd like to buy", "how much", "is there a discount",
            "i want to return", "can i get a refund",
        ],
        "service_provider": [
            "كيف يمكنني مساعدتك", "تفضل بالطلب", "الخدمة متاحة",
            "how can i help", "what can i do for you", "at your service",
            "we offer", "available now", "let me assist you",
        ],
    }

    # ─── أوزان الثقة حسب نوع العلامة — Confidence weights by marker type
    _MARKER_CONFIDENCE: dict[str, float] = {
        "teacher": 0.6,
        "student": 0.6,
        "boss": 0.65,
        "employee": 0.65,
        "parent": 0.7,
        "child": 0.7,
        "host": 0.7,
        "guest": 0.6,
        "customer": 0.6,
        "service_provider": 0.6,
    }

    def infer_role(self, text: str) -> SocialRole:
        """
        استنتاج الدور الاجتماعي — Infer the social role from text.
        يستنتج دور المتحدث في المحادثة بناءً على العلامات اللغوية.

        Args:
            text: النص — text to analyze

        Returns:
            SocialRole — الدور الاجتماعي المكتشف
        """
        if not text or not text.strip():
            return SocialRole()

        best_role = ""
        best_confidence = 0.0
        best_markers: list[str] = []

        text_lower = text.lower()

        for role, markers in self._ROLE_MARKERS.items():
            found_markers: list[str] = []
            for marker in markers:
                if marker in text or marker in text_lower:
                    found_markers.append(marker)

            if found_markers:
                # حساب الثقة — Compute confidence
                base_conf = self._MARKER_CONFIDENCE.get(role, 0.5)
                marker_conf = min(0.3, len(found_markers) * 0.1)
                total_conf = min(1.0, base_conf + marker_conf)

                if total_conf > best_confidence:
                    best_confidence = total_conf
                    best_role = role
                    best_markers = found_markers

        return SocialRole(
            role=best_role,
            confidence=best_confidence,
            markers=best_markers[:10],
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  ذاكرة المحادثة — ConversationMemory
# ═══════════════════════════════════════════════════════════════════════════════


class ConversationMemory:
    """
    ذاكرة المحادثة — تحفظ تاريخ المحادثة وتتبع تحولات المشاعر.
    Stores conversation history and tracks emotion transitions over time.

    Features:
    - Stores recent conversation turns and their emotion profiles
    - Tracks emotion transitions over time
    - Detects emotional shifts (sudden change from joy to anger)
    - Provides context for better perception

    الميزات:
    - يحفظ أدوار المحادثة الأخيرة وملفات المشاعر
    - يتتبع انتقالات المشاعر عبر الزمن
    - يكشف التحولات العاطفية المفاجئة
    - يوفر السياق لإدراك أفضل
    """

    # ─── ثوابت — Constants ───────────────────────────────────────────────
    MAX_MEMORY_SIZE = 50          # الحد الأقصى للسجلات المحفوظة — max entries
    SHIFT_THRESHOLD = 0.5        # عتبة التحول المفاجئ — sudden shift threshold

    def __init__(self) -> None:
        """
        تهيئة ذاكرة المحادثة — Initialize conversation memory.
        """
        self._entries: list[ConversationMemoryEntry] = []
        self._emotion_history: list[str] = []  # تاريخ المشاعر السائدة

    def add_entry(
        self,
        text: str,
        emotion_profile: EmotionProfile,
        social_role: str = "",
    ) -> list[EmotionShift]:
        """
        إضافة سجل — Add a new entry to conversation memory.
        يضيف سجلاً جديداً إلى ذاكرة المحادثة ويكشف التحولات العاطفية.

        Args:
            text: النص — text
            emotion_profile: ملف المشاعر — emotion profile
            social_role: الدور الاجتماعي — social role

        Returns:
            list[EmotionShift] — التحولات العاطفية المكتشفة
        """
        entry = ConversationMemoryEntry(
            text=text,
            emotion_profile=emotion_profile,
            timestamp=time.time(),
            social_role=social_role,
        )

        self._entries.append(entry)
        self._emotion_history.append(emotion_profile.dominant_emotion)

        # تقليم السجلات — Trim memory
        if len(self._entries) > self.MAX_MEMORY_SIZE:
            self._entries = self._entries[-self.MAX_MEMORY_SIZE:]
            self._emotion_history = self._emotion_history[-self.MAX_MEMORY_SIZE:]

        # كشف التحولات العاطفية — Detect emotion shifts
        shifts = self._detect_emotion_shifts()

        return shifts

    def get_recent_entries(self, count: int = 10) -> list[ConversationMemoryEntry]:
        """
        الحصول على السجلات الأخيرة — Get recent conversation memory entries.
        يعيد آخر سجلات ذاكرة المحادثة.

        Args:
            count: عدد السجلات — number of entries

        Returns:
            list[ConversationMemoryEntry] — السجلات الأخيرة
        """
        return self._entries[-count:]

    def get_emotion_history(self) -> list[str]:
        """
        الحصول على تاريخ المشاعر — Get emotion history.
        يعيد تاريخ المشاعر السائدة عبر أدوار المحادثة.

        Returns:
            list[str] — تاريخ المشاعر
        """
        return list(self._emotion_history)

    def _detect_emotion_shifts(self) -> list[EmotionShift]:
        """
        كشف التحولات العاطفية — Detect emotion shifts.
        يكشف التحولات المفاجئة في المشاعر بين أدوار المحادثة.

        Returns:
            list[EmotionShift] — التحولات المكتشفة
        """
        shifts: list[EmotionShift] = []

        if len(self._emotion_history) < 2:
            return shifts

        # فحص آخر تحول — Check last transition
        prev_emotion = self._emotion_history[-2]
        curr_emotion = self._emotion_history[-1]

        if prev_emotion != curr_emotion:
            # حساب حجم التحول — Compute shift magnitude
            shift_magnitude = self._compute_shift_magnitude(prev_emotion, curr_emotion)

            is_sudden = shift_magnitude >= self.SHIFT_THRESHOLD

            shifts.append(EmotionShift(
                from_emotion=prev_emotion,
                to_emotion=curr_emotion,
                shift_magnitude=shift_magnitude,
                is_sudden=is_sudden,
            ))

        return shifts

    def _compute_shift_magnitude(self, from_emotion: str, to_emotion: str) -> float:
        """
        حساب حجم التحول العاطفي — Compute emotion shift magnitude.
        يحسب حجم التحول بين مشاعرين بناءً على التكافؤ والاستثارة.

        Args:
            from_emotion: المشاعر السابقة — previous emotion
            to_emotion: المشاعر الجديدة — new emotion

        Returns:
            float — حجم التحول (0-1)
        """
        va_from = EmotionDetector._VALENCE_AROUSAL.get(from_emotion, (0.0, 0.0))
        va_to = EmotionDetector._VALENCE_AROUSAL.get(to_emotion, (0.0, 0.0))

        # مسافة إقليدية في فضاء التكافؤ-الاستثارة — Euclidean distance in VA space
        distance = math.sqrt(
            (va_to[0] - va_from[0]) ** 2 + (va_to[1] - va_from[1]) ** 2
        )

        # تطبيع إلى [0, 1] — Normalize to [0, 1]
        max_distance = math.sqrt(2 * (2.0 ** 2))  # أقصى مسافة ممكنة — max possible distance
        return min(1.0, distance / max_distance)

    def clear(self) -> None:
        """
        مسح الذاكرة — Clear conversation memory.
        يمسح كل سجلات ذاكرة المحادثة.
        """
        self._entries.clear()
        self._emotion_history.clear()


# ═══════════════════════════════════════════════════════════════════════════════
#  محرك الإدراك الاجتماعي — SocialPerceptionEngine
# ═══════════════════════════════════════════════════════════════════════════════


class SocialPerceptionEngine:
    """
    محرك الإدراك الاجتماعي — المحرك الرئيسي للإدراك الاجتماعي.

    Orchestrates all social perception components to provide a comprehensive
    analysis of social interactions, including emotion detection, context
    analysis, conversational dynamics, norm evaluation, sarcasm detection,
    prosodic analysis, social role inference, and conversation memory.

    Usage:
        engine = SocialPerceptionEngine()
        result = await engine.perceive("مرحباً، كيف حالك؟", context={})
    """

    def __init__(self) -> None:
        """
        تهيئة محرك الإدراك الاجتماعي — Initialize the Social Perception Engine.
        يهيّئ جميع المكونات الفرعية للإدراك الاجتماعي.
        """
        self._emotion_detector = EmotionDetector()
        self._context_analyzer = SocialContextAnalyzer()
        self._dynamics_tracker = ConversationalDynamicsTracker()
        self._norm_evaluator = SocialNormEvaluator()
        self._sarcasm_detector = SarcasmDetector()
        self._prosodic_analyzer = ProsodicAnalyzer()
        self._role_inference = SocialRoleInference()
        self._conversation_memory = ConversationMemory()

        # إحصائيات الاستخدام — Usage statistics
        self._stats: dict[str, int | float] = {
            "perceive_calls": 0,
            "emotion_detections": 0,
            "context_analyses": 0,
            "dynamics_updates": 0,
            "norm_evaluations": 0,
            "total_turns_tracked": 0,
        }
        self._start_time = time.time()

        if SOCIAL_PERCEPTION_ENABLED:
            logger.info(
                "تم تفعيل محرك الإدراك الاجتماعي — Social Perception Engine enabled"
            )

    # ─── الواجهة الرئيسية — Public API ─────────────────────────────────

    async def perceive(
        self,
        text: str,
        context: dict | None = None,
    ) -> dict:
        """
        الإدراك الاجتماعي — نقطة الدخول الرئيسية للإدراك الاجتماعي.
        Main entry point: perceive and interpret social cues in text.

        Provides comprehensive social perception analysis including:
        - Emotion detection from text (with negation, intensity, emojis, dialects)
        - Social context analysis (formality, power, group, culture)
        - Conversational dynamics tracking
        - Social norm evaluation
        - Sarcasm/irony detection
        - Prosodic indicators analysis
        - Social role inference
        - Conversation memory and emotion shift detection
        - Culturally-aware recommendations

        Args:
            text: النص المراد تحليله — text to analyze
            context: سياق إضافي — additional context dict with keys:
                - "participants": list[str] — المشاركون
                - "speaker": str — المتحدث الحالي
                - "timestamp": float — الوقت

        Returns:
            dict — نتيجة الإدراك الاجتماعي الشاملة (SocialPerceptionReport as dict)
        """
        self._stats["perceive_calls"] += 1
        context = context or {}

        try:
            # 1. كشف المشاعر — Detect emotions (with negation, intensity, emoji, dialect)
            emotions = self._emotion_detector.detect_emotions(text)
            self._stats["emotion_detections"] += 1

            # 2. تحليل السياق الاجتماعي — Analyze social context
            participants = context.get("participants", [])
            social_context = self._context_analyzer.analyze_interaction(
                text, participants
            )
            self._stats["context_analyses"] += 1

            # 3. تتبع الديناميكيات — Track dynamics
            speaker = context.get("speaker", "unknown")
            timestamp = context.get("timestamp", time.time())
            turn = ConversationTurn(
                speaker=speaker,
                content=text,
                timestamp=timestamp,
                emotion=emotions.dominant_emotion,
            )
            dynamics = self._dynamics_tracker.track_turn(turn)
            self._stats["dynamics_updates"] += 1
            self._stats["total_turns_tracked"] += 1

            # 4. تقييم المعايير الاجتماعية — Evaluate social norms
            norms = self._norm_evaluator.evaluate(text, social_context)
            self._stats["norm_evaluations"] += 1

            # 5. كشف السخرية — Detect sarcasm
            sarcasm = self._sarcasm_detector.detect_sarcasm(text)

            # 6. تحليل المؤشرات الإعرابية — Analyze prosodic indicators
            prosodic = self._prosodic_analyzer.analyze(text)

            # تطبيق معدّلات المؤشرات الإعرابية على المشاعر — Apply prosodic modifiers
            emotions.arousal = max(-1.0, min(1.0, emotions.arousal + prosodic.arousal_modifier))
            emotions.valence = max(-1.0, min(1.0, emotions.valence))

            # 7. استنتاج الدور الاجتماعي — Infer social role
            social_role = self._role_inference.infer_role(text)

            # 8. تحديث ذاكرة المحادثة — Update conversation memory
            emotion_shifts = self._conversation_memory.add_entry(
                text=text,
                emotion_profile=emotions,
                social_role=social_role.role,
            )

            # كشف اللهجة — Detect dialect
            dialect_detected = self._emotion_detector.detect_dialect(text)

            # كشف النفي — Detect negation
            _, ar_negated = self._emotion_detector._detect_arabic_emotions(text)
            _, en_negated = self._emotion_detector._detect_english_emotions(text)
            negation_applied = ar_negated or en_negated

            # كشف معدّل الشدة — Detect intensity modifier
            intensity_modifier = self._emotion_detector._compute_intensity_modifier(text)

            # 9. توليد التوصيات — Generate recommendations
            recommendations = self._generate_recommendations(
                emotions, social_context, dynamics, norms
            )

            # إضافة توصيات بناءً على السخرية — Add sarcasm-based recommendations
            if sarcasm.is_sarcastic:
                recommendations.append(
                    "يبدو أن هناك سخرية في الكلام — يُنصح بالرد بحذر وعدم أخذ الكلام حرفياً "
                    "— Sarcasm detected; respond with care and don't take literally"
                )

            # إضافة توصيات بناءً على التحول العاطفي — Add emotion shift recommendations
            for shift in emotion_shifts:
                if shift.is_sudden:
                    recommendations.append(
                        f"تحول عاطفي مفاجئ من {shift.from_emotion} إلى {shift.to_emotion} — "
                        f"Sudden emotional shift from {shift.from_emotion} to {shift.to_emotion}"
                    )

            # إضافة توصيات بناءً على الدور الاجتماعي — Add role-based recommendations
            if social_role.role:
                recommendations.append(
                    f"الدور الاجتماعي المكتشف: {social_role.role} — "
                    f"Detected social role: {social_role.role}"
                )

            # إنشاء التقرير الشامل — Create comprehensive report
            report = SocialPerceptionReport(
                emotions=emotions,
                social_context=social_context,
                dynamics=dynamics,
                norms=norms,
                sarcasm=sarcasm,
                prosodic=prosodic,
                social_role=social_role,
                emotion_shifts=emotion_shifts,
                recommendations=recommendations[:10],
                dialect_detected=dialect_detected,
                negation_applied=negation_applied,
                intensity_modifier=intensity_modifier,
            )

            logger.info(
                "محرك الإدراك: إدراك مكتمل — Perception complete | "
                "dominant_emotion=%s, formality=%s, engagement=%.2f, norm_score=%.2f, "
                "sarcasm=%s, role=%s, dialect=%s",
                emotions.dominant_emotion,
                social_context.formality.value,
                dynamics.engagement,
                norms.overall,
                sarcasm.is_sarcastic,
                social_role.role,
                dialect_detected,
            )

            return report.to_dict()

        except Exception as exc:
            logger.error(
                "محرك الإدراك: خطأ في الإدراك — Perception error | %s", exc,
            )
            # إرجاع نتيجة فارغة بدلاً من الفشل — return empty result instead of failing
            error_report = SocialPerceptionReport(
                emotions=EmotionProfile(emotions={"neutral": 1.0}),
                recommendations=["حدث خطأ في التحليل — analysis error occurred"],
            )
            return error_report.to_dict()

    # ─── طرق داخلية — Internal methods ──────────────────────────────────

    def _generate_recommendations(
        self,
        emotions: EmotionProfile,
        social_context: SocialContext,
        dynamics: DynamicsUpdate,
        norms: NormEvaluation,
    ) -> list[str]:
        """
        توليد التوصيات — Generate social interaction recommendations.
        يولّد توصيات بناءً على تحليل المشاعر والسياق والمعايير.

        Args:
            emotions: ملف المشاعر
            social_context: السياق الاجتماعي
            dynamics: ديناميكيات المحادثة
            norms: تقييم المعايير

        Returns:
            list[str] — قائمة التوصيات
        """
        recommendations: list[str] = []

        # توصيات المشاعر — Emotion recommendations
        if emotions.dominant_emotion == "anger":
            recommendations.append(
                "المتحدث يبدو غاضباً — يُنصح بالرد بهدوء وتعاطف "
                "— Speaker appears angry; respond with calm and empathy"
            )
        elif emotions.dominant_emotion == "sadness":
            recommendations.append(
                "المتحدث يبدو حزيناً — يُنصح بإظهار التعاطف والدعم "
                "— Speaker appears sad; show empathy and support"
            )
        elif emotions.dominant_emotion == "joy":
            recommendations.append(
                "المتحدث يبدو سعيداً — مشاركة الفرح تعزز العلاقة "
                "— Speaker appears joyful; sharing joy strengthens the bond"
            )
        elif emotions.dominant_emotion == "fear":
            recommendations.append(
                "المتحدث يبدو خائفاً — يُنصح بتقديم الطمأنينة والأمان "
                "— Speaker appears fearful; provide reassurance and safety"
            )
        elif emotions.dominant_emotion == "gratitude":
            recommendations.append(
                "المتحدث يُظهر امتناناً — الرد بالشكر يعزز المودة "
                "— Speaker shows gratitude; reciprocating strengthens rapport"
            )

        # توصيات السياق — Context recommendations
        if social_context.formality == FormalityLevel.FORMAL:
            recommendations.append(
                "السياق رسمي — استخدم الألقاب واللغة الرسمية "
                "— Formal context; use honorifics and formal language"
            )
        elif social_context.formality == FormalityLevel.INTIMATE:
            recommendations.append(
                "السياق حميم — يمكن استخدام لغة أكثر دفئاً "
                "— Intimate context; warmer language is appropriate"
            )

        # توصيات ديناميكية القوة — Power dynamics recommendations
        if social_context.power_dynamics.direction == PowerDirection.SUPERIOR:
            recommendations.append(
                "المتحدث في موقف قوة — يُنصح بالاحترام والتهذيب "
                "— Speaker holds power; respond with respect and courtesy"
            )
        elif social_context.power_dynamics.direction == PowerDirection.SUBORDINATE:
            recommendations.append(
                "المتحدث في موقف ضعف — يُنصح باللطف والتشجيع "
                "— Speaker is in a subordinate position; be kind and encouraging"
            )

        # توصيات المعايير — Norm recommendations
        recommendations.extend(norms.suggestions[:3])

        # توصيات المشاركة — Engagement recommendations
        if dynamics.engagement < 0.3:
            recommendations.append(
                "مستوى المشاركة منخفض — حاول إشراك المتحدث أكثر "
                "— Low engagement; try to involve the speaker more"
            )

        # توصيات ثقافية — Cultural recommendations
        has_religious = any(
            m.marker_type == MarkerType.RELIGIOUS
            for m in social_context.cultural_markers
        )
        if has_religious:
            recommendations.append(
                "سياق ديني — احترام المقدسات والآداب الإسلامية مطلوب "
                "— Religious context; respect for sacred values is expected"
            )

        has_hospitality = any(
            m.marker_type == MarkerType.HOSPITALITY
            for m in social_context.cultural_markers
        )
        if has_hospitality:
            recommendations.append(
                "سياق ضيافة — الكرم والترحيب من القيم الأساسية "
                "— Hospitality context; generosity and welcome are core values"
            )

        return recommendations[:10]  # الحد الأقصى 10 توصيات — max 10

    # ─── الإحصائيات — Statistics ─────────────────────────────────────────

    def get_stats(self) -> dict:
        """
        الحصول على الإحصائيات — Get engine statistics.
        يعيد إحصائيات تشغيل محرك الإدراك الاجتماعي.

        Returns:
            dict — إحصائيات المحرك
        """
        uptime = time.time() - self._start_time
        stats = dict(self._stats)
        stats["uptime_seconds"] = round(uptime, 2)
        stats["enabled"] = SOCIAL_PERCEPTION_ENABLED
        return stats
