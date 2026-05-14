"""
BABSHARQII v29.0-symphony — Hierarchical Goal Manager (مدير الأهداف الهرمي)
تفكيك الأهداف الكبيرة إلى أهداف فرعية قابلة للتنفيذ والتتبع

Architecture:
  ┌────────────────────────────────────────────┐
  │           HIERARCHICAL GOAL MANAGER         │
  │                                             │
  │  Goal ← decompose → [SubGoal1, SubGoal2, …] │
  │   ↓                                          │
  │  Track progress → Update → Complete          │
  └────────────────────────────────────────────┘
"""

import time
import logging
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any

logger = logging.getLogger("mamoun.hierarchical_goal_manager")


@dataclass
class SubGoal:
    """هدف فرعي — A sub-goal within a larger goal"""
    id: str = ""
    description: str = ""
    status: str = "pending"  # pending, in_progress, completed, failed
    progress: float = 0.0  # 0.0 - 1.0
    priority: str = "medium"  # low, medium, high, critical
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status,
            "progress": self.progress,
            "priority": self.priority,
            "dependencies": self.dependencies,
        }


@dataclass
class Goal:
    """هدف — A hierarchical goal"""
    id: str = ""
    description: str = ""
    subgoals: List[SubGoal] = field(default_factory=list)
    status: str = "pending"
    progress: float = 0.0
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    priority: str = "medium"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status,
            "progress": self.progress,
            "subgoals": [sg.to_dict() for sg in self.subgoals],
            "priority": self.priority,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  Goal Decomposition Templates
# ═══════════════════════════════════════════════════════════════════════════════

_DECOMPOSITION_TEMPLATES = {
    "website": [
        ("Design the UI/UX layout and wireframes", "high"),
        ("Set up the project structure and framework", "high"),
        ("Implement the frontend components", "medium"),
        ("Build the backend API and database", "medium"),
        ("Test and deploy the application", "medium"),
    ],
    "app": [
        ("Define the app requirements and features", "high"),
        ("Design the user interface", "high"),
        ("Develop the frontend", "medium"),
        ("Build the backend services", "medium"),
        ("Test and publish the app", "medium"),
    ],
    "analysis": [
        ("Gather and clean the data", "high"),
        ("Perform exploratory data analysis", "high"),
        ("Apply statistical or ML methods", "medium"),
        ("Generate visualizations and reports", "medium"),
    ],
    "research": [
        ("Define research questions", "high"),
        ("Search and collect sources", "high"),
        ("Analyze and synthesize findings", "medium"),
        ("Write the research report", "medium"),
    ],
}

_DEFAULT_DECOMPOSITION = [
    ("Analyze the requirements", "high"),
    ("Plan the approach", "high"),
    ("Execute the main task", "medium"),
    ("Review and refine", "low"),
]


class HierarchicalGoalManager:
    """
    مدير الأهداف الهرمي — تفكيك الأهداف وتتبعها

    Decomposes high-level goals into executable sub-goals,
    tracks progress, and supports persistence.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or Path("/tmp/mamoun/goals.db")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._goals: Dict[str, Goal] = {}
        self._counter = 0
        self._initialized = False

    def initialize(self) -> bool:
        """تهيئة مدير الأهداف"""
        try:
            self._ensure_schema()
            self._load_goals()
            self._initialized = True
            return True
        except Exception as e:
            logger.error("HierarchicalGoalManager init failed: %s", e)
            return False

    def _ensure_schema(self):
        """Create DB tables"""
        conn = sqlite3.connect(str(self._db_path))
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS hg_goals (
                id TEXT PRIMARY KEY, description TEXT NOT NULL,
                status TEXT DEFAULT 'pending', progress REAL DEFAULT 0,
                priority TEXT DEFAULT 'medium', created_at REAL, completed_at REAL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS hg_subgoals (
                id TEXT PRIMARY KEY, goal_id TEXT NOT NULL,
                description TEXT NOT NULL, status TEXT DEFAULT 'pending',
                progress REAL DEFAULT 0, priority TEXT DEFAULT 'medium',
                dependencies TEXT DEFAULT '[]',
                FOREIGN KEY (goal_id) REFERENCES hg_goals(id))""")
            conn.commit()
        finally:
            conn.close()

    def _load_goals(self):
        """Load goals from DB"""
        try:
            conn = sqlite3.connect(str(self._db_path))
            try:
                cur = conn.execute("SELECT id, description, status, progress, priority, created_at, completed_at FROM hg_goals")
                for row in cur.fetchall():
                    goal_id = row[0]
                    goal = Goal(id=goal_id, description=row[1], status=row[2],
                               progress=row[3], priority=row[4], created_at=row[5], completed_at=row[6])
                    # Load subgoals
                    cur2 = conn.execute("SELECT id, description, status, progress, priority, dependencies FROM hg_subgoals WHERE goal_id = ?", (goal_id,))
                    for sg_row in cur2.fetchall():
                        import json
                        goal.subgoals.append(SubGoal(
                            id=sg_row[0], description=sg_row[1], status=sg_row[2],
                            progress=sg_row[3], priority=sg_row[4],
                            dependencies=json.loads(sg_row[5] or "[]"),
                        ))
                    self._goals[goal_id] = goal
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Failed to load goals: %s", e)

    def decompose_goal(self, description: str) -> Goal:
        """
        تفكيك هدف — Decompose a high-level goal into sub-goals.

        Args:
            description: The high-level goal description.

        Returns:
            A Goal with populated subgoals.
        """
        if not self._initialized:
            self.initialize()

        self._counter += 1
        goal_id = f"goal_{self._counter}_{int(time.time())}"

        # Find matching template
        desc_lower = description.lower()
        template = None
        for key, tmpl in _DECOMPOSITION_TEMPLATES.items():
            if key in desc_lower:
                template = tmpl
                break
        if template is None:
            template = _DEFAULT_DECOMPOSITION

        # Create subgoals
        subgoals = []
        for i, (sg_desc, sg_priority) in enumerate(template):
            sg_id = f"{goal_id}_sg_{i+1}"
            subgoals.append(SubGoal(id=sg_id, description=sg_desc, priority=sg_priority))

        goal = Goal(
            id=goal_id,
            description=description,
            subgoals=subgoals,
            status="pending",
            progress=0.0,
        )

        self._goals[goal_id] = goal
        self._persist_goal(goal)
        logger.info("Goal decomposed: %s → %d subgoals", description[:50], len(subgoals))
        return goal

    def update_progress(self, goal_id: str, subgoal_id: str, progress: float, status: str = None) -> Optional[Goal]:
        """
        تحديث تقدم هدف فرعي — Update sub-goal progress.

        Args:
            goal_id: The parent goal ID.
            subgoal_id: The sub-goal ID.
            progress: Progress value (0.0-1.0).
            status: Optional new status.

        Returns:
            Updated Goal, or None if not found.
        """
        goal = self._goals.get(goal_id)
        if not goal:
            return None

        for sg in goal.subgoals:
            if sg.id == subgoal_id:
                sg.progress = progress
                if status:
                    sg.status = status
                break

        # Update overall progress
        if goal.subgoals:
            goal.progress = sum(sg.progress for sg in goal.subgoals) / len(goal.subgoals)

        # Check if all subgoals are completed
        if all(sg.status == "completed" for sg in goal.subgoals):
            goal.status = "completed"
            goal.completed_at = time.time()

        self._persist_goal(goal)
        return goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """الحصول على هدف"""
        return self._goals.get(goal_id)

    def list_goals(self, status: str = None) -> List[Goal]:
        """قائمة الأهداف"""
        goals = list(self._goals.values())
        if status:
            goals = [g for g in goals if g.status == status]
        return goals

    def _persist_goal(self, goal: Goal):
        """حفظ هدف"""
        try:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO hg_goals (id, description, status, progress, priority, created_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (goal.id, goal.description, goal.status, goal.progress, goal.priority, goal.created_at, goal.completed_at),
                )
                for sg in goal.subgoals:
                    import json
                    conn.execute(
                        "INSERT OR REPLACE INTO hg_subgoals (id, goal_id, description, status, progress, priority, dependencies) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (sg.id, goal.id, sg.description, sg.status, sg.progress, sg.priority, json.dumps(sg.dependencies)),
                    )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Failed to persist goal: %s", e)
