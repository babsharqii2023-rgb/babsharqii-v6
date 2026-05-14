"""
BABSHARQII v23.0 — API Routes for v23 Systems
Neural Bus + Absolute Executor + Self-Healing
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, List, Any

from mamoun.api.deps import require_auth

router = APIRouter(prefix="/v23", tags=["v23 — Neural Bus + Executor + Self-Healing"])


# ═══════════════════════════════════════════════════════════════════════════════
#  Request Models
# ═══════════════════════════════════════════════════════════════════════════════

class ExecuteRequest(BaseModel):
    """طلب تنفيذ"""
    request: str
    context: Optional[Dict[str, Any]] = None


class NeuralPublishRequest(BaseModel):
    """طلب نشر إشارة عصبية"""
    signal_type: str
    source: str
    payload: Optional[Dict[str, Any]] = None
    priority: Optional[int] = 2


class HealthCheckRequest(BaseModel):
    """طلب فحص صحي"""
    component: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
#  Status Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/status")
async def get_v23_status():
    """حالة أنظمة v23 الكاملة"""
    from mamoun.core.mamoun_kernel import get_kernel
    kernel = get_kernel()
    return kernel.get_v23_status()


@router.get("/data")
async def get_v23_data():
    """بيانات v23 للواجهة"""
    from mamoun.core.mamoun_kernel import get_kernel
    kernel = get_kernel()
    return kernel.get_v23_data()


# ═══════════════════════════════════════════════════════════════════════════════
#  Neural Bus Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/neural-bus/status")
async def get_neural_bus_status():
    """حالة الناقل العصبي"""
    from mamoun.core.neural_bus import neural_bus
    return neural_bus.get_status()


@router.get("/neural-bus/signals")
async def get_neural_bus_signals(limit: int = 20):
    """آخر الإشارات العصبية"""
    from mamoun.core.neural_bus import neural_bus
    return {"signals": neural_bus.get_recent_signals(limit=limit)}


@router.get("/neural-bus/flow")
async def get_neural_bus_flow():
    """تدفق الإشارات بين المحركات"""
    from mamoun.core.neural_bus import neural_bus
    return neural_bus.get_signal_flow()


@router.get("/neural-bus/subscriptions")
async def get_neural_bus_subscriptions():
    """كل الاشتراكات العصبية"""
    from mamoun.core.neural_bus import neural_bus
    return {"subscriptions": neural_bus.get_subscriptions()}


@router.post("/neural-bus/publish", dependencies=[Depends(require_auth)])
async def publish_neural_signal(req: NeuralPublishRequest):
    """نشر إشارة عصبية"""
    from mamoun.core.neural_bus import neural_bus, SignalPriority
    try:
        priority = SignalPriority(req.priority)
    except ValueError:
        priority = SignalPriority.NORMAL

    signal = neural_bus.publish(
        signal_type=req.signal_type,
        source=req.source,
        payload=req.payload or {},
        priority=priority,
    )
    return {"published": True, "signal_id": signal.id}


@router.get("/neural-bus/stats")
async def get_neural_bus_stats():
    """إحصائيات الناقل العصبي — NeuralBus stats for monitoring (M-6)."""
    from mamoun.core.neural_bus import neural_bus
    return neural_bus.get_stats()


# ═══════════════════════════════════════════════════════════════════════════════
#  Absolute Executor Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/executor/status")
async def get_executor_status():
    """حالة محرك التنفيذ المطلق"""
    from mamoun.core.absolute_executor import absolute_executor
    return absolute_executor.get_status()


@router.post("/executor/execute", dependencies=[Depends(require_auth)])
async def execute_request(req: ExecuteRequest):
    """تنفيذ طلب — INTENT → PLAN → EXECUTE → VERIFY → FIX → REPORT"""
    from mamoun.core.absolute_executor import absolute_executor
    result = await absolute_executor.execute(
        user_request=req.request,
        context=req.context or {},
    )
    return result


@router.get("/executor/plans")
async def get_executor_plans(limit: int = 10):
    """آخر خطط التنفيذ"""
    from mamoun.core.absolute_executor import absolute_executor
    return {"plans": absolute_executor.get_recent_plans(limit=limit)}


@router.get("/executor/plans/{plan_id}")
async def get_executor_plan(plan_id: str):
    """خطة تنفيذ محددة"""
    from mamoun.core.absolute_executor import absolute_executor
    plan = absolute_executor.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="خطة التنفيذ غير موجودة")
    return plan


# ═══════════════════════════════════════════════════════════════════════════════
#  Self-Healing Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/healing/status")
async def get_healing_status():
    """حالة محرك الشفاء الذاتي"""
    from mamoun.core.self_healing import self_healing
    return self_healing.get_status()


@router.get("/healing/report")
async def get_healing_report():
    """تقرير صحي شامل"""
    from mamoun.core.self_healing import self_healing
    return self_healing.get_health_report()


@router.post("/healing/check", dependencies=[Depends(require_auth)])
async def run_health_check(req: HealthCheckRequest = None):
    """تشغيل فحص صحي"""
    from mamoun.core.self_healing import self_healing
    result = self_healing.run_health_check()
    return result


@router.get("/healing/issues")
async def get_active_issues():
    """المشاكل النشطة"""
    from mamoun.core.self_healing import self_healing
    return {"issues": self_healing.get_active_issues()}


@router.post("/healing/trigger", dependencies=[Depends(require_auth)])
async def trigger_healing(component: str = ""):
    """v31: Trigger self-healing manually — runs health check + auto-repair."""
    from mamoun.core.self_healing import self_healing
    result = self_healing.run_health_check()
    # Publish healing triggered to NeuralBus
    try:
        from mamoun.core.neural_bus import neural_bus
        if neural_bus._initialized:
            neural_bus.publish(
                signal_type="healing_started",
                source="api:healing_trigger",
                payload={"component": component, "result": result},
            )
    except Exception:
        pass
    return {"triggered": True, "result": result}


class SelfUpdateRequest(BaseModel):
    """طلب تحديث ذاتي"""
    repo_path: Optional[str] = None
    max_fix_attempts: Optional[int] = 3
    auto_restart: Optional[bool] = False


@router.post("/healing/self-update", dependencies=[Depends(require_auth)])
async def autonomous_self_update(req: SelfUpdateRequest = None):
    """
    v31.2: تحديث ذاتي كامل — مامون يسحب التحديثات، يفحصها، يصلح الأخطاء، يطبقها
    
    Full cycle: git pull → validate → fix (if broken) → restart (with approval)
    Time: 37 seconds - 5 minutes (depending on if LLM fixes needed)
    """
    from mamoun.core.self_healing import self_healing
    if req is None:
        req = SelfUpdateRequest()
    
    report = await self_healing.autonomous_self_update(
        repo_path=req.repo_path,
        max_fix_attempts=req.max_fix_attempts or 3,
    )
    
    # If auto_restart and healthy → schedule restart
    if req.auto_restart and report.get("success") and report.get("restart_needed"):
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # Schedule a graceful restart after a short delay
            import os
            import signal
            loop.call_later(3, lambda: os.kill(os.getpid(), signal.SIGTERM))
            report["restart_scheduled"] = True
        except Exception:
            report["restart_scheduled"] = False
    
    return report


@router.post("/healing/git-pull", dependencies=[Depends(require_auth)])
async def git_pull_and_apply(repo_path: str = ""):
    """v31.2: سحب تحديثات من GitHub وتطبيقها مع فحص الصحة"""
    from mamoun.core.self_healing import self_healing
    result = self_healing.git_pull_and_apply(repo_path or None)
    return result


class ConfigureGithubRequest(BaseModel):
    """طلب تهيئة GitHub"""
    repo: str
    token: str
    branch: Optional[str] = "main"


@router.post("/healing/configure-github", dependencies=[Depends(require_auth)])
async def configure_github(req: ConfigureGithubRequest):
    """
    v32: تهيئة GitHub للتحديث الذاتي — يكفي تعيينها مرة واحدة
    
    بعد التهيئة، يمكنك استخدام /healing/autonomous-update مباشرة
    بدون الحاجة لتقديم repo/token مرة أخرى.
    
    Example:
        POST /v23/healing/configure-github
        {
            "repo": "babsharqii2023-rgb/babsharqii-v5",
            "token": "ghp_xxxxxxxx",
            "branch": "main"
        }
    """
    from mamoun.core.self_healing import self_healing
    result = self_healing.configure_github(
        repo=req.repo,
        token=req.token,
        branch=req.branch or "main",
    )
    return result


@router.get("/healing/github-config")
async def get_github_config():
    """v32: الحصول على إعدادات GitHub الحالية"""
    from mamoun.core.self_healing import self_healing
    return self_healing.get_github_config()


@router.post("/healing/autonomous-update", dependencies=[Depends(require_auth)])
async def autonomous_update():
    """
    v32: تحديث ذاتي — فقط أعط الأمر!
    
    يجب تهيئة GitHub أولاً عبر /healing/configure-github
    ثم يمكنك استدعاء هذا الـ endpoint مباشرة.
    
    الدورة الكاملة:
    1. سحب التحديثات من GitHub (git pull)
    2. فحص صحة الكود (validate)
    3. إذا صالح → جاهز للنشر
    4. إذا تالف → محاولة إصلاح بالـ LLM (حتى 3 مرات)
    5. إذا فشلت كل المحاولات → تراجع (rollback)
    6. بعد موافقتك → إعادة تشغيل
    
    المدة: 1-5 دقائق
    """
    from mamoun.core.self_healing import self_healing
    report = await self_healing.autonomous_update()
    return report
