"""
BABSHARQII v24.0 — World Knowledge Graph
الرسم البياني المعرفي العالمي — مأمون يبني نموذجاً للعالم

Unlike CausalGraph (which stores causal relationships), WorldGraph stores:
- ENTITIES: people, places, concepts, technologies, organizations
- RELATIONS: works_at, located_in, competitor_of, part_of, related_to
- FACTS: with confidence scores and source tracking
- TEMPORAL: facts that change over time (stock prices, events)

This builds a persistent knowledge base that grows with every interaction.
"""
import os, time, uuid, json, logging
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from pathlib import Path

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.world_graph")


@dataclass
class WorldEntity:
    """كيان في العالم — شخص، مكان، مفهوم، تقنية، منظمة"""
    entity_id: str = ""
    name: str = ""
    entity_type: str = "concept"  # person, place, tech, org, event, concept
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.8
    source: str = ""  # where did we learn about this
    first_seen: float = 0.0
    last_updated: float = 0.0

    def __post_init__(self):
        if not self.entity_id:
            self.entity_id = f"ent_{uuid.uuid4().hex[:8]}"
        if not self.first_seen:
            self.first_seen = time.time()
        if not self.last_updated:
            self.last_updated = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WorldRelation:
    """علاقة بين كيانين"""
    relation_id: str = ""
    source_entity_id: str = ""
    target_entity_id: str = ""
    relation_type: str = ""  # works_at, located_in, competitor_of, etc.
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.7
    temporal_start: float = 0.0  # when this relation started
    temporal_end: float = 0.0    # when it ended (0 = still active)
    source: str = ""
    created_at: float = 0.0

    def __post_init__(self):
        if not self.relation_id:
            self.relation_id = f"rel_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


class WorldKnowledgeGraph:
    """
    الرسم البياني المعرفي العالمي
    
    Usage:
        wkg = WorldKnowledgeGraph()
        wkg.initialize()
        
        # Add entities
        openai = wkg.add_entity("OpenAI", entity_type="org", properties={"founded": 2015})
        sam = wkg.add_entity("Sam Altman", entity_type="person")
        
        # Add relation
        wkg.add_relation("Sam Altman", "OpenAI", "ceo_of", confidence=0.95)
        
        # Query
        connections = wkg.get_connections("OpenAI")
        path = wkg.find_path("Sam Altman", "GPT-4")
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._entities: Dict[str, WorldEntity] = {}
        self._relations: Dict[str, WorldRelation] = {}
        self._name_index: Dict[str, str] = {}  # lowercase name → entity_id
        self._adjacency: Dict[str, List[str]] = {}  # entity_id → [relation_ids]
        self._llm = None
        self._initialized = False

    def set_llm_client(self, llm_client):
        self._llm = llm_client

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("WorldKnowledgeGraph initialized — %d entities, %d relations",
                       len(self._entities), len(self._relations))
            return True
        except Exception as e:
            logger.error("WorldKnowledgeGraph init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS wg_entities (
                    entity_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    entity_type TEXT DEFAULT 'concept',
                    properties TEXT DEFAULT '{}',
                    confidence REAL DEFAULT 0.8,
                    source TEXT DEFAULT '',
                    first_seen REAL DEFAULT 0,
                    last_updated REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS wg_relations (
                    relation_id TEXT PRIMARY KEY,
                    source_entity_id TEXT NOT NULL,
                    target_entity_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    properties TEXT DEFAULT '{}',
                    confidence REAL DEFAULT 0.7,
                    temporal_start REAL DEFAULT 0,
                    temporal_end REAL DEFAULT 0,
                    source TEXT DEFAULT '',
                    created_at REAL DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_wg_ent_name ON wg_entities(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_wg_rel_src ON wg_relations(source_entity_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_wg_rel_tgt ON wg_relations(target_entity_id)")
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT * FROM wg_entities"):
                e = WorldEntity(
                    entity_id=row[0], name=row[1], entity_type=row[2],
                    properties=json.loads(row[3]), confidence=row[4],
                    source=row[5], first_seen=row[6], last_updated=row[7]
                )
                self._entities[e.entity_id] = e
                self._name_index[e.name.lower()] = e.entity_id

            for row in conn.execute("SELECT * FROM wg_relations"):
                r = WorldRelation(
                    relation_id=row[0], source_entity_id=row[1],
                    target_entity_id=row[2], relation_type=row[3],
                    properties=json.loads(row[4]), confidence=row[5],
                    temporal_start=row[6], temporal_end=row[7],
                    source=row[8], created_at=row[9]
                )
                self._relations[r.relation_id] = r
                self._adjacency.setdefault(r.source_entity_id, []).append(r.relation_id)
        finally:
            conn.close()

    def _persist_entity(self, e: WorldEntity):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO wg_entities
                (entity_id, name, entity_type, properties, confidence, source, first_seen, last_updated)
                VALUES (?,?,?,?,?,?,?,?)
            """, (e.entity_id, e.name, e.entity_type, json.dumps(e.properties),
                  e.confidence, e.source, e.first_seen, e.last_updated))
            conn.commit()
        finally:
            conn.close()

    def _persist_relation(self, r: WorldRelation):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO wg_relations
                (relation_id, source_entity_id, target_entity_id, relation_type,
                 properties, confidence, temporal_start, temporal_end, source, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (r.relation_id, r.source_entity_id, r.target_entity_id,
                  r.relation_type, json.dumps(r.properties), r.confidence,
                  r.temporal_start, r.temporal_end, r.source, r.created_at))
            conn.commit()
        finally:
            conn.close()

    def add_entity(self, name: str, entity_type: str = "concept",
                   properties: Dict = None, confidence: float = 0.8,
                   source: str = "") -> WorldEntity:
        existing = self._name_index.get(name.lower())
        if existing and existing in self._entities:
            e = self._entities[existing]
            e.last_updated = time.time()
            if properties:
                e.properties.update(properties)
            self._persist_entity(e)
            return e

        e = WorldEntity(name=name, entity_type=entity_type,
                        properties=properties or {}, confidence=confidence, source=source)
        self._entities[e.entity_id] = e
        self._name_index[name.lower()] = e.entity_id
        self._persist_entity(e)
        return e

    def add_relation(self, source_name: str, target_name: str,
                     relation_type: str, confidence: float = 0.7,
                     source: str = "") -> Optional[WorldRelation]:
        src = self.add_entity(source_name)
        tgt = self.add_entity(target_name)

        # Check for existing relation of same type
        for rid in self._adjacency.get(src.entity_id, []):
            r = self._relations[rid]
            if r.target_entity_id == tgt.entity_id and r.relation_type == relation_type:
                r.confidence = max(r.confidence, confidence)
                self._persist_relation(r)
                return r

        r = WorldRelation(
            source_entity_id=src.entity_id, target_entity_id=tgt.entity_id,
            relation_type=relation_type, confidence=confidence, source=source,
        )
        self._relations[r.relation_id] = r
        self._adjacency.setdefault(src.entity_id, []).append(r.relation_id)
        self._persist_relation(r)
        return r

    def get_connections(self, entity_name: str, depth: int = 1) -> Dict:
        """الحصول على جميع اتصالات كيان"""
        eid = self._name_index.get(entity_name.lower())
        if not eid:
            return {"entity": entity_name, "connections": []}

        visited = {eid}
        result = []
        frontier = [eid]

        for _ in range(depth):
            next_frontier = []
            for fid in frontier:
                for rid in self._adjacency.get(fid, []):
                    r = self._relations[rid]
                    target = self._entities.get(r.target_entity_id)
                    if target and target.entity_id not in visited:
                        visited.add(target.entity_id)
                        result.append({
                            "entity": target.name,
                            "relation": r.relation_type,
                            "confidence": r.confidence,
                        })
                        next_frontier.append(target.entity_id)
            frontier = next_frontier

        return {"entity": entity_name, "connections": result}

    def find_path(self, source_name: str, target_name: str, max_depth: int = 6) -> List[Dict]:
        """إيجاد مسار بين كيانين"""
        src_eid = self._name_index.get(source_name.lower())
        tgt_eid = self._name_index.get(target_name.lower())
        if not src_eid or not tgt_eid:
            return []

        from collections import deque
        visited = {src_eid}
        queue = deque([(src_eid, [])])

        while queue:
            current, path = queue.popleft()
            if len(path) >= max_depth:
                continue

            for rid in self._adjacency.get(current, []):
                r = self._relations[rid]
                if r.target_entity_id == tgt_eid:
                    src_name = self._entities.get(r.source_entity_id, WorldEntity(name="?")).name
                    tgt_name = self._entities.get(r.target_entity_id, WorldEntity(name="?")).name
                    return path + [{"from": src_name, "to": tgt_name, "via": r.relation_type}]

                if r.target_entity_id not in visited:
                    visited.add(r.target_entity_id)
                    src_name = self._entities.get(r.source_entity_id, WorldEntity(name="?")).name
                    tgt_name = self._entities.get(r.target_entity_id, WorldEntity(name="?")).name
                    queue.append((r.target_entity_id, path + [{"from": src_name, "to": tgt_name, "via": r.relation_type}]))

        return []

    def get_stats(self) -> Dict:
        return {
            "entities": len(self._entities),
            "relations": len(self._relations),
            "entity_types": list(set(e.entity_type for e in self._entities.values())),
            "relation_types": list(set(r.relation_type for r in self._relations.values())),
        }


world_knowledge_graph = WorldKnowledgeGraph()
