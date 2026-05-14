"""
BABSHARQII v25.0 — Knowledge Bridge
جسر المعرفة — ربط المفاهيم بين النطاقات

Maps conceptual knowledge between domains using:
1. Concept embedding alignment
2. Structural similarity detection
3. Cross-domain analogy generation
4. Knowledge graph bridging

Unlike DomainAdapter (which operates on weight matrices),
KnowledgeBridge operates on conceptual representations.
"""

import time
import uuid
import json
import logging
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.knowledge_bridge")


@dataclass
class ConceptMap:
    """خريطة مفاهيم — ربط بين مفهومين في نطاقين مختلفين"""
    map_id: str = ""
    source_concept: str = ""
    source_domain: str = ""
    target_concept: str = ""
    target_domain: str = ""
    similarity: float = 0.0
    mapping_type: str = "analogical"  # analogical, structural, functional
    evidence: List[str] = field(default_factory=list)
    created_at: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class KnowledgeBridge:
    """
    جسر المعرفة — يربط المفاهيم عبر النطاقات

    Usage:
        bridge = KnowledgeBridge()
        bridge.initialize()

        # Register concepts in domains
        bridge.register_concept("neural_network", "AI", embedding=np.array([...]))
        bridge.register_concept("brain", "Biology", embedding=np.array([...]))

        # Find analogies
        analogies = bridge.find_analogies("neural_network", "AI", target_domain="Biology")
        # → "brain" (analogical similarity)
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._concepts: Dict[str, Dict] = {}  # "domain:concept" → {embedding, metadata}
        self._concept_maps: Dict[str, ConceptMap] = {}
        self._llm = None
        self._initialized = False

    def set_llm_client(self, llm_client):
        self._llm = llm_client

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("KnowledgeBridge initialized — %d concepts, %d maps",
                       len(self._concepts), len(self._concept_maps))
            return True
        except Exception as e:
            logger.error("KnowledgeBridge init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kb_concepts (
                    concept_key TEXT PRIMARY KEY,
                    concept_name TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    embedding TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}',
                    created_at REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kb_maps (
                    map_id TEXT PRIMARY KEY,
                    source_concept TEXT NOT NULL,
                    source_domain TEXT NOT NULL,
                    target_concept TEXT NOT NULL,
                    target_domain TEXT NOT NULL,
                    similarity REAL DEFAULT 0,
                    mapping_type TEXT DEFAULT 'analogical',
                    evidence TEXT DEFAULT '[]',
                    created_at REAL DEFAULT 0
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT * FROM kb_concepts"):
                key = row[0]
                embedding = None
                if row[3]:
                    embedding = np.frombuffer(bytes.fromhex(row[3]), dtype=np.float64).copy()
                self._concepts[key] = {
                    "name": row[1], "domain": row[2],
                    "embedding": embedding,
                    "metadata": json.loads(row[4]),
                }
        finally:
            conn.close()

    def register_concept(self, name: str, domain: str,
                         embedding: np.ndarray = None,
                         metadata: Dict = None) -> Dict:
        """تسجيل مفهوم في نطاق"""
        key = f"{domain}:{name}"
        self._concepts[key] = {
            "name": name, "domain": domain,
            "embedding": embedding,
            "metadata": metadata or {},
        }

        # Persist
        conn = get_db_connection(self.db_path)
        try:
            emb_hex = embedding.tobytes().hex() if embedding is not None else ""
            conn.execute("""
                INSERT OR REPLACE INTO kb_concepts
                (concept_key, concept_name, domain, embedding, metadata, created_at)
                VALUES (?,?,?,?,?,?)
            """, (key, name, domain, emb_hex, json.dumps(metadata or {}), time.time()))
            conn.commit()
        finally:
            conn.close()

        return {"concept": name, "domain": domain, "key": key}

    def find_analogies(self, concept: str, source_domain: str,
                       target_domain: str = None,
                       top_k: int = 5) -> List[Dict]:
        """
        إيجاد تشبيهات — مفاهيم مشابهة في نطاق آخر

        Uses cosine similarity between embeddings to find
        structurally similar concepts across domains.
        """
        src_key = f"{source_domain}:{concept}"
        src_data = self._concepts.get(src_key)
        if not src_data or src_data["embedding"] is None:
            return []

        src_emb = src_data["embedding"]
        results = []

        for key, data in self._concepts.items():
            if key == src_key:
                continue
            if target_domain and data["domain"] != target_domain:
                continue
            if source_domain and data["domain"] == source_domain:
                continue  # Skip same domain

            if data["embedding"] is not None:
                # Cosine similarity
                sim = float(np.dot(src_emb, data["embedding"]) /
                           (np.linalg.norm(src_emb) * np.linalg.norm(data["embedding"]) + 1e-10))
                results.append({
                    "source": concept,
                    "source_domain": source_domain,
                    "target": data["name"],
                    "target_domain": data["domain"],
                    "similarity": round(sim, 4),
                    "mapping_type": "analogical",
                })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def bridge_domains(self, source_domain: str, target_domain: str,
                       concept_pairs: List[Tuple[str, str]] = None) -> Dict:
        """
        بناء جسر بين نطاقين — إنشاء خريطة مفاهيمية
        """
        bridges_created = 0

        if concept_pairs:
            for src_concept, tgt_concept in concept_pairs:
                src_key = f"{source_domain}:{src_concept}"
                tgt_key = f"{target_domain}:{tgt_concept}"
                src_data = self._concepts.get(src_key)
                tgt_data = self._concepts.get(tgt_key)

                sim = 0.5  # default
                if (src_data and tgt_data and
                    src_data["embedding"] is not None and
                    tgt_data["embedding"] is not None):
                    sim = float(np.dot(src_data["embedding"], tgt_data["embedding"]) /
                               (np.linalg.norm(src_data["embedding"]) *
                                np.linalg.norm(tgt_data["embedding"]) + 1e-10))

                cmap = ConceptMap(
                    map_id=f"map_{uuid.uuid4().hex[:8]}",
                    source_concept=src_concept,
                    source_domain=source_domain,
                    target_concept=tgt_concept,
                    target_domain=target_domain,
                    similarity=sim,
                    created_at=time.time(),
                )
                self._concept_maps[cmap.map_id] = cmap
                bridges_created += 1

        return {
            "source_domain": source_domain,
            "target_domain": target_domain,
            "bridges_created": bridges_created,
            "total_bridges": len(self._concept_maps),
        }

    def get_stats(self) -> Dict:
        return {
            "concepts": len(self._concepts),
            "concept_maps": len(self._concept_maps),
            "domains": list(set(d["domain"] for d in self._concepts.values())),
        }


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

knowledge_bridge = KnowledgeBridge()
