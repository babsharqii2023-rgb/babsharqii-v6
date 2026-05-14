"""
BABSHARQII v38.0 — Feature Flag Runtime Manager
مدير الميزات الحي — يتحكم بكل الميزات بدون إعادة تشغيل

الطبقة 2 من آلية التحكم الشاملة:
- يستبدل كل MAMOUN_* env vars بـ runtime flags
- تفعيل/إيقاف فوري عبر API
- يربط كل ميزة بـ 154 feature في الواجهة
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("mamoun.api.feature_flags")

# مسار تخزين حالة الميزات
_FLAGS_FILE = Path(__file__).parent.parent.parent / "data" / "feature_flags.json"


class FeatureFlagManager:
    """مدير الميزات الحي — تفعيل/إيقاف فوري بدون restart"""

    # تعريف كل الميزات المتاحة مع بياناتها
    FLAG_DEFINITIONS = {
        "MAMOUN_TRADING": {
            "label_ar": "التداول",
            "label_en": "Trading Engine",
            "description": "محرك التداول الآلي — يتصل بأسواق المال",
            "category": "capabilities",
            "endpoint": "/api/capabilities/trading/overview",
            "page": "trading",
            "icon": "📈",
            "risk_level": "high",
        },
        "MAMOUN_INSTAGRAM_AUTOMATION": {
            "label_ar": "انستقرام",
            "label_en": "Instagram Automation",
            "description": "إدارة حساب انستقرام تلقائياً",
            "category": "capabilities",
            "endpoint": "/api/capabilities/instagram/status",
            "page": "instagram",
            "icon": "📸",
            "risk_level": "medium",
        },
        "MAMOUN_ECOMMERCE_MODE": {
            "label_ar": "المتجر الإلكتروني",
            "label_en": "E-Commerce",
            "description": "بناء وإدارة متجر إلكتروني",
            "category": "capabilities",
            "endpoint": "/api/capabilities/ecommerce/status",
            "page": "ecommerce",
            "icon": "🛒",
            "risk_level": "medium",
        },
        "MAMOUN_BLENDER": {
            "label_ar": "بلندر ثلاثي الأبعاد",
            "label_en": "Blender 3D",
            "description": "التحكم بـ Blender لإنشاء تصاميم ثلاثية الأبعاد",
            "category": "capabilities",
            "endpoint": "/api/capabilities/blender/status",
            "page": "blender",
            "icon": "🎨",
            "risk_level": "low",
        },
        "MAMOUN_ROBOT_CONTROL": {
            "label_ar": "الروبوت",
            "label_en": "Robot Control",
            "description": "التحكم بروبوت فعلي أو محاكى",
            "category": "capabilities",
            "endpoint": "/api/embodiment/status",
            "page": "embodiment",
            "icon": "🤖",
            "risk_level": "high",
        },
        "MAMOUN_IOT_GATEWAY": {
            "label_ar": "أجهزة IoT",
            "label_en": "IoT Gateway",
            "description": "التحكم بأجهزة الإنترنت الذكية",
            "category": "capabilities",
            "endpoint": "/api/embodiment/status",
            "page": "embodiment",
            "icon": "🏠",
            "risk_level": "medium",
        },
        "MAMOUN_MOBILE_BUILDER": {
            "label_ar": "بناء التطبيقات",
            "label_en": "Mobile App Builder",
            "description": "بناء تطبيقات موبايل تلقائياً",
            "category": "capabilities",
            "endpoint": "/api/capabilities/mobile/status",
            "page": "mobile",
            "icon": "📱",
            "risk_level": "low",
        },
        "MAMOUN_SELF_PROGRAMMING": {
            "label_ar": "البرمجة الذاتية",
            "label_en": "Self-Programming",
            "description": "تعديل الكود ذاتياً مع sandbox وapproval",
            "category": "core",
            "endpoint": "/api/v24/self-modify/status",
            "page": "self-modify",
            "icon": "🧬",
            "risk_level": "critical",
        },
        "MAMOUN_AUTO_EVOLVE": {
            "label_ar": "التطور التلقائي",
            "label_en": "Auto-Evolve",
            "description": "دورات تطور ذاتي دورية",
            "category": "core",
            "endpoint": "/api/evolution/current",
            "page": "evolution",
            "icon": "🧪",
            "risk_level": "critical",
        },
        "MAMOUN_AGENT_BROWSER": {
            "label_ar": "متصفح الوكيل",
            "label_en": "Agent Browser",
            "description": "تصفح الويب تلقائياً",
            "category": "capabilities",
            "endpoint": "/api/capabilities/browser/status",
            "page": "browser",
            "icon": "🌐",
            "risk_level": "medium",
        },
        "MAMOUN_LAPTOP_CONTROL": {
            "label_ar": "تحكم بالحاسوب",
            "label_en": "Laptop Control",
            "description": "التحكم بحاسوب المستخدم",
            "category": "capabilities",
            "endpoint": "/api/capabilities/laptop-control/status",
            "page": "laptop",
            "icon": "💻",
            "risk_level": "critical",
        },
    }

    def __init__(self):
        self._flags: dict[str, bool] = {}
        self._history: list[dict] = []
        self._load()

    def _load(self):
        """تحميل حالة الميزات من الملف + env vars"""
        # أولاً: من env vars (القيمة الابتدائية)
        for flag_name in self.FLAG_DEFINITIONS:
            env_val = os.getenv(flag_name, "false").lower()
            self._flags[flag_name] = env_val in ("true", "1", "yes")

        # ثانياً: من ملف الحالة (يتجاوز env vars إذا وجد)
        if _FLAGS_FILE.exists():
            try:
                with open(_FLAGS_FILE) as f:
                    saved = json.load(f)
                for k, v in saved.get("flags", {}).items():
                    if k in self.FLAG_DEFINITIONS:
                        self._flags[k] = v
                self._history = saved.get("history", [])[-50:]
            except Exception as e:
                logger.warning(f"Failed to load feature flags: {e}")

    def _save(self):
        """حفظ حالة الميزات"""
        _FLAGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(_FLAGS_FILE, "w") as f:
                json.dump({
                    "flags": self._flags,
                    "history": self._history[-50:],
                    "last_updated": time.time(),
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save feature flags: {e}")

    def get_all(self) -> dict:
        """الحصول على كل الميزات وحالتها"""
        result = {}
        for flag_name, definition in self.FLAG_DEFINITIONS.items():
            result[flag_name] = {
                **definition,
                "enabled": self._flags.get(flag_name, False),
                "env_value": os.getenv(flag_name, "false"),
                "runtime_value": self._flags.get(flag_name, False),
            }
        return result

    def get(self, flag_name: str) -> bool:
        """الحصول على حالة ميزة واحدة"""
        return self._flags.get(flag_name, False)

    async def toggle(self, flag_name: str, enabled: Optional[bool] = None) -> bool:
        """
        تبديل ميزة فورياً — بدون إعادة تشغيل

        Args:
            flag_name: اسم الميزة (مثل MAMOUN_TRADING)
            enabled: True=تفعيل, False=إيقاف, None=عكس الحالة

        Returns:
            الحالة الجديدة
        """
        if flag_name not in self.FLAG_DEFINITIONS:
            raise ValueError(f"ميزة غير معروفة: {flag_name}")

        current = self._flags.get(flag_name, False)
        new_state = enabled if enabled is not None else not current

        if new_state == current:
            return current

        # تسجيل التغيير
        self._history.append({
            "flag": flag_name,
            "from": current,
            "to": new_state,
            "timestamp": time.time(),
        })

        # تطبيق التغيير
        self._flags[flag_name] = new_state

        # تحديث env var فعلياً (للتوافق مع الكود القديم)
        os.environ[flag_name] = "true" if new_state else "false"

        # حفظ
        self._save()

        # إرسال إشارة عبر NeuralBus
        try:
            from mamoun.core.neural_bus import neural_bus
            neural_bus.publish({
                "type": "vital_change" if new_state else "energy_drop",
                "source": "feature_flag_manager",
                "data": {"flag": flag_name, "enabled": new_state},
                "priority": 2,
            })
        except Exception:
            pass

        logger.info(f"Feature flag {flag_name} changed: {current} → {new_state}")
        return new_state

    def get_history(self, limit: int = 20) -> list[dict]:
        """سجل تغييرات الميزات"""
        return self._history[-limit:]


# Singleton
feature_flag_manager = FeatureFlagManager()


# ═══ FastAPI Router ═══

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/v2/feature-flags", tags=["feature_flags"])


class ToggleRequest(BaseModel):
    enabled: bool


@router.get("")
async def get_all_flags():
    """عرض كل الميزات وحالتها"""
    flags = feature_flag_manager.get_all()
    return {
        "flags": flags,
        "total": len(flags),
        "active": sum(1 for f in flags.values() if f["enabled"]),
        "categories": list(set(f["category"] for f in flags.values())),
    }


@router.get("/{flag_name}")
async def get_flag(flag_name: str):
    """عرض حالة ميزة واحدة"""
    flags = feature_flag_manager.get_all()
    if flag_name not in flags:
        raise HTTPException(status_code=404, detail=f"ميزة غير معروفة: {flag_name}")
    return flags[flag_name]


@router.post("/{flag_name}/toggle")
async def toggle_flag(flag_name: str, req: ToggleRequest):
    """تبديل ميزة فورياً"""
    try:
        new_state = await feature_flag_manager.toggle(flag_name, req.enabled)
        definition = feature_flag_manager.FLAG_DEFINITIONS.get(flag_name, {})
        return {
            "success": True,
            "flag": flag_name,
            "enabled": new_state,
            "label_ar": definition.get("label_ar", ""),
            "message": f"تم {'تفعيل' if new_state else 'إيقاف'} {definition.get('label_ar', flag_name)}",
            "navigate_to": definition.get("page", "") if new_state else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{flag_name}/enable")
async def enable_flag(flag_name: str):
    """تفعيل ميزة"""
    return await toggle_flag(flag_name, ToggleRequest(enabled=True))


@router.post("/{flag_name}/disable")
async def disable_flag(flag_name: str):
    """إيقاف ميزة"""
    return await toggle_flag(flag_name, ToggleRequest(enabled=False))


@router.get("/history")
async def get_flag_history():
    """سجل تغييرات الميزات"""
    return {
        "history": feature_flag_manager.get_history(),
        "total": len(feature_flag_manager.get_history()),
    }


@router.get("/by-category/{category}")
async def get_flags_by_category(category: str):
    """عرض ميزات فئة معينة"""
    all_flags = feature_flag_manager.get_all()
    filtered = {k: v for k, v in all_flags.items() if v["category"] == category}
    return {"flags": filtered, "total": len(filtered)}
