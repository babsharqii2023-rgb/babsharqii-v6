"""
BABSHARQII v40.0 — External Project Controller (EPC)
متحكم المشاريع الخارجية — استنساخ + قراءة + كتابة + بناء + اختبار + نشر + طلبات سحب

A comprehensive, safety-first controller for managing external projects.
Allows Mamoun to clone, read, modify, build, test, deploy, and create
pull requests for external git repositories — all with proper validation,
rollback capability, and persistent tracking.

Key Features:
  - Clone git repositories with branch selection
  - Read and modify files in external projects
  - Run build/test/deploy commands with safety validation
  - Create pull requests via GitHub CLI
  - Manage multiple external projects simultaneously
  - Persistent tracking via unified database (epc_projects table)
  - Rollback capability with automatic backups
  - Protected repo patterns and command validation

Database Table: epc_projects
  - id, name, url, branch, local_path, status, created_at, last_activity

Usage:
    epc = ExternalProjectController()
    result = await epc.clone_repo("https://github.com/user/repo.git", branch="main")
    content = await epc.read_file(result["project_id"], "README.md")
    await epc.write_file(result["project_id"], "src/main.py", "print('hello')")
    build_result = await epc.build_project(result["project_id"])
    test_result = await epc.test_project(result["project_id"])
    deploy_result = await epc.deploy_project(result["project_id"], target="preview")
    pr_result = await epc.create_pull_request(result["project_id"], "Fix bug", "Description")
    projects = await epc.list_projects()
    status = await epc.get_project_status(result["project_id"])
    controller_status = epc.get_status()
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

from mamoun.core.llm_client import get_llm_client, LLMMessage
from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.core.external_project_controller")


# ═══════════════════════════════════════════════════════════════════════════════
#  Constants & Safety Configuration
# ═══════════════════════════════════════════════════════════════════════════════

# Base directory for all cloned external projects
EXTERNAL_PROJECTS_DIR = Path(
    os.getenv("MAMOUN_EXTERNAL_PROJECTS_DIR", "/home/z/my-project/external-projects")
)

# Maximum command execution timeout in seconds
MAX_COMMAND_TIMEOUT = 300  # 5 minutes

# Default clone timeout in seconds
DEFAULT_CLONE_TIMEOUT = 120

# Maximum file size for read/write operations (1 MB)
MAX_FILE_SIZE = 1_048_576

# Maximum number of concurrent project operations
MAX_CONCURRENT_OPS = 5

# Forbidden command patterns — safety guard against destructive operations
FORBIDDEN_COMMAND_PATTERNS = [
    "rm -rf /",
    "rm -rf ~",
    "mkfs.",
    "dd if=",
    ":(){ :|:& };:",
    "shutdown",
    "reboot",
    "init 0",
    "init 6",
    "format ",
    "del /f /s /q C:",
    "> /dev/sd",
    "mv / ",
    "chmod -R 777 /",
    "chown -R",
    "wget.*|.*sh",
    "curl.*|.*sh",
    "passwd",
    "useradd",
    "userdel",
    "iptables",
    "ufw",
    "systemctl",
    "service ",
    "crontab",
    "nohup",
]

# Protected repository URL patterns — these repos cannot be cloned or modified
PROTECTED_REPO_PATTERNS = [
    "babsharqii2023-rgb/babsharqii-v5",
    "mamoun-core",
    "safety_guard",
    "laws.yaml",
]

# Protected file patterns — cannot be read or written in external projects
PROTECTED_FILE_PATTERNS = [
    ".env",
    ".env.local",
    ".env.production",
    ".key",
    ".pem",
    ".ssh/",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "service-account.json",
    "laws.yaml",
    "safety_guard.py",
]

# Directories to skip when walking project trees
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".next", "dist", "build",
    ".backups", "venv", ".venv", ".tox", ".mypy_cache", ".pytest_cache",
    "coverage", ".coverage", "htmlcov", ".eggs", "*.egg-info",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class ProjectStatus:
    """Possible statuses for an external project."""
    CLONING = "cloning"
    READY = "ready"
    BUILDING = "building"
    TESTING = "testing"
    DEPLOYING = "deploying"
    ERROR = "error"
    ARCHIVED = "archived"


@dataclass
class RollbackSnapshot:
    """A snapshot for rollback capability."""
    snapshot_id: str = ""
    project_id: str = ""
    file_path: str = ""
    original_content: str = ""
    timestamp: float = 0.0
    operation: str = ""  # write_file, run_command, etc.

    def __post_init__(self):
        if not self.snapshot_id:
            self.snapshot_id = f"snap_{uuid.uuid4().hex[:12]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "project_id": self.project_id,
            "file_path": self.file_path,
            "original_content_hash": hash(self.original_content) if self.original_content else 0,
            "content_size": len(self.original_content) if self.original_content else 0,
            "timestamp": self.timestamp,
            "operation": self.operation,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  External Project Controller
# ═══════════════════════════════════════════════════════════════════════════════

class ExternalProjectController:
    """
    متحكم المشاريع الخارجية — The comprehensive controller for external projects.

    Provides full lifecycle management of external git repositories:
      - Clone repositories with branch selection
      - Read and write files with safety checks
      - Execute build, test, and deploy commands
      - Create pull requests via git CLI
      - Track all projects in persistent database
      - Rollback capability for all modifications
      - Safety validation for all operations

    Thread safety: This controller uses an asyncio Semaphore to limit concurrent
    operations. Database access is through the unified DB connection pattern.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the ExternalProject Controller.

        Args:
            db_path: Optional override for the database path.
                     Defaults to the unified DB path.
        """
        self._db_path = db_path or UNIFIED_DB_PATH
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_OPS)
        self._snapshots: Dict[str, List[RollbackSnapshot]] = {}
        self._active_operations: Dict[str, str] = {}  # project_id → operation
        self._stats = {
            "total_clones": 0,
            "total_reads": 0,
            "total_writes": 0,
            "total_commands": 0,
            "total_builds": 0,
            "total_tests": 0,
            "total_deploys": 0,
            "total_prs": 0,
            "total_rollbacks": 0,
            "total_errors": 0,
        }

        # Ensure base directory exists
        EXTERNAL_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize database schema
        self._init_db()

        logger.info(
            "ExternalProjectController initialized — projects dir: %s",
            EXTERNAL_PROJECTS_DIR,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Database Initialization
    # ─────────────────────────────────────────────────────────────────────────

    def _init_db(self):
        """
        إنشاء جدول المشاريع الخارجية في قاعدة البيانات الموحدة
        Create the epc_projects table if it doesn't exist.
        """
        conn = get_db_connection(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS epc_projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    branch TEXT DEFAULT 'main',
                    local_path TEXT NOT NULL,
                    status TEXT DEFAULT 'cloning',
                    created_at REAL NOT NULL,
                    last_activity REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_epc_projects_status
                ON epc_projects(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_epc_projects_name
                ON epc_projects(name)
            """)

            # Rollback snapshots table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS epc_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    original_content TEXT DEFAULT '',
                    timestamp REAL NOT NULL,
                    operation TEXT DEFAULT '',
                    FOREIGN KEY (project_id) REFERENCES epc_projects(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_epc_snapshots_project
                ON epc_snapshots(project_id)
            """)

            # Command history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS epc_command_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    command TEXT NOT NULL,
                    exit_code INTEGER DEFAULT -1,
                    stdout TEXT DEFAULT '',
                    stderr TEXT DEFAULT '',
                    timestamp REAL NOT NULL,
                    duration_ms REAL DEFAULT 0,
                    FOREIGN KEY (project_id) REFERENCES epc_projects(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_epc_cmd_history_project
                ON epc_command_history(project_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_epc_cmd_history_ts
                ON epc_command_history(timestamp)
            """)

            conn.commit()
            logger.debug("EPC database schema initialized")
        except Exception as e:
            logger.error("Failed to initialize EPC database schema: %s", e)
            conn.rollback()
        finally:
            conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Safety Validation
    # ─────────────────────────────────────────────────────────────────────────

    def _validate_command(self, command: str) -> tuple[bool, str]:
        """
        فحص أمان الأمر — Validate that a command is safe to execute.

        Checks against forbidden patterns and dangerous constructs.

        Args:
            command: The shell command to validate.

        Returns:
            Tuple of (is_safe, reason). If is_safe is False, reason explains why.
        """
        cmd_lower = command.lower().strip()

        # Check forbidden patterns
        for pattern in FORBIDDEN_COMMAND_PATTERNS:
            if pattern.lower() in cmd_lower:
                return False, f"Forbidden pattern detected: {pattern}"

        # Block attempts to write outside project directory
        if ".." in command and (">" in command or ">>" in command):
            return False, "Attempt to write outside project directory detected"

        # Block network operations that could exfiltrate data
        network_patterns = [
            "nc -l", "ncat", "socat", "python -m http.server",
            "php -S", "ruby -run -e httpd",
        ]
        for pattern in network_patterns:
            if pattern.lower() in cmd_lower:
                return False, f"Network server pattern detected: {pattern}"

        # Block pip install to system (allow within venv only)
        if "pip install" in cmd_lower and "--user" not in cmd_lower:
            # Allow if explicitly targeting a venv
            if "venv" not in cmd_lower and ".venv" not in cmd_lower:
                logger.warning("pip install without venv detected: %s", command)

        return True, "Command is safe"

    def _validate_repo_url(self, url: str) -> tuple[bool, str]:
        """
        فحص أمان رابط المستودع — Validate that a repository URL is allowed.

        Checks against protected repo patterns.

        Args:
            url: The git repository URL to validate.

        Returns:
            Tuple of (is_allowed, reason).
        """
        url_lower = url.lower()

        for pattern in PROTECTED_REPO_PATTERNS:
            if pattern.lower() in url_lower:
                return False, f"Protected repository: {pattern}"

        # Only allow https and git protocols
        if not (url_lower.startswith("https://") or
                url_lower.startswith("git@") or
                url_lower.startswith("git://") or
                url_lower.startswith("ssh://")):
            return False, f"Unsupported protocol in URL: {url[:30]}"

        return True, "Repository URL is allowed"

    def _validate_file_path(self, file_path: str) -> tuple[bool, str]:
        """
        فحص أمان مسار الملف — Validate that a file path is safe to access.

        Checks against protected file patterns and path traversal.

        Args:
            file_path: The relative file path within a project.

        Returns:
            Tuple of (is_safe, reason).
        """
        # Block path traversal
        if ".." in file_path:
            return False, "Path traversal detected (.. in path)"

        # Block absolute paths
        if file_path.startswith("/"):
            return False, "Absolute paths not allowed"

        # Check protected file patterns
        file_lower = file_path.lower()
        for pattern in PROTECTED_FILE_PATTERNS:
            if pattern.lower() in file_lower:
                return False, f"Protected file pattern: {pattern}"

        return True, "File path is safe"

    def _validate_project_access(self, project_id: str) -> tuple[bool, Optional[dict], str]:
        """
        فحص وجود المشروع — Validate that a project exists and get its record.

        Args:
            project_id: The project ID to look up.

        Returns:
            Tuple of (exists, project_record_or_None, reason).
        """
        conn = get_db_connection(self._db_path)
        try:
            cur = conn.execute(
                "SELECT * FROM epc_projects WHERE id = ?",
                (project_id,),
            )
            row = cur.fetchone()
            if row is None:
                return False, None, f"Project not found: {project_id}"
            project = dict(row)
            # Check if the local path still exists
            if not Path(project["local_path"]).exists():
                return False, project, f"Project directory missing: {project['local_path']}"
            return True, project, "Project exists"
        finally:
            conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Database Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _update_project_status(self, project_id: str, status: str):
        """Update the status and last_activity of a project in the database."""
        conn = get_db_connection(self._db_path)
        try:
            conn.execute(
                "UPDATE epc_projects SET status = ?, last_activity = ? WHERE id = ?",
                (status, time.time(), project_id),
            )
            conn.commit()
        except Exception as e:
            logger.error("Failed to update project status: %s", e)
        finally:
            conn.close()

    def _record_command(self, project_id: str, command: str, exit_code: int,
                        stdout: str, stderr: str, duration_ms: float):
        """Record a command execution in the history table."""
        conn = get_db_connection(self._db_path)
        try:
            conn.execute(
                """INSERT INTO epc_command_history
                   (project_id, command, exit_code, stdout, stderr, timestamp, duration_ms)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (project_id, command, exit_code,
                 stdout[:5000], stderr[:5000], time.time(), duration_ms),
            )
            conn.commit()
        except Exception as e:
            logger.error("Failed to record command history: %s", e)
        finally:
            conn.close()

    def _save_snapshot(self, snapshot: RollbackSnapshot):
        """Save a rollback snapshot to the database."""
        conn = get_db_connection(self._db_path)
        try:
            conn.execute(
                """INSERT INTO epc_snapshots
                   (snapshot_id, project_id, file_path, original_content, timestamp, operation)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (snapshot.snapshot_id, snapshot.project_id, snapshot.file_path,
                 snapshot.original_content, snapshot.timestamp, snapshot.operation),
            )
            conn.commit()
        except Exception as e:
            logger.error("Failed to save snapshot: %s", e)
        finally:
            conn.close()

        # Also keep in memory for quick access
        if snapshot.project_id not in self._snapshots:
            self._snapshots[snapshot.project_id] = []
        self._snapshots[snapshot.project_id].append(snapshot)

    # ─────────────────────────────────────────────────────────────────────────
    # Core Operations
    # ─────────────────────────────────────────────────────────────────────────

    async def clone_repo(self, url: str, branch: str = "main") -> dict:
        """
        استنساخ مستودع خارجي — Clone a git repository.

        Clones the specified repository into the external projects directory,
        registers it in the database, and returns the project info.

        Args:
            url: The git repository URL (https or git@ protocol).
            branch: The branch to clone (default: "main").

        Returns:
            Dict with keys: status, project_id, name, url, branch, local_path

        Raises:
            ValueError: If the URL is invalid or protected.
            RuntimeError: If the clone operation fails.
        """
        # Validate repository URL
        is_allowed, reason = self._validate_repo_url(url)
        if not is_allowed:
            self._stats["total_errors"] += 1
            raise ValueError(f"Repository URL not allowed: {reason}")

        async with self._semaphore:
            # Generate project ID and determine local path
            project_id = f"epc_{uuid.uuid4().hex[:12]}"
            repo_name = url.rstrip('/').split('/')[-1].replace('.git', '')
            if not repo_name:
                repo_name = f"repo_{int(time.time())}"
            local_path = EXTERNAL_PROJECTS_DIR / repo_name

            # Handle duplicate directory names
            if local_path.exists():
                local_path = EXTERNAL_PROJECTS_DIR / f"{repo_name}_{int(time.time())}"

            # Register project in database as "cloning"
            conn = get_db_connection(self._db_path)
            try:
                conn.execute(
                    """INSERT INTO epc_projects
                       (id, name, url, branch, local_path, status, created_at, last_activity)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (project_id, repo_name, url, branch, str(local_path),
                     ProjectStatus.CLONING, time.time(), time.time()),
                )
                conn.commit()
            except Exception as e:
                logger.error("Failed to register project in DB: %s", e)
                conn.rollback()
                self._stats["total_errors"] += 1
                raise RuntimeError(f"Failed to register project: {e}")
            finally:
                conn.close()

            # Execute git clone
            try:
                cmd = ["git", "clone", "--branch", branch, "--single-branch", url, str(local_path)]

                result = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    result.communicate(),
                    timeout=DEFAULT_CLONE_TIMEOUT,
                )

                if result.returncode != 0:
                    error_msg = stderr.decode('utf-8', errors='replace')[:500]
                    # If the specified branch doesn't exist, try cloning without branch constraint
                    if "Remote branch" in error_msg and "not found" in error_msg:
                        logger.warning(
                            "Branch '%s' not found for %s, cloning default branch",
                            branch, url,
                        )
                        cmd = ["git", "clone", url, str(local_path)]
                        # Remove the failed directory first
                        if local_path.exists():
                            shutil.rmtree(str(local_path), ignore_errors=True)

                        result = await asyncio.create_subprocess_exec(
                            *cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        stdout, stderr = await asyncio.wait_for(
                            result.communicate(),
                            timeout=DEFAULT_CLONE_TIMEOUT,
                        )

                        if result.returncode != 0:
                            error_msg = stderr.decode('utf-8', errors='replace')[:500]
                            self._update_project_status(project_id, ProjectStatus.ERROR)
                            self._stats["total_errors"] += 1
                            raise RuntimeError(f"Git clone failed: {error_msg}")

                        # Update branch to whatever was cloned
                        # Determine the default branch
                        try:
                            branch_result = await asyncio.create_subprocess_exec(
                                "git", "rev-parse", "--abbrev-ref", "HEAD",
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE,
                                cwd=str(local_path),
                            )
                            br_out, _ = await asyncio.wait_for(branch_result.communicate(), timeout=10)
                            actual_branch = br_out.decode('utf-8').strip()
                            conn2 = get_db_connection(self._db_path)
                            try:
                                conn2.execute(
                                    "UPDATE epc_projects SET branch = ? WHERE id = ?",
                                    (actual_branch, project_id),
                                )
                                conn2.commit()
                            finally:
                                conn2.close()
                        except Exception:
                            pass  # Non-critical, keep original branch name

                    else:
                        self._update_project_status(project_id, ProjectStatus.ERROR)
                        self._stats["total_errors"] += 1
                        raise RuntimeError(f"Git clone failed: {error_msg}")

                # Clone succeeded — update status to "ready"
                self._update_project_status(project_id, ProjectStatus.READY)
                self._stats["total_clones"] += 1

                logger.info(
                    "Cloned repository: %s → %s (project_id: %s)",
                    url, local_path, project_id,
                )

                return {
                    "status": "cloned",
                    "project_id": project_id,
                    "name": repo_name,
                    "url": url,
                    "branch": branch,
                    "local_path": str(local_path),
                }

            except asyncio.TimeoutError:
                self._update_project_status(project_id, ProjectStatus.ERROR)
                # Clean up partial clone
                if local_path.exists():
                    shutil.rmtree(str(local_path), ignore_errors=True)
                self._stats["total_errors"] += 1
                raise RuntimeError(
                    f"Clone timed out after {DEFAULT_CLONE_TIMEOUT}s for {url}"
                )

            except RuntimeError:
                raise  # Re-raise our own errors

            except Exception as e:
                self._update_project_status(project_id, ProjectStatus.ERROR)
                # Clean up partial clone
                if local_path.exists():
                    shutil.rmtree(str(local_path), ignore_errors=True)
                self._stats["total_errors"] += 1
                raise RuntimeError(f"Unexpected clone error: {e}")

    async def read_file(self, project_id: str, file_path: str) -> str:
        """
        قراءة ملف من مشروع خارجي — Read a file from an external project.

        Args:
            project_id: The project ID returned by clone_repo.
            file_path: Relative path to the file within the project.

        Returns:
            The file contents as a string.

        Raises:
            ValueError: If the file path is invalid or protected.
            FileNotFoundError: If the file doesn't exist.
            RuntimeError: If the file can't be read.
        """
        # Validate file path
        is_safe, reason = self._validate_file_path(file_path)
        if not is_safe:
            self._stats["total_errors"] += 1
            raise ValueError(f"File path not allowed: {reason}")

        # Validate project access
        exists, project, reason = self._validate_project_access(project_id)
        if not exists:
            raise FileNotFoundError(f"Project not accessible: {reason}")

        full_path = Path(project["local_path"]) / file_path

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not full_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Check file size
        try:
            file_size = full_path.stat().st_size
            if file_size > MAX_FILE_SIZE:
                raise RuntimeError(
                    f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE})"
                )
        except OSError as e:
            raise RuntimeError(f"Cannot stat file: {e}")

        # Read file content
        try:
            content = await asyncio.to_thread(
                self._read_file_sync, str(full_path)
            )
            self._stats["total_reads"] += 1

            # Update last activity
            self._update_project_status(project_id, project.get("status", ProjectStatus.READY))

            logger.debug("Read file: %s from project %s", file_path, project_id)
            return content

        except Exception as e:
            self._stats["total_errors"] += 1
            raise RuntimeError(f"Failed to read file: {e}")

    @staticmethod
    def _read_file_sync(path: str) -> str:
        """Synchronous file read with encoding fallback."""
        p = Path(path)
        try:
            return p.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            return p.read_text(encoding='latin-1')

    async def write_file(self, project_id: str, file_path: str, content: str) -> dict:
        """
        كتابة ملف في مشروع خارجي — Write (or create) a file in an external project.

        Creates an automatic backup before writing for rollback capability.

        Args:
            project_id: The project ID returned by clone_repo.
            file_path: Relative path to the file within the project.
            content: The new file content.

        Returns:
            Dict with keys: status, file_path, size, backup_path, snapshot_id

        Raises:
            ValueError: If the file path is invalid or protected.
            FileNotFoundError: If the project doesn't exist.
            RuntimeError: If the write operation fails.
        """
        # Validate file path
        is_safe, reason = self._validate_file_path(file_path)
        if not is_safe:
            self._stats["total_errors"] += 1
            raise ValueError(f"File path not allowed: {reason}")

        # Validate project access
        exists, project, reason = self._validate_project_access(project_id)
        if not exists and project is None:
            raise FileNotFoundError(f"Project not found: {reason}")

        local_path = Path(project["local_path"])
        full_path = local_path / file_path

        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Read current content for rollback (if file exists)
        original_content = ""
        if full_path.exists():
            try:
                original_content = await asyncio.to_thread(
                    self._read_file_sync, str(full_path)
                )
            except Exception:
                original_content = ""  # File may be binary, that's okay

        # Create rollback snapshot
        snapshot = RollbackSnapshot(
            project_id=project_id,
            file_path=file_path,
            original_content=original_content,
            operation="write_file",
        )
        self._save_snapshot(snapshot)

        # Create backup file
        backup_path = None
        if full_path.exists():
            backup_dir = local_path / ".backups"
            backup_dir.mkdir(exist_ok=True)
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{full_path.stem}_{timestamp_str}{full_path.suffix}"
            backup_path = backup_dir / backup_name
            try:
                await asyncio.to_thread(shutil.copy2, str(full_path), str(backup_path))
            except Exception as e:
                logger.warning("Failed to create backup for %s: %s", file_path, e)
                backup_path = None

        # Write the new content
        try:
            await asyncio.to_thread(
                self._write_file_sync, str(full_path), content
            )
            self._stats["total_writes"] += 1

            # Update last activity
            self._update_project_status(project_id, project.get("status", ProjectStatus.READY))

            logger.info(
                "Wrote file: %s in project %s (%d bytes, snapshot: %s)",
                file_path, project_id, len(content), snapshot.snapshot_id,
            )

            return {
                "status": "written",
                "file_path": file_path,
                "size": len(content),
                "backup_path": str(backup_path) if backup_path else None,
                "snapshot_id": snapshot.snapshot_id,
            }

        except Exception as e:
            self._stats["total_errors"] += 1
            raise RuntimeError(f"Failed to write file: {e}")

    @staticmethod
    def _write_file_sync(path: str, content: str):
        """Synchronous file write."""
        Path(path).write_text(content, encoding='utf-8')

    async def run_command(self, project_id: str, command: str) -> dict:
        """
        تشغيل أمر في دليل المشروع — Run a command in the project directory.

        Executes the command with safety validation and timeout enforcement.
        Records the command in the history table.

        Args:
            project_id: The project ID returned by clone_repo.
            command: The shell command to execute.

        Returns:
            Dict with keys: status, exit_code, stdout, stderr, duration_ms, command

        Raises:
            ValueError: If the command is not safe.
            FileNotFoundError: If the project doesn't exist.
            RuntimeError: If the command fails to execute.
        """
        # Validate command safety
        is_safe, reason = self._validate_command(command)
        if not is_safe:
            self._stats["total_errors"] += 1
            raise ValueError(f"Command not allowed: {reason}")

        # Validate project access
        exists, project, reason = self._validate_project_access(project_id)
        if not exists and project is None:
            raise FileNotFoundError(f"Project not found: {reason}")

        local_path = project["local_path"]
        if not Path(local_path).exists():
            raise FileNotFoundError(f"Project directory missing: {local_path}")

        # Execute the command
        start_time = time.time()
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=local_path,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=MAX_COMMAND_TIMEOUT,
            )

            duration_ms = (time.time() - start_time) * 1000
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')

            # Record in command history
            self._record_command(
                project_id, command, process.returncode,
                stdout_str, stderr_str, duration_ms,
            )

            self._stats["total_commands"] += 1

            # Update last activity
            self._update_project_status(project_id, project.get("status", ProjectStatus.READY))

            logger.info(
                "Command executed in project %s: '%s' (exit: %d, %.0fms)",
                project_id, command[:50], process.returncode, duration_ms,
            )

            return {
                "status": "completed",
                "exit_code": process.returncode,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "duration_ms": round(duration_ms, 2),
                "command": command,
            }

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            self._record_command(
                project_id, command, -1,
                "", f"Timed out after {MAX_COMMAND_TIMEOUT}s", duration_ms,
            )
            self._stats["total_errors"] += 1
            raise RuntimeError(
                f"Command timed out after {MAX_COMMAND_TIMEOUT}s: {command[:50]}"
            )

        except Exception as e:
            self._stats["total_errors"] += 1
            raise RuntimeError(f"Command execution failed: {e}")

    async def build_project(self, project_id: str) -> dict:
        """
        بناء المشروع — Build an external project.

        Detects the project type (Node.js, Python, etc.) and runs the
        appropriate build command.

        Args:
            project_id: The project ID returned by clone_repo.

        Returns:
            Dict with keys: status, project_type, build_command, exit_code,
                            stdout, stderr, duration_ms

        Raises:
            FileNotFoundError: If the project doesn't exist.
            RuntimeError: If the build fails.
        """
        exists, project, reason = self._validate_project_access(project_id)
        if not exists and project is None:
            raise FileNotFoundError(f"Project not found: {reason}")

        local_path = Path(project["local_path"])

        # Detect project type and determine build command
        build_command = None
        project_type = "unknown"

        if (local_path / "package.json").exists():
            project_type = "node"
            # Check for custom build script
            try:
                pkg = json.loads((local_path / "package.json").read_text(encoding='utf-8'))
                scripts = pkg.get("scripts", {})
                if "build" in scripts:
                    build_command = "npm run build"
                elif "compile" in scripts:
                    build_command = "npm run compile"
                else:
                    build_command = "npm install"  # Fallback to install
            except Exception:
                build_command = "npm install"

        elif (local_path / "pyproject.toml").exists():
            project_type = "python-pyproject"
            build_command = "pip install -e . 2>/dev/null || python -m build"

        elif (local_path / "setup.py").exists():
            project_type = "python-setup"
            build_command = "pip install -e . 2>/dev/null || python setup.py build"

        elif (local_path / "Makefile").exists():
            project_type = "make"
            build_command = "make build 2>/dev/null || make"

        elif (local_path / "Cargo.toml").exists():
            project_type = "rust"
            build_command = "cargo build --release"

        elif (local_path / "go.mod").exists():
            project_type = "go"
            build_command = "go build ./..."

        elif (local_path / "pom.xml").exists():
            project_type = "java-maven"
            build_command = "mvn compile"

        elif (local_path / "build.gradle").exists():
            project_type = "java-gradle"
            build_command = "./gradlew build 2>/dev/null || gradle build"

        else:
            return {
                "status": "no_build_system",
                "project_type": project_type,
                "message": "No recognized build system found",
            }

        # Update project status
        self._update_project_status(project_id, ProjectStatus.BUILDING)

        # Execute build
        try:
            result = await self.run_command(project_id, build_command)
            self._stats["total_builds"] += 1

            # Update status based on result
            if result["exit_code"] == 0:
                self._update_project_status(project_id, ProjectStatus.READY)
            else:
                self._update_project_status(project_id, ProjectStatus.ERROR)

            return {
                "status": "build_success" if result["exit_code"] == 0 else "build_failed",
                "project_type": project_type,
                "build_command": build_command,
                "exit_code": result["exit_code"],
                "stdout": result["stdout"][-2000:],
                "stderr": result["stderr"][-1000:],
                "duration_ms": result["duration_ms"],
            }

        except RuntimeError as e:
            self._update_project_status(project_id, ProjectStatus.ERROR)
            self._stats["total_errors"] += 1
            return {
                "status": "build_error",
                "project_type": project_type,
                "build_command": build_command,
                "error": str(e),
            }

    async def test_project(self, project_id: str) -> dict:
        """
        اختبار المشروع — Run tests for an external project.

        Detects the test framework and runs the appropriate test command.

        Args:
            project_id: The project ID returned by clone_repo.

        Returns:
            Dict with keys: status, test_framework, test_command, exit_code,
                            stdout, stderr, duration_ms, tests_passed,
                            tests_failed

        Raises:
            FileNotFoundError: If the project doesn't exist.
        """
        exists, project, reason = self._validate_project_access(project_id)
        if not exists and project is None:
            raise FileNotFoundError(f"Project not found: {reason}")

        local_path = Path(project["local_path"])

        # Detect test framework and determine test command
        test_command = None
        test_framework = "unknown"

        if (local_path / "package.json").exists():
            try:
                pkg = json.loads((local_path / "package.json").read_text(encoding='utf-8'))
                scripts = pkg.get("scripts", {})
                if "test" in scripts:
                    test_framework = "npm-test"
                    test_command = "npm test"
                elif "jest" in str(pkg.get("devDependencies", {})):
                    test_framework = "jest"
                    test_command = "npx jest"
            except Exception:
                pass

        elif (local_path / "pytest.ini").exists() or (local_path / "conftest.py").exists():
            test_framework = "pytest"
            test_command = "python -m pytest -v --tb=short 2>/dev/null || pytest -v --tb=short"

        elif (local_path / "setup.cfg").exists():
            try:
                cfg = (local_path / "setup.cfg").read_text(encoding='utf-8')
                if "pytest" in cfg or "tool:pytest" in cfg:
                    test_framework = "pytest"
                    test_command = "python -m pytest -v --tb=short"
                elif "unittest" in cfg:
                    test_framework = "unittest"
                    test_command = "python -m unittest discover -v"
            except Exception:
                pass

        elif list(local_path.glob("test_*.py")) or list(local_path.glob("*_test.py")):
            test_framework = "pytest"
            test_command = "python -m pytest -v --tb=short 2>/dev/null || python -m unittest discover -v"

        elif (local_path / "tests").is_dir() and (local_path / "setup.py").exists():
            test_framework = "python-unittest"
            test_command = "python -m unittest discover -s tests -v"

        elif (local_path / "Makefile").exists():
            test_framework = "make-test"
            test_command = "make test 2>/dev/null || make check"

        elif (local_path / "Cargo.toml").exists():
            test_framework = "cargo-test"
            test_command = "cargo test"

        elif (local_path / "go.mod").exists():
            test_framework = "go-test"
            test_command = "go test ./..."

        if test_command is None:
            return {
                "status": "no_test_framework",
                "test_framework": test_framework,
                "message": "No recognized test framework found",
            }

        # Update project status
        self._update_project_status(project_id, ProjectStatus.TESTING)

        # Execute tests
        try:
            result = await self.run_command(project_id, test_command)
            self._stats["total_tests"] += 1

            # Parse test results from output
            tests_passed = 0
            tests_failed = 0
            output = result["stdout"] + result["stderr"]

            # Try to extract pass/fail counts from common patterns
            import re
            # pytest pattern: "X passed, Y failed"
            pytest_match = re.search(r'(\d+) passed', output)
            if pytest_match:
                tests_passed = int(pytest_match.group(1))
            pytest_fail = re.search(r'(\d+) failed', output)
            if pytest_fail:
                tests_failed = int(pytest_fail.group(1))

            # Jest pattern: "Tests: X passed, Y failed"
            if tests_passed == 0 and tests_failed == 0:
                jest_match = re.search(r'Tests:\s+(\d+) passed', output)
                if jest_match:
                    tests_passed = int(jest_match.group(1))
                jest_fail = re.search(r'(\d+) failed', output)
                if jest_fail:
                    tests_failed = int(jest_fail.group(1))

            # go test pattern: "PASS X  FAIL Y" or just "ok" / "FAIL"
            if tests_passed == 0 and tests_failed == 0:
                if "PASS" in output:
                    pass_count = output.count("PASS")
                    tests_passed = max(pass_count, 1)
                if "FAIL" in output:
                    fail_count = output.count("FAIL")
                    tests_failed = max(fail_count, 1)

            # Update status based on result
            if result["exit_code"] == 0:
                self._update_project_status(project_id, ProjectStatus.READY)
            else:
                # Build might still be okay even if some tests fail
                self._update_project_status(project_id, ProjectStatus.READY)

            return {
                "status": "tests_passed" if result["exit_code"] == 0 else "tests_failed",
                "test_framework": test_framework,
                "test_command": test_command,
                "exit_code": result["exit_code"],
                "stdout": result["stdout"][-2000:],
                "stderr": result["stderr"][-1000:],
                "duration_ms": result["duration_ms"],
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
            }

        except RuntimeError as e:
            self._update_project_status(project_id, ProjectStatus.ERROR)
            self._stats["total_errors"] += 1
            return {
                "status": "test_error",
                "test_framework": test_framework,
                "test_command": test_command,
                "error": str(e),
            }

    async def deploy_project(self, project_id: str, target: str = "preview") -> dict:
        """
        نشر المشروع — Deploy an external project.

        Supports preview, staging, and production targets.
        Detects the project type and runs appropriate deploy commands.

        Args:
            project_id: The project ID returned by clone_repo.
            target: Deployment target: "preview", "staging", or "production".

        Returns:
            Dict with keys: status, target, deploy_commands, results

        Raises:
            FileNotFoundError: If the project doesn't exist.
            ValueError: If the target is invalid.
        """
        # Validate target
        valid_targets = {"preview", "staging", "production"}
        if target not in valid_targets:
            raise ValueError(
                f"Invalid deploy target: {target}. Must be one of: {valid_targets}"
            )

        exists, project, reason = self._validate_project_access(project_id)
        if not exists and project is None:
            raise FileNotFoundError(f"Project not found: {reason}")

        local_path = Path(project["local_path"])

        # Determine deploy commands based on project type and target
        deploy_commands = []

        if (local_path / "package.json").exists():
            # Node.js project
            try:
                pkg = json.loads((local_path / "package.json").read_text(encoding='utf-8'))
                scripts = pkg.get("scripts", {})

                # Build first
                if "build" in scripts:
                    deploy_commands.append("npm run build")

                # Deploy command depends on target
                if target == "preview" and "deploy:preview" in scripts:
                    deploy_commands.append("npm run deploy:preview")
                elif target == "staging" and "deploy:staging" in scripts:
                    deploy_commands.append("npm run deploy:staging")
                elif target == "production" and "deploy" in scripts:
                    deploy_commands.append("npm run deploy")
                elif "deploy:preview" in scripts:
                    deploy_commands.append(f"npm run deploy:preview")
                else:
                    # Try vercel/netlify CLI if available
                    if (local_path / "vercel.json").exists():
                        deploy_commands.append("npx vercel --yes")
                    elif (local_path / "netlify.toml").exists():
                        deploy_commands.append("npx netlify deploy --prod")
                    else:
                        deploy_commands.append("echo 'No deploy script found — build completed'")

            except Exception:
                deploy_commands.append("npm run build")

        elif (local_path / "Dockerfile").exists():
            # Docker-based deployment
            image_tag = f"{project['name']}:{target}"
            deploy_commands.append(f"docker build -t {image_tag} .")
            if target == "production":
                deploy_commands.append(f"docker push {image_tag}")

        elif (local_path / "docker-compose.yml").exists() or (local_path / "docker-compose.yaml").exists():
            compose_file = "docker-compose.yml"
            if (local_path / "docker-compose.yaml").exists():
                compose_file = "docker-compose.yaml"
            deploy_commands.append(f"docker-compose -f {compose_file} up -d --build")

        elif (local_path / "pyproject.toml").exists() or (local_path / "setup.py").exists():
            # Python project
            deploy_commands.append("pip install -e . 2>/dev/null || echo 'Install skipped'")
            # Look for Procfile or similar
            if (local_path / "Procfile").exists():
                deploy_commands.append("echo 'Procfile detected — ready for Heroku deployment'")

        elif (local_path / "Makefile").exists():
            if target == "production":
                deploy_commands.append("make deploy 2>/dev/null || make release 2>/dev/null || make build")
            else:
                deploy_commands.append("make deploy 2>/dev/null || make build")

        else:
            return {
                "status": "no_deploy_system",
                "target": target,
                "message": "No recognized deployment system found",
            }

        if not deploy_commands:
            return {
                "status": "no_deploy_commands",
                "target": target,
                "message": "Could not determine deploy commands for this project",
            }

        # Update project status
        self._update_project_status(project_id, ProjectStatus.DEPLOYING)

        # Execute deploy commands sequentially
        results = []
        all_success = True

        for cmd in deploy_commands:
            try:
                result = await self.run_command(project_id, cmd)
                results.append({
                    "command": cmd,
                    "exit_code": result["exit_code"],
                    "stdout": result["stdout"][-1000:],
                    "stderr": result["stderr"][-500:],
                    "duration_ms": result["duration_ms"],
                })
                if result["exit_code"] != 0:
                    all_success = False
            except RuntimeError as e:
                results.append({
                    "command": cmd,
                    "exit_code": -1,
                    "error": str(e),
                })
                all_success = False

        self._stats["total_deploys"] += 1

        # Update project status
        final_status = ProjectStatus.READY if all_success else ProjectStatus.ERROR
        self._update_project_status(project_id, final_status)

        return {
            "status": "deploy_success" if all_success else "deploy_failed",
            "target": target,
            "deploy_commands": deploy_commands,
            "results": results,
        }

    async def create_pull_request(self, project_id: str, title: str,
                                  description: str) -> dict:
        """
        إنشاء طلب سحب — Create a pull request for the external project.

        Uses the GitHub CLI (gh) to create a PR. If gh is not available,
        falls back to git push and provides manual instructions.

        Args:
            project_id: The project ID returned by clone_repo.
            title: The PR title.
            description: The PR description/body.

        Returns:
            Dict with keys: status, pr_url, branch, message

        Raises:
            FileNotFoundError: If the project doesn't exist.
            RuntimeError: If PR creation fails.
        """
        exists, project, reason = self._validate_project_access(project_id)
        if not exists and project is None:
            raise FileNotFoundError(f"Project not found: {reason}")

        local_path = Path(project["local_path"])

        if not (local_path / ".git").exists():
            raise RuntimeError("Not a git repository — cannot create PR")

        # Generate a feature branch name
        safe_title = "".join(c if c.isalnum() or c in "-_" else "-" for c in title.lower())
        safe_title = safe_title[:40].strip("-")
        timestamp = int(time.time())
        branch_name = f"mamoun/{safe_title}-{timestamp}"

        results = {}

        # Step 1: Create and checkout new branch
        try:
            checkout_result = await self.run_command(
                project_id, f"git checkout -b {branch_name}"
            )
            if checkout_result["exit_code"] != 0:
                raise RuntimeError(f"Failed to create branch: {checkout_result['stderr']}")
            results["branch_created"] = branch_name
        except RuntimeError as e:
            # Try git checkout main first, then branch
            try:
                await self.run_command(project_id, "git checkout main 2>/dev/null || git checkout master")
                checkout_result = await self.run_command(
                    project_id, f"git checkout -b {branch_name}"
                )
                if checkout_result["exit_code"] != 0:
                    raise RuntimeError(f"Failed to create branch: {checkout_result['stderr']}")
                results["branch_created"] = branch_name
            except RuntimeError:
                self._stats["total_errors"] += 1
                raise RuntimeError(f"Could not create feature branch: {e}")

        # Step 2: Stage all changes
        try:
            add_result = await self.run_command(project_id, "git add -A")
            if add_result["exit_code"] != 0:
                # It's okay if there's nothing to add
                results["staged"] = False
            else:
                results["staged"] = True
        except Exception:
            results["staged"] = False

        # Step 3: Commit changes
        # Escape quotes in commit message
        safe_title = title.replace('"', '\\"').replace("'", "\\'")
        safe_desc = description.replace('"', '\\"').replace("'", "\\'")[:200]
        commit_message = f"{safe_title}\n\n{safe_desc}"

        try:
            commit_result = await self.run_command(
                project_id, f'git commit -m "{commit_message}"'
            )
            if commit_result["exit_code"] != 0:
                # Maybe nothing to commit
                if "nothing to commit" in commit_result["stdout"].lower():
                    results["committed"] = False
                    results["commit_message"] = "No changes to commit"
                else:
                    self._stats["total_errors"] += 1
                    raise RuntimeError(f"Git commit failed: {commit_result['stderr']}")
            else:
                results["committed"] = True
                results["commit_message"] = commit_message
        except RuntimeError:
            raise

        # Step 4: Push branch
        try:
            push_result = await self.run_command(
                project_id, f"git push -u origin {branch_name}"
            )
            if push_result["exit_code"] != 0:
                results["pushed"] = False
                results["push_error"] = push_result["stderr"][:300]
            else:
                results["pushed"] = True
        except Exception as e:
            results["pushed"] = False
            results["push_error"] = str(e)[:300]

        # Step 5: Create PR using gh CLI
        pr_url = None
        if results.get("pushed", False):
            try:
                # Check if gh CLI is available
                gh_check = await self.run_command(project_id, "which gh 2>/dev/null")
                if gh_check["exit_code"] == 0:
                    safe_title_pr = title.replace('"', '\\"').replace("'", "\\'")
                    safe_desc_pr = description.replace('"', '\\"').replace("'", "\\'")[:500]
                    pr_result = await self.run_command(
                        project_id,
                        f'gh pr create --title "{safe_title_pr}" --body "{safe_desc_pr}" --head {branch_name}',
                    )
                    if pr_result["exit_code"] == 0:
                        pr_url = pr_result["stdout"].strip()
                        results["pr_created"] = True
                        results["pr_url"] = pr_url
                    else:
                        results["pr_created"] = False
                        results["pr_error"] = pr_result["stderr"][:300]
                else:
                    results["pr_created"] = False
                    results["pr_error"] = "GitHub CLI (gh) not installed"
            except Exception as e:
                results["pr_created"] = False
                results["pr_error"] = str(e)[:300]

        self._stats["total_prs"] += 1

        # Update database with the new branch
        conn = get_db_connection(self._db_path)
        try:
            conn.execute(
                "UPDATE epc_projects SET branch = ?, last_activity = ? WHERE id = ?",
                (branch_name, time.time(), project_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            conn.close()

        logger.info(
            "PR workflow for project %s: branch=%s, committed=%s, pushed=%s, pr=%s",
            project_id, branch_name,
            results.get("committed"), results.get("pushed"),
            pr_url or "N/A",
        )

        return {
            "status": "pr_created" if pr_url else "branch_pushed" if results.get("pushed") else "partial",
            "pr_url": pr_url,
            "branch": branch_name,
            "message": (
                f"Pull request created: {pr_url}" if pr_url
                else f"Branch '{branch_name}' pushed. Create PR manually." if results.get("pushed")
                else f"Branch '{branch_name}' created with changes. Push failed."
            ),
            "details": results,
        }

    async def list_projects(self) -> list:
        """
        عرض كل المشاريع الخارجية — List all tracked external projects.

        Returns:
            List of dicts, each containing:
              id, name, url, branch, local_path, status, created_at, last_activity
        """
        conn = get_db_connection(self._db_path)
        try:
            cur = conn.execute(
                """SELECT id, name, url, branch, local_path, status,
                          created_at, last_activity
                   FROM epc_projects
                   ORDER BY last_activity DESC"""
            )
            rows = cur.fetchall()
            projects = []
            for row in rows:
                project = dict(row)
                # Verify the directory still exists
                project["directory_exists"] = Path(project["local_path"]).exists()
                # Get git status if possible
                if project["directory_exists"] and (Path(project["local_path"]) / ".git").exists():
                    try:
                        proc = await asyncio.create_subprocess_exec(
                            "git", "status", "--porcelain",
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                            cwd=project["local_path"],
                        )
                        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
                        changes = stdout.decode('utf-8').strip()
                        project["uncommitted_changes"] = len(changes.split('\n')) if changes else 0
                    except Exception:
                        project["uncommitted_changes"] = -1
                else:
                    project["uncommitted_changes"] = 0
                projects.append(project)

            return projects

        finally:
            conn.close()

    async def get_project_status(self, project_id: str) -> dict:
        """
        حالة مشروع واحد — Get detailed status of a single external project.

        Includes database info, git status, file counts, disk usage,
        and last modified information.

        Args:
            project_id: The project ID returned by clone_repo.

        Returns:
            Dict with comprehensive project status information.

        Raises:
            FileNotFoundError: If the project doesn't exist in the database.
        """
        conn = get_db_connection(self._db_path)
        try:
            cur = conn.execute(
                "SELECT * FROM epc_projects WHERE id = ?",
                (project_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise FileNotFoundError(f"Project not found: {project_id}")
            project = dict(row)
        finally:
            conn.close()

        local_path = Path(project["local_path"])
        status_info = {
            "project_id": project_id,
            "name": project["name"],
            "url": project["url"],
            "branch": project["branch"],
            "local_path": project["local_path"],
            "status": project["status"],
            "created_at": project["created_at"],
            "last_activity": project["last_activity"],
            "directory_exists": local_path.exists(),
            "has_git": (local_path / ".git").exists() if local_path.exists() else False,
            "disk_usage": None,
            "file_count": 0,
            "dir_count": 0,
            "last_modified": None,
            "git_status": None,
            "last_commit": None,
            "project_type": "unknown",
            "recent_commands": [],
        }

        if not local_path.exists():
            status_info["status"] = "directory_missing"
            return status_info

        # Count files and directories
        try:
            file_count = 0
            dir_count = 0
            total_size = 0
            latest_mtime = 0
            latest_file = ""

            for item in local_path.rglob('*'):
                # Skip hidden and build directories
                if any(skip in str(item) for skip in SKIP_DIRS):
                    continue
                if item.is_file():
                    file_count += 1
                    try:
                        size = item.stat().st_size
                        total_size += size
                        mtime = item.stat().st_mtime
                        if mtime > latest_mtime:
                            latest_mtime = mtime
                            latest_file = str(item.relative_to(local_path))
                    except (PermissionError, OSError):
                        pass
                elif item.is_dir():
                    dir_count += 1

            status_info["file_count"] = file_count
            status_info["dir_count"] = dir_count
            status_info["disk_usage"] = {
                "total_bytes": total_size,
                "total_mb": round(total_size / (1024 * 1024), 2),
            }
            if latest_file:
                status_info["last_modified"] = {
                    "file": latest_file,
                    "timestamp": latest_mtime,
                }
        except Exception as e:
            logger.warning("Error counting files for project %s: %s", project_id, e)

        # Detect project type
        if (local_path / "package.json").exists():
            status_info["project_type"] = "node"
        elif (local_path / "pyproject.toml").exists():
            status_info["project_type"] = "python-pyproject"
        elif (local_path / "setup.py").exists():
            status_info["project_type"] = "python-setup"
        elif (local_path / "Cargo.toml").exists():
            status_info["project_type"] = "rust"
        elif (local_path / "go.mod").exists():
            status_info["project_type"] = "go"
        elif (local_path / "Dockerfile").exists():
            status_info["project_type"] = "docker"
        elif (local_path / "Makefile").exists():
            status_info["project_type"] = "make"

        # Git status
        if status_info["has_git"]:
            try:
                # Get changed files
                proc = await asyncio.create_subprocess_exec(
                    "git", "status", "--porcelain",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(local_path),
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
                changes = stdout.decode('utf-8').strip()
                changed_files = [line.strip() for line in changes.split('\n') if line.strip()]
                status_info["git_status"] = {
                    "uncommitted_changes": len(changed_files),
                    "changed_files": changed_files[:20],
                }

                # Get last commit
                proc = await asyncio.create_subprocess_exec(
                    "git", "log", "-1", "--format=%H|%ai|%s",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(local_path),
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
                if proc.returncode == 0 and stdout.decode('utf-8').strip():
                    parts = stdout.decode('utf-8').strip().split('|', 2)
                    status_info["last_commit"] = {
                        "hash": parts[0][:12] if len(parts) > 0 else "",
                        "date": parts[1] if len(parts) > 1 else "",
                        "message": parts[2] if len(parts) > 2 else "",
                    }

                # Get current branch
                proc = await asyncio.create_subprocess_exec(
                    "git", "rev-parse", "--abbrev-ref", "HEAD",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(local_path),
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
                if proc.returncode == 0:
                    status_info["current_branch"] = stdout.decode('utf-8').strip()

            except Exception as e:
                status_info["git_status"] = {"error": str(e)[:100]}

        # Recent command history
        conn2 = get_db_connection(self._db_path)
        try:
            cur2 = conn2.execute(
                """SELECT command, exit_code, timestamp, duration_ms
                   FROM epc_command_history
                   WHERE project_id = ?
                   ORDER BY timestamp DESC
                   LIMIT 10""",
                (project_id,),
            )
            status_info["recent_commands"] = [dict(r) for r in cur2.fetchall()]
        except Exception:
            pass
        finally:
            conn2.close()

        return status_info

    # ─────────────────────────────────────────────────────────────────────────
    # Rollback
    # ─────────────────────────────────────────────────────────────────────────

    async def rollback(self, project_id: str, snapshot_id: str) -> dict:
        """
        التراجع عن التغييرات — Rollback a file to a previous state.

        Restores a file from a snapshot. The snapshot must belong to the
        specified project.

        Args:
            project_id: The project ID.
            snapshot_id: The snapshot ID to rollback to.

        Returns:
            Dict with keys: status, file_path, snapshot_id

        Raises:
            FileNotFoundError: If the snapshot doesn't exist.
            RuntimeError: If rollback fails.
        """
        # Look up the snapshot
        conn = get_db_connection(self._db_path)
        try:
            cur = conn.execute(
                "SELECT * FROM epc_snapshots WHERE snapshot_id = ? AND project_id = ?",
                (snapshot_id, project_id),
            )
            row = cur.fetchone()
            if row is None:
                raise FileNotFoundError(
                    f"Snapshot not found: {snapshot_id} for project {project_id}"
                )
            snapshot = dict(row)
        finally:
            conn.close()

        # Restore the file
        full_path = Path(snapshot["local_path"] if "local_path" in snapshot else "") / snapshot["file_path"]
        # Get project local path
        exists, project, _ = self._validate_project_access(project_id)
        if not exists and project is None:
            raise FileNotFoundError(f"Project not found: {project_id}")

        full_path = Path(project["local_path"]) / snapshot["file_path"]

        try:
            # Create a backup of the current state before rollback
            if full_path.exists():
                backup_dir = Path(project["local_path"]) / ".backups"
                backup_dir.mkdir(exist_ok=True)
                pre_rollback_backup = backup_dir / f"{full_path.stem}_pre_rollback_{int(time.time())}{full_path.suffix}"
                await asyncio.to_thread(shutil.copy2, str(full_path), str(pre_rollback_backup))

            # Write the original content
            original_content = snapshot["original_content"]
            if original_content:
                await asyncio.to_thread(
                    self._write_file_sync, str(full_path), original_content
                )
            elif full_path.exists():
                # The file was newly created — delete it to rollback
                await asyncio.to_thread(os.remove, str(full_path))

            self._stats["total_rollbacks"] += 1
            self._update_project_status(project_id, project.get("status", ProjectStatus.READY))

            logger.info(
                "Rolled back %s in project %s to snapshot %s",
                snapshot["file_path"], project_id, snapshot_id,
            )

            return {
                "status": "rolled_back",
                "file_path": snapshot["file_path"],
                "snapshot_id": snapshot_id,
                "content_size": len(original_content) if original_content else 0,
            }

        except Exception as e:
            self._stats["total_errors"] += 1
            raise RuntimeError(f"Rollback failed: {e}")

    async def rollback_last(self, project_id: str) -> dict:
        """
        التراجع عن آخر تغيير — Rollback the most recent change for a project.

        Args:
            project_id: The project ID.

        Returns:
            Dict with keys: status, file_path, snapshot_id

        Raises:
            FileNotFoundError: If no snapshots exist for this project.
        """
        conn = get_db_connection(self._db_path)
        try:
            cur = conn.execute(
                """SELECT snapshot_id FROM epc_snapshots
                   WHERE project_id = ?
                   ORDER BY timestamp DESC
                   LIMIT 1""",
                (project_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise FileNotFoundError(
                    f"No snapshots found for project {project_id}"
                )
            snapshot_id = row["snapshot_id"]
        finally:
            conn.close()

        return await self.rollback(project_id, snapshot_id)

    # ─────────────────────────────────────────────────────────────────────────
    # LLM-Assisted Operations
    # ─────────────────────────────────────────────────────────────────────────

    async def llm_edit_file(self, project_id: str, file_path: str,
                            instruction: str) -> dict:
        """
        تعديل ملف بالذكاء الاصطناعي — Edit a file using LLM assistance.

        Reads the current file content, sends it to the LLM with the
        modification instruction, and writes the result back.

        Args:
            project_id: The project ID.
            file_path: Relative path to the file.
            instruction: Natural language instruction for the modification.

        Returns:
            Dict with keys: status, file_path, changes_description, snapshot_id
        """
        # Validate file path
        is_safe, reason = self._validate_file_path(file_path)
        if not is_safe:
            raise ValueError(f"File path not allowed: {reason}")

        # Read current content
        current_content = await self.read_file(project_id, file_path)

        # Determine language for context
        ext = Path(file_path).suffix.lower()
        lang_map = {
            '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
            '.tsx': 'TypeScript/React', '.jsx': 'JavaScript/React',
            '.go': 'Go', '.rs': 'Rust', '.java': 'Java',
            '.rb': 'Ruby', '.php': 'PHP', '.cs': 'C#',
            '.cpp': 'C++', '.c': 'C', '.swift': 'Swift',
            '.kt': 'Kotlin', '.scala': 'Scala',
            '.html': 'HTML', '.css': 'CSS', '.scss': 'SCSS',
            '.sql': 'SQL', '.sh': 'Shell', '.yaml': 'YAML',
            '.yml': 'YAML', '.json': 'JSON', '.xml': 'XML',
            '.md': 'Markdown',
        }
        language = lang_map.get(ext, "Code")

        # Build LLM prompt
        llm = get_llm_client()
        messages = [
            LLMMessage(
                role="system",
                content=(
                    f"You are an expert {language} developer. "
                    f"You will modify the provided file according to the instruction. "
                    f"Output ONLY the complete modified file content. "
                    f"Do NOT include markdown code blocks or explanations. "
                    f"Output the raw code only."
                ),
            ),
            LLMMessage(
                role="user",
                content=(
                    f"File: {file_path}\n"
                    f"Instruction: {instruction}\n\n"
                    f"Current content:\n"
                    f"```{ext.lstrip('.')}\n{current_content[:12000]}\n```\n\n"
                    f"Write the COMPLETE modified file. Output ONLY the code."
                ),
            ),
        ]

        response = await llm.chat(
            messages=messages,
            model="glm-5.1",
            temperature=0.3,
        )

        new_content = response.text

        if not new_content or len(new_content) < 10:
            raise RuntimeError("LLM generated empty or too-short response")

        # Strip markdown code block wrapper if present
        if new_content.strip().startswith('```'):
            lines = new_content.strip().split('\n')
            # Remove first line (```lang) and last line (```)
            if len(lines) > 2:
                new_content = '\n'.join(lines[1:-1])

        # Write the modified content
        write_result = await self.write_file(project_id, file_path, new_content)

        return {
            "status": "llm_edited",
            "file_path": file_path,
            "changes_description": instruction,
            "snapshot_id": write_result.get("snapshot_id"),
            "original_size": len(current_content),
            "new_size": len(new_content),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Project Cleanup
    # ─────────────────────────────────────────────────────────────────────────

    async def remove_project(self, project_id: str, keep_db_record: bool = False) -> dict:
        """
        حذف مشروع خارجي — Remove an external project from disk and database.

        Args:
            project_id: The project ID to remove.
            keep_db_record: If True, keep the database record but mark as "archived".

        Returns:
            Dict with keys: status, project_id, local_path

        Raises:
            FileNotFoundError: If the project doesn't exist.
        """
        exists, project, reason = self._validate_project_access(project_id)
        if not exists and project is None:
            raise FileNotFoundError(f"Project not found: {reason}")

        local_path = Path(project["local_path"])

        # Remove directory
        if local_path.exists():
            try:
                await asyncio.to_thread(shutil.rmtree, str(local_path), ignore_errors=True)
            except Exception as e:
                logger.warning("Failed to remove project directory: %s", e)

        # Update or remove database record
        conn = get_db_connection(self._db_path)
        try:
            if keep_db_record:
                conn.execute(
                    "UPDATE epc_projects SET status = ?, last_activity = ? WHERE id = ?",
                    (ProjectStatus.ARCHIVED, time.time(), project_id),
                )
            else:
                conn.execute("DELETE FROM epc_projects WHERE id = ?", (project_id,))
                conn.execute("DELETE FROM epc_snapshots WHERE project_id = ?", (project_id,))
                conn.execute("DELETE FROM epc_command_history WHERE project_id = ?", (project_id,))
            conn.commit()
        except Exception as e:
            logger.error("Failed to update database during removal: %s", e)
            conn.rollback()
        finally:
            conn.close()

        # Clean up in-memory snapshots
        if project_id in self._snapshots:
            del self._snapshots[project_id]

        logger.info("Removed project %s: %s", project_id, local_path)

        return {
            "status": "removed",
            "project_id": project_id,
            "local_path": str(local_path),
            "archived": keep_db_record,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Controller Status
    # ─────────────────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        """
        حالة المتحكم — Get the controller's overall status.

        Returns:
            Dict with keys:
              total_projects, projects_by_status, stats,
              external_dir, max_concurrent_ops
        """
        conn = get_db_connection(self._db_path)
        try:
            # Count projects by status
            cur = conn.execute(
                "SELECT status, COUNT(*) as count FROM epc_projects GROUP BY status"
            )
            projects_by_status = {row["status"]: row["count"] for row in cur.fetchall()}

            # Total projects
            cur = conn.execute("SELECT COUNT(*) as total FROM epc_projects")
            total_projects = cur.fetchone()["total"]

        finally:
            conn.close()

        return {
            "total_projects": total_projects,
            "projects_by_status": projects_by_status,
            "stats": dict(self._stats),
            "external_dir": str(EXTERNAL_PROJECTS_DIR),
            "max_concurrent_ops": MAX_CONCURRENT_OPS,
            "active_operations": len(self._active_operations),
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_epc_instance: Optional[ExternalProjectController] = None


def get_external_project_controller() -> ExternalProjectController:
    """
    الحصول على متحكم المشاريع الخارجية — Get the global EPC singleton.

    Returns:
        The ExternalProjectController singleton instance.
    """
    global _epc_instance
    if _epc_instance is None:
        _epc_instance = ExternalProjectController()
    return _epc_instance
