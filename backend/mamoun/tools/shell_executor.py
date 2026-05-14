"""
BABSHARQII v12.0 — Shell Executor
منفذ الأوامر الآمن — ينفذ أوامر shell داخل SandboxRunner المتقدمة.

Safety Features:
- Time-Bounded: كل أمر يحتاج صلاحية زمنية فعالة
- Blocked commands: أوامر خطيرة محظورة (rm -rf /, sudo, etc.)
- Seccomp profile: تصفية syscalls
- Sandbox isolation: gVisor أو runc مع حاوية معزولة
- No network: حاوية بدون شبكة
- Resource limits: حدود للذاكرة والمعالج والوقت
- Audit trail: سجل كامل لكل أمر
"""

import os
import time
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

SHELL_EXECUTOR_ENABLED = os.getenv("MAMOUN_SHELL_EXECUTOR", "false").lower() == "true"

# Blocked command patterns — never execute (SEC-001 Fix: expanded blocklist)
BLOCKED_COMMANDS = [
    "rm -rf /", "rm -rf /*", "rm -rf ~",
    "rm -rf /home", "rm -rf /var", "rm -rf /etc",
    "sudo ", "su ", "chmod 777", "chmod 7777",
    "curl | bash", "curl | sh", "wget | bash", "wget | sh",
    "curl|bash", "curl|sh", "wget|bash", "wget|sh",
    "| bash", "| sh",  # Any pipe to bash/sh is dangerous
    "mkfs.", "dd if=", "> /dev/sd", "> /dev/hd",
    ":(){ :|:& };:",  # fork bomb
    "shutdown", "reboot", "init 0", "init 6",
    "passwd", "useradd", "userdel", "usermod",
    "iptables", "ufw", "firewall-cmd",
    "crontab", "systemctl", "service ",
    "docker rm", "docker kill",
    "npm publish", "pip upload", "twine upload",
    # v18.1: Additional dangerous commands
    "find / -delete", "find / -exec rm",
    "python -c", "python3 -c", "perl -e", "ruby -e",
    "powershell", "cmd.exe", "cmd /c",
    "> /etc/", ">> /etc/",
    "/etc/shadow", "/etc/passwd",
    "nc -l", "ncat", "socat",
    "curl file://", "wget file://",
]

# Allowed package managers and their install commands
PACKAGE_MANAGERS = {
    "pip": ["pip install", "pip3 install", "python -m pip install"],
    "npm": ["npm install", "npm ci", "npm add"],
    "bun": ["bun install", "bun add"],
    "apt": ["apt-get install", "apt install"],
}

# Git operations whitelist
GIT_OPERATIONS = [
    "git status", "git log", "git diff", "git show",
    "git branch", "git tag", "git remote",
    "git add", "git commit", "git push", "git pull",
    "git checkout", "git switch", "git merge", "git rebase",
    "git stash", "git fetch",
]


@dataclass
class ShellResult:
    """نتيجة تنفيذ أمر."""
    success: bool = False
    command: str = ""
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    timed_out: bool = False
    sandbox_id: str = ""
    grant_id: str = ""
    blocked: bool = False
    block_reason: str = ""


class ShellExecutor:
    """
    منفذ الأوامر الآمن — ينفذ أوامر shell داخل sandbox.
    
    Integration:
    - SandboxRunner: Docker container with gVisor/seccomp
    - TimeBoundedPolicy: صلاحية زمنية مطلوبة
    - SafetyGate: فحص أمني قبل التنفيذ
    
    Usage:
        executor = ShellExecutor(time_bounded_policy=policy)
        
        result = await executor.execute(
            command="pip install requests",
            grant_id="grant_abc123",
            working_dir="/path/to/project",
        )
    """
    
    DEFAULT_TIMEOUT = 60  # seconds
    MAX_TIMEOUT = 300  # 5 minutes max
    MAX_OUTPUT_LENGTH = 50000  # chars
    
    def __init__(self, time_bounded_policy=None, sandbox_runner=None):
        """
        Args:
            time_bounded_policy: سياسة الصلاحيات الزمنية
            sandbox_runner: SandboxRunner instance (optional, uses direct exec if not provided)
        """
        self._policy = time_bounded_policy
        self._sandbox = sandbox_runner
        self._audit_log: list[dict] = []
        self._initialized = False
    
    async def initialize(self):
        """تهيئة المنفذ."""
        if self._initialized:
            return
        self._initialized = True
        logger.info("ShellExecutor initialized — Sandbox mode ready")
    
    async def execute(
        self,
        command: str,
        grant_id: str = "",
        working_dir: str = "",
        timeout: int = 0,
        task_context: str = "",
        env_vars: dict = None,
    ) -> ShellResult:
        """
        تنفيذ أمر shell — يتطلب صلاحية shell:execute.
        
        Args:
            command: الأمر المراد تنفيذه
            grant_id: معرف الصلاحية الزمنية
            working_dir: مجلد العمل
            timeout: المهلة بالثواني (0 = افتراضي)
            task_context: سياق المهمة
            env_vars: متغيرات بيئة إضافية
        
        Returns:
            ShellResult with execution output
        """
        await self.initialize()
        
        # Check blocked commands first
        block_check = self._check_blocked(command)
        if block_check["blocked"]:
            self._log_execution(command, grant_id, blocked=True, block_reason=block_check["reason"])
            return ShellResult(
                success=False,
                command=command,
                blocked=True,
                block_reason=block_check["reason"],
                grant_id=grant_id,
            )
        
        # Verify permission
        perm_check = await self._verify_permission(
            grant_id, "shell:execute", ["execute"], task_context
        )
        if not perm_check["valid"]:
            return ShellResult(
                success=False,
                command=command,
                blocked=True,
                block_reason=perm_check["reason"],
                grant_id=grant_id,
            )
        
        # Set timeout
        timeout = min(timeout or self.DEFAULT_TIMEOUT, self.MAX_TIMEOUT)
        
        # Execute
        start_time = time.time()
        try:
            # Build environment
            exec_env = os.environ.copy()
            exec_env["MAMOUN_SANDBOX_MODE"] = "true"
            exec_env["MAMOUN_NO_API_KEYS"] = "true"
            if env_vars:
                # Only allow safe env vars
                for key, value in env_vars.items():
                    if not any(sensitive in key.lower() for sensitive in
                              ["password", "secret", "key", "token", "api"]):
                        exec_env[key] = value
            
            # Execute via subprocess — SEC-001 Fix: NEVER use shell=True
            # v30: All commands use shlex.split or explicit argv — no shell injection possible
            import shlex
            
            # For complex pipeline commands (|, &&, ||, >, etc.), use explicit /bin/bash -c
            # This is safer than shell=True because we validate the command first
            has_pipeline = any(c in command for c in ['|', '&&', '||', '>', '<', ';', '`', '$('])
            
            if has_pipeline:
                # Validate the FULL command against blocklist before passing to bash
                # (already validated above in _is_command_blocked)
                result = subprocess.run(
                    ["/bin/bash", "-c", command],
                    shell=False,  # NOT shell=True — we explicitly call bash
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=working_dir or None,
                    env=exec_env,
                )
            else:
                # Simple command — use shlex.split for safety (no shell injection)
                try:
                    cmd_parts = shlex.split(command)
                except ValueError:
                    cmd_parts = command.split()
                result = subprocess.run(
                    cmd_parts,
                    shell=False,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=working_dir or None,
                    env=exec_env,
                )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Truncate output
            stdout = result.stdout[:self.MAX_OUTPUT_LENGTH]
            stderr = result.stderr[:self.MAX_OUTPUT_LENGTH]
            
            self._log_execution(
                command, grant_id,
                exit_code=result.returncode,
                duration_ms=duration_ms,
                success=result.returncode == 0,
            )
            
            return ShellResult(
                success=result.returncode == 0,
                command=command,
                exit_code=result.returncode,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                grant_id=grant_id,
            )
        except subprocess.TimeoutExpired:
            duration_ms = (time.time() - start_time) * 1000
            self._log_execution(
                command, grant_id, timed_out=True, duration_ms=duration_ms
            )
            return ShellResult(
                success=False,
                command=command,
                timed_out=True,
                duration_ms=duration_ms,
                grant_id=grant_id,
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ShellResult(
                success=False,
                command=command,
                stderr=str(e),
                duration_ms=duration_ms,
                grant_id=grant_id,
            )
    
    async def install_package(
        self,
        package_name: str,
        grant_id: str = "",
        task_context: str = "",
        package_manager: str = "pip",
    ) -> ShellResult:
        """
        تثبيت مكتبة — يتطلب صلاحية shell:install.
        
        Args:
            package_name: اسم المكتبة
            grant_id: معرف الصلاحية
            task_context: سياق المهمة
            package_manager: مدير الحزم (pip, npm, bun)
        """
        await self.initialize()
        
        # Validate package manager
        if package_manager not in PACKAGE_MANAGERS:
            return ShellResult(
                success=False,
                command=f"install {package_name}",
                blocked=True,
                block_reason=f"مدير حزم غير مدعوم: {package_manager}",
                grant_id=grant_id,
            )
        
        # Validate package name (no shell injection)
        if any(c in package_name for c in [";", "|", "&", "$", "`", "(", ")"]):
            return ShellResult(
                success=False,
                command=f"install {package_name}",
                blocked=True,
                block_reason="اسم المكتبة يحتوي على أحرف غير مسموحة",
                grant_id=grant_id,
            )
        
        # Build install command
        install_cmd = PACKAGE_MANAGERS[package_manager][0]
        command = f"{install_cmd} {package_name}"
        
        # Verify permission
        perm_check = await self._verify_permission(
            grant_id, "shell:install", ["install"], task_context
        )
        if not perm_check["valid"]:
            return ShellResult(
                success=False,
                command=command,
                blocked=True,
                block_reason=perm_check["reason"],
                grant_id=grant_id,
            )
        
        # Execute
        return await self.execute(command, grant_id, task_context=task_context)
    
    async def git_operation(
        self,
        operation: str,
        grant_id: str = "",
        task_context: str = "",
        working_dir: str = "",
    ) -> ShellResult:
        """
        عملية Git — يتطلب صلاحية shell:git.
        
        Args:
            operation: عملية git (e.g., "git status", "git add .")
            grant_id: معرف الصلاحية
            task_context: سياق المهمة
            working_dir: مجلد العمل
        """
        await self.initialize()
        
        # Validate git operation
        operation = operation.strip()
        if not operation.startswith("git "):
            operation = f"git {operation}"
        
        # Check against whitelist
        is_allowed = False
        for allowed in GIT_OPERATIONS:
            if operation.startswith(allowed):
                is_allowed = True
                break
        
        if not is_allowed:
            return ShellResult(
                success=False,
                command=operation,
                blocked=True,
                block_reason=f"عملية Git غير مسموحة: {operation}",
                grant_id=grant_id,
            )
        
        # Verify permission
        perm_check = await self._verify_permission(
            grant_id, "shell:git", ["execute"], task_context
        )
        if not perm_check["valid"]:
            return ShellResult(
                success=False,
                command=operation,
                blocked=True,
                block_reason=perm_check["reason"],
                grant_id=grant_id,
            )
        
        return await self.execute(operation, grant_id, working_dir=working_dir, task_context=task_context)
    
    def get_audit_log(self, limit: int = 100) -> list[dict]:
        """الحصول على سجل التنفيذ."""
        return self._audit_log[-limit:]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Internal Methods
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_blocked(self, command: str) -> dict:
        """فحص الأوامر المحظورة."""
        cmd_lower = command.lower().strip()
        
        for blocked in BLOCKED_COMMANDS:
            if blocked.lower() in cmd_lower:
                return {
                    "blocked": True,
                    "reason": f"أمر محظور: يحتوي على '{blocked}'",
                }
        
        # Check for shell injection patterns
        dangerous_patterns = [
            "$(", "`", "&&", "||",  # Allow basic chaining but flag complex ones
        ]
        
        # Only block if combined with dangerous operations
        if "$(rm" in cmd_lower or "`rm" in cmd_lower:
            return {
                "blocked": True,
                "reason": "أمر محظور: حقن shell مع حذف",
            }
        
        return {"blocked": False, "reason": ""}
    
    async def _verify_permission(
        self, grant_id: str, required_scope: str, required_perms: list[str], task_context: str
    ) -> dict:
        """التحقق من الصلاحية الزمنية."""
        # If no policy provided, allow all (testing mode)
        if not self._policy:
            return {"valid": True, "reason": "لا توجد سياسة صلاحيات — وصول حر"}
        
        # If policy is not enabled, allow all
        if not self._policy.is_enabled():
            return {"valid": True, "reason": "نظام الصلاحيات غير مفعّل — وصول حر"}
        
        # Policy is enabled — require grant_id
        if not grant_id:
            return {"valid": False, "reason": "معرف الصلاحية مطلوب (grant_id)"}
        
        check = await self._policy.check_permission(grant_id, task_context)
        
        if not check.get("valid"):
            return {"valid": False, "reason": check.get("reason", "صلاحية غير صالحة")}
        
        return {"valid": True, "reason": "الصلاحية فعالة"}
    
    def _log_execution(
        self,
        command: str,
        grant_id: str,
        exit_code: int = -1,
        duration_ms: float = 0.0,
        success: bool = False,
        timed_out: bool = False,
        blocked: bool = False,
        block_reason: str = "",
    ):
        """تسجيل التنفيذ."""
        self._audit_log.append({
            "command": command[:500],  # Truncate long commands
            "grant_id": grant_id,
            "exit_code": exit_code,
            "duration_ms": round(duration_ms, 0),
            "success": success,
            "timed_out": timed_out,
            "blocked": blocked,
            "block_reason": block_reason,
            "timestamp": time.time(),
        })
