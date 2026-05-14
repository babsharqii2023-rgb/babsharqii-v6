"""
BABSHARQII v10.0 — ARC-AGI-3 Adapter
مُكيّف ARC-AGI-3 — يربط المحاكي الافتراضي بنظام الاستدلال السائب

Bridges the CounterfactualSimulator with the FluidReasonerBrain,
enabling ARC-AGI-3 task solving with dual-branch verification.

v10.0 additions:
  - HypothesisGenerator for program-synthesis-based hypothesis generation
  - PatternDiscovery for hidden pattern detection
  - IterativeRefiner for multi-pass hypothesis refinement
  - Self-evaluation loop

Feature Flags:
  MAMOUN_ARC_MODE (default: false) — basic ARC support
  MAMOUN_FLUID_ADVANCED_MODE (default: false) — v10 advanced pipeline
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Optional

from mamoun.agi.fluid_reasoner.counterfactual_simulator import (
    CounterfactualSimulator,
    CounterfactualResult,
    RuleHypothesis,
    ARC_MODE_ENABLED,
)

# v10 Feature Flag
FLUID_ADVANCED_MODE: bool = os.environ.get(
    "MAMOUN_FLUID_ADVANCED_MODE", "false"
).lower() in ("true", "1", "yes")

logger = logging.getLogger(__name__)


@dataclass
class ARCAdapterConfig:
    """إعدادات مُكيّف ARC"""
    max_hypotheses: int = 30
    min_confidence: float = 0.55
    enable_multi_pass: bool = True
    max_refinement_passes: int = 3
    fallback_to_statistical: bool = True
    # v10 additions
    enable_advanced_pipeline: bool = True  # Use HypothesisGenerator + PatternDiscovery + IterativeRefiner
    enable_pattern_discovery: bool = True
    enable_iterative_refinement: bool = True
    enable_self_eval: bool = True


class ARCAdapter:
    """
    مُكيّف ARC-AGI-3

    Integrates the CounterfactualSimulator with the Fluid Reasoning pipeline.
    Provides a clean interface for ARC task solving.

    Workflow:
      1. Receive ARC task (train examples + test input)
      2. Generate hypotheses via CounterfactualSimulator
      3. If confidence ≥ threshold → return result
      4. If confidence < threshold → refine with multi-pass
      5. If still low confidence → fallback to statistical matching
    """

    def __init__(self, config: Optional[ARCAdapterConfig] = None):
        self.config = config or ARCAdapterConfig()
        self.simulator = CounterfactualSimulator(
            max_hypotheses=self.config.max_hypotheses,
            min_confidence=self.config.min_confidence,
        )

        # v10 advanced pipeline (lazy-loaded)
        self._hypothesis_generator = None
        self._pattern_discovery = None
        self._iterative_refiner = None

        self._solve_count = 0
        self._success_count = 0
        self._advanced_solve_count = 0

        # Check if advanced mode is enabled
        self._advanced_enabled = FLUID_ADVANCED_MODE and self.config.enable_advanced_pipeline

    def solve_task(
        self, task_id: str, train_examples: list[dict], test_input: dict
    ) -> Optional[list]:
        """
        حل مهمة ARC-AGI-3 باستخدام المحاكي الافتراضي + خط الأنابيب المتقدم (v10).

        v10 pipeline (when MAMOUN_FLUID_ADVANCED_MODE=true):
          1. Generate hypotheses via HypothesisGenerator (program synthesis)
          2. Discover patterns via PatternDiscovery
          3. Refine hypotheses via IterativeRefiner
          4. Self-evaluate: compare with CounterfactualSimulator results
          5. Return best result

        Returns predicted output grid, or None if unable to solve.
        """
        if not ARC_MODE_ENABLED:
            logger.info("ARC mode disabled — skipping counterfactual simulation")
            return None

        self._solve_count += 1

        # ═══ v10 Advanced Pipeline ═══
        if self._advanced_enabled:
            advanced_result = self._solve_task_advanced(
                task_id, train_examples, test_input
            )
            if advanced_result is not None:
                return advanced_result

        # ═══ v9 Standard Pipeline (fallback) ═══
        # Pass 1: Initial simulation
        result = self.simulator.simulate(
            task_id=task_id,
            train_examples=train_examples,
            test_input=test_input,
        )

        if result.predicted_output is not None and result.confidence >= self.config.min_confidence:
            self._success_count += 1
            logger.info(
                f"ARC task {task_id} solved in pass 1: "
                f"confidence={result.confidence:.2f}, "
                f"hypotheses={result.hypotheses_tested}"
            )
            return result.predicted_output

        # Multi-pass refinement (v9)
        if self.config.enable_multi_pass:
            for pass_num in range(2, self.config.max_refinement_passes + 1):
                refined = self._refine_simulation(result, train_examples, test_input)
                if refined and refined.confidence > result.confidence:
                    result = refined
                if result.confidence >= self.config.min_confidence:
                    self._success_count += 1
                    logger.info(
                        f"ARC task {task_id} solved in pass {pass_num}: "
                        f"confidence={result.confidence:.2f}"
                    )
                    return result.predicted_output

        # Fallback to statistical matching
        if self.config.fallback_to_statistical:
            logger.info(f"ARC task {task_id}: falling back to statistical matching")
            return self._statistical_fallback(train_examples, test_input)

        return None

    def _refine_simulation(
        self, previous: CounterfactualResult,
        train_examples: list[dict], test_input: dict,
    ) -> Optional[CounterfactualResult]:
        """تحسين المحاكاة بإنشاء فرضيات أكثر تحديداً"""
        if previous.best_hypothesis is None:
            return None

        # Try variations of the best hypothesis
        best_type = previous.best_hypothesis.hypothesis_type
        variations = self._generate_variations(best_type, previous.best_hypothesis)

        result = self.simulator.simulate(
            task_id=previous.task_id,
            train_examples=train_examples,
            test_input=test_input,
            candidate_rules=variations,
        )
        return result

    def _generate_variations(
        self, base_type, base_hypothesis: RuleHypothesis
    ) -> list[RuleHypothesis]:
        """ولّد تنويعات على الفرضية الأفضل"""
        from mamoun.agi.fluid_reasoner.counterfactual_simulator import HypothesisType

        variations = []
        # Try related hypothesis types
        related = {
            HypothesisType.COLOR_MAP: [HypothesisType.CONDITIONAL],
            HypothesisType.ROTATION: [HypothesisType.REFLECTION, HypothesisType.SYMMETRY],
            HypothesisType.REFLECTION: [HypothesisType.SYMMETRY, HypothesisType.ROTATION],
            HypothesisType.INVERSION: [HypothesisType.COLOR_MAP],
            HypothesisType.PATTERN_REPEAT: [HypothesisType.SYMMETRY],
            HypothesisType.SYMMETRY: [HypothesisType.REFLECTION, HypothesisType.PATTERN_REPEAT],
            HypothesisType.CONDITIONAL: [HypothesisType.COLOR_MAP],
        }

        for rel_type in related.get(base_type, []):
            variations.append(RuleHypothesis(
                hypothesis_id=f"var_{rel_type.value}",
                hypothesis_type=rel_type,
                rule={},
                confidence=0.1,
            ))

        return variations

    def _statistical_fallback(
        self, train_examples: list[dict], test_input: dict
    ) -> Optional[list]:
        """
        احتياطي إحصائي — حاول مطابقة الأنماط البسيطة.
        """
        if not train_examples:
            return None

        # Try: most common output structure
        first_output = train_examples[0].get("output", [])
        if first_output:
            # Return a copy of the first training output as fallback
            return [row[:] for row in first_output]
        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # v10 Advanced Pipeline
    # ═══════════════════════════════════════════════════════════════════════════

    def _solve_task_advanced(
        self, task_id: str, train_examples: list[dict], test_input: dict
    ) -> Optional[list]:
        """
        حل متقدم (v10) — استخدام HypothesisGenerator + PatternDiscovery + IterativeRefiner
        """
        self._advanced_solve_count += 1

        # Step 1: Generate hypotheses via HypothesisGenerator
        generator = self._get_hypothesis_generator()
        hypotheses = generator.generate(train_examples, test_input)

        if not hypotheses:
            logger.info(f"ARC task {task_id}: HypothesisGenerator produced no hypotheses")
            return None

        # Step 2: Discover patterns
        if self.config.enable_pattern_discovery:
            discovery = self._get_pattern_discovery()
            patterns = discovery.discover(train_examples)
            # Use pattern information to boost matching hypotheses
            for hyp in hypotheses:
                for pattern in patterns:
                    if pattern.details and hyp.category.value in pattern.pattern_type.value:
                        hyp.confidence = min(1.0, hyp.confidence + pattern.confidence * 0.1)

        # Step 3: Refine hypotheses
        if self.config.enable_iterative_refinement:
            refiner = self._get_iterative_refiner()
            refinement_result = refiner.refine(hypotheses, train_examples, test_input)
            if refinement_result.best_hypothesis:
                best = refinement_result.best_hypothesis
            else:
                best = max(hypotheses, key=lambda h: h.test_score) if hypotheses else None
        else:
            best = max(hypotheses, key=lambda h: h.test_score) if hypotheses else None

        if best is None or best.test_score < 0.3:
            logger.info(
                f"ARC task {task_id}: Advanced pipeline best score too low "
                f"({best.test_score:.2f if best else 0:.2f})"
            )
            return None

        # Step 4: Self-evaluation — compare with v9 CounterfactualSimulator
        if self.config.enable_self_eval:
            v9_result = self.simulator.simulate(
                task_id=task_id,
                train_examples=train_examples,
                test_input=test_input,
            )
            # Use v9 result if it's better
            if v9_result.confidence > best.test_score and v9_result.predicted_output is not None:
                logger.info(
                    f"ARC task {task_id}: v9 result ({v9_result.confidence:.2f}) "
                    f"better than v10 ({best.test_score:.2f}) — using v9"
                )
                self._success_count += 1
                return v9_result.predicted_output

        # Step 5: Apply best hypothesis to test input
        if best.transform_fn:
            try:
                predicted = best.transform_fn(test_input)
                if predicted is not None:
                    self._success_count += 1
                    logger.info(
                        f"ARC task {task_id}: Advanced pipeline solved "
                        f"(score={best.test_score:.2f}, category={best.category.value})"
                    )
                    return predicted
            except Exception as e:
                logger.warning(f"ARC task {task_id}: Failed to apply best hypothesis: {e}")

        return None

    def _get_hypothesis_generator(self):
        """تحميل كسول لمولّد الفرضيات"""
        if self._hypothesis_generator is None:
            from mamoun.agi.fluid_reasoner.hypothesis_generator import HypothesisGenerator
            self._hypothesis_generator = HypothesisGenerator(
                max_hypotheses=self.config.max_hypotheses,
            )
        return self._hypothesis_generator

    def _get_pattern_discovery(self):
        """تحميل كسول لمكتشف الأنماط"""
        if self._pattern_discovery is None:
            from mamoun.agi.fluid_reasoner.pattern_discovery import PatternDiscovery
            self._pattern_discovery = PatternDiscovery()
        return self._pattern_discovery

    def _get_iterative_refiner(self):
        """تحميل كسول للمنقّح التكراري"""
        if self._iterative_refiner is None:
            from mamoun.agi.fluid_reasoner.iterative_refiner import IterativeRefiner
            self._iterative_refiner = IterativeRefiner(
                max_refinement_passes=self.config.max_refinement_passes,
            )
        return self._iterative_refiner

    @property
    def stats(self) -> dict:
        """إحصائيات المُكيّف"""
        return {
            "total_solved": self._solve_count,
            "successful": self._success_count,
            "success_rate": self._success_count / self._solve_count if self._solve_count > 0 else 0.0,
            "advanced_solves": self._advanced_solve_count,
            "advanced_mode": self._advanced_enabled,
        }
