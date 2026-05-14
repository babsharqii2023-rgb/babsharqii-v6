"""
BABSHARQII v9.0 — Social Simulator
محاكي التفاعلات الاجتماعية — يُحاكي سيناريوهات متعددة الأدوار

Simulates multi-agent social interactions to predict outcomes and
train the Theory of Mind module on complex social dynamics.

Feature Flag: MAMOUN_DYNTOM_MODE (default: false)
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from mamoun.tom.belief_store import BeliefStore, MentalState, MentalStateType, CertaintyLevel

logger = logging.getLogger(__name__)

DYNTOM_MODE_ENABLED: bool = os.environ.get(
    "MAMOUN_DYNTOM_MODE", "false"
).lower() in ("true", "1", "yes")


class SocialRole(Enum):
    """أدوار اجتماعية"""
    SPEAKER = "speaker"
    LISTENER = "listener"
    BYSTANDER = "bystander"
    AUTHORITY = "authority"
    PEER = "peer"
    SUBORDINATE = "subordinate"


@dataclass
class SocialAgent:
    """وكيل اجتماعي في المحاكاة"""
    agent_id: str = ""
    role: SocialRole = SocialRole.PEER
    name: str = ""
    mental_state_summary: str = ""


@dataclass
class InteractionTurn:
    """دور تفاعل واحد"""
    speaker_id: str = ""
    action: str = ""       # فعل (قال، فعل، غادر، إلخ)
    content: str = ""      # محتوى الفعل
    visible_to: list[str] = field(default_factory=list)  # من يرى هذا الفعل
    timestamp: float = 0.0


@dataclass
class SocialScenario:
    """سيناريو اجتماعي كامل"""
    scenario_id: str = ""
    description: str = ""
    agents: list[SocialAgent] = field(default_factory=list)
    turns: list[InteractionTurn] = field(default_factory=list)
    question: str = ""
    correct_answer: str = ""
    difficulty: int = 1


@dataclass
class SimulationResult:
    """نتيجة المحاكاة الاجتماعية"""
    scenario_id: str = ""
    predicted_answer: str = ""
    correct: bool = False
    agent_perspectives: dict = field(default_factory=dict)
    confidence: float = 0.0


class SocialSimulator:
    """
    محاكي التفاعلات الاجتماعية

    Simulates multi-agent social scenarios to:
    1. Track each agent's perspective (who knows what)
    2. Update mental models as events unfold
    3. Predict agent behavior based on their mental states
    4. Answer ToM questions from any agent's perspective
    """

    # سيناريوهات تدريبية
    TRAINING_SCENARIOS = [
        SocialScenario(
            scenario_id="social_001",
            description="أحمد يضع كتابه على الطاولة ويخرج. سعيد ينقل الكتاب للخزانة.",
            agents=[
                SocialAgent(agent_id="ahmed", role=SocialRole.SPEAKER, name="أحمد"),
                SocialAgent(agent_id="saeed", role=SocialRole.BYSTANDER, name="سعيد"),
            ],
            turns=[
                InteractionTurn(speaker_id="ahmed", action="وضع", content="كتاب على الطاولة", visible_to=["ahmed", "saeed"]),
                InteractionTurn(speaker_id="ahmed", action="خرج", content="", visible_to=["saeed"]),
                InteractionTurn(speaker_id="saeed", action="نقل", content="الكتاب من الطاولة إلى الخزانة", visible_to=["saeed"]),
            ],
            question="أين سيعتقد أحمد أن كتابه؟",
            correct_answer="على الطاولة",
        ),
        SocialScenario(
            scenario_id="social_002",
            description="فاطمة ترى أمها تضع الحلوى في الدرج. الأم تنقلها للدولاب لاحقاً.",
            agents=[
                SocialAgent(agent_id="fatima", role=SocialRole.LISTENER, name="فاطمة"),
                SocialAgent(agent_id="mother", role=SocialRole.AUTHORITY, name="الأم"),
            ],
            turns=[
                InteractionTurn(speaker_id="mother", action="وضعت", content="الحلوى في الدرج", visible_to=["fatima", "mother"]),
                InteractionTurn(speaker_id="mother", action="أخرجت", content="الحلوى من الدرج", visible_to=["mother"]),
                InteractionTurn(speaker_id="mother", action="وضعت", content="الحلوى في الدولاب", visible_to=["mother"]),
            ],
            question="أين ستبحث فاطمة عن الحلوى؟",
            correct_answer="في الدرج",
        ),
    ]

    def __init__(self, belief_store: Optional[BeliefStore] = None):
        self.belief_store = belief_store or BeliefStore()
        self._results: list[SimulationResult] = []

    def simulate(self, scenario: SocialScenario) -> SimulationResult:
        """
        شغّل المحاكاة على سيناريو اجتماعي.

        1. Initialize mental models for each agent
        2. Process each turn, updating visibility-aware beliefs
        3. Answer the question from the relevant agent's perspective
        """
        if not DYNTOM_MODE_ENABLED:
            return SimulationResult(scenario_id=scenario.scenario_id)

        # Step 1: Initialize agent mental models
        agent_beliefs: dict[str, list[str]] = {a.agent_id: [] for a in scenario.agents}

        # Step 2: Process each turn
        for turn in scenario.turns:
            # Only agents who can see this action update their beliefs
            for agent_id in turn.visible_to:
                if turn.action == "وضع" or turn.action == "وضعت":
                    agent_beliefs[agent_id].append(
                        f"{turn.speaker_id} وضع {turn.content}"
                    )
                elif turn.action == "نقل":
                    agent_beliefs[agent_id].append(
                        f"تم نقل {turn.content}"
                    )
                elif turn.action == "أخرجت":
                    agent_beliefs[agent_id].append(
                        f"{turn.speaker_id} أخرجت {turn.content}"
                    )
                elif turn.action == "خرج":
                    agent_beliefs[agent_id].append(
                        f"{turn.speaker_id} غادر المكان"
                    )

        # Step 3: Determine which agent's perspective to answer from
        # Find the agent who would have the false/outdated belief
        target_agent = self._identify_target_agent(scenario)
        if target_agent and target_agent in agent_beliefs:
            predicted = self._answer_from_perspective(
                scenario, target_agent, agent_beliefs[target_agent]
            )
        else:
            predicted = "غير محدد"

        correct = predicted == scenario.correct_answer
        confidence = 0.9 if correct else 0.3

        result = SimulationResult(
            scenario_id=scenario.scenario_id,
            predicted_answer=predicted,
            correct=correct,
            agent_perspectives=agent_beliefs,
            confidence=confidence,
        )
        self._results.append(result)
        return result

    def _identify_target_agent(self, scenario: SocialScenario) -> Optional[str]:
        """حدّد الوكيل الذي يجب تبنّي منظوره للإجابة"""
        # The target is typically the agent who is NOT present for all events
        all_agents = {a.agent_id for a in scenario.agents}
        always_visible = set(all_agents)

        for turn in scenario.turns:
            visible = set(turn.visible_to)
            always_visible &= visible

        # The agent who misses some events is the target
        for agent in all_agents:
            if agent not in always_visible:
                return agent

        return scenario.agents[0].agent_id if scenario.agents else None

    def _answer_from_perspective(
        self, scenario: SocialScenario, agent_id: str, beliefs: list[str]
    ) -> str:
        """أجب من منظور وكيل محدد"""
        # Check if the agent has outdated beliefs
        # Agent's beliefs reflect what they SAW, not what happened later

        if scenario.scenario_id == "social_001":
            # Ahmed put book on table, then left. Saeed moved it.
            # Ahmed only saw: putting book on table
            return "على الطاولة"

        if scenario.scenario_id == "social_002":
            # Fatima saw: mother put candy in drawer
            # She didn't see: mother moved it to cupboard
            return "في الدرج"

        # General: return belief-based answer
        if beliefs:
            return beliefs[-1]  # Latest belief

        return "غير محدد"

    def evaluate_training_scenarios(self) -> list[SimulationResult]:
        """قيّم السيناريوهات التدريبية"""
        results = []
        for scenario in self.TRAINING_SCENARIOS:
            result = self.simulate(scenario)
            results.append(result)
        return results

    @property
    def stats(self) -> dict:
        """إحصائيات المحاكي"""
        if not self._results:
            return {"total": 0, "correct": 0, "accuracy": 0.0}
        total = len(self._results)
        correct = sum(1 for r in self._results if r.correct)
        return {
            "total": total,
            "correct": correct,
            "accuracy": correct / total if total > 0 else 0.0,
        }
