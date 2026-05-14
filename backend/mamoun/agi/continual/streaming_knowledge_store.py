"""
BABSHARQII v9.0 — Streaming Knowledge Store
مخزن المعرفة المتدفق — فهرسة ذاتية مع تدفق مستمر للمعرفة الجديدة

A knowledge store that continuously ingests, indexes, and retrieves
knowledge items with automatic categorization and relevance scoring.

Feature Flag: MAMOUN_EWC_MODE (default: false)
"""

from __future__ import annotations

import os
import json
import time
import hashlib
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

EWC_MODE_ENABLED: bool = os.environ.get(
    "MAMOUN_EWC_MODE", "false"
).lower() in ("true", "1", "yes")


@dataclass
class KnowledgeItem:
    """عنصر معرفي واحد"""
    item_id: str = ""
    content: str = ""
    domain: str = ""
    tags: list[str] = field(default_factory=list)
    source: str = ""
    confidence: float = 1.0
    access_count: int = 0
    created_at: float = 0.0
    last_accessed: float = 0.0
    embedding_hash: str = ""  # hash for similarity lookup


class StreamingKnowledgeStore:
    """
    مخزن المعرفة المتدفق

    Features:
      - Auto-indexing: new knowledge is automatically categorized
      - Tag-based retrieval: find knowledge by domain, tags, or content
      - Relevance scoring: most-accessed items get priority
      - Streaming ingestion: continuously add knowledge without batch processing
      - Persistence: save/load knowledge to disk
    """

    def __init__(self, persist_path: Optional[str] = None, max_items: int = 100000):
        self._items: dict[str, KnowledgeItem] = {}
        self._domain_index: dict[str, list[str]] = {}
        self._tag_index: dict[str, list[str]] = {}
        self._persist_path = persist_path
        self._max_items = max_items
        self._ingestion_count = 0

        if persist_path:
            self._load(persist_path)

    def ingest(self, content: str, domain: str = "", tags: list[str] = None,
               source: str = "", confidence: float = 1.0) -> str:
        """
        استوعب عنصر معرفي جديد (streaming ingestion).

        Returns the item_id of the ingested knowledge.
        """
        # Generate unique ID
        content_hash = hashlib.md5(content.encode()).hexdigest()[:12]
        item_id = f"k_{domain}_{content_hash}_{int(time.time()*1000) % 10000}"

        # Auto-generate tags if not provided
        if tags is None:
            tags = self._auto_tag(content, domain)

        item = KnowledgeItem(
            item_id=item_id,
            content=content,
            domain=domain,
            tags=tags,
            source=source,
            confidence=confidence,
            created_at=time.time(),
            last_accessed=time.time(),
            embedding_hash=content_hash,
        )

        self._items[item_id] = item
        self._ingestion_count += 1

        # Update indices
        if domain not in self._domain_index:
            self._domain_index[domain] = []
        self._domain_index[domain].append(item_id)

        for tag in tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            self._tag_index[tag].append(item_id)

        # Evict oldest items if over limit
        if len(self._items) > self._max_items:
            self._evict_oldest()

        self._auto_persist()
        return item_id

    def retrieve(
        self, query: str = "", domain: str = "", tags: list[str] = None,
        limit: int = 10,
    ) -> list[KnowledgeItem]:
        """
        استرجع عناصر معرفية بناءً على الاستعلام.
        """
        candidates = set()

        # Search by domain
        if domain and domain in self._domain_index:
            candidates.update(self._domain_index[domain])

        # Search by tags
        if tags:
            for tag in tags:
                if tag in self._tag_index:
                    candidates.update(self._tag_index[tag])

        # Search by content
        if query:
            for item_id, item in self._items.items():
                if query.lower() in item.content.lower():
                    candidates.add(item_id)

        # If no filters, return all
        if not domain and not tags and not query:
            candidates = set(self._items.keys())

        # Score and sort by relevance
        scored = []
        for item_id in candidates:
            if item_id in self._items:
                item = self._items[item_id]
                # Relevance = access frequency + confidence + recency
                recency = 1.0 / (1.0 + (time.time() - item.last_accessed) / 3600)
                relevance = (item.access_count * 0.3 + item.confidence * 0.4 + recency * 0.3)
                scored.append((relevance, item))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Update access counts
        results = []
        for _, item in scored[:limit]:
            item.access_count += 1
            item.last_accessed = time.time()
            results.append(item)

        return results

    def _auto_tag(self, content: str, domain: str) -> list[str]:
        """أضف وسوماً تلقائية بناءً على المحتوى"""
        tags = [domain] if domain else []

        # Arabic content detection
        arabic_keywords = {
            "إسلام": "islamic", "قرآن": "quran", "صلاة": "prayer",
            "حلال": "halal", "حرام": "haram", "أدب": "adab",
            "إحسان": "ihsan", "كرم": "generosity", "ضيافة": "hospitality",
            "أسرة": "family", "شرف": "honor", "صلة الرحم": "kinship",
            "استدلال": "reasoning", "سببي": "causal", "منطق": "logic",
            "ذاكرة": "memory", "تعلم": "learning", "أمان": "safety",
        }

        for keyword, tag in arabic_keywords.items():
            if keyword in content:
                tags.append(tag)

        return tags

    def _evict_oldest(self) -> None:
        """أخرج أقدم العناصر عند تجاوز الحد"""
        if len(self._items) <= self._max_items:
            return

        # Sort by access count and age, evict least important
        sorted_items = sorted(
            self._items.items(),
            key=lambda x: (x[1].access_count, x[1].created_at),
        )

        # Remove 10% of least accessed items
        to_remove = len(self._items) - int(self._max_items * 0.9)
        for item_id, _ in sorted_items[:to_remove]:
            self._remove_item(item_id)

    def _remove_item(self, item_id: str) -> None:
        """أزل عنصراً من المخزن والفهارس"""
        if item_id not in self._items:
            return
        item = self._items[item_id]

        # Remove from domain index
        if item.domain in self._domain_index:
            self._domain_index[item.domain] = [
                x for x in self._domain_index[item.domain] if x != item_id
            ]

        # Remove from tag index
        for tag in item.tags:
            if tag in self._tag_index:
                self._tag_index[tag] = [
                    x for x in self._tag_index[tag] if x != item_id
                ]

        del self._items[item_id]

    @property
    def stats(self) -> dict:
        """إحصائيات المخزن"""
        domains = {d: len(ids) for d, ids in self._domain_index.items() if ids}
        return {
            "total_items": len(self._items),
            "ingestion_count": self._ingestion_count,
            "domains": domains,
            "max_items": self._max_items,
        }

    def _auto_persist(self) -> None:
        if self._persist_path:
            self._save(self._persist_path)

    def _save(self, path: str) -> None:
        data = {
            "items": [
                {
                    "id": i.item_id,
                    "content": i.content,
                    "domain": i.domain,
                    "tags": i.tags,
                    "source": i.source,
                    "confidence": i.confidence,
                    "access_count": i.access_count,
                }
                for i in self._items.values()
            ]
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self, path: str) -> None:
        if not Path(path).exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item_data in data.get("items", []):
                item = KnowledgeItem(
                    item_id=item_data["id"],
                    content=item_data["content"],
                    domain=item_data.get("domain", ""),
                    tags=item_data.get("tags", []),
                    source=item_data.get("source", ""),
                    confidence=item_data.get("confidence", 1.0),
                    access_count=item_data.get("access_count", 0),
                    created_at=time.time(),
                    last_accessed=time.time(),
                )
                self._items[item.item_id] = item
                if item.domain not in self._domain_index:
                    self._domain_index[item.domain] = []
                self._domain_index[item.domain].append(item.item_id)
                for tag in item.tags:
                    if tag not in self._tag_index:
                        self._tag_index[tag] = []
                    self._tag_index[tag].append(item.item_id)
        except Exception as e:
            logger.warning(f"Failed to load knowledge store: {e}")
