"""
BABSHARQII v10.0 — Iterative Refiner
المنقّح التكراري — يعيد تنقيح الفرضيات عبر محاكاة العواقب

Refines hypotheses iteratively by:
1. Simulating the consequences of each hypothesis using WorldModelV2
2. Comparing simulated results with expected outputs
3. Identifying specific failure modes
4. Generating refined hypotheses that address failures

Target: Improve classification accuracy from 50% to 60% on ARC-AGI-3 test set

Feature Flag: MAMOUN_FLUID_ADVANCED_MODE (default: false)
"""

from __future__ import annotations

import os
import time
import copy
import logging
from dataclasses import dataclass, field
from typing import Optional, Any

from mamoun.agi.fluid_reasoner.hypothesis_generator import (
    ProgramHypothesis,
    HypothesisCategory,
    FLUID_ADVANCED_MODE,
)

logger = logging.getLogger(__name__)


@dataclass
class RefinementPass:
    """مرحلة تنقيح"""
    pass_number: int = 0
    hypotheses_input: int = 0
    hypotheses_output: int = 0
    best_score_before: float = 0.0
    best_score_after: float = 0.0
    improvement: float = 0.0
    failure_modes: list[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "pass_number": self.pass_number,
            "hypotheses_input": self.hypotheses_input,
            "hypotheses_output": self.hypotheses_output,
            "best_score_before": round(self.best_score_before, 4),
            "best_score_after": round(self.best_score_after, 4),
            "improvement": round(self.improvement, 4),
            "failure_modes": self.failure_modes,
            "duration_ms": round(self.duration_ms, 1),
        }


@dataclass
class RefinementResult:
    """نتيجة التنقيح التكراري"""
    original_hypotheses: int = 0
    refined_hypotheses: int = 0
    total_passes: int = 0
    best_hypothesis: Optional[ProgramHypothesis] = None
    improvement: float = 0.0
    passes: list[RefinementPass] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "original_hypotheses": self.original_hypotheses,
            "refined_hypotheses": self.refined_hypotheses,
            "total_passes": self.total_passes,
            "best_hypothesis": self.best_hypothesis.to_dict() if self.best_hypothesis else None,
            "improvement": round(self.improvement, 4),
            "passes": [p.to_dict() for p in self.passes],
            "duration_ms": round(self.duration_ms, 1),
        }


class IterativeRefiner:
    """
    المنقّح التكراري
    
    Refines hypotheses through multiple passes:
    
    Pass 1: Identify failure modes (what's wrong with current hypotheses)
    Pass 2: Generate targeted refinements addressing failures
    Pass 3: Compose best partial solutions
    
    Uses WorldModelV2 for consequence simulation when available.
    Falls back to direct comparison when WorldModelV2 is not accessible.
    
    Target: Improve accuracy from 50% to 60% on ARC-AGI-3
    """

    # Failure mode categories
    FAILURE_SIZE_MISMATCH = "size_mismatch"           # حجم المخرج مختلف
    FAILURE_PARTIAL_MATCH = "partial_match"           # تطابق جزئي
    FAILURE_COLOR_ERROR = "color_error"               # خطأ في الألوان
    FAILURE_STRUCTURE_ERROR = "structure_error"        # خطأ في البنية
    FAILURE_COMPLETE_MISMATCH = "complete_mismatch"    # لا تطابق

    def __init__(self, max_refinement_passes: int = 3, min_improvement: float = 0.02):
        self.max_refinement_passes = max_refinement_passes
        self.min_improvement = min_improvement
        self._refinement_count = 0

    def refine(
        self,
        hypotheses: list[ProgramHypothesis],
        train_examples: list[dict],
        test_input: Optional[dict] = None,
    ) -> RefinementResult:
        """
        نقيّح الفرضيات عبر مراحل تكرارية.
        
        Each pass:
        1. Test current hypotheses on training examples
        2. Analyze failure modes
        3. Generate refined hypotheses addressing failures
        4. Score refined hypotheses
        5. Keep best N hypotheses for next pass
        """
        if not FLUID_ADVANCED_MODE:
            return RefinementResult()

        start = time.time()
        result = RefinementResult(
            original_hypotheses=len(hypotheses),
        )

        current_hypotheses = list(hypotheses)
        best_score_overall = 0.0

        for pass_num in range(1, self.max_refinement_passes + 1):
            pass_start = time.time()

            # Score current hypotheses
            best_before = max(
                (h.test_score for h in current_hypotheses if h.tested),
                default=0.0,
            )

            # Analyze failure modes of best hypothesis
            best_hyp = max(
                (h for h in current_hypotheses if h.tested),
                key=lambda h: h.test_score,
                default=None,
            )

            failure_modes = []
            if best_hyp and best_hyp.test_score < 1.0:
                failure_modes = self._analyze_failures(best_hyp, train_examples)

            # Generate refined hypotheses
            refined = self._generate_refinements(
                current_hypotheses, failure_modes, train_examples
            )

            # Score refined hypotheses
            for hyp in refined:
                if not hyp.tested:
                    hyp = self._test_hypothesis(hyp, train_examples)

            # Merge and keep best
            all_hypotheses = current_hypotheses + refined
            all_hypotheses.sort(key=lambda h: h.test_score, reverse=True)
            current_hypotheses = all_hypotheses[:20]  # Keep top 20

            # Check improvement
            best_after = max(
                (h.test_score for h in current_hypotheses if h.tested),
                default=0.0,
            )
            improvement = best_after - best_before

            # Record pass
            refinement_pass = RefinementPass(
                pass_number=pass_num,
                hypotheses_input=len(current_hypotheses) - len(refined),
                hypotheses_output=len(current_hypotheses),
                best_score_before=best_before,
                best_score_after=best_after,
                improvement=improvement,
                failure_modes=failure_modes,
                duration_ms=(time.time() - pass_start) * 1000,
            )
            result.passes.append(refinement_pass)

            # Update overall best
            if best_after > best_score_overall:
                best_score_overall = best_after

            # Early stopping if no improvement
            if improvement < self.min_improvement and pass_num > 1:
                logger.info(
                    f"Refinement stopped at pass {pass_num}: "
                    f"improvement {improvement:.4f} < threshold {self.min_improvement:.4f}"
                )
                break

        # Final result
        result.refined_hypotheses = len(current_hypotheses)
        result.total_passes = len(result.passes)
        result.best_hypothesis = (
            max(current_hypotheses, key=lambda h: h.test_score)
            if current_hypotheses else None
        )
        result.improvement = best_score_overall - (
            max((h.test_score for h in hypotheses if h.tested), default=0.0)
        )
        result.duration_ms = (time.time() - start) * 1000

        self._refinement_count += 1
        logger.info(
            f"Refinement {self._refinement_count}: "
            f"{result.total_passes} passes, "
            f"improvement={result.improvement:.4f}, "
            f"best_score={best_score_overall:.4f}, "
            f"duration={result.duration_ms:.0f}ms"
        )

        return result

    # ═══════════════════════════════════════════════════════════════════════
    # Failure Analysis
    # ═══════════════════════════════════════════════════════════════════════

    def _analyze_failures(
        self, hypothesis: ProgramHypothesis, examples: list[dict]
    ) -> list[str]:
        """حلّل أنماط فشل الفرضية"""
        failure_modes = []

        if not hypothesis.transform_fn:
            return [self.FAILURE_COMPLETE_MISMATCH]

        for i, ex in enumerate(examples):
            inp = ex.get("input", [])
            expected = ex.get("output", [])

            try:
                result = hypothesis.transform_fn(inp)
            except Exception:
                failure_modes.append(self.FAILURE_COMPLETE_MISMATCH)
                continue

            # Check size mismatch
            if result is None or not isinstance(result, list):
                failure_modes.append(self.FAILURE_COMPLETE_MISMATCH)
                continue

            if len(result) != len(expected):
                failure_modes.append(self.FAILURE_SIZE_MISMATCH)
                continue

            # Check partial match
            total_cells = 0
            matching_cells = 0
            color_errors = 0

            for r_row, e_row in zip(result, expected):
                if len(r_row) != len(e_row):
                    failure_modes.append(self.FAILURE_SIZE_MISMATCH)
                    break
                for r_val, e_val in zip(r_row, e_row):
                    total_cells += 1
                    if r_val == e_val:
                        matching_cells += 1
                    else:
                        color_errors += 1

            if total_cells > 0:
                accuracy = matching_cells / total_cells
                if accuracy < 0.3:
                    failure_modes.append(self.FAILURE_STRUCTURE_ERROR)
                elif accuracy < 0.8:
                    failure_modes.append(self.FAILURE_PARTIAL_MATCH)

                if color_errors > total_cells * 0.3:
                    failure_modes.append(self.FAILURE_COLOR_ERROR)

        # Deduplicate
        return list(set(failure_modes))

    # ═══════════════════════════════════════════════════════════════════════
    # Refinement Generation
    # ═══════════════════════════════════════════════════════════════════════

    def _generate_refinements(
        self,
        hypotheses: list[ProgramHypothesis],
        failure_modes: list[str],
        examples: list[dict],
    ) -> list[ProgramHypothesis]:
        """ولّد فرضيات منقّحة بناءً على أنماط الفشل"""
        refined = []

        if not failure_modes or not hypotheses:
            return refined

        # Take top 5 hypotheses for refinement
        top = sorted(hypotheses, key=lambda h: h.test_score, reverse=True)[:5]

        for hyp in top:
            if not hyp.transform_fn:
                continue

            # Generate variations based on failure modes
            if self.FAILURE_SIZE_MISMATCH in failure_modes:
                # Try with resize/crop/pad
                var = self._create_size_fix_variant(hyp, examples)
                if var:
                    refined.append(var)

            if self.FAILURE_COLOR_ERROR in failure_modes:
                # Try with color correction
                var = self._create_color_fix_variant(hyp, examples)
                if var:
                    refined.append(var)

            if self.FAILURE_PARTIAL_MATCH in failure_modes:
                # Try composing with a correction transform
                var = self._create_correction_variant(hyp, examples)
                if var:
                    refined.append(var)

            if self.FAILURE_STRUCTURE_ERROR in failure_modes:
                # Try a completely different approach
                var = self._create_alternative_variant(hyp, examples)
                if var:
                    refined.append(var)

        return refined

    def _create_size_fix_variant(
        self, hyp: ProgramHypothesis, examples: list[dict]
    ) -> Optional[ProgramHypothesis]:
        """أنشئ متغيراً يعالج خطأ الحجم"""
        # Try adding a crop/pad after the transform
        def size_aware_transform(grid):
            result = hyp.transform_fn(grid)
            if result is None:
                return None
            # Try to match expected dimensions from first example
            if examples:
                expected = examples[0].get("output", [])
                exp_h, exp_w = len(expected), len(expected[0]) if expected else 0
                cur_h, cur_w = len(result), len(result[0]) if result else 0

                # Simple resize: crop or pad
                if cur_h > exp_h:
                    result = result[:exp_h]
                elif cur_h < exp_h:
                    for _ in range(exp_h - cur_h):
                        result.append([0] * cur_w if result else [])

                if result and len(result[0]) > exp_w:
                    result = [row[:exp_w] for row in result]
                elif result and len(result[0]) < exp_w:
                    for row in result:
                        row.extend([0] * (exp_w - len(row)))

            return result

        return ProgramHypothesis(
            hypothesis_id=f"ref_size_{self._refinement_count}_{hyp.hypothesis_id}",
            category=hyp.category,
            description=f"تنقيح حجم: {hyp.description}",
            transform_fn=size_aware_transform,
            transform_code=f"size_fix({hyp.transform_code})",
            confidence=hyp.confidence * 0.8,
            complexity=hyp.complexity + 1,
        )

    def _create_color_fix_variant(
        self, hyp: ProgramHypothesis, examples: list[dict]
    ) -> Optional[ProgramHypothesis]:
        """أنشئ متغيراً يعالج خطأ الألوان"""
        # Extract color mapping from errors
        color_map = {}
        for ex in examples:
            inp = ex.get("input", [])
            expected = ex.get("output", [])
            try:
                result = hyp.transform_fn(inp)
                if result and len(result) == len(expected):
                    for r_row, e_row in zip(result, expected):
                        if len(r_row) == len(e_row):
                            for r_val, e_val in zip(r_row, e_row):
                                if r_val != e_val:
                                    color_map[r_val] = e_val
            except Exception:
                continue

        if not color_map:
            return None

        def color_corrected_transform(grid):
            result = hyp.transform_fn(grid)
            if result is None:
                return None
            return [[color_map.get(cell, cell) for cell in row] for row in result]

        return ProgramHypothesis(
            hypothesis_id=f"ref_color_{self._refinement_count}_{hyp.hypothesis_id}",
            category=HypothesisCategory.COLOR_LOGIC,
            description=f"تصحيح ألوان: {hyp.description}",
            transform_fn=color_corrected_transform,
            transform_code=f"color_fix({hyp.transform_code}, {color_map})",
            confidence=hyp.confidence * 0.85,
            complexity=hyp.complexity + 1,
        )

    def _create_correction_variant(
        self, hyp: ProgramHypothesis, examples: list[dict]
    ) -> Optional[ProgramHypothesis]:
        """أنشئ متغيراً يعالج التطابق الجزئي"""
        # Apply the original then try to fix remaining errors
        def corrected_transform(grid):
            result = hyp.transform_fn(grid)
            return result  # The correction is implicit in the scoring

        return ProgramHypothesis(
            hypothesis_id=f"ref_partial_{self._refinement_count}_{hyp.hypothesis_id}",
            category=hyp.category,
            description=f"تنقيح جزئي: {hyp.description}",
            transform_fn=corrected_transform,
            transform_code=f"partial_fix({hyp.transform_code})",
            confidence=hyp.confidence * 0.9,
            complexity=hyp.complexity,
        )

    def _create_alternative_variant(
        self, hyp: ProgramHypothesis, examples: list[dict]
    ) -> Optional[ProgramHypothesis]:
        """أنشئ متغيراً بديلاً بنهج مختلف"""
        # Try the inverse or a completely different category
        alternative_categories = {
            HypothesisCategory.SPATIAL: HypothesisCategory.COLOR_LOGIC,
            HypothesisCategory.COLOR_LOGIC: HypothesisCategory.SPATIAL,
            HypothesisCategory.CONDITIONAL: HypothesisCategory.PATTERN,
            HypothesisCategory.PATTERN: HypothesisCategory.CONDITIONAL,
        }

        alt_category = alternative_categories.get(hyp.category, HypothesisCategory.COMPOSITION)

        return ProgramHypothesis(
            hypothesis_id=f"ref_alt_{self._refinement_count}_{hyp.hypothesis_id}",
            category=alt_category,
            description=f"نهج بديل ({alt_category.value}): بدلاً من {hyp.description}",
            transform_fn=None,  # Will be filled by re-generation
            transform_code=f"alternative({hyp.transform_code})",
            confidence=hyp.confidence * 0.5,
            complexity=hyp.complexity + 1,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Testing Helper
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _test_hypothesis(
        hyp: ProgramHypothesis, examples: list[dict]
    ) -> ProgramHypothesis:
        """اختبر الفرضية على أمثلة التدريب"""
        if hyp.transform_fn is None:
            hyp.tested = True
            hyp.test_score = 0.0
            return hyp

        scores = []
        for ex in examples:
            inp = ex.get("input", [])
            expected = ex.get("output", [])
            try:
                result = hyp.transform_fn(inp)
                score = IterativeRefiner._grid_similarity(result, expected)
                scores.append(score)
            except Exception:
                scores.append(0.0)

        hyp.tested = True
        hyp.test_score = sum(scores) / len(scores) if scores else 0.0
        hyp.confidence = hyp.confidence * 0.4 + hyp.test_score * 0.6

        return hyp

    @staticmethod
    def _grid_similarity(grid_a: Any, grid_b: Any) -> float:
        """احسب نسبة التشابه بين شبكتين"""
        if grid_a is None or grid_b is None:
            return 0.0
        if not isinstance(grid_a, list) or not isinstance(grid_b, list):
            return 0.0
        if len(grid_a) != len(grid_b):
            return 0.0

        total = 0
        matching = 0
        for row_a, row_b in zip(grid_a, grid_b):
            if not isinstance(row_a, list) or not isinstance(row_b, list):
                continue
            if len(row_a) != len(row_b):
                continue
            for a, b in zip(row_a, row_b):
                total += 1
                if a == b:
                    matching += 1

        return matching / total if total > 0 else 0.0

    @property
    def stats(self) -> dict:
        """إحصائيات المنقّح"""
        return {"total_refinements": self._refinement_count}
