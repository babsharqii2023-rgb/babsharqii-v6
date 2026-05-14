"""
BABSHARQII v26.0 — Symbolic Reasoning Engine
محرك الاستدلال المنطقي الرمزي — بدون LLM

Real symbolic AI: Propositional + First-Order Logic, Forward/Backward Chaining, Unification
"""

import time
import uuid
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Set, Tuple
from pathlib import Path
from enum import Enum

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.symbolic_reasoner")


class LogicOp(str, Enum):
    AND = "and"
    OR = "or"
    NOT = "not"
    IMPLIES = "implies"
    IFF = "iff"


@dataclass
class Term:
    """حد — متغير أو ثابت"""
    name: str
    is_variable: bool = False

    def __eq__(self, other):
        return isinstance(other, Term) and self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return f"?{self.name}" if self.is_variable else self.name


@dataclass
class Predicate:
    """محمول — علاقة بين حدود"""
    name: str
    args: List[Term] = field(default_factory=list)
    negated: bool = False
    _confidence: float = 1.0

    def __eq__(self, other):
        return (isinstance(other, Predicate) and self.name == other.name
                and self.args == other.args and self.negated == other.negated)

    def __hash__(self):
        return hash((self.name, tuple(a.name for a in self.args), self.negated))

    def __repr__(self):
        args_str = ", ".join(str(a) for a in self.args)
        prefix = "¬" if self.negated else ""
        return f"{prefix}{self.name}({args_str})"

    def negate(self) -> 'Predicate':
        return Predicate(name=self.name, args=list(self.args), negated=not self.negated)

    def substitute(self, bindings: Dict[str, Term]) -> 'Predicate':
        new_args = [bindings.get(a.name, a) if a.is_variable else a for a in self.args]
        return Predicate(name=self.name, args=new_args, negated=self.negated)

    def to_dict(self) -> dict:
        return {"name": self.name, "args": [{"name": a.name, "is_variable": a.is_variable} for a in self.args], "negated": self.negated}


@dataclass
class Rule:
    """قاعدة استدلال — IF premises THEN conclusion"""
    rule_id: str = ""
    name: str = ""
    premises: List[Predicate] = field(default_factory=list)
    conclusion: Predicate = field(default_factory=lambda: Predicate(name="true"))
    confidence: float = 1.0
    priority: int = 0
    created_at: float = 0.0

    def __post_init__(self):
        if not self.rule_id:
            self.rule_id = f"rule_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return {"rule_id": self.rule_id, "name": self.name,
                "premises": [p.to_dict() for p in self.premises],
                "conclusion": self.conclusion.to_dict(),
                "confidence": self.confidence}


@dataclass
class ProofResult:
    """نتيجة إثبات"""
    goal: str = ""
    proven: bool = False
    proof_chain: List[str] = field(default_factory=list)
    bindings: Dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0
    method: str = ""


class UnificationEngine:
    """محرك التوحيد"""

    @staticmethod
    def unify(p1: Predicate, p2: Predicate, bindings: Dict[str, Term] = None) -> Optional[Dict[str, Term]]:
        bindings = bindings or {}
        if p1.name != p2.name or len(p1.args) != len(p2.args):
            return None
        result = dict(bindings)
        for a1, a2 in zip(p1.args, p2.args):
            t1 = result.get(a1.name, a1) if a1.is_variable else a1
            t2 = result.get(a2.name, a2) if a2.is_variable else a2
            if t1.is_variable and t2.is_variable:
                if t1.name != t2.name:
                    result[t1.name] = t2
            elif t1.is_variable:
                result[t1.name] = t2
            elif t2.is_variable:
                result[t2.name] = t1
            elif t1.name != t2.name:
                return None
        return result


class SymbolicReasoner:
    """
    محرك الاستدلال الرمزي — استنتاج منطقي حقيقي بدون LLM

    - Knowledge Base: facts and rules in SQLite
    - Forward Chaining: derive all reachable facts
    - Backward Chaining: prove a specific goal
    - Unification: match variables across predicates
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._llm = None
        self._initialized = False
        self._facts: Set[Predicate] = set()
        self._rules: List[Rule] = []
        self._unification = UnificationEngine()
        self._proof_history: List[ProofResult] = []

    def set_llm_client(self, llm_client):
        self._llm = llm_client  # NOT USED

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("SymbolicReasoner initialized: %d facts, %d rules", len(self._facts), len(self._rules))
            return True
        except Exception as e:
            logger.error("SymbolicReasoner init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS sr_facts (
                fact_id TEXT PRIMARY KEY, predicate_name TEXT, args TEXT,
                negated INTEGER DEFAULT 0, confidence REAL DEFAULT 1.0,
                source TEXT DEFAULT '', created_at REAL DEFAULT 0)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS sr_rules (
                rule_id TEXT PRIMARY KEY, name TEXT, premises TEXT, conclusion TEXT,
                confidence REAL DEFAULT 1.0, priority INTEGER DEFAULT 0, created_at REAL DEFAULT 0)""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sr_facts_name ON sr_facts(predicate_name)")
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT predicate_name, args, negated, confidence FROM sr_facts"):
                args = [Term(name=a["name"], is_variable=a["is_variable"]) for a in json.loads(row[1])]
                p = Predicate(name=row[0], args=args, negated=bool(row[2]))
                p._confidence = row[3]
                self._facts.add(p)
            for row in conn.execute("SELECT rule_id, name, premises, conclusion, confidence, priority FROM sr_rules"):
                premises = [Predicate(name=p["name"],
                    args=[Term(name=a["name"], is_variable=a["is_variable"]) for a in p["args"]],
                    negated=p.get("negated", False)) for p in json.loads(row[2])]
                cd = json.loads(row[3])
                conclusion = Predicate(name=cd["name"],
                    args=[Term(name=a["name"], is_variable=a["is_variable"]) for a in cd["args"]],
                    negated=cd.get("negated", False))
                self._rules.append(Rule(rule_id=row[0], name=row[1], premises=premises,
                    conclusion=conclusion, confidence=row[4], priority=row[5]))
        finally:
            conn.close()

    def _persist_fact(self, pred: Predicate, source: str = ""):
        conn = get_db_connection(self.db_path)
        try:
            fact_id = f"fact_{abs(hash(pred)) & 0xFFFFFFFF:08x}"
            conn.execute("INSERT OR REPLACE INTO sr_facts (fact_id, predicate_name, args, negated, confidence, source, created_at) VALUES (?,?,?,?,?,?,?)",
                (fact_id, pred.name, json.dumps([{"name": a.name, "is_variable": a.is_variable} for a in pred.args]),
                 int(pred.negated), pred._confidence, source, time.time()))
            conn.commit()
        finally:
            conn.close()

    def _persist_rule(self, rule: Rule):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("INSERT OR REPLACE INTO sr_rules (rule_id, name, premises, conclusion, confidence, priority, created_at) VALUES (?,?,?,?,?,?,?)",
                (rule.rule_id, rule.name, json.dumps([p.to_dict() for p in rule.premises]),
                 json.dumps(rule.conclusion.to_dict()), rule.confidence, rule.priority, rule.created_at))
            conn.commit()
        finally:
            conn.close()

    def add_fact(self, predicate_name: str, args: List[str], negated: bool = False,
                 confidence: float = 1.0, source: str = "") -> Predicate:
        terms = [Term(name=a, is_variable=a.startswith("?")) for a in args]
        p = Predicate(name=predicate_name, args=terms, negated=negated)
        p._confidence = confidence
        self._facts.add(p)
        self._persist_fact(p, source)
        return p

    def add_rule(self, name: str, premises: List[Tuple[str, List[str]]],
                 conclusion: Tuple[str, List[str]], confidence: float = 1.0, priority: int = 0) -> Rule:
        premise_preds = [Predicate(name=p[0], args=[Term(name=a, is_variable=a.startswith("?")) for a in p[1]]) for p in premises]
        conc_pred = Predicate(name=conclusion[0], args=[Term(name=a, is_variable=a.startswith("?")) for a in conclusion[1]])
        rule = Rule(name=name, premises=premise_preds, conclusion=conc_pred, confidence=confidence, priority=priority)
        self._rules.append(rule)
        self._persist_rule(rule)
        return rule

    def forward_chain(self, max_iterations: int = 100) -> List[Predicate]:
        """التسلسل الأمامي — استنتاج كل الحقائق الممكنة"""
        new_facts = []
        derived = set()
        for iteration in range(max_iterations):
            iteration_new = 0
            for rule in sorted(self._rules, key=lambda r: -r.priority):
                bindings_list = self._find_matching_bindings(rule.premises)
                for bindings in bindings_list:
                    derived_conclusion = rule.conclusion.substitute(bindings)
                    if derived_conclusion not in self._facts and derived_conclusion not in derived:
                        derived.add(derived_conclusion)
                        self._facts.add(derived_conclusion)
                        derived_conclusion._confidence = rule.confidence
                        self._persist_fact(derived_conclusion, source=f"rule:{rule.name}")
                        new_facts.append(derived_conclusion)
                        iteration_new += 1
            if iteration_new == 0:
                break
        return new_facts

    def backward_chain(self, goal: Predicate, depth: int = 10) -> ProofResult:
        """التسلسل العكسي — إثبات هدف"""
        result = ProofResult(goal=str(goal), method="backward_chaining")
        # Check facts
        for fact in self._facts:
            if fact.name == goal.name and len(fact.args) == len(goal.args):
                bindings = self._unification.unify(fact, goal)
                if bindings is not None:
                    result.proven = True
                    result.proof_chain = [f"Fact: {fact}"]
                    result.bindings = {k: v.name for k, v in bindings.items()}
                    result.confidence = fact._confidence
                    return result
        if depth <= 0:
            return result
        # Try rules
        for rule in sorted(self._rules, key=lambda r: -r.priority):
            bindings = self._unification.unify(rule.conclusion, goal)
            if bindings is not None:
                all_proven = True
                sub_proofs = []
                combined_conf = rule.confidence
                for premise in rule.premises:
                    bound_premise = premise.substitute(bindings)
                    sub_result = self.backward_chain(bound_premise, depth - 1)
                    if not sub_result.proven:
                        all_proven = False
                        break
                    sub_proofs.append(sub_result)
                    combined_conf *= sub_result.confidence
                if all_proven:
                    result.proven = True
                    result.confidence = combined_conf
                    result.bindings = {k: v.name for k, v in bindings.items()}
                    result.proof_chain = [f"Rule: {rule.name}"] + [s for sp in sub_proofs for s in sp.proof_chain]
                    return result
        return result

    def prove(self, predicate_name: str, args: List[str]) -> ProofResult:
        """إثبات — محاولة بالتسلسل العكسي ثم الأمامي"""
        goal = Predicate(name=predicate_name, args=[Term(name=a, is_variable=a.startswith("?")) for a in args])
        result = self.backward_chain(goal)
        if not result.proven:
            self.forward_chain()
            result = self.backward_chain(goal)
        self._proof_history.append(result)
        return result

    def query(self, predicate_name: str, args: List[str] = None) -> List[Dict]:
        """استعلام عن حقائق مطابقة"""
        results = []
        for fact in self._facts:
            if fact.name == predicate_name:
                if args:
                    match = True
                    for i, a in enumerate(args):
                        if i < len(fact.args) and not fact.args[i].is_variable:
                            if fact.args[i].name != a and not a.startswith("?"):
                                match = False
                                break
                    if not match:
                        continue
                results.append({"predicate": str(fact), "args": [a.name for a in fact.args],
                    "negated": fact.negated, "confidence": fact._confidence})
        return results

    def _find_matching_bindings(self, premises: List[Predicate]) -> List[Dict[str, Term]]:
        if not premises:
            return [{}]
        first = premises[0]
        rest = premises[1:]
        results = []
        for fact in self._facts:
            bindings = self._unification.unify(first, fact)
            if bindings is not None:
                if rest:
                    remaining = [p.substitute(bindings) for p in rest]
                    sub_bindings = self._find_matching_bindings(remaining)
                    for sb in sub_bindings:
                        combined = dict(bindings)
                        combined.update(sb)
                        results.append(combined)
                else:
                    results.append(bindings)
        return results

    def get_stats(self) -> Dict:
        return {"facts": len(self._facts), "rules": len(self._rules),
                "proofs_attempted": len(self._proof_history),
                "proofs_successful": sum(1 for p in self._proof_history if p.proven)}


_symbolic_reasoner: Optional[SymbolicReasoner] = None

def get_symbolic_reasoner() -> SymbolicReasoner:
    global _symbolic_reasoner
    if _symbolic_reasoner is None:
        _symbolic_reasoner = SymbolicReasoner()
    return _symbolic_reasoner
