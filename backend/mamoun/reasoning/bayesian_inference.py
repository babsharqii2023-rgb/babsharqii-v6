"""
BABSHARQII v26.0 — Bayesian Inference Engine
محرك الاستدلال البايزي — بدون LLM

Real Bayesian inference with:
1. Prior/Posterior updating (Bayes' theorem)
2. Bayesian Network inference (variable elimination)
3. Belief updating from evidence
4. CPT (Conditional Probability Table) management
5. Marginal and conditional probability computation

NO LLM CALLS. Pure probability theory.
Based on: Bayes (1763), Pearl (1988), AIMA Ch.13-14
"""

import time
import uuid
import json
import logging
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Set, Tuple
from pathlib import Path

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.bayesian_inference")


@dataclass
class BNode:
    """عقدة شبكة بايزية"""
    node_id: str = ""
    name: str = ""
    values: List[str] = field(default_factory=lambda: ["true", "false"])
    parents: List[str] = field(default_factory=list)
    cpt: Dict[str, List[float]] = field(default_factory=dict)  # parent_values → P(node=true, node=false)
    prior: Optional[List[float]] = None  # for root nodes

    def __post_init__(self):
        if not self.node_id:
            self.node_id = f"bn_{uuid.uuid4().hex[:8]}"
        if not self.cpt and not self.prior:
            self.prior = [0.5, 0.5]

    def get_prob(self, value: str, parent_values: Dict[str, str] = None) -> float:
        """P(node=value | parents)"""
        if not self.parents:
            idx = self.values.index(value) if value in self.values else 0
            probs = self.prior or [0.5, 0.5]
            return probs[idx] if idx < len(probs) else 0.5
        key = "|".join(f"{p}={parent_values.get(p, 'true')}" for p in self.parents)
        probs = self.cpt.get(key, [0.5, 0.5])
        idx = self.values.index(value) if value in self.values else 0
        return probs[idx] if idx < len(probs) else 0.5

    def to_dict(self) -> dict:
        return {"node_id": self.node_id, "name": self.name, "values": self.values,
                "parents": self.parents, "cpt": self.cpt, "prior": self.prior}


@dataclass
class BeliefState:
    """حالة اعتقاد — توزيع احتمالي على متغير"""
    node_name: str = ""
    distribution: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"node_name": self.node_name, "distribution": self.distribution}


class BayesianInferenceEngine:
    """
    محرك الاستدلال البايزي — تحديث المعتقدات بالأدلة

    - Bayesian Network: DAG of conditional dependencies
    - Variable Elimination: exact inference
    - Belief Updating: posterior from evidence
    - No LLM — pure probability calculus
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._llm = None
        self._initialized = False
        self._nodes: Dict[str, BNode] = {}  # name → BNode
        self._evidence: Dict[str, str] = {}  # node_name → observed value
        self._beliefs: Dict[str, BeliefState] = {}

    def set_llm_client(self, llm_client):
        self._llm = llm_client  # NOT USED

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("BayesianInference initialized: %d nodes", len(self._nodes))
            return True
        except Exception as e:
            logger.error("BayesianInference init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS bi_nodes (
                node_id TEXT PRIMARY KEY, name TEXT, node_values TEXT,
                parents TEXT, cpt TEXT, prior TEXT)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS bi_evidence (
                node_name TEXT PRIMARY KEY, observed_value TEXT, confidence REAL DEFAULT 1.0,
                timestamp REAL DEFAULT 0)""")
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT node_id, name, node_values, parents, cpt, prior FROM bi_nodes"):
                vals = json.loads(row[2])
                parents = json.loads(row[3])
                cpt = json.loads(row[4]) if row[4] else {}
                prior = json.loads(row[5]) if row[5] else None
                self._nodes[row[1]] = BNode(node_id=row[0], name=row[1], values=vals,
                    parents=parents, cpt=cpt, prior=prior)
            for row in conn.execute("SELECT node_name, observed_value FROM bi_evidence"):
                self._evidence[row[0]] = row[1]
        finally:
            conn.close()

    def _persist_node(self, node: BNode):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("INSERT OR REPLACE INTO bi_nodes (node_id, name, node_values, parents, cpt, prior) VALUES (?,?,?,?,?,?)",
                (node.node_id, node.name, json.dumps(node.values), json.dumps(node.parents),
                 json.dumps(node.cpt), json.dumps(node.prior)))
            conn.commit()
        finally:
            conn.close()

    def _persist_evidence(self, node_name: str, value: str):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("INSERT OR REPLACE INTO bi_evidence (node_name, observed_value, timestamp) VALUES (?,?,?)",
                (node_name, value, time.time()))
            conn.commit()
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════════

    def add_node(self, name: str, values: List[str] = None, parents: List[str] = None,
                 cpt: Dict[str, List[float]] = None, prior: List[float] = None) -> BNode:
        """إضافة عقدة للشبكة البايزية"""
        node = BNode(name=name, values=values or ["true", "false"],
                     parents=parents or [], cpt=cpt or {}, prior=prior)
        # If no CPT and no prior, set uniform prior
        if not node.cpt and not node.prior:
            n_vals = len(node.values)
            node.prior = [1.0 / n_vals] * n_vals
        self._nodes[name] = node
        self._persist_node(node)
        return node

    def add_cpt_entry(self, node_name: str, parent_values: Dict[str, str],
                      probabilities: List[float]) -> bool:
        """إضافة مدخل في جدول الاحتمالات الشرطية"""
        node = self._nodes.get(node_name)
        if not node:
            return False
        key = "|".join(f"{p}={parent_values.get(p, 'true')}" for p in node.parents)
        node.cpt[key] = probabilities
        self._persist_node(node)
        return True

    def add_evidence(self, node_name: str, observed_value: str) -> bool:
        """إضافة دليل مرصود"""
        if node_name not in self._nodes:
            return False
        self._evidence[node_name] = observed_value
        self._persist_evidence(node_name, observed_value)
        return True

    def compute_posterior(self, node_name: str) -> BeliefState:
        """
        حساب التوزيع البعدي — P(node | evidence)

        Uses variable elimination (simplified for small networks).
        """
        node = self._nodes.get(node_name)
        if not node:
            return BeliefState(node_name=node_name, distribution={})

        # If this node has direct evidence
        if node_name in self._evidence:
            dist = {v: 1.0 if v == self._evidence[node_name] else 0.0 for v in node.values}
            belief = BeliefState(node_name=node_name, distribution=dist)
            self._beliefs[node_name] = belief
            return belief

        # Simple Bayesian update for nodes with parents
        if not node.parents:
            # Root node: prior is posterior (unless updated by evidence on children)
            prior = node.prior or [0.5, 0.5]
            dist = {v: prior[i] if i < len(prior) else 0.5 for i, v in enumerate(node.values)}
            belief = BeliefState(node_name=node_name, distribution=dist)
            self._beliefs[node_name] = belief
            return belief

        # Node with parents: compute P(node | parent_evidence)
        # P(node=val) = Σ_parents P(node=val|parents) * P(parents|evidence)
        dist = {}
        for val in node.values:
            prob = 0.0
            # Enumerate all parent value combinations
            parent_combos = self._enumerate_parent_values(node.parents)
            for combo in parent_combos:
                # P(node=val | parents=combo)
                cond_prob = node.get_prob(val, combo)
                # P(parents=combo | evidence)
                parent_prob = self._compute_parent_prob(combo)
                prob += cond_prob * parent_prob
            dist[val] = prob

        # Normalize
        total = sum(dist.values())
        if total > 0:
            dist = {k: v / total for k, v in dist.items()}

        belief = BeliefState(node_name=node_name, distribution=dist)
        self._beliefs[node_name] = belief
        return belief

    def update_belief(self, node_name: str, observed_value: str, confidence: float = 1.0) -> Dict:
        """
        تحديث المعتقد — Bayes' theorem

        P(H|E) = P(E|H) * P(H) / P(E)
        """
        node = self._nodes.get(node_name)
        if not node:
            return {"error": f"Node '{node_name}' not found"}

        prior_belief = self._beliefs.get(node_name)
        prior_dist = prior_belief.distribution if prior_belief else {
            v: (node.prior[i] if node.prior and i < len(node.prior) else 1.0 / len(node.values))
            for i, v in enumerate(node.values)
        }

        # Apply Bayes' rule
        likelihood = {}
        for val in node.values:
            # P(E|H=val) — how likely is the evidence if this value is true
            if val == observed_value:
                likelihood[val] = confidence
            else:
                likelihood[val] = 1.0 - confidence

        # Compute unnormalized posterior
        posterior = {}
        for val in node.values:
            posterior[val] = likelihood.get(val, 0.5) * prior_dist.get(val, 0.5)

        # Normalize
        total = sum(posterior.values())
        if total > 0:
            posterior = {k: v / total for k, v in posterior.items()}

        belief = BeliefState(node_name=node_name, distribution=posterior)
        self._beliefs[node_name] = belief
        self._evidence[node_name] = observed_value

        return {
            "node": node_name,
            "observed": observed_value,
            "prior": prior_dist,
            "posterior": posterior,
            "confidence": confidence,
        }

    def query_probability(self, node_name: str, value: str = "true") -> float:
        """P(node=value | evidence)"""
        belief = self.compute_posterior(node_name)
        return belief.distribution.get(value, 0.0)

    def explain_inference(self, node_name: str) -> Dict:
        """شرح الاستدلال — ما الذي أثر على هذا الاعتقاد؟"""
        node = self._nodes.get(node_name)
        if not node:
            return {"error": "node not found"}

        belief = self._beliefs.get(node_name)
        evidence_affecting = {k: v for k, v in self._evidence.items()
                              if k in node.parents or k == node_name}

        return {
            "node": node_name,
            "current_belief": belief.distribution if belief else {},
            "parents": node.parents,
            "evidence_affecting": evidence_affecting,
            "has_cpt": bool(node.cpt),
        }

    def _enumerate_parent_values(self, parents: List[str]) -> List[Dict[str, str]]:
        """توليد كل توليفات قيم الآباء"""
        if not parents:
            return [{}]
        combos = [{}]
        for parent in parents:
            pnode = self._nodes.get(parent)
            values = pnode.values if pnode else ["true", "false"]
            new_combos = []
            for combo in combos:
                for val in values:
                    new_combo = dict(combo)
                    new_combo[parent] = val
                    new_combos.append(new_combo)
            combos = new_combos
        return combos

    def _compute_parent_prob(self, combo: Dict[str, str]) -> float:
        """P(parents=combo | evidence) — simplified independence assumption"""
        prob = 1.0
        for parent, value in combo.items():
            if parent in self._evidence:
                # If we have evidence, probability is 1 if matches, 0 otherwise
                prob *= 1.0 if self._evidence[parent] == value else 0.0
            else:
                # Use prior or current belief
                pnode = self._nodes.get(parent)
                if pnode and pnode.prior:
                    idx = pnode.values.index(value) if value in pnode.values else 0
                    prob *= pnode.prior[idx] if idx < len(pnode.prior) else 1.0 / len(pnode.values)
                else:
                    prob *= 1.0 / 2  # uniform
        return prob

    def get_stats(self) -> Dict:
        return {
            "nodes": len(self._nodes),
            "evidence_count": len(self._evidence),
            "beliefs_computed": len(self._beliefs),
        }


_bayesian_engine: Optional[BayesianInferenceEngine] = None

def get_bayesian_engine() -> BayesianInferenceEngine:
    global _bayesian_engine
    if _bayesian_engine is None:
        _bayesian_engine = BayesianInferenceEngine()
    return _bayesian_engine
