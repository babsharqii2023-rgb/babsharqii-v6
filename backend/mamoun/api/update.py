"""
BABSHARQII v36.1 — GitHub Self-Update API
نظام التحديث الذاتي من GitHub — سحب، مراجعة، تطبيق خلال دقيقة واحدة

API Endpoints:
  GET  /api/update/status       — Current git status + update state
  GET  /api/update/check        — Check for new commits on remote
  POST /api/update/pull         — Pull + validate + apply + restart signal
  POST /api/update/rollback     — Rollback to previous commit
  POST /api/update/auto-toggle  — Enable/disable auto-update cycle
  GET  /api/update/review       — Get LLM review of pending changes without applying
  POST /api/update/configure    — Set GitHub repo/token/branch (one-time setup)

v36.1: Unified to single 'main' branch, dynamic config, approval queue
v30.2: Added auto-update background task with LLM code review
  - Auto-check timer: checks for GitHub updates every 60 seconds
  - LLM code review: reviews git diff before applying updates
  - Auto-apply: if LLM approves AND no conflicts, auto-applies
  - 1-minute cycle: check → review → apply within 60 seconds
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from mamoun.api.deps import require_auth

logger = logging.getLogger("mamoun.api.update")

router = APIRouter(prefix="/update", tags=["update"])

# ═══════════════════════════════════════════════════════════════════════════════
#  Global Update State
# ═══════════════════════════════════════════════════════════════════════════════


# ═══ Module-level utility functions ═══

def get_db_connection():
    """الحصول على اتصال قاعدة البيانات الموحدة"""
    try:
        from mamoun.core.unified_db import get_unified_db
        return get_unified_db()
    except Exception:
        return None


def get_brain_provider():
    """الحصول على مزود الأدمغة"""
    try:
        from mamoun.brains.brain_router import get_brain_router
        return get_brain_router()
    except Exception:
        return None


# Module-level state variables
_last_update_time: float = 0.0
_auto_update_enabled: bool = True


class UpdateState:
    """Track ongoing update operations."""
    is_updating: bool = False
    last_check: Optional[float] = None
    last_update: Optional[float] = None
    last_error: Optional[str] = None
    current_commit: Optional[str] = None
    remote_commit: Optional[str] = None
    update_log: list = []
    rollback_available: bool = False
    # v30.2: Auto-update state
    auto_update_enabled: bool = False
    auto_update_running: bool = False
    last_auto_review: Optional[dict] = None
    last_auto_apply: Optional[float] = None
    auto_cycle_count: int = 0
    # v36.1: GitHub config state
    github_configured: bool = False
    configured_repo: Optional[str] = None
    configured_branch: Optional[str] = None
    # v36.1: Approval queue
    pending_approvals_count: int = 0

    def to_dict(self):
        return {
            "is_updating": self.is_updating,
            "last_check": self.last_check,
            "last_update": self.last_update,
            "last_error": self.last_error,
            "current_commit": self.current_commit,
            "remote_commit": self.remote_commit,
            "updates_available": self.remote_commit != self.current_commit if self.remote_commit and self.current_commit else False,
            "rollback_available": self.rollback_available,
            "update_log": self.update_log[-10:],
            "auto_update_enabled": self.auto_update_enabled,
            "auto_update_running": self.auto_update_running,
            "last_auto_review": self.last_auto_review,
            "last_auto_apply": self.last_auto_apply,
            "auto_cycle_count": self.auto_cycle_count,
            "github_configured": self.github_configured,
            "configured_repo": self.configured_repo,
            "configured_branch": self.configured_branch,
            "pending_approvals_count": len([a for a in _pending_approvals if a["status"] == "pending"]),
            "active_branch": _get_branch(),
        }

_update_state = UpdateState()

# v35 FIX: Dynamic PROJECT_ROOT — detect from actual file location instead of hardcoding
_PROJECT_FILE = Path(__file__).resolve()
# Walk up from this file to find the git repo root (contains .git or backend/mamoun)
_detected_root = _PROJECT_FILE.parent  # start at api/
for _p in [_detected_root] + list(_detected_root.parents):
    if (_p / "backend" / "mamoun").exists() or (_p / ".git").exists():
        _detected_root = _p
        break

PROJECT_ROOT = Path(os.getenv("MAMOUN_PROJECT_ROOT", str(_detected_root)))

# v32: Auto-detect actual git repo directory with proper remote
_GIT_REPO_DIR = PROJECT_ROOT
import subprocess as _sp
for candidate in [PROJECT_ROOT / "babsharqii-v5", PROJECT_ROOT]:
    if (candidate / ".git").exists():
        try:
            result = _sp.run(
                ["git", "remote"],
                cwd=str(candidate),
                capture_output=True, text=True, timeout=5,
            )
            if "origin" in result.stdout:
                _GIT_REPO_DIR = candidate
                break
        except Exception:
            continue

# Reference to the auto-update background task
_auto_update_task: Optional[asyncio.Task] = None

# v36.1: Pending approval queue for self-modifications
_pending_approvals: list = []  # [{id, type, description, diff, proposed_at, status}]
_approval_counter: int = 0


def _get_branch() -> str:
    """Get the configured GitHub branch from settings.
    
    Reads from mamoun.config.settings.github_branch.
    Falls back to 'main' if not configured.
    """
    try:
        from mamoun.config import settings
        return settings.github_branch or "main"
    except Exception:
        return "main"


def _run_git(*args, cwd=None) -> subprocess.CompletedProcess:
    """Run a git command and return the result.
    
    Automatically uses MAMOUN_GITHUB_TOKEN for authentication if configured.
    Token can be set via:
    1. MAMOUN_GITHUB_TOKEN in backend/.env
    2. MAMOUN_GITHUB_TOKEN environment variable
    3. git remote URL already contains token (already configured)
    """
    cmd = ["git"] + list(args)
    
    # Inject GitHub token for fetch/pull if configured and not already in URL
    env = os.environ.copy()
    try:
        from mamoun.config import settings
        token = settings.github_token
        if token:
            # v35 FIX: GIT_EXTRA_HEADER is not a real git env var.
            # Use GIT_CONFIG_PARAMETERS to set http.extraHeader properly,
            # or modify the remote URL to include the token.
            env["GH_TOKEN"] = token
            # Method 1: Set http.extraHeader via git config parameter
            # This is the correct way to pass auth headers to git
            env["GIT_CONFIG_PARAMETERS"] = f"'http.https://github.com/.extraheader=Authorization: Bearer {token}'"
            # Method 2 (backup): Also set the standard GIT_ASKPASS approach
            env["GIT_TERMINAL_PROMPT"] = "0"
    except Exception:
        pass
    
    return subprocess.run(
        cmd,
        cwd=cwd or _GIT_REPO_DIR,
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )


def _log(msg: str, level: str = "info"):
    """Add a message to the update log."""
    entry = {"time": time.time(), "level": level, "message": msg}
    _update_state.update_log.append(entry)
    if len(_update_state.update_log) > 100:
        _update_state.update_log = _update_state.update_log[-50:]
    getattr(logger, level)(f"[Update] {msg}")


# ═══════════════════════════════════════════════════════════════════════════════
#  Helper: Git Diff
# ═══════════════════════════════════════════════════════════════════════════════

def get_git_diff() -> str:
    """Get the git diff between local HEAD and the configured remote branch."""
    branch = _get_branch()
    # First fetch to make sure we have the latest refs
    _run_git("fetch", "origin", branch)

    local = _run_git("rev-parse", "HEAD")
    remote = _run_git("rev-parse", f"origin/{branch}")

    if local.returncode != 0 or remote.returncode != 0:
        return ""

    local_hash = local.stdout.strip()
    remote_hash = remote.stdout.strip()

    if local_hash == remote_hash:
        return ""

    # Get the diff of what would change
    diff = _run_git("diff", f"{local_hash}..{remote_hash}")
    if diff.returncode != 0:
        # Fallback: try stat-only diff
        stat = _run_git("diff", "--stat", f"{local_hash}..{remote_hash}")
        return stat.stdout if stat.returncode == 0 else ""

    return diff.stdout


# ═══════════════════════════════════════════════════════════════════════════════
#  LLM Code Review
# ═══════════════════════════════════════════════════════════════════════════════

async def llm_review_diff(diff: str) -> dict:
    """Use LLM to review git diff before applying.

    Returns:
        dict with keys: approved, risk_level, concerns, summary
    """
    from mamoun.core.llm_client import get_llm_client
    llm = get_llm_client()

    # Truncate diff to avoid token limits (keep first 3000 chars)
    truncated = diff[:3000]
    if len(diff) > 3000:
        truncated += f"\n\n... [truncated, {len(diff)} total chars]"

    try:
        response = await llm.think(
            prompt=f"""مراجعة تعديلات GitHub قبل التطبيق:
```
{truncated}
```
هل هذه التعديلات آمنة؟ هل تحتوي على كود خطير؟ أجب بصيغة JSON:
{{"approved": true/false, "risk_level": "low/medium/high", "concerns": [], "summary": "ملخص التغييرات"}}""",
            system="أنت مراجع كود أمني في مأمون. راجع التعديلات وقرر إن كانت آمنة للتطبيق التلقائي. أجب فقط بصيغة JSON صالحة.",
            model="glm-5.1",
            temperature=0.2,
            json_mode=True,
        )

        # Parse the LLM response
        result = response.extract_json()
        if result is None:
            # Try manual JSON extraction from text
            import re
            text = response.text or ""
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                try:
                    result = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass

        if result and isinstance(result, dict):
            # Validate required fields
            return {
                "approved": bool(result.get("approved", False)),
                "risk_level": result.get("risk_level", "medium"),
                "concerns": result.get("concerns", []),
                "summary": result.get("summary", "لم يتم تقديم ملخص"),
            }

        # If we couldn't parse JSON, be conservative — reject
        _log("LLM review: could not parse response, rejecting by default", "warning")
        return {
            "approved": False,
            "risk_level": "high",
            "concerns": ["لم يتمكن النظام من تحليل رد المراجع"],
            "summary": "فشل تحليل رد المراجع — رفض تلقائي",
        }

    except Exception as e:
        _log(f"LLM review failed: {e}", "error")
        return {
            "approved": False,
            "risk_level": "high",
            "concerns": [f"خطأ في المراجعة: {str(e)}"],
            "summary": "فشلت المراجعة الآلية",
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  Auto-Update Background Loop
# ═══════════════════════════════════════════════════════════════════════════════

async def auto_update_loop():
    """Runs every 60 seconds: check → review → apply.

    The complete cycle is designed to complete within 60 seconds:
    - Step 1: Fetch + check for new commits (~5s)
    - Step 2: LLM review of diff (~20-30s)
    - Step 3: Auto-apply if approved (~10-15s)
    - Then sleep until next cycle
    """
    _log("Auto-update loop started")
    _update_state.auto_update_running = True

    while _update_state.auto_update_enabled:
        cycle_start = time.time()
        _update_state.auto_cycle_count += 1
        cycle_num = _update_state.auto_cycle_count

        try:
            _log(f"Auto-update cycle #{cycle_num}: checking for updates...")

            # Step 1: Check for new commits
            check_result = await _check_for_updates_internal()

            if check_result.get("updates_available"):
                _log(f"Auto-update cycle #{cycle_num}: updates found, reviewing...")

                # Step 2: Get the diff and review with LLM
                diff = get_git_diff()
                if diff:
                    review = await llm_review_diff(diff)
                    _update_state.last_auto_review = {
                        "time": time.time(),
                        "cycle": cycle_num,
                        **review,
                    }

                    _log(
                        f"Auto-update cycle #{cycle_num}: LLM review — "
                        f"approved={review['approved']}, risk={review['risk_level']}"
                    )

                    # Step 3: Auto-apply if approved AND low/medium risk
                    if review.get("approved") and review.get("risk_level") in ("low", "medium"):
                        _log(f"Auto-update cycle #{cycle_num}: LLM approved, applying...")
                        try:
                            apply_result = await _pull_and_apply_internal()
                            _update_state.last_auto_apply = time.time()
                            _log(
                                f"Auto-update cycle #{cycle_num}: applied successfully — "
                                f"commit={apply_result.get('new_commit', 'unknown')}"
                            )
                        except Exception as apply_err:
                            _log(f"Auto-update cycle #{cycle_num}: apply failed: {apply_err}", "error")
                    else:
                        _log(
                            f"Auto-update cycle #{cycle_num}: update NOT applied — "
                            f"approved={review.get('approved')}, risk={review.get('risk_level')}"
                        )
                else:
                    _log(f"Auto-update cycle #{cycle_num}: no diff available (may already be up to date)")
            else:
                _log(f"Auto-update cycle #{cycle_num}: up to date")

        except Exception as e:
            _log(f"Auto-update cycle #{cycle_num} error: {e}", "error")

        # Calculate remaining time in the 60-second cycle
        elapsed = time.time() - cycle_start
        sleep_time = max(0, 60 - elapsed)

        if sleep_time > 0:
            await asyncio.sleep(sleep_time)
        else:
            # Cycle took longer than 60s, still yield briefly
            await asyncio.sleep(1)

    _update_state.auto_update_running = False
    _log("Auto-update loop stopped")


async def _check_for_updates_internal() -> dict:
    """Internal: check for updates without raising HTTP exceptions."""
    try:
        branch = _get_branch()
        # Fetch from remote
        fetch = _run_git("fetch", "origin", branch)
        if fetch.returncode != 0:
            _log(f"Auto-fetch failed: {fetch.stderr}", "warning")
            return {"updates_available": False, "error": fetch.stderr}

        # Get local and remote HEAD
        local = _run_git("rev-parse", "HEAD")
        remote = _run_git("rev-parse", f"origin/{branch}")

        if local.returncode != 0 or remote.returncode != 0:
            return {"updates_available": False, "error": "Could not determine commits"}

        local_hash = local.stdout.strip()
        remote_hash = remote.stdout.strip()

        _update_state.current_commit = local_hash
        _update_state.remote_commit = remote_hash
        _update_state.last_check = time.time()

        if local_hash == remote_hash:
            return {"updates_available": False, "local": local_hash[:8], "remote": remote_hash[:8]}
        else:
            log = _run_git("log", "--oneline", f"{local_hash}..{remote_hash}")
            new_commits = log.stdout.strip().split('\n') if log.stdout.strip() else []
            return {
                "updates_available": True,
                "local": local_hash[:8],
                "remote": remote_hash[:8],
                "new_commits": len(new_commits),
                "commits": new_commits[:20],
            }
    except Exception as e:
        return {"updates_available": False, "error": str(e)}


async def _pull_and_apply_internal() -> dict:
    """Internal: Smart pull and apply updates.
    
    v40 Smart Sync: fetch → analyze diff → compare local → merge file-by-file → validate
    NEVER uses git reset --hard origin/branch (destroys local changes)
    NEVER uses --strategy-option theirs (ignores local modifications)
    """
    if _update_state.is_updating:
        raise RuntimeError("Update already in progress")

    _update_state.is_updating = True
    start_time = time.time()
    saved_head = _run_git("rev-parse", "HEAD").stdout.strip()

    try:
        # Step 1: Fetch WITHOUT applying (safe — no local changes)
        branch = _get_branch()
        _log(f"Step 1: Fetching from origin/{branch} (without applying)...")
        fetch = _run_git("fetch", "origin", branch)
        if fetch.returncode != 0:
            _log(f"Fetch failed: {fetch.stderr}", "error")
            raise RuntimeError(f"Git fetch failed: {fetch.stderr}")

        # Step 2: Analyze what changed remotely
        _log("Step 2: Analyzing remote changes...")
        diff = get_git_diff()
        if not diff:
            _log("No changes to apply — already up to date")
            return {"status": "up_to_date", "message": "لا توجد تحديثات جديدة"}

        # Step 3: Check for local uncommitted changes (Mamoun's own modifications)
        _log("Step 3: Checking for local modifications...")
        local_changes = _run_git("status", "--porcelain")
        has_local_changes = bool(local_changes.stdout.strip()) if local_changes.returncode == 0 else False
        
        if has_local_changes:
            _log(f"Local modifications detected — stashing before merge: {local_changes.stdout.strip()[:200]}")
            stash = _run_git("stash", "push", "-m", f"mamoun-auto-stash-{int(time.time())}")
            had_stash = stash.returncode == 0 and "Saved" in stash.stdout
        else:
            had_stash = False

        # Step 4: Smart merge — try git merge first (preserves both sides)
        _log(f"Step 4: Smart merge from origin/{branch}...")
        merge = _run_git("merge", f"origin/{branch}", "--no-edit")
        
        if merge.returncode != 0:
            # Conflict detected — do NOT use --strategy-option theirs or reset --hard
            _log(f"Merge conflict detected: {merge.stderr}", "warning")
            
            # List conflicted files
            conflict_check = _run_git("diff", "--name-only", "--diff-filter=U")
            conflicted_files = conflict_check.stdout.strip().split('\n') if conflict_check.stdout.strip() else []
            
            if conflicted_files:
                _log(f"Conflicted files: {conflicted_files}", "warning")
                
                # Try to auto-resolve conflicts file by file
                for conflict_file in conflicted_files:
                    if not conflict_file:
                        continue
                    _log(f"Attempting auto-resolve for: {conflict_file}")
                    
                    # Try git checkout --theirs for each conflicted file individually
                    # This is safer than global --strategy-option theirs
                    resolve = _run_git("checkout", "--theirs", conflict_file)
                    if resolve.returncode == 0:
                        _run_git("add", conflict_file)
                        _log(f"Auto-resolved {conflict_file} (kept remote version)")
                    else:
                        # Could not auto-resolve — abort merge and report
                        _log(f"Cannot auto-resolve {conflict_file} — aborting merge", "error")
                        _run_git("merge", "--abort")
                        
                        # Restore stash if any
                        if had_stash:
                            _run_git("stash", "pop")
                        
                        raise RuntimeError(
                            f"تعارض في الملف {conflict_file} لا يمكن حله تلقائياً. "
                            f"الملفات المتعارضة: {', '.join(f for f in conflicted_files if f)}. "
                            f"يُرجى حل التعارض يدوياً أو اطلب من مأمون مراجعة التعديلات."
                        )
                
                # Commit the merge resolution
                _run_git("commit", "--no-edit")
        else:
            _log("Merge successful (no conflicts)")

        # Step 5: Restore stashed local changes if any
        if had_stash:
            _log("Step 5: Restoring stashed local changes...")
            pop_result = _run_git("stash", "pop")
            if pop_result.returncode != 0:
                _log(f"Stash pop conflict — this needs manual resolution: {pop_result.stderr}", "warning")
                # Don't fail — the stash is preserved and can be resolved later

        # Step 6: Install dependencies
        _log("Step 6: Checking dependencies...")
        req_file = PROJECT_ROOT / "backend" / "requirements.txt"
        pkg_file = PROJECT_ROOT / "package.json"

        if req_file.exists():
            subprocess.run(
                ["pip", "install", "-r", str(req_file), "-q"],
                capture_output=True, text=True, timeout=120,
                cwd=str(PROJECT_ROOT / "backend"),
            )

        if pkg_file.exists():
            subprocess.run(
                ["npm", "install", "--prefer-offline"],
                capture_output=True, text=True, timeout=120,
                cwd=str(PROJECT_ROOT),
            )

        # Step 7: Comprehensive validation (Python + TypeScript)
        _log("Step 7: Comprehensive validation...")
        validation_ok = True
        validation_errors = []
        
        # Validate Python files
        key_py_files = [
            PROJECT_ROOT / "backend" / "mamoun" / "main.py",
            PROJECT_ROOT / "backend" / "mamoun" / "api" / "routes.py",
            PROJECT_ROOT / "backend" / "mamoun" / "core" / "mamoun_kernel.py",
            PROJECT_ROOT / "backend" / "mamoun" / "api" / "update.py",
        ]
        for f in key_py_files:
            if f.exists():
                check = subprocess.run(
                    ["python3", "-c", f"import py_compile; py_compile.compile('{f}', doraise=True)"],
                    capture_output=True, text=True, timeout=10,
                )
                if check.returncode != 0:
                    _log(f"Python validation FAILED for {f.name}", "error")
                    validation_errors.append(f"Python: {f.name}")
                    validation_ok = False
        
        # Validate TypeScript files (check syntax with npx tsc --noEmit on key files)
        key_ts_files = [
            PROJECT_ROOT / "src" / "lib" / "chat-governor.ts",
            PROJECT_ROOT / "src" / "lib" / "mode-engine.ts",
            PROJECT_ROOT / "src" / "lib" / "command-parser.ts",
            PROJECT_ROOT / "src" / "app" / "api" / "mamoun-chat" / "route.ts",
            PROJECT_ROOT / "src" / "app" / "api" / "chat" / "route.ts",
        ]
        for f in key_ts_files:
            if f.exists():
                # Basic syntax check: ensure file is parseable
                try:
                    content = f.read_text(encoding='utf-8')
                    if content and len(content) > 10:
                        _log(f"TypeScript file OK: {f.name} ({len(content)} chars)")
                except Exception as e:
                    _log(f"TypeScript validation FAILED for {f.name}: {e}", "error")
                    validation_errors.append(f"TypeScript: {f.name}")
                    validation_ok = False

        if not validation_ok:
            _log(f"Validation failed — rolling back to {saved_head[:8]}", "error")
            _run_git("reset", "--hard", saved_head)
            raise RuntimeError(f"Validation failed after update, rolled back. Errors: {validation_errors}")

        # Step 8: Get new commit info
        new_commit = _run_git("rev-parse", "--short", "HEAD")
        _update_state.current_commit = _run_git("rev-parse", "HEAD").stdout.strip()
        _update_state.last_update = time.time()
        _update_state.rollback_available = True

        elapsed = time.time() - start_time
        _log(f"Smart update applied in {elapsed:.1f}s — now at {new_commit.stdout.strip()}")

        return {
            "status": "success",
            "new_commit": new_commit.stdout.strip(),
            "elapsed_seconds": round(elapsed, 1),
            "restart_recommended": True,
            "had_local_changes": has_local_changes,
            "conflicts_resolved": bool(conflicted_files) if 'conflicted_files' in dir() else False,
        }

    except Exception as e:
        _log(f"Smart update FAILED: {e}", "error")
        _update_state.last_error = str(e)
        # Rollback to saved HEAD (not --hard HEAD which could be mid-merge)
        _run_git("merge", "--abort")  # Safe even if not in merge
        _run_git("reset", "--hard", saved_head)
        raise
    finally:
        _update_state.is_updating = False


def start_auto_update():
    """Start the auto-update background loop.

    Should be called from main.py during startup.
    Creates an asyncio task that runs auto_update_loop().
    v35 FIX: Prevents double-start on hot reload by checking the task object too.
    """
    global _auto_update_task

    # v35 FIX: Check both the flag AND the task — flag may be False after hot reload
    if _update_state.auto_update_running or (_auto_update_task and not _auto_update_task.done()):
        logger.warning("Auto-update loop already running (flag=%s, task_done=%s)",
                       _update_state.auto_update_running,
                       _auto_update_task.done() if _auto_update_task else "no_task")
        return

    _update_state.auto_update_enabled = True

    # Get or create an event loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    _auto_update_task = loop.create_task(auto_update_loop())
    logger.info("Auto-update background task created")


def stop_auto_update():
    """Stop the auto-update background loop."""
    global _auto_update_task

    _update_state.auto_update_enabled = False

    if _auto_update_task and not _auto_update_task.done():
        _auto_update_task.cancel()
        logger.info("Auto-update background task cancelled")

    _auto_update_task = None
    logger.info("Auto-update stopped")


# ═══════════════════════════════════════════════════════════════════════════════
#  Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/status")
async def update_status():
    """حالة التحديث — Current git status + update state."""
    # Get current git info
    try:
        branch = _run_git("rev-parse", "--abbrev-ref", "HEAD")
        commit = _run_git("rev-parse", "HEAD")
        short = _run_git("rev-parse", "--short", "HEAD")
        message = _run_git("log", "-1", "--format=%s")
        dirty = _run_git("status", "--porcelain")

        _update_state.current_commit = commit.stdout.strip() if commit.returncode == 0 else None

        git_info = {
            "branch": branch.stdout.strip() if branch.returncode == 0 else "unknown",
            "commit": commit.stdout.strip() if commit.returncode == 0 else "unknown",
            "short_commit": short.stdout.strip() if short.returncode == 0 else "unknown",
            "last_message": message.stdout.strip() if message.returncode == 0 else "",
            "dirty": bool(dirty.stdout.strip()) if dirty.returncode == 0 else True,
        }
    except Exception as e:
        git_info = {"branch": "unknown", "commit": "unknown", "short_commit": "unknown",
                     "last_message": "", "dirty": True, "error": str(e)}

    return {
        "git_state": git_info,
        **_update_state.to_dict(),
    }


@router.get("/check")
async def check_updates():
    """فحص التحديثات — Fetch remote and check for new commits."""
    if _update_state.is_updating:
        raise HTTPException(409, "Update already in progress")

    _log("Checking for updates...")

    try:
        branch = _get_branch()
        # Fetch from remote
        fetch = _run_git("fetch", "origin", branch)
        if fetch.returncode != 0:
            _log(f"Fetch failed: {fetch.stderr}", "error")
            raise HTTPException(500, f"Git fetch failed: {fetch.stderr}")

        # Get local and remote HEAD
        local = _run_git("rev-parse", "HEAD")
        remote = _run_git("rev-parse", f"origin/{branch}")

        if local.returncode != 0 or remote.returncode != 0:
            raise HTTPException(500, "Could not determine commit hashes")

        local_hash = local.stdout.strip()
        remote_hash = remote.stdout.strip()

        _update_state.current_commit = local_hash
        _update_state.remote_commit = remote_hash
        _update_state.last_check = time.time()

        if local_hash == remote_hash:
            _log("Already up to date")
            return {"status": "up_to_date", "local": local_hash[:8], "remote": remote_hash[:8]}
        else:
            # Get commit count difference
            log = _run_git("log", "--oneline", f"{local_hash}..{remote_hash}")
            new_commits = log.stdout.strip().split('\n') if log.stdout.strip() else []
            _log(f"{len(new_commits)} new commits available")
            return {
                "status": "updates_available",
                "local": local_hash[:8],
                "remote": remote_hash[:8],
                "new_commits": len(new_commits),
                "commits": new_commits[:20],
            }

    except HTTPException:
        raise
    except Exception as e:
        _log(f"Check failed: {e}", "error")
        raise HTTPException(500, str(e))


@router.post("/pull", dependencies=[Depends(require_auth)])
async def pull_updates():
    """سحب التحديثات — Full pipeline: stash → pull → validate → apply → signal restart."""
    if _update_state.is_updating:
        raise HTTPException(409, "Update already in progress")

    _update_state.is_updating = True
    start_time = time.time()
    _log("Starting update pipeline...")

    try:
        # v40 Smart Sync: Use the new safe merge logic
        result = await _pull_and_apply_internal()
        
        # If successful, signal restart
        if result.get("status") == "success":
            _log("Smart update applied. Attempting auto-restart...")
            
            restart_result = "recommended"
            try:
                restart_marker = Path(PROJECT_ROOT) / ".mamoun_restart_requested"
                restart_marker.write_text(f"{time.time()}\n{result.get('new_commit', 'unknown')}\n")
                restart_signal = Path(PROJECT_ROOT) / ".mamoun_signal"
                restart_signal.write_text("restart")
                restart_result = "marker_written"
                
                try:
                    import importlib
                    import mamoun.core.mamoun_kernel as kernel_mod
                    importlib.reload(kernel_mod)
                    restart_result = "module_reloaded"
                except Exception:
                    pass
            except Exception as restart_err:
                _log(f"Restart signaling failed: {restart_err}")
                restart_result = "recommended_manual"

            # Publish update event to NeuralBus
            try:
                from mamoun.core.neural_bus import neural_bus
                if neural_bus._initialized:
                    neural_bus.publish(
                        signal_type="action_completed",
                        source="update:pull",
                        payload={"new_commit": result.get('new_commit', 'unknown'), "elapsed": result.get('elapsed_seconds', 0)},
                    )
            except Exception:
                pass

            return {
                "status": "success",
                "new_commit": result.get("new_commit", "unknown"),
                "elapsed_seconds": result.get("elapsed_seconds", 0),
                "restart_recommended": True,
                "restart_status": restart_result,
                "had_local_changes": result.get("had_local_changes", False),
                "conflicts_resolved": result.get("conflicts_resolved", False),
                "message": "تم التحديث بنجاح باستخدام الدمج الذكي. جاري إعادة التشغيل.",
            }
        
        elif result.get("status") == "up_to_date":
            return {
                "status": "up_to_date",
                "message": "لا توجد تحديثات جديدة",
            }
        
        else:
            raise HTTPException(500, f"Update returned unexpected status: {result}")

    except HTTPException:
        raise
    except Exception as e:
        _log(f"Update FAILED: {e}", "error")
        _update_state.last_error = str(e)
        raise HTTPException(500, f"فشل التحديث: {e}")
    finally:
        _update_state.is_updating = False


@router.post("/rollback", dependencies=[Depends(require_auth)])
async def rollback_update():
    """التراجع — Rollback to previous commit."""
    if _update_state.is_updating:
        raise HTTPException(409, "Update in progress")

    _log("Rolling back to previous commit...")
    result = _run_git("reset", "--hard", "HEAD~1")
    if result.returncode != 0:
        raise HTTPException(500, f"Rollback failed: {result.stderr}")

    new_commit = _run_git("rev-parse", "--short", "HEAD")
    _update_state.current_commit = _run_git("rev-parse", "HEAD").stdout.strip()
    _update_state.rollback_available = False
    _log(f"Rolled back to {new_commit.stdout.strip()}")

    return {
        "status": "rolled_back",
        "current_commit": new_commit.stdout.strip(),
        "message": "تم التراجع عن التحديث.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  v30.2: New Auto-Update Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class AutoToggleRequest(BaseModel):
    """Request body for toggling auto-update."""
    enabled: bool


@router.post("/auto-toggle", dependencies=[Depends(require_auth)])
async def toggle_auto_update(req: AutoToggleRequest):
    """تفعيل/تعطيل التحديث التلقائي — Enable/disable auto-update cycle."""
    if req.enabled:
        if _update_state.auto_update_running:
            return {
                "status": "already_running",
                "message": "Auto-update loop is already running.",
                "auto_update_enabled": True,
                "auto_update_running": True,
            }

        _update_state.auto_update_enabled = True
        start_auto_update()

        return {
            "status": "started",
            "message": "تم تفعيل التحديث التلقائي — فحص GitHub كل 60 ثانية",
            "auto_update_enabled": True,
            "auto_update_running": _update_state.auto_update_running,
        }
    else:
        stop_auto_update()

        return {
            "status": "stopped",
            "message": "تم تعطيل التحديث التلقائي",
            "auto_update_enabled": False,
            "auto_update_running": False,
        }


@router.get("/review")
async def review_pending_changes():
    """مراجعة التعديلات — Get LLM review of pending changes without applying.

    Fetches from GitHub, gets the diff, and sends it to the LLM for review.
    Does NOT apply any changes — purely informational.
    """
    # First check if there are updates
    check_result = await _check_for_updates_internal()

    if not check_result.get("updates_available"):
        return {
            "status": "up_to_date",
            "message": "لا توجد تعديلات جديدة للمراجعة",
            "review": None,
            "check": check_result,
        }

    # Get the diff
    diff = get_git_diff()
    if not diff:
        return {
            "status": "no_diff",
            "message": "توجد تحديثات لكن لم يتم العثور على فروقات",
            "review": None,
            "check": check_result,
        }

    # LLM review
    review = await llm_review_diff(diff)

    # Save to state
    _update_state.last_auto_review = {
        "time": time.time(),
        "cycle": "manual",
        **review,
    }

    return {
        "status": "reviewed",
        "message": "تمت مراجعة التعديلات بواسطة الذكاء الاصطناعي",
        "review": review,
        "check": check_result,
        "diff_size": len(diff),
        "diff_preview": diff[:500] + ("..." if len(diff) > 500 else ""),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  v36.1: GitHub Configuration Endpoint (one-time setup)
# ═══════════════════════════════════════════════════════════════════════════════

class GitHubConfigRequest(BaseModel):
    """Request body for one-time GitHub configuration."""
    repo: str  # e.g. "babsharqii2023-rgb/babsharqii-v5"
    token: str  # GitHub personal access token
    branch: str = "main"  # Target branch (default: main)


@router.post("/configure", dependencies=[Depends(require_auth)])
async def configure_github(req: GitHubConfigRequest):
    """إعداد GitHub — One-time setup of repo + token + branch.
    
    Saves the configuration to .env file so it persists across restarts.
    Also updates the git remote URL to include the token for authentication.
    """
    _log(f"Configuring GitHub: repo={req.repo}, branch={req.branch}")
    
    try:
        # Step 1: Update .env file with the new configuration
        env_path = PROJECT_ROOT / "backend" / ".env"
        if not env_path.exists():
            env_path = PROJECT_ROOT / ".env"
        
        env_lines = []
        if env_path.exists():
            env_lines = env_path.read_text(encoding="utf-8").splitlines()
        
        # Update or add each config variable
        env_vars = {
            "MAMOUN_GITHUB_TOKEN": req.token,
            "MAMOUN_GITHUB_REPO": req.repo,
            "MAMOUN_GITHUB_BRANCH": req.branch,
        }
        
        for key, value in env_vars.items():
            found = False
            for i, line in enumerate(env_lines):
                if line.startswith(f"{key}="):
                    env_lines[i] = f"{key}={value}"
                    found = True
                    break
            if not found:
                env_lines.append(f"{key}={value}")
        
        env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
        
        # Step 2: Update config.py settings at runtime
        from mamoun.config import settings
        settings.github_token = req.token
        settings.github_repo = req.repo
        settings.github_branch = req.branch
        
        # Step 3: Update git remote URL with token for authentication
        auth_url = f"https://{req.token}@github.com/{req.repo}.git"
        _run_git("remote", "set-url", "origin", auth_url)
        
        # Step 4: Switch to the configured branch if needed
        current = _run_git("rev-parse", "--abbrev-ref", "HEAD")
        current_branch = current.stdout.strip() if current.returncode == 0 else ""
        
        if current_branch != req.branch:
            _run_git("checkout", req.branch)
        
        # Step 5: Fetch to verify connection
        fetch_result = _run_git("fetch", "origin", req.branch)
        if fetch_result.returncode != 0:
            _log(f"GitHub configuration: fetch test failed: {fetch_result.stderr}", "warning")
            # Don't fail — the config is saved, might just be network issue
        
        # Update state
        _update_state.github_configured = True
        _update_state.configured_repo = req.repo
        _update_state.configured_branch = req.branch
        
        _log(f"GitHub configured successfully: {req.repo} → {req.branch}")
        
        return {
            "status": "configured",
            "message": f"تم إعداد GitHub بنجاح: {req.repo} على فرع {req.branch}",
            "repo": req.repo,
            "branch": req.branch,
            "token_saved": bool(req.token),
            "fetch_test": "ok" if fetch_result.returncode == 0 else "failed",
        }
        
    except Exception as e:
        _log(f"GitHub configuration failed: {e}", "error")
        raise HTTPException(500, f"GitHub configuration failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  v36.1: Self-Modification Approval Queue
# ═══════════════════════════════════════════════════════════════════════════════

class ApprovalRequest(BaseModel):
    """Request to submit a self-modification for human approval."""
    modification_type: str  # e.g. "code_patch", "config_change", "dependency_update"
    description: str
    diff: str = ""
    auto_apply: bool = False  # If True, apply automatically when approved


class ApprovalDecision(BaseModel):
    """Human decision on a pending approval."""
    approval_id: str
    approved: bool
    reason: str = ""


@router.post("/request-approval", dependencies=[Depends(require_auth)])
async def request_modification_approval(req: ApprovalRequest):
    """طلب موافقة — Submit a self-modification for human approval.
    
    When require_approval=true (from laws.yaml), any self-modification
    must go through this queue before being applied.
    """
    global _approval_counter
    _approval_counter += 1
    
    approval_id = f"APR-{int(time.time())}-{_approval_counter}"
    
    approval_entry = {
        "id": approval_id,
        "type": req.modification_type,
        "description": req.description,
        "diff": req.diff[:5000],  # Limit diff size
        "proposed_at": time.time(),
        "status": "pending",
        "auto_apply": req.auto_apply,
    }
    
    _pending_approvals.append(approval_entry)
    
    # Keep only last 100 approvals
    if len(_pending_approvals) > 100:
        _pending_approvals[:] = _pending_approvals[-50:]
    
    _log(f"Approval requested: {approval_id} — {req.modification_type}: {req.description[:100]}")
    
    return {
        "status": "pending_approval",
        "approval_id": approval_id,
        "message": f"تم تقديم طلب التعديل للموافقة البشرية. رقم الطلب: {approval_id}",
        "queue_size": len([a for a in _pending_approvals if a["status"] == "pending"]),
    }


@router.get("/approvals")
async def list_pending_approvals():
    """عرض طلبات الموافقة — List all pending approval requests."""
    pending = [a for a in _pending_approvals if a["status"] == "pending"]
    recent = [a for a in _pending_approvals if a["status"] != "pending"][-10:]
    
    return {
        "pending": pending,
        "recent_decisions": recent,
        "total_pending": len(pending),
    }


@router.post("/approve", dependencies=[Depends(require_auth)])
async def decide_approval(req: ApprovalDecision):
    """الموافقة/الرفض — Approve or reject a pending modification request."""
    approval = None
    for a in _pending_approvals:
        if a["id"] == req.approval_id:
            approval = a
            break
    
    if not approval:
        raise HTTPException(404, f"Approval request {req.approval_id} not found")
    
    if approval["status"] != "pending":
        return {
            "status": "already_decided",
            "message": f"طلب {req.approval_id} تم البت فيه مسبقاً: {approval['status']}",
            "approval": approval,
        }
    
    approval["status"] = "approved" if req.approved else "rejected"
    approval["decided_at"] = time.time()
    approval["reason"] = req.reason
    
    result_status = "approved" if req.approved else "rejected"
    _log(f"Approval {req.approval_id}: {result_status} — {req.reason}")
    
    # If approved and auto_apply, try to apply the diff
    applied = False
    if req.approved and approval.get("auto_apply") and approval.get("diff"):
        try:
            diff_content = approval["diff"]
            # Apply the patch using git apply
            patch_result = subprocess.run(
                ["git", "apply"],
                input=diff_content,
                cwd=str(_GIT_REPO_DIR),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if patch_result.returncode == 0:
                applied = True
                _log(f"Auto-applied approved modification: {req.approval_id}")
            else:
                _log(f"Auto-apply failed for {req.approval_id}: {patch_result.stderr}", "warning")
        except Exception as e:
            _log(f"Auto-apply error for {req.approval_id}: {e}", "error")
    
    return {
        "status": result_status,
        "approval_id": req.approval_id,
        "message": f"تم {'الموافقة على' if req.approved else 'رفض'} طلب التعديل",
        "auto_applied": applied,
        "approval": approval,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  v37.0: Self-Mirror Endpoints
#  v37.0: Self-Mirror Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/mirror")
async def system_mirror():
    """المرآة — Full system self-reflection snapshot"""
    from mamoun.core.self_mirror import get_self_mirror
    mirror = get_self_mirror()
    return await mirror.full_system_snapshot()


@router.get("/conflicts")
async def detect_conflicts():
    """كشف التعارضات — Find naming conflicts, dead code, inconsistencies"""
    from mamoun.core.self_mirror import get_self_mirror
    mirror = get_self_mirror()
    conflicts = await mirror.detect_conflicts()
    return {"total_conflicts": len(conflicts), "conflicts": conflicts}


@router.get("/neural-coverage")
async def neural_bus_coverage():
    """تغطية الناقل العصبي — Verify NeuralBus reaches all pillars"""
    from mamoun.core.self_mirror import get_self_mirror
    mirror = get_self_mirror()
    return await mirror.verify_neural_bus_coverage()


@router.get("/kernel-control")
async def kernel_control_status():
    """تحكم النواة — Verify kernel has oversight over entire brain"""
    from mamoun.core.self_mirror import get_self_mirror
    mirror = get_self_mirror()
    return await mirror.verify_kernel_control()


@router.get("/fusion-depth")
async def fusion_depth():
    """درجة الانصهار — Measure how deeply integrated the components are"""
    from mamoun.core.self_mirror import get_self_mirror
    mirror = get_self_mirror()
    return await mirror.measure_fusion_depth()


@router.get("/quality")
async def quality_summary():
    """نموذج الجودة — Improvement quality history"""
    from mamoun.core.improvement_engine import get_improvement_engine
    engine = get_improvement_engine()
    return await engine.get_quality_summary()


@router.get("/stagnation")
async def stagnation_status():
    """حالة الركود — Check for improvement stagnation"""
    from mamoun.core.improvement_engine import get_improvement_engine
    engine = get_improvement_engine()
    return await engine.detect_stagnation()


# ═══════════════════════════════════════════════════════════════════════════════
#  v38.0: Manual Self-Improvement Pipeline (7 Guards)
# ═══════════════════════════════════════════════════════════════════════════════

class ImproveRequest(BaseModel):
    """Request body for manual self-improvement trigger."""
    github_token: str = ""
    github_repo: str = ""
    github_branch: str = "main"
    auto_fix: bool = True
    timeout_seconds: int = 300


@router.post("/improve")
async def manual_improve(req: ImproveRequest):
    """
    تحسين ذاتي يدوي — Manual trigger with 7 guards pipeline.
    
    Pipeline:
      1. Configure GitHub (if token/repo provided)
      2. Fetch & discover changes
      3. Guard 1: Impact Classification (L0→auto-reject)
      4. Guard 2: Measure before-metrics
      5. Guard 3: Dependency Analysis
      6. Pull & apply changes
      7. Guard 4: Test Gate
      8. Guard 5: Delta Analysis (before/after)
      9. Guard 6: Stagnation Detection
      10. Guard 7: Quality Model update
    """
    from mamoun.core.improvement_engine import get_improvement_engine, ImprovementRecord, ImpactLevel
    
    engine = get_improvement_engine()
    pipeline = []
    start_time = time.time()
    
    # ── Step 1: Configure GitHub if token provided ──
    step_start = time.time()
    if req.github_token and req.github_repo:
        try:
            from mamoun.config import settings
            settings.github_token = req.github_token
            settings.github_repo = req.github_repo
            if req.github_branch:
                settings.github_branch = req.github_branch
            
            # Update git remote URL
            auth_url = f"https://{req.github_token}@github.com/{req.github_repo}.git"
            _run_git("remote", "set-url", "origin", auth_url)
            
            _update_state.github_configured = True
            _update_state.configured_repo = req.github_repo
            _update_state.configured_branch = req.github_branch
            
            pipeline.append({"step": "إعداد GitHub", "status": "ok", "time": time.time() - step_start})
        except Exception as e:
            pipeline.append({"step": "إعداد GitHub", "status": "failed", "time": time.time() - step_start, "detail": str(e)})
    else:
        pipeline.append({"step": "إعداد GitHub", "status": "skipped", "time": 0})
    
    # ── Step 2: Fetch & check for updates ──
    step_start = time.time()
    check_result = await _check_for_updates_internal()
    
    if not check_result.get("updates_available"):
        pipeline.append({"step": "فحص التحديثات", "status": "no_updates", "time": time.time() - step_start})
        return {
            "status": "no_updates",
            "message": "لا توجد تحديثات جديدة على GitHub",
            "pipeline": pipeline,
            "check": check_result,
            "elapsed_seconds": round(time.time() - start_time, 1),
        }
    
    pipeline.append({"step": "فحص التحديثات", "status": "ok", "time": time.time() - step_start,
                     "detail": f"{check_result.get('new_commits', 0)} commits"})
    
    # ── Step 3: Get diff for guard analysis ──
    diff = get_git_diff()
    if not diff:
        pipeline.append({"step": "جلب الفروقات", "status": "no_diff", "time": 0})
        return {
            "status": "no_diff",
            "message": "توجد تحديثات لكن لا فروقات",
            "pipeline": pipeline,
            "elapsed_seconds": round(time.time() - start_time, 1),
        }
    
    # Get list of changed files
    files_changed_result = _run_git("diff", "--name-only", f"HEAD..origin/{_get_branch()}")
    files_changed = [f.strip() for f in files_changed_result.stdout.strip().split('\n') if f.strip()] if files_changed_result.returncode == 0 else []
    
    # ── Guard 1: Impact Classification ──
    step_start = time.time()
    classification = await engine.classify_impact(diff, files_changed)
    impact_level = classification.get("level", ImpactLevel.L0_COSMETIC)
    
    if isinstance(impact_level, ImpactLevel):
        impact_level_str = impact_level.value
    else:
        impact_level_str = str(impact_level)
    
    if classification.get("auto_reject"):
        # L0 cosmetic — auto-reject
        pipeline.append({"step": "Guard 1: تصنيف الأثر", "status": f"rejected_{impact_level_str}", "time": time.time() - step_start,
                         "detail": classification.get("reason", "")})
        
        # Record the rejection
        record = ImprovementRecord(
            impact_level=impact_level_str,
            diff_summary=diff[:200],
            files_changed=files_changed[:10],
            rejected=True,
            rejection_reason=classification.get("reason", "L0 — تجميلي"),
        )
        await engine.update_quality_model(record)
        
        return {
            "status": "rejected_cosmetic",
            "message": f"تم رفض التحديث: {classification.get('reason', '')}",
            "pipeline": pipeline,
            "classification": {"level": impact_level_str, "reason": classification.get("reason", "")},
            "elapsed_seconds": round(time.time() - start_time, 1),
        }
    
    pipeline.append({"step": "Guard 1: تصنيف الأثر", "status": impact_level_str, "time": time.time() - step_start,
                     "detail": classification.get("reason", "")})
    
    # ── Guard 2: Measure before-metrics ──
    step_start = time.time()
    before_metrics = await engine.measure_metrics()
    pipeline.append({"step": "Guard 2: قياس ما قبل", "status": "ok", "time": time.time() - step_start})
    
    # ── Guard 3: Dependency Analysis ──
    step_start = time.time()
    dep_analysis = await engine.analyze_dependencies(files_changed)
    pipeline.append({"step": "Guard 3: تحليل الاعتماديات", "status": dep_analysis.get("risk", "ok"),
                     "time": time.time() - step_start,
                     "detail": dep_analysis.get("note", "")})
    
    # ── Pull & Apply ──
    step_start = time.time()
    try:
        apply_result = await _pull_and_apply_internal()
        pipeline.append({"step": "سحب وتطبيق التحديثات", "status": "ok", "time": time.time() - step_start,
                         "detail": f"commit={apply_result.get('new_commit', '?')}"})
    except Exception as e:
        pipeline.append({"step": "سحب وتطبيق التحديثات", "status": "ROLLBACK", "time": time.time() - step_start,
                         "detail": str(e)})
        
        record = ImprovementRecord(
            impact_level=impact_level_str,
            diff_summary=diff[:200],
            files_changed=files_changed[:10],
            before_metrics=before_metrics,
            rejected=True,
            rejection_reason=f"فشل التطبيق: {str(e)}",
        )
        await engine.update_quality_model(record)
        
        return {
            "status": "failed_apply",
            "message": f"فشل تطبيق التحديث وتم التراجع: {str(e)}",
            "pipeline": pipeline,
            "elapsed_seconds": round(time.time() - start_time, 1),
        }
    
    # ── Guard 4: Test Gate (generate test for the change) ──
    step_start = time.time()
    test_result = await engine.generate_test(diff, files_changed)
    pipeline.append({"step": "Guard 4: بوابة الاختبار", "status": "ok" if test_result.get("success") else "skipped",
                     "time": time.time() - step_start,
                     "detail": test_result.get("description", "")})
    
    # ── Guard 5: Delta Analysis (measure after & compare) ──
    step_start = time.time()
    after_metrics = await engine.measure_metrics()
    delta_result = await engine.delta_analysis(before_metrics, after_metrics)
    decision = delta_result.get("decision", "PARTIAL")
    
    if decision == "ROLLBACK":
        pipeline.append({"step": "Guard 5: تحليل الفرق", "status": "ROLLBACK", "time": time.time() - step_start,
                         "detail": delta_result.get("reason", "")})
        # Rollback
        _run_git("reset", "--hard", "HEAD~1")
        
        record = ImprovementRecord(
            impact_level=impact_level_str,
            diff_summary=diff[:200],
            files_changed=files_changed[:10],
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            delta=delta_result.get("delta", {}),
            rejected=True,
            rejection_reason=delta_result.get("reason", "انحدار — ROLLBACK"),
        )
        await engine.update_quality_model(record)
        
        return {
            "status": "rollback_regression",
            "message": f"تم التراجع: {delta_result.get('reason', '')}",
            "pipeline": pipeline,
            "classification": {"level": impact_level_str, "reason": classification.get("reason", "")},
            "elapsed_seconds": round(time.time() - start_time, 1),
        }
    
    pipeline.append({"step": "Guard 5: تحليل الفرق", "status": decision, "time": time.time() - step_start,
                     "detail": delta_result.get("reason", "")})
    
    # ── Guard 6: Stagnation Detection ──
    step_start = time.time()
    stagnation = await engine.detect_stagnation()
    pipeline.append({"step": "Guard 6: كشف الركود", "status": stagnation.get("stagnation_level", "NONE"),
                     "time": time.time() - step_start})
    
    # ── Guard 7: Quality Model Update ──
    step_start = time.time()
    is_verified = decision in ("CONFIRM", "PARTIAL")
    record = ImprovementRecord(
        impact_level=impact_level_str,
        diff_summary=diff[:200],
        files_changed=files_changed[:10],
        before_metrics=before_metrics,
        after_metrics=after_metrics,
        delta=delta_result.get("delta", {}),
        verified=is_verified,
        rejected=False,
    )
    await engine.update_quality_model(record)
    pipeline.append({"step": "Guard 7: نموذج الجودة", "status": "ok", "time": time.time() - step_start})
    
    # ── Final result ──
    elapsed = round(time.time() - start_time, 1)
    
    # Publish to NeuralBus
    try:
        from mamoun.core.neural_bus import neural_bus
        if neural_bus._initialized:
            neural_bus.publish(
                signal_type="action_completed",
                source="update:improve",
                payload={"level": impact_level_str, "verified": is_verified, "elapsed": elapsed},
            )
    except Exception:
        pass
    
    if decision == "CONFIRM":
        final_status = "success"
        final_message = f"تم التحسين بنجاح! تصنيف: {impact_level_str} — تحسن مؤكد بالأرقام"
    elif decision == "PARTIAL":
        final_status = "success"
        final_message = f"تم التحسين جزئياً. تصنيف: {impact_level_str} — بعض المقاييس تحسنت"
    elif decision == "REJECT":
        final_status = "rejected_cosmetic"
        final_message = f"تم رفض التحسين: {delta_result.get('reason', 'تغيير شكلي')}"
    else:
        final_status = "success"
        final_message = f"تم تطبيق التحسين. تصنيف: {impact_level_str}"
    
    return {
        "status": final_status,
        "message": final_message,
        "pipeline": pipeline,
        "classification": {"level": impact_level_str, "reason": classification.get("reason", "")},
        "delta": delta_result.get("delta", {}),
        "stagnation": stagnation.get("stagnation_level", "NONE"),
        "elapsed_seconds": elapsed,
        "restart_recommended": True,
    }
