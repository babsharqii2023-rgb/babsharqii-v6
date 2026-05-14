"""
BABSHARQII v40.0 "مأمون" — Skill Generalizer
المعمِّم للمهارات — يعمم المهارات المُكتسبة لسياقات ومجالات مختلفة

Research basis:
  - Analogical Reasoning: تعلم بالتشبيه — تطبيق مهارة من مجال على مجال مشابه
  - Structure-Mapping Theory (Gentner): نظرية مطابقة البنية — نقل العلاقات
    بين المجالات مع الحفاظ على البنية العميقة
  - Cross-Domain Transfer: النقل بين المجالات — تعميم المهارات
    من سياق محدد إلى سياقات أوسع

Architecture:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                       SkillGeneralizer                                  │
  │                                                                         │
  │  ┌────────────────────┐  ┌────────────────────┐  ┌──────────────────┐  │
  │  │  SpecificityAnalyzer│  │  DomainMapper      │  │  SkillMerger     │  │
  │  │  تحليل الخصوصية    │  │  مطابقة المجالات  │  │  دمج المهارات    │  │
  │  └────────┬───────────┘  └────────┬───────────┘  └────────┬─────────┘  │
  │           │                       │                        │            │
  │  ┌────────▼───────────────────────▼────────────────────────▼─────────┐ │
  │  │              GeneralizationHistory (SQLite)                       │ │
  │  │  سجل التعاميم · نسب النجاح · مطابقات المجالات                    │ │
  │  └──────────────────────────────────────────────────────────────────┘ │
  └─────────────────────────────────────────────────────────────────────────┘

Env toggles:
    MAMOUN_ONE_SHOT_LEARNING (default: "false") — يتبع نفس مفتاح OneShotLearner
"""

from __future__ import annotations

import os
import json
import time
import uuid
import hashlib
import logging
import asyncio
from pathlib import Path
from typing import Any, Optional
from collections import defaultdict
from dataclasses import dataclass, field

import aiosqlite

from mamoun.config import DB_PATH
from mamoun.learning.one_shot_learner import (
    LearnedSkill,
    ONE_SHOT_LEARNING_ENABLED,
)

logger = logging.getLogger("mamoun.skill_generalizer")


# ═══════════════════════════════════════════════════════════════════════════════
# ثوابت — Constants
# ═══════════════════════════════════════════════════════════════════════════════

GENERALIZATION_SIMILARITY_THRESHOLD: float = float(
    os.getenv("MAMOUN_GENERALIZATION_SIMILARITY_THRESHOLD", "0.7")
)

MERGE_MIN_OVERLAP: float = float(
    os.getenv("MAMOUN_GENERALIZATION_MERGE_MIN_OVERLAP", "0.5")
)

# تعريف المجالات — domain definitions
DOMAIN_VOCABULARY: dict[str, set[str]] = {
    "finance": {
        "مال", "مالي", "ميزانية", "إيرادات", "مصروفات", "ربح", "خسارة",
        "سهم", "سوق", "استثمار", "محفظة", "تداول", "مصرف", "بنك",
        "financial", "budget", "revenue", "expense", "profit", "loss",
        "stock", "market", "investment", "portfolio", "trading", "bank",
    },
    "medical": {
        "طبي", "مرض", "علاج", "تشخيص", "أعراض", "دواء", "مستشفى",
        "طبيب", "مريض", "صحة", "تحليل", "أشعة", "جراحة",
        "medical", "disease", "treatment", "diagnosis", "symptoms",
        "medicine", "hospital", "doctor", "patient", "health",
    },
    "legal": {
        "قانون", "قضية", "محكمة", "عقد", "اتفاقية", "حقوق", "التزام",
        "محامي", "حكم", "قضائي", "تشريع", "لائحة", "قانوني",
        "legal", "case", "court", "contract", "agreement", "rights",
        "obligation", "lawyer", "judgment", "legislation", "regulation",
    },
    "education": {
        "تعليم", "منهج", "طالب", "معلم", "امتحان", "درجة", "مدرسة",
        "جامعة", "بحث", "أطروحة", "تدريس", "تعلم",
        "education", "curriculum", "student", "teacher", "exam",
        "grade", "school", "university", "research", "thesis",
    },
    "technology": {
        "تقنية", "برمجة", "خادم", "قاعدة بيانات", "خوارزمية", "شبكة",
        "أمان", "برنامج", "نظام", "تطبيق", "ذكاء اصطناعي",
        "technology", "programming", "server", "database", "algorithm",
        "network", "security", "software", "system", "application",
    },
    "tabular": {
        "جدول", "بيانات", "صف", "عمود", "خلية", "رأس", "إحصاء",
        "تقرير", "تحليل", "ملخص", "مجموع",
        "table", "data", "row", "column", "cell", "header",
        "statistics", "report", "analysis", "summary",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# أنواع البيانات — Dataclasses
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class GeneralizedSkill:
    """
    مهارة معممة — A generalized version of a learned skill.
    نسخة معممة من مهارة مُكتسبة تنطبق على مجالات متعددة.

    Attributes:
        original_skill_id: معرف المهارة الأصلية
        generalized_skill_id: معرف المهارة المعممة
        generalized_rules: القواعد المعممة — أنماط أوسع تنطبق على مجالات متعددة
        applicable_domains: المجالات المطبقة — المجالات التي يمكن تطبيق المهارة عليها
        generalization_confidence: ثقة التعميم (0.0–1.0)
        domain_mappings: مطابقات المجالات — كيف ترتبط المجالات المختلفة
    """
    original_skill_id: str = ""
    generalized_skill_id: str = ""
    generalized_rules: list[str] = field(default_factory=list)
    applicable_domains: list[str] = field(default_factory=list)
    generalization_confidence: float = 0.0
    domain_mappings: list[dict] = field(default_factory=list)

    def __post_init__(self):
        """توليد معرف تلقائي إن لم يكن موجوداً — Auto-generate ID if missing"""
        if not self.generalized_skill_id:
            hash_input = f"gen:{self.original_skill_id}"
            self.generalized_skill_id = (
                f"gen_{hashlib.md5(hash_input.encode()).hexdigest()[:12]}"
                f"_{uuid.uuid4().hex[:6]}"
            )

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "original_skill_id": self.original_skill_id,
            "generalized_skill_id": self.generalized_skill_id,
            "generalized_rules": self.generalized_rules,
            "applicable_domains": self.applicable_domains,
            "generalization_confidence": round(self.generalization_confidence, 4),
            "domain_mappings": self.domain_mappings,
        }


@dataclass
class DomainMapping:
    """
    مطابقة مجال — Mapping between two domains.
    مطابقة بين مجالين تُظهر كيف ترتبط القواعد والمتغيرات.

    Attributes:
        source_domain: المجال المصدر
        target_domain: المجال الهدف
        rule_mappings: مطابقات القواعد — كيف ترتبط القواعد بين المجالين
        variable_mappings: مطابقات المتغيرات — كيف ترتبط المتغيرات
        confidence: ثقة المطابقة (0.0–1.0)
    """
    source_domain: str = ""
    target_domain: str = ""
    rule_mappings: list[dict] = field(default_factory=list)
    variable_mappings: dict = field(default_factory=dict)
    confidence: float = 0.0

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "rule_mappings": self.rule_mappings,
            "variable_mappings": self.variable_mappings,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class MergedSkill:
    """
    مهارة مدمجة — A skill merged from multiple similar skills.
    مهارة ناتجة عن دمج عدة مهارات مشابهة في مهارة أقوى وأشمل.

    Attributes:
        merged_skill_id: معرف المهارة المدمجة
        source_skill_ids: معرفات المهارات المصدرية
        merged_rules: القواعد المدمجة — اتحاد القواعد من جميع المصادر
        merged_variables: المتغيرات المدمجة — متغيرات مشتركة ومستقلة
        coverage_score: درجة التغطية — مدى شمول المهارة المدمجة (0.0–1.0)
    """
    merged_skill_id: str = ""
    source_skill_ids: list[str] = field(default_factory=list)
    merged_rules: list[str] = field(default_factory=list)
    merged_variables: dict = field(default_factory=dict)
    coverage_score: float = 0.0

    def __post_init__(self):
        """توليد معرف تلقائي إن لم يكن موجوداً — Auto-generate ID if missing"""
        if not self.merged_skill_id:
            hash_input = f"merged:{','.join(sorted(self.source_skill_ids))}"
            self.merged_skill_id = (
                f"merged_{hashlib.md5(hash_input.encode()).hexdigest()[:12]}"
                f"_{uuid.uuid4().hex[:6]}"
            )

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "merged_skill_id": self.merged_skill_id,
            "source_skill_ids": self.source_skill_ids,
            "merged_rules": self.merged_rules,
            "merged_variables": self.merged_variables,
            "coverage_score": round(self.coverage_score, 4),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SkillGeneralizer — المعمِّم للمهارات
# ═══════════════════════════════════════════════════════════════════════════════


class SkillGeneralizer:
    """
    المعمِّم للمهارات — Generalizes learned skills to different contexts.

    يحلل المهارة المُكتسبة ويحدد أي أجزائها خاصة بالمجال وأيها عام
    وقابل للتعميم. ثم يُنشئ نسخاً معممة تنطبق على مجالات مختلفة
    باستخدام الاستدلال بالتشبيه (Analogical Reasoning).

    العملية:
      1. تحليل الخصوصية: تحديد الأجزاء الخاصة والعامة
      2. التعميم: إنشاء قواعد أوسع من القواعد الخاصة
      3. مطابقة المجالات: ربط المجالات عبر التشبيه البنيوي
      4. الدمج: توحيد المهارات المتشابهة في مهارة أقوى

    تفعيل: MAMOUN_ONE_SHOT_LEARNING=true (افتراضي: false)
    """

    def __init__(self, db_path: str = ""):
        """
        تهيئة المعمِّم للمهارات.

        Args:
            db_path: مسار قاعدة بيانات SQLite (افتراضي: DB_PATH من الإعدادات)
        """
        self._db_path = db_path or str(DB_PATH)
        self._initialized = False

        # إحصائيات — statistics
        self._total_generalized: int = 0
        self._total_domain_mappings: int = 0
        self._total_merges: int = 0
        self._last_activity_time: float = 0.0
        self._running: bool = True

        # سجل التعاميم — generalization history in memory
        self._generalization_log: list[dict] = []
        self._max_log_size: int = 500

        logger.info(
            "تم تهيئة المعمِّم للمهارات — ONE_SHOT_LEARNING=%s, SIMILARITY_THRESHOLD=%.2f",
            ONE_SHOT_LEARNING_ENABLED, GENERALIZATION_SIMILARITY_THRESHOLD,
        )

    # =========================================================================
    # تهيئة قاعدة البيانات — Database Initialization
    # =========================================================================

    async def _initialize(self) -> None:
        """إنشاء جداول قاعدة البيانات — Create database tables."""
        if self._initialized:
            return

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS skill_generalizations (
                    generalized_skill_id TEXT PRIMARY KEY,
                    original_skill_id TEXT NOT NULL,
                    generalized_rules TEXT DEFAULT '[]',
                    applicable_domains TEXT DEFAULT '[]',
                    generalization_confidence REAL DEFAULT 0.0,
                    domain_mappings TEXT DEFAULT '[]',
                    created_at REAL DEFAULT 0.0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS skill_domain_mappings (
                    mapping_id TEXT PRIMARY KEY,
                    source_domain TEXT NOT NULL,
                    target_domain TEXT NOT NULL,
                    source_skill_id TEXT NOT NULL,
                    rule_mappings TEXT DEFAULT '[]',
                    variable_mappings TEXT DEFAULT '{}',
                    confidence REAL DEFAULT 0.0,
                    created_at REAL DEFAULT 0.0
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_domain_source
                ON skill_domain_mappings(source_domain)
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS skill_merges (
                    merged_skill_id TEXT PRIMARY KEY,
                    source_skill_ids TEXT DEFAULT '[]',
                    merged_rules TEXT DEFAULT '[]',
                    merged_variables TEXT DEFAULT '{}',
                    coverage_score REAL DEFAULT 0.0,
                    created_at REAL DEFAULT 0.0
                )
            """)
            await db.commit()

        self._initialized = True
        logger.info("تم تهيئة جداول تعميم المهارات")

    # =========================================================================
    # واجهة رئيسية — Main API
    # =========================================================================

    async def generalize_skill(self, skill: LearnedSkill) -> GeneralizedSkill:
        """
        تعميم مهارة — Generalize a learned skill.

        العملية:
          1. تحليل القواعد لتحديد الأجزاء الخاصة والعامة
          2. تحويل القواعد الخاصة إلى قواعد معممة
          3. تحديد المجالات المطبقة
          4. حساب ثقة التعميم

        Args:
            skill: المهارة المُكتسبة

        Returns:
            GeneralizedSkill — المهارة المعممة
        """
        await self._initialize()

        if not ONE_SHOT_LEARNING_ENABLED:
            logger.debug("تعميم المهارات معطل — تم إرجاع مهارة معممة فارغة")
            return GeneralizedSkill(original_skill_id=skill.skill_id)

        start_time = time.time()

        # ─── الخطوة ١: تحليل الخصوصية ────────────────────────────────
        specificity = self._analyze_specificity(skill)

        # ─── الخطوة ٢: تعميم القواعد ──────────────────────────────────
        generalized_rules = self._generalize_rules(
            skill.abstract_rules, specificity
        )

        # ─── الخطوة ٣: تحديد المجالات المطبقة ────────────────────────
        applicable_domains = self._identify_applicable_domains(skill)

        # ─── الخطوة ٤: بناء مطابقات المجالات ──────────────────────────
        domain_mappings = self._build_domain_mappings(
            skill, applicable_domains
        )

        # ─── الخطوة ٥: حساب ثقة التعميم ──────────────────────────────
        confidence = self._compute_generalization_confidence(
            skill, specificity, applicable_domains
        )

        # ─── الخطوة ٦: إنشاء المهارة المعممة ────────────────────────
        generalized = GeneralizedSkill(
            original_skill_id=skill.skill_id,
            generalized_rules=generalized_rules,
            applicable_domains=applicable_domains,
            generalization_confidence=confidence,
            domain_mappings=[dm.to_dict() for dm in domain_mappings],
        )

        # ─── الخطوة ٧: تخزين التعميم ────────────────────────────────
        await self._store_generalization(generalized)

        # تحديث الإحصائيات
        self._total_generalized += 1
        self._total_domain_mappings += len(domain_mappings)
        self._last_activity_time = time.time()

        # تسجيل في السجل
        self._generalization_log.append({
            "original_skill_id": skill.skill_id,
            "generalized_skill_id": generalized.generalized_skill_id,
            "applicable_domains": applicable_domains,
            "confidence": confidence,
            "timestamp": time.time(),
        })
        if len(self._generalization_log) > self._max_log_size:
            self._generalization_log = self._generalization_log[-self._max_log_size:]

        elapsed = (time.time() - start_time) * 1000
        logger.info(
            "تم تعميم المهارة '%s' → '%s' — %d مجال، ثقة=%.3f، %.1f مللي ثانية",
            skill.skill_id, generalized.generalized_skill_id,
            len(applicable_domains), confidence, elapsed,
        )

        return generalized

    async def apply_to_domain(
        self, skill: LearnedSkill, target_domain: str
    ) -> DomainMapping:
        """
        تطبيق مهارة على مجال جديد — Apply a skill to a new domain via analogy.

        يستخدم الاستدلال بالتشبيه لنقل المهارة من مجالها الأصلي
        إلى مجال هدف. يحدد المطابقات بين القواعد والمتغيرات.

        Args:
            skill: المهارة المُكتسبة
            target_domain: المجال الهدف

        Returns:
            DomainMapping — مطابقة المجال
        """
        await self._initialize()

        if not ONE_SHOT_LEARNING_ENABLED:
            return DomainMapping(
                source_domain="unknown",
                target_domain=target_domain,
            )

        # تحديد المجال المصدر
        source_domain = self._detect_domain(skill)

        # بناء مطابقات القواعد
        rule_mappings = self._map_rules_to_domain(
            skill.abstract_rules, source_domain, target_domain
        )

        # بناء مطابقات المتغيرات
        variable_mappings = self._map_variables_to_domain(
            skill.dynamic_variables, source_domain, target_domain
        )

        # حساب ثقة المطابقة
        confidence = self._compute_mapping_confidence(
            rule_mappings, variable_mappings
        )

        mapping = DomainMapping(
            source_domain=source_domain,
            target_domain=target_domain,
            rule_mappings=rule_mappings,
            variable_mappings=variable_mappings,
            confidence=confidence,
        )

        # تخزين المطابقة
        await self._store_domain_mapping(skill.skill_id, mapping)

        self._total_domain_mappings += 1
        self._last_activity_time = time.time()

        logger.info(
            "مطابقة مجال: '%s' → '%s' — %d قاعدة، ثقة=%.3f",
            source_domain, target_domain,
            len(rule_mappings), confidence,
        )

        return mapping

    async def find_similar_skills(
        self, skill_id: str, threshold: float = GENERALIZATION_SIMILARITY_THRESHOLD
    ) -> list[dict]:
        """
        البحث عن مهارات مشابهة — Find skills similar to the given one.

        يقارن القواعد والمتغيرات والنوع لإيجاد مهارات يمكن دمجها.

        Args:
            skill_id: معرف المهارة المرجعية
            threshold: عتبة التشابه (0.0–1.0)

        Returns:
            قائمة المهارات المشابهة مع درجات التشابه
        """
        await self._initialize()

        # استرجاع المهارة المرجعية من قاعدة البيانات
        reference = await self._get_skill_from_db(skill_id)
        if not reference:
            logger.warning("المهارة '%s' غير موجودة", skill_id)
            return []

        # استرجاع جميع المهارات
        all_skills = await self._get_all_skills_from_db()

        similar: list[dict] = []
        for other in all_skills:
            if other.skill_id == skill_id:
                continue

            similarity = self._compute_skill_similarity(reference, other)
            if similarity >= threshold:
                similar.append({
                    "skill_id": other.skill_id,
                    "skill_name": other.skill_name,
                    "skill_name_ar": other.skill_name_ar,
                    "task_type": other.task_type,
                    "similarity": round(similarity, 4),
                    "success_rate": other.success_rate,
                })

        # ترتيب حسب التشابه
        similar.sort(key=lambda x: x["similarity"], reverse=True)

        logger.info(
            "البحث عن مشابهات لـ '%s': %d نتيجة (عتبة=%.2f)",
            skill_id, len(similar), threshold,
        )

        return similar

    async def merge_skills(self, skill_ids: list[str]) -> MergedSkill:
        """
        دمج مهارات — Merge multiple similar skills into a stronger one.

        يجمع القواعد والمتغيرات من عدة مهارات في مهارة واحدة
        أقوى وأشمل. يزيل التكرار ويحسب التغطية.

        Args:
            skill_ids: قائمة معرفات المهارات للدمج

        Returns:
            MergedSkill — المهارة المدمجة
        """
        await self._initialize()

        if len(skill_ids) < 2:
            logger.warning("الدمج يتطلب مهارتين على الأقل")
            return MergedSkill(source_skill_ids=skill_ids)

        # استرجاع المهارات
        skills: list[LearnedSkill] = []
        for sid in skill_ids:
            skill = await self._get_skill_from_db(sid)
            if skill:
                skills.append(skill)

        if len(skills) < 2:
            logger.warning("لم يتم العثور على مهارات كافية للدمج")
            return MergedSkill(source_skill_ids=skill_ids)

        # دمج القواعد
        all_rules: list[str] = []
        for skill in skills:
            all_rules.extend(skill.abstract_rules)

        # إزالة التكرار
        seen_rules: set[str] = set()
        merged_rules: list[str] = []
        for rule in all_rules:
            normalized = rule.strip().lower()
            if normalized not in seen_rules:
                seen_rules.add(normalized)
                merged_rules.append(rule)

        # دمج المتغيرات
        merged_variables: dict = {}
        for skill in skills:
            for var in skill.dynamic_variables:
                var_name = var.get("name", "")
                if var_name not in merged_variables:
                    merged_variables[var_name] = var
                else:
                    # المتغير موجود — تحديث الأنواع إذا كانت مختلفة
                    existing = merged_variables[var_name]
                    if existing.get("type") != var.get("type"):
                        merged_variables[var_name]["type"] = "any"

        # حساب درجة التغطية
        coverage_score = self._compute_coverage_score(skills, merged_rules)

        merged = MergedSkill(
            source_skill_ids=skill_ids,
            merged_rules=merged_rules,
            merged_variables=merged_variables,
            coverage_score=coverage_score,
        )

        # تخزين الدمج
        await self._store_merge(merged)

        self._total_merges += 1
        self._last_activity_time = time.time()

        logger.info(
            "تم دمج %d مهارة في '%s' — %d قاعدة، تغطية=%.3f",
            len(skills), merged.merged_skill_id,
            len(merged_rules), coverage_score,
        )

        return merged

    async def get_generalization_history(self) -> list[dict]:
        """
        سجل التعاميم — Get the history of generalizations.

        Returns:
            قائمة سجلات التعميم
        """
        await self._initialize()

        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM skill_generalizations
                ORDER BY created_at DESC
                LIMIT 100
            """)
            rows = await cursor.fetchall()

        history: list[dict] = []
        for row in rows:
            history.append({
                "generalized_skill_id": row["generalized_skill_id"],
                "original_skill_id": row["original_skill_id"],
                "applicable_domains": json.loads(
                    row["applicable_domains"] if row["applicable_domains"] else "[]"
                ),
                "generalization_confidence": row["generalization_confidence"],
                "created_at": row["created_at"],
            })

        return history

    # =========================================================================
    # تحليل الخصوصية — Specificity Analysis
    # =========================================================================

    def _analyze_specificity(self, skill: LearnedSkill) -> dict[str, float]:
        """
        تحليل خصوصية المهارة — Analyze how specific vs. general each rule is.

        لكل قاعدة، يحدد درجة الخصوصية (0.0 = عام جداً، 1.0 = خاص جداً).
        القواعد التي تحتوي على قيم محددة أو مصطلحات مجال محدد هي أكثر خصوصية.

        Args:
            skill: المهارة المُكتسبة

        Returns:
            قاموس يربط كل قاعدة بدرجة خصوصيتها
        """
        specificity: dict[str, float] = {}

        for i, rule in enumerate(skill.abstract_rules):
            score = 0.0

            # عامل ١: وجود قيم رقمية محددة (أكثر خصوصية)
            import re
            numbers = re.findall(r"\d+\.?\d*", rule)
            if numbers:
                score += 0.3

            # عامل ٢: وجود مصطلحات مجال محدد
            domain_vocab = set()
            for vocab in DOMAIN_VOCABULARY.values():
                domain_vocab.update(vocab)

            rule_words = set(re.findall(r"\w+", rule.lower()))
            domain_matches = rule_words & domain_vocab
            if domain_matches:
                score += min(0.4, len(domain_matches) * 0.1)

            # عامل ٣: قصر القاعدة (أقصر = أكثر عمومية غالباً)
            if len(rule) < 30:
                score -= 0.1
            elif len(rule) > 100:
                score += 0.2

            # عامل ٤: وجود أسماء مفاتيح محددة
            if "'" in rule or '"' in rule:
                score += 0.15

            specificity[f"rule_{i}"] = max(0.0, min(1.0, score))

        return specificity

    # =========================================================================
    # تعميم القواعد — Rule Generalization
    # =========================================================================

    def _generalize_rules(
        self, rules: list[str], specificity: dict[str, float]
    ) -> list[str]:
        """
        تعميم القواعد — Generalize rules by making specific parts abstract.

        القواعد ذات الخصوصية العالية تُحوَّل إلى نسخ أوسع عن طريق:
        - استبدال القيم المحددة بمتغيرات
        - استبدال مصطلحات المجال بمصطلحات عامة

        Args:
            rules: القواعد الأصلية
            specificity: درجات الخصوصية لكل قاعدة

        Returns:
            القواعد المعممة
        """
        generalized: list[str] = []

        for i, rule in enumerate(rules):
            key = f"rule_{i}"
            spec_score = specificity.get(key, 0.0)

            if spec_score < 0.3:
                # القاعدة عامة بالفعل — تحفظ كما هي
                generalized.append(rule)
            elif spec_score < 0.6:
                # متوسطة الخصوصية — تعميم جزئي
                generalized.append(self._partially_generalize_rule(rule))
            else:
                # عالية الخصوصية — تعميم كامل
                generalized.append(self._fully_generalize_rule(rule))

        return generalized

    @staticmethod
    def _partially_generalize_rule(rule: str) -> str:
        """تعميم جزئي لقاعدة — Partially generalize a rule."""
        import re as _re
        # استبدال الأرقام بمتغيرات
        result = _re.sub(r"\b\d+\.?\d*\b", "[رقم]", rule)
        return result

    @staticmethod
    def _fully_generalize_rule(rule: str) -> str:
        """تعميم كامل لقاعدة — Fully generalize a rule."""
        import re as _re
        result = rule

        # استبدال القيم بين علامات اقتباس بمتغيرات
        result = _re.sub(r"'[^']*'", "[قيمة]", result)
        result = _re.sub(r'"[^"]*"', "[قيمة]", result)

        # استبدال الأرقام بمتغيرات
        result = _re.sub(r"\b\d+\.?\d*\b", "[رقم]", result)

        # إضافة مؤشر التعميم
        result = f"[معمم] {result}"

        return result

    # =========================================================================
    # مطابقة المجالات — Domain Mapping
    # =========================================================================

    def _identify_applicable_domains(self, skill: LearnedSkill) -> list[str]:
        """
        تحديد المجالات المطبقة — Identify domains where the skill can apply.

        يحلل المفردات في القواعد والقيود لتحديد المجالات المناسبة.

        Args:
            skill: المهارة المُكتسبة

        Returns:
            قائمة المجالات المطبقة
        """
        domain_scores: dict[str, float] = defaultdict(float)

        # تحليل المفردات في القواعد
        all_text = " ".join(skill.abstract_rules + skill.constraints)
        text_words = set(all_text.lower().split())

        for domain, vocab in DOMAIN_VOCABULARY.items():
            overlap = text_words & vocab
            if overlap:
                domain_scores[domain] += len(overlap) * 0.2

        # تحليل المفردات في المتغيرات
        for var in skill.dynamic_variables:
            var_name = var.get("name", "").lower()
            var_path = var.get("path", "").lower()
            combined = f"{var_name} {var_path}"
            combined_words = set(combined.split())

            for domain, vocab in DOMAIN_VOCABULARY.items():
                overlap = combined_words & vocab
                if overlap:
                    domain_scores[domain] += len(overlap) * 0.15

        # تحليل المفردات في نوع المهمة
        task_type = skill.task_type.lower()
        for domain, vocab in DOMAIN_VOCABULARY.items():
            if task_type in vocab:
                domain_scores[domain] += 0.3

        # تحليل اسم المهارة
        skill_text = f"{skill.skill_name} {skill.skill_name_ar}".lower()
        for domain, vocab in DOMAIN_VOCABULARY.items():
            overlap = set(skill_text.split()) & vocab
            if overlap:
                domain_scores[domain] += len(overlap) * 0.1

        # إضافة المجال العام دائماً
        domain_scores["general"] = 0.5

        # ترتيب حسب الدرجة
        sorted_domains = sorted(
            domain_scores.items(), key=lambda x: x[1], reverse=True
        )

        # إرجاع المجالات ذات الدرجة المعنوية
        return [domain for domain, score in sorted_domains if score >= 0.1]

    def _detect_domain(self, skill: LearnedSkill) -> str:
        """تحديد المجال الرئيسي للمهارة — Detect the primary domain of a skill."""
        domains = self._identify_applicable_domains(skill)
        # استبعاد 'general' والبحث عن المجال الأكثر تحديداً
        specific_domains = [d for d in domains if d != "general"]
        return specific_domains[0] if specific_domains else "general"

    def _build_domain_mappings(
        self, skill: LearnedSkill, domains: list[str]
    ) -> list[DomainMapping]:
        """بناء مطابقات المجالات — Build domain mappings for all applicable domains."""
        source_domain = self._detect_domain(skill)
        mappings: list[DomainMapping] = []

        for target_domain in domains:
            if target_domain == source_domain:
                continue

            mapping = self._create_domain_mapping(
                skill, source_domain, target_domain
            )
            if mapping.confidence >= 0.2:
                mappings.append(mapping)

        return mappings

    def _create_domain_mapping(
        self, skill: LearnedSkill, source_domain: str, target_domain: str
    ) -> DomainMapping:
        """إنشاء مطابقة مجال — Create a domain mapping."""
        rule_mappings = self._map_rules_to_domain(
            skill.abstract_rules, source_domain, target_domain
        )

        variable_mappings = self._map_variables_to_domain(
            skill.dynamic_variables, source_domain, target_domain
        )

        confidence = self._compute_mapping_confidence(
            rule_mappings, variable_mappings
        )

        return DomainMapping(
            source_domain=source_domain,
            target_domain=target_domain,
            rule_mappings=rule_mappings,
            variable_mappings=variable_mappings,
            confidence=confidence,
        )

    def _map_rules_to_domain(
        self, rules: list[str], source_domain: str, target_domain: str
    ) -> list[dict]:
        """
        مطابقة القواعد مع مجال هدف — Map rules to a target domain.

        يستبدل المفردات الخاصة بالمجال المصدر بمفردات المجال الهدف.
        """
        source_vocab = DOMAIN_VOCABULARY.get(source_domain, set())
        target_vocab = DOMAIN_VOCABULARY.get(target_domain, set())

        mappings: list[dict] = []

        # بناء قاموس ترجمة مبسط بين المجالين
        source_list = sorted(source_vocab)
        target_list = sorted(target_vocab)

        for i, rule in enumerate(rules):
            rule_mapping: dict = {
                "source_rule_index": i,
                "source_rule": rule,
                "target_rule": rule,  # يبدأ بنسخة مطابقة
                "transformations": [],
            }

            # محاولة مطابقة المفردات
            for src_word in source_list:
                if src_word in rule.lower():
                    # البحث عن مقابل في المجال الهدف
                    idx = source_list.index(src_word)
                    if idx < len(target_list):
                        tgt_word = target_list[idx]
                        rule_mapping["target_rule"] = rule_mapping["target_rule"].replace(
                            src_word, tgt_word
                        )
                        rule_mapping["transformations"].append({
                            "from": src_word,
                            "to": tgt_word,
                        })

            mappings.append(rule_mapping)

        return mappings

    @staticmethod
    def _map_variables_to_domain(
        variables: list[dict], source_domain: str, target_domain: str
    ) -> dict:
        """
        مطابقة المتغيرات مع مجال هدف — Map variables to a target domain.
        """
        mappings: dict = {}
        domain_hints: dict[str, dict[str, str]] = {
            "finance": {"amount": "value", "price": "cost", "quantity": "shares"},
            "medical": {"amount": "dosage", "price": "cost", "quantity": "units"},
            "tabular": {"amount": "cell_value", "price": "column_value", "quantity": "row_count"},
        }

        source_hints = domain_hints.get(source_domain, {})
        target_hints = domain_hints.get(target_domain, {})

        for var in variables:
            var_name = var.get("name", "")
            # محاولة إيجاد مقابل
            mapped_name = var_name
            for src_key, tgt_val in source_hints.items():
                if src_key in var_name.lower():
                    # البحث في تلميحات المجال الهدف
                    for tgt_key, tgt_val2 in target_hints.items():
                        if tgt_key == src_key:
                            mapped_name = var_name.replace(src_key, tgt_val2)
                            break
                    break

            mappings[var_name] = {
                "mapped_name": mapped_name,
                "source_type": var.get("type", "string"),
                "target_type": var.get("type", "string"),  # النوع يبقى نفسه عادةً
            }

        return mappings

    @staticmethod
    def _compute_mapping_confidence(
        rule_mappings: list[dict], variable_mappings: dict
    ) -> float:
        """حساب ثقة المطابقة — Compute confidence for a domain mapping."""
        if not rule_mappings and not variable_mappings:
            return 0.0

        # ثقة القواعد: نسبة القواعد التي تم تحويلها بنجاح
        rules_with_transforms = sum(
            1 for rm in rule_mappings if rm.get("transformations")
        )
        rule_confidence = (
            rules_with_transforms / max(1, len(rule_mappings))
            if rule_mappings else 0.5
        )

        # ثقة المتغيرات: نسبة المتغيرات المعينة
        var_confidence = (
            len(variable_mappings) / max(1, len(variable_mappings))
            if variable_mappings else 0.5
        )

        # الثقة المركبة
        confidence = 0.6 * rule_confidence + 0.4 * var_confidence

        return max(0.0, min(1.0, confidence))

    # =========================================================================
    # حساب التشابه — Similarity Computation
    # =========================================================================

    def _compute_skill_similarity(
        self, skill_a: LearnedSkill, skill_b: LearnedSkill
    ) -> float:
        """
        حساب تشابه مهارتين — Compute similarity between two skills.

        يستخدم تشابه Jaccard على مستوى القواعد والمتغيرات مع مراعاة نوع المهمة.
        """
        # تشابه نوع المهمة
        type_sim = 1.0 if skill_a.task_type == skill_b.task_type else 0.0
        if type_sim == 0.0:
            # أنواع مختلفة — تخفيض كبير
            type_penalty = 0.3
        else:
            type_penalty = 1.0

        # تشابه القواعد (Jaccard على مستوى الكلمات)
        rules_a_words: set[str] = set()
        for rule in skill_a.abstract_rules:
            rules_a_words.update(rule.lower().split())

        rules_b_words: set[str] = set()
        for rule in skill_b.abstract_rules:
            rules_b_words.update(rule.lower().split())

        if rules_a_words or rules_b_words:
            rules_intersection = rules_a_words & rules_b_words
            rules_union = rules_a_words | rules_b_words
            rules_sim = len(rules_intersection) / max(1, len(rules_union))
        else:
            rules_sim = 0.5

        # تشابه المتغيرات
        vars_a = {v.get("name", "") for v in skill_a.dynamic_variables}
        vars_b = {v.get("name", "") for v in skill_b.dynamic_variables}
        if vars_a or vars_b:
            vars_intersection = vars_a & vars_b
            vars_union = vars_a | vars_b
            vars_sim = len(vars_intersection) / max(1, len(vars_union))
        else:
            vars_sim = 0.5

        # تشابه القيود
        constraints_a = set(c.lower() for c in skill_a.constraints)
        constraints_b = set(c.lower() for c in skill_b.constraints)
        if constraints_a or constraints_b:
            constraints_intersection = constraints_a & constraints_b
            constraints_union = constraints_a | constraints_b
            constraints_sim = len(constraints_intersection) / max(1, len(constraints_union))
        else:
            constraints_sim = 0.5

        # التشابه النهائي = مرجح
        similarity = (
            0.2 * type_penalty
            + 0.35 * rules_sim
            + 0.25 * vars_sim
            + 0.2 * constraints_sim
        )

        return max(0.0, min(1.0, similarity))

    @staticmethod
    def _compute_coverage_score(
        skills: list[LearnedSkill], merged_rules: list[str]
    ) -> float:
        """حساب درجة التغطية — Compute coverage score for merged skills."""
        if not skills or not merged_rules:
            return 0.0

        # نسبة القواعد المدمجة إلى إجمالي القواعد الأصلية
        total_original = sum(len(s.abstract_rules) for s in skills)
        if total_original == 0:
            return 0.5

        coverage = len(merged_rules) / total_original

        # تعديل: إذا كانت القواعد المدمجة تغطي معظم الأصلية = تغطية عالية
        # لكن إذا كانت أقل بكثير = تكرار عالي = تغطية جيدة أيضاً
        unique_ratio = len(merged_rules) / max(1, total_original)

        if unique_ratio > 0.8:
            # تغطية عالية — معظم القواعد محفوظة
            score = 0.8 + 0.2 * (1.0 - unique_ratio)
        elif unique_ratio > 0.5:
            # تغطية متوسطة — تكرار معقول
            score = 0.6 + 0.2 * unique_ratio
        else:
            # تغطية منخفضة — كثير من التكرار
            score = unique_ratio

        # عامل تنوع المهارات المصدرية
        diversity_bonus = min(0.1, len(skills) * 0.03)

        return max(0.0, min(1.0, score + diversity_bonus))

    # =========================================================================
    # حساب ثقة التعميم — Generalization Confidence
    # =========================================================================

    def _compute_generalization_confidence(
        self,
        skill: LearnedSkill,
        specificity: dict[str, float],
        applicable_domains: list[str],
    ) -> float:
        """
        حساب ثقة التعميم — Compute confidence for the generalization.

        العوامل:
          - خصوصية المهارة الأصلية (أقل خصوصية = ثقة أعلى)
          - عدد المجالات المطبقة (أكثر = ثقة أعلى)
          - معدل نجاح المهارة الأصلية
        """
        # عامل الخصوصية: متوسط الخصوصية (أقل = أفضل للتعميم)
        if specificity:
            avg_specificity = sum(specificity.values()) / len(specificity)
            specificity_factor = 1.0 - avg_specificity  # عكس الخصوصية
        else:
            specificity_factor = 0.5

        # عامل المجالات
        domain_count = len([d for d in applicable_domains if d != "general"])
        domain_factor = min(1.0, domain_count * 0.25)

        # عامل معدل النجاح
        success_factor = skill.success_rate

        # الثقة المركبة
        confidence = (
            0.3 * specificity_factor
            + 0.4 * domain_factor
            + 0.3 * success_factor
        )

        return max(0.0, min(1.0, confidence))

    # =========================================================================
    # مساعدات التخزين — Storage Helpers
    # =========================================================================

    async def _store_generalization(self, gen: GeneralizedSkill) -> None:
        """تخزين تعميم — Store a generalization."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO skill_generalizations
                (generalized_skill_id, original_skill_id, generalized_rules,
                 applicable_domains, generalization_confidence,
                 domain_mappings, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                gen.generalized_skill_id,
                gen.original_skill_id,
                json.dumps(gen.generalized_rules, ensure_ascii=False),
                json.dumps(gen.applicable_domains, ensure_ascii=False),
                gen.generalization_confidence,
                json.dumps(gen.domain_mappings, ensure_ascii=False),
                time.time(),
            ))
            await db.commit()

    async def _store_domain_mapping(
        self, skill_id: str, mapping: DomainMapping
    ) -> None:
        """تخزين مطابقة مجال — Store a domain mapping."""
        mapping_id = f"dm_{uuid.uuid4().hex[:12]}"
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO skill_domain_mappings
                (mapping_id, source_domain, target_domain, source_skill_id,
                 rule_mappings, variable_mappings, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mapping_id,
                mapping.source_domain,
                mapping.target_domain,
                skill_id,
                json.dumps(mapping.rule_mappings, ensure_ascii=False),
                json.dumps(mapping.variable_mappings, ensure_ascii=False),
                mapping.confidence,
                time.time(),
            ))
            await db.commit()

    async def _store_merge(self, merged: MergedSkill) -> None:
        """تخزين دمج — Store a merge."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO skill_merges
                (merged_skill_id, source_skill_ids, merged_rules,
                 merged_variables, coverage_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                merged.merged_skill_id,
                json.dumps(merged.source_skill_ids),
                json.dumps(merged.merged_rules, ensure_ascii=False),
                json.dumps(merged.merged_variables, ensure_ascii=False),
                merged.coverage_score,
                time.time(),
            ))
            await db.commit()

    async def _get_skill_from_db(self, skill_id: str) -> Optional[LearnedSkill]:
        """استرجاع مهارة من قاعدة البيانات — Get a skill from the database."""
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM one_shot_skills WHERE skill_id = ?",
                (skill_id,),
            )
            row = await cursor.fetchone()
            if row:
                from mamoun.learning.one_shot_learner import OneShotLearner
                return OneShotLearner._row_to_skill(row)
        return None

    async def _get_all_skills_from_db(self) -> list[LearnedSkill]:
        """استرجاع جميع المهارات — Get all skills from the database."""
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM one_shot_skills ORDER BY success_rate DESC"
            )
            rows = await cursor.fetchall()
            from mamoun.learning.one_shot_learner import OneShotLearner
            return [OneShotLearner._row_to_skill(row) for row in rows]

    # =========================================================================
    # واجهة الحالة — Status Interface
    # =========================================================================

    def get_status(self) -> dict:
        """
        حالة النظام — Get the current status of the SkillGeneralizer.

        Returns:
            قاموس يحتوي على حالة النظام والإحصائيات
        """
        return {
            "module": "SkillGeneralizer",
            "enabled": ONE_SHOT_LEARNING_ENABLED,
            "running": self._running,
            "initialized": self._initialized,
            "total_generalized": self._total_generalized,
            "total_domain_mappings": self._total_domain_mappings,
            "total_merges": self._total_merges,
            "generalization_log_size": len(self._generalization_log),
            "last_activity_time": self._last_activity_time,
            "config": {
                "similarity_threshold": GENERALIZATION_SIMILARITY_THRESHOLD,
                "merge_min_overlap": MERGE_MIN_OVERLAP,
                "domain_vocabularies": list(DOMAIN_VOCABULARY.keys()),
            },
        }

    async def shutdown(self) -> None:
        """
        إيقاف النظام — Gracefully shut down the SkillGeneralizer.

        يقوم بتنظيف الموارد وتحديث الإحصائيات.
        """
        logger.info(
            "إيقاف المعمِّم للمهارات — تعاميم: %d، مطابقات: %d، دموج: %d",
            self._total_generalized, self._total_domain_mappings,
            self._total_merges,
        )
        self._running = False
        self._generalization_log.clear()
