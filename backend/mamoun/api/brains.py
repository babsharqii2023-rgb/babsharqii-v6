"""
BABSHARQII v40.0 — Brains & Instincts Routes
Multi-brain architecture and instinct system routes.
v40.0 Fusion: Added SSE deliberation endpoint for 5-brain real deliberation
"""

import json
import asyncio
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from mamoun.api.deps import require_auth, brains, instincts

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Brains Routes
# =============================================================================

# Mapping of brain_id → standardized display info
_BRAIN_META = {
    "neural":     {"nameAr": "العصبي",      "model": "glm-5.1",         "type": "deep_learning"},
    "causal":     {"nameAr": "السببي",       "model": "deepseek-reasoner","type": "causal_reasoning"},
    "symbolic":   {"nameAr": "الرمزي",       "model": "glm-4-plus",      "type": "symbolic_logic"},
    "bayesian":   {"nameAr": "الاحتمالي",    "model": "gemini-2.0-flash","type": "probabilistic"},
    "world_model":{"nameAr": "نموذج العالم", "model": "deepseek-chat",   "type": "world_modeling"},
}


class DeliberationRequest(BaseModel):
    message: str
    active_brains: List[str] = ["neural", "causal", "symbolic", "bayesian", "world_model"]
    context: dict = {}


@router.get("/brains")
async def get_brains():
    result = []
    for b in brains:
        d = b.state.to_dict()
        # Ensure standardized fields for frontend
        d["id"] = b.state.id
        d["nameAr"] = d.get("name_ar", "") or _BRAIN_META.get(b.state.id, {}).get("nameAr", "")
        if not d.get("model"):
            d["model"] = _BRAIN_META.get(b.state.id, {}).get("model", "")
        d["type"] = _BRAIN_META.get(b.state.id, {}).get("type", "")
        d["enabled"] = b.state.status in ("active", "thinking")
        result.append(d)
    return {"brains": result}


@router.post("/brains/{brain_id}/activate", dependencies=[Depends(require_auth)])
async def activate_brain(brain_id: str):
    for brain in brains:
        if brain.state.id == brain_id:
            brain.activate()
            return {"success": True}
    raise HTTPException(status_code=404, detail="الدماغ غير موجود")


@router.post("/brains/{brain_id}/deactivate", dependencies=[Depends(require_auth)])
async def deactivate_brain(brain_id: str):
    for brain in brains:
        if brain.state.id == brain_id:
            brain.deactivate()
            return {"success": True}
    raise HTTPException(status_code=404, detail="الدماغ غير موجود")


# =============================================================================
# v40.0 Fusion: SSE Deliberation — مداولة 5 أدمغة حقيقية
# =============================================================================

@router.post("/deliberate")
async def deliberate(req: DeliberationRequest):
    """مداولة حقيقية بـ 5 أدمغة مع بث SSE"""
    
    async def stream_deliberation():
        # بث كل دماغ يفكر
        for brain_id in req.active_brains:
            meta = _BRAIN_META.get(brain_id, {})
            yield f"data: {json.dumps({'type': 'brain_thinking', 'brain': brain_id, 'nameAr': meta.get('nameAr', brain_id), 'model': meta.get('model', '')})}\n\n"
            await asyncio.sleep(0.1)
        
        # تنفيذ المداولة عبر BrainRouter
        try:
            from mamoun.brains.brain_router import get_brain_router
            router_instance = get_brain_router()
            result = await router_instance.route(req.message, context=req.context)
            
            if result:
                result_data = {
                    "type": "deliberation_complete",
                    "winning_brain": getattr(result, 'winning_brain', None) or getattr(result, 'brain_id', 'neural'),
                    "response": getattr(result, 'response', '') or getattr(result, 'content', '') or str(result),
                    "confidence": getattr(result, 'confidence', 0.8),
                    "brain_responses": getattr(result, 'brain_responses', {}),
                    "consensus_level": getattr(result, 'consensus_level', 0.7),
                }
                yield f"data: {json.dumps(result_data)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'deliberation_fallback', 'response': '', 'confidence': 0.5})}\n\n"
        except Exception as e:
            logger.error(f"Deliberation failed: {e}")
            yield f"data: {json.dumps({'type': 'deliberation_error', 'error': str(e)[:200]})}\n\n"
    
    return StreamingResponse(stream_deliberation(), media_type="text/event-stream")


# =============================================================================
# v100 Fusion: BrainRouter Direct — توجيه مباشر بنتيجة JSON (لا SSE)
# =============================================================================

class RouteRequest(BaseModel):
    query: str
    active_brains: List[str] = ["neural", "causal", "symbolic", "bayesian", "world_model"]
    context: dict = {}


@router.post("/brains/route")
async def route_brain(req: RouteRequest):
    """توجيه مباشر عبر BrainRouter — يرجع JSON فوري بدون SSE"""
    try:
        from mamoun.brains.brain_router import get_brain_router
        router_instance = get_brain_router()
        result = await router_instance.route(req.query, context=req.context)
        if result:
            return result.to_dict()
        raise HTTPException(status_code=500, detail="فشل التوجيه")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Brain routing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)[:200])


# =============================================================================
# v100 Fusion: Brain Status — حالة الأدمغة التفصيلية مع بيانات النماذج البديلة
# =============================================================================

@router.get("/brains/status")
async def get_brain_status():
    """تقرير حالة الأدمغة التفصيلي — يعرض النموذج الأصلي والفعلي ومفتاح API"""
    try:
        from mamoun.brains.brain_router import get_brain_router
        router_instance = get_brain_router()
        status = router_instance.get_brain_status()
        
        # حساب الملخص
        total = len(status)
        active = sum(1 for s in status.values() if s.get("status") in ("active", "thinking", "idle"))
        on_fallback = sum(1 for s in status.values() if s.get("is_on_fallback", False))
        missing_keys = sum(1 for s in status.values() if not s.get("has_api_key", True))
        warnings = [s["fallback_warning"] for s in status.values() if s.get("fallback_warning")]
        
        return {
            "brains": status,
            "summary": {
                "active_brains": active,
                "total_brains": total,
                "brains_on_fallback": on_fallback,
                "missing_api_keys": missing_keys,
                "fallback_warnings": warnings,
            }
        }
    except Exception as e:
        logger.error(f"Brain status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)[:200])
