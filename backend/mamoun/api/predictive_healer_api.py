"""
BABSHARQII v40.0 — Predictive Healer API
نظام الإصلاح التنبؤي — API Endpoints

API Endpoints:
  GET  /api/predictive-healer/status     — حالة النظام التنبؤي
  POST /api/predictive-healer/predict     — تشغيل التحليل التنبؤي
  POST /api/predictive-healer/prevent     — اتخاذ إجراء وقائي
"""

import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from mamoun.api.deps import require_auth
from mamoun.core.predictive_healer import get_predictive_healer

logger = logging.getLogger("mamoun.api.predictive_healer")

router = APIRouter(prefix="/predictive-healer", tags=["predictive-healer"])


class PreventRequest(BaseModel):
    component: str
    failure_type: str
    prevention_action: str


@router.get("/status")
async def get_status():
    """حالة النظام التنبؤي"""
    healer = get_predictive_healer()
    return healer.get_status()


@router.post("/predict", dependencies=[Depends(require_auth)])
async def run_prediction():
    """تشغيل التحليل التنبؤي"""
    healer = get_predictive_healer()

    # Collect metrics first
    metrics = await healer.collect_metrics()

    # Run prediction
    predictions = await healer.predict_failures()

    return {
        "metrics": metrics,
        "predictions": predictions,
        "prediction_count": len(predictions),
        "critical_count": len([p for p in predictions if p.get("severity") == "critical"]),
    }


@router.post("/prevent", dependencies=[Depends(require_auth)])
async def take_preventive_action(req: PreventRequest):
    """اتخاذ إجراء وقائي"""
    healer = get_predictive_healer()
    prediction = {
        "component": req.component,
        "failure_type": req.failure_type,
        "prevention_action": req.prevention_action,
    }
    result = await healer.take_preventive_action(prediction)
    return result
