"""
BABSHARQII v22.0 — Temporal Awareness API
واجهة برمجة الإدراك الزمني — Timeline, Patterns, Absence, Suggestions

API Endpoints:
  GET  /api/temporal/status    — Full temporal awareness status
  GET  /api/temporal/timeline  — Recent timeline events
  POST /api/temporal/event     — Record a new temporal event
"""

import time
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from mamoun.api.deps import require_auth

router = APIRouter(prefix="/temporal", tags=["temporal"])


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج البيانات — Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class TemporalEventRequest(BaseModel):
    """نموذج تسجيل حدث زمني"""
    event_type: str = "interaction"  # login, interaction, project_update, absence, milestone
    content: str = ""
    topic: str = ""
    metadata: Dict[str, Any] = {}


# ═══════════════════════════════════════════════════════════════════════════════
#  محرك الإدراك الزمني — محاولة استخدام Core module أولاً
# ═══════════════════════════════════════════════════════════════════════════════

_engine = None

def _get_engine():
    """الحصول على محرك الإدراك الزمني — من Core أو إنشاء بديل"""
    global _engine
    if _engine is not None:
        return _engine

    # محاولة استخدام Core module
    try:
        from mamoun.core.temporal_awareness import temporal_awareness
        if not temporal_awareness._initialized:
            temporal_awareness.initialize()
        _engine = temporal_awareness
        return _engine
    except Exception:
        pass

    # بديل — حالة بسيطة في الذاكرة
    _engine = _InMemoryTemporalEngine()
    return _engine


class _InMemoryTemporalEngine:
    """محرك بديل — حالة بسيطة في الذاكرة عند عدم توفر Core"""

    def __init__(self):
        self._events: List[Dict] = []
        self._counter = 0
        self._last_activity = 0.0
        self._total_sessions = 0
        self._initialized = True

    def record_activity(self, event_type: str = "interaction", content: str = "",
                        topic: str = "", metadata: dict = None) -> dict:
        now = time.time()
        self._counter += 1
        event = {
            "id": f"evt_{self._counter}",
            "event_type": event_type,
            "content": content,
            "timestamp": now,
            "metadata": metadata or {},
        }
        self._events.append(event)
        self._last_activity = now
        self._total_sessions += 1
        # الحد الأقصى 500 حدث
        if len(self._events) > 500:
            self._events = self._events[-500:]
        return {"recorded": True, "notifications": []}

    def get_status(self) -> dict:
        absence_days = 0.0
        if self._last_activity:
            absence_days = (time.time() - self._last_activity) / 86400
        return {
            "initialized": self._initialized,
            "total_events": len(self._events),
            "total_sessions": self._total_sessions,
            "weekly_patterns": 0,
            "last_activity": self._last_activity,
            "days_since_last_activity": round(absence_days, 2),
        }

    def get_timeline(self, limit: int = 20) -> List[dict]:
        recent = sorted(self._events, key=lambda e: e["timestamp"], reverse=True)[:limit]
        for e in recent:
            diff = time.time() - e["timestamp"]
            if diff < 60: e["time_ago"] = "الآن"
            elif diff < 3600: e["time_ago"] = f"منذ {int(diff/60)} دقيقة"
            elif diff < 86400: e["time_ago"] = f"منذ {int(diff/3600)} ساعة"
            else: e["time_ago"] = f"منذ {int(diff/86400)} يوم"
        return recent

    def get_weekly_patterns(self, limit: int = 10) -> List[dict]:
        return []

    def get_absence_status(self) -> dict:
        if not self._last_activity:
            return {"absent": False, "days": 0, "message": "", "severity": "low"}
        days = (time.time() - self._last_activity) / 86400
        if days >= 3:
            return {"absent": True, "days": round(days, 1),
                    "message": f"لم تدخل منذ {days:.0f} أيام", "severity": "high"}
        elif days >= 1:
            return {"absent": True, "days": round(days, 1),
                    "message": f"لم تدخل منذ {days:.0f} يوم", "severity": "medium"}
        return {"absent": False, "days": round(days, 2), "message": "", "severity": "low"}

    def get_proactive_suggestions(self) -> List[dict]:
        suggestions = []
        absence = self.get_absence_status()
        if absence["absent"]:
            suggestions.append({"type": "absence_return", "message": absence["message"],
                                "priority": absence["severity"]})
        return suggestions[:5]


# ═══════════════════════════════════════════════════════════════════════════════
#  Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/status")
async def temporal_status():
    """الحالة الكاملة للإدراك الزمني — timeline, patterns, absence, suggestions"""
    engine = _get_engine()
    return {
        "version": "v22.0",
        "status": engine.get_status(),
        "absence": engine.get_absence_status(),
        "weekly_patterns": engine.get_weekly_patterns(limit=5),
        "proactive_suggestions": engine.get_proactive_suggestions(),
    }


@router.get("/timeline")
async def temporal_timeline(
    limit: int = Query(20, description="عدد الأحداث الأخيرة"),
):
    """الجدول الزمني — Recent timeline events"""
    engine = _get_engine()
    events = engine.get_timeline(limit=limit)
    return {"events": events, "count": len(events)}


@router.post("/event", dependencies=[Depends(require_auth)])
async def record_temporal_event(event: TemporalEventRequest):
    """تسجيل حدث زمني جديد — Record a new temporal event"""
    engine = _get_engine()
    result = engine.record_activity(
        event_type=event.event_type,
        content=event.content,
        topic=event.topic,
        metadata=event.metadata,
    )
    return {
        "recorded": result.get("recorded", True),
        "notifications": result.get("notifications", []),
        "status": engine.get_status(),
    }
