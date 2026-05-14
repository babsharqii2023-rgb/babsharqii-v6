"""
BABSHARQII v12.0 — FileSystem Tool
أداة الملفات الآمنة — تقرأ وتكتب ملفات المشروع داخل sandbox.

Safety Features:
- Zero Standing Privilege: لا وصول بدون صلاحية زمنية
- Sandbox root: لا وصول خارج مسار المشروع
- Forbidden paths: لا وصول لـ /etc, /var, secrets/, keys/
- Time-bounded: كل عملية تحتاج صلاحية فعالة
- Audit trail: سجل كامل لكل عملية قراءة/كتابة
- Confirmation gate: حذف الملفات يتطلب تأكيد إضافي
"""

import os
import json
import logging
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

FILESYSTEM_ENABLED = os.getenv("MAMOUN_FILESYSTEM_TOOLS", "false").lower() == "true"

# Forbidden path patterns — never accessible
FORBIDDEN_PATTERNS = [
    "/etc/", "/var/", "/sys/", "/proc/", "/dev/", "/root/",
    "secrets/", "keys/", "certs/", ".ssh/", ".gnupg/",
    ".env", "credentials", "password", "token",
    "__pycache__", ".git/objects/",
]

# Protected files — read-only even with write permission
PROTECTED_FILES = [
    "laws.yaml", "policies.yaml", "policies_v2.yaml",
    "safety_guard.py", "approval_gate.py", "safety_gate_client.py",
    "settings.yaml",
]


@dataclass
class FileSystemResult:
    """نتيجة عملية ملف."""
    success: bool = False
    path: str = ""
    operation: str = ""  # "read", "write", "list", "delete", "mkdir", "copy"
    content: str = ""    # For read operations
    entries: list = field(default_factory=list)  # For list operations
    error: str = ""
    size_bytes: int = 0
    timestamp: float = 0.0
    grant_id: str = ""


class FileSystemTool:
    """
    أداة الملفات الآمنة — تقرأ وتكتب ملفات المشروع داخل sandbox.
    
    Integration with TimeBoundedPolicy:
    - Every operation requires a valid grant_id
    - Grant must be active and not expired
    - Grant scope must include "filesystem:read" or "filesystem:write"
    - Grant task_context must match current task
    
    Usage:
        fs = FileSystemTool(sandbox_root="/path/to/project", time_bounded_policy=policy)
        
        # Request permission first
        result = await policy.request_permission(
            agent_id="code_agent",
            scope="filesystem:write",
            permissions=["read", "write"],
            duration_minutes=60,
            resource_path="/path/to/project/backend",
            task_context="fix_bug_123",
        )
        grant_id = result["grant_id"]
        
        # Use the tool
        write_result = await fs.write_file("backend/new_module.py", "print('hello')", grant_id)
    """
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB max file size
    MAX_LIST_ENTRIES = 1000  # Max entries in directory listing
    
    def __init__(self, sandbox_root: str = "", time_bounded_policy=None):
        """
        Args:
            sandbox_root: المسار الجذر — لا وصول خارجه
            time_bounded_policy: سياسة الصلاحيات الزمنية
        """
        self.sandbox_root = Path(sandbox_root or os.getenv(
            "MAMOUN_PROJECT_ROOT", str(Path(__file__).parent.parent.parent.parent)
        )).resolve()
        self._policy = time_bounded_policy
        self._audit_log: list[dict] = []
        self._initialized = False
    
    async def initialize(self):
        """تهيئة الأداة."""
        if self._initialized:
            return
        self._initialized = True
        logger.info(f"FileSystemTool initialized — Sandbox root: {self.sandbox_root}")
    
    async def read_file(self, path: str, grant_id: str = "", task_context: str = "") -> FileSystemResult:
        """
        قراءة ملف — يتطلب صلاحية filesystem:read.
        
        Args:
            path: مسار الملف (نسبي أو مطلق داخل sandbox)
            grant_id: معرف الصلاحية الزمنية
            task_context: سياق المهمة
        
        Returns:
            FileSystemResult with content
        """
        await self.initialize()
        
        # Verify permission
        perm_check = await self._verify_permission(
            grant_id, "filesystem:read", ["read"], task_context
        )
        if not perm_check["valid"]:
            return FileSystemResult(
                success=False, path=path, operation="read",
                error=perm_check["reason"],
            )
        
        # Resolve and validate path
        resolved = self._resolve_path(path)
        validation = self._validate_path(resolved, "read")
        if not validation["valid"]:
            return FileSystemResult(
                success=False, path=path, operation="read",
                error=validation["reason"],
            )
        
        # Read the file
        try:
            if not resolved.exists():
                return FileSystemResult(
                    success=False, path=str(resolved), operation="read",
                    error=f"الملف غير موجود: {path}",
                )
            
            if not resolved.is_file():
                return FileSystemResult(
                    success=False, path=str(resolved), operation="read",
                    error=f"المسار ليس ملفاً: {path}",
                )
            
            size = resolved.stat().st_size
            if size > self.MAX_FILE_SIZE:
                return FileSystemResult(
                    success=False, path=str(resolved), operation="read",
                    error=f"الملف كبير جداً ({size} bytes > {self.MAX_FILE_SIZE} bytes)",
                )
            
            content = resolved.read_text(encoding='utf-8', errors='replace')
            
            self._log_operation("read", str(resolved), grant_id, size_bytes=size)
            
            return FileSystemResult(
                success=True,
                path=str(resolved),
                operation="read",
                content=content,
                size_bytes=size,
                timestamp=self._now(),
                grant_id=grant_id,
            )
        except PermissionError:
            return FileSystemResult(
                success=False, path=str(resolved), operation="read",
                error="صلاحيات النظام تمنع قراءة هذا الملف",
            )
        except Exception as e:
            return FileSystemResult(
                success=False, path=str(resolved), operation="read",
                error=str(e),
            )
    
    async def write_file(
        self,
        path: str,
        content: str,
        grant_id: str = "",
        task_context: str = "",
        create_dirs: bool = True,
    ) -> FileSystemResult:
        """
        كتابة ملف — يتطلب صلاحية filesystem:write.
        
        Args:
            path: مسار الملف
            content: المحتوى
            grant_id: معرف الصلاحية
            task_context: سياق المهمة
            create_dirs: إنشاء المجلدات إذا لم تكن موجودة
        
        Returns:
            FileSystemResult
        """
        await self.initialize()
        
        # Verify permission
        perm_check = await self._verify_permission(
            grant_id, "filesystem:write", ["write"], task_context
        )
        if not perm_check["valid"]:
            return FileSystemResult(
                success=False, path=path, operation="write",
                error=perm_check["reason"],
            )
        
        # Resolve and validate path
        resolved = self._resolve_path(path)
        validation = self._validate_path(resolved, "write")
        if not validation["valid"]:
            return FileSystemResult(
                success=False, path=str(resolved), operation="write",
                error=validation["reason"],
            )
        
        # Check protected files
        if resolved.name in PROTECTED_FILES:
            return FileSystemResult(
                success=False, path=str(resolved), operation="write",
                error=f"الملف محمي ولا يمكن تعديله: {resolved.name}",
            )
        
        # Write the file
        try:
            if create_dirs:
                resolved.parent.mkdir(parents=True, exist_ok=True)
            
            resolved.write_text(content, encoding='utf-8')
            size = resolved.stat().st_size
            
            self._log_operation("write", str(resolved), grant_id, size_bytes=size)
            
            return FileSystemResult(
                success=True,
                path=str(resolved),
                operation="write",
                size_bytes=size,
                timestamp=self._now(),
                grant_id=grant_id,
            )
        except PermissionError:
            return FileSystemResult(
                success=False, path=str(resolved), operation="write",
                error="صلاحيات النظام تمنع الكتابة في هذا المسار",
            )
        except Exception as e:
            return FileSystemResult(
                success=False, path=str(resolved), operation="write",
                error=str(e),
            )
    
    async def list_dir(self, path: str, grant_id: str = "", task_context: str = "") -> FileSystemResult:
        """
        عرض محتويات مجلد — يتطلب صلاحية filesystem:read.
        """
        await self.initialize()
        
        perm_check = await self._verify_permission(
            grant_id, "filesystem:read", ["read"], task_context
        )
        if not perm_check["valid"]:
            return FileSystemResult(
                success=False, path=path, operation="list",
                error=perm_check["reason"],
            )
        
        resolved = self._resolve_path(path)
        validation = self._validate_path(resolved, "read")
        if not validation["valid"]:
            return FileSystemResult(
                success=False, path=str(resolved), operation="list",
                error=validation["reason"],
            )
        
        try:
            if not resolved.exists():
                return FileSystemResult(
                    success=False, path=str(resolved), operation="list",
                    error=f"المجلد غير موجود: {path}",
                )
            
            entries = []
            for entry in sorted(resolved.iterdir()):
                if len(entries) >= self.MAX_LIST_ENTRIES:
                    break
                entries.append({
                    "name": entry.name,
                    "type": "dir" if entry.is_dir() else "file",
                    "size": entry.stat().st_size if entry.is_file() else 0,
                })
            
            self._log_operation("list", str(resolved), grant_id, size_bytes=len(entries))
            
            return FileSystemResult(
                success=True,
                path=str(resolved),
                operation="list",
                entries=entries,
                timestamp=self._now(),
                grant_id=grant_id,
            )
        except PermissionError:
            return FileSystemResult(
                success=False, path=str(resolved), operation="list",
                error="صلاحيات النظام تمنع عرض هذا المجلد",
            )
        except Exception as e:
            return FileSystemResult(
                success=False, path=str(resolved), operation="list",
                error=str(e),
            )
    
    async def delete_file(
        self,
        path: str,
        grant_id: str = "",
        task_context: str = "",
        confirm: bool = False,
    ) -> FileSystemResult:
        """
        حذف ملف — يتطلب صلاحية filesystem:delete + تأكيد.
        
        Args:
            path: مسار الملف
            grant_id: معرف الصلاحية
            task_context: سياق المهمة
            confirm: تأكيد الحذف (يجب أن يكون True)
        """
        await self.initialize()
        
        if not confirm:
            return FileSystemResult(
                success=False, path=path, operation="delete",
                error="تأكيد الحذف مطلوب — مرر confirm=True",
            )
        
        perm_check = await self._verify_permission(
            grant_id, "filesystem:delete", ["delete"], task_context
        )
        if not perm_check["valid"]:
            return FileSystemResult(
                success=False, path=path, operation="delete",
                error=perm_check["reason"],
            )
        
        resolved = self._resolve_path(path)
        validation = self._validate_path(resolved, "delete")
        if not validation["valid"]:
            return FileSystemResult(
                success=False, path=str(resolved), operation="delete",
                error=validation["reason"],
            )
        
        # Protected files
        if resolved.name in PROTECTED_FILES:
            return FileSystemResult(
                success=False, path=str(resolved), operation="delete",
                error=f"الملف محمي ولا يمكن حذفه: {resolved.name}",
            )
        
        try:
            if not resolved.exists():
                return FileSystemResult(
                    success=False, path=str(resolved), operation="delete",
                    error=f"الملف غير موجود: {path}",
                )
            
            size = resolved.stat().st_size
            resolved.unlink()
            
            self._log_operation("delete", str(resolved), grant_id, size_bytes=size)
            
            return FileSystemResult(
                success=True,
                path=str(resolved),
                operation="delete",
                size_bytes=size,
                timestamp=self._now(),
                grant_id=grant_id,
            )
        except Exception as e:
            return FileSystemResult(
                success=False, path=str(resolved), operation="delete",
                error=str(e),
            )
    
    async def copy_file(
        self,
        src: str,
        dst: str,
        grant_id: str = "",
        task_context: str = "",
    ) -> FileSystemResult:
        """نسخ ملف — يتطلب صلاحية filesystem:read + filesystem:write."""
        await self.initialize()
        
        perm_check = await self._verify_permission(
            grant_id, "filesystem:write", ["read", "write"], task_context
        )
        if not perm_check["valid"]:
            return FileSystemResult(
                success=False, path=src, operation="copy",
                error=perm_check["reason"],
            )
        
        src_resolved = self._resolve_path(src)
        dst_resolved = self._resolve_path(dst)
        
        # Validate both paths
        for r in [src_resolved, dst_resolved]:
            v = self._validate_path(r, "write")
            if not v["valid"]:
                return FileSystemResult(
                    success=False, path=str(r), operation="copy",
                    error=v["reason"],
                )
        
        try:
            dst_resolved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_resolved, dst_resolved)
            
            self._log_operation("copy", f"{src} -> {dst}", grant_id)
            
            return FileSystemResult(
                success=True,
                path=str(dst_resolved),
                operation="copy",
                timestamp=self._now(),
                grant_id=grant_id,
            )
        except Exception as e:
            return FileSystemResult(
                success=False, path=str(src_resolved), operation="copy",
                error=str(e),
            )
    
    def get_audit_log(self, limit: int = 100) -> list[dict]:
        """الحصول على سجل العمليات."""
        return self._audit_log[-limit:]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Internal Methods
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _resolve_path(self, path: str) -> Path:
        """حل المسار النسبي إلى مطلق داخل sandbox."""
        p = Path(path)
        if not p.is_absolute():
            p = self.sandbox_root / p
        return p.resolve()
    
    def _validate_path(self, resolved: Path, operation: str) -> dict:
        """
        التحقق من صحة المسار — داخل sandbox وخارج المسارات المحظورة.
        """
        # Must be inside sandbox root
        try:
            resolved.relative_to(self.sandbox_root)
        except ValueError:
            return {
                "valid": False,
                "reason": f"المسار خارج منطقة الحماية: {resolved} (الجذر: {self.sandbox_root})",
            }
        
        # Check forbidden patterns
        path_str = str(resolved)
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in path_str:
                return {
                    "valid": False,
                    "reason": f"مسار محظور: يحتوي على '{pattern}'",
                }
        
        return {"valid": True, "reason": ""}
    
    async def _verify_permission(
        self, grant_id: str, required_scope: str, required_perms: list[str], task_context: str
    ) -> dict:
        """
        التحقق من الصلاحية الزمنية.
        """
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
        
        # Verify scope matches
        grant_scope = check.get("scope", "")
        if grant_scope and grant_scope != required_scope:
            # Check if grant scope is broader
            grant_category = grant_scope.split(":")[0]
            required_category = required_scope.split(":")[0]
            if grant_category != required_category:
                return {
                    "valid": False,
                    "reason": f"نطاق الصلاحية لا يتطابق: لديك '{grant_scope}'، تحتاج '{required_scope}'",
                }
        
        return {"valid": True, "reason": "الصلاحية فعالة"}
    
    def _log_operation(self, operation: str, path: str, grant_id: str, size_bytes: int = 0):
        """تسجيل العملية."""
        entry = {
            "operation": operation,
            "path": path,
            "grant_id": grant_id,
            "size_bytes": size_bytes,
            "timestamp": self._now(),
        }
        self._audit_log.append(entry)
    
    @staticmethod
    def _now() -> float:
        import time
        return time.time()
