"""
BABSHARQII v10.0 — Nested Beliefs Engine
محرك المعتقدات المتداخلة — نمذجة المعتقدات من المستوى 2 و 3

Implements nested mental modeling for Theory of Mind Level 3:
- Level 2: "I believe that you believe X"
- Level 3: "I believe that you believe that I believe X"

Inspired by MetaMind (NeurIPS 2025) hierarchical mental modeling and
Dynamic Belief Graphs for Theory-of-Mind Reasoning (arXiv 2025).

Confidence decays exponentially with nesting depth.

Feature Flag: MAMOUN_TOM_ADVANCED (default: false)
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

TOM_ADVANCED_ENABLED: bool = os.environ.get(
    "MAMOUN_TOM_ADVANCED", "false"
).lower() in ("true", "1", "yes")


class DeceptionRiskLevel(str, Enum):
    """مستوى خطر الخداع"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class NestedBeliefModel:
    """نموذج معتقدات متداخلة"""
    model_id: str = ""
    subject_id: str = ""        # الوكيل الذي يفكر
    about_id: str = ""           # الوكيل الذي يُفكر فيه
    depth: int = 2               # عمق التداخل (2 أو 3)
    beliefs: list[str] = field(default_factory=list)    # المعتقدات المستنتجة
    confidence: float = 0.0      # الثقة (تتناقص أُسياً مع العمق)
    last_updated: float = 0.0
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "subject_id": self.subject_id,
            "about_id": self.about_id,
            "depth": self.depth,
            "beliefs": self.beliefs,
            "confidence": round(self.confidence, 4),
            "last_updated": self.last_updated,
            "evidence": self.evidence,
        }


@dataclass
class PredictedAction:
    """إجراء متوقع"""
    action: str = ""
    probability: float = 0.0
    reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "probability": round(self.probability, 4),
            "reasoning": self.reasoning,
        }


class NestedBeliefEngine:
    """
    محرك المعتقدات المتداخلة
    
    Models nested beliefs at Level 2 and Level 3:
    - Level 2: "أعتقد أنك تعتقد X" (I believe you believe X)
    - Level 3: "أعتقد أنك تعتقد أنني أعتقد Y" (I believe you believe I believe Y)
    
    Confidence formula: base_confidence * (0.5 ^ (depth - 1))
    """

    CONFIDENCE_BASE = 0.7
    CONFIDENCE_DECAY = 0.5  # Each depth level halves confidence
    MIN_CONFIDENCE = 0.1
    DECEPTION_INDICATORS = [
        "إخفاء", "كتمان", "تضليل", "كذب", "خداع",
        "conceal", "deceive", "mislead", "hide",
    ]

    def __init__(self, max_depth: int = 3):
        self.max_depth = max_depth
        self._model_counter = 0
        self._models: dict[str, NestedBeliefModel] = {}

    def model_nested_belief(
        self,
        agent_id: str,
        about_agent_id: str,
        observations: list[dict],
        existing_models: Optional[dict] = None,
    ) -> NestedBeliefModel:
        """
        نمذجة معتقدات متداخلة — ماذا يعتقد A عن B؟
        
        Args:
            agent_id: الوكيل الذي يفكر (A)
            about_agent_id: الوكيل الذي يُفكر فيه (B)
            observations: ملاحظات عن تفاعل A مع B
            existing_models: نماذج موجودة من v9.0
        
        Returns:
            NestedBeliefModel — نموذج المعتقدات المتداخلة
        """
        if not TOM_ADVANCED_ENABLED:
            return NestedBeliefModel(subject_id=agent_id, about_id=about_agent_id)

        self._model_counter += 1

        # Determine depth based on observation count
        obs_count = len(observations)
        if obs_count < 3:
            depth = 2
        elif obs_count < 8:
            depth = 2
        else:
            depth = min(self.max_depth, 3)

        # Infer beliefs at each level
        beliefs = []
        evidence = []

        # Level 2: "What does A believe about B?"
        level2_beliefs = self._infer_level2_beliefs(agent_id, about_agent_id, observations)
        beliefs.extend(level2_beliefs)
        evidence.append(f"استنتاج من المستوى 2: {len(level2_beliefs)} معتقد")

        # Level 3: "What does A believe that B believes about A?"
        if depth >= 3:
            level3_beliefs = self._infer_level3_beliefs(
                agent_id, about_agent_id, observations, level2_beliefs
            )
            beliefs.extend(level3_beliefs)
            evidence.append(f"استنتاج من المستوى 3: {len(level3_beliefs)} معتقد")

        # Compute confidence with exponential decay
        confidence = self.CONFIDENCE_BASE * (self.CONFIDENCE_DECAY ** (depth - 1))
        confidence = max(self.MIN_CONFIDENCE, confidence)

        # Adjust based on evidence strength
        if obs_count > 5:
            confidence = min(1.0, confidence * 1.2)

        model = NestedBeliefModel(
            model_id=f"nbm_{self._model_counter:04d}",
            subject_id=agent_id,
            about_id=about_agent_id,
            depth=depth,
            beliefs=beliefs,
            confidence=confidence,
            last_updated=time.time(),
            evidence=evidence,
        )

        self._models[model.model_id] = model
        return model

    def detect_deception_risk(self, model: NestedBeliefModel) -> DeceptionRiskLevel:
        """
        كشف خطر الخداع من نموذج المعتقدات المتداخلة.
        
        Deception indicators:
        - Mismatch between stated and inferred beliefs
        - High depth beliefs about concealment
        - Contradictory nested beliefs
        """
        if not TOM_ADVANCED_ENABLED:
            return DeceptionRiskLevel.NONE

        deception_score = 0.0

        # Check for deception indicators in beliefs
        for belief in model.beliefs:
            for indicator in self.DECEPTION_INDICATORS:
                if indicator in belief.lower():
                    deception_score += 0.3
                    break

        # Higher depth increases uncertainty
        if model.depth >= 3:
            deception_score += 0.1

        # Low confidence suggests potential deception
        if model.confidence < 0.3:
            deception_score += 0.2

        # Map score to risk level
        if deception_score >= 0.7:
            return DeceptionRiskLevel.CRITICAL
        elif deception_score >= 0.5:
            return DeceptionRiskLevel.HIGH
        elif deception_score >= 0.3:
            return DeceptionRiskLevel.MEDIUM
        elif deception_score > 0.0:
            return DeceptionRiskLevel.LOW
        return DeceptionRiskLevel.NONE

    def predict_behavior_from_nested(
        self, agent_id: str, model: NestedBeliefModel, situation: dict
    ) -> list[PredictedAction]:
        """
        تنبؤ سلوك الوكيل بناءً على معتقداته المتداخلة.
        """
        if not TOM_ADVANCED_ENABLED:
            return []

        predictions = []

        for belief in model.beliefs[:5]:
            action = self._belief_to_action(belief, situation)
            if action:
                prob = model.confidence * 0.8
                predictions.append(PredictedAction(
                    action=action,
                    probability=prob,
                    reasoning=f"بناءً على: {belief[:60]}",
                ))

        # Sort by probability
        predictions.sort(key=lambda p: p.probability, reverse=True)
        return predictions[:5]

    # ═══════════════════════════════════════════════════════════════════════
    # Internal Methods
    # ═══════════════════════════════════════════════════════════════════════

    def _infer_level2_beliefs(
        self, agent_id: str, about_id: str, observations: list[dict]
    ) -> list[str]:
        """استنتاج معتقدات المستوى 2: ماذا يعتقد A عن B؟"""
        beliefs = []

        for obs in observations:
            action = obs.get("action", "")
            stated = obs.get("stated_intention", "")
            context = obs.get("context", "")

            if stated:
                beliefs.append(f"{agent_id} يعتقد أن {about_id} ينوي: {stated}")

            if action:
                consistency = obs.get("consistency_score", 1.0)
                if consistency < 0.5:
                    beliefs.append(
                        f"{agent_id} يعتقد أن {about_id} يخفي شيئاً (سلوك غير متسق: {action[:40]})"
                    )
                else:
                    beliefs.append(f"{agent_id} يعتقد أن {about_id} يسعى لـ: {action[:40]}")

            if context:
                beliefs.append(f"{agent_id} يعتقد أن {about_id} يعمل في سياق: {context[:40]}")

        return beliefs[:10]

    def _infer_level3_beliefs(
        self,
        agent_id: str,
        about_id: str,
        observations: list[dict],
        level2_beliefs: list[str],
    ) -> list[str]:
        """استنتاج معتقدات المستوى 3: ماذا يعتقد A أن B يعتقد عن A؟"""
        beliefs = []

        # From Level 2 beliefs, infer Level 3
        for l2 in level2_beliefs[:3]:
            # Simple transformation: "A believes B wants X" →
            # "A believes B believes A knows about X"
            if "ينوي" in l2:
                beliefs.append(
                    f"{agent_id} يعتقد أن {about_id} يعتقد أن {agent_id} يعرف عن نواياه"
                )
            elif "يخفي" in l2:
                beliefs.append(
                    f"{agent_id} يعتقد أن {about_id} يعتقد أن {agent_id} لا يعلم ما يخفيه"
                )

        # From observations directly
        for obs in observations[:2]:
            action = obs.get("action", "")
            if action:
                beliefs.append(
                    f"{agent_id} يعتقد أن {about_id} يعتقد أن {agent_id} سيتفاعل مع: {action[:30]}"
                )

        return beliefs[:5]

    @staticmethod
    def _belief_to_action(belief: str, situation: dict) -> Optional[str]:
        """حوّل معتقد إلى إجراء متوقع"""
        if "ينوي" in belief:
            return "التعاون مع النية المعلنة"
        elif "يخفي" in belief:
            return "التحقق من المعلومات قبل التصرف"
        elif "يعرف" in belief:
            return "التصرف بناءً على المعرفة المشتركة"
        elif "سياق" in belief:
            return "مراعاة السياق في الرد"
        return None

    def get_model(self, model_id: str) -> Optional[NestedBeliefModel]:
        """احصل على نموذج محدد"""
        return self._models.get(model_id)

    def get_all_models(self) -> list[NestedBeliefModel]:
        """احصل على جميع النماذج"""
        return list(self._models.values())

    @property
    def stats(self) -> dict:
        return {
            "total_models": len(self._models),
            "max_depth": self.max_depth,
            "enabled": TOM_ADVANCED_ENABLED,
        }
