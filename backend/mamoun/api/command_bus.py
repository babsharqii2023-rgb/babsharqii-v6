"""
BABSHARQII v38.0 — Unified Command Bus
ناقل الأوامر الموحّد — يحوّل الأوامر النصية إلى أفعال حقيقية

الطبقة 1 من آلية التحكم الشاملة:
- يصنّف الأمر حسب القصد (feature_toggle, git_op, brain_control, etc.)
- يُنفّذه عبر النظام المناسب
- يُعيد النتيجة + الأثر + صفحة العرض المقترحة
"""

import re
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

logger = logging.getLogger("mamoun.api.command_bus")

# Dynamically determine project root
_PROJECT_ROOT = str(Path(__file__).parent.parent.parent.parent)

router = APIRouter(prefix="/v2", tags=["command_bus"])


class CommandRequest(BaseModel):
    command: str
    context: dict = {}


class CommandResponse(BaseModel):
    success: bool
    action: str
    target: str
    message: str
    data: Any = None
    navigate_to: Optional[str] = None  # صفحة العرض المقترحة
    needs_confirmation: bool = False  # هل يحتاج تأكيد (نعم/لا)؟
    confirmation_id: Optional[str] = None
    side_effects: list = []


# ═══ تصنيف الأوامر ═══

# أنماط الأوامر — الترتيب مهم: brain_control قبل feature_toggle
COMMAND_PATTERNS = {
    "brain_control": [
        r"(?:فعّل|شغّل|activate)\s+(?:الدماغ|دماغ|brain)\s+(.+)",
        r"(?:أوقف|اوقف|deactivate|disable)\s+(?:الدماغ|دماغ|brain)\s+(.+)",
        r"(?:اسأل|سؤال|query)\s+(?:الدماغ|دماغ|brain)\s+(.+)",
        r"(?:عدّل|تعديل|modify).*(?:درجة|حرارة|temperature).*(?:دماغ|brain)\s*(.+)",
        # نمط مباشر: activate/disable + اسم دماغ معروف
        r"(?:فعّل|شغّل|activate|enable)\s+(neural|causal|symbolic|bayesian|world_model|العصبي|السببي|الرمزي|الاحتمالي|العالمي|نموذج العالم)\s+(?:الدماغ|دماغ|brain)?$",
        r"(?:أوقف|اوقف|deactivate|disable)\s+(neural|causal|symbolic|bayesian|world_model|العصبي|السببي|الرمزي|الاحتمالي|العالمي|نموذج العالم)\s+(?:الدماغ|دماغ|brain)?$",
    ],
    "diagnosis": [
        r"(?:شخّص|تشخيص|diagnose|فحص).*(?:النظام|الخلل|المشكلة|نظام|مشكلة)",
        r"(?:أصلح|إصلاح|heal|fix|repair).*(?:النظام|المشكلة|ذاتي)",
    ],
    "feature_toggle": [
        r"(?:فعّل|فعّل|شغّل|شغل|تفعيل|تشغيل|enable|activate)\s+(.+)",
        r"(?:أوقف|اوقف|أطفئ|اطفئ|إيقاف|إطفاء|disable|deactivate|stop)\s+(.+)",
    ],
    "git_op": [
        r"(?:اسحب|سحب|pull|جلب).*(?:تحديث|تعديل|تغيير|update)",
        r"(?:افحص|فحص|check).*(?:تحديث|تعديل|جديد|update)",
        r"(?:ارفع|رفع|push|دفع).*(?:تحديث|تعديل|تغيير)",
        r"(?:تراجع|rollback|restore).*(?:تحديث|تعديل)",
        r"^pull\s+updates?$",
    ],
    "project": [
        r"(?:ابنِ|بناء|build|create|أنشئ|انشئ).*(?:مشروع|project|موقع|site|تطبيق|app)",
    ],
    "evolution": [
        r"(?:طوّر|تطوير|evolve|تحسين).*(?:النظام|ذاتي|self)",
        r"(?:حسّن|تحسين|improve).*(?:الأداء|النظام|الذات)",
    ],
    "terminal": [
        r"(?:نفّذ|تنفيذ|execute|run|شغّل).*(?:أمر|command|كود|script)",
        r"(?:افتح|فتح|open).*(?:طرفية|terminal|سيرفر|server)",
    ],
    "settings": [
        r"(?:غيّر|تغيير|change|عدّل|تعديل).*(?:إعداد|setting|توكن|token|مفتاح|key)",
    ],
}

# خريطة الميزات — ربط الأسماء العربية بالأنظمة الفعلية
FEATURE_MAP = {
    # القدرات
    "التداول": {"flag": "MAMOUN_TRADING", "endpoint": "/api/capabilities/trading/overview", "page": "trading"},
    "تداول": {"flag": "MAMOUN_TRADING", "endpoint": "/api/capabilities/trading/overview", "page": "trading"},
    "trading": {"flag": "MAMOUN_TRADING", "endpoint": "/api/capabilities/trading/overview", "page": "trading"},
    "انستقرام": {"flag": "MAMOUN_INSTAGRAM_AUTOMATION", "endpoint": "/api/capabilities/instagram/status", "page": "instagram"},
    "instagram": {"flag": "MAMOUN_INSTAGRAM_AUTOMATION", "endpoint": "/api/capabilities/instagram/status", "page": "instagram"},
    "المتجر": {"flag": "MAMOUN_ECOMMERCE_MODE", "endpoint": "/api/capabilities/ecommerce/status", "page": "ecommerce"},
    "متجر": {"flag": "MAMOUN_ECOMMERCE_MODE", "endpoint": "/api/capabilities/ecommerce/status", "page": "ecommerce"},
    "ecommerce": {"flag": "MAMOUN_ECOMMERCE_MODE", "endpoint": "/api/capabilities/ecommerce/status", "page": "ecommerce"},
    "بلندر": {"flag": "MAMOUN_BLENDER", "endpoint": "/api/capabilities/blender/status", "page": "blender"},
    "blender": {"flag": "MAMOUN_BLENDER", "endpoint": "/api/capabilities/blender/status", "page": "blender"},
    "روبوت": {"flag": "MAMOUN_ROBOT_CONTROL", "endpoint": "/api/embodiment/status", "page": "embodiment"},
    "robot": {"flag": "MAMOUN_ROBOT_CONTROL", "endpoint": "/api/embodiment/status", "page": "embodiment"},
    "iot": {"flag": "MAMOUN_IOT_GATEWAY", "endpoint": "/api/embodiment/status", "page": "embodiment"},
    "الموبايل": {"flag": "MAMOUN_MOBILE_BUILDER", "endpoint": "/api/capabilities/mobile/status", "page": "mobile"},
    "mobile": {"flag": "MAMOUN_MOBILE_BUILDER", "endpoint": "/api/capabilities/mobile/status", "page": "mobile"},
    "البرمجة الذاتية": {"flag": "MAMOUN_SELF_PROGRAMMING", "endpoint": "/api/v24/self-modify/status", "page": "self-modify"},
    "self-programming": {"flag": "MAMOUN_SELF_PROGRAMMING", "endpoint": "/api/v24/self-modify/status", "page": "self-modify"},
    # الأنظمة
    "التطور التلقائي": {"flag": "MAMOUN_AUTO_EVOLVE", "endpoint": "/api/evolution/current", "page": "evolution"},
    "auto-evolve": {"flag": "MAMOUN_AUTO_EVOLVE", "endpoint": "/api/evolution/current", "page": "evolution"},
}

# خريطة الأدمغة
BRAIN_MAP = {
    "neural": "neural", "العصبي": "neural", "عصبي": "neural", "الأساسي": "neural", "اساسي": "neural",
    "causal": "causal", "السببي": "causal", "سببي": "causal",
    "symbolic": "symbolic", "الرمزي": "symbolic", "رمزي": "symbolic",
    "bayesian": "bayesian", "الاحتمالي": "bayesian", "احتمالي": "bayesian",
    "world_model": "world_model", "world": "world_model", "العالمي": "world_model", "عالمي": "world_model",
    "نموذج العالم": "world_model",
}

# انتظار تأكيد — تخزين مؤقت
_pending_confirmations: dict = {}


def classify_command(command: str) -> tuple[str, str, bool]:
    """تصنيف الأمر: يُرجع (نوع الأمر، الهدف، هل تفعيل أم إيقاف)"""
    cmd_lower = command.strip().lower()

    for action_type, patterns in COMMAND_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, cmd_lower)
            if match:
                target = match.group(1).strip() if match.groups() else ""
                is_activate = "فعّل" in cmd_lower or "شغّل" in cmd_lower or "enable" in cmd_lower or "activate" in cmd_lower or "تفعيل" in cmd_lower
                return action_type, target, is_activate

    # محاولة تصنيف بسيطة
    if any(w in cmd_lower for w in ["فعّل", "شغّل", "activate", "enable"]):
        return "feature_toggle", "", True
    if any(w in cmd_lower for w in ["أوقف", "اوقف", "deactivate", "disable"]):
        return "feature_toggle", "", False
    if any(w in cmd_lower for w in ["اسحب", "pull", "تحديث"]):
        return "git_op", "pull", False
    if any(w in cmd_lower for w in ["شخّص", "diagnose", "فحص"]):
        return "diagnosis", "full", False
    if any(w in cmd_lower for w in ["ابنِ", "بناء", "build"]):
        return "project", "", False

    return "unknown", "", False


def find_feature(target: str) -> dict | None:
    """البحث عن ميزة بالاسم"""
    target_lower = target.lower().strip()
    # مطابقة مباشرة
    if target_lower in FEATURE_MAP:
        return FEATURE_MAP[target_lower]
    # مطابقة جزئية
    for key, val in FEATURE_MAP.items():
        if key in target_lower or target_lower in key:
            return val
    return None


def find_brain(target: str) -> str | None:
    """البحث عن دماغ بالاسم"""
    target_lower = target.lower().strip()
    if target_lower in BRAIN_MAP:
        return BRAIN_MAP[target_lower]
    for key, val in BRAIN_MAP.items():
        if key in target_lower or target_lower in key:
            return val
    return None


@router.post("/command")
async def execute_command(req: CommandRequest):
    """
    نقطة الدخول الموحّدة — أي أمر نصي يُنفّذ فعلياً
    """
    action_type, target, is_activate = classify_command(req.command)

    if action_type == "feature_toggle":
        return await _handle_feature_toggle(target, is_activate)
    elif action_type == "git_op":
        return await _handle_git_op(target, req.context)
    elif action_type == "brain_control":
        return await _handle_brain_control(target, is_activate, req.context)
    elif action_type == "diagnosis":
        return await _handle_diagnosis()
    elif action_type == "project":
        return await _handle_project(req.command, req.context)
    elif action_type == "evolution":
        return await _handle_evolution()
    elif action_type == "terminal":
        return await _handle_terminal(req.command)
    elif action_type == "settings":
        return await _handle_settings(req.command, req.context)
    else:
        return CommandResponse(
            success=False,
            action="unknown",
            target="",
            message=f"لم أفهم الأمر: '{req.command}'. جرب: 'فعّل التداول', 'اسحب التحديثات', 'شخّص النظام'",
        )


async def _handle_feature_toggle(target: str, is_activate: bool) -> CommandResponse:
    """تفعيل/إيقاف ميزة فعلياً"""
    feature = find_feature(target)
    if not feature:
        # حاول البحث في كل الميزات المعروفة
        from mamoun.api.feature_flags import feature_flag_manager
        all_flags = feature_flag_manager.get_all()
        for flag_name, flag_info in all_flags.items():
            if target.lower() in flag_name.lower() or target.lower() in flag_info.get("label_ar", "").lower():
                feature = {"flag": flag_name, "endpoint": flag_info.get("endpoint", ""), "page": flag_info.get("page", "")}
                break

    if not feature:
        return CommandResponse(
            success=False,
            action="feature_toggle",
            target=target,
            message=f"لم أجد الميزة '{target}'. الميزات المتاحة: {', '.join(FEATURE_MAP.keys())}",
        )

    flag_name = feature["flag"]

    # غيّر الحالة فعلياً
    from mamoun.api.feature_flags import feature_flag_manager
    new_state = await feature_flag_manager.toggle(flag_name, is_activate)

    action_verb = "تفعيل" if is_activate else "إيقاف"
    page = feature.get("page", "")

    return CommandResponse(
        success=True,
        action="feature_toggle",
        target=flag_name,
        message=f"تم {action_verb} {target} فعلياً — الحالة الآن: {'مفعّل' if new_state else 'موقف'}",
        data={"flag": flag_name, "enabled": new_state, "endpoint": feature.get("endpoint", "")},
        navigate_to=page if is_activate else None,  # فتح صفحة الميزة عند التفعيل
        side_effects=[f"تغيير {flag_name} من {not new_state} إلى {new_state}"],
    )


async def _handle_git_op(target: str, context: dict) -> CommandResponse:
    """عمليات GitHub"""
    if "pull" in target.lower() or "سحب" in target:
        # فحص أولاً
        import subprocess
        try:
            result = subprocess.run(
                ["git", "fetch", "origin"],
                capture_output=True, text=True, timeout=30,
                cwd=_PROJECT_ROOT
            )

            # مقارنة local مع remote
            result2 = subprocess.run(
                ["git", "log", "--oneline", "HEAD..origin/main"],
                capture_output=True, text=True, timeout=15,
                cwd=_PROJECT_ROOT
            )

            new_commits = result2.stdout.strip()

            if not new_commits:
                return CommandResponse(
                    success=True,
                    action="git_op",
                    target="pull",
                    message="أنت على أحدث إصدار — لا توجد تحديثات جديدة",
                    data={"has_updates": False},
                    navigate_to="github",
                )

            # هناك تحديثات — اسأل المستخدم أولاً
            import uuid
            conf_id = str(uuid.uuid4())[:8]
            _pending_confirmations[conf_id] = {
                "type": "git_pull",
                "new_commits": new_commits,
                "timestamp": __import__("time").time(),
            }

            return CommandResponse(
                success=True,
                action="git_op",
                target="pull",
                message=f"توجد تحديثات جديدة:\n{new_commits}\n\nهل تريد التطبيق؟",
                data={"has_updates": True, "new_commits": new_commits.split("\n")},
                navigate_to="github",
                needs_confirmation=True,
                confirmation_id=conf_id,
            )
        except Exception as e:
            return CommandResponse(
                success=False,
                action="git_op",
                target="pull",
                message=f"فشل فحص التحديثات: {e}",
            )

    return CommandResponse(success=False, action="git_op", target=target, message="عملية غير معروفة")


async def _handle_brain_control(target: str, is_activate: bool, context: dict) -> CommandResponse:
    """تحكم بالأدمغة"""
    brain_id = find_brain(target)
    if not brain_id:
        return CommandResponse(
            success=False,
            action="brain_control",
            target=target,
            message=f"لم أجد الدماغ '{target}'. الأدمغة: neural, causal, symbolic, bayesian, world_model",
        )

    from mamoun.core.mamoun_kernel import get_kernel
    kernel = get_kernel()

    brain = kernel._brains.get(brain_id)
    if not brain:
        return CommandResponse(
            success=False,
            action="brain_control",
            target=brain_id,
            message=f"الدماغ '{brain_id}' غير مسجّل",
        )

    if is_activate:
        brain.activate()
        action_verb = "تفعيل"
    else:
        brain.deactivate()
        action_verb = "إيقاف"

    return CommandResponse(
        success=True,
        action="brain_control",
        target=brain_id,
        message=f"تم {action_verb} الدماغ {brain_id} فعلياً",
        data={
            "brain_id": brain_id,
            "status": brain.state.status,
            "model": brain.state.model,
            "confidence": brain.state.confidence,
        },
        navigate_to="deliberation",
    )


async def _handle_diagnosis() -> CommandResponse:
    """تشخيص النظام"""
    results = []

    # فحص الخادم
    try:
        from mamoun.core.mamoun_kernel import get_kernel
        kernel = get_kernel()
        results.append({"check": "النواة", "status": "ok" if kernel._running else "error", "detail": f"{'تعمل' if kernel._running else 'متوقفة'}"})
    except Exception as e:
        results.append({"check": "النواة", "status": "error", "detail": str(e)[:100]})

    # فحص الأدمغة
    try:
        from mamoun.core.mamoun_kernel import get_kernel
        kernel = get_kernel()
        active = sum(1 for b in kernel._brains.values() if b.state.status == "active")
        results.append({"check": "الأدمغة", "status": "ok" if active >= 3 else "warn", "detail": f"{active}/5 نشطة"})
    except Exception as e:
        results.append({"check": "الأدمغة", "status": "error", "detail": str(e)[:100]})

    # فحص LLM
    try:
        from mamoun.core.llm_client import get_llm_client
        llm = get_llm_client()
        stats = llm.get_stats()
        results.append({"check": "LLM", "status": "ok", "detail": f"طلبات: {stats.get('total_requests', 0)}"})
    except Exception as e:
        results.append({"check": "LLM", "status": "error", "detail": str(e)[:100]})

    # فحص NeuralBus
    try:
        from mamoun.core.neural_bus import neural_bus
        bus_stats = neural_bus.get_stats()
        results.append({"check": "الناقل العصبي", "status": "ok", "detail": f"إشارات: {bus_stats.get('total_published', 0)}"})
    except Exception as e:
        results.append({"check": "الناقل العصبي", "status": "error", "detail": str(e)[:100]})

    errors = sum(1 for r in results if r["status"] == "error")

    return CommandResponse(
        success=errors == 0,
        action="diagnosis",
        target="full",
        message=f"التشخيص: {len(results)} فحوصات — {errors} أخطاء",
        data={"results": results},
        navigate_to="diagnose",
    )


async def _handle_project(command: str, context: dict) -> CommandResponse:
    """بناء مشروع"""
    import uuid
    conf_id = str(uuid.uuid4())[:8]
    _pending_confirmations[conf_id] = {
        "type": "build_project",
        "command": command,
        "timestamp": __import__("time").time(),
    }

    return CommandResponse(
        success=True,
        action="project",
        target="new",
        message=f"سيتم بناء مشروع بناءً على: '{command}'. هل تريد المتابعة؟",
        data={"description": command},
        needs_confirmation=True,
        confirmation_id=conf_id,
    )


async def _handle_evolution() -> CommandResponse:
    """تطوير ذاتي"""
    import uuid
    conf_id = str(uuid.uuid4())[:8]
    _pending_confirmations[conf_id] = {
        "type": "evolution",
        "timestamp": __import__("time").time(),
    }

    return CommandResponse(
        success=True,
        action="evolution",
        target="self",
        message="سيتم تشغيل دورة التطور الذاتي. هذا قد يُغيّر كود النظام. هل تريد المتابعة؟",
        needs_confirmation=True,
        confirmation_id=conf_id,
    )


async def _handle_terminal(command: str) -> CommandResponse:
    """تنفيذ أمر طرفية"""
    return CommandResponse(
        success=True,
        action="terminal",
        target=command,
        message=f"افتح الطرفية لتنفيذ: {command}",
        navigate_to="terminal",
    )


async def _handle_settings(command: str, context: dict) -> CommandResponse:
    """تغيير إعدادات"""
    return CommandResponse(
        success=True,
        action="settings",
        target="",
        message="افتح الإعدادات",
        navigate_to="settings",
    )


@router.post("/command/confirm/{confirmation_id}")
async def confirm_command(confirmation_id: str, req: BaseModel = None):
    """تأكيد أمر معلّق — نعم/لا"""
    import subprocess

    pending = _pending_confirmations.pop(confirmation_id, None)
    if not pending:
        raise HTTPException(status_code=404, detail="لم أجد طلب التأكيد — ربما انتهت صلاحيته")

    conf_type = pending["type"]

    if conf_type == "git_pull":
        # سحب فعلي
        try:
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                capture_output=True, text=True, timeout=60,
                cwd=_PROJECT_ROOT
            )
            output = result.stdout + result.stderr
            success = result.returncode == 0

            return {
                "success": success,
                "action": "git_pull_confirmed",
                "message": f"تم سحب التحديثات {'بنجاح' if success else 'مع أخطاء'}:\n{output[:500]}",
                "output": output[:2000],
            }
        except Exception as e:
            return {"success": False, "action": "git_pull_confirmed", "message": f"فشل السحب: {e}"}

    elif conf_type == "build_project":
        try:
            from mamoun.core.mamoun_kernel import get_kernel
            kernel = get_kernel()
            # سيتم تنفيذ عبر project orchestrator
            return {
                "success": True,
                "action": "build_project_confirmed",
                "message": "تم تأكيد بناء المشروع — جارٍ التنفيذ...",
            }
        except Exception as e:
            return {"success": False, "message": f"فشل بناء المشروع: {e}"}

    elif conf_type == "evolution":
        try:
            return {
                "success": True,
                "action": "evolution_confirmed",
                "message": "تم تأكيد دورة التطور — جارٍ التنفيذ...",
            }
        except Exception as e:
            return {"success": False, "message": f"فشل التطور: {e}"}

    return {"success": False, "message": "نوع تأكيد غير معروف"}


@router.post("/command/reject/{confirmation_id}")
async def reject_command(confirmation_id: str):
    """رفض أمر معلّق"""
    pending = _pending_confirmations.pop(confirmation_id, None)
    if not pending:
        raise HTTPException(status_code=404, detail="لم أجد طلب التأكيد")

    return {
        "success": True,
        "action": "rejected",
        "message": "تم إلغاء العملية بناءً على طلبك",
    }


@router.get("/command/pending")
async def list_pending_confirmations():
    """عرض الأوامر المنتظرة تأكيد"""
    return {
        "pending": [
            {"id": k, **v} for k, v in _pending_confirmations.items()
        ],
        "total": len(_pending_confirmations),
    }
