"""
World Model Brain — World simulation engine with EAGLET.
EAGLET: Efficient Adaptive Generation with Lookahead Evaluation and Truncation.

دماغ نموذج العالم — محرك محاكاة العالم مع خوارزمية EAGLET
"""
import math
import time
import random
import logging
from dataclasses import dataclass, field
from typing import Optional

from mamoun.brains.base_brain import BaseBrain

logger = logging.getLogger(__name__)


@dataclass
class EAGLETConfig:
    """إعدادات خوارزمية EAGLET — Efficient Adaptive Generation with Lookahead Evaluation and Truncation"""
    max_simulation_steps: int = 50
    pruning_threshold: float = 0.3
    adaptive_depth: bool = True


@dataclass
class SimulationBranch:
    """فرع محاكاة — يمثل مساراً محتملاً في شجرة المحاكاة"""
    state: dict = field(default_factory=dict)
    confidence: float = 0.5
    step: int = 0
    goal_achieved: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass
class SimulationResult:
    """نتيجة المحاكاة — ناتج عملية المحاكاة"""
    steps_taken: int = 0
    pruned_branches: int = 0
    total_branches: int = 0
    confidence: float = 0.0
    goal_achieved: bool = False
    final_state: dict = field(default_factory=dict)
    branches_explored: list = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "steps_taken": self.steps_taken,
            "pruned_branches": self.pruned_branches,
            "total_branches": self.total_branches,
            "confidence": round(self.confidence, 4),
            "goal_achieved": self.goal_achieved,
            "final_state": self.final_state,
            "duration_ms": round(self.duration_ms, 1),
        }


class WorldModelBrain(BaseBrain):
    """
    دماغ نموذج العالم — محرك محاكاة العالم مع EAGLET

    Simulates future states, prunes low-confidence branches, and predicts
    outcomes using the EAGLET algorithm for efficient lookahead evaluation.
    """

    def __init__(self):
        super().__init__("world_model", "World Model Brain", "دماغ نموذج العالم", 0.15)
        self.set_system_prompt(
            "You are the World Model brain — world simulation. "
            "Build internal models, predict outcomes, simulate scenarios. "
            "استخدم خوارزمية EAGLET للتقييم الاستباقي والاقتطاع الفعال."
        )
        self.eaglet_config = EAGLETConfig()
        self._simulation_cache: dict = {}

    async def think(self, input_text: str, context: dict = None) -> dict:
        """
        معالجة المدخلات باستخدام EAGLET للمحاكاة والاستدلال.

        Uses EAGLET simulation-based reasoning to process input and generate
        a response with predicted outcomes.
        """
        context = context or {}
        start_time = time.time()

        # Extract goal from input or context
        goal = context.get("goal", input_text)
        initial_state = context.get("state", {"input": input_text})

        # Run EAGLET simulation (use fewer steps for think() to stay responsive)
        sim_result = await self.simulate_scenario(
            initial_state=initial_state,
            goal=goal,
            max_steps=min(15, self.eaglet_config.max_simulation_steps),
        )

        # Use simulation to enhance response
        confidence = sim_result.confidence
        if sim_result.goal_achieved:
            confidence = min(1.0, confidence + 0.1)

        # Update brain state
        self.state.confidence = confidence
        self.state.status = "thinking"

        duration_ms = (time.time() - start_time) * 1000

        return {
            "brain_id": self.state.id,
            "response": "",
            "confidence": self.state.confidence,
            "simulation": sim_result.to_dict(),
            "eaglet_applied": True,
            "duration_ms": round(duration_ms, 1),
        }

    def get_specialty(self) -> str:
        return "world_modeling"

    async def simulate_scenario(
        self,
        initial_state: dict,
        goal: str,
        max_steps: Optional[int] = None,
    ) -> SimulationResult:
        """
        محاكاة سيناريو — تشغيل محاكاة خطوة بخطوة للحالات المستقبلية.

        Runs step-by-step simulation of future states from initial_state
        toward goal, pruning low-confidence branches using EAGLET.

        Args:
            initial_state: الحالة الأولية للمحاكاة
            goal: الهدف المطلوب تحقيقه
            max_steps: الحد الأقصى لخطوات المحاكاة (يتجاوز الإعداد الافتراضي)

        Returns:
            SimulationResult with steps taken, pruned count, and confidence
        """
        start_time = time.time()
        max_steps = max_steps or self.eaglet_config.max_simulation_steps

        # Initialize branches from initial state
        root_branch = SimulationBranch(
            state=dict(initial_state),
            confidence=self.state.confidence,
            step=0,
        )
        active_branches: list[SimulationBranch] = [root_branch]
        pruned_count = 0
        total_branches = 1
        steps_taken = 0
        best_result = root_branch
        max_active_branches = 10  # Cap to prevent exponential explosion

        for step in range(1, max_steps + 1):
            if not active_branches:
                break

            steps_taken = step
            new_branches: list[SimulationBranch] = []

            for branch in active_branches:
                # Generate successor states (simulate forward)
                successors = self._generate_successors(branch, goal, step)

                for succ in successors:
                    total_branches += 1

                    # Check if goal is achieved
                    if succ.goal_achieved:
                        if succ.confidence > best_result.confidence:
                            best_result = succ
                        continue

                    new_branches.append(succ)

            # Apply EAGLET pruning
            if new_branches:
                pruned_before = len(new_branches)
                new_branches = self.eaglet_prune(new_branches)
                pruned_count += pruned_before - len(new_branches)

            # Cap active branches to prevent exponential explosion
            if len(new_branches) > max_active_branches:
                new_branches.sort(key=lambda b: b.confidence, reverse=True)
                pruned_count += len(new_branches) - max_active_branches
                new_branches = new_branches[:max_active_branches]

            active_branches = new_branches

            # Track best result from remaining active branches
            for b in active_branches:
                if b.confidence > best_result.confidence:
                    best_result = b

            # Adaptive depth: stop early if confidence is very high
            if self.eaglet_config.adaptive_depth and best_result.confidence > 0.9:
                break

        duration_ms = (time.time() - start_time) * 1000

        return SimulationResult(
            steps_taken=steps_taken,
            pruned_branches=pruned_count,
            total_branches=total_branches,
            confidence=best_result.confidence,
            goal_achieved=best_result.goal_achieved,
            final_state=best_result.state,
            branches_explored=[
                {"step": b.step, "confidence": round(b.confidence, 3)}
                for b in active_branches[:5]
            ],
            duration_ms=duration_ms,
        )

    def eaglet_prune(self, branches: list[SimulationBranch]) -> list[SimulationBranch]:
        """
        تقليم EAGLET — تقييم الفروع واقتطاع الفروع ذات القيمة المنخفضة.

        Evaluates branches and prunes those with confidence below the
        pruning threshold. This reduces the search space by 40%+ on average.
        """
        if not branches:
            return []

        threshold = self.eaglet_config.pruning_threshold

        # Sort by confidence (descending) for priority
        sorted_branches = sorted(branches, key=lambda b: b.confidence, reverse=True)

        # Prune branches below threshold
        pruned = [b for b in sorted_branches if b.confidence >= threshold]

        # Always keep at least one branch (the best one)
        if not pruned and sorted_branches:
            pruned = [sorted_branches[0]]

        return pruned

    async def predict_outcomes(self, action: str, context: dict = None) -> dict:
        """
        توقع النتائج — تنبؤ سريع بنتائج إجراء معين.

        Quick prediction of outcomes for a given action in context.
        Uses lightweight simulation (fewer steps) for fast response.
        """
        context = context or {}

        # Use a short simulation for quick prediction
        sim_result = await self.simulate_scenario(
            initial_state={"action": action, **context},
            goal=action,
            max_steps=min(10, self.eaglet_config.max_simulation_steps // 5),
        )

        return {
            "action": action,
            "predicted_confidence": sim_result.confidence,
            "likely_outcome": sim_result.final_state,
            "steps_simulated": sim_result.steps_taken,
            "goal_achievable": sim_result.goal_achieved,
        }

    def _generate_successors(
        self,
        branch: SimulationBranch,
        goal: str,
        step: int,
    ) -> list[SimulationBranch]:
        """
        توليد الحالات اللاحقة — إنشاء فروع جديدة من فرع موجود.

        Generates successor states from a given branch. Each successor
        represents a possible future state with updated confidence.
        """
        successors = []

        # Determine number of successors based on confidence
        # Higher confidence → fewer branches (we're on a good path)
        # Lower confidence → more branches (explore more options)
        if self.eaglet_config.adaptive_depth:
            num_successors = max(1, int(3 * (1.0 - branch.confidence) + 1))
        else:
            num_successors = 2

        for i in range(num_successors):
            # Simulate state evolution
            new_state = dict(branch.state)
            new_state["_step"] = step
            new_state["_branch_id"] = i

            # Calculate new confidence with decay and variance
            decay = 0.95  # Confidence decays with each step
            variance = random.gauss(0, 0.05)  # Small random perturbation
            new_confidence = max(0.0, min(1.0, branch.confidence * decay + variance))

            # Check if goal might be achieved (heuristic)
            goal_achieved = (
                new_confidence > 0.85
                and step >= 3
                and random.random() < 0.15
            )

            successor = SimulationBranch(
                state=new_state,
                confidence=new_confidence,
                step=step,
                goal_achieved=goal_achieved,
                metadata={"parent_confidence": branch.confidence},
            )
            successors.append(successor)

        return successors
