"""
BABSHARQII v40.0 — Episodic Memory Store
مخزن الذاكرة الحلقية — تخزين واسترجاع التجارب والمحادثات والقرارات

Stores agent conversations, decisions, and experiences in a lightweight
vector database (ChromaDB) with SQLite fallback. Supports:

  • Episodic entries with timestamps, participants, emotions, context
  • Similarity search via embeddings (TF-IDF fallback when no model)
  • Time-range queries and participant-based filtering
  • Integration with StrategicForgetting for automatic lifecycle management

Architecture:
  ┌──────────────────────────────────────────────────────────────────────┐
  │                   EpisodicMemoryStore                                │
  │                                                                      │
  │  ┌────────────────────┐  ┌─────────────────────────────────────────┐│
  │  │ ChromaDB Backend   │  │ SQLite Fallback                         ││
  │  │ (vector similarity │  │ (LIKE search + TF-IDF scoring,         ││
  │  │  via embeddings)   │  │  always-active resilience layer)        ││
  │  └────────┬───────────┘  └──────────────┬──────────────────────────┘│
  │           │                             │                            │
  │  ┌────────▼─────────────────────────────▼────────────────────────┐ │
  │  │              Unified Query Interface                          │ │
  │  │  store_episode / retrieve_episode / search_episodes           │ │
  │  │  search_by_time_range / search_by_participant                │ │
  │  │  get_recent_episodes                                          │ │
  │  └──────────────────────────────────────────────────────────────┘ │
  └──────────────────────────────────────────────────────────────────────┘

Env toggles:
    MAMOUN_EPISODIC_MEMORY_ENABLED — تمكين/تعطيل الذاكرة الحلقية (الافتراضي: false)
"""

from __future__ import annotations

import os
import re
import uuid
import time
import json
import math
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from collections import Counter

from mamoun.config import DB_PATH

logger = logging.getLogger("mamoun.episodic_memory")

# ─── مفاتيح التهيئة البيئية — Environment Config ─────────────────────────────

EPISODIC_MEMORY_ENABLED: bool = os.environ.get(
    "MAMOUN_EPISODIC_MEMORY_ENABLED", "false"
).lower() in ("true", "1", "yes")


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج البيانات — Data Models
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class EpisodicEntry:
    """
    مدخل ذاكرة حلقية — يمثل حلقة واحدة من تجربة الوكيل.
    A single episodic memory entry representing an agent experience.

    أنواع الحلقات — Episode types:
      - conversation: محادثة — a dialogue exchange
      - decision: قرار — a decision made by the agent
      - observation: ملاحظة — something the agent observed
      - learning: تعلّم — a learning event or insight
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    episode_type: str = "conversation"       # نوع الحلقة
    content: str = ""                        # المحتوى الرئيسي
    participants: List[str] = field(default_factory=list)   # المشاركون
    emotions: List[str] = field(default_factory=list)       # المشاعر المرتبطة
    context: Dict[str, Any] = field(default_factory=dict)   # سياق إضافي
    timestamp: float = field(default_factory=time.time)     # وقت الإنشاء
    importance_score: float = 0.5            # درجة الأهمية (0-1)
    access_count: int = 0                    # عدد مرات الوصول
    last_accessed: float = field(default_factory=time.time) # آخر وصول
    tags: List[str] = field(default_factory=list)           # وسوم
    embedding: Optional[List[float]] = None  # المتجه المُدمج

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary."""
        result = asdict(self)
        # Remove embedding from dict output (too large for JSON serialization usually)
        result.pop("embedding", None)
        return result


@dataclass
class EpisodicSearchResult:
    """
    نتيجة بحث حلقية — نتيجة واحدة من بحث الذاكرة الحلقية.
    A single search result from episodic memory.
    """
    entry: EpisodicEntry = field(default_factory=EpisodicEntry)
    score: float = 0.0          # درجة التشابه (0-1)
    source: str = "sqlite"      # المصدر: 'chromadb' أو 'sqlite'

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary."""
        return {
            "entry": self.entry.to_dict(),
            "score": round(self.score, 4),
            "source": self.source,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  توليد المتجهات — Embedding Generation (TF-IDF Fallback)
# ═══════════════════════════════════════════════════════════════════════════════


class TFIDFEmbedder:
    """
    مُولّد متجهات TF-IDF — بديل بسيط لنماذج التضمين.
    Simple TF-IDF based embedding generator as fallback when no
    embedding model is available.

    يُنشئ متجهات ثنائية الأبعاد (مُخفّضة) من نص عربي/إنجليزي.
    Generates reduced-dimension vectors from Arabic/English text.
    """

    # حجم المتجه — Embedding dimension
    DIMENSION: int = 128

    def __init__(self):
        self._vocabulary: Dict[str, int] = {}
        self._idf_cache: Dict[str, float] = {}
        self._doc_count: int = 0

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """
        تقسيم النص إلى كلمات — Tokenize text into words.
        Handles Arabic and English text.
        """
        # Remove punctuation and normalize
        text = text.lower().strip()
        # Arabic normalization: remove diacritics
        text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
        # Split on non-alphanumeric (preserves Arabic and English)
        tokens = re.findall(r'[\u0600-\u06FF\u0750-\u077Fa-zA-Z0-9]+', text)
        return tokens

    def _build_vocabulary(self, tokens: List[str]) -> None:
        """بناء المفردات — Build vocabulary from tokens."""
        for token in tokens:
            if token not in self._vocabulary:
                self._vocabulary[token] = len(self._vocabulary)

    def embed(self, text: str) -> List[float]:
        """
        توليد متجه من النص — Generate embedding vector from text.
        Uses a simple bag-of-words approach with TF normalization,
        reduced to the target dimension via hashing.
        """
        tokens = self._tokenize(text)
        if not tokens:
            return [0.0] * self.DIMENSION

        # Build vocabulary on the fly
        self._build_vocabulary(tokens)
        self._doc_count += 1

        # Compute term frequency
        tf_counts = Counter(tokens)
        max_tf = max(tf_counts.values()) if tf_counts else 1
        tf_norm = {t: 0.5 + 0.5 * (c / max_tf) for t, c in tf_counts.items()}

        # Generate fixed-dimension vector via hashing
        vector = [0.0] * self.DIMENSION
        for token, tf_val in tf_norm.items():
            # Hash token to dimension indices (2 indices per token for better coverage)
            idx1 = hash(token) % self.DIMENSION
            idx2 = (hash(token + "_2") ^ hash(token)) % self.DIMENSION
            weight = tf_val
            vector[idx1] += weight
            vector[idx2] += weight * 0.5

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        """
        حساب تشابه جيب التمام — Compute cosine similarity between two vectors.
        """
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


# ═══════════════════════════════════════════════════════════════════════════════
#  مخزن الذاكرة الحلقية — EpisodicMemoryStore
# ═══════════════════════════════════════════════════════════════════════════════


class EpisodicMemoryStore:
    """
    مخزن الذاكرة الحلقية — Episodic Memory Store.

    Stores and retrieves episodic memories (conversations, decisions,
    observations, learnings) with support for:

      • Vector similarity search (ChromaDB primary, SQLite fallback)
      • Time-range queries
      • Participant-based filtering
      • Automatic embedding generation (TF-IDF fallback)
      • Integration with StrategicForgetting for lifecycle management

    يتكامل مع النسيان الإستراتيجي لإدارة دورة حياة الذكريات تلقائياً.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        تهيئة مخزن الذاكرة الحلقية — Initialize the episodic memory store.

        Args:
            db_path: مسار قاعدة بيانات SQLite الاحتياطية
        """
        self._db_path = db_path or DB_PATH
        self._chroma_client = None
        self._chroma_collection = None
        self._chroma_available = False
        self._embedder = TFIDFEmbedder()
        self._initialized = False

    # ─── التهيئة — Initialization ──────────────────────────────────────────

    def _initialize(self) -> None:
        """تهيئة المكونات — Initialize components."""
        if self._initialized:
            return
        self._ensure_schema()
        self._connect_chromadb()
        self._initialized = True
        logger.info("تم تهيئة مخزن الذاكرة الحلقية")

    def _ensure_schema(self) -> None:
        """إنشاء جداول SQLite إذا لم تكن موجودة — Create SQLite tables if missing."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path))
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodic_memory_v14 (
                    id TEXT PRIMARY KEY,
                    episode_type TEXT NOT NULL DEFAULT 'conversation',
                    content TEXT NOT NULL,
                    participants TEXT DEFAULT '[]',
                    emotions TEXT DEFAULT '[]',
                    context TEXT DEFAULT '{}',
                    timestamp REAL DEFAULT 0,
                    importance_score REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    last_accessed REAL DEFAULT 0,
                    tags TEXT DEFAULT '[]',
                    embedding TEXT DEFAULT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_episodic_v14_timestamp
                ON episodic_memory_v14 (timestamp DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_episodic_v14_type
                ON episodic_memory_v14 (episode_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_episodic_v14_importance
                ON episodic_memory_v14 (importance_score DESC)
            """)
            conn.commit()
        finally:
            conn.close()

    def _connect_chromadb(self) -> None:
        """محاولة الاتصال بـ ChromaDB — Attempt ChromaDB connection."""
        try:
            import chromadb
            # Try persistent client first (local directory-based)
            chroma_dir = self._db_path.parent / "chroma_episodic"
            chroma_dir.mkdir(parents=True, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(path=str(chroma_dir))
            self._chroma_collection = self._chroma_client.get_or_create_collection(
                name="episodic_memory_v14",
                metadata={
                    "description": "BABSHARQII v14 — الذاكرة الحلقية — Episodic Memory",
                    "version": "14.0",
                },
            )
            self._chroma_available = True
            logger.info("تم الاتصال بـ ChromaDB للذاكرة الحلقية")
        except Exception as e:
            logger.warning(f"ChromaDB غير متاح، سيتم استخدام SQLite: {e}")
            self._chroma_available = False

    # ─── التخزين — Store ──────────────────────────────────────────────────

    def store_episode(self, entry: EpisodicEntry) -> str:
        """
        تخزين حلقة ذاكرة — Store an episodic memory entry.

        Generates embedding if not provided, stores in both ChromaDB
        (if available) and SQLite fallback.

        Args:
            entry: مدخل الذاكرة الحلقية — the episodic entry to store

        Returns:
            معرف المدخل — the entry ID
        """
        self._initialize()

        if not EPISODIC_MEMORY_ENABLED:
            logger.debug("الذاكرة الحلقية معطلة — Episodic memory disabled")
            return entry.id

        # Generate embedding if missing
        if entry.embedding is None:
            entry.embedding = self._embedder.embed(entry.content)

        # Store in SQLite (always, for resilience)
        self._store_sqlite(entry)

        # Store in ChromaDB (if available)
        if self._chroma_available:
            self._store_chromadb(entry)

        logger.debug(f"تم تخزين حلقة ذاكرة: {entry.id} ({entry.episode_type})")
        return entry.id

    def _store_sqlite(self, entry: EpisodicEntry) -> None:
        """تخزين في SQLite — Store entry in SQLite."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO episodic_memory_v14
                    (id, episode_type, content, participants, emotions, context,
                     timestamp, importance_score, access_count, last_accessed, tags, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry.id,
                        entry.episode_type,
                        entry.content,
                        json.dumps(entry.participants, ensure_ascii=False),
                        json.dumps(entry.emotions, ensure_ascii=False),
                        json.dumps(entry.context, ensure_ascii=False),
                        entry.timestamp,
                        entry.importance_score,
                        entry.access_count,
                        entry.last_accessed,
                        json.dumps(entry.tags, ensure_ascii=False),
                        json.dumps(entry.embedding) if entry.embedding else None,
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"فشل تخزين SQLite: {e}")

    def _store_chromadb(self, entry: EpisodicEntry) -> None:
        """تخزين في ChromaDB — Store entry in ChromaDB."""
        if not self._chroma_available or not self._chroma_collection:
            return
        try:
            metadata = {
                "episode_type": entry.episode_type,
                "timestamp": entry.timestamp,
                "importance_score": entry.importance_score,
                "access_count": entry.access_count,
                "last_accessed": entry.last_accessed,
                "tags": json.dumps(entry.tags, ensure_ascii=False),
                "participants": json.dumps(entry.participants, ensure_ascii=False),
                "emotions": json.dumps(entry.emotions, ensure_ascii=False),
            }
            # Only include string/number/bool values in metadata
            clean_meta = {k: str(v) for k, v in metadata.items()}

            if entry.embedding:
                self._chroma_collection.upsert(
                    ids=[entry.id],
                    documents=[entry.content],
                    embeddings=[entry.embedding],
                    metadatas=[clean_meta],
                )
            else:
                self._chroma_collection.upsert(
                    ids=[entry.id],
                    documents=[entry.content],
                    metadatas=[clean_meta],
                )
        except Exception as e:
            logger.error(f"فشل تخزين ChromaDB: {e}")

    # ─── الاسترجاع — Retrieve ─────────────────────────────────────────────

    def retrieve_episode(self, entry_id: str) -> Optional[EpisodicEntry]:
        """
        استرجاع حلقة ذاكرة بالمعرف — Retrieve an episode by ID.

        يحدّث عدد الوصول وآخر وصول تلقائياً.
        Automatically updates access_count and last_accessed.

        Args:
            entry_id: معرف الحلقة — the episode ID

        Returns:
            المدخل أو لا شيء — the entry or None
        """
        self._initialize()

        # Try ChromaDB first
        entry = None
        if self._chroma_available:
            entry = self._retrieve_chromadb(entry_id)

        # Fallback to SQLite
        if entry is None:
            entry = self._retrieve_sqlite(entry_id)

        # Update access metadata
        if entry is not None:
            entry.access_count += 1
            entry.last_accessed = time.time()
            self._update_access_metadata(entry)

        return entry

    def _retrieve_sqlite(self, entry_id: str) -> Optional[EpisodicEntry]:
        """استرجاع من SQLite — Retrieve from SQLite."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cur = conn.execute(
                    """
                    SELECT id, episode_type, content, participants, emotions, context,
                           timestamp, importance_score, access_count, last_accessed, tags, embedding
                    FROM episodic_memory_v14
                    WHERE id = ?
                    """,
                    (entry_id,),
                )
                row = cur.fetchone()
                if row:
                    return self._row_to_entry(row)
                return None
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"فشل استرجاع SQLite: {e}")
            return None

    def _retrieve_chromadb(self, entry_id: str) -> Optional[EpisodicEntry]:
        """استرجاع من ChromaDB — Retrieve from ChromaDB."""
        if not self._chroma_available or not self._chroma_collection:
            return None
        try:
            result = self._chroma_collection.get(
                ids=[entry_id],
                include=["documents", "metadatas", "embeddings"],
            )
            if result["ids"]:
                meta = result["metadatas"][0] if result["metadatas"] else {}
                doc = result["documents"][0] if result["documents"] else ""
                embedding = result["embeddings"][0] if result.get("embeddings") else None
                return EpisodicEntry(
                    id=result["ids"][0],
                    episode_type=meta.get("episode_type", "conversation"),
                    content=doc,
                    participants=json.loads(meta.get("participants", "[]")),
                    emotions=json.loads(meta.get("emotions", "[]")),
                    context=json.loads(meta.get("context", "{}")) if "context" in meta else {},
                    timestamp=float(meta.get("timestamp", 0)),
                    importance_score=float(meta.get("importance_score", 0.5)),
                    access_count=int(meta.get("access_count", 0)),
                    last_accessed=float(meta.get("last_accessed", 0)),
                    tags=json.loads(meta.get("tags", "[]")),
                    embedding=embedding,
                )
            return None
        except Exception as e:
            logger.error(f"فشل استرجاع ChromaDB: {e}")
            return None

    def _update_access_metadata(self, entry: EpisodicEntry) -> None:
        """تحديث بيانات الوصول — Update access metadata for an entry."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    """
                    UPDATE episodic_memory_v14
                    SET access_count = ?, last_accessed = ?
                    WHERE id = ?
                    """,
                    (entry.access_count, entry.last_accessed, entry.id),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"فشل تحديث بيانات الوصول: {e}")

    # ─── البحث — Search ────────────────────────────────────────────────────

    def search_episodes(
        self,
        query: str,
        limit: int = 10,
        episode_type: Optional[str] = None,
    ) -> List[EpisodicSearchResult]:
        """
        بحث في الذكريات الحلقية — Search episodic memories by similarity.

        Args:
            query: نص البحث — search text
            limit: الحد الأقصى للنتائج — max results
            episode_type: تصفية حسب النوع — filter by episode type

        Returns:
            قائمة نتائج البحث — list of search results
        """
        self._initialize()

        if not EPISODIC_MEMORY_ENABLED:
            return []

        results: List[EpisodicSearchResult] = []

        # Try ChromaDB vector search first
        if self._chroma_available:
            chroma_results = self._search_chromadb(query, limit, episode_type)
            results.extend(chroma_results)

        # Always include SQLite results (with TF-IDF scoring)
        sqlite_results = self._search_sqlite(query, limit, episode_type)
        results.extend(sqlite_results)

        # Deduplicate by entry ID (prefer ChromaDB results)
        seen_ids: set = set()
        deduped: List[EpisodicSearchResult] = []
        for r in results:
            if r.entry.id not in seen_ids:
                seen_ids.add(r.entry.id)
                deduped.append(r)

        # Sort by score descending
        deduped.sort(key=lambda r: r.score, reverse=True)
        return deduped[:limit]

    def _search_chromadb(
        self,
        query: str,
        limit: int,
        episode_type: Optional[str] = None,
    ) -> List[EpisodicSearchResult]:
        """بحث متجهي في ChromaDB — Vector search in ChromaDB."""
        if not self._chroma_available or not self._chroma_collection:
            return []
        try:
            query_embedding = self._embedder.embed(query)

            where_filter = None
            if episode_type:
                where_filter = {"episode_type": episode_type}

            result = self._chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter,
                include=["documents", "metadatas", "distances", "embeddings"],
            )

            results: List[EpisodicSearchResult] = []
            if result["ids"] and result["ids"][0]:
                for i, doc_id in enumerate(result["ids"][0]):
                    meta = result["metadatas"][0][i] if result["metadatas"] else {}
                    distance = result["distances"][0][i] if result.get("distances") else 0
                    score = max(0.0, 1.0 - distance)

                    entry = EpisodicEntry(
                        id=doc_id,
                        episode_type=meta.get("episode_type", "conversation"),
                        content=result["documents"][0][i] if result["documents"] else "",
                        participants=json.loads(meta.get("participants", "[]")),
                        emotions=json.loads(meta.get("emotions", "[]")),
                        context=json.loads(meta.get("context", "{}")) if "context" in meta else {},
                        timestamp=float(meta.get("timestamp", 0)),
                        importance_score=float(meta.get("importance_score", 0.5)),
                        access_count=int(meta.get("access_count", 0)),
                        last_accessed=float(meta.get("last_accessed", 0)),
                        tags=json.loads(meta.get("tags", "[]")),
                        embedding=result["embeddings"][0][i] if result.get("embeddings") else None,
                    )
                    results.append(EpisodicSearchResult(
                        entry=entry,
                        score=score,
                        source="chromadb",
                    ))
            return results
        except Exception as e:
            logger.error(f"فشل بحث ChromaDB: {e}")
            return []

    def _search_sqlite(
        self,
        query: str,
        limit: int,
        episode_type: Optional[str] = None,
    ) -> List[EpisodicSearchResult]:
        """بحث في SQLite مع تسجيل TF-IDF — SQLite search with TF-IDF scoring."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            try:
                if episode_type:
                    cur = conn.execute(
                        """
                        SELECT id, episode_type, content, participants, emotions, context,
                               timestamp, importance_score, access_count, last_accessed, tags, embedding
                        FROM episodic_memory_v14
                        WHERE episode_type = ? AND content LIKE ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (episode_type, f"%{query}%", limit * 2),
                    )
                else:
                    cur = conn.execute(
                        """
                        SELECT id, episode_type, content, participants, emotions, context,
                               timestamp, importance_score, access_count, last_accessed, tags, embedding
                        FROM episodic_memory_v14
                        WHERE content LIKE ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (f"%{query}%", limit * 2),
                    )

                query_embedding = self._embedder.embed(query)
                results: List[EpisodicSearchResult] = []

                for row in cur.fetchall():
                    entry = self._row_to_entry(row)
                    # Compute similarity score
                    if entry.embedding:
                        entry_vec = entry.embedding
                    else:
                        entry_vec = self._embedder.embed(entry.content)

                    score = TFIDFEmbedder.cosine_similarity(query_embedding, entry_vec)
                    # Boost by importance
                    score = score * (0.5 + 0.5 * entry.importance_score)

                    results.append(EpisodicSearchResult(
                        entry=entry,
                        score=score,
                        source="sqlite",
                    ))

                return results
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"فشل بحث SQLite: {e}")
            return []

    # ─── البحث بالوقت — Time-range Search ─────────────────────────────────

    def search_by_time_range(
        self,
        start_time: float,
        end_time: float,
        episode_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[EpisodicEntry]:
        """
        بحث حسب النطاق الزمني — Search by time range.

        Args:
            start_time: بداية النطاق الزمني (Unix timestamp)
            end_time: نهاية النطاق الزمني (Unix timestamp)
            episode_type: تصفية حسب النوع (اختياري)
            limit: الحد الأقصى للنتائج

        Returns:
            قائمة المدخلات في النطاق الزمني
        """
        self._initialize()

        try:
            conn = sqlite3.connect(str(self._db_path))
            try:
                if episode_type:
                    cur = conn.execute(
                        """
                        SELECT id, episode_type, content, participants, emotions, context,
                               timestamp, importance_score, access_count, last_accessed, tags, embedding
                        FROM episodic_memory_v14
                        WHERE timestamp >= ? AND timestamp <= ? AND episode_type = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (start_time, end_time, episode_type, limit),
                    )
                else:
                    cur = conn.execute(
                        """
                        SELECT id, episode_type, content, participants, emotions, context,
                               timestamp, importance_score, access_count, last_accessed, tags, embedding
                        FROM episodic_memory_v14
                        WHERE timestamp >= ? AND timestamp <= ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (start_time, end_time, limit),
                    )

                entries: List[EpisodicEntry] = []
                for row in cur.fetchall():
                    entries.append(self._row_to_entry(row))
                return entries
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"فشل البحث الزمني: {e}")
            return []

    # ─── البحث بالمشارك — Participant Search ──────────────────────────────

    def search_by_participant(
        self,
        participant: str,
        limit: int = 20,
    ) -> List[EpisodicEntry]:
        """
        بحث حسب المشارك — Search by participant.

        Args:
            participant: اسم المشارك أو معرّفه
            limit: الحد الأقصى للنتائج

        Returns:
            قائمة المدخلات التي يشارك فيها المشارك المحدد
        """
        self._initialize()

        try:
            conn = sqlite3.connect(str(self._db_path))
            try:
                # Use JSON-like search in participants array
                cur = conn.execute(
                    """
                    SELECT id, episode_type, content, participants, emotions, context,
                           timestamp, importance_score, access_count, last_accessed, tags, embedding
                    FROM episodic_memory_v14
                    WHERE participants LIKE ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (f'%"{participant}"%', limit),
                )
                entries: List[EpisodicEntry] = []
                for row in cur.fetchall():
                    entry = self._row_to_entry(row)
                    # Double-check: only include if participant is actually in the list
                    if participant in entry.participants:
                        entries.append(entry)
                return entries
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"فشل البحث بالمشارك: {e}")
            return []

    # ─── الذكريات الأخيرة — Recent Episodes ──────────────────────────────

    def get_recent_episodes(
        self,
        limit: int = 10,
        episode_type: Optional[str] = None,
    ) -> List[EpisodicEntry]:
        """
        الحصول على أحدث الذكريات — Get the most recent episodic entries.

        Args:
            limit: الحد الأقصى للنتائج
            episode_type: تصفية حسب النوع (اختياري)

        Returns:
            قائمة أحدث المدخلات مرتبة زمنياً
        """
        self._initialize()

        try:
            conn = sqlite3.connect(str(self._db_path))
            try:
                if episode_type:
                    cur = conn.execute(
                        """
                        SELECT id, episode_type, content, participants, emotions, context,
                               timestamp, importance_score, access_count, last_accessed, tags, embedding
                        FROM episodic_memory_v14
                        WHERE episode_type = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (episode_type, limit),
                    )
                else:
                    cur = conn.execute(
                        """
                        SELECT id, episode_type, content, participants, emotions, context,
                               timestamp, importance_score, access_count, last_accessed, tags, embedding
                        FROM episodic_memory_v14
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (limit,),
                    )

                entries: List[EpisodicEntry] = []
                for row in cur.fetchall():
                    entries.append(self._row_to_entry(row))
                return entries
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"فشل جلب الذكريات الأخيرة: {e}")
            return []

    # ─── الحذف — Delete ────────────────────────────────────────────────────

    def delete_episode(self, entry_id: str) -> bool:
        """
        حذف حلقة ذاكرة — Delete an episodic memory entry.

        Args:
            entry_id: معرف الحلقة

        Returns:
            True إذا تم الحذف بنجاح
        """
        self._initialize()

        success = False

        # Delete from SQLite
        try:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cur = conn.execute(
                    "DELETE FROM episodic_memory_v14 WHERE id = ?",
                    (entry_id,),
                )
                conn.commit()
                if cur.rowcount > 0:
                    success = True
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"فشل حذف SQLite: {e}")

        # Delete from ChromaDB
        if self._chroma_available and self._chroma_collection:
            try:
                self._chroma_collection.delete(ids=[entry_id])
                success = True
            except Exception as e:
                logger.error(f"فشل حذف ChromaDB: {e}")

        return success

    # ─── تحديث — Update ────────────────────────────────────────────────────

    def update_episode(self, entry: EpisodicEntry) -> bool:
        """
        تحديث حلقة ذاكرة — Update an existing episodic memory entry.

        Args:
            entry: المدخل المحدّث

        Returns:
            True إذا تم التحديث بنجاح
        """
        self._initialize()

        # Re-generate embedding if content changed
        if entry.embedding is None:
            entry.embedding = self._embedder.embed(entry.content)

        self._store_sqlite(entry)
        if self._chroma_available:
            self._store_chromadb(entry)

        return True

    # ─── إحصائيات — Statistics ─────────────────────────────────────────────

    def get_all_entries(self, limit: int = 1000) -> List[EpisodicEntry]:
        """
        الحصول على جميع المدخلات — Get all episodic entries.
        Used primarily by StrategicForgetting for cycle evaluation.

        Args:
            limit: الحد الأقصى للنتائج

        Returns:
            قائمة جميع المدخلات
        """
        self._initialize()

        try:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cur = conn.execute(
                    """
                    SELECT id, episode_type, content, participants, emotions, context,
                           timestamp, importance_score, access_count, last_accessed, tags, embedding
                    FROM episodic_memory_v14
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                entries: List[EpisodicEntry] = []
                for row in cur.fetchall():
                    entries.append(self._row_to_entry(row))
                return entries
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"فشل جلب جميع المدخلات: {e}")
            return []

    def count_episodes(self, episode_type: Optional[str] = None) -> int:
        """
        عدد الذكريات — Count episodic entries.

        Args:
            episode_type: تصفية حسب النوع (اختياري)

        Returns:
            عدد المدخلات
        """
        self._initialize()

        try:
            conn = sqlite3.connect(str(self._db_path))
            try:
                if episode_type:
                    cur = conn.execute(
                        "SELECT COUNT(*) FROM episodic_memory_v14 WHERE episode_type = ?",
                        (episode_type,),
                    )
                else:
                    cur = conn.execute(
                        "SELECT COUNT(*) FROM episodic_memory_v14",
                    )
                row = cur.fetchone()
                return row[0] if row else 0
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"فشل عد الذكريات: {e}")
            return 0

    # ─── الحالة والإيقاف — Status & Shutdown ─────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """
        حالة مخزن الذاكرة الحلقية — Episodic memory store status.
        """
        if not self._initialized:
            self._initialize()
        return {
            "enabled": EPISODIC_MEMORY_ENABLED,
            "initialized": self._initialized,
            "chromadb_available": self._chroma_available,
            "total_episodes": self.count_episodes(),
            "by_type": {
                "conversation": self.count_episodes("conversation"),
                "decision": self.count_episodes("decision"),
                "observation": self.count_episodes("observation"),
                "learning": self.count_episodes("learning"),
            },
            "db_path": str(self._db_path),
            "وصف": "مخزن الذاكرة الحلقية — Episodic Memory Store",
        }

    def shutdown(self) -> None:
        """
        إيقاف مخزن الذاكرة الحلقية — Shutdown the episodic memory store.
        """
        self._chroma_client = None
        self._chroma_collection = None
        self._chroma_available = False
        self._initialized = False
        logger.info("تم إيقاف مخزن الذاكرة الحلقية")

    # ─── أدوات مساعدة — Utilities ─────────────────────────────────────────

    @staticmethod
    def _row_to_entry(row: tuple) -> EpisodicEntry:
        """تحويل صف SQLite إلى مدخل — Convert SQLite row to EpisodicEntry."""
        return EpisodicEntry(
            id=row[0],
            episode_type=row[1],
            content=row[2],
            participants=json.loads(row[3]) if row[3] else [],
            emotions=json.loads(row[4]) if row[4] else [],
            context=json.loads(row[5]) if row[5] else {},
            timestamp=row[6],
            importance_score=row[7],
            access_count=row[8],
            last_accessed=row[9],
            tags=json.loads(row[10]) if row[10] else [],
            embedding=json.loads(row[11]) if row[11] else None,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton — النسخة الوحيدة
# ═══════════════════════════════════════════════════════════════════════════════

episodic_memory_store = EpisodicMemoryStore()
