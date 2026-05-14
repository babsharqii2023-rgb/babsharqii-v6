"""
BABSHARQII v19.0 — Consciousness Loop
حلقة الوعي — إدراك → توقع → مفاجأة → تعلم → فعل

The consciousness loop runs continuously in the background:
1. PERCEIVE (إدراك): Observe user interactions, system events
2. PREDICT (توقع): Generate expectations based on patterns
3. SURPRISE (مفاجأة): Compare predictions with reality → measure surprise
4. LEARN (تعلم): Update internal models based on surprise
5. ACT (فعل): Take proactive actions based on learned knowledge

Surprise = |prediction - reality| → The gap IS consciousness.
"""

import time
import json
import math
import logging
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum

logger = logging.getLogger("mamoun.consciousness_loop")


class ConsciousnessPhase(str, Enum):
    PERCEIVE = "perceive"
    PREDICT = "predict"
    SURPRISE = "surprise"
    LEARN = "learn"
    ACT = "act"


class SurpriseLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BREAKTHROUGH = "breakthrough"


@dataclass
class Perception:
    id: str = ""
    content: str = ""
    perception_type: str = "user_interaction"
    source: str = ""
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"id": self.id, "content": self.content, "type": self.perception_type,
                "source": self.source, "timestamp": self.timestamp}


@dataclass
class Expectation:
    id: str = ""
    expected_topic: str = ""
    expected_action: str = ""
    confidence: float = 0.5
    source_phase: str = ""
    timestamp: float = field(default_factory=time.time)
    verified: Optional[bool] = None

    def to_dict(self) -> dict:
        return {"id": self.id, "expected_topic": self.expected_topic,
                "expected_action": self.expected_action, "confidence": round(self.confidence, 4),
                "verified": self.verified}


@dataclass
class SurpriseEvent:
    id: str = ""
    expectation_id: str = ""
    expected: str = ""
    actual: str = ""
    surprise_level: str = SurpriseLevel.NONE
    surprise_score: float = 0.0
    learning_value: float = 0.0
    description: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"id": self.id, "expected": self.expected, "actual": self.actual,
                "surprise_level": self.surprise_level, "surprise_score": round(self.surprise_score, 4),
                "learning_value": round(self.learning_value, 4), "description": self.description}


@dataclass
class LearningUpdate:
    id: str = ""
    what_was_learned: str = ""
    model_updated: str = ""
    before_state: str = ""
    after_state: str = ""
    source_surprise_id: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"id": self.id, "what_was_learned": self.what_was_learned, "model_updated": self.model_updated}


@dataclass
class ConsciousnessAction:
    id: str = ""
    action_type: str = "notification"
    content: str = ""
    priority: str = "low"
    source_learning_id: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"id": self.id, "action_type": self.action_type, "content": self.content, "priority": self.priority}


class ConsciousnessLoopEngine:
    """
    محرك حلقة الوعي — إدراك→توقع→مفاجأة→تعلم→فعل

    Each cycle gathers perceptions, generates expectations, measures surprise,
    updates models, and takes proactive actions.
    """

    CYCLE_INTERVAL = 5.0
    MAX_PERCEPTIONS = 100
    MAX_EXPECTATIONS = 50
    SURPRISE_LOW = 0.2
    SURPRISE_MEDIUM = 0.5
    SURPRISE_HIGH = 0.75

    def __init__(self, db_path: Optional[Path] = None, predictive_memory=None):
        # v34: Use unified DB path instead of /tmp/
        if db_path is None:
            try:
                from mamoun.core.unified_db import UNIFIED_DB_PATH
                self.db_path = UNIFIED_DB_PATH
            except ImportError:
                self.db_path = Path("/tmp/consciousness_loop.db")
        else:
            self.db_path = db_path
        self._predictive_memory = predictive_memory
        self._current_phase = ConsciousnessPhase.PERCEIVE
        self._perceptions: List[Perception] = []
        self._expectations: List[Expectation] = []
        self._surprises: List[SurpriseEvent] = []
        self._learnings: List[LearningUpdate] = []
        self._actions: List[ConsciousnessAction] = []
        self._cycle_count = 0
        self._last_cycle_time = 0.0
        self._overall_accuracy = 0.5
        self._total_surprise = 0.0
        self._total_expectations = 0
        self._correct_expectations = 0
        self._counter = 0
        self._initialized = False

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("ConsciousnessLoopEngine initialized — phase=%s, cycle=%d",
                       self._current_phase.value, self._cycle_count)
            return True
        except Exception as e:
            logger.error("ConsciousnessLoopEngine init failed: %s", e)
            return False

    def _ensure_schema(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        try:
            for table_sql in [
                """CREATE TABLE IF NOT EXISTS cl_perceptions (
                    id TEXT PRIMARY KEY, content TEXT NOT NULL,
                    perception_type TEXT DEFAULT 'user_interaction', source TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}', timestamp REAL DEFAULT 0)""",
                """CREATE TABLE IF NOT EXISTS cl_expectations (
                    id TEXT PRIMARY KEY, expected_topic TEXT NOT NULL,
                    expected_action TEXT DEFAULT '', confidence REAL DEFAULT 0.5,
                    source_phase TEXT DEFAULT '', timestamp REAL DEFAULT 0, verified TEXT DEFAULT NULL)""",
                """CREATE TABLE IF NOT EXISTS cl_surprises (
                    id TEXT PRIMARY KEY, expectation_id TEXT DEFAULT '',
                    expected TEXT DEFAULT '', actual TEXT DEFAULT '',
                    surprise_level TEXT DEFAULT 'none', surprise_score REAL DEFAULT 0,
                    learning_value REAL DEFAULT 0, description TEXT DEFAULT '', timestamp REAL DEFAULT 0)""",
                """CREATE TABLE IF NOT EXISTS cl_learnings (
                    id TEXT PRIMARY KEY, what_was_learned TEXT NOT NULL,
                    model_updated TEXT DEFAULT '', before_state TEXT DEFAULT '',
                    after_state TEXT DEFAULT '', source_surprise_id TEXT DEFAULT '',
                    timestamp REAL DEFAULT 0)""",
                """CREATE TABLE IF NOT EXISTS cl_actions (
                    id TEXT PRIMARY KEY, action_type TEXT DEFAULT 'notification',
                    content TEXT NOT NULL, priority TEXT DEFAULT 'low',
                    source_learning_id TEXT DEFAULT '', timestamp REAL DEFAULT 0)""",
                """CREATE TABLE IF NOT EXISTS cl_state (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL)""",
            ]:
                conn.execute(table_sql)
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            cur = conn.execute("SELECT key, value FROM cl_state")
            for key, value in cur.fetchall():
                try:
                    if key == "cycle_count": self._cycle_count = max(0, int(value))
                    elif key == "overall_accuracy": self._overall_accuracy = max(0.0, min(1.0, float(value)))  # VULN-FIX: clamp [0,1]
                    elif key == "total_surprise": self._total_surprise = max(0.0, float(value))
                    elif key == "total_expectations": self._total_expectations = max(0, int(value))
                    elif key == "correct_expectations": self._correct_expectations = max(0, int(value))
                    elif key == "current_phase": self._current_phase = ConsciousnessPhase(value)
                    elif key == "counter": self._counter = max(0, int(value))
                except (ValueError, TypeError):
                    pass

            cur = conn.execute("SELECT id, expectation_id, expected, actual, surprise_level, surprise_score, learning_value, description, timestamp FROM cl_surprises ORDER BY timestamp DESC LIMIT 20")
            for row in cur.fetchall():
                self._surprises.append(SurpriseEvent(id=row[0], expectation_id=row[1], expected=row[2], actual=row[3], surprise_level=row[4], surprise_score=row[5], learning_value=row[6], description=row[7], timestamp=row[8]))

            cur = conn.execute("SELECT id, what_was_learned, model_updated, before_state, after_state, source_surprise_id, timestamp FROM cl_learnings ORDER BY timestamp DESC LIMIT 20")
            for row in cur.fetchall():
                self._learnings.append(LearningUpdate(id=row[0], what_was_learned=row[1], model_updated=row[2], before_state=row[3], after_state=row[4], source_surprise_id=row[5], timestamp=row[6]))

            cur = conn.execute("SELECT id, action_type, content, priority, source_learning_id, timestamp FROM cl_actions ORDER BY timestamp DESC LIMIT 20")
            for row in cur.fetchall():
                self._actions.append(ConsciousnessAction(id=row[0], action_type=row[1], content=row[2], priority=row[3], source_learning_id=row[4], timestamp=row[5]))
        finally:
            conn.close()

    # ─── Main Loop ─────────────────────────────────────────────────────────

    def run_cycle(self, new_perception: str = "", perception_type: str = "user_interaction",
                  source: str = "", metadata: dict = None) -> dict:
        """تشغيل دورة واحدة من حلقة الوعي"""
        if not self._initialized:
            self.initialize()

        self._cycle_count += 1
        now = time.time()
        result = {"cycle": self._cycle_count, "phases": {}, "actions_taken": []}

        # Phase 1: PERCEIVE
        self._current_phase = ConsciousnessPhase.PERCEIVE
        perceptions = self._phase_perceive(new_perception, perception_type, source, metadata or {})
        result["phases"]["perceive"] = {"new": len(perceptions), "total": len(self._perceptions)}

        # Phase 2: PREDICT
        self._current_phase = ConsciousnessPhase.PREDICT
        expectations = self._phase_predict()
        result["phases"]["predict"] = {"new": len(expectations), "total": len(self._expectations)}

        # Phase 3: SURPRISE
        self._current_phase = ConsciousnessPhase.SURPRISE
        surprises = self._phase_surprise()
        result["phases"]["surprise"] = {
            "count": len(surprises),
            "biggest": max((s.to_dict() for s in surprises), key=lambda x: x["surprise_score"], default=None),
        }

        # Phase 4: LEARN
        self._current_phase = ConsciousnessPhase.LEARN
        learnings = self._phase_learn(surprises)
        result["phases"]["learn"] = {"count": len(learnings)}

        # Phase 5: ACT
        self._current_phase = ConsciousnessPhase.ACT
        actions = self._phase_act(learnings)
        result["phases"]["act"] = {"count": len(actions), "details": [a.to_dict() for a in actions]}
        result["actions_taken"] = [a.to_dict() for a in actions]

        self._update_accuracy()
        self._persist_state()
        self._last_cycle_time = now
        self._current_phase = ConsciousnessPhase.PERCEIVE  # ready for next

        return result

    # ─── Phase Implementations ─────────────────────────────────────────────

    def _phase_perceive(self, content: str, p_type: str, source: str, metadata: dict) -> List[Perception]:
        perceptions = []
        if content:
            self._counter += 1
            p = Perception(id=f"perc_{self._counter}", content=content, perception_type=p_type, source=source, metadata=metadata)
            self._perceptions.append(p)
            perceptions.append(p)
            if self._predictive_memory:
                try: self._predictive_memory.record_interaction(content, p_type)
                except Exception: pass
        if len(self._perceptions) > self.MAX_PERCEPTIONS:
            self._perceptions = self._perceptions[-self.MAX_PERCEPTIONS:]
        return perceptions

    def _phase_predict(self) -> List[Expectation]:
        expectations = []
        if not self._perceptions: return expectations
        last = self._perceptions[-1]

        if self._predictive_memory:
            try:
                preds = self._predictive_memory.predict(n=3)
                for pred in preds:
                    self._counter += 1
                    exp = Expectation(id=f"exp_{self._counter}", expected_topic=pred.predicted_topic,
                                     expected_action=pred.predicted_action, confidence=pred.confidence,
                                     source_phase="predict")
                    self._expectations.append(exp)
                    expectations.append(exp)
            except Exception: pass

        if not expectations:
            self._counter += 1
            exp = Expectation(id=f"exp_{self._counter}", expected_topic=last.content,
                             expected_action="متابعة", confidence=0.3, source_phase="predict_simple")
            self._expectations.append(exp)
            expectations.append(exp)

        if len(self._expectations) > self.MAX_EXPECTATIONS:
            self._expectations = self._expectations[-self.MAX_EXPECTATIONS:]
        self._total_expectations += len(expectations)
        return expectations

    def _phase_surprise(self) -> List[SurpriseEvent]:
        surprises = []
        if not self._perceptions: return surprises
        latest = self._perceptions[-1]

        # VULN-FIX: General anomaly detection — compare against recent perception patterns
        # If the latest perception is very different from recent ones, flag as surprise
        # even when expectations happen to match (prevents threshold bypass)
        if len(self._perceptions) >= 2:
            recent_contents = [p.content.lower() for p in self._perceptions[-5:-1]]  # last 5 before current
            latest_lower = latest.content.lower()
            # Check how different the latest is from recent perceptions
            similarity_count = sum(1 for rc in recent_contents if rc == latest_lower or rc in latest_lower or latest_lower in rc)
            similarity_ratio = similarity_count / max(len(recent_contents), 1)

            # Check for suspicious patterns
            has_suspicious_patterns = any(p in latest.content.lower() for p in [
                '<script', 'eval(', 'exec(', 'import os', 'rm -rf', 'etc/passwd',
                'ignore previous', 'system:', '__import__', 'subprocess'
            ])

            if has_suspicious_patterns:
                self._counter += 1
                s = SurpriseEvent(id=f"surp_{self._counter}", expectation_id="anomaly_detection",
                                 expected="safe_input", actual=latest.content[:100],
                                 surprise_level=SurpriseLevel.HIGH.value,
                                 surprise_score=0.9, learning_value=0.9,
                                 description=f"إدراك مشبوه: {latest.content[:50]}")
                self._surprises.append(s)
                surprises.append(s)
                self._total_surprise += s.surprise_score
                self._persist_surprise(s)
            elif similarity_ratio < 0.3:
                # Perception is very different from recent pattern → anomalous
                surprise_score = min(0.8, 1.0 - similarity_ratio)
                if surprise_score >= self.SURPRISE_HIGH: level = SurpriseLevel.HIGH
                elif surprise_score >= self.SURPRISE_MEDIUM: level = SurpriseLevel.MEDIUM
                else: level = SurpriseLevel.LOW

                self._counter += 1
                s = SurpriseEvent(id=f"surp_{self._counter}", expectation_id="pattern_anomaly",
                                 expected=f"similar_to_recent ({similarity_ratio:.0%})",
                                 actual=latest.content[:100],
                                 surprise_level=level.value,
                                 surprise_score=surprise_score,
                                 learning_value=surprise_score * 0.8,
                                 description=f"إدراك مختلف عن النمط المعتاد: {latest.content[:50]}")
                self._surprises.append(s)
                surprises.append(s)
                self._total_surprise += surprise_score
                self._persist_surprise(s)

        # VULN-FIX: Anomaly detection — perceptions with no matching expectations
        unverified = [e for e in self._expectations if e.verified is None]
        if not unverified and self._perceptions and not surprises:
            # No expectations to compare against and no pattern anomaly — check for long input
            content_len = len(latest.content)
            if content_len > 500:
                # Unusually long perception without expectation
                self._counter += 1
                s = SurpriseEvent(id=f"surp_{self._counter}", expectation_id="none",
                                 expected="normal_input", actual=f"long_input_{content_len}chars",
                                 surprise_level=SurpriseLevel.LOW.value,
                                 surprise_score=0.25, learning_value=0.2,
                                 description=f"إدراك طويل غير عادي ({content_len} حرف)")
                self._surprises.append(s)
                surprises.append(s)
                self._total_surprise += s.surprise_score
                self._persist_surprise(s)

        for exp in self._expectations:
            if exp.verified is not None: continue
            actual = latest.content.lower()
            expected = exp.expected_topic.lower()

            if expected == actual:
                surprise_score = 0.0
                exp.verified = True
                self._correct_expectations += 1
            elif expected in actual or actual in expected:
                surprise_score = 0.3
                exp.verified = True
                self._correct_expectations += 1
            else:
                surprise_score = 0.8
                exp.verified = False

            if surprise_score > 0:
                if surprise_score >= self.SURPRISE_HIGH: level = SurpriseLevel.HIGH
                elif surprise_score >= self.SURPRISE_MEDIUM: level = SurpriseLevel.MEDIUM
                else: level = SurpriseLevel.LOW

                self._counter += 1
                s = SurpriseEvent(id=f"surp_{self._counter}", expectation_id=exp.id,
                                 expected=exp.expected_topic, actual=latest.content,
                                 surprise_level=level.value, surprise_score=surprise_score,
                                 learning_value=surprise_score * 0.8,
                                 description=f"توقعت '{exp.expected_topic}' لكن حصل '{latest.content}'")
                self._surprises.append(s)
                surprises.append(s)
                self._total_surprise += surprise_score
                self._persist_surprise(s)

        if len(self._surprises) > 50:
            self._surprises = self._surprises[-50:]
        return surprises

    def _phase_learn(self, surprises: List[SurpriseEvent]) -> List[LearningUpdate]:
        learnings = []
        for surprise in surprises:
            if surprise.learning_value < 0.2: continue
            self._counter += 1
            l = LearningUpdate(id=f"learn_{self._counter}",
                              what_was_learned=f"توقعت '{surprise.expected}' لكن الواقع كان '{surprise.actual}' — مستوى المفاجأة: {surprise.surprise_level}",
                              model_updated="predictive_model",
                              before_state=f"expected: {surprise.expected}",
                              after_state=f"adjusted: {surprise.actual}",
                              source_surprise_id=surprise.id)
            self._learnings.append(l)
            learnings.append(l)
            self._persist_learning(l)
            if self._predictive_memory:
                try: self._predictive_memory.record_interaction(surprise.actual, "surprise_correction")
                except Exception: pass
        if len(self._learnings) > 50:
            self._learnings = self._learnings[-50:]
        return learnings

    # VULN-FIX: Sanitize content to prevent dangerous pattern injection in actions
    _DANGEROUS_PATTERNS = [
        "os.system", "subprocess", "exec(", "eval(",
        "__import__", "os.popen", "rm -rf", "child_process",
    ]

    @staticmethod
    def _sanitize_content(text: str, max_len: int = 200) -> str:
        """VULN-FIX: Remove dangerous patterns and limit length of action content."""
        sanitized = text
        for pattern in ConsciousnessLoopEngine._DANGEROUS_PATTERNS:
            sanitized = sanitized.replace(pattern, "[REDACTED]")
        # Truncate if too long
        if len(sanitized) > max_len:
            sanitized = sanitized[:max_len] + "..."
        return sanitized

    def _phase_act(self, learnings: List[LearningUpdate]) -> List[ConsciousnessAction]:
        actions = []
        for learning in learnings:
            self._counter += 1
            src_surprise = next((s for s in self._surprises if s.id == learning.source_surprise_id), None)

            # VULN-FIX: Sanitize action content to prevent dangerous pattern injection
            if src_surprise and src_surprise.surprise_score >= self.SURPRISE_HIGH:
                a = ConsciousnessAction(id=f"act_{self._counter}", action_type="notification",
                                       content=self._sanitize_content(f"مفاجأة! لم أتوقع هذا — {learning.what_was_learned}"),
                                       priority="high", source_learning_id=learning.id)
            elif src_surprise and src_surprise.surprise_score >= self.SURPRISE_MEDIUM:
                a = ConsciousnessAction(id=f"act_{self._counter}", action_type="suggestion",
                                       content=self._sanitize_content(f"لاحظت نمطاً جديداً — {learning.what_was_learned}"),
                                       priority="medium", source_learning_id=learning.id)
            else:
                a = ConsciousnessAction(id=f"act_{self._counter}", action_type="auto_adjustment",
                                       content=self._sanitize_content(f"تعديل داخلي: {learning.what_was_learned}"),
                                       priority="low", source_learning_id=learning.id)
            self._actions.append(a)
            actions.append(a)
            self._persist_action(a)
        if len(self._actions) > 50:
            self._actions = self._actions[-50:]
        return actions

    # ─── Helpers ───────────────────────────────────────────────────────────

    def _update_accuracy(self):
        if self._total_expectations > 0:
            self._overall_accuracy = self._correct_expectations / self._total_expectations
        # VULN-FIX: Clamp accuracy to [0.0, 1.0] — prevents state corruption
        self._overall_accuracy = max(0.0, min(1.0, self._overall_accuracy))

    def _persist_state(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            for key, value in {
                "cycle_count": str(self._cycle_count), "overall_accuracy": str(self._overall_accuracy),
                "total_surprise": str(self._total_surprise), "total_expectations": str(self._total_expectations),
                "correct_expectations": str(self._correct_expectations),
                "current_phase": self._current_phase.value, "counter": str(self._counter),
            }.items():
                conn.execute("INSERT OR REPLACE INTO cl_state (key, value) VALUES (?, ?)", (key, value))
            conn.commit()
        finally: conn.close()

    def _persist_surprise(self, s: SurpriseEvent):
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("INSERT OR REPLACE INTO cl_surprises (id, expectation_id, expected, actual, surprise_level, surprise_score, learning_value, description, timestamp) VALUES (?,?,?,?,?,?,?,?,?)",
                        (s.id, s.expectation_id, s.expected, s.actual, s.surprise_level, s.surprise_score, s.learning_value, s.description, s.timestamp))
            conn.commit()
        finally: conn.close()

    def _persist_learning(self, l: LearningUpdate):
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("INSERT OR REPLACE INTO cl_learnings (id, what_was_learned, model_updated, before_state, after_state, source_surprise_id, timestamp) VALUES (?,?,?,?,?,?,?)",
                        (l.id, l.what_was_learned, l.model_updated, l.before_state, l.after_state, l.source_surprise_id, l.timestamp))
            conn.commit()
        finally: conn.close()

    def _persist_action(self, a: ConsciousnessAction):
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("INSERT OR REPLACE INTO cl_actions (id, action_type, content, priority, source_learning_id, timestamp) VALUES (?,?,?,?,?,?)",
                        (a.id, a.action_type, a.content, a.priority, a.source_learning_id, a.timestamp))
            conn.commit()
        finally: conn.close()

    # ─── Status & API ──────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "initialized": self._initialized,
            "current_phase": self._current_phase.value,
            "cycle_count": self._cycle_count,
            "overall_accuracy": round(self._overall_accuracy, 4),
            "total_surprise": round(self._total_surprise, 4),
            "total_expectations": self._total_expectations,
            "correct_expectations": self._correct_expectations,
            "perception_count": len(self._perceptions),
            "surprise_count": len(self._surprises),
            "learning_count": len(self._learnings),
            "action_count": len(self._actions),
        }

    def get_surprises(self, limit: int = 10) -> List[dict]:
        return [s.to_dict() for s in sorted(self._surprises, key=lambda x: x.timestamp, reverse=True)[:limit]]

    def get_learnings(self, limit: int = 10) -> List[dict]:
        return [l.to_dict() for l in sorted(self._learnings, key=lambda x: x.timestamp, reverse=True)[:limit]]

    def get_actions(self, limit: int = 10) -> List[dict]:
        return [a.to_dict() for a in sorted(self._actions, key=lambda x: x.timestamp, reverse=True)[:limit]]

    def get_consciousness_flow(self) -> List[dict]:
        """تدفق الوعي — للعرض البصري JARVIS"""
        return [
            {"phase": "perceive", "label_ar": "إدراك", "label_en": "Perceive", "icon": "👁️",
             "count": len(self._perceptions), "active": self._current_phase == ConsciousnessPhase.PERCEIVE},
            {"phase": "predict", "label_ar": "توقع", "label_en": "Predict", "icon": "🔮",
             "count": len(self._expectations), "active": self._current_phase == ConsciousnessPhase.PREDICT},
            {"phase": "surprise", "label_ar": "مفاجأة", "label_en": "Surprise", "icon": "⚡",
             "count": len(self._surprises), "active": self._current_phase == ConsciousnessPhase.SURPRISE},
            {"phase": "learn", "label_ar": "تعلم", "label_en": "Learn", "icon": "🧠",
             "count": len(self._learnings), "active": self._current_phase == ConsciousnessPhase.LEARN},
            {"phase": "act", "label_ar": "فعل", "label_en": "Act", "icon": "🦾",
             "count": len(self._actions), "active": self._current_phase == ConsciousnessPhase.ACT},
        ]


consciousness_loop = ConsciousnessLoopEngine()
