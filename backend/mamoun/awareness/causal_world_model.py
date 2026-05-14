"""
BABSHARQII v25.0 — Causal World Model (No LLM)
النموذج السببي العالمي — بدون LLM

Builds a comprehensive causal model of the world using PURE algorithms:
1. PC Algorithm: Causal structure discovery from observational data
2. Conditional Independence Tests: Determine if X ⊥ Y | Z
3. V-Structure Detection: Find colliders (X → Z ← Y)
4. do-Calculus: Compute interventional distributions WITHOUT LLM
5. Counterfactual Reasoning: From structural equations
6. Bayesian Network Inference: Probabilistic reasoning over the causal graph
7. Intervention Propagation: Forward-simulate interventions through the DAG

NO LLM CALLS. Pure mathematical causal reasoning.

Based on:
- Pearl's do-calculus (2009)
- PC algorithm (Spirtes, Glymour, Scheines, 2000)
- Bayesian Network inference (message passing)
"""

import time
import uuid
import json
import logging
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Set, Tuple
from pathlib import Path
from enum import Enum
from collections import defaultdict

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.causal_world_model")


# ═══════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════

class CausalRelation(str, Enum):
    CAUSES = "causes"           # A → B (direct cause)
    PREVENTS = "prevents"       # A → ¬B (inhibitor)
    ENABLES = "enables"         # A is prerequisite for B
    MEDIATES = "mediates"       # A mediates C → B


@dataclass
class CausalVariable:
    """متغير سببي — يمكن ملاحظته أو التدخل فيه"""
    var_id: str = ""
    name: str = ""
    var_type: str = "continuous"   # continuous, binary, categorical
    categories: List[str] = field(default_factory=list)
    observed_values: List[float] = field(default_factory=list)
    mean: float = 0.0
    std: float = 1.0
    description: str = ""
    created_at: float = 0.0

    def __post_init__(self):
        if not self.var_id:
            self.var_id = f"var_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def add_observation(self, value: float):
        """إضافة ملاحظة وتحديث الإحصائيات"""
        self.observed_values.append(value)
        n = len(self.observed_values)
        self.mean = self.mean * (n - 1) / n + value / n
        if n > 1:
            self.std = np.std(self.observed_values)

    def to_dict(self) -> dict:
        return {
            "var_id": self.var_id, "name": self.name, "var_type": self.var_type,
            "mean": self.mean, "std": self.std, "n_observations": len(self.observed_values),
            "description": self.description,
        }


@dataclass
class StructuralEquation:
    """
    معادلة هيكلية — y = f(parents) + noise
    
    For continuous: y = Σ β_i * x_i + ε
    For binary: P(y=1) = σ(Σ β_i * x_i)
    """
    equation_id: str = ""
    target_var: str = ""
    parent_vars: List[str] = field(default_factory=list)
    coefficients: Dict[str, float] = field(default_factory=dict)  # parent → β
    intercept: float = 0.0
    noise_std: float = 0.1
    relation_type: str = CausalRelation.CAUSES.value
    r_squared: float = 0.0  # fit quality
    n_observations: int = 0

    def __post_init__(self):
        if not self.equation_id:
            self.equation_id = f"eq_{uuid.uuid4().hex[:8]}"

    def predict(self, parent_values: Dict[str, float]) -> float:
        """التنبؤ بالقيمة بناءً على قيم الآباء"""
        result = self.intercept
        for parent, beta in self.coefficients.items():
            result += beta * parent_values.get(parent, 0.0)
        return result

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════
# PC Algorithm — Causal Structure Discovery (No LLM)
# ═══════════════════════════════════════════════════════════════

class PCDiscovery:
    """
    خوارزمية PC — اكتشاف البنية السببية من البيانات
    
    Step 1: Start with complete undirected graph
    Step 2: Remove edges where X ⊥ Y (unconditional independence)
    Step 3: Remove edges where X ⊥ Y | Z (conditional independence)
    Step 4: Orient V-structures: X - Z - Y → X → Z ← Y
    Step 5: Apply orientation rules (Meek's rules)
    
    Uses partial correlation for conditional independence tests.
    NO LLM CALLS.
    """

    @staticmethod
    def partial_correlation(data: np.ndarray, i: int, j: int,
                            conditioning: List[int] = None) -> float:
        """
        حساب الارتباط الجزئي ρ(X_i, X_j | Z)
        
        If |ρ| < threshold → X_i ⊥ X_j | Z (conditionally independent)
        """
        if conditioning is None or len(conditioning) == 0:
            # Simple correlation
            if data.shape[0] < 2:
                return 0.0
            return float(np.corrcoef(data[:, i], data[:, j])[0, 1])

        # Partial correlation using precision matrix
        # Select relevant columns
        indices = [i, j] + list(conditioning)
        sub = data[:, indices]
        
        try:
            cov = np.cov(sub, rowvar=False)
            if cov.shape[0] < 2:
                return 0.0
            precision = np.linalg.pinv(cov)
            # Partial correlation from precision matrix
            rho = -precision[0, 1] / np.sqrt(precision[0, 0] * precision[1, 1])
            return float(np.clip(rho, -1, 1))
        except (np.linalg.LinAlgError, ValueError):
            return 0.0

    @staticmethod
    def independence_test(data: np.ndarray, i: int, j: int,
                          conditioning: List[int] = None,
                          alpha: float = 0.05) -> bool:
        """
        اختبار الاستقلال: هل X_i ⊥ X_j | Z؟
        
        Returns True if independent (should remove edge)
        Uses Fisher z-transform for significance testing
        """
        n = data.shape[0]
        if n < 5:
            return True  # Not enough data, assume independent

        rho = PCDiscovery.partial_correlation(data, i, j, conditioning)
        
        # Handle NaN or perfect correlation
        if np.isnan(rho) or np.isinf(rho):
            return False  # Can't determine → assume dependent

        # Fisher z-transform
        if abs(rho) >= 0.999:
            return False  # Perfect correlation → dependent

        z = 0.5 * np.log((1 + rho) / (1 - rho + 1e-10))
        cond_size = len(conditioning) if conditioning else 0
        z_stat = abs(z) * np.sqrt(max(n - cond_size - 3, 1))

        # Two-sided test at alpha
        try:
            from scipy import stats
            p_value = 2 * (1 - stats.norm.cdf(z_stat))
            return p_value > alpha
        except Exception:
            # Fallback: simple threshold
            return abs(rho) < 0.1

    @staticmethod
    def discover(data: np.ndarray, variable_names: List[str],
                 alpha: float = 0.05, max_cond_size: int = 3) -> Dict:
        """
        اكتشاف البنية السببية من البيانات
        
        Args:
            data: (n_samples, n_variables) observation matrix
            variable_names: names for each variable
            alpha: significance level for independence tests
            max_cond_size: maximum conditioning set size
            
        Returns:
            Dictionary with edges and orientations
        """
        n_vars = data.shape[1]
        
        # Step 1: Start with complete undirected graph
        adj = np.ones((n_vars, n_vars), dtype=bool)
        np.fill_diagonal(adj, False)
        
        # Separation sets
        sep_sets: Dict[Tuple[int, int], Set[int]] = defaultdict(set)

        # Step 2-3: Remove edges based on independence tests
        for cond_size in range(max_cond_size + 1):
            for i in range(n_vars):
                for j in range(i + 1, n_vars):
                    if not adj[i, j]:
                        continue

                    # Try all conditioning sets of size cond_size
                    neighbors_i = [k for k in range(n_vars)
                                  if adj[i, k] and k != j]
                    
                    if len(neighbors_i) < cond_size:
                        continue

                    # Test independence
                    from itertools import combinations
                    found_independent = False
                    for cond_set in combinations(neighbors_i, cond_size):
                        if PCDiscovery.independence_test(data, i, j, list(cond_set), alpha):
                            adj[i, j] = False
                            adj[j, i] = False
                            sep_sets[(i, j)] = set(cond_set)
                            sep_sets[(j, i)] = set(cond_set)
                            found_independent = True
                            break

        # Step 4: Orient V-structures
        # X → Z ← Y if X-Z, Y-Z, and X not connected to Y
        orientations: Dict[Tuple[int, int], str] = {}  # (i,j) → "i→j"
        
        for z in range(n_vars):
            neighbors_z = [k for k in range(n_vars) if adj[z, k]]
            for idx_a in range(len(neighbors_z)):
                for idx_b in range(idx_a + 1, len(neighbors_z)):
                    a = neighbors_z[idx_a]
                    b = neighbors_z[idx_b]
                    # If a and b are NOT connected → V-structure
                    if not adj[a, b]:
                        # a → z ← b (collider at z)
                        if z not in sep_sets.get((a, b), set()):
                            orientations[(a, z)] = "a→z"
                            orientations[(b, z)] = "b→z"

        # Step 5: Meek's orientation rules
        # (simplified version)
        changed = True
        while changed:
            changed = False
            for i in range(n_vars):
                for j in range(n_vars):
                    if not adj[i, j]:
                        continue
                    # Rule 1: If k→i-j and k not adj j, then i→j
                    for k in range(n_vars):
                        if orientations.get((k, i)) == "k→i" and not adj[k, j]:
                            if (i, j) not in orientations and (j, i) not in orientations:
                                orientations[(i, j)] = "i→j"
                                changed = True
                    # Rule 2: If i→k→j and i-j, then i→j
                    for k in range(n_vars):
                        if (orientations.get((i, k)) == "i→k" and
                            orientations.get((k, j)) == "k→j"):
                            if (i, j) not in orientations and (j, i) not in orientations:
                                orientations[(i, j)] = "i→j"
                                changed = True

        # Build result
        edges = []
        for i in range(n_vars):
            for j in range(i + 1, n_vars):
                if adj[i, j]:
                    if orientations.get((i, j)) == "i→j":
                        edges.append({
                            "source": variable_names[i],
                            "target": variable_names[j],
                            "direction": "i→j",
                            "type": "causes",
                        })
                    elif orientations.get((j, i)) == "j→i":
                        edges.append({
                            "source": variable_names[j],
                            "target": variable_names[i],
                            "direction": "j→i",
                            "type": "causes",
                        })
                    else:
                        edges.append({
                            "source": variable_names[i],
                            "target": variable_names[j],
                            "direction": "undirected",
                            "type": "associated",
                        })

        return {
            "variables": variable_names,
            "edges": edges,
            "n_samples": data.shape[0],
            "alpha": alpha,
            "v_structures": len([e for e in edges if e["direction"] != "undirected"]),
            "undirected": len([e for e in edges if e["direction"] == "undirected"]),
        }


# ═══════════════════════════════════════════════════════════════
# Causal World Model — Full Engine (No LLM)
# ═══════════════════════════════════════════════════════════════

class CausalWorldModel:
    """
    النموذج السببي العالمي — بدون LLM
    
    يبني نموذجاً سببياً شاملاً للعالم باستخدام:
    - خوارزمية PC لاكتشاف البنية السببية
    - المعادلات الهيكلية للتنبؤ
    - do-calculus رياضي (بدون LLM)
    - الاستدلال البايزي عبر الشبكة
    
    Usage:
        model = CausalWorldModel()
        model.initialize()
        
        # Add observations
        model.add_observation({"rain": 1, "sprinkler": 0, "wet_ground": 1, "slippery": 1})
        model.add_observation({"rain": 0, "sprinkler": 1, "wet_ground": 1, "slippery": 0})
        
        # Discover causal structure
        structure = model.discover_structure()
        # → rain → wet_ground, sprinkler → wet_ground, wet_ground → slippery
        
        # do-calculus: P(slippery | do(rain=1))
        result = model.do_intervention("rain", 1.0)
        # → {wet_ground: 0.9, slippery: 0.6}
        
        # Counterfactual: would it be slippery if it hadn't rained?
        cf = model.counterfactual({"slippery": 1}, {"rain": 0})
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._variables: Dict[str, CausalVariable] = {}
        self._equations: Dict[str, StructuralEquation] = {}  # target_var → equation
        self._edges: List[Dict] = []  # discovered causal edges
        self._observations: List[Dict[str, float]] = []
        self._data_matrix: Optional[np.ndarray] = None
        self._var_order: List[str] = []  # variable name → column index
        self._llm = None  # NOT USED — pure mathematical reasoning
        self._initialized = False

    def set_llm_client(self, llm_client):
        """LLM not used — causal reasoning is purely mathematical"""
        self._llm = None  # Explicitly ignore LLM

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("CausalWorldModel initialized — %d variables, %d equations",
                       len(self._variables), len(self._equations))
            return True
        except Exception as e:
            logger.error("CausalWorldModel init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cwm_variables (
                    var_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    var_type TEXT DEFAULT 'continuous',
                    mean REAL DEFAULT 0,
                    std REAL DEFAULT 1,
                    n_observations INTEGER DEFAULT 0,
                    description TEXT DEFAULT '',
                    created_at REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cwm_equations (
                    equation_id TEXT PRIMARY KEY,
                    target_var TEXT NOT NULL,
                    parent_vars TEXT DEFAULT '[]',
                    coefficients TEXT DEFAULT '{}',
                    intercept REAL DEFAULT 0,
                    noise_std REAL DEFAULT 0.1,
                    relation_type TEXT DEFAULT 'causes',
                    r_squared REAL DEFAULT 0,
                    n_observations INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cwm_observations (
                    obs_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT NOT NULL,
                    timestamp REAL DEFAULT 0
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT * FROM cwm_variables"):
                var = CausalVariable(
                    var_id=row[0], name=row[1], var_type=row[2],
                    mean=row[3], std=row[4], description=row[6],
                    created_at=row[7],
                )
                var.observed_values = []  # Don't load all observations into memory
                self._variables[var.name] = var
                self._var_order.append(var.name)

            for row in conn.execute("SELECT * FROM cwm_equations"):
                eq = StructuralEquation(
                    equation_id=row[0], target_var=row[1],
                    parent_vars=json.loads(row[2]),
                    coefficients=json.loads(row[3]),
                    intercept=row[4], noise_std=row[5],
                    relation_type=row[6], r_squared=row[7],
                    n_observations=row[8],
                )
                self._equations[eq.target_var] = eq
        finally:
            conn.close()

    def _persist_variable(self, var: CausalVariable):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO cwm_variables
                (var_id, name, var_type, mean, std, n_observations, description, created_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (var.var_id, var.name, var.var_type, var.mean, var.std,
                  len(var.observed_values), var.description, var.created_at))
            conn.commit()
        finally:
            conn.close()

    def _persist_equation(self, eq: StructuralEquation):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO cwm_equations
                (equation_id, target_var, parent_vars, coefficients, intercept,
                 noise_std, relation_type, r_squared, n_observations)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (eq.equation_id, eq.target_var, json.dumps(eq.parent_vars),
                  json.dumps(eq.coefficients), eq.intercept, eq.noise_std,
                  eq.relation_type, eq.r_squared, eq.n_observations))
            conn.commit()
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════
    # Core API
    # ═══════════════════════════════════════════════════════════

    def add_variable(self, name: str, var_type: str = "continuous",
                     description: str = "") -> CausalVariable:
        """إضافة متغير سببي"""
        if name in self._variables:
            return self._variables[name]

        var = CausalVariable(name=name, var_type=var_type, description=description)
        self._variables[name] = var
        self._var_order.append(name)
        self._persist_variable(var)
        return var

    def add_observation(self, data: Dict[str, float]):
        """إضافة ملاحظة — تحديث الإحصائيات"""
        # Ensure all variables exist
        for name, value in data.items():
            if name not in self._variables:
                self.add_variable(name)
            self._variables[name].add_observation(value)

        self._observations.append(data)

        # Update data matrix
        self._rebuild_data_matrix()

        # Persist observation
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT INTO cwm_observations (data, timestamp)
                VALUES (?,?)
            """, (json.dumps(data), time.time()))
            conn.commit()
        finally:
            conn.close()

        # Update variable stats
        for name in data:
            self._persist_variable(self._variables[name])

    def add_observations_batch(self, observations: List[Dict[str, float]]):
        """إضافة مجموعة ملاحظات دفعة واحدة"""
        for obs in observations:
            self.add_observation(obs)

    def _rebuild_data_matrix(self):
        """إعادة بناء مصفوفة البيانات"""
        if not self._observations or not self._var_order:
            return

        n = len(self._observations)
        m = len(self._var_order)
        self._data_matrix = np.zeros((n, m))

        for i, obs in enumerate(self._observations):
            for j, var_name in enumerate(self._var_order):
                self._data_matrix[i, j] = obs.get(var_name, 0.0)

    def discover_structure(self, alpha: float = 0.05,
                           max_cond_size: int = 3) -> Dict:
        """
        اكتشاف البنية السببية من البيانات المرصودة — بدون LLM
        
        Uses PC algorithm:
        1. Start with complete graph
        2. Remove independent edges
        3. Orient V-structures
        4. Apply Meek's rules
        """
        if self._data_matrix is None or self._data_matrix.shape[0] < 5:
            return {"error": "Need at least 5 observations for structure discovery"}

        result = PCDiscovery.discover(
            self._data_matrix, self._var_order,
            alpha=alpha, max_cond_size=max_cond_size
        )
        self._edges = result["edges"]

        # Build structural equations from discovered edges
        self._build_equations()

        return result

    def _build_equations(self):
        """بناء المعادلات الهيكلية من الحواف المكتشفة"""
        # Group edges by target (use both directed and undirected)
        target_parents: Dict[str, List[str]] = defaultdict(list)
        for edge in self._edges:
            if edge["direction"] != "undirected":
                target_parents[edge["target"]].append(edge["source"])
            else:
                # For undirected edges, treat both as potential targets
                # Use correlation strength to decide direction (higher mean → source)
                src = edge["source"]
                tgt = edge["target"]
                src_var = self._variables.get(src)
                tgt_var = self._variables.get(tgt)
                if src_var and tgt_var:
                    # Heuristic: variable with lower mean is more likely cause
                    if abs(src_var.mean) <= abs(tgt_var.mean):
                        target_parents[tgt].append(src)
                    else:
                        target_parents[src].append(tgt)
                else:
                    target_parents[tgt].append(src)

        # Fit linear structural equations
        if self._data_matrix is None:
            return

        for target, parents in target_parents.items():
            if target not in self._var_order:
                continue

            tgt_idx = self._var_order.index(target)
            parent_indices = [self._var_order.index(p) for p in parents if p in self._var_order]

            if not parent_indices:
                continue

            # OLS regression: Y = X @ β + ε
            Y = self._data_matrix[:, tgt_idx]
            X = self._data_matrix[:, parent_indices]
            # Add intercept
            X_with_intercept = np.column_stack([np.ones(len(Y)), X])

            try:
                # Solve normal equations
                beta = np.linalg.lstsq(X_with_intercept, Y, rcond=None)[0]
                
                coefficients = {}
                for i, parent in enumerate(parents):
                    if i + 1 < len(beta):
                        coefficients[parent] = float(beta[i + 1])

                # Compute R²
                Y_pred = X_with_intercept @ beta
                ss_res = np.sum((Y - Y_pred) ** 2)
                ss_tot = np.sum((Y - np.mean(Y)) ** 2)
                r_squared = 1 - ss_res / (ss_tot + 1e-10)

                eq = StructuralEquation(
                    target_var=target,
                    parent_vars=parents,
                    coefficients=coefficients,
                    intercept=float(beta[0]),
                    noise_std=float(np.std(Y - Y_pred)),
                    r_squared=float(r_squared),
                    n_observations=self._data_matrix.shape[0],
                )
                self._equations[target] = eq
                self._persist_equation(eq)

            except np.linalg.LinAlgError:
                pass

    def do_intervention(self, variable: str, value: float) -> Dict[str, float]:
        """
        do-calculus رياضي — بدون LLM
        
        P(Y | do(X = v)):
        1. Set X = v (remove incoming edges to X)
        2. Propagate through structural equations
        3. Return predicted values for all descendants
        """
        if variable not in self._variables:
            return {variable: value}

        # Build current state
        state: Dict[str, float] = {name: var.mean for name, var in self._variables.items()}
        state[variable] = value  # do(X = v)

        # Topological propagation
        # Process variables in topological order (roots first)
        processed = set()
        max_iterations = len(self._equations) + 1

        for _ in range(max_iterations):
            changed = False
            for target, eq in self._equations.items():
                if target == variable:
                    continue  # Don't modify intervened variable
                if target in processed:
                    continue

                # Check if all parents have been computed
                parent_vals = {}
                all_parents_ready = True
                for parent in eq.parent_vars:
                    if parent in state:
                        parent_vals[parent] = state[parent]
                    else:
                        all_parents_ready = False
                        break

                if all_parents_ready:
                    predicted = eq.predict(parent_vals)
                    # Add noise (deterministic for now)
                    state[target] = predicted
                    processed.add(target)
                    changed = True

            if not changed:
                break

        return state

    def counterfactual(self, observed: Dict[str, float],
                       intervention: Dict[str, float]) -> Dict[str, float]:
        """
        استدلال مضاد للواقع — بدون LLM
        
        Given we observed O, what would have happened if I were true?
        
        Steps (Pearl's 3-step procedure):
        1. Abduction: Update noise terms given observations
        2. Action: Set intervened variables
        3. Prediction: Forward-simulate with updated noise
        """
        # Step 1: Abduction — infer noise terms from observations
        noise_terms: Dict[str, float] = {}
        for target, eq in self._equations.items():
            if target in observed:
                predicted = eq.predict(observed)
                noise_terms[target] = observed[target] - predicted

        # Step 2: Action — apply intervention
        state = {name: var.mean for name, var in self._variables.items()}
        state.update(observed)  # Start from observed
        state.update(intervention)  # Apply intervention (overrides observed)

        # Step 3: Prediction — forward-simulate with inferred noise
        processed = set()
        for _ in range(len(self._equations) + 1):
            changed = False
            for target, eq in self._equations.items():
                if target in intervention:
                    continue  # Intervened variable is fixed
                if target in processed:
                    continue

                parent_vals = {p: state.get(p, 0.0) for p in eq.parent_vars}
                predicted = eq.predict(parent_vals)
                # Add inferred noise
                if target in noise_terms:
                    predicted += noise_terms[target]
                state[target] = predicted
                processed.add(target)
                changed = True

            if not changed:
                break

        # Return only the counterfactual values
        return {k: round(v, 4) for k, v in state.items()}

    def explain_effect(self, cause: str, effect: str) -> Dict:
        """
        تفسير سببي — كيف يسبب X الـ Y؟
        يجد المسار السببي ويحسب التأثير الكلي
        
        بدون LLM — رياضيات بحتة
        """
        if cause not in self._variables or effect not in self._variables:
            return {"error": "Variable not found"}

        # Find causal path using BFS through structural equations
        paths = self._find_causal_paths(cause, effect)
        if not paths:
            return {"cause": cause, "effect": effect, "path_found": False}

        # Compute total effect along each path
        total_effect = 0.0
        path_details = []
        for path in paths:
            path_effect = 1.0
            detail = []
            for i in range(len(path) - 1):
                src, tgt = path[i], path[i + 1]
                eq = self._equations.get(tgt)
                if eq:
                    coeff = eq.coefficients.get(src, 0.0)
                    path_effect *= coeff
                    detail.append({
                        "from": src, "to": tgt,
                        "coefficient": round(coeff, 4),
                    })
            total_effect += path_effect
            path_details.append({"path": path, "effect": round(path_effect, 4)})

        return {
            "cause": cause,
            "effect": effect,
            "path_found": True,
            "paths": path_details,
            "total_effect": round(total_effect, 4),
        }

    def _find_causal_paths(self, source: str, target: str,
                           max_depth: int = 10) -> List[List[str]]:
        """BFS لإيجاد المسارات السببية"""
        # Build adjacency from equations
        adjacency: Dict[str, List[str]] = defaultdict(list)
        for tgt, eq in self._equations.items():
            for parent in eq.parent_vars:
                adjacency[parent].append(tgt)

        from collections import deque
        visited = {source}
        queue = deque([(source, [source])])
        all_paths = []

        while queue:
            current, path = queue.popleft()
            if len(path) > max_depth:
                continue
            for neighbor in adjacency.get(current, []):
                if neighbor == target:
                    all_paths.append(path + [neighbor])
                elif neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return all_paths

    def get_stats(self) -> Dict:
        return {
            "variables": len(self._variables),
            "observations": len(self._observations),
            "structural_equations": len(self._equations),
            "discovered_edges": len(self._edges),
            "equation_details": {tgt: {"r_squared": eq.r_squared, "parents": eq.parent_vars}
                               for tgt, eq in self._equations.items()},
        }


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

causal_world_model = CausalWorldModel()
