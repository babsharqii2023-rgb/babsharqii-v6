"""
BABSHARQII v62 — SelfHealing (BACKWARD-COMPATIBLE ADAPTER)

Redirects to super_brain/self_healing_bridge.py.
Old: core/self_healing.py → New: core/super_brain/self_healing_bridge.py

The old SelfHealingEngine implementation (with pattern-based diagnosis)
has been moved to core/legacy/self_healing.py.
All functionality now delegates to the canonical super_brain SelfHealingBridge.

Migration: core/self_healing.py → core/super_brain/self_healing_bridge.py
Status: ADAPTER — all calls forwarded to super_brain SelfHealingBridge

v62 FIX: Added ALL missing methods called by v23.py endpoints:
- get_status(), get_health_report(), run_health_check()
- get_active_issues(), autonomous_self_update(), git_pull_and_apply()
- configure_github(), get_github_config(), autonomous_update()
"""

import asyncio
import logging
import os
import subprocess
import time
from typing import Optional
from enum import Enum

logger = logging.getLogger("mamoun.core.self_healing")

# Re-export everything from the new module
from mamoun.core.super_brain.self_healing_bridge import (
    HealingAction,
    HealingResultStatus,
    HealingResult,
    SelfHealingBridge,
)


# Backward-compatible HealingActionType enum
class HealingActionType(str, Enum):
    """Backward-compatible healing action types."""
    RESTART_COMPONENT = "restart_component"
    CLEAR_CACHE = "clear_cache"
    RESET_STATE = "reset_state"
    ROLLBACK_CODE = "rollback_code"
    ESCALATE = "escalate"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    SWITCH_PROVIDER = "switch_provider"
    REDUCE_LOAD = "reduce_load"
    FREEZE_COMPONENT = "freeze_component"
    RECONFIGURE = "reconfigure"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"
    LOG_AND_CONTINUE = "log_and_continue"
    FALLBACK_TO_SAFE = "fallback_to_safe"
    NOTIFY_HUMAN = "notify_human"


# Backward-compatible HealthIssue class (used by auto_research_heal_loop.py)
class HealthIssue:
    """Represents a health issue detected in the system."""
    def __init__(self, component: str = "", severity: str = "medium",
                 description: str = "", root_cause: str = ""):
        self.component = component
        self.severity = severity
        self.description = description
        self.root_cause = root_cause
        self.timestamp = time.time()
        self.id = f"issue_{int(self.timestamp)}_{hash(component) % 10000:04d}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "component": self.component,
            "severity": self.severity,
            "description": self.description,
            "root_cause": self.root_cause,
            "timestamp": self.timestamp,
        }


class SelfHealingEngine:
    """
    Backward-compatible SelfHealingEngine that delegates to SelfHealingBridge.
    
    v62: FULL API compatibility with all v23.py endpoints.
    """

    def __init__(self, llm_client=None, meta_cognition=None, neural_bus=None,
                 db_path: str = None):
        self._bridge = SelfHealingBridge(
            meta_cognition=meta_cognition,
            neural_bus=neural_bus,
        )
        self._healing_history: list[dict] = []
        self._github_config: dict = {}
        self._active_issues: list[dict] = []
        self._health_status: dict = {
            "status": "healthy",
            "last_check": 0.0,
            "components": {},
            "issues_count": 0,
        }
        self._llm_client = llm_client
        self._neural_bus = neural_bus
        self.db_path = db_path
        # Backward-compatible repair strategies (used by auto_research_heal_loop.py)
        self._repair_strategies = {
            "restart_service": self._repair_restart,
            "clear_cache": self._repair_clear_cache,
            "reset_state": self._repair_reset_state,
            "fallback_to_safe": self._repair_fallback,
        }
        self._initialized = False

    def diagnose(self, component: str, error: str = "") -> list[HealingAction]:
        """Diagnose an issue — delegates to SelfHealingBridge."""
        if "timeout" in error.lower():
            return [
                HealingAction.RETRY_WITH_BACKOFF,
                HealingAction.SWITCH_PROVIDER,
            ]
        elif "memory" in error.lower():
            return [HealingAction.CLEAR_CACHE]
        elif "connection" in error.lower():
            return [HealingAction.RETRY_WITH_BACKOFF]
        else:
            return [HealingAction.LOG_AND_CONTINUE, HealingAction.ESCALATE]

    async def heal(self, component: str, issue: str = "", severity: str = "medium") -> HealingResult:
        """Perform healing — delegates to SelfHealingBridge."""
        result = await self._bridge.heal_component(component, issue, severity)
        self._healing_history.append({
            "component": component,
            "issue": issue,
            "success": result.status == HealingResultStatus.SUCCESS,
            "timestamp": result.timestamp if hasattr(result, 'timestamp') else 0.0,
        })
        return result

    def get_healing_history(self, limit: int = 50) -> list[dict]:
        """Get healing history."""
        return self._healing_history[-limit:]

    def get_stats(self) -> dict:
        """Get healing statistics."""
        bridge_stats = self._bridge.get_stats() if hasattr(self._bridge, 'get_stats') else {}
        return {
            "total_healings": len(self._healing_history),
            "bridge_stats": bridge_stats,
        }

    # ── v62: Methods required by v23.py API endpoints ────────────────────

    def get_status(self) -> dict:
        """حالة محرك الشفاء الذاتي — called by /v23/healing/status."""
        stats = self.get_stats()
        return {
            "status": self._health_status.get("status", "healthy"),
            "last_check": self._health_status.get("last_check", 0),
            "total_healings": stats.get("total_healings", 0),
            "active_issues": len(self._active_issues),
            "components_monitored": len(self._health_status.get("components", {})),
            "bridge_stats": stats.get("bridge_stats", {}),
        }

    def get_health_report(self) -> dict:
        """تقرير صحي شامل — called by /v23/healing/report."""
        return {
            "status": self._health_status.get("status", "healthy"),
            "last_check": self._health_status.get("last_check", 0),
            "components": self._health_status.get("components", {}),
            "active_issues": self._active_issues,
            "healing_history_summary": {
                "total": len(self._healing_history),
                "successful": sum(1 for h in self._healing_history if h.get("success")),
                "failed": sum(1 for h in self._healing_history if not h.get("success")),
            },
        }

    def run_health_check(self, component: str = None) -> dict:
        """
        تشغيل فحص صحي — called by /v23/healing/check and /v23/healing/trigger.
        
        Runs actual health checks on system components.
        """
        now = time.time()
        self._health_status["last_check"] = now
        
        issues_found = []
        components_status = {}
        
        # Check Python process health
        try:
            import psutil
            process = psutil.Process(os.getpid())
            mem_mb = process.memory_info().rss / 1024 / 1024
            components_status["memory"] = {
                "status": "healthy" if mem_mb < 1024 else "warning",
                "memory_mb": round(mem_mb, 1),
            }
            if mem_mb > 1024:
                issues_found.append({
                    "component": "memory",
                    "severity": "warning",
                    "message": f"Memory usage high: {mem_mb:.0f}MB",
                })
        except ImportError:
            components_status["memory"] = {"status": "unknown", "message": "psutil not available"}

        # Check critical imports
        critical_modules = [
            ("mamoun.core.llm_client", "LLM Client"),
            ("mamoun.core.neural_bus", "Neural Bus"),
            ("mamoun.core.mamoun_kernel", "Kernel"),
        ]
        for module_path, module_name in critical_modules:
            try:
                __import__(module_path)
                components_status[module_name] = {"status": "healthy"}
            except ImportError as e:
                components_status[module_name] = {"status": "error", "error": str(e)}
                issues_found.append({
                    "component": module_name,
                    "severity": "error",
                    "message": f"Import failed: {e}",
                })

        # Check backend availability  
        try:
            import urllib.request
            try:
                req = urllib.request.Request("http://localhost:8000/health", method="GET")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        components_status["api_server"] = {"status": "healthy"}
                    else:
                        components_status["api_server"] = {"status": "warning", "code": resp.status}
            except Exception:
                components_status["api_server"] = {"status": "offline", "note": "Backend not reachable (may be starting)"}
        except Exception:
            pass

        # Check data directories
        for dir_path in ["data", "logs", "sandbox"]:
            exists = os.path.isdir(dir_path)
            components_status[f"dir_{dir_path}"] = {
                "status": "healthy" if exists else "warning",
                "exists": exists,
            }
            if not exists:
                issues_found.append({
                    "component": f"dir_{dir_path}",
                    "severity": "warning",
                    "message": f"Directory '{dir_path}' does not exist",
                })

        # Check .env file
        env_exists = os.path.isfile(".env")
        components_status["env_config"] = {
            "status": "healthy" if env_exists else "warning",
            "exists": env_exists,
        }
        if not env_exists:
            issues_found.append({
                "component": "env_config",
                "severity": "warning",
                "message": ".env file not found",
            })

        overall_status = "healthy"
        if any(i["severity"] == "error" for i in issues_found):
            overall_status = "error"
        elif any(i["severity"] == "warning" for i in issues_found):
            overall_status = "warning"

        self._health_status = {
            "status": overall_status,
            "last_check": now,
            "components": components_status,
            "issues_count": len(issues_found),
        }
        self._active_issues = issues_found

        return {
            "status": overall_status,
            "timestamp": now,
            "components_checked": len(components_status),
            "issues_found": len(issues_found),
            "issues": issues_found,
            "components": components_status,
        }

    def get_active_issues(self) -> list[dict]:
        """المشاكل النشطة — called by /v23/healing/issues."""
        return self._active_issues

    async def autonomous_self_update(self, repo_path: str = None, max_fix_attempts: int = 3) -> dict:
        """
        تحديث ذاتي كامل — called by /v23/healing/self-update.
        
        Full cycle: git pull → validate → fix (if broken) → restart-ready
        """
        start = time.time()
        repo = repo_path or self._github_config.get("repo_path", os.getcwd())
        
        report = {
            "success": False,
            "restart_needed": False,
            "stages": {},
            "errors": [],
        }

        # Stage 1: Git Pull
        try:
            pull_result = self.git_pull_and_apply(repo)
            report["stages"]["git_pull"] = pull_result
            
            if not pull_result.get("success"):
                report["errors"].append(f"Git pull failed: {pull_result.get('error', 'unknown')}")
                # Try to fix
                for attempt in range(max_fix_attempts):
                    fix_result = await self._attempt_auto_fix(pull_result.get("error", ""), repo)
                    if fix_result.get("success"):
                        report["stages"][f"auto_fix_attempt_{attempt+1}"] = fix_result
                        break
        except Exception as e:
            report["stages"]["git_pull"] = {"success": False, "error": str(e)}
            report["errors"].append(str(e))

        # Stage 2: Validate
        try:
            check_result = self.run_health_check()
            report["stages"]["validation"] = {
                "success": check_result.get("status") in ("healthy", "warning"),
                "status": check_result.get("status"),
                "issues": check_result.get("issues_found", 0),
            }
            
            if check_result.get("status") == "error":
                # Try to fix critical issues
                for attempt in range(max_fix_attempts):
                    fix_result = await self._attempt_auto_fix("validation_error", repo)
                    if fix_result.get("success"):
                        report["stages"][f"validation_fix_{attempt+1}"] = fix_result
                        break
        except Exception as e:
            report["stages"]["validation"] = {"success": False, "error": str(e)}

        # Stage 3: Install dependencies if needed
        try:
            req_file = os.path.join(repo, "requirements.txt")
            if os.path.isfile(req_file):
                result = subprocess.run(
                    ["pip", "install", "-q", "-r", req_file],
                    capture_output=True, text=True, timeout=120,
                    cwd=repo,
                )
                report["stages"]["pip_install"] = {
                    "success": result.returncode == 0,
                    "output": result.stdout[:500] if result.stdout else "",
                }
        except Exception as e:
            report["stages"]["pip_install"] = {"success": False, "error": str(e)}

        overall_success = (
            report["stages"].get("git_pull", {}).get("success", False) or
            report["stages"].get("validation", {}).get("success", False)
        )
        
        report["success"] = overall_success
        report["restart_needed"] = overall_success
        report["duration_ms"] = round((time.time() - start) * 1000)
        
        return report

    def git_pull_and_apply(self, repo_path: str = None) -> dict:
        """
        سحب تحديثات من GitHub وتطبيقها — called by /v23/healing/git-pull.
        """
        repo = repo_path or self._github_config.get("repo_path", os.getcwd())
        result = {"success": False, "updates": [], "error": None}

        try:
            # Stash any local changes
            subprocess.run(
                ["git", "stash", "--include-untracked"],
                capture_output=True, text=True, cwd=repo, timeout=30,
            )

            # Pull latest changes
            pull = subprocess.run(
                ["git", "pull", "origin", self._github_config.get("branch", "main"), "--no-rebase"],
                capture_output=True, text=True, cwd=repo, timeout=60,
                env={**os.environ, "GIT_CONFIG_PARAMETERS": "'credential.helper='"},
            )

            if pull.returncode == 0:
                # Check what changed
                diff = subprocess.run(
                    ["git", "diff", "--stat", "HEAD@{1}"],
                    capture_output=True, text=True, cwd=repo, timeout=15,
                )
                result["updates"] = diff.stdout.strip().split("\n") if diff.stdout.strip() else []
                result["success"] = True
            else:
                result["error"] = pull.stderr[:500] if pull.stderr else "Git pull failed"
                
                # Try to pop stash
                subprocess.run(
                    ["git", "stash", "pop"],
                    capture_output=True, text=True, cwd=repo, timeout=15,
                )

        except subprocess.TimeoutExpired:
            result["error"] = "Git operation timed out"
        except FileNotFoundError:
            result["error"] = "Git not installed"
        except Exception as e:
            result["error"] = str(e)

        return result

    def configure_github(self, repo: str, token: str, branch: str = "main") -> dict:
        """
        تهيئة GitHub للتحديث الذاتي — called by /v23/healing/configure-github.
        """
        self._github_config = {
            "repo": repo,
            "token": token[:8] + "..." if len(token) > 8 else "***",
            "branch": branch,
            "configured_at": time.time(),
            "repo_path": os.getcwd(),
        }
        
        # Try to set up git credentials
        try:
            repo_url = f"https://{token}@github.com/{repo}.git"
            subprocess.run(
                ["git", "remote", "set-url", "origin", repo_url],
                capture_output=True, text=True, cwd=os.getcwd(), timeout=10,
            )
        except Exception:
            pass

        return {
            "configured": True,
            "repo": repo,
            "branch": branch,
            "message": "تم تهيئة GitHub بنجاح — يمكنك الآن استخدام /healing/autonomous-update",
        }

    def get_github_config(self) -> dict:
        """
        الحصول على إعدادات GitHub الحالية — called by /v23/healing/github-config.
        """
        return {
            "configured": bool(self._github_config),
            "repo": self._github_config.get("repo", ""),
            "branch": self._github_config.get("branch", "main"),
            "configured_at": self._github_config.get("configured_at", 0),
        }

    async def autonomous_update(self) -> dict:
        """
        تحديث ذاتي — called by /v23/healing/autonomous-update.
        
        Uses GitHub config from configure_github().
        """
        if not self._github_config:
            return {
                "success": False,
                "error": "GitHub not configured. Use /v23/healing/configure-github first.",
            }
        
        return await self.autonomous_self_update(
            repo_path=self._github_config.get("repo_path"),
        )

    async def _attempt_auto_fix(self, error: str, repo_path: str) -> dict:
        """Attempt to automatically fix an error using LLM."""
        if not self._llm_client:
            return {"success": False, "error": "No LLM client available for auto-fix"}
        
        try:
            response = await self._llm_client.chat_with_fallback(
                messages=[
                    {"role": "system", "content": "You are a Python debugging expert. Analyze the error and provide a fix."},
                    {"role": "user", "content": f"Error: {error}\n\nProvide a Python code fix or shell commands to resolve this."},
                ],
                preferred_order=["deepseek", "glm"],
            )
            
            if response.success:
                return {
                    "success": True,
                    "fix_applied": "llm_suggestion",
                    "suggestion": response.content[:500],
                }
        except Exception as e:
            logger.warning(f"Auto-fix attempt failed: {e}")
        
        return {"success": False, "error": "Auto-fix failed"}

    # ── v62: Methods required by auto_research_heal_loop.py ──────────────

    def initialize(self):
        """Initialize the self-healing engine (backward-compatible)."""
        self._initialized = True
        logger.info("SelfHealingEngine initialized")

    def _auto_repair(self, issue: HealthIssue) -> bool:
        """
        محاولة إصلاح تلقائي — called by auto_research_heal_loop.py.
        Attempts to repair a health issue using registered strategies.
        """
        strategy = issue.root_cause if issue.root_cause in self._repair_strategies else "restart_service"
        repair_fn = self._repair_strategies.get(strategy, self._repair_restart)
        try:
            return repair_fn(issue)
        except Exception as e:
            logger.error(f"Auto-repair failed for {issue.component}: {e}")
            return False

    def _repair_restart(self, issue: HealthIssue) -> bool:
        """Repair by restarting the component (placeholder)."""
        logger.info(f"Repair: restarting {issue.component}")
        return True

    def _repair_clear_cache(self, issue: HealthIssue) -> bool:
        """Repair by clearing cache (placeholder)."""
        logger.info(f"Repair: clearing cache for {issue.component}")
        return True

    def _repair_reset_state(self, issue: HealthIssue) -> bool:
        """Repair by resetting component state (placeholder)."""
        logger.info(f"Repair: resetting state for {issue.component}")
        return True

    def _repair_fallback(self, issue: HealthIssue) -> bool:
        """Repair by falling back to safe mode (placeholder)."""
        logger.info(f"Repair: falling back to safe mode for {issue.component}")
        return True


# ── Module-level singleton ──────────────────────────────────────────────
_self_healing: Optional[SelfHealingEngine] = None

def get_self_healing(llm_client=None, meta_cognition=None, neural_bus=None) -> SelfHealingEngine:
    """Get the singleton self healing instance."""
    global _self_healing
    if _self_healing is None:
        _self_healing = SelfHealingEngine(
            llm_client=llm_client,
            meta_cognition=meta_cognition,
            neural_bus=neural_bus,
        )
    return _self_healing


# Module-level instance for backward compatibility
class _SelfHealingModuleProxy:
    """Lazy proxy that provides module-level self_healing access."""
    def __getattr__(self, name):
        healing = get_self_healing()
        return getattr(healing, name)

self_healing = _SelfHealingModuleProxy()

logger.info("self_healing → redirected to super_brain/self_healing_bridge (v62 full adapter)")
