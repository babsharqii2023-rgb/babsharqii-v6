"""
BABSHARQII v40.0 — Constraint-Aware Planning Engine
محرك التخطيط الواعي بالقيود — يُحلّل الأهداف مع القيود ويصمّم خطط تنفيذ متعددة

Inspired by ROI-Reasoning and constraint satisfaction research.
Generates optimistic / realistic / pessimistic plan variants,
validates them against all constraints, and suggests relaxations
when no valid plan exists.

Feature Flag: MAMOUN_CONSTRAINT_PLANNING (default: false)
"""

import os
import time
import uuid
import logging
import threading
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)

# ── Feature Flag ────────────────────────────────────────────────────
CONSTRAINT_PLANNING_ENABLED = os.getenv(
    "MAMOUN_CONSTRAINT_PLANNING", "false"
).lower() in ("true", "1", "yes")


# ═══════════════════════════════════════════════════════════════════
#  Data Classes — فئات البيانات
# ═══════════════════════════════════════════════════════════════════

class ConstraintType(Enum):
    """أنواع القيود — Constraint type categories."""
    BUDGET = "budget"       # قيود الميزانية
    TIME = "time"           # قيود الوقت
    COMPUTE = "compute"     # قيود الحوسبة
    LEGAL = "legal"         # قيود قانونية
    QUALITY = "quality"     # قيود الجودة


class ConstraintOperator(Enum):
    """عمليات المقارنة — Comparison operators for constraints."""
    LTE = "lte"     # أقل من أو يساوي
    GTE = "gte"     # أكبر من أو يساوي
    EQ = "eq"       # يساوي
    NEQ = "neq"     # لا يساوي
    IN = "in"       # ضمن مجموعة


class PlanVariant(Enum):
    """متغيرات الخطة — Plan optimism levels."""
    OPTIMISTIC = "optimistic"       # متفائل
    REALISTIC = "realistic"         # واقعي
    PESSIMISTIC = "pessimistic"     # متشائم


@dataclass
class Constraint:
    """
    قيد واحد — A single constraint definition.
    """
    constraint_id: str = ""
    name: str = ""
    name_ar: str = ""
    constraint_type: str = "budget"  # ConstraintType value
    operator: str = "lte"            # ConstraintOperator value
    value: float = 0.0
    unit: str = ""
    is_hard: bool = True             # Hard constraints cannot be relaxed
    priority: int = 5                # 1 = highest, 10 = lowest
    description: str = ""
    description_ar: str = ""
    is_active: bool = True

    def __post_init__(self):
        if not self.constraint_id:
            self.constraint_id = f"cstr_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return asdict(self)

    def evaluate(self, actual_value: float) -> bool:
        """
        تقييم القيد مقابل قيمة فعلية — Evaluate constraint against actual value.
        """
        op = self.operator
        if op == ConstraintOperator.LTE.value:
            return actual_value <= self.value
        elif op == ConstraintOperator.GTE.value:
            return actual_value >= self.value
        elif op == ConstraintOperator.EQ.value:
            return abs(actual_value - self.value) < 1e-9
        elif op == ConstraintOperator.NEQ.value:
            return abs(actual_value - self.value) >= 1e-9
        elif op == ConstraintOperator.IN.value:
            # For IN, value represents an upper bound; actual must be within [0, value]
            return 0 <= actual_value <= self.value
        return True


@dataclass
class PlanStep:
    """
    خطوة تنفيذ — A single step in an execution plan.
    """
    step_id: str = ""
    description: str = ""
    description_ar: str = ""
    action: str = ""
    cost: float = 0.0
    duration: float = 0.0            # seconds
    resources_needed: dict = field(default_factory=dict)
    dependencies: list = field(default_factory=list)   # list of step_id

    def __post_init__(self):
        if not self.step_id:
            self.step_id = f"step_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PlanningGoal:
    """
    هدف تخطيط — A goal to be planned for.
    """
    goal_id: str = ""
    description: str = ""
    description_ar: str = ""
    target_outcome: dict = field(default_factory=dict)
    estimated_cost: float = 0.0
    estimated_duration: float = 0.0   # seconds
    required_resources: dict = field(default_factory=dict)
    priority: int = 5                 # 1 = highest

    def __post_init__(self):
        if not self.goal_id:
            self.goal_id = f"goal_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExecutionPlan:
    """
    خطة تنفيذ — A complete execution plan variant.
    """
    plan_id: str = ""
    goal_id: str = ""
    variant: str = "realistic"        # PlanVariant value
    steps: list = field(default_factory=list)   # list[PlanStep]
    total_cost: float = 0.0
    total_duration: float = 0.0
    resource_usage: dict = field(default_factory=dict)
    constraint_compliance: dict = field(default_factory=dict)  # constraint_id -> bool
    risk_assessment: str = ""
    estimated_success_rate: float = 0.0

    def __post_init__(self):
        if not self.plan_id:
            self.plan_id = f"plan_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        result = {
            "plan_id": self.plan_id,
            "goal_id": self.goal_id,
            "variant": self.variant,
            "steps": [s.to_dict() if hasattr(s, "to_dict") else s for s in self.steps],
            "total_cost": self.total_cost,
            "total_duration": self.total_duration,
            "resource_usage": self.resource_usage,
            "constraint_compliance": self.constraint_compliance,
            "risk_assessment": self.risk_assessment,
            "estimated_success_rate": round(self.estimated_success_rate, 4),
        }
        return result


@dataclass
class PlanningResult:
    """
    نتيجة التخطيط — Result of planning for a goal.
    """
    goal_id: str = ""
    plans: dict = field(default_factory=dict)     # variant_name -> ExecutionPlan
    recommended_plan: str = ""                     # plan_id of recommended plan
    feasibility_score: float = 0.0
    warnings: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "plans": {k: (v.to_dict() if hasattr(v, "to_dict") else v)
                      for k, v in self.plans.items()},
            "recommended_plan": self.recommended_plan,
            "feasibility_score": round(self.feasibility_score, 4),
            "warnings": self.warnings,
        }


@dataclass
class ValidationResult:
    """
    نتيجة التحقق — Validation result for a plan against constraints.
    """
    plan_id: str = ""
    is_valid: bool = True
    violations: list = field(default_factory=list)   # list[dict]
    warnings: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RelaxationSuggestion:
    """
    اقتراح تخفيف القيد — Suggestion to relax a constraint.
    """
    constraint_id: str = ""
    current_value: float = 0.0
    suggested_value: float = 0.0
    impact_description: str = ""
    impact_description_ar: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FeasibilityReport:
    """
    تقرير الجدوى — Feasibility assessment for a goal.
    """
    goal_id: str = ""
    is_feasible: bool = True
    feasibility_score: float = 0.0
    blocking_constraints: list = field(default_factory=list)   # constraint_ids
    suggested_relaxations: list = field(default_factory=list)  # RelaxationSuggestion

    def to_dict(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "is_feasible": self.is_feasible,
            "feasibility_score": round(self.feasibility_score, 4),
            "blocking_constraints": self.blocking_constraints,
            "suggested_relaxations": [
                r.to_dict() if hasattr(r, "to_dict") else r
                for r in self.suggested_relaxations
            ],
        }


# ═══════════════════════════════════════════════════════════════════
#  Constraint Engine — محرك القيود
# ═══════════════════════════════════════════════════════════════════

class ConstraintEngine:
    """
    محرك التخطيط الواعي بالقيود — Constraint-Aware Planning Engine.

    Analyzes goals with constraints (budget, time, compute, legal, quality)
    and designs multi-option execution plans.  Generates three plan variants
    (optimistic, realistic, pessimistic), validates them, and suggests
    relaxations when no valid plan exists.

    Usage:
        engine = ConstraintEngine()
        cid = engine.add_constraint(Constraint(
            name="Max Budget", name_ar="الحد الأقصى للميزانية",
            constraint_type=ConstraintType.BUDGET.value,
            operator=ConstraintOperator.LTE.value,
            value=100.0, unit="USD", is_hard=True, priority=1,
        ))
        result = engine.plan(PlanningGoal(
            description="Deploy model", estimated_cost=80.0,
        ))
    """

    def __init__(self):
        self._constraints: dict[str, Constraint] = {}
        self._planning_history: list[PlanningResult] = []
        self._lock = threading.Lock()
        self._plan_counter = 0
        self._active = True

        # Variant multipliers — معاملات المتغيرات
        # Optimistic assumes best-case (lower cost/time), pessimistic worst-case
        self._variant_multipliers = {
            PlanVariant.OPTIMISTIC.value: {
                "cost": 0.7, "duration": 0.75, "success": 0.95,
                "risk": "منخفض — Low risk: assumptions hold, no blockers",
            },
            PlanVariant.REALISTIC.value: {
                "cost": 1.0, "duration": 1.0, "success": 0.75,
                "risk": "متوسط — Medium risk: some uncertainty expected",
            },
            PlanVariant.PESSIMISTIC.value: {
                "cost": 1.5, "duration": 1.6, "success": 0.45,
                "risk": "مرتفع — High risk: likely overruns and blockers",
            },
        }

    # ── Constraint Management — إدارة القيود ─────────────────────

    def add_constraint(self, constraint: Constraint) -> str:
        """
        إضافة قيد جديد — Add a new constraint to the engine.

        Returns:
            constraint_id of the added constraint.
        """
        with self._lock:
            if not constraint.constraint_id:
                constraint.constraint_id = f"cstr_{uuid.uuid4().hex[:8]}"
            self._constraints[constraint.constraint_id] = constraint
            logger.info(
                f"ConstraintEngine: Added constraint '{constraint.name}' "
                f"({constraint.constraint_type}) id={constraint.constraint_id}"
            )
            return constraint.constraint_id

    def remove_constraint(self, constraint_id: str) -> bool:
        """
        إزالة قيد — Remove a constraint by ID.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            removed = self._constraints.pop(constraint_id, None)
            if removed:
                logger.info(
                    f"ConstraintEngine: Removed constraint '{removed.name}' "
                    f"id={constraint_id}"
                )
                return True
            return False

    def get_constraints(self, constraint_type: str = None) -> list:
        """
        الحصول على القيود — Get constraints, optionally filtered by type.

        Args:
            constraint_type: One of ConstraintType values, or None for all.

        Returns:
            List of matching Constraint objects.
        """
        with self._lock:
            constraints = list(self._constraints.values())
        if constraint_type is not None:
            constraints = [c for c in constraints if c.constraint_type == constraint_type]
        # Return only active constraints by default
        return [c for c in constraints if c.is_active]

    # ── Planning — التخطيط ───────────────────────────────────────

    def plan(self, goal: PlanningGoal) -> PlanningResult:
        """
        تخطيط الهدف — Generate multi-variant execution plans for a goal.

        Creates optimistic, realistic, and pessimistic plan variants,
        validates each against all active constraints, and recommends
        the best feasible plan.

        Args:
            goal: The planning goal to generate plans for.

        Returns:
            PlanningResult with all plan variants and a recommendation.
        """
        if not CONSTRAINT_PLANNING_ENABLED:
            logger.warning("ConstraintEngine: Planning disabled by feature flag")
            return PlanningResult(
                goal_id=goal.goal_id,
                warnings=["Planning disabled — MAMOUN_CONSTRAINT_PLANNING not set"],
            )

        warnings = []
        plans: dict[str, ExecutionPlan] = {}

        # Gather active constraints — جمع القيود النشطة
        active_constraints = self.get_constraints()

        # Generate each variant — إنشاء كل متغير
        for variant_name, multipliers in self._variant_multipliers.items():
            plan = self._generate_variant(goal, variant_name, multipliers)
            plans[variant_name] = plan

        # Validate each variant — التحقق من كل متغير
        best_plan_id = ""
        best_score = -1.0

        for variant_name, plan in plans.items():
            validation = self.validate_plan(plan, active_constraints)
            plan.constraint_compliance = {
                v["constraint_id"]: not v["violated"]
                for v in validation.violations
            }
            # Add extra compliance entries for constraints not in violations
            for c in active_constraints:
                if c.constraint_id not in plan.constraint_compliance:
                    plan.constraint_compliance[c.constraint_id] = True

            if validation.is_valid and plan.estimated_success_rate > best_score:
                best_score = plan.estimated_success_rate
                best_plan_id = plan.plan_id

            if validation.warnings:
                warnings.extend(
                    [f"[{variant_name}] {w}" for w in validation.warnings]
                )

        # Compute overall feasibility — حساب الجدوى العامة
        feasible_plans = [
            p for p in plans.values()
            if all(p.constraint_compliance.get(cid, True) for cid in
                   [c.constraint_id for c in active_constraints if c.is_hard])
        ]
        feasibility_score = len(feasible_plans) / max(1, len(plans))

        # If no feasible plan, try relaxations — إذا لا توجد خطة ممكنة
        if not feasible_plans and active_constraints:
            warnings.append(
                "لا توجد خطة ممكنة تحت القيود الحالية — No feasible plan under current constraints"
            )

        # Recommend the best feasible plan, or the realistic one — التوصية
        recommended = best_plan_id
        if not recommended:
            # Fallback: recommend realistic variant
            realistic = plans.get(PlanVariant.REALISTIC.value)
            if realistic:
                recommended = realistic.plan_id
                warnings.append(
                    "التوصية بخطة واقعية رغم انتهاك القيود — "
                    "Recommending realistic plan despite constraint violations"
                )

        result = PlanningResult(
            goal_id=goal.goal_id,
            plans=plans,
            recommended_plan=recommended,
            feasibility_score=feasibility_score,
            warnings=warnings,
        )

        with self._lock:
            self._planning_history.append(result)
            self._plan_counter += 1

        logger.info(
            f"ConstraintEngine: Generated plans for goal '{goal.description[:50]}' "
            f"— feasibility={feasibility_score:.2f}"
        )
        return result

    def _generate_variant(
        self, goal: PlanningGoal, variant: str, multipliers: dict
    ) -> ExecutionPlan:
        """
        توليد متغير خطة — Generate a single plan variant.
        """
        cost_mult = multipliers["cost"]
        dur_mult = multipliers["duration"]
        success_rate = multipliers["success"]
        risk_text = multipliers["risk"]

        # Build steps based on goal — بناء الخطوات بناءً على الهدف
        steps = self._decompose_goal(goal, cost_mult, dur_mult)

        total_cost = sum(s.cost for s in steps)
        total_duration = sum(s.duration for s in steps)

        # Resource usage — استخدام الموارد
        resource_usage = {}
        for step in steps:
            for res_key, res_val in step.resources_needed.items():
                if isinstance(res_val, (int, float)):
                    resource_usage[res_key] = resource_usage.get(res_key, 0.0) + res_val

        return ExecutionPlan(
            goal_id=goal.goal_id,
            variant=variant,
            steps=steps,
            total_cost=round(total_cost, 4),
            total_duration=round(total_duration, 2),
            resource_usage=resource_usage,
            risk_assessment=risk_text,
            estimated_success_rate=success_rate,
        )

    def _decompose_goal(
        self, goal: PlanningGoal, cost_mult: float, dur_mult: float
    ) -> list:
        """
        تفكيك الهدف إلى خطوات — Decompose a goal into execution steps.

        This is a heuristic decomposition. In a production system this would
        call an LLM or use a task library.  Here we generate representative
        steps based on the goal's estimated cost and duration.
        """
        steps: list[PlanStep] = []
        base_cost = goal.estimated_cost * cost_mult
        base_duration = goal.estimated_duration * dur_mult

        # Step 1: Analysis — التحليل
        steps.append(PlanStep(
            description="Analyze goal requirements and constraints",
            description_ar="تحليل متطلبات الهدف والقيود",
            action="analyze",
            cost=round(base_cost * 0.10, 4),
            duration=round(base_duration * 0.15, 2),
            resources_needed={"cpu": 0.2, "memory_mb": 128},
            dependencies=[],
        ))

        # Step 2: Resource allocation — تخصيص الموارد
        steps.append(PlanStep(
            description="Allocate required resources and verify availability",
            description_ar="تخصيص الموارد المطلوبة والتحقق من توفرها",
            action="allocate",
            cost=round(base_cost * 0.05, 4),
            duration=round(base_duration * 0.10, 2),
            resources_needed={"cpu": 0.1, "memory_mb": 64},
            dependencies=[steps[0].step_id],
        ))

        # Step 3: Preparation — التحضير
        steps.append(PlanStep(
            description="Prepare data, models, and environment",
            description_ar="تحضير البيانات والنماذج والبيئة",
            action="prepare",
            cost=round(base_cost * 0.15, 4),
            duration=round(base_duration * 0.20, 2),
            resources_needed={"cpu": 0.3, "memory_mb": 256, "storage_mb": 512},
            dependencies=[steps[1].step_id],
        ))

        # Step 4: Core execution — التنفيذ الأساسي
        steps.append(PlanStep(
            description="Execute core task operations",
            description_ar="تنفيذ العمليات الأساسية للمهمة",
            action="execute",
            cost=round(base_cost * 0.50, 4),
            duration=round(base_duration * 0.40, 2),
            resources_needed={"cpu": 0.8, "memory_mb": 512, "api_calls": 10},
            dependencies=[steps[2].step_id],
        ))

        # Step 5: Validation — التحقق
        steps.append(PlanStep(
            description="Validate results against quality constraints",
            description_ar="التحقق من النتائج مقابل قيود الجودة",
            action="validate",
            cost=round(base_cost * 0.10, 4),
            duration=round(base_duration * 0.10, 2),
            resources_needed={"cpu": 0.2, "memory_mb": 128},
            dependencies=[steps[3].step_id],
        ))

        # Step 6: Delivery — التسليم
        steps.append(PlanStep(
            description="Deliver results and release resources",
            description_ar="تسليم النتائج وتحرير الموارد",
            action="deliver",
            cost=round(base_cost * 0.10, 4),
            duration=round(base_duration * 0.05, 2),
            resources_needed={"cpu": 0.1, "memory_mb": 64},
            dependencies=[steps[4].step_id],
        ))

        return steps

    # ── Validation — التحقق ──────────────────────────────────────

    def validate_plan(
        self, plan: ExecutionPlan, constraints: list = None
    ) -> ValidationResult:
        """
        التحقق من الخطة — Validate a plan against constraints.

        Checks every constraint against the plan's projected cost, duration,
        and resource usage.  Hard constraint violations make the plan invalid.

        Args:
            plan: The execution plan to validate.
            constraints: Constraints to validate against (default: all active).

        Returns:
            ValidationResult with violations and warnings.
        """
        if constraints is None:
            constraints = self.get_constraints()

        violations = []
        warnings = []
        is_valid = True

        for constraint in constraints:
            if not constraint.is_active:
                continue

            # Determine the actual value for this constraint type — تحديد القيمة الفعلية
            actual_value = self._extract_actual_value(plan, constraint)
            passed = constraint.evaluate(actual_value)

            if not passed:
                violation = {
                    "constraint_id": constraint.constraint_id,
                    "constraint_name": constraint.name,
                    "constraint_name_ar": constraint.name_ar,
                    "constraint_type": constraint.constraint_type,
                    "operator": constraint.operator,
                    "limit_value": constraint.value,
                    "actual_value": actual_value,
                    "unit": constraint.unit,
                    "is_hard": constraint.is_hard,
                    "violated": True,
                }
                violations.append(violation)

                if constraint.is_hard:
                    is_valid = False
                else:
                    warn_msg = (
                        f"Soft constraint '{constraint.name}' violated: "
                        f"actual={actual_value} {constraint.unit}, "
                        f"limit={constraint.value} {constraint.unit}"
                    )
                    warnings.append(warn_msg)

        return ValidationResult(
            plan_id=plan.plan_id,
            is_valid=is_valid,
            violations=violations,
            warnings=warnings,
        )

    def _extract_actual_value(
        self, plan: ExecutionPlan, constraint: Constraint
    ) -> float:
        """
        استخراج القيمة الفعلية — Extract the actual metric value from a plan
        for a given constraint type.
        """
        ctype = constraint.constraint_type

        if ctype == ConstraintType.BUDGET.value:
            return plan.total_cost
        elif ctype == ConstraintType.TIME.value:
            return plan.total_duration
        elif ctype == ConstraintType.COMPUTE.value:
            # Try to match specific resource keys
            res_key = constraint.unit.lower() if constraint.unit else "cpu"
            if res_key in plan.resource_usage:
                return plan.resource_usage[res_key]
            # Default: max CPU usage
            return plan.resource_usage.get("cpu", 0.0)
        elif ctype == ConstraintType.LEGAL.value:
            # Legal constraints are typically binary (0=pass, 1=fail)
            # We check if the plan mentions any restricted actions
            for step in plan.steps:
                if isinstance(step, dict):
                    action = step.get("action", "")
                else:
                    action = getattr(step, "action", "")
                restricted = ["bypass", "override_safety", "ignore_law"]
                if action in restricted:
                    return 1.0
            return 0.0
        elif ctype == ConstraintType.QUALITY.value:
            # Quality constraint: success rate as the metric
            return plan.estimated_success_rate
        else:
            return 0.0

    # ── Feasibility — الجدوى ─────────────────────────────────────

    def evaluate_feasibility(self, goal: PlanningGoal) -> FeasibilityReport:
        """
        تقييم جدوى الهدف — Evaluate whether a goal is feasible
        under current constraints without generating full plans.

        Args:
            goal: The goal to evaluate.

        Returns:
            FeasibilityReport with feasibility score and blocking constraints.
        """
        active_constraints = self.get_constraints()
        blocking: list[str] = []
        relaxations: list[RelaxationSuggestion] = []

        # Check each constraint against the goal's estimates — فحص كل قيد
        for constraint in active_constraints:
            if not constraint.is_active:
                continue

            actual = self._goal_metric(goal, constraint)
            passed = constraint.evaluate(actual)

            if not passed:
                blocking.append(constraint.constraint_id)
                # Suggest relaxation for soft constraints — اقتراح تخفيف للقيود اللينة
                if not constraint.is_hard:
                    relaxation = self._compute_relaxation(constraint, actual)
                    relaxations.append(relaxation)

        # Compute feasibility score — حساب درجة الجدوى
        total_hard = [c for c in active_constraints if c.is_hard and c.is_active]
        hard_blocking = [cid for cid in blocking
                         if cid in {c.constraint_id for c in total_hard}]
        total_soft = [c for c in active_constraints if not c.is_hard and c.is_active]
        soft_blocking = len(blocking) - len(hard_blocking)

        if total_hard and hard_blocking:
            # Any hard constraint violation makes it infeasible
            feasibility = 0.0
        else:
            hard_score = 1.0
            soft_score = 1.0 - (soft_blocking / max(1, len(total_soft)))
            # Weight: hard constraints dominate
            hard_weight = len(total_hard) / max(1, len(active_constraints))
            soft_weight = 1.0 - hard_weight
            feasibility = hard_score * hard_weight + soft_score * soft_weight

        is_feasible = len(hard_blocking) == 0

        # If not feasible, suggest relaxations for hard constraints too
        if not is_feasible:
            for constraint in active_constraints:
                if (constraint.constraint_id in hard_blocking
                        and not any(r.constraint_id == constraint.constraint_id
                                    for r in relaxations)):
                    actual = self._goal_metric(goal, constraint)
                    relaxation = self._compute_relaxation(constraint, actual)
                    relaxations.append(relaxation)

        return FeasibilityReport(
            goal_id=goal.goal_id,
            is_feasible=is_feasible,
            feasibility_score=round(feasibility, 4),
            blocking_constraints=blocking,
            suggested_relaxations=relaxations,
        )

    def _goal_metric(self, goal: PlanningGoal, constraint: Constraint) -> float:
        """
        استخراج مقياس الهدف — Extract metric from goal for a constraint.
        """
        ctype = constraint.constraint_type

        if ctype == ConstraintType.BUDGET.value:
            return goal.estimated_cost
        elif ctype == ConstraintType.TIME.value:
            return goal.estimated_duration
        elif ctype == ConstraintType.COMPUTE.value:
            res_key = constraint.unit.lower() if constraint.unit else "cpu"
            return goal.required_resources.get(res_key, 0.0)
        elif ctype == ConstraintType.LEGAL.value:
            return 0.0   # goals are assumed legally compliant by default
        elif ctype == ConstraintType.QUALITY.value:
            return goal.target_outcome.get("min_quality", 0.5)
        return 0.0

    # ── Relaxations — التخفيفات ──────────────────────────────────

    def suggest_relaxations(
        self, goal: PlanningGoal, failed_constraints: list = None
    ) -> list:
        """
        اقتراح تخفيفات — Suggest constraint relaxations to make a goal feasible.

        Args:
            goal: The goal that failed constraints.
            failed_constraints: List of Constraint objects or constraint IDs
                               that were violated.  If None, evaluates all.

        Returns:
            List of RelaxationSuggestion objects.
        """
        if failed_constraints is None:
            report = self.evaluate_feasibility(goal)
            failed_constraints = [
                self._constraints[cid] for cid in report.blocking_constraints
                if cid in self._constraints
            ]

        suggestions: list[RelaxationSuggestion] = []

        for item in failed_constraints:
            if isinstance(item, str):
                constraint = self._constraints.get(item)
                if not constraint:
                    continue
            else:
                constraint = item

            actual = self._goal_metric(goal, constraint)
            relaxation = self._compute_relaxation(constraint, actual)
            suggestions.append(relaxation)

        return suggestions

    def _compute_relaxation(
        self, constraint: Constraint, actual: float
    ) -> RelaxationSuggestion:
        """
        حساب تخفيف مقترح — Compute a suggested relaxation for one constraint.

        Strategy: increase limit by 20% above actual value (for LTE/IN),
        or decrease threshold for GTE.  Never relax legal constraints.
        """
        current = constraint.value
        op = constraint.operator

        if constraint.constraint_type == ConstraintType.LEGAL.value:
            return RelaxationSuggestion(
                constraint_id=constraint.constraint_id,
                current_value=current,
                suggested_value=current,
                impact_description="Legal constraints cannot be relaxed",
                impact_description_ar="لا يمكن تخفيف القيود القانونية",
            )

        if op in (ConstraintOperator.LTE.value, ConstraintOperator.IN.value):
            # Raise the ceiling — رفع الحد الأعلى
            suggested = actual * 1.20
            if suggested <= current:
                suggested = current * 1.20
            impact_en = (
                f"Increase {constraint.name} from {current} to {suggested:.2f} "
                f"{constraint.unit} to accommodate actual usage of {actual:.2f}"
            )
            impact_ar = (
                f"زيادة {constraint.name_ar} من {current} إلى {suggested:.2f} "
                f"{constraint.unit} لاستيعاب الاستخدام الفعلي {actual:.2f}"
            )
        elif op == ConstraintOperator.GTE.value:
            # Lower the floor — خفض الحد الأدنى
            suggested = actual * 0.80
            if suggested >= current:
                suggested = current * 0.80
            impact_en = (
                f"Lower {constraint.name} from {current} to {suggested:.2f} "
                f"{constraint.unit} to match actual value of {actual:.2f}"
            )
            impact_ar = (
                f"خفض {constraint.name_ar} من {current} إلى {suggested:.2f} "
                f"{constraint.unit} لمطابقة القيمة الفعلية {actual:.2f}"
            )
        else:
            # EQ / NEQ — not easily relaxable
            suggested = actual
            impact_en = (
                f"Adjust {constraint.name} to {suggested:.2f} {constraint.unit}"
            )
            impact_ar = (
                f"تعديل {constraint.name_ar} إلى {suggested:.2f} {constraint.unit}"
            )

        return RelaxationSuggestion(
            constraint_id=constraint.constraint_id,
            current_value=current,
            suggested_value=round(suggested, 4),
            impact_description=impact_en,
            impact_description_ar=impact_ar,
        )

    # ── History — السجل ──────────────────────────────────────────

    def get_planning_history(self, limit: int = 20) -> list:
        """
        الحصول على سجل التخطيط — Get recent planning results.
        """
        with self._lock:
            results = self._planning_history[-limit:]
        return [r.to_dict() for r in results]

    # ── Lifecycle — دورة الحياة ──────────────────────────────────

    def get_status(self) -> dict:
        """
        حالة المحرك — Get engine status.
        """
        with self._lock:
            active_count = sum(
                1 for c in self._constraints.values() if c.is_active
            )
            hard_count = sum(
                1 for c in self._constraints.values()
                if c.is_active and c.is_hard
            )
            return {
                "enabled": CONSTRAINT_PLANNING_ENABLED,
                "active": self._active,
                "total_constraints": len(self._constraints),
                "active_constraints": active_count,
                "hard_constraints": hard_count,
                "soft_constraints": active_count - hard_count,
                "plans_generated": self._plan_counter,
                "constraints_by_type": {
                    ct.value: sum(
                        1 for c in self._constraints.values()
                        if c.constraint_type == ct.value and c.is_active
                    )
                    for ct in ConstraintType
                },
            }

    async def shutdown(self):
        """
        إيقاف المحرك — Shutdown the constraint engine.
        Clears all constraints and planning history.
        Compliant with Law 5 (shutdown protocol).
        """
        logger.info(
            "ConstraintEngine: Shutting down — clearing constraints and history "
            "(Law 5 compliant)"
        )
        with self._lock:
            self._constraints.clear()
            self._planning_history.clear()
            self._active = False


# ── Singleton — النمط المفرد ────────────────────────────────────
constraint_engine = ConstraintEngine()
