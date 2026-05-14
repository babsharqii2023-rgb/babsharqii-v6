"""
BABSHARQII v40.0 — External Project Controller
يتحكم بمشاريع خارجية — استنساخ + تعديل + نشر + مراقبة + تشغيل أوامر
v40.0 Fusion Step 7: Enhanced External Project Control

Endpoints:
  - POST /clone          — استنساخ مشروع خارجي
  - POST /edit            — تعديل ملف واحد بالـ LLM
  - POST /modify          — تعديل متعدد الملفات بالـ LLM (جديد)
  - POST /deploy          — نشر مشروع خارجي
  - GET  /monitor/{name}  — مراقبة صحة المشروع (جديد)
  - POST /run             — تشغيل أمر في دليل المشروع (جديد)
  - GET  /structure/{name}— عرض شجرة الملفات مع الأحجام (جديد)
  - GET  /list            — عرض المشاريع الخارجية
"""

import subprocess
import logging
import time
import json
import os
import shutil
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("mamoun.api.external_controller")

router = APIRouter(prefix="/external", tags=["external-controller"])

EXTERNAL_DIR = Path("/home/z/my-project/external-projects")

# ═══ Safety: forbidden command patterns ═══════════════════════════
FORBIDDEN_COMMAND_PATTERNS = [
    "rm -rf /", "mkfs.", "dd if=", ":(){ :|:& };:",
    "shutdown", "reboot", "init 0", "init 6",
    "format ", "del /f /s /q C:",
    "> /dev/sd", "mv / ", "chmod -R 777 /",
]

MAX_COMMAND_TIMEOUT = 120  # seconds


class CloneRequest(BaseModel):
    repo_url: str
    target_dir: Optional[str] = None
    branch: Optional[str] = None


class ExternalEditRequest(BaseModel):
    project_dir: str
    file_path: str
    description: str  # ماذا تريد تغييره
    auto_approve: bool = False


class ModifyExternalRequest(BaseModel):
    """طلب تعديل مشروع خارجي عبر عدة ملفات"""
    project_dir: str
    description: str  # وصف التعديل المطلوب — LLM يحلل ويعدّل


class DeployRequest(BaseModel):
    project_dir: str
    build_command: Optional[str] = None
    deploy_command: Optional[str] = None


class RunCommandRequest(BaseModel):
    """طلب تشغيل أمر في دليل المشروع"""
    project_dir: str
    command: str
    timeout: Optional[int] = 30


# ═══ Endpoints ═══════════════════════════════════════════════════════

@router.post("/clone")
async def clone_project(req: CloneRequest):
    """استنساخ مشروع خارجي"""
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    
    target = req.target_dir or req.repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    target_path = EXTERNAL_DIR / target
    
    if target_path.exists():
        return {"status": "already_exists", "path": str(target_path)}
    
    cmd = ["git", "clone", req.repo_url, str(target_path)]
    if req.branch:
        cmd.extend(["-b", req.branch])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return {"status": "cloned", "path": str(target_path), "repo": req.repo_url}
        else:
            raise HTTPException(500, f"فشل الاستنساخ: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        raise HTTPException(408, "انتهت مهلة الاستنساخ")


@router.post("/edit")
async def edit_external_file(req: ExternalEditRequest):
    """تعديل ملف في مشروع خارجي بالـ LLM"""
    project_path = Path(req.project_dir)
    if not project_path.exists():
        raise HTTPException(404, f"المشروع غير موجود: {req.project_dir}")
    
    file_path = project_path / req.file_path
    if not file_path.exists():
        raise HTTPException(404, f"الملف غير موجود: {req.file_path}")
    
    # قراءة الكود الحالي
    try:
        current_code = file_path.read_text(encoding='utf-8')
    except Exception as e:
        raise HTTPException(500, f"فشل قراءة الملف: {e}")
    
    # تعديل بالـ LLM
    try:
        from mamoun.core.llm_client import get_llm_client
        llm = get_llm_client()
        
        is_ts = str(file_path).endswith(('.ts', '.tsx', '.js', '.jsx'))
        lang = "TypeScript/React" if is_ts else "Python"
        
        new_code = await llm.think(
            f"Modify this {lang} file:\n\nFile: {req.file_path}\nInstruction: {req.description}\n\nCurrent code:\n```{'typescript' if is_ts else 'python'}\n{current_code[:8000]}\n```\n\nWrite the COMPLETE modified file. Output ONLY the code.",
            model="glm-5.1", temperature=0.3,
        )
        
        if not new_code or len(new_code) < 20:
            raise HTTPException(500, "فشل توليد الكود المعدّل")
        
        # إزالة markdown wrapper
        if new_code.strip().startswith('```'):
            lines = new_code.strip().split('\n')
            new_code = '\n'.join(lines[1:-1])
        
        # نسخ احتياطي
        backup_dir = project_path / ".backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / f"{file_path.stem}_{int(time.time())}{file_path.suffix}"
        import shutil
        shutil.copy2(file_path, backup_path)
        
        # كتابة التعديل
        file_path.write_text(new_code, encoding='utf-8')
        
        return {
            "status": "edited",
            "file": req.file_path,
            "backup": str(backup_path),
            "size": len(new_code),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"External edit failed: {e}")
        raise HTTPException(500, f"فشل التعديل: {str(e)[:200]}")


@router.post("/deploy")
async def deploy_external(req: DeployRequest):
    """نشر مشروع خارجي"""
    project_path = Path(req.project_dir)
    if not project_path.exists():
        raise HTTPException(404, f"المشروع غير موجود: {req.project_dir}")
    
    results = {"build": None, "deploy": None}
    
    # بناء
    build_cmd = req.build_command or "npm run build"
    try:
        build_result = subprocess.run(
            build_cmd.split(), capture_output=True, text=True,
            cwd=str(project_path), timeout=120,
        )
        results["build"] = {
            "success": build_result.returncode == 0,
            "output": build_result.stdout[-500:] if build_result.stdout else "",
            "errors": build_result.stderr[-500:] if build_result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        results["build"] = {"success": False, "errors": "Build timed out"}
    
    # نشر
    if req.deploy_command:
        try:
            deploy_result = subprocess.run(
                req.deploy_command.split(), capture_output=True, text=True,
                cwd=str(project_path), timeout=120,
            )
            results["deploy"] = {
                "success": deploy_result.returncode == 0,
                "output": deploy_result.stdout[-500:] if deploy_result.stdout else "",
            }
        except subprocess.TimeoutExpired:
            results["deploy"] = {"success": False, "errors": "Deploy timed out"}
    
    return results


@router.get("/list")
async def list_external_projects():
    """عرض المشاريع الخارجية"""
    if not EXTERNAL_DIR.exists():
        return {"projects": []}
    
    projects = []
    for d in EXTERNAL_DIR.iterdir():
        if d.is_dir() and not d.name.startswith('.'):
            projects.append({
                "name": d.name,
                "path": str(d),
                "has_git": (d / ".git").exists(),
            })
    
    return {"projects": projects}


# ═══ v40.0 Fusion Step 7: New Endpoints ══════════════════════════════


@router.post("/modify")
async def modify_external_project(req: ModifyExternalRequest):
    """
    تعديل مشروع خارجي عبر عدة ملفات — LLM يحلل المشروع ويعدّله

    يقرأ هيكل المشروع، يحلله بالـ LLM، ثم يعدّل الملفات المناسبة
    """
    project_path = Path(req.project_dir)
    if not project_path.exists():
        # Try as project name under EXTERNAL_DIR
        alt_path = EXTERNAL_DIR / req.project_dir
        if alt_path.exists():
            project_path = alt_path
        else:
            raise HTTPException(404, f"المشروع غير موجود: {req.project_dir}")

    # Step 1: Gather project structure and key files
    file_list = []
    key_files_content = {}
    skip_dirs = {".git", "node_modules", "__pycache__", ".next", "dist", "build", ".backups", "venv", ".venv"}

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            fp = Path(root) / f
            rel = fp.relative_to(project_path)
            file_list.append(str(rel))
            # Read key files (small source files)
            if fp.suffix in ('.py', '.ts', '.tsx', '.js', '.jsx', '.json', '.yaml', '.yml', '.md') and fp.stat().st_size < 50000:
                try:
                    key_files_content[str(rel)] = fp.read_text(encoding='utf-8')[:3000]
                except Exception:
                    pass

    if not file_list:
        raise HTTPException(400, "المشروع فارغ — لا توجد ملفات")

    # Step 2: Analyze with LLM and get modification plan
    try:
        from mamoun.core.llm_client import get_llm_client
        llm = get_llm_client()

        files_preview = "\n".join(file_list[:80])
        key_content_preview = "\n".join(
            f"\n--- {path} ---\n{content[:1500]}"
            for path, content in list(key_files_content.items())[:15]
        )

        analysis_prompt = f"""أنت مطور برمجيات خبير. حلّل هذا المشروع واقترح التعديلات المطلوبة.

المشروع: {project_path.name}
التعديل المطلوب: {req.description}

هيكل الملفات:
{files_preview}

محتوى الملفات الرئيسية:
{key_content_preview[:12000]}

المطلوب:
1. حدد الملفات التي تحتاج تعديل
2. لكل ملف، اكتب الكود المعدّل كاملاً

أجب بصيغة JSON:
[
    {{
        "file_path": "relative/path/to/file",
        "explanation": "سبب التعديل",
        "new_content": "الكود الجديد كاملاً"
    }}
]

إذا لم يكن أي تعديل مطلوب، أجب: []"""

        response = await llm.think(
            analysis_prompt,
            model="glm-5.1",
            temperature=0.3,
        )

        # Parse the LLM response for modifications
        modifications = []
        raw = response if isinstance(response, str) else str(response)

        # Try JSON extraction
        try:
            # Find JSON array in response
            start = raw.find('[')
            end = raw.rfind(']') + 1
            if start >= 0 and end > start:
                parsed = json.loads(raw[start:end])
                if isinstance(parsed, list):
                    modifications = parsed
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM modification response as JSON")

        if not modifications:
            return {
                "status": "no_changes",
                "message": "لم يحدد الـ LLM أي تعديلات مطلوبة",
                "project": str(project_path),
            }

        # Step 3: Apply modifications with backup
        backup_dir = project_path / ".backups"
        backup_dir.mkdir(exist_ok=True)
        timestamp = int(time.time())
        applied = []
        errors = []

        for mod in modifications:
            file_path_str = mod.get("file_path", "")
            new_content = mod.get("new_content", "")
            explanation = mod.get("explanation", "")

            if not file_path_str or not new_content:
                continue

            target_file = project_path / file_path_str
            if not target_file.exists():
                # Try creating the file if parent directory exists
                target_file.parent.mkdir(parents=True, exist_ok=True)
                if not target_file.parent.exists():
                    errors.append(f"المسار غير موجود: {file_path_str}")
                    continue

            # Backup original
            if target_file.exists():
                backup_path = backup_dir / f"{target_file.stem}_{timestamp}{target_file.suffix}"
                shutil.copy2(target_file, backup_path)

            # Write new content
            try:
                target_file.write_text(new_content, encoding='utf-8')
                applied.append({
                    "file": file_path_str,
                    "explanation": explanation,
                    "size": len(new_content),
                })
            except Exception as e:
                errors.append(f"فشل كتابة {file_path_str}: {e}")

        return {
            "status": "modified",
            "project": str(project_path),
            "modifications_applied": len(applied),
            "modifications": applied,
            "errors": errors,
            "backup_dir": str(backup_dir),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"External modify failed: {e}")
        raise HTTPException(500, f"فشل التعديل: {str(e)[:200]}")


@router.get("/monitor/{project_name}")
async def monitor_external_project(project_name: str):
    """
    مراقبة صحة المشروع الخارجي

    يفحص: حالة البناء، نتائج الاختبارات، التغييرات في الملفات
    """
    project_path = EXTERNAL_DIR / project_name
    if not project_path.exists():
        raise HTTPException(404, f"المشروع غير موجود: {project_name}")

    health = {
        "project": project_name,
        "path": str(project_path),
        "exists": True,
        "has_git": (project_path / ".git").exists(),
        "build_status": None,
        "test_status": None,
        "file_changes": None,
        "disk_usage": None,
        "last_modified": None,
    }

    # Disk usage
    try:
        total_size = sum(f.stat().st_size for f in project_path.rglob('*') if f.is_file())
        health["disk_usage"] = {
            "total_bytes": total_size,
            "total_mb": round(total_size / (1024 * 1024), 2),
        }
    except Exception:
        pass

    # Last modified file
    try:
        latest = max(
            (f for f in project_path.rglob('*') if f.is_file() and '.git' not in str(f)),
            key=lambda f: f.stat().st_mtime,
            default=None,
        )
        if latest:
            health["last_modified"] = {
                "file": str(latest.relative_to(project_path)),
                "timestamp": latest.stat().st_mtime,
            }
    except Exception:
        pass

    # Git status (if git repo)
    if health["has_git"]:
        try:
            git_status = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True,
                cwd=str(project_path), timeout=10,
            )
            changed_files = [line.strip() for line in git_status.stdout.strip().split('\n') if line.strip()]
            health["file_changes"] = {
                "count": len(changed_files),
                "files": changed_files[:20],
            }

            # Last commit
            git_log = subprocess.run(
                ["git", "log", "-1", "--format=%H|%ai|%s"],
                capture_output=True, text=True,
                cwd=str(project_path), timeout=10,
            )
            if git_log.returncode == 0 and git_log.stdout.strip():
                parts = git_log.stdout.strip().split('|', 2)
                health["last_commit"] = {
                    "hash": parts[0][:12] if len(parts) > 0 else "",
                    "date": parts[1] if len(parts) > 1 else "",
                    "message": parts[2] if len(parts) > 2 else "",
                }
        except (subprocess.TimeoutExpired, Exception) as e:
            health["file_changes"] = {"error": str(e)[:100]}

    # Build check — detect project type and try build
    if (project_path / "package.json").exists():
        health["project_type"] = "node"
        try:
            build_check = subprocess.run(
                ["npm", "run", "build"],
                capture_output=True, text=True,
                cwd=str(project_path), timeout=60,
            )
            health["build_status"] = {
                "success": build_check.returncode == 0,
                "output": build_check.stdout[-300:] if build_check.stdout else "",
                "errors": build_check.stderr[-300:] if build_check.stderr else "",
            }
        except subprocess.TimeoutExpired:
            health["build_status"] = {"success": False, "errors": "Build timed out"}
        except Exception as e:
            health["build_status"] = {"success": False, "errors": str(e)[:200]}

    elif (project_path / "setup.py").exists() or (project_path / "pyproject.toml").exists():
        health["project_type"] = "python"
        # Python projects: try syntax check
        try:
            syntax_check = subprocess.run(
                ["python", "-m", "py_compile", "setup.py"],
                capture_output=True, text=True,
                cwd=str(project_path), timeout=10,
            )
            health["build_status"] = {
                "success": syntax_check.returncode == 0,
                "errors": syntax_check.stderr[-200:] if syntax_check.stderr else "",
            }
        except Exception:
            pass

    # Test check — look for test directories and try running
    test_dirs = ["tests", "test", "__tests__", "spec"]
    for td in test_dirs:
        if (project_path / td).exists():
            health["test_directory"] = td
            if health.get("project_type") == "node":
                try:
                    test_result = subprocess.run(
                        ["npm", "test"],
                        capture_output=True, text=True,
                        cwd=str(project_path), timeout=60,
                    )
                    health["test_status"] = {
                        "success": test_result.returncode == 0,
                        "output": test_result.stdout[-300:] if test_result.stdout else "",
                        "errors": test_result.stderr[-300:] if test_result.stderr else "",
                    }
                except subprocess.TimeoutExpired:
                    health["test_status"] = {"success": False, "errors": "Tests timed out"}
                except Exception as e:
                    health["test_status"] = {"success": False, "errors": str(e)[:200]}
            break

    return health


@router.post("/run")
async def run_command(req: RunCommandRequest):
    """
    تشغيل أمر في دليل المشروع — مع فحوصات أمان

    Safety checks:
    - Forbidden patterns blocked
    - Timeout enforced
    - Project must exist
    """
    project_path = Path(req.project_dir)
    if not project_path.exists():
        alt_path = EXTERNAL_DIR / req.project_dir
        if alt_path.exists():
            project_path = alt_path
        else:
            raise HTTPException(404, f"المشروع غير موجود: {req.project_dir}")

    # Safety: check for forbidden patterns
    cmd_lower = req.command.lower()
    for pattern in FORBIDDEN_COMMAND_PATTERNS:
        if pattern.lower() in cmd_lower:
            raise HTTPException(
                403,
                f"الأمر مرفوض لأسباب أمان — يحتوي نمطاً محظوراً: {pattern}",
            )

    # Safety: block commands that write outside project directory
    if ".." in req.command and (">" in req.command or ">>" in req.command):
        raise HTTPException(403, "الأمر مرفوض — محاولة كتابة خارج دليل المشروع")

    # Enforce timeout
    timeout = min(req.timeout or 30, MAX_COMMAND_TIMEOUT)

    try:
        result = subprocess.run(
            req.command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(project_path),
            timeout=timeout,
        )

        return {
            "status": "completed",
            "exit_code": result.returncode,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-1000:] if result.stderr else "",
            "command": req.command,
            "timeout": timeout,
            "project_dir": str(project_path),
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(
            408,
            f"انتهت مهلة الأمر بعد {timeout} ثانية",
        )
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        raise HTTPException(500, f"فشل تنفيذ الأمر: {str(e)[:200]}")


@router.get("/structure/{project_name}")
async def read_project_structure(project_name: str):
    """
    عرض شجرة الملفات الكاملة مع أحجام الملفات

    يعرض كل ملف ومجلد مع حجمه
    """
    project_path = EXTERNAL_DIR / project_name
    if not project_path.exists():
        raise HTTPException(404, f"المشروع غير موجود: {project_name}")

    skip_dirs = {".git", "node_modules", "__pycache__", ".next", "dist", "build", ".backups", "venv", ".venv"}

    def build_tree(path: Path, prefix: str = "") -> list:
        """بناء شجرة الملفات بشكل متداخل"""
        entries = []
        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return entries

        for item in items:
            if item.name in skip_dirs and item.is_dir():
                continue
            if item.name.startswith('.') and item.is_dir():
                continue

            if item.is_dir():
                try:
                    dir_size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                except (PermissionError, OSError):
                    dir_size = 0
                entries.append({
                    "name": item.name,
                    "type": "directory",
                    "size_bytes": dir_size,
                    "size_readable": _format_size(dir_size),
                    "path": str(item.relative_to(project_path)),
                })
            else:
                try:
                    file_size = item.stat().st_size
                except (PermissionError, OSError):
                    file_size = 0
                entries.append({
                    "name": item.name,
                    "type": "file",
                    "size_bytes": file_size,
                    "size_readable": _format_size(file_size),
                    "path": str(item.relative_to(project_path)),
                    "extension": item.suffix,
                })
        return entries

    tree = build_tree(project_path)

    # Total size
    try:
        total_size = sum(f.stat().st_size for f in project_path.rglob('*') if f.is_file())
    except (PermissionError, OSError):
        total_size = 0

    return {
        "project": project_name,
        "path": str(project_path),
        "tree": tree,
        "total_files": sum(1 for e in tree if e["type"] == "file"),
        "total_dirs": sum(1 for e in tree if e["type"] == "directory"),
        "total_size_bytes": total_size,
        "total_size_readable": _format_size(total_size),
    }


def _format_size(size_bytes: int) -> str:
    """تحويل حجم البايتات لصيغة مقروءة"""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.1f} {units[i]}"
