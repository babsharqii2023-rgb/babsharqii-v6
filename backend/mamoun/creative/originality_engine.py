"""
BABSHARQII v40.0 — Originality Engine
محرك الإبداع الأصيل

Generates truly original creative outputs through novel synthesis — not just
recombination but emergent ideas born from associative creativity, mutation,
and cross-domain inspiration. Inspired by DGM-H and associative creativity models.

Generates: designs, product ideas, marketing campaigns, logos, slogans, stories,
and code architectures.
"""

import os
import uuid
import time
import random
import math
import hashlib
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from pathlib import Path


# =============================================================================
# Feature Flag
# =============================================================================

MAMOUN_ORIGINALITY_ENGINE = os.environ.get("MAMOUN_ORIGINALITY_ENGINE_ENABLED", "false") == "true"


# =============================================================================
# Enums — التعدادات
# =============================================================================

class CreativeDomain(Enum):
    """Creative domains — مجالات الإبداع"""
    DESIGN = "design"
    PRODUCT_IDEA = "product_idea"
    MARKETING_CAMPAIGN = "marketing_campaign"
    SLOGAN = "slogan"
    LOGO_CONCEPT = "logo_concept"
    STORY = "story"
    CODE_ARCHITECTURE = "code_architecture"


class CreativeMutation(Enum):
    """Creative mutation types — أنواع الطفرات الإبداعية"""
    INVERSION = "inversion"           # قلب الفكرة رأساً على عقب
    EXAGGERATION = "exaggeration"     # المبالغة في سمة معينة
    COMBINATION = "combination"       # دمج فكرتين مختلفتين
    ANALOGY = "analogy"               # القياس من مجال آخر
    ABSTRACTION = "abstraction"       # التجريد إلى المبدأ الجوهري
    ARABIC_RHETORIC = "arabic_rhetoric"  # استخدام البلاغة العربية


# =============================================================================
# Data Classes — فئات البيانات
# =============================================================================

@dataclass
class CreativeSeed:
    """
    The seed for a creative generation process.
    البذرة الإبداعية — المدخلات الأساسية لتوليد فكرة أصيلة.
    """
    seed_id: str = ""
    domain: CreativeDomain = CreativeDomain.DESIGN
    description: str = ""
    description_ar: str = ""
    constraints: list = field(default_factory=list)
    target_audience: str = ""
    style_preferences: dict = field(default_factory=dict)
    inspiration_sources: list = field(default_factory=list)

    def __post_init__(self):
        if not self.seed_id:
            self.seed_id = f"seed_{uuid.uuid4().hex[:12]}"

    def to_dict(self) -> dict:
        return {
            "seed_id": self.seed_id,
            "domain": self.domain.value,
            "description": self.description,
            "description_ar": self.description_ar,
            "constraints": self.constraints,
            "target_audience": self.target_audience,
            "style_preferences": self.style_preferences,
            "inspiration_sources": self.inspiration_sources,
        }


@dataclass
class CreativeOutput:
    """
    A generated creative output with scoring and provenance.
    المخرجات الإبداعية — الفكرة المولدة مع تقييمها ومصادرها.
    """
    output_id: str = ""
    seed_id: str = ""
    domain: CreativeDomain = CreativeDomain.DESIGN
    title: str = ""
    title_ar: str = ""
    content: str = ""
    content_ar: str = ""
    novelty_score: float = 0.0
    feasibility_score: float = 0.0
    relevance_score: float = 0.0
    mutations_applied: list = field(default_factory=list)
    inspiration_sources: list = field(default_factory=list)
    created_at: float = 0.0

    def __post_init__(self):
        if not self.output_id:
            self.output_id = f"out_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return {
            "output_id": self.output_id,
            "seed_id": self.seed_id,
            "domain": self.domain.value,
            "title": self.title,
            "title_ar": self.title_ar,
            "content": self.content,
            "content_ar": self.content_ar,
            "novelty_score": round(self.novelty_score, 2),
            "feasibility_score": round(self.feasibility_score, 2),
            "relevance_score": round(self.relevance_score, 2),
            "mutations_applied": self.mutations_applied,
            "inspiration_sources": self.inspiration_sources,
            "created_at": self.created_at,
            "created_at_iso": datetime.fromtimestamp(self.created_at).isoformat() if self.created_at else None,
        }


# =============================================================================
# Knowledge Bases — قواعد المعرفة
# =============================================================================

# Arabic rhetorical devices — الأدوات البلاغية العربية
ARABIC_RHETORIC_DEVICES = {
    "jinas": {
        "name_en": "Paronomasia (Jinas)",
        "name_ar": "الجناس",
        "description": "Using words with similar sounds but different meanings for wordplay",
        "description_ar": "استخدام كلمات متشابهة اللفظ مختلفة المعنى",
        "examples": [
            "وافق شنّ طبقه — طبق: سقف / طبق: وافق",
            "يوم الفصل كان موقعه — وقع: حصل / وقع: مكان",
        ],
    },
    "saj": {
        "name_en": "Rhymed Prose (Saj')",
        "name_ar": "السجع",
        "description": "Rhythmic prose with end-rhyme for memorability",
        "description_ar": "نثر موزون مقفّى يسهّل الحفظ",
        "examples": [
            "في العلم سمو، وفي العمل نمو",
            "الصبر مفتاح الفرج، والجهد سبيل الفرح",
        ],
    },
    "tibaq": {
        "name_en": "Antithesis (Tibaq)",
        "name_ar": "الطباق",
        "description": "Contrasting opposite concepts for emphasis",
        "description_ar": "مقابلة المتضادات للتأكيد",
        "examples": [
            "البداية من النهاية، والنور من الظلام",
            "الصمت أبلغ من الكلام",
        ],
    },
    "istiara": {
        "name_en": "Metaphor (Isti'ara)",
        "name_ar": "الاستعارة",
        "description": "Borrowing imagery from one domain for another",
        "description_ar": "استعارة صورة من مجال لتوصيف مجال آخر",
        "examples": [
            "فجر الأمل يشرق من قلب اليأس",
            "بحر المعرفة لا ساحل له",
        ],
    },
}

# Cross-domain concept pools for associative creativity
# مجالات المفاهيم المتقاطعة للإبداع الترابطي
CROSS_DOMAIN_CONCEPTS = {
    "nature": ["تدفق النهر", "انعكاس الضوء", "نمو الشجرة", "تنفس المحيط", "دورة الفصول"],
    "architecture": ["قوس النصر", "الجسر المعلّق", "البرج الحلزوني", "القبابة الزجاجية", "المتاهة"],
    "music": ["الإيقاع المتنامي", "التناغم المضاد", "الصمت الموسيقي", "الارتجال", "الصدى"],
    "mathematics": ["اللولب الذهبي", "الكسيرات", "التناظر الخفي", "الانهيار المفاجئ", "التكرار الذاتي"],
    "cooking": ["المزج المتوازن", "التحول بالحرارة", "التخمير الإبداعي", "الطبقات المتداخلة", "البهارات"],
    "astronomy": ["المدار البيضاوي", "الثقب الأسود", "السديم الملون", "الجاذبية الخفية", "النجم النابض"],
    "biology": ["التعايش التكافلي", "التحول الكامل", "الحلقة المفقودة", "المناعة المكتسبة", "السلوك الجماعي"],
    "technology": ["الترميز العكسي", "الحلقة الراجعة", "الواجهة الشفافة", "التكرار التطوري", "النقطة المفردة"],
}

# Domain-specific clichés to avoid — الكليشيهات التي يجب تجنبها
DOMAIN_CLICHES = {
    CreativeDomain.SLOGAN: [
        "نحن الأفضل", "الجودة أولاً", "التميز بلا حدود",
        "الابداع بلا حدود", "مستقبل أفضل", "شراكة النجاح",
    ],
    CreativeDomain.MARKETING_CAMPAIGN: [
        "اشترِ واحد واحصل على الثاني مجاناً", "عرض لفترة محدودة",
        "الأكثر مبيعاً", "لا تفوّت الفرصة", "الأسعار التي لا تُقاوم",
    ],
    CreativeDomain.PRODUCT_IDEA: [
        "تطبيق يجمع كل شيء", "النسخة العربية من",
        "منصة ذكية باستخدام الذكاء الاصطناعي", "حل شامل متكامل",
    ],
    CreativeDomain.LOGO_CONCEPT: [
        "حرف أول داخل دائرة", "سهم للأعلى", "كرة أرضية",
        "ورقة خضراء", "شخص يمسك شيئاً",
    ],
    CreativeDomain.STORY: [
        "كان يا ما كان", "وفي النهاية عاشوا بسعادة",
        "البطل المختار", "الرحلة الملحمية",
    ],
}


# =============================================================================
# OriginalityEngine — محرك الإبداع الأصيل
# =============================================================================

class OriginalityEngine:
    """
    Engine for generating truly original creative outputs.

    Process — العملية الإبداعية:
    1. Seed: Define the creative domain and constraints
    2. Association: Find unexpected connections between distant concepts
    3. Mutation: Apply creative mutations (inversion, exaggeration, etc.)
    4. Synthesis: Combine mutated elements into a coherent creative output
    5. Evaluation: Score for novelty, feasibility, and relevance

    Maintains a "creative memory" of past outputs to avoid repetition.
    Uses cross-domain inspiration and Arabic rhetorical devices.
    """

    def __init__(
        self,
        db_path: str = "",
        novelty_weight: float = 0.4,
        feasibility_weight: float = 0.3,
        relevance_weight: float = 0.3,
    ):
        self._enabled = MAMOUN_ORIGINALITY_ENGINE
        self._novelty_weight = novelty_weight
        self._feasibility_weight = feasibility_weight
        self._relevance_weight = relevance_weight

        # Creative memory — الذاكرة الإبداعية
        self._creative_history: list[CreativeOutput] = []
        self._max_history = 500

        # Concept fingerprint store for deduplication
        self._fingerprint_store: dict[str, float] = {}

        # SQLite for persistent creative memory
        if not db_path:
            db_path = str(Path(__file__).parent.parent.parent / "data" / "creative_memory.db")
        self._db_path = db_path

        self._initialized = False
        self._novelty_scorer = None  # Lazy init to avoid circular imports

    def _get_novelty_scorer(self):
        """Lazy-load the novelty scorer — تحميل كسول للمُقيّم"""
        if self._novelty_scorer is None:
            from mamoun.creative.novelty_scorer import NoveltyScorer
            self._novelty_scorer = NoveltyScorer(db_path=self._db_path)
        return self._novelty_scorer

    async def _initialize(self):
        """Initialize SQLite tables — تهيئة جداول قاعدة البيانات"""
        if self._initialized:
            return
        try:
            import aiosqlite
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS creative_outputs (
                        output_id TEXT PRIMARY KEY,
                        seed_id TEXT NOT NULL,
                        domain TEXT NOT NULL,
                        title TEXT DEFAULT '',
                        title_ar TEXT DEFAULT '',
                        content TEXT DEFAULT '',
                        content_ar TEXT DEFAULT '',
                        novelty_score REAL DEFAULT 0.0,
                        feasibility_score REAL DEFAULT 0.0,
                        relevance_score REAL DEFAULT 0.0,
                        mutations_applied TEXT DEFAULT '[]',
                        inspiration_sources TEXT DEFAULT '[]',
                        fingerprint TEXT DEFAULT '',
                        created_at REAL DEFAULT 0.0
                    )
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_creative_outputs_domain
                    ON creative_outputs(domain)
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_creative_outputs_novelty
                    ON creative_outputs(novelty_score DESC)
                """)
                await db.commit()
        except ImportError:
            pass  # aiosqlite not available; fall back to in-memory
        self._initialized = True

    # =========================================================================
    # Core Generation — التوليد الأساسي
    # =========================================================================

    def generate(self, seed: CreativeSeed) -> CreativeOutput:
        """
        Generate a single creative output from a seed.
        توليد مخرج إبداعي واحد من بذرة.

        Process:
        1. Seed → 2. Association → 3. Mutation → 4. Synthesis → 5. Evaluation
        """
        if not self._enabled:
            return self._disabled_output(seed)

        # Step 1: Seed is already defined by the caller
        # الخطوة ١: البذرة مُعرَّفة بالفعل من المُستدعي

        # Step 2: Association — find unexpected connections
        # الخطوة ٢: الترابط — إيجاد روابط غير متوقعة
        associations = self._find_associations(seed)

        # Step 3: Mutation — apply creative mutations
        # الخطوة ٣: الطفرة — تطبيق الطفرات الإبداعية
        mutations_applied = []
        mutated_concepts = list(associations)
        mutation_types = self._select_mutations(seed)
        for mt in mutation_types:
            mutated_concepts = self._apply_mutation(mutated_concepts, mt, seed)
            mutations_applied.append(mt.value)

        # Step 4: Synthesis — combine into coherent output
        # الخطوة ٤: التركيب — الدمج في مخرج متسق
        title, title_ar, content, content_ar, inspirations = self._synthesize(
            seed, mutated_concepts, mutations_applied
        )

        # Step 5: Evaluation — score the output
        # الخطوة ٥: التقييم — تسجيل المخرجات
        novelty = self._evaluate_novelty(title + content, seed.domain)
        feasibility = self._evaluate_feasibility(content, seed)
        relevance = self._evaluate_relevance(content, seed)

        output = CreativeOutput(
            seed_id=seed.seed_id,
            domain=seed.domain,
            title=title,
            title_ar=title_ar,
            content=content,
            content_ar=content_ar,
            novelty_score=novelty,
            feasibility_score=feasibility,
            relevance_score=relevance,
            mutations_applied=mutations_applied,
            inspiration_sources=inspirations,
        )

        # Store in creative memory
        self._store_output(output)
        return output

    def generate_variants(self, seed: CreativeSeed, count: int = 3) -> list:
        """
        Generate multiple creative variants from a single seed.
        توليد عدة متغيرات إبداعية من بذرة واحدة.
        """
        if not self._enabled:
            return [self._disabled_output(seed) for _ in range(count)]

        variants = []
        for i in range(count):
            # Vary the random seed slightly for each variant
            # تنويع البذرة العشوائية قليلاً لكل متغير
            variant_seed = CreativeSeed(
                seed_id=f"{seed.seed_id}_v{i+1}",
                domain=seed.domain,
                description=seed.description,
                description_ar=seed.description_ar,
                constraints=seed.constraints.copy(),
                target_audience=seed.target_audience,
                style_preferences=dict(seed.style_preferences),
                inspiration_sources=seed.inspiration_sources.copy(),
            )
            variant = self.generate(variant_seed)
            variants.append(variant)
        return variants

    def mutate_idea(self, idea: CreativeOutput, mutation_type: str = None) -> CreativeOutput:
        """
        Apply a specific mutation to an existing creative output.
        تطبيق طفرة محددة على مخرج إبداعي موجود.

        Args:
            idea: The existing creative output to mutate
            mutation_type: Specific mutation type name, or None for random
        """
        if not self._enabled:
            return idea

        # Resolve mutation type
        # تحديد نوع الطفرة
        if mutation_type:
            mt = CreativeMutation(mutation_type)
        else:
            mt = random.choice(list(CreativeMutation))

        # Create a synthetic seed from the existing idea
        # إنشاء بذرة اصطناعية من الفكرة الموجودة
        synthetic_seed = CreativeSeed(
            seed_id=f"{idea.seed_id}_mut",
            domain=idea.domain,
            description=idea.content[:200],
            description_ar=idea.content_ar[:200] if idea.content_ar else "",
            constraints=[],
            target_audience="",
        )

        # Apply the mutation to the existing content
        # تطبيق الطفرة على المحتوى الموجود
        concepts = [idea.title, idea.content]
        mutated = self._apply_mutation(concepts, mt, synthetic_seed)

        # Synthesize new output
        # تركيب مخرج جديد
        title, title_ar, content, content_ar, inspirations = self._synthesize(
            synthetic_seed, mutated, [mt.value]
        )

        # Inherit some scoring from parent, boost novelty
        # وراثة بعض التقييم من الأصل، مع تعزيز الجدة
        novelty_boost = min(100, idea.novelty_score + random.uniform(5, 15))

        new_output = CreativeOutput(
            seed_id=synthetic_seed.seed_id,
            domain=idea.domain,
            title=title,
            title_ar=title_ar,
            content=content,
            content_ar=content_ar,
            novelty_score=novelty_boost,
            feasibility_score=idea.feasibility_score,
            relevance_score=idea.relevance_score,
            mutations_applied=idea.mutations_applied + [mt.value],
            inspiration_sources=list(set(idea.inspiration_sources + inspirations)),
        )

        self._store_output(new_output)
        return new_output

    def cross_domain_inspiration(self, domain_a: str, domain_b: str) -> list:
        """
        Borrow ideas from two unrelated domains and find inspiration bridges.
        استعارة أفكار من مجالين غير مرتبطين وإيجاد جسور إلهام.

        Returns a list of inspiration dicts with concepts from both domains
        combined in novel ways.
        """
        concepts_a = CROSS_DOMAIN_CONCEPTS.get(domain_a, [])
        concepts_b = CROSS_DOMAIN_CONCEPTS.get(domain_b, [])

        if not concepts_a or not concepts_b:
            return []

        inspirations = []
        for ca in concepts_a:
            for cb in concepts_b:
                bridge = self._build_concept_bridge(ca, cb, domain_a, domain_b)
                if bridge:
                    inspirations.append(bridge)

        # Return top inspirations by surprise score
        # إرجاع أفضل الإلهامات حسب درجة المفاجأة
        inspirations.sort(key=lambda x: x.get("surprise_score", 0), reverse=True)
        return inspirations[:10]

    def get_creative_history(self, domain: str = None, limit: int = 20) -> list:
        """
        Retrieve past creative outputs, optionally filtered by domain.
        استرجاع المخرجات الإبداعية السابقة، مع تصفية اختيارية حسب المجال.
        """
        if domain:
            domain_enum = CreativeDomain(domain) if isinstance(domain, str) else domain
            filtered = [o for o in self._creative_history if o.domain == domain_enum]
        else:
            filtered = list(self._creative_history)

        # Sort by novelty score descending
        # ترتيب حسب درجة الجدة تنازلياً
        filtered.sort(key=lambda o: o.novelty_score, reverse=True)
        return [o.to_dict() for o in filtered[:limit]]

    # =========================================================================
    # Internal: Association — الترابط
    # =========================================================================

    def _find_associations(self, seed: CreativeSeed) -> list:
        """
        Find unexpected connections between the seed concepts and distant domains.
        إيجاد روابط غير متوقعة بين مفاهيم البذرة والمجالات البعيدة.
        """
        associations = []

        # Add seed description as base concept
        # إضافة وصف البذرة كمفهوم أساسي
        associations.append(seed.description)
        if seed.description_ar:
            associations.append(seed.description_ar)

        # Pick random distant domains for cross-pollination
        # اختيار مجالات بعيدة عشوائياً للتلقيح المتقاطع
        domain_keys = list(CROSS_DOMAIN_CONCEPTS.keys())
        num_domains = random.randint(2, 4)
        selected_domains = random.sample(domain_keys, min(num_domains, len(domain_keys)))

        for dk in selected_domains:
            concepts = CROSS_DOMAIN_CONCEPTS[dk]
            pick = random.choice(concepts)
            associations.append(pick)

        # Add inspiration sources if provided
        # إضافة مصادر الإلهام إن وُجدت
        for source in seed.inspiration_sources:
            associations.append(source)

        # Arabic rhetoric device for slogans and marketing
        # أداة بلاغية عربية للشعارات والتسويق
        if seed.domain in (CreativeDomain.SLOGAN, CreativeDomain.MARKETING_CAMPAIGN):
            device_key = random.choice(list(ARABIC_RHETORIC_DEVICES.keys()))
            device = ARABIC_RHETORIC_DEVICES[device_key]
            associations.append(f"ARABIC_RHETORIC:{device['name_ar']}")

        return associations

    # =========================================================================
    # Internal: Mutation — الطفرة الإبداعية
    # =========================================================================

    def _select_mutations(self, seed: CreativeSeed) -> list:
        """Select mutation types to apply based on the domain — اختيار أنواع الطفرات"""
        mutations = []

        # Every domain gets at least one structural mutation
        # كل مجال يحصل على طفرة هيكلية واحدة على الأقل
        structural = random.choice([
            CreativeMutation.COMBINATION,
            CreativeMutation.ANALOGY,
            CreativeMutation.ABSTRACTION,
        ])
        mutations.append(structural)

        # Domain-specific mutation additions
        # إضافة طفرات خاصة بكل مجال
        if seed.domain in (CreativeDomain.SLOGAN, CreativeDomain.MARKETING_CAMPAIGN):
            mutations.append(CreativeMutation.ARABIC_RHETORIC)

        if seed.domain == CreativeDomain.STORY:
            mutations.append(random.choice([
                CreativeMutation.INVERSION,
                CreativeMutation.EXAGGERATION,
            ]))

        if seed.domain == CreativeDomain.PRODUCT_IDEA:
            mutations.append(CreativeMutation.COMBINATION)

        if seed.domain == CreativeDomain.CODE_ARCHITECTURE:
            mutations.append(CreativeMutation.ABSTRACTION)

        # Random bonus mutation
        # طفرة إضافية عشوائية
        if random.random() < 0.4:
            mutations.append(random.choice(list(CreativeMutation)))

        return mutations

    def _apply_mutation(self, concepts: list, mutation: CreativeMutation, seed: CreativeSeed) -> list:
        """
        Apply a specific creative mutation to the concept list.
        تطبيق طفرة إبداعية محددة على قائمة المفاهيم.
        """
        if not concepts:
            return concepts

        result = list(concepts)

        if mutation == CreativeMutation.INVERSION:
            # قلب الفكرة — reverse the core assumption
            inverted = self._invert_concepts(result)
            result.extend(inverted)

        elif mutation == CreativeMutation.EXAGGERATION:
            # المبالغة — push a concept to its extreme
            idx = random.randint(0, len(result) - 1)
            exaggerated = self._exaggerate_concept(result[idx])
            result.append(exaggerated)

        elif mutation == CreativeMutation.COMBINATION:
            # الدمج — combine two concepts into one
            if len(result) >= 2:
                i, j = random.sample(range(len(result)), 2)
                combined = self._combine_concepts(result[i], result[j])
                result.append(combined)

        elif mutation == CreativeMutation.ANALOGY:
            # القياس — draw an analogy from a random domain
            domain_keys = list(CROSS_DOMAIN_CONCEPTS.keys())
            dk = random.choice(domain_keys)
            analogy_source = random.choice(CROSS_DOMAIN_CONCEPTS[dk])
            analogy = f"ANALOGY:{analogy_source}↔{dk}"
            result.append(analogy)

        elif mutation == CreativeMutation.ABSTRACTION:
            # التجريد — extract the underlying principle
            idx = random.randint(0, len(result) - 1)
            abstracted = self._abstract_concept(result[idx])
            result.append(abstracted)

        elif mutation == CreativeMutation.ARABIC_RHETORIC:
            # البلاغة العربية — apply an Arabic rhetorical device
            device_key = random.choice(list(ARABIC_RHETORIC_DEVICES.keys()))
            device = ARABIC_RHETORIC_DEVICES[device_key]
            rhetoric_tag = f"RHETORIC:{device['name_ar']}({device['description_ar']})"
            result.append(rhetoric_tag)

        return result

    # =========================================================================
    # Internal: Mutation Helpers — مساعدات الطفرات
    # =========================================================================

    def _invert_concepts(self, concepts: list) -> list:
        """Invert key assumptions — قلب الافتراضات الأساسية"""
        inversions = []
        inversion_patterns = [
            "عكس: بدلاً من {c} → ماذا لو نقيض {c}؟",
            "نقيض: ليس {c} بل ضده",
        ]
        for c in concepts[:3]:  # Invert up to 3
            pattern = random.choice(inversion_patterns)
            inversions.append(pattern.format(c=c))
        return inversions

    def _exaggerate_concept(self, concept: str) -> str:
        """Push a concept to its extreme — دفع المفهوم إلى حده الأقصى"""
        exaggeration_templates = [
            "بالمبالغة: {c} × ١٠٠",
            "في الحد الأقصى: ماذا لو أصبح {c} لا محدود؟",
            "المبالغة: {c} بمستوى لم يُرَ من قبل",
        ]
        template = random.choice(exaggeration_templates)
        return template.format(c=concept)

    def _combine_concepts(self, concept_a: str, concept_b: str) -> str:
        """Combine two concepts — دمج مفهومين"""
        return f"دمج: [{concept_a}] + [{concept_b}] = توليف جديد"

    def _abstract_concept(self, concept: str) -> str:
        """Extract the underlying principle — استخلاص المبدأ الجوهري"""
        abstraction_templates = [
            "التجريد: المبدأ خلف «{c}» هو التحول عبر التفاعل",
            "المبدأ الجوهري لـ «{c}»: التوازن بين التناقضات",
            "جوهر «{c}»: من التعقيد ينبثق البساطة",
        ]
        template = random.choice(abstraction_templates)
        return template.format(c=concept)

    # =========================================================================
    # Internal: Synthesis — التركيب
    # =========================================================================

    def _synthesize(self, seed: CreativeSeed, concepts: list, mutations: list) -> tuple:
        """
        Synthesize mutated concepts into a coherent creative output.
        تركيب المفاهيم المتحولة في مخرج إبداعي متسق.

        Returns: (title, title_ar, content, content_ar, inspiration_sources)
        """
        domain = seed.domain
        description = seed.description or "فكرة إبداعية جديدة"
        description_ar = seed.description_ar or "فكرة إبداعية جديدة"

        # Extract non-rhetoric concepts for content building
        # استخلاص المفاهيم غير البلاغية لبناء المحتوى
        core_concepts = [c for c in concepts if not c.startswith(("RHETORIC:", "ANALOGY:", "عكس:", "نقيض:", "بالمبالغة:", "في الحد الأقصى:", "المبالغة:", "التجريد:", "المبدأ الجوهري", "جوهر", "دمج:"))]
        rhetoric_concepts = [c for c in concepts if c.startswith("RHETORIC:")]
        analogy_concepts = [c for c in concepts if c.startswith("ANALOGY:")]
        mutation_concepts = [c for c in concepts if any(c.startswith(p) for p in ("عكس:", "نقيض:", "بالمبالغة:", "في الحد الأقصى:", "المبالغة:", "التجريد:", "المبدأ الجوهري", "جوهر", "دمج:"))]

        inspiration_sources = []
        for ac in analogy_concepts:
            parts = ac.replace("ANALOGY:", "").split("↔")
            if len(parts) == 2:
                inspiration_sources.append(parts[1])

        # Build domain-specific output
        # بناء مخرج خاص بكل مجال
        if domain == CreativeDomain.SLOGAN:
            return self._synthesize_slogan(seed, core_concepts, rhetoric_concepts, mutation_concepts, inspiration_sources)
        elif domain == CreativeDomain.MARKETING_CAMPAIGN:
            return self._synthesize_campaign(seed, core_concepts, rhetoric_concepts, mutation_concepts, inspiration_sources)
        elif domain == CreativeDomain.PRODUCT_IDEA:
            return self._synthesize_product(seed, core_concepts, mutation_concepts, inspiration_sources)
        elif domain == CreativeDomain.LOGO_CONCEPT:
            return self._synthesize_logo(seed, core_concepts, mutation_concepts, inspiration_sources)
        elif domain == CreativeDomain.STORY:
            return self._synthesize_story(seed, core_concepts, mutation_concepts, inspiration_sources)
        elif domain == CreativeDomain.CODE_ARCHITECTURE:
            return self._synthesize_architecture(seed, core_concepts, mutation_concepts, inspiration_sources)
        else:
            return self._synthesize_design(seed, core_concepts, mutation_concepts, inspiration_sources)

    def _synthesize_slogan(self, seed, core, rhetoric, mutations, inspirations) -> tuple:
        """Synthesize a slogan — تركيب شعار"""
        # Extract rhetorical device for Arabic slogan
        # استخلاص الأداة البلاغية للشعار العربي
        rhetoric_name = "السجع"
        for rc in rhetoric:
            if "RHETORIC:" in rc:
                rhetoric_name = rc.split("(")[0].replace("RHETORIC:", "")
                break

        concept_words = [c.split()[-1] if c else "إبداع" for c in core[:2]]
        word_a = concept_words[0] if concept_words else "إبداع"
        word_b = concept_words[1] if len(concept_words) > 1 else "تميّز"

        title = f"Slogan Concept: {seed.description[:40]}"
        title_ar = f"مفهوم شعار: {seed.description_ar[:40] if seed.description_ar else seed.description[:40]}"

        # Generate Arabic slogans using rhetorical patterns
        # توليد شعارات عربية باستخدام أنماط بلاغية
        content = f"Slogan inspired by {rhetoric_name}, blending concepts: {', '.join(core[:3])}"
        content_ar = (
            f"شعار بأسلوب «{rhetoric_name}»:\n"
            f"  • في {word_a} نبني، ومن {word_b} نبدع\n"
            f"  • حيث {word_a} يلتقي {word_b}\n"
            f"  • من رحم {word_a} يُولد {word_b}"
        )

        if mutations:
            content_ar += f"\n  [طفرات: {', '.join(mutations)}]"

        return title, title_ar, content, content_ar, inspirations

    def _synthesize_campaign(self, seed, core, rhetoric, mutations, inspirations) -> tuple:
        """Synthesize a marketing campaign — تركيب حملة تسويقية"""
        title = f"Campaign: {seed.description[:50]}"
        title_ar = f"حملة: {seed.description_ar[:50] if seed.description_ar else seed.description[:50]}"

        phases = ["المرحلة الأولى: الإثارة والفضول", "المرحلة الثانية: الكشف والمشاركة", "المرحلة الثالثة: التحوّل والولاء"]
        core_str = " — ".join(core[:3])

        content = f"Multi-phase campaign inspired by: {core_str}"
        content_ar = (
            f"حملة تسويقية مبتكرة مستوحاة من: {core_str}\n\n"
            + "\n".join(f"  ◆ {p}" for p in phases)
            + f"\n\nالجمهور المستهدف: {seed.target_audience or 'الجمهور العام'}"
        )
        if mutations:
            content_ar += f"\nالطفرات المطبقة: {', '.join(mutations)}"

        return title, title_ar, content, content_ar, inspirations

    def _synthesize_product(self, seed, core, mutations, inspirations) -> tuple:
        """Synthesize a product idea — تركيب فكرة منتج"""
        title = f"Product: {seed.description[:50]}"
        title_ar = f"منتج: {seed.description_ar[:50] if seed.description_ar else seed.description[:50]}"

        features = [f"ميزة {i+1}: مستوحاة من «{c}»" for i, c in enumerate(core[:4])]
        content = f"Novel product concept blending: {', '.join(core[:3])}"
        content_ar = (
            f"فكرة منتج مبتكرة\n\n"
            + "\n".join(f"  ✓ {f}" for f in features)
            + f"\n\nالمشكلة التي يحلها: {seed.description}"
            + f"\nالقيود: {', '.join(seed.constraints) if seed.constraints else 'لا يوجد'}"
        )

        return title, title_ar, content, content_ar, inspirations

    def _synthesize_logo(self, seed, core, mutations, inspirations) -> tuple:
        """Synthesize a logo concept — تركيب مفهوم شعار بصري"""
        title = f"Logo: {seed.description[:50]}"
        title_ar = f"شعار بصري: {seed.description_ar[:50] if seed.description_ar else seed.description[:50]}"

        elements = [f"عنصر بصري مستوحى من «{c}»" for c in core[:3]]
        content = f"Logo concept combining: {', '.join(core[:3])}"
        content_ar = (
            f"مفهوم الشعار البصري\n\n"
            + "\n".join(f"  ◈ {e}" for e in elements)
            + f"\n\nنمط التصميم: {seed.style_preferences.get('style', 'عصري بسيط')}"
        )

        return title, title_ar, content, content_ar, inspirations

    def _synthesize_story(self, seed, core, mutations, inspirations) -> tuple:
        """Synthesize a story concept — تركيب مفهوم قصة"""
        title = f"Story: {seed.description[:50]}"
        title_ar = f"قصة: {seed.description_ar[:50] if seed.description_ar else seed.description[:50]}"

        acts = [
            f"الفصل الأول: البذرة — «{core[0] if core else 'البداية'}»",
            f"الفصل الثاني: الصراع — تحدّيات غير متوقعة من «{core[1] if len(core) > 1 else 'الوسط'}»",
            f"الفصل الثالث: التحول — نقطة التحول عبر «{core[2] if len(core) > 2 else 'الاكتشاف'}»",
        ]
        content = f"Story arc inspired by: {', '.join(core[:3])}"
        content_ar = (
            f"مفهوم القصة\n\n"
            + "\n".join(f"  ◆ {a}" for a in acts)
        )
        if mutations:
            content_ar += f"\n\nالطفرات السردية: {', '.join(mutations)}"

        return title, title_ar, content, content_ar, inspirations

    def _synthesize_architecture(self, seed, core, mutations, inspirations) -> tuple:
        """Synthesize a code architecture concept — تركيب مفهوم بنية برمجية"""
        title = f"Architecture: {seed.description[:50]}"
        title_ar = f"بنية برمجية: {seed.description_ar[:50] if seed.description_ar else seed.description[:50]}"

        components = [f"مكوّن مستوحى من «{c}»: واجهة + منطق + بيانات" for c in core[:3]]
        content = f"Novel architecture pattern blending: {', '.join(core[:3])}"
        content_ar = (
            f"بنية برمجية مبتكرة\n\n"
            + "\n".join(f"  ◈ {c}" for c in components)
            + f"\n\nالمبدأ التصميمي: التجريد والتركيب"
        )

        return title, title_ar, content, content_ar, inspirations

    def _synthesize_design(self, seed, core, mutations, inspirations) -> tuple:
        """Synthesize a design concept — تركيب مفهوم تصميم"""
        title = f"Design: {seed.description[:50]}"
        title_ar = f"تصميم: {seed.description_ar[:50] if seed.description_ar else seed.description[:50]}"

        elements = [f"عنصر تصميمي مستوحى من «{c}»" for c in core[:4]]
        content = f"Design concept inspired by: {', '.join(core[:3])}"
        content_ar = (
            f"مفهوم التصميم\n\n"
            + "\n".join(f"  ◈ {e}" for e in elements)
        )

        return title, title_ar, content, content_ar, inspirations

    # =========================================================================
    # Internal: Evaluation — التقييم
    # =========================================================================

    def _evaluate_novelty(self, text: str, domain: CreativeDomain) -> float:
        """
        Evaluate novelty by checking against stored fingerprints.
        تقييم الجدة بالتحقق من البصمات المخزنة.
        """
        fingerprint = self._compute_fingerprint(text)

        # Check similarity to existing outputs
        # التحقق من التشابه مع المخرجات الموجودة
        max_similarity = 0.0
        for existing_fp in self._fingerprint_store:
            similarity = self._fingerprint_similarity(fingerprint, existing_fp)
            max_similarity = max(max_similarity, similarity)

        # Novelty is inversely related to maximum similarity
        # الجدة عكسياً مرتبطة بأقصى تشابه
        novelty = max(0.0, min(100.0, (1.0 - max_similarity) * 100))

        # Check for clichés and penalize
        # التحقق من الكليشيهات والمعاقبة
        cliches = DOMAIN_CLICHES.get(domain, [])
        cliche_count = sum(1 for c in cliches if c in text)
        novelty -= cliche_count * 15
        novelty = max(0.0, novelty)

        # Small random factor for variation
        # عامل عشوائي صغير للتنويع
        novelty += random.uniform(-3, 3)
        return max(0.0, min(100.0, novelty))

    def _evaluate_feasibility(self, content: str, seed: CreativeSeed) -> float:
        """
        Evaluate how feasible the idea is to implement.
        تقييم مدى قابلية الفكرة للتنفيذ.
        """
        score = 70.0  # Base feasibility

        # Fewer constraints = higher feasibility
        # قيود أقل = قابلية أعلى للتنفيذ
        num_constraints = len(seed.constraints)
        score -= num_constraints * 5

        # Simple content tends to be more feasible
        # المحتوى البسيط يميل لأن يكون أكثر قابلية للتنفيذ
        if len(content) < 200:
            score += 10

        return max(0.0, min(100.0, score + random.uniform(-5, 5)))

    def _evaluate_relevance(self, content: str, seed: CreativeSeed) -> float:
        """
        Evaluate how relevant the output is to the original seed.
        تقييم مدى صلة المخرج بالبذرة الأصلية.
        """
        score = 65.0  # Base relevance

        # Check if seed keywords appear in content
        # التحقق من ظهور كلمات البذرة في المحتوى
        if seed.description:
            seed_words = set(seed.description.lower().split())
            content_words = set(content.lower().split())
            overlap = len(seed_words & content_words) / max(len(seed_words), 1)
            score += overlap * 30

        return max(0.0, min(100.0, score + random.uniform(-3, 3)))

    # =========================================================================
    # Internal: Fingerprinting & Dedup — البصمات ومنع التكرار
    # =========================================================================

    def _compute_fingerprint(self, text: str) -> str:
        """Compute a structural fingerprint for deduplication — بصمة هيكلية لمنع التكرار"""
        # Character frequency fingerprint
        # بصمة تردد الأحرف
        freq = {}
        for ch in text.lower():
            if ch.isalpha() or ch.isnumeric():
                freq[ch] = freq.get(ch, 0) + 1

        # Normalize
        total = sum(freq.values()) or 1
        sorted_freq = sorted(freq.items())
        fp_str = "|".join(f"{k}:{v/total:.3f}" for k, v in sorted_freq)

        return hashlib.md5(fp_str.encode()).hexdigest()

    def _fingerprint_similarity(self, fp_a: str, fp_b: str) -> float:
        """Compute similarity between two fingerprints — حساب التشابه بين بصمتين"""
        if fp_a == fp_b:
            return 1.0

        # Simple hamming-like distance on hex strings
        # مسافة هامنغ مبسطة على السلاسل السداسية عشرية
        min_len = min(len(fp_a), len(fp_b))
        if min_len == 0:
            return 0.0

        matching = sum(1 for a, b in zip(fp_a, fp_b) if a == b)
        return matching / min_len

    def _store_output(self, output: CreativeOutput):
        """Store output in creative memory — تخزين المخرج في الذاكرة الإبداعية"""
        self._creative_history.append(output)
        if len(self._creative_history) > self._max_history:
            self._creative_history = self._creative_history[-self._max_history:]

        # Store fingerprint
        fp = self._compute_fingerprint(output.title + output.content)
        self._fingerprint_store[fp] = output.created_at

    # =========================================================================
    # Internal: Concept Bridge — جسر المفاهيم
    # =========================================================================

    def _build_concept_bridge(self, concept_a: str, concept_b: str, domain_a: str, domain_b: str) -> dict:
        """
        Build a creative bridge between two concepts from different domains.
        بناء جسر إبداعي بين مفهومين من مجالين مختلفين.
        """
        # Surprise score: the more different the domains, the higher the surprise
        # درجة المفاجأة: كلما اختلفت المجالات أكثر، زادت المفاجأة
        domain_similarity = len(set(domain_a) & set(domain_b)) / max(len(set(domain_a) | set(domain_b)), 1)
        surprise_score = round((1.0 - domain_similarity) * 100, 1)

        bridge = {
            "concept_a": concept_a,
            "concept_b": concept_b,
            "domain_a": domain_a,
            "domain_b": domain_b,
            "bridge_description": f"ماذا يحدث عندما ندمج «{concept_a}» من {domain_a} مع «{concept_b}» من {domain_b}؟",
            "bridge_description_ar": f"ماذا يحدث عندما ندمج «{concept_a}» من {domain_a} مع «{concept_b}» من {domain_b}؟",
            "surprise_score": surprise_score,
            "creative_prompt": f"تصوّر: {concept_a} يلتقي {concept_b} — ما الفكرة الجديدة التي تنبثق؟",
        }
        return bridge

    # =========================================================================
    # Disabled Output — مخرج معطّل
    # =========================================================================

    def _disabled_output(self, seed: CreativeSeed) -> CreativeOutput:
        """Return a placeholder output when the engine is disabled — مخرج بديل عند تعطيل المحرك"""
        return CreativeOutput(
            seed_id=seed.seed_id,
            domain=seed.domain,
            title="[Engine Disabled]",
            title_ar="[المحرك معطّل]",
            content="The Originality Engine is not enabled. Set MAMOUN_ORIGINALITY_ENGINE_ENABLED=true.",
            content_ar="محرك الإبداع غير مُفعّل. اضبط MAMOUN_ORIGINALITY_ENGINE_ENABLED=true",
            novelty_score=0.0,
            feasibility_score=0.0,
            relevance_score=0.0,
        )

    # =========================================================================
    # Status & Lifecycle — الحالة ودورة الحياة
    # =========================================================================

    def get_status(self) -> dict:
        """
        Return the current status of the Originality Engine.
        إرجاع الحالة الحالية لمحرك الإبداع.
        """
        return {
            "module": "OriginalityEngine",
            "enabled": self._enabled,
            "feature_flag": "MAMOUN_ORIGINALITY_ENGINE_ENABLED",
            "history_size": len(self._creative_history),
            "fingerprint_store_size": len(self._fingerprint_store),
            "domains_supported": [d.value for d in CreativeDomain],
            "mutations_available": [m.value for m in CreativeMutation],
            "rhetoric_devices": list(ARABIC_RHETORIC_DEVICES.keys()),
            "cross_domain_pools": list(CROSS_DOMAIN_CONCEPTS.keys()),
            "weights": {
                "novelty": self._novelty_weight,
                "feasibility": self._feasibility_weight,
                "relevance": self._relevance_weight,
            },
            "initialized": self._initialized,
        }

    def shutdown(self):
        """
        Gracefully shut down the Originality Engine.
        إيقاف تشغيل محرك الإبداع بأمان.
        """
        # Clear in-memory stores
        # مسح المخازن في الذاكرة
        self._creative_history.clear()
        self._fingerprint_store.clear()
        self._novelty_scorer = None
        self._initialized = False
