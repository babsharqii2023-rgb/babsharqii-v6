"""
BABSHARQII v40.0 — Capability Assessor API
مسار API لتقييم القدرات الذاتية
"""

from fastapi import APIRouter

from mamoun.core.capability_assessor import CapabilityAssessor

router = APIRouter(prefix="/capabilities", tags=["capability-assessor"])


def _get_assessor() -> CapabilityAssessor:
    """Get or create a CapabilityAssessor instance with available components."""
    llm_client = None
    brain_router = None
    self_modifier = None

    try:
        from mamoun.core.llm_client import get_llm_client
        llm_client = get_llm_client()
    except Exception:
        pass

    try:
        from mamoun.brains.brain_router import get_brain_router
        brain_router = get_brain_router()
    except Exception:
        pass

    try:
        from mamoun.core.self_modifier import SelfModifier
        self_modifier = SelfModifier()
    except Exception:
        pass

    return CapabilityAssessor(
        llm_client=llm_client,
        brain_router=brain_router,
        self_modifier=self_modifier,
    )


@router.get("/assess")
async def assess_capabilities():
    """
    تقييم كامل للقدرات — runs full assessment and returns detailed report.

    Returns:
    {
        "overall_fusion_percent": 55-100,
        "bridges": {...},
        "brains": {...},
        "api_keys": {...},
        "capabilities": [...],
        "missing_capabilities": [...],
        "can_do_summary": "...",
        "recommendations": [...]
    }
    """
    assessor = _get_assessor()
    result = await assessor.assess()
    return result
