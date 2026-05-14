"""Preference API — PAHF Preference Learning endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from mamoun.api.deps import require_auth
from mamoun.preference import PAHFLearningEngine

router = APIRouter(prefix="/preference", tags=["preference"])

_engine: Optional[PAHFLearningEngine] = None


def get_engine() -> PAHFLearningEngine:
    global _engine
    if _engine is None:
        _engine = PAHFLearningEngine()
    return _engine


class ClarifyRequest(BaseModel):
    action: dict


class GroundRequest(BaseModel):
    action: dict


class FeedbackRequest(BaseModel):
    action: dict
    user_response: dict


class StorePreferenceRequest(BaseModel):
    category: str
    key: str
    value: object
    confidence: float = 0.5
    source: str = "explicit"


@router.get("/status")
async def preference_status():
    return get_engine().get_status()


@router.post("/clarify", dependencies=[Depends(require_auth)])
async def should_clarify(req: ClarifyRequest):
    should, question = get_engine().should_clarify(req.action)
    return {"should_clarify": should, "question": question}


@router.post("/ground", dependencies=[Depends(require_auth)])
async def ground_in_preferences(req: GroundRequest):
    grounded = get_engine().ground_in_preferences(req.action)
    return {"grounded_action": grounded}


@router.post("/feedback", dependencies=[Depends(require_auth)])
async def learn_from_feedback(req: FeedbackRequest):
    get_engine().learn_from_feedback(req.action, req.user_response)
    return {"learned": True}


@router.post("/store", dependencies=[Depends(require_auth)])
async def store_preference(req: StorePreferenceRequest):
    get_engine().memory.store_preference(
        category=req.category,
        key=req.key,
        value=req.value,
        confidence=req.confidence,
        source=req.source,
    )
    return {"stored": True}


@router.get("/preferences")
async def get_preferences(category: Optional[str] = None):
    return {"preferences": get_engine().memory.get_all_preferences(category)}
