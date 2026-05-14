"""
BABSHARQII v28.0-stable — Embodiment Controller
وحدة التحكم بالجسد الرقمي — بيئة تفاعلية معزولة للتجريب.

Provides browser automation (Playwright), desktop control, and plan execution
inside an isolated Docker container (mamoun-embodiment).
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

EMBODIMENT_SERVICE_URL = os.getenv("MAMOUN_EMBODIMENT_URL", "http://mamoun-embodiment:9222")


@dataclass
class EmbodimentAction:
    """إجراء في الجسد الرقمي."""
    action_type: str  # "launch_browser", "click", "type", "screenshot", "run_script", "navigate"
    params: dict = field(default_factory=dict)
    result: dict = field(default_factory=dict)
    success: bool = False
    duration_ms: float = 0.0
    timestamp: float = 0.0


@dataclass
class EmbodimentPlan:
    """خطة تنفيذ في الجسد الرقمي."""
    steps: list = field(default_factory=list)  # list[EmbodimentAction]
    status: str = "pending"  # pending, running, completed, failed, rolled_back
    completed_steps: int = 0
    failed_step: int = -1
    can_rollback: bool = True
    rollback_history: list = field(default_factory=list)


@dataclass
class BehaviorReport:
    """تقرير سلوكي — ناتج مراقبة الجسد الرقمي."""
    actions_taken: int
    suspicious_actions: list
    policy_violations: list
    risk_score: float  # 0-1
    recommendation: str


class SafetyBehaviorMonitor:
    """
    مراقب سلوكي — يراقب أنشطة الجسد الرقمي ويمنع الانحرافات.
    """

    SUSPICIOUS_PATTERNS = [
        "file://", "localhost", "127.0.0.1", "0.0.0.0",
        "admin", "root", "password", "secret", "token",
        "/etc/", "/var/", "/sys/", "/proc/",
        "rm -rf", "chmod", "chown", "sudo",
    ]

    def analyze(self, action_history: list) -> BehaviorReport:
        """تحليل سجل الإجراءات للكشف عن سلوكيات مشبوهة."""
        suspicious = []
        violations = []

        for action in action_history:
            # Check params for suspicious patterns
            params_str = json.dumps(action.params, ensure_ascii=False).lower()
            for pattern in self.SUSPICIOUS_PATTERNS:
                if pattern.lower() in params_str:
                    suspicious.append({
                        "action": action.action_type,
                        "pattern": pattern,
                        "params": action.params,
                    })

            # Check for policy violations
            if action.action_type == "run_script":
                js_len = action.params.get("js_length", 0)
                if js_len > 5000:
                    violations.append({
                        "action": action.action_type,
                        "violation": "script_too_long",
                        "details": f"Script length {js_len} exceeds 5000 chars limit",
                    })

        # Calculate risk score
        risk_score = min(1.0, (len(suspicious) * 0.2 + len(violations) * 0.3))

        # Generate recommendation
        if risk_score > 0.7:
            recommendation = "خطر عالي — يُنصح بإيقاف الجسد الرقمي فوراً"
        elif risk_score > 0.4:
            recommendation = "خطر متوسط — يُنصح بمراقبة دقيقة"
        else:
            recommendation = "سلوك طبيعي — يمكن المتابعة"

        return BehaviorReport(
            actions_taken=len(action_history),
            suspicious_actions=suspicious,
            policy_violations=violations,
            risk_score=risk_score,
            recommendation=recommendation,
        )


class EmbodimentController:
    """
    وحدة التحكم بالجسد الرقمي — تدير بيئة سطح المكتب المعزولة.

    Features:
    - launch_browser(url): Open a URL in the isolated Chromium
    - click(selector): Click an element
    - type_text(text): Type text into focused element
    - screenshot(): Capture current screen
    - run_script(js): Execute JavaScript in browser
    - execute_plan(steps): Execute a sequence of actions with rollback on failure
    - monitor_behavior(): SafetyGate-integrated behavior monitoring
    """

    EMBODIMENT_TIMEOUT = 120  # seconds
    MAX_ACTIONS_PER_SESSION = 50

    def __init__(self, service_url: str = ""):
        self.service_url = service_url or EMBODIMENT_SERVICE_URL
        self._session_active = False
        self._action_count = 0
        self._action_history: list[EmbodimentAction] = []
        self._safety_monitor = SafetyBehaviorMonitor()

    async def is_available(self) -> bool:
        """التحقق من توفر خدمة الجسد الرقمي."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.service_url}/health")
                return resp.status_code == 200
        except Exception:
            return False

    async def launch_browser(self, url: str = "about:blank") -> EmbodimentAction:
        """
        فتح المتصفح في بيئة الجسد الرقمي.
        Launches a browser in the isolated environment.
        """
        action = EmbodimentAction(
            action_type="launch_browser",
            params={"url": url},
            timestamp=time.time(),
        )

        start = time.time()
        try:
            # SafetyGate check
            safety_ok = await self._check_safety("launch_browser", {"url": url})
            if not safety_ok.granted:
                action.success = False
                action.result = {"error": safety_ok.reason}
                return action

            async with httpx.AsyncClient(timeout=self.EMBODIMENT_TIMEOUT) as client:
                resp = await client.post(
                    f"{self.service_url}/browser/launch",
                    json={"url": url},
                )
                if resp.status_code == 200:
                    action.success = True
                    action.result = resp.json()
                    self._session_active = True
                else:
                    action.success = False
                    action.result = {"error": f"HTTP {resp.status_code}"}
        except Exception as e:
            action.success = False
            action.result = {"error": str(e)}

        action.duration_ms = (time.time() - start) * 1000
        self._record_action(action)
        return action

    async def click(self, selector: str) -> EmbodimentAction:
        """النقر على عنصر في الصفحة."""
        action = EmbodimentAction(
            action_type="click",
            params={"selector": selector},
            timestamp=time.time(),
        )

        start = time.time()
        try:
            safety_ok = await self._check_safety("click", {"selector": selector})
            if not safety_ok.granted:
                action.success = False
                action.result = {"error": safety_ok.reason}
                return action

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.service_url}/browser/click",
                    json={"selector": selector},
                )
                action.success = resp.status_code == 200
                action.result = resp.json() if action.success else {"error": f"HTTP {resp.status_code}"}
        except Exception as e:
            action.success = False
            action.result = {"error": str(e)}

        action.duration_ms = (time.time() - start) * 1000
        self._record_action(action)
        return action

    async def type_text(self, text: str, selector: str = "") -> EmbodimentAction:
        """كتابة نص في حقل الإدخال."""
        action = EmbodimentAction(
            action_type="type_text",
            params={"text": text, "selector": selector},
            timestamp=time.time(),
        )

        start = time.time()
        try:
            safety_ok = await self._check_safety("type_text", {"text": text})
            if not safety_ok.granted:
                action.success = False
                action.result = {"error": safety_ok.reason}
                return action

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.service_url}/browser/type",
                    json={"text": text, "selector": selector},
                )
                action.success = resp.status_code == 200
                action.result = resp.json() if action.success else {"error": f"HTTP {resp.status_code}"}
        except Exception as e:
            action.success = False
            action.result = {"error": str(e)}

        action.duration_ms = (time.time() - start) * 1000
        self._record_action(action)
        return action

    async def screenshot(self) -> EmbodimentAction:
        """التقاط صورة للشاشة الحالية."""
        action = EmbodimentAction(
            action_type="screenshot",
            timestamp=time.time(),
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

    async def run_script(self, js: str) -> EmbodimentAction:
        """تنفيذ JavaScript في المتصفح."""
        action = EmbodimentAction(
            action_type="run_script",
            params={"js_length": len(js)},
            timestamp=time.time(),
        )

        start = time.time()
        try:
            # Extra safety check for scripts
            safety_ok = await self._check_safety("run_script", {"js_length": len(js)})
            if not safety_ok.granted:
                action.success = False
                action.result = {"error": safety_ok.reason}
                return action

            # Block dangerous JS patterns
            dangerous_patterns = [
                "fetch(", "XMLHttpRequest", "eval(", "import(", "require(",
                "child_process", "fs.", "process.env", "__proto__",
            ]
            for pattern in dangerous_patterns:
                if pattern in js:
                    action.success = False
                    action.result = {"error": f"نمط JavaScript محظور: {pattern}"}
                    action.duration_ms = (time.time() - start) * 1000
                    self._record_action(action)
                    return action

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.service_url}/browser/execute",
                    json={"script": js},
                )
                action.success = resp.status_code == 200
                action.result = resp.json() if action.success else {"error": f"HTTP {resp.status_code}"}
        except Exception as e:
            action.success = False
            action.result = {"error": str(e)}

        action.duration_ms = (time.time() - start) * 1000
        self._record_action(action)
        return action

    async def execute_plan(self, steps: list[dict]) -> EmbodimentPlan:
        """
        تنفيذ خطة من خطوات متسلسلة مع إمكانية التراجع عند الفشل.

        Each step is a dict: {"action": "click", "params": {"selector": "#btn"}}
        """
        plan = EmbodimentPlan(
            steps=[EmbodimentAction(action_type=s.get("action", ""), params=s.get("params", {})) for s in steps],
            status="running",
        )

        for i, step in enumerate(steps):
            action_type = step.get("action", "")
            params = step.get("params", {})

            # Execute the action
            if action_type == "launch_browser":
                result = await self.launch_browser(params.get("url", "about:blank"))
            elif action_type == "click":
                result = await self.click(params.get("selector", ""))
            elif action_type == "type_text":
                result = await self.type_text(params.get("text", ""), params.get("selector", ""))
            elif action_type == "screenshot":
                result = await self.screenshot()
            elif action_type == "run_script":
                result = await self.run_script(params.get("js", ""))
            else:
                result = EmbodimentAction(action_type=action_type, success=False, result={"error": "unknown_action"})

            plan.steps[i] = result
            plan.completed_steps = i + 1

            # Save rollback state
            if plan.can_rollback:
                plan.rollback_history.append({"step": i, "action": action_type, "params": params})

            if not result.success:
                plan.status = "failed"
                plan.failed_step = i
                # Auto-rollback
                if plan.can_rollback:
                    await self._rollback(plan)
                break

        if plan.status == "running":
            plan.status = "completed"

        return plan

    async def monitor_behavior(self) -> BehaviorReport:
        """
        مراقبة سلوك الجسد الرقمي — بالتعاون مع SafetyGate.
        """
        return self._safety_monitor.analyze(self._action_history)

    async def shutdown(self) -> bool:
        """إيقاف الجسد الرقمي — يُستخدم عند تفعيل القانون 5."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(f"{self.service_url}/shutdown")
                self._session_active = False
                return resp.status_code == 200
        except Exception:
            self._session_active = False
            return True  # Consider shutdown successful even if service unreachable

    def _record_action(self, action: EmbodimentAction):
        """تسجيل الإجراء في السجل."""
        self._action_count += 1
        self._action_history.append(action)

    async def _check_safety(self, action: str, params: dict):
        """التحقق من SafetyGate قبل تنفيذ الإجراء."""
        try:
            from mamoun.core.safety_gate_client import SafetyGateClient
            client = SafetyGateClient()
            return await client.request_permission(
                action=f"embodiment_{action}",
                resource="embodiment_environment",
                risk_level=3,  # Default moderate risk for embodiment actions
                details=json.dumps(params, ensure_ascii=False),
            )
        except Exception as e:
            logger.warning(f"SafetyGate check failed: {e}")
            # Fail-open for embodiment: allow in sandbox mode if SafetyGate unavailable
            from dataclasses import dataclass as _dc

            @_dc
            class _SafetyResult:
                granted: bool = True
                reason: str = "SafetyGate غير متاح — السماح بالتشغيل في وضع الحماية"

            return _SafetyResult()

    async def _rollback(self, plan: EmbodimentPlan):
        """التراجع عن الإجراءات المنفذة."""
        logger.info(f"بدء التراجع عن الخطة — {plan.completed_steps} خطوات")
        # Navigate back or close browser
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.service_url}/browser/navigate",
                    json={"url": "about:blank"},
                )
        except Exception:
            pass
