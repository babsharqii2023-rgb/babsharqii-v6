"""Swarm API — Swarm Formation Agent endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from mamoun.api.deps import require_auth
from mamoun.swarm import SwarmFormationAgent

router = APIRouter(prefix="/swarm", tags=["swarm"])

_swarm: Optional[SwarmFormationAgent] = None


def get_swarm() -> SwarmFormationAgent:
    global _swarm
    if _swarm is None:
        _swarm = SwarmFormationAgent()
    return _swarm


class FormSwarmRequest(BaseModel):
    goal: str
    available_agents: list[dict] = []


class CompleteSwarmRequest(BaseModel):
    swarm_id: str
    lessons: list[str] = []


@router.get("/status")
async def swarm_status():
    return get_swarm().get_status()


@router.post("/form", dependencies=[Depends(require_auth)])
async def form_swarm(req: FormSwarmRequest):
    swarm = get_swarm().form_swarm(req.goal, req.available_agents)
    return swarm.to_dict()


@router.post("/complete", dependencies=[Depends(require_auth)])
async def complete_swarm(req: CompleteSwarmRequest):
    success = get_swarm().complete_swarm(req.swarm_id, req.lessons)
    return {"success": success}


@router.get("/collective-memory")
async def collective_memory(domain: Optional[str] = None, limit: int = 10):
    swarm = get_swarm()
    lessons = swarm.collective_memory.get_relevant_lessons(domain or "general", limit)
    return {"lessons": lessons}
