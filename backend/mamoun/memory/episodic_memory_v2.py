"""
BABSHARQII v24.0 — Enhanced Episodic Memory with Consequence Tracking
ذاكرة عرضية مُحسّنة — تتبع العواقب الفعلية لكل فعل

Core difference from old EpisodicMemoryStore:
- Stores SITUATION (world state at time of action)
- Stores ACTION (what mamoun did)
- Stores OUTCOME (what actually happened)
- Stores LESSON (causal rule extracted)
- Supports retrieval by ANALOGY (similar situations)
- Feeds back into CausalGraph

This is the memory system that makes Mamoun learn from experience.
"""
import os, time, uuid, json, logging, math
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from pathlib import Path

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.episodic_memory_v2")


@dataclass
class Episode:
    """حلقة ذاكرة — تجربة كاملة مع العواقب"""
    episode_id: str = ""
    
    # What was the situation?
    situation: str = ""
    situation_entities: List[str] = field(default_factory=list)
    situation_emotions: List[str] = field(default_factory=list)
    
    # What did mamoun do?
    action_taken: str = ""
    action_type: str = ""  # respond, plan, create, analyze, avoid
    
    # What was the outcome?
    outcome: str = ""          # what actually happened
    outcome_positive: bool = True  # was it good or bad?
    outcome_user_reaction: str = ""  # liked, disliked, neutral, angry, happy
    
    # What did we learn?
    lesson: str = ""           # causal rule: "when X, do Y because Z"
    lesson_confidence: float = 0.5
    
    # Context
    timestamp: float = 0.0
    importance: float = 0.5   # 0-1, how important is this memory
    access_count: int = 0
    last_accessed: float = 0.0
    decay_factor: float = 1.0  # decreases over time

    def __post_init__(self):
        if not self.episode_id:
            self.episode_id = f"ep_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.last_accessed:
            self.last_accessed = time.time()

    def to_dict(self) -> dict:
        return asdict(self)

    def similarity(self, other: 'Episode') -> float:
        """Calculate similarity between two episodes"""
        score = 0.0
        # Situation similarity (simple word overlap)
        if self.situation and other.situation:
            words_a = set(self.situation.lower().split())
            words_b = set(other.situation.lower().split())
            if words_a and words_b:
                overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)
                score += overlap * 0.4
        # Emotion overlap
        if self.situation_emotions and other.situation_emotions:
            shared = set(self.situation_emotions) & set(other.situation_emotions)
            score += len(shared) / max(len(set(self.situation_emotions) | set(other.situation_emotions)), 1) * 0.2
        # Action type match
        if self.action_type and other.action_type and self.action_type == other.action_type:
            score += 0.2
        # Entity overlap
        if self.situation_entities and other.situation_entities:
            shared = set(self.situation_entities) & set(other.situation_entities)
            score += len(shared) / max(len(set(self.situation_entities) | set(other.situation_entities)), 1) * 0.2
        return min(1.0, score)


class EpisodicMemoryV2:
    """
    الذاكرة العرضية المُحسّنة
    
    Usage:
        mem = EpisodicMemoryV2()
        mem.initialize()
        
        # Record an experience
        ep = mem.record(
            situation="User asked about Python performance",
            action_taken="Gave detailed optimization tips",
            action_type="respond",
            outcome="User was satisfied and implemented suggestions",
            outcome_positive=True,
            outcome_user_reaction="happy",
        )
        
        # Extract a lesson
        mem.extract_lesson(ep.episode_id)
        
        # Recall similar situations
        similar = mem.recall_by_analogy("User asks about code speed")
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._episodes: Dict[str, Episode] = {}
        self._llm = None
        self._initialized = False

    def set_llm_client(self, llm_client):
        self._llm = llm_client

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("EpisodicMemoryV2 initialized — %d episodes", len(self._episodes))
            return True
        except Exception as e:
            logger.error("EpisodicMemoryV2 init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS emv2_episodes (
                    episode_id TEXT PRIMARY KEY,
                    situation TEXT DEFAULT '',
                    situation_entities TEXT DEFAULT '[]',
                    situation_emotions TEXT DEFAULT '[]',
                    action_taken TEXT DEFAULT '',
                    action_type TEXT DEFAULT '',
                    outcome TEXT DEFAULT '',
                    outcome_positive INTEGER DEFAULT 1,
                    outcome_user_reaction TEXT DEFAULT '',
                    lesson TEXT DEFAULT '',
                    lesson_confidence REAL DEFAULT 0.5,
                    timestamp REAL DEFAULT 0,
                    importance REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    last_accessed REAL DEFAULT 0,
                    decay_factor REAL DEFAULT 1.0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_emv2_action_type ON emv2_episodes(action_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_emv2_outcome_positive ON emv2_episodes(outcome_positive)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_emv2_timestamp ON emv2_episodes(timestamp)")
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT * FROM emv2_episodes ORDER BY timestamp DESC LIMIT 1000"):
                ep = Episode(
                    episode_id=row[0], situation=row[1],
                    situation_entities=json.loads(row[2]),
                    situation_emotions=json.loads(row[3]),
                    action_taken=row[4], action_type=row[5],
                    outcome=row[6], outcome_positive=bool(row[7]),
                    outcome_user_reaction=row[8],
                    lesson=row[9], lesson_confidence=row[10],
                    timestamp=row[11], importance=row[12],
                    access_count=row[13], last_accessed=row[14],
                    decay_factor=row[15]
                )
                self._episodes[ep.episode_id] = ep
        finally:
            conn.close()

    def _persist_episode(self, ep: Episode):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO emv2_episodes
                (episode_id, situation, situation_entities, situation_emotions,
                 action_taken, action_type, outcome, outcome_positive,
                 outcome_user_reaction, lesson, lesson_confidence,
                 timestamp, importance, access_count, last_accessed, decay_factor)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (ep.episode_id, ep.situation,
                  json.dumps(ep.situation_entities), json.dumps(ep.situation_emotions),
                  ep.action_taken, ep.action_type, ep.outcome, int(ep.outcome_positive),
                  ep.outcome_user_reaction, ep.lesson, ep.lesson_confidence,
                  ep.timestamp, ep.importance, ep.access_count,
                  ep.last_accessed, ep.decay_factor))
            conn.commit()
        finally:
            conn.close()

    def record(self, situation: str, action_taken: str, action_type: str = "",
               outcome: str = "", outcome_positive: bool = True,
               outcome_user_reaction: str = "",
               situation_entities: List[str] = None,
               situation_emotions: List[str] = None,
               importance: float = 0.5) -> Episode:
        """تسجيل تجربة جديدة"""
        ep = Episode(
            situation=situation, action_taken=action_taken,
            action_type=action_type, outcome=outcome,
            outcome_positive=outcome_positive,
            outcome_user_reaction=outcome_user_reaction,
            situation_entities=situation_entities or [],
            situation_emotions=situation_emotions or [],
            importance=importance,
        )
        self._episodes[ep.episode_id] = ep
        self._persist_episode(ep)
        return ep

    def extract_lesson(self, episode_id: str, lesson: str = None,
                       confidence: float = 0.5) -> Optional[Episode]:
        """استخلاص درس من تجربة"""
        ep = self._episodes.get(episode_id)
        if not ep:
            return None

        if lesson:
            ep.lesson = lesson
        else:
            # Auto-extract lesson from outcome
            if ep.outcome_positive:
                ep.lesson = f"when situation like '{ep.situation[:50]}', doing '{ep.action_taken[:50]}' leads to positive outcome"
            else:
                ep.lesson = f"when situation like '{ep.situation[:50]}', doing '{ep.action_taken[:50]}' leads to negative outcome — avoid"

        ep.lesson_confidence = confidence
        self._persist_episode(ep)
        return ep

    def recall_by_analogy(self, situation: str, top_k: int = 5) -> List[Dict]:
        """استرجاع ذكريات مشابهة بالتشابه"""
        query_ep = Episode(situation=situation)
        scored = []
        for ep in self._episodes.values():
            sim = query_ep.similarity(ep)
            # Boost by importance and recency
            age_days = (time.time() - ep.timestamp) / 86400
            recency_boost = math.exp(-age_days / 30)  # decay over 30 days
            score = sim * 0.6 + ep.importance * 0.2 + recency_boost * 0.2
            scored.append((score, ep))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, ep in scored[:top_k]:
            d = ep.to_dict()
            d["relevance_score"] = round(score, 3)
            ep.access_count += 1
            ep.last_accessed = time.time()
            self._persist_episode(ep)
            results.append(d)
        return results

    def get_lessons(self, positive_only: bool = None, limit: int = 20) -> List[Dict]:
        """استرجاع الدروس المستفادة"""
        episodes = list(self._episodes.values())
        if positive_only is not None:
            episodes = [e for e in episodes if e.outcome_positive == positive_only]
        episodes = [e for e in episodes if e.lesson]
        episodes.sort(key=lambda e: e.lesson_confidence, reverse=True)
        return [{"lesson": e.lesson, "confidence": e.lesson_confidence,
                 "situation": e.situation[:100], "action": e.action_taken[:100]}
                for e in episodes[:limit]]

    def get_stats(self) -> Dict:
        eps = list(self._episodes.values())
        return {
            "total_episodes": len(eps),
            "positive_outcomes": len([e for e in eps if e.outcome_positive]),
            "negative_outcomes": len([e for e in eps if not e.outcome_positive]),
            "lessons_learned": len([e for e in eps if e.lesson]),
            "avg_importance": round(sum(e.importance for e in eps) / max(len(eps), 1), 3),
        }


episodic_memory_v2 = EpisodicMemoryV2()
