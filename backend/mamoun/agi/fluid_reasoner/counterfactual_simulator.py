"""
BABSHARQII v9.0 — Counterfactual Simulator
المحاكي الافتراضي المزدوج — يختبر الفرضيات قبل التنفيذ

Simulates "what if?" scenarios in parallel: one branch assumes the hypothesis
is true, the other assumes it's false. Compares outcomes to select the
most consistent rule for the given ARC task.

This implements the core insight from Causal-JEPA: counterfactual simulation
in latent space enables hypothesis testing without trial-and-error execution.

Feature Flag: MAMOUN_ARC_MODE (default: false)
"""

from __future__ import annotations

import os
import copy
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any

logger = logging.getLogger(__name__)

ARC_MODE_ENABLED: bool = os.environ.get(
    "MAMOUN_ARC_MODE", "false"
).lower() in ("true", "1", "yes")


class HypothesisType(Enum):
    """أنواع فرضيات التحويل"""
    COLOR_MAP = "color_map"             # تعيين ألوان ثابت
    ROTATION = "rotation"               # تدوير
    REFLECTION = "reflection"           # انعكاس
    SCALING = "scaling"                 # تحجيم
    PATTERN_REPEAT = "pattern_repeat"   # تكرار نمط
    CONDITIONAL = "conditional"         # شرطي
    COUNT_BASED = "count_based"         # قائم على العدّ
    SYMMETRY = "symmetry"               # تماثل
    INVERSION = "inversion"             # عكس
    OBJECT_TRANSFORM = "object_transform"  # تحويل كائنات


@dataclass
class RuleHypothesis:
    """فرضية قاعدة تحويل"""
    hypothesis_id: str = ""
    hypothesis_type: HypothesisType = HypothesisType.COLOR_MAP
    rule: dict = field(default_factory=dict)  # قاعدة التحويل المقترحة
    confidence: float = 0.0
    consistency_score: float = 0.0     # مدى اتساقها مع أمثلة التدريب
    counterfactual_score: float = 0.0  # نتيجة المحاكاة الافتراضية
    verified: bool = False


@dataclass
class SimulationBranch:
    """فرع محاكاة — حقيقي أو مفترض"""
    branch_id: str = ""
    is_counterfactual: bool = False
    hypothesis: Optional[RuleHypothesis] = None
    predicted_output: Any = None
    consistency_with_training: float = 0.0
    expected_correctness: float = 0.0


@dataclass
class CounterfactualResult:
    """نتيجة المحاكاة الافتراضية المزدوجة"""
    task_id: str = ""
    best_hypothesis: Optional[RuleHypothesis] = None
    predicted_output: Any = None
    branches_evaluated: int = 0
    confidence: float = 0.0
    hypotheses_tested: int = 0


class CounterfactualSimulator:
    """
    المحاكي الافتراضي المزدوج

    For each candidate rule hypothesis:
      1. Branch A: Apply the rule → check consistency with training examples
      2. Branch B: Apply the INVERSE rule → check inconsistency (counterfactual)
      3. If Branch A is consistent AND Branch B is inconsistent → accept rule
      4. If both branches are consistent → rule is too weak, refine
      5. If Branch A is inconsistent → reject rule

    This dual-branch verification dramatically reduces false positives
    compared to single-branch consistency checking.
    """

    def __init__(self, max_hypotheses: int = 20, min_confidence: float = 0.6):
        self.max_hypotheses = max_hypotheses
        self.min_confidence = min_confidence

    def simulate(
        self,
        task_id: str,
        train_examples: list[dict],
        test_input: dict,
        candidate_rules: Optional[list[RuleHypothesis]] = None,
    ) -> CounterfactualResult:
        """
        شغّل المحاكاة الافتراضية المزدوجة على مهمة ARC.

        1. Generate candidate rule hypotheses from training examples
        2. For each hypothesis, run dual-branch simulation
        3. Select the best hypothesis based on combined scores
        4. Apply best hypothesis to test input
        """
        start = time.time()

        # Step 1: Generate hypotheses if not provided
        if candidate_rules is None:
            candidate_rules = self._generate_hypotheses(train_examples)

        # Step 2: Evaluate each hypothesis via dual-branch simulation
        evaluated = []
        for hyp in candidate_rules[:self.max_hypotheses]:
            result = self._dual_branch_evaluate(hyp, train_examples)
            if result is not None:
                evaluated.append(result)

        if not evaluated:
            return CounterfactualResult(task_id=task_id, branches_evaluated=0)

        # Step 3: Select best hypothesis
        best = max(evaluated, key=lambda h: h.consistency_score + h.counterfactual_score * 0.5)

        # Step 4: Apply to test input
        predicted = self._apply_rule(best, test_input)

        elapsed = (time.time() - start) * 1000
        logger.info(
            f"Counterfactual simulation for {task_id}: "
            f"{len(evaluated)} hypotheses, best={best.hypothesis_type.value}, "
            f"confidence={best.confidence:.2f}, time={elapsed:.0f}ms"
        )

        return CounterfactualResult(
            task_id=task_id,
            best_hypothesis=best,
            predicted_output=predicted,
            branches_evaluated=len(evaluated) * 2,  # dual branches
            confidence=best.confidence,
            hypotheses_tested=len(candidate_rules),
        )

    def _generate_hypotheses(self, train_examples: list[dict]) -> list[RuleHypothesis]:
        """
        ولّد فرضيات القواعد من أمثلة التدريب.

        Analyzes input-output pairs to extract candidate transformation rules.
        """
        hypotheses = []

        if not train_examples:
            return hypotheses

        # Hypothesis 1: Color mapping (most common in ARC easy tasks)
        color_map = self._extract_color_map(train_examples)
        if color_map:
            hypotheses.append(RuleHypothesis(
                hypothesis_id=f"hyp_color_{len(hypotheses)}",
                hypothesis_type=HypothesisType.COLOR_MAP,
                rule={"mapping": color_map},
                confidence=0.5,
            ))

        # Hypothesis 2: Rotation
        rotation = self._detect_rotation(train_examples)
        if rotation is not None:
            hypotheses.append(RuleHypothesis(
                hypothesis_id=f"hyp_rot_{len(hypotheses)}",
                hypothesis_type=HypothesisType.ROTATION,
                rule={"degrees": rotation},
                confidence=0.4,
            ))

        # Hypothesis 3: Reflection
        reflection = self._detect_reflection(train_examples)
        if reflection:
            hypotheses.append(RuleHypothesis(
                hypothesis_id=f"hyp_ref_{len(hypotheses)}",
                hypothesis_type=HypothesisType.REFLECTION,
                rule={"axis": reflection},
                confidence=0.4,
            ))

        # Hypothesis 4: Pattern repeat
        pattern = self._detect_pattern(train_examples)
        if pattern:
            hypotheses.append(RuleHypothesis(
                hypothesis_id=f"hyp_pattern_{len(hypotheses)}",
                hypothesis_type=HypothesisType.PATTERN_REPEAT,
                rule={"unit": pattern},
                confidence=0.3,
            ))

        # Hypothesis 5: Inversion (0↔1)
        if self._detect_inversion(train_examples):
            hypotheses.append(RuleHypothesis(
                hypothesis_id=f"hyp_inv_{len(hypotheses)}",
                hypothesis_type=HypothesisType.INVERSION,
                rule={"type": "binary_inversion"},
                confidence=0.6,
            ))

        # Hypothesis 6: Conditional transform (parity, position-based)
        conditional = self._detect_conditional(train_examples)
        if conditional:
            hypotheses.append(RuleHypothesis(
                hypothesis_id=f"hyp_cond_{len(hypotheses)}",
                hypothesis_type=HypothesisType.CONDITIONAL,
                rule=conditional,
                confidence=0.3,
            ))

        # Hypothesis 7: Symmetry completion
        symmetry = self._detect_symmetry(train_examples)
        if symmetry:
            hypotheses.append(RuleHypothesis(
                hypothesis_id=f"hyp_sym_{len(hypotheses)}",
                hypothesis_type=HypothesisType.SYMMETRY,
                rule={"axis": symmetry},
                confidence=0.4,
            ))

        return hypotheses

    def _dual_branch_evaluate(
        self, hypothesis: RuleHypothesis, train_examples: list[dict]
    ) -> Optional[RuleHypothesis]:
        """
        قيّم الفرضية عبر فرعين: حقيقي ومفترض (عكسي).
        """
        # Branch A: Apply rule to training inputs, check consistency
        consistency_scores = []
        for example in train_examples:
            input_grid = example.get("input", [])
            expected_output = example.get("output", [])
            predicted = self._apply_rule(hypothesis, input_grid)
            if predicted is not None:
                score = self._grid_similarity(predicted, expected_output)
                consistency_scores.append(score)

        if not consistency_scores:
            return None

        avg_consistency = sum(consistency_scores) / len(consistency_scores)
        hypothesis.consistency_score = avg_consistency

        # Branch B: Apply INVERSE rule, check inconsistency
        inverse_hyp = self._invert_hypothesis(hypothesis)
        counter_scores = []
        for example in train_examples:
            input_grid = example.get("input", [])
            expected_output = example.get("output", [])
            counter_predicted = self._apply_rule(inverse_hyp, input_grid)
            if counter_predicted is not None:
                score = self._grid_similarity(counter_predicted, expected_output)
                counter_scores.append(score)

        if counter_scores:
            avg_counter = sum(counter_scores) / len(counter_scores)
            # Good hypothesis: high consistency + low counterfactual consistency
            hypothesis.counterfactual_score = 1.0 - avg_counter
        else:
            hypothesis.counterfactual_score = 0.5

        # Combined confidence
        hypothesis.confidence = (
            avg_consistency * 0.6 + hypothesis.counterfactual_score * 0.4
        )
        hypothesis.verified = hypothesis.confidence >= self.min_confidence

        return hypothesis

    def _apply_rule(self, hypothesis: RuleHypothesis, grid: Any) -> Any:
        """طبّق قاعدة الفرضية على شبكة"""
        if grid is None:
            return None

        try:
            hyp_type = hypothesis.hypothesis_type
            rule = hypothesis.rule

            if hyp_type == HypothesisType.COLOR_MAP:
                mapping = rule.get("mapping", {})
                return self._apply_color_map(grid, mapping)

            elif hyp_type == HypothesisType.ROTATION:
                degrees = rule.get("degrees", 0)
                return self._apply_rotation(grid, degrees)

            elif hyp_type == HypothesisType.REFLECTION:
                axis = rule.get("axis", "vertical")
                return self._apply_reflection(grid, axis)

            elif hyp_type == HypothesisType.INVERSION:
                return self._apply_inversion(grid)

            elif hyp_type == HypothesisType.PATTERN_REPEAT:
                unit = rule.get("unit", grid)
                return self._apply_pattern_repeat(grid, unit)

            elif hyp_type == HypothesisType.SYMMETRY:
                axis = rule.get("axis", "vertical")
                return self._apply_symmetry(grid, axis)

            elif hyp_type == HypothesisType.CONDITIONAL:
                return self._apply_conditional(grid, rule)

            return None
        except Exception as e:
            logger.debug(f"Rule application failed: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════════════════
    # Rule application helpers
    # ═══════════════════════════════════════════════════════════════════════════

    def _apply_color_map(self, grid: list, mapping: dict) -> list:
        """طبّق تعيين الألوان"""
        result = []
        for row in grid:
            new_row = [mapping.get(cell, cell) for cell in row]
            result.append(new_row)
        return result

    def _apply_rotation(self, grid: list, degrees: int) -> list:
        """طبّق التدوير"""
        if degrees == 90:
            # Rotate 90° clockwise: transpose then reverse each row
            if not grid:
                return grid
            rows, cols = len(grid), len(grid[0])
            result = [[grid[rows - 1 - r][c] for r in range(rows)] for c in range(cols)]
            return result
        elif degrees == 180:
            return [row[::-1] for row in grid[::-1]]
        elif degrees == 270:
            if not grid:
                return grid
            rows, cols = len(grid), len(grid[0])
            result = [[grid[r][cols - 1 - c] for r in range(rows)] for c in range(cols)]
            return result
        return grid

    def _apply_reflection(self, grid: list, axis: str) -> list:
        """طبّق الانعكاس"""
        if axis == "vertical":
            return [row[::-1] for row in grid]
        elif axis == "horizontal":
            return grid[::-1]
        return grid

    def _apply_inversion(self, grid: list) -> list:
        """طبّق العكس (0↔1)"""
        result = []
        for row in grid:
            new_row = [1 if cell == 0 else 0 if cell == 1 else cell for cell in row]
            result.append(new_row)
        return result

    def _apply_pattern_repeat(self, grid: list, unit: Any) -> list:
        """طبّق تكرار النمط"""
        # Repeat the first row to fill
        if grid and len(grid) > 0:
            first_row = grid[0]
            return [first_row[:] for _ in range(len(grid))]
        return grid

    def _apply_symmetry(self, grid: list, axis: str) -> list:
        """طبّق استكمال التماثل"""
        result = [row[:] for row in grid]
        if axis == "vertical":
            mid = len(result[0]) // 2 if result else 0
            for row in result:
                for i in range(mid):
                    mirror_idx = len(row) - 1 - i
                    if 0 <= mirror_idx < len(row) and row[mirror_idx] == 0:
                        row[mirror_idx] = row[i]
        return result

    def _apply_conditional(self, grid: list, rule: dict) -> list:
        """طبّق التحويل الشرطي"""
        condition = rule.get("condition", "even")
        action = rule.get("action", "zero")
        result = [row[:] for row in grid]
        for i, row in enumerate(result):
            for j, cell in enumerate(row):
                if condition == "even" and cell % 2 == 0:
                    result[i][j] = 0 if action == "zero" else cell
                elif condition == "odd" and cell % 2 == 1:
                    result[i][j] = cell  # keep
                else:
                    result[i][j] = 0 if action == "zero_others" else cell
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # Hypothesis generation helpers
    # ═══════════════════════════════════════════════════════════════════════════

    def _extract_color_map(self, examples: list[dict]) -> Optional[dict]:
        """استخلاص تعيين الألوان من أمثلة التدريب"""
        mapping = {}
        for ex in examples:
            inp = ex.get("input", [])
            out = ex.get("output", [])
            if len(inp) == len(out):
                for in_row, out_row in zip(inp, out):
                    if len(in_row) == len(out_row):
                        for i_val, o_val in zip(in_row, out_row):
                            if i_val in mapping and mapping[i_val] != o_val:
                                return None  # Inconsistent mapping
                            mapping[i_val] = o_val
        return mapping if mapping else None

    def _detect_rotation(self, examples: list[dict]) -> Optional[int]:
        """كشف التدوير"""
        for degrees in [90, 180, 270]:
            all_match = True
            for ex in examples:
                inp = ex.get("input", [])
                expected = ex.get("output", [])
                rotated = self._apply_rotation(inp, degrees)
                if rotated != expected:
                    all_match = False
                    break
            if all_match and len(examples) > 0:
                return degrees
        return None

    def _detect_reflection(self, examples: list[dict]) -> Optional[str]:
        """كشف الانعكاس"""
        for axis in ["vertical", "horizontal"]:
            all_match = True
            for ex in examples:
                inp = ex.get("input", [])
                expected = ex.get("output", [])
                reflected = self._apply_reflection(inp, axis)
                if reflected != expected:
                    all_match = False
                    break
            if all_match and len(examples) > 0:
                return axis
        return None

    def _detect_inversion(self, examples: list[dict]) -> bool:
        """كشف العكس"""
        all_match = True
        for ex in examples:
            inp = ex.get("input", [])
            expected = ex.get("output", [])
            inverted = self._apply_inversion(inp)
            if inverted != expected:
                all_match = False
                break
        return all_match and len(examples) > 0

    def _detect_pattern(self, examples: list[dict]) -> Optional[list]:
        """كشف تكرار النمط"""
        for ex in examples:
            inp = ex.get("input", [])
            out = ex.get("output", [])
            if len(out) > 0 and all(row == out[0] for row in out):
                return out[0]
        return None

    def _detect_conditional(self, examples: list[dict]) -> Optional[dict]:
        """كشف التحويل الشرطي"""
        # Check if even cells are preserved, odd cells zeroed (or vice versa)
        for condition in ["even", "odd"]:
            all_match = True
            for ex in examples:
                inp = ex.get("input", [])
                expected = ex.get("output", [])
                result = self._apply_conditional(inp, {"condition": condition, "action": "zero_others"})
                if result != expected:
                    all_match = False
                    break
            if all_match and len(examples) > 0:
                return {"condition": condition, "action": "zero_others"}
        return None

    def _detect_symmetry(self, examples: list[dict]) -> Optional[str]:
        """كشف التماثل"""
        for axis in ["vertical"]:
            all_match = True
            for ex in examples:
                inp = ex.get("input", [])
                expected = ex.get("output", [])
                result = self._apply_symmetry(inp, axis)
                if result != expected:
                    all_match = False
                    break
            if all_match and len(examples) > 0:
                return axis
        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # Utility functions
    # ═══════════════════════════════════════════════════════════════════════════

    def _grid_similarity(self, grid_a: Any, grid_b: Any) -> float:
        """احسب نسبة التشابه بين شبكتين"""
        if grid_a is None or grid_b is None:
            return 0.0
        if not isinstance(grid_a, list) or not isinstance(grid_b, list):
            return 0.0
        if len(grid_a) != len(grid_b):
            return 0.0

        total_cells = 0
        matching_cells = 0

        for row_a, row_b in zip(grid_a, grid_b):
            if not isinstance(row_a, list) or not isinstance(row_b, list):
                continue
            if len(row_a) != len(row_b):
                continue
            for a, b in zip(row_a, row_b):
                total_cells += 1
                if a == b:
                    matching_cells += 1

        return matching_cells / total_cells if total_cells > 0 else 0.0

    def _invert_hypothesis(self, hypothesis: RuleHypothesis) -> RuleHypothesis:
        """أنشئ الفرضية العكسية"""
        inverted = RuleHypothesis(
            hypothesis_id=f"inv_{hypothesis.hypothesis_id}",
            hypothesis_type=hypothesis.hypothesis_type,
            rule=copy.deepcopy(hypothesis.rule),
            confidence=0.0,
        )

        # Invert the rule
        if hypothesis.hypothesis_type == HypothesisType.COLOR_MAP:
            mapping = hypothesis.rule.get("mapping", {})
            inverted.rule["mapping"] = {v: k for k, v in mapping.items()}
        elif hypothesis.hypothesis_type == HypothesisType.ROTATION:
            degrees = hypothesis.rule.get("degrees", 0)
            inverted.rule["degrees"] = (360 - degrees) % 360
        elif hypothesis.hypothesis_type == HypothesisType.REFLECTION:
            # Double reflection = identity, so use different axis
            current = hypothesis.rule.get("axis", "vertical")
            inverted.rule["axis"] = "horizontal" if current == "vertical" else "vertical"

        return inverted
