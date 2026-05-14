"""
BABSHARQII v19.0 — Experiential RLHF
التعلم من التجربة — Local Reinforcement Learning from Human Feedback

Tracks: question → answer → user action → model adjustment
Learns from what the user accepts, rejects, or modifies.
"""

import time
import json
import logging
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List

logger = logging.getLogger("mamoun.experiential_rlhf")


@dataclass
class ExperienceRecord:
    """سجل تجربة — سؤال → إجابة → رد فعل"""
    id: str = ""
    question: str = ""
    answer: str = ""
    user_action: str = ""  # accepted, rejected, modified, ignored
    modification: str = ""  # what the user changed
    reward: float = 0.0  # -1.0 to 1.0
    context: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"id": self.id, "question": self.question[:100], "answer": self.answer[:100],
                "user_action": self.user_action, "reward": round(self.reward, 4),
                "timestamp": self.timestamp}


@dataclass
class PreferenceUpdate:
    """تحديث تفضيل — ما تعلمه مأمون من التجربة"""
    id: str = ""
    category: str = ""  # response_style, topic_preference, detail_level, etc.
    before: str = ""
    after: str = ""
    evidence: str = ""
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"id": self.id, "category": self.category, "before": self.before,
                "after": self.after, "confidence": round(self.confidence, 4)}


class ExperientialRLHFEngine:
    """
    محرك التعلم من التجربة — RLHF محلي

    Reward mapping:
    - accepted → +1.0 (user liked the answer)
    - modified → +0.3 (answer was directionally right but needed adjustment)
    - ignored → 0.0 (neutral)
    - rejected → -1.0 (answer was wrong/unhelpful)
    """

    REWARD_MAP = {
        "accepted": 1.0,
        "modified": 0.3,
        "ignored": 0.0,
        "rejected": -1.0,
    }

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path("/tmp/experiential_rlhf.db")
        self._experiences: List[ExperienceRecord] = []
        self._preferences: List[PreferenceUpdate] = []
        self._pending_questions: Dict[str, str] = {}  # question_id → answer
        self._avg_reward = 0.0
        self._total_experiences = 0
        self._acceptance_rate = 0.0
        self._counter = 0
        self._initialized = False

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("ExperientialRLHFEngine initialized — %d experiences, avg_reward=%.2f",
                       len(self._experiences), self._avg_reward)
            return True
        except Exception as e:
            logger.error("ExperientialRLHFEngine init failed: %s", e)
            return False

    def _ensure_schema(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS rlhf_experiences (
                id TEXT PRIMARY KEY, question TEXT DEFAULT '', answer TEXT DEFAULT '',
                user_action TEXT DEFAULT '', modification TEXT DEFAULT '',
                reward REAL DEFAULT 0, context TEXT DEFAULT '{}', timestamp REAL DEFAULT 0)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS rlhf_preferences (
                id TEXT PRIMARY KEY, category TEXT DEFAULT '', before_val TEXT DEFAULT '',
                after_val TEXT DEFAULT '', evidence TEXT DEFAULT '', confidence REAL DEFAULT 0,
                timestamp REAL DEFAULT 0)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS rlhf_state (
                key TEXT PRIMARY KEY, value TEXT NOT NULL)""")
            conn.commit()
        finally: conn.close()

    def _load_from_db(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            cur = conn.execute("SELECT key, value FROM rlhf_state")
            for key, value in cur.fetchall():
                try:
                    if key == "avg_reward": self._avg_reward = float(value)
                    elif key == "total_experiences": self._total_experiences = int(value)
                    elif key == "acceptance_rate": self._acceptance_rate = float(value)
                    elif key == "counter": self._counter = int(value)
                except (ValueError, TypeError): pass

            cur = conn.execute("SELECT id, question, answer, user_action, modification, reward, context, timestamp FROM rlhf_experiences ORDER BY timestamp DESC LIMIT 100")
            for row in cur.fetchall():
                self._experiences.append(ExperienceRecord(id=row[0], question=row[1], answer=row[2],
                    user_action=row[3], modification=row[4], reward=row[5],
                    context=json.loads(row[6]) if row[6] else {}, timestamp=row[7]))

            cur = conn.execute("SELECT id, category, before_val, after_val, evidence, confidence, timestamp FROM rlhf_preferences ORDER BY timestamp DESC LIMIT 50")
            for row in cur.fetchall():
                self._preferences.append(PreferenceUpdate(id=row[0], category=row[1], before=row[2],
                    after=row[3], evidence=row[4], confidence=row[5], timestamp=row[6]))
        finally: conn.close()

    # ─── Core: Record Experience ────────────────────────────────────────────

    def record_question(self, question_id: str, question: str, answer: str):
        """تسجيل سؤال + إجابة (في انتظار رد فعل المستخدم)"""
        self._pending_questions[question_id] = answer

    def record_feedback(self, question_id: str, user_action: str, modification: str = "",
                        context: dict = None) -> Optional[PreferenceUpdate]:
        """تسجيل رد فعل المستخدم → حساب المكافأة → تحديث التفضيلات"""
        if not self._initialized:
            self.initialize()

        answer = self._pending_questions.pop(question_id, "")
        reward = self.REWARD_MAP.get(user_action, 0.0)

        # Create experience record
        self._counter += 1
        experience = ExperienceRecord(
            id=f"exp_{self._counter}",
            question=question_id if not answer else "",
            answer=answer,
            user_action=user_action,
            modification=modification,
            reward=reward,
            context=context or {},
        )
        self._experiences.append(experience)
        self._total_experiences += 1

        # Update running average
        total_reward = sum(e.reward for e in self._experiences)
        self._avg_reward = total_reward / len(self._experiences) if self._experiences else 0.0

        # Update acceptance rate
        accepted = sum(1 for e in self._experiences if e.user_action == "accepted")
        self._acceptance_rate = accepted / len(self._experiences) if self._experiences else 0.0

        # Generate preference update if significant
        pref_update = None
        if abs(reward) > 0.5 and answer:
            self._counter += 1
            pref_update = PreferenceUpdate(
                id=f"pref_{self._counter}",
                category="response_quality",
                before=f"answer: {answer[:50]}",
                after=f"action: {user_action}, reward: {reward}",
                evidence=f"User {user_action} the answer",
                confidence=min(1.0, abs(reward)),
            )
            self._preferences.append(pref_update)

        # Persist
        self._persist_experience(experience)
        if pref_update:
            self._persist_preference(pref_update)
        self._persist_state()

        return pref_update

    # ─── Persistence ───────────────────────────────────────────────────────

    def _persist_experience(self, e: ExperienceRecord):
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("INSERT OR REPLACE INTO rlhf_experiences (id, question, answer, user_action, modification, reward, context, timestamp) VALUES (?,?,?,?,?,?,?,?)",
                        (e.id, e.question, e.answer, e.user_action, e.modification, e.reward, json.dumps(e.context), e.timestamp))
            conn.commit()
        finally: conn.close()

    def _persist_preference(self, p: PreferenceUpdate):
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("INSERT OR REPLACE INTO rlhf_preferences (id, category, before_val, after_val, evidence, confidence, timestamp) VALUES (?,?,?,?,?,?,?)",
                        (p.id, p.category, p.before, p.after, p.evidence, p.confidence, p.timestamp))
            conn.commit()
        finally: conn.close()

    def _persist_state(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            for key, value in {"avg_reward": str(self._avg_reward), "total_experiences": str(self._total_experiences),
                              "acceptance_rate": str(self._acceptance_rate), "counter": str(self._counter)}.items():
                conn.execute("INSERT OR REPLACE INTO rlhf_state (key, value) VALUES (?, ?)", (key, value))
            conn.commit()
        finally: conn.close()

    # ─── Status & API ──────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "initialized": self._initialized,
            "total_experiences": len(self._experiences),
            "avg_reward": round(self._avg_reward, 4),
            "acceptance_rate": round(self._acceptance_rate, 4),
            "preference_count": len(self._preferences),
            "pending_questions": len(self._pending_questions),
        }

    def get_experiences(self, limit: int = 20) -> List[dict]:
        return [e.to_dict() for e in sorted(self._experiences, key=lambda e: e.timestamp, reverse=True)[:limit]]

    def get_preferences(self, limit: int = 20) -> List[dict]:
        return [p.to_dict() for p in sorted(self._preferences, key=lambda p: p.timestamp, reverse=True)[:limit]]

    def get_reward_trend(self, limit: int = 20) -> List[dict]:
        recent = sorted(self._experiences, key=lambda e: e.timestamp, reverse=True)[:limit]
        return [{"timestamp": e.timestamp, "reward": e.reward, "action": e.user_action} for e in reversed(recent)]


experiential_rlhf = ExperientialRLHFEngine()
