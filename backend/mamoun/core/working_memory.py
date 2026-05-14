"""
BABSHARQII v18.0 — Working Memory
الذاكرة العاملة — 7 عناصر مع تقييم الأهمية (Salience)

Based on:
- Miller's Law (7±2 items in human working memory)
- Global Workspace Theory: Working memory as the "spotlight"
- SOFAI (Fast/Slow AI): Working memory feeds System 2 reasoning

The WorkingMemory holds the CURRENT context that all modules can access.
Items are ranked by salience (importance + recency + relevance).
When capacity is exceeded, the least salient item is evicted.
"""

import time
import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Any
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger("mamoun.core.working_memory")


@dataclass
class MemoryItem:
    """عنصر في الذاكرة العاملة — يحمل محتوى + درجة أهمية"""
    id: str = ""
    content: str = ""
    item_type: str = "general"  # general, task, context, research, skill, error, goal
    salience: float = 0.5  # 0.0-1.0 — الأهمية
    source: str = ""  # من أتى بهذا العنصر (brain, user, system, research)
    created_at: float = 0.0
    accessed_at: float = 0.0
    access_count: int = 0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()
        if not self.accessed_at:
            self.accessed_at = self.created_at
        if not self.id:
            self.id = f"wm_{int(self.created_at)}_{hash(self.content) % 10000:04d}"

    def touch(self):
        """تحديث وقت الوصول وعدد المراجع"""
        self.accessed_at = time.time()
        self.access_count += 1

    @property
    def effective_salience(self) -> float:
        """الأهمية الفعّالة — تراعي الوقت والوصول"""
        # Decay: items lose salience over time (halflife = 10 minutes)
        age_seconds = time.time() - self.created_at
        decay = 0.5 ** (age_seconds / 600)  # 600s = 10 min halflife

        # Boost: items accessed more get higher salience
        access_boost = min(0.2, self.access_count * 0.05)

        return min(1.0, self.salience * decay + access_boost)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content[:500],
            "item_type": self.item_type,
            "salience": round(self.salience, 3),
            "effective_salience": round(self.effective_salience, 3),
            "source": self.source,
            "access_count": self.access_count,
            "created_at": self.created_at,
        }


class WorkingMemory:
    """
    الذاكرة العاملة — حافظة السياق الحالي

    Capacity: 7 items (Miller's Law)
    Eviction: Least salient item gets evicted when full
    Access: All modules can read/write
    Decay: Items lose salience over time unless accessed
    """

    CAPACITY = 7  # Miller's Law

    def __init__(self, capacity: int = None):
        self.capacity = capacity or self.CAPACITY
        self.items: list[MemoryItem] = []
        self._counter = 0

    def add(self, content: str, salience: float = 0.5, item_type: str = "general",
            source: str = "", metadata: dict = None) -> MemoryItem:
        """
        إضافة عنصر للذاكرة العاملة.
        إذا امتلأت الذاكرة، يُطرد العنصر الأقل أهمية.
        """
        self._counter += 1

        # Check if similar content already exists
        for existing in self.items:
            if existing.content[:100] == content[:100]:
                # Update existing item instead of adding duplicate
                existing.salience = max(existing.salience, salience)
                existing.touch()
                return existing

        item = MemoryItem(
            id=f"wm_{int(time.time())}_{self._counter}",
            content=content,
            item_type=item_type,
            salience=salience,
            source=source,
            metadata=metadata or {},
        )

        self.items.append(item)

        # Evict least salient if over capacity
        if len(self.items) > self.capacity:
            self._evict()

        logger.debug(
            "WorkingMemory add: [%s] salience=%.2f (items: %d/%d)",
            item_type, salience, len(self.items), self.capacity
        )

        return item

    def _evict(self):
        """طرد العنصر الأقل أهمية فعّالة"""
        if not self.items:
            return

        # Find item with lowest effective salience
        worst_idx = 0
        worst_salience = self.items[0].effective_salience

        for i, item in enumerate(self.items[1:], 1):
            es = item.effective_salience
            if es < worst_salience:
                worst_salience = es
                worst_idx = i

        evicted = self.items.pop(worst_idx)
        logger.debug("WorkingMemory evicted: [%s] '%s'", evicted.item_type, evicted.content[:50])

    def get_context(self, max_length: int = 4000) -> str:
        """
        الحصول على السياق الكامل من الذاكرة العاملة.
        مرتب حسب الأهمية الفعّالة.
        """
        # Sort by effective salience (highest first)
        sorted_items = sorted(self.items, key=lambda x: x.effective_salience, reverse=True)

        parts = []
        total_len = 0
        for item in sorted_items:
            entry = f"[{item.item_type}|{item.source}] {item.content}"
            if total_len + len(entry) > max_length:
                break
            parts.append(entry)
            total_len += len(entry)
            item.touch()  # Access boosts salience

        return "\n".join(parts)

    def get_by_type(self, item_type: str) -> list[MemoryItem]:
        """الحصول على عناصر بنوع محدد"""
        return [item for item in self.items if item.item_type == item_type]

    def get_goals(self) -> list[MemoryItem]:
        """الحصول على الأهداف الحالية"""
        return self.get_by_type("goal")

    def get_errors(self) -> list[MemoryItem]:
        """الحصول على الأخطاء الحالية"""
        return self.get_by_type("error")

    def clear_type(self, item_type: str):
        """مسح عناصر بنوع محدد"""
        self.items = [item for item in self.items if item.item_type != item_type]

    def decay_all(self):
        """تقليل أهمية جميع العناصر — يُستدعى دورياً"""
        # Remove items with very low effective salience
        before = len(self.items)
        self.items = [item for item in self.items if item.effective_salience > 0.05]
        removed = before - len(self.items)
        if removed:
            logger.debug("WorkingMemory decay removed %d items", removed)

    def get_status(self) -> dict:
        """حالة الذاكرة العاملة"""
        type_counts = {}
        for item in self.items:
            type_counts[item.item_type] = type_counts.get(item.item_type, 0) + 1

        return {
            "capacity": self.capacity,
            "current_items": len(self.items),
            "utilization": round(len(self.items) / self.capacity, 2),
            "type_counts": type_counts,
            "top_items": [
                {"content": str(item.content)[:100], "salience": round(item.effective_salience, 3), "type": item.item_type}
                for item in sorted(self.items, key=lambda x: x.effective_salience, reverse=True)[:5]
            ],
        }
