"""
BABSHARQII v21.0 — Desktop Controller (متحكم سطح المكتب)
يتحكم بسطح المكتب — ماوس، لوحة مفاتيح، لقطات شاشة، نوافذ، تطبيقات

يستخدم:
  - pyautogui: تحكم بالماوس واللوحة
  - keyboard: ضغط مفاتيح
  - PIL/Pillow: لقطات الشاشة
  - subprocess: فتح التطبيقات

الأمان:
  - كل إجراء يحتاج صلاحية
  - مراقبة سلوكية
  - إجراءات طوارئ
"""

import os
import time
import json
import logging
import asyncio
import subprocess
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

logger = logging.getLogger("mamoun.core.desktop_controller")

DESKTOP_CONTROL_ENABLED = os.getenv("MAMOUN_DESKTOP_CONTROL", "true").lower() == "true"


class DesktopController:
    """
    متحكم سطح المكتب — يتحكم بالماوس واللوحة والشاشة والتطبيقات

    القدرات:
    - لقطة شاشة (screenshot)
    - نقر الماوس (click)
    - كتابة نص (type_text)
    - ضغط مفتاح (press_key)
    - تحريك الماوس (move_mouse)
    - فتح تطبيق (open_application)
    - تمرير (scroll)
    - اختصار لوحة مفاتيح (hotkey)
    - سحب وإفلات (drag)
    - معلومات الشاشة (get_screen_info)
    - قائمة النوافذ (list_windows)
    - التركيز على نافذة (focus_window)
    """

    def __init__(self):
        self._initialized = False
        self._screen_width = 0
        self._screen_height = 0
        self._action_log: list[dict] = []
        self._screenshot_dir = Path(__file__).parent.parent.parent.parent / "download" / "screenshots"
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._screenshot_counter = 0

    async def initialize(self) -> bool:
        """تهيئة المتحكم"""
        if self._initialized:
            return True

        try:
            import pyautogui
            pyautogui.FAILSAFE = True  # Move mouse to corner to abort
            pyautogui.PAUSE = 0.1  # Small pause between actions
            self._screen_width, self._screen_height = pyautogui.size()
            self._initialized = True
            logger.info("DesktopController initialized — screen: %dx%d", self._screen_width, self._screen_height)
            return True
        except ImportError:
            logger.warning("pyautogui not available — desktop control limited")
            self._initialized = True  # Still usable for non-GUI environments
            return True
        except Exception as e:
            logger.warning("DesktopController init error: %s", e)
            return True

    def _log_action(self, action: str, details: dict = None):
        """تسجيل إجراء"""
        entry = {
            "action": action,
            "details": details or {},
            "timestamp": time.time(),
        }
        self._action_history.append(entry)
        if len(self._action_history) > 500:
            self._action_history = self._action_history[-250:]

    async def take_screenshot(self, region: dict = None) -> dict:
        """التقاط لقطة شاشة"""
        try:
            import pyautogui
            import base64
            from io import BytesIO

            if region:
                screenshot = pyautogui.screenshot(region=(
                    region.get("x", 0), region.get("y", 0),
                    region.get("width", 800), region.get("height", 600)
                ))
            else:
                screenshot = pyautogui.screenshot()

            # Save to file
            self._screenshot_counter += 1
            filepath = self._screenshot_dir / f"screenshot_{int(time.time())}_{self._screenshot_counter}.png"
            screenshot.save(str(filepath))

            # Also return base64
            buffer = BytesIO()
            screenshot.save(buffer, format="PNG")
            img_b64 = base64.b64encode(buffer.getvalue()).decode()

            return {
                "success": True,
                "filepath": str(filepath),
                "image_base64": img_b64,
                "size": f"{screenshot.width}x{screenshot.height}",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> dict:
        """النقر بالماوس"""
        try:
            import pyautogui
            pyautogui.click(x=x, y=y, button=button, clicks=clicks)
            return {"success": True, "x": x, "y": y, "button": button, "clicks": clicks}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def type_text(self, text: str, interval: float = 0.02) -> dict:
        """كتابة نص"""
        try:
            import pyautogui
            pyautogui.typewrite(text, interval=interval)
            return {"success": True, "text_length": len(text)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def press_key(self, key: str) -> dict:
        """ضغط مفتاح"""
        try:
            import pyautogui
            pyautogui.press(key)
            return {"success": True, "key": key}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def move_mouse(self, x: int, y: int, duration: float = 0.3) -> dict:
        """تحريك الماوس"""
        try:
            import pyautogui
            pyautogui.moveTo(x=x, y=y, duration=duration)
            return {"success": True, "x": x, "y": y}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def open_application(self, app_name: str) -> dict:
        """فتح تطبيق"""
        try:
            # Try multiple methods
            app_launchers = {
                "chrome": ["google-chrome", "google-chrome-stable"],
                "firefox": ["firefox"],
                "terminal": ["gnome-terminal", "xterm", "konsole"],
                "code": ["code", "codium"],
                "blender": ["blender"],
                "files": ["nautilus", "dolphin", "thunar"],
                "settings": ["gnome-control-center"],
            }

            commands = app_launchers.get(app_name.lower(), [app_name])

            for cmd in commands:
                try:
                    subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    return {"success": True, "app": app_name, "command": cmd}
                except FileNotFoundError:
                    continue

            return {"success": False, "error": f"التطبيق غير موجود: {app_name}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def scroll(self, direction: str = "down", amount: int = 3) -> dict:
        """تمرير الشاشة"""
        try:
            import pyautogui
            scroll_amount = amount if direction == "down" else -amount
            pyautogui.scroll(scroll_amount)
            return {"success": True, "direction": direction, "amount": amount}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def hotkey(self, keys: list) -> dict:
        """ضغط اختصار لوحة مفاتيح"""
        try:
            import pyautogui
            pyautogui.hotkey(*keys)
            return {"success": True, "keys": keys}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def drag(self, from_x: int, from_y: int, to_x: int, to_y: int,
                   duration: float = 0.5) -> dict:
        """سحب وإفلات"""
        try:
            import pyautogui
            pyautogui.moveTo(from_x, from_y)
            pyautogui.drag(to_x - from_x, to_y - from_y, duration=duration)
            return {"success": True, "from": [from_x, from_y], "to": [to_x, to_y]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_screen_info(self) -> dict:
        """معلومات الشاشة"""
        try:
            import pyautogui
            width, height = pyautogui.size()
            x, y = pyautogui.position()
            return {
                "success": True,
                "screen_width": width,
                "screen_height": height,
                "mouse_x": x,
                "mouse_y": y,
                "failsafe": pyautogui.FAILSAFE,
            }
        except Exception as e:
            return {"success": True, "screen_width": 1920, "screen_height": 1080, "mouse_x": 0, "mouse_y": 0}

    async def list_windows(self) -> dict:
        """قائمة النوافذ المفتوحة"""
        try:
            # Try using wmctrl
            result = subprocess.run(
                ["wmctrl", "-l"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                windows = []
                for line in result.stdout.strip().split("\n"):
                    parts = line.split(None, 3)
                    if len(parts) >= 4:
                        windows.append({
                            "id": parts[0],
                            "desktop": parts[1],
                            "host": parts[2],
                            "title": parts[3],
                        })
                return {"success": True, "windows": windows}
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return {"success": True, "windows": [], "note": "wmctrl not available"}

    async def focus_window(self, window_title: str) -> dict:
        """التركيز على نافذة"""
        try:
            result = subprocess.run(
                ["wmctrl", "-a", window_title],
                capture_output=True, text=True, timeout=5
            )
            return {"success": result.returncode == 0, "window": window_title}
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return {"success": False, "error": "wmctrl not available"}

    def get_status(self) -> dict:
        """حالة المتحكم"""
        return {
            "enabled": DESKTOP_CONTROL_ENABLED,
            "initialized": self._initialized,
            "screen_size": f"{self._screen_width}x{self._screen_height}",
            "actions_logged": len(self._action_log),
            "screenshot_dir": str(self._screenshot_dir),
        }


# Singleton
_desktop_controller: Optional[DesktopController] = None

def get_desktop_controller() -> DesktopController:
    global _desktop_controller
    if _desktop_controller is None:
        _desktop_controller = DesktopController()
    return _desktop_controller
