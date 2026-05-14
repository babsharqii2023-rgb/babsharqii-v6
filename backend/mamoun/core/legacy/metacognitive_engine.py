"""
BABSHARQII v24.0 — Metacognitive Engine
محرك الوعي الذاتي — مأمون يعرف ماذا يعرف وماذا لا يعرف

Core loop:
1. ASSESS: After thinking, rate own confidence and identify knowledge gaps
2. PLAN: Decide whether to respond, research, ask for clarification, or escalate
3. REFLECT: After response, evaluate if the outcome matched expectations
4. ADAPT: Adjust future behavior based on reflection

This is what separates a chatbot from an AGI — the ability to know its limits.
"""
import os, time, uuid, json, logging
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from pathlib import Path

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.metacognitive")


@dataclass
class SelfAssessment:
    """تقييم ذاتي للاستجابة"""
    assessment_id: str = ""
    topic: str = ""
    confidence: float = 0.5          # how confident are we
    knowledge_gaps: List[str] = field(default_factory=list)  # what don't we know
    uncertainty_sources: List[str] = field(default_factory=list)  # why uncertain
    strategy: str = "respond"        # respond, research, clarify, escalate, defer
    strategy_reason: str = ""
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.assessment_id:
            self.assessment_id = f"meta_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Reflection:
    """تأمل بعد الاستجابة — هل كانت النتيجة كما توقعنا؟"""
    reflection_id: str = ""
    assessment_id: str = ""
    expected_outcome: str = ""
    actual_outcome: str = ""
    outcome_matched: bool = True
    confidence_was_calibrated: bool = True  # was our confidence accurate?
    lesson: str = ""
    calibration_error: float = 0.0  # |expected_confidence - actual_success|
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.reflection_id:
            self.reflection_id = f"refl_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


class MetacognitiveEngine:
    """
    محرك الوعي الذاتي
    
    Usage:
        meta = MetacognitiveEngine()
        meta.initialize()
        
        # Before responding
        assessment = meta.assess("quantum computing", confidence=0.3)
        if assessment.strategy == "research":
            # Go research first
            ...
        elif assessment.strategy == "clarify":
            # Ask user for more info
            ...
        
        # After responding
        reflection = meta.reflect(assessment.assessment_id,
            expected_outcome="User will understand",
            actual_outcome="User was confused")
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._assessments: Dict[str, SelfAssessment] = {}
        self._reflections: Dict[str, Reflection] = {}
        self._calibration_history: List[float] = []  # track calibration over time
        self._llm = None
        self._initialized = False

    def set_llm_client(self, llm_client):
        self._llm = llm_client

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("MetacognitiveEngine initialized — assessments=%d", len(self._assessments))
            return True
        except Exception as e:
            logger.error("MetacognitiveEngine init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meta_assessments (
                    assessment_id TEXT PRIMARY KEY,
                    topic TEXT DEFAULT '',
                    confidence REAL DEFAULT 0.5,
                    knowledge_gaps TEXT DEFAULT '[]',
                    uncertainty_sources TEXT DEFAULT '[]',
                    strategy TEXT DEFAULT 'respond',
                    strategy_reason TEXT DEFAULT '',
                    timestamp REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meta_reflections (
                    reflection_id TEXT PRIMARY KEY,
                    assessment_id TEXT DEFAULT '',
                    expected_outcome TEXT DEFAULT '',
                    actual_outcome TEXT DEFAULT '',
                    outcome_matched INTEGER DEFAULT 1,
                    confidence_was_calibrated INTEGER DEFAULT 1,
                    lesson TEXT DEFAULT '',
                    calibration_error REAL DEFAULT 0,
                    timestamp REAL DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_meta_reflections_aid ON meta_reflections(assessment_id)")
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT * FROM meta_assessments"):
                a = SelfAssessment(
                    assessment_id=row[0], topic=row[1], confidence=row[2],
                    knowledge_gaps=json.loads(row[3]),
                    uncertainty_sources=json.loads(row[4]),
                    strategy=row[5], strategy_reason=row[6], timestamp=row[7]
                )
                self._assessments[a.assessment_id] = a
            for row in conn.execute("SELECT * FROM meta_reflections"):
                r = Reflection(
                    reflection_id=row[0], assessment_id=row[1],
                    expected_outcome=row[2], actual_outcome=row[3],
                    outcome_matched=bool(row[4]),
                    confidence_was_calibrated=bool(row[5]),
                    lesson=row[6], calibration_error=row[7], timestamp=row[8]
                )
                self._reflections[r.reflection_id] = r
                self._calibration_history.append(r.calibration_error)
        finally:
            conn.close()

    def _persist_assessment(self, a: SelfAssessment):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO meta_assessments
                (assessment_id, topic, confidence, knowledge_gaps, uncertainty_sources,
                 strategy, strategy_reason, timestamp)
                VALUES (?,?,?,?,?,?,?,?)
            """, (a.assessment_id, a.topic, a.confidence,
                  json.dumps(a.knowledge_gaps), json.dumps(a.uncertainty_sources),
                  a.strategy, a.strategy_reason, a.timestamp))
            conn.commit()
        finally:
            conn.close()

    def _persist_reflection(self, r: Reflection):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO meta_reflections
                (reflection_id, assessment_id, expected_outcome, actual_outcome,
                 outcome_matched, confidence_was_calibrated, lesson, calibration_error, timestamp)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (r.reflection_id, r.assessment_id, r.expected_outcome,
                  r.actual_outcome, int(r.outcome_matched), int(r.confidence_was_calibrated),
                  r.lesson, r.calibration_error, r.timestamp))
            conn.commit()
        finally:
            conn.close()

    def assess(self, topic: str, confidence: float = 0.5,
               context: str = "") -> SelfAssessment:
        """
        تقييم ذاتي — هل نعرف الإجابة؟ ما الذي لا نعرفه؟
        
        Strategy selection:
        - confidence > 0.7 → "respond" (we know this)
        - confidence 0.4-0.7 → "respond_with_caveat" (we kinda know)
        - confidence 0.2-0.4 → "research" (we should look it up first)
        - confidence < 0.2 → "clarify" or "escalate" (ask user or stronger model)
        """
        # Determine knowledge gaps based on confidence
        gaps = []
        uncertainty = []
        if confidence < 0.7:
            gaps.append(f"Insufficient knowledge about {topic}")
        if confidence < 0.4:
            uncertainty.append("Low confidence — may hallucinate")
        if confidence < 0.2:
            uncertainty.append("Very likely to be wrong — should not answer directly")

        # Strategy selection
        if confidence >= 0.7:
            strategy = "respond"
            reason = f"High confidence ({confidence:.1f}) — can answer directly"
        elif confidence >= 0.4:
            strategy = "respond_with_caveat"
            reason = f"Medium confidence ({confidence:.1f}) — answer but express uncertainty"
        elif confidence >= 0.2:
            strategy = "research"
            reason = f"Low confidence ({confidence:.1f}) — should research before answering"
        else:
            strategy = "clarify"
            reason = f"Very low confidence ({confidence:.1f}) — ask user for clarification"

        # Check calibration history — if we've been overconfident, be more cautious
        if len(self._calibration_history) > 5:
            avg_error = sum(self._calibration_history[-10:]) / len(self._calibration_history[-10:])
            if avg_error > 0.3:
                # We've been miscalibrated — be more conservative
                adjusted = confidence * 0.8
                if adjusted < 0.4 and strategy == "respond_with_caveat":
                    strategy = "research"
                    reason += " (adjusted down due to poor calibration history)"

        assessment = SelfAssessment(
            topic=topic, confidence=confidence,
            knowledge_gaps=gaps, uncertainty_sources=uncertainty,
            strategy=strategy, strategy_reason=reason,
        )
        self._assessments[assessment.assessment_id] = assessment
        self._persist_assessment(assessment)
        return assessment

    def reflect(self, assessment_id: str, expected_outcome: str,
                actual_outcome: str, success: bool = True) -> Reflection:
        """
        تأمل — هل كانت استجابتنا صحيحة؟
        
        This is the KEY to metacognition: comparing expectations to reality
        """
        assessment = self._assessments.get(assessment_id)
        predicted_confidence = assessment.confidence if assessment else 0.5
        
        # Calculate calibration error
        actual_success = 1.0 if success else 0.0
        calibration_error = abs(predicted_confidence - actual_success)
        
        # Was confidence calibrated?
        calibrated = calibration_error < 0.3
        
        # Auto-extract lesson
        # v35 FIX: 'topic' was used as fallback but was never defined as a local variable
        topic_str = assessment.topic if assessment else "unknown"
        if success:
            lesson = f"Our confidence ({predicted_confidence:.1f}) was well-calibrated for '{topic_str}'"
        else:
            lesson = f"We were {'over' if predicted_confidence > 0.5 else 'under'}confident ({predicted_confidence:.1f}) about '{topic_str}' — should have been more cautious"
            if predicted_confidence > 0.7 and not success:
                lesson = f"OVERCONFIDENCE: Predicted {predicted_confidence:.1f} but failed on '{topic_str}'"

        reflection = Reflection(
            assessment_id=assessment_id,
            expected_outcome=expected_outcome,
            actual_outcome=actual_outcome,
            outcome_matched=success,
            confidence_was_calibrated=calibrated,
            lesson=lesson,
            calibration_error=calibration_error,
        )
        self._reflections[reflection.reflection_id] = reflection
        self._calibration_history.append(calibration_error)
        self._persist_reflection(reflection)
        return reflection

    def get_calibration_score(self) -> float:
        """How well-calibrated is our confidence? 1.0 = perfect, 0.0 = terrible"""
        if not self._calibration_history:
            return 0.5
        avg_error = sum(self._calibration_history) / len(self._calibration_history)
        return round(1.0 - avg_error, 3)

    def get_stats(self) -> Dict:
        return {
            "total_assessments": len(self._assessments),
            "total_reflections": len(self._reflections),
            "calibration_score": self.get_calibration_score(),
            "strategy_distribution": {
                s: len([a for a in self._assessments.values() if a.strategy == s])
                for s in set(a.strategy for a in self._assessments.values())
            } if self._assessments else {},
        }

    def get_recent_assessments(self, limit=20) -> List[dict]:
        return [a.to_dict() for a in sorted(self._assessments.values(),
                key=lambda x: x.timestamp, reverse=True)[:limit]]

    def get_recent_reflections(self, limit=20) -> List[dict]:
        return [r.to_dict() for r in sorted(self._reflections.values(),
                key=lambda x: x.timestamp, reverse=True)[:limit]]


metacognitive_engine = MetacognitiveEngine()
