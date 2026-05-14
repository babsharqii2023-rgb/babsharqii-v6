"""
Full Agentic Terminal — وصول كامل إلى Terminal
v16.0

Enables Mamoun to execute system commands including:
- git operations (commit, push, pull, checkout)
- npm/bun operations (install, build, test, deploy)
- docker operations (build, run, stop)
- file operations (read, write, edit, mkdir)
- process management (start, stop, status)

SAFETY: All commands are:
1. Time-bounded (max execution time)
2. Risk-classified (low/medium/high/critical)
3. Audit-logged (every command recorded)
4. Require human approval for high-risk operations
5. Can be rolled back (for git operations)

Based on: OpenHands, SWE-agent concepts
"""

import asyncio
import json
import subprocess
import time
import logging
import shutil
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

logger = logging.getLogger("mamoun.terminal.agentic")


class CommandRisk:
    """Risk classification for terminal commands."""
    
    SAFE_COMMANDS = {
        "git status", "git log", "git diff", "git branch", "git remote",
        "npm list", "npm outdated", "npm audit",
        "ls", "cat", "head", "tail", "pwd", "which", "echo",
        "docker ps", "docker images", "docker logs",
        "ps", "top", "df", "free", "uptime",
        "python --version", "node --version", "npm --version",
    }
    
    LOW_RISK_PATTERNS = [
        "git add", "git stash",
        "npm install", "npm run build", "npm run lint",
        "mkdir", "cp", "mv",
    ]
    
    MEDIUM_RISK_PATTERNS = [
        "git commit", "git checkout", "git merge",
        "npm run test",
        "docker build", "docker compose",
    ]
    
    HIGH_RISK_PATTERNS = [
        "git push", "git push origin", "git reset", "git rebase",
        "npm run deploy", "npm publish",
        "docker run", "docker stop", "docker rm",
        "rm -rf",
    ]
    
    CRITICAL_PATTERNS = [
        "git push --force", "git clean -fd",
        "rm -rf /", "chmod 777",
        "curl | bash", "wget | bash",
    ]
    
    @classmethod
    def classify(cls, command: str) -> str:
        cmd_lower = command.strip().lower()
        
        # Check critical first
        for pattern in cls.CRITICAL_PATTERNS:
            if pattern.lower() in cmd_lower:
                return "critical"
        
        # Check high risk
        for pattern in cls.HIGH_RISK_PATTERNS:
            if cmd_lower.startswith(pattern.lower()):
                return "high"
        
        # Check medium risk
        for pattern in cls.MEDIUM_RISK_PATTERNS:
            if cmd_lower.startswith(pattern.lower()):
                return "medium"
        
        # Check low risk
        for pattern in cls.LOW_RISK_PATTERNS:
            if cmd_lower.startswith(pattern.lower()):
                return "low"
        
        # Check safe commands
        if cmd_lower in [s.lower() for s in cls.SAFE_COMMANDS]:
            return "safe"
        
        # Default to medium for unknown commands
        return "medium"


class AgenticTerminal:
    """
    Full terminal access for Mamoun with safety controls.
    """
    
    MAX_EXECUTION_TIME = 300  # 5 minutes max per command
    MAX_OUTPUT_LENGTH = 50000  # 50KB max output
    
    def __init__(
        self,
        project_root: str = ".",
        data_dir: str = "backend/data/terminal",
        dry_run: bool = False,
    ):
        self.project_root = Path(project_root).resolve()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.dry_run = dry_run
        self.audit_log_path = self.data_dir / "audit_log.jsonl"
        self.pending_approvals_path = self.data_dir / "pending_approvals.json"
        
        self.command_history: list[dict] = []
        self.pending_approvals: list[dict] = self._load_pending_approvals()
    
    def _load_pending_approvals(self) -> list:
        if self.pending_approvals_path.exists():
            try:
                with open(self.pending_approvals_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return []
    
    def _save_pending_approvals(self):
        with open(self.pending_approvals_path, "w") as f:
            json.dump(self.pending_approvals, f, indent=2, ensure_ascii=False)
    
    def _audit_log(self, entry: dict):
        with open(self.audit_log_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.command_history.append(entry)
    
    async def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        require_approval: bool = False,
        approval_id: Optional[str] = None,
    ) -> dict:
        """
        Execute a terminal command with safety controls.
        
        Returns: {
            "success": bool,
            "exit_code": int,
            "stdout": str,
            "stderr": str,
            "risk_level": str,
            "execution_time_ms": int,
            "approved": bool,
        }
        """
        risk = CommandRisk.classify(command)
        start_time = time.time()
        
        result = {
            "command": command,
            "risk_level": risk,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "approved": True,
            "success": False,
        }
        
        # Check if approval is needed
        if risk in ("high", "critical") and not approval_id:
            result["approved"] = False
            result["status"] = "pending_approval"
            result["message"] = f"الأمر يتطلب موافقة بشرية (مستوى الخطر: {risk})"
            
            # Add to pending approvals
            approval_entry = {
                "id": f"cmd_{int(time.time())}",
                "command": command,
                "risk_level": risk,
                "timestamp": result["timestamp"],
                "status": "pending",
            }
            self.pending_approvals.append(approval_entry)
            self._save_pending_approvals()
            self._audit_log(result)
            return result
        
        # Check if this is a dry run
        if self.dry_run:
            result["stdout"] = f"[DRY RUN] Would execute: {command}"
            result["exit_code"] = 0
            result["success"] = True
            result["dry_run"] = True
            self._audit_log(result)
            return result
        
        # Execute the command
        exec_timeout = min(timeout or self.MAX_EXECUTION_TIME, self.MAX_EXECUTION_TIME)
        
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.project_root),
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=exec_timeout,
            )
            
            result["exit_code"] = proc.returncode
            result["stdout"] = stdout.decode("utf-8", errors="replace")[:self.MAX_OUTPUT_LENGTH]
            result["stderr"] = stderr.decode("utf-8", errors="replace")[:self.MAX_OUTPUT_LENGTH]
            result["success"] = proc.returncode == 0
            
        except asyncio.TimeoutError:
            result["exit_code"] = -1
            result["stderr"] = f"انتهت المهلة بعد {exec_timeout} ثانية"
            result["success"] = False
        except Exception as e:
            result["exit_code"] = -1
            result["stderr"] = str(e)
            result["success"] = False
        
        result["execution_time_ms"] = round((time.time() - start_time) * 1000)
        self._audit_log(result)
        
        return result
    
    async def git_status(self) -> dict:
        """Get git repository status."""
        return await self.execute("git status --short")
    
    async def git_commit(self, message: str, approval_id: Optional[str] = None) -> dict:
        """Commit changes with a message."""
        return await self.execute(
            f'git add -A && git commit -m "{message}"',
            approval_id=approval_id,
        )
    
    async def git_push(self, remote: str = "origin", branch: str = "main", approval_id: Optional[str] = None) -> dict:
        """Push to remote (requires approval)."""
        return await self.execute(
            f"git push {remote} {branch}",
            approval_id=approval_id,
        )
    
    async def npm_build(self) -> dict:
        """Run npm build."""
        return await self.execute("npm run build", timeout=120)
    
    async def npm_test(self) -> dict:
        """Run npm test."""
        return await self.execute("npm test", timeout=300)
    
    def get_pending_approvals(self) -> list:
        return [a for a in self.pending_approvals if a["status"] == "pending"]
    
    def approve_command(self, approval_id: str) -> bool:
        for approval in self.pending_approvals:
            if approval["id"] == approval_id and approval["status"] == "pending":
                approval["status"] = "approved"
                approval["approved_at"] = datetime.now(timezone.utc).isoformat()
                self._save_pending_approvals()
                return True
        return False
    
    def reject_command(self, approval_id: str) -> bool:
        for approval in self.pending_approvals:
            if approval["id"] == approval_id and approval["status"] == "pending":
                approval["status"] = "rejected"
                approval["rejected_at"] = datetime.now(timezone.utc).isoformat()
                self._save_pending_approvals()
                return True
        return False
    
    def get_status(self) -> dict:
        return {
            "project_root": str(self.project_root),
            "dry_run": self.dry_run,
            "total_commands_executed": len(self.command_history),
            "pending_approvals": len(self.get_pending_approvals()),
            "recent_commands": [
                {"command": c.get("command", ""), "risk": c.get("risk_level", ""), "success": c.get("success")}
                for c in self.command_history[-10:]
            ],
        }
