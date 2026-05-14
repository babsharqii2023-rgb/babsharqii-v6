"""
BABSHARQII v22.0 — Predictive Memory API
واجهة برمجة الذاكرة التنبؤية — Predictions, Verification, Patterns

API Endpoints:
  GET   /api/predictions/status                — Prediction system status + recent predictions
  POST  /api/predictions/create                — Create a new prediction
  POST  /api/predictions/{prediction_id}/verify — Verify a prediction (correct/incorrect)
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from mamoun.api.deps import require_auth

router = APIRouter(prefix="/predictions", tags=["predictions"])


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج البيانات — Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class CreatePredictionRequest(BaseModel):
    """نموذج إنشاء تنبؤ"""
    predicted_topic: str = ""
    predicted_action: str = ""
    confidence: float = 0.5
    reasoning: str = ""
    evidence: List[str] = []


class VerifyPredictionRequest(BaseModel):
    """نموذج تحقق من تنبؤ"""
    correct: bool = True
    actual_topic: str = ""  # الموضوع الفعلي (إن اختلف)


# ═══════════════════════════════════════════════════════════════════════════════
#  محرك الذاكرة التنبؤية — محاولة استخدام Core module أولاً
# ═══════════════════════════════════════════════════════════════════════════════

_engine = None

def _get_engine():
    """الحصول على محرك الذاكرة التنبؤية — من Core فقط"""
    global _engine
    if _engine is not None:
        return _engine

    try:
        from mamoun.core.predictive_memory import predictive_memory
        if not predictive_memory._initialized:
            predictive_memory.initialize()
        _engine = predictive_memory
        return _engine
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/status")
async def predictions_status():
    """حالة نظام التنبؤ + التنبؤات الأخيرة — Prediction system status"""
    engine = _get_engine()
    if engine is None:
        raise HTTPException(503, {"error": "PredictiveMemory engine not available"})
    status = engine.get_status()
    predictions = engine.get_predictions()[:10]  # v35 FIX: get_predictions() takes no args
    patterns = engine.get_patterns(limit=5) if hasattr(engine, "get_patterns") else []
    return {
        "version": "v22.0",
        "status": status,
        "recent_predictions": predictions,
        "patterns": patterns,
    }


@router.post("/create", dependencies=[Depends(require_auth)])
async def create_prediction(req: CreatePredictionRequest):
    """إنشاء تنبؤ جديد — Create a new prediction via record_interaction"""
    engine = _get_engine()
    if engine is None:
        raise HTTPException(503, {"error": "PredictiveMemory engine not available"})
    # v35 FIX: Use record_interaction + predict instead of non-existent create_prediction
    engine.record_interaction(
        topic=req.predicted_topic,
        action=req.predicted_action,
        metadata={"confidence": req.confidence, "reasoning": req.reasoning, "evidence": req.evidence},
    )
    predictions = engine.predict(n=1)
    return {
        "created": True,
        "prediction": predictions[0].__dict__ if predictions else {},
        "status": engine.get_status(),
    }


@router.post("/{prediction_id}/verify", dependencies=[Depends(require_auth)])
async def verify_prediction(prediction_id: str, req: VerifyPredictionRequest):
    """تحقق من تنبؤ — Verify a prediction as correct or incorrect"""
    engine = _get_engine()
    if engine is None:
        raise HTTPException(503, {"error": "PredictiveMemory engine not available"})
    # v35 FIX: Use record_interaction with actual outcome to verify
    engine.record_interaction(
        topic=req.actual_topic or prediction_id,
        action="verified",
        metadata={"correct": req.correct, "prediction_id": prediction_id},
    )
    return {
        "verified": True,
        "prediction_id": prediction_id,
        "correct": req.correct,
        "status": engine.get_status(),
    }
