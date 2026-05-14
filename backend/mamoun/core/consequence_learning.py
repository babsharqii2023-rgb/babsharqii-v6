"""
BABSHARQII v24.0 — Consequence Learning Engine
محرك التعلم من العواقب — كل فعل له نتيجة ومأمون يتعلم منها

Core idea: Track every action Mamoun takes, wait for the outcome,
then update internal models based on whether the outcome was positive or negative.

This connects:
- EpisodicMemoryV2 (stores the experience)
- CausalGraph (updates causal weights)
- MetacognitiveEngine (updates confidence calibration)
- BehavioralMemory (adjusts personality)

Usage:
    cle = ConsequenceLearningEngine()
    cle.initialize()
    
    # Before action
    action_id = cle.register_action("gave_detailed_response", context="user_asking_quick_question")
    
    # ... time passes ...
    
    # After observing outcome
    cle.record_outcome(action_id, outcome="user_got_bored", positive=False)
    # → Updates causal graph, episodic memory, and behavioral traits
"""
import os, time, uuid, json, logging
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from pathlib import Path

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.consequence_learning")


@dataclass
class ActionRecord:
    """سجل فعل — ماذا فعلنا ومتى"""
    action_id: str = ""
    action_type: str = ""
    context: str = ""
    expected_outcome: str = ""
    confidence: float = 0.5
    timestamp: float = 0.0
    outcome_recorded: bool = False

    def __post_init__(self):
        if not self.action_id:
            self.action_id = f"act_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class OutcomeRecord:
    """سجل نتيجة — ماذا حدث فعلاً"""
    outcome_id: str = ""
    action_id: str = ""
    outcome: str = ""
    positive: bool = True
    user_reaction: str = ""
    surprise: float = 0.0  # how surprising was this outcome? (0=expected, 1=very surprising)
    lessons_extracted: int = 0
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.outcome_id:
            self.outcome_id = f"out_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


class ConsequenceLearningEngine:
    """
    محرك التعلم من العواقب
    
    Connects all the v24 systems into a unified learning loop:
    Action → Outcome → Update CausalGraph + EpisodicMemory + Metacognition + Behavior
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._actions: Dict[str, ActionRecord] = {}
        self._outcomes: Dict[str, OutcomeRecord] = {}
        self._llm = None
        self._causal_graph = None
        self._episodic_memory = None
        self._metacognitive = None
        self._behavioral = None
        self._initialized = False

    def set_llm_client(self, llm_client):
        self._llm = llm_client

    def set_systems(self, causal_graph=None, episodic_memory=None,
                    metacognitive=None, behavioral=None):
        """ربط مع الأنظمة الأخرى"""
        self._causal_graph = causal_graph
        self._episodic_memory = episodic_memory
        self._metacognitive = metacognitive
        self._behavioral = behavioral

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("ConsequenceLearningEngine initialized — actions=%d", len(self._actions))
            return True
        except Exception as e:
            logger.error("ConsequenceLearningEngine init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cl_actions (
                    action_id TEXT PRIMARY KEY,
                    action_type TEXT DEFAULT '',
                    context TEXT DEFAULT '',
                    expected_outcome TEXT DEFAULT '',
                    confidence REAL DEFAULT 0.5,
                    timestamp REAL DEFAULT 0,
                    outcome_recorded INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cl_outcomes (
                    outcome_id TEXT PRIMARY KEY,
                    action_id TEXT NOT NULL,
                    outcome TEXT DEFAULT '',
                    positive INTEGER DEFAULT 1,
                    user_reaction TEXT DEFAULT '',
                    surprise REAL DEFAULT 0,
                    lessons_extracted INTEGER DEFAULT 0,
                    timestamp REAL DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cl_outcomes_aid ON cl_outcomes(action_id)")
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT * FROM cl_actions"):
                a = ActionRecord(
                    action_id=row[0], action_type=row[1], context=row[2],
                    expected_outcome=row[3], confidence=row[4],
                    timestamp=row[5], outcome_recorded=bool(row[6])
                )
                self._actions[a.action_id] = a
            for row in conn.execute("SELECT * FROM cl_outcomes"):
                o = OutcomeRecord(
                    outcome_id=row[0], action_id=row[1], outcome=row[2],
                    positive=bool(row[3]), user_reaction=row[4],
                    surprise=row[5], lessons_extracted=row[6], timestamp=row[7]
                )
                self._outcomes[o.outcome_id] = o
        finally:
            conn.close()

    def _persist_action(self, a: ActionRecord):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO cl_actions
                (action_id, action_type, context, expected_outcome, confidence, timestamp, outcome_recorded)
                VALUES (?,?,?,?,?,?,?)
            """, (a.action_id, a.action_type, a.context, a.expected_outcome,
                  a.confidence, a.timestamp, int(a.outcome_recorded)))
            conn.commit()
        finally:
            conn.close()

    def _persist_outcome(self, o: OutcomeRecord):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO cl_outcomes
                (outcome_id, action_id, outcome, positive, user_reaction, surprise, lessons_extracted, timestamp)
                VALUES (?,?,?,?,?,?,?,?)
            """, (o.outcome_id, o.action_id, o.outcome, int(o.positive),
                  o.user_reaction, o.surprise, o.lessons_extracted, o.timestamp))
            conn.commit()
        finally:
            conn.close()

    def register_action(self, action_type: str, context: str = "",
                        expected_outcome: str = "", confidence: float = 0.5) -> ActionRecord:
        """تسجيل فعل قبل تنفيذه"""
        action = ActionRecord(
            action_type=action_type, context=context,
            expected_outcome=expected_outcome, confidence=confidence,
        )
        self._actions[action.action_id] = action
        self._persist_action(action)
        return action

    def record_outcome(self, action_id: str, outcome: str,
                       positive: bool = True, user_reaction: str = "") -> Optional[OutcomeRecord]:
        """تسجيل نتيجة فعل — وتحديث كل الأنظمة المرتبطة"""
        action = self._actions.get(action_id)
        if not action:
            return None

        # Calculate surprise
        expected_positive = action.confidence > 0.5
        surprise = abs(action.confidence - (1.0 if positive else 0.0))

        outcome_rec = OutcomeRecord(
            action_id=action_id, outcome=outcome,
            positive=positive, user_reaction=user_reaction,
            surprise=round(surprise, 3),
        )
        self._outcomes[outcome_rec.outcome_id] = outcome_rec
        action.outcome_recorded = True
        self._persist_outcome(outcome_rec)
        self._persist_action(action)

        lessons_count = 0

        # 1. Update CausalGraph
        if self._causal_graph and self._causal_graph._initialized:
            try:
                self._causal_graph.learn_from_outcome(
                    cause=action.action_type,
                    effect=outcome,
                    actually_happened=positive,
                    context=action.context,
                )
                lessons_count += 1
            except Exception as e:
                logger.warning("CausalGraph update failed: %s", e)

        # 2. Update EpisodicMemory
        if self._episodic_memory and self._episodic_memory._initialized:
            try:
                ep = self._episodic_memory.record(
                    situation=action.context,
                    action_taken=action.action_type,
                    outcome=outcome,
                    outcome_positive=positive,
                    outcome_user_reaction=user_reaction,
                )
                self._episodic_memory.extract_lesson(
                    ep.episode_id,
                    lesson=f"{'Do' if positive else 'Avoid'} '{action.action_type}' in context '{action.context[:50]}'",
                    confidence=1.0 - surprise,
                )
                lessons_count += 1
            except Exception as e:
                logger.warning("EpisodicMemory update failed: %s", e)

        # 3. Update Metacognitive
        if self._metacognitive and self._metacognitive._initialized:
            try:
                # Find latest assessment for this topic
                for aid, a in reversed(list(self._metacognitive._assessments.items())):
                    if action.action_type in a.topic or a.topic in action.context:
                        self._metacognitive.reflect(
                            a.assessment_id,
                            expected_outcome=action.expected_outcome or "positive",
                            actual_outcome=outcome,
                            success=positive,
                        )
                        lessons_count += 1
                        break
            except Exception as e:
                logger.warning("Metacognitive update failed: %s", e)

        # 4. Update BehavioralMemory
        if self._behavioral and self._behavioral._initialized:
            try:
                feedback = "liked" if positive else "disliked"
                self._behavioral.record_interaction(
                    user_message=action.context,
                    mamoun_response=action.action_type,
                    user_feedback=feedback,
                )
                lessons_count += 1
            except Exception as e:
                logger.warning("BehavioralMemory update failed: %s", e)

        outcome_rec.lessons_extracted = lessons_count
        self._persist_outcome(outcome_rec)

        return outcome_rec

    def get_stats(self) -> Dict:
        actions = list(self._actions.values())
        outcomes = list(self._outcomes.values())
        return {
            "total_actions": len(actions),
            "total_outcomes": len(outcomes),
            "positive_rate": round(
                len([o for o in outcomes if o.positive]) / max(len(outcomes), 1), 3
            ),
            "avg_surprise": round(
                sum(o.surprise for o in outcomes) / max(len(outcomes), 1), 3
            ),
            "total_lessons": sum(o.lessons_extracted for o in outcomes),
        }


consequence_learning = ConsequenceLearningEngine()
