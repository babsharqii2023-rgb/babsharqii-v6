"""
BABSHARQII v10.0 — Hypothesis Generator
مولّد الفرضيات — يولّد فرضيات متعددة لحل مهمة ARC-AGI باستخدام التركيب البرمجي

Generates multiple hypotheses for solving ARC-AGI tasks using:
1. Program synthesis — generate transformation functions from examples
2. LLM-assisted hypothesis generation
3. Heuristic rule generation from structural analysis

Inspired by ARC Prize 2025 top performers: the key insight is to treat
ARC tasks as program synthesis problems rather than direct prediction.

Feature Flag: MAMOUN_FLUID_ADVANCED_MODE (default: false)
"""

from __future__ import annotations

import os
import copy
import time
import hashlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any, Callable

logger = logging.getLogger(__name__)

FLUID_ADVANCED_MODE: bool = os.environ.get(
    "MAMOUN_FLUID_ADVANCED_MODE", "false"
).lower() in ("true", "1", "yes")


class HypothesisCategory(Enum):
    """فئات فرضيات التحويل"""
    SPATIAL = "spatial"             # علاقات مكانية
    TRANSFORMATION = "transformation"  # تحويلات هندسية
    COLOR_LOGIC = "color_logic"     # منطق الألوان
    COUNTING = "counting"           # قائم على العدّ
    COMPOSITION = "composition"     # تركيب عدة تحويلات
    CONDITIONAL = "conditional"     # شرطي
    PATTERN = "pattern"            # تكرار أنماط


@dataclass
class ProgramHypothesis:
    """
    فرضية برمجية — تحويل مُقترح كدالة قابلة للتنفيذ.
    
    Unlike simple rule hypotheses (v9.0), program hypotheses can represent
    complex multi-step transformations including loops, conditionals, and
    composition of simpler operations.
    """
    hypothesis_id: str = ""
    category: HypothesisCategory = HypothesisCategory.SPATIAL
    description: str = ""                     # وصف الفرضية بالعربية
    transform_fn: Optional[Any] = None        # دالة التحويل (callable)
    transform_code: str = ""                  # الشفرة المصدرية للتحويل
    confidence: float = 0.0                   # ثقة أولية
    complexity: int = 1                       # تعقيد الفرضية (عدد الخطوات)
    tested: bool = False
    test_score: float = 0.0                   # نتيجة الاختبار على أمثلة التدريب

    def to_dict(self) -> dict:
        return {
            "hypothesis_id": self.hypothesis_id,
            "category": self.category.value,
            "description": self.description,
            "transform_code": self.transform_code,
            "confidence": round(self.confidence, 4),
            "complexity": self.complexity,
            "tested": self.tested,
            "test_score": round(self.test_score, 4),
        }


class HypothesisGenerator:
    """
    مولّد الفرضيات
    
    Generates multiple hypotheses for ARC-AGI task solving using:
    1. Structural analysis of input-output pairs
    2. Program synthesis from patterns
    3. LLM-assisted generation (when available)
    4. Compositional hypothesis building
    
    Target: ≥5 valid hypotheses per ARC sample
    """

    # تعقيدات التحويلات المدعومة
    SIMPLE_TRANSFORMS = [
        "identity", "rotate_90", "rotate_180", "rotate_270",
        "flip_h", "flip_v", "transpose", "invert_colors",
    ]

    COMPOUND_TRANSFORMS = [
        "rotate_then_flip", "flip_then_color_map",
        "crop_and_repeat", "scale_and_center",
    ]

    def __init__(self, max_hypotheses: int = 20, use_llm: bool = True):
        self.max_hypotheses = max_hypotheses
        self.use_llm = use_llm
        self._hypothesis_counter = 0
        self._generation_stats = {
            "total_generated": 0,
            "spatial": 0,
            "transformation": 0,
            "color_logic": 0,
            "counting": 0,
            "composition": 0,
            "conditional": 0,
            "pattern": 0,
        }

    def generate(
        self, train_examples: list[dict], test_input: dict
    ) -> list[ProgramHypothesis]:
        """
        ولّد فرضيات لحل مهمة ARC-AGI.
        
        Strategy:
        1. Analyze structural differences between input/output
        2. Generate simple transformation hypotheses
        3. Generate compound hypotheses by composing simple ones
        4. Test each hypothesis against training examples
        5. Return ranked list of hypotheses
        """
        if not FLUID_ADVANCED_MODE:
            logger.debug("Fluid advanced mode disabled — returning empty hypotheses")
            return []

        start = time.time()
        hypotheses: list[ProgramHypothesis] = []

        # Step 1: Structural analysis
        analysis = self._analyze_structure(train_examples)

        # Step 2: Generate spatial hypotheses
        spatial_hyps = self._generate_spatial_hypotheses(analysis, train_examples)
        hypotheses.extend(spatial_hyps)

        # Step 3: Generate color logic hypotheses
        color_hyps = self._generate_color_hypotheses(analysis, train_examples)
        hypotheses.extend(color_hyps)

        # Step 4: Generate counting hypotheses
        count_hyps = self._generate_counting_hypotheses(analysis, train_examples)
        hypotheses.extend(count_hyps)

        # Step 5: Generate conditional hypotheses
        cond_hyps = self._generate_conditional_hypotheses(analysis, train_examples)
        hypotheses.extend(cond_hyps)

        # Step 6: Generate pattern hypotheses
        pattern_hyps = self._generate_pattern_hypotheses(analysis, train_examples)
        hypotheses.extend(pattern_hyps)

        # Step 7: Generate compositional hypotheses (from top simple ones)
        if len(hypotheses) >= 2:
            comp_hyps = self._generate_compositional_hypotheses(
                hypotheses[:5], train_examples
            )
            hypotheses.extend(comp_hyps)

        # Step 8: Test and score all hypotheses against training examples
        for hyp in hypotheses:
            hyp = self._test_hypothesis(hyp, train_examples)

        # Step 9: Sort by test score and return top N
        hypotheses.sort(key=lambda h: h.test_score, reverse=True)
        hypotheses = hypotheses[:self.max_hypotheses]

        # Update stats
        self._generation_stats["total_generated"] += len(hypotheses)
        for hyp in hypotheses:
            self._generation_stats[hyp.category.value] += 1

        elapsed = (time.time() - start) * 1000
        logger.info(
            f"Generated {len(hypotheses)} hypotheses in {elapsed:.0f}ms "
            f"(spatial={len(spatial_hyps)}, color={len(color_hyps)}, "
            f"count={len(count_hyps)}, cond={len(cond_hyps)}, "
            f"pattern={len(pattern_hyps)})"
        )

        return hypotheses

    # ═══════════════════════════════════════════════════════════════════════
    # Structural Analysis
    # ═══════════════════════════════════════════════════════════════════════

    @dataclass
    class StructuralAnalysis:
        """تحليل بنيوي لأمثلة التدريب"""
        same_dimensions: bool = False         # هل الأبعاد متطابقة؟
        input_sizes: list[tuple] = field(default_factory=list)
        output_sizes: list[tuple] = field(default_factory=list)
        color_changes: dict = field(default_factory=dict)     # تغييرات الألوان
        size_ratios: list[float] = field(default_factory=list)
        has_rotation: bool = False
        has_reflection: bool = False
        unique_input_colors: list[set] = field(default_factory=list)
        unique_output_colors: list[set] = field(default_factory=list)

    def _analyze_structure(self, examples: list[dict]) -> StructuralAnalysis:
        """حلّل البنية العامة لأمثلة التدريب"""
        analysis = self.StructuralAnalysis()

        for ex in examples:
            inp = ex.get("input", [])
            out = ex.get("output", [])

            in_h, in_w = len(inp), len(inp[0]) if inp else 0
            out_h, out_w = len(out), len(out[0]) if out else 0

            analysis.input_sizes.append((in_h, in_w))
            analysis.output_sizes.append((out_h, out_w))

            if in_h == out_h and in_w == out_w:
                analysis.same_dimensions = True and analysis.same_dimensions
            else:
                analysis.same_dimensions = False

            if in_h > 0 and in_w > 0:
                analysis.size_ratios.append((out_h * out_w) / (in_h * in_w))

            # Track colors
            in_colors = set()
            out_colors = set()
            for row in inp:
                in_colors.update(row)
            for row in out:
                out_colors.update(row)
            analysis.unique_input_colors.append(in_colors)
            analysis.unique_output_colors.append(out_colors)

        return analysis

    # ═══════════════════════════════════════════════════════════════════════
    # Hypothesis Generation Strategies
    # ═══════════════════════════════════════════════════════════════════════

    def _generate_spatial_hypotheses(
        self, analysis: StructuralAnalysis, examples: list[dict]
    ) -> list[ProgramHypothesis]:
        """ولّد فرضيات مكانية (تدوير، انعكاس، نقل)"""
        hypotheses = []

        # Rotation hypotheses
        for degrees in [90, 180, 270]:
            fn = self._make_rotation_fn(degrees)
            hyp = self._create_hypothesis(
                category=HypothesisCategory.SPATIAL,
                description=f"تدوير {degrees} درجة",
                transform_fn=fn,
                transform_code=f"lambda g: rotate(g, {degrees})",
                confidence=0.4,
                complexity=1,
            )
            hypotheses.append(hyp)

        # Reflection hypotheses
        for axis in ["horizontal", "vertical"]:
            fn = self._make_reflection_fn(axis)
            hyp = self._create_hypothesis(
                category=HypothesisCategory.SPATIAL,
                description=f"انعكاس {'أفقي' if axis == 'horizontal' else 'عمودي'}",
                transform_fn=fn,
                transform_code=f"lambda g: flip(g, '{axis}')",
                confidence=0.4,
                complexity=1,
            )
            hypotheses.append(hyp)

        # Transpose
        fn = self._make_transpose_fn()
        hypotheses.append(self._create_hypothesis(
            category=HypothesisCategory.SPATIAL,
            description="تبديل المصفوفة (transpose)",
            transform_fn=fn,
            transform_code="lambda g: transpose(g)",
            confidence=0.35,
            complexity=1,
        ))

        return hypotheses

    def _generate_color_hypotheses(
        self, analysis: StructuralAnalysis, examples: list[dict]
    ) -> list[ProgramHypothesis]:
        """ولّد فرضيات منطق الألوان"""
        hypotheses = []

        # Color mapping hypothesis
        mapping = self._extract_consistent_color_map(examples)
        if mapping:
            fn = self._make_color_map_fn(mapping)
            hypotheses.append(self._create_hypothesis(
                category=HypothesisCategory.COLOR_LOGIC,
                description=f"تعيين ألوان ثابت ({len(mapping)} لون)",
                transform_fn=fn,
                transform_code=f"lambda g: color_map(g, {mapping})",
                confidence=0.6,
                complexity=1,
            ))

        # Inversion hypothesis (0↔1 or all colors inverted)
        fn = self._make_inversion_fn()
        hypotheses.append(self._create_hypothesis(
            category=HypothesisCategory.COLOR_LOGIC,
            description="عكس الألوان (0↔1)",
            transform_fn=fn,
            transform_code="lambda g: invert(g)",
            confidence=0.3,
            complexity=1,
        ))

        # Color normalization — map to sorted indices
        fn = self._make_normalize_fn()
        hypotheses.append(self._create_hypothesis(
            category=HypothesisCategory.COLOR_LOGIC,
            description="تطبيع الألوان (ترتيب تصاعدي)",
            transform_fn=fn,
            transform_code="lambda g: normalize_colors(g)",
            confidence=0.25,
            complexity=1,
        ))

        return hypotheses

    def _generate_counting_hypotheses(
        self, analysis: StructuralAnalysis, examples: list[dict]
    ) -> list[ProgramHypothesis]:
        """ولّد فرضيات قائمة على العدّ"""
        hypotheses = []

        # Count-based size scaling
        if analysis.size_ratios:
            ratio = analysis.size_ratios[0]
            if ratio > 1.0:
                fn = self._make_repeat_fn(int(ratio))
                hypotheses.append(self._create_hypothesis(
                    category=HypothesisCategory.COUNTING,
                    description=f"تكرار النمط ×{int(ratio)}",
                    transform_fn=fn,
                    transform_code=f"lambda g: repeat(g, {int(ratio)})",
                    confidence=0.35,
                    complexity=2,
                ))

        # Count and replace: count occurrences of each color, map to new values
        fn = self._make_count_replace_fn()
        hypotheses.append(self._create_hypothesis(
            category=HypothesisCategory.COUNTING,
            description="عدّ واستبدال (قيمة الخلية = عدّ لونها)",
            transform_fn=fn,
            transform_code="lambda g: count_replace(g)",
            confidence=0.25,
            complexity=2,
        ))

        return hypotheses

    def _generate_conditional_hypotheses(
        self, analysis: StructuralAnalysis, examples: list[dict]
    ) -> list[ProgramHypothesis]:
        """ولّد فرضيات شرطية"""
        hypotheses = []

        # Even/odd conditional
        for condition in ["even", "odd"]:
            fn = self._make_conditional_fn(condition)
            hypotheses.append(self._create_hypothesis(
                category=HypothesisCategory.CONDITIONAL,
                description=f"تحويل شرطي ({'زوجي' if condition == 'even' else 'فردي'})",
                transform_fn=fn,
                transform_code=f"lambda g: conditional(g, '{condition}')",
                confidence=0.3,
                complexity=2,
            ))

        # Position-based conditional (top half vs bottom half)
        fn = self._make_position_conditional_fn()
        hypotheses.append(self._create_hypothesis(
            category=HypothesisCategory.CONDITIONAL,
            description="تحويل شرطي مكاني (نصف علوي vs سفلي)",
            transform_fn=fn,
            transform_code="lambda g: position_conditional(g)",
            confidence=0.25,
            complexity=2,
        ))

        return hypotheses

    def _generate_pattern_hypotheses(
        self, analysis: StructuralAnalysis, examples: list[dict]
    ) -> list[ProgramHypothesis]:
        """ولّد فرضيات الأنماط"""
        hypotheses = []

        # Symmetry completion
        for axis in ["vertical", "horizontal"]:
            fn = self._make_symmetry_fn(axis)
            hypotheses.append(self._create_hypothesis(
                category=HypothesisCategory.PATTERN,
                description=f"استكمال تماثل {'عمودي' if axis == 'vertical' else 'أفقي'}",
                transform_fn=fn,
                transform_code=f"lambda g: symmetry(g, '{axis}')",
                confidence=0.35,
                complexity=1,
            ))

        # Pattern repeat (tile)
        fn = self._make_tiling_fn()
        hypotheses.append(self._create_hypothesis(
            category=HypothesisCategory.PATTERN,
            description="تبليط النمط (tiling)",
            transform_fn=fn,
            transform_code="lambda g: tile(g)",
            confidence=0.3,
            complexity=2,
        ))

        return hypotheses

    def _generate_compositional_hypotheses(
        self, top_hypotheses: list[ProgramHypothesis], examples: list[dict]
    ) -> list[ProgramHypothesis]:
        """ولّد فرضيات مركبة من أفضل الفرضيات البسيطة"""
        hypotheses = []

        # Try composing top 3 hypotheses pairwise
        for i in range(min(3, len(top_hypotheses))):
            for j in range(i + 1, min(3, len(top_hypotheses))):
                h1 = top_hypotheses[i]
                h2 = top_hypotheses[j]

                if h1.transform_fn and h2.transform_fn:
                    composed_fn = self._compose_functions(h1.transform_fn, h2.transform_fn)
                    hypotheses.append(self._create_hypothesis(
                        category=HypothesisCategory.COMPOSITION,
                        description=f"تركيب: {h1.description} ثم {h2.description}",
                        transform_fn=composed_fn,
                        transform_code=f"lambda g: {h2.transform_code.strip('lambda g: ')}({h1.transform_code.strip('lambda g: ')}(g))",
                        confidence=min(h1.confidence, h2.confidence) * 0.9,
                        complexity=h1.complexity + h2.complexity,
                    ))

        return hypotheses

    # ═══════════════════════════════════════════════════════════════════════
    # Testing
    # ═══════════════════════════════════════════════════════════════════════

    def _test_hypothesis(
        self, hyp: ProgramHypothesis, examples: list[dict]
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
                score = self._grid_similarity(result, expected)
                scores.append(score)
            except Exception as e:
                logger.debug(f"Hypothesis {hyp.hypothesis_id} failed: {e}")
                scores.append(0.0)

        hyp.tested = True
        hyp.test_score = sum(scores) / len(scores) if scores else 0.0

        # Update confidence based on test results
        hyp.confidence = hyp.confidence * 0.4 + hyp.test_score * 0.6

        return hyp

    # ═══════════════════════════════════════════════════════════════════════
    # Transform Function Builders
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _make_rotation_fn(degrees: int) -> Callable:
        def rotate(grid):
            if not grid:
                return grid
            rows, cols = len(grid), len(grid[0])
            if degrees == 90:
                return [[grid[rows - 1 - r][c] for r in range(rows)] for c in range(cols)]
            elif degrees == 180:
                return [row[::-1] for row in grid[::-1]]
            elif degrees == 270:
                return [[grid[r][cols - 1 - c] for r in range(rows)] for c in range(cols)]
            return grid
        return rotate

    @staticmethod
    def _make_reflection_fn(axis: str) -> Callable:
        def reflect(grid):
            if axis == "horizontal":
                return grid[::-1]
            elif axis == "vertical":
                return [row[::-1] for row in grid]
            return grid
        return reflect

    @staticmethod
    def _make_transpose_fn() -> Callable:
        def transpose(grid):
            if not grid:
                return grid
            rows, cols = len(grid), len(grid[0])
            return [[grid[r][c] for r in range(rows)] for c in range(cols)]
        return transpose

    @staticmethod
    def _make_color_map_fn(mapping: dict) -> Callable:
        def color_map(grid):
            return [[mapping.get(cell, cell) for cell in row] for row in grid]
        return color_map

    @staticmethod
    def _make_inversion_fn() -> Callable:
        def invert(grid):
            return [[1 if cell == 0 else 0 if cell == 1 else cell for cell in row] for row in grid]
        return invert

    @staticmethod
    def _make_normalize_fn() -> Callable:
        def normalize(grid):
            if not grid:
                return grid
            all_colors = set()
            for row in grid:
                all_colors.update(row)
            sorted_colors = sorted(all_colors)
            mapping = {c: i for i, c in enumerate(sorted_colors)}
            return [[mapping[cell] for cell in row] for row in grid]
        return normalize

    @staticmethod
    def _make_repeat_fn(times: int) -> Callable:
        def repeat(grid):
            return [row[:] for row in grid for _ in range(times)]
        return repeat

    @staticmethod
    def _make_count_replace_fn() -> Callable:
        def count_replace(grid):
            if not grid:
                return grid
            from collections import Counter
            counts = Counter()
            for row in grid:
                counts.update(row)
            return [[counts[cell] for cell in row] for row in grid]
        return count_replace

    @staticmethod
    def _make_conditional_fn(condition: str) -> Callable:
        def conditional(grid):
            result = [row[:] for row in grid]
            for i, row in enumerate(result):
                for j, cell in enumerate(row):
                    if condition == "even" and cell % 2 == 0:
                        result[i][j] = 0
                    elif condition == "odd" and cell % 2 == 1:
                        result[i][j] = cell
                    else:
                        result[i][j] = 0
            return result
        return conditional

    @staticmethod
    def _make_position_conditional_fn() -> Callable:
        def position_conditional(grid):
            if not grid:
                return grid
            mid = len(grid) // 2
            result = [row[:] for row in grid]
            for i, row in enumerate(result):
                if i >= mid:
                    result[i] = [0 for _ in row]
            return result
        return position_conditional

    @staticmethod
    def _make_symmetry_fn(axis: str) -> Callable:
        def symmetry(grid):
            result = [row[:] for row in grid]
            if axis == "vertical" and result:
                mid = len(result[0]) // 2 if result else 0
                for row in result:
                    for i in range(mid):
                        mirror_idx = len(row) - 1 - i
                        if 0 <= mirror_idx < len(row):
                            row[mirror_idx] = row[i]
            return result
        return symmetry

    @staticmethod
    def _make_tiling_fn() -> Callable:
        def tile(grid):
            if not grid:
                return grid
            return [row[:] + row[:] for row in grid]
        return tile

    @staticmethod
    def _compose_functions(fn1: Callable, fn2: Callable) -> Callable:
        def composed(grid):
            return fn2(fn1(grid))
        return composed

    # ═══════════════════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════════════════

    def _create_hypothesis(
        self,
        category: HypothesisCategory,
        description: str,
        transform_fn: Callable,
        transform_code: str,
        confidence: float,
        complexity: int,
    ) -> ProgramHypothesis:
        self._hypothesis_counter += 1
        return ProgramHypothesis(
            hypothesis_id=f"hyp_v10_{self._hypothesis_counter:04d}",
            category=category,
            description=description,
            transform_fn=transform_fn,
            transform_code=transform_code,
            confidence=confidence,
            complexity=complexity,
        )

    @staticmethod
    def _extract_consistent_color_map(examples: list[dict]) -> Optional[dict]:
        """استخلاص تعيين ألوان ثابت من أمثلة التدريب"""
        mapping = {}
        for ex in examples:
            inp = ex.get("input", [])
            out = ex.get("output", [])
            if len(inp) == len(out):
                for in_row, out_row in zip(inp, out):
                    if len(in_row) == len(out_row):
                        for i_val, o_val in zip(in_row, out_row):
                            if i_val in mapping and mapping[i_val] != o_val:
                                return None  # Inconsistent
                            mapping[i_val] = o_val
        return mapping if mapping else None

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
        """إحصائيات المولّد"""
        return {
            "total_generated": self._generation_stats["total_generated"],
            "by_category": {k: v for k, v in self._generation_stats.items() if k != "total_generated"},
        }
