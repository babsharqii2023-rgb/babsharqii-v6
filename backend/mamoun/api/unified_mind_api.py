"""
BABSHARQII v40.0 — Unified Mind API
العقل الموحّد — API Endpoints

API Endpoints:
  POST /api/unified-mind/process   — معالجة استعلام عبر المسار الموحّد
  GET  /api/unified-mind/status    — حالة العقل الموحّد
  GET  /api/unified-mind/fusion    — نسبة الاندماج الحالية
"""

import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from mamoun.api.deps import require_auth
from mamoun.core.unified_mind import get_unified_mind

logger = logging.getLogger("mamoun.api.unified_mind")

router = APIRouter(prefix="/unified-mind", tags=["unified-mind"])


class ProcessRequest(BaseModel):
    query: str
    context: dict = {}


@router.post("/process", dependencies=[Depends(require_auth)])
async def process_query(req: ProcessRequest):
    """معالجة استعلام عبر المسار الموحّد الكامل"""
    mind = get_unified_mind()

    if not mind._initialized:
        await mind.initialize()

    result = await mind.process(req.query, req.context)
    return result.to_dict()


@router.get("/status")
async def get_status():
    """حالة العقل الموحّد"""
    mind = get_unified_mind()
    return mind.get_status()


@router.get("/fusion")
async def get_fusion_percent():
    """نسبة الاندماج الحالية"""
    mind = get_unified_mind()
    status = mind.get_status()

    # Also get capability assessment for more accurate fusion
    try:
        from mamoun.core.capability_assessor import CapabilityAssessor
        from mamoun.core.llm_client import get_llm_client
        llm = get_llm_client()
        assessor = CapabilityAssessor(llm_client=llm)
        assessment = await assessor.assess()
        fusion = assessment.get("overall_fusion_percent", 0)
    except Exception:
        fusion = status.get("fusion_percent", 0)

    return {
        "fusion_percent": round(fusion, 1),
        "active_subsystems": status.get("active_subsystems", 0),
        "total_subsystems": status.get("total_subsystems", 7),
        "subsystem_status": status.get("subsystem_status", {}),
    }
