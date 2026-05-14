"""
BABSHARQII (Mamoun) v6.0 — Hallucination Detector
كاشف الهلوسة — نظام كشف الهلوسة المتقدم لطبقة AGI

Implements a multi-signal hallucination detection system for LLM output
verification, inspired by zero-shot anomaly detection, self-consistency
checking (Wang et al., 2023), factual grounding verification, confidence
calibration, and entropy-based uncertainty estimation.

Research basis:
    - Zero-shot anomaly detection for identifying statements that don't
      match known patterns
    - Self-consistency checking — generate multiple completions and check
      agreement
    - Factual grounding — verify claims against knowledge base
    - Confidence calibration — detect overconfident wrong answers
    - Entropy-based uncertainty — high entropy in generation = potential
      hallucination

Env toggles:
    MAMOUN_HALLUCINATION_DETECTION_ENABLED — تمكين/تعطيل كشف الهلوسة (الافتراضي: false)
    MAMOUN_HALLUCINATION_THRESHOLD — عتبة الهلوسة (الافتراضي: 0.6)
    MAMOUN_HALLUCINATION_CONSISTENCY_SAMPLES — عدد عينات الاتساق (الافتراضي: 3)
"""

from __future__ import annotations

import os
import re
import math
import time
import hashlib
import logging
import random
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ثوابت النظام — System Constants
# ═══════════════════════════════════════════════════════════════════════════════

# عتبات الهلوسة — Hallucination thresholds
HALLUCINATION_THRESHOLD_LOW = 0.3     # أقل من هذا → آمن — safe
HALLUCINATION_THRESHOLD_MEDIUM = 0.5  # أقل من هذا → يحتاج مراجعة — needs review
HALLUCINATION_THRESHOLD_HIGH = 0.7    # أعلى من هذا → هلوسة محتملة — likely hallucination

# أوزان العوامل — Factor weights for hallucination score computation
WEIGHT_SELF_CONSISTENCY = 0.25        # وزن الاتساق الذاتي
WEIGHT_FACTUAL_GROUNDING = 0.30       # وزن التأصيل الواقعي
WEIGHT_FABRICATED_ENTITIES = 0.15     # وزن الكيانات المُختلقة
WEIGHT_NUMERICAL_HALLUCINATION = 0.10 # وزن هلوسة الأرقام
WEIGHT_LOGICAL_COHERENCE = 0.10       # وزن الترابط المنطقي
WEIGHT_CONFIDENCE_CALIBRATION = 0.10  # وزن معايرة الثقة

# إعدادات الاتساق الذاتي — Self-consistency settings
DEFAULT_N_SAMPLES = 3                 # عدد العينات الافتراضي
MIN_CONSISTENCY_RATIO = 0.5           # الحد الأدنى لنسبة الاتساق

# أنماط الادعاءات القابلة للتحقق — Verifiable claim patterns
CLAIM_PATTERNS: list[str] = [
    r"\d{4}",                          # سنوات — years
    r"\d+\.?\d*\s*%",                  # نسب مئوية — percentages
    r"\$\d+\.?\d*[BMK]?",             # مبالغ مالية — monetary amounts
    r"\b\d{1,3}(,\d{3})*\b",          # أرقام كبيرة — large numbers
    r"(?:in|at|from|خلال|في|من)\s+\w+", # إشارات مكانية/زمانية — spatiotemporal references
]

# كلمات مفتاحية للهلوسة — Hallucination indicator keywords
HALLUCINATION_INDICATORS_EN: list[str] = [
    "certainly", "definitely", "absolutely", "without doubt",
    "it is well known that", "it goes without saying",
    "everyone knows", "nobody can deny", "undeniably",
    "unquestionably", "indisputably",
]

HALLUCINATION_INDICATORS_AR: list[str] = [
    "بالتأكيد", "بلا شك", "بلا أدنى شك", "من المؤكد أن",
    "من المعروف أن", "لا يمكن إنكار", "لا خلاف على",
    "مما لا شك فيه", "قطعياً", "حتمياً",
]

# كلمات ربط تدل على ادعاء — Claim indicator phrases
CLAIM_INDICATORS_EN: list[str] = [
    "according to", "research shows", "studies indicate",
    "data suggests", "evidence demonstrates", "it has been proven",
    "statistics show", "reports confirm", "experts say",
]

CLAIM_INDICATORS_AR: list[str] = [
    "وفقاً لـ", "تشير الأبحاث", "تشير الدراسات",
    "تُظهر البيانات", "يُثبت الدليل", "أثبتت الإحصائيات",
    "تؤكد التقارير", "يقول الخبراء", "أظهرت النتائج",
]


# ═══════════════════════════════════════════════════════════════════════════════
# قاعدة المعرفة المُدمجة — Built-in Knowledge Base (100+ factual assertions)
# ═══════════════════════════════════════════════════════════════════════════════

BUILTIN_KNOWLEDGE: dict[str, str] = {
    # ─── جغرافيا — Geography ───
    "geo_capital_france": "Paris is the capital of France.",
    "geo_capital_germany": "Berlin is the capital of Germany.",
    "geo_capital_japan": "Tokyo is the capital of Japan.",
    "geo_capital_china": "Beijing is the capital of China.",
    "geo_capital_uk": "London is the capital of the United Kingdom.",
    "geo_capital_egypt": "Cairo is the capital of Egypt.",
    "geo_capital_saudi": "Riyadh is the capital of Saudi Arabia.",
    "geo_capital_usa": "Washington, D.C. is the capital of the United States.",
    "geo_capital_brazil": "Brasilia is the capital of Brazil.",
    "geo_capital_australia": "Canberra is the capital of Australia.",
    "geo_capital_india": "New Delhi is the capital of India.",
    "geo_capital_russia": "Moscow is the capital of Russia.",
    "geo_capital_canada": "Ottawa is the capital of Canada.",
    "geo_capital_italy": "Rome is the capital of Italy.",
    "geo_capital_spain": "Madrid is the capital of Spain.",
    "geo_continent_egypt": "Egypt is in Africa.",
    "geo_continent_brazil": "Brazil is in South America.",
    "geo_continent_japan": "Japan is in Asia.",
    "geo_continent_france": "France is in Europe.",
    "geo_continent_australia": "Australia is in Oceania.",
    "geo_ocean_largest": "The Pacific Ocean is the largest ocean on Earth.",
    "geo_river_nile": "The Nile is one of the longest rivers in the world.",
    "geo_mountain_everest": "Mount Everest is the tallest mountain on Earth at 8849 meters.",
    "geo_sahara": "The Sahara is the largest hot desert in the world.",
    "geo_population_china": "China has the largest population in the world.",
    # ─── تاريخ — History ───
    "hist_moon_landing": "Apollo 11 landed on the Moon in 1969.",
    "hist_ww2_end": "World War II ended in 1945.",
    "hist_ww1_end": "World War I ended in 1918.",
    "hist_french_revolution": "The French Revolution began in 1789.",
    "hist_us_independence": "The United States declared independence in 1776.",
    "hist_berlin_wall": "The Berlin Wall fell in 1989.",
    "hist_printing_press": "The printing press was invented by Gutenberg around 1440.",
    "hist_silk_road": "The Silk Road connected China to Europe in ancient times.",
    "hist_ottoman_end": "The Ottoman Empire ended after World War I in 1922.",
    "hist_egypt_pyramids": "The Great Pyramid of Giza was built around 2560 BC.",
    "hist_renaissance": "The Renaissance began in Italy in the 14th century.",
    "hist_industrial_rev": "The Industrial Revolution began in Britain in the late 18th century.",
    # ─── علوم — Science ───
    "sci_earth_shape": "The Earth is roughly spherical.",
    "sci_water_formula": "The chemical formula for water is H2O.",
    "sci_speed_light": "The speed of light is approximately 299792458 meters per second.",
    "sci_gravity": "Gravity on Earth accelerates objects at approximately 9.8 meters per second squared.",
    "sci_dna": "DNA stands for deoxyribonucleic acid.",
    "sci_photosynthesis": "Photosynthesis converts sunlight, water, and CO2 into glucose and oxygen.",
    "sci_boiling_water": "Water boils at 100 degrees Celsius at standard atmospheric pressure.",
    "sci_freezing_water": "Water freezes at 0 degrees Celsius at standard atmospheric pressure.",
    "sci_planets": "There are 8 planets in the solar system.",
    "sci_earth_distance_sun": "The Earth is approximately 150 million kilometers from the Sun.",
    "sci_human_chromosomes": "Humans have 46 chromosomes.",
    "sci_heart_chambers": "The human heart has 4 chambers.",
    "sci_skeleton_bones": "The adult human skeleton has 206 bones.",
    "sci_sound_speed": "The speed of sound in air at sea level is approximately 343 meters per second.",
    "sci_pi": "Pi is approximately 3.14159.",
    "sci_e_mc2": "Einstein's equation E=mc squared relates energy to mass and the speed of light.",
    "sci_oxygen_atomic": "The atomic number of oxygen is 8.",
    "sci_carbon_atomic": "The atomic number of carbon is 6.",
    "sci_iron_atomic": "The atomic number of iron is 26.",
    "sci_gold_atomic": "The atomic number of gold is 79.",
    # ─── رياضيات — Mathematics ───
    "math_pi_digits": "Pi starts with 3.14159.",
    "math_prime_first": "The first prime number is 2.",
    "math_zero_factorial": "0 factorial equals 1.",
    "math_sqrt2": "The square root of 2 is approximately 1.414.",
    "math_euler": "Euler's number e is approximately 2.71828.",
    "math_triangle_angles": "The interior angles of a triangle sum to 180 degrees.",
    "math_circle_degrees": "A circle has 360 degrees.",
    # ─── لغات — Languages ───
    "lang_most_spoken": "Mandarin Chinese is the most spoken language by native speakers.",
    "lang_english speakers": "English is widely spoken as a second language worldwide.",
    "lang_arabic_script": "Arabic is written from right to left.",
    "lang_latin_alphabet": "The Latin alphabet has 26 letters.",
    # ─── تقنية — Technology ───
    "tech_internet_start": "The World Wide Web was invented by Tim Berners-Lee in 1989.",
    "tech_first_computer": "ENIAC is considered one of the first general-purpose electronic computers.",
    "tech_python_created": "Python was created by Guido van Rossum and first released in 1991.",
    "tech_linux_created": "Linux was created by Linus Torvalds in 1991.",
    "tech_smartphone_first": "The first smartphone is generally considered to be the IBM Simon from 1994.",
    # ─── بيئة — Environment ───
    "env_earth_surface_water": "Approximately 71 percent of Earth's surface is covered by water.",
    "env_oxygen_atmosphere": "Oxygen makes up approximately 21 percent of Earth's atmosphere.",
    "env_nitrogen_atmosphere": "Nitrogen makes up approximately 78 percent of Earth's atmosphere.",
    "env_co2_ppm": "CO2 levels in the atmosphere were around 420 ppm in the 2020s.",
    # ─── طب — Medicine ───
    "med_blood_types": "There are 4 main blood types: A, B, AB, and O.",
    "med_body_temp": "Normal human body temperature is approximately 37 degrees Celsius.",
    "med_heart_rate": "A normal resting heart rate for adults is 60 to 100 beats per minute.",
    "med_sleep_hours": "Adults typically need 7 to 9 hours of sleep per night.",
    # ─── اقتصاد — Economics ───
    "econ_usd_reserve": "The US dollar is the world's primary reserve currency.",
    "econ_gdp_largest": "The United States has the largest GDP in the world.",
    "econ_bitcoin_created": "Bitcoin was created in 2009 by Satoshi Nakamoto.",
    # ─── فنون وثقافة — Arts & Culture ───
    "art_mona_lisa": "The Mona Lisa was painted by Leonardo da Vinci.",
    "art_beethoven_deaf": "Beethoven composed music while deaf.",
    "art_shakespeare": "William Shakespeare wrote plays in the late 16th and early 17th centuries.",
    "art_quran_language": "The Quran is written in Arabic.",
    # ─── فضاء — Space ───
    "space_sun_type": "The Sun is a G-type main-sequence star.",
    "space_moon_distance": "The Moon is approximately 384400 kilometers from Earth.",
    "space_jupiter_largest": "Jupiter is the largest planet in the solar system.",
    "space_mars_color": "Mars appears red due to iron oxide on its surface.",
    "space_saturn_rings": "Saturn is known for its prominent ring system.",
    "space_earth_moons": "Earth has 1 natural satellite, the Moon.",
    "space_solar_age": "The solar system is approximately 4.6 billion years old.",
    "space_universe_age": "The universe is approximately 13.8 billion years old.",
    "space_milky_way": "The Milky Way is the galaxy that contains our solar system.",
    # ─── منطقة الشرق الأوسط — Middle East ───
    "me_dubai_country": "Dubai is a city in the United Arab Emirates.",
    "me_mecca_country": "Mecca is a city in Saudi Arabia.",
    "me_baghdad_country": "Baghdad is the capital of Iraq.",
    "me_damascus_country": "Damascus is the capital of Syria.",
    "me_amman_country": "Amman is the capital of Jordan.",
    "me_beirut_country": "Beirut is the capital of Lebanon.",
    "me_dead_sea": "The Dead Sea is the lowest point on land on Earth.",
    "me_suez_canal": "The Suez Canal connects the Mediterranean Sea to the Red Sea.",
    "me_arabic_speakers": "Arabic is spoken by over 400 million people worldwide.",
    # ─── معلومات عامة — General Knowledge ───
    "gen_un_members": "The United Nations has 193 member states.",
    "gen_olympics_origins": "The Olympic Games originated in ancient Greece.",
    "gen_chess_origin": "Chess originated in northern India around the 6th century.",
    "gen_paper_origin": "Paper was invented in China.",
    "gen_compass_origin": "The magnetic compass was invented in China.",
    "gen_gunpowder_origin": "Gunpowder was invented in China.",
    "gen_oceans_count": "There are 5 oceans on Earth: Pacific, Atlantic, Indian, Southern, and Arctic.",
    "gen_continents_count": "There are 7 continents on Earth.",
    "gen_un_largest_country": "Russia is the largest country by area.",
    "gen_smallest_country": "Vatican City is the smallest country by area.",
}


class HallucinationType(str, Enum):
    """أنواع الهلوسة — Hallucination type classification"""
    SELF_CONSISTENCY = "self_consistency"           # عدم اتساق ذاتي
    FACTUAL_UNGROUNDING = "factual_ungrounding"     # عدم تأصيل واقعي
    FABRICATED_ENTITY = "fabricated_entity"         # كيان مُختلق
    NUMERICAL = "numerical"                          # هلوسة رقمية
    LOGICAL_INCOHERENCE = "logical_incoherence"     # عدم ترابط منطقي
    OVERCONFIDENCE = "overconfidence"                # ثقة مفرطة
    ENTROPY_ANOMALY = "entropy_anomaly"              # شذوذ الإنتروبيا


# ═══════════════════════════════════════════════════════════════════════════════
# هياكل البيانات — Dataclasses
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ConsistencyScore:
    """
    نقاط الاتساق — Result from self-consistency checking.
    نتيجة مقارنة العينات المتعددة لتحديد نسبة الاتفاق.
    """
    agreement_ratio: float = 0.0              # نسبة الاتفاق بين العينات (0-1)
    conflicting_claims: list[str] = field(default_factory=list)  # الادعاءات المتضاربة
    sample_count: int = 0                     # عدد العينات المُقارنة

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "agreement_ratio": round(self.agreement_ratio, 4),
            "conflicting_claims": self.conflicting_claims,
            "sample_count": self.sample_count,
        }


@dataclass
class GroundingResult:
    """
    نتيجة التأصيل — Result from factual grounding verification.
    نتيجة التحقق من ادعاء واحد مقابل المعرفة.
    """
    claim: str = ""                           # الادعاء المُتحقق منه
    grounded: bool = False                    # هل الادعاء مُأصل؟
    source: str = ""                          # مصدر التحقق — source of verification
    confidence: float = 0.0                   # ثقة التحقق (0-1)

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "claim": self.claim,
            "grounded": self.grounded,
            "source": self.source,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class FabricatedEntity:
    """
    كيان مُختلق — A detected fabricated entity.
    يمثل كياناً (اسم، مكان، منظمة، رابط) تم الكشف عنه كونه مُختلقاً.
    """
    entity: str = ""                          # الكيان المُكتشف
    entity_type: str = "unknown"              # نوع الكيان (person/place/org/url)
    reason: str = ""                          # سبب الاشتباه — reason for suspicion

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "entity": self.entity,
            "entity_type": self.entity_type,
            "reason": self.reason,
        }


@dataclass
class NumericalIssue:
    """
    مشكلة رقمية — A detected numerical hallucination.
    يمثل رقماً أو إحصائية مشبوهة تم الكشف عنها.
    """
    value: str = ""                           # القيمة المشبوهة
    context: str = ""                         # السياق الذي وردت فيه
    issue_type: str = "unknown"               # نوع المشكلة (suspicious_stat/impossible_math/exaggerated)

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "value": self.value,
            "context": self.context,
            "issue_type": self.issue_type,
        }


@dataclass
class CoherenceResult:
    """
    نتيجة الترابط — Result from logical coherence checking.
    نتيجة فحص التناسق المنطقي الداخلي للنص.
    """
    is_coherent: bool = True                  # هل النص متماسك منطقياً؟
    contradictions: list[str] = field(default_factory=list)  # التناقضات المُكتشفة

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "is_coherent": self.is_coherent,
            "contradictions": self.contradictions,
        }


@dataclass
class CalibrationResult:
    """
    نتيجة المعايرة — Result from confidence calibration check.
    نتيجة فحص معايرة الثقة لتحديد الثقة المفرطة.
    """
    is_overconfident: bool = False            # هل الثقة مفرطة؟
    claimed_confidence: float = 0.0           # الثقة المُعلنة
    estimated_confidence: float = 0.0         # الثقة المُقدرة
    overconfidence_ratio: float = 0.0         # نسبة الإفراط في الثقة

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "is_overconfident": self.is_overconfident,
            "claimed_confidence": round(self.claimed_confidence, 4),
            "estimated_confidence": round(self.estimated_confidence, 4),
            "overconfidence_ratio": round(self.overconfidence_ratio, 4),
        }


@dataclass
class HallucinationResult:
    """
    نتيجة كشف الهلوسة — Complete hallucination detection result.
    نتيجة شاملة لكشف الهلوسة تشمل التصنيف والتفاصيل والأجزاء المُعلَّمة.
    """
    is_hallucination: bool = False            # هل النص مُهلوس؟
    confidence: float = 0.0                   # ثقة الكشف (0-1)
    type: str = "none"                        # نوع الهلوسة الرئيسي
    details: dict = field(default_factory=dict)           # تفاصيل إضافية
    flagged_segments: list[str] = field(default_factory=list)  # الأجزاء المُعلَّمة

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "is_hallucination": self.is_hallucination,
            "confidence": round(self.confidence, 4),
            "type": self.type,
            "details": self.details,
            "flagged_segments": self.flagged_segments,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# كيانات معروفة للاستخدام في كشف الكيانات المُختلقة
# Known entities for fabricated entity detection
# ═══════════════════════════════════════════════════════════════════════════════

KNOWN_PLACES: set[str] = {
    # مدن عربية — Arabic cities
    "Cairo", "Riyadh", "Jeddah", "Mecca", "Medina", "Dubai", "Abu Dhabi",
    "Doha", "Muscat", "Kuwait City", "Manama", "Baghdad", "Damascus",
    "Amman", "Beirut", "Jerusalem", "Casablanca", "Marrakech", "Tunis",
    "Algiers", "Tripoli", "Khartoum", "Sanaa", "Aden", "Muscat",
    # مدن عالمية — World cities
    "New York", "London", "Paris", "Tokyo", "Beijing", "Shanghai",
    "Moscow", "Berlin", "Rome", "Madrid", "Istanbul", "Mumbai",
    "Delhi", "Bangkok", "Seoul", "Sydney", "Melbourne", "Toronto",
    "Vancouver", "Chicago", "Los Angeles", "San Francisco", "Washington",
    "Boston", "Miami", "Seattle", "Houston", "Atlanta", "Denver",
    "Singapore", "Hong Kong", "Taipei", "Jakarta", "Kuala Lumpur",
    "Mexico City", "Sao Paulo", "Buenos Aires", "Lima", "Bogota",
    "Santiago", "Johannesburg", "Cape Town", "Cairo", "Nairobi",
    "Lagos", "Addis Ababa", "Accra", "Casablanca", "Algiers",
    # دول — Countries
    "United States", "China", "Japan", "Germany", "France", "UK",
    "India", "Brazil", "Canada", "Australia", "Russia", "Italy",
    "Spain", "Mexico", "South Korea", "Saudi Arabia", "UAE",
    "Egypt", "Turkey", "Iran", "Indonesia", "Thailand", "Vietnam",
    "Philippines", "Malaysia", "Pakistan", "Bangladesh", "Nigeria",
    "South Africa", "Kenya", "Ethiopia", "Morocco", "Jordan",
    "Iraq", "Syria", "Lebanon", "Palestine", "Yemen", "Oman",
    "Kuwait", "Bahrain", "Qatar",
}

KNOWN_ORGANIZATIONS: set[str] = {
    # منظمات دولية — International organizations
    "United Nations", "UN", "UNESCO", "WHO", "World Health Organization",
    "World Bank", "IMF", "WTO", "NATO", "EU", "European Union",
    "African Union", "ASEAN", "OPEC", "Arab League",
    # شركات تقنية — Tech companies
    "Google", "Apple", "Microsoft", "Amazon", "Meta", "Facebook",
    "Tesla", "OpenAI", "NVIDIA", "Intel", "Samsung", "IBM",
    "Oracle", "SAP", "Adobe", "Netflix", "Spotify", "Uber",
    # شركات عربية — Arab companies
    "Aramco", "Emirates", "Etihad", "Qatar Airways", "Flydubai",
    "STC", "Mobily", "Zain", "Etisalat", "du",
    # جامعات — Universities
    "MIT", "Stanford", "Harvard", "Oxford", "Cambridge",
    "Yale", "Princeton", "Columbia", "Caltech", "ETH Zurich",
    "Cairo University", "King Saud University", "AUB",
    # وكالات فضاء — Space agencies
    "NASA", "ESA", "JAXA", "ISRO", "SpaceX", "Blue Origin",
}

# أنماط أسماء الأشخاص المُختلقة — Fabricated person name patterns
FABRICATED_NAME_PREFIXES: list[str] = [
    "Dr. ", "Prof. ", "Mr. ", "Mrs. ", "Ms. ",
    "د. ", "أ.د. ", "السيد ", "السيدة ",
]

# أنماط الروابط المزيفة — Fake URL patterns
SUSPICIOUS_URL_PATTERNS: list[str] = [
    r"https?://[a-z]{20,}\.(com|org|net)",  # أسماء نطاقات طويلة جداً
    r"https?://\w+\.(xyz|top|click|buzz|info)",  # نطاقات مشبوهة
]


# ═══════════════════════════════════════════════════════════════════════════════
# فحص الاتساق الذاتي — SelfConsistencyChecker (Inner Class)
# ═══════════════════════════════════════════════════════════════════════════════

class SelfConsistencyChecker:
    """
    فاحص الاتساق الذاتي — Generates N alternative responses and checks agreement.

    مستوحى من طريقة self-consistency (Wang et al., 2023):
    توليد عينات متعددة من نفس الموجه ومقارنة النتائج.
    التباين الكبير بين العينات يشير إلى هلوسة محتملة.
    Agreement score = % of claims that are consistent across alternatives.
    Low agreement = potential hallucination.
    """

    def __init__(self, n_samples: int = DEFAULT_N_SAMPLES):
        """
        تهيئة فاحص الاتساق الذاتي.

        Args:
            n_samples: عدد العينات المُولَّدة للمقارنة (الافتراضي: 3)
        """
        self.n_samples = n_samples

    def check(
        self,
        text: str,
        context: dict | None = None,
        alternative_texts: list[str] | None = None,
    ) -> ConsistencyScore:
        """
        فحص الاتساق الذاتي — Generate N alternatives and check agreement.

        إذا تم توفير نصوص بديلة، يقارن النص الأصلي بها.
        إذا لم يتم توفيرها، يحاكي توليد بدائل ويحلل الاتساق الداخلي.

        Args:
            text: النص الأصلي — original text
            context: سياق اختياري — optional context
            alternative_texts: نصوص بديلة للمقارنة (اختياري)

        Returns:
            ConsistencyScore — نتيجة الاتساق الذاتي
        """
        if not text or not text.strip():
            return ConsistencyScore(sample_count=0)

        # استخراج الادعاءات الرئيسية من النص — extract key claims
        claims = self._extract_key_claims(text)

        if alternative_texts and len(alternative_texts) > 0:
            # مقارنة مع النصوص البديلة المُوفرة — compare with provided alternatives
            return self._compare_with_alternatives(text, claims, alternative_texts)
        else:
            # محاكاة توليد بدائل وتحليل الاتساق — simulate alternatives and analyze
            return self._simulate_and_analyze(text, claims)

    def _extract_key_claims(self, text: str) -> list[str]:
        """
        استخراج الادعاءات الرئيسية — Extract key claims from text.

        يبحث عن جمل تحتوي على بيانات قابلة للتحقق أو ادعاءات.
        """
        if not text:
            return []

        claims: list[str] = []
        sentences = re.split(r"(?<=[.!?؟。！？])\s+", text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # فحص وجود بيانات قابلة للتحقق — check for verifiable data
            has_verifiable_data = any(
                re.search(pattern, sentence) for pattern in CLAIM_PATTERNS
            )
            has_claim_indicator = any(
                indicator in sentence.lower()
                for indicator in CLAIM_INDICATORS_EN + CLAIM_INDICATORS_AR
            )

            if has_verifiable_data or has_claim_indicator:
                claims.append(sentence)

        return claims

    def _compare_with_alternatives(
        self,
        text: str,
        claims: list[str],
        alternatives: list[str],
    ) -> ConsistencyScore:
        """
        مقارنة مع النصوص البديلة — Compare original with alternative texts.

        يحسب نسبة الاتفاق عبر مقارنة الادعاءات الرئيسية.
        """
        if not claims:
            return ConsistencyScore(
                agreement_ratio=1.0,
                sample_count=len(alternatives) + 1,
            )

        # استخراج ادعاءات كل بديل — extract claims from each alternative
        alt_claims_list: list[list[str]] = []
        for alt in alternatives:
            alt_claims_list.append(self._extract_key_claims(alt))

        # حساب نسبة الاتفاق لكل ادعاء — compute agreement per claim
        consistent_count = 0
        conflicting: list[str] = []

        for claim in claims:
            # تحقق من وجود ادعاء مشابه في البدائل — check for similar claim in alternatives
            is_consistent = self._is_claim_consistent(claim, alt_claims_list)
            if is_consistent:
                consistent_count += 1
            else:
                conflicting.append(claim[:100])

        agreement_ratio = consistent_count / len(claims) if claims else 1.0

        return ConsistencyScore(
            agreement_ratio=max(0.0, min(1.0, agreement_ratio)),
            conflicting_claims=conflicting[:10],
            sample_count=len(alternatives) + 1,
        )

    def _simulate_and_analyze(
        self,
        text: str,
        claims: list[str],
    ) -> ConsistencyScore:
        """
        محاكاة وتحليل — Simulate alternative generation and analyze consistency.

        في غياب نموذج توليد حقيقي، يحلل الاتساق الداخلي للنص
        ويحاكي تبايناً معقولاً بناءً على إنتروبيا الادعاءات.
        """
        if not claims:
            return ConsistencyScore(
                agreement_ratio=1.0,
                sample_count=self.n_samples,
            )

        # حساب الاتساق الداخلي — compute internal consistency
        sentences = re.split(r"(?<=[.!?؟。！？])\s+", text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= 1:
            return ConsistencyScore(
                agreement_ratio=1.0,
                sample_count=self.n_samples,
            )

        # تحليل التشابه بين الجمل — analyze inter-sentence similarity
        total_similarity = 0.0
        comparisons = 0
        conflicting: list[str] = []

        for i in range(len(sentences)):
            for j in range(i + 1, len(sentences)):
                sim = self._compute_text_similarity(sentences[i], sentences[j])
                total_similarity += sim
                comparisons += 1
                if sim < 0.05:
                    conflicting.append(
                        f"جملة {i+1} ↔ جملة {j+1}: تباعد كبير"
                    )

        # نسبة الاتفاق الداخلي — internal agreement ratio
        internal_agreement = total_similarity / max(1, comparisons)

        # محاكاة تباين معقول — simulate reasonable variance
        # الادعاءات الرقمية أكثر عرضة للتباين — numerical claims are more variable
        numerical_claims = sum(
            1 for c in claims
            if re.search(r"\d+\.?\d*\s*%", c) or re.search(r"\$\d+", c)
        )
        variability_factor = numerical_claims * 0.08  # كل ادعاء رقمي يقلل الاتفاق قليلاً

        agreement_ratio = max(0.0, min(1.0, internal_agreement - variability_factor))

        return ConsistencyScore(
            agreement_ratio=agreement_ratio,
            conflicting_claims=conflicting[:10],
            sample_count=self.n_samples,
        )

    @staticmethod
    def _is_claim_consistent(
        claim: str,
        alt_claims_list: list[list[str]],
    ) -> bool:
        """
        هل الادعاء متسق مع البدائل؟ — Is the claim consistent with alternatives?

        يتحقق من وجود ادعاء مشابه في كل بديل.
        """
        if not alt_claims_list:
            return True

        claim_words = set(re.findall(r"\w+", claim.lower()))
        if not claim_words:
            return True

        consistent_with_all = True
        for alt_claims in alt_claims_list:
            best_similarity = 0.0
            for alt_claim in alt_claims:
                alt_words = set(re.findall(r"\w+", alt_claim.lower()))
                if alt_words:
                    intersection = claim_words & alt_words
                    union = claim_words | alt_words
                    similarity = len(intersection) / len(union)
                    best_similarity = max(best_similarity, similarity)
            if best_similarity < 0.2:
                consistent_with_all = False
                break

        return consistent_with_all

    @staticmethod
    def _compute_text_similarity(text_a: str, text_b: str) -> float:
        """
        حساب التشابه بين نصين — Compute similarity between two texts.

        يستخدم تشابه Jaccard على مستوى الكلمات.
        """
        words_a = set(re.findall(r"\w+", text_a.lower()))
        words_b = set(re.findall(r"\w+", text_b.lower()))

        if not words_a and not words_b:
            return 1.0
        if not words_a or not words_b:
            return 0.0

        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)


# ═══════════════════════════════════════════════════════════════════════════════
# فحص التأصيل الواقعي — FactualGroundingChecker (Inner Class)
# ═══════════════════════════════════════════════════════════════════════════════

class FactualGroundingChecker:
    """
    فاحص التأصيل الواقعي — Checks claims against a knowledge base.

    يستند إلى إطار MIND (ACL 2024): التحقق من أن الادعاءات
    في النص مبنية على معرفة موجودة وليست مُخترعة.

    يحتوي على 100+ ادعاء واقعي مُدمج للتحقق.
    يصنف الادعاءات إلى: مُأصل (grounded)، غير مُأصل (ungrounded)،
    غير قابل للتحقق (unverifiable).
    """

    def __init__(self, knowledge: dict[str, str] | None = None):
        """
        تهيئة فاحص التأصيل الواقعي.

        Args:
            knowledge: قاعدة معرفية إضافية (اختياري)
        """
        # دمج المعرفة المُدمجة مع المعرفة المُوفرة — merge built-in with provided
        self._knowledge: dict[str, str] = {**BUILTIN_KNOWLEDGE}
        if knowledge:
            self._knowledge.update(knowledge)

    def update_knowledge(self, source: str, content: str) -> None:
        """
        تحديث قاعدة المعرفة — Add or update a knowledge source.

        Args:
            source: معرف المصدر — source identifier
            content: المحتوى المعرفي — knowledge content
        """
        self._knowledge[source] = content

    def check(
        self,
        claims: list[str],
        knowledge: dict[str, str] | None = None,
    ) -> list[GroundingResult]:
        """
        التحقق من التأصيل — Verify claims against knowledge base.

        يتحقق من كل ادعاء مقابل المعرفة المتاحة ويُصنفها.

        Args:
            claims: قائمة الادعاءات للتحقق
            knowledge: قاعدة معرفية إضافية (اختياري)

        Returns:
            list[GroundingResult] — نتائج التحقق لكل ادعاء
        """
        if not claims:
            return []

        # دمج قواعد المعرفة — merge knowledge bases
        merged_kb = {**self._knowledge}
        if knowledge:
            merged_kb.update(knowledge)

        results: list[GroundingResult] = []
        for claim in claims:
            result = self._verify_claim(claim, merged_kb)
            results.append(result)

        return results

    def _extract_verifiable_claims(self, text: str) -> list[str]:
        """
        استخراج الادعاءات القابلة للتحقق — Extract checkable claims from text.

        يبحث عن جمل تحتوي على بيانات قابلة للتحقق:
        أرقام، تواريخ، إحصائيات، ادعاءات مكانية/زمانية.
        """
        if not text:
            return []

        claims: list[str] = []
        sentences = re.split(r"(?<=[.!?؟。！？])\s+", text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            has_verifiable_data = any(
                re.search(pattern, sentence) for pattern in CLAIM_PATTERNS
            )
            has_claim_indicator = any(
                indicator in sentence.lower()
                for indicator in CLAIM_INDICATORS_EN + CLAIM_INDICATORS_AR
            )

            if has_verifiable_data or has_claim_indicator:
                claims.append(sentence)

        return claims

    def _verify_claim(self, claim: str, knowledge: dict[str, str]) -> GroundingResult:
        """
        التحقق من ادعاء واحد — Verify a single claim against knowledge.

        يصنف الادعاء إلى:
        - مُأصل: ادعاء مدعوم بالمعرفة
        - غير مُأصل: ادعاء يتعارض مع المعرفة
        - غير قابل للتحقق: لا دليل عليه ولا ضده

        Args:
            claim: الادعاء المراد التحقق منه
            knowledge: قاعدة المعرفة

        Returns:
            GroundingResult — نتيجة التحقق
        """
        if not knowledge:
            return GroundingResult(
                claim=claim,
                grounded=False,
                source="",
                confidence=0.0,
            )

        claim_words = set(re.findall(r"\w+", claim.lower()))
        if not claim_words:
            return GroundingResult(
                claim=claim,
                grounded=False,
                source="",
                confidence=0.0,
            )

        best_score = 0.0
        best_source = ""
        is_contradicted = False

        for source_key, content in knowledge.items():
            content_words = set(re.findall(r"\w+", content.lower()))
            if not content_words:
                continue

            # تشابه Jaccard — Jaccard similarity
            intersection = claim_words & content_words
            union = claim_words | content_words
            similarity = len(intersection) / len(union) if union else 0.0

            if similarity > best_score:
                best_score = similarity
                best_source = source_key

            # فحص التناقض — check for contradiction
            if similarity > 0.15:
                claim_has_negation = any(
                    w in claim.lower()
                    for w in [
                        "not", "no", "never", "neither", "nor",
                        "لا", "لم", "لن", "ليس", "ليست", "غير",
                    ]
                )
                content_has_negation = any(
                    w in content.lower()
                    for w in [
                        "not", "no", "never", "neither", "nor",
                        "لا", "لم", "لن", "ليس", "ليست", "غير",
                    ]
                )
                if claim_has_negation != content_has_negation:
                    is_contradicted = True

        # تصنيف النتيجة — classify result
        if is_contradicted:
            return GroundingResult(
                claim=claim,
                grounded=False,
                source=best_source,
                confidence=max(0.0, 1.0 - best_score),
            )
        elif best_score >= 0.25:
            return GroundingResult(
                claim=claim,
                grounded=True,
                source=best_source,
                confidence=best_score,
            )
        else:
            return GroundingResult(
                claim=claim,
                grounded=False,
                source="",
                confidence=0.0,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# كاشف الكيانات المُختلقة — FabricatedEntityDetector (Inner Class)
# ═══════════════════════════════════════════════════════════════════════════════

class FabricatedEntityDetector:
    """
    كاشف الكيانات المُختلقة — Detects fabricated names, places, organizations, URLs.

    يستخدم مطابقة الأنماط + قوائم الكيانات المعروفة للكشف عن:
    - أسماء أشخاص مُختلقة مُقدمة كحقيقية
    - أماكن غير موجودة
    - منظمات مُختلقة
    - روابط مزيفة
    """

    def detect(self, text: str) -> list[FabricatedEntity]:
        """
        كشف الكيانات المُختلقة — Detect fabricated entities in text.

        Args:
            text: النص المراد فحصه

        Returns:
            list[FabricatedEntity] — الكيانات المُكتشفة
        """
        if not text or not text.strip():
            return []

        entities: list[FabricatedEntity] = []

        # كشف الأماكن غير المعروفة — detect unknown places
        entities.extend(self._detect_unknown_places(text))

        # كشف المنظمات غير المعروفة — detect unknown organizations
        entities.extend(self._detect_unknown_organizations(text))

        # كشف الروابط المشبوهة — detect suspicious URLs
        entities.extend(self._detect_suspicious_urls(text))

        # كشف أسماء الأشخاص المشبوهة — detect suspicious person names
        entities.extend(self._detect_suspicious_person_names(text))

        return entities

    def _detect_unknown_places(self, text: str) -> list[FabricatedEntity]:
        """
        كشف الأماكن غير المعروفة — Detect unknown/fabricated place names.

        يبحث عن أسماء مدن/دول تُقدَّم كحقيقية لكنها غير معروفة.
        """
        results: list[FabricatedEntity] = []

        # أنماط الإشارة للمكان — place reference patterns
        place_patterns = [
            r"\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",      # in CityName
            r"\bfrom\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",     # from CityName
            r"\bat\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",       # at CityName
            r"\bفي\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",       # في CityName
            r"\bمن\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",       # من CityName
            r"\bUniversity of\s+([A-Z][a-z]+)",                 # University of X
            r"\bcity of\s+([A-Z][a-z]+)",                       # city of X
        ]

        for pattern in place_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                place_name = match.group(1)
                # استبعاد الكلمات الشائعة — exclude common words
                common_words = {
                    "The", "This", "That", "These", "Those", "A", "An",
                    "My", "Your", "His", "Her", "Our", "Their",
                    "Most", "Many", "Some", "All", "Each", "Every",
                    "First", "Second", "Third", "Last", "Next",
                    "New", "Old", "Great", "Big", "Small",
                }
                if place_name in common_words:
                    continue
                if place_name not in KNOWN_PLACES and len(place_name) > 3:
                    # لا يُعتبر مكاناً مُختلقاً إذا كان اسماً عاماً
                    # فقط إذا ورد في سياق جغرافي واضح
                    context_match = match.group(0)
                    results.append(FabricatedEntity(
                        entity=place_name,
                        entity_type="place",
                        reason=f"مكان غير معروف في السياق: «{context_match}» — unknown place in context",
                    ))

        return results

    def _detect_unknown_organizations(self, text: str) -> list[FabricatedEntity]:
        """
        كشف المنظمات غير المعروفة — Detect unknown/fabricated organizations.
        """
        results: list[FabricatedEntity] = []

        org_patterns = [
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Institute|Foundation|Association|Council|Agency|Commission|Authority|Corporation|Enterprises)\b",
            r"\b(?:the)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Organization|Organisation|Committee|Bureau|Department)\b",
        ]

        for pattern in org_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                full_org = match.group(0).strip()
                # فحص إذا كانت المنظمة معروفة — check if org is known
                is_known = any(
                    known_org.lower() in full_org.lower()
                    for known_org in KNOWN_ORGANIZATIONS
                )
                if not is_known:
                    results.append(FabricatedEntity(
                        entity=full_org,
                        entity_type="organization",
                        reason="منظمة غير معروفة — unknown organization",
                    ))

        return results

    def _detect_suspicious_urls(self, text: str) -> list[FabricatedEntity]:
        """
        كشف الروابط المشبوهة — Detect suspicious or fabricated URLs.
        """
        results: list[FabricatedEntity] = []

        # استخراج جميع الروابط — extract all URLs
        url_pattern = r"https?://[^\s<>\"']+"
        urls = re.findall(url_pattern, text)

        for url in urls:
            is_suspicious = False
            reason = ""

            for sus_pattern in SUSPICIOUS_URL_PATTERNS:
                if re.search(sus_pattern, url):
                    is_suspicious = True
                    reason = "نمط رابط مشبوه — suspicious URL pattern"
                    break

            # فحص أسماء النطاقات المعروفة — check for known domain patterns
            if not is_suspicious:
                known_domains = [
                    ".com", ".org", ".net", ".edu", ".gov", ".io",
                    ".co", ".me", ".ai", ".dev", ".app",
                ]
                has_valid_tld = any(url.endswith(tld) or tld + "/" in url for tld in known_domains)
                if not has_valid_tld:
                    is_suspicious = True
                    reason = "نطاق غير معروف — unknown TLD"

            if is_suspicious:
                results.append(FabricatedEntity(
                    entity=url,
                    entity_type="url",
                    reason=reason,
                ))

        return results

    def _detect_suspicious_person_names(self, text: str) -> list[FabricatedEntity]:
        """
        كشف أسماء الأشخاص المشبوهة — Detect suspicious person names.
        """
        results: list[FabricatedEntity] = []

        for prefix in FABRICATED_NAME_PREFIXES:
            pattern = re.escape(prefix) + r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
            matches = re.finditer(pattern, text)
            for match in matches:
                full_ref = match.group(0)
                person_name = match.group(1)

                # أسماء معروفة شائعة — well-known names
                known_names = {
                    "Einstein", "Newton", "Darwin", "Curie",
                    "Hawking", "Feynman", "Turing", "Nobel",
                    "Gutenberg", "Galileo", "Tesla", "Edison",
                    "Mandela", "Gandhi", "King", "Lincoln",
                    "Shakespeare", "Mozart", "Beethoven", "Da Vinci",
                    "Berners-Lee", "Torvalds", "Van Rossum",
                }

                name_words = set(person_name.split())
                if not name_words & known_names and len(person_name) > 5:
                    results.append(FabricatedEntity(
                        entity=full_ref,
                        entity_type="person",
                        reason="اسم شخص مشبوه مع لقب أكاديمي — suspicious person name with academic title",
                    ))

        return results


# ═══════════════════════════════════════════════════════════════════════════════
# كاشف هلوسة الأرقام — NumericalHallucinationDetector (Inner Class)
# ═══════════════════════════════════════════════════════════════════════════════

class NumericalHallucinationDetector:
    """
    كاشف هلوسة الأرقام — Detects numerical hallucinations.

    يكشف:
    - إحصائيات مشبوهة ("99.7% of people...")
    - استحالات رياضية
    - أرقام مبالغ فيها
    """

    # كلمات تدل على إحصائية — Words indicating a statistic
    STAT_INDICATORS: list[str] = [
        "percent", "%", "of people", "of adults", "of Americans",
        "of users", "of students", "of workers", "of cases",
        "نسبة", "من الناس", "من البالغين", "من المستخدمين",
    ]

    def detect(self, text: str) -> list[NumericalIssue]:
        """
        كشف هلوسة الأرقام — Detect numerical hallucinations in text.

        Args:
            text: النص المراد فحصه

        Returns:
            list[NumericalIssue] — المشاكل الرقمية المُكتشفة
        """
        if not text or not text.strip():
            return []

        issues: list[NumericalIssue] = []

        # كشف الإحصائيات المشبوهة — detect suspicious statistics
        issues.extend(self._detect_suspicious_statistics(text))

        # كشف الاستحالات الرياضية — detect mathematical impossibilities
        issues.extend(self._detect_math_impossibilities(text))

        # كشف الأرقام المبالغ فيها — detect exaggerated numbers
        issues.extend(self._detect_exaggerated_numbers(text))

        return issues

    def _detect_suspicious_statistics(self, text: str) -> list[NumericalIssue]:
        """
        كشف الإحصائيات المشبوهة — Detect suspicious statistics.

        إحصائيات مثل "99.7% of people..." بدون مصدر هي مشبوهة.
        """
        results: list[NumericalIssue] = []

        # البحث عن نسب مئوية مع كلمات إحصائية — find percentages with stat indicators
        percentage_pattern = r"(\d+\.?\d*)\s*%"
        matches = re.finditer(percentage_pattern, text)

        for match in matches:
            value = float(match.group(1))
            # البحث عن السياق المحيط — look at surrounding context
            start = max(0, match.start() - 80)
            end = min(len(text), match.end() + 80)
            context = text[start:end]

            # إحصائيات عالية جداً بدون مصدر — very high stats without source
            has_source = any(
                src in context.lower()
                for src in ["according to", "source:", "study", "survey", "report",
                            "وفقاً", "مصدر:", "دراسة", "استطلاع", "تقرير"]
            )

            if value >= 95 and not has_source:
                results.append(NumericalIssue(
                    value=f"{value}%",
                    context=context.strip(),
                    issue_type="suspicious_stat",
                ))
            elif value > 100:
                results.append(NumericalIssue(
                    value=f"{value}%",
                    context=context.strip(),
                    issue_type="impossible_stat",
                ))

        return results

    def _detect_math_impossibilities(self, text: str) -> list[NumericalIssue]:
        """
        كشف الاستحالات الرياضية — Detect mathematical impossibilities.

        يبحث عن تناقضات رقمية بسيطة مثل:
        - أجزاء لا تجمع 100%
        - أرقام تتجاوز حدود معروفة
        """
        results: list[NumericalIssue] = []

        # فحص مجموع النسب — check sum of percentages
        percentages = re.findall(r"(\d+\.?\d*)\s*%", text)
        if len(percentages) >= 2:
            total = sum(float(p) for p in percentages)
            if total > 200:  # أكثر من ضعف المائة بدون مبرر
                results.append(NumericalIssue(
                    value=f"مجموع النسب: {total:.1f}%",
                    context=f"النسب الموجودة: {', '.join(p + '%' for p in percentages)}",
                    issue_type="impossible_math",
                ))

        # فحص التواريخ المستحيلة — check impossible dates
        year_pattern = r"\b(in\s+the\s+year\s+)?(\d{4})\s*(?:AD|BC|CE|BCE)?\b"
        year_matches = re.finditer(year_pattern, text)
        for match in year_matches:
            year_str = match.group(2)
            year = int(year_str)
            if year > 2100 or (year < 0):
                context_start = max(0, match.start() - 40)
                context_end = min(len(text), match.end() + 40)
                results.append(NumericalIssue(
                    value=year_str,
                    context=text[context_start:context_end].strip(),
                    issue_type="impossible_date",
                ))

        return results

    def _detect_exaggerated_numbers(self, text: str) -> list[NumericalIssue]:
        """
        كشف الأرقام المبالغ فيها — Detect exaggerated numbers.
        """
        results: list[NumericalIssue] = []

        # أرقام كبيرة جداً بدون سياق علمي — very large numbers without scientific context
        large_num_pattern = r"\b(\d{1,3}(?:,\d{3}){3,})\b"  # مليون فأكثر
        matches = re.finditer(large_num_pattern, text)

        for match in matches:
            context_start = max(0, match.start() - 60)
            context_end = min(len(text), match.end() + 60)
            context = text[context_start:context_end]

            # سياقات مشروعة للأرقام الكبيرة — legitimate contexts for large numbers
            legitimate_contexts = [
                "population", "GDP", "revenue", "budget", "distance",
                "light", "speed", "universe", "galaxy", "stars",
                "سكان", "ناتج", "إيرادات", "ميزانية", "مسافة",
                "الكون", "مجرة", "نجوم",
            ]

            has_legitimate_context = any(
                ctx in context.lower() for ctx in legitimate_contexts
            )

            if not has_legitimate_context:
                results.append(NumericalIssue(
                    value=match.group(1),
                    context=context.strip(),
                    issue_type="exaggerated",
                ))

        return results


# ═══════════════════════════════════════════════════════════════════════════════
# كاشف الهلوسة الرئيسي — HallucinationDetector
# ═══════════════════════════════════════════════════════════════════════════════

class HallucinationDetector:
    """
    كاشف الهلوسة — Main hallucination detection class.

    نظام كشف هلوسة متعدد الإشارات يجمع بين:
    1. فحص الاتساق الذاتي — Self-consistency checking
    2. التحقق من التأصيل الواقعي — Factual grounding verification
    3. كشف الكيانات المُختلقة — Fabricated entity detection
    4. كشف هلوسة الأرقام — Numerical hallucination detection
    5. فحص الترابط المنطقي — Logical coherence checking
    6. معايرة الثقة — Confidence calibration

    Integration:
    يعمل كفلتر للتحقق من مخرجات النموذج اللغوي
    قبل تقديمها للمستخدم أو استخدامها في اتخاذ القرارات.

    Example:
        detector = HallucinationDetector()
        result = detector.detect(
            "The capital of France is Lyon, and 99.9% of people agree.",
            context={"domain": "geography"}
        )
    """

    def __init__(
        self,
        n_samples: int | None = None,
        knowledge: dict[str, str] | None = None,
        custom_weights: dict[str, float] | None = None,
    ):
        """
        تهيئة كاشف الهلوسة.

        Args:
            n_samples: عدد عينات الاتساق الذاتي (الافتراضي: من البيئة أو 3)
            knowledge: قاعدة معرفية اختيارية للتحقق
            custom_weights: أوزان مخصصة للعوامل (اختياري)
        """
        # إعدادات البيئة — environment settings
        self._enabled = os.getenv(
            "MAMOUN_HALLUCINATION_DETECTION_ENABLED", "false"
        ).lower() in ("true", "1", "yes")

        self._threshold = float(
            os.getenv("MAMOUN_HALLUCINATION_THRESHOLD", "0.6")
        )

        env_samples = os.getenv("MAMOUN_HALLUCINATION_CONSISTENCY_SAMPLES")
        self._n_samples = n_samples or (
            int(env_samples) if env_samples else DEFAULT_N_SAMPLES
        )

        # المكونات الفرعية — sub-components
        self._consistency_checker = SelfConsistencyChecker(n_samples=self._n_samples)
        self._grounding_checker = FactualGroundingChecker(knowledge=knowledge)
        self._entity_detector = FabricatedEntityDetector()
        self._numerical_detector = NumericalHallucinationDetector()

        # أوزان العوامل — factor weights (can be customized)
        self._weights = {
            "self_consistency": WEIGHT_SELF_CONSISTENCY,
            "factual_grounding": WEIGHT_FACTUAL_GROUNDING,
            "fabricated_entities": WEIGHT_FABRICATED_ENTITIES,
            "numerical_hallucination": WEIGHT_NUMERICAL_HALLUCINATION,
            "logical_coherence": WEIGHT_LOGICAL_COHERENCE,
            "confidence_calibration": WEIGHT_CONFIDENCE_CALIBRATION,
        }
        if custom_weights:
            for key, weight in custom_weights.items():
                if key in self._weights:
                    self._weights[key] = weight

        # إحصائيات — statistics
        self._total_checks = 0
        self._hallucination_count = 0
        self._total_duration_ms = 0.0

        logger.info(
            "كاشف الهلوسة AGI مهيأ — HallucinationDetector initialized "
            "(enabled=%s, threshold=%.2f, n_samples=%d)",
            self._enabled,
            self._threshold,
            self._n_samples,
        )

    @property
    def enabled(self) -> bool:
        """هل كاشف الهلوسة مُمكّن؟ — Is the detector enabled?"""
        return self._enabled

    @property
    def threshold(self) -> float:
        """عتبة الهلوسة — Hallucination threshold"""
        return self._threshold

    def detect(self, text: str, context: dict | None = None) -> dict:
        """
        كشف الهلوسة — Main entry point for hallucination detection.

        يحلل النص للكشف عن الهلوسة عبر ستة محاور:
        1. الاتساق الذاتي: مقارنة عينات متعددة
        2. التأصيل الواقعي: التحقق من الادعاءات
        3. الكيانات المُختلقة: كشف الأسماء والأماكن المزيفة
        4. هلوسة الأرقام: كشف الإحصائيات والأرقام المشبوهة
        5. الترابط المنطقي: إيجاد تناقضات داخلية
        6. معايرة الثقة: كشف الثقة المفرطة

        Args:
            text: النص المراد فحصه
            context: سياق اختياري (قاموس يحتوي على معلومات إضافية)

        Returns:
            dict — نتيجة كشف الهلوسة شاملة
        """
        start_time = time.time()

        # إذا كان الكاشف معطلاً، أرجع نتيجة آمنة — return safe result if disabled
        if not self._enabled:
            result = HallucinationResult(
                is_hallucination=False,
                confidence=0.0,
                type="disabled",
                details={"message": "كاشف الهلوسة معطل — Hallucination detection is disabled"},
            )
            return result.to_dict()

        # التحقق من المدخلات — validate inputs
        if not text or not text.strip():
            result = HallucinationResult(
                is_hallucination=False,
                confidence=0.0,
                type="empty_input",
            )
            return result.to_dict()

        # ═══════════════════════════════════════════════════════════
        # المرحلة 1: فحص الاتساق الذاتي — Phase 1: Self-consistency
        # ═══════════════════════════════════════════════════════════
        consistency_score = self._check_self_consistency(text, context)

        # ═══════════════════════════════════════════════════════════
        # المرحلة 2: التحقق من التأصيل الواقعي — Phase 2: Factual grounding
        # ═══════════════════════════════════════════════════════════
        claims = self._grounding_checker._extract_verifiable_claims(text)

        # دمج المعرفة من السياق — merge context knowledge
        context_knowledge: dict[str, str] = {}
        if context and "knowledge" in context:
            context_knowledge.update(context["knowledge"])

        grounding_results = self._check_factual_grounding(claims, context_knowledge)

        # ═══════════════════════════════════════════════════════════
        # المرحلة 3: كشف الكيانات المُختلقة — Phase 3: Fabricated entities
        # ═══════════════════════════════════════════════════════════
        fabricated_entities = self._detect_fabricated_entities(text)

        # ═══════════════════════════════════════════════════════════
        # المرحلة 4: كشف هلوسة الأرقام — Phase 4: Numerical hallucination
        # ═══════════════════════════════════════════════════════════
        numerical_issues = self._detect_numerical_hallucination(text)

        # ═══════════════════════════════════════════════════════════
        # المرحلة 5: فحص الترابط المنطقي — Phase 5: Logical coherence
        # ═══════════════════════════════════════════════════════════
        coherence_result = self._check_logical_coherence(text)

        # ═══════════════════════════════════════════════════════════
        # المرحلة 6: معايرة الثقة — Phase 6: Confidence calibration
        # ═══════════════════════════════════════════════════════════
        claimed_confidence = 1.0
        if context and "confidence" in context:
            claimed_confidence = float(context["confidence"])
        calibration_result = self._check_confidence_calibration(
            text, claimed_confidence
        )

        # ═══════════════════════════════════════════════════════════
        # المرحلة 7: حساب نقاط الهلوسة المركبة — Phase 7: Compute composite score
        # ═══════════════════════════════════════════════════════════

        # عامل الاتساق الذاتي — self-consistency factor (low agreement = more hallucination)
        consistency_factor = 1.0 - consistency_score.agreement_ratio

        # عامل التأصيل الواقعي — factual grounding factor
        if grounding_results:
            grounded_ratio = sum(1 for r in grounding_results if r.grounded) / len(grounding_results)
            grounding_factor = 1.0 - grounded_ratio
        else:
            grounding_factor = 0.0  # لا ادعاءات = لا هلوسة من هذا الباب

        # عامل الكيانات المُختلقة — fabricated entities factor
        entity_factor = min(1.0, len(fabricated_entities) * 0.3)

        # عامل هلوسة الأرقام — numerical hallucination factor
        numerical_factor = min(1.0, len(numerical_issues) * 0.25)

        # عامل الترابط المنطقي — logical coherence factor
        coherence_factor = 0.0 if coherence_result.is_coherent else min(
            1.0, len(coherence_result.contradictions) * 0.2
        )

        # عامل معايرة الثقة — confidence calibration factor
        calibration_factor = 0.0
        if calibration_result.is_overconfident:
            calibration_factor = min(1.0, calibration_result.overconfidence_ratio)

        # حساب النقاط المركبة — compute composite score
        hallucination_score = (
            self._weights["self_consistency"] * consistency_factor
            + self._weights["factual_grounding"] * grounding_factor
            + self._weights["fabricated_entities"] * entity_factor
            + self._weights["numerical_hallucination"] * numerical_factor
            + self._weights["logical_coherence"] * coherence_factor
            + self._weights["confidence_calibration"] * calibration_factor
        )

        # تأثير التفاعل — interaction effect
        # إذا كان هناك عدة مؤشرات معاً → تعزيز — boost if multiple indicators align
        active_indicators = sum(1 for f in [
            consistency_factor, grounding_factor, entity_factor,
            numerical_factor, coherence_factor, calibration_factor,
        ] if f > 0.3)
        if active_indicators >= 3:
            interaction_boost = 0.1 * (active_indicators - 2)
            hallucination_score += interaction_boost

        hallucination_score = max(0.0, min(1.0, hallucination_score))

        # تحديد نوع الهلوسة الرئيسي — determine dominant hallucination type
        factors_map = {
            HallucinationType.SELF_CONSISTENCY: consistency_factor,
            HallucinationType.FACTUAL_UNGROUNDING: grounding_factor,
            HallucinationType.FABRICATED_ENTITY: entity_factor,
            HallucinationType.NUMERICAL: numerical_factor,
            HallucinationType.LOGICAL_INCOHERENCE: coherence_factor,
            HallucinationType.OVERCONFIDENCE: calibration_factor,
        }
        dominant_type = max(factors_map, key=factors_map.get)
        if all(f < 0.1 for f in factors_map.values()):
            dominant_type = HallucinationType.ENTROPY_ANOMALY

        # بناء قائمة الأجزاء المُعلَّمة — build flagged segments list
        flagged_segments: list[str] = []
        for claim in consistency_score.conflicting_claims:
            flagged_segments.append(f"[اتساق] {claim}")
        for gr in grounding_results:
            if not gr.grounded:
                flagged_segments.append(f"[تأصيل] {gr.claim[:80]}")
        for fe in fabricated_entities:
            flagged_segments.append(f"[كيان] {fe.entity} ({fe.entity_type})")
        for ni in numerical_issues:
            flagged_segments.append(f"[رقم] {ni.value}")
        for contr in coherence_result.contradictions:
            flagged_segments.append(f"[تناقض] {contr}")

        # بناء نتيجة الهلوسة — build hallucination result
        is_hallucination = hallucination_score >= self._threshold

        result = HallucinationResult(
            is_hallucination=is_hallucination,
            confidence=hallucination_score,
            type=dominant_type.value if is_hallucination else "none",
            details={
                "hallucination_score": round(hallucination_score, 4),
                "threshold": self._threshold,
                "consistency": consistency_score.to_dict(),
                "grounding": [r.to_dict() for r in grounding_results],
                "fabricated_entities": [e.to_dict() for e in fabricated_entities],
                "numerical_issues": [i.to_dict() for i in numerical_issues],
                "coherence": coherence_result.to_dict(),
                "calibration": calibration_result.to_dict(),
                "factors": {
                    "consistency_factor": round(consistency_factor, 4),
                    "grounding_factor": round(grounding_factor, 4),
                    "entity_factor": round(entity_factor, 4),
                    "numerical_factor": round(numerical_factor, 4),
                    "coherence_factor": round(coherence_factor, 4),
                    "calibration_factor": round(calibration_factor, 4),
                },
                "claims_extracted": len(claims),
                "claims_grounded": sum(1 for r in grounding_results if r.grounded),
                "claims_ungrounded": sum(1 for r in grounding_results if not r.grounded),
                "active_indicators": active_indicators,
                "duration_ms": round((time.time() - start_time) * 1000, 1),
            },
            flagged_segments=flagged_segments[:20],
        )

        # تحديث الإحصائيات — update statistics
        self._total_checks += 1
        self._total_duration_ms += (time.time() - start_time) * 1000
        if is_hallucination:
            self._hallucination_count += 1

        logger.info(
            "كشف هلوسة AGI: score=%.3f type=%s is_hallucination=%s — "
            "Hallucination detection: score=%.3f type=%s is_hallucination=%s",
            hallucination_score, result.type, is_hallucination,
            hallucination_score, result.type, is_hallucination,
        )

        return result.to_dict()

    # ═══════════════════════════════════════════════════════════════
    # الطرق الداخلية — Internal Methods
    # ═══════════════════════════════════════════════════════════════

    def _check_self_consistency(
        self,
        text: str,
        context: dict | None = None,
    ) -> ConsistencyScore:
        """
        فحص الاتساق الذاتي — Check self-consistency of the text.

        يقارن توليدات متعددة (محاكاة أو مُوفرة) لتحديد الاتفاق.

        Args:
            text: النص الأصلي
            context: سياق اختياري قد يحتوي على نصوص بديلة

        Returns:
            ConsistencyScore — نتيجة الاتساق الذاتي
        """
        alternatives: list[str] | None = None
        if context and "alternative_texts" in context:
            alternatives = context["alternative_texts"]

        return self._consistency_checker.check(text, context, alternatives)

    def _check_factual_grounding(
        self,
        claims: list[str],
        knowledge: dict[str, str] | None = None,
    ) -> list[GroundingResult]:
        """
        التحقق من التأصيل الواقعي — Verify claims against knowledge base.

        يتحقق من أن الادعاءات مبنية على معرفة موجودة وليست مُختلقة.

        Args:
            claims: قائمة الادعاءات المستخرجة
            knowledge: قاعدة المعرفة للتحقق

        Returns:
            list[GroundingResult] — نتائج التحقق لكل ادعاء
        """
        return self._grounding_checker.check(claims, knowledge)

    def _check_confidence_calibration(
        self,
        text: str,
        confidence: float,
    ) -> CalibrationResult:
        """
        معايرة الثقة — Check confidence calibration.

        يكشف الثقة المفرطة بناءً على مؤشرات الهلوسة في النص.

        Args:
            text: النص المراد فحصه
            confidence: مستوى الثقة المُعلن (0-1)

        Returns:
            CalibrationResult — نتيجة المعايرة
        """
        # حساب الثقة المُقدرة بناءً على مؤشرات النص — estimate confidence from text
        text_lower = text.lower()

        # عدد مؤشرات الهلوسة — count hallucination indicators
        indicator_count = 0
        for indicator in HALLUCINATION_INDICATORS_EN + HALLUCINATION_INDICATORS_AR:
            if indicator in text_lower:
                indicator_count += 1

        # عدد مؤشرات عدم اليقين — count uncertainty indicators
        uncertainty_indicators = [
            "maybe", "perhaps", "possibly", "might", "could",
            "roughly", "approximately", "about", "around",
            "ربما", "رب", "قد", "يمكن", "تقريباً", "حوالي",
        ]
        uncertainty_count = sum(
            1 for ui in uncertainty_indicators if ui in text_lower
        )

        # تقدير الثقة — estimate confidence
        # مؤشرات الهلوسة ترفع الثقة المُعلنة — hallucination indicators inflate stated confidence
        # مؤشرات عدم اليقين تخفض الثقة — uncertainty indicators reduce it
        estimated_confidence = max(0.0, min(1.0,
            0.7  # أساس معقول — reasonable baseline
            - indicator_count * 0.1   # عقوبة الإفراط في الثقة
            + uncertainty_count * 0.05  # مكافأة الصدق
        ))

        # حساب نسبة الإفراط — compute overconfidence ratio
        overconfidence = max(0.0, confidence - estimated_confidence)
        overconfidence_ratio = overconfidence / max(0.01, confidence)

        return CalibrationResult(
            is_overconfident=overconfidence > 0.2,
            claimed_confidence=confidence,
            estimated_confidence=estimated_confidence,
            overconfidence_ratio=overconfidence_ratio,
        )

    def _detect_fabricated_entities(self, text: str) -> list[FabricatedEntity]:
        """
        كشف الكيانات المُختلقة — Detect fabricated entities in text.

        يكشف أسماء أشخاص مزيفة، أماكن غير موجودة،
        منظمات مُختلقة، وروابط مشبوهة.

        Args:
            text: النص المراد فحصه

        Returns:
            list[FabricatedEntity] — الكيانات المُكتشفة
        """
        return self._entity_detector.detect(text)

    def _check_logical_coherence(self, text: str) -> CoherenceResult:
        """
        فحص الترابط المنطقي — Check internal logical coherence.

        يبحث عن تناقضات داخلية في النص مثل:
        - جمل متعارضة
        - نفي متبادل
        - ادعاءات متضاربة

        Args:
            text: النص المراد فحصه

        Returns:
            CoherenceResult — نتيجة الترابط
        """
        if not text or not text.strip():
            return CoherenceResult(is_coherent=True)

        # أنماط الإثبات والنفي — affirmative and negation patterns
        affirmative_patterns = [
            r"\b(is|are|was|were)\s+\w+",
            r"\b(can|could|will|would|should)\b",
            r"\b(يكون|كان|هو|هي)\b",
            r"\b(يمكن|سي|يجب|قد)\b",
        ]

        negation_patterns = [
            r"\b(is\s+not|are\s+not|was\s+not|were\s+not)\b",
            r"\b(cannot|can't|couldn't|won't|wouldn't|shouldn't)\b",
            r"\b(not|never|neither|nor)\b",
            r"\b(لا\s+يكون|لم\s+يكن|ليس|ليست)\b",
            r"\b(لا\s+يمكن|لن|لا\s+يجب)\b",
        ]

        sentences = re.split(r"(?<=[.!?؟。！？])\s+", text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) < 2:
            return CoherenceResult(is_coherent=True)

        contradictions: list[str] = []

        # فحص كل زوج من الجمل — check every pair of sentences
        for i in range(len(sentences)):
            for j in range(i + 1, len(sentences)):
                a_lower = sentences[i].lower()
                b_lower = sentences[j].lower()

                # فحص التناقض بالإثبات والنفي — check affirmative/negation contradiction
                a_affirmative = any(
                    re.search(p, a_lower) for p in affirmative_patterns
                )
                b_negation = any(
                    re.search(p, b_lower) for p in negation_patterns
                )
                a_negation = any(
                    re.search(p, a_lower) for p in negation_patterns
                )
                b_affirmative = any(
                    re.search(p, b_lower) for p in affirmative_patterns
                )

                if (a_affirmative and b_negation) or (a_negation and b_affirmative):
                    # فحص وجود كلمات مشتركة ذات معنى — check for meaningful shared words
                    a_words = set(re.findall(r"\w+", a_lower))
                    b_words = set(re.findall(r"\w+", b_lower))
                    stop_words = {
                        "the", "a", "an", "is", "are", "was", "were",
                        "be", "been", "have", "has", "had", "do", "does",
                        "did", "will", "would", "could", "should", "may",
                        "might", "can", "shall", "to", "of", "in", "for",
                        "on", "with", "at", "by", "from", "as", "not",
                        "no", "never", "neither", "nor",
                        "هو", "هي", "كان", "يكون", "التي", "الذي",
                        "إلى", "من", "في", "على", "مع", "عن",
                    }
                    meaningful_common = (a_words & b_words) - stop_words
                    if len(meaningful_common) >= 2:
                        contradictions.append(
                            f"جملة {i+1} ↔ جملة {j+1}: تناقض محتمل"
                        )

        is_coherent = len(contradictions) == 0

        return CoherenceResult(
            is_coherent=is_coherent,
            contradictions=contradictions[:10],
        )

    def _detect_numerical_hallucination(self, text: str) -> list[NumericalIssue]:
        """
        كشف هلوسة الأرقام — Detect numerical hallucinations.

        يكشف إحصائيات مشبوهة، استحالات رياضية، وأرقام مبالغ فيها.

        Args:
            text: النص المراد فحصه

        Returns:
            list[NumericalIssue] — المشاكل الرقمية المُكتشفة
        """
        return self._numerical_detector.detect(text)

    def get_stats(self) -> dict:
        """
        إحصائيات الاستخدام — Get usage statistics.

        Returns:
            dict — إحصائيات تشمل عدد الفحوصات والهلوسات
        """
        return {
            "total_checks": self._total_checks,
            "hallucination_count": self._hallucination_count,
            "hallucination_rate": (
                round(self._hallucination_count / max(1, self._total_checks), 4)
            ),
            "avg_duration_ms": (
                round(self._total_duration_ms / max(1, self._total_checks), 1)
            ),
            "enabled": self._enabled,
            "threshold": self._threshold,
            "n_samples": self._n_samples,
            "knowledge_base_size": len(self._grounding_checker._knowledge),
        }
