"""
BABSHARQII v9.0 — Belief Store
مستودع المعتقدات — يحتفظ بمعتقدات ورغبات ونوايا المستخدمين مع تحديث تلقائي

Implements a dynamic Theory of Mind by tracking users' mental states
across conversations. Updates beliefs, desires, and intentions as new
information becomes available.

Feature Flag: MAMOUN_DYNTOM_MODE (default: false)
"""

from __future__ import annotations

import os
import json
import time
import logging
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

DYNTOM_MODE_ENABLED: bool = os.environ.get(
    "MAMOUN_DYNTOM_MODE", "false"
).lower() in ("true", "1", "yes")


class MentalStateType(Enum):
    """أنواع الحالات العقلية"""
    BELIEF = "belief"            # معتقد — ما يعتقده المستخدم
    DESIRE = "desire"            # رغبة — ما يريده المستخدم
    INTENTION = "intention"      # نية — ما ينوي المستخدم فعله
    EMOTION = "emotion"          # عاطفة — ما يشعر به المستخدم
    KNOWLEDGE = "knowledge"      # معرفة — ما يعرفه المستخدم


class CertaintyLevel(Enum):
    """مستويات اليقين"""
    CERTAIN = "certain"          # متأكد (شاهد بنفسه)
    LIKELY = "likely"            # مرجح
    UNCERTAIN = "uncertain"      # غير متأكد
    FALSE_BELIEF = "false_belief"  # معتقد خاطئ


@dataclass
class MentalState:
    """حالة عقلية واحدة"""
    state_id: str = ""
    user_id: str = ""
    state_type: MentalStateType = MentalStateType.BELIEF
    content: str = ""                    # محتوى الحالة العقلية
    certainty: CertaintyLevel = CertaintyLevel.LIKELY
    source: str = ""                     # مصدر المعلومة
    timestamp: float = 0.0
    last_updated: float = 0.0
    update_count: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class UserMentalModel:
    """نموذج عقلي كامل لمستخدم"""
    user_id: str = ""
    beliefs: list[MentalState] = field(default_factory=list)
    desires: list[MentalState] = field(default_factory=list)
    intentions: list[MentalState] = field(default_factory=list)
    emotions: list[MentalState] = field(default_factory=list)
    knowledge: list[MentalState] = field(default_factory=list)
    conversation_history: list[dict] = field(default_factory=list)
    last_interaction: float = 0.0


class BeliefStore:
    """
    مستودع المعتقدات — يُدير النماذج العقلية للمستخدمين

    Architecture:
      ┌─────────────────────────────────────────────────────────────────┐
      │                      BeliefStore                              │
      │                                                               │
      │  User A ──── UserMentalModel ──── beliefs/desires/intentions │
      │  User B ──── UserMentalModel ──── beliefs/desires/intentions │
      │  ...                                                          │
      │                                                               │
      │  update_from_utterance() ──── تحديث تلقائي من الكلام        │
      │  resolve_false_beliefs() ─── كشف المعتقدات الخاطئة          │
      │  predict_action() ───────── توقع السلوك                     │
      │  get_perspective() ──────── تبنّي منظور المستخدم            │
      └─────────────────────────────────────────────────────────────────┘
    """

    def __init__(self, persist_path: Optional[str] = None):
        self._models: dict[str, UserMentalModel] = {}
        self._persist_path = persist_path
        if persist_path:
            self._load(persist_path)

    def get_or_create_model(self, user_id: str) -> UserMentalModel:
        """احصل على النموذج العقلي أو أنشئه"""
        if user_id not in self._models:
            self._models[user_id] = UserMentalModel(
                user_id=user_id,
                last_interaction=time.time(),
            )
        return self._models[user_id]

    def add_mental_state(self, user_id: str, state: MentalState) -> None:
        """أضف حالة عقلية للمستخدم"""
        model = self.get_or_create_model(user_id)
        state.user_id = user_id
        state.timestamp = time.time()
        state.last_updated = time.time()
        state.update_count = 1

        if state.state_type == MentalStateType.BELIEF:
            model.beliefs.append(state)
        elif state.state_type == MentalStateType.DESIRE:
            model.desires.append(state)
        elif state.state_type == MentalStateType.INTENTION:
            model.intentions.append(state)
        elif state.state_type == MentalStateType.EMOTION:
            model.emotions.append(state)
        elif state.state_type == MentalStateType.KNOWLEDGE:
            model.knowledge.append(state)

        model.last_interaction = time.time()
        self._auto_persist()

    def update_from_utterance(
        self, user_id: str, utterance: str, context: dict = None
    ) -> list[MentalState]:
        """
        حدّث النموذج العقلي بناءً على كلام المستخدم.

        Extracts mental state indicators from the utterance and updates
        the user's mental model accordingly.
        """
        if not DYNTOM_MODE_ENABLED:
            return []

        model = self.get_or_create_model(user_id)
        extracted_states = []

        # Record conversation
        model.conversation_history.append({
            "utterance": utterance,
            "context": context or {},
            "timestamp": time.time(),
        })

        # Extract beliefs (أعتقد، أظن، في رأيي، أرى أن)
        belief_indicators = ["أعتقد", "أظن", "في رأيي", "أرى أن", "متأكد أن", "أعرف أن"]
        for indicator in belief_indicators:
            if indicator in utterance:
                content = utterance.split(indicator, 1)[-1].strip()
                if content:
                    state = MentalState(
                        state_id=f"bel_{int(time.time()*1000)}_{len(model.beliefs)}",
                        state_type=MentalStateType.BELIEF,
                        content=content,
                        certainty=CertaintyLevel.LIKELY,
                        source="utterance",
                    )
                    extracted_states.append(state)
                    model.beliefs.append(state)
                break

        # Extract desires (أريد، أتمنى، أحتاج، أرغب)
        desire_indicators = ["أريد", "أتمنى", "أحتاج", "أرغب", "أود", "ليت"]
        for indicator in desire_indicators:
            if indicator in utterance:
                content = utterance.split(indicator, 1)[-1].strip()
                if content:
                    state = MentalState(
                        state_id=f"des_{int(time.time()*1000)}_{len(model.desires)}",
                        state_type=MentalStateType.DESIRE,
                        content=content,
                        certainty=CertaintyLevel.CERTAIN,
                        source="utterance",
                    )
                    extracted_states.append(state)
                    model.desires.append(state)
                break

        # Extract intentions (سأفعل، أنوي، خطتي، سأذهب)
        intention_indicators = ["سأفعل", "أنوي", "خطتي", "سأذهب", "سأبدأ", "نويت"]
        for indicator in intention_indicators:
            if indicator in utterance:
                content = utterance.split(indicator, 1)[-1].strip()
                if content:
                    state = MentalState(
                        state_id=f"int_{int(time.time()*1000)}_{len(model.intentions)}",
                        state_type=MentalStateType.INTENTION,
                        content=content,
                        certainty=CertaintyLevel.LIKELY,
                        source="utterance",
                    )
                    extracted_states.append(state)
                    model.intentions.append(state)
                break

        model.last_interaction = time.time()
        self._auto_persist()
        return extracted_states

    def resolve_false_beliefs(self, user_id: str, reality: dict) -> list[MentalState]:
        """
        كشف المعتقدات الخاطئة — قارن معتقدات المستخدم بالواقع الفعلي.

        Returns list of false beliefs that were identified and updated.
        """
        model = self.get_or_create_model(user_id)
        false_beliefs = []

        for belief in model.beliefs:
            # Check if belief content contradicts known reality
            for key, value in reality.items():
                if key in belief.content and str(value) not in belief.content:
                    # Mark as false belief
                    belief.certainty = CertaintyLevel.FALSE_BELIEF
                    belief.last_updated = time.time()
                    belief.update_count += 1
                    false_beliefs.append(belief)
                    break

        self._auto_persist()
        return false_beliefs

    def predict_action(self, user_id: str, situation: str) -> Optional[str]:
        """
        توقّع سلوك المستخدم بناءً على نموذجه العقلي.

        Uses the user's desires and intentions to predict their likely
        behavior in a given situation.
        """
        model = self.get_or_create_model(user_id)

        # Check active intentions first
        active_intentions = [
            i for i in model.intentions
            if i.certainty in (CertaintyLevel.CERTAIN, CertaintyLevel.LIKELY)
        ]
        if active_intentions:
            # Return the most recent intention
            latest = max(active_intentions, key=lambda x: x.timestamp)
            return f"بناءً على نيته: {latest.content}"

        # Check desires
        active_desires = [
            d for d in model.desires
            if d.certainty in (CertaintyLevel.CERTAIN, CertaintyLevel.LIKELY)
        ]
        if active_desires:
            latest = max(active_desires, key=lambda x: x.timestamp)
            return f"بناءً على رغبته: {latest.content}"

        # Fallback: predict based on beliefs
        if model.beliefs:
            return "لا يمكن التوقع بدقة — معتقدات غير كافية"

        return None

    def get_perspective(self, user_id: str) -> dict:
        """
        احصل على منظور المستخدم — ماذا يرى/يعتقد/يريد.

        Returns a summary of the user's mental model from their perspective.
        """
        model = self.get_or_create_model(user_id)
        return {
            "beliefs": [
                {"content": b.content, "certainty": b.certainty.value}
                for b in model.beliefs
            ],
            "desires": [
                {"content": d.content, "certainty": d.certainty.value}
                for d in model.desires
            ],
            "intentions": [
                {"content": i.content, "certainty": i.certainty.value}
                for i in model.intentions
            ],
            "emotion": model.emotions[-1].content if model.emotions else "unknown",
            "interaction_count": len(model.conversation_history),
        }

    def _auto_persist(self) -> None:
        """احفظ تلقائياً إذا تم تعيين مسار الحفظ"""
        if self._persist_path:
            self._save(self._persist_path)

    def _save(self, path: str) -> None:
        """احفظ المستودع"""
        data = {}
        for uid, model in self._models.items():
            data[uid] = {
                "beliefs": [
                    {"content": b.content, "certainty": b.certainty.value, "source": b.source}
                    for b in model.beliefs
                ],
                "desires": [
                    {"content": d.content, "certainty": d.certainty.value}
                    for d in model.desires
                ],
                "intentions": [
                    {"content": i.content, "certainty": i.certainty.value}
                    for i in model.intentions
                ],
            }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self, path: str) -> None:
        """حمّل المستودع المحفوظ"""
        if not Path(path).exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for uid, model_data in data.items():
                model = self.get_or_create_model(uid)
                for b in model_data.get("beliefs", []):
                    model.beliefs.append(MentalState(
                        state_type=MentalStateType.BELIEF,
                        content=b["content"],
                        certainty=CertaintyLevel(b.get("certainty", "likely")),
                        source=b.get("source", ""),
                    ))
        except Exception as e:
            logger.warning(f"Failed to load belief store: {e}")
