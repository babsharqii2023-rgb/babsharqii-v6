"""Hyperagent API — DGM-H Architecture endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from mamoun.api.deps import require_auth
from mamoun.hyperagent import HyperagentLoop, MetaAgent, SupraMetaAgent

router = APIRouter(prefix="/hyperagent", tags=["hyperagent"])

# Singletons
_hyperagent_loop: Optional[HyperagentLoop] = None
_meta_agent: Optional[MetaAgent] = None
_supra_meta: Optional[SupraMetaAgent] = None


def get_loop() -> HyperagentLoop:
    global _hyperagent_loop
    if _hyperagent_loop is None:
        _hyperagent_loop = HyperagentLoop()
    return _hyperagent_loop


def get_meta() -> MetaAgent:
    global _meta_agent
    if _meta_agent is None:
        _meta_agent = MetaAgent()
    return _meta_agent


def get_supra() -> SupraMetaAgent:
    global _supra_meta
    if _supra_meta is None:
        _supra_meta = SupraMetaAgent()
    return _supra_meta


class CycleRequest(BaseModel):
    current_performance: float = 0.5
    domain: str = "general"
    task_result: Optional[dict] = None
    resource_usage: Optional[dict] = None


class EvaluateRequest(BaseModel):
    current_performance: float = 0.5
    domain: str = "general"
    recent_improvements: list = []
    resource_usage: Optional[dict] = None


@router.get("/status")
async def hyperagent_status():
    """Get full DGM-H architecture status."""
    return get_loop().get_full_status()


@router.post("/cycle", dependencies=[Depends(require_auth)])
async def run_cycle(req: CycleRequest):
    """Run one DGM-H cycle."""
    loop = get_loop()
    return await loop.run_cycle(
        task_result=req.task_result,
        current_performance=req.current_performance,
        domain=req.domain,
        resource_usage=req.resource_usage or {},
    )


@router.get("/meta/status")
async def meta_status():
    """Get MetaAgent status."""
    return get_meta().get_status()


@router.get("/meta/params")
async def meta_params():
    """Get current meta-parameters."""
    return get_meta().get_meta_params()


@router.get("/meta/history")
async def meta_history(limit: int = 50):
    """Get meta-modification history."""
    return {"history": get_meta().get_meta_history(limit)}


@router.post("/supra/evaluate", dependencies=[Depends(require_auth)])
async def supra_evaluate(req: EvaluateRequest):
    """Evaluate whether improvement is necessary."""
    decision, reasoning, context = get_supra().evaluate_improvement_necessity(
        current_performance=req.current_performance,
        domain=req.domain,
        recent_improvements=req.recent_improvements,
        resource_usage=req.resource_usage or {},
    )
    return {
        "decision": decision.value,
        "reasoning": reasoning,
        "context": context,
    }


@router.get("/supra/status")
async def supra_status():
    """Get SupraMetaAgent status."""
    return get_supra().get_status()


@router.get("/curriculum/status")
async def curriculum_status():
    """Get curriculum controller status."""
    from mamoun.hyperagent import CurriculumController
    return CurriculumController().get_status()


@router.get("/archive/statistics")
async def archive_statistics():
    """Get evolution archive statistics."""
    from mamoun.hyperagent import EvolutionArchive
    return EvolutionArchive().get_statistics()


@router.get("/archive/successful")
async def archive_successful(domain: Optional[str] = None, limit: int = 20):
    """Get successful variants from archive."""
    from mamoun.hyperagent import EvolutionArchive
    archive = EvolutionArchive()
    variants = archive.get_successful_variants(domain, limit)
    return {"variants": [v.to_dict() for v in variants]}
