"""
VariantArchive v59.2 — أرشيف المتغيرات المستوحى من Darwin-Godel Machine

Inspired by: JennyZZT/dgm (2026) — Archive of code variants with fitness tracking

CRITICAL FIX from v59:
- v59: EvolutionLoopV2 يحفظ فقط بيانات meta-cognition (لا كود)
- v59.2: VariantArchive يحفظ الكود الفعلي + النتائج + الـ fitness
- كل نسخة كود تُسجَّل مع: timestamp, fitness, reliability, diff
- Rollback يُعيد الكود الفعلي + الحالة
- الحفاظ على آخر 50 نسخة لكل ملف

v59.2 — Super Mind العقل الخارق مامون
"""

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class VariantStatus(str, Enum):
    """حالة نسخة الكود"""
    ACTIVE = "active"           # النسخة الحالية
    PREVIOUS = "previous"       # نسخة سابقة
    ROLLED_BACK = "rolled_back" # تم التراجع عنها
    REVERTED = "reverted"       # تم استعادتها بعد تراجع


@dataclass
class CodeVariant:
    """نسخة كود واحدة مع بيانات fitness"""
    variant_id: str
    file_path: str
    code_hash: str
    code_content: str
    fitness_score: float = 0.0
    reliability_score: float = 0.0
    status: VariantStatus = VariantStatus.ACTIVE
    timestamp: float = field(default_factory=time.time)
    parent_variant_id: str = ""
    diff_from_parent: str = ""
    metadata: dict = field(default_factory=dict)
    test_results: dict = field(default_factory=dict)


class VariantArchive:
    """
    أرشيف متغيرات الكود — مستوحى من DGM

    المسؤوليات:
    1. حفظ كل نسخة كود قبل التغيير (snapshot)
    2. تتبع fitness لكل نسخة (من MetaCognition)
    3. السماح بالتراجع لأي نسخة سابقة
    4. حفظ الـ diff بين النسخ
    5. تنظيف النسخ القديمة (أكثر من 50)

    Integration:
    - EvolutionLoopV2: save_snapshot → VariantArchive.save_variant
    - SelfModifier: قبل apply → VariantArchive.save_variant
    - FullSelfRewriter: قبل rewrite → VariantArchive.save_variant
    - MetaCognition: تحديث fitness لكل نسخة
    """

    MAX_VARIANTS_PER_FILE = 50
    ARCHIVE_DIR = "variant_archive"

    def __init__(self, base_dir: str = None, meta_cognition=None, neural_bus=None):
        self._base_dir = Path(base_dir) if base_dir else Path("/tmp/super_mind_variants")
        self._meta_cognition = meta_cognition
        self._neural_bus = neural_bus
        self._variants: dict[str, list[CodeVariant]] = {}  # file_path → [variants]
        self._active_variants: dict[str, str] = {}  # file_path → variant_id

        # التأكد من وجود مجلد الأرشيف
        self._archive_dir = self._base_dir / self.ARCHIVE_DIR
        self._archive_dir.mkdir(parents=True, exist_ok=True)

        # تحميل الأرشيف المحفوظ
        self._load_archive()

    def set_meta_cognition(self, meta_cognition):
        self._meta_cognition = meta_cognition

    def set_neural_bus(self, neural_bus):
        self._neural_bus = neural_bus

    def save_variant(
        self,
        file_path: str,
        code_content: str,
        fitness_score: float = 0.0,
        reliability_score: float = 0.0,
        parent_variant_id: str = "",
        metadata: dict = None,
    ) -> CodeVariant:
        """
        حفظ نسخة كود جديدة في الأرشيف

        يتم استدعاؤها قبل كل تعديل كود لتوفير إمكانية التراجع
        """
        # حساب hash الكود
        code_hash = hashlib.sha256(code_content.encode()).hexdigest()[:16]

        # معرّف النسخة
        variant_id = f"{Path(file_path).stem}_{int(time.time())}_{code_hash[:8]}"

        # حساب diff من النسخة السابقة
        diff = ""
        if file_path in self._variants and self._variants[file_path]:
            parent = self._variants[file_path][-1]
            diff = self._compute_diff(parent.code_content, code_content)
            if not parent_variant_id:
                parent_variant_id = parent.variant_id

        # الحصول على fitness من MetaCognition إذا لم يُحدَّد
        if fitness_score == 0.0 and self._meta_cognition:
            try:
                component_name = Path(file_path).stem
                profile = self._meta_cognition.get_profile(component_name)
                if profile:
                    fitness_score = profile.reliability_score
            except Exception:
                pass

        # إنشاء النسخة
        variant = CodeVariant(
            variant_id=variant_id,
            file_path=file_path,
            code_hash=code_hash,
            code_content=code_content,
            fitness_score=fitness_score,
            reliability_score=reliability_score,
            status=VariantStatus.ACTIVE,
            parent_variant_id=parent_variant_id,
            diff_from_parent=diff,
            metadata=metadata or {},
        )

        # تحديث حالة النسخة السابقة
        if file_path in self._variants and self._variants[file_path]:
            for old_variant in reversed(self._variants[file_path]):
                if old_variant.status == VariantStatus.ACTIVE:
                    old_variant.status = VariantStatus.PREVIOUS
                    break

        # إضافة للأرشيف
        if file_path not in self._variants:
            self._variants[file_path] = []
        self._variants[file_path].append(variant)

        # تحديث النسخة النشطة
        self._active_variants[file_path] = variant_id

        # تنظيف النسخ القديمة
        self._cleanup_old_variants(file_path)

        # حفظ على القرص
        self._save_variant_to_disk(variant)

        logger.info(
            f"Variant saved: {variant_id} for {file_path} "
            f"(fitness={fitness_score:.3f}, hash={code_hash})"
        )

        return variant

    def rollback(self, file_path: str, variant_id: str = None) -> Optional[CodeVariant]:
        """
        التراجع إلى نسخة سابقة

        Args:
            file_path: مسار الملف
            variant_id: معرّف النسخة (إذا None، يرجع للنسخة السابقة)

        Returns: النسخة المستعادة أو None
        """
        variants = self._variants.get(file_path, [])
        if not variants:
            logger.warning(f"No variants found for {file_path}")
            return None

        # تحديد النسخة المستهدفة
        target = None
        if variant_id:
            for v in variants:
                if v.variant_id == variant_id:
                    target = v
                    break
        else:
            # الرجوع للنسخة السابقة
            for v in reversed(variants):
                if v.status == VariantStatus.PREVIOUS:
                    target = v
                    break

        if not target:
            logger.warning(f"Rollback target not found for {file_path}")
            return None

        # تحديث الحالة
        # النسخة الحالية → ROLLED_BACK
        current_id = self._active_variants.get(file_path)
        if current_id:
            for v in variants:
                if v.variant_id == current_id:
                    v.status = VariantStatus.ROLLED_BACK
                    break

        # النسخة المستهدفة → ACTIVE (REVERTED)
        target.status = VariantStatus.REVERTED
        self._active_variants[file_path] = target.variant_id

        # كتابة الكود المستعاد على القرص
        self._write_code_to_disk(file_path, target.code_content)

        logger.info(
            f"Rolled back {file_path} to variant {target.variant_id} "
            f"(fitness={target.fitness_score:.3f})"
        )

        # إرسال تنبيه عبر NeuralBus
        if self._neural_bus:
            try:
                try:
                    from ..shared.neural_bus import Event, EventType
                except ImportError:
                    from shared.neural_bus import Event, EventType

                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self._neural_bus.publish(Event(
                        event_type=EventType.META_ASSESSMENT if hasattr(EventType, 'META_ASSESSMENT') else EventType.HEARTBEAT,
                        source="variant_archive",
                        data={
                            "action": "rollback",
                            "file_path": file_path,
                            "variant_id": target.variant_id,
                            "fitness": target.fitness_score,
                        },
                    )))
            except Exception as e:
                logger.debug(f"NeuralBus publish failed: {e}")

        return target

    def get_active_variant(self, file_path: str) -> Optional[CodeVariant]:
        """الحصول على النسخة النشطة"""
        variant_id = self._active_variants.get(file_path)
        if not variant_id:
            return None
        for v in self._variants.get(file_path, []):
            if v.variant_id == variant_id:
                return v
        return None

    def get_variant_history(self, file_path: str, limit: int = 10) -> list[dict]:
        """الحصول على تاريخ نسخ ملف"""
        variants = self._variants.get(file_path, [])
        return [
            {
                "variant_id": v.variant_id,
                "status": v.status.value,
                "fitness": v.fitness_score,
                "reliability": v.reliability_score,
                "timestamp": v.timestamp,
                "code_hash": v.code_hash,
                "parent": v.parent_variant_id,
                "has_diff": bool(v.diff_from_parent),
            }
            for v in reversed(variants[-limit:])
        ]

    def get_best_variant(self, file_path: str) -> Optional[CodeVariant]:
        """الحصول على أفضل نسخة بناءً على fitness"""
        variants = self._variants.get(file_path, [])
        if not variants:
            return None
        return max(variants, key=lambda v: v.fitness_score)

    def update_fitness(self, file_path: str, variant_id: str, fitness: float):
        """تحديث fitness لنسخة"""
        for v in self._variants.get(file_path, []):
            if v.variant_id == variant_id:
                v.fitness_score = fitness
                self._save_variant_to_disk(v)
                break

    def _compute_diff(self, old_content: str, new_content: str) -> str:
        """حساب الفرق بين نسختين"""
        import difflib
        diff = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile="previous",
            tofile="current",
        )
        return "".join(diff)[:5000]  # حد أقصى

    def _cleanup_old_variants(self, file_path: str):
        """تنظيف النسخ القديمة — الحفاظ على آخر 50"""
        variants = self._variants.get(file_path, [])
        if len(variants) > self.MAX_VARIANTS_PER_FILE:
            # الحفاظ على: آخر 40 + أفضل 5 + النشطة
            active_ids = set()
            for v in variants:
                if v.status in (VariantStatus.ACTIVE, VariantStatus.REVERTED):
                    active_ids.add(v.variant_id)

            # أفضل 5 بناءً على fitness
            sorted_by_fitness = sorted(variants, key=lambda v: v.fitness_score, reverse=True)
            top_ids = {v.variant_id for v in sorted_by_fitness[:5]}

            # آخر 40
            recent = variants[-40:]
            recent_ids = {v.variant_id for v in recent}

            # النسخ للحفظ
            keep_ids = active_ids | top_ids | recent_ids

            # حذف الباقي
            self._variants[file_path] = [
                v for v in variants if v.variant_id in keep_ids
            ]

    def _save_variant_to_disk(self, variant: CodeVariant):
        """حفظ نسخة على القرص"""
        try:
            # مجلد الملف
            file_dir = self._archive_dir / Path(variant.file_path).parent
            file_dir.mkdir(parents=True, exist_ok=True)

            # حفظ بيانات النسخة
            meta_path = file_dir / f"{variant.variant_id}.json"
            meta_data = {
                "variant_id": variant.variant_id,
                "file_path": variant.file_path,
                "code_hash": variant.code_hash,
                "fitness_score": variant.fitness_score,
                "reliability_score": variant.reliability_score,
                "status": variant.status.value,
                "timestamp": variant.timestamp,
                "parent_variant_id": variant.parent_variant_id,
                "metadata": variant.metadata,
                "test_results": variant.test_results,
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta_data, f, ensure_ascii=False, indent=2)

            # حفظ الكود
            code_path = file_dir / f"{variant.variant_id}.py"
            with open(code_path, "w", encoding="utf-8") as f:
                f.write(variant.code_content)

        except Exception as e:
            logger.error(f"Failed to save variant to disk: {e}")

    def _write_code_to_disk(self, file_path: str, code_content: str):
        """كتابة الكود المستعاد على القرص"""
        try:
            # محاولة الكتابة في المسار الفعلي
            actual_path = Path(file_path)
            if actual_path.exists():
                # إنشاء نسخة احتياطية أولاً
                backup_path = actual_path.with_suffix(actual_path.suffix + ".bak")
                with open(actual_path, "r", encoding="utf-8") as f:
                    current_content = f.read()
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(current_content)

                # كتابة الكود المستعاد
                with open(actual_path, "w", encoding="utf-8") as f:
                    f.write(code_content)

                logger.info(f"Code restored to {file_path} (backup at {backup_path})")
        except Exception as e:
            logger.error(f"Failed to write code to disk: {e}")

    def _load_archive(self):
        """تحميل الأرشيف المحفوظ من القرص"""
        try:
            if not self._archive_dir.exists():
                return

            for json_file in self._archive_dir.rglob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    file_path = data.get("file_path", "")
                    variant_id = data.get("variant_id", "")

                    # تحميل الكود
                    code_path = json_file.with_suffix(".py")
                    code_content = ""
                    if code_path.exists():
                        with open(code_path, "r", encoding="utf-8") as f:
                            code_content = f.read()

                    variant = CodeVariant(
                        variant_id=variant_id,
                        file_path=file_path,
                        code_hash=data.get("code_hash", ""),
                        code_content=code_content,
                        fitness_score=data.get("fitness_score", 0.0),
                        reliability_score=data.get("reliability_score", 0.0),
                        status=VariantStatus(data.get("status", "previous")),
                        timestamp=data.get("timestamp", 0),
                        parent_variant_id=data.get("parent_variant_id", ""),
                        metadata=data.get("metadata", {}),
                        test_results=data.get("test_results", {}),
                    )

                    if file_path not in self._variants:
                        self._variants[file_path] = []
                    self._variants[file_path].append(variant)

                    if variant.status in (VariantStatus.ACTIVE, VariantStatus.REVERTED):
                        self._active_variants[file_path] = variant_id

                except Exception as e:
                    logger.debug(f"Failed to load variant from {json_file}: {e}")

        except Exception as e:
            logger.error(f"Failed to load archive: {e}")

    def get_stats(self) -> dict:
        """إحصائيات الأرشيف"""
        total_variants = sum(len(v) for v in self._variants.values())
        active_files = len(self._active_variants)

        return {
            "total_variants": total_variants,
            "tracked_files": len(self._variants),
            "active_files": active_files,
            "archive_dir": str(self._archive_dir),
            "files": {
                fp: len(vars_list)
                for fp, vars_list in self._variants.items()
            },
        }
