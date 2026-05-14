"""
BABSHARQII v40.0 — Continuous Learner API
واجهة برمجة نظام التعلم المستمر

Endpoints:
  - POST /api/learning/cycle     — تشغيل دورة تعلّم واحدة
  - GET  /api/learning/status    — حالة النظام وقاعدة المعرفة
  - GET  /api/learning/knowledge — محتويات قاعدة المعرفة
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("mamoun.api.continuous_learner")

router = APIRouter(prefix="/learning", tags=["continuous-learner"])


class CycleRequest(BaseModel):
    """طلب تشغيل دورة تعلّم"""
    areas: Optional[list] = None  # مجالات محددة (اختياري)


class CycleResponse(BaseModel):
    """نتيجة دورة التعلّم"""
    status: str
    cycle_id: str = ""
    areas_researched: int = 0
    total_findings: int = 0
    total_proposals: int = 0
    duration_seconds: float = 0.0
    findings_by_area: dict = {}


@router.post("/cycle")
async def trigger_learning_cycle(req: CycleRequest = CycleRequest()):
    """
    تشغيل دورة تعلّم واحدة

    يبحث في المجالات المحددة (أو كل المجالات الافتراضية)
    ويُحلّل النتائج ويُنشئ اقتراحات تحسين
    """
    try:
        from mamoun.core.continuous_learner import get_continuous_learner
        learner = get_continuous_learner()

        # Ensure LLM client is set
        if not learner._llm:
            try:
                from mamoun.core.llm_client import get_llm_client
                learner._llm = get_llm_client()
            except Exception as e:
                logger.warning("Could not set LLM client on learner: %s", e)

        # Override areas if specified
        if req.areas:
            original_areas = learner.DEFAULT_AREAS
            learner.DEFAULT_AREAS = req.areas
            result = await learner.learn_cycle()
            learner.DEFAULT_AREAS = original_areas
        else:
            result = await learner.learn_cycle()

        return {
            "status": "completed",
            "cycle_id": result.cycle_id,
            "areas_researched": result.areas_researched,
            "total_findings": result.total_findings,
            "total_proposals": result.total_proposals,
            "duration_seconds": round(result.duration_seconds, 2),
            "findings_by_area": {
                k: {
                    "summary": v.get("summary", "")[:300],
                    "confidence": v.get("confidence", 0),
                    "proposals_count": len(v.get("proposals", [])),
                    "method": v.get("method", "unknown"),
                }
                for k, v in result.findings_by_area.items()
                if not k.startswith("_")
            },
        }

    except Exception as e:
        logger.error("Learning cycle failed: %s", e)
        raise HTTPException(500, f"فشلت دورة التعلّم: {str(e)[:200]}")


@router.get("/status")
async def get_learner_status():
    """
    حالة نظام التعلم المستمر وقاعدة المعرفة

    يعرض: هل يعمل، كم دورة، كم مدخل في قاعدة المعرفة، آخر دورة
    """
    try:
        from mamoun.core.continuous_learner import get_continuous_learner
        learner = get_continuous_learner()
        return learner.get_status()
    except Exception as e:
        logger.error("Failed to get learner status: %s", e)
        raise HTTPException(500, f"فشل الحصول على حالة المتعلّم: {str(e)[:200]}")


@router.get("/knowledge")
async def get_knowledge_base():
    """
    محتويات قاعدة المعرفة

    يعرض كل المدخلات مرتبة حسب المجال
    """
    try:
        from mamoun.core.continuous_learner import get_continuous_learner
        learner = get_continuous_learner()
        kb = learner.get_knowledge_base()

        # Summarize for readability
        summary = {}
        for area, entries in kb.items():
            summary[area] = {
                "entries_count": len(entries),
                "latest_entry": entries[0] if entries else None,
            }

        return {
            "areas": list(kb.keys()),
            "total_entries": sum(len(v) for v in kb.values()),
            "summary": summary,
            "full_knowledge": kb,
        }
    except Exception as e:
        logger.error("Failed to get knowledge base: %s", e)
        raise HTTPException(500, f"فشل الحصول على قاعدة المعرفة: {str(e)[:200]}")
