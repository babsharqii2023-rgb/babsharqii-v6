"""
BABSHARQII v40.0 — Novelty Scorer
مُقيّم الجدة

Evaluates the novelty of a generated idea on a 0-100 scale by comparing
against an internal knowledge base, reference base, and previous training data.

Scoring dimensions:
  - Uniqueness (0-100): How different from known ideas
  - Surprise (0-100): How unexpected the combination is
  - Transformative potential (0-100): How likely to inspire further innovation
  - Overall novelty (weighted combination)

Includes domain-specific cliché detection and penalty, plus novelty trend tracking.
"""

import os
import uuid
import time
import json
import math
import hashlib
import random
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from pathlib import Path
from enum import Enum


# =============================================================================
# Feature Flag
# =============================================================================

MAMOUN_NOVELTY_SCORER = os.environ.get("MAMOUN_NOVELTY_SCORER_ENABLED", "false") == "true"


# =============================================================================
# Data Classes — فئات البيانات
# =============================================================================

@dataclass
class NoveltyScore:
    """
    The result of a novelty evaluation.
    نتيجة تقييم الجدة — درجات شاملة ومفصّلة.
    """
    overall_score: float = 0.0
    uniqueness: float = 0.0
    surprise: float = 0.0
    transformative_potential: float = 0.0
    domain: str = ""
    is_novel: bool = False  # True if overall_score >= 60
    explanation: str = ""
    explanation_ar: str = ""

    def __post_init__(self):
        self.is_novel = self.overall_score >= 60.0

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 2),
            "uniqueness": round(self.uniqueness, 2),
            "surprise": round(self.surprise, 2),
            "transformative_potential": round(self.transformative_potential, 2),
            "domain": self.domain,
            "is_novel": self.is_novel,
            "explanation": self.explanation,
            "explanation_ar": self.explanation_ar,
        }


@dataclass
class ReferenceComparison:
    """
    Comparison results against the reference base.
    نتائج المقارنة مع قاعدة المراجع.
    """
    closest_matches: list = field(default_factory=list)
    min_distance: float = 1.0
    avg_distance: float = 1.0
    percentile_rank: float = 50.0

    def to_dict(self) -> dict:
        return {
            "closest_matches": self.closest_matches[:5],
            "min_distance": round(self.min_distance, 4),
            "avg_distance": round(self.avg_distance, 4),
            "percentile_rank": round(self.percentile_rank, 2),
        }


@dataclass
class ClicheReport:
    """
    Report on detected clichés in an idea.
    تقرير عن الكليشيهات المكتشفة في فكرة.
    """
    cliches_found: list = field(default_factory=list)
    penalty_score: float = 0.0
    suggestions: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "cliches_found": self.cliches_found,
            "penalty_score": round(self.penalty_score, 2),
            "suggestions": self.suggestions,
        }


# =============================================================================
# Domain Cliché Databases — قواعد بيانات الكليشيهات حسب المجال
# =============================================================================

DOMAIN_CLICHE_DB = {
    "slogan": {
        "cliches": [
            "نحن الأفضل", "الجودة أولاً", "التميز بلا حدود",
            "الإبداع بلا حدود", "مستقبل أفضل", "شراكة النجاح",
            "الأول دائماً", "اختيارك الأمثل", "نحو القمة",
        ],
        "alternatives": [
            "استخدم تشبيهاً غير متوقع من الطبيعة",
            "اعتمد على الطباق (تضاد) لإبراز التميز",
            "استخدم الجناس لخلق لفظ مميز",
            "ابنِ الشعار على السجع مع معنى عميق",
        ],
    },
    "marketing_campaign": {
        "cliches": [
            "اشترِ واحد واحصل على الثاني مجاناً", "عرض لفترة محدودة",
            "الأكثر مبيعاً", "لا تفوّت الفرصة", "الأسعار التي لا تُقاوم",
            "خصم حصري", "فرصة العمر", "لن تجد أفضل من هذا",
        ],
        "alternatives": [
            "ابنِ الحملة على قصة حقيقية",
            "استخدم الاستعارة لربط المنتج بتجربة عاطفية",
            "قدّم تحدياً تفاعلياً بدلاً من خصم مباشر",
            "اربط الحملة بقضية مجتمعية ذات صلة",
        ],
    },
    "product_idea": {
        "cliches": [
            "تطبيق يجمع كل شيء", "النسخة العربية من",
            "منصة ذكية باستخدام الذكاء الاصطناعي", "حل شامل متكامل",
            "الأول من نوعه", "ثورة في عالم",
        ],
        "alternatives": [
            "ركّز على مشكلة محددة بدلاً من حل شامل",
            "استلهام من طبيعة مختلفة تماماً",
            "ادمج مجالين غير مرتبطين بشكل غير متوقع",
            "ابدأ من التجربة الشخصية الأليمة",
        ],
    },
    "logo_concept": {
        "cliches": [
            "حرف أول داخل دائرة", "سهم للأعلى", "كرة أرضية",
            "ورقة خضراء", "شخص يمسك شيئاً", "موجة بسيطة",
        ],
        "alternatives": [
            "استخدم التجريد العضوي بدل الأشكال الهندسية المعتادة",
            "ابنِ الشعار من مسافة سلبية (negative space)",
            "استلهم من خط عربي حقيقي",
            "فكّر في حركة بدل شكل ثابت",
        ],
    },
    "story": {
        "cliches": [
            "كان يا ما كان", "وفي النهاية عاشوا بسعادة",
            "البطل المختار", "الرحلة الملحمية", "العدو الذي هو النفس",
        ],
        "alternatives": [
            "ابدأ من النهاية وارجع بالزمن",
            "اجعل البطل غير متوقع (طفل، عجوز، آلة)",
            "استخدم قالب الرسالة أو اليوميات",
            "ادمج الواقع بالخيال بسلاسة",
        ],
    },
    "design": {
        "cliches": [
            "تصميم بسيط ونظيف", "ألوان هادئة", "خط عصري",
            "تدرج لوني", "أيقونات مسطحة",
        ],
        "alternatives": [
            "استخدم تناقضاً صارخاً في الألوان",
            "ادمج التصميم المسطح مع عمق محدود",
            "استلهم من أنماط تقليدية بلمسة حديثة",
            "اختر قيوداً فنية غير معتادة وابدع ضمنها",
        ],
    },
    "code_architecture": {
        "cliches": [
            "بنية مايكروسيرفيس", "طبقات MVC", "REST API",
            "قاعدة بيانات علائقية", "ذاكرة تخزين مؤقت",
        ],
        "alternatives": [
            "فكّر في معمارية مبنية على الأحداث (event-driven)",
            "استخدم نمط CQRS لفصل القراءة والكتابة",
            "جرب معمارية قائمة على الرسم البياني",
            "استلهم من الأنظمة البيولوجية التكيفية",
        ],
    },
}


# =============================================================================
# NoveltyScorer — مُقيّم الجدة
# =============================================================================

class NoveltyScorer:
    """
    Evaluates the novelty of generated ideas by comparing against:
      - Internal knowledge base (past outputs stored in SQLite)
      - Reference base (common patterns and clichés per domain)
      - Semantic distance from known patterns

    Scoring dimensions:
      - Uniqueness (weight 0.35): How different from known ideas
      - Surprise (weight 0.35): How unexpected the combination is
      - Transformative potential (weight 0.30): How likely to inspire innovation

    Domain-specific cliché detection with penalty.
    Tracks novelty trends over time.
    """

    NOVELTY_THRESHOLD = 60.0  # Ideas >= 60 are considered novel
    UNIQUENESS_WEIGHT = 0.35
    SURPRISE_WEIGHT = 0.35
    TRANSFORMATIVE_WEIGHT = 0.30

    def __init__(self, db_path: str = ""):
        self._enabled = MAMOUN_NOVELTY_SCORER
        self._reference_base: dict = {}  # domain -> list of reference fingerprints
        self._scoring_history: list[dict] = []  # track trends over time
        self._max_history = 1000

        # SQLite for persistent reference storage
        if not db_path:
            db_path = str(Path(__file__).parent.parent.parent / "data" / "novelty_references.db")
        self._db_path = db_path
        self._initialized = False

    async def _initialize(self):
        """Initialize SQLite tables — تهيئة جداول قاعدة البيانات"""
        if self._initialized:
            return
        try:
            import aiosqlite
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS novelty_references (
                        ref_id TEXT PRIMARY KEY,
                        domain TEXT NOT NULL,
                        content TEXT NOT NULL,
                        fingerprint TEXT NOT NULL,
                        added_at REAL DEFAULT 0.0
                    )
                """)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS novelty_scores (
                        score_id TEXT PRIMARY KEY,
                        domain TEXT NOT NULL,
                        overall_score REAL DEFAULT 0.0,
                        uniqueness REAL DEFAULT 0.0,
                        surprise REAL DEFAULT 0.0,
                        transformative_potential REAL DEFAULT 0.0,
                        is_novel INTEGER DEFAULT 0,
                        scored_at REAL DEFAULT 0.0
                    )
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_novelty_refs_domain
                    ON novelty_references(domain)
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_novelty_scores_domain
                    ON novelty_scores(domain)
                """)
                await db.commit()
        except ImportError:
            pass  # aiosqlite not available; use in-memory
        self._initialized = True

    # =========================================================================
    # Core Scoring — التسجيل الأساسي
    # =========================================================================

    def score_novelty(self, idea: dict, domain: str) -> NoveltyScore:
        """
        Score the novelty of an idea on a 0-100 scale.
        تسجيل جدة فكرة على مقياس ٠-١٠٠.

        Args:
            idea: dict with keys 'title', 'content', 'content_ar', etc.
            domain: creative domain string (e.g. 'slogan', 'product_idea')

        Returns:
            NoveltyScore with overall, uniqueness, surprise, and transformative scores
        """
        if not self._enabled:
            return NoveltyScore(
                overall_score=0.0,
                uniqueness=0.0,
                surprise=0.0,
                transformative_potential=0.0,
                domain=domain,
                explanation="NoveltyScorer is disabled. Set MAMOUN_NOVELTY_SCORER_ENABLED=true.",
                explanation_ar="مُقيّم الجدة معطّل. اضبط MAMOUN_NOVELTY_SCORER_ENABLED=true.",
            )

        # Build combined text for analysis
        # بناء النص المركب للتحليل
        title = idea.get("title", "")
        content = idea.get("content", "")
        content_ar = idea.get("content_ar", "")
        combined = f"{title} {content} {content_ar}".strip()

        # Compute individual scores
        # حساب الدرجات الفردية
        uniqueness = self._compute_uniqueness(combined, domain)
        surprise = self._compute_surprise(combined, domain)
        transformative = self._compute_transformative_potential(combined, domain)

        # Weighted overall score
        # الدرجة الإجمالية الموزونة
        overall = (
            uniqueness * self.UNIQUENESS_WEIGHT +
            surprise * self.SURPRISE_WEIGHT +
            transformative * self.TRANSFORMATIVE_WEIGHT
        )

        # Apply cliché penalty
        # تطبيق عقوبة الكليشيهات
        cliche_report = self.detect_cliches(idea, domain)
        overall -= cliche_report.penalty_score
        overall = max(0.0, min(100.0, overall))

        # Generate explanations
        # توليد التفسيرات
        is_novel = overall >= self.NOVELTY_THRESHOLD
        explanation, explanation_ar = self._generate_explanation(
            overall, uniqueness, surprise, transformative, cliche_report, is_novel
        )

        score = NoveltyScore(
            overall_score=round(overall, 2),
            uniqueness=round(uniqueness, 2),
            surprise=round(surprise, 2),
            transformative_potential=round(transformative, 2),
            domain=domain,
            is_novel=is_novel,
            explanation=explanation,
            explanation_ar=explanation_ar,
        )

        # Track in history
        # تتبع في السجل
        self._scoring_history.append({
            "score_id": f"ns_{uuid.uuid4().hex[:8]}",
            "domain": domain,
            "overall_score": overall,
            "uniqueness": uniqueness,
            "surprise": surprise,
            "transformative_potential": transformative,
            "is_novel": is_novel,
            "scored_at": time.time(),
        })
        if len(self._scoring_history) > self._max_history:
            self._scoring_history = self._scoring_history[-self._max_history:]

        return score

    def compare_with_reference(self, idea: dict, domain: str) -> ReferenceComparison:
        """
        Compare an idea against the reference base for the given domain.
        مقارنة فكرة مع قاعدة المراجع في المجال المحدد.
        """
        combined = f"{idea.get('title', '')} {idea.get('content', '')} {idea.get('content_ar', '')}".strip()
        idea_fp = self._fingerprint(combined)

        refs = self._reference_base.get(domain, [])
        if not refs:
            return ReferenceComparison(
                closest_matches=[],
                min_distance=1.0,
                avg_distance=1.0,
                percentile_rank=95.0,  # No refs → assume highly novel
            )

        distances = []
        closest = []
        for ref in refs:
            dist = self._fingerprint_distance(idea_fp, ref.get("fingerprint", ""))
            distances.append(dist)
            if dist < 0.3:  # Close match threshold
                closest.append({
                    "ref_id": ref.get("ref_id", ""),
                    "content_preview": ref.get("content", "")[:100],
                    "distance": round(dist, 4),
                })

        min_dist = min(distances) if distances else 1.0
        avg_dist = sum(distances) / len(distances) if distances else 1.0

        # Percentile: higher = more novel than references
        # النسبة المئوية: أعلى = أجدد من المراجع
        novelty_scores_in_domain = [
            h["overall_score"] for h in self._scoring_history
            if h["domain"] == domain
        ]
        if novelty_scores_in_domain:
            idea_score = (1 - min_dist) * 100
            below = sum(1 for s in novelty_scores_in_domain if s < idea_score)
            percentile = (below / len(novelty_scores_in_domain)) * 100
        else:
            percentile = 50.0

        return ReferenceComparison(
            closest_matches=closest[:5],
            min_distance=round(min_dist, 4),
            avg_distance=round(avg_dist, 4),
            percentile_rank=round(percentile, 2),
        )

    def detect_cliches(self, idea: dict, domain: str) -> ClicheReport:
        """
        Detect clichés in an idea and generate improvement suggestions.
        اكتشاف الكليشيهات في فكرة وتوليد اقتراحات التحسين.
        """
        domain_data = DOMAIN_CLICHE_DB.get(domain, {})
        cliches = domain_data.get("cliches", [])
        alternatives = domain_data.get("alternatives", [])

        combined = f"{idea.get('title', '')} {idea.get('content', '')} {idea.get('content_ar', '')}".strip()

        found = []
        for cliche in cliches:
            if cliche in combined:
                found.append(cliche)

        # Penalty: each cliché reduces score by 8 points
        # العقوبة: كل كليشيه يخفض الدرجة ٨ نقاط
        penalty = len(found) * 8.0

        # Generate suggestions
        # توليد الاقتراحات
        suggestions = []
        if found:
            # Pick 2-3 random alternatives
            num_suggestions = min(len(alternatives), 3)
            suggestions = random.sample(alternatives, num_suggestions) if alternatives else []
            suggestions.append("حاول استخدام الاستعارة أو الجناس بدل العبارات المألوفة")

        return ClicheReport(
            cliches_found=found,
            penalty_score=penalty,
            suggestions=suggestions,
        )

    def get_novelty_trends(self, domain: str = None) -> dict:
        """
        Get novelty scoring trends over time.
        الحصول على اتجاهات تسجيل الجدة عبر الزمن.
        """
        if domain:
            filtered = [h for h in self._scoring_history if h["domain"] == domain]
        else:
            filtered = list(self._scoring_history)

        if not filtered:
            return {
                "total_scores": 0,
                "avg_overall": 0.0,
                "avg_uniqueness": 0.0,
                "avg_surprise": 0.0,
                "avg_transformative": 0.0,
                "novel_rate": 0.0,
                "trend_direction": "neutral",
                "domain": domain,
            }

        avg_overall = sum(h["overall_score"] for h in filtered) / len(filtered)
        avg_uniqueness = sum(h["uniqueness"] for h in filtered) / len(filtered)
        avg_surprise = sum(h["surprise"] for h in filtered) / len(filtered)
        avg_transformative = sum(h["transformative_potential"] for h in filtered) / len(filtered)
        novel_count = sum(1 for h in filtered if h.get("is_novel"))
        novel_rate = (novel_count / len(filtered)) * 100

        # Determine trend direction from recent scores
        # تحديد اتجاه الاتجاه من الدرجات الأخيرة
        trend = "neutral"
        if len(filtered) >= 5:
            recent = [h["overall_score"] for h in filtered[-5:]]
            older = [h["overall_score"] for h in filtered[-10:-5]] if len(filtered) >= 10 else recent
            avg_recent = sum(recent) / len(recent)
            avg_older = sum(older) / len(older)
            diff = avg_recent - avg_older
            if diff > 3:
                trend = "improving"
            elif diff < -3:
                trend = "declining"

        return {
            "total_scores": len(filtered),
            "avg_overall": round(avg_overall, 2),
            "avg_uniqueness": round(avg_uniqueness, 2),
            "avg_surprise": round(avg_surprise, 2),
            "avg_transformative": round(avg_transformative, 2),
            "novel_rate": round(novel_rate, 2),
            "trend_direction": trend,
            "domain": domain,
        }

    def add_reference(self, idea: dict, domain: str) -> str:
        """
        Add an idea to the reference base for future comparisons.
        إضافة فكرة إلى قاعدة المراجع للمقارنات المستقبلية.

        Returns the reference ID.
        """
        ref_id = f"ref_{uuid.uuid4().hex[:8]}"
        combined = f"{idea.get('title', '')} {idea.get('content', '')} {idea.get('content_ar', '')}".strip()
        fp = self._fingerprint(combined)

        if domain not in self._reference_base:
            self._reference_base[domain] = []

        self._reference_base[domain].append({
            "ref_id": ref_id,
            "domain": domain,
            "content": combined[:500],
            "fingerprint": fp,
            "added_at": time.time(),
        })

        return ref_id

    # =========================================================================
    # Internal: Scoring Components — مكونات التسجيل الداخلية
    # =========================================================================

    def _compute_uniqueness(self, text: str, domain: str) -> float:
        """
        Compute uniqueness: how different from known ideas in the reference base.
        حساب التفرّد: مدى الاختلاف عن الأفكار المعروفة في قاعدة المراجع.
        """
        fp = self._fingerprint(text)
        refs = self._reference_base.get(domain, [])

        if not refs:
            # No references yet → assume relatively unique with some randomness
            # لا مراجع بعد → نفترض تفرّداً نسبياً مع بعض العشوائية
            return 70.0 + random.uniform(-5, 10)

        # Compute distance to all references
        # حساب المسافة لجميع المراجع
        distances = [self._fingerprint_distance(fp, r.get("fingerprint", "")) for r in refs]

        # Uniqueness is based on minimum distance (closest match)
        # التفرّد مبني على أقل مسافة (أقرب تطابق)
        min_dist = min(distances)
        uniqueness = min_dist * 100  # Distance 0 = not unique, 1 = fully unique

        return max(0.0, min(100.0, uniqueness + random.uniform(-3, 3)))

    def _compute_surprise(self, text: str, domain: str) -> float:
        """
        Compute surprise: how unexpected the combination of concepts is.
        حساب المفاجأة: مدى عدم توقع تركيبة المفاهيم.
        """
        # Heuristic: count the number of distinct concept transitions
        # استدلال: عدّ عدد الانتقالات المفاهيمية المختلفة
        words = text.split()
        if len(words) < 3:
            return 30.0

        # Measure vocabulary diversity (type-token ratio)
        # قياس تنوع المفردات (نسبة النوع إلى الرمز)
        unique_words = set(w.lower() for w in words if len(w) > 2)
        ttr = len(unique_words) / max(len(words), 1)

        # Concept density: ratio of "bridge" markers
        # كثافة المفاهيم: نسبة علامات "الجسر"
        bridge_markers = ["دمج", "تركيب", "+","↔", "مع", "التقاء", "إلهام", "استعارة"]
        bridge_count = sum(1 for m in bridge_markers if m in text)
        bridge_density = min(bridge_count / max(len(words) / 20, 1), 1.0)

        surprise = (ttr * 50) + (bridge_density * 50)
        return max(0.0, min(100.0, surprise + random.uniform(-5, 5)))

    def _compute_transformative_potential(self, text: str, domain: str) -> float:
        """
        Compute transformative potential: how likely the idea is to inspire
        further innovation and be built upon.
        حساب الإمكانات التحويلية: مدى احتمالية إلهام الفكرة لمزيد من الابتكار.
        """
        # Heuristic: ideas that combine multiple domains have higher transformative potential
        # استدلال: الأفكار التي تجمع مجالات متعددة لها إمكانات تحويلية أعلى

        domain_keywords = {
            "nature": ["طبيعة", "نهر", "شجرة", "نمو", "تدفق"],
            "architecture": ["بناء", "قوس", "جسر", "برج", "تصميم"],
            "music": ["إيقاع", "تناغم", "صمت", "ارتجال"],
            "mathematics": ["لولب", "تناظر", "كسيري", "ذهبي"],
            "technology": ["ترميز", "حلقة", "واجهة", "تكرار"],
            "biology": ["تعايش", "تحول", "مناعة", "سلوك"],
        }

        domains_touched = 0
        for dk, keywords in domain_keywords.items():
            if any(kw in text for kw in keywords):
                domains_touched += 1

        # More domains touched = higher transformative potential
        # المزيد من المجالات الملموسة = إمكانات تحويلية أعلى
        base_score = min(domains_touched * 20, 80)

        # Check for abstraction markers (which indicate generalizability)
        # التحقق من علامات التجريد (التي تشير إلى القابلية للتعميم)
        abstraction_markers = ["مبدأ", "نمط", "قاعدة", "جوهر", "أساس"]
        abstraction_count = sum(1 for m in abstraction_markers if m in text)
        abstraction_bonus = min(abstraction_count * 8, 20)

        return max(0.0, min(100.0, base_score + abstraction_bonus + random.uniform(-3, 3)))

    # =========================================================================
    # Internal: Fingerprinting — البصمات
    # =========================================================================

    def _fingerprint(self, text: str) -> str:
        """
        Compute a structural fingerprint for similarity comparison.
        حساب بصمة هيكلية لمقارنة التشابه.
        """
        # N-gram based fingerprint
        # بصمة مبنية على المتتاليات
        normalized = text.lower().strip()
        if not normalized:
            return hashlib.md5(b"empty").hexdigest()

        # Character trigram frequencies
        # ترددات الثلاثيات الحرفية
        trigrams = {}
        for i in range(len(normalized) - 2):
            tg = normalized[i:i+3]
            if tg.isalpha() or any(c.isalpha() for c in tg):
                trigrams[tg] = trigrams.get(tg, 0) + 1

        if not trigrams:
            return hashlib.md5(normalized.encode()).hexdigest()

        # Sort and hash
        sorted_tg = sorted(trigrams.items(), key=lambda x: x[0])
        fp_str = "|".join(f"{k}:{v}" for k, v in sorted_tg)
        return hashlib.md5(fp_str.encode()).hexdigest()

    def _fingerprint_distance(self, fp_a: str, fp_b: str) -> float:
        """
        Compute distance between two fingerprints (0 = identical, 1 = completely different).
        حساب المسافة بين بصمتين (٠ = متطابقتان، ١ = مختلفتان كلياً).
        """
        if fp_a == fp_b:
            return 0.0

        # Hamming-based distance on hex representations
        # مسافة مبنية على هامنغ على التمثيلات السداسية
        min_len = min(len(fp_a), len(fp_b))
        if min_len == 0:
            return 1.0

        matching = sum(1 for a, b in zip(fp_a, fp_b) if a == b)
        similarity = matching / min_len
        return 1.0 - similarity

    # =========================================================================
    # Internal: Explanation — التفسير
    # =========================================================================

    def _generate_explanation(
        self,
        overall: float,
        uniqueness: float,
        surprise: float,
        transformative: float,
        cliche_report: ClicheReport,
        is_novel: bool,
    ) -> tuple:
        """Generate bilingual explanation for the novelty score — توليد تفسير ثنائي اللغة"""
        parts_en = []
        parts_ar = []

        if is_novel:
            parts_en.append(f"Novel idea (score: {overall:.1f}/100).")
            parts_ar.append(f"فكرة أصيلة (الدرجة: {overall:.1f}/١٠٠).")
        else:
            parts_en.append(f"Insufficient novelty (score: {overall:.1f}/100).")
            parts_ar.append(f"جدة غير كافية (الدرجة: {overall:.1f}/١٠٠).")

        if uniqueness > 70:
            parts_en.append("Highly unique compared to known ideas.")
            parts_ar.append("عالية التفرّد مقارنة بالأفكار المعروفة.")
        elif uniqueness < 40:
            parts_en.append("Similar to existing ideas in the reference base.")
            parts_ar.append("مشابهة للأفكار الموجودة في قاعدة المراجع.")

        if surprise > 70:
            parts_en.append("Unexpected concept combination.")
            parts_ar.append("تركيبة مفاهيم غير متوقعة.")
        elif surprise < 40:
            parts_en.append("Predictable concept combinations.")
            parts_ar.append("تركيبات مفاهيم متوقعة.")

        if transformative > 70:
            parts_en.append("High transformative potential — could inspire new directions.")
            parts_ar.append("إمكانات تحويلية عالية — قد تلهّم اتجاهات جديدة.")

        if cliche_report.cliches_found:
            cliche_str = ", ".join(cliche_report.cliches_found[:3])
            parts_en.append(f"Clichés detected: {cliche_str}")
            parts_ar.append(f"كليشيهات مكتشفة: {cliche_str}")

        return " ".join(parts_en), " ".join(parts_ar)

    # =========================================================================
    # Status & Lifecycle — الحالة ودورة الحياة
    # =========================================================================

    def get_status(self) -> dict:
        """
        Return the current status of the Novelty Scorer.
        إرجاع الحالة الحالية لمُقيّم الجدة.
        """
        return {
            "module": "NoveltyScorer",
            "enabled": self._enabled,
            "feature_flag": "MAMOUN_NOVELTY_SCORER_ENABLED",
            "reference_base_domains": list(self._reference_base.keys()),
            "reference_counts": {d: len(refs) for d, refs in self._reference_base.items()},
            "scoring_history_size": len(self._scoring_history),
            "novelty_threshold": self.NOVELTY_THRESHOLD,
            "weights": {
                "uniqueness": self.UNIQUENESS_WEIGHT,
                "surprise": self.SURPRISE_WEIGHT,
                "transformative": self.TRANSFORMATIVE_WEIGHT,
            },
            "domains_with_cliche_detection": list(DOMAIN_CLICHE_DB.keys()),
            "initialized": self._initialized,
        }

    def shutdown(self):
        """
        Gracefully shut down the Novelty Scorer.
        إيقاف تشغيل مُقيّم الجدة بأمان.
        """
        self._reference_base.clear()
        self._scoring_history.clear()
        self._initialized = False
