"""
BABSHARQII v40.0 — Reflective Journal
A SQLite-backed journal that records every wrong decision, root cause analysis,
and lessons learned. This is the organism's long-term procedural memory.
"""

import time
import json
import logging
import aiosqlite
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

logger = logging.getLogger("mamoun.reflective_journal")


@dataclass
class JournalEntry:
    """A reflective journal entry."""
    id: Optional[int] = None
    timestamp: float = 0.0
    entry_type: str = ""  # error, recovery, learning, insight, dream, evolution, anomaly, calibration
    summary: str = ""
    details: str = ""
    emotional_valence: float = 0.0  # -1 to 1
    confidence: float = 0.0
    root_cause: str = ""
    lesson_learned: str = ""
    related_brain_ids: str = ""  # JSON array
    skill_gained: str = ""
    metadata: str = "{}"  # JSON
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat() if self.timestamp else None,
            "entry_type": self.entry_type,
            "summary": self.summary,
            "details": self.details,
            "emotional_valence": self.emotional_valence,
            "confidence": self.confidence,
            "root_cause": self.root_cause,
            "lesson_learned": self.lesson_learned,
            "related_brain_ids": json.loads(self.related_brain_ids) if self.related_brain_ids else [],
            "skill_gained": self.skill_gained,
            "metadata": json.loads(self.metadata) if self.metadata else {},
        }


class ReflectiveJournal:
    """
    SQLite-backed reflective journal for the organism.
    
    Records:
    - Every error with root cause analysis
    - Every recovery with what worked
    - Every learning/insight from reflection
    - Dream interpretations
    - Evolution events
    - Anomaly detections
    - Calibration points
    """
    
    PATTERN_ANALYSIS_THRESHOLD = 10  # analyze every 10 new errors
    
    def __init__(self, db_path: str = ""):
        if not db_path:
            db_path = str(Path(__file__).parent.parent.parent / "data" / "mamoun.db")
        self._db_path = db_path
        self._initialized = False
        self._error_count_since_analysis = 0
        self._age_mem = None  # Lazy-initialized AgeMem instance
    
    async def initialize(self):
        """Create the database table if it doesn't exist."""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS reflective_journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    entry_type TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    details TEXT DEFAULT '',
                    emotional_valence REAL DEFAULT 0.0,
                    confidence REAL DEFAULT 0.0,
                    root_cause TEXT DEFAULT '',
                    lesson_learned TEXT DEFAULT '',
                    related_brain_ids TEXT DEFAULT '[]',
                    skill_gained TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}'
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_journal_type ON reflective_journal(entry_type)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_journal_timestamp ON reflective_journal(timestamp)
            """)
            await db.commit()
        
        self._initialized = True
    
    async def add_entry(self, entry: JournalEntry) -> int:
        """Add a new journal entry and return its ID."""
        await self.initialize()
        
        if not entry.timestamp:
            entry.timestamp = time.time()
        
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("""
                INSERT INTO reflective_journal 
                (timestamp, entry_type, summary, details, emotional_valence, 
                 confidence, root_cause, lesson_learned, related_brain_ids, 
                 skill_gained, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.timestamp,
                entry.entry_type,
                entry.summary,
                entry.details,
                entry.emotional_valence,
                entry.confidence,
                entry.root_cause,
                entry.lesson_learned,
                entry.related_brain_ids,
                entry.skill_gained,
                entry.metadata,
            ))
            await db.commit()
            entry_id = cursor.lastrowid
        
        # Register entry in AgeMem for aging/reinforcement tracking
        try:
            age_mem = await self._get_age_mem()
            await age_mem.register_entry(entry_id, base_relevance=1.0)
        except Exception as e:
            logger.debug(f"فشل تسجيل المدخل {entry_id} في نظام التقادم: {e}")
        
        # Track error count for abstraction analysis
        if entry.entry_type == "error":
            self._error_count_since_analysis += 1
            if self._error_count_since_analysis >= self.PATTERN_ANALYSIS_THRESHOLD:
                await self.analyze_for_abstraction()
                self._error_count_since_analysis = 0
        
        return entry_id
    
    async def get_entries(
        self, 
        entry_type: str = "", 
        limit: int = 50, 
        offset: int = 0
    ) -> list[JournalEntry]:
        """Get journal entries, optionally filtered by type.
        
        Accessed entries are automatically reinforced in AgeMem to
        reflect their continued relevance.
        """
        await self.initialize()
        
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            
            if entry_type:
                cursor = await db.execute(
                    "SELECT * FROM reflective_journal WHERE entry_type = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (entry_type, limit, offset)
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM reflective_journal ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
            
            rows = await cursor.fetchall()
            entries = []
            for row in rows:
                entry = JournalEntry(
                    id=row["id"],
                    timestamp=row["timestamp"],
                    entry_type=row["entry_type"],
                    summary=row["summary"],
                    details=row["details"],
                    emotional_valence=row["emotional_valence"],
                    confidence=row["confidence"],
                    root_cause=row["root_cause"],
                    lesson_learned=row["lesson_learned"],
                    related_brain_ids=row["related_brain_ids"],
                    skill_gained=row["skill_gained"],
                    metadata=row["metadata"],
                )
                entries.append(entry)
                
                # Reinforce entry in AgeMem on access
                if entry.id is not None:
                    await self._reinforce_entry(entry.id)
            
            return entries
    
    async def search(self, query: str, limit: int = 20) -> list[JournalEntry]:
        """Search journal entries by text content.
        
        Search results are automatically reinforced in AgeMem to
        reflect their continued relevance.
        """
        await self.initialize()
        
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM reflective_journal 
                   WHERE summary LIKE ? OR details LIKE ? OR root_cause LIKE ? OR lesson_learned LIKE ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", limit)
            )
            rows = await cursor.fetchall()
            entries = []
            for row in rows:
                entry = JournalEntry(
                    id=row["id"],
                    timestamp=row["timestamp"],
                    entry_type=row["entry_type"],
                    summary=row["summary"],
                    details=row["details"],
                    emotional_valence=row["emotional_valence"],
                    confidence=row["confidence"],
                    root_cause=row["root_cause"],
                    lesson_learned=row["lesson_learned"],
                    related_brain_ids=row["related_brain_ids"],
                    skill_gained=row["skill_gained"],
                    metadata=row["metadata"],
                )
                entries.append(entry)
                
                # Reinforce entry in AgeMem on search access
                if entry.id is not None:
                    await self._reinforce_entry(entry.id)
            
            return entries
    
    async def get_lessons_learned(self, limit: int = 20) -> list[dict]:
        """Get all lessons learned — for the organism to learn from past mistakes."""
        await self.initialize()
        
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT id, timestamp, entry_type, summary, root_cause, lesson_learned
                   FROM reflective_journal 
                   WHERE lesson_learned != '' AND entry_type IN ('error', 'recovery', 'anomaly')
                   ORDER BY timestamp DESC LIMIT ?""",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_error_patterns(self, limit: int = 50) -> list[dict]:
        """Identify recurring error patterns for proactive prevention."""
        await self.initialize()
        
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT summary, COUNT(*) as count, AVG(emotional_valence) as avg_valence
                   FROM reflective_journal 
                   WHERE entry_type = 'error'
                   GROUP BY summary
                   HAVING count > 1
                   ORDER BY count DESC LIMIT ?""",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def count_entries(self, entry_type: str = "") -> int:
        """Count total journal entries."""
        await self.initialize()
        
        async with aiosqlite.connect(self._db_path) as db:
            if entry_type:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM reflective_journal WHERE entry_type = ?",
                    (entry_type,)
                )
            else:
                cursor = await db.execute("SELECT COUNT(*) FROM reflective_journal")
            row = await cursor.fetchone()
            return row[0]
    
    async def _get_age_mem(self):
        """Lazy-initialize the AgeMem instance."""
        if self._age_mem is None:
            from .age_mem import AgeMem
            self._age_mem = AgeMem(db_path=self._db_path)
        return self._age_mem
    
    async def _reinforce_entry(self, entry_id: int):
        """تعزيز مدخل في نظام تقادم الذاكرة عند الوصول إليه."""
        try:
            age_mem = await self._get_age_mem()
            await age_mem.reinforce_entry(entry_id)
        except Exception as e:
            logger.debug(f"فشل تعزيز المدخل {entry_id}: {e}")
    
    async def age_memories(self) -> int:
        """تقادم جميع المدخلات في نظام الذاكرة.
        
        يُطبّق صيغة التقادم على جميع المدخلات النشطة ويُحدّث
        قيم الصلة. يجب استدعاء هذه الدالة بشكل دوري.
        
        Returns:
            عدد المدخلات التي تم تقادمها
        """
        age_mem = await self._get_age_mem()
        aged_count = await age_mem.age_entries()
        logger.info(f"تم تقادم {aged_count} مدخل ذاكرة")
        return aged_count
    
    async def analyze_for_abstraction(self) -> list[dict]:
        """
        Analyze error patterns and propose abstract rules for recurring issues.
        
        Uses AbstractionEngine to find patterns with 3+ occurrences and
        submits them through the approval gate.
        
        Returns list of proposed rules as dicts, or empty list if no patterns found.
        """
        from .abstraction_engine import AbstractionEngine
        
        engine = AbstractionEngine(journal_db_path=self._db_path)
        rules = await engine.analyze_patterns()
        
        proposed = []
        for rule in rules:
            if rule.created_from_count >= 3:
                result = await engine.propose_rule(rule)
                proposed.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "description": rule.description,
                    "condition": rule.condition,
                    "action": rule.action,
                    "confidence": rule.confidence,
                    "created_from_count": rule.created_from_count,
                    "approval_result": result,
                })
        
        return proposed
