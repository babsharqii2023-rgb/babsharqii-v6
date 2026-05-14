"""
BABSHARQII v40.0 — Strategic Forgetting
النسيان الإستراتيجي — خوارزمية النسيان المبني على الأهمية والعمر

Implements the "strategic forgetting" algorithm inspired by research on
memory aging and importance-based decay (ALTK-Evolve, DarwinTod).

The human brain forgets strategically — not randomly. Emotionally
significant memories persist while trivial ones fade. Frequently
accessed knowledge stays sharp while unused knowledge decays.
This module replicates that principle for AGI memory management.

Forgetting Formula:
    retention_score = base_importance
                    × access_frequency_factor
                    × recency_factor
                    × emotional_factor
                    × age_decay_factor

Factors:
  • age_decay_factor:       exponential decay based on memory age
  • access_frequency_factor: boost for frequently accessed memories
  • recency_factor:         bonus for recently accessed memories
  • emotional_factor:       emotionally significant memories decay slower
  • base_importance:        the original importance score (0-1)

Actions:
  • keep:    retention_score > archive_threshold → retains the memory
  • archive: delete_threshold < score ≤ archive_threshold → moves to archive
  • delete:  retention_score ≤ delete_threshold → permanently removes

Env toggles:
    MAMOUN_STRATEGIC_FORGETTING_ENABLED — تمكين/تعطيل النسيان الإستراتيجي (الافتراضي: false)
"""

from __future__ import annotations

import os
import time
import math
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from mamoun.memory.episodic_memory_store import (
    EpisodicEntry,
    EpisodicMemoryStore,
)

logger = logging.getLogger("mamoun.strategic_forgetting")

# ─── مفاتيح التهيئة البيئية — Environment Config ─────────────────────────────

STRATEGIC_FORGETTING_ENABLED: bool = os.environ.get(
    "MAMOUN_STRATEGIC_FORGETTING_ENABLED", "false"
).lower() in ("true", "1", "yes")

# ─── عتبات افتراضية — Default Thresholds ────────────────────────────────────

DEFAULT_ARCHIVE_THRESHOLD: float = float(
    os.environ.get("MAMOUN_FORGETTING_ARCHIVE_THRESHOLD", "0.3")
)
DEFAULT_DELETE_THRESHOLD: float = float(
    os.environ.get("MAMOUN_FORGETTING_DELETE_THRESHOLD", "0.1")
)
DEFAULT_MAX_MEMORY_AGE_DAYS: float = float(
    os.environ.get("MAMOUN_FORGETTING_MAX_AGE_DAYS", "365")
)
DEFAULT_AGE_DECAY_RATE: float = float(
    os.environ.get("MAMOUN_FORGETTING_AGE_DECAY_RATE", "0.002")
)
DEFAULT_EMOTIONAL_DECAY_SLOWDOWN: float = float(
    os.environ.get("MAMOUN_FORGETTING_EMOTIONAL_SLOWDOWN", "0.5")
)


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج البيانات — Data Models
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ForgettingDecision:
    """
    قرار النسيان — قرار بشأن مصير ذاكرة واحدة.
    A decision about the fate of a single memory entry.
    """
    entry_id: str = ""                   # معرف المدخل
    retention_score: float = 0.0         # درجة الاحتفاظ (0-1)
    action: str = "keep"                 # الإجراء: keep / archive / delete
    reason: str = ""                     # السبب (بالعربية)

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary."""
        return {
            "entry_id": self.entry_id,
            "retention_score": round(self.retention_score, 4),
            "action": self.action,
            "reason": self.reason,
        }


@dataclass
class ForgettingReport:
    """
    تقرير النسيان — تقرير شامل عن دورة النسيان الإستراتيجي.
    Comprehensive report of a strategic forgetting cycle.
    """
    total_evaluated: int = 0             # إجمالي المدخلات المُقيَّمة
    kept: int = 0                        # المحفوظة
    archived: int = 0                    # المؤرشفة
    deleted: int = 0                     # المحذوفة
    cycle_timestamp: float = field(default_factory=time.time)  # وقت الدورة

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary."""
        return {
            "total_evaluated": self.total_evaluated,
            "kept": self.kept,
            "archived": self.archived,
            "deleted": self.deleted,
            "cycle_timestamp": self.cycle_timestamp,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  المشاعر ذات الأهمية العاطفية — Emotionally Significant Emotions
# ═══════════════════════════════════════════════════════════════════════════════

# المشاعر التي تبطئ النسيان — Emotions that slow down forgetting
EMOTIONALLY_SIGNIFICANT: set = {
    # فرح قوي — Strong joy
    "joy", "love", "gratitude", "pride",
    # حزن عميق — Deep sadness
    "sadness", "grief", "loss",
    # صدمة — Trauma
    "fear", "anger", "shame",
    # عربية — Arabic equivalents
    "فرح", "حب", "امتنان", "فخر",
    "حزن", "خوف", "غضب", "خجل",
    "ثقة", "مفاجأة",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  النسيان الإستراتيجي — StrategicForgetting
# ═══════════════════════════════════════════════════════════════════════════════


class StrategicForgetting:
    """
    النسيان الإستراتيجي — Strategic Forgetting Engine.

    Implements a biologically-inspired forgetting algorithm that evaluates
    each memory based on multiple factors:

    1. العمر — Age: older memories decay exponentially
    2. تكرار الوصول — Access frequency: more accessed = more retained
    3. الأهمية الأصلية — Original importance: higher importance persists
    4. الأهمية العاطفية — Emotional valence: emotional memories decay slower
    5. حداثة الوصول — Recency: recently accessed memories get a boost

    Formula:
        retention_score = base_importance
                        × access_frequency_factor
                        × recency_factor
                        × emotional_factor
                        × age_decay_factor

    تصميم مستوحى من أبحاث ALTK-Evolve و DarwinTod في تقادم الذاكرة.
    """

    def __init__(
        self,
        archive_threshold: float = DEFAULT_ARCHIVE_THRESHOLD,
        delete_threshold: float = DEFAULT_DELETE_THRESHOLD,
        max_memory_age_days: float = DEFAULT_MAX_MEMORY_AGE_DAYS,
        age_decay_rate: float = DEFAULT_AGE_DECAY_RATE,
        emotional_decay_slowdown: float = DEFAULT_EMOTIONAL_DECAY_SLOWDOWN,
    ):
        """
        تهيئة محرك النسيان الإستراتيجي — Initialize the strategic forgetting engine.

        Args:
            archive_threshold: عتبة الأرشفة — score below this triggers archiving (default: 0.3)
            delete_threshold: عتبة الحذف — score below this triggers deletion (default: 0.1)
            max_memory_age_days: أقصى عمر للذاكرة — max days before forced archival (default: 365)
            age_decay_rate: معدل تقادم العمر — exponential decay rate per day (default: 0.002)
            emotional_decay_slowdown: إبطاء التقادم العاطفي — emotional slowdown factor (default: 0.5)
        """
        self.archive_threshold = archive_threshold
        self.delete_threshold = delete_threshold
        self.max_memory_age_days = max_memory_age_days
        self.age_decay_rate = age_decay_rate
        self.emotional_decay_slowdown = emotional_decay_slowdown
        self._last_cycle_timestamp: float = 0.0
        self._cycle_count: int = 0

    # ─── حساب العوامل — Factor Computation ────────────────────────────────

    def _compute_age_decay_factor(self, entry: EpisodicEntry) -> float:
        """
        حساب عامل تقادم العمر — Compute age decay factor.

        Uses exponential decay: factor = e^(-rate × age_days)

        الذكريات القديمة تتلاشى بشكل أسي — Older memories decay exponentially.
        """
        now = time.time()
        age_seconds = now - entry.timestamp
        age_days = age_seconds / 86400.0

        # Exponential decay
        factor = math.exp(-self.age_decay_rate * age_days)
        return max(0.0, min(1.0, factor))

    def _compute_access_frequency_factor(self, entry: EpisodicEntry) -> float:
        """
        حساب عامل تكرار الوصول — Compute access frequency factor.

        Uses logarithmic scaling: factor = 1 + log(1 + access_count) / log(1 + 100)
        Normalized so that 100 accesses ≈ factor of 2.0

        الذكريات المتكررة الوصول تبقى أطول — Frequently accessed memories persist.
        """
        if entry.access_count <= 0:
            return 1.0
        # Logarithmic scaling to prevent unbounded growth
        factor = 1.0 + math.log(1 + entry.access_count) / math.log(1 + 100)
        return min(factor, 3.0)  # Cap at 3x boost

    def _compute_recency_factor(self, entry: EpisodicEntry) -> float:
        """
        حساب عامل حداثة الوصول — Compute recency factor.

        Recently accessed memories get a boost that decays over 7 days.

        الذكريات المنشأة حديثاً تحصل على تعزيز — Recent access boosts retention.
        """
        now = time.time()
        seconds_since_access = now - entry.last_accessed
        days_since_access = seconds_since_access / 86400.0

        # Recency bonus decays over 7 days
        recency_half_life_days = 7.0
        factor = 1.0 + math.exp(-0.693 * days_since_access / recency_half_life_days)
        return min(factor, 2.0)  # Cap at 2x boost

    def _compute_emotional_factor(self, entry: EpisodicEntry) -> float:
        """
        حساب العامل العاطفي — Compute emotional factor.

        Emotionally significant memories decay slower.
        Factor ranges from 1.0 (no emotions) to (1 + emotional_decay_slowdown).

        الذكريات العاطفية تتلاشى أبطأ — Emotional memories decay slower.
        """
        if not entry.emotions:
            return 1.0

        # Check how many emotions are significant
        significant_count = sum(
            1 for e in entry.emotions
            if e.lower() in EMOTIONALLY_SIGNIFICANT
        )

        if significant_count == 0:
            return 1.0

        # More significant emotions → slower decay
        # Factor = 1 + slowdown × (significant_count / total_emotions)
        emotion_ratio = significant_count / len(entry.emotions)
        factor = 1.0 + self.emotional_decay_slowdown * emotion_ratio
        return min(factor, 2.0)  # Cap at 2x boost

    # ─── تقييم ذاكرة واحدة — Evaluate Single Memory ──────────────────────

    def evaluate_memory(self, entry: EpisodicEntry) -> ForgettingDecision:
        """
        تقييم ذاكرة واحدة — Evaluate a single memory for forgetting.

        Computes the retention score and determines the appropriate action:
          - keep:    retention_score > archive_threshold
          - archive: delete_threshold < score ≤ archive_threshold
          - delete:  retention_score ≤ delete_threshold

        Args:
            entry: مدخل الذاكرة الحلقية — the episodic entry to evaluate

        Returns:
            قرار النسيان — the forgetting decision
        """
        # Compute individual factors
        age_decay = self._compute_age_decay_factor(entry)
        access_freq = self._compute_access_frequency_factor(entry)
        recency = self._compute_recency_factor(entry)
        emotional = self._compute_emotional_factor(entry)
        base_importance = max(0.0, min(1.0, entry.importance_score))

        # Compute composite retention score
        raw_score = (
            base_importance
            * access_freq
            * recency
            * emotional
            * age_decay
        )

        # Normalize to 0-1 range using soft sigmoid mapping.
        # Raw scores can exceed 1.0 due to multiplicative factors
        # (access_freq, recency, emotional all ≥ 1.0). We use a
        # saturating function so that:
        #   raw ≈ 0   → score ≈ 0   (unimportant, old, unaccessed)
        #   raw ≈ 0.5 → score ≈ 0.4 (moderate)
        #   raw ≈ 1.0 → score ≈ 0.7 (good, recent, important)
        #   raw ≈ 2.0 → score ≈ 0.9 (excellent, frequently accessed)
        #   raw ≥ 3.0 → score ≈ 1.0 (top-tier memory)
        #
        # تطبيع باستخدام سيجمويد للحفاظ على تدرج معنوي
        retention_score = 1.0 - math.exp(-raw_score)
        retention_score = max(0.0, min(1.0, retention_score))

        # Determine action
        now = time.time()
        age_days = (now - entry.timestamp) / 86400.0

        # Force archive/delete for extremely old memories
        if age_days > self.max_memory_age_days and retention_score < self.delete_threshold:
            action = "delete"
            reason = (
                f"ذاكرة قديمة جداً ({age_days:.0f} يوم) مع درجة احتفاظ منخفضة "
                f"({retention_score:.4f}) — Very old memory with low retention"
            )
        elif age_days > self.max_memory_age_days:
            action = "archive"
            reason = (
                f"ذاكرة قديمة ({age_days:.0f} يوم) — تجاوزت الحد الأقصى للعمر "
                f"— Old memory exceeded max age"
            )
        elif retention_score <= self.delete_threshold:
            action = "delete"
            reason = (
                f"درجة احتفاظ منخفضة جداً ({retention_score:.4f}) — "
                f"لا قيمة تذكر للذاكرة — Very low retention score"
            )
        elif retention_score <= self.archive_threshold:
            action = "archive"
            reason = (
                f"درجة احتفاظ متوسطة ({retention_score:.4f}) — "
                f"أرشفة للحفاظ على المساحة — Moderate retention, archiving"
            )
        else:
            action = "keep"
            reason = (
                f"درجة احتفاظ جيدة ({retention_score:.4f}) — "
                f"الذاكرة محفوظة — Good retention, keeping memory"
            )

        return ForgettingDecision(
            entry_id=entry.id,
            retention_score=retention_score,
            action=action,
            reason=reason,
        )

    # ─── دورة النسيان الكاملة — Full Forgetting Cycle ────────────────────

    def run_forgetting_cycle(
        self,
        store: EpisodicMemoryStore,
        dry_run: bool = False,
    ) -> ForgettingReport:
        """
        تنفيذ دورة نسيان إستراتيجي كاملة — Run a complete forgetting cycle.

        Iterates through all episodic memories, evaluates each one,
        and applies the appropriate action (keep/archive/delete).

        Args:
            store: مخزن الذاكرة الحلقية — the episodic memory store
            dry_run: تشغيل جاف — if True, evaluate but don't apply actions

        Returns:
            تقرير النسيان — the forgetting report
        """
        if not STRATEGIC_FORGETTING_ENABLED:
            logger.debug("النسيان الإستراتيجي معطّل — Strategic forgetting disabled")
            return ForgettingReport()

        self._cycle_count += 1
        cycle_start = time.time()
        self._last_cycle_timestamp = cycle_start

        logger.info(f"بدء دورة النسيان الإستراتيجي #{self._cycle_count}")

        # Fetch all entries from the store
        entries = store.get_all_entries()

        report = ForgettingReport()
        decisions: List[ForgettingDecision] = []

        for entry in entries:
            decision = self.evaluate_memory(entry)
            decisions.append(decision)
            report.total_evaluated += 1

            if decision.action == "keep":
                report.kept += 1
            elif decision.action == "archive":
                report.archived += 1
                if not dry_run:
                    # Mark as archived by reducing importance to 0
                    entry.importance_score = 0.0
                    entry.context["archived"] = True
                    entry.context["archived_at"] = time.time()
                    entry.context["archival_reason"] = decision.reason
                    store.update_episode(entry)
            elif decision.action == "delete":
                report.deleted += 1
                if not dry_run:
                    store.delete_episode(entry.id)

        # Log summary
        elapsed = time.time() - cycle_start
        logger.info(
            f"اكتملت دورة النسيان #{self._cycle_count}: "
            f"تم تقييم {report.total_evaluated} ذاكرة، "
            f"محفوظة={report.kept}، مؤرشفة={report.archived}، محذوفة={report.deleted} "
            f"({elapsed:.2f} ثانية)"
        )

        # Log individual decisions at debug level
        for d in decisions:
            if d.action != "keep":
                logger.debug(
                    f"قرار نسيان: {d.entry_id} → {d.action} "
                    f"(درجة={d.retention_score:.4f}): {d.reason}"
                )

        return report

    # ─── الحالة والإيقاف — Status & Shutdown ─────────────────────────────

    def get_status(self) -> dict:
        """
        حالة محرك النسيان الإستراتيجي — Strategic forgetting engine status.
        """
        return {
            "enabled": STRATEGIC_FORGETTING_ENABLED,
            "archive_threshold": self.archive_threshold,
            "delete_threshold": self.delete_threshold,
            "max_memory_age_days": self.max_memory_age_days,
            "age_decay_rate": self.age_decay_rate,
            "emotional_decay_slowdown": self.emotional_decay_slowdown,
            "cycle_count": self._cycle_count,
            "last_cycle_timestamp": self._last_cycle_timestamp,
            "وصف": "النسيان الإستراتيجي — Strategic Forgetting Engine",
        }

    def shutdown(self) -> None:
        """
        إيقاف محرك النسيان الإستراتيجي — Shutdown the strategic forgetting engine.
        """
        logger.info(
            f"تم إيقاف النسيان الإستراتيجي بعد {self._cycle_count} دورة"
        )
        self._cycle_count = 0
        self._last_cycle_timestamp = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton — النسخة الوحيدة
# ═══════════════════════════════════════════════════════════════════════════════

strategic_forgetting = StrategicForgetting()
