"""
BABSHARQII v40.0 — Evolution, Approval, Procedural Memory & Fitness Routes
Phase 3 (Evolution), Phase 4 (Approval), Phase 5 (Procedural Memory), and Fitness routes.
"""

import logging
import time
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from mamoun.api.deps import (
    require_auth,
    mutation_engine,
    evolution_loop,
    approval_gate,
    procedural_memory,
    fitness_evaluator,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Evolution Routes (Phase 3)
# =============================================================================

@router.get("/evolution/current")
async def get_current_genome():
    version = mutation_engine.get_current_version()
    return {"version": version.to_dict(), "genome": version.genome.to_dict()}


@router.get("/evolution/archive")
async def get_evolution_archive():
    archive = mutation_engine.get_archive()
    return {"archive": [v.to_dict() for v in archive], "total": len(archive)}


@router.get("/evolution/tree")
async def get_evolution_tree():
    return mutation_engine.get_evolution_tree()


@router.post("/evolution/run-cycle", dependencies=[Depends(require_auth)])
async def run_evolution_cycle():
    """Run one complete evolution cycle."""
    result = await evolution_loop.run_cycle()
    return {"result": result.__dict__}


@router.get("/evolution/pending")
async def get_pending_mutations():
    return {"mutations": [m.to_dict() for m in mutation_engine.get_pending_mutations()]}


# =============================================================================
# Approval Routes (Phase 4)
# =============================================================================

@router.get("/approval/pending")
async def get_pending_approvals():
    """GET pending approvals — no auth required for dashboard display."""
    return {"pending": await approval_gate.get_pending()}


@router.post("/approval/{request_id}/approve", dependencies=[Depends(require_auth)])
async def approve_request(request_id: str):
    success = await approval_gate.approve(request_id)
    return {"success": success}


@router.post("/approval/{request_id}/reject", dependencies=[Depends(require_auth)])
async def reject_request(request_id: str, reason: str = ""):
    success = await approval_gate.reject(request_id, reason)
    return {"success": success}


@router.post("/approval/auto-deploy", dependencies=[Depends(require_auth)])
async def set_auto_deploy(enabled: bool = False):
    await approval_gate.set_auto_deploy(enabled)
    return {"auto_deploy": enabled}


# =============================================================================
# Procedural Memory Routes (Phase 5)
# =============================================================================

@router.get("/memory/skills")
async def get_all_skills():
    return {"skills": await procedural_memory.get_all_skills()}


@router.post("/memory/extract-skills", dependencies=[Depends(require_auth)])
async def extract_skills():
    new_skills = await procedural_memory.extract_skills()
    return {"extracted": len(new_skills), "skills": [s.to_dict() for s in new_skills]}


# =============================================================================
# Fitness Routes
# =============================================================================

@router.get("/fitness/current")
async def get_current_fitness():
    version = mutation_engine.get_current_version()
    genome_dict = version.genome.to_dict()
    report = fitness_evaluator.evaluate(genome_dict, version.fitness_score)
    return {"fitness": report.to_dict()}


# =============================================================================
# v40.0 Fusion: Self-Improvement & Agent Builder & Project Scaffolder
# =============================================================================

class ImprovementRequest(BaseModel):
    area: str
    description: str = ""
    severity: str = "medium"

class BuildAgentRequest(BaseModel):
    specification: str
    agent_name: Optional[str] = None

class ScaffoldProjectRequest(BaseModel):
    description: str
    target_dir: Optional[str] = None
    tech_stack: Optional[str] = None

class CreateToolRequest(BaseModel):
    tool_description: str
    tool_name: Optional[str] = None


@router.post("/evolution/improve")
async def trigger_improvement(req: ImprovementRequest):
    """تفعيل التحسين الذاتي من المحادثة"""
    try:
        from mamoun.core.mamoun_kernel import get_kernel
        kernel = get_kernel()
        if not hasattr(kernel, '_live_self_modifier') or not kernel._live_self_modifier:
            return {"success": False, "error": "LiveSelfModifier not activated"}
        lsm = kernel._live_self_modifier
        weakness = lsm.report_weakness(req.area, req.description, req.severity, "chat")
        success = await lsm.improve_myself(weakness)
        return {"success": success, "weakness_id": weakness.weakness_id, "area": req.area}
    except Exception as e:
        logger.error(f"Self-improvement failed: {e}")
        return {"success": False, "error": str(e)}


@router.post("/evolution/build-agent")
async def build_agent(req: BuildAgentRequest):
    """بناء أيجنت جديد من المحادثة"""
    try:
        from mamoun.core.mamoun_kernel import get_kernel
        from mamoun.core.llm_client import get_llm_client
        kernel = get_kernel()
        llm = get_llm_client()

        # تصميم الأيجنت بالـ LLM
        design = await llm.think_json(f"""صمّم أيجنت بناءً على: {req.specification}
أجب بصيغة JSON:
{{
    "agent_name": "...",
    "agent_id": "...",
    "description": "...",
    "tools_needed": [],
    "brain_mapping": {{"primary": "neural", "support": []}},
    "schedule": "manual",
    "code": "كود Python الكامل للأيجنت مع class و async def run()"
}}""", model="glm-5.1")

        if not design or "code" not in design:
            return {"success": False, "error": "LLM failed to design agent"}

        # كتابة الملف
        agent_id = design.get("agent_id", f"agent_{int(time.time())}")
        from pathlib import Path
        agents_dir = Path(__file__).parent.parent / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        agent_file = agents_dir / f"{agent_id}.py"
        agent_file.write_text(design["code"], encoding="utf-8")

        # تسجيل في Feature Flags
        try:
            from mamoun.api.feature_flags import feature_flags
            await feature_flags.enable(f"agent_{agent_id}")
        except Exception:
            pass

        return {
            "success": True,
            "agent_id": agent_id,
            "agent_name": design.get("agent_name", agent_id),
            "file": str(agent_file),
            "tools_needed": design.get("tools_needed", []),
        }
    except Exception as e:
        logger.error(f"Agent build failed: {e}")
        return {"success": False, "error": str(e)}


@router.post("/evolution/scaffold")
async def scaffold_project(req: ScaffoldProjectRequest):
    """بناء مشروع كامل من الصفر"""
    try:
        from mamoun.core.mamoun_kernel import get_kernel
        from mamoun.core.llm_client import get_llm_client
        import subprocess
        kernel = get_kernel()
        llm = get_llm_client()

        # تصميم الهيكل بالـ LLM
        structure = await llm.think_json(f"""صمّم هيكل مشروع كامل بناءً على: {req.description}
التقنيات المطلوبة: {req.tech_stack or 'Next.js + TypeScript'}
أجب بصيغة JSON:
{{
    "project_name": "...",
    "tech_stack": [],
    "files": [
        {{"path": "package.json", "content": "..."}},
        {{"path": "src/app/page.tsx", "content": "..."}}
    ],
    "install_commands": [],
    "test_command": ""
}}""", model="glm-5.1")

        if not structure or "files" not in structure:
            return {"success": False, "error": "LLM failed to design project"}

        # إنشاء المجلد والملفات
        target_dir = req.target_dir or f"/home/z/my-project/download/{structure.get('project_name', 'new-project')}"
        from pathlib import Path
        project_dir = Path(target_dir)
        project_dir.mkdir(parents=True, exist_ok=True)

        created_files = []
        for file_info in structure["files"][:50]:  # حد أقصى 50 ملف
            file_path = project_dir / file_info["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file_info.get("content", ""), encoding="utf-8")
            created_files.append(file_info["path"])

        return {
            "success": True,
            "project_name": structure.get("project_name", "new-project"),
            "files_created": len(created_files),
            "files": created_files,
            "target_dir": str(project_dir),
        }
    except Exception as e:
        logger.error(f"Project scaffold failed: {e}")
        return {"success": False, "error": str(e)}


@router.post("/evolution/create-tool")
async def create_tool(req: CreateToolRequest):
    """بناء أداة جديدة حسب الحاجة"""
    try:
        from mamoun.core.mamoun_kernel import get_kernel
        from mamoun.core.llm_client import get_llm_client
        import subprocess
        kernel = get_kernel()
        llm = get_llm_client()

        # تصميم الأداة بالـ LLM
        design = await llm.think_json(f"""صمّم أداة بناءً على: {req.tool_description}
أجب بصيغة JSON:
{{
    "tool_name": "...",
    "tool_id": "...",
    "description": "...",
    "function_signature": "async def tool_name(query: str) -> dict",
    "implementation": "كود Python كامل للوحدة مع import و class/function",
    "required_packages": []
}}""", model="glm-5.1")

        if not design or "implementation" not in design:
            return {"success": False, "error": "LLM failed to design tool"}

        # تثبيت الحزم المطلوبة
        for pkg in design.get("required_packages", [])[:10]:
            try:
                subprocess.run(["pip", "install", pkg, "-q"], capture_output=True, timeout=30)
            except Exception:
                pass

        # كتابة ملف الأداة
        from pathlib import Path
        tool_id = design.get("tool_id", f"tool_{int(time.time())}")
        tools_dir = Path(__file__).parent.parent / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        tool_file = tools_dir / f"{tool_id}.py"
        tool_file.write_text(design["implementation"], encoding="utf-8")

        # Hot reload — حاول استيراد الأداة
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(tool_id, str(tool_file))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception:
            pass

        return {
            "success": True,
            "tool_id": tool_id,
            "tool_name": design.get("tool_name", tool_id),
            "file": str(tool_file),
        }
    except Exception as e:
        logger.error(f"Tool creation failed: {e}")
        return {"success": False, "error": str(e)}
