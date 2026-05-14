"""
BABSHARQII v40.0 "Mamoun" — AgeMem (Memory Aging System)
Manages the aging and forgetting of memory entries over time.
Memories that aren't accessed decay in relevance; frequently accessed
memories get "reinforced" (boosted relevance).

This is the organism's ability to forget — a crucial component of
efficient cognition. Not everything deserves to be remembered forever.

Aging formula:
    relevance = base_relevance * (decay_factor ^ time_elapsed) * (1 + log(1 + retrieval_count))
"""

import os
import time
import math
import logging
import aiosqlite
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("mamoun.age_mem")

# ─── Configurable via MAMOUN_ env vars ────────────────────────────────────────
DEFAULT_DECAY_FACTOR = float(os.environ.get("MAMOUN_AGEMEM_DECAY_FACTOR", "0.95"))
DEFAULT_AGING_PERIOD_HOURS = float(os.environ.get("MAMOUN_AGEMEM_AGING_PERIOD_HOURS", "24"))
DEFAULT_RELEVANCE_THRESHOLD = float(os.environ.get("MAMOUN_AGEMEM_RELEVANCE_THRESHOLD", "0.1"))
DEFAULT_BASE_RELEVANCE = float(os.environ.get("MAMOUN_AGEMEM_BASE_RELEVANCE", "1.0"))


@dataclass
class AgedEntry:
    """عنصر ذاكرة متقدم في العمر — يمثل حالة تقادم مدخل ذاكرة."""
    entry_id: int
    base_relevance: float = DEFAULT_BASE_RELEVANCE
    retrieval_count: int = 0
    last_accessed: float = 0.0
    current_relevance: float = DEFAULT_BASE_RELEVANCE
    created_at: float = 0.0
    archived: bool = False

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "base_relevance": self.base_relevance,
            "retrieval_count": self.retrieval_count,
            "last_accessed": self.last_accessed,
            "current_relevance": self.current_relevance,
            "created_at": self.created_at,
            "archived": self.archived,
        }


class AgeMem:
    """
    نظام تقادم الذاكرة — Memory Aging System.

    Manages the lifecycle of memory entries through time-based decay
    and access-based reinforcement:

    1. Decaying: Memories lose relevance over time if not accessed
    2. Reinforcing: Frequently accessed memories gain relevance
    3. Pruning: Extremely decayed memories can be archived/removed

    Aging formula:
        relevance = base_relevance × (decay_factor ^ hours_elapsed) × (1 + log(1 + retrieval_count))

    - decay_factor < 1 means relevance decreases over time
    - retrieval_count > 0 means frequent access boosts relevance
    - The log function ensures diminishing returns on reinforcement
    """

    def __init__(
        self,
        db_path: str = "",
        decay_factor: float = DEFAULT_DECAY_FACTOR,
        aging_period_hours: float = DEFAULT_AGING_PERIOD_HOURS,
        relevance_threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    ):
        if not db_path:
            db_path = str(Path(__file__).parent.parent.parent / "data" / "mamoun.db")
        self._db_path = db_path
        self._initialized = False
        self.decay_factor = decay_factor
        self.aging_period_hours = aging_period_hours
        self.relevance_threshold = relevance_threshold

    async def _initialize(self):
        """إنشاء جدول تقادم الذاكرة إذا لم يكن موجوداً."""
        if self._initialized:
            return

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS memory_aging (
                    entry_id INTEGER PRIMARY KEY,
                    base_relevance REAL DEFAULT 1.0,
                    retrieval_count INTEGER DEFAULT 0,
                    last_accessed REAL DEFAULT 0.0,
                    current_relevance REAL DEFAULT 1.0,
                    created_at REAL DEFAULT 0.0,
                    archived INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_aging_relevance
                ON memory_aging(current_relevance)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_aging_archived
                ON memory_aging(archived)
            """)
            await db.commit()

        self._initialized = True
        logger.info("تم تهيئة نظام تقادم الذاكرة")

    def _compute_relevance(
        self,
        base_relevance: float,
        retrieval_count: int,
        hours_elapsed: float,
    ) -> float:
        """
        حساب الصلة الحالية باستخدام صيغة التقادم.

        relevance = base_relevance × (decay_factor ^ hours_elapsed) × (1 + log(1 + retrieval_count))

        المعاملات:
            base_relevance: الصلة الأساسية للمدخل (0.0 - 1.0)
            retrieval_count: عدد مرات الاسترجاع
            hours_elapsed: الساعات المنقضية منذ آخر وصول
        """
        decay_component = self.decay_factor ** hours_elapsed
        reinforcement_component = 1.0 + math.log(1 + retrieval_count)
        relevance = base_relevance * decay_component * reinforcement_component
        return max(0.0, relevance)

    async def register_entry(
        self,
        entry_id: int,
        base_relevance: float = DEFAULT_BASE_RELEVANCE,
    ) -> bool:
        """
        تسجيل مدخل جديد في نظام تقادم الذاكرة.

        يجب استدعاء هذه الدالة عند إضافة مدخل جديد للذاكرة.
        """
        await self._initialize()

        now = time.time()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO memory_aging
                (entry_id, base_relevance, retrieval_count, last_accessed, current_relevance, created_at, archived)
                VALUES (?, ?, 0, ?, ?, ?, 0)
            """, (
                entry_id,
                base_relevance,
                now,
                base_relevance,
                now,
            ))
            await db.commit()

        logger.debug(f"تم تسجيل المدخل {entry_id} في نظام التقادم بصلة أساسية {base_relevance}")
        return True

    async def age_entries(self) -> int:
        """
        تطبيق التقادم على جميع المدخلات النشطة.

        يحسب الصلة الجديدة لكل مدخل بناءً على الوقت المنقضي
        وعدد مرات الاسترجاع.

        Returns:
            عدد المدخلات التي تم تحديث صلتها
        """
        await self._initialize()

        now = time.time()
        aged_count = 0

        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT entry_id, base_relevance, retrieval_count, last_accessed, created_at
                FROM memory_aging
                WHERE archived = 0
            """)
            rows = await cursor.fetchall()

            for row in rows:
                entry_id = row["entry_id"]
                base_relevance = row["base_relevance"]
                retrieval_count = row["retrieval_count"]
                last_accessed = row["last_accessed"]

                # Calculate hours since last access
                hours_elapsed = (now - last_accessed) / 3600.0

                # Compute new relevance
                new_relevance = self._compute_relevance(
                    base_relevance, retrieval_count, hours_elapsed
                )

                await db.execute("""
                    UPDATE memory_aging
                    SET current_relevance = ?
                    WHERE entry_id = ?
                """, (new_relevance, entry_id))

                aged_count += 1

            await db.commit()

        logger.info(f"تم تقادم {aged_count} مدخل ذاكرة")
        return aged_count

    async def reinforce_entry(self, entry_id: int) -> bool:
        """
        تعزيز مدخل ذاكرة عند الوصول إليه.

        يزيد عدد مرات الاسترجاع ويحدّث وقت آخر وصول
        ويعيد حساب الصلة.

        Returns:
            True إذا تم التعزيز بنجاح، False إذا لم يُوجد المدخل
        """
        await self._initialize()

        now = time.time()

        async with aiosqlite.connect(self._db_path) as db:
            # Check if entry exists and is not archived
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT entry_id, base_relevance, retrieval_count
                FROM memory_aging
                WHERE entry_id = ? AND archived = 0
            """, (entry_id,))
            row = await cursor.fetchone()

            if not row:
                logger.debug(f"لم يتم العثور على المدخل {entry_id} للتعزيز")
                return False

            new_count = row["retrieval_count"] + 1
            base_relevance = row["base_relevance"]

            # Recompute relevance with new count and fresh last_accessed
            new_relevance = self._compute_relevance(
                base_relevance, new_count, 0.0  # 0 hours since just accessed
            )

            await db.execute("""
                UPDATE memory_aging
                SET retrieval_count = ?,
                    last_accessed = ?,
                    current_relevance = ?
                WHERE entry_id = ? AND archived = 0
            """, (new_count, now, new_relevance, entry_id))
            await db.commit()

        logger.debug(
            f"تم تعزيز المدخل {entry_id}: عدد الاسترجاعات={new_count}، الصلة={new_relevance:.4f}"
        )
        return True

    async def get_decayed_entries(self, threshold: Optional[float] = None) -> list[AgedEntry]:
        """
        الحصول على المدخلات التي انخفضت صلتها عن الحد الأدنى.

        Args:
            threshold: حد الصلة الأدنى (يستخدم القيمة الافتراضية إذا لم يُحدد)

        Returns:
            قائمة المدخلات المتقدمة في التقادم
        """
        await self._initialize()

        if threshold is None:
            threshold = self.relevance_threshold

        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT entry_id, base_relevance, retrieval_count,
                       last_accessed, current_relevance, created_at, archived
                FROM memory_aging
                WHERE current_relevance < ? AND archived = 0
                ORDER BY current_relevance ASC
            """, (threshold,))
            rows = await cursor.fetchall()

        entries = []
        for row in rows:
            entries.append(AgedEntry(
                entry_id=row["entry_id"],
                base_relevance=row["base_relevance"],
                retrieval_count=row["retrieval_count"],
                last_accessed=row["last_accessed"],
                current_relevance=row["current_relevance"],
                created_at=row["created_at"],
                archived=bool(row["archived"]),
            ))

        return entries

    async def prune_decayed(self, threshold: Optional[float] = None) -> int:
        """
        أرشفة/إزالة المدخلات التي انخفضت صلتها عن الحد الأدنى.

        لا يتم حذف المدخلات فعلياً، بل تُعلَّم كـ "مؤرشفة"
        للحفاظ على سجل التقادم.

        Returns:
            عدد المدخلات المؤرشفة
        """
        await self._initialize()

        if threshold is None:
            threshold = self.relevance_threshold

        # First, run aging to get current relevance values
        await self.age_entries()

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("""
                UPDATE memory_aging
                SET archived = 1
                WHERE current_relevance < ? AND archived = 0
            """, (threshold,))
            await db.commit()
            pruned_count = cursor.rowcount

        if pruned_count > 0:
            logger.info(f"تم أرشفة {pruned_count} مدخل ذاكرة متقادم (صلة < {threshold})")
        return pruned_count

    async def get_entry_status(self, entry_id: int) -> Optional[AgedEntry]:
        """
        الحصول على حالة تقادم مدخل محدد.
        """
        await self._initialize()

        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT entry_id, base_relevance, retrieval_count,
                       last_accessed, current_relevance, created_at, archived
                FROM memory_aging
                WHERE entry_id = ?
            """, (entry_id,))
            row = await cursor.fetchone()

        if not row:
            return None

        return AgedEntry(
            entry_id=row["entry_id"],
            base_relevance=row["base_relevance"],
            retrieval_count=row["retrieval_count"],
            last_accessed=row["last_accessed"],
            current_relevance=row["current_relevance"],
            created_at=row["created_at"],
            archived=bool(row["archived"]),
        )

    async def get_stats(self) -> dict:
        """
        الحصول على إحصائيات نظام تقادم الذاكرة.
        """
        await self._initialize()

        async with aiosqlite.connect(self._db_path) as db:
            # Total active entries
            cursor = await db.execute(
                "SELECT COUNT(*) FROM memory_aging WHERE archived = 0"
            )
            active_count = (await cursor.fetchone())[0]

            # Total archived entries
            cursor = await db.execute(
                "SELECT COUNT(*) FROM memory_aging WHERE archived = 1"
            )
            archived_count = (await cursor.fetchone())[0]

            # Average relevance
            cursor = await db.execute(
                "SELECT AVG(current_relevance) FROM memory_aging WHERE archived = 0"
            )
            avg_relevance = (await cursor.fetchone())[0] or 0.0

            # Most accessed
            cursor = await db.execute("""
                SELECT entry_id, retrieval_count
                FROM memory_aging
                WHERE archived = 0
                ORDER BY retrieval_count DESC
                LIMIT 1
            """)
            most_accessed = await cursor.fetchone()

        return {
            "إجمالي_النشطة": active_count,
            "إجمالي_المؤرشفة": archived_count,
            "متوسط_الصلة": round(avg_relevance, 4),
            "الأكثر_استرجاعاً": {
                "entry_id": most_accessed[0] if most_accessed else None,
                "retrieval_count": most_accessed[1] if most_accessed else 0,
            },
            "عامل_التقادم": self.decay_factor,
            "فترة_التقادم_بالساعات": self.aging_period_hours,
            "حد_الصلة_الأدنى": self.relevance_threshold,
        }
