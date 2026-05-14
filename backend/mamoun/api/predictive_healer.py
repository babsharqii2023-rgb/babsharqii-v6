"""
BABSHARQII v40.0 — Predictive Healer API
واجهة برمجة نظام الإصلاح التنبؤي

Endpoints:
  GET  /api/predictive-healer/status    — التنبؤات والحالة الحالية
  POST /api/predictive-healer/predict   — تشغيل تحليل تنبؤي
  POST /api/predictive-healer/prevent   — اتخاذ إجراء وقائي لتنبؤ معين
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("mamoun.api.predictive_healer")

router = APIRouter(prefix="/predictive-healer", tags=["predictive-healer"])


class PreventRequest(BaseModel):
    """طلب اتخاذ إجراء وقائي"""
    prediction_id: Optional[str] = None
    component: Optional[str] = None
    failure_type: Optional[str] = None


@router.get("/status")
async def get_healer_status():
    """
    حالة نظام الإصلاح التنبؤي

    يعرض: التنبؤات النشطة، دقة التنبؤات، عدد الإجراءات الوقائية
    """
    try:
        from mamoun.core.predictive_healer import get_predictive_healer
        healer = get_predictive_healer()

        if not healer._initialized:
            healer.initialize()

        return healer.get_status()
    except Exception as e:
        logger.error("Failed to get healer status: %s", e)
        raise HTTPException(500, f"فشل الحصول على حالة المعالج التنبؤي: {str(e)[:200]}")


@router.post("/predict")
async def run_prediction():
    """
    تشغيل تحليل تنبؤي

    يجمع المقاييس ويحلل الأنماط ويُنبئ بالأعطال المحتملة
    """
    try:
        from mamoun.core.predictive_healer import get_predictive_healer
        from mamoun.core.llm_client import get_llm_client

        healer = get_predictive_healer()

        if not healer._initialized:
            healer.initialize()

        # Ensure LLM client is set
        if not healer._llm:
            try:
                healer._llm = get_llm_client()
            except Exception:
                pass

        # Run prediction
        predictions = await healer.predict_failures()

        return {
            "status": "completed",
            "predictions_count": len(predictions),
            "predictions": [p.to_dict() for p in predictions],
            "healer_status": healer.get_status(),
        }
    except Exception as e:
        logger.error("Prediction failed: %s", e)
        raise HTTPException(500, f"فشل التحليل التنبؤي: {str(e)[:200]}")


@router.post("/prevent")
async def take_preventive_action(req: PreventRequest):
    """
    اتخاذ إجراء وقائي لتنبؤ معين

    إن لم يُحدّد تنبؤ، يبحث عن الأعلى أولوية
    """
    try:
        from mamoun.core.predictive_healer import get_predictive_healer

        healer = get_predictive_healer()

        if not healer._initialized:
            healer.initialize()

        # Find the prediction to prevent
        target_prediction = None

        if req.prediction_id:
            # Find by ID
            for pred in healer.get_predictions():
                if pred.prediction_id == req.prediction_id:
                    target_prediction = pred.to_dict()
                    break
        elif req.component or req.failure_type:
            # Find by component/failure_type
            for pred in healer.get_predictions():
                if req.component and pred.component == req.component:
                    target_prediction = pred.to_dict()
                    break
                if req.failure_type and pred.failure_type == req.failure_type:
                    target_prediction = pred.to_dict()
                    break

        if not target_prediction:
            # Find the highest-severity prediction
            active = healer.get_predictions()
            if active:
                # Sort by severity (critical > high > medium > low)
                severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
                active.sort(key=lambda p: severity_order.get(p.severity, 0), reverse=True)
                target_prediction = active[0].to_dict()
            else:
                return {
                    "status": "no_predictions",
                    "message": "لا توجد تنبؤات نشطة — النظام يعمل بشكل طبيعي",
                    "message_ar": "لا توجد تنبؤات نشطة — النظام يعمل بشكل طبيعي",
                }

        # Take preventive action
        result = await healer.take_preventive_action(target_prediction)

        return {
            "status": "action_taken" if result.get("success") else "action_failed",
            "result": result,
        }
    except Exception as e:
        logger.error("Preventive action failed: %s", e)
        raise HTTPException(500, f"فشل الإجراء الوقائي: {str(e)[:200]}")
