"""
BABSHARQII v40.0 — Semantic Router API
واجهة برمجة نظام التوافق الدلالي

Endpoints:
  - POST /api/brains/semantic-route  — توجيه دلالي لاستعلام
  - GET  /api/brains/semantic-stats  — إحصائيات التوجيه الدلالي
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("mamoun.api.semantic_router")

router = APIRouter(prefix="/brains", tags=["semantic-router"])


class SemanticRouteRequest(BaseModel):
    """طلب توجيه دلالي"""
    query: str


@router.post("/semantic-route")
async def semantic_route_query(req: SemanticRouteRequest):
    """
    توجيه دلالي لاستعلام

    يستخدم embeddings لتصنيف الاستعلام وتوجيهه
    للأدمغة المناسبة بدقة أعلى من مطابقة الكلمات المفتاحية
    """
    if not req.query or not req.query.strip():
        raise HTTPException(400, "الاستعلام مطلوب")

    try:
        from mamoun.brains.semantic_router import get_semantic_router
        from mamoun.core.llm_client import get_llm_client

        semantic_router = get_semantic_router()

        # Ensure LLM client is set
        if not semantic_router._llm:
            try:
                semantic_router._llm = get_llm_client()
            except Exception:
                pass  # Will use hash-based embeddings

        result = await semantic_router.route(req.query.strip())

        return {
            "query": req.query.strip()[:200],
            "type": result["type"],
            "brains": result["brains"],
            "weights": result["weights"],
            "confidence": result["confidence"],
            "method": result["method"],
            "matched_template": result.get("matched_template", ""),
        }

    except Exception as e:
        logger.error("Semantic routing failed: %s", e)
        raise HTTPException(500, f"فشل التوجيه الدلالي: {str(e)[:200]}")


@router.get("/semantic-stats")
async def get_semantic_stats():
    """
    إحصائيات التوجيه الدلالي

    يعرض: عدد الاستعلامات، نسبة التوجيه الدلالي، متوسط الثقة، توزيع الأنواع
    """
    try:
        from mamoun.brains.semantic_router import get_semantic_router
        semantic_router = get_semantic_router()
        return semantic_router.get_stats()
    except Exception as e:
        logger.error("Failed to get semantic stats: %s", e)
        raise HTTPException(500, f"فشل الحصول على إحصائيات التوجيه: {str(e)[:200]}")
