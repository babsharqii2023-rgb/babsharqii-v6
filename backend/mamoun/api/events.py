"""
BABSHARQII v22.0 — System Events API
واجهة برمجة أحداث النظام — Kernel, Brain, Evolution Events, SSE Streaming

API Endpoints:
  GET  /api/events/recent  — Recent system events
  GET  /api/events/stream  — SSE endpoint for real-time event streaming
  POST /api/events/emit    — Emit a new system event
"""

import time
import asyncio
import json
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from mamoun.api.deps import require_auth

router = APIRouter(prefix="/events", tags=["events"])


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج البيانات — Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class EmitEventRequest(BaseModel):
    """نموذج إصدار حدث جديد"""
    event_type: str = "system"  # kernel, brain, evolution, system, user, alert
    source: str = "api"
    content: str = ""
    severity: str = "info"  # info, warning, error, critical
    metadata: Dict[str, Any] = {}


# ═══════════════════════════════════════════════════════════════════════════════
#  حالة الأحداث في الذاكرة — In-Memory Event State
# ═══════════════════════════════════════════════════════════════════════════════

_events: List[Dict] = []
_event_counter = 0
_max_events = 500

# قائمة انتظار SSE — مشتركين ينتظرون أحداث حقيقية
_sse_subscribers: List[asyncio.Queue] = []


def _add_event(event_type: str, source: str, content: str,
               severity: str, metadata: Dict) -> Dict:
    """إضافة حدث جديد وإبلاغ مشتركي SSE"""
    global _event_counter
    _event_counter += 1
    now = time.time()
    event = {
        "id": f"evt_{_event_counter}",
        "event_type": event_type,
        "source": source,
        "content": content,
        "severity": severity,
        "metadata": metadata,
        "timestamp": now,
    }
    _events.append(event)
    # الحد الأقصى
    if len(_events) > _max_events:
        _events[:] = _events[-_max_events:]

    # إبلاغ مشتركي SSE
    for queue in _sse_subscribers:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass  # تجاهل إذا كانت القائمة ممتلئة

    return event


# ═══════════════════════════════════════════════════════════════════════════════
#  أحداث أولية — Seed Events (for dashboard display)
# ═══════════════════════════════════════════════════════════════════════════════

_seed_time = time.time()
_seed_events = [
    {"event_type": "kernel", "source": "mamoun_kernel", "content": "تم تهيئة النواة بنجاح", "severity": "info"},
    {"event_type": "brain", "source": "brain_orchestrator", "content": "5 أدمغة نشطة — GPT-4o, Claude, Gemini, DeepSeek, Qwen", "severity": "info"},
    {"event_type": "system", "source": "autonomic", "content": "الجهاز العصبي المستقل يعمل", "severity": "info"},
    {"event_type": "evolution", "source": "evolution_loop", "content": "حلقة التطور جاهزة — الجيل 1", "severity": "info"},
]
for i, seed in enumerate(_seed_events):
    _add_event(
        event_type=seed["event_type"],
        source=seed["source"],
        content=seed["content"],
        severity=seed["severity"],
        metadata={"seed": True},
    )
    # تعديل timestamp ليكون متباعداً
    _events[-1]["timestamp"] = _seed_time - (len(_seed_events) - i) * 60


# ═══════════════════════════════════════════════════════════════════════════════
#  Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/recent")
async def recent_events(
    limit: int = Query(50, description="عدد الأحداث الأخيرة"),
    event_type: Optional[str] = Query(None, description="تصفية حسب النوع"),
    severity: Optional[str] = Query(None, description="تصفية حسب الخطورة"),
):
    """الأحداث الأخيرة — Recent system events with optional filtering"""
    filtered = _events[:]

    if event_type:
        filtered = [e for e in filtered if e["event_type"] == event_type]
    if severity:
        filtered = [e for e in filtered if e["severity"] == severity]

    # ترتيب من الأحدث للأقدم
    filtered.sort(key=lambda e: e["timestamp"], reverse=True)
    recent = filtered[:limit]

    # إضافة time_ago لكل حدث
    now = time.time()
    for e in recent:
        diff = now - e["timestamp"]
        if diff < 60: e["time_ago"] = "الآن"
        elif diff < 3600: e["time_ago"] = f"منذ {int(diff/60)} دقيقة"
        elif diff < 86400: e["time_ago"] = f"منذ {int(diff/3600)} ساعة"
        else: e["time_ago"] = f"منذ {int(diff/86400)} يوم"

    return {"events": recent, "count": len(recent), "total": len(_events)}


@router.get("/stream")
async def event_stream():
    """بث أحداث حقيقي — SSE endpoint for real-time event streaming"""

    async def event_generator():
        """مولد أحداث SSE — يرسل أحداث حقيقية + نبضات心跳"""
        queue = asyncio.Queue(maxsize=100)
        _sse_subscribers.append(queue)

        try:
            # إرسال حدث اتصال أولي
            yield f"data: {json.dumps({'type': 'connected', 'message': 'متصل ببث الأحداث'}, ensure_ascii=False)}\n\n"

            while True:
                try:
                    # انتظار حدث مع مهلة 30 ثانية
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # نبض心跳 — إبقاء الاتصال حياً
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()}, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            # إزالة المشترك
            if queue in _sse_subscribers:
                _sse_subscribers.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/emit", dependencies=[Depends(require_auth)])
async def emit_event(req: EmitEventRequest):
    """إصدار حدث جديد — Emit a new system event"""
    event = _add_event(
        event_type=req.event_type,
        source=req.source,
        content=req.content,
        severity=req.severity,
        metadata=req.metadata,
    )
    return {
        "emitted": True,
        "event": event,
        "total_events": len(_events),
    }
