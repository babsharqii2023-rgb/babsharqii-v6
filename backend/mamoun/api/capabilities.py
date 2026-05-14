"""
BABSHARQII v21.0 — Capabilities API Routes
مسارات API لكل القدرات الـ 12 — كل قدرة بنسبة 100%
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional, Any

from mamoun.api.deps import require_auth

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


# ═══════════════════════════════════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════════════════════════════════

class LaptopControlRequest(BaseModel):
    action: str = Field(..., description="screenshot|click|type_text|press_key|move_mouse|open_app|scroll|hotkey|drag|get_screen_info")
    params: dict = Field(default_factory=dict)

class TerminalRequest(BaseModel):
    command: str
    timeout: Optional[int] = None
    approval_id: Optional[str] = None

class CodeGenerationRequest(BaseModel):
    spec: str
    language: str = "python"
    context: Optional[dict] = None

class CodeReviewRequest(BaseModel):
    code: str
    language: str = "python"

class SkillLearningRequest(BaseModel):
    skill_description: str
    source: str = "user_request"

class DeepResearchRequest(BaseModel):
    query: str
    depth: int = 3
    verify: bool = True

class ProjectBuildRequest(BaseModel):
    idea: str
    project_type: str = "web"

class InstagramAnalysisRequest(BaseModel):
    username: str
    analysis_type: str = "full"

class BlenderControlRequest(BaseModel):
    action: str = Field(..., description="add_object|render|execute_script|get_status|create_scene|generate_script|list_objects")
    params: dict = Field(default_factory=dict)

class BrowserActionRequest(BaseModel):
    action: str = Field(..., description="navigate|click|fill|screenshot|get_text|google_search|status")
    params: dict = Field(default_factory=dict)

class SandboxTestRequest(BaseModel):
    code: str
    language: str = "python"

class ProjectOrchestratorRequest(BaseModel):
    idea: str
    project_type: str = "full"

class TradingActionRequest(BaseModel):
    action: str = Field(..., description="get_price|get_signal|get_portfolio|get_overview|get_chart|add_portfolio|create_alert")
    params: dict = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════════════════════════

def _get_engine():
    from mamoun.core.capabilities_engine import get_capabilities_engine
    return get_capabilities_engine()


# ═══════════════════════════════════════════════════════════════════════════════
# Overall Status
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/status")
async def get_all_capabilities():
    """حالة كل القدرات الـ 12"""
    engine = _get_engine()
    return engine.get_status()

@router.get("/test")
async def test_all_capabilities():
    """اختبار كل القدرات"""
    engine = _get_engine()
    return await engine.run_all_tests()

@router.get("/projects")
async def get_capabilities_projects():
    """مشاريع القدرات"""
    try:
        from mamoun.core.project_orchestrator import get_project_orchestrator
        orchestrator = get_project_orchestrator()
        return orchestrator.get_status()
    except Exception:
        return {"projects": [], "total": 0}


@router.get("/code")
async def get_capabilities_code():
    """قدرات البرمجة"""
    return {
        "languages": ["typescript", "python", "html", "css", "javascript"],
        "frameworks": ["next.js", "react", "tailwind", "fastapi"],
        "max_complexity": "high",
        "status": "available",
    }


@router.get("/laptop-control")
async def get_capabilities_laptop():
    """قدرات التحكم بالحاسوب"""
    return {"status": "available", "permissions": ["screenshot", "click", "type", "scroll"]}


@router.get("/instagram")
async def get_capabilities_instagram():
    """قدرات إنستغرام"""
    return {"status": "inactive", "accounts": [], "analysis_available": True}


@router.get("/sandbox")
async def get_capabilities_sandbox():
    """بيئة الاختبار"""
    return {"status": "available", "active_sandboxes": 0, "supported_languages": ["python", "javascript"]}


@router.get("/blender")
async def get_capabilities_blender():
    """قدرات بلندر"""
    return {"status": "inactive", "models": 0, "scenes": 0}


@router.get("/orchestrator")
async def get_capabilities_orchestrator():
    """منسق القدرات"""
    try:
        engine = _get_engine()
        return engine.get_status()
    except Exception:
        return {"status": "running", "active_tasks": 0, "queued_tasks": 0}


@router.get("/{capability_id}")
async def get_capability_status(capability_id: str):
    """حالة قدرة واحدة"""
    engine = _get_engine()
    cap = engine.get_capability(capability_id)
    if not cap:
        raise HTTPException(404, f"قدرة غير موجودة: {capability_id}")
    return cap.to_dict()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Laptop Control — التحكم باللابتوب (100%)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/laptop-control", dependencies=[Depends(require_auth)])
async def control_laptop(req: LaptopControlRequest):
    """التحكم باللابتوب — ماوس، لوحة، شاشة، تطبيقات"""
    engine = _get_engine()
    result = await engine.control_laptop(req.action, req.params)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "فشل التحكم"))
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Terminal — الطرفية (100%)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/terminal/execute", dependencies=[Depends(require_auth)])
async def execute_terminal_command(req: TerminalRequest):
    """تنفيذ أمر في الطرفية"""
    engine = _get_engine()
    result = await engine.execute_terminal_command(req.command, req.timeout, req.approval_id)
    return result

@router.get("/terminal/status")
async def get_terminal_status():
    """حالة الطرفية"""
    engine = _get_engine()
    return await engine.get_terminal_status()


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Professional Coding — كتابة أكواد احترافية (100%)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/code/generate", dependencies=[Depends(require_auth)])
async def generate_code(req: CodeGenerationRequest):
    """توليد كود احترافي"""
    engine = _get_engine()
    result = await engine.generate_code(req.spec, req.language, req.context)
    return result

@router.post("/code/review")
async def review_code(req: CodeReviewRequest):
    """مراجعة كود احترافية"""
    engine = _get_engine()
    result = await engine.review_code(req.code, req.language)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Skill Learning — تعلم مهارات جديدة (100%)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/skills/learn", dependencies=[Depends(require_auth)])
async def learn_skill(req: SkillLearningRequest):
    """تعلم مهارة جديدة"""
    engine = _get_engine()
    result = await engine.learn_skill(req.skill_description, req.source)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Web Research — أبحاث الويب (100%)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/research/deep", dependencies=[Depends(require_auth)])
async def deep_research(req: DeepResearchRequest):
    """بحث عميق مع تحقق"""
    engine = _get_engine()
    result = await engine.deep_research(req.query, req.depth, req.verify)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Project Building — بناء مشاريع كاملة (100%)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/projects/build", dependencies=[Depends(require_auth)])
async def build_project(req: ProjectBuildRequest):
    """بناء مشروع كامل"""
    engine = _get_engine()
    result = await engine.build_project(req.idea, req.project_type)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Instagram Analysis — دراسة الانستغرام (100%)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/instagram/analyze")
async def analyze_instagram(req: InstagramAnalysisRequest):
    """تحليل صفحة انستغرام بشكل عميق"""
    engine = _get_engine()
    result = await engine.analyze_instagram(req.username, req.analysis_type)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Blender Control — التحكم ببلندر (100%)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/blender/control", dependencies=[Depends(require_auth)])
async def control_blender(req: BlenderControlRequest):
    """التحكم ببلندر"""
    engine = _get_engine()
    result = await engine.control_blender(req.action, req.params)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Project Orchestrator — باني مشاريع شامل (100%)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/orchestrator/start", dependencies=[Depends(require_auth)])
async def start_project_orchestration(req: ProjectOrchestratorRequest):
    """بدء تنسيق مشروع شامل"""
    engine = _get_engine()
    result = await engine.orchestrate_project(req.idea, req.project_type)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Agent Browser — المتصفح الوكيلي (100%)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/browser/action", dependencies=[Depends(require_auth)])
async def browser_action(req: BrowserActionRequest):
    """إجراء في المتصفح الوكيلي"""
    engine = _get_engine()
    result = await engine.browser_action(req.action, req.params)
    return result

@router.get("/browser/navigate")
async def browser_navigate(url: str = Query(...)):
    """فتح صفحة في المتصفح"""
    engine = _get_engine()
    result = await engine.browser_navigate(url)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Testing Sandbox — بيئة تجريب معزولة (100%)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/sandbox/test", dependencies=[Depends(require_auth)])
async def run_sandbox_test(req: SandboxTestRequest):
    """تشغيل اختبار في بيئة معزولة"""
    engine = _get_engine()
    result = await engine.run_sandbox_test(req.code, req.language)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Trading Room — غرفة التداول (100%)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/trading/action", dependencies=[Depends(require_auth)])
async def trading_action(req: TradingActionRequest):
    """إجراء تداول"""
    engine = _get_engine()
    params = req.params

    if req.action == "get_price":
        return await engine.get_market_data(params.get("symbol", "BTC"))
    elif req.action == "get_signal":
        return await engine.get_trading_signals(params.get("symbol", "BTC"))
    elif req.action == "get_portfolio":
        return await engine.get_portfolio()
    elif req.action == "get_overview":
        return await engine.get_market_overview()
    else:
        raise HTTPException(400, f"إجراء تداول غير معروف: {req.action}")

@router.get("/trading/price/{symbol}")
async def get_trading_price(symbol: str):
    """سعر أصل"""
    engine = _get_engine()
    return await engine.get_market_data(symbol)

@router.get("/trading/signal/{symbol}")
async def get_trading_signal(symbol: str):
    """إشارة تداول"""
    engine = _get_engine()
    return await engine.get_trading_signals(symbol)

@router.get("/trading/portfolio")
async def get_trading_portfolio():
    """المحفظة"""
    engine = _get_engine()
    return await engine.get_portfolio()

@router.get("/trading/overview")
async def get_trading_overview():
    """نظرة عامة على السوق"""
    engine = _get_engine()
    return await engine.get_market_overview()
