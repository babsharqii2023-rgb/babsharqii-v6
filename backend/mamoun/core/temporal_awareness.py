"""
BABSHARQII v19.0 — Temporal Awareness
الإدراك الزمني — Time-series analysis + Cron-based checks + Activity timeline

Tracks:
- When user is active (time patterns)
- "لم تدخل منذ 3 أيام" (absence detection)
- "عادة تسأل عن التصميم يوم الخميس" (weekly patterns)
- Project progress over time
- Activity timeline for visualization
"""

import time
import json
import logging
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger("mamoun.temporal_awareness")


@dataclass
class ActivityEvent:
    """حدث زمني"""
    id: str = ""
    event_type: str = "login"  # login, interaction, project_update, absence, milestone
    content: str = ""
    timestamp: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"id": self.id, "event_type": self.event_type, "content": self.content,
                "timestamp": self.timestamp, "time_ago": self._time_ago()}

    def _time_ago(self) -> str:
        diff = time.time() - self.timestamp
        if diff < 60: return "الآن"
        elif diff < 3600: return f"منذ {int(diff/60)} دقيقة"
        elif diff < 86400: return f"منذ {int(diff/3600)} ساعة"
        else: return f"منذ {int(diff/86400)} يوم"


@dataclass
class WeeklyPattern:
    """نمط أسبوعي"""
    day: int = 0  # 0=Monday
    hour: int = 0
    topic: str = ""
    frequency: int = 0
    confidence: float = 0.0

    def to_dict(self) -> dict:
        days_ar = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
        return {"day": self.day, "day_ar": days_ar[self.day], "hour": self.hour,
                "topic": self.topic, "frequency": self.frequency, "confidence": round(self.confidence, 4)}


@dataclass
class AbsenceRecord:
    """سجل غياب"""
    start_time: float = 0.0
    end_time: float = 0.0
    duration_days: float = 0.0
    notification_sent: bool = False

    def to_dict(self) -> dict:
        return {"duration_days": round(self.duration_days, 1), "notification_sent": self.notification_sent}


class TemporalAwarenessEngine:
    """
    محرك الإدراك الزمني — يتعقب الأنماط الزمنية ويُنبه ذكياً

    Features:
    - Absence detection: "لم تدخل منذ X أيام"
    - Weekly patterns: "عادة تسأل عن التصميم يوم الخميس"
    - Activity timeline: visual timeline of all events
    - Proactive notifications based on time patterns
    """

    ABSENCE_THRESHOLD_DAYS = 1.0
    ACTIVITY_RETENTION_DAYS = 90
    MAX_EVENTS = 500
    MAX_WEEKLY_PATTERNS = 50

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path("/tmp/temporal_awareness.db")
        self._events: List[ActivityEvent] = []
        self._weekly_patterns: List[WeeklyPattern] = []
        self._absences: List[AbsenceRecord] = []
        self._last_activity: float = 0.0
        self._first_activity: float = 0.0
        self._total_sessions: int = 0
        self._counter = 0
        self._initialized = False

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("TemporalAwarenessEngine initialized — %d events, %d patterns",
                       len(self._events), len(self._weekly_patterns))
            return True
        except Exception as e:
            logger.error("TemporalAwarenessEngine init failed: %s", e)
            return False

    def _ensure_schema(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS ta_events (
                id TEXT PRIMARY KEY, event_type TEXT DEFAULT 'interaction',
                content TEXT NOT NULL, timestamp REAL DEFAULT 0, metadata TEXT DEFAULT '{}')""")
            conn.execute("""CREATE TABLE IF NOT EXISTS ta_weekly (
                day INTEGER, hour INTEGER, topic TEXT, frequency INTEGER DEFAULT 1,
                confidence REAL DEFAULT 0, PRIMARY KEY (day, hour, topic))""")
            conn.execute("""CREATE TABLE IF NOT EXISTS ta_state (
                key TEXT PRIMARY KEY, value TEXT NOT NULL)""")
            conn.commit()
        finally: conn.close()

    def _load_from_db(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            cur = conn.execute("SELECT key, value FROM ta_state")
            for key, value in cur.fetchall():
                try:
                    if key == "last_activity": self._last_activity = float(value)
                    elif key == "first_activity": self._first_activity = float(value)
                    elif key == "total_sessions": self._total_sessions = int(value)
                    elif key == "counter": self._counter = int(value)
                except (ValueError, TypeError): pass

            cur = conn.execute("SELECT id, event_type, content, timestamp, metadata FROM ta_events ORDER BY timestamp DESC LIMIT 200")
            for row in cur.fetchall():
                self._events.append(ActivityEvent(id=row[0], event_type=row[1], content=row[2],
                                                  timestamp=row[3], metadata=json.loads(row[4]) if row[4] else {}))

            cur = conn.execute("SELECT day, hour, topic, frequency, confidence FROM ta_weekly ORDER BY frequency DESC LIMIT 50")
            for row in cur.fetchall():
                self._weekly_patterns.append(WeeklyPattern(day=row[0], hour=row[1], topic=row[2],
                                                           frequency=row[3], confidence=row[4]))
        finally: conn.close()

    # ─── Core: Record Activity ─────────────────────────────────────────────

    def record_activity(self, event_type: str = "interaction", content: str = "",
                        topic: str = "", metadata: dict = None) -> dict:
        """تسجيل نشاط جديد"""
        if not self._initialized:
            self.initialize()

        now = time.time()
        result = {"recorded": True, "notifications": []}

        # Check for absence (before updating)
        absence_check = self._check_absence(now)
        if absence_check:
            result["notifications"].append(absence_check)

        # Record the event
        self._counter += 1
        event = ActivityEvent(
            id=f"evt_{self._counter}",
            event_type=event_type,
            content=content,
            timestamp=now,
            metadata=metadata or {},
        )
        self._events.append(event)

        # Update weekly pattern
        if topic:
            self._update_weekly_pattern(topic, now)

        # Update activity timestamps
        if not self._first_activity:
            self._first_activity = now
        self._last_activity = now
        self._total_sessions += 1

        # Check for time-based notifications
        time_notifications = self._check_time_patterns(now)
        result["notifications"].extend(time_notifications)

        # Prune old events
        cutoff = now - (self.ACTIVITY_RETENTION_DAYS * 86400)
        self._events = [e for e in self._events if e.timestamp > cutoff]
        if len(self._events) > self.MAX_EVENTS:
            self._events = self._events[-self.MAX_EVENTS:]

        # Persist
        self._persist_event(event)
        self._persist_state()

        return result

    def _check_absence(self, now: float) -> Optional[dict]:
        """فحص الغياب — هل المستخدم غاب طويلاً؟"""
        if not self._last_activity:
            return None

        absence_days = (now - self._last_activity) / 86400
        if absence_days >= self.ABSENCE_THRESHOLD_DAYS:
            return {
                "type": "absence",
                "message": f"لم تدخل منذ {absence_days:.1f} أيام",
                "message_en": f"You haven't logged in for {absence_days:.1f} days",
                "days_absent": round(absence_days, 1),
                "severity": "high" if absence_days > 3 else "medium" if absence_days > 1 else "low",
            }
        return None

    def _update_weekly_pattern(self, topic: str, timestamp: float):
        """تحديث الأنماط الأسبوعية"""
        dt = datetime.fromtimestamp(timestamp)
        day = dt.weekday()
        hour = dt.hour

        for pattern in self._weekly_patterns:
            if pattern.day == day and pattern.hour == hour and pattern.topic.lower() == topic.lower():
                pattern.frequency += 1
                pattern.confidence = min(1.0, pattern.frequency * 0.1)
                return

        self._weekly_patterns.append(WeeklyPattern(day=day, hour=hour, topic=topic, frequency=1, confidence=0.1))
        if len(self._weekly_patterns) > self.MAX_WEEKLY_PATTERNS:
            self._weekly_patterns.sort(key=lambda p: p.frequency, reverse=True)
            self._weekly_patterns = self._weekly_patterns[:self.MAX_WEEKLY_PATTERNS]

    def _check_time_patterns(self, now: float) -> List[dict]:
        """فحص الأنماط الزمنية — هل هناك نمط يتكرر الآن؟"""
        notifications = []
        dt = datetime.fromtimestamp(now)
        current_day = dt.weekday()
        current_hour = dt.hour

        for pattern in self._weekly_patterns:
            if pattern.day == current_day and pattern.hour == current_hour and pattern.confidence > 0.3:
                notifications.append({
                    "type": "weekly_pattern",
                    "message": f"عادة تسأل عن '{pattern.topic}' في هذا الوقت من الأسبوع",
                    "topic": pattern.topic,
                    "confidence": round(pattern.confidence, 2),
                })

        return notifications

    # ─── Persistence ───────────────────────────────────────────────────────

    def _persist_event(self, event: ActivityEvent):
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("INSERT OR REPLACE INTO ta_events (id, event_type, content, timestamp, metadata) VALUES (?,?,?,?,?)",
                        (event.id, event.event_type, event.content, event.timestamp, json.dumps(event.metadata)))
            conn.commit()
        finally: conn.close()

    def _persist_state(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            for key, value in {"last_activity": str(self._last_activity), "first_activity": str(self._first_activity),
                              "total_sessions": str(self._total_sessions), "counter": str(self._counter)}.items():
                conn.execute("INSERT OR REPLACE INTO ta_state (key, value) VALUES (?, ?)", (key, value))

            for p in self._weekly_patterns[:30]:
                conn.execute("INSERT OR REPLACE INTO ta_weekly (day, hour, topic, frequency, confidence) VALUES (?,?,?,?,?)",
                           (p.day, p.hour, p.topic, p.frequency, p.confidence))
            conn.commit()
        finally: conn.close()

    # ─── Status & API ──────────────────────────────────────────────────────

    def get_status(self) -> dict:
        absence_days = 0.0
        if self._last_activity:
            absence_days = (time.time() - self._last_activity) / 86400

        return {
            "initialized": self._initialized,
            "total_events": len(self._events),
            "total_sessions": self._total_sessions,
            "weekly_patterns": len(self._weekly_patterns),
            "last_activity": self._last_activity,
            "days_since_last_activity": round(absence_days, 2),
            "first_activity": self._first_activity,
        }

    def get_timeline(self, limit: int = 20) -> List[dict]:
        """الجدول الزمني — للعرض البصري JARVIS"""
        recent = sorted(self._events, key=lambda e: e.timestamp, reverse=True)[:limit]
        return [e.to_dict() for e in recent]

    def get_weekly_patterns(self, limit: int = 10) -> List[dict]:
        """الأنماط الأسبوعية"""
        sorted_patterns = sorted(self._weekly_patterns, key=lambda p: p.confidence, reverse=True)
        return [p.to_dict() for p in sorted_patterns[:limit]]

    def get_absence_status(self) -> dict:
        """حالة الغياب"""
        if not self._last_activity:
            return {"absent": False, "days": 0, "message": ""}

        days = (time.time() - self._last_activity) / 86400
        if days >= 3:
            return {"absent": True, "days": round(days, 1),
                    "message": f"لم تدخل منذ {days:.0f} أيام — مشاريعك تحتاج تحديث",
                    "severity": "high"}
        elif days >= 1:
            return {"absent": True, "days": round(days, 1),
                    "message": f"لم تدخل منذ {days:.0f} يوم",
                    "severity": "medium"}
        return {"absent": False, "days": round(days, 2), "message": "", "severity": "low"}

    def get_proactive_suggestions(self) -> List[dict]:
        """اقتراحات استباقية مبنية على الزمن"""
        suggestions = []

        # Absence-based suggestion
        absence = self.get_absence_status()
        if absence["absent"]:
            suggestions.append({
                "type": "absence_return",
                "message": absence["message"],
                "priority": absence["severity"],
            })

        # Weekly pattern suggestion
        now = time.time()
        dt = datetime.fromtimestamp(now)
        for pattern in self._weekly_patterns:
            if pattern.day == dt.weekday() and pattern.confidence > 0.3:
                suggestions.append({
                    "type": "weekly_pattern",
                    "message": f"عادة تعمل على '{pattern.topic}' في هذا اليوم",
                    "priority": "low",
                })

        return suggestions[:5]


temporal_awareness = TemporalAwarenessEngine()
