"""
BABSHARQII v10.0 — Pattern Discovery
مكتشف الأنماط — يكتشف الأنماط المخفية من الأمثلة القليلة باستخدام مقارنة بنيوية

Discovers hidden patterns in ARC-AGI tasks by analyzing structural
relationships between input-output pairs. Goes beyond simple rule
extraction to discover:
1. Spatial relationships (adjacency, containment, alignment)
2. Object-level transformations (move, resize, color-change)
3. Relational patterns (symmetry, proportion, periodicity)

Target: Pattern discovery accuracy > 80% on 10 medium-difficulty ARC tasks

Feature Flag: MAMOUN_FLUID_ADVANCED_MODE (default: false)
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any

logger = logging.getLogger(__name__)

FLUID_ADVANCED_MODE: bool = os.environ.get(
    "MAMOUN_FLUID_ADVANCED_MODE", "false"
).lower() in ("true", "1", "yes")


class PatternType(Enum):
    """أنماط مكتشفة"""
    SPATIAL_RELATION = "spatial_relation"    # علاقة مكانية
    OBJECT_TRANSFORM = "object_transform"    # تحويل كائن
    SIZE_PROPORTION = "size_proportion"      # نسبة حجم
    COLOR_GRADIENT = "color_gradient"        # تدرج لوني
    SYMMETRY = "symmetry"                    # تماثل
    PERIODICITY = "periodicity"              # دورية
    CONTAINMENT = "containment"              # احتواء
    ADJACENCY = "adjacency"                  # تجاور
    ALIGNMENT = "alignment"                  # محاذاة


@dataclass
class DiscoveredPattern:
    """نمط مكتشف"""
    pattern_id: str = ""
    pattern_type: PatternType = PatternType.SPATIAL_RELATION
    description: str = ""                  # وصف بالعربية
    confidence: float = 0.0                # ثقة الاكتشاف
    consistency: float = 0.0               # اتساق عبر أمثلة التدريب
    evidence_count: int = 0                # عدد الأدلة الداعمة
    details: dict = field(default_factory=dict)  # تفاصيل إضافية

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type.value,
            "description": self.description,
            "confidence": round(self.confidence, 4),
            "consistency": round(self.consistency, 4),
            "evidence_count": self.evidence_count,
            "details": self.details,
        }


@dataclass
class ObjectInfo:
    """معلومات عن كائن في الشبكة"""
    color: int = 0
    positions: list[tuple] = field(default_factory=list)
    size: int = 0
    bbox: tuple = (0, 0, 0, 0)  # min_row, min_col, max_row, max_col


class PatternDiscovery:
    """
    مكتشف الأنماط
    
    Analyzes ARC task examples to discover hidden patterns using:
    1. Object extraction and tracking between input/output
    2. Spatial relationship analysis
    3. Structural comparison (what changed, what stayed the same)
    4. Relational pattern detection
    
    Target: Accuracy > 80% on medium-difficulty ARC tasks
    """

    def __init__(self, min_confidence: float = 0.6):
        self.min_confidence = min_confidence
        self._discovery_count = 0

    def discover(
        self, train_examples: list[dict]
    ) -> list[DiscoveredPattern]:
        """
        اكتشف الأنماط من أمثلة التدريب.
        
        Analyzes all input-output pairs to find consistent patterns
        that explain the transformation.
        """
        if not FLUID_ADVANCED_MODE:
            return []

        if not train_examples:
            return []

        patterns: list[DiscoveredPattern] = []

        # Step 1: Discover size change patterns
        size_patterns = self._discover_size_patterns(train_examples)
        patterns.extend(size_patterns)

        # Step 2: Discover color patterns
        color_patterns = self._discover_color_patterns(train_examples)
        patterns.extend(color_patterns)

        # Step 3: Discover spatial patterns
        spatial_patterns = self._discover_spatial_patterns(train_examples)
        patterns.extend(spatial_patterns)

        # Step 4: Discover object-level patterns
        object_patterns = self._discover_object_patterns(train_examples)
        patterns.extend(object_patterns)

        # Step 5: Discover symmetry patterns
        symmetry_patterns = self._discover_symmetry_patterns(train_examples)
        patterns.extend(symmetry_patterns)

        # Step 6: Filter by confidence
        patterns = [p for p in patterns if p.confidence >= self.min_confidence]

        # Sort by confidence
        patterns.sort(key=lambda p: p.confidence, reverse=True)

        self._discovery_count += len(patterns)
        logger.info(
            f"Discovered {len(patterns)} patterns "
            f"(size={len(size_patterns)}, color={len(color_patterns)}, "
            f"spatial={len(spatial_patterns)}, object={len(object_patterns)}, "
            f"symmetry={len(symmetry_patterns)})"
        )

        return patterns

    # ═══════════════════════════════════════════════════════════════════════
    # Size Pattern Discovery
    # ═══════════════════════════════════════════════════════════════════════

    def _discover_size_patterns(
        self, examples: list[dict]
    ) -> list[DiscoveredPattern]:
        """اكتشف أنماط تغير الحجم"""
        patterns = []

        # Check for consistent size ratio
        ratios = []
        for ex in examples:
            inp = ex.get("input", [])
            out = ex.get("output", [])
            in_size = len(inp) * len(inp[0]) if inp and inp[0] else 0
            out_size = len(out) * len(out[0]) if out and out[0] else 0
            if in_size > 0:
                ratios.append(out_size / in_size)

        if ratios and all(abs(r - ratios[0]) < 0.01 for r in ratios):
            ratio = ratios[0]
            if ratio != 1.0:
                self._discovery_count += 1
                patterns.append(DiscoveredPattern(
                    pattern_id=f"pat_size_{self._discovery_count}",
                    pattern_type=PatternType.SIZE_PROPORTION,
                    description=f"نسبة حجم ثابت: {ratio:.1f}x",
                    confidence=0.9,
                    consistency=1.0,
                    evidence_count=len(examples),
                    details={"ratio": ratio, "consistent": True},
                ))

        # Check for dimension swapping (transpose)
        all_transposed = True
        for ex in examples:
            inp = ex.get("input", [])
            out = ex.get("output", [])
            in_h, in_w = len(inp), len(inp[0]) if inp else 0
            out_h, out_w = len(out), len(out[0]) if out else 0
            if in_h != out_w or in_w != out_h:
                all_transposed = False
                break

        if all_transposed and len(examples) > 0:
            self._discovery_count += 1
            patterns.append(DiscoveredPattern(
                pattern_id=f"pat_size_{self._discovery_count}",
                pattern_type=PatternType.SIZE_PROPORTION,
                description="تبديل الأبعاد (transpose)",
                confidence=0.85,
                consistency=1.0,
                evidence_count=len(examples),
                details={"type": "transpose"},
            ))

        return patterns

    # ═══════════════════════════════════════════════════════════════════════
    # Color Pattern Discovery
    # ═══════════════════════════════════════════════════════════════════════

    def _discover_color_patterns(
        self, examples: list[dict]
    ) -> list[DiscoveredPattern]:
        """اكتشف أنماط الألوان"""
        patterns = []

        # Check for consistent color mapping
        mapping = {}
        consistent = True
        for ex in examples:
            inp = ex.get("input", [])
            out = ex.get("output", [])
            for in_row, out_row in zip(inp, out):
                for i_val, o_val in zip(in_row, out_row):
                    if i_val in mapping:
                        if mapping[i_val] != o_val:
                            consistent = False
                            break
                    else:
                        mapping[i_val] = o_val
                if not consistent:
                    break
            if not consistent:
                break

        if consistent and mapping:
            self._discovery_count += 1
            patterns.append(DiscoveredPattern(
                pattern_id=f"pat_color_{self._discovery_count}",
                pattern_type=PatternType.COLOR_GRADIENT,
                description=f"تعيين ألوان ثابت ({len(mapping)} لون)",
                confidence=0.85,
                consistency=1.0,
                evidence_count=len(examples),
                details={"mapping": mapping},
            ))

        # Check for color reduction (fewer colors in output)
        reductions = []
        for ex in examples:
            inp = ex.get("input", [])
            out = ex.get("output", [])
            in_colors = len(set(c for row in inp for c in row)) if inp else 0
            out_colors = len(set(c for row in out for c in row)) if out else 0
            if in_colors > 0:
                reductions.append(out_colors < in_colors)

        if reductions and all(reductions):
            self._discovery_count += 1
            patterns.append(DiscoveredPattern(
                pattern_id=f"pat_color_{self._discovery_count}",
                pattern_type=PatternType.COLOR_GRADIENT,
                description="تقليل الألوان (ألوان أقل في المخرج)",
                confidence=0.7,
                consistency=1.0,
                evidence_count=len(examples),
                details={"type": "color_reduction"},
            ))

        return patterns

    # ═══════════════════════════════════════════════════════════════════════
    # Spatial Pattern Discovery
    # ═══════════════════════════════════════════════════════════════════════

    def _discover_spatial_patterns(
        self, examples: list[dict]
    ) -> list[DiscoveredPattern]:
        """اكتشف أنماط مكانية (تجاور، احتواء، محاذاة)"""
        patterns = []

        # Check adjacency patterns (neighboring cells)
        for ex in examples:
            inp = ex.get("input", [])
            if not inp:
                continue
            adj_pairs = self._find_adjacent_pairs(inp)
            if adj_pairs:
                self._discovery_count += 1
                patterns.append(DiscoveredPattern(
                    pattern_id=f"pat_spatial_{self._discovery_count}",
                    pattern_type=PatternType.ADJACENCY,
                    description=f"أزواج متجاورة ({len(adj_pairs)} زوج)",
                    confidence=0.5,
                    consistency=0.5,
                    evidence_count=1,
                    details={"adjacent_pairs": adj_pairs[:10]},
                ))

        # Check alignment (cells aligned in rows/columns)
        for ex in examples:
            inp = ex.get("input", [])
            if not inp:
                continue
            alignment = self._check_alignment(inp)
            if alignment:
                self._discovery_count += 1
                patterns.append(DiscoveredPattern(
                    pattern_id=f"pat_spatial_{self._discovery_count}",
                    pattern_type=PatternType.ALIGNMENT,
                    description=f"محاذاة {alignment}",
                    confidence=0.5,
                    consistency=0.5,
                    evidence_count=1,
                    details={"alignment_type": alignment},
                ))

        return patterns

    # ═══════════════════════════════════════════════════════════════════════
    # Object Pattern Discovery
    # ═══════════════════════════════════════════════════════════════════════

    def _discover_object_patterns(
        self, examples: list[dict]
    ) -> list[DiscoveredPattern]:
        """اكتشف أنماط على مستوى الكائنات"""
        patterns = []

        # Extract objects from each example and track changes
        for i, ex in enumerate(examples):
            inp = ex.get("input", [])
            out = ex.get("output", [])

            in_objects = self._extract_objects(inp)
            out_objects = self._extract_objects(out)

            # Compare object counts
            if len(in_objects) != len(out_objects):
                self._discovery_count += 1
                patterns.append(DiscoveredPattern(
                    pattern_id=f"pat_obj_{self._discovery_count}",
                    pattern_type=PatternType.OBJECT_TRANSFORM,
                    description=f"تغير عدد الكائنات: {len(in_objects)} → {len(out_objects)}",
                    confidence=0.6,
                    consistency=0.5,
                    evidence_count=1,
                    details={
                        "input_objects": len(in_objects),
                        "output_objects": len(out_objects),
                    },
                ))

            # Track object movement
            for in_obj in in_objects:
                for out_obj in out_objects:
                    if in_obj.color == out_obj.color:
                        movement = self._compute_movement(in_obj, out_obj)
                        if movement != (0, 0):
                            self._discovery_count += 1
                            patterns.append(DiscoveredPattern(
                                pattern_id=f"pat_obj_{self._discovery_count}",
                                pattern_type=PatternType.OBJECT_TRANSFORM,
                                description=f"حركة كائن (لون {in_obj.color}): إزاحة ({movement[0]}, {movement[1]})",
                                confidence=0.55,
                                consistency=0.5,
                                evidence_count=1,
                                details={
                                    "color": in_obj.color,
                                    "delta_row": movement[0],
                                    "delta_col": movement[1],
                                },
                            ))

        return patterns

    # ═══════════════════════════════════════════════════════════════════════
    # Symmetry Pattern Discovery
    # ═══════════════════════════════════════════════════════════════════════

    def _discover_symmetry_patterns(
        self, examples: list[dict]
    ) -> list[DiscoveredPattern]:
        """اكتشف أنماط التماثل"""
        patterns = []

        # Check vertical symmetry
        v_sym_count = 0
        h_sym_count = 0
        for ex in examples:
            out = ex.get("output", [])
            if self._is_vertically_symmetric(out):
                v_sym_count += 1
            if self._is_horizontally_symmetric(out):
                h_sym_count += 1

        if v_sym_count == len(examples) and examples:
            self._discovery_count += 1
            patterns.append(DiscoveredPattern(
                pattern_id=f"pat_sym_{self._discovery_count}",
                pattern_type=PatternType.SYMMETRY,
                description="تماثل عمودي في جميع المخرجات",
                confidence=0.8,
                consistency=1.0,
                evidence_count=len(examples),
                details={"axis": "vertical"},
            ))

        if h_sym_count == len(examples) and examples:
            self._discovery_count += 1
            patterns.append(DiscoveredPattern(
                pattern_id=f"pat_sym_{self._discovery_count}",
                pattern_type=PatternType.SYMMETRY,
                description="تماثل أفقي في جميع المخرجات",
                confidence=0.8,
                consistency=1.0,
                evidence_count=len(examples),
                details={"axis": "horizontal"},
            ))

        return patterns

    # ═══════════════════════════════════════════════════════════════════════
    # Object Extraction
    # ═══════════════════════════════════════════════════════════════════════

    def _extract_objects(self, grid: list) -> list[ObjectInfo]:
        """استخرج الكائنات من شبكة (مجموعات متصلة من نفس اللون)"""
        if not grid:
            return []

        objects = []
        visited = set()
        rows, cols = len(grid), len(grid[0])

        def bfs(start_r, start_c, color):
            positions = []
            queue = [(start_r, start_c)]
            while queue:
                r, c = queue.pop(0)
                if (r, c) in visited:
                    continue
                if r < 0 or r >= rows or c < 0 or c >= cols:
                    continue
                if grid[r][c] != color:
                    continue
                visited.add((r, c))
                positions.append((r, c))
                queue.extend([(r-1, c), (r+1, c), (r, c-1), (r, c+1)])
            return positions

        for r in range(rows):
            for c in range(cols):
                if (r, c) not in visited and grid[r][c] != 0:
                    positions = bfs(r, c, grid[r][c])
                    if positions:
                        min_r = min(p[0] for p in positions)
                        max_r = max(p[0] for p in positions)
                        min_c = min(p[1] for p in positions)
                        max_c = max(p[1] for p in positions)
                        objects.append(ObjectInfo(
                            color=grid[r][c],
                            positions=positions,
                            size=len(positions),
                            bbox=(min_r, min_c, max_r, max_c),
                        ))

        return objects

    # ═══════════════════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _find_adjacent_pairs(grid: list) -> list[tuple]:
        """ابحث عن أزواج قيم متجاورة"""
        pairs = set()
        for r, row in enumerate(grid):
            for c, val in enumerate(row):
                # Right neighbor
                if c + 1 < len(row):
                    pairs.add((val, row[c + 1]))
                # Down neighbor
                if r + 1 < len(grid):
                    pairs.add((val, grid[r + 1][c]))
        return list(pairs)

    @staticmethod
    def _check_alignment(grid: list) -> Optional[str]:
        """تحقق من محاذاة الخلايا غير الصفرية"""
        non_zero_positions = []
        for r, row in enumerate(grid):
            for c, val in enumerate(row):
                if val != 0:
                    non_zero_positions.append((r, c))

        if not non_zero_positions:
            return None

        # Check row alignment
        rows = set(p[0] for p in non_zero_positions)
        if len(rows) == 1:
            return "row"

        # Check column alignment
        cols = set(p[1] for p in non_zero_positions)
        if len(cols) == 1:
            return "column"

        # Check diagonal
        diag = set(p[0] - p[1] for p in non_zero_positions)
        if len(diag) == 1:
            return "diagonal"

        return None

    @staticmethod
    def _compute_movement(obj_a: ObjectInfo, obj_b: ObjectInfo) -> tuple:
        """احسب إزاحة حركة الكائن"""
        if not obj_a.positions or not obj_b.positions:
            return (0, 0)
        a_center_r = sum(p[0] for p in obj_a.positions) / len(obj_a.positions)
        a_center_c = sum(p[1] for p in obj_a.positions) / len(obj_a.positions)
        b_center_r = sum(p[0] for p in obj_b.positions) / len(obj_b.positions)
        b_center_c = sum(p[1] for p in obj_b.positions) / len(obj_b.positions)
        return (round(b_center_r - a_center_r), round(b_center_c - a_center_c))

    @staticmethod
    def _is_vertically_symmetric(grid: list) -> bool:
        """تحقق من التماثل العمودي"""
        if not grid:
            return True
        for row in grid:
            if row != row[::-1]:
                return False
        return True

    @staticmethod
    def _is_horizontally_symmetric(grid: list) -> bool:
        """تحقق من التماثل الأفقي"""
        if not grid:
            return True
        return grid == grid[::-1]

    @property
    def stats(self) -> dict:
        """إحصائيات المكتشف"""
        return {"total_patterns_discovered": self._discovery_count}
