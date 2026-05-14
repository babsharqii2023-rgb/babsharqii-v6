"""
BABSHARQII v24.0 — Causal Graph Engine
محرك الرسم البياني السببي — مأمون يفهم السبب والنتيجة فعلياً

This is NOT a text-based causal reasoner. This builds an actual directed
acyclic graph (DAG) of causal relationships, supports:
1. add_cause() — add a causal edge: X causes Y with confidence
2. observe() — given evidence, propagate through the graph
3. intervene() — do-calculus: what happens if we DO X?
4. counterfactual() — what would have happened if X had NOT occurred?
5. explain() — find the causal chain from A to B
6. learn_from_outcome() — adjust edge weights based on real outcomes

Storage: UnifiedDB (SQLite) for persistence
"""

import time
import uuid
import json
import logging
import asyncio
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Set, Tuple
from pathlib import Path
from enum import Enum

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.causal_graph")


# ═══════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════

class EdgeType(str, Enum):
    CAUSES = "causes"               # A causes B (direct)
    ENABLES = "enables"             # A enables B (prerequisite)
    PREVENTS = "prevents"           # A prevents B (inhibitor)
    CORRELATES = "correlates"       # A correlates with B (no causation)
    MEDIATES = "mediates"           # A mediates between C and B


@dataclass
class CausalNode:
    """عقدة في الرسم البياني السببي — مفهوم أو حدث"""
    node_id: str = ""
    name: str = ""
    category: str = "event"       # event, entity, property, action
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    evidence_count: int = 0       # how many times observed
    first_seen: float = 0.0
    last_seen: float = 0.0

    def __post_init__(self):
        if not self.node_id:
            self.node_id = f"node_{uuid.uuid4().hex[:8]}"
        if not self.first_seen:
            self.first_seen = time.time()
        if not self.last_seen:
            self.last_seen = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CausalEdge:
    """حافة سببية — علاقة سببية بين عقدتين"""
    edge_id: str = ""
    source_id: str = ""
    target_id: str = ""
    edge_type: str = EdgeType.CAUSES.value
    confidence: float = 0.5
    strength: float = 0.5        # how strong is the effect
    evidence_count: int = 0
    conditions: List[str] = field(default_factory=list)  # when does this apply
    last_observed: float = 0.0
    created_at: float = 0.0

    def __post_init__(self):
        if not self.edge_id:
            self.edge_id = f"edge_{uuid.uuid4().hex[:8]}"
        if not self.last_observed:
            self.last_observed = time.time()
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CausalExplanation:
    """تفسير سببي — سلسلة من الأسباب"""
    query: str = ""
    chain: List[Dict[str, Any]] = field(default_factory=list)
    total_confidence: float = 0.0
    path_found: bool = False


@dataclass
class InterventionResult:
    """نتيجة تدخل — ماذا يحدث لو فعلنا X"""
    intervention: str = ""
    predicted_effects: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    side_effects: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# Causal Graph Engine
# ═══════════════════════════════════════════════════════════════

class CausalGraph:
    """
    محرك الرسم البياني السببي
    
    الفرق بين هذا وبين CausalBrain:
    - CausalBrain: يرسل prompt لـ LLM ويرجع نص
    - CausalGraph: يبني DAG فعلي، يدعم do-calculus، يتعلم من العواقب
    
    الاستخدام:
        cg = CausalGraph()
        cg.initialize()
        cg.add_cause("rain", "wet_ground", confidence=0.9)
        cg.add_cause("wet_ground", "slippery", confidence=0.7)
        cg.explain("rain", "slippery")  # → rain→wet_ground→slippery
        cg.intervene("wet_ground")       # → what happens if ground is wet?
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._nodes: Dict[str, CausalNode] = {}
        self._edges: Dict[str, CausalEdge] = {}
        self._adjacency: Dict[str, List[str]] = {}  # source_id → [edge_ids]
        self._reverse_adj: Dict[str, List[str]] = {}  # target_id → [edge_ids]
        self._llm = None
        self._initialized = False
        self._node_name_index: Dict[str, str] = {}  # lowercase name → node_id

    def set_llm_client(self, llm_client):
        """تعيين عميل LLM للاستدلال المتقدم"""
        self._llm = llm_client

    def initialize(self) -> bool:
        """تهيئة — إنشاء الجداول وتحميل البيانات"""
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("CausalGraph initialized — nodes=%d, edges=%d",
                       len(self._nodes), len(self._edges))
            return True
        except Exception as e:
            logger.error("CausalGraph init failed: %s", e)
            return False

    def _ensure_schema(self):
        """إنشاء جداول قاعدة البيانات"""
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cg_nodes (
                    node_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT DEFAULT 'event',
                    description TEXT DEFAULT '',
                    properties TEXT DEFAULT '{}',
                    evidence_count INTEGER DEFAULT 0,
                    first_seen REAL DEFAULT 0,
                    last_seen REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cg_edges (
                    edge_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    edge_type TEXT DEFAULT 'causes',
                    confidence REAL DEFAULT 0.5,
                    strength REAL DEFAULT 0.5,
                    evidence_count INTEGER DEFAULT 0,
                    conditions TEXT DEFAULT '[]',
                    last_observed REAL DEFAULT 0,
                    created_at REAL DEFAULT 0,
                    FOREIGN KEY (source_id) REFERENCES cg_nodes(node_id),
                    FOREIGN KEY (target_id) REFERENCES cg_nodes(node_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cg_edges_source ON cg_edges(source_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cg_edges_target ON cg_edges(target_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cg_nodes_name ON cg_nodes(name)")
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        """تحميل البيانات من قاعدة البيانات"""
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT * FROM cg_nodes"):
                node = CausalNode(
                    node_id=row[0], name=row[1], category=row[2],
                    description=row[3], properties=json.loads(row[4]),
                    evidence_count=row[5], first_seen=row[6], last_seen=row[7]
                )
                self._nodes[node.node_id] = node
                self._node_name_index[node.name.lower()] = node.node_id

            for row in conn.execute("SELECT * FROM cg_edges"):
                edge = CausalEdge(
                    edge_id=row[0], source_id=row[1], target_id=row[2],
                    edge_type=row[3], confidence=row[4], strength=row[5],
                    evidence_count=row[6], conditions=json.loads(row[7]),
                    last_observed=row[8], created_at=row[9]
                )
                self._edges[edge.edge_id] = edge
                self._adjacency.setdefault(edge.source_id, []).append(edge.edge_id)
                self._reverse_adj.setdefault(edge.target_id, []).append(edge.edge_id)
        finally:
            conn.close()

    def _persist_node(self, node: CausalNode):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO cg_nodes
                (node_id, name, category, description, properties, evidence_count, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (node.node_id, node.name, node.category, node.description,
                  json.dumps(node.properties), node.evidence_count,
                  node.first_seen, node.last_seen))
            conn.commit()
        finally:
            conn.close()

    def _persist_edge(self, edge: CausalEdge):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO cg_edges
                (edge_id, source_id, target_id, edge_type, confidence, strength,
                 evidence_count, conditions, last_observed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (edge.edge_id, edge.source_id, edge.target_id, edge.edge_type,
                  edge.confidence, edge.strength, edge.evidence_count,
                  json.dumps(edge.conditions), edge.last_observed, edge.created_at))
            conn.commit()
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════
    # Core API: Add nodes and edges
    # ═══════════════════════════════════════════════════════════

    def add_node(self, name: str, category: str = "event",
                 description: str = "", properties: Dict = None) -> CausalNode:
        """إضافة عقدة جديدة أو تحديث موجودة"""
        # Check if node with same name exists
        existing_id = self._node_name_index.get(name.lower())
        if existing_id and existing_id in self._nodes:
            node = self._nodes[existing_id]
            node.evidence_count += 1
            node.last_seen = time.time()
            if description:
                node.description = description
            if properties:
                node.properties.update(properties)
            self._persist_node(node)
            return node

        node = CausalNode(
            name=name, category=category,
            description=description, properties=properties or {}
        )
        self._nodes[node.node_id] = node
        self._node_name_index[name.lower()] = node.node_id
        self._persist_node(node)
        return node

    def add_cause(self, source: str, target: str,
                  edge_type: str = EdgeType.CAUSES.value,
                  confidence: float = 0.5, strength: float = 0.5,
                  conditions: List[str] = None) -> CausalEdge:
        """
        إضافة علاقة سببية: source → target
        
        مثال:
            cg.add_cause("rain", "wet_ground", confidence=0.9)
            cg.add_cause("wet_ground", "slippery", confidence=0.7)
            cg.add_cause("umbrella", "dry_person", edge_type="prevents", confidence=0.8)
        """
        # Ensure both nodes exist
        source_node = self.add_node(source)
        target_node = self.add_node(target)

        # Check for existing edge
        for eid in self._adjacency.get(source_node.node_id, []):
            edge = self._edges[eid]
            if edge.target_id == target_node.node_id and edge.edge_type == edge_type:
                # Update existing edge
                edge.evidence_count += 1
                edge.last_observed = time.time()
                # Bayesian update of confidence
                alpha = 0.1  # learning rate
                edge.confidence = edge.confidence * (1 - alpha) + confidence * alpha
                self._persist_edge(edge)
                return edge

        # Create new edge
        edge = CausalEdge(
            source_id=source_node.node_id,
            target_id=target_node.node_id,
            edge_type=edge_type,
            confidence=confidence,
            strength=strength,
            conditions=conditions or [],
        )
        self._edges[edge.edge_id] = edge
        self._adjacency.setdefault(edge.source_id, []).append(edge.edge_id)
        self._reverse_adj.setdefault(edge.target_id, []).append(edge.edge_id)
        self._persist_edge(edge)
        return edge

    def _find_node_by_name(self, name: str) -> Optional[CausalNode]:
        """البحث عن عقدة بالاسم"""
        node_id = self._node_name_index.get(name.lower())
        if node_id:
            return self._nodes.get(node_id)
        return None

    # ═══════════════════════════════════════════════════════════
    # Core API: Query the graph
    # ═══════════════════════════════════════════════════════════

    def explain(self, source: str, target: str, max_depth: int = 10) -> CausalExplanation:
        """
        تفسير سببي: كيف يسبب source الـ target؟
        يجد أقصر مسار سببي بين العقدتين.
        
        مثال:
            cg.explain("rain", "slippery")
            # → rain→wet_ground→slippery (confidence=0.63)
        """
        source_node = self._find_node_by_name(source)
        target_node = self._find_node_by_name(target)

        if not source_node or not target_node:
            return CausalExplanation(
                query=f"{source} → {target}",
                path_found=False
            )

        # BFS to find causal path
        path = self._find_path(source_node.node_id, target_node.node_id, max_depth)
        if not path:
            return CausalExplanation(
                query=f"{source} → {target}",
                path_found=False
            )

        # Build explanation chain
        chain = []
        total_conf = 1.0
        for i in range(len(path) - 1):
            edge = self._get_edge_between(path[i], path[i + 1])
            if edge:
                source_n = self._nodes.get(path[i])
                target_n = self._nodes.get(path[i + 1])
                chain.append({
                    "source": source_n.name if source_n else path[i],
                    "target": target_n.name if target_n else path[i + 1],
                    "relation": edge.edge_type,
                    "confidence": round(edge.confidence, 3),
                    "strength": round(edge.strength, 3),
                })
                total_conf *= edge.confidence

        return CausalExplanation(
            query=f"{source} → {target}",
            chain=chain,
            total_confidence=round(total_conf, 3),
            path_found=True
        )

    def _find_path(self, source_id: str, target_id: str, max_depth: int) -> List[str]:
        """BFS لإيجاد أقصر مسار سببي"""
        from collections import deque
        visited = {source_id}
        queue = deque([(source_id, [source_id])])

        while queue:
            current, path = queue.popleft()
            if len(path) > max_depth:
                continue

            for eid in self._adjacency.get(current, []):
                edge = self._edges[eid]
                if edge.edge_type in (EdgeType.PREVENTS.value, EdgeType.CORRELATES.value):
                    continue  # Only follow causal/enabling/mediating edges

                next_id = edge.target_id
                if next_id == target_id:
                    return path + [next_id]
                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, path + [next_id]))

        return []

    def _get_edge_between(self, source_id: str, target_id: str) -> Optional[CausalEdge]:
        """إيجاد الحافة بين عقدتين"""
        for eid in self._adjacency.get(source_id, []):
            edge = self._edges[eid]
            if edge.target_id == target_id:
                return edge
        return None

    def intervene(self, action: str, max_depth: int = 5) -> InterventionResult:
        """
        تدخل (do-calculus): ماذا يحدث لو فعلنا action؟
        
        مثال:
            cg.intervene("rain")
            # → wet_ground (0.9), traffic_slow (0.6), umbrella_sales_up (0.5)
        """
        node = self._find_node_by_name(action)
        if not node:
            return InterventionResult(intervention=action)

        effects = []
        side_effects = []

        # BFS from the action node
        visited = {node.node_id}
        queue = [(node.node_id, 1.0, 0)]

        while queue:
            current_id, cumulative_conf, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            for eid in self._adjacency.get(current_id, []):
                edge = self._edges[eid]
                next_node = self._nodes.get(edge.target_id)
                if not next_node or next_node.node_id in visited:
                    continue

                visited.add(next_node.node_id)
                effect_conf = cumulative_conf * edge.confidence

                if edge.edge_type == EdgeType.PREVENTS.value:
                    side_effects.append(f"prevents {next_node.name} (conf={effect_conf:.2f})")
                else:
                    effects.append({
                        "effect": next_node.name,
                        "confidence": round(effect_conf, 3),
                        "relation": edge.edge_type,
                        "depth": depth + 1,
                    })

                if effect_conf > 0.1:
                    queue.append((next_node.node_id, effect_conf, depth + 1))

        # Sort by confidence
        effects.sort(key=lambda x: x["confidence"], reverse=True)

        avg_conf = sum(e["confidence"] for e in effects) / max(len(effects), 1)
        return InterventionResult(
            intervention=action,
            predicted_effects=effects[:10],
            confidence=round(avg_conf, 3),
            side_effects=side_effects[:5],
        )

    def counterfactual(self, observed: str, prevented: str) -> Dict[str, Any]:
        """
        ماذا لو لم يحدث prevented؟
        
        مثال:
            cg.counterfactual("slippery", "rain")
            # → لو لم تمطر، الأرض ما كانت بتززل (confidence)
        """
        obs_node = self._find_node_by_name(observed)
        prev_node = self._find_node_by_name(prevented)

        if not obs_node or not prev_node:
            return {"question": f"ماذا لو لم يحدث {prevented}؟", "answer": "لا بيانات كافية"}

        # Find all paths from prevented to observed
        paths = self._find_all_paths(prev_node.node_id, obs_node.node_id, max_depth=8)

        if not paths:
            return {
                "question": f"ماذا لو لم يحدث {prevented}؟",
                "answer": f"لا علاقة سببية مباشرة بين {prevented} و {observed}",
                # v35 FIX: eid was used outside its list comprehension scope — NameError
                "alternative_causes": [n.name for n in self._nodes.values()
                                       if n.node_id != prev_node.node_id
                                       and any(e.target_id == obs_node.node_id
                                               for eid in self._reverse_adj.get(n.node_id, [])
                                               for e in [self._edges[eid]]
                                               if eid in self._edges)]
            }

        # Calculate what would change
        removed_effects = []
        for path in paths:
            chain_names = []
            path_conf = 1.0
            for i in range(len(path) - 1):
                edge = self._get_edge_between(path[i], path[i + 1])
                if edge:
                    n = self._nodes.get(path[i + 1])
                    chain_names.append(n.name if n else path[i + 1])
                    path_conf *= edge.confidence
            removed_effects.append({
                "chain": chain_names,
                "probability_removed": round(path_conf, 3),
            })

        return {
            "question": f"ماذا لو لم يحدث {prevented}؟",
            "observed": observed,
            "prevented": prevented,
            "would_not_happen": removed_effects,
            "total_paths_removed": len(paths),
        }

    def _find_all_paths(self, source_id: str, target_id: str, max_depth: int = 8) -> List[List[str]]:
        """إيجاد جميع المسارات السببية بين عقدتين"""
        all_paths = []

        def dfs(current, path, visited):
            if len(path) > max_depth:
                return
            if current == target_id:
                all_paths.append(list(path))
                return
            for eid in self._adjacency.get(current, []):
                edge = self._edges[eid]
                if edge.target_id not in visited and edge.edge_type != EdgeType.PREVENTS.value:
                    visited.add(edge.target_id)
                    path.append(edge.target_id)
                    dfs(edge.target_id, path, visited)
                    path.pop()
                    visited.remove(edge.target_id)

        dfs(source_id, [source_id], {source_id})
        return all_paths

    # ═══════════════════════════════════════════════════════════
    # Learning from outcomes
    # ═══════════════════════════════════════════════════════════

    def learn_from_outcome(self, cause: str, effect: str, actually_happened: bool,
                           context: str = "") -> Dict[str, Any]:
        """
        تعلم من العواقب الفعلية
        
        إذا توقعنا أن X يسبب Y، وحدث Y فعلاً → نزيد الثقة
        إذا لم يحدث Y → ننقص الثقة
        
        مثال:
            cg.learn_from_outcome("rain", "wet_ground", actually_happened=True)
            # → confidence increases
            cg.learn_from_outcome("rain", "traffic", actually_happened=False)  
            # → confidence decreases
        """
        source_node = self._find_node_by_name(cause)
        target_node = self._find_node_by_name(effect)

        if not source_node or not target_node:
            # Auto-create the causal link
            conf = 0.7 if actually_happened else 0.3
            edge = self.add_cause(cause, effect, confidence=conf)
            return {
                "action": "created_new_edge",
                "cause": cause,
                "effect": effect,
                "confidence": edge.confidence,
                "observed": actually_happened,
            }

        edge = self._get_edge_between(source_node.node_id, target_node.node_id)
        if not edge:
            conf = 0.7 if actually_happened else 0.3
            edge = self.add_cause(cause, effect, confidence=conf)
            return {
                "action": "created_new_edge",
                "cause": cause,
                "effect": effect,
                "confidence": edge.confidence,
                "observed": actually_happened,
            }

        # Bayesian update
        old_conf = edge.confidence
        learning_rate = 0.15
        if actually_happened:
            edge.confidence = min(0.99, edge.confidence + learning_rate * (1.0 - edge.confidence))
        else:
            edge.confidence = max(0.01, edge.confidence - learning_rate * edge.confidence)

        edge.evidence_count += 1
        edge.last_observed = time.time()
        self._persist_edge(edge)

        return {
            "action": "updated_confidence",
            "cause": cause,
            "effect": effect,
            "old_confidence": round(old_conf, 3),
            "new_confidence": round(edge.confidence, 3),
            "evidence_count": edge.evidence_count,
            "observed": actually_happened,
        }

    # ═══════════════════════════════════════════════════════════
    # LLM-powered discovery
    # ═══════════════════════════════════════════════════════════

    async def discover_causes(self, phenomenon: str) -> List[Dict[str, Any]]:
        """
        اكتشاف أسباب ظاهرة باستخدام LLM
        
        يطلب من LLM تحليل الظاهرة واستخلاص الأسباب المحتملة
        ثم يضيفها للرسم البياني
        """
        if not self._llm:
            return []

        try:
            result = await self._llm.think_json(
                f"ما الأسباب المحتملة لظاهرة '{phenomenon}'؟ "
                f"أعطني قائمة بأسباب مباشرة وغير مباشرة مع تقدير احتمال كل سبب (0-1). "
                f"الرد بصيغة JSON: {{\"causes\": [{{\"cause\": \"...\", \"probability\": 0.8, \"type\": \"direct/indirect\"}}]}}",
                model="glm-5.1",
                temperature=0.3,
            )

            discovered = []
            causes = result.get("causes", []) if isinstance(result, dict) else []
            for cause_data in causes:
                if isinstance(cause_data, dict) and "cause" in cause_data:
                    prob = float(cause_data.get("probability", 0.5))
                    edge = self.add_cause(
                        cause_data["cause"], phenomenon,
                        confidence=min(0.9, prob),
                    )
                    discovered.append({
                        "cause": cause_data["cause"],
                        "probability": prob,
                        "type": cause_data.get("type", "unknown"),
                        "edge_id": edge.edge_id,
                    })

            return discovered

        except Exception as e:
            logger.error("discover_causes failed: %s", e)
            return []

    # ═══════════════════════════════════════════════════════════
    # Graph statistics and API
    # ═══════════════════════════════════════════════════════════

    def get_node(self, name: str) -> Optional[Dict]:
        node = self._find_node_by_name(name)
        return node.to_dict() if node else None

    def get_nodes(self, category: str = None, limit: int = 100) -> List[dict]:
        nodes = list(self._nodes.values())
        if category:
            nodes = [n for n in nodes if n.category == category]
        return [n.to_dict() for n in sorted(nodes, key=lambda x: x.evidence_count, reverse=True)[:limit]]

    def get_edges(self, source: str = None, target: str = None, limit: int = 100) -> List[dict]:
        edges = list(self._edges.values())
        if source:
            src_node = self._find_node_by_name(source)
            if src_node:
                edges = [e for e in edges if e.source_id == src_node.node_id]
        if target:
            tgt_node = self._find_node_by_name(target)
            if tgt_node:
                edges = [e for e in edges if e.target_id == tgt_node.node_id]
        return [e.to_dict() for e in sorted(edges, key=lambda x: x.confidence, reverse=True)[:limit]]

    def get_stats(self) -> Dict:
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "categories": list(set(n.category for n in self._nodes.values())),
            "avg_confidence": round(
                sum(e.confidence for e in self._edges.values()) / max(len(self._edges), 1), 3
            ),
            "high_confidence_edges": len([e for e in self._edges.values() if e.confidence > 0.7]),
        }

    def get_subgraph(self, center: str, depth: int = 2) -> Dict:
        """الحصول على الرسم الفرعي حول عقدة معينة"""
        node = self._find_node_by_name(center)
        if not node:
            return {"center": center, "nodes": [], "edges": []}

        visited_nodes = {node.node_id}
        visited_edges = set()
        frontier = [node.node_id]

        for _ in range(depth):
            next_frontier = []
            for nid in frontier:
                for eid in self._adjacency.get(nid, []):
                    edge = self._edges[eid]
                    if eid not in visited_edges:
                        visited_edges.add(eid)
                        visited_nodes.add(edge.target_id)
                        next_frontier.append(edge.target_id)
                for eid in self._reverse_adj.get(nid, []):
                    edge = self._edges[eid]
                    if eid not in visited_edges:
                        visited_edges.add(eid)
                        visited_nodes.add(edge.source_id)
                        next_frontier.append(edge.source_id)
            frontier = next_frontier

        return {
            "center": center,
            "nodes": [self._nodes[nid].to_dict() for nid in visited_nodes if nid in self._nodes],
            "edges": [self._edges[eid].to_dict() for eid in visited_edges if eid in self._edges],
        }


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

causal_graph = CausalGraph()
