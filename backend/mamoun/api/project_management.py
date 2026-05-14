"""
BABSHARQII v31.0 — Project Management API
واجهة برمجة التطبيقات للطبقات الأربع الجديدة:
  - ProjectRegistry
  - SmartScheduler
  - SessionContext
  - ProjectPool

All endpoints mirror 1:1 with the dashboard features.
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from mamoun.api.deps import require_auth

logger = logging.getLogger("mamoun.api.project_management")

router = APIRouter(prefix="/project-mgmt", tags=["project_management"])


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: Get singleton instances (lazy init)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_registry():
    from mamoun.core.project_registry import get_project_registry
    return get_project_registry()

def _get_scheduler():
    from mamoun.core.smart_scheduler import get_smart_scheduler
    return get_smart_scheduler()

def _get_session_context():
    from mamoun.core.session_context import get_session_context_manager
    return get_session_context_manager()

def _get_pool():
    from mamoun.core.project_pool import get_project_pool
    return get_project_pool()


# ═══════════════════════════════════════════════════════════════════════════════
# Request Models
# ═══════════════════════════════════════════════════════════════════════════════

class RegisterProjectRequest(BaseModel):
    name: str
    description: str = ""
    repo_url: str = ""
    branch: str = "main"
    tags: list[str] = []
    category: str = ""

class UpdateProjectRequest(BaseModel):
    status: Optional[str] = None
    health: Optional[str] = None
    phase: Optional[str] = None
    repo_url: Optional[str] = None
    completion_pct: Optional[float] = None
    error_count: Optional[int] = None
    warning_count: Optional[int] = None
    tags: Optional[list[str]] = None
    category: Optional[str] = None
    priority_score: Optional[float] = None

class ScheduleProjectRequest(BaseModel):
    project_id: str
    repo_url: str = ""
    branch: str = "main"
    github_token: str = ""
    github_sync_interval: Optional[int] = None
    health_check_interval: Optional[int] = None
    build_test_interval: Optional[int] = None
    error_scan_interval: Optional[int] = None

class SubmitPoolTaskRequest(BaseModel):
    project_id: str
    task_type: str = "build"
    handler_name: str = ""
    input_data: dict = {}
    priority: int = 5
    timeout_seconds: int = 300

class MarkActionRequest(BaseModel):
    project_id: str
    action: str
    result: str = "success"
    details: str = ""

class AddApprovalRequest(BaseModel):
    project_id: str
    description: str
    risk_level: str = "medium"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. ProjectRegistry Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/registry/projects")
async def list_all_projects():
    """قائمة كل المشاريع + حالاتها"""
    registry = _get_registry()
    projects = registry.get_all_projects()
    return {
        "total": len(projects),
        "projects": [p.to_dict() for p in projects],
    }

@router.get("/registry/summary")
async def registry_summary():
    """ملخص الفهرس المركزي"""
    registry = _get_registry()
    summary = registry.get_summary()
    return summary.to_dict()

@router.get("/registry/project/{project_id}")
async def get_project(project_id: str):
    """حالة مشروع واحد"""
    registry = _get_registry()
    entry = registry.get_project_status(project_id)
    if not entry:
        raise HTTPException(404, f"مشروع غير موجود: {project_id}")
    return entry.to_dict()

@router.post("/registry/register", dependencies=[Depends(require_auth)])
async def register_project(req: RegisterProjectRequest):
    """تسجيل مشروع جديد في الفهرس"""
    registry = _get_registry()
    entry = registry.register_project(
        name=req.name,
        description=req.description,
        repo_url=req.repo_url,
        branch=req.branch,
        tags=req.tags,
        category=req.category,
    )
    return {"status": "registered", "project": entry.to_dict()}

@router.patch("/registry/project/{project_id}", dependencies=[Depends(require_auth)])
async def update_project(project_id: str, req: UpdateProjectRequest):
    """تحديث حالة مشروع"""
    registry = _get_registry()
    updates = {k: v for k, v in req.dict().items() if v is not None}
    entry = registry.update_project(project_id, **updates)
    if not entry:
        raise HTTPException(404, f"مشروع غير موجود: {project_id}")
    return {"status": "updated", "project": entry.to_dict()}

@router.delete("/registry/project/{project_id}", dependencies=[Depends(require_auth)])
async def remove_project(project_id: str):
    """إزالة مشروع من الفهرس"""
    registry = _get_registry()
    removed = registry.remove_project(project_id)
    if not removed:
        raise HTTPException(404, f"مشروع غير موجود: {project_id}")
    return {"status": "removed", "project_id": project_id}

@router.get("/registry/search")
async def search_projects(q: str = Query("")):
    """بحث في المشاريع"""
    registry = _get_registry()
    results = registry.search_projects(q)
    return {"query": q, "results": [p.to_dict() for p in results]}

@router.get("/registry/by-status/{status}")
async def projects_by_status(status: str):
    """مشاريع بحالة معينة"""
    registry = _get_registry()
    results = registry.get_projects_by_status(status)
    return {"status": status, "count": len(results), "projects": [p.to_dict() for p in results]}

@router.get("/registry/by-health/{health}")
async def projects_by_health(health: str):
    """مشاريع بصحة معينة"""
    registry = _get_registry()
    results = registry.get_projects_by_health(health)
    return {"health": health, "count": len(results), "projects": [p.to_dict() for p in results]}

@router.get("/registry/stale")
async def stale_projects(threshold_hours: int = Query(24)):
    """مشاريع لم تُفحص منذ فترة"""
    registry = _get_registry()
    results = registry.get_stale_projects(threshold_hours)
    return {"threshold_hours": threshold_hours, "count": len(results), "projects": [p.to_dict() for p in results]}

@router.post("/registry/sync-disk", dependencies=[Depends(require_auth)])
async def sync_from_disk():
    """إعادة قراءة كل state.json من القرص"""
    registry = _get_registry()
    registry.load_from_disk()
    return {"status": "synced", "total": len(registry.get_all_projects())}


# ═══════════════════════════════════════════════════════════════════════════════
# 2. SmartScheduler Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/scheduler/status")
async def scheduler_status():
    """حالة الجدولة الذكية"""
    scheduler = _get_scheduler()
    return scheduler.get_status()

@router.get("/scheduler/report")
async def scheduler_report():
    """تقرير شامل: متى فُحص كل مشروع آخر مرة"""
    scheduler = _get_scheduler()
    return scheduler.report_schedule_status()

@router.post("/scheduler/start", dependencies=[Depends(require_auth)])
async def start_scheduler():
    """بدء الجدولة الذكية"""
    scheduler = _get_scheduler()
    # Wire up dependencies
    try:
        scheduler.set_registry(_get_registry())
        scheduler.set_pool(_get_pool())
    except Exception:
        pass
    await scheduler.start()
    return {"status": "started", "message": "تم بدء الجدولة الذكية"}

@router.post("/scheduler/stop", dependencies=[Depends(require_auth)])
async def stop_scheduler():
    """إيقاف الجدولة"""
    scheduler = _get_scheduler()
    await scheduler.shutdown()
    return {"status": "stopped"}

@router.post("/scheduler/schedule-project", dependencies=[Depends(require_auth)])
async def schedule_project(req: ScheduleProjectRequest):
    """تسجيل مستودع مشروع للجدولة"""
    scheduler = _get_scheduler()
    intervals = {}
    if req.github_sync_interval:
        intervals["github_sync_interval"] = req.github_sync_interval
    if req.health_check_interval:
        intervals["health_check_interval"] = req.health_check_interval
    if req.build_test_interval:
        intervals["build_test_interval"] = req.build_test_interval
    if req.error_scan_interval:
        intervals["error_scan_interval"] = req.error_scan_interval
    
    config = scheduler.register_project_repo(
        project_id=req.project_id,
        repo_url=req.repo_url,
        branch=req.branch,
        github_token=req.github_token,
        **intervals,
    )
    return {"status": "scheduled", "config": config.to_dict()}

@router.delete("/scheduler/schedule-project/{project_id}", dependencies=[Depends(require_auth)])
async def unschedule_project(project_id: str):
    """إلغاء جدولة مشروع"""
    scheduler = _get_scheduler()
    scheduler.unregister_project(project_id)
    return {"status": "unscheduled", "project_id": project_id}

@router.get("/scheduler/priorities")
async def prioritize_projects():
    """ترتيب المشاريع بالأولوية"""
    scheduler = _get_scheduler()
    return {"priority_order": scheduler.prioritize_projects()}


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SessionContext Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/context/status")
async def context_status():
    """حالة سياق الجلسة"""
    ctx = _get_session_context()
    return ctx.get_status()

@router.get("/context/current")
async def get_current_context():
    """السياق الحالي الكامل"""
    ctx = _get_session_context()
    context = ctx.get_context()
    return context.to_dict()

@router.get("/context/prompt")
async def get_session_prompt():
    """سياق جاهز لإدراجه في بداية prompt أي جلسة AI"""
    ctx = _get_session_context()
    return {"prompt": ctx.get_session_prompt()}

@router.post("/context/generate", dependencies=[Depends(require_auth)])
async def generate_context():
    """توليد/تحديث السياق من Registry + Scheduler"""
    ctx = _get_session_context()
    try:
        ctx.set_registry(_get_registry())
        ctx.set_scheduler(_get_scheduler())
    except Exception:
        pass
    context = ctx.auto_generate()
    return {"status": "generated", "context": context.to_dict()}

@router.post("/context/mark-action", dependencies=[Depends(require_auth)])
async def mark_action(req: MarkActionRequest):
    """تسجيل فعل على مشروع"""
    ctx = _get_session_context()
    ctx.mark_project_action(
        project_id=req.project_id,
        action=req.action,
        result=req.result,
        details=req.details,
    )
    return {"status": "recorded"}

@router.post("/context/add-approval", dependencies=[Depends(require_auth)])
async def add_approval(req: AddApprovalRequest):
    """إضافة موافقة معلقة"""
    ctx = _get_session_context()
    ctx.add_pending_approval(
        project_id=req.project_id,
        description=req.description,
        risk_level=req.risk_level,
    )
    return {"status": "added"}

@router.delete("/context/approval/{project_id}", dependencies=[Depends(require_auth)])
async def remove_approval(project_id: str):
    """إزالة موافقة معلقة"""
    ctx = _get_session_context()
    ctx.remove_pending_approval(project_id)
    return {"status": "removed"}


# ═══════════════════════════════════════════════════════════════════════════════
# 4. ProjectPool Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/pool/status")
async def pool_status():
    """حالة حوض المشاريع"""
    pool = _get_pool()
    return pool.get_pool_status()

@router.post("/pool/submit", dependencies=[Depends(require_auth)])
async def submit_pool_task(req: SubmitPoolTaskRequest):
    """إرسال مهمة مشروع للحوض"""
    pool = _get_pool()
    task = await pool.submit(
        project_id=req.project_id,
        task_type=req.task_type,
        handler_name=req.handler_name,
        input_data=req.input_data,
        priority=req.priority,
        timeout_seconds=req.timeout_seconds,
    )
    return {"status": "submitted", "task": task.to_dict()}

@router.get("/pool/results/{project_id}")
async def pool_results(project_id: str):
    """نتائج مشروع من الحوض"""
    pool = _get_pool()
    results = pool.get_results(project_id)
    return {"project_id": project_id, "results": results}

@router.get("/pool/task/{task_id}")
async def pool_task_result(task_id: str):
    """نتيجة مهمة واحدة"""
    pool = _get_pool()
    result = pool.get_task_result(task_id)
    if not result:
        raise HTTPException(404, f"مهمة غير موجودة: {task_id}")
    return result

@router.post("/pool/cancel/{project_id}", dependencies=[Depends(require_auth)])
async def cancel_pool_tasks(project_id: str):
    """إلغاء كل مهام مشروع"""
    pool = _get_pool()
    cancelled = await pool.cancel(project_id)
    return {"status": "cancelled", "count": cancelled}

@router.post("/pool/rebalance", dependencies=[Depends(require_auth)])
async def rebalance_pool():
    """إعادة توزيع الموارد"""
    pool = _get_pool()
    await pool.rebalance()
    return {"status": "rebalanced", "pool_status": pool.get_status()}

@router.post("/pool/start", dependencies=[Depends(require_auth)])
async def start_pool():
    """بدء الحوض"""
    pool = _get_pool()
    await pool.start()
    return {"status": "started"}

@router.post("/pool/shutdown", dependencies=[Depends(require_auth)])
async def shutdown_pool():
    """إيقاف الحوض"""
    pool = _get_pool()
    await pool.shutdown()
    return {"status": "shutdown"}


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Unified Status — كل الطبقات في endpoint واحد
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/unified-status")
async def unified_status():
    """حالة موحدة لكل الطبقات الأربع — للداش بورد"""
    registry = _get_registry()
    scheduler = _get_scheduler()
    ctx = _get_session_context()
    pool = _get_pool()
    
    return {
        "registry": registry.get_summary().to_dict(),
        "scheduler": scheduler.get_status(),
        "session_context": ctx.get_status(),
        "project_pool": pool.get_status(),
        "timestamp": time.time(),
    }
