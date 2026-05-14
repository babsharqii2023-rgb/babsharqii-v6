"""
BABSHARQII v26.0 — Abstract Generalization Engine
محرك التعميم التجريدي — بدون LLM

Real abstract generalization:
1. Pattern extraction from examples
2. Variable identification (what changes vs what stays)
3. Rule abstraction (from specific to general)
4. Similarity-based generalization
5. Category formation from exemplars
6. Analogical mapping between domains

NO LLM CALLS. Pure symbolic + statistical generalization.
Based on: Gentner's Structure-Mapping Theory (1983), Gick & Holyoak (1983)
"""

import time
import uuid
import json
import logging
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
from collections import Counter

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.abstract_generalization")


@dataclass
class Pattern:
    """نمط — هيكل مجرد يستخلص من أمثلة"""
    pattern_id: str = ""
    name: str = ""
    structure: List[Dict] = field(default_factory=list)  # list of {role, value, is_variable}
    source_examples: List[str] = field(default_factory=list)
    confidence: float = 0.0
    generality: float = 0.0  # how many examples it covers
    created_at: float = 0.0

    def __post_init__(self):
        if not self.pattern_id:
            self.pattern_id = f"pat_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Category:
    """فئة — مجموعة من الأشياء المتشابهة"""
    category_id: str = ""
    name: str = ""
    members: List[str] = field(default_factory=list)
    prototype: Dict[str, float] = field(default_factory=dict)  # feature → typical value
    boundaries: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # feature → (min, max)
    created_at: float = 0.0

    def __post_init__(self):
        if not self.category_id:
            self.category_id = f"cat_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()


class AbstractGeneralizationEngine:
    """
    محرك التعميم التجريدي — تعميم حقيقي بدون LLM

    - Pattern extraction: find what's common across examples
    - Variable detection: identify what changes vs stays
    - Category formation: group similar items
    - Analogical mapping: find structural correspondences
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._llm = None
        self._initialized = False
        self._patterns: Dict[str, Pattern] = {}
        self._categories: Dict[str, Category] = {}
        self._examples: Dict[str, List[Dict]] = {}  # pattern_name → examples

    def set_llm_client(self, llm_client):
        self._llm = llm_client  # NOT USED

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("AbstractGeneralization initialized: %d patterns, %d categories",
                        len(self._patterns), len(self._categories))
            return True
        except Exception as e:
            logger.error("AbstractGeneralization init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS ag_patterns (
                pattern_id TEXT PRIMARY KEY, name TEXT, structure TEXT,
                source_examples TEXT, confidence REAL, generality REAL, created_at REAL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS ag_categories (
                category_id TEXT PRIMARY KEY, name TEXT, members TEXT,
                prototype TEXT, boundaries TEXT, created_at REAL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS ag_examples (
                example_id TEXT PRIMARY KEY, pattern_name TEXT, features TEXT, timestamp REAL)""")
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT pattern_id, name, structure, source_examples, confidence, generality FROM ag_patterns"):
                self._patterns[row[1]] = Pattern(pattern_id=row[0], name=row[1],
                    structure=json.loads(row[2]), source_examples=json.loads(row[3]),
                    confidence=row[4], generality=row[5])
            for row in conn.execute("SELECT category_id, name, members, prototype, boundaries FROM ag_categories"):
                self._categories[row[1]] = Category(category_id=row[0], name=row[1],
                    members=json.loads(row[2]), prototype=json.loads(row[3]),
                    boundaries={k: tuple(v) for k, v in json.loads(row[4]).items()})
        finally:
            conn.close()

    def _persist_pattern(self, pattern: Pattern):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("INSERT OR REPLACE INTO ag_patterns VALUES (?,?,?,?,?,?,?)",
                (pattern.pattern_id, pattern.name, json.dumps(pattern.structure),
                 json.dumps(pattern.source_examples), pattern.confidence,
                 pattern.generality, pattern.created_at))
            conn.commit()
        finally:
            conn.close()

    def _persist_category(self, cat: Category):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("INSERT OR REPLACE INTO ag_categories VALUES (?,?,?,?,?,?)",
                (cat.category_id, cat.name, json.dumps(cat.members),
                 json.dumps(cat.prototype), json.dumps({k: list(v) for k, v in cat.boundaries.items()}),
                 cat.created_at))
            conn.commit()
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════════

    def add_example(self, pattern_name: str, features: Dict[str, Any]) -> Pattern:
        """إضافة مثال واستخلاص النمط المجرد"""
        self._examples.setdefault(pattern_name, []).append(features)

        # Try to extract pattern when we have 2+ examples
        examples = self._examples[pattern_name]
        if len(examples) >= 2:
            pattern = self._extract_pattern(pattern_name, examples)
            self._patterns[pattern_name] = pattern
            self._persist_pattern(pattern)
            return pattern

        return Pattern(name=pattern_name, source_examples=[str(features)[:200]],
                       confidence=0.3, generality=0.0)

    def _extract_pattern(self, name: str, examples: List[Dict]) -> Pattern:
        """استخلاص النمط — ما الذي ثابت وما الذي متغير؟"""
        structure = []

        if not examples:
            return Pattern(name=name, confidence=0.0, generality=0.0)

        # Get all keys across all examples
        all_keys = set()
        for ex in examples:
            all_keys.update(ex.keys())

        for key in sorted(all_keys):
            values = [ex.get(key) for ex in examples if key in ex]
            if not values:
                continue

            # Check if value is constant across examples
            unique_values = set(str(v) for v in values)
            if len(unique_values) == 1:
                # Constant — stays as-is
                structure.append({"role": key, "value": values[0], "is_variable": False})
            else:
                # Variable — abstracted
                # Try to find common type
                if all(isinstance(v, (int, float)) for v in values):
                    mean_val = np.mean(values)
                    std_val = np.std(values)
                    structure.append({"role": key, "value": f"~N({mean_val:.2f},{std_val:.2f})", "is_variable": True})
                else:
                    structure.append({"role": key, "value": f"?{key}", "is_variable": True})

        # Calculate confidence based on how many features are stable
        n_constant = sum(1 for s in structure if not s["is_variable"])
        confidence = n_constant / max(len(structure), 1)

        return Pattern(name=name, structure=structure,
                       source_examples=[str(ex)[:100] for ex in examples[:5]],
                       confidence=confidence, generality=len(examples) / 10.0)

    def generalize(self, examples: List[Dict[str, Any]], name: str = "") -> Pattern:
        """تعميم — استخلاص القاعدة العامة من أمثلة"""
        name = name or f"gen_{uuid.uuid4().hex[:6]}"
        for ex in examples:
            self._examples.setdefault(name, []).append(ex)
        pattern = self._extract_pattern(name, self._examples[name])
        self._patterns[name] = pattern
        self._persist_pattern(pattern)
        return pattern

    def form_category(self, name: str, items: List[Dict[str, float]]) -> Category:
        """تكوين فئة — تجميع متشابهات"""
        if not items:
            return Category(name=name)

        # Compute prototype (centroid)
        all_keys = set()
        for item in items:
            all_keys.update(item.keys())

        prototype = {}
        boundaries = {}
        for key in sorted(all_keys):
            values = [item.get(key, 0.0) for item in items]
            prototype[key] = float(np.mean(values))
            boundaries[key] = (float(min(values)), float(max(values)))

        cat = Category(name=name, members=[str(i)[:50] for i in items[:20]],
                       prototype=prototype, boundaries=boundaries)
        self._categories[name] = cat
        self._persist_category(cat)
        return cat

    def classify(self, item: Dict[str, float]) -> List[Dict]:
        """تصنيف — أي فئة ينتمي إليها هذا العنصر؟"""
        results = []
        for name, cat in self._categories.items():
            if not cat.prototype:
                continue
            # Compute distance to prototype
            distance = 0.0
            n_features = 0
            for key, proto_val in cat.prototype.items():
                item_val = item.get(key, proto_val)
                # Normalize by range
                min_val, max_val = cat.boundaries.get(key, (0.0, 1.0))
                rng = max_val - min_val if max_val != min_val else 1.0
                distance += abs(item_val - proto_val) / rng
                n_features += 1
            if n_features > 0:
                distance /= n_features
            similarity = max(0.0, 1.0 - distance)
            results.append({"category": name, "similarity": round(similarity, 4), "distance": round(distance, 4)})

        return sorted(results, key=lambda x: -x["similarity"])

    def find_analogy(self, source: Dict, candidates: List[Dict]) -> List[Dict]:
        """إيجاد تشابه بنيوي — أي المرشحين يشبه المصدر؟"""
        results = []
        source_keys = set(source.keys())
        for i, cand in enumerate(candidates):
            cand_keys = set(cand.keys())
            # Structural overlap
            overlap = source_keys & cand_keys
            if not overlap:
                continue
            # Value similarity on overlapping keys
            value_sim = 0.0
            for key in overlap:
                sv = source[key]
                cv = cand[key]
                if isinstance(sv, (int, float)) and isinstance(cv, (int, float)):
                    max_val = max(abs(sv), abs(cv), 1.0)
                    value_sim += 1.0 - abs(sv - cv) / max_val
                elif str(sv) == str(cv):
                    value_sim += 1.0
            value_sim /= max(len(overlap), 1)
            structural_sim = len(overlap) / max(len(source_keys | cand_keys), 1)
            combined = 0.5 * structural_sim + 0.5 * value_sim
            results.append({"candidate_index": i, "structural_similarity": round(structural_sim, 4),
                            "value_similarity": round(value_sim, 4), "combined": round(combined, 4)})
        return sorted(results, key=lambda x: -x["combined"])

    def get_stats(self) -> Dict:
        return {"patterns": len(self._patterns), "categories": len(self._categories),
                "total_examples": sum(len(v) for v in self._examples.values())}


_abstract_generalization: Optional[AbstractGeneralizationEngine] = None

def get_abstract_generalization() -> AbstractGeneralizationEngine:
    global _abstract_generalization
    if _abstract_generalization is None:
        _abstract_generalization = AbstractGeneralizationEngine()
    return _abstract_generalization
