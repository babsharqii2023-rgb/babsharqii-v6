"""
BABSHARQII v40.0 — File System API
واجهة نظام الملفات — يسمح للمحادثة بإنشاء/تعديل/حذف ملفات بأمان
v40.0 Fusion Step 4: File System API
"""

import os
import shutil
import time
import logging
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("mamoun.api.file_system")

router = APIRouter(prefix="/fs", tags=["file-system"])

# ═══ Configuration ═══════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # babsharqii-v5
PROTECTED_PATTERNS = ['.env', '.key', '.pem', 'safety_guard', 'laws.yaml', 'id_rsa']
PROTECTED_NAMES = {
    '.env', '.env.local', '.env.production', '.env.development',
    'laws.yaml', 'safety_guard.py', 'approval_gate.py',
    'package-lock.json', 'yarn.lock',
}


class CreateFileRequest(BaseModel):
    path: str
    content: str = ""
    specification: Optional[str] = None  # for LLM-generated content


class WriteFileRequest(BaseModel):
    path: str
    content: str
    create_backup: bool = True


class DeleteFileRequest(BaseModel):
    path: str
    force: bool = False


# ═══ Security Helpers ═════════════════════════════════════════════════

def _validate_path(path: str) -> Path:
    """التحقق أن المسار داخل المشروع فقط"""
    target = (PROJECT_ROOT / path).resolve()
    if not str(target).startswith(str(PROJECT_ROOT.resolve())):
        raise HTTPException(403, "مسار خارج المشروع — غير مسموح")
    if target.name in PROTECTED_NAMES:
        raise HTTPException(403, f"ملف محمي — لا يمكن تعديل {target.name}")
    for pattern in PROTECTED_PATTERNS:
        if pattern in str(target):
            raise HTTPException(403, f"مسار محمي — يحتوي على {pattern}")
    return target


def _backup_file(target: Path) -> Optional[str]:
    """إنشاء نسخة احتياطية"""
    if not target.exists():
        return None
    backup_dir = PROJECT_ROOT / ".backups" / "fs"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{target.stem}_{int(time.time())}{target.suffix}"
    shutil.copy2(target, backup_path)
    return str(backup_path)


# ═══ Endpoints ═══════════════════════════════════════════════════════

@router.post("/create")
async def create_file(req: CreateFileRequest):
    """إنشاء ملف جديد"""
    target = _validate_path(req.path)
    
    # إذا كان المحتوى فارغاً والمواصفات موجودة → ولّد بالـ LLM
    content = req.content
    if not content and req.specification:
        try:
            from mamoun.core.llm_client import get_llm_client
            llm = get_llm_client()
            is_ts = req.path.endswith(('.ts', '.tsx', '.js', '.jsx'))
            lang = "TypeScript/React" if is_ts else "Python"
            generated = await llm.think(
                f"Generate a {lang} file for: {req.specification}\nFile: {req.path}\nOutput ONLY the code, no markdown.",
                model="glm-5.1", temperature=0.3,
            )
            if generated and len(generated) > 20:
                content = generated.strip()
                if content.startswith('```'):
                    lines = content.split('\n')
                    content = '\n'.join(lines[1:-1])
        except Exception as e:
            logger.warning(f"LLM content generation failed: {e}")
    
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    
    return {"status": "created", "path": str(target.relative_to(PROJECT_ROOT)), "size": len(content)}


@router.get("/read")
async def read_file(path: str):
    """قراءة ملف"""
    target = _validate_path(path)
    if not target.exists():
        raise HTTPException(404, f"الملف غير موجود: {path}")
    if not target.is_file():
        raise HTTPException(400, f"ليس ملفاً: {path}")
    if target.stat().st_size > 500_000:  # 500KB limit
        raise HTTPException(413, "الملف كبير جداً — الحد الأقصى 500KB")
    
    try:
        content = target.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        content = target.read_text(encoding='latin-1')
    
    return {
        "path": str(target.relative_to(PROJECT_ROOT)),
        "content": content,
        "size": len(content),
        "modified": target.stat().st_mtime,
    }


@router.post("/write")
async def write_file(req: WriteFileRequest):
    """تعديل ملف موجود — مع نسخة احتياطية"""
    target = _validate_path(req.path)
    
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
    
    # نسخ احتياطي
    backup_path = None
    if req.create_backup and target.exists():
        backup_path = _backup_file(target)
    
    target.write_text(req.content, encoding='utf-8')
    
    return {
        "status": "written",
        "path": str(target.relative_to(PROJECT_ROOT)),
        "size": len(req.content),
        "backup": backup_path,
    }


@router.post("/delete")
async def delete_file(req: DeleteFileRequest):
    """حذف ملف — محمي بشدة"""
    target = _validate_path(req.path)
    
    if not target.exists():
        raise HTTPException(404, f"الملف غير موجود: {path}")
    
    # نسخ احتياطي قبل الحذف
    backup_path = _backup_file(target)
    
    target.unlink()
    
    return {"status": "deleted", "path": str(target.relative_to(PROJECT_ROOT)), "backup": backup_path}


@router.get("/list")
async def list_directory(path: str = ""):
    """عرض محتويات مجلد"""
    target = _validate_path(path) if path else PROJECT_ROOT
    
    if not target.exists():
        raise HTTPException(404, f"المجلد غير موجود: {path}")
    if not target.is_dir():
        raise HTTPException(400, f"ليس مجلداً: {path}")
    
    entries = []
    for entry in sorted(target.iterdir()):
        if entry.name.startswith('.') and entry.name not in ['.env.example']:
            continue
        if entry.name in ('node_modules', '__pycache__', '.git', '.next', '.backups'):
            continue
        entries.append({
            "name": entry.name,
            "type": "directory" if entry.is_dir() else "file",
            "size": entry.stat().st_size if entry.is_file() else 0,
        })
    
    return {"path": str(target.relative_to(PROJECT_ROOT)) if path else "/", "entries": entries}


@router.get("/tree")
async def project_tree():
    """عرض شجرة المشروع كاملة"""
    tree_lines = []
    skip_dirs = {'node_modules', '__pycache__', '.git', '.next', '.backups', '.venv', 'dist', 'build'}
    skip_exts = {'.pyc', '.pyo', '.map'}
    
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Skip unwanted directories
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
        
        rel_root = Path(root).relative_to(PROJECT_ROOT)
        level = len(rel_root.parts)
        indent = "  " * level
        
        if str(rel_root) != ".":
            tree_lines.append(f"{indent}{rel_root.name}/")
        
        # Limit files shown per directory
        for f in sorted(files)[:30]:
            if Path(f).suffix in skip_exts:
                continue
            tree_lines.append(f"{indent}  {f}")
    
    tree_text = '\n'.join(tree_lines[:500])  # Limit output
    return {"tree": tree_text, "root": str(PROJECT_ROOT.name)}
