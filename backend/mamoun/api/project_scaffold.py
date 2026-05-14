"""
BABSHARQII v50.0 — Project Scaffolder API
نقاط الاتصال لمنشئ المشاريع
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

router = APIRouter(prefix="/project-scaffold", tags=["Project Scaffolder"])


class ScaffoldRequest(BaseModel):
    name: str
    description: str
    language: str = "python"
    project_type: str = "python_fastapi"
    structure: Optional[Dict[str, str]] = None
    project_dir: Optional[str] = None


@router.post("/create")
async def scaffold_project(request: ScaffoldRequest):
    """إنشاء مشروع كامل من وصف"""
    try:
        from mamoun.core.project_scaffolder import get_project_scaffolder
        scaffolder = get_project_scaffolder()

        spec = {
            "name": request.name,
            "description": request.description,
            "language": request.language,
            "project_type": request.project_type,
            "structure": request.structure or {},
            "project_dir": request.project_dir or "",
        }

        result = await scaffolder.scaffold_project(spec)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_scaffolder_status():
    """حالة منشئ المشاريع"""
    try:
        from mamoun.core.project_scaffolder import get_project_scaffolder
        scaffolder = get_project_scaffolder()
        return scaffolder.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def get_project_types():
    """أنواع المشاريع المدعومة"""
    return {
        "types": [
            {"id": "python_fastapi", "name": "Python FastAPI", "description": "Web API project with FastAPI"},
            {"id": "python_cli", "name": "Python CLI", "description": "Command-line tool"},
            {"id": "python_data", "name": "Python Data", "description": "Data processing/analysis"},
            {"id": "nextjs_react", "name": "Next.js React", "description": "Modern web application"},
            {"id": "nodejs_api", "name": "Node.js API", "description": "REST API with Express"},
            {"id": "fullstack", "name": "Full Stack", "description": "Next.js + FastAPI combined"},
        ]
    }
