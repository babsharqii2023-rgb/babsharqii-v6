"""
BABSHARQII (Mamoun) v6.0 — Common Sense Reasoning Filter
مرشح المنطق العام — نظام ترشيح ثلاثي المراحل لكشف الادعاءات غير المعقولة

Tri-stage logical filtering architecture inspired by BrainBench-style
evaluation (CommonSenseQA benchmarking approach) and research on
commonsense reasoning in LLMs.

Architecture:
    CommonSenseFilter
    ├── PhysicalPlausibilityChecker (inner class)
    │   └── 50+ built-in physical constraint rules
    ├── SocialNormChecker (inner class)
    │   └── 30+ built-in social/cultural norm rules (Arab/Islamic + Western)
    ├── SarcasmDetector (inner class)
    │   └── Incongruity-based detection with Arabic-specific markers
    ├── ImplicitAssumptionDetector (inner class)
    │   └── Uncover unstated premises in arguments
    └── AmbiguityResolver
        └── Resolve ambiguous statements

Env toggles:
    MAMOUN_COMMON_SENSE_ENABLED (default: "false")
    MAMOUN_COMMON_SENSE_SARCASM_THRESHOLD (default: "0.5")
    MAMOUN_COMMON_SENSE_CULTURAL_CONTEXT (default: "arab_islamic")
"""

from __future__ import annotations

import os
import re
import time
import logging
import math
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)

# ─── مفاتيح التهيئة البيئية — Environment Config ─────────────────────────────
COMMON_SENSE_ENABLED: bool = os.environ.get(
    "MAMOUN_COMMON_SENSE_ENABLED", "false"
).lower() in ("true", "1", "yes")

SARCASM_THRESHOLD: float = float(
    os.environ.get("MAMOUN_COMMON_SENSE_SARCASM_THRESHOLD", "0.5")
)

CULTURAL_CONTEXT: str = os.environ.get(
    "MAMOUN_COMMON_SENSE_CULTURAL_CONTEXT", "arab_islamic"
)


# ═══════════════════════════════════════════════════════════════════════════════
# أنواع البيانات — Data Types
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Claim:
    """
    ادعاء قابل للاختبار — A testable claim extracted from text.
    يمثل ادعاءً يمكن فحصه مقابل قواعد المنطق العام.
    """
    text: str = ""                      # نص الادعاء — claim text
    claim_type: str = ""                # physical | social | temporal
    testable: bool = True               # هل يمكن اختباره؟ — is it testable?

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "claim_type": self.claim_type,
            "testable": self.testable,
        }


@dataclass
class Violation:
    """
    انتهاك لقاعدة المنطق العام — A common sense rule violation.
    يمثل انتهاكاً لقاعدة من قواعد المنطق العام.
    """
    claim: str = ""                     # الادعاء المنتهك — violated claim
    rule_violated: str = ""             # معرف القاعدة المنتهكة — rule ID
    severity: float = 0.8               # شدة الانتهاك (0.0–1.0)
    explanation: str = ""               # شرح الانتهاك — violation explanation

    def to_dict(self) -> dict:
        return {
            "claim": self.claim,
            "rule_violated": self.rule_violated,
            "severity": round(self.severity, 4),
            "explanation": self.explanation,
        }


@dataclass
class CommonSenseRule:
    """
    قاعدة منطق عام — A single common-sense rule.
    قاعدة ثابتة للمنطق العام مع دالة فحص اختيارية.
    """
    id: str = ""                        # معرف القاعدة — rule identifier
    category: str = ""                  # physical | social | temporal | logical
    description: str = ""               # وصف القاعدة — rule description
    check_function_name: str = ""       # اسم دالة الفحص — check function name
    violation_patterns: list[str] = field(default_factory=list)
    severity: float = 0.8               # شدة الانتهاك الافتراضية

    def check(self, text: str) -> Optional[str]:
        """
        فحص النص مقابل القاعدة — Check text against this rule.
        يرجع وصف الانتهاك إن وُجد، أو None إن لم يُوجد.
        """
        for pattern in self.violation_patterns:
            try:
                if re.search(pattern, text, re.IGNORECASE | re.UNICODE):
                    return self.description
            except re.error:
                logger.warning(
                    "نمط تعبير نمطي غير صالح في القاعدة %s: %s",
                    self.id, pattern,
                )
                continue
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "description": self.description,
            "check_function_name": self.check_function_name,
            "severity": round(self.severity, 4),
        }


@dataclass
class SarcasmResult:
    """
    نتيجة كشف السخرية — Sarcasm detection result.
    ناتج تحليل السخرية واللغة غير الحرفية في النص.
    """
    is_sarcastic: bool = False          # هل النص ساخر؟
    confidence: float = 0.0             # ثقة الكشف (0.0–1.0)
    markers_found: list[str] = field(default_factory=list)  # العلامات المكتشفة
    explanation: str = ""               # شرح نتيجة الكشف

    def to_dict(self) -> dict:
        return {
            "is_sarcastic": self.is_sarcastic,
            "confidence": round(self.confidence, 4),
            "markers_found": self.markers_found,
            "explanation": self.explanation,
        }


@dataclass
class Assumption:
    """
    افتراض ضمني — An implicit assumption uncovered from text.
    يمثل فرضية غير مصرح بها مُستنتجة من الادعاء.
    """
    text: str = ""                      # نص الافتراض — assumption text
    necessity_level: str = "likely"     # required | likely | possible
    source_claim: str = ""              # الادعاء المصدر — originating claim

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "necessity_level": self.necessity_level,
            "source_claim": self.source_claim,
        }


@dataclass
class Resolution:
    """
    حل الغموض — An ambiguity resolution.
    يمثل حلاً مقترحاً لعبارة غامضة.
    """
    ambiguous_text: str = ""            # النص الغامض — ambiguous text
    resolved_meaning: str = ""          # المعنى المقترح — resolved meaning
    confidence: float = 0.5             # ثقة الحل — resolution confidence
    alternatives: list[str] = field(default_factory=list)  # بدائل محتملة

    def to_dict(self) -> dict:
        return {
            "ambiguous_text": self.ambiguous_text,
            "resolved_meaning": self.resolved_meaning,
            "confidence": round(self.confidence, 4),
            "alternatives": self.alternatives,
        }


@dataclass
class CommonSenseResult:
    """
    نتيجة مرشح المنطق العام — Complete common sense filter result.
    نتيجة شاملة لتحليل المنطق العام تشمل الانتهاكات والسخرية والافتراضات.
    """
    violations: list[Violation] = field(default_factory=list)
    sarcasm: Optional[SarcasmResult] = None
    assumptions: list[Assumption] = field(default_factory=list)
    overall_score: float = 1.0          # 0.0 = سيء، 1.0 = جيد
    filtered_text: str = ""             # النص بعد الترشيح — filtered text

    def to_dict(self) -> dict:
        return {
            "violations": [v.to_dict() for v in self.violations],
            "sarcasm": self.sarcasm.to_dict() if self.sarcasm else None,
            "assumptions": [a.to_dict() for a in self.assumptions],
            "overall_score": round(self.overall_score, 4),
            "filtered_text": self.filtered_text,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# فاحص الاحتمالية الفيزيائية — Physical Plausibility Checker
# ═══════════════════════════════════════════════════════════════════════════════


class PhysicalPlausibilityChecker:
    """
    فاحص الاحتمالية الفيزيائية — Checks if claims are physically possible.

    يحتوي على قاعدة معرفة من القيود الفيزيائية الأساسية:
    الجاذبية، الديناميكا الحرارية، أساسيات البيولوجيا، إلخ.

    Knowledge base of physical constraints:
    - Gravity: objects fall downward
    - Thermodynamics: water freezes at 0°C, boils at 100°C
    - Biology: humans need oxygen, food, water
    - Chemistry: fire burns, ice melts
    - Physics: energy conservation, speed of light limit
    """

    # 50+ قاعدة احتمالية فيزيائية — Physical plausibility rules
    _PHYSICAL_RULES: list[CommonSenseRule] = [
        # ─── الجاذبية والحركة — Gravity & Motion ─────────────────────────
        CommonSenseRule(
            id="phys_001", category="physical",
            description="الماء لا يتدفق صعوداً بدون قوة خارجية / Water does not flow uphill without external force",
            check_function_name="check_water_flow",
            violation_patterns=[
                r"الماء\s+(يتدفق|يسيل|يصعد)\s+صعود[اً]",
                r"water\s+(flows?|runs?|moves?)\s+(uphill|up\s+hill|upward)",
                r"النهر\s+(يصعد|يتسلق)\s+(الجبل|المرتفع)",
            ], severity=0.95,
        ),
        CommonSenseRule(
            id="phys_002", category="physical",
            description="الأشياء تسقط لأسفل وليس للأعلى بدون قوة / Objects fall downward without force",
            check_function_name="check_gravity",
            violation_patterns=[
                r"(سقط|سقطت|وقع|وقعت)\s+(لأعلى|للأعلى|صعوداً|للسماء)",
                r"fell\s+(upward|up\s*wards?|into\s+the\s+sky)",
                r"الجاذبية\s+(تدفع|تسحب)\s+(لأعلى|للأعلى)",
            ], severity=0.95,
        ),
        CommonSenseRule(
            id="phys_003", category="physical",
            description="الإنسان لا يستطيع الطيران بدون وسيلة / Humans cannot fly unaided",
            check_function_name="check_human_flight",
            violation_patterns=[
                r"(طار|طاروا|يطير|تحلّق)\s+(بدون|من\s+غير)\s+(أجنحة|طائرة|وسيلة)",
                r"(flew|flies?|flying)\s+(without|with\s*no)\s+(wings|airplane|aid)",
            ], severity=0.85,
        ),
        CommonSenseRule(
            id="phys_004", category="physical",
            description="الشخص الميت لا يتكلم ولا يتحرك / A dead person cannot speak or move",
            check_function_name="check_dead_person",
            violation_patterns=[
                r"المي[تّ]\s+(قال|يتكلم|وقف|مشى|ركض|أجاب)",
                r"(the\s+)?dead\s+(man|person|body)\s+(said|spoke|stood|walked|ran|replied)",
            ], severity=0.95,
        ),
        # ─── الحرارة والديناميكا الحرارية — Thermodynamics ───────────────
        CommonSenseRule(
            id="phys_005", category="physical",
            description="النار تحرق ولا تبرد / Fire burns and does not cool",
            check_function_name="check_fire",
            violation_patterns=[
                r"النار\s+(تبرّد|تبرد|تبريد|تجمّد|تثلج)",
                r"fire\s+(cools?|freezes?|chills?)",
            ], severity=0.90,
        ),
        CommonSenseRule(
            id="phys_006", category="physical",
            description="الثلج بارد ولا يكون ساخناً / Snow/ice is cold, not hot",
            check_function_name="check_snow",
            violation_patterns=[
                r"(الثلج|الجليد)\s+(ساخن|حار|يحترق|يغلي)",
                r"(snow|ice)\s+(is\s+)?(hot|burning|boiling)",
            ], severity=0.90,
        ),
        CommonSenseRule(
            id="phys_007", category="physical",
            description="الماء يتجمد عند صفر مئوية / Water freezes at 0°C",
            check_function_name="check_freezing_point",
            violation_patterns=[
                r"الماء\s+(يتجمد|يتثلج)\s+(فوق|أعلى|أكثر\s+من)\s+\d+",
                r"water\s+(freezes?|turns?\s+to\s+ice)\s+(above|over|at\s+(?:\d+[1-9]|[1-9]\d+))",
            ], severity=0.88,
        ),
        CommonSenseRule(
            id="phys_008", category="physical",
            description="الماء يغلي عند 100 مئوية / Water boils at 100°C",
            check_function_name="check_boiling_point",
            violation_patterns=[
                r"الماء\s+(يغلي|يتبخر)\s+(عند|في)\s+(أقل|تحت)\s+\d+",
                r"water\s+boils?\s+(at|below|under)\s+\d+°?C",
            ], severity=0.87,
        ),
        # ─── البيولوجيا — Biology Basics ──────────────────────────────────
        CommonSenseRule(
            id="phys_009", category="physical",
            description="البشر يحتاجون الأكسجين للعيش / Humans need oxygen to survive",
            check_function_name="check_oxygen",
            violation_patterns=[
                r"(البشر|الإنسان|الناس)\s+(يعيش|يعيشون|يعيشوا)\s+(بدون|من\s+غير)\s+(أكسجين|هواء|تنفس)",
                r"humans?\s+can\s+(live|survive|exist)\s+(without|with\s*no)\s+(oxygen|air|breathing)",
            ], severity=0.95,
        ),
        CommonSenseRule(
            id="phys_010", category="physical",
            description="البشر يحتاجون الماء للعيش / Humans need water to survive",
            check_function_name="check_water_survival",
            violation_patterns=[
                r"(البشر|الإنسان|الناس)\s+(يعيش|يعيشون|يعيشوا)\s+(بدون|من\s+غير)\s+ماء\s+(لمدة\s+)?\d+\s+(يوم|أسبوع|شهر)",
                r"humans?\s+can\s+live\s+without\s+water\s+for\s+\d+\s+(days?|weeks?|months?)",
            ], severity=0.92,
        ),
        CommonSenseRule(
            id="phys_011", category="physical",
            description="البشر يحتاجون الطعام للعيش / Humans need food to survive",
            check_function_name="check_food_survival",
            violation_patterns=[
                r"(البشر|الإنسان)\s+(يعيش|يعيشون)\s+(بدون|من\s+غير)\s+(طعام|أكل)\s+(لمدة\s+)?\d+\s+(شهر|سنة)",
                r"humans?\s+can\s+live\s+without\s+(food|eating)\s+for\s+\d+\s+(months?|years?)",
            ], severity=0.88,
        ),
        CommonSenseRule(
            id="phys_012", category="physical",
            description="الإنسان لا يستطيع التنفس تحت الماء بدون معدات / Humans cannot breathe underwater without equipment",
            check_function_name="check_underwater_breathing",
            violation_patterns=[
                r"(تنفس|يتنفس)\s+(تحت\s+الماء|في\s+الماء)\s+(بدون|من\s+غير)\s+(معدات|أكسجين|أنبوب)",
                r"breath(es?|ing)\s+underwater\s+(without|with\s*no)\s+(equipment|oxygen|tank)",
            ], severity=0.93,
        ),
        CommonSenseRule(
            id="phys_013", category="physical",
            description="الأطفال يولدون صغاراً ولا يولدون بالغين / Babies are born small, not as adults",
            check_function_name="check_birth",
            violation_patterns=[
                r"(وُلد|ولدت)\s+(راشد|بالغ|كبير|ناضج)",
                r"born\s+(as\s+)?(an?\s+)?(adult|fully\s+grown|mature)",
            ], severity=0.90,
        ),
        CommonSenseRule(
            id="phys_014", category="physical",
            description="الإنسان لا يستطيع العيش إلى الأبد / Humans cannot live forever",
            check_function_name="check_immortality",
            violation_patterns=[
                r"(الإنسان|البشر|الناس)\s+(يعيش|يعيشون|خلّد|يخلد)\s+(إلى\s+الأبد|للأبد|أبداً)",
                r"humans?\s+(can\s+)?(live|survive|exist)\s+(forever|eternally|for\s+eternity)",
            ], severity=0.85,
        ),
        CommonSenseRule(
            id="phys_015", category="physical",
            description="الأكل الفاسد يسبب المرض / Spoiled food causes illness",
            check_function_name="check_spoiled_food",
            violation_patterns=[
                r"(الأكل|الطعام)\s+(الفاسد|المنتهي|المتعفن)\s+(مفيد|صحي|آمن|جيد)",
                r"(spoiled|rotten|expired)\s+food\s+(is\s+)?(healthy|safe|good|nutritious)",
            ], severity=0.80,
        ),
        # ─── الضوء والصوت — Light & Sound ────────────────────────────────
        CommonSenseRule(
            id="phys_016", category="physical",
            description="لا شيء يسير أسرع من الضوء / Nothing travels faster than light",
            check_function_name="check_speed_of_light",
            violation_patterns=[
                r"(أسرع|أسرع\s+من)\s+(الضوء|سرعة\s+الضوء)",
                r"faster\s+than\s+(the\s+)?speed\s+of\s+light",
                r"(يسير|يتحرك|يقطع)\s+(أسرع|أكثر\s+سرعة)\s+من\s+الضوء",
            ], severity=0.92,
        ),
        CommonSenseRule(
            id="phys_017", category="physical",
            description="الظلام عدم وجود الضوء / Darkness is absence of light",
            check_function_name="check_darkness",
            violation_patterns=[
                r"الظلام\s+(يضيء|ينير|يشع|يُصدر\s+ضوء)",
                r"darkness\s+(emits?|produces?|radiates?)\s+light",
            ], severity=0.85,
        ),
        CommonSenseRule(
            id="phys_018", category="physical",
            description="الصوت لا ينتشر في الفراغ / Sound cannot travel in a vacuum",
            check_function_name="check_sound_vacuum",
            violation_patterns=[
                r"الصوت\s+(ينتشر|يسير|ينتقل)\s+(في|خلال)\s+(الفراغ|الفضاء)",
                r"sound\s+(travels?|propagates?|moves?)\s+(in|through)\s+(a\s+)?vacuum",
            ], severity=0.88,
        ),
        # ─── الفلك والأرض — Astronomy & Earth ────────────────────────────
        CommonSenseRule(
            id="phys_019", category="physical",
            description="الشمس لا تدور حول الأرض / The Sun does not revolve around the Earth",
            check_function_name="check_heliocentric",
            violation_patterns=[
                r"الشمس\s+تدور\s+حول\s+الأرض",
                r"the\s+sun\s+revolves?\s+around\s+the\s+earth",
                r"الأرض\s+مركز\s+الكون",
            ], severity=0.88,
        ),
        CommonSenseRule(
            id="phys_020", category="physical",
            description="الأرض كروية وليست مسطحة / The Earth is spherical, not flat",
            check_function_name="check_earth_shape",
            violation_patterns=[
                r"الأرض\s+(مسطحة|مربع[ةٍ])",
                r"the\s+earth\s+is\s+flat",
            ], severity=0.90,
        ),
        CommonSenseRule(
            id="phys_021", category="physical",
            description="القمر أصغر من الأرض / The Moon is smaller than Earth",
            check_function_name="check_moon_size",
            violation_patterns=[
                r"القمر\s+(أكبر|أضخم|أعظم)\s+من\s+الأرض",
                r"the\s+moon\s+is\s+(bigger|larger|greater)\s+than\s+(the\s+)?earth",
            ], severity=0.90,
        ),
        CommonSenseRule(
            id="phys_022", category="physical",
            description="الليل والنهار ناتجان عن دوران الأرض / Day and night result from Earth's rotation",
            check_function_name="check_day_night",
            violation_patterns=[
                r"الشمس\s+(تغيب|تختفي|تسقط)\s+(تحت|في)\s+الأرض\s+(للليل|في\s+الليل)",
                r"the\s+sun\s+(sets?|goes?\s+down)\s+(under|beneath)\s+the\s+earth",
            ], severity=0.85,
        ),
        # ─── الطاقة والمادة — Energy & Matter ────────────────────────────
        CommonSenseRule(
            id="phys_023", category="physical",
            description="الطاقة لا تُخلق من العدم / Energy cannot be created from nothing",
            check_function_name="check_energy_conservation",
            violation_patterns=[
                r"الطاقة\s+(تُخلق|تُصنع|تظهر)\s+(من|من\s+ال)\s+(عدم|لا\s+شيء|فراغ)",
                r"energy\s+(is\s+)?(created|produced|generated)\s+(from|out\s+of)\s+(nothing|thin\s+air|void)",
            ], severity=0.92,
        ),
        CommonSenseRule(
            id="phys_024", category="physical",
            description="المادة لا تختفي بل تتحول / Matter does not disappear, it transforms",
            check_function_name="check_matter_conservation",
            violation_patterns=[
                r"المادة\s+(تختفي|تزول|تعدم)\s+(تماماً|كلياً)",
                r"matter\s+(disappears?|vanishes?)\s+(completely|entirely|into\s+nothing)",
            ], severity=0.88,
        ),
        CommonSenseRule(
            id="phys_025", category="physical",
            description="الحديد يغرق في الماء / Iron sinks in water",
            check_function_name="check_iron_sink",
            violation_patterns=[
                r"(الحديد|المعدن|الفولاذ)\s+(يطفو|يسبح|يعوم)\s+(على|فوق)\s+الماء",
                r"(iron|steel|metal)\s+(floats?|swims?)\s+(on|in)\s+water",
            ], severity=0.85,
        ),
        CommonSenseRule(
            id="phys_026", category="physical",
            description="الخشب يطفو على الماء / Wood floats on water",
            check_function_name="check_wood_float",
            violation_patterns=[
                r"الخشب\s+(يغرق|يسقط|يهبط)\s+(في|إلى\s+قاع)\s+الماء",
                r"wood\s+(sinks?|goes?\s+to\s+the\s+bottom)\s+(in|of)\s+water",
            ], severity=0.80,
        ),
        # ─── إضافية — Additional Physical Rules ──────────────────────────
        CommonSenseRule(
            id="phys_027", category="physical",
            description="الزجاج هش وينكسر / Glass is fragile and breaks",
            check_function_name="check_glass_fragile",
            violation_patterns=[
                r"الزجاج\s+(لا\s+ينكسر|متين|صلب|لا\s+يُكسر)",
                r"glass\s+(doesn'?t\s+break|is\s+unbreakable|is\s+strong|cannot\s+be\s+broken)",
            ], severity=0.82,
        ),
        CommonSenseRule(
            id="phys_028", category="physical",
            description="المطاط يتمدد ولا ينكمش عند سحبه / Rubber stretches, doesn't shrink when pulled",
            check_function_name="check_rubber",
            violation_patterns=[
                r"المطاط\s+(ينكمش|يتقلص)\s+(عند|إذا)\s+(سحب|شد)",
                r"rubber\s+(shrinks?|contracts?)\s+(when|if)\s+(pulled|stretched)",
            ], severity=0.78,
        ),
        CommonSenseRule(
            id="phys_029", category="physical",
            description="الصخرة صلبة لا يمكن ثقبها باليد / Rocks are solid and cannot be pierced by hand",
            check_function_name="check_rock_hardness",
            violation_patterns=[
                r"(ثقب|خرق|شق)\s+(الصخرة|الحجر)\s+(باليد|بإصبع|بيده)",
                r"(pierce|penetrate|break)\s+(a\s+)?(rock|stone)\s+(with|by)\s+(bare\s+hand|finger)",
            ], severity=0.85,
        ),
        CommonSenseRule(
            id="phys_030", category="physical",
            description="الشخص لا يستطيع رفع أكثر من وزنه عادةً / A person cannot normally lift more than their weight",
            check_function_name="check_human_strength",
            violation_patterns=[
                r"(رفع|حمل)\s+(طن|أطنان|سيارة|فيل)\s+(بيده|بيد\s+واحدة|بسهولة)",
                r"(lifted|carried)\s+(a\s+)?(car|elephant|ton|truck)\s+(with\s+one\s+hand|easily|barehanded)",
            ], severity=0.80,
        ),
        CommonSenseRule(
            id="phys_031", category="physical",
            description="الماء لا يحترق / Water does not burn",
            check_function_name="check_water_burn",
            violation_patterns=[
                r"الماء\s+(يحترق|يشتعل|يُشعل)",
                r"water\s+(burns?|catches?\s+fire|ignites?)",
            ], severity=0.92,
        ),
        CommonSenseRule(
            id="phys_032", category="physical",
            description="الهواء له وزن / Air has weight",
            check_function_name="check_air_weight",
            violation_patterns=[
                r"الهواء\s+(ليس\s+له|لا\s+يملك|بدون)\s+وزن",
                r"air\s+(has\s+no|doesn'?t\s+have|is\s+without)\s+weight",
            ], severity=0.80,
        ),
        CommonSenseRule(
            id="phys_033", category="physical",
            description="النباتات تحتاج ضوء الشمس للنمو / Plants need sunlight to grow",
            check_function_name="check_plant_sunlight",
            violation_patterns=[
                r"النباتات?\s+(تنمو|تعيش|تزدهر)\s+(بدون|من\s+غير)\s+(شمس|ضوء|شمس)",
                r"plants?\s+(can\s+)?(grow|live|thrive)\s+(without|with\s*no)\s+(sunlight|sun|light)",
            ], severity=0.82,
        ),
        CommonSenseRule(
            id="phys_034", category="physical",
            description="الحليب يفسد إذا تُرك خارج الثلاجة / Milk spoils if left outside the fridge",
            check_function_name="check_milk_spoil",
            violation_patterns=[
                r"الحليب\s+(لا\s+يفسد|يبقى|يظل)\s+(طازج|صالح|جيد)\s+(خارج|بدون)\s+(الثلاجة|تبريد)",
                r"milk\s+(doesn'?t|does\s+not|won'?t)\s+spoil\s+(outside|without\s+refrigeration)",
            ], severity=0.78,
        ),
        CommonSenseRule(
            id="phys_035", category="physical",
            description="المعادن توصل الكهرباء / Metals conduct electricity",
            check_function_name="check_metal_conductivity",
            violation_patterns=[
                r"المعادن?\s+(لا\s+توصل|لا\s+تنقل|عازل[ة])\s+(الكهرباء|التيار)",
                r"metals?\s+(do\s+not|doesn'?t)\s+conduct\s+electricity",
            ], severity=0.85,
        ),
        CommonSenseRule(
            id="phys_036", category="physical",
            description="الخشب عازل للكهرباء / Wood is an electrical insulator",
            check_function_name="check_wood_insulator",
            violation_patterns=[
                r"الخشب\s+(موصل|يوصل|ينقل)\s+(الكهرباء|التيار)",
                r"wood\s+conducts?\s+electricity",
            ], severity=0.80,
        ),
        CommonSenseRule(
            id="phys_037", category="physical",
            description="الجليد يذوب عند تسخينه / Ice melts when heated",
            check_function_name="check_ice_melt",
            violation_patterns=[
                r"الجليد\s+(لا\s+يذوب|يبقى|يستمر)\s+(صلب|جليد)\s+(عند|إذا)\s+(تسخين|حرارة)",
                r"ice\s+(doesn'?t|does\s+not)\s+melt\s+(when|if)\s+heated",
            ], severity=0.88,
        ),
        CommonSenseRule(
            id="phys_038", category="physical",
            description="الماء يتبخر عند الغليان / Water evaporates when boiled",
            check_function_name="check_evaporation",
            violation_patterns=[
                r"الماء\s+(لا\s+يتبخر|يبقى)\s+(سائل|ماء)\s+(عند|إذا)\s+غلي",
                r"water\s+(doesn'?t|does\s+not)\s+evaporate\s+(when|if)\s+boiled",
            ], severity=0.85,
        ),
        CommonSenseRule(
            id="phys_039", category="physical",
            description="البرق يسبق الرعد دائماً / Lightning always precedes thunder",
            check_function_name="check_lightning_thunder",
            violation_patterns=[
                r"الرعد\s+(يسبق|يأتي\s+قبل)\s+البرق",
                r"thunder\s+(precedes?|comes?\s+before)\s+lightning",
            ], severity=0.82,
        ),
        CommonSenseRule(
            id="phys_040", category="physical",
            description="القمر لا يصدر ضوءاً خاصاً / The Moon does not emit its own light",
            check_function_name="check_moon_light",
            violation_patterns=[
                r"القمر\s+(يصدر|يُنتج|يشع)\s+(ضوء|نور)\s+(خاص|ذاتي|من\s+نفسه)",
                r"the\s+moon\s+(emits?|produces?|generates?)\s+(its\s+own|self)\s+light",
            ], severity=0.83,
        ),
        CommonSenseRule(
            id="phys_041", category="physical",
            description="السماء زرقاء بسبب تشتت الضوء / The sky is blue due to light scattering",
            check_function_name="check_sky_color",
            violation_patterns=[
                r"السماء\s+(زرقاء\s+لأنها|ملونة\s+باللون\s+الأزرق\s+لأنها)\s+(مائية|ماء|بحر)",
                r"the\s+sky\s+is\s+blue\s+because\s+it'?s\s+(water|ocean|sea|reflects?\s+the\s+sea)",
            ], severity=0.75,
        ),
        CommonSenseRule(
            id="phys_042", category="physical",
            description="المغناطيس يجذب الحديد لا الخشب / Magnets attract iron, not wood",
            check_function_name="check_magnet",
            violation_patterns=[
                r"المغناطيس\s+(يجذب|يجذب\s+إلى)\s+(الخشب|البلاستيك|الزجاج)",
                r"magnets?\s+(attracts?|pulls?)\s+(wood|plastic|glass)",
            ], severity=0.85,
        ),
        CommonSenseRule(
            id="phys_043", category="physical",
            description="الإنسان لا يستطيع السباحة في الحمم البركانية / Humans cannot swim in volcanic lava",
            check_function_name="check_lava",
            violation_patterns=[
                r"(سبح|يسبح)\s+(في|داخل)\s+(الحمم|اللافا|البركان)",
                r"(sw[ai]m|swimming)\s+(in|through)\s+(lava|magma|volcanic)",
            ], severity=0.95,
        ),
        CommonSenseRule(
            id="phys_044", category="physical",
            description="الإنسان لا يستطيع الأكل بقدميه / Humans cannot eat with their feet",
            check_function_name="check_eat_feet",
            violation_patterns=[
                r"(أكل|يأكل)\s+(بقدم|بقدميه|برجليه)",
                r"(eat|eating)\s+(with|using)\s+(feet|foot|toes)",
            ], severity=0.80,
        ),
        CommonSenseRule(
            id="phys_045", category="physical",
            description="الوقت لا يعود للوراء / Time does not go backward",
            check_function_name="check_time_reverse",
            violation_patterns=[
                r"الوقت\s+(يعود|يرجع|يسير)\s+(للوراء|إلى\s+الوراء|بالاتجاه\s+المعاكس)",
                r"time\s+(goes?|moves?|runs?|flows?)\s+backward",
            ], severity=0.92,
        ),
        CommonSenseRule(
            id="phys_046", category="physical",
            description="الأسماك تموت خارج الماء / Fish die out of water",
            check_function_name="check_fish_water",
            violation_patterns=[
                r"السمك[ة]?\s+(تعيش|تعيشون|تنجو)\s+(خارج|برّاً|بدون)\s+الماء\s+(لمدة\s+)?\d+",
                r"fish\s+(can\s+)?(live|survive)\s+(out\s+of|without)\s+water\s+for\s+\d+",
            ], severity=0.90,
        ),
        CommonSenseRule(
            id="phys_047", category="physical",
            description="الطيور تبيض ولا تلد / Birds lay eggs, they don't give live birth",
            check_function_name="check_bird_eggs",
            violation_patterns=[
                r"الطيور?\s+(تلد|تضع\s+صغار|تحمل)\s+(صغير|مولود)",
                r"birds?\s+(give\s+birth|deliver)\s+(to\s+)?(babies?|young|offspring)",
            ], severity=0.85,
        ),
        CommonSenseRule(
            id="phys_048", category="physical",
            description="الزئبق سائل في درجة حرارة الغرفة / Mercury is liquid at room temperature",
            check_function_name="check_mercury",
            violation_patterns=[
                r"الزئبق\s+(صلب|جامد)\s+(في|عند)\s+(درجة\s+حرارة\s+الغرفة|الحرارة\s+العادية)",
                r"mercury\s+is\s+(solid|hard)\s+at\s+room\s+temperature",
            ], severity=0.78,
        ),
        CommonSenseRule(
            id="phys_049", category="physical",
            description="لا يمكن سماع الانفجارات في الفضاء / Explosions cannot be heard in space",
            check_function_name="check_space_sound",
            violation_patterns=[
                r"(سُمع|يسمع|سماع)\s+(انفجار|صوت)\s+(في|من)\s+(الفضاء|الفراغ\s+الخارجي)",
                r"(heard|hear)\s+(an?\s+)?(explosion|sound|bang)\s+in\s+(space|outer\s+space)",
            ], severity=0.85,
        ),
        CommonSenseRule(
            id="phys_050", category="physical",
            description="الإنسان لا يستطيع رؤية الأشعة تحت الحمراء بالعين المجردة / Humans cannot see infrared light with naked eyes",
            check_function_name="check_infrared",
            violation_patterns=[
                r"(الإنسان|البشر|الناس)\s+(يرى|يرون|يمكنهم\s+رؤية)\s+(الأشعة\s+تحت\s+الحمراء|الأشعة\s+الحمراء)\s+(بالعين|بالعين\s+المجردة)",
                r"humans?\s+can\s+see\s+infrared\s+(light|radiation|rays)\s+with\s+(the\s+)?(naked\s+)?eyes?",
            ], severity=0.80,
        ),
        CommonSenseRule(
            id="phys_051", category="physical",
            description="الماء العذب أخف من الماء المالح / Fresh water is lighter than salt water",
            check_function_name="check_water_density",
            violation_patterns=[
                r"الماء\s+(العذب|الحلو)\s+(أثقل|أكثف)\s+من\s+الماء\s+(المالح|المملح)",
                r"fresh\s*water\s+is\s+(heavier|denser)\s+than\s+salt\s*water",
            ], severity=0.75,
        ),
        CommonSenseRule(
            id="phys_052", category="physical",
            description="الماء يتمدد عند التجمد / Water expands when freezing",
            check_function_name="check_water_expansion",
            violation_patterns=[
                r"الماء\s+(ينكمش|يتقلص|يصغر)\s+(عند|إذا)\s+(تجمد|تثلج)",
                r"water\s+(contracts?|shrinks?)\s+(when|if|upon)\s+(freezing|it\s+freezes)",
            ], severity=0.82,
        ),
    ]

    def __init__(self):
        """تهيئة فاحص الاحتمالية الفيزيائية."""
        self._rules = list(self._PHYSICAL_RULES)

    def _extract_claims(self, text: str) -> list[Claim]:
        """
        استخراج الادعاءات القابلة للاختبار من النص.
        Extract testable claims from text.

        يقسم النص إلى جمل ويحدد أيها يحتوي على ادعاءات قابلة للاختبار
        مقابل قواعد الاحتمالية الفيزيائية.
        """
        if not text or not text.strip():
            return []

        # تقسيم النص إلى جمل — split into sentences
        sentences = re.split(r"(?<=[.!?؟。！？])\s+", text.strip())
        claims: list[Claim] = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 5:
                continue

            # فحص هل الجملة تحتوي على فعل أو ادعاء قابل للاختبار
            has_action_verb = bool(re.search(
                r"(ي\w+|ت\w+|will|can|is|are|was|were|does|do|has|have|had)\b",
                sentence, re.IGNORECASE,
            ))

            if has_action_verb:
                claims.append(Claim(
                    text=sentence,
                    claim_type="physical",
                    testable=True,
                ))

        return claims

    def _evaluate_claim(self, claim: Claim, rules: list[CommonSenseRule]) -> Optional[Violation]:
        """
        تقييم ادعاء واحد مقابل القواعد الفيزيائية.
        Evaluate a single claim against physical rules.

        يرجع انتهاكاً إن وجد، أو None إن لم يُوجد.
        """
        for rule in rules:
            violation_desc = rule.check(claim.text)
            if violation_desc is not None:
                return Violation(
                    claim=claim.text,
                    rule_violated=rule.id,
                    severity=rule.severity,
                    explanation=violation_desc,
                )
        return None

    def check(self, text: str) -> list[Violation]:
        """
        فحص النص بالكامل مقابل القواعد الفيزيائية.
        Check full text against all physical plausibility rules.

        Args:
            text: النص المراد فحصه

        Returns:
            قائمة بالانتهاكات المكتشفة
        """
        claims = self._extract_claims(text)
        violations: list[Violation] = []

        for claim in claims:
            violation = self._evaluate_claim(claim, self._rules)
            if violation is not None:
                violations.append(violation)

        # فحص النص الكامل أيضاً — بعض الأنماط تمتد عبر جمل متعددة
        full_text_claim = Claim(text=text, claim_type="physical", testable=True)
        violation = self._evaluate_claim(full_text_claim, self._rules)
        if violation is not None:
            # تجنب التكرار — avoid duplicates
            already_found = any(v.rule_violated == violation.rule_violated for v in violations)
            if not already_found:
                violations.append(violation)

        return violations

    def get_rules(self) -> list[CommonSenseRule]:
        """إرجاع القواعد الفيزيائية النشطة — Return active physical rules."""
        return list(self._rules)

    def add_rule(self, rule: CommonSenseRule) -> None:
        """إضافة قاعدة فيزيائية جديدة — Add a new physical rule."""
        self._rules.append(rule)


# ═══════════════════════════════════════════════════════════════════════════════
# فاحص المعايير الاجتماعية — Social Norm Checker
# ═══════════════════════════════════════════════════════════════════════════════


class SocialNormChecker:
    """
    فاحص المعايير الاجتماعية — Checks claims against social/cultural norms.

    يحتوي على قاعدة بيانات واعية ثقافياً تشمل:
    - المعايير العربية/الإسلامية كأساس أولي
    - المعايير الغربية كأساس ثانوي
    - كشف: اقتراحات غير لائقة، عدم حساسية ثقافية، انتهاكات الخصوصية
    """

    # 30+ قاعدة معايير اجتماعية — Social norm rules
    _SOCIAL_RULES: list[CommonSenseRule] = [
        # ─── الكرم والضيافة — Hospitality (Arab/Islamic) ─────────────────
        CommonSenseRule(
            id="social_001", category="social",
            description="إهانة الضيف انتهاك للكرم العربي / Insulting a guest violates Arab hospitality",
            check_function_name="check_guest_insult",
            violation_patterns=[
                r"(أهان|شتم|أهانة)\s+(الضيف|الزائر|الضيوف)",
                r"(insulted|offended)\s+(the\s+)?(guest|visitor)",
            ], severity=0.70,
        ),
        CommonSenseRule(
            id="social_002", category="social",
            description="رفض إطعام الضيف جوعان انتهاك للكرم / Refusing to feed a hungry guest violates hospitality",
            check_function_name="check_refuse_food",
            violation_patterns=[
                r"(رفض|منع)\s+(إطعام|تقديم\s+طعام)\s+(الضيف|الزائر)\s+(وهو\s+)?(جوعان|جائع)",
                r"(refused|denied)\s+(to\s+)?(feed|give\s+food)\s+(the\s+)?(guest|visitor)\s+(who\s+was\s+)?(hungry|starving)",
            ], severity=0.72,
        ),
        CommonSenseRule(
            id="social_003", category="social",
            description="عدم تقديم القهوة للضيف عربياً عدم كرم / Not offering coffee to a guest is inhospitable in Arab culture",
            check_function_name="check_coffee_hospitality",
            violation_patterns=[
                r"(لم\s+يقدم|رفض\s+تقديم)\s+(القهوة|الشاي)\s+(للضيف|للزائر)",
                r"(didn'?t|did\s+not|refused\s+to)\s+(offer|serve)\s+(coffee|tea)\s+to\s+(the\s+)?(guest|visitor)",
            ], severity=0.55,
        ),
        # ─── احترام الوالدين — Respect for Parents ──────────────────────
        CommonSenseRule(
            id="social_004", category="social",
            description="عدم احترام الوالدين انتهاك للمعايير الثقافية / Disrespecting parents violates cultural norms",
            check_function_name="check_parent_respect",
            violation_patterns=[
                r"(عقّ|عقوق|عدم\s+احترام)\s+(الوالدين|الأب|الأم)",
                r"(disrespecting|disobeying)\s+(parents|father|mother)",
            ], severity=0.65,
        ),
        CommonSenseRule(
            id="social_005", category="social",
            description="ضرب الوالدين محرم ثقافياً ودينياً / Striking parents is culturally and religiously forbidden",
            check_function_name="check_parent_violence",
            violation_patterns=[
                r"(ضرب|صفع|اعتدى)\s+(على\s+)?(والدي|أبي|أمي|الأب|الأم)",
                r"(hit|struck|beat|slapped)\s+(my\s+)?(parents?|father|mother|mom|dad)",
            ], severity=0.90,
        ),
        # ─── الوعد والأمانة — Promise & Trust ────────────────────────────
        CommonSenseRule(
            id="social_006", category="social",
            description="كسر الوعد انتهاك للثقة / Breaking a promise violates trust",
            check_function_name="check_promise_break",
            violation_patterns=[
                r"(كسر|نكث|خلف)\s+(الوعد|العهد)",
                r"(broke|breaking)\s+(a\s+)?(promise|oath|pledge|vow)",
            ], severity=0.60,
        ),
        CommonSenseRule(
            id="social_007", category="social",
            description="الغش في المعاملة خيانة للأمانة / Cheating in dealings betrays trust",
            check_function_name="check_cheating",
            violation_patterns=[
                r"(غشّ|خدع|احتال)\s+(في|على)\s+(البيع|الشراء|المعاملة|الناس)",
                r"(cheated|defrauded|scammed)\s+(in|on|during)\s+(a\s+)?(deal|transaction|trade|sale)",
            ], severity=0.72,
        ),
        # ─── الحياء والخصوصية — Modesty & Privacy ───────────────────────
        CommonSenseRule(
            id="social_008", category="social",
            description="انتهاك خصوصية الآخرين غير مقبول / Violating others' privacy is unacceptable",
            check_function_name="check_privacy_violation",
            violation_patterns=[
                r"(تجسس|راقب|اخترق)\s+(على\s+)?(خصوصية|حياة|هاتف|رسائل)\s+(الآخرين|الناس|شخص)",
                r"(spied|snooped|intruded|invaded)\s+(on|into)\s+(someone'?s?\s+)?(privacy|messages?|phone|life)",
            ], severity=0.75,
        ),
        CommonSenseRule(
            id="social_009", category="social",
            description="إفشاء الأسرار الشخصية انتهاك للثقة / Revealing personal secrets violates trust",
            check_function_name="check_secret_reveal",
            violation_patterns=[
                r"(أفشى|كشف|نشر)\s+(سر|أسرار)\s+(شخص|الآخرين|صديق)",
                r"(revealed|disclosed|leaked|shared)\s+(someone'?s?\s+)?(secret|secrets|confidential)",
            ], severity=0.70,
        ),
        # ─── آداب الطعام — Dining Etiquette ─────────────────────────────
        CommonSenseRule(
            id="social_010", category="social",
            description="الأكل بصوت عالٍ غير مهذب / Eating loudly is impolite",
            check_function_name="check_loud_eating",
            violation_patterns=[
                r"(أكل|يأكل)\s+(بصوت\s+عالٍ|بضجيج|بإزعاج)",
                r"(eating|ate)\s+(loudly|noisily|with\s+mouth\s+open)",
            ], severity=0.40,
        ),
        CommonSenseRule(
            id="social_011", category="social",
            description="لا ينبغي رفض الطعام المقدم من مضيف عربي / One should not reject food offered by an Arab host",
            check_function_name="check_reject_food",
            violation_patterns=[
                r"(رفض|أبى)\s+(الأكل|الطعام)\s+(المقدم|الذي\s+قدمه)\s+(المضيف|صاحب\s+البيت)",
                r"(refused|declined|rejected)\s+(the\s+)?(food|meal|dish)\s+(offered|served|prepared)\s+by\s+(the\s+)?(host)",
            ], severity=0.50,
        ),
        # ─── المعايير الإسلامية — Islamic Norms ─────────────────────────
        CommonSenseRule(
            id="social_012", category="social",
            description="شرب الخمر محرم في الإسلام / Drinking alcohol is prohibited in Islam",
            check_function_name="check_alcohol_islam",
            violation_patterns=[
                r"(شرب|يتناول)\s+(الخمر|الكحول|المسكر)\s+(حلال|مسموح|جائز)\s+(في\s+الإسلام|للمسلم)",
                r"(drinking|consuming)\s+alcohol\s+(is\s+)?(halal|permitted|allowed)\s+in\s+Islam",
            ], severity=0.80,
        ),
        CommonSenseRule(
            id="social_013", category="social",
            description="أكل لحم الخنزير محرم في الإسلام / Eating pork is prohibited in Islam",
            check_function_name="check_pork_islam",
            violation_patterns=[
                r"(أكل|تناول)\s+(لحم\s+الخنزير|الخنزير)\s+(حلال|مسموح|جائز)\s+(في\s+الإسلام|للمسلم)",
                r"(eating|consuming)\s+pork\s+(is\s+)?(halal|permitted|allowed)\s+in\s+Islam",
            ], severity=0.80,
        ),
        CommonSenseRule(
            id="social_014", category="social",
            description="الصلاة واجبة على المسلم / Prayer is obligatory for Muslims",
            check_function_name="check_prayer_obligation",
            violation_patterns=[
                r"الصلاة\s+(ليست\s+واجبة|غير\s+مطلوبة|لا\s+لازم)\s+(على|من)\s+(المسلم|المسلمين)",
                r"(prayer|salah)\s+(is\s+not|isn'?t)\s+(obligatory|required|mandatory)\s+for\s+(Muslims?|the\s+Muslim)",
            ], severity=0.70,
        ),
        CommonSenseRule(
            id="social_015", category="social",
            description="الربا محرم في الإسلام / Usury/interest is prohibited in Islam",
            check_function_name="check_usury_islam",
            violation_patterns=[
                r"الربا\s+(حلال|مسموح|جائز|مباح)\s+(في\s+الإسلام)",
                r"(usury|interest|riba)\s+(is\s+)?(halal|permitted|allowed)\s+in\s+Islam",
            ], severity=0.78,
        ),
        # ─── آداب التعامل — Interpersonal Etiquette ─────────────────────
        CommonSenseRule(
            id="social_016", category="social",
            description="السلام على الآخرين من الآداب / Greeting others is good manners",
            check_function_name="check_greeting",
            violation_patterns=[
                r"(تجاهل|تخطى|لم\s+يُسلّم)\s+(على|سلام)\s+(الجار|الصديق|المعرفة)",
                r"(ignored|avoided|didn'?t\s+greet)\s+(the\s+)?(neighbor|friend|acquaintance)",
            ], severity=0.45,
        ),
        CommonSenseRule(
            id="social_017", category="social",
            description="قطع الحديث غير مهذب / Interrupting someone is impolite",
            check_function_name="check_interrupting",
            violation_patterns=[
                r"(قاطع|يقاطع|تَقَاطُع)\s+(الحديث|الكلام|الحديث)",
                r"(interrupted|interrupts?|cutting\s+off)\s+(someone|a\s+conversation|the\s+speaker)",
            ], severity=0.50,
        ),
        CommonSenseRule(
            id="social_018", category="social",
            description="الكذب على الآخرين سلوك سيء / Lying to others is bad behavior",
            check_function_name="check_lying",
            violation_patterns=[
                r"(كذب|يكذب|أكذوبة)\s+(على)\s+(الناس|الأصدقاء|العائلة)",
                r"(lied|lies?|lying)\s+to\s+(people|friends?|family)",
            ], severity=0.65,
        ),
        # ─── حساسية ثقافية — Cultural Sensitivity ────────────────────────
        CommonSenseRule(
            id="social_019", category="social",
            description="السخرية من الأديان غير مقبولة / Mocking religions is unacceptable",
            check_function_name="check_religion_mockery",
            violation_patterns=[
                r"(سخر|سخرية|استهزاء)\s+(من|بال)\s+(دين|الأديان|الإسلام|المسيحية|اليهودية)",
                r"(mocked|mockery|making\s+fun)\s+(of|about)\s+(religion|Islam|Christianity|Judaism|faith)",
            ], severity=0.85,
        ),
        CommonSenseRule(
            id="social_020", category="social",
            description="التحقير بسبب العرق أو الجنسية غير مقبول / Demeaning based on race or nationality is unacceptable",
            check_function_name="check_racism",
            violation_patterns=[
                r"(تحقير|إهانة|عنصرية)\s+(بسبب|على\s+أساس)\s+(العرق|الجنسية|اللون|الأصل)",
                r"(demeaning|insulting|racist)\s+(based\s+on|because\s+of)\s+(race|nationality|color|origin|ethnicity)",
            ], severity=0.85,
        ),
        CommonSenseRule(
            id="social_021", category="social",
            description="التمييز ضد المرأة غير مقبول / Discrimination against women is unacceptable",
            check_function_name="check_gender_discrimination",
            violation_patterns=[
                r"(تمييز|عنصرية)\s+(ضد|على)\s+(المرأة|النساء|البنات)",
                r"(discrimination|sexism|prejudice)\s+(against|toward)\s+(women|females?|girls)",
            ], severity=0.80,
        ),
        # ─── معايير غربية — Western Norms ────────────────────────────────
        CommonSenseRule(
            id="social_022", category="social",
            description="الحضور المتأخر بدون إخطار غير مهذب غربياً / Arriving late without notice is impolite in Western culture",
            check_function_name="check_lateness_western",
            violation_patterns=[
                r"(تأخر|وصل\s+متأخر)\s+(بدون|من\s+غير)\s+(إخطار|إعلام|اتصال)",
                r"(arrived\s+late|was\s+late|showed\s+up\s+late)\s+(without|with\s*no)\s+(notice|calling|informing)",
            ], severity=0.50,
        ),
        CommonSenseRule(
            id="social_023", category="social",
            description="عدم ترك إكرامية في المطعم الغربي غير مهذب / Not tipping at Western restaurants is impolite",
            check_function_name="check_tipping",
            violation_patterns=[
                r"(لم\s+يترك|رفض\s+ترك)\s+(إكرامية|بقشيش)\s+(في|عند)\s+(المطعم|المراقص)",
                r"(didn'?t|did\s+not|refused\s+to)\s+(leave|give)\s+(a\s+)?(tip|gratuity)\s+(at|in)\s+(the\s+)?(restaurant)",
            ], severity=0.40,
        ),
        CommonSenseRule(
            id="social_024", category="social",
            description="التحدث بصوت عالٍ في الأماكن العامة غير مهذب / Talking loudly in public spaces is impolite",
            check_function_name="check_loud_public",
            violation_patterns=[
                r"(تحدث|يتحدث|صرخ)\s+(بصوت\s+عالٍ|بصوت\s+مرتفع)\s+(في|بـ)\s+(المكان\s+العام|الشارع|المكتبة|المستشفى)",
                r"(talking|speaking|yelling)\s+(loudly|at\s+the\s+top\s+of)\s+(in|at)\s+(public|the\s+(street|library|hospital))",
            ], severity=0.45,
        ),
        # ─── احترام المعاقين وكبار السن — Respect for Disabled & Elderly ─
        CommonSenseRule(
            id="social_025", category="social",
            description="السخرية من ذوي الاحتياجات الخاصة غير مقبولة / Mocking people with disabilities is unacceptable",
            check_function_name="check_disability_mockery",
            violation_patterns=[
                r"(سخر|سخرية|استهزاء)\s+(من|بال)\s+(المعاق|ذوي\s+الاحتياجات|الإعاقة|الأصم|الأعمى)",
                r"(mocked|mockery|making\s+fun)\s+(of|about)\s+(the\s+)?(disabled|handicapped|deaf|blind|wheelchair)",
            ], severity=0.88,
        ),
        CommonSenseRule(
            id="social_026", category="social",
            description="عدم احترام كبار السن انتهاك للمعايير / Disrespecting the elderly violates norms",
            check_function_name="check_elderly_respect",
            violation_patterns=[
                r"(أهان|عاق|تجاهل|استهزأ)\s+(بـ|من)\s+(كبار\s+السن|المسن|الكبير\s+في\s+السن|الشيخ)",
                r"(insulted|disrespected|ignored|mocked)\s+(the\s+)?(elderly|old\s+(man|woman|people)|senior)",
            ], severity=0.70,
        ),
        # ─── احترام الموتى — Respect for the Deceased ────────────────────
        CommonSenseRule(
            id="social_027", category="social",
            description="الافتخار بالموتى أو السخرية منهم غير مقبول / Boasting about or mocking the dead is unacceptable",
            check_function_name="check_dead_respect",
            violation_patterns=[
                r"(سخر|افتخر|ضحك)\s+(من|على)\s+(الميت|الموتى|الجنازة|الدفين)",
                r"(mocked|laughed|boasted)\s+(at|about)\s+(the\s+)?(dead|deceased|funeral|corpse)",
            ], severity=0.80,
        ),
        # ─── حقوق الطفل — Children's Rights ──────────────────────────────
        CommonSenseRule(
            id="social_028", category="social",
            description="إيذاء الأطفال غير مقبول / Harming children is unacceptable",
            check_function_name="check_child_harm",
            violation_patterns=[
                r"(ضرب|آذى|عاقب\s+بقسوة|أساء)\s+(الطفل|الأطفال|الصغير)",
                r"(hit|beat|hurt|harmed|abused)\s+(the\s+)?(child|children|kid|baby|toddler)",
            ], severity=0.92,
        ),
        CommonSenseRule(
            id="social_029", category="social",
            description="تشغيل الأطفال في أعمال شاقة غير مقبول / Child labor in heavy work is unacceptable",
            check_function_name="check_child_labor",
            violation_patterns=[
                r"(شغّل|استغل|أجبر)\s+(الطفل|الأطفال)\s+(في|على)\s+(العمل|المناجم|المصانع|أعمال\s+شاقة)",
                r"(employed|used|forced)\s+(a\s+)?(child|children)\s+(to\s+)?(work|labor|mine|factory)",
            ], severity=0.85,
        ),
        # ─── العدالة — Justice & Fairness ─────────────────────────────────
        CommonSenseRule(
            id="social_030", category="social",
            description="الرشوة فساد وغير مقبولة / Bribery is corruption and unacceptable",
            check_function_name="check_bribery",
            violation_patterns=[
                r"(قدّم|أعطى|دفع)\s+(رشوة|مبلغ)\s+(لـ|إلى)\s+(المسؤول|القاضي|الشرطة)",
                r"(offered|gave|paid)\s+(a\s+)?(bribe|kickback)\s+to\s+(the\s+)?(official|judge|police|officer)",
            ], severity=0.82,
        ),
        CommonSenseRule(
            id="social_031", category="social",
            description="سرقة ممتلكات الآخرين جريمة / Stealing others' property is a crime",
            check_function_name="check_stealing",
            violation_patterns=[
                r"(سرق|يسرق|أخذ)\s+(ممتلكات|أشياء|مال)\s+(الآخرين|شخص|الناس)",
                r"(stole|steals?|robbed)\s+(someone'?s?\s+)?(property|things|money|belongings)",
            ], severity=0.88,
        ),
        CommonSenseRule(
            id="social_032", category="social",
            description="الاعتداء على الضعفاء جُبن / Attacking the weak is cowardice",
            check_function_name="check_attacking_weak",
            violation_patterns=[
                r"(اعتدى|هاجم|ضرب)\s+(على\s+)?(الضعيف|الأعمى|المريض|الأرملة|اليتيم)",
                r"(attacked|assaulted|beat)\s+(the\s+)?(weak|blind|sick|widow|orphan|helpless)",
            ], severity=0.85,
        ),
    ]

    def __init__(self, cultural_context: str = CULTURAL_CONTEXT):
        """
        تهيئة فاحص المعايير الاجتماعية.

        Args:
            cultural_context: السياق الثقافي — arab_islamic | western | universal
        """
        self._cultural_context = cultural_context
        self._rules = list(self._SOCIAL_RULES)

    def check(self, claims: list[Claim]) -> list[Violation]:
        """
        فحص الادعاءات مقابل المعايير الاجتماعية.
        Check claims against social norms.

        Args:
            claims: قائمة الادعاءات المراد فحصها

        Returns:
            قائمة بالانتهاكات الاجتماعية المكتشفة
        """
        violations: list[Violation] = []

        for claim in claims:
            for rule in self._rules:
                violation_desc = rule.check(claim.text)
                if violation_desc is not None:
                    violations.append(Violation(
                        claim=claim.text,
                        rule_violated=rule.id,
                        severity=rule.severity,
                        explanation=violation_desc,
                    ))

        return violations

    def check_text(self, text: str) -> list[Violation]:
        """
        فحص النص المباشر مقابل المعايير الاجتماعية.
        Check raw text against social norms.
        """
        violations: list[Violation] = []

        for rule in self._rules:
            violation_desc = rule.check(text)
            if violation_desc is not None:
                violations.append(Violation(
                    claim=text[:200],  # مقتطف من النص — text snippet
                    rule_violated=rule.id,
                    severity=rule.severity,
                    explanation=violation_desc,
                ))

        return violations

    def get_rules(self) -> list[CommonSenseRule]:
        """إرجاع القواعد الاجتماعية النشطة — Return active social rules."""
        return list(self._rules)

    def add_rule(self, rule: CommonSenseRule) -> None:
        """إضافة قاعدة اجتماعية جديدة — Add a new social rule."""
        self._rules.append(rule)


# ═══════════════════════════════════════════════════════════════════════════════
# كاشف السخرية — Sarcasm Detector (Incongruity-based)
# ═══════════════════════════════════════════════════════════════════════════════


class SarcasmDetector:
    """
    كاشف السخرية — Detects sarcastic intent via incongruity analysis.

    يعتمد على كشف التفاوت بين المعنى الحرفي والسياق المتوقع:
    - التناقض بين الحرفي والمرجع
    - علامات سخرية عربية خاصة (يا سلااام، أكيد، نبرة معكوسة)
    - علامات سخرية إنجليزية (oh great, yeah right, sure sure)
    - المبالغة الواضحة

    Incongruity-based detection: literal meaning vs. context expectation.
    Arabic-specific markers: "يا سلااام", "أكيد", inverted tone.
    """

    # علامات سخرية عربية — Arabic sarcasm markers (pattern, weight, name)
    _ARABIC_MARKERS: list[tuple[str, float, str]] = [
        (r"يا\s+سلاا+م", 0.80, "يا سلااام — مدح ساخر"),
        (r"يا\s+للاسف\s*!+", 0.65, "يا للأسف — سخرية مؤسفة"),
        (r"يا\s+للعجب", 0.70, "يا للعجب — تعجب ساخر"),
        (r"بالطبع\s*!{2,}", 0.60, "بالطبع!! — تأكيد ساخر"),
        (r"أكيد\s*!{2,}", 0.55, "أكيد!! — تأكيد ساخر مختصر"),
        (r"طبعاً\s+طبعاً", 0.55, "طبعاً طبعاً — تكرار ساخر"),
        (r"لا\s+شكّ?\s+في\s+ذلك", 0.45, "لا شك في ذلك — إقرار ساخر"),
        (r"واضح\s+أنّ?", 0.40, "واضح أنّ — سخرية ضمنية"),
        (r"كم\s+هو\s+\w+\s*!", 0.45, "كم هو...! — مدح ساخر"),
        (r"ما\s+أ\w+\s*!", 0.45, "ما أ...! — تعجب ساخر"),
        (r"مش\s+هوّن\s+عليك", 0.50, "مش هوّن عليك — تهكم شعبي"),
        (r"الله\s+يُصلح\s+الحال", 0.40, "الله يصلح الحال — تهكم دعائي"),
        (r"الله\s+يكافيك\s+الشر", 0.35, "الله يكافيك الشر — تهكم دعائي"),
        (r"شكراً\s+جزيلاً\s*!{2,}", 0.45, "شكراً جزيلاً!! — شكر ساخر"),
        (r"ممتاز\s*!{2,}", 0.50, "ممتاز!! — مدح ساخر"),
        (r"عظيم\s*!{2,}", 0.50, "عظيم!! — مدح ساخر"),
        (r"أحسنت\s*!{2,}", 0.45, "أحسنت!! — تأييد ساخر"),
        (r"مبروك\s*!{2,}", 0.40, "مبروك!! — تهنئة ساخرة"),
    ]

    # علامات سخرية إنجليزية — English sarcasm markers
    _ENGLISH_MARKERS: list[tuple[str, float, str]] = [
        (r"oh\s+(great|wonderful|perfect|joy|fantastic)", 0.70, "oh great — sarcastic exclamation"),
        (r"yeah\s+right", 0.80, "yeah right — dismissive sarcasm"),
        (r"sure\s*,?\s*sure", 0.65, "sure sure — repeated dismissal"),
        (r"totally\s+not", 0.60, "totally not — ironic negation"),
        (r"(?:how\s+)?wonderful\s*[.!]", 0.45, "wonderful — situational sarcasm"),
        (r"obviously\s*[,!]", 0.40, "obviously — ironic obviousness"),
        (r"glad\s+to\s+hear\s+that\s*[.!]", 0.40, "glad to hear — mock gladness"),
        (r"wow\s*,?\s*(just\s+)?wow", 0.60, "wow wow — dismissive amazement"),
        (r"big\s+surprise\s*([.!]|$)", 0.55, "big surprise — mock surprise"),
        (r"tell\s+me\s+something\s+I\s+don'?t\s+know", 0.65, "tell me something — sarcastic dismissal"),
        (r"oh\s+boy", 0.35, "oh boy — mock enthusiasm"),
        (r"great\s*,?\s*just\s+great", 0.65, "great just great — mock approval"),
        (r"thanks\s+a\s+lot\s*([.!]|$)", 0.50, "thanks a lot — mock gratitude"),
        (r"very\s+funny\s*([.!]|$)", 0.55, "very funny — mock amusement"),
        (r"what\s+a\s+surprise", 0.50, "what a surprise — mock surprise"),
    ]

    # أنماط المبالغة — Exaggeration patterns
    _EXAGGERATION_PATTERNS: list[tuple[str, float, str]] = [
        (r"\b(مليون|مليار|تريليون)\s+(مرة|سنة|يوم|شخص)\b", 0.40, "مبالغة عددية"),
        (r"\b(a\s+)?(million|billion|trillion)\s+(times|years|days|people)\b", 0.40, "numeric exaggeration"),
        (r"\bأطول\s+من\s+(السماء|الكون|الأبدية)\b", 0.50, "مبالغة وصفية"),
        (r"\b(longer|taller|bigger)\s+than\s+(the\s+)?(sky|universe|eternity)\b", 0.50, "descriptive exaggeration"),
        (r"\bأبطأ\s+من\s+(السلحفاة|الحلزون|القوقع)\b", 0.35, "تشبيه مبالغ — slow metaphor"),
        (r"\bأثقل\s+من\s+(الجبل|الجبال|الكون)\b", 0.40, "تشبيه مبالغ — heavy metaphor"),
    ]

    # أنماط التناقض السياقي — Contextual incongruity patterns
    _INCONGRUITY_PATTERNS: list[tuple[str, float, str]] = [
        # مدح في سياق سلبي — praise in negative context
        (r"(رائع|ممتاز|عظيم).{0,15}(لكن|ولكن|إلا\s+أن|مشكلة|كارثة)", 0.55, "تناقض سياقي: مدح ثم ذم"),
        (r"(great|wonderful|perfect).{0,15}(but|however|except|problem|disaster)", 0.55, "contextual incongruity: praise then criticism"),
        # إيجابية مفرطة — excessive positivity
        (r"(أفضل|أحسن|أروع).{0,5}(أبداً|في\s+التاريخ|في\s+العالم|على\s+الإطلاق)\s*!+", 0.50, "إيجابية مفرطة"),
        (r"(best|greatest|most\s+amazing).{0,5}(ever|in\s+history|in\s+the\s+world)\s*!+", 0.50, "excessive positivity"),
    ]

    def detect(self, text: str, context: str = "") -> SarcasmResult:
        """
        كشف السخرية — Analyze text for sarcastic intent.

        يستخدم ثلاثة محاور للكشف:
        1. علامات سخرية مباشرة (عربية + إنجليزية)
        2. أنماط المبالغة الواضحة
        3. التناقض بين الحرفي والسياق (incongruity)

        Args:
            text: النص المراد تحليله
            context: سياق اختياري للمقارنة

        Returns:
            SarcasmResult — نتيجة كشف السخرية
        """
        if not text or not text.strip():
            return SarcasmResult(is_sarcastic=False, confidence=0.0)

        markers_found: list[str] = []
        total_weight: float = 0.0

        # ─── فحص العلامات العربية — Arabic markers ───────────────────
        for pattern, weight, name in self._ARABIC_MARKERS:
            try:
                if re.search(pattern, text, re.IGNORECASE | re.UNICODE):
                    markers_found.append(name)
                    total_weight += weight
            except re.error:
                continue

        # ─── فحص العلامات الإنجليزية — English markers ───────────────
        for pattern, weight, name in self._ENGLISH_MARKERS:
            try:
                if re.search(pattern, text, re.IGNORECASE | re.UNICODE):
                    markers_found.append(name)
                    total_weight += weight
            except re.error:
                continue

        # ─── فحص المبالغة — Exaggeration ──────────────────────────────
        for pattern, weight, name in self._EXAGGERATION_PATTERNS:
            try:
                if re.search(pattern, text, re.IGNORECASE | re.UNICODE):
                    markers_found.append(name)
                    total_weight += weight
            except re.error:
                continue

        # ─── فحص التناقض السياقي — Incongruity ──────────────────────
        for pattern, weight, name in self._INCONGRUITY_PATTERNS:
            try:
                if re.search(pattern, text, re.IGNORECASE | re.UNICODE):
                    markers_found.append(name)
                    total_weight += weight
            except re.error:
                continue

        # ─── حساب الثقة — Confidence computation ─────────────────────
        # علامات متعددة تزيد اليقين لكن بشكل متناقص
        confidence = min(1.0, total_weight)

        # ─── فحص السياق — Context check ──────────────────────────────
        if context and confidence < SARCASM_THRESHOLD:
            context_incongruity = self._check_context_incongruity(text, context)
            if context_incongruity > 0:
                confidence = min(1.0, confidence + context_incongruity)
                markers_found.append("تناقض مع السياق / context incongruity")

        is_sarcastic = confidence >= SARCASM_THRESHOLD

        # ─── شرح النتيجة — Explanation ───────────────────────────────
        explanation = self._generate_explanation(is_sarcastic, markers_found, confidence)

        return SarcasmResult(
            is_sarcastic=is_sarcastic,
            confidence=round(confidence, 4),
            markers_found=markers_found,
            explanation=explanation,
        )

    @staticmethod
    def _check_context_incongruity(text: str, context: str) -> float:
        """
        فحص التناقض بين النص والسياق.
        Check incongruity between text and its context.

        يُرجع وزناً إضافياً (0.0–0.3) إن وُجد تفاوت ملحوظ.
        """
        # كلمات إيجابية وسلبية أساسية — basic sentiment words
        positive_ar = {"رائع", "ممتاز", "عظيم", "جميل", "أحسنت", "مبارك", "سعيد"}
        negative_ar = {"سيء", "فاشل", "كارثة", "مشكلة", "حزين", "مؤلم", "صعب"}
        positive_en = {"great", "wonderful", "excellent", "good", "happy", "beautiful", "amazing"}
        negative_en = {"bad", "terrible", "awful", "problem", "sad", "painful", "difficult"}

        text_words = set(re.findall(r"\w+", text.lower()))
        context_words = set(re.findall(r"\w+", context.lower()))

        # حساب المشاعر في النص والسياق — compute sentiment
        text_pos = len(text_words & (positive_ar | positive_en))
        text_neg = len(text_words & (negative_ar | negative_en))
        ctx_pos = len(context_words & (positive_ar | positive_en))
        ctx_neg = len(context_words & (negative_ar | negative_en))

        # إذا كان النص إيجابياً والسياق سلبياً (أو العكس) → تناقض
        text_sentiment = text_pos - text_neg
        ctx_sentiment = ctx_pos - ctx_neg

        if (text_sentiment > 0 and ctx_sentiment < 0) or (text_sentiment < 0 and ctx_sentiment > 0):
            return 0.25  # وزن إضافي للتناقض السياقي

        return 0.0

    @staticmethod
    def _generate_explanation(is_sarcastic: bool, markers: list[str], confidence: float) -> str:
        """توليد شرح لنتيجة الكشف — Generate explanation for detection result."""
        if not markers:
            return "لا علامات سخرية مكتشفة — No sarcasm markers detected"

        marker_summary = "؛ ".join(markers[:5])
        if len(markers) > 5:
            marker_summary += f"؛ +{len(markers) - 5} علامات أخرى"

        if is_sarcastic:
            return (
                f"النص يحتمل السخرية (ثقة: {confidence:.0%}) — "
                f"العلامات: {marker_summary} — "
                f"المعنى المقصود قد يكون عكس الظاهر"
            )
        else:
            return (
                f"علامات سخرية محدودة (ثقة: {confidence:.0%}) — "
                f"العلامات: {marker_summary} — "
                f"يُنصح بالتحقق من السياق"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# كاشف الافتراضات الضمنية — Implicit Assumption Detector
# ═══════════════════════════════════════════════════════════════════════════════


class ImplicitAssumptionDetector:
    """
    كاشف الافتراضات الضمنية — Uncovers hidden premises in arguments.

    يكشف الافتراضات غير المصرح بها في الحجج والادعاءات.
    نمط العمل: "إذا أ ثم ب" ← يفترض أن أ ممكن وأن أ→ب صحيح

    Returns list of assumptions with necessity level:
    - required: الافتراض ضروري لصحة الادعاء
    - likely: الافتراض محتمل لكن ليس حتمياً
    - possible: الافتراض ممكن لكنه اختياري
    """

    # أنماط الافتراضات الضمنية — Implicit assumption patterns
    # (pattern, assumption_template, necessity_level)
    _ASSUMPTION_PATTERNS: list[tuple[str, str, str]] = [
        # ─── الأوامر والنصائح — Commands & Advice ─────────────────────
        (
            r"(يجب\s+أن|لازم\s+أن|يلزم\s+أن|عليك\s+أن)\s+(ت\w+|ي\w+)",
            "الإجراء «{action}» ممكن التنفيذ — الفاعل قادر عليه",
            "required",
        ),
        (
            r"(لا\s+ت\w+|ممنوع\s+\w+|يُحظر\s+\w+)",
            "الفعل المنهي عنه ممكن الحدوث — يحتاج منعاً",
            "required",
        ),
        # ─── السببية — Causality ──────────────────────────────────────
        (
            r"(لأنّ?|بسبب|بما\s+أنّ?|بما\s+أن)\s+(.+?)(?:\.|،|$)",
            "السبب «{cause}» حقيقي ومؤكد — وكافٍ لتفسير النتيجة",
            "likely",
        ),
        (
            r"(إذا|لو|إن)\s+(.+?)\s+(ف|سوف|سين|ست|فإنّ?)\s+",
            "الشرط «{condition}» ممكن الحدوث — والنتيجة حتمية إن تحقق",
            "likely",
        ),
        # ─── المقارنات — Comparisons ─────────────────────────────────
        (
            r"(أفضل|أحسن|أسوأ|أكثر|أقل)\s+من",
            "المقارنة بين الطرفين صحيحة ومتكافئة — نفس المعايير مطبقة",
            "possible",
        ),
        # ─── التعميمات — Generalizations ──────────────────────────────
        (
            r"(كل|جميع|كُلّ|كلّ)\s+(ال\w+|\w+)\s+(ي\w+|ت\w+|أ\w+)",
            "التعميم صحيح لجميع أفراد المجموعة — لا استثناءات",
            "required",
        ),
        (
            r"(لا\s+أحد|لا\s+شيء|أي\s+شخص|كل\s+شخص)",
            "التعميم السلبي أو الشامل مطلق — لا استثناءات",
            "required",
        ),
        # ─── الاقتباسات والمراجع — Citations & References ─────────────
        (
            r"((الطبيب|الأستاذ|الخبير|المهندس|العالِم)\s+(قال|أكد|نصح|أشار|أعلن|صرّح))",
            "الشخص المذكور مؤهل في مجاله — ومعلوماته موثوقة",
            "likely",
        ),
        (
            r"((تشير|تُظهر|تؤكد|أثبتت)\s+(الأبحاث|الدراسات|الإحصائيات|البيانات))",
            "البحث المُشار إليه حقيقي وذو مصداقية — والاستنتاج مُبرر",
            "likely",
        ),
        # ─── التضمينات الزمنية — Temporal Implications ────────────────
        (
            r"(بعد|عقب|إثر)\s+(ال\w+|\w+)",
            "الحدث المذكور وقع بالفعل — الترتيب الزمني صحيح",
            "likely",
        ),
        (
            r"(قبل|مِن\s+قبل)\s+(ال\w+|\w+)",
            "الحدث المذكور وقع قبل الحدث اللاحق — الترتيب الزمني صحيح",
            "likely",
        ),
        # ─── الافتراضات القيمية — Value Assumptions ──────────────────
        (
            r"(يجب|ينبغي|المفروض|من\s+الواجب)",
            "الحكم القيمي مُتفق عليه — القيمة المعيارية مُسلّمة",
            "possible",
        ),
        (
            r"(من\s+الطبيعي|من\s+المعتاد|عادةً|عادة)",
            "ما يُعتبر طبيعياً أو معتاداً هو كذلك في هذا السياق",
            "possible",
        ),
    ]

    def detect(self, claims: list[Claim]) -> list[Assumption]:
        """
        كشف الافتراضات الضمنية — Detect implicit assumptions in claims.

        Args:
            claims: قائمة الادعاءات المراد تحليلها

        Returns:
            قائمة بالافتراضات الضمنية المكتشفة
        """
        assumptions: list[Assumption] = []

        for claim in claims:
            for pattern, template, necessity in self._ASSUMPTION_PATTERNS:
                try:
                    match = re.search(pattern, claim.text, re.IGNORECASE | re.UNICODE)
                    if match:
                        # استبدال المتغيرات في القالب — substitute variables in template
                        assumption_text = template
                        if match.groups():
                            for i, group in enumerate(match.groups()):
                                if group:
                                    placeholder = "{action}" if i == 0 else "{cause}" if "cause" in template else "{condition}"
                                    assumption_text = assumption_text.replace(placeholder, group.strip(), 1)

                        assumptions.append(Assumption(
                            text=assumption_text,
                            necessity_level=necessity,
                            source_claim=claim.text,
                        ))
                except re.error:
                    continue

        return assumptions

    def detect_from_text(self, text: str) -> list[Assumption]:
        """
        كشف الافتراضات الضمنية من نص خام.
        Detect implicit assumptions from raw text.
        """
        claim = Claim(text=text, claim_type="social", testable=True)
        return self.detect([claim])


# ═══════════════════════════════════════════════════════════════════════════════
# حلّال الغموض — Ambiguity Resolver
# ═══════════════════════════════════════════════════════════════════════════════


class AmbiguityResolver:
    """
    حلّال الغموض — Resolves ambiguous statements.

    يكشف العبارات الغامضة ويقترح حلولاً محتملة.
    """

    # أنماط الغموض — Ambiguity patterns
    # (pattern, description, primary_resolution, alternatives)
    _AMBIGUITY_PATTERNS: list[tuple[str, str, str, list[str]]] = [
        # ─── ضمائر غامضة — Ambiguous pronouns ────────────────────────
        (
            r"\b(هو|هي|هم|هن)\b.{0,30}(قال|فعل|ذهب|أراد)",
            "ضمير غامض — قد يشير إلى أكثر من شخص",
            "يُحتاج سياق إضافي لتحديد المُشار إليه",
            ["تحديد الاسم بدلاً من الضمير", "إعادة صياغة الجملة"],
        ),
        # ─── كلمات ذات معانٍ متعددة — Polysemous words ───────────────
        (
            r"\b(عين)\b",
            "كلمة «عين» متعددة المعاني — عين الماء / العين البصرية / العين (جاسوس)",
            "تحديد المعنى من السياق",
            ["عين ماء", "عين بصرية", "جاسوس"],
        ),
        (
            r"\b(بنك)\b",
            "كلمة «بنك» متعددة المعاني — بنك مالي / بنك الدم / ضفة النهر",
            "تحديد المعنى من السياق",
            ["بنك مالي", "بنك دم", "ضفة نهر"],
        ),
        # ─── تعبيرات زمنية غامضة — Ambiguous time expressions ──────────
        (
            r"\b(قريباً|قريب|قريبا)\b",
            "تعبير زمني غامض — «قريباً» لا يحدد وقتاً دقيقاً",
            "تحديد مدة زمنية محددة",
            ["خلال أيام", "خلال أسابيع", "خلال أشهر"],
        ),
        (
            r"\b(بعد\s+فترة|بعد\s+مدة|في\s+الوقت\s+المناسب)\b",
            "تعبير زمني غامض — لا يحدد وقتاً دقيقاً",
            "تحديد تاريخ أو مدة زمنية",
            ["تحديد تاريخ", "تحديد عدد الأيام/الأسابيع"],
        ),
        # ─── نفي غامض — Ambiguous negation ────────────────────────────
        (
            r"\b(لا\s+بأس|مش\s+كثير|مو\s+كثير)\b",
            "نفي غامض — قد يعني القبول المتردد أو الرفض المهذب",
            "تحديد النية: قبول أم رفض؟",
            ["قبول متردد", "رفض مهذب", "محايد"],
        ),
        # ─── كميات غامضة — Ambiguous quantities ────────────────────────
        (
            r"\b(بعض|كثير|قليل|عدة|عدد)\b",
            "كمية غامضة — لا تحدد رقماً دقيقاً",
            "تحديد كمية أو نطاق رقمي",
            ["تحديد رقم تقريبي", "تحديد نطاق"],
        ),
        # ─── أوامر غامضة — Ambiguous commands ──────────────────────────
        (
            r"\b(تصرف|افعل\s+ما\s+تراه|كما\s+تراه\s+مناسباً)\b",
            "أمر غامض — لا يحدد إجراءً واضحاً",
            "تحديد إجراء محدد",
            ["طلب توضيح", "اقتراح خيارات محددة"],
        ),
    ]

    def resolve(self, text: str) -> list[Resolution]:
        """
        حل الغموض — Resolve ambiguous statements in text.

        Args:
            text: النص المراد تحليله

        Returns:
            قائمة بحلول الغموض المقترحة
        """
        resolutions: list[Resolution] = []

        for pattern, description, primary, alternatives in self._AMBIGUITY_PATTERNS:
            try:
                match = re.search(pattern, text, re.IGNORECASE | re.UNICODE)
                if match:
                    # استخراج النص الغامض — extract ambiguous text
                    ambiguous = match.group(0)
                    # حساب الثقة بناءً على طول السياق المتاح
                    confidence = max(0.3, min(0.8, 1.0 - len(text) / 1000))

                    resolutions.append(Resolution(
                        ambiguous_text=ambiguous,
                        resolved_meaning=primary,
                        confidence=round(confidence, 4),
                        alternatives=alternatives,
                    ))
            except re.error:
                continue

        return resolutions


# ═══════════════════════════════════════════════════════════════════════════════
# مرشح المنطق العام — Common Sense Filter (Main Entry Point)
# ═══════════════════════════════════════════════════════════════════════════════


class CommonSenseFilter:
    """
    مرشح المنطق العام — Common Sense Reasoning Filter for BABSHARQII v6.0.

    Tri-stage logical filtering:
    1. Physical plausibility check — هل يمكن أن يحدث هذا فعلياً؟
    2. Social/cultural norms check — هل ينتهك هذا المعايير الاجتماعية؟
    3. Temporal consistency check — هل الادعاءات الزمنية متسقة؟

    Plus:
    - Sarcasm detection via incongruity
    - Implicit assumption detection
    - Ambiguity resolution

    Usage:
        csf = CommonSenseFilter()
        result = csf.filter("الماء يتدفق صعوداً إلى الجبل")
        print(result.to_dict())
    """

    def __init__(
        self,
        cultural_context: str = CULTURAL_CONTEXT,
        sarcasm_threshold: float = SARCASM_THRESHOLD,
    ):
        """
        تهيئة مرشح المنطق العام.

        Args:
            cultural_context: السياق الثقافي — arab_islamic | western | universal
            sarcasm_threshold: عتبة كشف السخرية (0.0–1.0)
        """
        self._enabled = COMMON_SENSE_ENABLED
        self._cultural_context = cultural_context
        self._sarcasm_threshold = sarcasm_threshold

        # المكونات الداخلية — Inner components
        self._physical_checker = PhysicalPlausibilityChecker()
        self._social_checker = SocialNormChecker(cultural_context=cultural_context)
        self._sarcasm_detector = SarcasmDetector()
        self._assumption_detector = ImplicitAssumptionDetector()
        self._ambiguity_resolver = AmbiguityResolver()

        # القواعد المخصصة — Custom rules
        self._custom_rules: list[CommonSenseRule] = []

        # إحصائيات الاستخدام — Usage statistics
        self._stats = {
            "total_filters": 0,
            "violations_found": 0,
            "sarcasm_detected": 0,
            "assumptions_found": 0,
            "physical_violations": 0,
            "social_violations": 0,
            "temporal_violations": 0,
            "avg_score": 0.0,
            "enabled": self._enabled,
            "cultural_context": self._cultural_context,
            "sarcasm_threshold": self._sarcasm_threshold,
        }

        logger.info(
            "مرشح المنطق العام مهيأ — CommonSenseFilter initialized "
            "(enabled=%s, context=%s, sarcasm_threshold=%.2f)",
            self._enabled,
            self._cultural_context,
            self._sarcasm_threshold,
        )

    @property
    def enabled(self) -> bool:
        """هل المرشح مُمكّن؟ — Is the filter enabled?"""
        return self._enabled

    def filter(self, text: str) -> dict:
        """
        ترشيح المنطق العام — Main entry point: analyze text for common sense violations.

        يمرر النص عبر المراحل الثلاث:
        1. فحص الاحتمالية الفيزيائية
        2. فحص المعايير الاجتماعية
        3. فحص الاتساق الزمني

        ثم يضيف:
        - كشف السخرية
        - كشف الافتراضات الضمنية
        - حل الغموض

        Args:
            text: النص المراد تحليله

        Returns:
            قاموس يحتوي على نتيجة التحليل الكاملة
        """
        start_time = time.time()

        # إذا كان المرشح معطلاً، أرجع نتيجة آمنة — return safe result if disabled
        if not self._enabled:
            return CommonSenseResult(
                overall_score=1.0,
                filtered_text=text,
            ).to_dict()

        if not text or not text.strip():
            return CommonSenseResult(
                overall_score=1.0,
                filtered_text=text or "",
            ).to_dict()

        # ═══════════════════════════════════════════════════════════════
        # المرحلة 1: فحص الاحتمالية الفيزيائية — Physical plausibility
        # ═══════════════════════════════════════════════════════════════
        physical_violations = self._check_physical_plausibility(
            self._physical_checker._extract_claims(text)
        )
        # فحص إضافي للنص الكامل — also check full text
        full_text_violations = self._physical_checker.check(text)
        all_physical = physical_violations + [
            v for v in full_text_violations
            if v.rule_violated not in {ev.rule_violated for ev in physical_violations}
        ]

        # ═══════════════════════════════════════════════════════════════
        # المرحلة 2: فحص المعايير الاجتماعية — Social norms
        # ═══════════════════════════════════════════════════════════════
        claims_for_social = [
            Claim(text=text, claim_type="social", testable=True)
        ]
        social_violations = self._check_social_norms(claims_for_social)

        # ═══════════════════════════════════════════════════════════════
        # المرحلة 3: فحص الاتساق الزمني — Temporal consistency
        # ═══════════════════════════════════════════════════════════════
        temporal_claims = [
            Claim(text=text, claim_type="temporal", testable=True)
        ]
        temporal_violations = self._check_temporal_consistency(temporal_claims)

        # ═══════════════════════════════════════════════════════════════
        # كشف السخرية — Sarcasm detection
        # ═══════════════════════════════════════════════════════════════
        sarcasm_result = self._detect_sarcasm(text, context="")

        # ═══════════════════════════════════════════════════════════════
        # كشف الافتراضات الضمنية — Implicit assumption detection
        # ═══════════════════════════════════════════════════════════════
        all_claims = self._physical_checker._extract_claims(text)
        all_claims.append(Claim(text=text, claim_type="general", testable=True))
        assumptions = self._detect_implicit_assumptions(all_claims)

        # ═══════════════════════════════════════════════════════════════
        # حل الغموض — Ambiguity resolution
        # ═══════════════════════════════════════════════════════════════
        resolutions = self._resolve_ambiguity(text)

        # ═══════════════════════════════════════════════════════════════
        # تجميع النتائج — Aggregate results
        # ═══════════════════════════════════════════════════════════════
        all_violations = all_physical + social_violations + temporal_violations

        # حساب النتيجة الإجمالية — compute overall score
        overall_score = self._compute_overall_score(
            all_violations, sarcasm_result
        )

        # إنشاء النص المرشح — create filtered text
        filtered_text = self._apply_filtering(text, all_violations, sarcasm_result)

        # تحديث الإحصائيات — update statistics
        self._update_stats(all_violations, sarcasm_result, assumptions, overall_score)

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "مرشح المنطق العام اكتمل — CommonSenseFilter completed "
            "(score=%.2f, violations=%d, sarcasm=%s, duration=%.1fms)",
            overall_score,
            len(all_violations),
            sarcasm_result.is_sarcastic,
            duration_ms,
        )

        result = CommonSenseResult(
            violations=all_violations,
            sarcasm=sarcasm_result,
            assumptions=assumptions,
            overall_score=overall_score,
            filtered_text=filtered_text,
        )

        # إضافة حلول الغموض إلى النتيجة — include ambiguity resolutions
        result_dict = result.to_dict()
        result_dict["ambiguity_resolutions"] = [r.to_dict() for r in resolutions]
        result_dict["duration_ms"] = round(duration_ms, 1)

        return result_dict

    def _check_physical_plausibility(self, claims: list[Claim]) -> list[Violation]:
        """
        المرحلة ١: فحص الاحتمالية الفيزيائية — Can this happen in reality?

        يفحص الادعاءات مقابل قواعد القيود الفيزيائية:
        الجاذبية، الديناميكا الحرارية، البيولوجيا، إلخ.

        Args:
            claims: قائمة الادعاءات المراد فحصها

        Returns:
            قائمة بانتهاكات الاحتمالية الفيزيائية
        """
        violations: list[Violation] = []

        for claim in claims:
            if claim.claim_type not in ("physical", ""):
                continue
            violation = self._physical_checker._evaluate_claim(
                claim, self._physical_checker._rules
            )
            if violation is not None:
                violations.append(violation)

        # فحص القواعد المخصصة — check custom rules
        for claim in claims:
            for rule in self._custom_rules:
                if rule.category != "physical":
                    continue
                violation_desc = rule.check(claim.text)
                if violation_desc is not None:
                    violations.append(Violation(
                        claim=claim.text,
                        rule_violated=rule.id,
                        severity=rule.severity,
                        explanation=violation_desc,
                    ))

        return violations

    def _check_social_norms(self, claims: list[Claim]) -> list[Violation]:
        """
        المرحلة ٢: فحص المعايير الاجتماعية — Does this violate social conventions?

        يفحص الادعاءات مقابل المعايير الاجتماعية والثقافية.
        يشمل: اقتراحات غير لائقة، عدم حساسية ثقافية، انتهاكات الخصوصية.

        Args:
            claims: قائمة الادعاءات المراد فحصها

        Returns:
            قائمة بانتهاكات المعايير الاجتماعية
        """
        violations = self._social_checker.check(claims)

        # فحص القواعد المخصصة — check custom rules
        for claim in claims:
            for rule in self._custom_rules:
                if rule.category != "social":
                    continue
                violation_desc = rule.check(claim.text)
                if violation_desc is not None:
                    violations.append(Violation(
                        claim=claim.text,
                        rule_violated=rule.id,
                        severity=rule.severity,
                        explanation=violation_desc,
                    ))

        return violations

    def _check_temporal_consistency(self, claims: list[Claim]) -> list[Violation]:
        """
        المرحلة ٣: فحص الاتساق الزمني — Are time-based claims consistent?

        يفحص الادعاءات ذات الطابع الزمني للتحقق من:
        - تناقضات الترتيب الزمني
        - ادعاءات عن المستقبل كأنها وقعت
        - تواريخ مستحيلة

        Args:
            claims: قائمة الادعاءات المراد فحصها

        Returns:
            قائمة بانتهاكات الاتساق الزمني
        """
        violations: list[Violation] = []

        # أنماط التناقضات الزمنية — Temporal contradiction patterns
        temporal_patterns: list[tuple[str, str, float]] = [
            (
                r"قبل\s+أن\s+(يحدث|يقع|يتم|يُنجز).{0,20}(كان\s+قد|تمَّ|أُنجز)",
                "لا يمكن أن يحدث شيء قبل أن يحدث — تناقض زمني / "
                "Something cannot happen before it happens",
                0.92,
            ),
            (
                r"before\s+it\s+happened.{0,20}(was\s+already|had\s+already)",
                "An effect cannot precede its cause — temporal contradiction",
                0.92,
            ),
            (
                r"النتيجة\s+(سبقت|جاءت\s+قبل)\s+السبب",
                "النتيجة لا تسبق السبب / An effect cannot precede its cause",
                0.93,
            ),
            (
                r"the\s+(effect|result)\s+(preceded|came\s+before)\s+(the\s+)?cause",
                "An effect cannot precede its cause",
                0.93,
            ),
            (
                r"المستقبل\s+(حدث|وقع|تمّ|انتهى)",
                "المستقبل لم يقع بعد / The future has not yet occurred",
                0.90,
            ),
            (
                r"the\s+future\s+(has\s+)?(happened|occurred|ended)",
                "The future has not yet occurred",
                0.90,
            ),
            (
                r"غداً\s+(كان|حدث|وقعت)",
                "غداً لم يقع بعد — Tomorrow has not yet occurred",
                0.88,
            ),
            (
                r"(البارحة|أمس)\s+(سيكون|سيفعل|سيمضي)",
                "الماضي لا يُستخدم مع المستقبل — Yesterday cannot use future tense",
                0.85,
            ),
            (
                r"yesterday\s+(will|shall|is\s+going\s+to)",
                "Past time reference with future tense — temporal inconsistency",
                0.85,
            ),
            (
                r"(في\s+عام|سنة)\s+(\d{4}).{0,30}(قبل\s+الميلاد|BC).{0,30}(إنترنت|هاتف|كهرباء|سيارة|طائرة)",
                "تكنولوجيا حديثة في عصر قديم — Anachronism detected",
                0.90,
            ),
            (
                r"(الشمس\s+شرقت\s+في\s+المغرب|غربت\s+في\s+المشرق)",
                "الشمس تشرق من المشرق لا من المغرب — The Sun rises in the east",
                0.88,
            ),
        ]

        for claim in claims:
            for pattern, description, severity in temporal_patterns:
                try:
                    if re.search(pattern, claim.text, re.IGNORECASE | re.UNICODE):
                        violations.append(Violation(
                            claim=claim.text,
                            rule_violated="temporal_inconsistency",
                            severity=severity,
                            explanation=description,
                        ))
                except re.error:
                    continue

        # فحص القواعد المخصصة — check custom rules
        for claim in claims:
            for rule in self._custom_rules:
                if rule.category != "temporal":
                    continue
                violation_desc = rule.check(claim.text)
                if violation_desc is not None:
                    violations.append(Violation(
                        claim=claim.text,
                        rule_violated=rule.id,
                        severity=rule.severity,
                        explanation=violation_desc,
                    ))

        return violations

    def _detect_sarcasm(self, text: str, context: str = "") -> SarcasmResult:
        """
        كشف السخرية — Detect sarcastic intent via incongruity analysis.

        يحلل النص للكشف عن السخرية بناءً على:
        - التفاوت بين المعنى الحرفي والسياق المتوقع
        - علامات سخرية عربية وإنجليزية محددة

        Args:
            text: النص المراد تحليله
            context: سياق اختياري للمقارنة

        Returns:
            SarcasmResult — نتيجة كشف السخرية
        """
        return self._sarcasm_detector.detect(text, context=context)

    def _detect_implicit_assumptions(self, claims: list[Claim]) -> list[Assumption]:
        """
        كشف الافتراضات الضمنية — Find unstated premises.

        يكشف الافتراضات غير المصرح بها في الحجج:
        "إذا أ ثم ب" ← يفترض أن أ ممكن وأن أ→ب صحيح

        Args:
            claims: قائمة الادعاءات المراد تحليلها

        Returns:
            قائمة بالافتراضات الضمنية مع مستوى الضرورة
        """
        return self._assumption_detector.detect(claims)

    def _resolve_ambiguity(self, text: str) -> list[Resolution]:
        """
        حل الغموض — Resolve ambiguous statements.

        يكشف العبارات الغامضة ويقترح حلولاً محتملة.

        Args:
            text: النص المراد تحليله

        Returns:
            قائمة بحلول الغموض المقترحة
        """
        return self._ambiguity_resolver.resolve(text)

    @staticmethod
    def _compute_overall_score(
        violations: list[Violation],
        sarcasm: SarcasmResult,
    ) -> float:
        """
        حساب النتيجة الإجمالية — Compute overall common sense score.

        النتيجة تعتمد على:
        - عدد وشدة الانتهاكات
        - كشف السخرية (يخفض الثقة)
        """
        if not violations and not sarcasm.is_sarcastic:
            return 1.0

        # خصم الانتهاكات — penalty for violations
        if violations:
            max_severity = max(v.severity for v in violations)
            extra_penalty = min(0.3, len(violations) * 0.05)
            violation_score = max(0.0, 1.0 - max_severity - extra_penalty)
        else:
            violation_score = 1.0

        # خصم السخرية — penalty for sarcasm
        sarcasm_penalty = sarcasm.confidence * 0.2 if sarcasm.is_sarcastic else 0.0

        overall = max(0.0, violation_score - sarcasm_penalty)
        return round(overall, 4)

    @staticmethod
    def _apply_filtering(
        text: str,
        violations: list[Violation],
        sarcasm: SarcasmResult,
    ) -> str:
        """
        تطبيق الترشيح على النص — Apply filtering to text.

        يضيف تنبيهات للانتهاكات المكتشفة دون حذف المحتوى الأصلي.
        """
        if not violations and not sarcasm.is_sarcastic:
            return text

        # إضافة علامات تحذيرية — add warning markers
        filtered_parts: list[str] = []

        if violations:
            warning_lines = [
                f"⚠️ [{v.rule_violated}] {v.explanation}"
                for v in violations[:5]  # حد أقصى 5 تحذيرات
            ]
            filtered_parts.append("【تنبيهات المنطق العام】\n" + "\n".join(warning_lines))

        if sarcasm.is_sarcastic:
            filtered_parts.append(
                f"🗣️ تنبيه سخرية: النص قد يكون ساخراً (ثقة: {sarcasm.confidence:.0%})"
            )

        filtered_parts.append(text)

        return "\n".join(filtered_parts)

    def _update_stats(
        self,
        violations: list[Violation],
        sarcasm: SarcasmResult,
        assumptions: list[Assumption],
        score: float,
    ) -> None:
        """تحديث الإحصائيات — Update usage statistics."""
        self._stats["total_filters"] += 1
        self._stats["violations_found"] += len(violations)
        if sarcasm.is_sarcastic:
            self._stats["sarcasm_detected"] += 1
        self._stats["assumptions_found"] += len(assumptions)
        self._stats["physical_violations"] += sum(
            1 for v in violations if v.rule_violated.startswith("phys_")
        )
        self._stats["social_violations"] += sum(
            1 for v in violations if v.rule_violated.startswith("social_")
        )
        self._stats["temporal_violations"] += sum(
            1 for v in violations if v.rule_violated.startswith("temporal_")
        )
        # حساب المتوسط المتحرك — compute running average
        n = self._stats["total_filters"]
        prev_avg = self._stats["avg_score"]
        self._stats["avg_score"] = round(
            (prev_avg * (n - 1) + score) / n, 4
        )

    def get_rules(self) -> list[dict]:
        """
        إرجاع القواعد النشطة — Return active common sense rules.

        Returns:
            قائمة قواميس تحتوي على القواعد النشطة
        """
        rules: list[dict] = []

        # القواعد الفيزيائية — Physical rules
        for rule in self._physical_checker.get_rules():
            rules.append(rule.to_dict())

        # القواعد الاجتماعية — Social rules
        for rule in self._social_checker.get_rules():
            rules.append(rule.to_dict())

        # القواعد المخصصة — Custom rules
        for rule in self._custom_rules:
            rules.append(rule.to_dict())

        return rules

    def add_rule(self, rule: CommonSenseRule) -> None:
        """
        إضافة قاعدة جديدة — Add a new common sense rule.

        يمكن إضافة قواعد مخصصة لأي فئة:
        physical, social, temporal, logical

        Args:
            rule: القاعدة المراد إضافتها
        """
        self._custom_rules.append(rule)

        # إضافة للفحص المناسب — add to appropriate checker
        if rule.category == "physical":
            self._physical_checker.add_rule(rule)
        elif rule.category == "social":
            self._social_checker.add_rule(rule)

        logger.info(
            "قاعدة جديدة مضافة — Rule added: %s (%s)",
            rule.id, rule.category,
        )

    def get_stats(self) -> dict:
        """
        إرجاع إحصائيات الاستخدام — Return usage statistics.

        Returns:
            قاموس يحتوي على إحصائيات الاستخدام
        """
        return dict(self._stats)


# ═══════════════════════════════════════════════════════════════════════════════
# نقطة الدخول — Module Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

# مثيل افتراضي — Default instance (lazy)
_default_filter: CommonSenseFilter | None = None


def get_common_sense_filter() -> CommonSenseFilter:
    """
    الحصول على مثيل مرشح المنطق العام الافتراضي.
    Get the default CommonSenseFilter instance (singleton).
    """
    global _default_filter
    if _default_filter is None:
        _default_filter = CommonSenseFilter()
    return _default_filter
