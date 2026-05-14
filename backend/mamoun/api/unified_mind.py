"""
BABSHARQII v40.0 — Unified Mind API
واجهة برمجة العقل الموحّد

Endpoints:
  POST /api/unified-mind/process — معالجة استعلام عبر الأنبوب الموحّد
  GET  /api/unified-mind/status  — حالة العقل الموحّد
  GET  /api/unified-mind/fusion  — نسبة الدمج الحالية
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("mamoun.api.unified_mind")

router = APIRouter(prefix="/unified-mind", tags=["unified-mind"])


class ProcessRequest(BaseModel):
    """طلب معالجة عبر العقل الموحّد"""
    query: str
    context: Optional[dict] = None


@router.post("/process")
async def process_query(req: ProcessRequest):
    """
    معالجة استعلام عبر الأنبوب الموحّد

    يمر الاستعلام عبر:
    1. تقييم القدرات
    2. التوجيه الدلالي
    3. مداولة الأدمغة
    4. تنفيذ القرار
    5. اختبار النتيجة (إن كان تعديلاً)
    6. فحص الأعراض الجانبية
    7. التعلّم من التفاعل
    """
    if not req.query or not req.query.strip():
        raise HTTPException(400, "الاستعلام مطلوب")

    try:
        from mamoun.core.unified_mind import get_unified_mind

        mind = get_unified_mind()

        if not mind._initialized:
            await mind.initialize()

        result = await mind.process(
            query=req.query.strip(),
            context=req.context or {},
        )

        return {
            "status": "processed",
            **result,
        }
    except Exception as e:
        logger.error("UnifiedMind processing failed: %s", e)
        raise HTTPException(500, f"فشلت معالجة العقل الموحّد: {str(e)[:200]}")


@router.get("/status")
async def get_unified_mind_status():
    """
    حالة العقل الموحّد

    يعرض: الأنظمة الفرعية المتاحة، عدد العمليات، حالة التهيئة
    """
    try:
        from mamoun.core.unified_mind import get_unified_mind

        mind = get_unified_mind()
        return mind.get_status()
    except Exception as e:
        logger.error("Failed to get UnifiedMind status: %s", e)
        raise HTTPException(500, f"فشل الحصول على حالة العقل الموحّد: {str(e)[:200]}")


@router.get("/fusion")
async def get_fusion_percent():
    """
    نسبة الدمج الحالية

    يعرض: نسبة دمج الأنظمة، تفاصيل كل نظام فرعي
    """
    try:
        from mamoun.core.unified_mind import get_unified_mind

        mind = get_unified_mind()
        return mind.get_fusion_percent()
    except Exception as e:
        logger.error("Failed to get fusion percent: %s", e)
        raise HTTPException(500, f"فشل الحصول على نسبة الدمج: {str(e)[:200]}")
