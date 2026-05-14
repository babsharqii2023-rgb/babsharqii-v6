"""
BABSHARQII v21.0 — Embodiment Service (خدمة التحكم بالجسد الرقمي)
خادم FastAPI حقيقي يتيح لمامون التحكم بالشاشة والفأرة ولوحة المفاتيح

يعمل كخدمة مستقلة يمكن تشغيلها مع النظام أو منفصلة.
يستخدم pyautogui + Pillow للتحكم الفعلي بالحاسوب.

REST API Endpoints:
  GET  /health                    — فحص الصحة
  POST /browser/screenshot        — التقاط صورة الشاشة
  POST /mouse/click               — نقر بالفأرة
  POST /mouse/move                — تحريك الفأرة
  POST /mouse/drag                — سحب بالفأرة
  POST /mouse/scroll              — تمرير بالفأرة
  POST /keyboard/type             — كتابة نص
  POST /keyboard/press            — ضغط مفتاح
  POST /keyboard/hotkey           — اختصار لوحة مفاتيح
  POST /screen/info               — معلومات الشاشة
  POST /session/start             — بدء جلسة تحكم
  POST /session/end               — إنهاء جلسة تحكم

Safety:
  - كل جلسة محدودة المدة (5 دقائق كحد أقصى)
  - كل إجراء مسجّل في سجل المراجعة
  - أوامر خطيرة محظورة (Ctrl+Alt+Del, Alt+F4, إلخ)
  - يمكن إيقاف الطوارئ فوراً عبر /emergency/stop
"""

import asyncio
import base64
import io
import json
import time
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from enum import Enum

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger("mamoun.embodiment_service")

# ═══════════════════════════════════════════════════════════════════════════════
# محرك التحكم الفعلي — باستخدام pyautogui + Pillow
# ═══════════════════════════════════════════════════════════════════════════════

class EmbodimentController:
    """متحكم فعلي بالحاسوب — يتحكم بالفأرة ولوحة المفاتيح ولقطات الشاشة"""

    MAX_SESSION_DURATION = 300  # 5 دقائق
    MAX_ACTIONS_PER_SESSION = 500
    MAX_SESSIONS_PER_HOUR = 10

    BLOCKED_HOTKEYS = [
        {"ctrl", "alt", "delete"},
        {"alt", "f4"},
        {"ctrl", "shift", "escape"},
        {"alt", "tab"},
    ]

    def __init__(self):
        self._pyautogui = None
        self._pillow = None
        self._session_active = False
        self._session_start = 0.0
        self._action_count = 0
        self._sessions_this_hour: list[float] = []
        self._audit_log: list[dict] = []
        self._action_counter = 0
        self._initialized = False

    def initialize(self) -> bool:
        """تهيئة المكتبات"""
        if self._initialized:
            return True
        try:
            import pyautogui
            pyautogui.FAILSAFE = True  # تحريك الفأرة للزاوية يوقف كل شيء
            pyautogui.PAUSE = 0.05  # وقفة صغيرة بين الأوامر للأمان
            self._pyautogui = pyautogui

            from PIL import ImageGrab
            self._pillow = ImageGrab

            self._initialized = True
            logger.info("EmbodimentController initialized — pyautogui + Pillow ready")
            return True
        except ImportError as e:
            logger.error("Missing dependencies: %s — install: pip install pyautogui Pillow", e)
            return False

    @property
    def is_available(self) -> bool:
        return self._initialized

    # ─── Session Management ─────────────────────────────────────────────────

    def start_session(self, task_description: str = "") -> dict:
        """بدء جلسة تحكم"""
        if not self._initialized:
            return {"success": False, "error": "المتحكم غير مهيأ — ثبّت pyautogui و Pillow"}

        now = time.time()
        self._sessions_this_hour = [t for t in self._sessions_this_hour if now - t < 3600]

        if len(self._sessions_this_hour) >= self.MAX_SESSIONS_PER_HOUR:
            return {"success": False, "error": "تم تجاوز حد الجلسات في الساعة"}

        if self._session_active:
            return {"success": False, "error": "يوجد جلسة نشطة بالفعل"}

        self._session_active = True
        self._session_start = now
        self._action_count = 0
        self._sessions_this_hour.append(now)

        self._audit("session_start", {"task": task_description})

        return {
            "success": True,
            "session_start": now,
            "max_duration": self.MAX_SESSION_DURATION,
            "max_actions": self.MAX_ACTIONS_PER_SESSION,
            "message": f"بدأت جلسة التحكم — المهمة: {task_description}",
        }

    def end_session(self) -> dict:
        """إنهاء جلسة التحكم"""
        duration = time.time() - self._session_start if self._session_active else 0
        self._session_active = False
        self._session_start = 0
        self._action_count = 0

        self._audit("session_end", {"duration": round(duration, 2)})
        return {"success": True, "duration_seconds": round(duration, 2)}

    def emergency_stop(self) -> dict:
        """إيقاف طوارئ — ينهي الجلسة فوراً"""
        self._session_active = False
        self._audit("emergency_stop", {})
        logger.warning("EMERGENCY STOP activated!")
        return {"success": True, "message": "تم الإيقاف الطارئ — الجلسة منتهية"}

    def _check_session(self) -> bool:
        """التحقق من صلاحية الجلسة"""
        if not self._session_active:
            return False
        if time.time() - self._session_start > self.MAX_SESSION_DURATION:
            self.end_session()
            return False
        if self._action_count >= self.MAX_ACTIONS_PER_SESSION:
            self.end_session()
            return False
        return True

    # ─── Screenshot ─────────────────────────────────────────────────────────

    def take_screenshot(self) -> dict:
        """التقاط صورة للشاشة"""
        if not self._check_session():
            return {"success": False, "error": "لا توجد جلسة نشطة"}

        try:
            img = self._pillow.grab()
            buffer = io.BytesIO()
            img.save(buffer, format="PNG", optimize=True)
            img_bytes = buffer.getvalue()
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")

            self._action_count += 1
            self._audit("screenshot", {"size_bytes": len(img_bytes), "width": img.width, "height": img.height})

            return {
                "success": True,
                "image_base64": img_b64,
                "width": img.width,
                "height": img.height,
                "size_bytes": len(img_bytes),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_screen_info(self) -> dict:
        """معلومات الشاشة"""
        try:
            size = self._pyautogui.size()
            return {
                "success": True,
                "width": size.width,
                "height": size.height,
                "pixel_ratio": 1.0,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ─── Mouse Control ──────────────────────────────────────────────────────

    def mouse_click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> dict:
        """نقر بالفأرة"""
        if not self._check_session():
            return {"success": False, "error": "لا توجد جلسة نشطة"}

        try:
            self._pyautogui.click(x=x, y=y, button=button, clicks=clicks)
            self._action_count += 1
            self._audit("mouse_click", {"x": x, "y": y, "button": button, "clicks": clicks})
            return {"success": True, "x": x, "y": y, "button": button}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def mouse_move(self, x: int, y: int, duration: float = 0.3) -> dict:
        """تحريك الفأرة"""
        if not self._check_session():
            return {"success": False, "error": "لا توجد جلسة نشطة"}

        try:
            self._pyautogui.moveTo(x=x, y=y, duration=duration)
            self._action_count += 1
            self._audit("mouse_move", {"x": x, "y": y, "duration": duration})
            return {"success": True, "x": x, "y": y}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def mouse_drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5, button: str = "left") -> dict:
        """سحب بالفأرة"""
        if not self._check_session():
            return {"success": False, "error": "لا توجد جلسة نشطة"}

        try:
            self._pyautogui.moveTo(start_x, start_y)
            self._pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration, button=button)
            self._action_count += 1
            self._audit("mouse_drag", {"start": [start_x, start_y], "end": [end_x, end_y]})
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def mouse_scroll(self, x: int, y: int, amount: int = 3) -> dict:
        """تمرير بالفأرة"""
        if not self._check_session():
            return {"success": False, "error": "لا توجد جلسة نشطة"}

        try:
            self._pyautogui.scroll(amount, x=x, y=y)
            self._action_count += 1
            self._audit("mouse_scroll", {"x": x, "y": y, "amount": amount})
            return {"success": True, "amount": amount}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ─── Keyboard Control ───────────────────────────────────────────────────

    def keyboard_type(self, text: str, interval: float = 0.02) -> dict:
        """كتابة نص بلوحة المفاتيح"""
        if not self._check_session():
            return {"success": False, "error": "لا توجد جلسة نشطة"}

        # فحص المحتوى الحساس
        sensitive = ["password", "passwd", "كلمة المرور", "credit_card", "رقم البطاقة"]
        for s in sensitive:
            if s in text.lower():
                return {"success": False, "error": f"النص يحتوي على بيانات حساسة: '{s}'"}

        try:
            self._pyautogui.typewrite(text, interval=interval) if text.isascii() else self._pyautogui.write(text, interval=interval)
            self._action_count += 1
            self._audit("keyboard_type", {"length": len(text)})
            return {"success": True, "chars_typed": len(text)}
        except Exception as e:
            # Fallback: try with pyperclip for non-ASCII
            try:
                import pyperclip
                pyperclip.copy(text)
                self._pyautogui.hotkey('ctrl', 'v')
                self._action_count += 1
                self._audit("keyboard_type_clipboard", {"length": len(text)})
                return {"success": True, "chars_typed": len(text), "method": "clipboard"}
            except Exception as e2:
                return {"success": False, "error": f"{str(e)} | clipboard fallback: {str(e2)}"}

    def keyboard_press(self, key: str) -> dict:
        """ضغط مفتاح"""
        if not self._check_session():
            return {"success": False, "error": "لا توجد جلسة نشطة"}

        try:
            self._pyautogui.press(key)
            self._action_count += 1
            self._audit("keyboard_press", {"key": key})
            return {"success": True, "key": key}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def keyboard_hotkey(self, keys: list[str]) -> dict:
        """اختصار لوحة مفاتيح"""
        if not self._check_session():
            return {"success": False, "error": "لا توجد جلسة نشطة"}

        # فحص الاختصارات المحظورة
        key_set = set(k.lower() for k in keys)
        for blocked in self.BLOCKED_HOTKEYS:
            if key_set == blocked:
                return {"success": False, "error": f"اختصار محظور: {keys}"}

        try:
            self._pyautogui.hotkey(*keys)
            self._action_count += 1
            self._audit("keyboard_hotkey", {"keys": keys})
            return {"success": True, "keys": keys}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ─── Utilities ───────────────────────────────────────────────────────────

    def get_mouse_position(self) -> dict:
        """الحصول على موقع الفأرة الحالي"""
        try:
            pos = self._pyautogui.position()
            return {"success": True, "x": pos.x, "y": pos.y}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_status(self) -> dict:
        """حالة المتحكم"""
        return {
            "initialized": self._initialized,
            "session_active": self._session_active,
            "action_count": self._action_count,
            "session_duration": round(time.time() - self._session_start, 2) if self._session_active else 0,
            "sessions_this_hour": len(self._sessions_this_hour),
            "audit_log_size": len(self._audit_log),
        }

    def get_audit_log(self, limit: int = 50) -> list[dict]:
        """سجل المراجعة"""
        return self._audit_log[-limit:]

    def _audit(self, action: str, details: dict):
        """تسجيل إجراء"""
        self._audit_log.append({
            "action": action,
            "details": details,
            "timestamp": time.time(),
            "timestamp_iso": datetime.now(timezone.utc).isoformat(),
            "session_action_count": self._action_count,
        })


# ═══════════════════════════════════════════════════════════════════════════════
# FastAPI Application
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Mamoun Embodiment Service",
    description="خدمة التحكم بالجسد الرقمي — التحكم بالشاشة والفأرة ولوحة المفاتيح",
    version="21.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

controller = EmbodimentController()


@app.on_event("startup")
async def startup():
    controller.initialize()


# ─── Request Models ──────────────────────────────────────────────────────────

class SessionRequest(BaseModel):
    task_description: str = ""

class MouseClickRequest(BaseModel):
    x: int
    y: int
    button: str = "left"
    clicks: int = 1

class MouseMoveRequest(BaseModel):
    x: int
    y: int
    duration: float = 0.3

class MouseDragRequest(BaseModel):
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    duration: float = 0.5
    button: str = "left"

class MouseScrollRequest(BaseModel):
    x: int
    y: int
    amount: int = 3

class KeyboardTypeRequest(BaseModel):
    text: str
    interval: float = 0.02

class KeyboardPressRequest(BaseModel):
    key: str

class KeyboardHotkeyRequest(BaseModel):
    keys: list[str]


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "mamoun-embodiment",
        "version": "21.0.0",
        "controller_initialized": controller.is_available,
    }

@app.post("/session/start")
async def session_start(req: SessionRequest):
    return controller.start_session(req.task_description)

@app.post("/session/end")
async def session_end():
    return controller.end_session()

@app.post("/emergency/stop")
async def emergency_stop():
    return controller.emergency_stop()

@app.post("/browser/screenshot")
async def screenshot():
    result = controller.take_screenshot()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Screenshot failed"))
    return result

@app.get("/screen/info")
async def screen_info():
    return controller.get_screen_info()

@app.get("/mouse/position")
async def mouse_position():
    return controller.get_mouse_position()

@app.post("/mouse/click")
async def mouse_click(req: MouseClickRequest):
    return controller.mouse_click(req.x, req.y, req.button, req.clicks)

@app.post("/mouse/move")
async def mouse_move(req: MouseMoveRequest):
    return controller.mouse_move(req.x, req.y, req.duration)

@app.post("/mouse/drag")
async def mouse_drag(req: MouseDragRequest):
    return controller.mouse_drag(req.start_x, req.start_y, req.end_x, req.end_y, req.duration, req.button)

@app.post("/mouse/scroll")
async def mouse_scroll(req: MouseScrollRequest):
    return controller.mouse_scroll(req.x, req.y, req.amount)

@app.post("/keyboard/type")
async def keyboard_type(req: KeyboardTypeRequest):
    return controller.keyboard_type(req.text, req.interval)

@app.post("/keyboard/press")
async def keyboard_press(req: KeyboardPressRequest):
    return controller.keyboard_press(req.key)

@app.post("/keyboard/hotkey")
async def keyboard_hotkey(req: KeyboardHotkeyRequest):
    return controller.keyboard_hotkey(req.keys)

@app.get("/status")
async def status():
    return controller.get_status()

@app.get("/audit/log")
async def audit_log(limit: int = 50):
    return controller.get_audit_log(limit)


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton for import by other modules
# ═══════════════════════════════════════════════════════════════════════════════

_embodiment_controller: Optional[EmbodimentController] = None

def get_embodiment_controller() -> EmbodimentController:
    global _embodiment_controller
    if _embodiment_controller is None:
        _embodiment_controller = EmbodimentController()
        _embodiment_controller.initialize()
    return _embodiment_controller


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("EMBODIMENT_PORT", "9222"))
    uvicorn.run(app, host="0.0.0.0", port=port)
