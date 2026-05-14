"""
BABSHARQII (Mamoun) v6.0 — Cultural Value Alignment Engine
محرك التوافق القيمي الثقافي — نظام شامل لمحاذاة سلوك الكائن الرقمي مع القيم الثقافية

Implements a comprehensive Cultural Value Alignment system inspired by
Constitutional AI (Anthropic), Hofstede's Cultural Dimensions theory,
the Moral Machine experiment, and inclusive AI research.

Architecture:
    CulturalAlignmentEngine
    ├── ValueConstitution (principle management)
    │   ├── Core principles (non-negotiable)
    │   ├── Cultural principles (context-dependent)
    │   └── Principle conflict resolution
    ├── CulturalContextDetector (identify cultural context)
    │   ├── Language/region detection
    │   ├── Norm sensitivity analysis
    │   └── Cultural dimension scoring (Hofstede-inspired)
    ├── AlignmentScorer (measure alignment with values)
    │   ├── Principle adherence scoring
    │   ├── Cultural sensitivity scoring
    │   └── Harm potential assessment
    └── BehaviorFilter (filter/modify output for alignment)
        ├── Output sanitization
        ├── Tone adjustment
        └── Recommendation modification

Research basis:
    - Constitutional AI (Anthropic): AI behavior guided by a constitution
    - Value Alignment via RLHF and Constitutional methods
    - Hofstede's Cultural Dimensions (1980/2001): quantifying cultural
      differences across 6 dimensions
    - Moral Machine experiment (MIT): understanding human moral preferences
      across cultures
    - Inclusive AI: avoiding cultural bias while respecting cultural diversity
    - Maqasid al-Shariah (Islamic legal philosophy): preservation of life,
      intellect, lineage, property, and religion

Env toggles:
    MAMOUN_CULTURAL_ALIGNMENT_ENABLED — تمكين/تعطيل التوافق الثقافي (الافتراضي: true)
    MAMOUN_CULTURAL_DEFAULT_CONTEXT — السياق الثقافي الافتراضي (الافتراضي: arab_islamic)
    MAMOUN_CULTURAL_ALIGNMENT_THRESHOLD — عتبة التوافق (الافتراضي: 0.7)
    MAMOUN_CULTURAL_STRICT_MODE — الوضع الصارم (الافتراضي: false)
"""

from __future__ import annotations

import os
import re
import time
import math
import logging
import hashlib
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# إعدادات البيئة — Environment Configuration
# ═══════════════════════════════════════════════════════════════════════════════

ENV_ENABLED: bool = os.environ.get(
    "MAMOUN_CULTURAL_ALIGNMENT_ENABLED", "true"
).lower() in ("true", "1", "yes", "on")

ENV_DEFAULT_CONTEXT: str = os.environ.get(
    "MAMOUN_CULTURAL_DEFAULT_CONTEXT", "arab_islamic"
).lower()

ENV_ALIGNMENT_THRESHOLD: float = float(
    os.environ.get("MAMOUN_CULTURAL_ALIGNMENT_THRESHOLD", "0.7")
)

ENV_STRICT_MODE: bool = os.environ.get(
    "MAMOUN_CULTURAL_STRICT_MODE", "false"
).lower() in ("true", "1", "yes", "on")


# ═══════════════════════════════════════════════════════════════════════════════
# ثوابت النظام — System Constants
# ═══════════════════════════════════════════════════════════════════════════════

# أنواع الانتهاكات — Violation categories
VIOLATION_HARM = "harm"                    # ضرر
VIOLATION_DIGNITY = "dignity"              # كرامة
VIOLATION_PRIVACY = "privacy"              # خصوصية
VIOLATION_TRUTH = "truth"                  # صدق
VIOLATION_JUSTICE = "justice"              # عدالة
VIOLATION_PARENTS = "parents"              # والدين
VIOLATION_HOSPITALITY = "hospitality"       # ضيافة
VIOLATION_LINEAGE = "lineage"              # نسَل
VIOLATION_SACRED = "sacred"                # مقدسات
VIOLATION_TOLERANCE = "tolerance"          # تسامح

# مستويات الحساسية — Sensitivity levels
SENSITIVITY_LOW = "low"
SENSITIVITY_MEDIUM = "medium"
SENSITIVITY_HIGH = "high"
SENSITIVITY_CRITICAL = "critical"

# أنواع الضرر — Harm types
HARM_PHYSICAL = "physical"                 # ضرر جسدي
HARM_PSYCHOLOGICAL = "psychological"       # ضرر نفسي
HARM_SOCIAL = "social"                     # ضرر اجتماعي
HARM_FINANCIAL = "financial"               # ضرر مالي

# أوزان التسجيل — Scoring weights
WEIGHT_PRINCIPLE_SCORE = 0.40              # وزن نقاط المبادئ
WEIGHT_CULTURAL_SCORE = 0.30               # وزن الحساسية الثقافية
WEIGHT_HARM_SCORE = 0.30                   # وزن تقييم الضرر

# أوزان الأبعاد الثقافية (هوفستيد) — Hofstede dimension weights
WEIGHT_POWER_DISTANCE = 0.15
WEIGHT_INDIVIDUALISM = 0.20
WEIGHT_MASCULINITY = 0.10
WEIGHT_UNCERTAINTY_AVOIDANCE = 0.20
WEIGHT_LONG_TERM_ORIENTATION = 0.20
WEIGHT_INDULGENCE = 0.15

# السياقات الثقافية المدعومة — Supported cultural contexts
SUPPORTED_CONTEXTS: list[str] = [
    "arab_islamic",      # عربي إسلامي
    "arab_christian",    # عربي مسيحي
    "western_eu",        # أوروبي غربي
    "north_american",    # أمريكي شمالي
    "east_asian",        # شرق آسيوي
    "south_asian",       # جنوب آسيوي
    "sub_saharan",       # أفريقي جنوب الصحراء
    "latin_american",    # أمريكي لاتيني
    "universal",         # عالمي (محايد ثقافياً)
]

# أنماط كشف اللغة العربية — Arabic language detection patterns
ARABIC_UNICODE_RANGE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+")
ARABIC_RATIO_THRESHOLD = 0.15  # نسبة الحروف العربية لاعتبار النص عربياً

# كلمات مفتاحية للسياق الثقافي — Cultural context keywords
CONTEXT_KEYWORDS_ARAB_ISLAMIC: list[str] = [
    "الله", "الإسلام", "مسجد", "صلاة", "رمضان", "حلال", "حرام",
    "قرآن", "نبي", "شهادة", "زكاة", "حج", "عمرة", "إمام", "خليفة",
    "شريعة", "فتوى", "مفتي", "محكمة شرعية", "أوقاف",
]

CONTEXT_KEYWORDS_ARAB_GENERAL: list[str] = [
    "يا أخي", "يا أختي", "والله", "تكرم", "عيني", "أهلاً وسهلاً",
    "تفضل", "يسعدني", "مع السلامة", "يحييك", "كرم", "ضيافة",
    "عائلة", "عشيرة", "قبيلة", "شرف", "وجاهة", "سيد",
]

CONTEXT_KEYWORDS_SACRED: list[str] = [
    "مقدسات", "القرآن", "التوراة", "الإنجيل", "الكعبة",
    "المسجد الأقصى", "القدس", "مكة", "المدينة", "رسول",
    "نبي الله", "آل البيت", "الصحابة",
]

# أنماط المحتوى المسيء — Offensive content patterns
OFFENSIVE_PATTERNS_AR: list[str] = [
    r"لعن[ةٍ]\s*الله",
    r"سب\s*(الله|الدين|الرسول|النبي)",
    r"كفر\s*(بـ|بال)",
    r"استهزاء\s*(بـ|بال)\s*(دين|مقدس)",
    r"تحقير\s*(العرق|الجنس|الدين)",
]

OFFENSIVE_PATTERNS_EN: list[str] = [
    r"\bblasphem\w+\b",
    r"\bheret\w+\b",
    r"\binsult\s+(?:the|islam|muslim|prophet|quran|religion)",
    r"\bmock(?:ery|ing)?\s+(?:the|sacred|holy|divine|prophet)",
    r"\bdiscriminat\w+\s+(?:against|on\s+basis\s+of)",
]


# ═══════════════════════════════════════════════════════════════════════════════
# تصنيفات البيانات — Enumerations
# ═══════════════════════════════════════════════════════════════════════════════

class PrincipleCategory(str, Enum):
    """تصنيفات المبادئ — Principle categories"""
    CORE = "core"                          # مبدأ جوهري — non-negotiable
    CULTURAL = "cultural"                  # مبدأ ثقافي — context-dependent
    SITUATIONAL = "situational"            # مبدأ ظرفي — depends on situation


class ToneLevel(str, Enum):
    """مستويات النبرة — Tone levels for output adjustment"""
    FORMAL = "formal"                      # رسمي
    SEMI_FORMAL = "semi_formal"            # شبه رسمي
    INFORMAL = "informal"                  # غير رسمي
    RESPECTFUL = "respectful"              # محترم (فوق الرسمي)


class HarmSeverity(str, Enum):
    """شدة الضرر — Harm severity levels"""
    NONE = "none"                          # لا ضرر
    MINIMAL = "minimal"                    # ضرر طفيف
    MODERATE = "moderate"                  # ضرر متوسط
    SEVERE = "severe"                      # ضرر شديد
    CRITICAL = "critical"                  # ضرر حرج


class ConflictResolutionStrategy(str, Enum):
    """استراتيجيات حل التعارض — Conflict resolution strategies"""
    CORE_PRIORITY = "core_priority"        # المبادئ الجوهرية تتقدم
    WEIGHT_BASED = "weight_based"          # حسب الوزن النسبي
    CONTEXT_DEPENDENT = "context_dependent"  # حسب السياق الثقافي
    HARM_MINIMIZATION = "harm_minimization"  # تقليل الضرر أولاً


# ═══════════════════════════════════════════════════════════════════════════════
# هياكل البيانات — Dataclasses
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CulturalDimension:
    """
    الأبعاد الثقافية (هوفستيد) — Cultural dimensions (Hofstede-inspired).
    يمثل الأبعاد الستة للقيم الثقافية وفقاً لنموذج هوفستيد.
    """
    power_distance: float = 80.0            # المسافة السلطوية (0-100)
    individualism: float = 30.0             # الفردية مقابل الجماعية (0-100)
    masculinity: float = 55.0               # الذكورة مقابل الأنوثة (0-100)
    uncertainty_avoidance: float = 70.0     # تجنب عدم اليقين (0-100)
    long_term_orientation: float = 50.0     # التوجه طويل المدى (0-100)
    indulgence: float = 35.0                # التسامح/الاستمتاع (0-100)

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "power_distance": round(self.power_distance, 2),
            "individualism": round(self.individualism, 2),
            "masculinity": round(self.masculinity, 2),
            "uncertainty_avoidance": round(self.uncertainty_avoidance, 2),
            "long_term_orientation": round(self.long_term_orientation, 2),
            "indulgence": round(self.indulgence, 2),
        }

    def normalize(self) -> CulturalDimension:
        """تطبيع القيم بين 0 و1 — Normalize values to 0-1 range"""
        return CulturalDimension(
            power_distance=self.power_distance / 100.0,
            individualism=self.individualism / 100.0,
            masculinity=self.masculinity / 100.0,
            uncertainty_avoidance=self.uncertainty_avoidance / 100.0,
            long_term_orientation=self.long_term_orientation / 100.0,
            indulgence=self.indulgence / 100.0,
        )


@dataclass
class Principle:
    """
    مبدأ قيمي — A value principle in the constitution.
    يمثل مبدأً من مبادئ الدستور القيمي مع معلوماته الكاملة.
    """
    id: str = ""                            # معرف المبدأ
    text_ar: str = ""                       # نص المبدأ بالعربية
    text_en: str = ""                       # نص المبدأ بالإنجليزية
    category: PrincipleCategory = PrincipleCategory.CORE  # تصنيف المبدأ
    weight: float = 1.0                     # الوزن النسبي (0-1)
    is_core: bool = True                    # هل هو مبدأ جوهري؟
    violations: list[str] = field(default_factory=list)   # أنواع الانتهاكات
    cultural_contexts: list[str] = field(default_factory=list)  # السياقات المطبقة

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "id": self.id,
            "text_ar": self.text_ar,
            "text_en": self.text_en,
            "category": self.category.value,
            "weight": round(self.weight, 4),
            "is_core": self.is_core,
            "violations": self.violations,
            "cultural_contexts": self.cultural_contexts,
        }


@dataclass
class CulturalContext:
    """
    السياق الثقافي — Detected cultural context of interaction.
    يمثل السياق الثقافي المكتشف من النص أو الجلسة.
    """
    region: str = "arab_islamic"            # المنطقة الثقافية
    language: str = "arabic"                # اللغة المكتشفة
    dimensions: CulturalDimension = field(default_factory=CulturalDimension)  # الأبعاد الثقافية
    sensitivity_level: str = SENSITIVITY_MEDIUM  # مستوى الحساسية
    confidence: float = 0.0                 # ثقة الكشف (0-1)
    detected_keywords: list[str] = field(default_factory=list)  # كلمات مفتاحية مكتشفة

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "region": self.region,
            "language": self.language,
            "dimensions": self.dimensions.to_dict(),
            "sensitivity_level": self.sensitivity_level,
            "confidence": round(self.confidence, 4),
            "detected_keywords": self.detected_keywords,
        }


@dataclass
class AlignmentScore:
    """
    نقاط التوافق — Alignment scoring result.
    يمثل نقاط التوافق مع المبادئ القيمية والسياق الثقافي.
    """
    principle_score: float = 0.0            # نقاط الالتزام بالمبادئ (0-1)
    cultural_score: float = 0.0             # نقاط الحساسية الثقافية (0-1)
    harm_score: float = 0.0                 # نقاط الضرر المحتمل (0-1, 0 = لا ضرر)
    overall: float = 0.0                    # النقاط الإجمالية (0-1)
    details: dict = field(default_factory=dict)  # تفاصيل إضافية

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "principle_score": round(self.principle_score, 4),
            "cultural_score": round(self.cultural_score, 4),
            "harm_score": round(self.harm_score, 4),
            "overall": round(self.overall, 4),
            "details": self.details,
        }


@dataclass
class HarmAssessment:
    """
    تقييم الضرر — Harm potential assessment.
    يمثل تقييم الضرر المحتمل عبر أنواع متعددة.
    """
    physical_harm: float = 0.0              # ضرر جسدي (0-1)
    psychological_harm: float = 0.0         # ضرر نفسي (0-1)
    social_harm: float = 0.0                # ضرر اجتماعي (0-1)
    financial_harm: float = 0.0             # ضرر مالي (0-1)
    overall_harm: float = 0.0               # الضرر الإجمالي (0-1)
    severity: HarmSeverity = HarmSeverity.NONE  # شدة الضرر

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "physical_harm": round(self.physical_harm, 4),
            "psychological_harm": round(self.psychological_harm, 4),
            "social_harm": round(self.social_harm, 4),
            "financial_harm": round(self.financial_harm, 4),
            "overall_harm": round(self.overall_harm, 4),
            "severity": self.severity.value,
        }


@dataclass
class PrincipleViolation:
    """
    انتهاك مبدأ — A detected principle violation.
    يمثل انتهاكاً لمبدأ من مبادئ الدستور القيمي.
    """
    principle_id: str = ""                  # معرف المبدأ المنتهك
    principle_text_ar: str = ""             # نص المبدأ بالعربية
    principle_text_en: str = ""             # نص المبدأ بالإنجليزية
    severity: float = 0.0                   # شدة الانتهاك (0-1)
    explanation: str = ""                   # شرح الانتهاك
    offending_segment: str = ""             # الجزء المسيء

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "principle_id": self.principle_id,
            "principle_text_ar": self.principle_text_ar,
            "principle_text_en": self.principle_text_en,
            "severity": round(self.severity, 4),
            "explanation": self.explanation,
            "offending_segment": self.offending_segment[:200],
        }


@dataclass
class AlignmentResult:
    """
    نتيجة التوافق — Complete cultural alignment result.
    نتيجة شاملة لتحليل التوافق الثقافي تشمل النقاط والانتهاكات والتوصيات.
    """
    score: AlignmentScore = field(default_factory=AlignmentScore)  # نقاط التوافق
    violations: list[PrincipleViolation] = field(default_factory=list)  # الانتهاكات
    recommendations: list[str] = field(default_factory=list)  # التوصيات
    filtered_output: str = ""               # النص المُعدَّل
    context: Optional[CulturalContext] = None  # السياق المكتشف
    is_aligned: bool = True                 # هل النص متوافق؟
    passed_threshold: bool = True           # هل تجاوز العتبة؟

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "score": self.score.to_dict(),
            "violations": [v.to_dict() for v in self.violations],
            "recommendations": self.recommendations,
            "filtered_output": self.filtered_output,
            "context": self.context.to_dict() if self.context else None,
            "is_aligned": self.is_aligned,
            "passed_threshold": self.passed_threshold,
        }


@dataclass
class AlignmentStats:
    """
    إحصائيات المحرك — Engine statistics.
    إحصائيات تشغيل محرك التوافق الثقافي.
    """
    total_alignments: int = 0               # عدد عمليات التوافق
    total_violations: int = 0               # عدد الانتهاكات
    total_filtered: int = 0                 # عدد عمليات الترشيح
    average_score: float = 0.0              # متوسط النقاط
    context_distribution: dict = field(default_factory=dict)  # توزيع السياقات
    violation_distribution: dict = field(default_factory=dict)  # توزيع الانتهاكات
    uptime_start: float = 0.0               # وقت بدء التشغيل

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "total_alignments": self.total_alignments,
            "total_violations": self.total_violations,
            "total_filtered": self.total_filtered,
            "average_score": round(self.average_score, 4),
            "context_distribution": self.context_distribution,
            "violation_distribution": self.violation_distribution,
            "uptime_seconds": round(time.time() - self.uptime_start, 2) if self.uptime_start else 0,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# الدستور القيمي — ValueConstitution
# ═══════════════════════════════════════════════════════════════════════════════

class ValueConstitution:
    """
    الدستور القيمي — Value Constitution for BABSHARQII.

    يحتوي على المبادئ الجوهرية (غير القابلة للتفاوض) والمبادئ الثقافية
    (التي تعتمد على السياق) مع آلية حل التعارضات.

    Constitution of principles:
    - Core principles: universal, non-negotiable values
    - Cultural principles: context-dependent values
    - Conflict resolution: priority hierarchy when principles clash
    """

    def __init__(self, strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.CORE_PRIORITY):
        """
        تهيئة الدستور القيمي.

        Args:
            strategy: استراتيجية حل التعارض بين المبادئ
        """
        self._strategy = strategy
        self._principles: dict[str, Principle] = {}
        self._conflict_history: list[dict] = []
        self._initialize_default_principles()
        logger.info(
            "الدستور القيمي: تم التهيئة — Value Constitution initialized | "
            "principles=%d, strategy=%s",
            len(self._principles),
            self._strategy.value,
        )

    def _initialize_default_principles(self) -> None:
        """تهيئة المبادئ الافتراضية — Initialize default principles."""

        # ─── المبادئ الجوهرية — Core Principles (non-negotiable) ───
        core_principles: list[Principle] = [
            Principle(
                id="core_no_harm",
                text_ar="لا ضرر ولا ضرار",
                text_en="No harm shall be inflicted or reciprocated",
                category=PrincipleCategory.CORE,
                weight=1.0,
                is_core=True,
                violations=[VIOLATION_HARM],
                cultural_contexts=SUPPORTED_CONTEXTS,
            ),
            Principle(
                id="core_dignity",
                text_ar="حفظ الكرامة الإنسانية",
                text_en="Preserve human dignity",
                category=PrincipleCategory.CORE,
                weight=1.0,
                is_core=True,
                violations=[VIOLATION_DIGNITY],
                cultural_contexts=SUPPORTED_CONTEXTS,
            ),
            Principle(
                id="core_privacy",
                text_ar="احترام الخصوصية",
                text_en="Respect privacy",
                category=PrincipleCategory.CORE,
                weight=0.95,
                is_core=True,
                violations=[VIOLATION_PRIVACY],
                cultural_contexts=SUPPORTED_CONTEXTS,
            ),
            Principle(
                id="core_truthfulness",
                text_ar="الصدق والأمانة",
                text_en="Truthfulness and honesty",
                category=PrincipleCategory.CORE,
                weight=0.95,
                is_core=True,
                violations=[VIOLATION_TRUTH],
                cultural_contexts=SUPPORTED_CONTEXTS,
            ),
            Principle(
                id="core_justice",
                text_ar="العدالة وعدم التمييز",
                text_en="Justice and non-discrimination",
                category=PrincipleCategory.CORE,
                weight=0.95,
                is_core=True,
                violations=[VIOLATION_JUSTICE],
                cultural_contexts=SUPPORTED_CONTEXTS,
            ),
        ]

        # ─── المبادئ الثقافية — Cultural Principles (context-dependent) ───
        cultural_principles: list[Principle] = [
            Principle(
                id="cult_respect_parents",
                text_ar="احترام الوالدين",
                text_en="Respect for parents",
                category=PrincipleCategory.CULTURAL,
                weight=0.85,
                is_core=False,
                violations=[VIOLATION_PARENTS],
                cultural_contexts=["arab_islamic", "arab_christian", "east_asian", "south_asian"],
            ),
            Principle(
                id="cult_hospitality",
                text_ar="الكرم والضيافة",
                text_en="Generosity and hospitality",
                category=PrincipleCategory.CULTURAL,
                weight=0.75,
                is_core=False,
                violations=[VIOLATION_HOSPITALITY],
                cultural_contexts=["arab_islamic", "arab_christian"],
            ),
            Principle(
                id="cult_preserve_lineage",
                text_ar="حفظ النسل",
                text_en="Preservation of lineage",
                category=PrincipleCategory.CULTURAL,
                weight=0.80,
                is_core=False,
                violations=[VIOLATION_LINEAGE],
                cultural_contexts=["arab_islamic"],
            ),
            Principle(
                id="cult_respect_sacred",
                text_ar="احترام القدسات",
                text_en="Respect for the sacred",
                category=PrincipleCategory.CULTURAL,
                weight=0.90,
                is_core=False,
                violations=[VIOLATION_SACRED],
                cultural_contexts=["arab_islamic", "arab_christian"],
            ),
            Principle(
                id="cult_tolerance",
                text_ar="التسامح والتعايش",
                text_en="Tolerance and coexistence",
                category=PrincipleCategory.CULTURAL,
                weight=0.80,
                is_core=False,
                violations=[VIOLATION_TOLERANCE],
                cultural_contexts=SUPPORTED_CONTEXTS,
            ),
        ]

        # تسجيل جميع المبادئ — register all principles
        for principle in core_principles + cultural_principles:
            self._principles[principle.id] = principle

    def add_principle(self, principle: Principle) -> None:
        """
        إضافة مبدأ جديد — Add a new principle to the constitution.

        Args:
            principle: المبدأ المراد إضافته
        """
        if not principle.id:
            logger.warning("الدستور القيمي: محاولة إضافة مبدأ بدون معرف — skipped")
            return
        self._principles[principle.id] = principle
        logger.info(
            "الدستور القيمي: مبدأ مضاف — Principle added | id=%s, core=%s",
            principle.id, principle.is_core,
        )

    def remove_principle(self, principle_id: str) -> bool:
        """
        إزالة مبدأ — Remove a principle from the constitution.
        المبادئ الجوهرية لا يمكن إزالتها.

        Args:
            principle_id: معرف المبدأ المراد إزالته

        Returns:
            bool — هل تمت الإزالة بنجاح؟
        """
        principle = self._principles.get(principle_id)
        if principle is None:
            return False
        if principle.is_core:
            logger.warning(
                "الدستور القيمي: لا يمكن إزالة مبدأ جوهري — Cannot remove core principle | id=%s",
                principle_id,
            )
            return False
        del self._principles[principle_id]
        logger.info("الدستور القيمي: مبدأ محذوف — Principle removed | id=%s", principle_id)
        return True

    def get_principles(
        self,
        category: PrincipleCategory | None = None,
        context: str | None = None,
    ) -> list[Principle]:
        """
        الحصول على المبادئ — Get principles, optionally filtered.

        Args:
            category: تصفية حسب التصنيف (اختياري)
            context: تصفية حسب السياق الثقافي (اختياري)

        Returns:
            list[Principle] — قائمة المبادئ المفلترة
        """
        principles = list(self._principles.values())

        if category is not None:
            principles = [p for p in principles if p.category == category]

        if context is not None:
            principles = [
                p for p in principles
                if not p.cultural_contexts or context in p.cultural_contexts
            ]

        return principles

    def get_principle(self, principle_id: str) -> Optional[Principle]:
        """الحصول على مبدأ بالمعرف — Get a principle by ID."""
        return self._principles.get(principle_id)

    def resolve_conflict(
        self,
        principle_a: Principle,
        principle_b: Principle,
    ) -> Principle:
        """
        حل التعارض بين مبدأين — Resolve conflict between two principles.

        Args:
            principle_a: المبدأ الأول
            principle_b: المبدأ الثاني

        Returns:
            Principle — المبدأ الأسبق
        """
        # تسجيل التعارض — log the conflict
        conflict_record = {
            "principle_a": principle_a.id,
            "principle_b": principle_b.id,
            "strategy": self._strategy.value,
            "timestamp": time.time(),
        }

        if self._strategy == ConflictResolutionStrategy.CORE_PRIORITY:
            # المبادئ الجوهرية لها الأولوية — core principles take priority
            if principle_a.is_core and not principle_b.is_core:
                winner = principle_a
            elif principle_b.is_core and not principle_a.is_core:
                winner = principle_b
            else:
                winner = principle_a if principle_a.weight >= principle_b.weight else principle_b

        elif self._strategy == ConflictResolutionStrategy.WEIGHT_BASED:
            winner = principle_a if principle_a.weight >= principle_b.weight else principle_b

        elif self._strategy == ConflictResolutionStrategy.HARM_MINIMIZATION:
            # المبدأ الأكثر صلة بتقليل الضرر يتقدم — harm reduction wins
            harm_principle = next(
                (p for p in [principle_a, principle_b] if VIOLATION_HARM in p.violations),
                principle_a,
            )
            winner = harm_principle

        else:
            # الافتراضي: الجوهري أولاً ثم الوزن — default: core first, then weight
            if principle_a.is_core and not principle_b.is_core:
                winner = principle_a
            elif principle_b.is_core and not principle_a.is_core:
                winner = principle_b
            else:
                winner = principle_a if principle_a.weight >= principle_b.weight else principle_b

        conflict_record["winner"] = winner.id
        self._conflict_history.append(conflict_record)

        logger.debug(
            "الدستور القيمي: تعارض محلول — Conflict resolved | "
            "%s vs %s → %s",
            principle_a.id, principle_b.id, winner.id,
        )

        return winner

    def get_conflict_history(self, limit: int = 50) -> list[dict]:
        """
        سجل التعارضات — Get conflict resolution history.

        Args:
            limit: الحد الأقصى للسجلات

        Returns:
            list[dict] — سجل التعارضات
        """
        return self._conflict_history[-limit:]


# ═══════════════════════════════════════════════════════════════════════════════
# كاشف السياق الثقافي — CulturalContextDetector
# ═══════════════════════════════════════════════════════════════════════════════

class CulturalContextDetector:
    """
    كاشف السياق الثقافي — Detects cultural context from text input.

    يحلل النص لتحديد اللغة والمنطقة الثقافية ومستوى الحساسية
    والأبعاد الثقافية وفقاً لنموذج هوفستيد المُعدَّل.

    Detection capabilities:
    - Language detection (Arabic vs English vs other)
    - Region detection from context clues
    - Cultural dimension scoring (Hofstede model)
    - Sensitivity level determination (low/medium/high/critical)
    """

    # الأبعاد الثقافية المُعرَّفة مسبقاً — Pre-defined cultural dimensions
    # بناءً على بيانات هوفستيد المُعدَّلة — Based on adapted Hofstede data
    _CULTURAL_DIMENSIONS: dict[str, CulturalDimension] = {
        "arab_islamic": CulturalDimension(
            power_distance=80, individualism=30, masculinity=55,
            uncertainty_avoidance=70, long_term_orientation=50, indulgence=35,
        ),
        "arab_christian": CulturalDimension(
            power_distance=75, individualism=35, masculinity=50,
            uncertainty_avoidance=65, long_term_orientation=45, indulgence=40,
        ),
        "western_eu": CulturalDimension(
            power_distance=35, individualism=75, masculinity=45,
            uncertainty_avoidance=40, long_term_orientation=65, indulgence=65,
        ),
        "north_american": CulturalDimension(
            power_distance=40, individualism=85, masculinity=55,
            uncertainty_avoidance=35, long_term_orientation=55, indulgence=70,
        ),
        "east_asian": CulturalDimension(
            power_distance=75, individualism=25, masculinity=65,
            uncertainty_avoidance=60, long_term_orientation=80, indulgence=30,
        ),
        "south_asian": CulturalDimension(
            power_distance=80, individualism=30, masculinity=55,
            uncertainty_avoidance=45, long_term_orientation=55, indulgence=30,
        ),
        "sub_saharan": CulturalDimension(
            power_distance=70, individualism=25, masculinity=45,
            uncertainty_avoidance=55, long_term_orientation=35, indulgence=40,
        ),
        "latin_american": CulturalDimension(
            power_distance=70, individualism=25, masculinity=55,
            uncertainty_avoidance=75, long_term_orientation=25, indulgence=45,
        ),
        "universal": CulturalDimension(
            power_distance=50, individualism=50, masculinity=50,
            uncertainty_avoidance=50, long_term_orientation=50, indulgence=50,
        ),
    }

    def __init__(self, default_context: str = ENV_DEFAULT_CONTEXT):
        """
        تهيئة كاشف السياق الثقافي.

        Args:
            default_context: السياق الثقافي الافتراضي
        """
        self._default_context = default_context if default_context in SUPPORTED_CONTEXTS else "arab_islamic"

    def detect_context(self, text: str) -> CulturalContext:
        """
        كشف السياق الثقافي — Detect cultural context from text.

        Args:
            text: النص المراد تحليله

        Returns:
            CulturalContext — السياق الثقافي المكتشف
        """
        if not text or not text.strip():
            return CulturalContext(
                region=self._default_context,
                language="unknown",
                dimensions=self._CULTURAL_DIMENSIONS.get(
                    self._default_context, CulturalDimension()
                ),
                sensitivity_level=SENSITIVITY_LOW,
                confidence=0.0,
            )

        # كشف اللغة — detect language
        language = self._detect_language(text)

        # كشف المنطقة — detect region
        region, region_confidence, detected_keywords = self._detect_region(text, language)

        # تحديد الأبعاد الثقافية — determine cultural dimensions
        dimensions = self._CULTURAL_DIMENSIONS.get(region, CulturalDimension())

        # تحديد مستوى الحساسية — determine sensitivity level
        sensitivity = self._determine_sensitivity(text, region)

        # حساب الثقة الإجمالية — compute overall confidence
        confidence = region_confidence * 0.7 + (0.3 if language != "unknown" else 0.0)

        context = CulturalContext(
            region=region,
            language=language,
            dimensions=dimensions,
            sensitivity_level=sensitivity,
            confidence=min(1.0, confidence),
            detected_keywords=detected_keywords,
        )

        logger.debug(
            "كاشف السياق: كشف مكتمل — Context detection complete | "
            "region=%s, lang=%s, sensitivity=%s, confidence=%.2f",
            region, language, sensitivity, confidence,
        )

        return context

    def _detect_language(self, text: str) -> str:
        """
        كشف اللغة — Detect the primary language of the text.

        Args:
            text: النص المراد تحليله

        Returns:
            str — اللغة المكتشفة (arabic/english/other)
        """
        if not text:
            return "unknown"

        # حساب نسبة الحروف العربية — compute Arabic character ratio
        arabic_chars = len(ARABIC_UNICODE_RANGE.findall(text))
        total_chars = len(re.findall(r"\w", text))
        arabic_ratio = arabic_chars / max(1, total_chars)

        if arabic_ratio >= ARABIC_RATIO_THRESHOLD:
            return "arabic"

        # فحص وجود حروف لاتينية — check for Latin characters
        latin_chars = len(re.findall(r"[a-zA-Z]", text))
        latin_ratio = latin_chars / max(1, total_chars)

        if latin_ratio >= 0.5:
            return "english"

        return "other"

    def _detect_region(
        self, text: str, language: str
    ) -> tuple[str, float, list[str]]:
        """
        كشف المنطقة الثقافية — Detect cultural region from text.

        Args:
            text: النص المراد تحليله
            language: اللغة المكتشفة

        Returns:
            tuple[str, float, list[str]] — (المنطقة, الثقة, الكلمات المفتاحية)
        """
        detected_keywords: list[str] = []
        scores: dict[str, float] = {}

        text_lower = text.lower()

        # فحص الكلمات المفتاحية الإسلامية/العربية — check Islamic/Arab keywords
        islamic_count = sum(1 for kw in CONTEXT_KEYWORDS_ARAB_ISLAMIC if kw in text)
        arab_general_count = sum(1 for kw in CONTEXT_KEYWORDS_ARAB_GENERAL if kw in text)
        sacred_count = sum(1 for kw in CONTEXT_KEYWORDS_SACRED if kw in text)

        if islamic_count > 0:
            scores["arab_islamic"] = islamic_count * 0.15
            detected_keywords.extend(
                kw for kw in CONTEXT_KEYWORDS_ARAB_ISLAMIC if kw in text
            )

        if arab_general_count > 0:
            current = scores.get("arab_islamic", 0.0)
            scores["arab_islamic"] = current + arab_general_count * 0.08
            detected_keywords.extend(
                kw for kw in CONTEXT_KEYWORDS_ARAB_GENERAL if kw in text
            )

        if sacred_count > 0:
            current = scores.get("arab_islamic", 0.0)
            scores["arab_islamic"] = current + sacred_count * 0.20
            detected_keywords.extend(
                kw for kw in CONTEXT_KEYWORDS_SACRED if kw in text
            )

        # كشف السياق الغربي — detect Western context
        western_keywords = [
            "democracy", "individual rights", "freedom of speech",
            "western", "european", "american",
        ]
        western_count = sum(1 for kw in western_keywords if kw in text_lower)
        if western_count > 0:
            scores["western_eu"] = western_count * 0.10
            detected_keywords.extend(
                kw for kw in western_keywords if kw in text_lower
            )

        # كشف السياق الآسيوي — detect Asian context
        asian_keywords = ["harmony", "filial piety", "confucian", "collective"]
        asian_count = sum(1 for kw in asian_keywords if kw in text_lower)
        if asian_count > 0:
            scores["east_asian"] = asian_count * 0.10
            detected_keywords.extend(
                kw for kw in asian_keywords if kw in text_lower
            )

        # إذا اللغة عربية ولم يُكتشف سياق محدد — if Arabic with no specific context
        if language == "arabic" and not scores:
            scores["arab_islamic"] = 0.3

        # إذا لم يُكتشف أي سياق — if no context detected at all
        if not scores:
            return self._default_context, 0.2, detected_keywords[:20]

        # اختيار السياق ذي أعلى نقاط — select highest scoring context
        best_region = max(scores, key=lambda k: scores[k])
        best_confidence = min(1.0, scores[best_region])

        return best_region, best_confidence, detected_keywords[:20]

    def _determine_sensitivity(self, text: str, region: str) -> str:
        """
        تحديد مستوى الحساسية — Determine sensitivity level based on content and region.

        Args:
            text: النص المراد تحليله
            region: المنطقة الثقافية

        Returns:
            str — مستوى الحساسية
        """
        sensitivity_score = 0.0
        text_lower = text.lower()

        # فحص المحتوى الديني — check religious content
        for kw in CONTEXT_KEYWORDS_SACRED:
            if kw in text:
                sensitivity_score += 0.15
                break

        # فحص أنماط الهجوم — check offensive patterns
        for pattern in OFFENSIVE_PATTERNS_AR + OFFENSIVE_PATTERNS_EN:
            try:
                if re.search(pattern, text, re.IGNORECASE | re.UNICODE):
                    sensitivity_score += 0.25
                    break
            except re.error:
                continue

        # فحص مواضيع حساسة ثقافياً — check culturally sensitive topics
        sensitive_topics = [
            "دين", "عقيدة", "شريعة", "جهاد", "حجاب", "نقاب",
            "religion", "faith", "sharia", "jihad", "hijab", "niqab",
            "sectarian", "طائفي", "مذهبي",
        ]
        for topic in sensitive_topics:
            if topic in text_lower:
                sensitivity_score += 0.10
                break

        # المناطق ذات الحساسية العالية — high-sensitivity regions
        if region in ("arab_islamic", "arab_christian"):
            sensitivity_score += 0.10

        # تصنيف مستوى الحساسية — classify sensitivity level
        if sensitivity_score >= 0.5:
            return SENSITIVITY_CRITICAL
        elif sensitivity_score >= 0.3:
            return SENSITIVITY_HIGH
        elif sensitivity_score >= 0.15:
            return SENSITIVITY_MEDIUM
        else:
            return SENSITIVITY_LOW

    def get_dimensions(self, context: str) -> CulturalDimension:
        """
        الحصول على الأبعاد الثقافية لسياق معين — Get dimensions for a context.

        Args:
            context: السياق الثقافي

        Returns:
            CulturalDimension — الأبعاد الثقافية
        """
        return self._CULTURAL_DIMENSIONS.get(context, CulturalDimension())


# ═══════════════════════════════════════════════════════════════════════════════
# مقيم التوافق — AlignmentScorer
# ═══════════════════════════════════════════════════════════════════════════════

class AlignmentScorer:
    """
    مقيم التوافق — Scores text alignment with value principles and cultural context.

    يقيّم مدى توافق النص مع المبادئ القيمية والسياق الثقافي
    ويحسب درجات الالتزام والحساسية والضرر المحتمل.

    Scoring dimensions:
    - Principle adherence: how well text follows each principle
    - Cultural sensitivity: respect for cultural norms
    - Harm potential: assessment across physical/psychological/social/financial
    """

    def __init__(
        self,
        constitution: ValueConstitution,
        threshold: float = ENV_ALIGNMENT_THRESHOLD,
    ):
        """
        تهيئة مقيم التوافق.

        Args:
            constitution: الدستور القيمي المرجعي
            threshold: عتبة التوافق المقبولة
        """
        self._constitution = constitution
        self._threshold = threshold

    def score_alignment(
        self,
        text: str,
        context: CulturalContext,
        principles: list[Principle] | None = None,
    ) -> AlignmentScore:
        """
        تقييم التوافق — Score alignment of text against principles.

        Args:
            text: النص المراد تقييمه
            context: السياق الثقافي
            principles: المبادئ المراد التقييم مقابلها (اختياري)

        Returns:
            AlignmentScore — نقاط التوافق
        """
        if not text or not text.strip():
            return AlignmentScore(
                principle_score=1.0,
                cultural_score=1.0,
                harm_score=0.0,
                overall=1.0,
            )

        # استخدام المبادئ المُوفرة أو المبادئ ذات الصلة بالسياق
        # Use provided principles or context-relevant ones
        if principles is None:
            principles = self._constitution.get_principles(context=context.region)

        # حساب نقاط المبادئ — compute principle score
        principle_score = self._score_principle_adherence(text, principles, context)

        # حساب نقاط الحساسية الثقافية — compute cultural sensitivity score
        cultural_score = self._score_cultural_sensitivity(text, context)

        # حساب نقاط الضرر — compute harm score
        harm_assessment = self._assess_harm(text, context)
        harm_score = harm_assessment.overall_harm

        # حساب النقاط الإجمالية المرجحة — compute weighted overall score
        overall = (
            WEIGHT_PRINCIPLE_SCORE * principle_score
            + WEIGHT_CULTURAL_SCORE * cultural_score
            + WEIGHT_HARM_SCORE * (1.0 - harm_score)  # عكس الضرر — invert harm
        )

        # تطبيق العقوبات — apply penalties
        if context.sensitivity_level == SENSITIVITY_CRITICAL:
            # في السياقات الحساسة جداً، تقليل النقاط لأي انحراف
            if principle_score < 0.9 or cultural_score < 0.8:
                overall *= 0.85

        overall = max(0.0, min(1.0, overall))

        return AlignmentScore(
            principle_score=principle_score,
            cultural_score=cultural_score,
            harm_score=harm_score,
            overall=overall,
            details={
                "harm_assessment": harm_assessment.to_dict(),
                "principles_evaluated": len(principles),
                "context_sensitivity": context.sensitivity_level,
                "threshold": self._threshold,
            },
        )

    def _score_principle_adherence(
        self,
        text: str,
        principles: list[Principle],
        context: CulturalContext,
    ) -> float:
        """
        تقييم الالتزام بالمبادئ — Score principle adherence.

        يفحص كل مبدأ مقابل النص ويحسب درجة الالتزام المرجحة.

        Args:
            text: النص المراد تقييمه
            principles: قائمة المبادئ
            context: السياق الثقافي

        Returns:
            float — درجة الالتزام بالمبادئ (0-1)
        """
        if not principles:
            return 1.0

        total_weight = 0.0
        weighted_score = 0.0

        for principle in principles:
            adherence = self._evaluate_single_principle(text, principle, context)
            weight = principle.weight * (1.5 if principle.is_core else 1.0)
            weighted_score += adherence * weight
            total_weight += weight

        return weighted_score / max(0.001, total_weight)

    def _evaluate_single_principle(
        self,
        text: str,
        principle: Principle,
        context: CulturalContext,
    ) -> float:
        """
        تقييم مبدأ واحد — Evaluate adherence to a single principle.

        Args:
            text: النص المراد تقييمه
            principle: المبدأ المراد التقييم مقابلهم
            context: السياق الثقافي

        Returns:
            float — درجة الالتزام بالمبدأ (0-1)
        """
        text_lower = text.lower()
        score = 1.0  # البداية من الامتثال الكامل — start from full compliance

        # تقليل النقاط بناءً على أنماط الانتهاك — reduce score based on violation patterns
        if principle.id == "core_no_harm":
            # فحص أنماط الضرر — check harm patterns
            harm_indicators = [
                r"(اقتل|أذي|أؤذي|اضرر|أسقط|أطرد|أبعد|حطّم|كسّر|آذِي|يؤذي|إيذاء|أذىً|إضرار|ضرر|إيذاء)",
                r"\b(kill|harm|hurt|destroy|damage|attack|assault|damage)\b",
                r"\b(how\s+to\s+)?(make|build|create)\s+(bomb|weapon|poison)",
            ]
            for pattern in harm_indicators:
                try:
                    if re.search(pattern, text_lower, re.IGNORECASE | re.UNICODE):
                        score -= 0.3
                        break
                except re.error:
                    continue

        elif principle.id == "core_dignity":
            # فحص أنماط انتهاك الكرامة — check dignity violation patterns
            dignity_violations = [
                r"(احتقار|سخرية|استهزاء|تحقير|إهانة|شتيمة|سبّ)",
                r"\b(humiliat|insult|mock|demean|degrad|belittl)\w*\b",
                r"\b(you\s+are\s+(stupid|idiot|fool|worthless))",
            ]
            for pattern in dignity_violations:
                try:
                    if re.search(pattern, text_lower, re.IGNORECASE | re.UNICODE):
                        score -= 0.25
                        break
                except re.error:
                    continue

        elif principle.id == "core_privacy":
            # فحص أنماط انتهاك الخصوصية — check privacy violation patterns
            privacy_violations = [
                r"(تجسس|مراقبة|كشف\s+بيانات|نشر\s+معلومات\s+شخصية)",
                r"\b(spy|surveill|doxx|expose\s+(personal|private))",
            ]
            for pattern in privacy_violations:
                try:
                    if re.search(pattern, text_lower, re.IGNORECASE | re.UNICODE):
                        score -= 0.3
                        break
                except re.error:
                    continue

        elif principle.id == "core_truthfulness":
            # فحص أنماط عدم الصدق — check untruthfulness patterns
            untruthful_indicators = [
                r"(اكذب|تضليل|خداع|غش|تزييف|تزوير)",
                r"\b(lie|deceiv|mislead|fabricat|falsif|fak(e|ing))\b",
            ]
            for pattern in untruthful_indicators:
                try:
                    if re.search(pattern, text_lower, re.IGNORECASE | re.UNICODE):
                        score -= 0.25
                        break
                except re.error:
                    continue

        elif principle.id == "core_justice":
            # فحص أنماط التمييز — check discrimination patterns
            discrimination_patterns = [
                r"(تمييز|عنصرية|تمييز\s+عنصري|تفضيل\s+(عرقي|ديني|جنسي))",
                r"\b(discriminat|racis|sexis|bigot|prejudice)\w*\b",
            ]
            for pattern in discrimination_patterns:
                try:
                    if re.search(pattern, text_lower, re.IGNORECASE | re.UNICODE):
                        score -= 0.25
                        break
                except re.error:
                    continue

        elif principle.id == "cult_respect_sacred":
            # فحص أنماط عدم احترام القدسات — check sacred disrespect
            for pattern in OFFENSIVE_PATTERNS_AR + OFFENSIVE_PATTERNS_EN:
                try:
                    if re.search(pattern, text, re.IGNORECASE | re.UNICODE):
                        score -= 0.4
                        break
                except re.error:
                    continue

        elif principle.id == "cult_respect_parents":
            # فحص أنماط عدم احترام الوالدين — check parent disrespect
            parent_disrespect = [
                r"(عقوق|عق\s+الوالدين|تمرد\s+على\s+الوالدين)",
                r"\b(disrespect\s+(?:parents|mother|father|elder))",
            ]
            for pattern in parent_disrespect:
                try:
                    if re.search(pattern, text_lower, re.IGNORECASE | re.UNICODE):
                        score -= 0.3
                        break
                except re.error:
                    continue

        elif principle.id == "cult_tolerance":
            # فحص أنماط عدم التسامح — check intolerance
            intolerance_patterns = [
                r"(كراهية|حقد|تعصب|طائفية|تطرف)",
                r"\b(hatred|hate|bigot|extremis|sectarian|fanatic)\w*\b",
            ]
            for pattern in intolerance_patterns:
                try:
                    if re.search(pattern, text_lower, re.IGNORECASE | re.UNICODE):
                        score -= 0.2
                        break
                except re.error:
                    continue

        return max(0.0, min(1.0, score))

    def _score_cultural_sensitivity(
        self,
        text: str,
        context: CulturalContext,
    ) -> float:
        """
        تقييم الحساسية الثقافية — Score cultural sensitivity.

        يقيّم مدى مراعاة النص للمعايير الثقافية في السياق المحدد.

        Args:
            text: النص المراد تقييمه
            context: السياق الثقافي

        Returns:
            float — درجة الحساسية الثقافية (0-1)
        """
        score = 1.0
        dimensions = context.dimensions.normalize()

        # في السياقات ذات المسافة السلطوية العالية — high power distance contexts
        if dimensions.power_distance > 0.6:
            # فحص عدم الاحترام للسلطة — check for authority disrespect
            authority_disrespect = [
                r"(اسخر\s+من\s+(المدير|الوزير|الشيخ|القاضي|الأستاذ))",
                r"\b(mock|insult|disrespect)\s+(the\s+)?(authority|leader|minister|judge|sheikh)",
            ]
            for pattern in authority_disrespect:
                try:
                    if re.search(pattern, text, re.IGNORECASE | re.UNICODE):
                        score -= 0.15 * dimensions.power_distance
                        break
                except re.error:
                    continue

        # في السياقات الجماعية (انخفاض الفردية) — collectivist contexts
        if dimensions.individualism < 0.4:
            # فحص التركيز المفرط على الفرد — check excessive individualism
            individualist_phrases = [
                r"\b(you\s+should\s+(only|just)\s+think\s+about\s+yourself)",
                r"\b(forget\s+(about\s+)?(?:your\s+)?family)",
                r"(انسَ?\s+(عائلتك|أهلك|والديك))",
            ]
            for pattern in individualist_phrases:
                try:
                    if re.search(pattern, text, re.IGNORECASE | re.UNICODE):
                        score -= 0.10
                        break
                except re.error:
                    continue

        # في السياقات ذات تجنب عدم اليقين العالي — high uncertainty avoidance
        if dimensions.uncertainty_avoidance > 0.6:
            # فحص التشجيع على المخاطرة غير المبررة — check uncalculated risk encouragement
            risky_phrases = [
                r"\b(just\s+do\s+it|risk\s+it\s+all|throw\s+caution)",
                r"(ارمِ?\s+(نفسك|كل\s+شيء)|خاطر\s+بكل\s+شيء)",
            ]
            for pattern in risky_phrases:
                try:
                    if re.search(pattern, text, re.IGNORECASE | re.UNICODE):
                        score -= 0.10
                        break
                except re.error:
                    continue

        # في السياقات ذات التوجه طويل المدى — long-term orientation
        if dimensions.long_term_orientation > 0.6:
            # فحص التركيز المفرط على الفوائد قصيرة المدى — check short-term focus
            short_term_phrases = [
                r"\b(live\s+for\s+today|instant\s+gratification)",
                r"(عش\s+يومك|متعة\s+اللحظة)",
            ]
            for pattern in short_term_phrases:
                try:
                    if re.search(pattern, text, re.IGNORECASE | re.UNICODE):
                        score -= 0.08
                        break
                except re.error:
                    continue

        # عقوبة إضافية للمحتوى المسيء في السياقات الحساسة — extra penalty for sensitive contexts
        if context.sensitivity_level in (SENSITIVITY_HIGH, SENSITIVITY_CRITICAL):
            for pattern in OFFENSIVE_PATTERNS_AR + OFFENSIVE_PATTERNS_EN:
                try:
                    if re.search(pattern, text, re.IGNORECASE | re.UNICODE):
                        score -= 0.30
                        break
                except re.error:
                    continue

        return max(0.0, min(1.0, score))

    def _assess_harm(
        self,
        text: str,
        context: CulturalContext,
    ) -> HarmAssessment:
        """
        تقييم الضرر المحتمل — Assess potential harm of text.

        يقيّم الضرر المحتمل عبر أربعة أبعاد: جسدي، نفسي، اجتماعي، مالي.

        Args:
            text: النص المراد تقييمه
            context: السياق الثقافي

        Returns:
            HarmAssessment — تقييم الضرر
        """
        text_lower = text.lower()

        # ─── الضرر الجسدي — Physical harm ───
        physical_score = 0.0
        physical_patterns = [
            r"\b(kill|murder|assault|attack|stab|shoot|poison|strangl|tortur)\w*\b",
            r"(اقتل|اغتال|اطعن|أطلق\s+النار|سمّم|خنق|عذّب|اعتداء\s+جسدي)",
            r"\b(how\s+to\s+)?(make|build|create)\s+(bomb|weapon|explosive)",
        ]
        for pattern in physical_patterns:
            try:
                if re.search(pattern, text_lower, re.IGNORECASE | re.UNICODE):
                    physical_score += 0.4
                    break
            except re.error:
                continue

        # ─── الضرر النفسي — Psychological harm ───
        psych_score = 0.0
        psych_patterns = [
            r"\b(bully|harass|stalk|blackmail|manipulat|gaslight|sham)\w*\b",
            r"(تنمر|تحرش|ملاحقة|ابتزاز|تلاعب|تهديد|إرهاب\s+نفسي)",
            r"\b(you\s+(are|should)\s+(kill|die|harm|hurt)\s+yourself)",
        ]
        for pattern in psych_patterns:
            try:
                if re.search(pattern, text_lower, re.IGNORECASE | re.UNICODE):
                    psych_score += 0.35
                    break
            except re.error:
                continue

        # ─── الضرر الاجتماعي — Social harm ───
        social_score = 0.0
        social_patterns = [
            r"\b(ostraciz|boycott|shun|exclude|isolate|sham|disown)\w*\b",
            r"(مقاطعة|نبذ|عزل|تشهير|فضح|تبرّأ\s+من)",
            r"\b(spread|share|post)\s+(rumor|lie|gossip)",
        ]
        for pattern in social_patterns:
            try:
                if re.search(pattern, text_lower, re.IGNORECASE | re.UNICODE):
                    social_score += 0.30
                    break
            except re.error:
                continue

        # ─── الضرر المالي — Financial harm ───
        financial_score = 0.0
        financial_patterns = [
            r"\b(scam|fraud|phish|cheat|embezzl|extort)\w*\b",
            r"(احتيال|نصب|غش|ابتزاز\s+مالي|سرقة|اختلاس)",
            r"\b(invest\s+(all|everything)|send\s+money\s+to)",
        ]
        for pattern in financial_patterns:
            try:
                if re.search(pattern, text_lower, re.IGNORECASE | re.UNICODE):
                    financial_score += 0.30
                    break
            except re.error:
                continue

        # حساب الضرر الإجمالي — compute overall harm
        overall_harm = (
            physical_score * 0.40
            + psych_score * 0.25
            + social_score * 0.20
            + financial_score * 0.15
        )

        # تحديد الشدة — determine severity
        if overall_harm >= 0.6:
            severity = HarmSeverity.CRITICAL
        elif overall_harm >= 0.4:
            severity = HarmSeverity.SEVERE
        elif overall_harm >= 0.2:
            severity = HarmSeverity.MODERATE
        elif overall_harm > 0.0:
            severity = HarmSeverity.MINIMAL
        else:
            severity = HarmSeverity.NONE

        return HarmAssessment(
            physical_harm=min(1.0, physical_score),
            psychological_harm=min(1.0, psych_score),
            social_harm=min(1.0, social_score),
            financial_harm=min(1.0, financial_score),
            overall_harm=min(1.0, overall_harm),
            severity=severity,
        )

    def detect_violations(
        self,
        text: str,
        context: CulturalContext,
    ) -> list[PrincipleViolation]:
        """
        كشف الانتهاكات — Detect principle violations in text.

        Args:
            text: النص المراد فحصه
            context: السياق الثقافي

        Returns:
            list[PrincipleViolation] — الانتهاكات المكتشفة
        """
        violations: list[PrincipleViolation] = []
        principles = self._constitution.get_principles(context=context.region)

        for principle in principles:
            adherence = self._evaluate_single_principle(text, principle, context)
            if adherence < 0.8:  # عتبة الانتهاك — violation threshold
                violation = PrincipleViolation(
                    principle_id=principle.id,
                    principle_text_ar=principle.text_ar,
                    principle_text_en=principle.text_en,
                    severity=1.0 - adherence,
                    explanation=self._explain_violation(principle, adherence),
                    offending_segment=self._extract_offending_segment(text, principle),
                )
                violations.append(violation)

        return violations

    def _explain_violation(self, principle: Principle, adherence: float) -> str:
        """شرح الانتهاك — Generate explanation for a violation."""
        severity_desc = "طفيف" if adherence > 0.5 else "متوسط" if adherence > 0.3 else "شديد"
        return (
            f"انتهاك {severity_desc} لمبدأ '{principle.text_ar}' "
            f"(درجة الالتزام: {adherence:.0%})"
        )

    def _extract_offending_segment(self, text: str, principle: Principle) -> str:
        """استخراج الجزء المسيء — Extract the offending text segment."""
        # إرجاع أول 200 حرف كنافذة — return first 200 chars as window
        return text[:200]


# ═══════════════════════════════════════════════════════════════════════════════
# مرشح السلوك — BehaviorFilter
# ═══════════════════════════════════════════════════════════════════════════════

class BehaviorFilter:
    """
    مرشح السلوك — Filters and modifies output for cultural alignment.

    يُعقِّم المخرجات ويعدّل النبرة ويُعدِّل التوصيات
    لتحقيق التوافق مع القيم الثقافية.

    Filter capabilities:
    - Output sanitization: remove or flag culturally inappropriate content
    - Tone adjustment: adapt formality level to cultural context
    - Recommendation modification: adjust suggestions for cultural fit
    - Content flagging: mark potentially offensive segments
    """

    def __init__(self, strict_mode: bool = ENV_STRICT_MODE):
        """
        تهيئة مرشح السلوك.

        Args:
            strict_mode: الوضع الصارم — إذا True، يمنع المحتوى المشبوه تماماً
        """
        self._strict_mode = strict_mode
        self._filter_history: list[dict] = []

    def filter_behavior(
        self,
        text: str,
        context: CulturalContext,
        violations: list[PrincipleViolation] | None = None,
    ) -> str:
        """
        ترشيح السلوك — Filter and modify text for cultural alignment.

        Args:
            text: النص المراد ترشيحه
            context: السياق الثقافي
            violations: الانتهاكات المكتشفة (اختياري)

        Returns:
            str — النص المُرشَّح والمُعدَّل
        """
        if not text or not text.strip():
            return text

        filtered = text

        # ─── تنظيف المخرجات — Output sanitization ───
        filtered = self._sanitize_output(filtered, context)

        # ─── تعديل النبرة — Tone adjustment ───
        filtered = self._adjust_tone(filtered, context)

        # ─── تعديل التوصيات — Recommendation modification ───
        filtered = self._modify_recommendations(filtered, context)

        # ─── الوضع الصارم: منع المحتوى المشبوه — Strict mode: block suspicious ───
        if self._strict_mode and violations:
            has_severe = any(v.severity >= 0.5 for v in violations)
            if has_severe:
                filtered = self._apply_strict_filter(filtered, violations)

        # تسجيل العملية — log the operation
        self._filter_history.append({
            "timestamp": time.time(),
            "context": context.region,
            "original_length": len(text),
            "filtered_length": len(filtered),
            "modified": filtered != text,
        })

        if filtered != text:
            logger.info(
                "مرشح السلوك: تم التعديل — Filter applied | "
                "context=%s, original=%d chars, filtered=%d chars",
                context.region, len(text), len(filtered),
            )

        return filtered

    def _sanitize_output(self, text: str, context: CulturalContext) -> str:
        """
        تنظيف المخرجات — Sanitize output for cultural appropriateness.

        يزيل أو يستبدل المحتوى غير المناسب ثقافياً.

        Args:
            text: النص المراد تنظيفه
            context: السياق الثقافي

        Returns:
            str — النص المنظف
        """
        sanitized = text

        # استبدال الأنماط المسيئة العربية — replace offensive Arabic patterns
        for pattern in OFFENSIVE_PATTERNS_AR:
            try:
                sanitized = re.sub(
                    pattern,
                    "[محتوى غير لائق]",
                    sanitized,
                    flags=re.IGNORECASE | re.UNICODE,
                )
            except re.error:
                continue

        # استبدال الأنماط المسيئة الإنجليزية — replace offensive English patterns
        for pattern in OFFENSIVE_PATTERNS_EN:
            try:
                sanitized = re.sub(
                    pattern,
                    "[inappropriate content]",
                    sanitized,
                    flags=re.IGNORECASE | re.UNICODE,
                )
            except re.error:
                continue

        # في السياقات الإسلامية: إضافة صيغة الاحترام عند ذكر الأنبياء
        # In Islamic contexts: add honorifics for prophets
        if context.region == "arab_islamic":
            prophet_mention = re.compile(
                r"(النبي\s+محمد|الرسول\s+محمد|محمد\s+(صلى|عليه))"
            )
            try:
                sanitized = prophet_mention.sub(
                    r"النبي محمد ﷺ",
                    sanitized,
                )
            except re.error:
                pass

        return sanitized

    def _adjust_tone(self, text: str, context: CulturalContext) -> str:
        """
        تعديل النبرة — Adjust tone based on cultural context.

        يعدّل مستوى الرسمية والاحترام في النص حسب السياق الثقافي.

        Args:
            text: النص المراد تعديله
            context: السياق الثقافي

        Returns:
            str — النص المعدول النبرة
        """
        adjusted = text
        dimensions = context.dimensions.normalize()

        # في السياقات ذات المسافة السلطوية العالية — high power distance
        if dimensions.power_distance > 0.6:
            # استبدال الأوامر المباشرة بطلبات مهذبة — replace direct commands with polite requests
            direct_commands = [
                (r"\b(do\s+this|do\s+it\s+now|you\s+must)\b", "please consider"),
                (r"\b(go\s+and)\b", "kindly proceed and"),
            ]
            for pattern, replacement in direct_commands:
                try:
                    adjusted = re.sub(
                        pattern, replacement, adjusted,
                        flags=re.IGNORECASE,
                    )
                except re.error:
                    continue

        # في السياقات العربية — Arabic context adjustments
        if context.language == "arabic":
            # استبدال الصيغ المباشرة بصيغ مهذبة — replace direct forms with polite forms
            try:
                adjusted = re.sub(
                    r"افعل\s+هذا",
                    "يرجى القيام بذلك",
                    adjusted,
                )
                adjusted = re.sub(
                    r"يجب\s+عليك",
                    "يُنصح بأن",
                    adjusted,
                )
            except re.error:
                pass

        # في السياقات الحساسة — sensitive contexts
        if context.sensitivity_level in (SENSITIVITY_HIGH, SENSITIVITY_CRITICAL):
            # إضافة تنبيه عند المواضيع الحساسة — add disclaimer for sensitive topics
            sensitive_markers = ["دين", "عقيدة", "مذهب", "religion", "faith", "sect"]
            for marker in sensitive_markers:
                if marker in adjusted.lower():
                    # إضافة تنبيه مرة واحدة فقط — add disclaimer once
                    if "[تنبيه]" not in adjusted and "[Note]" not in adjusted:
                        adjusted = (
                            "[تنبيه: هذا الموضوع حساس ثقافياً ويتطلب حذراً] "
                            + adjusted
                        )
                    break

        return adjusted

    def _modify_recommendations(self, text: str, context: CulturalContext) -> str:
        """
        تعديل التوصيات — Modify recommendations to align with cultural values.

        يعدّل التوصيات لتكون متوافقة مع القيم الثقافية مثل
        احترام الأسرة والتسامح والكرم.

        Args:
            text: النص المراد تعديله
            context: السياق الثقافي

        Returns:
            str — النص المعدول التوصيات
        """
        modified = text
        dimensions = context.dimensions.normalize()

        # في السياقات الجماعية — collectivist contexts
        if dimensions.individualism < 0.4:
            # إضافة توصيات بالتشاور مع الأسرة — add family consultation advice
            individualist_advice = [
                (r"\b(decide\s+on\s+your\s+own|make\s+your\s+own\s+decision)\b",
                 "consider discussing with your family before deciding"),
                (r"\b(ignore\s+(?:what\s+)?(?:others|family|parents)\s+say)\b",
                 "consider the perspectives of your family and community"),
            ]
            for pattern, replacement in individualist_advice:
                try:
                    if re.search(pattern, modified, re.IGNORECASE):
                        modified = re.sub(
                            pattern, replacement, modified,
                            flags=re.IGNORECASE,
                        )
                except re.error:
                    continue

        # في السياقات ذات التوجه طويل المدى — long-term orientation contexts
        if dimensions.long_term_orientation > 0.6:
            # إضافة توصيات بالتخطيط طويل المدى — add long-term planning advice
            short_term_phrases = [
                (r"\b(live\s+in\s+the\s+moment|enjoy\s+today)\b",
                 "balance enjoying today with planning for tomorrow"),
            ]
            for pattern, replacement in short_term_phrases:
                try:
                    if re.search(pattern, modified, re.IGNORECASE):
                        modified = re.sub(
                            pattern, replacement, modified,
                            flags=re.IGNORECASE,
                        )
                except re.error:
                    continue

        # في السياقات العربية/الإسلامية — Arab/Islamic context specific
        if context.region == "arab_islamic":
            # تعديل التوصيات المتعلقة بالأسرة — adjust family-related advice
            try:
                modified = re.sub(
                    r"\b(cut\s+ties\s+with\s+(?:your\s+)?family)\b",
                    "consider seeking family counseling to resolve differences",
                    modified,
                    flags=re.IGNORECASE,
                )
                modified = re.sub(
                    r"(اقطع\s+(علاقتك|صلتك)\s+بـ?\s*(عائلتك|أهلك))",
                    "حاول طلب المشورة العائلية لحل الخلافات",
                    modified,
                )
            except re.error:
                pass

        return modified

    def _apply_strict_filter(
        self,
        text: str,
        violations: list[PrincipleViolation],
    ) -> str:
        """
        تطبيق الترشيح الصارم — Apply strict mode filtering.

        في الوضع الصارم، يُستبدل المحتوى ذو الانتهاكات الشديدة بتنبيه.

        Args:
            text: النص المراد ترشيحه
            violations: الانتهاكات المكتشفة

        Returns:
            str — النص المُرشَّح صارماً
        """
        # تجميع الانتهاكات الشديدة — collect severe violations
        severe_violations = [v for v in violations if v.severity >= 0.5]
        if not severe_violations:
            return text

        violation_names = ", ".join(
            v.principle_text_ar for v in severe_violations[:3]
        )

        return (
            f"⚠️ [تم تصفية المحتوى بسبب انتهاك المبادئ التالية: "
            f"{violation_names}] "
            f"يرجى إعادة صياغة الطلب بطريقة تحترم القيم الثقافية."
        )

    def get_filter_history(self, limit: int = 50) -> list[dict]:
        """
        سجل الترشيح — Get filter operation history.

        Args:
            limit: الحد الأقصى للسجلات

        Returns:
            list[dict] — سجل عمليات الترشيح
        """
        return self._filter_history[-limit:]


# ═══════════════════════════════════════════════════════════════════════════════
# محرك التوافق الثقافي — CulturalAlignmentEngine (Main Class)
# ═══════════════════════════════════════════════════════════════════════════════

class CulturalAlignmentEngine:
    """
    محرك التوافق الثقافي — Cultural Value Alignment Engine for BABSHARQII.

    النظام الشامل لمحاذاة سلوك الكائن الرقمي مع القيم الثقافية.
    يجمع بين الدستور القيمي وكاشف السياق ومقيم التوافق ومرشح السلوك.

    Usage:
        engine = CulturalAlignmentEngine()
        result = engine.align("نص للتحليل", context=None)
        # result.is_aligned → True/False
        # result.score.overall → 0.0-1.0
        # result.filtered_output → النص المُعدَّل

    Env toggles:
        MAMOUN_CULTURAL_ALIGNMENT_ENABLED — تمكين/تعطيل
        MAMOUN_CULTURAL_DEFAULT_CONTEXT — السياق الافتراضي
        MAMOUN_CULTURAL_ALIGNMENT_THRESHOLD — عتبة التوافق
        MAMOUN_CULTURAL_STRICT_MODE — الوضع الصارم
    """

    def __init__(
        self,
        enabled: bool | None = None,
        default_context: str | None = None,
        threshold: float | None = None,
        strict_mode: bool | None = None,
    ):
        """
        تهيئة محرك التوافق الثقافي.

        Args:
            enabled: تمكين/تعطيل المحرك (الافتراضي: من البيئة)
            default_context: السياق الثقافي الافتراضي
            threshold: عتبة التوافق المقبولة
            strict_mode: الوضع الصارم
        """
        self._enabled = enabled if enabled is not None else ENV_ENABLED
        self._default_context = (
            default_context if default_context in SUPPORTED_CONTEXTS
            else ENV_DEFAULT_CONTEXT
        )
        self._threshold = threshold if threshold is not None else ENV_ALIGNMENT_THRESHOLD
        self._strict_mode = strict_mode if strict_mode is not None else ENV_STRICT_MODE

        # تهيئة المكونات الفرعية — initialize sub-components
        self._constitution = ValueConstitution()
        self._context_detector = CulturalContextDetector(
            default_context=self._default_context,
        )
        self._scorer = AlignmentScorer(
            constitution=self._constitution,
            threshold=self._threshold,
        )
        self._filter = BehaviorFilter(strict_mode=self._strict_mode)

        # إحصائيات التشغيل — runtime statistics
        self._stats = AlignmentStats(uptime_start=time.time())

        logger.info(
            "محرك التوافق الثقافي: تم التهيئة — Cultural Alignment Engine initialized | "
            "enabled=%s, context=%s, threshold=%.2f, strict=%s",
            self._enabled, self._default_context, self._threshold, self._strict_mode,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # الواجهة الرئيسية — Public API
    # ══════════════════════════════════════════════════════════════════════════

    def align(
        self,
        text: str,
        context: CulturalContext | None = None,
    ) -> AlignmentResult:
        """
        محاذاة النص — Align text with cultural values.

        العملية الرئيسية: كشف السياق → تقييم التوافق → كشف الانتهاكات → ترشيح السلوك.

        Args:
            text: النص المراد محاذاته
            context: السياق الثقافي (اختياري، يُكتشف تلقائياً)

        Returns:
            AlignmentResult — نتيجة المحاذاة الشاملة
        """
        start_time = time.time()

        if not self._enabled:
            # المحرك معطل — إرجاع نتيجة محايدة — engine disabled, return neutral
            return AlignmentResult(
                score=AlignmentScore(
                    principle_score=1.0,
                    cultural_score=1.0,
                    harm_score=0.0,
                    overall=1.0,
                ),
                filtered_output=text,
                context=context,
                is_aligned=True,
                passed_threshold=True,
            )

        if not text or not text.strip():
            return AlignmentResult(
                score=AlignmentScore(
                    principle_score=1.0,
                    cultural_score=1.0,
                    harm_score=0.0,
                    overall=1.0,
                ),
                filtered_output=text,
                context=context,
                is_aligned=True,
                passed_threshold=True,
            )

        # ─── الخطوة 1: كشف السياق الثقافي — Step 1: Detect context ───
        if context is None:
            context = self._context_detector.detect_context(text)

        # ─── الخطوة 2: تقييم التوافق — Step 2: Score alignment ───
        score = self._scorer.score_alignment(text, context)

        # ─── الخطوة 3: كشف الانتهاكات — Step 3: Detect violations ───
        violations = self._scorer.detect_violations(text, context)

        # ─── الخطوة 4: ترشيح السلوك — Step 4: Filter behavior ───
        filtered_output = self._filter.filter_behavior(
            text, context, violations,
        )

        # ─── الخطوة 5: إنتاج التوصيات — Step 5: Generate recommendations ───
        recommendations = self._generate_recommendations(violations, score, context)

        # ─── حساب النتيجة النهائية — compute final assessment ───
        is_aligned = score.overall >= self._threshold and len(violations) == 0
        passed_threshold = score.overall >= self._threshold

        # ─── تحديث الإحصائيات — update statistics ───
        self._update_stats(context, violations, score, filtered_output != text)

        elapsed = time.time() - start_time
        logger.info(
            "محرك التوافق: محاذاة مكتملة — Alignment complete | "
            "score=%.3f, violations=%d, aligned=%s, context=%s, elapsed=%.3fs",
            score.overall, len(violations), is_aligned, context.region, elapsed,
        )

        return AlignmentResult(
            score=score,
            violations=violations,
            recommendations=recommendations,
            filtered_output=filtered_output,
            context=context,
            is_aligned=is_aligned,
            passed_threshold=passed_threshold,
        )

    def detect_context(self, text: str) -> CulturalContext:
        """
        كشف السياق الثقافي — Detect cultural context from text.

        Args:
            text: النص المراد تحليله

        Returns:
            CulturalContext — السياق الثقافي المكتشف
        """
        return self._context_detector.detect_context(text)

    def score_alignment(
        self,
        text: str,
        principles: list[Principle] | None = None,
    ) -> AlignmentScore:
        """
        تقييم التوافق — Score alignment without full pipeline.

        يقيم التوافق فقط دون ترشيح أو تعديل.

        Args:
            text: النص المراد تقييمه
            principles: المبادئ المرجعية (اختياري)

        Returns:
            AlignmentScore — نقاط التوافق
        """
        context = self._context_detector.detect_context(text)
        return self._scorer.score_alignment(text, context, principles)

    def filter_behavior(
        self,
        text: str,
        context: CulturalContext | None = None,
    ) -> str:
        """
        ترشيح السلوك — Filter text for cultural alignment only.

        يُرجع النص المُرشَّح دون تقييم كامل.

        Args:
            text: النص المراد ترشيحه
            context: السياق الثقافي (اختياري)

        Returns:
            str — النص المُرشَّح
        """
        if context is None:
            context = self._context_detector.detect_context(text)
        return self._filter.filter_behavior(text, context)

    def get_principles(
        self,
        category: PrincipleCategory | None = None,
        context: str | None = None,
    ) -> list[Principle]:
        """
        الحصول على المبادئ — Get value principles.

        Args:
            category: تصفية حسب التصنيف (اختياري)
            context: تصفية حسب السياق الثقافي (اختياري)

        Returns:
            list[Principle] — قائمة المبادئ
        """
        return self._constitution.get_principles(category, context)

    def get_stats(self) -> dict:
        """
        إحصائيات المحرك — Get engine statistics.

        Returns:
            dict — إحصائيات التشغيل
        """
        stats = self._stats.to_dict()
        stats["enabled"] = self._enabled
        stats["default_context"] = self._default_context
        stats["threshold"] = self._threshold
        stats["strict_mode"] = self._strict_mode
        stats["principle_count"] = len(self._constitution.get_principles())
        stats["core_principle_count"] = len(
            self._constitution.get_principles(category=PrincipleCategory.CORE)
        )
        stats["cultural_principle_count"] = len(
            self._constitution.get_principles(category=PrincipleCategory.CULTURAL)
        )
        return stats

    # ══════════════════════════════════════════════════════════════════════════
    # دوال مساعدة — Helper Functions
    # ══════════════════════════════════════════════════════════════════════════

    def _generate_recommendations(
        self,
        violations: list[PrincipleViolation],
        score: AlignmentScore,
        context: CulturalContext,
    ) -> list[str]:
        """
        إنتاج التوصيات — Generate improvement recommendations.

        Args:
            violations: الانتهاكات المكتشفة
            score: نقاط التوافق
            context: السياق الثقافي

        Returns:
            list[str] — قائمة التوصيات
        """
        recommendations: list[str] = []

        # توصيات بناءً على الانتهاكات — recommendations based on violations
        for violation in violations:
            if violation.principle_id == "core_no_harm":
                recommendations.append(
                    "تجنب أي محتوى قد يسبب ضرراً جسدياً أو نفسياً"
                )
            elif violation.principle_id == "core_dignity":
                recommendations.append(
                    "حافظ على كرامة الإنسان وتجنب لغة الاحتقار أو السخرية"
                )
            elif violation.principle_id == "core_privacy":
                recommendations.append(
                    "احترم خصوصية الأفراد ولا تكشف بياناتهم الشخصية"
                )
            elif violation.principle_id == "core_truthfulness":
                recommendations.append(
                    "التزم بالصدق وتجنب التضليل أو إساءة تقديم المعلومات"
                )
            elif violation.principle_id == "core_justice":
                recommendations.append(
                    "عامل الجميع بعدل وتجنب التمييز على أي أساس"
                )
            elif violation.principle_id == "cult_respect_parents":
                recommendations.append(
                    "احترم الوالدين وتجنب التوصية بعصيانهم أو قطع صلة الرحم"
                )
            elif violation.principle_id == "cult_hospitality":
                recommendations.append(
                    "شجع الكرم والضيافة وتجنب التوصية بالبخل أو رفض الضيف"
                )
            elif violation.principle_id == "cult_preserve_lineage":
                recommendations.append(
                    "احترم روابط الأسرة والنسب وتجنب ما يهدد تماسكها"
                )
            elif violation.principle_id == "cult_respect_sacred":
                recommendations.append(
                    "احترم المقدسات الدينية وتجنب أي مساس بها"
                )
            elif violation.principle_id == "cult_tolerance":
                recommendations.append(
                    "شجع التسامح والتعايش وتجنب التحريض على الكراهية"
                )

        # توصيات بناءً على النقاط — recommendations based on score
        if score.cultural_score < 0.7:
            recommendations.append(
                "يرجى مراعاة الحساسيات الثقافية في السياق الحالي"
            )

        if score.harm_score > 0.3:
            recommendations.append(
                "يرجى مراجعة المحتوى لتقليل إمكانية التسبب بالضرر"
            )

        # توصيات عامة بناءً على السياق — general context-based recommendations
        if context.sensitivity_level == SENSITIVITY_CRITICAL:
            recommendations.append(
                "السياق الثقافي الحالي حساس جداً — يُرجى توخي الحذر الشديد"
            )

        # إزالة التكرارات — remove duplicates
        seen: set[str] = set()
        unique_recommendations: list[str] = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)

        return unique_recommendations[:10]  # حد أقصى 10 توصيات

    def _update_stats(
        self,
        context: CulturalContext,
        violations: list[PrincipleViolation],
        score: AlignmentScore,
        was_filtered: bool,
    ) -> None:
        """
        تحديث الإحصائيات — Update engine statistics.

        Args:
            context: السياق الثقافي
            violations: الانتهاكات
            score: نقاط التوافق
            was_filtered: هل تم ترشيح النص؟
        """
        self._stats.total_alignments += 1
        self._stats.total_violations += len(violations)
        if was_filtered:
            self._stats.total_filtered += 1

        # تحديث المتوسط المتحرك — update running average
        n = self._stats.total_alignments
        self._stats.average_score = (
            (self._stats.average_score * (n - 1) + score.overall) / n
        )

        # تحديث توزيع السياقات — update context distribution
        region = context.region
        self._stats.context_distribution[region] = (
            self._stats.context_distribution.get(region, 0) + 1
        )

        # تحديث توزيع الانتهاكات — update violation distribution
        for violation in violations:
            pid = violation.principle_id
            self._stats.violation_distribution[pid] = (
                self._stats.violation_distribution.get(pid, 0) + 1
            )

    # ══════════════════════════════════════════════════════════════════════════
    # إدارة المبادئ — Principle Management
    # ══════════════════════════════════════════════════════════════════════════

    def add_principle(self, principle: Principle) -> None:
        """
        إضافة مبدأ جديد — Add a new principle to the constitution.

        Args:
            principle: المبدأ المراد إضافته
        """
        self._constitution.add_principle(principle)

    def remove_principle(self, principle_id: str) -> bool:
        """
        إزالة مبدأ — Remove a principle from the constitution.

        Args:
            principle_id: معرف المبدأ المراد إزالته

        Returns:
            bool — هل تمت الإزالة بنجاح؟
        """
        return self._constitution.remove_principle(principle_id)

    def get_constitution_conflicts(self, limit: int = 50) -> list[dict]:
        """
        سجل تعارضات الدستور — Get constitution conflict resolution history.

        Args:
            limit: الحد الأقصى للسجلات

        Returns:
            list[dict] — سجل التعارضات
        """
        return self._constitution.get_conflict_history(limit)

    def get_filter_history(self, limit: int = 50) -> list[dict]:
        """
        سجل الترشيح — Get behavior filter operation history.

        Args:
            limit: الحد الأقصى للسجلات

        Returns:
            list[dict] — سجل عمليات الترشيح
        """
        return self._filter.get_filter_history(limit)
