"""
BABSHARQII v19.0 — User Mental Model
النموذج العقلي للمستخدم — Bayesian updating

Builds and maintains a mental model of the user:
- Tech level (beginner → expert)
- Communication style (detailed → concise)
- Goals (what they're trying to achieve)
- Patterns (recurring behaviors)
- Recurring errors (common mistakes)
- Mood (inferred from typing speed, message length, time of day)
- Bayesian updating: every interaction refines the model

Example output:
  "المستوى التقني: متقدم | أسلوب: مختصر | أهداف: بناء شركة ديكور"
"""

import time
import json
import math
import logging
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum

logger = logging.getLogger("mamoun.user_mental_model")


class TechLevel(str, Enum):
    BEGINNER = "beginner"      # مبتدئ
    INTERMEDIATE = "intermediate"  # متوسط
    ADVANCED = "advanced"      # متقدم
    EXPERT = "expert"         # خبير


class CommStyle(str, Enum):
    DETAILED = "detailed"     # مفصّل
    BALANCED = "balanced"     # متوازن
    CONCISE = "concise"       # مختصر


class Mood(str, Enum):
    PRODUCTIVE = "productive"  # منتج 🟢
    NEUTRAL = "neutral"       # عادي 🟡
    FRUSTRATED = "frustrated"  # محبط 🔴
    CURIOUS = "curious"       # فضولي 🔵


@dataclass
class BayesianDimension:
    """بُعد مع Bayesian updating — احتمالات لكل قيمة"""
    name: str = ""
    probabilities: Dict[str, float] = field(default_factory=dict)
    evidence_count: int = 0
    last_updated: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "probabilities": {k: round(v, 4) for k, v in self.probabilities.items()},
            "evidence_count": self.evidence_count,
            "top": max(self.probabilities, key=self.probabilities.get) if self.probabilities else "",
        }


@dataclass
class UserGoal:
    """هدف المستخدم"""
    goal: str = ""
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    first_seen: float = 0.0
    last_seen: float = 0.0

    def to_dict(self) -> dict:
        return {"goal": self.goal, "confidence": round(self.confidence, 4), "evidence": self.evidence[:3]}


@dataclass
class UserPattern:
    """نمط متكرر للمستخدم"""
    pattern: str = ""
    frequency: int = 0
    last_seen: float = 0.0

    def to_dict(self) -> dict:
        return {"pattern": self.pattern, "frequency": self.frequency}


@dataclass
class RecurringError:
    """خطأ متكرر"""
    error_type: str = ""
    description: str = ""
    count: int = 0
    last_seen: float = 0.0

    def to_dict(self) -> dict:
        return {"error_type": self.error_type, "description": self.description, "count": self.count}


class UserMentalModel:
    """
    النموذج العقلي للمستخدم — يبني صورة كاملة عن المستخدم

    Uses Bayesian updating:
      P(H|E) = P(E|H) * P(H) / P(E)
    
    Each interaction provides evidence that updates:
    - Tech level probabilities
    - Communication style probabilities
    - Mood probabilities
    - Goal tracking
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path("/tmp/user_mental_model.db")

        # Bayesian dimensions
        self._tech_level = BayesianDimension(
            name="tech_level",
            probabilities={"beginner": 0.25, "intermediate": 0.25, "advanced": 0.25, "expert": 0.25}
        )
        self._comm_style = BayesianDimension(
            name="comm_style",
            probabilities={"detailed": 0.33, "balanced": 0.34, "concise": 0.33}
        )
        self._mood = BayesianDimension(
            name="mood",
            probabilities={"productive": 0.25, "neutral": 0.50, "frustrated": 0.10, "curious": 0.15}
        )

        # Structured data
        self._goals: List[UserGoal] = []
        self._patterns: List[UserPattern] = []
        self._errors: List[RecurringError] = []

        # Interaction stats
        self._total_interactions = 0
        self._avg_message_length = 0.0
        self._avg_response_time = 0.0  # seconds
        self._session_count = 0
        self._first_seen = 0.0
        self._last_seen = 0.0
        self._interaction_times: List[float] = []
        self._message_lengths: List[int] = []

        self._counter = 0
        self._initialized = False

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("UserMentalModel initialized — %d interactions, tech=%s",
                       self._total_interactions, self._tech_level.to_dict()["top"])
            return True
        except Exception as e:
            logger.error("UserMentalModel init failed: %s", e)
            return False

    def _ensure_schema(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS umm_state (
                key TEXT PRIMARY KEY, value TEXT NOT NULL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS umm_goals (
                goal TEXT PRIMARY KEY, confidence REAL DEFAULT 0,
                evidence TEXT DEFAULT '[]', first_seen REAL DEFAULT 0, last_seen REAL DEFAULT 0)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS umm_patterns (
                pattern TEXT PRIMARY KEY, frequency INTEGER DEFAULT 1, last_seen REAL DEFAULT 0)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS umm_errors (
                error_type TEXT PRIMARY KEY, description TEXT DEFAULT '',
                count INTEGER DEFAULT 1, last_seen REAL DEFAULT 0)""")
            conn.commit()
        finally: conn.close()

    def _load_from_db(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            cur = conn.execute("SELECT key, value FROM umm_state")
            for key, value in cur.fetchall():
                try:
                    if key == "tech_level": self._tech_level.probabilities = json.loads(value)
                    elif key == "comm_style": self._comm_style.probabilities = json.loads(value)
                    elif key == "mood": self._mood.probabilities = json.loads(value)
                    elif key == "tech_evidence": self._tech_level.evidence_count = int(value)
                    elif key == "comm_evidence": self._comm_style.evidence_count = int(value)
                    elif key == "mood_evidence": self._mood.evidence_count = int(value)
                    elif key == "total_interactions": self._total_interactions = int(value)
                    elif key == "avg_message_length": self._avg_message_length = float(value)
                    elif key == "session_count": self._session_count = int(value)
                    elif key == "first_seen": self._first_seen = float(value)
                    elif key == "last_seen": self._last_seen = float(value)
                except (ValueError, TypeError, json.JSONDecodeError): pass

            cur = conn.execute("SELECT goal, confidence, evidence, first_seen, last_seen FROM umm_goals")
            for row in cur.fetchall():
                self._goals.append(UserGoal(goal=row[0], confidence=row[1],
                                           evidence=json.loads(row[2]) if row[2] else [],
                                           first_seen=row[3], last_seen=row[4]))

            cur = conn.execute("SELECT pattern, frequency, last_seen FROM umm_patterns")
            for row in cur.fetchall():
                self._patterns.append(UserPattern(pattern=row[0], frequency=row[1], last_seen=row[2]))

            cur = conn.execute("SELECT error_type, description, count, last_seen FROM umm_errors")
            for row in cur.fetchall():
                self._errors.append(RecurringError(error_type=row[0], description=row[1], count=row[2], last_seen=row[3]))
        finally: conn.close()

    # ─── Core: Update Model ────────────────────────────────────────────────

    def update(self, message: str = "", message_length: int = 0,
               response_time: float = 0.0, topics: List[str] = None,
               errors: List[str] = None, metadata: dict = None):
        """
        تحديث النموذج العقلي بناءً على تفاعل جديد

        Args:
            message: رسالة المستخدم
            message_length: طول الرسالة (أحرف)
            response_time: وقت الاستجابة (ثواني)
            topics: الموضوعات المطروحة
            errors: أخطاء حدثت
            metadata: بيانات إضافية
        """
        if not self._initialized:
            self.initialize()

        now = time.time()
        self._total_interactions += 1
        self._last_seen = now
        if not self._first_seen:
            self._first_seen = now

        # Track message length
        if message_length > 0:
            self._message_lengths.append(message_length)
            if len(self._message_lengths) > 100:
                self._message_lengths = self._message_lengths[-100:]
            self._avg_message_length = sum(self._message_lengths) / len(self._message_lengths)

        # Track response time
        if response_time > 0:
            self._interaction_times.append(response_time)
            if len(self._interaction_times) > 100:
                self._interaction_times = self._interaction_times[-100:]
            self._avg_response_time = sum(self._interaction_times) / len(self._interaction_times)

        # Bayesian update: Tech level
        self._update_tech_level(message, message_length, topics or [])

        # Bayesian update: Communication style
        self._update_comm_style(message_length)

        # Bayesian update: Mood
        self._update_mood(message_length, response_time)

        # Update goals
        if topics:
            self._update_goals(topics)

        # Update patterns
        self._update_patterns(topics or [], now)

        # Update errors
        if errors:
            self._update_errors(errors, now)

        # Persist
        self._persist_state()

        logger.debug("UserMentalModel updated — tech=%s, style=%s, mood=%s",
                     self._tech_level.to_dict()["top"],
                     self._comm_style.to_dict()["top"],
                     self._mood.to_dict()["top"])

    def _bayesian_update(self, dimension: BayesianDimension, evidence: Dict[str, float]):
        """
        Bayesian updating:
        P(H|E) = P(E|H) * P(H) / P(E)
        
        evidence: {hypothesis: likelihood} where likelihood is how likely the evidence is under each hypothesis
        """
        # Prior probabilities
        prior = dimension.probabilities.copy()

        # Calculate posterior
        posterior = {}
        normalizer = 0.0

        for hypothesis, prior_prob in prior.items():
            likelihood = evidence.get(hypothesis, 0.5)  # default likelihood
            posterior[hypothesis] = likelihood * prior_prob
            normalizer += posterior[hypothesis]

        # Normalize
        if normalizer > 0:
            for hypothesis in posterior:
                posterior[hypothesis] /= normalizer

        # Update with smoothing (don't change too fast)
        alpha = 0.3  # learning rate
        for hypothesis in prior:
            if hypothesis in posterior:
                dimension.probabilities[hypothesis] = (
                    alpha * posterior[hypothesis] + (1 - alpha) * prior[hypothesis]
                )

        dimension.evidence_count += 1
        dimension.last_updated = time.time()

    def _update_tech_level(self, message: str, msg_len: int, topics: List[str]):
        """تحديث مستوى التقنية بناءً على الأدلة"""
        evidence = {"beginner": 1.0, "intermediate": 1.0, "advanced": 1.0, "expert": 1.0}

        # Longer, more technical messages → higher tech level
        if msg_len > 200:
            evidence["beginner"] *= 0.5
            evidence["intermediate"] *= 0.8
            evidence["advanced"] *= 1.2
            evidence["expert"] *= 1.3
        elif msg_len < 30:
            evidence["beginner"] *= 1.3
            evidence["intermediate"] *= 1.1
            evidence["advanced"] *= 0.8
            evidence["expert"] *= 0.7

        # Technical keywords
        tech_keywords = ["api", "kernel", "react", "docker", "kubernetes", "database",
                        "pipeline", "deployment", "architecture", "algorithm", "backend"]
        msg_lower = message.lower()
        tech_count = sum(1 for kw in tech_keywords if kw in msg_lower)
        if tech_count >= 3:
            evidence["advanced"] *= 1.5
            evidence["expert"] *= 1.4
        elif tech_count >= 1:
            evidence["intermediate"] *= 1.3
            evidence["advanced"] *= 1.2

        self._bayesian_update(self._tech_level, evidence)

    def _update_comm_style(self, msg_len: int):
        """تحديث أسلوب التواصل"""
        evidence = {"detailed": 1.0, "balanced": 1.0, "concise": 1.0}

        if msg_len > 150:
            evidence["detailed"] *= 1.5
            evidence["balanced"] *= 1.0
            evidence["concise"] *= 0.5
        elif msg_len > 50:
            evidence["detailed"] *= 1.0
            evidence["balanced"] *= 1.3
            evidence["concise"] *= 0.8
        else:
            evidence["detailed"] *= 0.5
            evidence["balanced"] *= 0.8
            evidence["concise"] *= 1.5

        self._bayesian_update(self._comm_style, evidence)

    def _update_mood(self, msg_len: int, response_time: float):
        """تحديث المزاج بناءً على السلوك"""
        evidence = {"productive": 1.0, "neutral": 1.0, "frustrated": 1.0, "curious": 1.0}

        # Fast response + long message = productive
        if response_time > 0:
            if response_time < 30:
                evidence["productive"] *= 1.4
            elif response_time > 120:
                evidence["frustrated"] *= 1.3

        # Very short messages might indicate frustration
        if msg_len > 0 and msg_len < 10:
            evidence["frustrated"] *= 1.3
            evidence["productive"] *= 0.7

        # Medium messages with questions = curious
        if msg_len > 20 and msg_len < 100:
            evidence["curious"] *= 1.2

        # Late night = possibly frustrated or curious
        hour = __import__('datetime').datetime.now().hour
        if hour >= 23 or hour < 5:
            evidence["frustrated"] *= 1.2
            evidence["curious"] *= 1.1

        self._bayesian_update(self._mood, evidence)

    def _update_goals(self, topics: List[str]):
        """تحديث أهداف المستخدم"""
        for topic in topics:
            found = False
            for goal in self._goals:
                if topic.lower() in goal.goal.lower() or goal.goal.lower() in topic.lower():
                    goal.confidence = min(1.0, goal.confidence + 0.1)
                    goal.evidence.append(topic)
                    if len(goal.evidence) > 10:
                        goal.evidence = goal.evidence[-10:]
                    goal.last_seen = time.time()
                    found = True
                    break
            if not found:
                self._goals.append(UserGoal(
                    goal=topic, confidence=0.3, evidence=[topic],
                    first_seen=time.time(), last_seen=time.time()
                ))

        # Keep top 10 goals
        self._goals.sort(key=lambda g: g.confidence, reverse=True)
        if len(self._goals) > 10:
            self._goals = self._goals[:10]

    def _update_patterns(self, topics: List[str], now: float):
        """تحديث أنماط المستخدم"""
        for topic in topics:
            found = False
            for pattern in self._patterns:
                if topic.lower() == pattern.pattern.lower():
                    pattern.frequency += 1
                    pattern.last_seen = now
                    found = True
                    break
            if not found:
                self._patterns.append(UserPattern(pattern=topic, frequency=1, last_seen=now))

        self._patterns.sort(key=lambda p: p.frequency, reverse=True)
        if len(self._patterns) > 20:
            self._patterns = self._patterns[:20]

    def _update_errors(self, errors: List[str], now: float):
        """تحديث الأخطاء المتكررة"""
        for error in errors:
            found = False
            for e in self._errors:
                if error.lower() in e.error_type.lower():
                    e.count += 1
                    e.last_seen = now
                    found = True
                    break
            if not found:
                self._errors.append(RecurringError(error_type=error, description=error, count=1, last_seen=now))

    # ─── Persistence ───────────────────────────────────────────────────────

    def _persist_state(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            state = {
                "tech_level": json.dumps(self._tech_level.probabilities),
                "comm_style": json.dumps(self._comm_style.probabilities),
                "mood": json.dumps(self._mood.probabilities),
                "tech_evidence": str(self._tech_level.evidence_count),
                "comm_evidence": str(self._comm_style.evidence_count),
                "mood_evidence": str(self._mood.evidence_count),
                "total_interactions": str(self._total_interactions),
                "avg_message_length": str(self._avg_message_length),
                "session_count": str(self._session_count),
                "first_seen": str(self._first_seen),
                "last_seen": str(self._last_seen),
            }
            for key, value in state.items():
                conn.execute("INSERT OR REPLACE INTO umm_state (key, value) VALUES (?, ?)", (key, value))

            for goal in self._goals:
                conn.execute("INSERT OR REPLACE INTO umm_goals (goal, confidence, evidence, first_seen, last_seen) VALUES (?,?,?,?,?)",
                           (goal.goal, goal.confidence, json.dumps(goal.evidence), goal.first_seen, goal.last_seen))

            for pattern in self._patterns[:20]:
                conn.execute("INSERT OR REPLACE INTO umm_patterns (pattern, frequency, last_seen) VALUES (?,?,?)",
                           (pattern.pattern, pattern.frequency, pattern.last_seen))

            for error in self._errors:
                conn.execute("INSERT OR REPLACE INTO umm_errors (error_type, description, count, last_seen) VALUES (?,?,?,?)",
                           (error.error_type, error.description, error.count, error.last_seen))

            conn.commit()
        finally: conn.close()

    # ─── Status & API ──────────────────────────────────────────────────────

    def get_status(self) -> dict:
        tech = self._tech_level.to_dict()
        style = self._comm_style.to_dict()
        mood = self._mood.to_dict()
        return {
            "initialized": self._initialized,
            "total_interactions": self._total_interactions,
            "tech_level": tech,
            "comm_style": style,
            "mood": mood,
            "goals_count": len(self._goals),
            "patterns_count": len(self._patterns),
            "errors_count": len(self._errors),
            "avg_message_length": round(self._avg_message_length, 1),
            "first_seen": self._first_seen,
            "last_seen": self._last_seen,
        }

    def get_profile(self) -> dict:
        """ملف المستخدم الكامل — للعرض البصري JARVIS"""
        tech = self._tech_level.to_dict()
        style = self._comm_style.to_dict()
        mood = self._mood.to_dict()

        # Map to Arabic
        tech_ar = {"beginner": "مبتدئ", "intermediate": "متوسط", "advanced": "متقدم", "expert": "خبير"}
        style_ar = {"detailed": "مفصّل", "balanced": "متوازن", "concise": "مختصر"}
        mood_ar = {"productive": "منتج 🟢", "neutral": "عادي 🟡", "frustrated": "محبط 🔴", "curious": "فضولي 🔵"}

        return {
            "tech_level": {
                "value": tech["top"],
                "value_ar": tech_ar.get(tech["top"], tech["top"]),
                "confidence": tech["probabilities"].get(tech["top"], 0),
                "probabilities": tech["probabilities"],
            },
            "comm_style": {
                "value": style["top"],
                "value_ar": style_ar.get(style["top"], style["top"]),
                "confidence": style["probabilities"].get(style["top"], 0),
                "probabilities": style["probabilities"],
            },
            "mood": {
                "value": mood["top"],
                "value_ar": mood_ar.get(mood["top"], mood["top"]),
                "confidence": mood["probabilities"].get(mood["top"], 0),
                "probabilities": mood["probabilities"],
            },
            "goals": [g.to_dict() for g in self._goals[:5]],
            "patterns": [p.to_dict() for p in self._patterns[:5]],
            "recurring_errors": [e.to_dict() for e in self._errors[:5]],
        }

    def get_goals(self) -> List[dict]:
        return [g.to_dict() for g in sorted(self._goals, key=lambda g: g.confidence, reverse=True)]

    def get_patterns(self) -> List[dict]:
        return [p.to_dict() for p in sorted(self._patterns, key=lambda p: p.frequency, reverse=True)]

    def get_errors(self) -> List[dict]:
        return [e.to_dict() for e in sorted(self._errors, key=lambda e: e.count, reverse=True)]

    def get_radar_data(self) -> List[dict]:
        """بيانات الرادار — للعرض البصري (5 أبعاد)"""
        tech = self._tech_level.to_dict()
        style = self._comm_style.to_dict()
        mood = self._mood.to_dict()

        return [
            {"dimension": "tech_level", "label_ar": "المستوى التقني",
             "value": list(tech["probabilities"].values())},
            {"dimension": "comm_style", "label_ar": "أسلوب التواصل",
             "value": list(style["probabilities"].values())},
            {"dimension": "mood", "label_ar": "المزاج",
             "value": list(mood["probabilities"].values())},
            {"dimension": "goal_clarity", "label_ar": "وضوح الأهداف",
             "value": min(1.0, len(self._goals) * 0.2)},
            {"dimension": "error_rate", "label_ar": "معدل الأخطاء",
             "value": min(1.0, sum(e.count for e in self._errors) * 0.1)},
        ]


user_mental_model = UserMentalModel()
