"""
BABSHARQII v40.0 — Embodiment Routes
Digital Body routes for browser automation and behavioral monitoring (v6.0).
"""

import os as _os
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from mamoun.api.deps import require_auth

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Embodiment Request Models
# =============================================================================

class EmbodimentLaunchRequest(BaseModel):
    url: str = "about:blank"

class EmbodimentClickRequest(BaseModel):
    selector: str

class EmbodimentTypeRequest(BaseModel):
    text: str
    selector: str = ""

class EmbodimentPlanRequest(BaseModel):
    steps: list[dict]


# =============================================================================
# Embodiment Routes
# =============================================================================

# v30: Use module-level singleton to avoid creating new instances per request
_embodiment_controller = None

def _get_controller():
    global _embodiment_controller
    if _embodiment_controller is None:
        from mamoun.core.embodiment_controller_v2 import EmbodimentControllerV2
        _embodiment_controller = EmbodimentControllerV2()
    return _embodiment_controller


@router.get("/embodiment/status", dependencies=[Depends(require_auth)])
async def get_embodiment_status():
    """التحقق من حالة الجسد الرقمي."""
    try:
        controller = _get_controller()
        available = await controller.is_available()
        return {"available": available, "enabled": _os.getenv("MAMOUN_EMBODIMENT_ENABLED", "false").lower() == "true"}
    except Exception as e:
        return {"available": False, "enabled": False, "error": str(e)}


@router.post("/embodiment/launch", dependencies=[Depends(require_auth)])
async def embodiment_launch_browser(request: EmbodimentLaunchRequest):
    """فتح المتصفح في الجسد الرقمي."""
    controller = _get_controller()
    result = await controller.launch_browser(request.url)
    return result.__dict__


@router.post("/embodiment/click", dependencies=[Depends(require_auth)])
async def embodiment_click(request: EmbodimentClickRequest):
    """النقر على عنصر في الجسد الرقمي."""
    controller = _get_controller()
    result = await controller.click(request.selector)
    return result.__dict__


@router.post("/embodiment/type", dependencies=[Depends(require_auth)])
async def embodiment_type(request: EmbodimentTypeRequest):
    """كتابة نص في الجسد الرقمي."""
    controller = _get_controller()
    result = await controller.type_text(request.text, request.selector)
    return result.__dict__


@router.post("/embodiment/screenshot", dependencies=[Depends(require_auth)])
async def embodiment_screenshot():
    """التقاط صورة من الجسد الرقمي."""
    controller = _get_controller()
    result = await controller.screenshot()
    return result.__dict__


@router.post("/embodiment/execute-plan", dependencies=[Depends(require_auth)])
async def embodiment_execute_plan(request: EmbodimentPlanRequest):
    """تنفيذ خطة في الجسد الرقمي."""
    controller = _get_controller()
    plan = await controller.execute_plan(request.steps)
    return {
        "status": plan.status,
        "completed_steps": plan.completed_steps,
        "total_steps": len(plan.steps),
        "failed_step": plan.failed_step,
    }


@router.get("/embodiment/behavior-report", dependencies=[Depends(require_auth)])
async def embodiment_behavior_report():
    """تقرير سلوكي من الجسد الرقمي."""
    controller = _get_controller()
    report = await controller.monitor_behavior()
    return report.__dict__
