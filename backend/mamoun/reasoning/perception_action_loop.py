"""
BABSHARQII v26.0 — Perception-Action Loop Engine
محرك الحلقة الإدراكية-التنفيذية — بدون LLM

The fundamental AGI loop:
1. PERCEIVE: Extract features from input
2. INTERPRET: Match against known patterns
3. EVALUATE: Assess situation urgency/importance
4. DECIDE: Choose action (reactive or deliberative)
5. ACT: Execute the chosen action
6. OBSERVE: Monitor outcome
7. ADAPT: Update internal model based on result

Based on: OODA Loop (Boyd), Sense-Think-Act architecture
"""

import time, uuid, json, logging, numpy as np
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
from enum import Enum

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.perception_action_loop")


class PALPhase(str, Enum):
    PERCEIVE = "perceive"
    INTERPRET = "interpret"
    EVALUATE = "evaluate"
    DECIDE = "decide"
    ACT = "act"
    OBSERVE = "observe"
    ADAPT = "adapt"


@dataclass
class Perception:
    """إدراك — ما يستقبله النظام"""
    perception_id: str = ""
    input_type: str = "text"  # text, event, signal
    raw_input: str = ""
    features: Dict[str, float] = field(default_factory=dict)
    salience: float = 0.5
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.perception_id:
            self.perception_id = f"perc_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()


@dataclass
class ActionDecision:
    """قرار فعل — ماذا سيفعل النظام"""
    decision_id: str = ""
    action_type: str = "respond"  # respond, wait, explore, escalate, ignore
    action_params: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    urgency: float = 0.5
    reasoning: str = ""
    phase_trace: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.decision_id:
            self.decision_id = f"dec_{uuid.uuid4().hex[:8]}"


class PerceptionActionLoop:
    """
    حلقة الإدراك-الفعل — التفاعل المستمر مع البيئة

    Complete OODA-style loop without LLM dependency.
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._llm = None
        self._initialized = False
        self._perception_history: List[Perception] = []
        self._decision_history: List[ActionDecision] = []
        self._action_outcomes: Dict[str, bool] = {}
        self._feature_extractors: Dict[str, Any] = {}
        self._action_thresholds = {
            "respond": 0.3, "wait": 0.2, "explore": 0.5,
            "escalate": 0.8, "ignore": 0.1,
        }

    def set_llm_client(self, llm_client):
        self._llm = llm_client  # NOT USED

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("PerceptionActionLoop initialized")
            return True
        except Exception as e:
            logger.error("PAL init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS pal_perceptions (
                perception_id TEXT PRIMARY KEY, input_type TEXT, raw_input TEXT,
                features TEXT, salience REAL, timestamp REAL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS pal_decisions (
                decision_id TEXT PRIMARY KEY, action_type TEXT, action_params TEXT,
                confidence REAL, urgency REAL, reasoning TEXT, phase_trace TEXT, timestamp REAL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS pal_outcomes (
                decision_id TEXT PRIMARY KEY, outcome TEXT, reward REAL, timestamp REAL)""")
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT decision_id, outcome, reward FROM pal_outcomes"):
                self._action_outcomes[row[0]] = row[1] == "positive"
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════
    # The Complete Loop
    # ═══════════════════════════════════════════════════════════════

    def process(self, raw_input: str, input_type: str = "text",
                context: Dict = None) -> ActionDecision:
        """
        المعالجة الكاملة: إدراك → تفسير → تقييم → قرار → فعل
        """
        context = context or {}
        decision = ActionDecision()

        # Phase 1: PERCEIVE
        perception = self._perceive(raw_input, input_type)
        decision.phase_trace.append(PALPhase.PERCEIVE.value)

        # Phase 2: INTERPRET
        interpretation = self._interpret(perception)
        decision.phase_trace.append(PALPhase.INTERPRET.value)

        # Phase 3: EVALUATE
        evaluation = self._evaluate(perception, interpretation, context)
        decision.phase_trace.append(PALPhase.EVALUATE.value)

        # Phase 4: DECIDE
        action_type, confidence, reasoning = self._decide(evaluation, context)
        decision.action_type = action_type
        decision.confidence = confidence
        decision.urgency = evaluation.get("urgency", 0.5)
        decision.reasoning = reasoning
        decision.phase_trace.append(PALPhase.DECIDE.value)

        # Phase 5: ACT (return decision for kernel to execute)
        decision.phase_trace.append(PALPhase.ACT.value)

        self._decision_history.append(decision)
        self._persist_decision(decision)
        return decision

    def observe_outcome(self, decision_id: str, outcome: str, reward: float = 0.0):
        """مراقبة النتيجة — Phase 6+7"""
        self._action_outcomes[decision_id] = outcome == "positive"
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("INSERT OR REPLACE INTO pal_outcomes VALUES (?,?,?,?)",
                (decision_id, outcome, reward, time.time()))
            conn.commit()
        finally:
            conn.close()

    def _perceive(self, raw_input: str, input_type: str) -> Perception:
        """استخلاص الخصائص من المدخل"""
        features = {}
        if input_type == "text":
            features["length"] = len(raw_input)
            features["word_count"] = len(raw_input.split())
            features["question"] = 1.0 if "?" in raw_input or "؟" in raw_input else 0.0
            features["arabic_ratio"] = sum(1 for c in raw_input if '\u0600' <= c <= '\u06FF') / max(len(raw_input), 1)
            features["exclamation"] = 1.0 if "!" in raw_input else 0.0
            features["urgency_words"] = sum(1 for w in ["عاجل", "urgent", "الآن", "now", "فوراً"] if w in raw_input.lower()) / 3.0

        salience = min(1.0, features.get("urgency_words", 0) * 2 + features.get("question", 0) * 0.3 + 0.3)
        perc = Perception(input_type=input_type, raw_input=raw_input[:200],
                          features=features, salience=salience)
        self._perception_history.append(perc)
        return perc

    def _interpret(self, perception: Perception) -> Dict:
        """تفسير — مطابقة مع أنماط معروفة"""
        return {
            "type": "question" if perception.features.get("question", 0) > 0 else "statement",
            "urgency_level": "high" if perception.features.get("urgency_words", 0) > 0.3 else "normal",
            "language": "arabic" if perception.features.get("arabic_ratio", 0) > 0.3 else "english",
            "complexity": min(1.0, perception.features.get("word_count", 0) / 20),
        }

    def _evaluate(self, perception: Perception, interpretation: Dict, context: Dict) -> Dict:
        """تقييم — مدى أهمية هذا المدخل"""
        urgency = perception.salience
        if interpretation.get("urgency_level") == "high":
            urgency = max(urgency, 0.8)
        if context.get("is_repeated"):
            urgency *= 0.7  # slightly less urgent if repeated

        return {
            "urgency": urgency,
            "needs_response": urgency > 0.2,
            "needs_deep_thinking": interpretation.get("complexity", 0) > 0.7,
            "interpretation": interpretation,
        }

    def _decide(self, evaluation: Dict, context: Dict) -> Tuple[str, float, str]:
        """قرار — ماذا نفعل؟"""
        urgency = evaluation.get("urgency", 0.5)
        needs_response = evaluation.get("needs_response", True)
        needs_deep = evaluation.get("needs_deep_thinking", False)

        if urgency > 0.8:
            return "escalate", 0.9, "Critical urgency — escalate immediately"
        elif needs_deep:
            return "respond", 0.6, "Complex query — deep response needed"
        elif needs_response:
            return "respond", 0.7, "Normal response"
        elif urgency < 0.15:
            return "ignore", 0.3, "Low salience — can be ignored"
        else:
            return "wait", 0.5, "Medium urgency — can wait"

    def _persist_decision(self, decision: ActionDecision):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("INSERT OR REPLACE INTO pal_decisions VALUES (?,?,?,?,?,?,?,?)",
                (decision.decision_id, decision.action_type, json.dumps(decision.action_params),
                 decision.confidence, decision.urgency, decision.reasoning,
                 json.dumps(decision.phase_trace), time.time()))
            conn.commit()
        finally:
            conn.close()

    def get_stats(self) -> Dict:
        total = len(self._decision_history)
        positive = sum(1 for v in self._action_outcomes.values() if v)
        return {
            "total_perceptions": len(self._perception_history),
            "total_decisions": total,
            "positive_outcomes": positive,
            "outcome_rate": positive / max(len(self._action_outcomes), 1),
            "action_distribution": {
                at: sum(1 for d in self._decision_history if d.action_type == at)
                for at in ["respond", "wait", "explore", "escalate", "ignore"]
            },
        }


_pal_engine: Optional[PerceptionActionLoop] = None

def get_pal_engine() -> PerceptionActionLoop:
    global _pal_engine
    if _pal_engine is None:
        _pal_engine = PerceptionActionLoop()
    return _pal_engine
