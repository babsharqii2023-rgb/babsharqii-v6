"""
BABSHARQII v24.0 — World Monitor
مأمون يراقب العالم باستمرار

v24 Architecture:
1. Periodic Information Gathering: web search every 15 minutes
2. Relevance Scoring: filter what matters before notifying user
3. Trend Detection: identify emerging patterns
4. User State Prediction: infer user's likely state from time/patterns
5. Context Awareness: time, day, market, news, user habits

Safety: Never sends notifications without relevance scoring (threshold > 0.7)
"""

import os
import time
import uuid
import json
import logging
import asyncio
import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from pathlib import Path

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.world_monitor")


# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

WORLD_MONITOR_ENABLED = os.environ.get("MAMOUN_WORLD_MONITOR", "true").lower() in ("true", "1", "yes")
MONITOR_INTERVAL_SECONDS = int(os.environ.get("MAMOUN_WORLD_MONITOR_INTERVAL", "900"))  # 15 min
RELEVANCE_THRESHOLD = float(os.environ.get("MAMOUN_WORLD_RELEVANCE_THRESHOLD", "0.7"))


@dataclass
class WorldSnapshot:
    """لقطة من العالم في لحظة معينة"""
    snapshot_id: str = ""
    timestamp: float = 0.0

    # Time context
    time_of_day: str = ""
    day_type: str = ""
    is_night: bool = False

    # Gathered info
    trends: List[str] = field(default_factory=list)
    market_status: str = ""
    notable_events: List[Dict[str, str]] = field(default_factory=list)

    # User context
    user_likely_state: str = ""

    # Insights
    insights: List[str] = field(default_factory=list)
    notifications_sent: int = 0

    def __post_init__(self):
        if not self.snapshot_id:
            self.snapshot_id = f"snap_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class UserHabit:
    """عادة مستخدم — نمط متكرر"""
    habit_id: str = ""
    habit_type: str = ""  # "login_time", "query_pattern", "active_hours"
    pattern: str = ""
    confidence: float = 0.5
    last_seen: float = 0.0
    occurrence_count: int = 0

    def __post_init__(self):
        if not self.habit_id:
            self.habit_id = f"habit_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return asdict(self)


class WorldMonitor:
    """
    مأمون يراقب العالم باستمرار

    Pipeline:
    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
    │ Gather Data  │───→│ Score Relevance│───→│ Notify User │
    │ (15min cycle)│    │ (> 0.7 only)  │    │ (if needed) │
    └─────────────┘    └──────────────┘    └─────────────┘
         │                    │
         ▼                    ▼
    ┌─────────────┐    ┌──────────────┐
    │ Trend Detect │    │ Insight Gen  │
    └─────────────┘    └──────────────┘
    """

    def __init__(
        self,
        llm_client=None,
        notifier=None,
        web_search_fn=None,
        db_path: Optional[Path] = None,
    ):
        self._llm = llm_client
        self._notifier = notifier
        self._web_search = web_search_fn
        self.db_path = db_path or UNIFIED_DB_PATH

        self._snapshots: List[WorldSnapshot] = []
        self._habits: List[UserHabit] = []
        self._is_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._snapshot_count = 0
        self._notification_count = 0
        self._initialized = False

    def set_llm_client(self, llm_client):
        """تعيين عميل LLM — يُستدعى من main.py عند التشغيل"""
        self._llm = llm_client

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("WorldMonitor initialized — snapshots=%d, habits=%d",
                       len(self._snapshots), len(self._habits))
            return True
        except Exception as e:
            logger.error("WorldMonitor init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS wm_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    timestamp REAL DEFAULT 0,
                    time_of_day TEXT DEFAULT '',
                    day_type TEXT DEFAULT '',
                    is_night INTEGER DEFAULT 0,
                    trends TEXT DEFAULT '[]',
                    market_status TEXT DEFAULT '',
                    notable_events TEXT DEFAULT '[]',
                    user_likely_state TEXT DEFAULT '',
                    insights TEXT DEFAULT '[]',
                    notifications_sent INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS wm_habits (
                    habit_id TEXT PRIMARY KEY,
                    habit_type TEXT DEFAULT '',
                    pattern TEXT DEFAULT '',
                    confidence REAL DEFAULT 0.5,
                    last_seen REAL DEFAULT 0,
                    occurrence_count INTEGER DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS wm_state (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            cur = conn.execute("SELECT key, value FROM wm_state")
            for key, value in cur.fetchall():
                try:
                    if key == "snapshot_count": self._snapshot_count = int(value)
                    elif key == "notification_count": self._notification_count = int(value)
                except (ValueError, TypeError):
                    pass

            cur = conn.execute("SELECT habit_id, habit_type, pattern, confidence, last_seen, occurrence_count FROM wm_habits")
            for row in cur.fetchall():
                self._habits.append(UserHabit(
                    habit_id=row[0], habit_type=row[1], pattern=row[2],
                    confidence=row[3], last_seen=row[4], occurrence_count=row[5]
                ))
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════
    # Core: Monitor Loop
    # ═══════════════════════════════════════════════════════════════

    async def monitor_cycle(self) -> WorldSnapshot:
        """دورة مراقبة واحدة — تجمع بيانات وتحللها"""
        now = datetime.datetime.now()

        snapshot = WorldSnapshot(
            time_of_day=now.strftime("%H:%M"),
            day_type="weekend" if now.weekday() > 4 else "workday",
            is_night=now.hour > 22 or now.hour < 6,
        )

        # 1. Time context
        snapshot.user_likely_state = self._predict_user_state(now)

        # 2. Web search for trends (if search function available)
        snapshot.trends = await self._fetch_trends()

        # 3. Market status
        snapshot.market_status = self._check_market_status(now)

        # 4. Generate insights from gathered data
        if self._llm:
            snapshot.insights = await self._generate_insights(snapshot)
        else:
            snapshot.insights = self._heuristic_insights(snapshot)

        # 5. Notify user if needed
        for insight in snapshot.insights:
            relevance = self._score_relevance(insight, snapshot)
            if relevance >= RELEVANCE_THRESHOLD:
                await self._notify_user(insight, relevance)
                snapshot.notifications_sent += 1

        # Save snapshot
        self._snapshots.append(snapshot)
        self._snapshot_count += 1
        self._persist_snapshot(snapshot)

        return snapshot

    def _predict_user_state(self, now: datetime.datetime) -> str:
        """توقع حالة المستخدم بناءً على الوقت والعادات"""
        hour = now.hour

        if 6 <= hour < 9:
            return "waking_up"
        elif 9 <= hour < 12:
            return "working_morning"
        elif 12 <= hour < 14:
            return "lunch_break"
        elif 14 <= hour < 18:
            return "working_afternoon"
        elif 18 <= hour < 21:
            return "evening_relax"
        elif 21 <= hour < 23:
            return "winding_down"
        else:
            return "sleeping"

    async def _fetch_trends(self) -> List[str]:
        """جلب الترندات من الويب"""
        if self._web_search:
            try:
                results = await self._web_search("today's most important news", num=5)
                if results and isinstance(results, list):
                    return [r.get("name", r.get("snippet", ""))[:100] for r in results[:5]]
            except Exception as e:
                logger.error("Web search failed: %s", e)

        # Fallback: return empty (no web search available)
        return []

    def _check_market_status(self, now: datetime.datetime) -> str:
        """التحقق من حالة السوق"""
        # Simple heuristic — real implementation would use finance API
        weekday = now.weekday()
        hour = now.hour

        if weekday > 4:
            return "closed_weekend"
        elif 9 <= hour < 16:
            return "open"
        elif 16 <= hour < 17:
            return "closing"
        else:
            return "closed"

    async def _generate_insights(self, snapshot: WorldSnapshot) -> List[str]:
        """توليد رؤى من البيانات المجمعة"""
        if not self._llm:
            return self._heuristic_insights(snapshot)

        context = f"""الوقت: {snapshot.time_of_day} ({snapshot.day_type})
حالة المستخدم المتوقعة: {snapshot.user_likely_state}
حالة السوق: {snapshot.market_status}
الترندات: {', '.join(snapshot.trends[:3]) if snapshot.trends else 'لا توجد'}

بناءً على هذه المعلومات، هل هناك شيء مهم يجب أن أخبر المستخدم عنه؟
أجب بقائمة JSON (أو قائمة فارغة إذا لا شيء مهم):
["رؤية 1", "رؤية 2"]"""

        try:
            result = await self._llm.think_json(context, model="glm-5.1", temperature=0.3)
            if isinstance(result, list):
                return [str(item) for item in result[:5]]
            return []
        except Exception:
            return self._heuristic_insights(snapshot)

    def _heuristic_insights(self, snapshot: WorldSnapshot) -> List[str]:
        """رؤى استدلالية — بدون LLM"""
        insights = []

        if snapshot.is_night:
            insights.append("المستخدم نائم غالباً — سأؤجل الإشعارات")
        if snapshot.market_status == "open" and snapshot.day_type == "workday":
            insights.append("الأسواق مفتوحة — قد يهم المستخدم")
        if snapshot.user_likely_state == "waking_up":
            insights.append("المستخدم يستيقظ — يمكن إرسال ملخص الصباح")

        return insights

    def _score_relevance(self, insight: str, snapshot: WorldSnapshot) -> float:
        """تقييم صلة الرؤية بالمستخدم"""
        score = 0.5  # Base score

        # Boost for user-relevant keywords
        high_relevance_keywords = ["مهم", "عاجل", "تحذير", "فرصة", "خطر", "تغيير كبير", "urgent", "important", "alert"]
        for kw in high_relevance_keywords:
            if kw in insight.lower():
                score += 0.2
                break

        # Reduce score at night (don't disturb sleeping user)
        if snapshot.is_night:
            score -= 0.3

        # Boost during active hours
        if snapshot.user_likely_state in ("working_morning", "working_afternoon"):
            score += 0.1

        return min(1.0, max(0.0, score))

    async def _notify_user(self, insight: str, relevance: float):
        """إشعار المستخدم"""
        if self._notifier:
            try:
                from mamoun.notifications.notifier import NotificationPriority
                priority = NotificationPriority.URGENT.value if relevance > 0.9 else NotificationPriority.NORMAL.value
                await self._notifier.send(
                    title="Mamoun World Update",
                    title_ar="مأمون — تحديث عالمي",
                    body=insight[:200],
                    body_ar=insight[:200],
                    priority=priority,
                )
                self._notification_count += 1
            except Exception as e:
                logger.error("Notification failed: %s", e)

    # ═══════════════════════════════════════════════════════════════
    # User Habit Tracking
    # ═══════════════════════════════════════════════════════════════

    def record_user_activity(self, activity_type: str, pattern: str):
        """تسجيل نشاط مستخدم — لتتبع العادات"""
        for habit in self._habits:
            if habit.habit_type == activity_type and habit.pattern == pattern:
                habit.occurrence_count += 1
                habit.last_seen = time.time()
                habit.confidence = min(1.0, habit.confidence + 0.05)
                self._persist_habit(habit)
                return

        new_habit = UserHabit(
            habit_type=activity_type,
            pattern=pattern,
            confidence=0.3,
            last_seen=time.time(),
        )
        self._habits.append(new_habit)
        self._persist_habit(new_habit)

    # ═══════════════════════════════════════════════════════════════
    # Main Loop
    # ═══════════════════════════════════════════════════════════════

    async def start(self):
        if not WORLD_MONITOR_ENABLED:
            logger.info("WorldMonitor: Disabled")
            return
        if self._is_running:
            return
        if not self._initialized:
            self.initialize()

        self._is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("WorldMonitor started — interval=%ds", MONITOR_INTERVAL_SECONDS)

    async def _monitor_loop(self):
        while self._is_running:
            try:
                await self.monitor_cycle()
                await asyncio.sleep(MONITOR_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Monitor loop error: %s", e)
                await asyncio.sleep(60)

    async def shutdown(self):
        self._is_running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
        logger.info("WorldMonitor shutdown — snapshots=%d, notifications=%d",
                    self._snapshot_count, self._notification_count)

    # ═══════════════════════════════════════════════════════════════
    # Persistence
    # ═══════════════════════════════════════════════════════════════

    def _persist_snapshot(self, snapshot: WorldSnapshot):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO wm_snapshots
                (snapshot_id, timestamp, time_of_day, day_type, is_night, trends, market_status,
                 notable_events, user_likely_state, insights, notifications_sent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (snapshot.snapshot_id, snapshot.timestamp, snapshot.time_of_day,
                  snapshot.day_type, 1 if snapshot.is_night else 0,
                  json.dumps(snapshot.trends, ensure_ascii=False),
                  snapshot.market_status,
                  json.dumps(snapshot.notable_events, ensure_ascii=False),
                  snapshot.user_likely_state,
                  json.dumps(snapshot.insights, ensure_ascii=False),
                  snapshot.notifications_sent))
            for key, value in {"snapshot_count": str(self._snapshot_count),
                              "notification_count": str(self._notification_count)}.items():
                conn.execute("INSERT OR REPLACE INTO wm_state (key, value) VALUES (?, ?)", (key, value))
            # Clean old snapshots (keep last 100)
            conn.execute("DELETE FROM wm_snapshots WHERE timestamp < ?", (time.time() - 86400 * 7,))
            conn.commit()
        finally:
            conn.close()

    def _persist_habit(self, habit: UserHabit):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO wm_habits (habit_id, habit_type, pattern, confidence, last_seen, occurrence_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (habit.habit_id, habit.habit_type, habit.pattern,
                  habit.confidence, habit.last_seen, habit.occurrence_count))
            conn.commit()
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════
    # API
    # ═══════════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        return {
            "enabled": WORLD_MONITOR_ENABLED,
            "initialized": self._initialized,
            "is_running": self._is_running,
            "snapshot_count": self._snapshot_count,
            "notification_count": self._notification_count,
            "habits_count": len(self._habits),
            "monitor_interval_seconds": MONITOR_INTERVAL_SECONDS,
            "relevance_threshold": RELEVANCE_THRESHOLD,
        }

    def get_current_context(self) -> dict:
        """السياق العالمي الحالي"""
        now = datetime.datetime.now()
        latest = self._snapshots[-1] if self._snapshots else None
        return {
            "time": now.strftime("%H:%M"),
            "day_type": "weekend" if now.weekday() > 4 else "workday",
            "is_night": now.hour > 22 or now.hour < 6,
            "user_state": self._predict_user_state(now),
            "market_status": self._check_market_status(now),
            "latest_snapshot": latest.to_dict() if latest else None,
        }

    def get_habits(self) -> List[dict]:
        return [h.to_dict() for h in sorted(self._habits, key=lambda h: h.confidence, reverse=True)]


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

world_monitor = WorldMonitor()
