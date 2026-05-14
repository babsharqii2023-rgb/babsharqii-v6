"""A2UI API — Dynamic UI Generation endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from mamoun.api.deps import require_auth
from mamoun.a2ui import DynamicUIGenerator

router = APIRouter(prefix="/a2ui", tags=["a2ui"])

_generator: Optional[DynamicUIGenerator] = None


def get_generator() -> DynamicUIGenerator:
    global _generator
    if _generator is None:
        _generator = DynamicUIGenerator()
    return _generator


class GenerateSectionRequest(BaseModel):
    section_name: str
    section_type: str
    fields: list[dict] = []


class GeneratePermissionRequest(BaseModel):
    request: dict


@router.get("/status")
async def a2ui_status():
    return get_generator().get_status()


@router.post("/generate/section", dependencies=[Depends(require_auth)])
async def generate_section(req: GenerateSectionRequest):
    messages = get_generator().generate_task_section(
        section_name=req.section_name,
        section_type=req.section_type,
        fields=req.fields,
    )
    return {
        "section_type": req.section_type,
        "messages": [m.to_jsonl() for m in messages],
        "message_count": len(messages),
    }


@router.post("/generate/permission", dependencies=[Depends(require_auth)])
async def generate_permission(req: GeneratePermissionRequest):
    messages = get_generator().generate_permission_request(req.request)
    return {
        "messages": [m.to_jsonl() for m in messages],
    }


@router.post("/generate/evolution-status", dependencies=[Depends(require_auth)])
async def generate_evolution_status():
    from mamoun.hyperagent import CurriculumController
    status = CurriculumController().get_status()
    messages = get_generator().generate_evolution_status(status)
    return {
        "messages": [m.to_jsonl() for m in messages],
    }
