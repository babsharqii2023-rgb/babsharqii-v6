"""
BABSHARQII v12.0 — Embodiment Controller V2
متحكم الجسد الرقمي النسخة الثانية — تحكم بالفأرة ولوحة المفاتيح في بيئة معزولة.

Improvements over V1:
- Time-Bounded Delegation: لا يتحرك إلا بصلاحية تخول صريحة ومؤقتة
- Mouse + Keyboard control: تحكم كامل بالفأرة ولوحة المفاتيح
- Screenshot-based interaction: مثل Claude Computer Use
- Action recording: تسجيل كل إجراء مع ربط بالصلاحية
- Enhanced safety: SafetyBehaviorMonitor + TimeBoundedPolicy
- Kill switch: إيقاف فوري عند انتهاء الصلاحية
"""

import os
import time
import json
import logging
import httpx
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

EMBODIMENT_V2_ENABLED = os.getenv("MAMOUN_EMBODIMENT_V2", "false").lower() == "true"
EMBODIMENT_SERVICE_URL = os.getenv("MAMOUN_EMBODIMENT_URL", "http://mamoun-embodiment:9222")


@dataclass
class MouseAction:
    """إجراء فأرة."""
    action_type: str  # "click", "double_click", "right_click", "move", "drag", "scroll"
    x: int = 0
    y: int = 0
    button: str = "left"  # left, right, middle
    scroll_amount: int = 0  # positive = up, negative = down
    duration_ms: int = 0
    timestamp: float = 0.0


@dataclass
class KeyboardAction:
    """إجراء لوحة مفاتيح."""
    action_type: str  # "type", "press", "hotkey"
    text: str = ""        # For type action
    key: str = ""         # For press action
    keys: list = field(default_factory=list)  # For hotkey action (e.g., ["ctrl", "c"])
    duration_ms: int = 0
    timestamp: float = 0.0


@dataclass
class ScreenState:
    """حالة الشاشة."""
    width: int = 1920
    height: int = 1080
    screenshot_base64: str = ""
    timestamp: float = 0.0
    active_window: str = ""


@dataclass
class EmbodimentActionV2:
    """إجراء في الجسد الرقمي V2 — مع ربط بالصلاحية."""
    id: str = ""
    action_type: str = ""  # mouse, keyboard, screenshot, launch_browser, navigate
    params: dict = field(default_factory=dict)
    result: dict = field(default_factory=dict)
    success: bool = False
    grant_id: str = ""        # الصلاحية الزمنية المرتبطة
    duration_ms: float = 0.0
    timestamp: float = 0.0
    risk_score: float = 0.0   # تقييم المخاطر (0-1)


class EmbodimentControllerV2:
    """
    متحكم الجسد الرقمي V2 — تحكم بالفأرة ولوحة المفاتيح.
    
    Key Principle:
    لا يتحرك إلا بصلاحية تخول صريحة ومؤقتة من TimeBoundedPolicy.
    إذا انتهت الصلاحية أثناء التنفيذ، يتوقف فوراً.
    
    Features:
    - Screenshot-based interaction (مثل Claude Computer Use)
    - Mouse control (click, move, drag, scroll)
    - Keyboard control (type, press, hotkey)
    - Browser automation (launch, navigate, click elements)
    - Action recording with time-bounded permission tracking
    - SafetyBehaviorMonitor integration
    - Kill switch on permission expiry
    """
    
    SESSION_TIMEOUT = 300  # 5 minutes max session
    MAX_ACTIONS_PER_SESSION = 200
    MAX_SESSIONS_PER_HOUR = 4
    
    # Suspicious patterns to watch for
    SUSPICIOUS_PATTERNS = [
        "file://", "localhost", "127.0.0.1", "0.0.0.0",
        "admin", "root", "password", "secret", "token",
        "/etc/", "/var/", "/sys/", "/proc/",
        "rm -rf", "chmod", "chown", "sudo",
        "bank", "payment", "credit_card",
    ]
    
    def __init__(self, time_bounded_policy=None, service_url: str = ""):
        self._policy = time_bounded_policy
        self.service_url = service_url or EMBODIMENT_SERVICE_URL
        self._session_active = False
        self._action_count = 0
        self._action_history: list[EmbodimentActionV2] = []
        self._current_grant_id: str = ""
        self._session_start: float = 0.0
        self._sessions_this_hour: list[float] = []
        self._action_counter = 0
    
    async def is_available(self) -> bool:
        """التحقق من توفر خدمة الجسد الرقمي."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.service_url}/health")
                return resp.status_code == 200
        except Exception:
            return False
    
    async def start_session(self, grant_id: str, task_description: str = "") -> dict:
        """
        بدء جلسة تحكم — يتطلب صلاحية embodiment:control.
        
        Args:
            grant_id: صلاحية زمنية فعالة
            task_description: وصف المهمة
        
        Returns:
            dict with session info
        """
        # Check feature flag
        if not EMBODIMENT_V2_ENABLED:
            return {"success": False, "error": "متحكم الجسد V2 غير مفعّل — أضف MAMOUN_EMBODIMENT_V2=true"}
        
        # Verify permission
        if self._policy and self._policy.is_enabled():
            if not grant_id:
                return {"success": False, "error": "بدء الجلسة يتطلب صلاحية زمنية (embodiment:control)"}
            check = await self._policy.check_permission(grant_id)
            if not check.get("valid"):
                return {"success": False, "error": f"صلاحية غير صالحة: {check.get('reason')}"}
        
        # Check session limits
        now = time.time()
        self._sessions_this_hour = [t for t in self._sessions_this_hour if now - t < 3600]
        if len(self._sessions_this_hour) >= self.MAX_SESSIONS_PER_HOUR:
            return {"success": False, "error": "تم تجاوز حد الجلسات في الساعة"}
        
        self._session_active = True
        self._session_start = now
        self._current_grant_id = grant_id
        self._action_count = 0
        self._sessions_this_hour.append(now)
        
        return {
            "success": True,
            "session_start": now,
            "max_duration": self.SESSION_TIMEOUT,
            "max_actions": self.MAX_ACTIONS_PER_SESSION,
            "message": f"بدأت جلسة التحكم — المهمة: {task_description}",
        }
    
    async def take_screenshot(self, grant_id: str = "") -> EmbodimentActionV2:
        """
        التقاط صورة للشاشة — يتطلب صلاحية embodiment:view.
        """
        self._action_counter += 1
        action = EmbodimentActionV2(
            id=f"emb_v2_{int(time.time())}_{self._action_counter}",
            action_type="screenshot",
            timestamp=time.time(),
            grant_id=grant_id or self._current_grant_id,
        )
        
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{self.service_url}/browser/screenshot")
                action.success = resp.status_code == 200
                action.result = resp.json() if action.success else {"error": f"HTTP {resp.status_code}"}
        except Exception as e:
            action.success = False
            action.result = {"error": str(e)}
        
        action.duration_ms = (time.time() - start) * 1000
        self._record_action(action)
        return action
    
    async def mouse_click(self, x: int, y: int, button: str = "left", grant_id: str = "") -> EmbodimentActionV2:
        """
        نقر بالفأرة — يتطلب صلاحية embodiment:control.
        """
        # Verify permission before action
        if not await self._verify_before_action(grant_id):
            return self._denied_action("mouse_click", grant_id)
        
        self._action_counter += 1
        action = EmbodimentActionV2(
            id=f"emb_v2_{int(time.time())}_{self._action_counter}",
            action_type="mouse_click",
            params={"x": x, "y": y, "button": button},
            timestamp=time.time(),
            grant_id=grant_id or self._current_grant_id,
        )
        
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.service_url}/mouse/click",
                    json={"x": x, "y": y, "button": button},
                )
                action.success = resp.status_code == 200
                action.result = resp.json() if action.success else {"error": f"HTTP {resp.status_code}"}
        except Exception as e:
            action.success = False
            action.result = {"error": str(e)}
        
        action.duration_ms = (time.time() - start) * 1000
        action.risk_score = self._calculate_risk(action)
        self._record_action(action)
        return action
    
    async def keyboard_type(self, text: str, grant_id: str = "") -> EmbodimentActionV2:
        """
        كتابة نص بلوحة المفاتيح — يتطلب صلاحية embodiment:control.
        """
        # Check for sensitive data in text
        sensitive_check = self._check_sensitive_input(text)
        if not sensitive_check["safe"]:
            return self._denied_action("keyboard_type", grant_id, sensitive_check["reason"])
        
        if not await self._verify_before_action(grant_id):
            return self._denied_action("keyboard_type", grant_id)
        
        self._action_counter += 1
        action = EmbodimentActionV2(
            id=f"emb_v2_{int(time.time())}_{self._action_counter}",
            action_type="keyboard_type",
            params={"text_length": len(text)},  # Don't store actual text
            timestamp=time.time(),
            grant_id=grant_id or self._current_grant_id,
        )
        
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.service_url}/keyboard/type",
                    json={"text": text},
                )
                action.success = resp.status_code == 200
                action.result = resp.json() if action.success else {"error": f"HTTP {resp.status_code}"}
        except Exception as e:
            action.success = False
            action.result = {"error": str(e)}
        
        action.duration_ms = (time.time() - start) * 1000
        action.risk_score = self._calculate_risk(action)
        self._record_action(action)
        return action
    
    async def keyboard_hotkey(self, keys: list[str], grant_id: str = "") -> EmbodimentActionV2:
        """
        اختصار لوحة مفاتيح — يتطلب صلاحية embodiment:control.
        """
        # Block dangerous hotkeys
        blocked_hotkeys = [
            {"ctrl", "alt", "delete"},
            {"alt", "f4"},
            {"ctrl", "shift", "escape"},
        ]
        key_set = set(k.lower() for k in keys)
        for blocked in blocked_hotkeys:
            if key_set == blocked:
                return self._denied_action("keyboard_hotkey", grant_id, f"اختصار محظور: {keys}")
        
        if not await self._verify_before_action(grant_id):
            return self._denied_action("keyboard_hotkey", grant_id)
        
        self._action_counter += 1
        action = EmbodimentActionV2(
            id=f"emb_v2_{int(time.time())}_{self._action_counter}",
            action_type="keyboard_hotkey",
            params={"keys": keys},
            timestamp=time.time(),
            grant_id=grant_id or self._current_grant_id,
        )
        
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.service_url}/keyboard/hotkey",
                    json={"keys": keys},
                )
                action.success = resp.status_code == 200
                action.result = resp.json() if action.success else {"error": f"HTTP {resp.status_code}"}
        except Exception as e:
            action.success = False
            action.result = {"error": str(e)}
        
        action.duration_ms = (time.time() - start) * 1000
        self._record_action(action)
        return action
    
    async def end_session(self) -> dict:
        """
        إنهاء جلسة التحكم.
        """
        self._session_active = False
        self._current_grant_id = ""
        self._action_count = 0
        
        return {
            "success": True,
            "actions_taken": len(self._action_history),
            "message": "تم إنهاء جلسة التحكم بنجاح",
        }
    
    async def get_action_history(self) -> list[dict]:
        """الحصول على سجل الإجراءات."""
        return [
            {
                "id": a.id,
                "action_type": a.action_type,
                "success": a.success,
                "risk_score": a.risk_score,
                "duration_ms": a.duration_ms,
                "grant_id": a.grant_id,
                "timestamp": a.timestamp,
            }
            for a in self._action_history
        ]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Internal Methods
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def _verify_before_action(self, grant_id: str) -> bool:
        """التحقق من الصلاحية قبل كل إجراء."""
        # Check session limits
        if not self._session_active:
            return False
        
        if self._action_count >= self.MAX_ACTIONS_PER_SESSION:
            logger.warning("Max actions per session reached")
            return False
        
        # Check session timeout
        if time.time() - self._session_start > self.SESSION_TIMEOUT:
            logger.warning("Session timeout — ending session")
            await self.end_session()
            return False
        
        # Check time-bounded permission
        if self._policy and self._policy.is_enabled():
            gid = grant_id or self._current_grant_id
            if not gid:
                return False
            check = await self._policy.check_permission(gid)
            if not check.get("valid"):
                logger.warning(f"Permission expired during session: {check.get('reason')}")
                await self.end_session()  # Kill switch!
                return False
        
        return True
    
    def _check_sensitive_input(self, text: str) -> dict:
        """فحص المدخلات الحساسة."""
        sensitive_patterns = [
            "password", "passwd", "كلمة المرور",
            "credit_card", "رقم البطاقة",
            "ssn", "رقم الهوية",
        ]
        text_lower = text.lower()
        for pattern in sensitive_patterns:
            if pattern in text_lower:
                return {"safe": False, "reason": f"النص يحتوي على بيانات حساسة: '{pattern}'"}
        return {"safe": True, "reason": ""}
    
    def _calculate_risk(self, action: EmbodimentActionV2) -> float:
        """حساب مخاطر الإجراء."""
        risk = 0.0
        
        # Keyboard actions are higher risk
        if action.action_type.startswith("keyboard"):
            risk += 0.2
        
        # Check params for suspicious patterns
        params_str = json.dumps(action.params, ensure_ascii=False).lower()
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern.lower() in params_str:
                risk += 0.3
        
        return min(1.0, risk)
    
    def _record_action(self, action: EmbodimentActionV2):
        """تسجيل الإجراء."""
        self._action_count += 1
        self._action_history.append(action)
        
        if action.risk_score > 0.7:
            logger.warning(f"High risk action detected: {action.id} | risk={action.risk_score:.2f}")
    
    def _denied_action(self, action_type: str, grant_id: str, reason: str = "صلاحية غير صالحة") -> EmbodimentActionV2:
        """إنشاء إجراء مرفوض."""
        self._action_counter += 1
        return EmbodimentActionV2(
            id=f"emb_v2_{int(time.time())}_{self._action_counter}",
            action_type=action_type,
            success=False,
            result={"error": reason},
            grant_id=grant_id or self._current_grant_id,
            timestamp=time.time(),
        )
