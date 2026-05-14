"""
BABSHARQII v22.0 — Living Systems API
واجهة برمجة الأنظمة الحية — Heartbeat, Emotion, Memory, Bonding, Reflexes

API Endpoints:
  GET  /api/living/status          — Full living systems status
  GET  /api/living/heartbeat       — Current heartbeat data
  GET  /api/living/vitals          — Vital signs snapshot
  GET  /api/living/emotions        — Emotion spectrum
  GET  /api/living/memory          — Emotional memory status
  GET  /api/living/memory/recall   — Recall emotional episodes
  GET  /api/living/bonding         — Bonding status
  GET  /api/living/bonding/insights — User insights
  GET  /api/living/reflexes        — Reflexes status
  POST /api/living/event           — Process emotional event
  GET  /api/living/identity        — Narrative identity
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, Dict, List, Any

from mamoun.api.deps import require_auth

router = APIRouter(prefix="/living", tags=["living"])


class EmotionalEventRequest(BaseModel):
    event_type: str = "user_message"
    intensity: float = 0.5
    valence: float = 0.0
    source: str = "api"
    description: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
#  Global State Helper
# ═══════════════════════════════════════════════════════════════════════════════

def _get_kernel():
    """Get the global kernel instance"""
    from mamoun.api.deps import get_kernel
    return get_kernel()


# ═══════════════════════════════════════════════════════════════════════════════
#  Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/status")
async def living_status():
    """الحالة الكاملة للأنظمة الحية — Full living systems status"""
    kernel = _get_kernel()
    if not kernel:
        raise HTTPException(503, "Kernel not available")

    return {
        "version": "v22.0",
        "living_systems_initialized": kernel._living_systems_initialized,
        "living_state": kernel._living_state.get_status() if kernel._living_state else {},
        "emotional_memory": kernel._emotional_memory.get_status() if kernel._emotional_memory else {},
        "deep_bonding": kernel._deep_bonding.get_status() if kernel._deep_bonding else {},
        "reflexes": kernel._reflexes_engine.get_status() if kernel._reflexes_engine else {},
        "autonomic": kernel._autonomic_system.get_status() if kernel._autonomic_system else {},
    }


@router.get("/heartbeat")
async def heartbeat():
    """بيانات النبض — Heartbeat data for JARVIS display"""
    kernel = _get_kernel()
    if not kernel or not kernel._living_state:
        raise HTTPException(503, "Living state not available")

    return kernel._living_state.get_heartbeat_data()


@router.get("/vitals")
async def vitals():
    """المؤشرات الحيوية — Vital signs snapshot"""
    kernel = _get_kernel()
    if not kernel or not kernel._living_state:
        raise HTTPException(503, "Living state not available")

    return kernel._living_state.get_vitals_snapshot()


@router.get("/emotions")
async def emotions():
    """طيف المشاعر — Emotion spectrum"""
    kernel = _get_kernel()
    if not kernel or not kernel._living_state:
        raise HTTPException(503, "Living state not available")

    return {
        "dominant": kernel._living_state.get_dominant_emotion(),
        "spectrum": kernel._living_state.get_emotion_spectrum(),
        "pending_thoughts": kernel._living_state.get_pending_thoughts(),
        "pending_actions": kernel._living_state.get_pending_actions(),
    }


@router.get("/memory", dependencies=[Depends(require_auth)])
async def memory_status():
    """حالة الذاكرة العاطفية"""
    kernel = _get_kernel()
    if not kernel or not kernel._emotional_memory:
        raise HTTPException(503, "Emotional memory not available")

    return kernel._emotional_memory.get_status()


@router.get("/memory/recall")
async def memory_recall(
    query: str = Query("", description="Search query"),
    limit: int = Query(10, description="Max results"),
):
    """استرجاع الذكريات العاطفية"""
    kernel = _get_kernel()
    if not kernel or not kernel._emotional_memory:
        raise HTTPException(503, "Emotional memory not available")

    results = kernel._emotional_memory.recall(query=query, limit=limit)
    return {"results": results, "count": len(results)}


@router.get("/identity")
async def identity():
    """الهوية السردية — Narrative identity"""
    kernel = _get_kernel()
    if not kernel or not kernel._emotional_memory:
        raise HTTPException(503, "Emotional memory not available")

    return kernel._emotional_memory.get_identity()


@router.get("/bonding")
async def bonding_status():
    """حالة الارتباط — Bonding status"""
    kernel = _get_kernel()
    if not kernel or not kernel._deep_bonding:
        raise HTTPException(503, "Deep bonding not available")

    return kernel._deep_bonding.get_status()


@router.get("/bonding/insights")
async def bonding_insights(
    category: str = Query(None, description="Filter by category"),
    limit: int = Query(20, description="Max results"),
):
    """معارف عن المستخدم — User insights"""
    kernel = _get_kernel()
    if not kernel or not kernel._deep_bonding:
        raise HTTPException(503, "Deep bonding not available")

    return {"insights": kernel._deep_bonding.get_insights(category=category, limit=limit)}


@router.get("/reflexes")
async def reflexes_status():
    """حالة ردود الفعل — Reflexes status"""
    kernel = _get_kernel()
    if not kernel or not kernel._reflexes_engine:
        raise HTTPException(503, "Reflexes engine not available")

    return kernel._reflexes_engine.get_status()


@router.post("/event", dependencies=[Depends(require_auth)])
async def process_event(event: EmotionalEventRequest):
    """معالجة حدث عاطفي — Process an emotional event"""
    kernel = _get_kernel()
    if not kernel or not kernel._living_state:
        raise HTTPException(503, "Living state not available")

    from mamoun.core.living_state import EmotionalEvent
    import time

    result = kernel._living_state.process_event(EmotionalEvent(
        timestamp=time.time(),
        event_type=event.event_type,
        intensity=event.intensity,
        valence=event.valence,
        source=event.source,
        description=event.description,
    ))

    return {
        "processed": True,
        "dominant_emotion": kernel._living_state.get_dominant_emotion(),
        "vitals": kernel._living_state.get_vitals_snapshot(),
        "effects": result if isinstance(result, dict) else "processed",
    }


@router.get("/dashboard")
async def living_dashboard():
    """بيانات الداش بورد الحية — All data needed for the living dashboard"""
    kernel = _get_kernel()
    if not kernel:
        raise HTTPException(503, "Kernel not available")

    data = {
        "version": "v22.0",
        "heartbeat": {},
        "vitals": {},
        "emotions": {},
        "bonding": {},
        "identity": {},
        "reflexes_summary": {},
        "memory_summary": {},
    }

    if kernel._living_state:
        data["heartbeat"] = kernel._living_state.get_heartbeat_data()
        data["vitals"] = kernel._living_state.get_vitals_snapshot()
        data["emotions"] = {
            "dominant": kernel._living_state.get_dominant_emotion(),
            "spectrum": kernel._living_state.get_emotion_spectrum(),
        }

    if kernel._deep_bonding:
        data["bonding"] = kernel._deep_bonding.get_bonding_data()

    if kernel._emotional_memory:
        data["identity"] = kernel._emotional_memory.get_identity()
        data["memory_summary"] = {
            "total_episodes": len(kernel._emotional_memory._episodes),
            "relationships": len(kernel._emotional_memory._relational_map),
        }

    if kernel._reflexes_engine:
        data["reflexes_summary"] = {
            "total_triggers": len(kernel._reflexes_engine._triggers),
            "total_fired": sum(t.fire_count for t in kernel._reflexes_engine._triggers.values()),
        }

    return data
