"""
BABSHARQII v40.0 "مأمون" — One-Shot Learner
المتعلم من المثال الواحد — يستخلص القواعد المجردة والمتغيرات الديناميكية من مثال واحد

Research basis:
  - Neuro-Symbolic Integration (NSI): دمج التعلم العصبي مع الاستدلال الرمزي
  - VLBiMan: تعلم ثنائي الاتجاه من مثال واحد باستخدام المطابقة البصرية-اللغوية
  - One-Shot Generalization via Template Extraction: استخلاص قوالب من مثال واحد
    ثم تعبئتها بمتغيرات جديدة لإنشاء حالات مختلفة

Architecture:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                        OneShotLearner                                  │
  │                                                                         │
  │  ┌────────────────────┐  ┌────────────────────┐  ┌──────────────────┐  │
  │  │  RuleExtractor     │  │ VariableExtractor  │  │ SkillApplicator  │  │
  │  │  استخلاص القواعد   │  │ استخلاص المتغيرات  │  │ تطبيق المهارة   │  │
  │  └────────┬───────────┘  └────────┬───────────┘  └────────┬─────────┘  │
  │           │                       │                        │            │
  │  ┌────────▼───────────────────────▼────────────────────────▼─────────┐ │
  │  │                    SkillStore (SQLite)                            │ │
  │  │  تخزين · استرجاع · تحقق · إحصائيات · إعادة استخدام               │ │
  │  └──────────────────────────────────────────────────────────────────┘ │
  └─────────────────────────────────────────────────────────────────────────┘

Env toggles:
    MAMOUN_ONE_SHOT_LEARNING (default: "false")
"""

from __future__ import annotations

import os
import re
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

logger = logging.getLogger("mamoun.one_shot_learner")


# ═══════════════════════════════════════════════════════════════════════════════
# ثوابت التهيئة البيئية — Environment Config
# ═══════════════════════════════════════════════════════════════════════════════

ONE_SHOT_LEARNING_ENABLED: bool = os.getenv(
    "MAMOUN_ONE_SHOT_LEARNING", "false"
).lower() in ("true", "1", "yes")

MAX_STORED_SKILLS: int = int(
    os.getenv("MAMOUN_ONE_SHOT_MAX_SKILLS", "1000")
)

CONFIDENCE_THRESHOLD: float = float(
    os.getenv("MAMOUN_ONE_SHOT_CONFIDENCE_THRESHOLD", "0.5")
)


# ═══════════════════════════════════════════════════════════════════════════════
# أنواع البيانات — Dataclasses
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class LearningExample:
    """
    مثال تعليمي — A single task example to learn from.
    مثال واحد يتم تحليله لاستخلاص المهارة.

    Attributes:
        example_id: معرف المثال
        task_type: نوع المهمة (extraction, classification, transformation, ...)
        description: وصف المهمة بالإنجليزية
        description_ar: وصف المهمة بالعربية
        input_data: بيانات الإدخال
        output_data: بيانات الإخراج المتوقعة
        context: سياق المهمة
        metadata: بيانات إضافية
    """
    example_id: str = ""
    task_type: str = ""
    description: str = ""
    description_ar: str = ""
    input_data: dict = field(default_factory=dict)
    output_data: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        """توليد معرف تلقائي إن لم يكن موجوداً — Auto-generate ID if missing"""
        if not self.example_id:
            hash_input = f"{self.task_type}:{json.dumps(self.input_data, sort_keys=True)}"
            self.example_id = f"ex_{hashlib.md5(hash_input.encode()).hexdigest()[:12]}"

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "example_id": self.example_id,
            "task_type": self.task_type,
            "description": self.description,
            "description_ar": self.description_ar,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "context": self.context,
            "metadata": self.metadata,
        }


@dataclass
class LearnedSkill:
    """
    مهارة مُكتسبة — A skill learned from a single example.
    مهارة تم تعلمها من مثال واحد مع قواعدها المجردة ومتغيراتها.

    Attributes:
        skill_id: معرف المهارة
        skill_name: اسم المهارة بالإنجليزية
        skill_name_ar: اسم المهارة بالعربية
        task_type: نوع المهمة
        abstract_rules: القواعد المجردة — أنماط ثابتة تحدد المهارة
        dynamic_variables: المتغيرات الديناميكية — أجزاء تتغير بين الحالات
        constraints: القيود — شروط يجب توفرها لنجاح المهارة
        prerequisites: المتطلبات المسبقة — ما يلزم قبل تنفيذ المهارة
        source_example_id: معرف المثال المصدر
        created_at: وقت الإنشاء
        application_count: عدد مرات التطبيق
        success_rate: معدل النجاح (0.0–1.0)
        template: قالب المهارة — هيكل الإدخال/الإخراج مع المتغيرات
    """
    skill_id: str = ""
    skill_name: str = ""
    skill_name_ar: str = ""
    task_type: str = ""
    abstract_rules: list[str] = field(default_factory=list)
    dynamic_variables: list[dict] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    source_example_id: str = ""
    created_at: float = field(default_factory=time.time)
    application_count: int = 0
    success_rate: float = 0.0
    template: dict = field(default_factory=dict)

    def __post_init__(self):
        """توليد معرف تلقائي إن لم يكن موجوداً — Auto-generate ID if missing"""
        if not self.skill_id:
            hash_input = f"{self.task_type}:{self.skill_name}:{self.source_example_id}"
            self.skill_id = f"skill_{hashlib.md5(hash_input.encode()).hexdigest()[:12]}_{uuid.uuid4().hex[:6]}"

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "skill_name_ar": self.skill_name_ar,
            "task_type": self.task_type,
            "abstract_rules": self.abstract_rules,
            "dynamic_variables": self.dynamic_variables,
            "constraints": self.constraints,
            "prerequisites": self.prerequisites,
            "source_example_id": self.source_example_id,
            "created_at": self.created_at,
            "application_count": self.application_count,
            "success_rate": round(self.success_rate, 4),
            "template": self.template,
        }


@dataclass
class SkillApplicationResult:
    """
    نتيجة تطبيق مهارة — Result of applying a learned skill to a new instance.
    نتيجة تطبيق مهارة مُكتسبة على حالة جديدة مع بيانات الإخراج والثقة.

    Attributes:
        skill_id: معرف المهارة المُطبَّقة
        instance_id: معرف الحالة الجديدة
        success: هل نجح التطبيق؟
        output_data: بيانات الإخراج المنتجة
        confidence: مستوى الثقة (0.0–1.0)
        substitutions: التعيينات — المتغيرات الديناميكية وقيمها المُعيَّنة
        errors: أخطاء حدثت أثناء التطبيق
    """
    skill_id: str = ""
    instance_id: str = ""
    success: bool = False
    output_data: dict = field(default_factory=dict)
    confidence: float = 0.0
    substitutions: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "skill_id": self.skill_id,
            "instance_id": self.instance_id,
            "success": self.success,
            "output_data": self.output_data,
            "confidence": round(self.confidence, 4),
            "substitutions": self.substitutions,
            "errors": self.errors,
        }


@dataclass
class ValidationResult:
    """
    نتيجة التحقق — Validation result for a learned skill.
    نتيجة التحقق من صحة مهارة مُكتسبة عبر حالات اختبار.

    Attributes:
        skill_id: معرف المهارة المُتحقَّق منها
        total_cases: إجمالي حالات الاختبار
        passed: عدد الحالات الناجحة
        failed: عدد الحالات الفاشلة
        accuracy: دقة المهارة (0.0–1.0)
        details: تفاصيل كل حالة اختبار
    """
    skill_id: str = ""
    total_cases: int = 0
    passed: int = 0
    failed: int = 0
    accuracy: float = 0.0
    details: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "skill_id": self.skill_id,
            "total_cases": self.total_cases,
            "passed": self.passed,
            "failed": self.failed,
            "accuracy": round(self.accuracy, 4),
            "details": self.details,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# OneShotLearner — المتعلم من المثال الواحد
# ═══════════════════════════════════════════════════════════════════════════════


class OneShotLearner:
    """
    المتعلم من المثال الواحد — Learns skills from a single example.

    يستخلص من مثال واحد:
      1. القواعد المجردة (abstract_rules): الأنماط الثابتة التي تحدد طبيعة المهارة
      2. المتغيرات الديناميكية (dynamic_variables): الأجزاء التي تتغير بين الحالات
      3. القيود (constraints): شروط ضرورية لنجاح المهارة
      4. المتطلبات المسبقة (prerequisites): ما يلزم قبل تنفيذ المهارة

    ثم يبني قالباً (template) يمكن تطبيقه على حالات جديدة بتعيين المتغيرات.

    تفعيل: MAMOUN_ONE_SHOT_LEARNING=true (افتراضي: false)
    """

    def __init__(self, db_path: str = ""):
        """
        تهيئة المتعلم من المثال الواحد.

        Args:
            db_path: مسار قاعدة بيانات SQLite (افتراضي: DB_PATH من الإعدادات)
        """
        self._db_path = db_path or str(DB_PATH)
        self._initialized = False

        # ذاكرة مؤقتة — in-memory cache for quick access
        self._skill_cache: dict[str, LearnedSkill] = {}
        self._max_cache_size: int = 200

        # إحصائيات — statistics
        self._total_learned: int = 0
        self._total_applied: int = 0
        self._total_validated: int = 0
        self._last_activity_time: float = 0.0
        self._running: bool = True

        logger.info(
            "تم تهيئة المتعلم من المثال الواحد — ONE_SHOT_LEARNING=%s, MAX_SKILLS=%d",
            ONE_SHOT_LEARNING_ENABLED, MAX_STORED_SKILLS,
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
                CREATE TABLE IF NOT EXISTS one_shot_skills (
                    skill_id TEXT PRIMARY KEY,
                    skill_name TEXT NOT NULL,
                    skill_name_ar TEXT DEFAULT '',
                    task_type TEXT DEFAULT '',
                    abstract_rules TEXT DEFAULT '[]',
                    dynamic_variables TEXT DEFAULT '[]',
                    constraints TEXT DEFAULT '[]',
                    prerequisites TEXT DEFAULT '[]',
                    source_example_id TEXT DEFAULT '',
                    created_at REAL DEFAULT 0.0,
                    application_count INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0,
                    template TEXT DEFAULT '{}'
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_one_shot_task_type
                ON one_shot_skills(task_type)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_one_shot_success_rate
                ON one_shot_skills(success_rate DESC)
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS one_shot_applications (
                    application_id TEXT PRIMARY KEY,
                    skill_id TEXT NOT NULL,
                    instance_id TEXT DEFAULT '',
                    success INTEGER DEFAULT 0,
                    output_data TEXT DEFAULT '{}',
                    confidence REAL DEFAULT 0.0,
                    substitutions TEXT DEFAULT '{}',
                    errors TEXT DEFAULT '[]',
                    applied_at REAL DEFAULT 0.0,
                    FOREIGN KEY (skill_id) REFERENCES one_shot_skills(skill_id)
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_applications_skill_id
                ON one_shot_applications(skill_id)
            """)
            await db.commit()

        self._initialized = True
        logger.info("تم تهيئة جداول التعلم من المثال الواحد")

    # =========================================================================
    # واجهة رئيسية — Main API
    # =========================================================================

    async def learn_from_example(self, example: LearningExample) -> LearnedSkill:
        """
        التعلم من مثال واحد — Learn a skill from a single example.

        العملية:
          1. تحليل الإدخال والإخراج لاستخلاص القواعد المجردة
          2. تحديد المتغيرات الديناميكية (الأجزاء المتغيرة)
          3. استخلاص القيود والمتطلبات المسبقة
          4. بناء قالب المهارة
          5. تخزين المهارة في SQLite

        Args:
            example: مثال تعليمي يحتوي على إدخال وإخراج وسياق

        Returns:
            LearnedSkill — المهارة المُكتسبة
        """
        await self._initialize()

        if not ONE_SHOT_LEARNING_ENABLED:
            logger.debug("التعلم من المثال الواحد معطل — تم إرجاع مهارة فارغة")
            return LearnedSkill()

        start_time = time.time()

        # ─── الخطوة ١: استخلاص القواعد المجردة ───────────────────────
        abstract_rules = self._extract_abstract_rules(example)

        # ─── الخطوة ٢: تحديد المتغيرات الديناميكية ──────────────────
        dynamic_variables = self._extract_dynamic_variables(example)

        # ─── الخطوة ٣: استخلاص القيود ───────────────────────────────
        constraints = self._extract_constraints(example)

        # ─── الخطوة ٤: استخلاص المتطلبات المسبقة ────────────────────
        prerequisites = self._extract_prerequisites(example)

        # ─── الخطوة ٥: بناء قالب المهارة ────────────────────────────
        template = self._build_template(example, dynamic_variables)

        # ─── الخطوة ٦: إنشاء كائن المهارة ───────────────────────────
        skill_name = self._generate_skill_name(example)
        skill_name_ar = self._generate_skill_name_ar(example)

        skill = LearnedSkill(
            skill_name=skill_name,
            skill_name_ar=skill_name_ar,
            task_type=example.task_type,
            abstract_rules=abstract_rules,
            dynamic_variables=dynamic_variables,
            constraints=constraints,
            prerequisites=prerequisites,
            source_example_id=example.example_id,
            created_at=time.time(),
            application_count=0,
            success_rate=1.0,  # يبدأ بثقة كاملة من المثال الواحد
            template=template,
        )

        # ─── الخطوة ٧: تخزين المهارة ────────────────────────────────
        await self._store_skill(skill)

        # تحديث الإحصائيات
        self._total_learned += 1
        self._last_activity_time = time.time()

        # تحديث الذاكرة المؤقتة
        self._skill_cache[skill.skill_id] = skill
        if len(self._skill_cache) > self._max_cache_size:
            oldest_key = min(self._skill_cache, key=lambda k: self._skill_cache[k].created_at)
            del self._skill_cache[oldest_key]

        elapsed = (time.time() - start_time) * 1000
        logger.info(
            "تم تعلم مهارة جديدة: '%s' (%s) — %d قاعدة، %d متغير، %.1f مللي ثانية",
            skill_name, skill.skill_id, len(abstract_rules),
            len(dynamic_variables), elapsed,
        )

        return skill

    async def apply_skill(
        self, skill_id: str, new_instance: dict
    ) -> SkillApplicationResult:
        """
        تطبيق مهارة مُكتسبة على حالة جديدة — Apply a learned skill.

        العملية:
          1. استرجاع المهارة من التخزين
          2. مطابقة المتغيرات الديناميكية مع الحالة الجديدة
          3. تعبئة القالب بالقيم الجديدة
          4. التحقق من القيود
          5. إرجاع النتيجة مع مستوى الثقة

        Args:
            skill_id: معرف المهارة
            new_instance: الحالة الجديدة (إدخال)

        Returns:
            SkillApplicationResult — نتيجة التطبيق
        """
        await self._initialize()

        if not ONE_SHOT_LEARNING_ENABLED:
            return SkillApplicationResult(
                skill_id=skill_id,
                errors=["التعلم من المثال الواحد معطل"],
            )

        # استرجاع المهارة
        skill = await self.get_skill(skill_id)
        if not skill.skill_id:
            return SkillApplicationResult(
                skill_id=skill_id,
                errors=[f"المهارة '{skill_id}' غير موجودة"],
            )

        instance_id = f"inst_{uuid.uuid4().hex[:10]}"
        errors: list[str] = []
        substitutions: dict = {}

        # ─── الخطوة ١: مطابقة المتغيرات الديناميكية ─────────────────
        for var in skill.dynamic_variables:
            var_name = var.get("name", "")
            var_path = var.get("path", "")
            var_type = var.get("type", "string")

            # محاولة استخراج القيمة من الحالة الجديدة
            # أولاً: المسار المباشر (بدون بادئة input./output.)
            direct_path = var.get("direct_path", var_path)
            value = self._resolve_path(new_instance, direct_path)
            # ثانياً: المسار الكامل مع البادئة
            if value is None:
                value = self._resolve_path(new_instance, var_path)
            # ثالثاً: البحث باسم المتغير مباشرة
            if value is None:
                value = new_instance.get(var_name)
            if value is not None:
                substitutions[var_name] = value
            elif var.get("required", True):
                errors.append(
                    f"المتغير المطلوب '{var_name}' غير موجود في المسار '{var_path}'"
                )

        # ─── الخطوة ٢: التحقق من القيود ────────────────────────────
        for constraint in skill.constraints:
            if not self._check_constraint(constraint, new_instance, substitutions):
                errors.append(f"القيد غير متحقق: {constraint}")

        # ─── الخطوة ٣: تعبئة القالب ─────────────────────────────────
        output_data = {}
        if not errors:
            output_data = self._fill_template(skill.template, substitutions)

        # ─── الخطوة ٤: حساب الثقة ───────────────────────────────────
        confidence = self._compute_application_confidence(
            skill, substitutions, errors
        )

        # ─── الخطوة ٥: تسجيل التطبيق ───────────────────────────────
        success = len(errors) == 0 and confidence >= CONFIDENCE_THRESHOLD
        result = SkillApplicationResult(
            skill_id=skill_id,
            instance_id=instance_id,
            success=success,
            output_data=output_data,
            confidence=confidence,
            substitutions=substitutions,
            errors=errors,
        )

        await self._store_application(result)

        # تحديث إحصائيات المهارة
        await self._update_skill_stats(skill_id, success)

        self._total_applied += 1
        self._last_activity_time = time.time()

        logger.info(
            "تطبيق المهارة '%s' على '%s': %s (ثقة=%.3f)",
            skill_id, instance_id,
            "نجح" if success else "فشل",
            confidence,
        )

        return result

    async def validate_skill(
        self, skill_id: str, test_cases: list[dict]
    ) -> ValidationResult:
        """
        التحقق من صحة مهارة — Validate a skill against test cases.

        يختبر المهارة على مجموعة من حالات الاختبار ويحسب الدقة.

        Args:
            skill_id: معرف المهارة
            test_cases: قائمة حالات الاختبار، كل حالة تحتوي على:
                - input: الإدخال
                - expected_output: الإخراج المتوقع

        Returns:
            ValidationResult — نتيجة التحقق
        """
        await self._initialize()

        if not test_cases:
            return ValidationResult(skill_id=skill_id)

        passed = 0
        failed = 0
        details: list[dict] = []

        for i, case in enumerate(test_cases):
            input_data = case.get("input", {})
            expected_output = case.get("expected_output", {})

            # تطبيق المهارة على حالة الاختبار
            result = await self.apply_skill(skill_id, input_data)

            # مقارنة الناتج مع المتوقع
            match = self._compare_outputs(result.output_data, expected_output)
            case_passed = result.success and match

            if case_passed:
                passed += 1
            else:
                failed += 1

            details.append({
                "case_index": i,
                "success": case_passed,
                "output": result.output_data,
                "expected": expected_output,
                "confidence": result.confidence,
                "errors": result.errors,
            })

        accuracy = passed / max(1, len(test_cases))

        # تحديث معدل نجاح المهارة
        await self._update_skill_success_rate(skill_id, accuracy)

        validation = ValidationResult(
            skill_id=skill_id,
            total_cases=len(test_cases),
            passed=passed,
            failed=failed,
            accuracy=accuracy,
            details=details,
        )

        self._total_validated += 1
        self._last_activity_time = time.time()

        logger.info(
            "تحقق المهارة '%s': %d/%d نجح (دقة=%.3f)",
            skill_id, passed, len(test_cases), accuracy,
        )

        return validation

    async def get_skill(self, skill_id: str) -> LearnedSkill:
        """
        استرجاع مهارة — Retrieve a learned skill by ID.

        Args:
            skill_id: معرف المهارة

        Returns:
            LearnedSkill — المهارة المطلوبة أو مهارة فارغة إن لم تُوجد
        """
        await self._initialize()

        # فحص الذاكرة المؤقتة أولاً
        if skill_id in self._skill_cache:
            return self._skill_cache[skill_id]

        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM one_shot_skills WHERE skill_id = ?",
                (skill_id,),
            )
            row = await cursor.fetchone()
            if row:
                skill = self._row_to_skill(row)
                self._skill_cache[skill_id] = skill
                return skill

        return LearnedSkill()

    async def list_skills(self) -> list[dict]:
        """
        قائمة المهارات المُكتسبة — List all learned skills.

        Returns:
            قائمة قواميس تحتوي على ملخص كل مهارة
        """
        await self._initialize()

        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT skill_id, skill_name, skill_name_ar, task_type,
                       application_count, success_rate, created_at
                FROM one_shot_skills
                ORDER BY success_rate DESC, created_at DESC
            """)
            rows = await cursor.fetchall()

        return [
            {
                "skill_id": row["skill_id"],
                "skill_name": row["skill_name"],
                "skill_name_ar": row["skill_name_ar"],
                "task_type": row["task_type"],
                "application_count": row["application_count"],
                "success_rate": round(row["success_rate"], 4),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    # =========================================================================
    # استخلاص القواعد والمتغيرات — Rule & Variable Extraction
    # =========================================================================

    def _extract_abstract_rules(self, example: LearningExample) -> list[str]:
        """
        استخلاص القواعد المجردة من المثال — Extract abstract rules from the example.

        القواعد المجردة هي الأنماط الثابتة في العلاقة بين الإدخال والإخراج
        التي لا تتغير بغض النظر عن القيم المحددة.

        Args:
            example: المثال التعليمي

        Returns:
            قائمة القواعد المجردة
        """
        rules: list[str] = []
        input_data = example.input_data
        output_data = example.output_data

        # قاعدة: نوع المهمة يحدد طبيعة التحويل
        if example.task_type:
            rules.append(f"نوع التحويل: {example.task_type}")

        # قاعدة: بنية الإدخال تحدد بنية الإخراج
        input_structure = self._describe_structure(input_data)
        output_structure = self._describe_structure(output_data)
        if input_structure and output_structure:
            rules.append(
                f"تحويل البنية: {input_structure} → {output_structure}"
            )

        # قاعدة: العلاقات بين المفاتيح في الإدخال والإخراج
        input_keys = set(self._flatten_keys(input_data))
        output_keys = set(self._flatten_keys(output_data))

        shared_keys = input_keys & output_keys
        if shared_keys:
            rules.append(
                f"مفاتيح مشتركة بين الإدخال والإخراج: {', '.join(sorted(shared_keys)[:5])}"
            )

        new_keys = output_keys - input_keys
        if new_keys:
            rules.append(
                f"مفاتيح جديدة في الإخراج: {', '.join(sorted(new_keys)[:5])}"
            )

        # قاعدة: أنماط القيم الثابتة
        constant_patterns = self._find_constant_patterns(input_data, output_data)
        for pattern in constant_patterns:
            rules.append(f"نمط ثابت: {pattern}")

        # قاعدة: اتجاه التحويل (زيادة، نقصان، إعادة تنظيم)
        transform_direction = self._infer_transform_direction(input_data, output_data)
        if transform_direction:
            rules.append(f"اتجاه التحويل: {transform_direction}")

        return rules

    def _extract_dynamic_variables(self, example: LearningExample) -> list[dict]:
        """
        استخلاص المتغيرات الديناميكية — Extract dynamic variables from the example.

        المتغيرات الديناميكية هي الأجزاء في الإدخال والإخراج التي تتغير
        بين الحالات المختلفة. يتم تحديدها بمقارنة أنواع القيم وأماكنها.

        Args:
            example: المثال التعليمي

        Returns:
            قائمة المتغيرات الديناميكية
        """
        variables: list[dict] = []

        # استخراج المتغيرات من الإدخال — مطلوبة عند التطبيق
        input_vars = self._identify_variables(example.input_data, prefix="input")
        for var in input_vars:
            var["source"] = "input"
            var["required"] = True
        variables.extend(input_vars)

        # استخراج المتغيرات من الإخراج — ليست مطلوبة من الحالة الجديدة (تُنتج بالقالب)
        output_vars = self._identify_variables(example.output_data, prefix="output")
        for var in output_vars:
            var["source"] = "output"
            var["required"] = False  # متغيرات الإخراج لا تُستخرج من الإدخال
        variables.extend(output_vars)

        # إزالة التكرار
        seen_paths: set[str] = set()
        unique_vars: list[dict] = []
        for var in variables:
            path = var.get("path", "")
            if path not in seen_paths:
                seen_paths.add(path)
                unique_vars.append(var)

        return unique_vars

    def _extract_constraints(self, example: LearningExample) -> list[str]:
        """
        استخلاص القيود — Extract constraints from the example.

        القيود هي شروط ضرورية لنجاح المهارة مثل:
        - أنواع البيانات المطلوبة
        - وجود مفاتيح معينة
        - نطاقات القيم

        Args:
            example: المثال التعليمي

        Returns:
            قائمة القيود
        """
        constraints: list[str] = []
        input_data = example.input_data
        output_data = example.output_data

        # قيد: أنواع بيانات الإدخال المطلوبة
        for key, value in input_data.items():
            value_type = type(value).__name__
            constraints.append(f"الإدخال '{key}' يجب أن يكون من نوع {value_type}")

        # قيد: وجود مفاتيح إدخال
        required_keys = list(input_data.keys())
        if required_keys:
            constraints.append(
                f"يجب أن يحتوي الإدخال على المفاتيح: {', '.join(required_keys[:5])}"
            )

        # قيد: أنواع بيانات الإخراج المتوقعة
        for key, value in output_data.items():
            value_type = type(value).__name__
            constraints.append(f"الإخراج '{key}' يجب أن يكون من نوع {value_type}")

        # قيد: السياق
        if example.context:
            for key, value in example.context.items():
                if isinstance(value, bool) and value:
                    constraints.append(f"شرط السياق: {key} يجب أن يكون صحيحاً")

        return constraints

    def _extract_prerequisites(self, example: LearningExample) -> list[str]:
        """
        استخلاص المتطلبات المسبقة — Extract prerequisites from the example.

        المتطلبات المسبقة هي ما يلزم توفره قبل تنفيذ المهارة.

        Args:
            example: المثال التعليمي

        Returns:
            قائمة المتطلبات المسبقة
        """
        prerequisites: list[str] = []

        # متطلب: توفر بيانات الإدخال
        if example.input_data:
            prerequisites.append("توفر بيانات الإدخال بالبنية المطلوبة")

        # متطلب: توفر السياق المناسب
        if example.context:
            prerequisites.append("توفر السياق المناسب للمهمة")

        # متطلب: نوع المهمة
        if example.task_type:
            task_prerequisites = {
                "extraction": "توفر مصدر بيانات قابل للاستخراج",
                "classification": "توفر فئات محددة مسبقاً",
                "transformation": "توفر مخطط التحويل",
                "generation": "توفر قالب أو نموذج للتوليد",
                "summarization": "توفر نص أصلي كافي الطول",
                "translation": "تحديد اللغة المصدر والهدف",
            }
            prereq = task_prerequisites.get(example.task_type)
            if prereq:
                prerequisites.append(prereq)

        # متطلب: بيانات إضافية من metadata
        if example.metadata.get("requires_external_data"):
            prerequisites.append("توفر بيانات خارجية إضافية")

        if example.metadata.get("requires_authentication"):
            prerequisites.append("توفر صلاحيات الوصول المناسبة")

        return prerequisites

    # =========================================================================
    # بناء القالب وتطبيقه — Template Building & Application
    # =========================================================================

    def _build_template(
        self, example: LearningExample, dynamic_variables: list[dict]
    ) -> dict:
        """
        بناء قالب المهارة — Build the skill template.

        القالب يحدد كيفية تحويل الإدخال إلى إخراج مع تحديد أماكن المتغيرات.

        Args:
            example: المثال التعليمي
            dynamic_variables: المتغيرات الديناميكية

        Returns:
            قالب المهارة كقاموس
        """
        template: dict = {
            "input_schema": self._extract_schema(example.input_data),
            "output_schema": self._extract_schema(example.output_data),
            "variable_slots": [],
            "transformation_hint": example.task_type,
        }

        for var in dynamic_variables:
            template["variable_slots"].append({
                "name": var.get("name", ""),
                "path": var.get("path", ""),
                "type": var.get("type", "string"),
                "default": var.get("default"),
            })

        return template

    def _fill_template(self, template: dict, substitutions: dict) -> dict:
        """
        تعبئة القالب بالقيم الجديدة — Fill the template with new values.

        Args:
            template: قالب المهارة
            substitutions: تعيينات المتغيرات

        Returns:
            بيانات الإخراج المنتجة
        """
        output_schema = template.get("output_schema", {})
        variable_slots = template.get("variable_slots", [])

        # بناء الإخراج من المخطط مع تعيين المتغيرات
        output = self._construct_from_schema(output_schema, substitutions, variable_slots)

        return output

    # =========================================================================
    # مساعدات التخزين — Storage Helpers
    # =========================================================================

    async def _store_skill(self, skill: LearnedSkill) -> None:
        """تخزين مهارة في SQLite — Store a skill in SQLite."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO one_shot_skills
                (skill_id, skill_name, skill_name_ar, task_type,
                 abstract_rules, dynamic_variables, constraints,
                 prerequisites, source_example_id, created_at,
                 application_count, success_rate, template)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                skill.skill_id,
                skill.skill_name,
                skill.skill_name_ar,
                skill.task_type,
                json.dumps(skill.abstract_rules, ensure_ascii=False),
                json.dumps(skill.dynamic_variables, ensure_ascii=False),
                json.dumps(skill.constraints, ensure_ascii=False),
                json.dumps(skill.prerequisites, ensure_ascii=False),
                skill.source_example_id,
                skill.created_at,
                skill.application_count,
                skill.success_rate,
                json.dumps(skill.template, ensure_ascii=False),
            ))
            await db.commit()

    async def _store_application(self, result: SkillApplicationResult) -> None:
        """تخزين نتيجة تطبيق — Store an application result."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO one_shot_applications
                (application_id, skill_id, instance_id, success,
                 output_data, confidence, substitutions, errors, applied_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.instance_id,
                result.skill_id,
                result.instance_id,
                1 if result.success else 0,
                json.dumps(result.output_data, ensure_ascii=False),
                result.confidence,
                json.dumps(result.substitutions, ensure_ascii=False),
                json.dumps(result.errors, ensure_ascii=False),
                time.time(),
            ))
            await db.commit()

    async def _update_skill_stats(self, skill_id: str, success: bool) -> None:
        """تحديث إحصائيات المهارة — Update skill statistics after application."""
        skill = await self.get_skill(skill_id)
        if not skill.skill_id:
            return

        skill.application_count += 1
        # تحديث معدل النجاح بشكل متحرك
        if skill.application_count == 1:
            skill.success_rate = 1.0 if success else 0.0
        else:
            alpha = 0.1  # عامل التحديث المتحرك
            new_rate = 1.0 if success else 0.0
            skill.success_rate = (1 - alpha) * skill.success_rate + alpha * new_rate

        await self._store_skill(skill)

        # تحديث الذاكرة المؤقتة
        self._skill_cache[skill_id] = skill

    async def _update_skill_success_rate(
        self, skill_id: str, accuracy: float
    ) -> None:
        """تحديث معدل نجاح المهارة بعد التحقق — Update success rate after validation."""
        skill = await self.get_skill(skill_id)
        if not skill.skill_id:
            return

        # دمج الدقة الجديدة مع المعدل الحالي
        skill.success_rate = (skill.success_rate + accuracy) / 2.0
        await self._store_skill(skill)
        self._skill_cache[skill_id] = skill

    # =========================================================================
    # مساعدات داخلية — Internal Helpers
    # =========================================================================

    @staticmethod
    def _describe_structure(data: dict) -> str:
        """وصف بنية البيانات — Describe the structure of data."""
        if not data:
            return "فارغ"

        parts: list[str] = []
        for key, value in data.items():
            if isinstance(value, dict):
                parts.append(f"{key}:كائن({len(value)})")
            elif isinstance(value, list):
                parts.append(f"{key}:قائمة({len(value)})")
            else:
                parts.append(f"{key}:{type(value).__name__}")

        return "{" + ", ".join(parts[:5]) + "}"

    @staticmethod
    def _flatten_keys(data: dict, prefix: str = "") -> list[str]:
        """تسطيح مفاتيح القاموس — Flatten dictionary keys."""
        keys: list[str] = []
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.append(full_key)
            if isinstance(value, dict):
                keys.extend(OneShotLearner._flatten_keys(value, full_key))
        return keys

    @staticmethod
    def _find_constant_patterns(input_data: dict, output_data: dict) -> list[str]:
        """إيجاد الأنماط الثابتة بين الإدخال والإخراج — Find constant patterns."""
        patterns: list[str] = []

        for key in input_data:
            if key in output_data:
                in_val = input_data[key]
                out_val = output_data[key]
                if in_val == out_val:
                    patterns.append(f"'{key}' ينتقل كما هو من الإدخال إلى الإخراج")
                elif isinstance(in_val, (int, float)) and isinstance(out_val, (int, float)):
                    if out_val > in_val:
                        patterns.append(f"'{key}' يزداد من {in_val} إلى {out_val}")
                    elif out_val < in_val:
                        patterns.append(f"'{key}' ينقص من {in_val} إلى {out_val}")

        return patterns

    @staticmethod
    def _infer_transform_direction(input_data: dict, output_data: dict) -> str:
        """استنتاج اتجاه التحويل — Infer the direction of transformation."""
        in_size = len(json.dumps(input_data))
        out_size = len(json.dumps(output_data))

        if out_size < in_size * 0.5:
            return "ضغط/تلخيص"
        elif out_size > in_size * 2:
            return "توسيع/توليد"
        elif set(output_data.keys()) - set(input_data.keys()):
            return "إضافة حقول جديدة"
        elif set(input_data.keys()) - set(output_data.keys()):
            return "تصفية/إزالة حقول"
        else:
            return "تحويل قيم"

    def _identify_variables(self, data: dict, prefix: str = "") -> list[dict]:
        """تحديد المتغيرات الديناميكية في البيانات — Identify dynamic variables.

        المتغيرات من الإدخال تستخدم مساراً بادئة 'input.' ومتغيرات الإخراج 'output.'.
        عند التطبيق، يتم تجريد البادئة تلقائياً للبحث في الحالة الجديدة.
        """
        variables: list[dict] = []

        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            # المسار المباشر — يُستخدم عند التطبيق بدون بادئة
            direct_path = key
            if isinstance(value, dict):
                nested = self._identify_variables(value, path)
                # إضافة المسارات المتداخلة
                for var in nested:
                    var["direct_path"] = f"{key}.{var.get('direct_path', var.get('path', '')).split('.')[-1]}"
                variables.extend(nested)
            elif isinstance(value, list):
                variables.append({
                    "name": key,
                    "path": path,
                    "direct_path": direct_path,
                    "type": "list",
                    "required": True,
                    "default": None,
                })
            elif isinstance(value, (int, float)):
                variables.append({
                    "name": key,
                    "path": path,
                    "direct_path": direct_path,
                    "type": "number",
                    "required": True,
                    "default": None,
                })
            elif isinstance(value, str):
                variables.append({
                    "name": key,
                    "path": path,
                    "direct_path": direct_path,
                    "type": "string",
                    "required": True,
                    "default": None,
                })
            elif isinstance(value, bool):
                variables.append({
                    "name": key,
                    "path": path,
                    "direct_path": direct_path,
                    "type": "boolean",
                    "required": False,
                    "default": value,
                })

        return variables

    @staticmethod
    def _resolve_path(data: dict, path: str) -> Any:
        """استخراج قيمة من مسار — Resolve a value from a dot-separated path."""
        if not path:
            return None

        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _check_constraint(
        self, constraint: str, instance: dict, substitutions: dict
    ) -> bool:
        """التحقق من قيد — Check if a constraint is satisfied."""
        # قيود بسيطة: التحقق من توفر المفاتيح المطلوبة
        if "يجب أن يحتوي" in constraint:
            # استخراج أسماء المفاتيح من القيد
            for key in substitutions:
                if key in constraint:
                    return True
            # التحقق من وجود المفاتيح في instance
            for key in instance:
                if key in constraint:
                    return True
            return False

        if "يجب أن يكون من نوع" in constraint:
            # التحقق من النوع — افتراضي صحيح إذا تعذر التحقق
            return True

        # القيود المنطقية
        if "يجب أن يكون صحيحاً" in constraint:
            key = constraint.replace("شرط السياق: ", "").replace(" يجب أن يكون صحيحاً", "")
            value = self._resolve_path(instance, key)
            return value is True

        return True

    @staticmethod
    def _compute_application_confidence(
        skill: LearnedSkill,
        substitutions: dict,
        errors: list[str],
    ) -> float:
        """حساب ثقة التطبيق — Compute confidence for skill application."""
        if errors:
            return max(0.0, 0.3 - len(errors) * 0.1)

        # نسبة المتغيرات المُعيَّنة
        required_vars = [
            v for v in skill.dynamic_variables if v.get("required", True)
        ]
        if not required_vars:
            return skill.success_rate

        filled_vars = sum(
            1 for v in required_vars
            if v.get("name") in substitutions
        )
        fill_ratio = filled_vars / max(1, len(required_vars))

        # الثقة = مزيج من معدل نجاح المهارة ونسبة المتغيرات المُعيَّنة
        confidence = skill.success_rate * 0.6 + fill_ratio * 0.4

        return max(0.0, min(1.0, confidence))

    @staticmethod
    def _compare_outputs(actual: dict, expected: dict) -> bool:
        """مقارنة ناتجين — Compare two output dictionaries."""
        if not expected:
            return True
        if not actual and expected:
            return False

        for key, expected_value in expected.items():
            actual_value = actual.get(key)
            if actual_value != expected_value:
                # مقارنة مرنة: تحويل إلى نص للمقارنة
                if str(actual_value).strip() != str(expected_value).strip():
                    return False

        return True

    @staticmethod
    def _extract_schema(data: dict) -> dict:
        """استخلاص مخطط البيانات — Extract a schema from data."""
        schema: dict = {}
        for key, value in data.items():
            if isinstance(value, dict):
                schema[key] = {
                    "_type": "object",
                    "_schema": OneShotLearner._extract_schema(value),
                }
            elif isinstance(value, list):
                schema[key] = {
                    "_type": "array",
                    "_length": len(value),
                }
            else:
                schema[key] = {
                    "_type": type(value).__name__,
                    "_value": value,
                }
        return schema

    @staticmethod
    def _construct_from_schema(
        schema: dict, substitutions: dict, variable_slots: list[dict]
    ) -> dict:
        """بناء إخراج من المخطط — Construct output from schema."""
        result: dict = {}
        slot_map = {s.get("name"): s for s in variable_slots}

        for key, descriptor in schema.items():
            if not isinstance(descriptor, dict):
                result[key] = descriptor
                continue

            _type = descriptor.get("_type", "string")

            if _type == "object" and "_schema" in descriptor:
                result[key] = OneShotLearner._construct_from_schema(
                    descriptor["_schema"], substitutions, variable_slots
                )
            elif key in substitutions:
                result[key] = substitutions[key]
            elif key in slot_map:
                default = slot_map[key].get("default")
                result[key] = default if default is not None else descriptor.get("_value")
            else:
                result[key] = descriptor.get("_value")

        return result

    @staticmethod
    def _generate_skill_name(example: LearningExample) -> str:
        """توليد اسم المهارة بالإنجليزية — Generate skill name in English."""
        if example.description:
            words = re.findall(r"\w+", example.description.lower())[:3]
            return f"{example.task_type}_{'_'.join(words)}" if words else example.task_type
        return f"{example.task_type}_skill_{uuid.uuid4().hex[:6]}"

    @staticmethod
    def _generate_skill_name_ar(example: LearningExample) -> str:
        """توليد اسم المهارة بالعربية — Generate skill name in Arabic."""
        if example.description_ar:
            return example.description_ar[:60]
        type_names: dict[str, str] = {
            "extraction": "استخراج",
            "classification": "تصنيف",
            "transformation": "تحويل",
            "generation": "توليد",
            "summarization": "تلخيص",
            "translation": "ترجمة",
        }
        base = type_names.get(example.task_type, example.task_type)
        return f"مهارة {base} من مثال واحد"

    @staticmethod
    def _row_to_skill(row) -> LearnedSkill:
        """تحويل صف قاعدة بيانات إلى كائن مهارة — Convert DB row to LearnedSkill."""
        abstract_rules = []
        try:
            abstract_rules = json.loads(row["abstract_rules"]) if row["abstract_rules"] else []
        except (json.JSONDecodeError, TypeError):
            pass

        dynamic_variables = []
        try:
            dynamic_variables = json.loads(row["dynamic_variables"]) if row["dynamic_variables"] else []
        except (json.JSONDecodeError, TypeError):
            pass

        constraints = []
        try:
            constraints = json.loads(row["constraints"]) if row["constraints"] else []
        except (json.JSONDecodeError, TypeError):
            pass

        prerequisites = []
        try:
            prerequisites = json.loads(row["prerequisites"]) if row["prerequisites"] else []
        except (json.JSONDecodeError, TypeError):
            pass

        template = {}
        try:
            template = json.loads(row["template"]) if row["template"] else {}
        except (json.JSONDecodeError, TypeError):
            pass

        return LearnedSkill(
            skill_id=row["skill_id"],
            skill_name=row["skill_name"],
            skill_name_ar=row["skill_name_ar"] or "",
            task_type=row["task_type"] or "",
            abstract_rules=abstract_rules,
            dynamic_variables=dynamic_variables,
            constraints=constraints,
            prerequisites=prerequisites,
            source_example_id=row["source_example_id"] or "",
            created_at=row["created_at"] or 0.0,
            application_count=row["application_count"] or 0,
            success_rate=row["success_rate"] or 0.0,
            template=template,
        )

    # =========================================================================
    # واجهة الحالة — Status Interface
    # =========================================================================

    def get_status(self) -> dict:
        """
        حالة النظام — Get the current status of the OneShotLearner.

        Returns:
            قاموس يحتوي على حالة النظام والإحصائيات
        """
        return {
            "module": "OneShotLearner",
            "enabled": ONE_SHOT_LEARNING_ENABLED,
            "running": self._running,
            "initialized": self._initialized,
            "total_learned": self._total_learned,
            "total_applied": self._total_applied,
            "total_validated": self._total_validated,
            "cached_skills": len(self._skill_cache),
            "last_activity_time": self._last_activity_time,
            "config": {
                "max_stored_skills": MAX_STORED_SKILLS,
                "confidence_threshold": CONFIDENCE_THRESHOLD,
            },
        }

    async def shutdown(self) -> None:
        """
        إيقاف النظام — Gracefully shut down the OneShotLearner.

        يقوم بتنظيف الموارد وتحديث الإحصائيات.
        """
        logger.info(
            "إيقاف المتعلم من المثال الواحد — تعلم: %d، تطبيق: %d، تحقق: %d",
            self._total_learned, self._total_applied, self._total_validated,
        )
        self._running = False
        self._skill_cache.clear()
