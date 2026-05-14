"""
BABSHARQII v40.0 — Procedural Memory
Extracts behavioral skills from repeated task patterns.
Implements AutoSkill/Memento-Skills approach for skill extraction and storage.
"""

import time
import json
import logging
import aiosqlite
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """A behavioral skill extracted from repeated patterns."""
    id: str = ""
    name: str = ""
    name_ar: str = ""
    description: str = ""
    category: str = ""  # response_style, task_pattern, error_handling, communication
    trigger_condition: str = ""  # When to activate this skill
    action_template: str = ""  # How to execute this skill
    context_patterns: list = field(default_factory=list)  # Input patterns that match
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    last_used: float = 0.0
    created_at: float = 0.0
    auto_extracted: bool = False  # Was this skill auto-extracted?
    source_interactions: int = 0  # How many interactions led to this skill
    related_brain_ids: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "name_ar": self.name_ar,
            "description": self.description,
            "category": self.category,
            "trigger_condition": self.trigger_condition,
            "success_rate": self.success_rate,
            "last_used": self.last_used,
            "auto_extracted": self.auto_extracted,
        }


@dataclass
class InteractionRecord:
    """Record of an interaction that might lead to skill extraction."""
    id: Optional[int] = None
    timestamp: float = 0.0
    input_type: str = ""  # question, greeting, analysis, creative, debugging
    input_pattern: str = ""  # Regex or keyword pattern
    response_strategy: str = ""  # What strategy was used
    brain_used: str = ""
    success: bool = False
    user_feedback: float = 0.0  # -1 to 1
    latency_ms: float = 0.0
    context: str = "{}"  # JSON


class ProceduralMemory:
    """
    Procedural Memory for skill extraction and application.
    
    Implements:
    1. AutoSkill: Automatic extraction of skills from repeated patterns
    2. Memento-Skills: Context-aware skill retrieval
    3. Skill database: SQLite-backed persistent storage
    
    Example: If the organism notices it gives short responses in the morning
    and users prefer that, it extracts a "concise_morning_response" skill.
    """
    
    def __init__(self, db_path: str = ""):
        if not db_path:
            db_path = str(Path(__file__).parent.parent.parent / "data" / "mamoun.db")
        self._db_path = db_path
        self._initialized = False
        self._skill_counter = 0
    
    async def initialize(self):
        """Create database tables."""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self._db_path) as db:
            # Skills table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS procedural_skills (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    name_ar TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    category TEXT DEFAULT '',
                    trigger_condition TEXT DEFAULT '',
                    action_template TEXT DEFAULT '',
                    context_patterns TEXT DEFAULT '[]',
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0,
                    last_used REAL DEFAULT 0.0,
                    created_at REAL DEFAULT 0.0,
                    auto_extracted INTEGER DEFAULT 0,
                    source_interactions INTEGER DEFAULT 0,
                    related_brain_ids TEXT DEFAULT '[]'
                )
            """)
            
            # Interaction records table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS interaction_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    input_type TEXT DEFAULT '',
                    input_pattern TEXT DEFAULT '',
                    response_strategy TEXT DEFAULT '',
                    brain_used TEXT DEFAULT '',
                    success INTEGER DEFAULT 0,
                    user_feedback REAL DEFAULT 0.0,
                    latency_ms REAL DEFAULT 0.0,
                    context TEXT DEFAULT '{}'
                )
            """)
            
            await db.execute("CREATE INDEX IF NOT EXISTS idx_skills_category ON procedural_skills(category)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_interactions_type ON interaction_records(input_type)")
            await db.commit()
        
        self._initialized = True
    
    async def record_interaction(self, record: InteractionRecord):
        """Record an interaction for potential skill extraction."""
        await self.initialize()
        
        if not record.timestamp:
            record.timestamp = time.time()
        
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                INSERT INTO interaction_records 
                (timestamp, input_type, input_pattern, response_strategy, 
                 brain_used, success, user_feedback, latency_ms, context)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.timestamp,
                record.input_type,
                record.input_pattern,
                record.response_strategy,
                record.brain_used,
                1 if record.success else 0,
                record.user_feedback,
                record.latency_ms,
                record.context,
            ))
            await db.commit()
    
    async def extract_skills(self, min_occurrences: int = 5, min_success_rate: float = 0.7) -> list[Skill]:
        """
        AutoSkill: Extract skills from repeated interaction patterns.
        
        A skill is extracted when:
        1. Same input pattern appears >= min_occurrences times
        2. Same response strategy was used with >= min_success_rate
        3. The pattern hasn't already been extracted as a skill
        """
        await self.initialize()
        
        new_skills = []
        
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Find patterns: same input_type + response_strategy with high success rate
            cursor = await db.execute("""
                SELECT input_type, response_strategy, brain_used,
                       COUNT(*) as count,
                       AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate,
                       AVG(user_feedback) as avg_feedback,
                       AVG(latency_ms) as avg_latency
                FROM interaction_records
                WHERE timestamp > ?
                GROUP BY input_type, response_strategy
                HAVING count >= ? AND success_rate >= ?
                ORDER BY count DESC
            """, (time.time() - 86400 * 7, min_occurrences, min_success_rate))  # Last 7 days
            
            rows = await cursor.fetchall()
            
            for row in rows:
                input_type = row["input_type"]
                strategy = row["response_strategy"]
                brain = row["brain_used"]
                count = row["count"]
                success_rate = row["success_rate"]
                
                # Check if this skill already exists
                existing = await self._find_similar_skill(db, input_type, strategy)
                if existing:
                    # Update existing skill's statistics
                    await self._update_skill_stats(db, existing, success_rate, count)
                    continue
                
                # Extract new skill
                self._skill_counter += 1
                skill_id = f"skill_auto_{int(time.time())}_{self._skill_counter}"
                
                skill = Skill(
                    id=skill_id,
                    name=f"auto_{input_type}_{strategy}",
                    name_ar=self._translate_skill_name(input_type, strategy),
                    description=f"مهارة مستخرجة تلقائياً: نمط {input_type} مع استراتيجية {strategy}",
                    category=self._categorize_skill(input_type),
                    trigger_condition=f"input_type == '{input_type}'",
                    action_template=strategy,
                    success_count=count,
                    failure_count=0,
                    success_rate=success_rate,
                    last_used=time.time(),
                    created_at=time.time(),
                    auto_extracted=True,
                    source_interactions=count,
                    related_brain_ids=[brain] if brain else [],
                )
                
                # Save to database
                await self._save_skill(db, skill)
                new_skills.append(skill)
        
        return new_skills
    
    async def get_applicable_skills(self, input_type: str, context: dict = None) -> list[Skill]:
        """Get skills applicable to the current input type and context."""
        await self.initialize()
        
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM procedural_skills 
                WHERE trigger_condition LIKE ? OR category = ?
                ORDER BY success_rate DESC, success_count DESC
                LIMIT 5
            """, (f"%{input_type}%", input_type))
            
            rows = await cursor.fetchall()
            skills = []
            for row in rows:
                skills.append(Skill(
                    id=row["id"],
                    name=row["name"],
                    name_ar=row["name_ar"],
                    description=row["description"],
                    category=row["category"],
                    trigger_condition=row["trigger_condition"],
                    action_template=row["action_template"],
                    success_count=row["success_count"],
                    failure_count=row["failure_count"],
                    success_rate=row["success_rate"],
                    related_brain_ids=json.loads(row["related_brain_ids"]) if row["related_brain_ids"] else [],
                ))
            return skills
    
    async def update_skill_usage(self, skill_id: str, success: bool):
        """Update a skill's success/failure count after use."""
        await self.initialize()
        
        async with aiosqlite.connect(self._db_path) as db:
            if success:
                await db.execute("""
                    UPDATE procedural_skills 
                    SET success_count = success_count + 1, 
                        success_rate = CAST(success_count AS REAL) / (success_count + failure_count),
                        last_used = ?
                    WHERE id = ?
                """, (time.time(), skill_id))
            else:
                await db.execute("""
                    UPDATE procedural_skills 
                    SET failure_count = failure_count + 1,
                        success_rate = CAST(success_count AS REAL) / (success_count + failure_count),
                        last_used = ?
                    WHERE id = ?
                """, (time.time(), skill_id))
            await db.commit()
    
    async def get_all_skills(self, limit: int = 50) -> list[dict]:
        """Get all procedural skills."""
        await self.initialize()
        
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM procedural_skills 
                ORDER BY success_rate DESC, success_count DESC
                LIMIT ?
            """, (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # =========================================================================
    # Helpers
    # =========================================================================
    
    async def _find_similar_skill(self, db, input_type: str, strategy: str) -> Optional[str]:
        """Check if a similar skill already exists."""
        cursor = await db.execute("""
            SELECT id FROM procedural_skills 
            WHERE trigger_condition LIKE ? AND action_template = ?
            LIMIT 1
        """, (f"%{input_type}%", strategy))
        row = await cursor.fetchone()
        return row[0] if row else None
    
    async def _update_skill_stats(self, db, skill_id: str, success_rate: float, count: int):
        """Update an existing skill's statistics."""
        await db.execute("""
            UPDATE procedural_skills 
            SET success_rate = ?, source_interactions = ?, last_used = ?
            WHERE id = ?
        """, (success_rate, count, time.time(), skill_id))
        await db.commit()
    
    async def _save_skill(self, db, skill: Skill):
        """Save a new skill to the database."""
        await db.execute("""
            INSERT INTO procedural_skills 
            (id, name, name_ar, description, category, trigger_condition,
             action_template, context_patterns, success_count, failure_count,
             success_rate, last_used, created_at, auto_extracted,
             source_interactions, related_brain_ids)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            skill.id, skill.name, skill.name_ar, skill.description,
            skill.category, skill.trigger_condition, skill.action_template,
            json.dumps(skill.context_patterns), skill.success_count,
            skill.failure_count, skill.success_rate, skill.last_used,
            skill.created_at, 1 if skill.auto_extracted else 0,
            skill.source_interactions,
            json.dumps(skill.related_brain_ids),
        ))
        await db.commit()
    
    def _categorize_skill(self, input_type: str) -> str:
        """Categorize a skill based on its input type."""
        categories = {
            "greeting": "communication",
            "question": "response_style",
            "analysis": "task_pattern",
            "creative": "task_pattern",
            "debugging": "error_handling",
            "meta": "communication",
        }
        return categories.get(input_type, "general")
    
    def _translate_skill_name(self, input_type: str, strategy: str) -> str:
        """Generate an Arabic name for an auto-extracted skill."""
        type_names = {
            "greeting": "الترحيب",
            "question": "الإجابة على الأسئلة",
            "analysis": "التحليل",
            "creative": "الإبداع",
            "debugging": "تصحيح الأخطاء",
            "meta": "التأمل الذاتي",
        }
        return f"مهارة {type_names.get(input_type, input_type)} — {strategy}"

    # ═══════════════════════════════════════════════════════════════════════════
    # v10 Additions: Pruning and Age Statistics
    # ═══════════════════════════════════════════════════════════════════════════

    async def prune_old_skills(self, days_threshold: int = 30) -> list[str]:
        """
        حذف المهارات القديمة غير المستخدمة (v10).

        Prunes skills that:
        - Have not been used for > days_threshold days
        - Have importance_weight < 0.5 (low importance)
        - NEVER prunes skills with success_rate > 0.9 or importance > 0.7

        Returns:
            List of pruned skill IDs.
        """
        await self.initialize()

        threshold_seconds = days_threshold * 86400
        now = time.time()
        pruned_ids: list[str] = []

        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute("""
                SELECT id, name, success_rate, last_used, success_count
                FROM procedural_skills
                WHERE (last_used - created_at) > 0
                ORDER BY last_used ASC
            """)
            rows = await cursor.fetchall()

            for row in rows:
                skill_id = row["id"]
                success_rate = row["success_rate"]
                last_used = row["last_used"]
                success_count = row["success_count"]
                time_since_use = now - last_used

                # NEVER prune high-importance skills
                if success_rate > 0.9 or success_count > 100:
                    continue

                # Prune if old and low importance
                if time_since_use > threshold_seconds and success_rate < 0.5:
                    await db.execute("DELETE FROM procedural_skills WHERE id = ?", (skill_id,))
                    pruned_ids.append(skill_id)

            await db.commit()

        if pruned_ids:
            logger.info(f"Pruned {len(pruned_ids)} old skills (>{days_threshold} days unused)")

        return pruned_ids

    async def get_skill_age_stats(self) -> dict:
        """
        إحصائيات عمر المهارات (v10).
        
        Returns dict with:
        - avg_age_days: average age of all skills
        - max_age_days: oldest skill age
        - skills_near_threshold: count of skills approaching pruning threshold
        - total_skills: total number of skills
        """
        await self.initialize()

        now = time.time()
        ages = []

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("SELECT created_at, last_used FROM procedural_skills")
            rows = await cursor.fetchall()

            for row in rows:
                age = now - row[0]
                ages.append(age / 86400)  # Convert to days

        if not ages:
            return {
                "avg_age_days": 0.0,
                "max_age_days": 0.0,
                "skills_near_threshold": 0,
                "total_skills": 0,
            }

        near_threshold = sum(1 for a in ages if a > 20)  # >20 days = approaching 30-day threshold

        return {
            "avg_age_days": round(sum(ages) / len(ages), 2),
            "max_age_days": round(max(ages), 2),
            "skills_near_threshold": near_threshold,
            "total_skills": len(ages),
        }
