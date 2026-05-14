"""
BABSHARQII v25.0 — Long-Term Planning Engine
محرك التخطيط طويل المدى — خطط تمتد لأشهر وسنوات

Extends HierarchicalPlanner with:
1. Temporal horizons: days, weeks, months, quarters, years
2. Milestone tracking with deadlines
3. Adaptive replanning based on changing circumstances
4. Progress forecasting (will we hit the deadline?)
5. Strategic goal decomposition over extended periods
6. Resource estimation and allocation over time
7. Risk assessment for long-term goals

This is NOT text generation. It builds actual plan trees with
temporal constraints, progress tracking, and adaptive replanning.
"""

import time
import uuid
import json
import logging
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
from enum import Enum

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.long_term_planner")


# ═══════════════════════════════════════════════════════════════
# Temporal Horizons
# ═══════════════════════════════════════════════════════════════

class TemporalHorizon(str, Enum):
    IMMEDIATE = "immediate"    # < 1 hour
    TODAY = "today"            # < 1 day
    THIS_WEEK = "this_week"    # < 1 week
    THIS_MONTH = "this_month"  # < 1 month
    THIS_QUARTER = "quarter"   # < 3 months
    THIS_YEAR = "this_year"    # < 1 year
    MULTI_YEAR = "multi_year"  # 1+ years


# Hours in each horizon (approximate)
HORIZON_HOURS = {
    TemporalHorizon.IMMEDIATE.value: 1,
    TemporalHorizon.TODAY.value: 8,
    TemporalHorizon.THIS_WEEK.value: 40,
    TemporalHorizon.THIS_MONTH.value: 160,
    TemporalHorizon.THIS_QUARTER.value: 480,
    TemporalHorizon.THIS_YEAR.value: 1920,
    TemporalHorizon.MULTI_YEAR.value: 5000,
}


@dataclass
class Milestone:
    """معلم — نقطة تحقق في الخطة طويلة المدى"""
    milestone_id: str = ""
    goal_id: str = ""           # parent goal
    title: str = ""
    description: str = ""
    deadline: float = 0.0       # unix timestamp
    completed_at: float = 0.0
    status: str = "pending"     # pending, in_progress, completed, missed, replanned
    progress: float = 0.0       # 0-1
    priority: float = 0.5
    risk_level: float = 0.0     # 0-1, how risky is this milestone
    dependencies: List[str] = field(default_factory=list)
    estimated_hours: float = 0.0
    actual_hours: float = 0.0
    horizon: str = TemporalHorizon.THIS_MONTH.value

    def __post_init__(self):
        if not self.milestone_id:
            self.milestone_id = f"ms_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class StrategicGoal:
    """هدف استراتيجي — يمتد لأشهر أو سنوات"""
    goal_id: str = ""
    title: str = ""
    description: str = ""
    vision: str = ""             # وصف الرؤية طويلة المدى
    horizon: str = TemporalHorizon.THIS_YEAR.value
    start_date: float = 0.0
    target_date: float = 0.0
    status: str = "active"      # active, on_hold, completed, abandoned
    progress: float = 0.0
    milestones: List[str] = field(default_factory=list)  # milestone IDs
    risks: List[Dict] = field(default_factory=list)
    resources_estimated: float = 0.0  # total hours
    resources_used: float = 0.0
    created_at: float = 0.0
    last_reviewed: float = 0.0

    def __post_init__(self):
        if not self.goal_id:
            self.goal_id = f"goal_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()
        if not self.last_reviewed:
            self.last_reviewed = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ForecastResult:
    """نتيجة التنبؤ — هل سنصل للموعد النهائي؟"""
    goal_id: str = ""
    on_track: bool = True
    progress_rate: float = 0.0     # progress per day
    days_remaining: float = 0.0
    estimated_completion: float = 0.0  # unix timestamp
    confidence: float = 0.0
    risk_factors: List[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class LongTermPlanner:
    """
    محرك التخطيط طويل المدى — خطط تمتد لأشهر وسنوات

    Usage:
        ltp = LongTermPlanner()
        ltp.initialize()

        # Create a multi-year strategic goal
        goal = ltp.create_goal(
            "Build AGI System",
            vision="Create a system that can reason, learn, and adapt autonomously",
            horizon="multi_year",
            target_date=time.time() + 2*365*24*3600  # 2 years from now
        )

        # Add milestones
        m1 = ltp.add_milestone(goal.goal_id, "Core reasoning engine",
                               horizon="this_quarter", deadline=...)
        m2 = ltp.add_milestone(goal.goal_id, "Transfer learning system",
                               horizon="this_year", deadline=...)

        # Set dependencies
        ltp.add_milestone_dependency(m2.milestone_id, m1.milestone_id)

        # Update progress
        ltp.update_milestone(m1.milestone_id, progress=0.8)

        # Forecast: will we hit the target?
        forecast = ltp.forecast(goal.goal_id)
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._goals: Dict[str, StrategicGoal] = {}
        self._milestones: Dict[str, Milestone] = {}
        self._llm = None
        self._initialized = False

    def set_llm_client(self, llm_client):
        self._llm = llm_client

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("LongTermPlanner initialized — %d goals, %d milestones",
                       len(self._goals), len(self._milestones))
            return True
        except Exception as e:
            logger.error("LongTermPlanner init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ltp_goals (
                    goal_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    vision TEXT DEFAULT '',
                    horizon TEXT DEFAULT 'this_year',
                    start_date REAL DEFAULT 0,
                    target_date REAL DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    progress REAL DEFAULT 0,
                    milestones TEXT DEFAULT '[]',
                    risks TEXT DEFAULT '[]',
                    resources_estimated REAL DEFAULT 0,
                    resources_used REAL DEFAULT 0,
                    created_at REAL DEFAULT 0,
                    last_reviewed REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ltp_milestones (
                    milestone_id TEXT PRIMARY KEY,
                    goal_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    deadline REAL DEFAULT 0,
                    completed_at REAL DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    progress REAL DEFAULT 0,
                    priority REAL DEFAULT 0.5,
                    risk_level REAL DEFAULT 0,
                    dependencies TEXT DEFAULT '[]',
                    estimated_hours REAL DEFAULT 0,
                    actual_hours REAL DEFAULT 0,
                    horizon TEXT DEFAULT 'this_month'
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ltp_ms_goal ON ltp_milestones(goal_id)")
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT * FROM ltp_goals"):
                g = StrategicGoal(
                    goal_id=row[0], title=row[1], description=row[2],
                    vision=row[3], horizon=row[4], start_date=row[5],
                    target_date=row[6], status=row[7], progress=row[8],
                    milestones=json.loads(row[9]), risks=json.loads(row[10]),
                    resources_estimated=row[11], resources_used=row[12],
                    created_at=row[13], last_reviewed=row[14],
                )
                self._goals[g.goal_id] = g

            for row in conn.execute("SELECT * FROM ltp_milestones"):
                m = Milestone(
                    milestone_id=row[0], goal_id=row[1], title=row[2],
                    description=row[3], deadline=row[4], completed_at=row[5],
                    status=row[6], progress=row[7], priority=row[8],
                    risk_level=row[9], dependencies=json.loads(row[10]),
                    estimated_hours=row[11], actual_hours=row[12],
                    horizon=row[13],
                )
                self._milestones[m.milestone_id] = m
        finally:
            conn.close()

    def _persist_goal(self, g: StrategicGoal):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO ltp_goals
                (goal_id, title, description, vision, horizon, start_date,
                 target_date, status, progress, milestones, risks,
                 resources_estimated, resources_used, created_at, last_reviewed)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (g.goal_id, g.title, g.description, g.vision, g.horizon,
                  g.start_date, g.target_date, g.status, g.progress,
                  json.dumps(g.milestones), json.dumps(g.risks),
                  g.resources_estimated, g.resources_used,
                  g.created_at, g.last_reviewed))
            conn.commit()
        finally:
            conn.close()

    def _persist_milestone(self, m: Milestone):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO ltp_milestones
                (milestone_id, goal_id, title, description, deadline,
                 completed_at, status, progress, priority, risk_level,
                 dependencies, estimated_hours, actual_hours, horizon)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (m.milestone_id, m.goal_id, m.title, m.description,
                  m.deadline, m.completed_at, m.status, m.progress,
                  m.priority, m.risk_level, json.dumps(m.dependencies),
                  m.estimated_hours, m.actual_hours, m.horizon))
            conn.commit()
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════
    # Core API
    # ═══════════════════════════════════════════════════════════

    def create_goal(self, title: str, description: str = "",
                    vision: str = "", horizon: str = TemporalHorizon.THIS_YEAR.value,
                    target_date: float = 0, resources_estimated: float = 0) -> StrategicGoal:
        """إنشاء هدف استراتيجي طويل المدى"""
        goal = StrategicGoal(
            title=title, description=description, vision=vision,
            horizon=horizon, start_date=time.time(),
            target_date=target_date, resources_estimated=resources_estimated,
        )
        self._goals[goal.goal_id] = goal
        self._persist_goal(goal)
        return goal

    def add_milestone(self, goal_id: str, title: str,
                      description: str = "", deadline: float = 0,
                      horizon: str = TemporalHorizon.THIS_MONTH.value,
                      priority: float = 0.5, estimated_hours: float = 0) -> Optional[Milestone]:
        """إضافة معلم للهدف"""
        goal = self._goals.get(goal_id)
        if not goal:
            return None

        ms = Milestone(
            goal_id=goal_id, title=title, description=description,
            deadline=deadline, horizon=horizon, priority=priority,
            estimated_hours=estimated_hours,
        )
        self._milestones[ms.milestone_id] = ms
        goal.milestones.append(ms.milestone_id)
        self._persist_milestone(ms)
        self._persist_goal(goal)
        return ms

    def add_milestone_dependency(self, milestone_id: str, depends_on_id: str) -> bool:
        """إضافة تبعية بين معلمين"""
        ms = self._milestones.get(milestone_id)
        dep = self._milestones.get(depends_on_id)
        if not ms or not dep:
            return False
        if depends_on_id not in ms.dependencies:
            ms.dependencies.append(depends_on_id)
            self._persist_milestone(ms)
        return True

    def update_milestone(self, milestone_id: str, progress: float = None,
                         status: str = None, actual_hours: float = None,
                         risk_level: float = None) -> Optional[Milestone]:
        """تحديث معلم"""
        ms = self._milestones.get(milestone_id)
        if not ms:
            return None

        if progress is not None:
            ms.progress = min(1.0, max(0.0, progress))
        if status:
            ms.status = status
            if status == "completed":
                ms.progress = 1.0
                ms.completed_at = time.time()
        if actual_hours is not None:
            ms.actual_hours = actual_hours
        if risk_level is not None:
            ms.risk_level = min(1.0, max(0.0, risk_level))

        self._persist_milestone(ms)

        # Update parent goal progress
        goal = self._goals.get(ms.goal_id)
        if goal:
            self._recalculate_goal_progress(goal)

        return ms

    def _recalculate_goal_progress(self, goal: StrategicGoal):
        """إعادة حساب تقدم الهدف بناءً على معالمه"""
        if not goal.milestones:
            return
        ms_list = [self._milestones.get(mid) for mid in goal.milestones]
        ms_list = [m for m in ms_list if m]
        if ms_list:
            # Weighted by estimated hours
            total_weight = sum(m.estimated_hours or 1.0 for m in ms_list)
            weighted_progress = sum(
                (m.estimated_hours or 1.0) * m.progress for m in ms_list
            )
            goal.progress = weighted_progress / total_weight
            goal.last_reviewed = time.time()

            # Check if all milestones completed
            if all(m.status == "completed" for m in ms_list):
                goal.status = "completed"

            self._persist_goal(goal)

    def forecast(self, goal_id: str) -> ForecastResult:
        """
        تنبؤ — هل سنصل للهدف في الموعد المحدد؟

        Uses progress rate to project completion date:
        - If progress_rate * days_remaining < (1 - progress), we're behind
        - Calculates confidence based on milestone status distribution
        - Identifies risk factors
        """
        goal = self._goals.get(goal_id)
        if not goal:
            return ForecastResult(goal_id=goal_id)

        now = time.time()
        days_elapsed = max((now - goal.start_date) / 86400, 0.1)
        progress_rate = goal.progress / days_elapsed  # progress per day

        days_remaining = max((goal.target_date - now) / 86400, 0)
        projected_progress = goal.progress + progress_rate * days_remaining
        on_track = projected_progress >= 0.95

        # Estimated completion
        if progress_rate > 0:
            days_to_complete = (1.0 - goal.progress) / progress_rate
            estimated_completion = now + days_to_complete * 86400
        else:
            estimated_completion = goal.target_date + 365 * 86400  # far future

        # Confidence based on milestone status
        ms_list = [self._milestones.get(mid) for mid in goal.milestones]
        ms_list = [m for m in ms_list if m]
        if ms_list:
            completed_ratio = sum(1 for m in ms_list if m.status == "completed") / len(ms_list)
            at_risk_ratio = sum(1 for m in ms_list if m.risk_level > 0.7) / len(ms_list)
            confidence = completed_ratio * (1 - at_risk_ratio) * 0.8
        else:
            confidence = 0.1

        # Risk factors
        risk_factors = []
        if progress_rate == 0:
            risk_factors.append("no_progress_made")
        if not on_track:
            risk_factors.append("behind_schedule")
        high_risk_ms = [m for m in ms_list if m.risk_level > 0.7 and m.status != "completed"]
        if high_risk_ms:
            risk_factors.append(f"{len(high_risk_ms)}_high_risk_milestones")
        blocked_ms = [m for m in ms_list if m.status == "pending"
                      and any(self._milestones.get(d, Milestone()).status != "completed"
                             for d in m.dependencies)]
        if blocked_ms:
            risk_factors.append(f"{len(blocked_ms)}_blocked_milestones")

        # Recommendation
        if on_track:
            recommendation = "on_track"
        elif progress_rate > 0 and not on_track:
            recommendation = "accelerate_or_reduce_scope"
        else:
            recommendation = "replan_or_abandon"

        return ForecastResult(
            goal_id=goal_id,
            on_track=on_track,
            progress_rate=round(progress_rate, 4),
            days_remaining=round(days_remaining, 1),
            estimated_completion=estimated_completion,
            confidence=round(confidence, 3),
            risk_factors=risk_factors,
            recommendation=recommendation,
        )

    def replan(self, goal_id: str) -> Dict[str, Any]:
        """
        إعادة تخطيط — تعديل الخطة بناءً على الظروف الحالية

        - تحديد المعالم المتأخرة
        - اقتراح تعديلات الجدول الزمني
        - تخفيض أولويات المعالم غير الحرجة
        """
        goal = self._goals.get(goal_id)
        if not goal:
            return {"error": "Goal not found"}

        forecast = self.forecast(goal_id)
        actions = []

        # Check for missed deadlines
        now = time.time()
        for mid in goal.milestones:
            ms = self._milestones.get(mid)
            if not ms:
                continue
            if ms.deadline > 0 and ms.deadline < now and ms.status != "completed":
                # Milestone is overdue
                ms.status = "replanned"
                # Extend deadline by 50%
                original_duration = ms.deadline - goal.start_date
                ms.deadline = now + original_duration * 0.5
                actions.append(f"Extended deadline for '{ms.title}' by 50%")
                self._persist_milestone(ms)

        # If behind schedule, reduce scope
        if not forecast.on_track:
            low_priority = [
                m for m in [self._milestones.get(mid) for mid in goal.milestones]
                if m and m.priority < 0.3 and m.status == "pending"
            ]
            for ms in low_priority[:2]:
                ms.status = "replanned"
                actions.append(f"Deferred low-priority milestone '{ms.title}'")
                self._persist_milestone(ms)

        self._recalculate_goal_progress(goal)

        return {
            "goal_id": goal_id,
            "forecast": forecast.on_track,
            "actions_taken": actions,
            "new_progress": goal.progress,
        }

    def get_goal_tree(self, goal_id: str = None) -> Dict:
        """الحصول على شجرة الهدف مع معالمه"""
        if goal_id:
            goals = [self._goals.get(goal_id)]
        else:
            goals = list(self._goals.values())

        result = []
        for g in goals:
            if not g:
                continue
            milestones = [
                self._milestones.get(mid).to_dict()
                for mid in g.milestones
                if self._milestones.get(mid)
            ]
            result.append({
                **g.to_dict(),
                "milestones": milestones,
                "forecast": self.forecast(g.goal_id).to_dict() if g.target_date > 0 else None,
            })

        return {"goals": result}

    def get_stats(self) -> Dict:
        goals = list(self._goals.values())
        ms = list(self._milestones.values())
        return {
            "total_goals": len(goals),
            "active_goals": len([g for g in goals if g.status == "active"]),
            "completed_goals": len([g for g in goals if g.status == "completed"]),
            "total_milestones": len(ms),
            "completed_milestones": len([m for m in ms if m.status == "completed"]),
            "overdue_milestones": len([m for m in ms if m.deadline > 0
                                      and m.deadline < time.time()
                                      and m.status != "completed"]),
            "by_horizon": {h.value: len([g for g in goals if g.horizon == h.value])
                          for h in TemporalHorizon},
        }


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

long_term_planner = LongTermPlanner()
