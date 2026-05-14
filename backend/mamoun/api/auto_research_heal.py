"""
BABSHARQII v40.0 — Auto Research-Heal API
واجهة برمجة حلقة البحث والشفاء التلقائية

API Endpoints:
  GET  /api/auto-research-heal/status  — حالة حلقة البحث-الشفاء
  POST /api/auto-research-heal/start   — بدء الحلقة
  POST /api/auto-research-heal/stop    — إيقاف الحلقة
  POST /api/auto-research-heal/cycle   — تشغيل دورة يدوياً
  GET  /api/auto-research-heal/history — سجل الدورات السابقة
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("mamoun.api.auto_research_heal")

router = APIRouter(prefix="/auto-research-heal", tags=["auto-research-heal"])


class ManualCycleRequest(BaseModel):
    component: str
    description: str = ""
    severity: str = "medium"


@router.get("/status")
async def get_auto_research_heal_status():
    """حالة حلقة البحث والشفاء التلقائية"""
    try:
        from mamoun.core.auto_research_heal_loop import get_auto_research_heal
        loop = get_auto_research_heal()
        return loop.get_status()
    except Exception as e:
        logger.error("Failed to get auto-research-heal status: %s", e)
        return {
            "enabled": False,
            "running": False,
            "error": str(e)[:200],
        }


@router.post("/start")
async def start_auto_research_heal():
    """بدء حلقة البحث والشفاء التلقائية"""
    try:
        from mamoun.core.auto_research_heal_loop import get_auto_research_heal
        loop = get_auto_research_heal()
        if not loop._initialized:
            loop.initialize()
        await loop.start()
        return {"status": "started", "info": loop.get_status()}
    except Exception as e:
        logger.error("Failed to start auto-research-heal: %s", e)
        raise HTTPException(500, f"فشل بدء حلقة البحث-الشفاء: {str(e)[:200]}")


@router.post("/stop")
async def stop_auto_research_heal():
    """إيقاف حلقة البحث والشفاء التلقائية"""
    try:
        from mamoun.core.auto_research_heal_loop import get_auto_research_heal
        loop = get_auto_research_heal()
        await loop.shutdown()
        return {"status": "stopped"}
    except Exception as e:
        logger.error("Failed to stop auto-research-heal: %s", e)
        raise HTTPException(500, f"فشل إيقاف حلقة البحث-الشفاء: {str(e)[:200]}")


@router.post("/cycle")
async def run_manual_cycle(req: ManualCycleRequest):
    """تشغيل دورة بحث-شفاء يدوياً"""
    try:
        from mamoun.core.auto_research_heal_loop import get_auto_research_heal
        loop = get_auto_research_heal()
        if not loop._initialized:
            loop.initialize()
        cycle = await loop.run_cycle(req.component, req.description, req.severity)
        return cycle.to_dict()
    except Exception as e:
        logger.error("Manual cycle failed: %s", e)
        raise HTTPException(500, f"فشل الدورة اليدوية: {str(e)[:200]}")


@router.get("/history")
async def get_auto_research_heal_history(limit: int = 20):
    """سجل دورات البحث-الشفاء"""
    try:
        from mamoun.core.auto_research_heal_loop import get_auto_research_heal
        loop = get_auto_research_heal()
        return {"history": loop.get_history(limit=limit)}
    except Exception as e:
        logger.error("Failed to get history: %s", e)
        return {"history": [], "error": str(e)[:200]}
