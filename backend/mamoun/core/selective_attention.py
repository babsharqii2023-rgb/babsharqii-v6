"""
BABSHARQII v24.0 — Selective Attention Engine
محرك الانتباه الانتقائي — مأمون يركّز على ما يهم

Core idea: Not everything deserves equal processing. This engine:
1. Classifies incoming signals by importance (HIGH/MEDIUM/LOW)
2. Routes HIGH signals to immediate processing
3. Queues MEDIUM signals for batch processing
4. Archives or ignores LOW signals
5. Dynamically adjusts thresholds based on user patterns

Usage:
    sae = SelectiveAttentionEngine()
    sae.initialize()
    
    # Incoming signal
    priority = sae.classify("Server is down!", context="production")
    # → priority = "critical" → process immediately
    
    priority = sae.classify("New blog post about Python", context="browsing")
    # → priority = "low" → archive for later
"""
import os, time, uuid, json, logging, math
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from pathlib import Path
from enum import Enum

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.attention")


class AttentionLevel(str, Enum):
    CRITICAL = "critical"   # Must act NOW (system failure, safety threat)
    HIGH = "high"           # Important, process soon
    MEDIUM = "medium"       # Worth noticing, batch process
    LOW = "low"             # Archive for later
    IGNORE = "ignore"       # Noise, discard


@dataclass
class AttentionSignal:
    """إشارة انتباه — حدث أو رسالة تحتاج تقييم"""
    signal_id: str = ""
    content: str = ""
    source: str = ""           # user, system, world, memory
    context: str = ""
    level: str = AttentionLevel.MEDIUM.value
    score: float = 0.5         # 0-1 importance score
    keywords: List[str] = field(default_factory=list)
    processed: bool = False
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.signal_id:
            self.signal_id = f"sig_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


class SelectiveAttentionEngine:
    """
    محرك الانتباه الانتقائي
    
    Classifies signals based on:
    1. Keyword matching (critical patterns like "error", "crash", "urgent")
    2. Source priority (user > system > world)
    3. User attention patterns (what does this user usually care about?)
    4. Temporal context (is this time-sensitive?)
    """

    # Critical keywords that demand immediate attention
    CRITICAL_KEYWORDS = {
        "error", "crash", "fail", "down", "urgent", "emergency",
        "security", "breach", "attack", "lost", "corrupted", "dead",
        "عطل", "طوارئ", "خطر", "فشل", "عاجل",
    }

    HIGH_KEYWORDS = {
        "important", "deadline", "today", "now", "asap", "critical",
        "bug", "issue", "problem", "warning",
        "مهم", "مشكلة", "موعد", "اليوم",
    }

    LOW_KEYWORDS = {
        "fyi", "blog", "article", "news", "update", "tips", "general",
        "مقال", "نصيحة", "عام",
    }

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._signals: Dict[str, AttentionSignal] = {}
        self._user_patterns: Dict[str, Dict] = {}  # user attention patterns
        self._threshold_medium = 0.4
        self._threshold_high = 0.7
        self._threshold_critical = 0.9
        self._llm = None
        self._initialized = False

    def set_llm_client(self, llm_client):
        self._llm = llm_client

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("SelectiveAttentionEngine initialized")
            return True
        except Exception as e:
            logger.error("SelectiveAttentionEngine init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sa_signals (
                    signal_id TEXT PRIMARY KEY,
                    content TEXT DEFAULT '',
                    source TEXT DEFAULT '',
                    context TEXT DEFAULT '',
                    level TEXT DEFAULT 'medium',
                    score REAL DEFAULT 0.5,
                    keywords TEXT DEFAULT '[]',
                    processed INTEGER DEFAULT 0,
                    timestamp REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sa_patterns (
                    pattern_key TEXT PRIMARY KEY,
                    pattern_data TEXT DEFAULT '{}',
                    updated_at REAL DEFAULT 0
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT * FROM sa_signals ORDER BY timestamp DESC LIMIT 500"):
                s = AttentionSignal(
                    signal_id=row[0], content=row[1], source=row[2],
                    context=row[3], level=row[4], score=row[5],
                    keywords=json.loads(row[6]), processed=bool(row[7]),
                    timestamp=row[8]
                )
                self._signals[s.signal_id] = s
            for row in conn.execute("SELECT * FROM sa_patterns"):
                self._user_patterns[row[0]] = json.loads(row[1])
        finally:
            conn.close()

    def _persist_signal(self, s: AttentionSignal):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO sa_signals
                (signal_id, content, source, context, level, score, keywords, processed, timestamp)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (s.signal_id, s.content, s.source, s.context, s.level, s.score,
                  json.dumps(s.keywords), int(s.processed), s.timestamp))
            conn.commit()
        finally:
            conn.close()

    def classify(self, content: str, source: str = "user",
                 context: str = "") -> AttentionSignal:
        """
        تصنيف إشارة — ما مستوى أهميتها؟
        
        Returns an AttentionSignal with level and score.
        """
        words = set(content.lower().split())
        # Also check for substring matches (crashed → crash)
        content_lower = content.lower()
        score = 0.3  # baseline

        # Keyword scoring
        critical_matches = set()
        high_matches = set()
        low_matches = set()
        for kw in self.CRITICAL_KEYWORDS:
            if kw in content_lower:
                critical_matches.add(kw)
        for kw in self.HIGH_KEYWORDS:
            if kw in content_lower:
                high_matches.add(kw)
        for kw in self.LOW_KEYWORDS:
            if kw in content_lower:
                low_matches.add(kw)

        if critical_matches:
            score += 0.5
        if high_matches:
            score += 0.25
        if low_matches:
            score -= 0.1

        # Source priority
        source_boost = {"user": 0.15, "system": 0.1, "world": 0.05, "memory": 0.0}
        score += source_boost.get(source, 0.0)

        # Length heuristic (longer messages often more important)
        if len(content) > 200:
            score += 0.05

        # Clamp
        score = max(0.0, min(1.0, score))

        # Determine level
        if score >= self._threshold_critical:
            level = AttentionLevel.CRITICAL.value
        elif score >= self._threshold_high:
            level = AttentionLevel.HIGH.value
        elif score >= self._threshold_medium:
            level = AttentionLevel.MEDIUM.value
        elif score > 0.2:
            level = AttentionLevel.LOW.value
        else:
            level = AttentionLevel.IGNORE.value

        signal = AttentionSignal(
            content=content, source=source, context=context,
            level=level, score=round(score, 3),
            keywords=list(critical_matches | high_matches | low_matches),
        )
        self._signals[signal.signal_id] = signal
        self._persist_signal(signal)
        return signal

    def get_pending(self, min_level: str = AttentionLevel.MEDIUM.value,
                    limit: int = 20) -> List[Dict]:
        """الحصول على الإشارات غير المعالجة"""
        level_order = {
            AttentionLevel.CRITICAL.value: 5,
            AttentionLevel.HIGH.value: 4,
            AttentionLevel.MEDIUM.value: 3,
            AttentionLevel.LOW.value: 2,
            AttentionLevel.IGNORE.value: 1,
        }
        min_priority = level_order.get(min_level, 3)

        pending = [s for s in self._signals.values()
                   if not s.processed and level_order.get(s.level, 0) >= min_priority]
        pending.sort(key=lambda s: (-level_order.get(s.level, 0), -s.score))
        return [s.to_dict() for s in pending[:limit]]

    def mark_processed(self, signal_id: str) -> bool:
        s = self._signals.get(signal_id)
        if not s:
            return False
        s.processed = True
        self._persist_signal(s)
        return True

    def get_stats(self) -> Dict:
        signals = list(self._signals.values())
        return {
            "total_signals": len(signals),
            "processed": len([s for s in signals if s.processed]),
            "pending": len([s for s in signals if not s.processed]),
            "by_level": {
                l.value: len([s for s in signals if s.level == l.value])
                for l in AttentionLevel
            },
        }


selective_attention = SelectiveAttentionEngine()
