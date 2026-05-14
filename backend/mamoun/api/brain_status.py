"""
BABSHARQII v40.0 — Brain Status API
حالة الأدمغة التفصيلية — عرض النموذج الأصلي والفعلي وتحذيرات البدائل

API Endpoints:
  GET /api/brains/status — حالة تفصيلية لكل دماغ مع تحذيرات النماذج البديلة
"""

import logging
from fastapi import APIRouter, Depends

from mamoun.api.deps import require_auth

logger = logging.getLogger("mamoun.api.brain_status")

router = APIRouter(tags=["brain-status"])


@router.get("/brains/status")
async def get_brain_status():
    """
    تقرير حالة الأدمغة التفصيلي
    
    يعرض لكل دماغ:
    - النموذج الأصلي (original_model)
    - النموذج الفعلي المستخدم (actual_model)
    - هل الدماغ على نموذج بديل (is_on_fallback)
    - مفتاح API المطلوب (api_key_env)
    - هل مفتاح API موجود (has_api_key)
    - تحذير إن كان على بديل (fallback_warning)
    """
    try:
        from mamoun.brains.brain_router import get_brain_router
        router_instance = get_brain_router()
        brain_status = router_instance.get_brain_status()
        
        # Summarize fallback warnings
        fallback_warnings = []
        for brain_id, status in brain_status.items():
            if status.get("fallback_warning"):
                fallback_warnings.append(status["fallback_warning"])
        
        # Calculate summary stats
        total_brains = len(brain_status)
        active_brains = sum(1 for s in brain_status.values() if s.get("status") in ("active", "thinking", "idle"))
        brains_on_fallback = sum(1 for s in brain_status.values() if s.get("is_on_fallback"))
        missing_api_keys = sum(1 for s in brain_status.values() if not s.get("has_api_key"))
        
        return {
            "status": "ok",
            "brains": brain_status,
            "summary": {
                "total_brains": total_brains,
                "active_brains": active_brains,
                "brains_on_fallback": brains_on_fallback,
                "missing_api_keys": missing_api_keys,
                "all_brains_original": brains_on_fallback == 0,
                "fallback_warnings": fallback_warnings,
            },
        }
    except Exception as e:
        logger.error(f"Failed to get brain status: {e}")
        # Fallback: return basic status from registry without router
        try:
            from mamoun.brains.brain_router import BRAIN_MODEL_REGISTRY
            import os
            
            brains = {}
            for brain_id, entry in BRAIN_MODEL_REGISTRY.items():
                api_key_env = entry.get("api_key_env", "")
                brains[brain_id] = {
                    "brain_id": brain_id,
                    "name_ar": entry.get("name_ar", ""),
                    "original_model": entry.get("original_model", ""),
                    "actual_model": "unknown",
                    "fallback_model": entry.get("fallback_model", ""),
                    "is_on_fallback": False,
                    "api_key_env": api_key_env,
                    "has_api_key": bool(os.environ.get(api_key_env, "")),
                    "status": "router_unavailable",
                    "confidence": 0.0,
                    "weight": 0.0,
                    "total_interactions": 0,
                    "error_count": 0,
                    "fallback_warning": None,
                }
            
            return {
                "status": "degraded",
                "brains": brains,
                "summary": {
                    "total_brains": len(brains),
                    "active_brains": 0,
                    "brains_on_fallback": 0,
                    "missing_api_keys": sum(1 for s in brains.values() if not s.get("has_api_key")),
                    "all_brains_original": True,
                    "fallback_warnings": [],
                    "error": str(e)[:200],
                },
            }
        except Exception as e2:
            return {
                "status": "error",
                "brains": {},
                "summary": {
                    "total_brains": 0,
                    "active_brains": 0,
                    "brains_on_fallback": 0,
                    "missing_api_keys": 0,
                    "all_brains_original": True,
                    "fallback_warnings": [],
                    "error": str(e2)[:200],
                },
            }
