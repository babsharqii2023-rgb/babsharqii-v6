"""
BABSHARQII v17.0 — Code Self-Patcher
يقرأ ملفات Python باستخدام AST، يرسل الأخطاء + السياق إلى LLM لتوليد التصحيحات،
يطبّق التصحيحات المحققة، ويحافظ على نسخ احتياطية للتراجع.

Pipeline: Error → analyze_file(ast) → generate_patch(LLM) → validate_patch → apply_patch → verify → rollback_if_failed

v17.0: Uses LLMClient (GLM-5.1) instead of raw httpx calls
"""

import ast
import time
import json
import difflib
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

try:
    import black
    HAS_BLACK = True
except ImportError:
    HAS_BLACK = False


@dataclass
class CodePatch:
    """A code patch proposed by the self-healing system."""
    id: str = ""
    target_file: str = ""
    target_function: str = ""
    error_message: str = ""
    error_type: str = ""
    original_code: str = ""
    patched_code: str = ""
    diff: str = ""
    description: str = ""
    risk_level: str = "medium"  # low, medium, high
    status: str = "pending"  # pending, validated, applied, verified, failed, rolled_back
    llm_model: str = ""
    created_at: float = 0.0
    applied_at: float = 0.0
    verified_at: float = 0.0
    attempt: int = 1
    max_attempts: int = 3
    backup_path: str = ""
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "target_file": self.target_file,
            "target_function": self.target_function,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "description": self.description,
            "risk_level": self.risk_level,
            "status": self.status,
            "attempt": f"{self.attempt}/{self.max_attempts}",
            "created_at": self.created_at,
            "diff_preview": self.diff[:500] if self.diff else "",
        }


@dataclass
class FileAnalysis:
    """AST-based analysis of a Python file."""
    file_path: str = ""
    line_count: int = 0
    functions: list = field(default_factory=list)  # [{name, line, args, docstring}]
    classes: list = field(default_factory=list)  # [{name, line, methods}]
    imports: list = field(default_factory=list)  # [{module, names}]
    error_line: int = 0
    error_context: str = ""  # Lines around the error
    full_source: str = ""
    modifiable: bool = True


class CodePatcher:
    """
    Self-Healing Code Patcher for Python files.
    
    v17.0: Uses the unified LLMClient (GLM-5.1) for all LLM calls.
    
    Uses:
    - ast module to parse and understand Python code structure
    - black for code formatting after patches
    - LLMClient (GLM-5.1) for intelligent patch generation
    - Backup system for safe rollback
    """
    
    # Patterns that should NEVER appear in patches (safety)
    DANGEROUS_PATTERNS = [
        "os.system", "os.popen", "os.remove", "os.unlink",
        "subprocess.call", "subprocess.run", "subprocess.Popen",
        "exec(", "eval(", "__import__",
        "open('/etc", "open('/proc", "open('/sys",
        "shutil.rmtree", "shutil.copy", "shutil.move",
        "import ctypes", "import socket",
    ]
    
    # Files that can NEVER be modified
    IMMUTABLE_FILES = [
        "safety_guard.py",
        "approval_gate.py",
        "laws.yaml",
        "settings.yaml",
        "Dockerfile",
    ]
    
    def __init__(
        self,
        llm_client=None,
        llm_model: str = "glm-5.1",
        backup_dir: str = "",
        project_root: str = "",
    ):
        # v17.0: Use the unified LLMClient instead of raw httpx
        if llm_client is None:
            from mamoun.core.llm_client import get_llm_client
            llm_client = get_llm_client()
        self._llm = llm_client
        self.llm_model = llm_model
        self.backup_dir = backup_dir or str(Path(__file__).parent.parent.parent / "data" / "patches")
        self.project_root = project_root or str(Path(__file__).parent.parent.parent)
        self._patch_counter = 0
        self._applied_patches: list[CodePatch] = []
    
    # =========================================================================
    # Phase 1: File Analysis (AST)
    # =========================================================================
    
    def analyze_file(self, file_path: str, error_line: int = 0) -> FileAnalysis:
        """
        Analyze a Python file using AST to understand its structure.
        Returns function signatures, class definitions, imports, and error context.
        """
        analysis = FileAnalysis(file_path=file_path, error_line=error_line)
        
        # Check if modifiable
        for immutable in self.IMMUTABLE_FILES:
            if file_path.endswith(immutable):
                analysis.modifiable = False
                return analysis
        
        # Read source
        full_path = self._resolve_path(file_path)
        if not full_path or not full_path.exists():
            analysis.modifiable = False
            return analysis
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                source = f.read()
        except Exception as e:
            analysis.modifiable = False
            return analysis
        
        analysis.full_source = source
        analysis.line_count = source.count('\n') + 1
        
        # Parse AST
        try:
            tree = ast.parse(source)
        except SyntaxError:
            # File has syntax errors — can still try to patch
            return analysis
        
        # Extract functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                args = [arg.arg for arg in node.args.args]
                analysis.functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": args,
                    "docstring": ast.get_docstring(node) or "",
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                })
            elif isinstance(node, ast.ClassDef):
                methods = [
                    n.name for n in node.body 
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                analysis.classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": methods,
                })
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom):
                    names = [alias.name for alias in node.names]
                    analysis.imports.append({
                        "module": node.module or "",
                        "names": names,
                    })
                else:
                    for alias in node.names:
                        analysis.imports.append({
                            "module": alias.name,
                            "names": [],
                        })
        
        # Extract error context (lines around the error)
        if error_line > 0:
            lines = source.split('\n')
            start = max(0, error_line - 5)
            end = min(len(lines), error_line + 5)
            context_lines = lines[start:end]
            analysis.error_context = '\n'.join(
                f"{start + i + 1:>4} | {line}" 
                for i, line in enumerate(context_lines)
            )
        
        return analysis
    
    # =========================================================================
    # Phase 2: Patch Generation (LLM via LLMClient)
    # =========================================================================
    
    async def generate_patch(
        self,
        error_type: str,
        error_message: str,
        error_traceback: str,
        file_path: str,
        error_line: int = 0,
    ) -> Optional[CodePatch]:
        """
        Generate a code patch using LLM analysis.
        The LLM receives: error + AST analysis + context → returns a diff or patched code.
        """
        # Analyze the file
        analysis = self.analyze_file(file_path, error_line)
        
        if not analysis.modifiable:
            return None
        
        # Build the prompt for LLM
        prompt = self._build_patch_prompt(
            error_type, error_message, error_traceback, analysis
        )
        
        # Call LLM via the unified LLMClient
        try:
            llm_response = await self._call_llm(prompt)
        except Exception as e:
            # LLM failed — try heuristic fallback
            patched_code = self._heuristic_fallback(error_message, analysis)
            if not patched_code:
                return None
            llm_response = json.dumps({
                "patchedCode": patched_code,
                "description": "تصحيح دفاعي تلقائي (LLM غير متاح)",
                "riskLevel": "high",
            })
        
        # Parse LLM response
        patch_data = self._parse_llm_response(llm_response)
        if not patch_data:
            return None
        
        # Create the patch object
        self._patch_counter += 1
        patch = CodePatch(
            id=f"patch-{int(time.time())}-{self._patch_counter}",
            target_file=file_path,
            target_function=self._extract_function_from_traceback(error_traceback, analysis),
            error_message=error_message,
            error_type=error_type,
            original_code=analysis.full_source,
            patched_code=patch_data.get("patchedCode", ""),
            diff="",
            description=patch_data.get("description", ""),
            risk_level=patch_data.get("riskLevel", "medium"),
            llm_model=self.llm_model,
            created_at=time.time(),
        )
        
        # Generate unified diff
        if patch.original_code and patch.patched_code:
            patch.diff = self._generate_diff(patch.original_code, patch.patched_code, file_path)
        
        return patch
    
    def _build_patch_prompt(
        self,
        error_type: str,
        error_message: str,
        error_traceback: str,
        analysis: FileAnalysis,
    ) -> str:
        """Build the Arabic/English prompt for LLM patch generation."""
        functions_str = "\n".join(
            f"  - {f['name']}({', '.join(f['args'])}) [line {f['line']}]"
            for f in analysis.functions[:20]
        )
        
        return f"""أنت محرك إصلاح ذاتي في BABSHARQII v17.0 (مأمون). قم بإنشاء تصحيح للكود التالي.

نوع الخطأ: {error_type}
رسالة الخطأ: {error_message}

تتبع الخطأ:
```
{error_traceback[:2000]}
```

سياق الخطأ في الملف:
```
{analysis.error_context}
```

بنية الملف ({analysis.file_path}):
الدوال:
{functions_str}

الكود المصدري الكامل:
```python
{analysis.full_source[:6000]}
```

القواعد الصارمة:
1. لا تستخدم exec(), eval(), __import__, os.system, subprocess
2. لا تعدل استيرادات حساسة (os, subprocess, sys)
3. أضف معالجة أخطاء دفاعية
4. حافظ على نفس الواجهة (function signatures)
5. لا تحذف أي دوال موجودة
6. الكود يجب أن يكون Python صالح

أجب بصيغة JSON فقط:
{{
  "patchedCode": "الكود المصحح الكامل هنا",
  "description": "وصف ما يفعله التصحيح بالعربية",
  "riskLevel": "low" | "medium" | "high"
}}"""
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM via the unified LLMClient (GLM-5.1) for patch generation."""
        response = await self._llm.think(
            prompt=prompt,
            system="أنت محرك إصلاح ذاتي في BABSHARQII v17.0 (مأمون). تولّد تصحيحات كود Python آمنة.\nالقواعد الصارمة:\n1. لا تستخدم exec(), eval(), __import__, os.system, subprocess\n2. أضف معالجة أخطاء دفاعية\n3. حافظ على نفس الواجهة\n4. لا تحذف دوال موجودة\n5. أجب بصيغة JSON فقط",
            model=self.llm_model,
            temperature=0.3,
        )
        return response.text
    
    def _parse_llm_response(self, raw: str) -> Optional[dict]:
        """Extract JSON from LLM response."""
        import re
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if not json_match:
            return None
        
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            return None
    
    def _heuristic_fallback(self, error_message: str, analysis: FileAnalysis) -> Optional[str]:
        """Generate a simple defensive patch when LLM is unavailable."""
        if not analysis.full_source:
            return None
        
        # Common patterns: add try-catch, add null checks
        msg = error_message.lower()
        
        if "keyerror" in msg or "key" in msg:
            return analysis.full_source  # Return unchanged — real fix needs LLM
        
        if "attributeerror" in msg:
            return analysis.full_source
        
        if "typeerror" in msg or "nonetype" in msg:
            return analysis.full_source
        
        return None
    
    # =========================================================================
    # Phase 3: Validation
    # =========================================================================
    
    def validate_patch(self, patch: CodePatch) -> tuple[bool, list[str]]:
        """
        Validate a patch before applying it.
        Returns (is_valid, list_of_errors).
        """
        errors = []
        
        # Check modifiability
        for immutable in self.IMMUTABLE_FILES:
            if patch.target_file.endswith(immutable):
                errors.append(f"الملف {patch.target_file} محمي ولا يمكن تعديله")
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in patch.patched_code:
                errors.append(f"نمط خطير مكتشف: {pattern}")
        
        # Check syntax validity
        try:
            ast.parse(patch.patched_code)
        except SyntaxError as e:
            errors.append(f"خطأ بناء الجملة في الكود المصحح: {e}")
        
        # Check patch is not empty
        if not patch.patched_code.strip():
            errors.append("الكود المصحح فارغ")
        
        # Check patch actually changes something
        if patch.patched_code.strip() == patch.original_code.strip():
            errors.append("التصحيح لا يغير أي شيء")
        
        # Check that functions are preserved
        try:
            original_tree = ast.parse(patch.original_code)
            patched_tree = ast.parse(patch.patched_code)
            
            original_funcs = {
                n.name for n in ast.walk(original_tree) 
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            patched_funcs = {
                n.name for n in ast.walk(patched_tree) 
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            
            missing = original_funcs - patched_funcs
            if missing:
                errors.append(f"الدوال المفقودة في التصحيح: {', '.join(missing)}")
        except SyntaxError:
            pass  # Already caught above
        
        return len(errors) == 0, errors
    
    # =========================================================================
    # Phase 4: Application
    # =========================================================================
    
    async def apply_patch(self, patch: CodePatch) -> bool:
        """Apply a validated patch to the target file."""
        # Validate first
        is_valid, errors = self.validate_patch(patch)
        if not is_valid:
            patch.status = "failed"
            return False
        
        full_path = self._resolve_path(patch.target_file)
        if not full_path:
            patch.status = "failed"
            return False
        
        # Create backup
        backup_path = await self._create_backup(full_path)
        patch.backup_path = str(backup_path)
        
        # Format the patched code with black
        try:
            if HAS_BLACK:
                formatted = black.format_str(patch.patched_code, mode=black.Mode())
                patch.patched_code = formatted
        except Exception:
            pass  # Black formatting failed — use unformatted code
        
        # Write the patched file
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(patch.patched_code)
        except Exception as e:
            # Write failed — rollback
            await self._restore_backup(full_path, backup_path)
            patch.status = "failed"
            return False
        
        patch.status = "applied"
        patch.applied_at = time.time()
        self._applied_patches.append(patch)
        
        return True
    
    async def rollback_patch(self, patch: CodePatch) -> bool:
        """Rollback a patch by restoring the backup."""
        if not patch.backup_path:
            return False
        
        full_path = self._resolve_path(patch.target_file)
        if not full_path:
            return False
        
        backup_path = Path(patch.backup_path)
        if not backup_path.exists():
            if patch.original_code:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(patch.original_code)
                patch.status = "rolled_back"
                return True
            return False
        
        return await self._restore_backup(full_path, backup_path)
    
    # =========================================================================
    # Helpers
    # =========================================================================
    
    def _resolve_path(self, file_path: str) -> Optional[Path]:
        """Resolve a file path safely, preventing path traversal."""
        p = Path(file_path)
        if p.exists() and p.is_file() and p.suffix == '.py':
            try:
                p.resolve().relative_to(Path(self.project_root).resolve())
                return p
            except ValueError:
                return None
        
        p = Path(self.project_root) / file_path
        if p.exists() and p.is_file() and p.suffix == '.py':
            try:
                p.resolve().relative_to(Path(self.project_root).resolve())
                return p
            except ValueError:
                return None
        
        p = Path(self.project_root) / "mamoun" / file_path
        if p.exists() and p.is_file():
            try:
                p.resolve().relative_to(Path(self.project_root).resolve())
                return p
            except ValueError:
                return None
        
        return None
    
    async def _create_backup(self, file_path: Path) -> Path:
        """Create a timestamped backup of a file."""
        backup_dir = Path(self.backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = int(time.time())
        backup_name = f"{file_path.stem}_{timestamp}.bak"
        backup_path = backup_dir / backup_name
        
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    async def _restore_backup(self, file_path: Path, backup_path: Path) -> bool:
        """Restore a file from its backup."""
        try:
            shutil.copy2(backup_path, file_path)
            return True
        except Exception:
            return False
    
    def _generate_diff(self, original: str, patched: str, file_path: str) -> str:
        """Generate a unified diff between original and patched code."""
        original_lines = original.splitlines(keepends=True)
        patched_lines = patched.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines, patched_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )
        return ''.join(diff)
    
    def _extract_function_from_traceback(self, traceback_str: str, analysis: FileAnalysis) -> str:
        """Try to extract the function name from the error traceback."""
        import re
        match = re.search(r'in (\w+)', traceback_str)
        if match:
            return match.group(1)
        
        matches = re.findall(r'in (\w+)', traceback_str)
        if matches:
            return matches[-1]
        
        return ""
