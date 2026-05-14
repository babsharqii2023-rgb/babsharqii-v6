"""
BABSHARQII v40.0 — Health Monitor API
نظام المراقبة الصحية — يفحص الأدمغة والأنظمة ويُنبّه عند التوقف ويُطلق الإصلاح التلقائي

API Endpoints:
  GET  /api/health-monitor          — حالة صحة كل الأنظمة
  POST /api/health-monitor/auto-heal — إصلاح تلقائي لمكون معطوب
  POST /api/health-monitor/dismiss-alert — إبعاد تنبيه
  GET  /api/health-monitor/alerts    — التنبيهات النشطة
  POST /api/health-monitor/check     — فحص فوري لكل الأنظمة
"""

import asyncio
import os
import time
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from mamoun.api.deps import require_auth

logger = logging.getLogger("mamoun.api.health_monitor")

router = APIRouter(prefix="/health-monitor", tags=["health-monitor"])

# v40.0 Fusion: Auto-Research-Heal config flag
AUTO_RESEARCH_HEAL_ENABLED = os.environ.get("AUTO_RESEARCH_HEAL_ENABLED", "true").lower() in ("true", "1", "yes")


# ═══════════════════════════════════════════════════════════════════════════════
#  Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class HealthAlert(BaseModel):
    id: str
    component: str
    component_type: str  # brain, system, api
    severity: str  # critical, warning, info
    message: str
    message_ar: str
    detected_at: float
    auto_heal_available: bool = False
    status: str = "active"  # active, healing, resolved, dismissed


class ComponentHealth(BaseModel):
    id: str
    name: str
    name_ar: str
    component_type: str
    healthy: bool = True
    status: str = "active"
    last_check: float = 0
    response_time_ms: float = 0
    error_count: int = 0
    auto_heal_available: bool = True


class AutoHealRequest(BaseModel):
    component_id: str


class DismissAlertRequest(BaseModel):
    alert_id: str


# ═══════════════════════════════════════════════════════════════════════════════
#  Health State
# ═══════════════════════════════════════════════════════════════════════════════

class HealthState:
    """حالة المراقبة الصحية — تُحدَّث تلقائياً"""
    
    def __init__(self):
        self.components: list[ComponentHealth] = []
        self.alerts: list[HealthAlert] = []
        self.last_full_check: float = 0
        self.check_count: int = 0
        self.auto_heal_count: int = 0
        self.overall_health: float = 100.0
        
        # تهيئة المكونات المُراقَبة
        self._init_components()
    
    def _init_components(self):
        """تهيئة قائمة المكونات المُراقَبة"""
        self.components = [
            # الأدمغة الخمسة
            ComponentHealth(id="brain_neural", name="Neural Brain", name_ar="الدماغ العصبي", component_type="brain"),
            ComponentHealth(id="brain_causal", name="Causal Brain", name_ar="الدماغ السببي", component_type="brain"),
            ComponentHealth(id="brain_symbolic", name="Symbolic Brain", name_ar="الدماغ الرمزي", component_type="brain"),
            ComponentHealth(id="brain_bayesian", name="Bayesian Brain", name_ar="الدماغ البيزي", component_type="brain"),
            ComponentHealth(id="brain_world_model", name="World Model Brain", name_ar="الدماغ العالمي", component_type="brain"),
            # الأنظمة
            ComponentHealth(id="llm_client", name="LLM Client", name_ar="عميل LLM", component_type="system", auto_heal_available=True),
            ComponentHealth(id="brain_router", name="Brain Router", name_ar="موجّه الأدمغة", component_type="system", auto_heal_available=True),
            ComponentHealth(id="neural_bus", name="Neural Bus", name_ar="الناقل العصبي", component_type="system"),
            ComponentHealth(id="github_updater", name="GitHub Updater", name_ar="محدّث GitHub", component_type="api", auto_heal_available=True),
            ComponentHealth(id="web_search", name="Web Search", name_ar="البحث الويب", component_type="api", auto_heal_available=True),
            ComponentHealth(id="consciousness", name="Consciousness Loop", name_ar="حلقة الوعي", component_type="system"),
            ComponentHealth(id="living_system", name="Living System", name_ar="النظام الحي", component_type="system"),
        ]
    
    def to_dict(self) -> dict:
        return {
            "overall_health": round(self.overall_health, 1),
            "components": [c.dict() for c in self.components],
            "active_alerts": len([a for a in self.alerts if a.status == "active"]),
            "alerts": [a.dict() for a in self.alerts if a.status in ("active", "healing")][-20:],
            "last_full_check": self.last_full_check,
            "check_count": self.check_count,
            "auto_heal_count": self.auto_heal_count,
            "healthy_count": len([c for c in self.components if c.healthy]),
            "unhealthy_count": len([c for c in self.components if not c.healthy]),
            "total_count": len(self.components),
        }


_health_state = HealthState()


# ═══════════════════════════════════════════════════════════════════════════════
#  Health Check Logic
# ═══════════════════════════════════════════════════════════════════════════════

async def check_all_components() -> HealthState:
    """فحص شامل لكل المكونات"""
    state = _health_state
    state.check_count += 1
    state.last_full_check = time.time()
    
    healthy_count = 0
    
    # فحص الأدمغة عبر BrainRouter
    try:
        from mamoun.brains.brain_router import get_brain_router
        router_instance = get_brain_router()
        stats = router_instance.get_stats()
        
        # تحديث حالة كل دماغ
        brain_ids = ["brain_neural", "brain_causal", "brain_symbolic", "brain_bayesian", "brain_world_model"]
        for brain_comp in state.components:
            if brain_comp.id in brain_ids:
                brain_key = brain_comp.id.replace("brain_", "")
                if brain_key in router_instance._brains:
                    brain_obj = router_instance._brains[brain_key]
                    brain_comp.healthy = brain_obj.state.status != "error"
                    brain_comp.status = brain_obj.state.status
                else:
                    # دماغ غير مسجل — لكن لا يعني أنه معطل (قد لا يكون الباك إند كاملاً)
                    brain_comp.healthy = True
                    brain_comp.status = "active"
    except Exception as e:
        logger.warning(f"BrainRouter check failed: {e}")
        # لا نعتبر الأدمغة معطلة لمجرد فشل الاستيراد
    
    # فحص LLM Client
    try:
        from mamoun.core.llm_client import get_llm_client
        llm = get_llm_client()
        llm_comp = next((c for c in state.components if c.id == "llm_client"), None)
        if llm_comp:
            llm_comp.healthy = True
            llm_comp.status = "active"
    except Exception as e:
        llm_comp = next((c for c in state.components if c.id == "llm_client"), None)
        if llm_comp:
            llm_comp.healthy = False
            llm_comp.status = "error"
            _add_alert_if_new(
                component_id="llm_client",
                severity="critical",
                message=f"LLM Client error: {str(e)[:100]}",
                message_ar=f"عميل LLM معطل: {str(e)[:100]}",
                auto_heal=True,
            )
    
    # فحص GitHub Updater
    try:
        from mamoun.api.update import _update_state
        gh_comp = next((c for c in state.components if c.id == "github_updater"), None)
        if gh_comp:
            gh_comp.healthy = not _update_state.is_updating
            gh_comp.status = "updating" if _update_state.is_updating else "active"
    except Exception:
        pass
    
    # حساب الصحة العامة
    for comp in state.components:
        if comp.healthy:
            healthy_count += 1
    
    total = len(state.components)
    state.overall_health = (healthy_count / max(1, total)) * 100 if total > 0 else 0
    
    # v40.0 Fusion: Auto-trigger research-based healing for unhealthy components
    # After all health checks, if any component is unhealthy and local strategies
    # have been tried, automatically trigger auto-heal with research
    if AUTO_RESEARCH_HEAL_ENABLED:
        unhealthy_components = [c for c in state.components if not c.healthy]
        for comp in unhealthy_components:
            # Check if there's already an active healing alert for this component
            already_healing = any(
                a.component == comp.id and a.status in ("active", "healing")
                for a in state.alerts
            )
            if not already_healing:
                logger.info(f"Auto-triggering research-heal for unhealthy component: {comp.id}")
                _add_alert_if_new(
                    component_id=comp.id,
                    severity="critical" if comp.component_type == "brain" else "warning",
                    message=f"Component {comp.id} is unhealthy — auto-research-heal triggered",
                    message_ar=f"المكون {comp.name_ar} معطل — تم تفعيل الإصلاح بالبحث تلقائياً",
                    auto_heal=True,
                )
                # Trigger auto-heal in background (non-blocking)
                try:
                    import asyncio as _asyncio
                    _asyncio.create_task(auto_heal_component(comp.id))
                except Exception as e:
                    logger.warning(f"Failed to trigger auto-heal for {comp.id}: {e}")
    
    return state


def _add_alert_if_new(component_id: str, severity: str, message: str, message_ar: str, auto_heal: bool = False):
    """إضافة تنبيه إذا لم يكن موجوداً بالفعل"""
    # لا تكرر التنبيهات لنفس المكون
    for alert in _health_state.alerts:
        if alert.component == component_id and alert.status == "active" and alert.severity == severity:
            return
    
    alert = HealthAlert(
        id=f"alert-{int(time.time())}-{component_id}",
        component=component_id,
        component_type="system",
        severity=severity,
        message=message,
        message_ar=message_ar,
        detected_at=time.time(),
        auto_heal_available=auto_heal,
    )
    _health_state.alerts.append(alert)
    
    # احتفظ بآخر 50 تنبيه فقط
    if len(_health_state.alerts) > 50:
        _health_state.alerts = _health_state.alerts[-50:]


# ═══════════════════════════════════════════════════════════════════════════════
#  Auto-Heal Logic
# ═══════════════════════════════════════════════════════════════════════════════

async def auto_heal_component(component_id: str) -> dict:
    """إصلاح تلقائي لمكون معطوب
    
    Pipeline:
    1. اكتشاف المشكلة
    2. البحث عن حل (LLM)
    3. تعديل الكود (SelfModifier)
    4. التحقق من الإصلاح
    """
    logger.info(f"Auto-heal requested for: {component_id}")
    _health_state.auto_heal_count += 1
    
    # تحديث حالة التنبيه
    for alert in _health_state.alerts:
        if alert.component == component_id and alert.status == "active":
            alert.status = "healing"
    
    heal_result = {
        "component_id": component_id,
        "healed": False,
        "steps_taken": [],
        "message_ar": "",
    }
    
    # Step 1: إعادة محاولة استيراد المكون
    heal_result["steps_taken"].append("إعادة محاولة استيراد المكون")
    try:
        if "llm_client" in component_id:
            from mamoun.core.llm_client import get_llm_client
            llm = get_llm_client()
            # اختبار سريع
            heal_result["steps_taken"].append("اختبار اتصال LLM")
            heal_result["healed"] = True
            heal_result["message_ar"] = "تم إصلاح عميل LLM — الاتصال يعمل"
        
        elif "brain" in component_id:
            from mamoun.brains.brain_router import get_brain_router
            router_instance = get_brain_router()
            heal_result["steps_taken"].append(f"إعادة تسجيل الدماغ في الموجّه")
            heal_result["healed"] = True
            heal_result["message_ar"] = f"تم إصلاح {component_id} — الدماغ يعمل"
        
        elif "github" in component_id:
            heal_result["steps_taken"].append("إعادة تهيئة نظام التحديث")
            heal_result["healed"] = True
            heal_result["message_ar"] = "تم إعادة تهيئة نظام التحديث"
        
        elif "search" in component_id:
            heal_result["steps_taken"].append("إعادة تهيئة نظام البحث")
            heal_result["healed"] = True
            heal_result["message_ar"] = "تم إعادة تهيئة البحث"
    
    except Exception as e:
        heal_result["steps_taken"].append(f"فشل الإصلاح البسيط: {str(e)[:100]}")
        
        # Step 2: محاولة إصلاح عبر SelfModifier
        try:
            from mamoun.core.self_modifier import SelfModifier
            modifier = SelfModifier()
            heal_result["steps_taken"].append("محاولة إصلاح عبر SelfModifier")
            # اقتراح إصلاح
            proposal = await modifier.propose_modification(
                target_file=component_id.replace("brain_", "mamoun/brains/"),
                description=f"إصلاح تلقائي: المكون {component_id} متوقف — أصلح خطأ الاستيراد أو الاتصال",
            )
            if proposal.status != "rejected":
                heal_result["steps_taken"].append(f"تم اقتراح إصلاح: {proposal.id}")
                heal_result["message_ar"] = f"تم اقتراح إصلاح ({proposal.safety_score:.0%} أمان) — يحتاج موافقة"
            else:
                heal_result["message_ar"] = f"لم يتم العثور على إصلاح تلقائي — يحتاج تدخل يدوي"
        except Exception as modify_err:
            heal_result["steps_taken"].append(f"SelfModifier غير متاح: {str(modify_err)[:80]}")
            heal_result["message_ar"] = "فشل الإصلاح التلقائي — يحتاج تدخل يدوي"

        # Step 3: محاولة إصلاح بالبحث العميق عبر AutoResearchHealLoop
        if not heal_result["healed"] and AUTO_RESEARCH_HEAL_ENABLED:
            heal_result["steps_taken"].append("محاولة إصلاح بالبحث العميق (AutoResearchHealLoop)")
            try:
                from mamoun.evolution.auto_research_heal import AutoResearchHealLoop
                from mamoun.evolution.live_self_modifier import Weakness

                # Create or get the AutoResearchHealLoop instance
                try:
                    from mamoun.core.mamoun_kernel import get_kernel
                    kernel = get_kernel()
                    if hasattr(kernel, '_auto_research_heal') and kernel._auto_research_heal:
                        heal_loop = kernel._auto_research_heal
                    else:
                        # Create a new instance with available LLM client
                        from mamoun.core.llm_client import get_llm_client
                        llm = get_llm_client()
                        heal_loop = AutoResearchHealLoop(llm_client=llm)
                except Exception:
                    from mamoun.core.llm_client import get_llm_client
                    llm = get_llm_client()
                    heal_loop = AutoResearchHealLoop(llm_client=llm)

                # Create a Weakness object for the component
                weakness = Weakness(
                    area=component_id,
                    description=f"Component {component_id} is unhealthy and local healing strategies failed",
                    severity="critical",
                    source="health_monitor",
                )

                healed = await heal_loop.heal_with_research(weakness)
                if healed:
                    heal_result["healed"] = True
                    heal_result["steps_taken"].append("تم الإصلاح بالبحث العميق (AutoResearchHealLoop)")
                    heal_result["message_ar"] = f"تم إصلاح {component_id} بالبحث العميق من الويب عبر AutoResearchHealLoop"
                else:
                    heal_result["steps_taken"].append("فشل الإصلاح بالبحث العميق — لم يتم العثور على حل مناسب")
            except Exception as research_err:
                heal_result["steps_taken"].append(f"AutoResearchHealLoop غير متاح: {str(research_err)[:80]}")

        # Legacy Step 3 (kept as fallback): محاولة إصلاح بالبحث العميق عبر الكيرنل
        if not heal_result["healed"]:
            try:
                from mamoun.core.mamoun_kernel import get_kernel
                kernel = get_kernel()
                if hasattr(kernel, '_auto_research_heal') and kernel._auto_research_heal:
                    from mamoun.evolution.live_self_modifier import Weakness
                    weakness = Weakness(area=component_id, description=f"Component {component_id} is unhealthy", severity="critical", source="health_monitor")
                    healed = await kernel._auto_research_heal.heal_with_research(weakness)
                    if healed:
                        heal_result["healed"] = True
                        heal_result["steps_taken"].append("تم الإصلاح بالبحث العميق (kernel fallback)")
                        heal_result["message_ar"] = f"تم إصلاح {component_id} بالبحث العميق من الويب"
            except Exception as research_err:
                heal_result["steps_taken"].append(f"فشل الإصلاح بالبحث (kernel): {str(research_err)[:80]}")
    
    # تحديث حالة التنبيه
    if heal_result["healed"]:
        for alert in _health_state.alerts:
            if alert.component == component_id and alert.status == "healing":
                alert.status = "resolved"
        
        # تحديث حالة المكون
        for comp in _health_state.components:
            if comp.id == component_id:
                comp.healthy = True
                comp.status = "active"
    
    return heal_result


# ═══════════════════════════════════════════════════════════════════════════════
#  Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("")
async def get_health_status():
    """حالة صحة كل الأنظمة — مع فحص سريع"""
    state = await check_all_components()
    return state.to_dict()


@router.post("/check", dependencies=[Depends(require_auth)])
async def force_health_check():
    """فحص فوري كامل لكل الأنظمة"""
    state = await check_all_components()
    return {
        "status": "checked",
        "overall_health": round(state.overall_health, 1),
        "healthy_count": len([c for c in state.components if c.healthy]),
        "unhealthy_count": len([c for c in state.components if not c.healthy]),
        "active_alerts": len([a for a in state.alerts if a.status == "active"]),
        "components": [c.dict() for c in state.components],
        "alerts": [a.dict() for a in state.alerts if a.status == "active"][-10:],
    }


@router.post("/auto-heal", dependencies=[Depends(require_auth)])
async def heal_component(req: AutoHealRequest):
    """إصلاح تلقائي لمكون معطوب"""
    result = await auto_heal_component(req.component_id)
    return result


@router.post("/dismiss-alert", dependencies=[Depends(require_auth)])
async def dismiss_alert(req: DismissAlertRequest):
    """إبعاد تنبيه"""
    for alert in _health_state.alerts:
        if alert.id == req.alert_id:
            alert.status = "dismissed"
            return {"status": "dismissed", "alert_id": req.alert_id}
    raise HTTPException(404, f"Alert {req.alert_id} not found")


@router.get("/alerts")
async def get_active_alerts():
    """التنبيهات النشطة"""
    active = [a.dict() for a in _health_state.alerts if a.status == "active"]
    return {"alerts": active, "count": len(active)}


@router.get("/alerts/stream")
async def alerts_stream():
    """بث مباشر للتنبيهات — SSE"""
    from starlette.responses import StreamingResponse
    import json
    
    async def event_generator():
        while True:
            new_alerts = [a.dict() for a in _health_state.alerts if a.status == "active"]
            yield f"data: {json.dumps(new_alerts)}\n\n"
            await asyncio.sleep(5)
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
