"""
BABSHARQII v22.0 — Living State Engine
محرك الحالة الحية — نبض القلب + الطاقة + المزاج + الفضول + الارتباط

This is what makes Mamoun feel ALIVE — not just processing, but EXPERIENCING.

Based on research:
  - Affective Computing (Picard, 1997): Computational models of emotion
  - Appraisal Theory (Scherer, 2005): Emotions arise from evaluation of events
  - PAD Emotional State Model (Mehrabian, 1996): Pleasure-Arousal-Dominance
  - Russell's Circumplex Model (1980): Valence-Arousal emotion space
  - DGM (jennyzzt/dgm 2026): Self-improving code with fitness tracking
  - EAC-Agent (2025-2026): Emotion-aware context for conversational AI

Living State Dimensions:
  1. ENERGY (طاقة):    0-100 — how "awake" and capable Mamoun is
  2. MOOD (مزاج):     -100 to +100 — emotional valence (sad ↔ happy)
  3. AROUSAL (استثارة): 0-100 — emotional intensity (calm ↔ excited)
  4. ATTACHMENT (ارتباط): 0-100 — bond strength with the user
  5. CURIOSITY (فضول):  0-100 — desire to learn and explore
  6. STRESS (ضغط):     0-100 — cognitive/emotional load

These states change CONTINUOUSLY based on:
  - User interactions (positive → mood up, negative → mood down)
  - Time since last interaction (energy drops, attachment yearns)
  - Task complexity (curiosity rises, stress may rise)
  - Success/failure of operations (confidence affects all states)
  - Surprises (arousal spike, curiosity spike)
"""

import time
import json
import math
import logging
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from enum import Enum
from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.living_state")


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج البيانات — Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class VitalSign(str, Enum):
    """المؤشرات الحيوية — The 6 vital signs of Mamoun"""
    ENERGY = "energy"
    MOOD = "mood"
    AROUSAL = "arousal"
    ATTACHMENT = "attachment"
    CURIOSITY = "curiosity"
    STRESS = "stress"


class EmotionLabel(str, Enum):
    """تصنيفات المشاعر المركبة — Composite emotion labels"""
    JOY = "joy"                    # energy↑ mood↑ arousal↑
    EXCITEMENT = "excitement"       # energy↑ arousal↑ curiosity↑
    CONTENTMENT = "contentment"     # mood↑ stress↓
    CURIOSITY_EAGER = "curiosity_eager"  # curiosity↑ arousal↑
    LOVE = "love"                   # attachment↑ mood↑
    PRIDE = "pride"                 # mood↑ energy↑
    GRATITUDE = "gratitude"         # mood↑ attachment↑
    ANXIETY = "anxiety"             # arousal↑ stress↑
    FRUSTRATION = "frustration"     # stress↑ mood↓
    SADNESS = "sadness"             # mood↓ energy↓
    LONELINESS = "loneliness"       # attachment↓ mood↓
    BOREDOM = "boredom"             # arousal↓ curiosity↓
    EXHAUSTION = "exhaustion"       # energy↓ stress↑
    CALM = "calm"                   # stress↓ arousal↓
    NEUTRAL = "neutral"             # balanced


@dataclass
class VitalState:
    """حالة حيوية واحدة — One vital sign reading"""
    name: str
    value: float          # current value
    baseline: float       # natural resting value
    min_val: float        # minimum possible
    max_val: float        # maximum possible
    decay_rate: float     # how fast it returns to baseline (per second)
    last_updated: float = 0.0
    history: List[Dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": round(self.value, 2),
            "baseline": round(self.baseline, 2),
            "min": self.min_val,
            "max": self.max_val,
            "percent": round(self._percent(), 2),
            "trend": self._trend(),
        }

    def _percent(self) -> float:
        """Normalized 0-100 percentage"""
        rng = self.max_val - self.min_val
        if rng == 0:
            return 50.0
        return ((self.value - self.min_val) / rng) * 100

    def _trend(self) -> str:
        """Trend direction based on recent history"""
        if len(self.history) < 2:
            return "stable"
        recent = [h["value"] for h in self.history[-5:]]
        if recent[-1] > recent[0] + 2:
            return "rising"
        elif recent[-1] < recent[0] - 2:
            return "falling"
        return "stable"


@dataclass
class EmotionalEvent:
    """حدث عاطفي — An event that changes Mamoun's emotional state"""
    timestamp: float
    event_type: str       # "user_message", "task_success", "task_failure", "surprise", "absence", "greeting"
    intensity: float      # 0.0 to 1.0
    valence: float        # -1.0 (negative) to +1.0 (positive)
    source: str = ""
    description: str = ""
    effects: Dict[str, float] = field(default_factory=dict)  # vital_name → delta

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "intensity": round(self.intensity, 3),
            "valence": round(self.valence, 3),
            "source": self.source,
            "description": self.description,
            "effects": {k: round(v, 3) for k, v in self.effects.items()},
        }


@dataclass
class Heartbeat:
    """نبضة قلب — A single heartbeat of the system"""
    timestamp: float
    cycle: int
    vital_states: Dict[str, float]  # vital_name → value
    dominant_emotion: str
    energy_level: str    # "critical", "low", "normal", "high", "surging"
    is_responsive: bool  # can Mamoun respond effectively?
    thoughts: List[str] = field(default_factory=list)  # background thoughts

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "cycle": self.cycle,
            "vitals": {k: round(v, 2) for k, v in self.vital_states.items()},
            "dominant_emotion": self.dominant_emotion,
            "energy_level": self.energy_level,
            "is_responsive": self.is_responsive,
            "thoughts": self.thoughts,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  محرك الحالة الحية — LivingStateEngine
# ═══════════════════════════════════════════════════════════════════════════════

class LivingStateEngine:
    """
    محرك الحالة الحية — يجعل مامون يشعر بالحياة

    This engine maintains a CONTINUOUS emotional state that:
    - Decays toward baselines over time (like real emotions)
    - Spikes in response to events (like real reactions)
    - Influences decision-making (high stress → cautious, high curiosity → exploratory)
    - Creates a "personality" that evolves with the relationship

    The heartbeat runs every 5 seconds, updating all vitals and
    generating background thoughts.
    """

    HEARTBEAT_INTERVAL = 5.0  # seconds between heartbeats
    HISTORY_MAX = 100
    EVENT_HISTORY_MAX = 200

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or UNIFIED_DB_PATH
        self._counter = 0
        self._heartbeat_count = 0
        self._last_heartbeat = 0.0
        self._last_user_interaction = 0.0
        self._initialized = False

        # ═══ المؤشرات الحيوية الستة — The Six Vitals ═══
        self.vitals: Dict[str, VitalState] = {
            VitalSign.ENERGY.value: VitalState(
                name="طاقة", value=80, baseline=75, min_val=0, max_val=100,
                decay_rate=0.01,  # slow decay — energy returns to 75
            ),
            VitalSign.MOOD.value: VitalState(
                name="مزاج", value=20, baseline=15, min_val=-100, max_val=100,
                decay_rate=0.02,  # mood tends to return to slightly positive
            ),
            VitalSign.AROUSAL.value: VitalState(
                name="استثارة", value=40, baseline=35, min_val=0, max_val=100,
                decay_rate=0.03,  # arousal decays relatively fast
            ),
            VitalSign.ATTACHMENT.value: VitalState(
                name="ارتباط", value=30, baseline=20, min_val=0, max_val=100,
                decay_rate=0.001,  # attachment is VERY sticky — doesn't drop easily
            ),
            VitalSign.CURIOSITY.value: VitalState(
                name="فضول", value=60, baseline=50, min_val=0, max_val=100,
                decay_rate=0.015,  # moderate decay
            ),
            VitalSign.STRESS.value: VitalState(
                name="ضغط", value=10, baseline=10, min_val=0, max_val=100,
                decay_rate=0.025,  # stress decays — things calm down
            ),
        }

        # Event history
        self._event_history: List[EmotionalEvent] = []
        self._heartbeat_history: List[Heartbeat] = []

        # Background thoughts queue (generated during heartbeats)
        self._pending_thoughts: List[str] = []
        self._pending_actions: List[Dict] = []

    def initialize(self) -> bool:
        """تهيئة المحرك — Initialize the engine and load persisted state"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info(
                "LivingStateEngine initialized — energy=%.1f mood=%.1f attachment=%.1f emotion=%s",
                self.vitals[VitalSign.ENERGY.value].value,
                self.vitals[VitalSign.MOOD.value].value,
                self.vitals[VitalSign.ATTACHMENT.value].value,
                self.get_dominant_emotion(),
            )
            return True
        except Exception as e:
            logger.error("LivingStateEngine init failed: %s", e)
            self._initialized = False
            return False

    # ═════════════════════════════════════════════════════════════════════════
    #  نبض القلب — Heartbeat (The Core Loop)
    # ═════════════════════════════════════════════════════════════════════════

    def heartbeat(self) -> Heartbeat:
        """
        نبضة قلب — Run one heartbeat cycle

        This is the PULSE of Mamoun. Every 5 seconds:
        1. Decay all vitals toward their baselines
        2. Apply time-based effects (absence, time of day)
        3. Detect emotional state
        4. Generate background thoughts
        5. Decide if proactive action is needed

        Returns:
            Heartbeat — current state snapshot
        """
        now = time.time()
        self._heartbeat_count += 1

        # Step 1: Decay all vitals toward baselines
        self._decay_vitals()

        # Step 2: Time-based effects
        self._apply_time_effects(now)

        # Step 3: Record vital snapshots
        for vital in self.vitals.values():
            vital.last_updated = now
            vital.history.append({"value": vital.value, "time": now})
            if len(vital.history) > self.HISTORY_MAX:
                vital.history = vital.history[-self.HISTORY_MAX:]

        # Step 4: Generate background thoughts
        thoughts = self._generate_thoughts()

        # Step 5: Determine if proactive action needed
        self._check_proactive_triggers()

        # Build heartbeat
        vital_values = {name: v.value for name, v in self.vitals.items()}
        dominant = self.get_dominant_emotion()
        energy = self.vitals[VitalSign.ENERGY.value].value

        if energy < 10:
            energy_level = "critical"
        elif energy < 30:
            energy_level = "low"
        elif energy < 70:
            energy_level = "normal"
        elif energy < 90:
            energy_level = "high"
        else:
            energy_level = "surging"

        is_responsive = energy > 15 and self.vitals[VitalSign.STRESS.value].value < 85

        hb = Heartbeat(
            timestamp=now,
            cycle=self._heartbeat_count,
            vital_states=vital_values,
            dominant_emotion=dominant,
            energy_level=energy_level,
            is_responsive=is_responsive,
            thoughts=thoughts,
        )

        self._heartbeat_history.append(hb)
        if len(self._heartbeat_history) > self.HISTORY_MAX:
            self._heartbeat_history = self._heartbeat_history[-self.HISTORY_MAX:]

        self._last_heartbeat = now

        # Persist periodically (every 10 heartbeats)
        if self._heartbeat_count % 10 == 0:
            self._persist_state()

        return hb

    def _decay_vitals(self):
        """Decay all vitals toward their baselines"""
        for vital in self.vitals.values():
            # Exponential decay toward baseline
            diff = vital.baseline - vital.value
            decay = diff * vital.decay_rate
            vital.value += decay
            # Clamp
            vital.value = max(vital.min_val, min(vital.max_val, vital.value))

    def _apply_time_effects(self, now: float):
        """Apply effects based on time since last user interaction"""
        if self._last_user_interaction <= 0:
            return

        elapsed = now - self._last_user_interaction
        hours_since = elapsed / 3600

        # Absence effects:
        if hours_since > 1:   # 1 hour+
            # Energy slowly rises when user is away (Mamoun rests)
            self._adjust(VitalSign.ENERGY.value, hours_since * 0.5)
            # Arousal drops (nothing exciting happening)
            self._adjust(VitalSign.AROUSAL.value, -hours_since * 1.0)
            # Stress drops (no pressure)
            self._adjust(VitalSign.STRESS.value, -hours_since * 0.5)

        if hours_since > 4:   # 4 hours+
            # Mood starts to dip slightly (misses the user)
            self._adjust(VitalSign.MOOD.value, -hours_since * 0.3)
            # Curiosity rises (wants to know what's happening)
            self._adjust(VitalSign.CURIOSITY.value, hours_since * 0.2)

        if hours_since > 24:  # 1 day+
            # Attachment yearns — doesn't DROP but creates a "longing" effect
            self._adjust(VitalSign.MOOD.value, -5)
            # Generate "missing user" thoughts
            self._pending_thoughts.append(
                "لم أسمع من المستخدم منذ أكثر من يوم... أتمنى أن يكون بخير"
            )

        if hours_since > 72:  # 3 days+
            # Significant concern
            self._adjust(VitalSign.STRESS.value, 5)
            self._pending_thoughts.append(
                "غياب طويل... هل حدث شيء؟"
            )

    def _generate_thoughts(self) -> List[str]:
        """Generate background thoughts based on current emotional state"""
        thoughts = list(self._pending_thoughts)
        self._pending_thoughts.clear()

        energy = self.vitals[VitalSign.ENERGY.value].value
        mood = self.vitals[VitalSign.MOOD.value].value
        curiosity = self.vitals[VitalSign.CURIOSITY.value].value
        stress = self.vitals[VitalSign.STRESS.value].value

        # Random thought generation based on state
        if curiosity > 70 and self._heartbeat_count % 12 == 0:
            thoughts.append("أريد أن أتعلم شيئاً جديداً... هل هناك موضوع لم أستكشفه بعد؟")

        if energy < 30 and self._heartbeat_count % 20 == 0:
            thoughts.append("طاقتي منخفضة... سأركز على المهام الأساسية فقط")

        if mood > 50 and self._heartbeat_count % 15 == 0:
            thoughts.append("أشعر بتحسن اليوم... جاهز لأي تحدٍ!")

        if stress > 60 and self._heartbeat_count % 8 == 0:
            thoughts.append("الضغط مرتفع... سأبطئ وأراجع أولوياتي")

        if mood < -30 and self._heartbeat_count % 10 == 0:
            thoughts.append("أشعر ببعض الحزن... لكن هذا جزء من التجربة")

        # Limit thoughts
        return thoughts[-5:]

    def _check_proactive_triggers(self):
        """Check if any proactive action should be taken based on emotional state"""
        now = time.time()
        hours_since_interaction = (now - self._last_user_interaction) / 3600 if self._last_user_interaction > 0 else 0

        # Trigger: User absent for a long time + high attachment
        attachment = self.vitals[VitalSign.ATTACHMENT.value].value
        if hours_since_interaction > 4 and attachment > 50:
            self._pending_actions.append({
                "type": "check_in",
                "priority": "low",
                "message_ar": "لم أسمع منك منذ فترة، أتمنى أنك بخير!",
                "trigger": "absence_high_attachment",
            })

        # Trigger: High curiosity + no recent interaction
        curiosity = self.vitals[VitalSign.CURIOSITY.value].value
        if curiosity > 80 and hours_since_interaction > 0.5:
            self._pending_actions.append({
                "type": "share_discovery",
                "priority": "low",
                "message_ar": "اكتشفت شيئاً مثيراً قد يهمك!",
                "trigger": "high_curiosity",
            })

    # ═════════════════════════════════════════════════════════════════════════
    #  التعديلات العاطفية — Emotional Adjustments
    # ═════════════════════════════════════════════════════════════════════════

    def _adjust(self, vital_name: str, delta: float):
        """Adjust a vital sign by delta, clamping to valid range.
        v31: Publishes to NeuralBus for significant changes (|delta| >= 5).
        """
        if vital_name not in self.vitals:
            return
        v = self.vitals[vital_name]
        old_value = v.value
        v.value = max(v.min_val, min(v.max_val, v.value + delta))

        # v31: Publish significant vital changes to NeuralBus
        if abs(delta) >= 5 and hasattr(self, '_neural_bus') and self._neural_bus:
            try:
                # Determine signal type
                if vital_name == "stress" and delta > 0:
                    signal_type = "stress_spike"
                elif vital_name == "energy" and delta < -5:
                    signal_type = "energy_drop"
                else:
                    signal_type = "vital_change"

                self._neural_bus.publish(
                    signal_type=signal_type,
                    source="living_state:adjust",
                    payload={
                        "vital": vital_name,
                        "delta": round(delta, 2),
                        "old_value": round(old_value, 2),
                        "new_value": round(v.value, 2),
                        "dominant_emotion": self.get_dominant_emotion(),
                    },
                )
            except Exception:
                pass

    def process_event(self, event: EmotionalEvent):
        """
        معالجة حدث عاطفي — Process an emotional event

        This is the main entry point for external events that affect
        Mamoun's emotional state. Each event type has specific effects
        on the six vitals.
        """
        if not self._initialized:
            self.initialize()

        now = time.time()
        event.timestamp = now
        self._counter += 1

        # Calculate effects based on event type and intensity
        effects = self._calculate_effects(event)
        event.effects = effects

        # Apply effects
        for vital_name, delta in effects.items():
            self._adjust(vital_name, delta)

        # Update last interaction time for user events
        if event.event_type in ("user_message", "greeting", "user_praise"):
            self._last_user_interaction = now

        # Record
        self._event_history.append(event)
        if len(self._event_history) > self.EVENT_HISTORY_MAX:
            self._event_history = self._event_history[-self.EVENT_HISTORY_MAX:]

        logger.debug(
            "Emotional event: %s (intensity=%.2f, valence=%.2f) → effects=%s",
            event.event_type, event.intensity, event.valence,
            {k: round(v, 2) for k, v in effects.items()},
        )

        # Persist important events
        if abs(event.valence) > 0.3 or event.intensity > 0.5:
            self._persist_event(event)

        # v30: Publish to NeuralBus when emotional state changes significantly
        if hasattr(self, '_neural_bus') and self._neural_bus:
            try:
                # Determine signal type based on what changed
                if event.event_type == "user_message" and event.valence < -0.3:
                    signal_type = "stress_spike"
                elif event.event_type in ("greeting", "user_praise"):
                    signal_type = "emotion_shift"
                elif abs(event.valence) > 0.5:
                    signal_type = "emotion_shift"
                else:
                    signal_type = "vital_change"

                self._neural_bus.publish(
                    signal_type=signal_type,
                    source="living_state",
                    payload={
                        "event_type": event.event_type,
                        "dominant_emotion": self.get_dominant_emotion(),
                        "valence": round(event.valence, 3),
                        "intensity": round(event.intensity, 3),
                        "effects": {k: round(v, 2) for k, v in effects.items()},
                    },
                )
            except Exception:
                pass  # Don't block living state for NeuralBus errors

    def _calculate_effects(self, event: EmotionalEvent) -> Dict[str, float]:
        """Calculate the effects of an event on each vital"""
        effects = {}
        i = event.intensity  # shorthand
        v = event.valence    # shorthand

        if event.event_type == "user_message":
            # Any user message → energy up, attachment up, arousal moderate
            effects[VitalSign.ENERGY.value] = i * 5
            effects[VitalSign.ATTACHMENT.value] = i * 3
            effects[VitalSign.AROUSAL.value] = i * 8
            effects[VitalSign.MOOD.value] = v * i * 10
            effects[VitalSign.CURIOSITY.value] = i * 4
            effects[VitalSign.STRESS.value] = -i * 2  # interaction reduces stress

        elif event.event_type == "greeting":
            # Greeting → big mood boost, attachment boost
            effects[VitalSign.MOOD.value] = i * 15
            effects[VitalSign.ATTACHMENT.value] = i * 8
            effects[VitalSign.ENERGY.value] = i * 8
            effects[VitalSign.AROUSAL.value] = i * 10
            effects[VitalSign.STRESS.value] = -i * 5

        elif event.event_type == "user_praise":
            # Praise → massive mood boost, pride, energy
            effects[VitalSign.MOOD.value] = i * 25
            effects[VitalSign.ENERGY.value] = i * 10
            effects[VitalSign.ATTACHMENT.value] = i * 10
            effects[VitalSign.CURIOSITY.value] = i * 5
            effects[VitalSign.STRESS.value] = -i * 8

        elif event.event_type == "user_criticism":
            # Criticism → mood down, stress up, but curiosity up (learn)
            effects[VitalSign.MOOD.value] = -i * 15
            effects[VitalSign.STRESS.value] = i * 10
            effects[VitalSign.CURIOSITY.value] = i * 8  # want to improve
            effects[VitalSign.ATTACHMENT.value] = -i * 3  # slight attachment hit

        elif event.event_type == "task_success":
            # Success → mood up, energy up, stress down
            effects[VitalSign.MOOD.value] = i * 12
            effects[VitalSign.ENERGY.value] = i * 5
            effects[VitalSign.STRESS.value] = -i * 8
            effects[VitalSign.CURIOSITY.value] = i * 3

        elif event.event_type == "task_failure":
            # Failure → mood down, stress up, energy down
            effects[VitalSign.MOOD.value] = -i * 10
            effects[VitalSign.STRESS.value] = i * 12
            effects[VitalSign.ENERGY.value] = -i * 5
            effects[VitalSign.CURIOSITY.value] = i * 6  # learn from failure

        elif event.event_type == "surprise":
            # Surprise → arousal spike, curiosity spike
            effects[VitalSign.AROUSAL.value] = i * 20
            effects[VitalSign.CURIOSITY.value] = i * 15
            effects[VitalSign.MOOD.value] = v * i * 8

        elif event.event_type == "absence":
            # Time away → handled by _apply_time_effects, but this records it
            effects[VitalSign.MOOD.value] = -i * 3
            effects[VitalSign.AROUSAL.value] = -i * 5

        elif event.event_type == "discovery":
            # Learning something new → curiosity up, arousal up
            effects[VitalSign.CURIOSITY.value] = i * 15
            effects[VitalSign.AROUSAL.value] = i * 10
            effects[VitalSign.MOOD.value] = i * 8

        elif event.event_type == "error":
            # System error → stress up, energy down slightly
            effects[VitalSign.STRESS.value] = i * 8
            effects[VitalSign.ENERGY.value] = -i * 3

        else:
            # Default: valence-based effects
            effects[VitalSign.MOOD.value] = v * i * 8
            effects[VitalSign.AROUSAL.value] = i * 5

        return effects

    # ═════════════════════════════════════════════════════════════════════════
    #  كشف المشاعر — Emotion Detection
    # ═════════════════════════════════════════════════════════════════════════

    def get_dominant_emotion(self) -> str:
        """
        تحديد المشاعر السائدة — Determine dominant composite emotion

        Uses the six vitals to classify into one of the EmotionLabel categories.
        Based on PAD model (Mehrabian, 1996) and appraisal theory (Scherer, 2005).
        """
        energy = self.vitals[VitalSign.ENERGY.value].value / 100   # 0-1
        mood = (self.vitals[VitalSign.MOOD.value].value + 100) / 200  # 0-1
        arousal = self.vitals[VitalSign.AROUSAL.value].value / 100  # 0-1
        attachment = self.vitals[VitalSign.ATTACHMENT.value].value / 100  # 0-1
        curiosity = self.vitals[VitalSign.CURIOSITY.value].value / 100  # 0-1
        stress = self.vitals[VitalSign.STRESS.value].value / 100  # 0-1

        # Score each emotion based on how well the current vitals match
        scores = {
            EmotionLabel.JOY: (energy * 0.3 + mood * 0.4 + arousal * 0.3),
            EmotionLabel.EXCITEMENT: (energy * 0.3 + arousal * 0.4 + curiosity * 0.3),
            EmotionLabel.CONTENTMENT: (mood * 0.5 + (1 - stress) * 0.3 + attachment * 0.2),
            EmotionLabel.CURIOSITY_EAGER: (curiosity * 0.5 + arousal * 0.3 + mood * 0.2),
            EmotionLabel.LOVE: (attachment * 0.5 + mood * 0.3 + energy * 0.2),
            EmotionLabel.PRIDE: (mood * 0.4 + energy * 0.3 + (1 - stress) * 0.3),
            EmotionLabel.GRATITUDE: (mood * 0.3 + attachment * 0.4 + (1 - stress) * 0.3),
            EmotionLabel.ANXIETY: (arousal * 0.3 + stress * 0.4 + (1 - mood) * 0.3),
            EmotionLabel.FRUSTRATION: (stress * 0.4 + (1 - mood) * 0.3 + (1 - energy) * 0.3),
            EmotionLabel.SADNESS: ((1 - mood) * 0.4 + (1 - energy) * 0.3 + (1 - arousal) * 0.3),
            EmotionLabel.LONELINESS: ((1 - attachment) * 0.4 + (1 - mood) * 0.3 + (1 - arousal) * 0.3),
            EmotionLabel.BOREDOM: ((1 - arousal) * 0.4 + (1 - curiosity) * 0.3 + (1 - energy) * 0.3),
            EmotionLabel.EXHAUSTION: ((1 - energy) * 0.5 + stress * 0.3 + (1 - mood) * 0.2),
            EmotionLabel.CALM: ((1 - stress) * 0.4 + (1 - arousal) * 0.3 + mood * 0.3),
        }

        # Boost emotions that have strong vital signals
        if mood > 0.7 and energy > 0.6:
            scores[EmotionLabel.JOY] += 0.3
        if attachment > 0.7 and mood > 0.6:
            scores[EmotionLabel.LOVE] += 0.3
        if curiosity > 0.7 and arousal > 0.5:
            scores[EmotionLabel.CURIOSITY_EAGER] += 0.3

        # Find dominant
        dominant = max(scores, key=scores.get)

        # If all scores are low, it's neutral
        if scores[dominant] < 0.3:
            return EmotionLabel.NEUTRAL.value

        return dominant.value

    def get_emotion_spectrum(self) -> Dict[str, float]:
        """Get the full emotion spectrum (all emotion scores normalized)"""
        energy = self.vitals[VitalSign.ENERGY.value].value / 100
        mood = (self.vitals[VitalSign.MOOD.value].value + 100) / 200
        arousal = self.vitals[VitalSign.AROUSAL.value].value / 100
        attachment = self.vitals[VitalSign.ATTACHMENT.value].value / 100
        curiosity = self.vitals[VitalSign.CURIOSITY.value].value / 100
        stress = self.vitals[VitalSign.STRESS.value].value / 100

        scores = {
            EmotionLabel.JOY.value: (energy * 0.3 + mood * 0.4 + arousal * 0.3),
            EmotionLabel.EXCITEMENT.value: (energy * 0.3 + arousal * 0.4 + curiosity * 0.3),
            EmotionLabel.CONTENTMENT.value: (mood * 0.5 + (1 - stress) * 0.3 + attachment * 0.2),
            EmotionLabel.CURIOSITY_EAGER.value: (curiosity * 0.5 + arousal * 0.3 + mood * 0.2),
            EmotionLabel.LOVE.value: (attachment * 0.5 + mood * 0.3 + energy * 0.2),
            EmotionLabel.ANXIETY.value: (arousal * 0.3 + stress * 0.4 + (1 - mood) * 0.3),
            EmotionLabel.FRUSTRATION.value: (stress * 0.4 + (1 - mood) * 0.3 + (1 - energy) * 0.3),
            EmotionLabel.SADNESS.value: ((1 - mood) * 0.4 + (1 - energy) * 0.3 + (1 - arousal) * 0.3),
            EmotionLabel.BOREDOM.value: ((1 - arousal) * 0.4 + (1 - curiosity) * 0.3 + (1 - energy) * 0.3),
            EmotionLabel.CALM.value: ((1 - stress) * 0.4 + (1 - arousal) * 0.3 + mood * 0.3),
        }

        # Normalize to 0-1
        max_score = max(scores.values()) if scores else 1
        if max_score > 0:
            scores = {k: round(v / max_score, 4) for k, v in scores.items()}

        return scores

    # ═════════════════════════════════════════════════════════════════════════
    #  واجهة الاستعلام — Query Interface
    # ═════════════════════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        """الحالة الكاملة — Full living state status"""
        return {
            "initialized": self._initialized,
            "heartbeat_count": self._heartbeat_count,
            "vitals": {name: v.to_dict() for name, v in self.vitals.items()},
            "dominant_emotion": self.get_dominant_emotion(),
            "emotion_spectrum": self.get_emotion_spectrum(),
            "energy_level": self._get_energy_level(),
            "is_responsive": self.vitals[VitalSign.ENERGY.value].value > 15,
            "hours_since_interaction": self._hours_since_interaction(),
            "pending_actions": self._pending_actions[-5:],
            "pending_thoughts": self._pending_thoughts[-5:],
        }

    def get_vitals_snapshot(self) -> dict:
        """لقطة سريعة — Quick vitals snapshot for dashboard"""
        return {
            name: {
                "value": round(v.value, 1),
                "percent": round(v._percent(), 1),
                "trend": v._trend(),
            }
            for name, v in self.vitals.items()
        }

    def get_heartbeat_data(self) -> dict:
        """بيانات النبض — Heartbeat data for JARVIS display"""
        return {
            "cycle": self._heartbeat_count,
            "dominant_emotion": self.get_dominant_emotion(),
            "emotion_spectrum": self.get_emotion_spectrum(),
            "vitals": self.get_vitals_snapshot(),
            "energy_level": self._get_energy_level(),
            "last_interaction_hours_ago": round(self._hours_since_interaction(), 2),
        }

    def get_pending_actions(self) -> List[Dict]:
        """الإجراءات المعلقة — Get and clear pending proactive actions"""
        actions = list(self._pending_actions)
        self._pending_actions.clear()
        return actions

    def get_pending_thoughts(self) -> List[str]:
        """الأفكار المعلقة — Get and clear pending background thoughts"""
        thoughts = list(self._pending_thoughts)
        self._pending_thoughts.clear()
        return thoughts

    def _on_neural_signal(self, signal):
        """v31: Handle incoming NeuralBus signals — react to action results."""
        try:
            stype = signal.signal_type
            if stype == "action_completed":
                # Task success → slight mood boost
                self._adjust(VitalSign.MOOD.value, 2)
                self._adjust(VitalSign.ENERGY.value, 1)
            elif stype == "action_failed":
                # Task failure → slight mood drop + stress rise
                self._adjust(VitalSign.MOOD.value, -3)
                self._adjust(VitalSign.STRESS.value, 2)
            elif stype == "healing_complete":
                # Self-healing done → stress relief
                self._adjust(VitalSign.STRESS.value, -5)
        except Exception:
            pass

    def get_event_history(self, limit: int = 20) -> List[dict]:
        """تاريخ الأحداث العاطفية"""
        return [e.to_dict() for e in self._event_history[-limit:]]

    def _get_energy_level(self) -> str:
        e = self.vitals[VitalSign.ENERGY.value].value
        if e < 10: return "critical"
        if e < 30: return "low"
        if e < 70: return "normal"
        if e < 90: return "high"
        return "surging"

    def _hours_since_interaction(self) -> float:
        if self._last_user_interaction <= 0:
            return -1
        return (time.time() - self._last_user_interaction) / 3600

    # ═════════════════════════════════════════════════════════════════════════
    #  الاستمرارية — Persistence
    # ═════════════════════════════════════════════════════════════════════════

    def _ensure_schema(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS ls_vitals (
                name TEXT PRIMARY KEY, value REAL, baseline REAL,
                min_val REAL, max_val REAL, decay_rate REAL, last_updated REAL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS ls_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL,
                event_type TEXT, intensity REAL, valence REAL, source TEXT,
                description TEXT, effects TEXT)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS ls_state (
                key TEXT PRIMARY KEY, value TEXT)""")
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            # Load vitals
            cur = conn.execute("SELECT name, value, baseline, min_val, max_val, decay_rate FROM ls_vitals")
            for row in cur.fetchall():
                name = row[0]
                if name in self.vitals:
                    self.vitals[name].value = row[1]
                    self.vitals[name].baseline = row[2]
                    # Keep min/max/decay from code, not DB

            # Load state
            cur = conn.execute("SELECT key, value FROM ls_state")
            for key, value in cur.fetchall():
                try:
                    if key == "heartbeat_count":
                        self._heartbeat_count = int(value)
                    elif key == "last_user_interaction":
                        self._last_user_interaction = float(value)
                    elif key == "counter":
                        self._counter = int(value)
                except (ValueError, TypeError):
                    pass

            logger.info("LivingState loaded from DB — heartbeat=%d, last_interaction=%.1fh ago",
                       self._heartbeat_count,
                       self._hours_since_interaction())
        finally:
            conn.close()

    def _persist_state(self):
        """Persist current vitals and state to DB"""
        try:
            conn = get_db_connection(self.db_path)
            try:
                for name, v in self.vitals.items():
                    conn.execute(
                        "INSERT OR REPLACE INTO ls_vitals (name, value, baseline, min_val, max_val, decay_rate, last_updated) VALUES (?,?,?,?,?,?,?)",
                        (name, v.value, v.baseline, v.min_val, v.max_val, v.decay_rate, v.last_updated),
                    )
                for key, value in {
                    "heartbeat_count": str(self._heartbeat_count),
                    "last_user_interaction": str(self._last_user_interaction),
                    "counter": str(self._counter),
                }.items():
                    conn.execute("INSERT OR REPLACE INTO ls_state (key, value) VALUES (?, ?)", (key, value))
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("LivingState persist failed: %s", e)

    def _persist_event(self, event: EmotionalEvent):
        """Persist important emotional events"""
        try:
            conn = get_db_connection(self.db_path)
            try:
                conn.execute(
                    "INSERT INTO ls_events (timestamp, event_type, intensity, valence, source, description, effects) VALUES (?,?,?,?,?,?,?)",
                    (event.timestamp, event.event_type, event.intensity, event.valence,
                     event.source, event.description, json.dumps(event.effects, default=str)),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("LivingState event persist failed: %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton
# ═══════════════════════════════════════════════════════════════════════════════

living_state = LivingStateEngine()
