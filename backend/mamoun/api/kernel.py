"""
BABSHARQII v18.0 — Kernel API
واجهة برمجة النواة — نقطة الدخول الرئيسية لمأمون الحي

This route provides direct access to the MamounKernel — the living core.
Includes: Chat, Brains, Skills, Working Memory, Capability Router, Tools, Projects
"""

import time
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from mamoun.core.mamoun_kernel import get_kernel, KernelEvent, EventType, EventPriority
from mamoun.core.llm_client import get_llm_client
from mamoun.api.deps import require_auth

# M-5: Rate limiting for auth-sensitive endpoints
from fastapi import Request
from mamoun.api.rate_limiter import limiter

logger = logging.getLogger("mamoun.api.kernel")

router = APIRouter(prefix="/kernel", tags=["kernel"])


class ChatRequest(BaseModel):
    message: str
    model: str = "auto"  # auto = kernel decides
    context: dict = {}


class ChatResponse(BaseModel):
    response: str
    confidence: float
    winning_brain: str
    escalation: str
    concerns: list = []
    needs_approval: bool = False
    needs_user_input: bool = False
    # v17.0: Real deliberation data
    brain_responses: dict = {}
    consensus_level: float = 0.0
    cjs: float = 0.0
    conflict_detected: bool = False
    mirror_reflection: str = ""
    query_type: str = ""


@router.post("/chat", dependencies=[Depends(require_auth)])
@limiter.limit("10/minute")
async def kernel_chat(request: Request, req: ChatRequest):
    """
    Main chat endpoint — goes through the full consciousness pipeline.
    Perceive → Brain Competition → Global Workspace → Reflexion → Execute → Learn
    """
    kernel = get_kernel()

    # Ensure brains are registered
    if not kernel._brains:
        _register_brains(kernel)

    try:
        result = await kernel.chat(
            message=req.message,
            context=req.context,
        )
        # Get deliberation data if available
        deliberation = getattr(kernel, '_last_deliberation', None)
        brain_responses = {}
        consensus_level = 0.0
        cjs = 0.0
        conflict_detected = False
        mirror_reflection = ""
        query_type = ""

        if deliberation:
            brain_responses = {
                bid: {
                    "response": resp.get("response", "")[:300],
                    "confidence": resp.get("confidence", 0),
                    "stance": resp.get("stance", "neutral"),
                    "model_used": resp.get("model_used", ""),
                }
                for bid, resp in deliberation.brain_responses.items()
            }
            consensus_level = deliberation.consensus_level
            cjs = deliberation.critical_junction_score
            conflict_detected = deliberation.conflict_detected
            mirror_reflection = deliberation.mirror_reflection[:500]
            query_type = deliberation.query_type

        return ChatResponse(
            response=result.get("response", ""),
            confidence=result.get("confidence", 0),
            winning_brain=result.get("winning_brain", ""),
            escalation=result.get("escalation", ""),
            concerns=result.get("concerns", result.get("review_concerns", [])),
            needs_approval=result.get("needs_approval", False),
            needs_user_input=result.get("needs_user_input", False),
            brain_responses=brain_responses,
            consensus_level=consensus_level,
            cjs=cjs,
            conflict_detected=conflict_detected,
            mirror_reflection=mirror_reflection,
            query_type=query_type,
        )
    except Exception as e:
        logger.error("Kernel chat error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", dependencies=[Depends(require_auth)])
@limiter.limit("20/minute")
async def kernel_status(request: Request):
    """Get kernel status — the heartbeat of the system."""
    kernel = get_kernel()
    return kernel.get_status()


@router.post("/think", dependencies=[Depends(require_auth)])
@limiter.limit("10/minute")
async def kernel_think(request: Request, req: ChatRequest):
    """
    Quick think — bypasses the full pipeline, goes directly to LLM.
    Useful for simple questions that don't need multi-brain deliberation.
    """
    llm = get_llm_client()
    response = await llm.think(
        prompt=req.message,
        model="glm-5.1",
        temperature=0.7,
    )
    return {
        "response": response.text,
        "model": response.model,
        "confidence": 0.7,
        "latency_ms": response.latency_ms,
    }


@router.post("/reflect", dependencies=[Depends(require_auth)])
async def kernel_reflect(request: Request, req: ChatRequest):
    """
    Reflexion endpoint — deep metacognitive analysis.
    The system thinks about its own thinking.
    """
    llm = get_llm_client()
    response = await llm.reflect(
        content=req.context.get("content", req.message),
        question=req.message,
    )
    return {
        "reflection": response.text,
        "model": response.model,
        "latency_ms": response.latency_ms,
    }


@router.get("/brains", dependencies=[Depends(require_auth)])
@limiter.limit("20/minute")
async def list_living_brains(request: Request):
    """List all registered living brains with their current state."""
    kernel = get_kernel()
    if not kernel._brains:
        _register_brains(kernel)

    brains = {}
    for brain_id, brain in kernel._brains.items():
        brains[brain_id] = brain.state.to_dict()

    return {
        "brains": brains,
        "total": len(brains),
        "workspace": kernel.workspace.get_status(),
    }


@router.post("/brains/{brain_id}/activate", dependencies=[Depends(require_auth)])
async def activate_brain(brain_id: str):
    """Activate a specific brain."""
    kernel = get_kernel()
    brain = kernel._brains.get(brain_id)
    if not brain:
        raise HTTPException(status_code=404, detail=f"Brain '{brain_id}' not found")
    brain.activate()
    return {"status": "activated", "brain_id": brain_id}


@router.post("/brains/{brain_id}/deactivate", dependencies=[Depends(require_auth)])
async def deactivate_brain(brain_id: str):
    """Deactivate a specific brain."""
    kernel = get_kernel()
    brain = kernel._brains.get(brain_id)
    if not brain:
        raise HTTPException(status_code=404, detail=f"Brain '{brain_id}' not found")
    brain.deactivate()
    return {"status": "deactivated", "brain_id": brain_id}


@router.get("/workspace", dependencies=[Depends(require_auth)])
async def workspace_status():
    """Get the Global Workspace status — what's currently in the spotlight."""
    kernel = get_kernel()
    ws = kernel.workspace
    current = ws.current
    return {
        "current": {
            "id": current.id if current else None,
            "winning_brain": current.winning_brain if current else None,
            "confidence": current.confidence if current else 0,
            "content_preview": current.content[:200] if current else None,
        },
        "history_size": len(ws.history),
        "recent_winners": [
            {"brain": e.winning_brain, "confidence": e.confidence}
            for e in ws.history[-10:]
        ],
    }


@router.get("/llm-stats")
async def llm_stats():
    """Get LLM usage statistics."""
    llm = get_llm_client()
    return llm.get_stats()


# ─────────────────────────────────────────────────────────────────────────────
# v18.0: Skills & Working Memory endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/skills")
async def list_skills():
    """List all registered skills."""
    kernel = get_kernel()
    if not hasattr(kernel, '_skill_executor'):
        raise HTTPException(status_code=503, detail="SkillExecutor not initialized")
    return {
        "skills": kernel._skill_executor.list_skills(),
        "total": len(kernel._skill_executor._skills),
        "stats": kernel._skill_executor.get_stats(),
    }


@router.post("/skills/{skill_id}/execute", dependencies=[Depends(require_auth)])
async def execute_skill(skill_id: str, req: ChatRequest):
    """Execute a specific skill directly."""
    kernel = get_kernel()
    if not hasattr(kernel, '_skill_executor'):
        raise HTTPException(status_code=503, detail="SkillExecutor not initialized")

    skill = kernel._skill_executor.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

    if skill.requires_approval:
        return {
            "status": "requires_approval",
            "skill_id": skill_id,
            "message": f"المهارة '{skill.name_ar}' تتطلب موافقة قبل التنفيذ",
        }

    result = await kernel._skill_executor.execute(
        skill_id=skill_id,
        message=req.message,
        context=req.context,
    )
    return result.to_dict()


@router.get("/working-memory")
async def working_memory_status():
    """Get working memory status."""
    kernel = get_kernel()
    if not hasattr(kernel, '_working_memory'):
        raise HTTPException(status_code=503, detail="WorkingMemory not initialized")
    return kernel._working_memory.get_status()


@router.get("/capabilities")
async def capability_stats():
    """Get capability routing statistics."""
    kernel = get_kernel()
    if not hasattr(kernel, '_capability_router'):
        raise HTTPException(status_code=503, detail="CapabilityRouter not initialized")
    return kernel._capability_router.get_stats()


# ─────────────────────────────────────────────────────────────────────────────
# v18.0: Real Tools & Project Orchestrator endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/tools")
async def list_real_tools():
    """List all available real tools."""
    from mamoun.core.real_tools import get_real_tools
    tools = get_real_tools()
    return {"tools": tools.list_tools(), "initialized": tools._initialized}


@router.post("/tools/{tool_name}/execute", dependencies=[Depends(require_auth)])
async def execute_real_tool(tool_name: str, req: ChatRequest):
    """Execute a real tool — web search, image gen, video analysis, etc."""
    from mamoun.core.real_tools import get_real_tools
    tools = get_real_tools()
    
    # Map tool_name to kwargs
    tool_kwargs = {"message": req.message}
    
    if tool_name == "web_search":
        tool_kwargs = {"query": req.message, "num_results": req.context.get("num_results", 10)}
    elif tool_name == "image_gen":
        tool_kwargs = {"prompt": req.message, "size": req.context.get("size", "1024x1024")}
    elif tool_name == "video_analysis":
        tool_kwargs = {"video_path": req.context.get("video_path", req.message), "question": req.message, "analysis_type": req.context.get("analysis_type", "comprehensive")}
    elif tool_name == "n8n_workflow":
        tool_kwargs = {"description": req.message}
    elif tool_name == "blender":
        tool_kwargs = {"script_description": req.message}
    elif tool_name == "server_control":
        tool_kwargs = {"command": req.message, "working_dir": req.context.get("working_dir", "")}
    elif tool_name == "code_gen":
        tool_kwargs = {"description": req.message, "language": req.context.get("language", "python"), "execute": req.context.get("execute", True)}
    elif tool_name == "system_info":
        tool_kwargs = {}
    
    result = await tools.call_tool(tool_name, **tool_kwargs)
    return {
        "success": result.success,
        "tool_name": result.tool_name,
        "output": result.output[:5000],
        "data": result.data,
        "artifacts": result.artifacts,
        "error": result.error,
        "duration_ms": result.duration_ms,
    }


@router.post("/projects/start", dependencies=[Depends(require_auth)])
async def start_project(req: ChatRequest):
    """Start a new project from an idea — research runs automatically."""
    from mamoun.core.project_orchestrator import get_project_orchestrator
    from mamoun.core.real_tools import get_real_tools
    from mamoun.core.llm_client import get_llm_client
    
    tools = get_real_tools()
    llm = get_llm_client()
    orchestrator = get_project_orchestrator(llm_client=llm, real_tools=tools)
    
    project = await orchestrator.start_project(idea=req.message)
    return {
        "project_id": project.id,
        "name": project.name,
        "phase": project.phase.value,
        "message": f"بدأ المشروع '{project.name}' — جاري البحث...",
    }


@router.post("/projects/{project_id}/approve", dependencies=[Depends(require_auth)])
async def approve_project(project_id: str, req: ChatRequest = None):
    """Approve current phase and advance to next."""
    from mamoun.core.project_orchestrator import get_project_orchestrator
    from mamoun.core.real_tools import get_real_tools
    from mamoun.core.llm_client import get_llm_client
    
    tools = get_real_tools()
    llm = get_llm_client()
    orchestrator = get_project_orchestrator(llm_client=llm, real_tools=tools)
    
    project = await orchestrator.approve_and_continue(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"مشروع غير موجود: {project_id}")
    
    return {
        "project_id": project.id,
        "name": project.name,
        "phase": project.phase.value,
        "steps": [
            {"id": s.id, "name_ar": s.name_ar, "status": s.status}
            for s in project.steps
        ],
    }


@router.get("/projects")
async def list_projects():
    """List all projects."""
    from mamoun.core.project_orchestrator import get_project_orchestrator
    from mamoun.core.real_tools import get_real_tools
    from mamoun.core.llm_client import get_llm_client
    
    tools = get_real_tools()
    llm = get_llm_client()
    orchestrator = get_project_orchestrator(llm_client=llm, real_tools=tools)
    return {"projects": orchestrator.list_projects()}


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details."""
    from mamoun.core.project_orchestrator import get_project_orchestrator
    from mamoun.core.real_tools import get_real_tools
    from mamoun.core.llm_client import get_llm_client
    
    tools = get_real_tools()
    llm = get_llm_client()
    orchestrator = get_project_orchestrator(llm_client=llm, real_tools=tools)
    
    project = orchestrator.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"مشروع غير موجود: {project_id}")
    
    return {
        "id": project.id,
        "name": project.name,
        "phase": project.phase.value,
        "steps": [
            {
                "id": s.id,
                "name_ar": s.name_ar,
                "status": s.status,
                "duration_ms": s.duration_ms,
            }
            for s in project.steps
        ],
        "artifacts": project.artifacts,
        "notifications": project.notifications[-5:],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Register all living brains
# ─────────────────────────────────────────────────────────────────────────────

def _register_brains(kernel):
    """Register all 5 living brains with the kernel."""
    from mamoun.brains.living_brains import (
        NeuralBrain,
        CausalBrain,
        SymbolicBrain,
        BayesianBrain,
        WorldModelBrain,
    )
    from mamoun.core.llm_client import get_llm_client

    llm = get_llm_client()

    brains = [
        NeuralBrain(llm_client=llm),
        CausalBrain(llm_client=llm),
        SymbolicBrain(llm_client=llm),
        BayesianBrain(llm_client=llm),
        WorldModelBrain(llm_client=llm),
    ]

    for brain in brains:
        kernel.register_brain(brain.state.id, brain)


# ─────────────────────────────────────────────────────────────────────────────
# v18.0: Self-Modification endpoints — واجهة تعديل الذات
# ─────────────────────────────────────────────────────────────────────────────

class ProposeModificationRequest(BaseModel):
    target_file: str
    description: str


@router.get("/self-modify/history", dependencies=[Depends(require_auth)])
async def self_modify_history():
    """الحصول على سجل التعديلات — list modification history."""
    from mamoun.core.self_modifier import get_self_modifier
    modifier = get_self_modifier()
    records = await modifier.get_history()
    return {
        "history": [r.to_dict() for r in records],
        "total": len(records),
    }


@router.post("/self-modify/propose", dependencies=[Depends(require_auth)])
async def self_modify_propose(req: ProposeModificationRequest):
    """اقتراح تعديل جديد — propose a new self-modification."""
    from mamoun.core.self_modifier import get_self_modifier
    modifier = get_self_modifier()

    proposal = await modifier.propose_modification(
        target_file=req.target_file,
        description=req.description,
    )

    if proposal.status == "rejected":
        return {
            "status": "rejected",
            "proposal": proposal.to_dict(),
            "message": "تم رفض المقترح — تحقق من validation_errors",
        }

    # تشغيل التحقق تلقائياً
    validation = await modifier.validate_modification(proposal)

    return {
        "status": proposal.status,
        "proposal": proposal.to_dict(),
        "validation": validation.to_dict(),
        "message": (
            "تم إنشاء المقترح وهو بانتظار المراجعة"
            if proposal.status == "pending"
            else "تم إنشاء المقترح وتمت الموافقة المبدئية"
        ),
    }


@router.post("/self-modify/{modification_id}/approve", dependencies=[Depends(require_auth)])
async def self_modify_approve(modification_id: str):
    """الموافقة على تعديل وتطبيقه — approve and apply a modification."""
    from mamoun.core.self_modifier import get_self_modifier
    modifier = get_self_modifier()

    proposal = modifier.get_proposal(modification_id)
    if not proposal:
        raise HTTPException(status_code=404, detail=f"التعديل غير موجود: {modification_id}")

    # الموافقة
    approved = modifier.approve_proposal(modification_id, approver="human")
    if not approved:
        raise HTTPException(status_code=400, detail="فشل الموافقة — تحقق من حالة التعديل")

    # اختبار في Sandbox
    sandbox_result = await modifier.test_in_sandbox(proposal)

    if not sandbox_result.get("success", False):
        return {
            "status": "sandbox_failed",
            "proposal_id": modification_id,
            "sandbox_result": sandbox_result,
            "message": "فشل اختبار Sandbox — لم يتم تطبيق التعديل",
        }

    # تطبيق التعديل
    apply_result = await modifier.apply_modification(proposal)

    return {
        "status": "applied" if apply_result.success else "apply_failed",
        "proposal_id": modification_id,
        "apply_result": apply_result.to_dict(),
        "sandbox_result": sandbox_result,
        "message": (
            "تم تطبيق التعديل بنجاح"
            if apply_result.success
            else f"فشل التطبيق: {apply_result.error}"
        ),
    }


@router.post("/self-modify/{modification_id}/reject", dependencies=[Depends(require_auth)])
async def self_modify_reject(modification_id: str):
    """رفض تعديل — reject a proposed modification."""
    from mamoun.core.self_modifier import get_self_modifier
    modifier = get_self_modifier()

    rejected = modifier.reject_proposal(modification_id)
    if not rejected:
        raise HTTPException(status_code=400, detail="فشل الرفض — تحقق من حالة التعديل")

    return {
        "status": "rejected",
        "proposal_id": modification_id,
        "message": "تم رفض التعديل",
    }


@router.post("/self-modify/{modification_id}/rollback", dependencies=[Depends(require_auth)])
async def self_modify_rollback(modification_id: str):
    """التراجع عن تعديل — rollback a previously applied modification."""
    from mamoun.core.self_modifier import get_self_modifier
    modifier = get_self_modifier()

    rollback_result = await modifier.rollback(modification_id)

    if not rollback_result.success:
        raise HTTPException(
            status_code=400,
            detail=f"فشل التراجع: {rollback_result.error}",
        )

    return {
        "status": "rolled_back",
        "rollback_result": rollback_result.to_dict(),
        "message": "تم التراجع عن التعديل واستعادة الكود الأصلي",
    }


@router.get("/self-modify/analyze", dependencies=[Depends(require_auth)])
async def self_modify_analyze():
    """تحليل ذاتي — get self-analysis of the system's codebase."""
    from mamoun.core.self_modifier import get_self_modifier
    modifier = get_self_modifier()

    analysis = await modifier.analyze_self()
    return {
        "analysis": analysis.to_dict(),
        "dashboard_config": modifier._rebuild_dashboard_config(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# v18.0: Build Project & Auto-Evolve endpoints
# ─────────────────────────────────────────────────────────────────────────────

class BuildProjectRequest(BaseModel):
    description: str
    project_type: str = "web"  # web, mobile, api, script, fullstack
    language: str = "auto"  # auto, python, typescript, etc.
    auto_approve: bool = False  # Skip approval gates for development


@router.post("/build-project", dependencies=[Depends(require_auth)])
async def build_project(req: BuildProjectRequest):
    """
    بناء مشروع كامل من وصف — Build a complete project from a description.
    
    This is the ONE-SHOT project builder. It:
    1. Researches the market/domain
    2. Generates a complete project plan
    3. Writes ALL files using LLM + CodeGenTool
    4. Returns the project with all artifacts
    
    Unlike /projects/start (which is async), this runs synchronously and returns
    the complete project in one response.
    """
    import asyncio
    from mamoun.core.llm_client import get_llm_client
    from mamoun.core.real_tools import get_real_tools
    
    llm = get_llm_client()
    tools = get_real_tools()
    start_time = time.time()
    
    # Step 1: Generate project specification using LLM
    spec_response = await llm.think(
        prompt=f"""أنت مهندس برمجيات خبير. أنشئ مواصفات مشروع كامل بناءً على هذا الوصف:

{req.description}

نوع المشروع: {req.project_type}
اللغة المطلوبة: {req.language}

أنشئ مواصفات مفصلة بصيغة JSON:
{{
  "project_name": "اسم المشروع بالإنجليزية",
  "project_name_ar": "اسم المشروع بالعربية",
  "description": "وصف تفصيلي",
  "tech_stack": {{
    "frontend": "...",
    "backend": "...",
    "database": "...",
    "deployment": "..."
  }},
  "folder_structure": {{
    "path/to/file.ext": "وصف محتوى الملف"
  }},
  "features": ["feature1", "feature2"],
  "pages": [
    {{"name": "اسم الصفحة", "description": "وصف الصفحة", "components": ["comp1", "comp2"]}}
  ],
  "api_endpoints": [
    {{"method": "GET", "path": "/api/...", "description": "..."}}
  ],
  "database_schema": {{
    "table_name": {{"columns": [...]}}
  }}
}}""",
        system="أنت مهندس برمجيات محترف. أنشئ مواصفات JSON كاملة ومفصلة لمشروع حقيقي.",
        model="glm-5.1",
        temperature=0.4,
        json_mode=True,
    )
    
    spec = spec_response.extract_json()
    if not spec:
        # Fallback spec
        spec = {
            "project_name": req.description[:30].replace(" ", "_"),
            "project_name_ar": req.description[:50],
            "description": req.description,
            "tech_stack": {"frontend": "Next.js + Tailwind CSS", "backend": "Python FastAPI", "database": "SQLite"},
            "folder_structure": {},
            "features": ["core_functionality"],
            "pages": [],
            "api_endpoints": [],
            "database_schema": {},
        }
    
    project_name = spec.get("project_name", "project")
    
    # Step 2: Generate code files using CodeGenTool
    generated_files = []
    folder_structure = spec.get("folder_structure", {})
    
    # If no folder structure specified, generate a default one
    if not folder_structure:
        folder_structure = {
            "README.md": f"# {project_name}",
            "package.json": "Node.js package configuration",
            "src/app/page.tsx": "Main page component",
            "src/app/layout.tsx": "Root layout",
            "src/app/globals.css": "Global styles",
        }
    
    for file_path, file_description in folder_structure.items():
        try:
            # Determine language from extension
            ext = file_path.rsplit(".", 1)[-1] if "." in file_path else "txt"
            lang_map = {
                "tsx": "typescript", "ts": "typescript", "jsx": "javascript",
                "js": "javascript", "py": "python", "css": "css",
                "json": "json", "md": "markdown", "html": "html",
                "yaml": "yaml", "yml": "yaml", "sql": "sql",
            }
            language = lang_map.get(ext, "text")
            
            result = await tools.call_tool(
                "code_gen",
                description=f"أنشئ ملف {file_path} لمشروع {project_name}: {file_description}\n\nالمواصفات: {spec.get('description', '')}",
                language=language,
                execute=False,  # Don't execute, just generate
            )
            
            if result.success:
                generated_files.append({
                    "path": file_path,
                    "description": file_description,
                    "generated": True,
                    "size": len(result.output) if result.output else 0,
                })
            else:
                generated_files.append({
                    "path": file_path,
                    "description": file_description,
                    "generated": False,
                    "error": result.error[:200] if result.error else "unknown",
                })
        except Exception as e:
            generated_files.append({
                "path": file_path,
                "description": file_description,
                "generated": False,
                "error": str(e)[:200],
            })
    
    # Step 3: Generate main pages if specified
    pages_generated = []
    for page in spec.get("pages", []):
        try:
            page_result = await tools.call_tool(
                "code_gen",
                description=f"""أنشئ صفحة React/Next.js كاملة لـ: {page.get('name', 'Page')}
الوصف: {page.get('description', '')}
المكونات: {', '.join(page.get('components', []))}
المشروع: {project_name}
التقنيات: Tailwind CSS + React hooks

اكتب كود React كامل مع Tailwind CSS. الصفحة يجب أن تكون متجاوبة (responsive) وجاهزة للاستخدام.""",
                language="typescript",
                execute=False,
            )
            pages_generated.append({
                "page": page.get("name", ""),
                "generated": page_result.success,
            })
        except Exception as e:
            pages_generated.append({
                "page": page.get("name", ""),
                "generated": False,
                "error": str(e)[:200],
            })
    
    duration_ms = (time.time() - start_time) * 1000
    success_count = sum(1 for f in generated_files if f.get("generated"))
    
    return {
        "status": "completed",
        "project_name": project_name,
        "project_name_ar": spec.get("project_name_ar", ""),
        "specification": spec,
        "generated_files": generated_files,
        "pages_generated": pages_generated,
        "total_files": len(generated_files),
        "successful_files": success_count,
        "success_rate": success_count / max(1, len(generated_files)),
        "duration_ms": round(duration_ms),
        "message": f"تم بناء مشروع '{project_name}' — {success_count}/{len(generated_files)} ملف تم إنشاؤه بنجاح",
    }


@router.post("/evolve", dependencies=[Depends(require_auth)])
async def trigger_evolution():
    """
    تفعيل دورة التطور الذاتي — Trigger a self-evolution cycle.
    
    This runs the full self-programming loop:
    1. Collect performance data from all brains
    2. Run MetaAgent to detect issues
    3. Propose code modifications
    4. Return proposed modifications for approval
    """
    kernel = get_kernel()
    
    # Collect performance data from living brains
    performance_data = {}
    for brain_id, brain in kernel._brains.items():
        try:
            performance_data[brain_id] = {
                "task_type": brain.get_specialty(),
                "confidence": {
                    "current": brain.state.confidence,
                    "expected": 0.7,
                },
                "success_rate": {
                    "current": brain.state.successful_interactions / max(1, brain.state.total_interactions),
                    "expected": 0.85,
                },
            }
        except Exception as e:
            performance_data[brain_id] = {"error": str(e)[:200]}
    
    # Run self-programming cycle
    try:
        from mamoun.evolution.self_programming_loop import SelfProgrammingLoop
        loop = SelfProgrammingLoop()
        result = await loop.run_cycle(performance_data)
        
        return {
            "status": "evolution_cycle_complete",
            "performance_data": performance_data,
            "cycle_result": result,
            "message": "تم تشغيل دورة التطور — تحقق من /kernel/self-modify/history للتعديلات المقترحة",
        }
    except Exception as e:
        return {
            "status": "evolution_failed",
            "error": str(e),
            "performance_data": performance_data,
            "message": f"فشل التطور: {str(e)}",
        }


@router.post("/self-modify/auto-improve", dependencies=[Depends(require_auth)])
async def auto_improve():
    """
    تحسين تلقائي — One-click self-improvement cycle.
    
    The system:
    1. Analyzes its own codebase
    2. Identifies the weakest areas
    3. Proposes improvements
    4. Returns proposals for human approval
    
    This is the FULL self-modification pipeline in one endpoint.
    """
    from mamoun.core.self_modifier import get_self_modifier
    modifier = get_self_modifier()
    
    # Step 1: Self-analysis
    analysis = await modifier.analyze_self()
    
    # Step 2: Get top improvement suggestions
    suggestions = analysis.suggested_improvements[:3]  # Top 3 only
    
    # Step 3: Propose modifications for each suggestion
    proposals = []
    for suggestion in suggestions:
        # Parse suggestion to find target file
        # Format: "تحسين X في ملف Y: الوصف"
        target_file = "mamoun/core/skill_executor.py"  # Default target
        
        # Try to extract file from suggestion
        if "ملف" in suggestion or "file" in suggestion.lower():
            parts = suggestion.split("ملف")
            if len(parts) > 1:
                file_hint = parts[1].split(":")[0].strip()
                # Try to find matching file
                from pathlib import Path
                backend_path = Path(__file__).parent.parent.parent
                for py_file in backend_path.rglob("*.py"):
                    if file_hint.lower() in py_file.name.lower():
                        target_file = str(py_file.relative_to(backend_path))
                        break
        
        try:
            proposal = await modifier.propose_modification(
                target_file=target_file,
                description=suggestion,
            )
            proposals.append({
                "id": proposal.id,
                "target_file": proposal.target_file,
                "description": suggestion,
                "status": proposal.status,
                "safety_score": proposal.safety_score,
            })
        except Exception as e:
            proposals.append({
                "target_file": target_file,
                "description": suggestion,
                "status": "error",
                "error": str(e)[:200],
            })
    
    return {
        "status": "analysis_complete",
        "analysis": {
            "total_files": analysis.total_files,
            "total_lines": analysis.total_lines,
            "total_functions": analysis.total_functions,
            "health_score": analysis.health_score,
            "complexity_score": analysis.complexity_score,
        },
        "proposals": proposals,
        "total_suggestions": len(suggestions),
        "message": f"تم تحليل النظام — {len(proposals)} مقترحات للتحسين. استخدم /kernel/self-modify/{{id}}/approve للموافقة",
    }
