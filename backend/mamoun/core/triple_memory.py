"""
BABSHARQII v40.0 — Triple Memory Manager
Connects to PostgreSQL (episodic), Neo4j (semantic), and ChromaDB (procedural).
Falls back to SQLite when other databases are unavailable.

Memory Architecture:
  - Episodic   → PostgreSQL : conversations, events, experiences (time-series)
  - Semantic   → Neo4j      : knowledge graph, relationships, concepts
  - Procedural → ChromaDB   : vectors, skills, embeddings (similarity search)
"""

import json
import time
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

from mamoun.config import settings, DB_PATH

logger = logging.getLogger("mamoun.triple_memory")


# =============================================================================
# Data Types
# =============================================================================

@dataclass
class MemoryEntry:
    """A unified memory entry that can be stored in any of the three systems."""
    id: str
    memory_type: str  # 'episodic', 'semantic', 'procedural'
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SearchResult:
    """A search result from any memory system."""
    entry: MemoryEntry
    score: float
    source: str  # 'postgresql', 'neo4j', 'chromadb', 'sqlite_fallback'

    def to_dict(self) -> dict:
        return {
            "entry": self.entry.to_dict(),
            "score": self.score,
            "source": self.source,
        }


# =============================================================================
# Connection Wrappers
# =============================================================================

class PostgreSQLConnection:
    """Episodic memory — conversations, events, experiences."""

    def __init__(self):
        self.host = settings.postgres_host
        self.port = settings.postgres_port
        self.dbname = settings.postgres_db
        self.user = settings.postgres_user
        self.password = settings.postgres_password
        self._pool = None
        self._available = False

    def connect(self) -> bool:
        """Try to connect to PostgreSQL. Returns True on success."""
        try:
            import psycopg2
            self._pool = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                connect_timeout=5,
            )
            self._pool.autocommit = True
            self._ensure_schema()
            self._available = True
            logger.info(f"PostgreSQL connected: {self.host}:{self.port}/{self.dbname}")
            return True
        except Exception as e:
            logger.warning(f"PostgreSQL unavailable: {e}")
            self._available = False
            return False

    def _ensure_schema(self):
        """Create tables if they don't exist."""
        if not self._pool:
            return
        with self._pool.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS episodic_memory (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    timestamp REAL DEFAULT extract_epoch from now(),
                    tags TEXT[] DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT now()
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_episodic_timestamp
                ON episodic_memory (timestamp DESC);
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_episodic_tags
                ON episodic_memory USING GIN (tags);
            """)

    @property
    def available(self) -> bool:
        if not self._available:
            return False
        try:
            with self._pool.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except Exception:
            self._available = False
            return False

    def store_episodic(self, entry: MemoryEntry) -> bool:
        if not self.available:
            return False
        try:
            with self._pool.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO episodic_memory (id, content, metadata, timestamp, tags)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        metadata = EXCLUDED.metadata,
                        tags = EXCLUDED.tags
                    """,
                    (entry.id, entry.content, json.dumps(entry.metadata), entry.timestamp, entry.tags),
                )
            return True
        except Exception as e:
            logger.error(f"PostgreSQL store failed: {e}")
            return False

    def retrieve_episodic(self, entry_id: str) -> Optional[MemoryEntry]:
        if not self.available:
            return None
        try:
            with self._pool.cursor() as cur:
                cur.execute(
                    "SELECT id, content, metadata, timestamp, tags FROM episodic_memory WHERE id = %s",
                    (entry_id,),
                )
                row = cur.fetchone()
                if row:
                    return MemoryEntry(
                        id=row[0],
                        memory_type="episodic",
                        content=row[1],
                        metadata=json.loads(row[2]) if isinstance(row[2], str) else row[2],
                        timestamp=row[3],
                        tags=row[4] or [],
                    )
                return None
        except Exception as e:
            logger.error(f"PostgreSQL retrieve failed: {e}")
            return None

    def search_episodic(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Full-text search in episodic memory."""
        if not self.available:
            return []
        try:
            with self._pool.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, content, metadata, timestamp, tags,
                           similarity(content, %s) as score
                    FROM episodic_memory
                    WHERE content %% %s
                    ORDER BY score DESC
                    LIMIT %s
                    """,
                    (query, query, limit),
                )
                results = []
                for row in cur.fetchall():
                    results.append(SearchResult(
                        entry=MemoryEntry(
                            id=row[0],
                            memory_type="episodic",
                            content=row[1],
                            metadata=json.loads(row[2]) if isinstance(row[2], str) else row[2],
                            timestamp=row[3],
                            tags=row[4] or [],
                        ),
                        score=row[5] or 0.0,
                        source="postgresql",
                    ))
                return results
        except Exception as e:
            logger.error(f"PostgreSQL search failed: {e}")
            return []

    def delete_episodic(self, entry_id: str) -> bool:
        if not self.available:
            return False
        try:
            with self._pool.cursor() as cur:
                cur.execute("DELETE FROM episodic_memory WHERE id = %s", (entry_id,))
            return cur.rowcount > 0
        except Exception as e:
            logger.error(f"PostgreSQL delete failed: {e}")
            return False


class Neo4jConnection:
    """Semantic memory — knowledge graph, relationships, concepts."""

    def __init__(self):
        self.uri = settings.neo4j_uri
        self.user = settings.neo4j_user
        self.password = settings.neo4j_password
        self._driver = None
        self._available = False

    def connect(self) -> bool:
        """Try to connect to Neo4j. Returns True on success."""
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                connection_timeout=5,
            )
            # Verify connectivity
            self._driver.verify_connectivity()
            self._ensure_constraints()
            self._available = True
            logger.info(f"Neo4j connected: {self.uri}")
            return True
        except Exception as e:
            logger.warning(f"Neo4j unavailable: {e}")
            self._available = False
            return False

    def _ensure_constraints(self):
        """Create uniqueness constraints if they don't exist."""
        if not self._driver:
            return
        with self._driver.session() as session:
            session.run(
                "CREATE CONSTRAINT semantic_node_id IF NOT EXISTS "
                "FOR (n:SemanticNode) REQUIRE n.id IS UNIQUE"
            )

    @property
    def available(self) -> bool:
        if not self._available:
            return False
        try:
            with self._driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception:
            self._available = False
            return False

    def store_semantic(self, entry: MemoryEntry) -> bool:
        """Store a semantic node with its relationships."""
        if not self.available:
            return False
        try:
            with self._driver.session() as session:
                # Create or update the node
                session.run(
                    """
                    MERGE (n:SemanticNode {id: $id})
                    SET n.content = $content,
                        n.memory_type = $memory_type,
                        n.timestamp = $timestamp,
                        n.tags = $tags,
                        n.metadata = $metadata
                    """,
                    id=entry.id,
                    content=entry.content,
                    memory_type=entry.memory_type,
                    timestamp=entry.timestamp,
                    tags=entry.tags,
                    metadata=json.dumps(entry.metadata),
                )
                # Create relationships from metadata
                relations = entry.metadata.get("relations", [])
                for rel in relations:
                    target_id = rel.get("target_id", "")
                    rel_type = rel.get("type", "RELATED_TO")
                    if target_id and rel_type:
                        # Sanitize relationship type for Cypher
                        safe_rel_type = "".join(c for c in rel_type.upper() if c.isalnum() or c == "_")
                        if not safe_rel_type:
                            safe_rel_type = "RELATED_TO"
                        session.run(
                            f"""
                            MERGE (t:SemanticNode {{id: $target_id}})
                            WITH t
                            MATCH (n:SemanticNode {{id: $id}})
                            MERGE (n)-[:{safe_rel_type}]->(t)
                            """,
                            id=entry.id,
                            target_id=target_id,
                        )
            return True
        except Exception as e:
            logger.error(f"Neo4j store failed: {e}")
            return False

    def retrieve_semantic(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a semantic node by ID."""
        if not self.available:
            return None
        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (n:SemanticNode {id: $id})
                    RETURN n.id, n.content, n.memory_type, n.timestamp,
                           n.tags, n.metadata
                    """,
                    id=entry_id,
                )
                record = result.single()
                if record:
                    return MemoryEntry(
                        id=record["n.id"],
                        memory_type=record["n.memory_type"] or "semantic",
                        content=record["n.content"],
                        metadata=json.loads(record["n.metadata"]) if isinstance(record["n.metadata"], str) else (record["n.metadata"] or {}),
                        timestamp=record["n.timestamp"] or time.time(),
                        tags=record["n.tags"] or [],
                    )
                return None
        except Exception as e:
            logger.error(f"Neo4j retrieve failed: {e}")
            return None

    def search_semantic(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search semantic nodes by content or tags."""
        if not self.available:
            return []
        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (n:SemanticNode)
                    WHERE n.content CONTAINS $query OR $query IN n.tags
                    RETURN n.id, n.content, n.memory_type, n.timestamp,
                           n.tags, n.metadata
                    LIMIT $limit
                    """,
                    query=query,
                    limit=limit,
                )
                results = []
                for record in result:
                    results.append(SearchResult(
                        entry=MemoryEntry(
                            id=record["n.id"],
                            memory_type=record["n.memory_type"] or "semantic",
                            content=record["n.content"],
                            metadata=json.loads(record["n.metadata"]) if isinstance(record["n.metadata"], str) else (record["n.metadata"] or {}),
                            timestamp=record["n.timestamp"] or time.time(),
                            tags=record["n.tags"] or [],
                        ),
                        score=1.0,  # Neo4j doesn't return relevance scores
                        source="neo4j",
                    ))
                return results
        except Exception as e:
            logger.error(f"Neo4j search failed: {e}")
            return []

    def delete_semantic(self, entry_id: str) -> bool:
        """Delete a semantic node and its relationships."""
        if not self.available:
            return False
        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (n:SemanticNode {id: $id})
                    DETACH DELETE n
                    RETURN count(n) as deleted
                    """,
                    id=entry_id,
                )
                record = result.single()
                return record and record["deleted"] > 0
        except Exception as e:
            logger.error(f"Neo4j delete failed: {e}")
            return False


class ChromaDBConnection:
    """Procedural memory — vectors, skills, embeddings."""

    def __init__(self):
        self.host = settings.chroma_host
        self.port = settings.chroma_port
        self._client = None
        self._collection = None
        self._available = False

    def connect(self) -> bool:
        """Try to connect to ChromaDB. Returns True on success."""
        try:
            import chromadb
            self._client = chromadb.HttpClient(
                host=self.host,
                port=self.port,
                timeout=5,
            )
            # Verify connection
            self._client.heartbeat()
            # Get or create the main collection
            self._collection = self._client.get_or_create_collection(
                name="procedural_memory",
                metadata={"description": "BABSHARQII procedural memory — skills and patterns"},
            )
            self._available = True
            logger.info(f"ChromaDB connected: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.warning(f"ChromaDB unavailable: {e}")
            self._available = False
            return False

    @property
    def available(self) -> bool:
        if not self._available:
            return False
        try:
            self._client.heartbeat()
            return True
        except Exception:
            self._available = False
            return False

    def store_procedural(self, entry: MemoryEntry) -> bool:
        """Store a procedural memory entry with its embedding."""
        if not self.available or not self._collection:
            return False
        try:
            metadata = {
                "memory_type": entry.memory_type,
                "timestamp": entry.timestamp,
                "tags": json.dumps(entry.tags),
                **{k: str(v) for k, v in entry.metadata.items() if isinstance(v, (str, int, float, bool))},
            }

            if entry.embedding:
                self._collection.upsert(
                    ids=[entry.id],
                    documents=[entry.content],
                    embeddings=[entry.embedding],
                    metadatas=[metadata],
                )
            else:
                # Let ChromaDB generate embeddings
                self._collection.upsert(
                    ids=[entry.id],
                    documents=[entry.content],
                    metadatas=[metadata],
                )
            return True
        except Exception as e:
            logger.error(f"ChromaDB store failed: {e}")
            return False

    def retrieve_procedural(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a procedural memory entry by ID."""
        if not self.available or not self._collection:
            return None
        try:
            result = self._collection.get(ids=[entry_id], include=["documents", "metadatas", "embeddings"])
            if result["ids"]:
                meta = result["metadatas"][0] if result["metadatas"] else {}
                tags = json.loads(meta.pop("tags", "[]"))
                return MemoryEntry(
                    id=result["ids"][0],
                    memory_type=meta.pop("memory_type", "procedural"),
                    content=result["documents"][0] if result["documents"] else "",
                    metadata=meta,
                    timestamp=meta.get("timestamp", time.time()),
                    tags=tags,
                    embedding=result["embeddings"][0] if result.get("embeddings") else None,
                )
            return None
        except Exception as e:
            logger.error(f"ChromaDB retrieve failed: {e}")
            return None

    def search_procedural(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search procedural memory by similarity."""
        if not self.available or not self._collection:
            return []
        try:
            result = self._collection.query(
                query_texts=[query],
                n_results=limit,
                include=["documents", "metadatas", "distances"],
            )
            results = []
            if result["ids"] and result["ids"][0]:
                for i, doc_id in enumerate(result["ids"][0]):
                    meta = result["metadatas"][0][i] if result["metadatas"] else {}
                    tags = json.loads(meta.pop("tags", "[]"))
                    distance = result["distances"][0][i] if result.get("distances") else 0
                    # Convert distance to similarity score (1 - distance for cosine)
                    score = max(0, 1 - distance)
                    results.append(SearchResult(
                        entry=MemoryEntry(
                            id=doc_id,
                            memory_type=meta.pop("memory_type", "procedural"),
                            content=result["documents"][0][i] if result["documents"] else "",
                            metadata=meta,
                            timestamp=meta.get("timestamp", time.time()),
                            tags=tags,
                        ),
                        score=score,
                        source="chromadb",
                    ))
            return results
        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}")
            return []

    def delete_procedural(self, entry_id: str) -> bool:
        """Delete a procedural memory entry."""
        if not self.available or not self._collection:
            return False
        try:
            self._collection.delete(ids=[entry_id])
            return True
        except Exception as e:
            logger.error(f"ChromaDB delete failed: {e}")
            return False


# =============================================================================
# SQLite Fallback
# =============================================================================

class SQLiteFallback:
    """Fallback store using SQLite when other databases are unavailable."""

    def __init__(self, db_path=None):
        if db_path is None:
            self.db_path = DB_PATH
        elif isinstance(db_path, str):
            # Handle :memory: and string paths
            self.db_path = db_path
        else:
            self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        """Create the fallback memory table if it doesn't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_fallback (
                    id TEXT PRIMARY KEY,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    timestamp REAL DEFAULT 0,
                    tags TEXT DEFAULT '[]',
                    embedding TEXT DEFAULT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_fallback_type
                ON memory_fallback (memory_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_fallback_timestamp
                ON memory_fallback (timestamp DESC)
            """)
            conn.commit()
        finally:
            conn.close()

    def store(self, entry: MemoryEntry) -> bool:
        try:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO memory_fallback
                    (id, memory_type, content, metadata, timestamp, tags, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry.id,
                        entry.memory_type,
                        entry.content,
                        json.dumps(entry.metadata),
                        entry.timestamp,
                        json.dumps(entry.tags),
                        json.dumps(entry.embedding) if entry.embedding else None,
                    ),
                )
                conn.commit()
                return True
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"SQLite fallback store failed: {e}")
            return False

    def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        try:
            conn = sqlite3.connect(str(self.db_path))
            try:
                cur = conn.execute(
                    "SELECT id, memory_type, content, metadata, timestamp, tags, embedding FROM memory_fallback WHERE id = ?",
                    (entry_id,),
                )
                row = cur.fetchone()
                if row:
                    return MemoryEntry(
                        id=row[0],
                        memory_type=row[1],
                        content=row[2],
                        metadata=json.loads(row[3]),
                        timestamp=row[4],
                        tags=json.loads(row[5]),
                        embedding=json.loads(row[6]) if row[6] else None,
                    )
                return None
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"SQLite fallback retrieve failed: {e}")
            return None

    def search(self, query: str, memory_type: Optional[str] = None, limit: int = 10) -> List[SearchResult]:
        """Simple LIKE-based search in the fallback store."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            try:
                if memory_type:
                    cur = conn.execute(
                        """
                        SELECT id, memory_type, content, metadata, timestamp, tags
                        FROM memory_fallback
                        WHERE memory_type = ? AND content LIKE ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (memory_type, f"%{query}%", limit),
                    )
                else:
                    cur = conn.execute(
                        """
                        SELECT id, memory_type, content, metadata, timestamp, tags
                        FROM memory_fallback
                        WHERE content LIKE ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (f"%{query}%", limit),
                    )
                results = []
                for row in cur.fetchall():
                    results.append(SearchResult(
                        entry=MemoryEntry(
                            id=row[0],
                            memory_type=row[1],
                            content=row[2],
                            metadata=json.loads(row[3]),
                            timestamp=row[4],
                            tags=json.loads(row[5]),
                        ),
                        score=0.5,  # Fixed score for LIKE search
                        source="sqlite_fallback",
                    ))
                return results
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"SQLite fallback search failed: {e}")
            return []

    def delete(self, entry_id: str) -> bool:
        try:
            conn = sqlite3.connect(str(self.db_path))
            try:
                cur = conn.execute("DELETE FROM memory_fallback WHERE id = ?", (entry_id,))
                conn.commit()
                return cur.rowcount > 0
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"SQLite fallback delete failed: {e}")
            return False


# =============================================================================
# Triple Memory Manager
# =============================================================================

class TripleMemoryManager:
    """
    Unified interface for the triple memory system.

    Routes operations to the appropriate database based on memory type:
      - episodic   → PostgreSQL (fallback: SQLite)
      - semantic   → Neo4j (fallback: SQLite)
      - procedural → ChromaDB (fallback: SQLite)
    """

    def __init__(self):
        self._postgres = PostgreSQLConnection()
        self._neo4j = Neo4jConnection()
        self._chroma = ChromaDBConnection()
        self._sqlite = SQLiteFallback()
        self._initialized = False

    def initialize(self) -> Dict[str, bool]:
        """Attempt to connect to all databases. Returns connection statuses."""
        statuses = {
            "postgresql": self._postgres.connect(),
            "neo4j": self._neo4j.connect(),
            "chromadb": self._chroma.connect(),
        }
        self._initialized = True
        logger.info(f"Triple Memory initialized: {statuses}")
        return statuses

    def get_status(self) -> Dict[str, Any]:
        """Get the current connection status of all databases."""
        if not self._initialized:
            self.initialize()
        return {
            "postgresql": {
                "connected": self._postgres.available,
                "purpose": "الذاكرة الحلقاتية (أحداث وخبرات)",
                "type": "episodic",
            },
            "neo4j": {
                "connected": self._neo4j.available,
                "purpose": "الذاكرة الدلالية (رسم بياني معرفي)",
                "type": "semantic",
            },
            "chromadb": {
                "connected": self._chroma.available,
                "purpose": "الذاكرة الإجرائية (متجهات وتشابه)",
                "type": "procedural",
            },
            "sqlite_fallback": {
                "connected": True,
                "purpose": "الذاكرة الاحتياطية (عند عدم توفر قواعد أخرى)",
                "type": "fallback",
                "location": str(self._sqlite.db_path),
            },
        }

    # ── Unified Interface ──────────────────────────────────────────────

    def store(self, entry: MemoryEntry) -> bool:
        """
        Store a memory entry in the appropriate database based on its type.

        Routes:
          - episodic   → PostgreSQL
          - semantic   → Neo4j
          - procedural → ChromaDB

        Always stores in SQLite fallback as well for resilience.
        """
        if not self._initialized:
            self.initialize()

        # Always store in SQLite fallback for resilience
        self._sqlite.store(entry)

        if entry.memory_type == "episodic":
            success = self._postgres.store_episodic(entry)
            if success:
                logger.debug(f"Stored episodic entry {entry.id} in PostgreSQL")
                return True
            logger.warning(f"PostgreSQL store failed, entry {entry.id} in SQLite fallback only")
            return True  # SQLite fallback already stored

        elif entry.memory_type == "semantic":
            success = self._neo4j.store_semantic(entry)
            if success:
                logger.debug(f"Stored semantic entry {entry.id} in Neo4j")
                return True
            logger.warning(f"Neo4j store failed, entry {entry.id} in SQLite fallback only")
            return True

        elif entry.memory_type == "procedural":
            success = self._chroma.store_procedural(entry)
            if success:
                logger.debug(f"Stored procedural entry {entry.id} in ChromaDB")
                return True
            logger.warning(f"ChromaDB store failed, entry {entry.id} in SQLite fallback only")
            return True

        else:
            logger.warning(f"Unknown memory type '{entry.memory_type}', stored in SQLite fallback only")
            return True

    def retrieve(self, entry_id: str, memory_type: Optional[str] = None) -> Optional[MemoryEntry]:
        """
        Retrieve a memory entry by ID.

        If memory_type is specified, only queries that database.
        Otherwise, tries all databases in order.
        """
        if not self._initialized:
            self.initialize()

        if memory_type == "episodic":
            result = self._postgres.retrieve_episodic(entry_id)
            return result or self._sqlite.retrieve(entry_id)

        elif memory_type == "semantic":
            result = self._neo4j.retrieve_semantic(entry_id)
            return result or self._sqlite.retrieve(entry_id)

        elif memory_type == "procedural":
            result = self._chroma.retrieve_procedural(entry_id)
            return result or self._sqlite.retrieve(entry_id)

        else:
            # Try all databases
            for retriever in [
                self._postgres.retrieve_episodic,
                self._neo4j.retrieve_semantic,
                self._chroma.retrieve_procedural,
            ]:
                try:
                    result = retriever(entry_id)
                    if result:
                        return result
                except Exception:
                    continue
            return self._sqlite.retrieve(entry_id)

    def search(self, query: str, memory_type: Optional[str] = None, limit: int = 10) -> List[SearchResult]:
        """
        Search across memory systems.

        If memory_type is specified, only searches that database.
        Otherwise, searches all databases and merges results.
        """
        if not self._initialized:
            self.initialize()

        results: List[SearchResult] = []

        if memory_type == "episodic" or memory_type is None:
            try:
                results.extend(self._postgres.search_episodic(query, limit))
            except Exception as e:
                logger.error(f"PostgreSQL search error: {e}")

        if memory_type == "semantic" or memory_type is None:
            try:
                results.extend(self._neo4j.search_semantic(query, limit))
            except Exception as e:
                logger.error(f"Neo4j search error: {e}")

        if memory_type == "procedural" or memory_type is None:
            try:
                results.extend(self._chroma.search_procedural(query, limit))
            except Exception as e:
                logger.error(f"ChromaDB search error: {e}")

        # Always include SQLite fallback results if no primary results or explicitly requested
        if not results or memory_type is None:
            try:
                results.extend(self._sqlite.search(query, memory_type, limit))
            except Exception as e:
                logger.error(f"SQLite fallback search error: {e}")

        # Deduplicate by entry ID (prefer primary over fallback)
        seen_ids = set()
        deduped = []
        for r in results:
            if r.entry.id not in seen_ids:
                seen_ids.add(r.entry.id)
                deduped.append(r)

        # Sort by score descending
        deduped.sort(key=lambda r: r.score, reverse=True)
        return deduped[:limit]

    def delete(self, entry_id: str, memory_type: Optional[str] = None) -> bool:
        """
        Delete a memory entry from all databases.

        If memory_type is specified, only deletes from that database.
        Otherwise, attempts deletion from all databases.
        """
        if not self._initialized:
            self.initialize()

        success = False

        if memory_type == "episodic" or memory_type is None:
            if self._postgres.delete_episodic(entry_id):
                success = True

        if memory_type == "semantic" or memory_type is None:
            if self._neo4j.delete_semantic(entry_id):
                success = True

        if memory_type == "procedural" or memory_type is None:
            if self._chroma.delete_procedural(entry_id):
                success = True

        # Always try to delete from fallback too
        if self._sqlite.delete(entry_id):
            success = True

        return success


# =============================================================================
# Singleton
# =============================================================================

triple_memory = TripleMemoryManager()
