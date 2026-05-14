"""
BABSHARQII v6.0 — World Model V2 Brain
دماغ نموذج العالم المتقدم — محرك محاكاة مع System 2 واستدلال سببي

Extends WorldModelBrain with:
- JEPA-inspired State Prediction: internal state representations with latent vectors
- System 2 Deep Reasoning: multiple EAGLET simulation passes with goal variation
- Causal Reasoning Integration: root cause analysis from error patterns
- Enhanced EAGLET: dynamic pruning, adaptive branching, early termination
- Knowledge Gap Detection: identifies when the system lacks information

This brain uses a "slow thinking" approach (System 2) that runs multiple
simulations with different goals and merges results for deeper understanding.
"""

import os
import math
import time
import random
import logging
from dataclasses import dataclass, field
from typing import Optional

from mamoun.brains.world_model_brain import (
    WorldModelBrain,
    EAGLETConfig,
    SimulationBranch,
    SimulationResult,
)
from mamoun.core.causal_reasoner import CausalReasoner, CausalRule

logger = logging.getLogger(__name__)

# Env toggles for v6 features
V6_ENABLED = os.environ.get("MAMOUN_V6_ENABLED", "true").lower() in ("true", "1", "yes")


@dataclass
class StateRepresentation:
    """
    تمثيل الحالة — تمثيل داخلي للحالة مستوحى من JEPA.
    JEPA-inspired internal state representation with latent vector simulation.

    Instead of predicting words, predicts future states in a latent space,
    enabling more abstract and compositional reasoning.
    """
    latent_vector: list[float] = field(default_factory=list)  # Simulated JEPA latent
    confidence: float = 0.0
    predicted_outcome: dict = field(default_factory=dict)
    uncertainty: float = 0.0
    step: int = 0

    def to_dict(self) -> dict:
        return {
            "latent_vector_dim": len(self.latent_vector),
            "latent_vector_sample": self.latent_vector[:4] if self.latent_vector else [],
            "confidence": round(self.confidence, 4),
            "predicted_outcome": self.predicted_outcome,
            "uncertainty": round(self.uncertainty, 4),
            "step": self.step,
        }

    def similarity(self, other: "StateRepresentation") -> float:
        """
        حساب التشابه — تشابه جيب التمام بين المتجهات الكامنة.
        Cosine similarity between latent vectors.
        """
        if not self.latent_vector or not other.latent_vector:
            return 0.0

        # Align dimensions
        min_dim = min(len(self.latent_vector), len(other.latent_vector))
        a = self.latent_vector[:min_dim]
        b = other.latent_vector[:min_dim]

        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return max(-1.0, min(1.0, dot / (mag_a * mag_b)))


class WorldModelV2(WorldModelBrain):
    """
    دماغ نموذج العالم المتقدم — محرك محاكاة مع System 2 واستدلال سببي.

    World Model V2 extends the EAGLET-based WorldModelBrain with:
    1. System 2 deep reasoning via multi-pass simulation
    2. JEPA-inspired state prediction in latent space
    3. Causal reasoning for root cause analysis
    4. Enhanced EAGLET with dynamic pruning and adaptive branching
    5. Knowledge gap detection
    """

    # System 2 simulation pass configurations
    SIMULATION_PASSES = 3
    LATENT_DIM = 16  # Dimension of simulated JEPA latent vectors

    def __init__(self):
        super().__init__()
        # Override brain identity for V2
        self.state.id = "world_model_v2"
        self.state.name = "World Model V2"
        self.state.name_ar = "دماغ نموذج العالم المتقدم"

        self.set_system_prompt(
            "You are the advanced World Model brain (V2) — deep reasoning. "
            "Build internal models, predict outcomes, simulate scenarios with System 2. "
            "استخدم التفكير العميق والاستدلال السببي وتنبؤ الحالات."
        )

        # Causal reasoner for root cause analysis
        self._causal_reasoner = CausalReasoner()

        # State cache for JEPA predictions
        self._state_cache: dict[str, StateRepresentation] = {}

        # Detected knowledge gaps
        self._knowledge_gaps: list[dict] = []

        # Enhanced EAGLET parameters
        self._dynamic_pruning_enabled = True
        self._adaptive_branching_enabled = True
        self._early_termination_confidence = 0.9

    async def think(self, input_text: str, context: dict = None) -> dict:
        """
        معالجة المدخلات باستخدام System 2 مع تحليل سببي.

        Uses System 2 deep reasoning with causal analysis to process
        input and generate a response with deeper understanding.

        Args:
            input_text: نص المدخلة
            context: سياق إضافي

        Returns:
            نتيجة التفكير مع محاكاة وتحليل سببي
        """
        if not V6_ENABLED:
            return await super().think(input_text, context)

        context = context or {}
        start_time = time.time()

        # Run System 2 deep reasoning
        deep_result = await self.deep_reason(input_text, context)

        # Detect knowledge gaps
        gaps = self.detect_knowledge_gap(context)
        self._knowledge_gaps = gaps

        # Update brain state
        self.state.confidence = deep_result.get("confidence", 0.5)
        self.state.status = "thinking"

        duration_ms = (time.time() - start_time) * 1000

        return {
            "brain_id": self.state.id,
            "response": "",
            "confidence": self.state.confidence,
            "simulation": deep_result.get("simulation", {}),
            "eaglet_applied": True,
            "system2_applied": True,
            "causal_analysis": deep_result.get("causal_analysis", {}),
            "knowledge_gaps": gaps,
            "duration_ms": round(duration_ms, 1),
        }

    async def deep_reason(self, input_text: str, context: dict = None) -> dict:
        """
        التفكير العميق — محاكاة متعددة المسارات مع أهداف مختلفة ودمج النتائج.
        System 2 Deep Reasoning: runs multiple EAGLET simulations with
        different goals and merges results for deeper understanding.

        Each pass uses a different simulation goal:
        - Pass 1: Direct goal (what we want to achieve)
        - Pass 2: Risk assessment (what could go wrong)
        - Pass 3: Alternative paths (exploring different approaches)

        Args:
            input_text: نص المدخلة
            context: سياق إضافي

        Returns:
            نتيجة التفكير العميق مع تحليل مدمج
        """
        context = context or {}
        start_time = time.time()

        goal = context.get("goal", input_text)
        initial_state = context.get("state", {"input": input_text})
        errors = context.get("errors", [])

        # ─── Pass 1: Direct Goal Simulation ─────────────────────────────────
        pass1_result = await self.simulate_scenario(
            initial_state=initial_state,
            goal=goal,
            max_steps=min(20, self.eaglet_config.max_simulation_steps),
        )

        # ─── Pass 2: Risk Assessment Simulation ─────────────────────────────
        risk_goal = f"مخاطر: {goal}"  # Risk: {goal}
        risk_state = {**initial_state, "_mode": "risk_assessment"}
        pass2_result = await self.simulate_scenario(
            initial_state=risk_state,
            goal=risk_goal,
            max_steps=min(15, self.eaglet_config.max_simulation_steps),
        )

        # ─── Pass 3: Alternative Paths Simulation ───────────────────────────
        alt_goal = f"بدائل: {goal}"  # Alternatives: {goal}
        alt_state = {**initial_state, "_mode": "alternative_exploration"}
        pass3_result = await self.simulate_scenario(
            initial_state=alt_state,
            goal=alt_goal,
            max_steps=min(15, self.eaglet_config.max_simulation_steps),
        )

        # ─── Merge Results ──────────────────────────────────────────────────
        # Weighted merge: direct goal has highest weight
        merged_confidence = (
            pass1_result.confidence * 0.50
            + pass2_result.confidence * 0.25
            + pass3_result.confidence * 0.25
        )

        # If goal was achieved in any pass, boost confidence
        goal_achieved = (
            pass1_result.goal_achieved
            or pass2_result.goal_achieved
            or pass3_result.goal_achieved
        )
        if goal_achieved:
            merged_confidence = min(1.0, merged_confidence + 0.05)

        # ─── Causal Analysis ────────────────────────────────────────────────
        causal_rules: list[CausalRule] = []
        if errors:
            causal_rules = await self._causal_reasoner.analyze_root_cause(errors)

        # ─── Build State Representation ─────────────────────────────────────
        state_rep = await self.predict_state(
            current_state=initial_state,
            action=input_text,
        )

        # ─── JEPA State Caching ─────────────────────────────────────────────
        cache_key = f"{input_text[:50]}_{hash(str(initial_state))}"
        self._state_cache[cache_key] = state_rep

        duration_ms = (time.time() - start_time) * 1000

        # Determine best result for simulation data
        best_result = pass1_result
        if pass2_result.confidence > best_result.confidence and pass2_result.goal_achieved:
            best_result = pass2_result
        if pass3_result.confidence > best_result.confidence and pass3_result.goal_achieved:
            best_result = pass3_result

        return {
            "confidence": round(merged_confidence, 4),
            "goal_achieved": goal_achieved,
            "simulation": best_result.to_dict(),
            "pass1_confidence": round(pass1_result.confidence, 4),
            "pass2_confidence": round(pass2_result.confidence, 4),
            "pass3_confidence": round(pass3_result.confidence, 4),
            "state_prediction": state_rep.to_dict(),
            "causal_analysis": {
                "rules_found": len(causal_rules),
                "top_rules": [r.to_dict() for r in causal_rules[:3]],
            },
            "passes_completed": self.SIMULATION_PASSES,
            "duration_ms": round(duration_ms, 1),
        }

    async def predict_state(
        self,
        current_state: dict,
        action: str,
    ) -> StateRepresentation:
        """
        تنبؤ الحالة — تنبؤ الحالة المستقبلية مستوحى من JEPA.
        JEPA-inspired state prediction: builds internal state representations
        and predicts future states (not words).

        Simulates a latent representation of the current state, then
        predicts how the state would evolve after taking an action.

        Args:
            current_state: الحالة الحالية
            action: الإجراء المخطط

        Returns:
            StateRepresentation with predicted future state
        """
        # Generate simulated latent vector from current state
        latent = self._encode_to_latent(current_state, action)

        # Simulate state transition
        step = current_state.get("_step", 0) + 1

        # Predict outcome confidence using a short simulation
        sim_result = await self.simulate_scenario(
            initial_state={**current_state, "action": action},
            goal=action,
            max_steps=min(5, self.eaglet_config.max_simulation_steps // 10),
        )

        # Compute uncertainty: 1 - confidence, adjusted by simulation variance
        uncertainty = 1.0 - sim_result.confidence
        if sim_result.pruned_branches > 0:
            pruned_ratio = sim_result.pruned_branches / max(1, sim_result.total_branches)
            uncertainty = min(1.0, uncertainty + pruned_ratio * 0.1)

        # Predict outcome from simulation
        predicted_outcome = {
            "goal_achievable": sim_result.goal_achieved,
            "predicted_confidence": round(sim_result.confidence, 4),
            "steps_to_predict": sim_result.steps_taken,
            "branches_explored": sim_result.total_branches,
        }

        # Evolve latent vector (simulate state transition in latent space)
        evolved_latent = self._evolve_latent(latent, sim_result.confidence, step)

        return StateRepresentation(
            latent_vector=evolved_latent,
            confidence=sim_result.confidence,
            predicted_outcome=predicted_outcome,
            uncertainty=round(uncertainty, 4),
            step=step,
        )

    def detect_knowledge_gap(self, context: dict) -> list[dict]:
        """
        كشف الفجوة المعرفية — تحديد متى يفتقر النظام إلى المعلومات.
        Identifies when the system lacks information for confident reasoning.

        Knowledge gaps are detected by:
        1. Low confidence in state predictions
        2. High uncertainty in simulation results
        3. Missing context keys that would be expected
        4. Insufficient error data for causal reasoning

        Args:
            context: سياق المهمة الحالية

        Returns:
            قائمة الفجوات المعرفية المكتشفة
        """
        gaps: list[dict] = []

        if not context:
            gaps.append({
                "type": "missing_context",
                "description": "لا يوجد سياق كافٍ — يتطلب معلومات إضافية",
                "severity": "high",
            })
            return gaps

        # Check 1: Low confidence in cached state predictions
        for key, state_rep in self._state_cache.items():
            if state_rep.uncertainty > 0.6:
                gaps.append({
                    "type": "high_uncertainty",
                    "description": (
                        f"شك عالي في التنبؤ (خطوة {state_rep.step}): "
                        f"عدم اليقين = {state_rep.uncertainty:.2f}"
                    ),
                    "severity": "medium",
                    "step": state_rep.step,
                    "uncertainty": state_rep.uncertainty,
                })

        # Check 2: Missing expected context keys
        expected_keys = ["goal", "state", "errors", "history", "domain"]
        missing_keys = [k for k in expected_keys if k not in context]
        if missing_keys:
            gaps.append({
                "type": "missing_context_keys",
                "description": f"مفاتيح سياق مفقودة: {', '.join(missing_keys)}",
                "severity": "low",
                "missing_keys": missing_keys,
            })

        # Check 3: Insufficient error data for causal reasoning
        errors = context.get("errors", [])
        if errors and len(errors) < 3:
            gaps.append({
                "type": "insufficient_error_data",
                "description": (
                    f"بيانات خطأ غير كافية للاستدلال السببي "
                    f"({len(errors)} أخطاء فقط — يُحتاج 3 على الأقل)"
                ),
                "severity": "medium",
                "error_count": len(errors),
            })

        # Check 4: Low overall confidence
        if self.state.confidence < 0.3:
            gaps.append({
                "type": "low_confidence",
                "description": (
                    f"ثقة منخفضة في النتائج ({self.state.confidence:.2f}) — "
                    f"يُحتاج مزيد من البيانات أو المراجعة البشرية"
                ),
                "severity": "high",
                "confidence": self.state.confidence,
            })

        # Check 5: No causal rules found (gap in causal understanding)
        if not self._causal_reasoner._rule_cache:
            gaps.append({
                "type": "no_causal_knowledge",
                "description": "لا توجد معرفة سببية متراكمة — يحتاج تحليل أخطاء أكثر",
                "severity": "medium",
            })

        return gaps

    # ─── Enhanced EAGLET Overrides ──────────────────────────────────────────

    def eaglet_prune(self, branches: list[SimulationBranch]) -> list[SimulationBranch]:
        """
        تقليم EAGLET محسّن — مع عتبة تقليم ديناميكية.
        Enhanced EAGLET pruning with dynamic threshold based on
        simulation depth and adaptive behavior.
        """
        if not branches:
            return []

        # Dynamic pruning threshold: increases with average step depth
        # Deeper simulations → stricter pruning (more aggressive)
        if self._dynamic_pruning_enabled and branches:
            avg_step = sum(b.step for b in branches) / len(branches)
            # Threshold increases by 0.02 per step (deeper = stricter)
            dynamic_threshold = self.eaglet_config.pruning_threshold + avg_step * 0.02
            dynamic_threshold = min(0.7, dynamic_threshold)  # Cap at 0.7
        else:
            dynamic_threshold = self.eaglet_config.pruning_threshold

        # Sort by confidence (descending)
        sorted_branches = sorted(branches, key=lambda b: b.confidence, reverse=True)

        # Prune branches below dynamic threshold
        pruned = [b for b in sorted_branches if b.confidence >= dynamic_threshold]

        # Always keep at least one branch (the best one)
        if not pruned and sorted_branches:
            pruned = [sorted_branches[0]]

        return pruned

    def _generate_successors(
        self,
        branch: SimulationBranch,
        goal: str,
        step: int,
    ) -> list[SimulationBranch]:
        """
        توليد الحالات اللاحقة محسّن — مع عامل تفرع متكيف.
        Enhanced successor generation with adaptive branching factor
        and early termination when confidence > 0.9.
        """
        # Early termination: if confidence is very high, generate minimal successors
        if self._early_termination_confidence and branch.confidence > self._early_termination_confidence:
            # Minimal branching — just continue the current path
            new_state = dict(branch.state)
            new_state["_step"] = step
            new_state["_branch_id"] = 0

            successor = SimulationBranch(
                state=new_state,
                confidence=min(1.0, branch.confidence * 0.98),
                step=step,
                goal_achieved=True,  # High confidence → goal likely achieved
                metadata={"parent_confidence": branch.confidence, "early_terminated": True},
            )
            return [successor]

        # Adaptive branching factor: adjust based on confidence and step depth
        if self._adaptive_branching_enabled:
            # Base branching: more branches for low confidence, fewer for high
            base_branches = max(1, int(3 * (1.0 - branch.confidence) + 1))

            # Adjust based on simulation depth: deeper = fewer branches
            depth_factor = max(0.5, 1.0 - step * 0.03)
            num_successors = max(1, int(base_branches * depth_factor))
        else:
            num_successors = 2

        successors = []
        for i in range(num_successors):
            new_state = dict(branch.state)
            new_state["_step"] = step
            new_state["_branch_id"] = i

            # Calculate new confidence with decay and variance
            decay = 0.95
            variance = random.gauss(0, 0.05)
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

    # ─── JEPA Latent Space Helpers ──────────────────────────────────────────

    def _encode_to_latent(self, state: dict, action: str) -> list[float]:
        """
        ترميز إلى فضاء كامن — تحويل الحالة والإجراء إلى متجه كامن.
        Encode state and action into a simulated latent vector.

        Uses a deterministic hash-based encoding to simulate what a
        JEPA model would learn in its latent space.
        """
        latent = [0.0] * self.LATENT_DIM

        # Encode state values into latent dimensions
        state_str = str(state) + action
        for i in range(self.LATENT_DIM):
            # Use hash-based encoding with position-dependent seeds
            seed = hash(f"{state_str}_{i}") % 10000
            random.seed(seed)
            latent[i] = random.gauss(0, 1.0)

        # Normalize latent vector
        mag = math.sqrt(sum(x * x for x in latent))
        if mag > 0:
            latent = [x / mag for x in latent]

        return latent

    def _evolve_latent(
        self, latent: list[float], confidence: float, step: int
    ) -> list[float]:
        """
        تطوير المتجه الكامن — محاكاة انتقال الحالة في الفضاء الكامن.
        Evolve the latent vector to simulate state transition.

        Applies a small perturbation based on confidence and step,
        simulating how the state would evolve in the latent space.
        """
        evolved = latent.copy()
        for i in range(len(evolved)):
            # Small perturbation based on confidence and step
            perturbation = random.gauss(0, 0.1 * (1.0 - confidence))
            evolved[i] = evolved[i] + perturbation

        # Re-normalize
        mag = math.sqrt(sum(x * x for x in evolved))
        if mag > 0:
            evolved = [x / mag for x in evolved]

        return evolved
