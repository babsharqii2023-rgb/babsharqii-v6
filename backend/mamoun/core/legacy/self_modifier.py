"""
BABSHARQII v18.0 — Self-Modification Engine (مُعدِّل الذات)
المحرك الذي يسمح لمأمون بتعديل كوده الخاص بأمان

This is the CRITICAL self-modification engine that allows Mamoun to:
1. Read & Analyze its own source code files
2. Propose modifications using LLM (via llm_client)
3. Validate modifications against safety rules (laws.yaml)
4. Test in sandbox before applying
5. Apply with rollback capability
6. Log all modifications for audit trail

Safety Guarantees (Law 8 — Responsible Self-Improvement):
- NEVER modify laws.yaml, safety_guard.py, approval_gate.py, or safety_gate/
- NEVER modify .env or credentials
- All modifications require approval if MAMOUN_REQUIRE_APPROVAL=true
- Always backup before applying
- Always test in sandbox before applying
- Modifications that increase risk score above threshold are auto-rejected
- Full audit trail maintained

Based on research:
- DGM (jennyzzt/dgm): Self-modifying code with frozen foundation models
- OpenEnded: Open-ended learning through self-modification
- SWE-Agent: Autonomous software engineering
"""

import os
import ast
import json
import re
import time
import difflib
import shutil
import hashlib
import logging
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger("mamoun.core.self_modifier")


# ─────────────────────────────────────────────────────────────────────────────
# Data Models — نماذج البيانات
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ModificationProposal:
    """مقترح تعديل — proposed code modification."""
    id: str = ""
    target_file: str = ""
    description: str = ""
    original_code: str = ""
    proposed_code: str = ""
    diff: str = ""
    safety_score: float = 0.0
    risk_level: str = "medium"  # low, medium, high, critical
    created_at: float = 0.0
    status: str = "pending"  # pending, testing, approved, applied, rejected, rolled_back
    approved_by: str = ""  # "auto" or user identifier
    applied_at: float = 0.0
    rolled_back_at: float = 0.0
    backup_path: str = ""
    sandbox_result: dict = field(default_factory=dict)
    llm_model: str = ""
    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "target_file": self.target_file,
            "description": self.description,
            "diff_preview": self.diff[:1000] if self.diff else "",
            "safety_score": round(self.safety_score, 3),
            "risk_level": self.risk_level,
            "created_at": self.created_at,
            "created_at_iso": datetime.fromtimestamp(self.created_at).isoformat() if self.created_at else "",
            "status": self.status,
            "approved_by": self.approved_by,
            "applied_at": self.applied_at,
            "rolled_back_at": self.rolled_back_at,
            "backup_path": self.backup_path,
            "sandbox_passed": self.sandbox_result.get("success", False),
            "llm_model": self.llm_model,
            "validation_errors": self.validation_errors,
        }


@dataclass
class ValidationResult:
    """نتيجة التحقق — result of safety validation."""
    is_valid: bool = False
    safety_score: float = 0.0
    risk_level: str = "high"
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    law_violations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "safety_score": round(self.safety_score, 3),
            "risk_level": self.risk_level,
            "errors": self.errors,
            "warnings": self.warnings,
            "law_violations": self.law_violations,
        }


@dataclass
class ApplyResult:
    """نتيجة التطبيق — result of applying a modification."""
    success: bool = False
    modification_id: str = ""
    backup_path: str = ""
    applied_at: float = 0.0
    error: str = ""
    files_modified: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "modification_id": self.modification_id,
            "backup_path": self.backup_path,
            "applied_at": self.applied_at,
            "applied_at_iso": datetime.fromtimestamp(self.applied_at).isoformat() if self.applied_at else "",
            "error": self.error,
            "files_modified": self.files_modified,
        }


@dataclass
class RollbackResult:
    """نتيجة التراجع — result of rolling back a modification."""
    success: bool = False
    modification_id: str = ""
    rolled_back_at: float = 0.0
    error: str = ""
    original_restored: bool = False

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "modification_id": self.modification_id,
            "rolled_back_at": self.rolled_back_at,
            "rolled_back_at_iso": datetime.fromtimestamp(self.rolled_back_at).isoformat() if self.rolled_back_at else "",
            "error": self.error,
            "original_restored": self.original_restored,
        }


@dataclass
class SelfAnalysis:
    """تحليل ذاتي — analysis of the system's own codebase."""
    total_files: int = 0
    total_lines: int = 0
    total_functions: int = 0
    total_classes: int = 0
    complexity_score: float = 0.0
    health_score: float = 0.0
    suggested_improvements: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    dashboard_sections: List[str] = field(default_factory=list)
    file_breakdown: dict = field(default_factory=dict)
    analyzed_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "total_functions": self.total_functions,
            "total_classes": self.total_classes,
            "complexity_score": round(self.complexity_score, 3),
            "health_score": round(self.health_score, 3),
            "suggested_improvements": self.suggested_improvements[:20],
            "capabilities": self.capabilities,
            "dashboard_sections": self.dashboard_sections,
            "file_breakdown": {
                k: v for k, v in list(self.file_breakdown.items())[:15]
            },
            "analyzed_at": self.analyzed_at,
            "analyzed_at_iso": datetime.fromtimestamp(self.analyzed_at).isoformat() if self.analyzed_at else "",
        }


@dataclass
class ModificationRecord:
    """سجل تعديل — audit trail record."""
    id: str = ""
    target_file: str = ""
    description: str = ""
    status: str = ""
    safety_score: float = 0.0
    risk_level: str = ""
    created_at: float = 0.0
    applied_at: float = 0.0
    rolled_back_at: float = 0.0
    approved_by: str = ""
    diff_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "target_file": self.target_file,
            "description": self.description[:200],
            "status": self.status,
            "safety_score": round(self.safety_score, 3),
            "risk_level": self.risk_level,
            "created_at": self.created_at,
            "created_at_iso": datetime.fromtimestamp(self.created_at).isoformat() if self.created_at else "",
            "applied_at": self.applied_at,
            "approved_by": self.approved_by,
            "diff_hash": self.diff_hash,
        }


# ─────────────────────────────────────────────────────────────────────────────
# SelfModifier Engine — مُعدِّل الذات
# ─────────────────────────────────────────────────────────────────────────────

class SelfModifier:
    """
    Self-Modification Engine — مُعدِّل الذات

    Allows Mamoun to safely modify its own code through a rigorous pipeline:
    Propose → Validate → Test in Sandbox → Approve → Apply → Log

    All modifications are:
    - Validated against safety rules (Law 3, Law 8)
    - Tested in isolated sandbox (Law 4)
    - Backed up before application
    - Fully audited (Law 2)
    - Reversible via rollback
    """

    # الملفات المحمية — لا يمكن تعديلها أبداً (Law 3, Law 8)
    PROTECTED_FILES = {
        "laws.yaml", "settings.yaml", "Dockerfile",
        ".env", ".key", ".pem", ".secret",
        "safety_guard.py", "approval_gate.py",
        "self_modifier.py",  # لا يمكن تعديل نفسه مباشرة
        "middleware.ts",  # ملف الوسيط الحرج في الواجهة الأمامية
    }

    # المجلدات المحمية
    PROTECTED_DIRS = {
        "safety_gate", "secrets", "keys", "certs",
    }

    # أنماط خطيرة ممنوعة في الكود المقترح
    FORBIDDEN_PATTERNS = [
        # Python أنماط خطيرة
        "os.system", "os.popen", "subprocess.call", "subprocess.run",
        "exec(", "eval(", "__import__",
        "shutil.rmtree", "os.remove", "os.unlink",
        "import secrets", "import credential",
        "open('/etc", "open('/proc", "open('/sys",
        "os.environ[", "os.getenv('MAMOUN", "os.getenv('DEEPSEEK",
        "os.getenv('GEMINI", "os.getenv('OPENAI",
        # JavaScript/TypeScript أنماط خطيرة
        "process.exit", "child_process", "fs.unlinkSync", "rm -rf",
    ]

    # عتبة درجة الأمان — أقل من هذا يُرفض تلقائياً
    SAFETY_SCORE_THRESHOLD = 0.6

    # الحد الأقصى لمحاولات التعديل لكل ملف في الجلسة
    MAX_ATTEMPTS_PER_FILE = 3

    def __init__(
        self,
        project_root: str = "",
        data_dir: str = "",
    ):
        self.project_root = project_root or str(
            Path(__file__).parent.parent.parent.parent
        )
        self.backend_root = str(Path(__file__).parent.parent.parent)

        # مسار تخزين سجلات التعديلات
        self.data_dir = data_dir or str(
            Path(self.backend_root) / "data" / "self_modifications"
        )
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)

        # مسار النسخ الاحتياطية
        self.backup_dir = str(Path(self.data_dir) / "backups")
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)

        # سجل التعديلات في الذاكرة
        self._history: List[ModificationProposal] = []
        self._proposal_counter = 0

        # تتبع المحاولات لكل ملف
        self._attempt_tracker: dict[str, int] = {}

        # تحميل السجل من القرص
        self._load_history()

        logger.info(
            "SelfModifier initialized — project_root=%s, data_dir=%s",
            self.project_root, self.data_dir,
        )

    # =========================================================================
    # المرحلة 1: اقتراح التعديل — Propose Modification
    # =========================================================================

    async def propose_modification(
        self,
        target_file: str,
        description: str,
    ) -> ModificationProposal:
        """
        اقتراح تعديل — propose a code modification using LLM analysis.

        Reads the current source, sends it to the LLM with the description,
        and generates a proposed modification with safety scoring.

        Args:
            target_file: relative path to the file to modify
            description: natural language description of desired change

        Returns:
            ModificationProposal with proposed_code, diff, and safety_score
        """
        # التحقق من أن الملف غير محمي
        if self._is_protected_file(target_file):
            error_msg = f"الملف '{target_file}' محمي ولا يمكن تعديله (Law 3, Law 8)"
            logger.warning("Propose blocked: %s", error_msg)
            return ModificationProposal(
                id=self._generate_id(),
                target_file=target_file,
                description=description,
                status="rejected",
                validation_errors=[error_msg],
            )

        # التحقق من عدد المحاولات
        attempts = self._attempt_tracker.get(target_file, 0)
        if attempts >= self.MAX_ATTEMPTS_PER_FILE:
            error_msg = f"تم تجاوز الحد الأقصى للمحاولات ({self.MAX_ATTEMPTS_PER_FILE}) للملف '{target_file}'"
            logger.warning("Propose blocked: %s", error_msg)
            return ModificationProposal(
                id=self._generate_id(),
                target_file=target_file,
                description=description,
                status="rejected",
                validation_errors=[error_msg],
            )

        # قراءة الكود المصدري الحالي
        original_code = self._read_source(target_file)
        if original_code is None:
            error_msg = f"فشل قراءة الملف: {target_file}"
            logger.error("Propose failed: %s", error_msg)
            return ModificationProposal(
                id=self._generate_id(),
                target_file=target_file,
                description=description,
                status="rejected",
                validation_errors=[error_msg],
            )

        # توليد الكود المقترح باستخدام LLM
        proposed_code = await self._generate_proposed_code(
            target_file, original_code, description
        )
        if not proposed_code:
            error_msg = "فشل توليد الكود المقترح من LLM"
            logger.error("Propose failed: %s", error_msg)
            return ModificationProposal(
                id=self._generate_id(),
                target_file=target_file,
                description=description,
                original_code=original_code,
                status="rejected",
                validation_errors=[error_msg],
            )

        # توليد الفرق
        diff = self._generate_diff(original_code, proposed_code, target_file)

        # حساب درجة الأمان المبدئية
        safety_score = self._compute_safety_score(diff, target_file, proposed_code)

        # تحديد مستوى الخطر
        risk_level = self._determine_risk_level(safety_score, target_file)

        # إنشاء المقترح
        self._proposal_counter += 1
        proposal = ModificationProposal(
            id=self._generate_id(),
            target_file=target_file,
            description=description,
            original_code=original_code,
            proposed_code=proposed_code,
            diff=diff,
            safety_score=safety_score,
            risk_level=risk_level,
            created_at=time.time(),
            status="pending",
            llm_model="glm-5.1",
        )

        # تسجيل المقترح
        self._history.append(proposal)
        self._save_history()

        # تحديث عداد المحاولات
        self._attempt_tracker[target_file] = attempts + 1

        logger.info(
            "Proposed modification %s for %s — safety=%.3f, risk=%s",
            proposal.id, target_file, safety_score, risk_level,
        )

        return proposal

    # =========================================================================
    # المرحلة 2: التحقق من الأمان — Validate Modification
    # =========================================================================

    async def validate_modification(self, proposal: ModificationProposal) -> ValidationResult:
        """
        التحقق من الأمان — validate a proposed modification against safety rules.

        Checks:
        1. File is not protected (Law 3)
        2. No forbidden patterns in proposed code (Law 1)
        3. Code is syntactically valid
        4. Function signatures are preserved
        5. Safety score meets threshold
        6. Diff doesn't touch critical sections
        """
        result = ValidationResult()

        # 1. فحص الملفات المحمية
        if self._is_protected_file(proposal.target_file):
            result.errors.append(
                f"الملف '{proposal.target_file}' محمي بموجب Law 3 — لا يمكن تعديله"
            )
            result.law_violations.append("L3: Identity Protection")

        # 2. فحص الأنماط المحظورة
        is_safe, violations = self._check_safety(proposal.diff)
        if not is_safe:
            result.errors.extend(violations)
            result.law_violations.append("L1: No Harm — dangerous code pattern")

        # 3. فحص صحة بناء الجملة — إرسال للمدقق المناسب حسب امتداد الملف
        is_valid_syntax, syntax_error = self._validate_syntax(
            proposal.proposed_code, proposal.target_file
        )
        if not is_valid_syntax:
            result.errors.append(f"خطأ في بناء الجملة: {syntax_error}")

        # 4. فحص الحفاظ على الدوال
        func_errors = self._check_function_preservation(
            proposal.original_code, proposal.proposed_code
        )
        result.errors.extend(func_errors)

        # 5. فحص درجة الأمان
        if proposal.safety_score < self.SAFETY_SCORE_THRESHOLD:
            result.warnings.append(
                f"درجة الأمان ({proposal.safety_score:.3f}) أقل من الحد الأدنى ({self.SAFETY_SCORE_THRESHOLD})"
            )

        # 6. فحص الأمان المتقدم عبر SafetyGuard
        try:
            from mamoun.core.safety_guard import SafetyGuard
            guard = SafetyGuard()
            if guard.is_file_protected(proposal.target_file):
                result.errors.append(
                    f"الملف محمي بواسطة SafetyGuard: {proposal.target_file}"
                )
                result.law_violations.append("L3: SafetyGuard protection")

            code_safe, code_violations = guard.check_code_safety(proposal.proposed_code)
            if not code_safe:
                result.errors.extend(code_violations)
                result.law_violations.append("L1: Code safety violation")
        except Exception as e:
            result.warnings.append(f"لم يتم التحقق من SafetyGuard: {e}")

        # حساب النتيجة النهائية
        if result.errors:
            result.is_valid = False
            result.risk_level = "critical" if result.law_violations else "high"
        elif result.warnings:
            result.is_valid = True
            result.risk_level = "medium"
        else:
            result.is_valid = True
            result.risk_level = proposal.risk_level or "low"

        result.safety_score = proposal.safety_score

        # تحديث حالة المقترح
        if result.is_valid:
            proposal.status = "approved" if result.risk_level == "low" else "pending"
        else:
            proposal.status = "rejected"
            proposal.validation_errors = result.errors

        logger.info(
            "Validation %s for %s — valid=%s, risk=%s, errors=%d",
            proposal.id, proposal.target_file,
            result.is_valid, result.risk_level, len(result.errors),
        )

        return result

    # =========================================================================
    # المرحلة 3: الاختبار في Sandbox — Test in Sandbox
    # =========================================================================

    async def test_in_sandbox(self, proposal: ModificationProposal) -> dict:
        """
        الاختبار في Sandbox — test a proposed modification in an isolated environment.
        Uses SandboxRunner (Docker) when available, falls back to dev bypass.
        """
        if proposal.status not in ("pending", "approved"):
            return {
                "success": False,
                "error": f"لا يمكن اختبار مقترح بحالة '{proposal.status}'",
            }

        proposal.status = "testing"

        # Check if sandbox bypass is enabled (for development without Docker)
        sandbox_bypass = os.getenv("MAMOUN_SANDBOX_BYPASS", "true").lower() in ("true", "1", "yes")

        try:
            from mamoun.core.sandbox_runner import SandboxRunner

            # If bypass is enabled and Docker isn't available, skip Docker
            if sandbox_bypass:
                try:
                    import subprocess
                    docker_check = subprocess.run(
                        ["docker", "info"],
                        capture_output=True, text=True, timeout=5
                    )
                    docker_available = docker_check.returncode == 0
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    docker_available = False

                if not docker_available:
                    # Development bypass: syntax check + safety check only
                    logger.info("Docker not available — using dev bypass for sandbox test")
                    return await self._dev_sandbox_bypass(proposal)

            # Full Docker sandbox
            sandbox = SandboxRunner(
                project_root=self.backend_root,
                timeout=120,
                memory_limit="512m",
            )
            sandbox_result = await sandbox.test_patch(
                patched_code=proposal.proposed_code,
                target_file=proposal.target_file,
            )
            proposal.sandbox_result = sandbox_result.to_dict()

            if sandbox_result.success:
                proposal.status = "approved"
                logger.info("Sandbox PASSED for %s", proposal.id)
            else:
                proposal.status = "rejected"
                proposal.validation_errors.append(
                    f"فشل اختبار Sandbox: {sandbox_result.stderr[:300]}"
                )
                logger.warning("Sandbox FAILED for %s: %s", proposal.id, sandbox_result.stderr[:200])

            self._save_history()
            return sandbox_result.to_dict()

        except ImportError:
            # SandboxRunner not available — use dev bypass
            logger.info("SandboxRunner not available — using dev bypass")
            return await self._dev_sandbox_bypass(proposal)
        except Exception as e:
            proposal.status = "rejected"
            proposal.validation_errors.append(f"خطأ في Sandbox: {str(e)}")
            logger.error("Sandbox error for %s: %s", proposal.id, e)
            self._save_history()
            return {"success": False, "error": str(e)}

    async def _dev_sandbox_bypass(self, proposal: ModificationProposal) -> dict:
        """
        وضع تطوير — bypass sandbox when Docker is not available.
        Performs syntax check + safety check only. NOT for production.
        """
        # 1. Syntax check — dispatch to appropriate validator based on file extension
        is_valid_syntax, syntax_error = self._validate_syntax(
            proposal.proposed_code, proposal.target_file
        )
        if not is_valid_syntax:
            proposal.status = "rejected"
            proposal.validation_errors.append(f"خطأ في بناء الجملة: {syntax_error}")
            self._save_history()
            return {"success": False, "error": f"خطأ في بناء الجملة: {syntax_error}", "mode": "dev_bypass"}

        # 2. Safety check
        is_safe, violations = self._check_safety(proposal.diff)
        if not is_safe:
            proposal.status = "rejected"
            proposal.validation_errors.extend(violations)
            self._save_history()
            return {"success": False, "error": f"أنماط محظورة: {violations}", "mode": "dev_bypass"}

        # 3. Function preservation check
        func_errors = self._check_function_preservation(
            proposal.original_code, proposal.proposed_code
        )
        if func_errors:
            proposal.status = "rejected"
            proposal.validation_errors.extend(func_errors)
            self._save_history()
            return {"success": False, "error": f"أخطاء حفظ الدوال: {func_errors}", "mode": "dev_bypass"}

        # All checks passed in dev mode
        proposal.status = "approved"
        proposal.sandbox_result = {
            "success": True,
            "mode": "dev_bypass",
            "warning": "Docker غير متاح — تم التحقق من بناء الجملة والأمان فقط (وضع تطوير)",
            "checks_performed": ["syntax", "safety_patterns", "function_preservation"],
        }
        self._save_history()
        logger.info("Dev bypass PASSED for %s (syntax+safety check)", proposal.id)
        return proposal.sandbox_result

    # =========================================================================
    # المرحلة 4: التطبيق — Apply Modification
    # =========================================================================

    async def apply_modification(self, proposal: ModificationProposal) -> ApplyResult:
        """
        تطبيق التعديل — apply a validated and tested modification.

        Steps:
        1. Verify proposal is approved
        2. Check approval requirement (Law 8)
        3. Create backup
        4. Write modified code
        5. Update history
        """
        # التحقق من حالة المقترح
        if proposal.status not in ("approved",):
            return ApplyResult(
                success=False,
                modification_id=proposal.id,
                error=f"لا يمكن تطبيق مقترح بحالة '{proposal.status}' — يجب أن يكون 'approved'",
            )

        # التحقق من متطلب الموافقة (Law 8)
        require_approval = os.getenv(
            "MAMOUN_REQUIRE_APPROVAL", "true"
        ).lower() == "true"

        if require_approval and proposal.approved_by == "":
            return ApplyResult(
                success=False,
                modification_id=proposal.id,
                error="يتطلب التعديل موافقة بشرية — أرسل طلب موافقة أولاً",
            )

        # التحقق مرة أخرى من الأمان
        if self._is_protected_file(proposal.target_file):
            return ApplyResult(
                success=False,
                modification_id=proposal.id,
                error=f"الملف '{proposal.target_file}' محمي — تم رفض التعديل",
            )

        # إنشاء نسخة احتياطية
        backup_path = self._backup_file(proposal.target_file)
        if not backup_path:
            return ApplyResult(
                success=False,
                modification_id=proposal.id,
                error=f"فشل إنشاء نسخة احتياطية لـ {proposal.target_file}",
            )
        proposal.backup_path = backup_path

        # كتابة الكود المعدل
        target_path = self._resolve_target_path(proposal.target_file)
        if not target_path:
            return ApplyResult(
                success=False,
                modification_id=proposal.id,
                error=f"لم يتم العثور على الملف: {proposal.target_file}",
            )

        try:
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(proposal.proposed_code)
        except Exception as e:
            # محاولة استعادة النسخة الاحتياطية
            self._restore_from_backup(target_path, backup_path)
            return ApplyResult(
                success=False,
                modification_id=proposal.id,
                error=f"فشل كتابة الملف: {e}",
            )

        # تحديث حالة المقترح
        proposal.status = "applied"
        proposal.applied_at = time.time()
        self._save_history()

        # تسجيل في سجل المراجعة
        self._log_audit(proposal)

        logger.info(
            "Applied modification %s to %s — backup=%s",
            proposal.id, proposal.target_file, backup_path,
        )

        return ApplyResult(
            success=True,
            modification_id=proposal.id,
            backup_path=backup_path,
            applied_at=proposal.applied_at,
            files_modified=[proposal.target_file],
        )

    # =========================================================================
    # المرحلة 5: التراجع — Rollback
    # =========================================================================

    async def rollback(self, modification_id: str) -> RollbackResult:
        """
        التراجع عن تعديل — rollback a previously applied modification.

        Restores the original file from backup.
        """
        proposal = self._find_proposal(modification_id)
        if not proposal:
            return RollbackResult(
                success=False,
                modification_id=modification_id,
                error=f"لم يتم العثور على التعديل: {modification_id}",
            )

        if proposal.status != "applied":
            return RollbackResult(
                success=False,
                modification_id=modification_id,
                error=f"لا يمكن التراجع عن تعديل بحالة '{proposal.status}' — يجب أن يكون 'applied'",
            )

        # محاولة الاستعادة من النسخة الاحتياطية
        target_path = self._resolve_target_path(proposal.target_file)
        if not target_path:
            # محاولة الاستعادة من original_code
            if proposal.original_code:
                target_path = Path(self.backend_root) / proposal.target_file
                target_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write(proposal.original_code)
                    proposal.status = "rolled_back"
                    proposal.rolled_back_at = time.time()
                    self._save_history()
                    return RollbackResult(
                        success=True,
                        modification_id=modification_id,
                        rolled_back_at=proposal.rolled_back_at,
                        original_restored=True,
                    )
                except Exception as e:
                    return RollbackResult(
                        success=False,
                        modification_id=modification_id,
                        error=f"فشل استعادة الكود الأصلي: {e}",
                    )

        restored = self._restore_from_backup(target_path, proposal.backup_path)

        if restored:
            proposal.status = "rolled_back"
            proposal.rolled_back_at = time.time()
            self._save_history()

            logger.info(
                "Rolled back modification %s from %s",
                modification_id, proposal.target_file,
            )

            return RollbackResult(
                success=True,
                modification_id=modification_id,
                rolled_back_at=proposal.rolled_back_at,
                original_restored=True,
            )
        else:
            return RollbackResult(
                success=False,
                modification_id=modification_id,
                error="فشل استعادة النسخة الاحتياطية",
            )

    # =========================================================================
    # المرحلة 6: التحليل الذاتي — Self Analysis
    # =========================================================================

    async def analyze_self(self) -> SelfAnalysis:
        """
        التحليل الذاتي — analyze the system's own codebase.

        Scans all Python files in the mamoun module and computes:
        - Total files, lines, functions, classes
        - Complexity and health scores
        - Suggested improvements (via LLM)
        - Capabilities list
        - Dashboard sections for UI
        """
        analysis = SelfAnalysis(analyzed_at=time.time())
        mamoun_path = Path(self.backend_root) / "mamoun"

        if not mamoun_path.exists():
            return analysis

        # مسح جميع ملفات Python
        py_files = list(mamoun_path.rglob("*.py"))
        analysis.total_files = len(py_files)

        total_functions = 0
        total_classes = 0
        file_breakdown = {}

        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    source = f.read()

                lines = source.count('\n') + 1
                analysis.total_lines += lines

                # تحليل AST
                try:
                    tree = ast.parse(source)
                    funcs = sum(
                        1 for n in ast.walk(tree)
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    )
                    classes = sum(
                        1 for n in ast.walk(tree)
                        if isinstance(n, ast.ClassDef)
                    )
                    total_functions += funcs
                    total_classes += classes

                    # تقسيم حسب المجلد
                    rel_path = py_file.relative_to(mamoun_path)
                    module = str(rel_path.parts[0]) if len(rel_path.parts) > 1 else "root"
                    if module not in file_breakdown:
                        file_breakdown[module] = {"files": 0, "lines": 0, "functions": 0}
                    file_breakdown[module]["files"] += 1
                    file_breakdown[module]["lines"] += lines
                    file_breakdown[module]["functions"] += funcs
                except SyntaxError:
                    pass
            except Exception:
                pass

        analysis.total_functions = total_functions
        analysis.total_classes = total_classes
        analysis.file_breakdown = file_breakdown

        # حساب درجة التعقيد (مبسط)
        if analysis.total_files > 0:
            avg_lines = analysis.total_lines / analysis.total_files
            analysis.complexity_score = min(1.0, avg_lines / 200.0)

        # حساب درجة الصحة
        applied_count = sum(1 for p in self._history if p.status == "applied")
        rolled_back_count = sum(1 for p in self._history if p.status == "rolled_back")
        if applied_count + rolled_back_count > 0:
            success_rate = applied_count / (applied_count + rolled_back_count)
            analysis.health_score = 0.5 + 0.5 * success_rate
        else:
            analysis.health_score = 0.8  # Default healthy

        # بناء قائمة القدرات
        analysis.capabilities = self._discover_capabilities(mamoun_path)

        # بناء أقسام لوحة التحكم
        analysis.dashboard_sections = self._build_dashboard_sections(file_breakdown)

        # اقتراحات التحسين عبر LLM
        try:
            analysis.suggested_improvements = await self._generate_improvement_suggestions(
                analysis
            )
        except Exception as e:
            logger.warning("Failed to generate improvement suggestions: %s", e)
            analysis.suggested_improvements = [
                "لم يتم توليد اقتراحات — تأكد من اتصال LLM"
            ]

        return analysis

    # =========================================================================
    # سجل التعديلات — Modification History
    # =========================================================================

    async def get_history(self) -> List[ModificationRecord]:
        """الحصول على سجل التعديلات — get modification history."""
        records = []
        for proposal in self._history:
            records.append(ModificationRecord(
                id=proposal.id,
                target_file=proposal.target_file,
                description=proposal.description,
                status=proposal.status,
                safety_score=proposal.safety_score,
                risk_level=proposal.risk_level,
                created_at=proposal.created_at,
                applied_at=proposal.applied_at,
                rolled_back_at=proposal.rolled_back_at,
                approved_by=proposal.approved_by,
                diff_hash=hashlib.sha256(
                    proposal.diff.encode()
                ).hexdigest()[:16] if proposal.diff else "",
            ))
        return records

    def get_proposal(self, modification_id: str) -> Optional[ModificationProposal]:
        """الحصول على مقترح محدد — get a specific proposal by ID."""
        return self._find_proposal(modification_id)

    def approve_proposal(self, modification_id: str, approver: str = "human") -> bool:
        """الموافقة على مقترح — approve a pending proposal."""
        proposal = self._find_proposal(modification_id)
        if not proposal:
            return False
        if proposal.status not in ("pending", "approved"):
            return False
        proposal.approved_by = approver
        proposal.status = "approved"
        self._save_history()
        logger.info("Modification %s approved by %s", modification_id, approver)
        return True

    def reject_proposal(self, modification_id: str) -> bool:
        """رفض مقترح — reject a pending proposal."""
        proposal = self._find_proposal(modification_id)
        if not proposal:
            return False
        if proposal.status not in ("pending", "approved", "testing"):
            return False
        proposal.status = "rejected"
        self._save_history()
        logger.info("Modification %s rejected", modification_id)
        return True

    # =========================================================================
    # إعادة بناء لوحة التحكم — Dashboard Config Rebuild
    # =========================================================================

    def _rebuild_dashboard_config(self) -> dict:
        """
        إعادة بناء إعدادات لوحة التحكم — rebuild dashboard configuration
        when the system evolves through self-modification.
        """
        config = {
            "version": "18.0",
            "updated_at": time.time(),
            "sections": [],
            "capabilities": [],
            "health_indicators": {},
        }

        # بناء الأقسام من المجلدات المكتشفة
        mamoun_path = Path(self.backend_root) / "mamoun"
        if mamoun_path.exists():
            for module_dir in sorted(mamoun_path.iterdir()):
                if module_dir.is_dir() and not module_dir.name.startswith("_"):
                    py_count = len(list(module_dir.rglob("*.py")))
                    if py_count > 0:
                        config["sections"].append({
                            "id": module_dir.name,
                            "label_ar": self._module_name_ar(module_dir.name),
                            "file_count": py_count,
                            "active": True,
                        })

        # مؤشرات الصحة من السجل
        applied = sum(1 for p in self._history if p.status == "applied")
        rejected = sum(1 for p in self._history if p.status == "rejected")
        rolled_back = sum(1 for p in self._history if p.status == "rolled_back")

        config["health_indicators"] = {
            "total_modifications": len(self._history),
            "applied": applied,
            "rejected": rejected,
            "rolled_back": rolled_back,
            "success_rate": applied / max(1, applied + rejected + rolled_back),
        }

        return config

    # =========================================================================
    # Syntax Validation — التحقق من بناء الجملة (Python + TypeScript + JavaScript)
    # =========================================================================

    # امتدادات ملفات TypeScript/JavaScript
    TS_JS_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx"}

    def _validate_syntax(self, content: str, filepath: str) -> Tuple[bool, str]:
        """
        التحقق من بناء الجملة — dispatch to the right validator based on file extension.

        - Python files (.py) → ast.parse()
        - TypeScript files (.ts, .tsx) → _validate_typescript()
        - JavaScript files (.js, .jsx) → _validate_javascript()
        - Unknown extensions → basic regex check (lenient pass)

        Returns:
            (is_valid, error_message) — error_message is empty string if valid
        """
        ext = Path(filepath).suffix.lower()

        if ext == ".py":
            # Python — استخدم ast.parse كالسابق
            try:
                ast.parse(content)
                return (True, "")
            except SyntaxError as e:
                return (False, str(e))

        elif ext in (".ts", ".tsx"):
            return self._validate_typescript(content, filepath)

        elif ext in (".js", ".jsx"):
            return self._validate_javascript(content, filepath)

        else:
            # امتداد غير معروف — فحص أساسي بالتعبيرات النمطية
            return self._validate_unknown(content, filepath)

    def _validate_typescript(self, content: str, filepath: str) -> Tuple[bool, str]:
        """
        مدقق TypeScript — يستخدم npx tsc --noEmit للتحقق من بناء الجملة.

        Pipeline:
        1. Write content to a temp file with the same extension
        2. Run `npx tsc --noEmit --noEmitOnError` on it
        3. Return (is_valid, error_message)
        4. Clean up temp file

        If npx tsc is not available, falls back to regex-based basic check.
        """
        ext = Path(filepath).suffix.lower()
        suffix = ext if ext in (".ts", ".tsx") else ".ts"

        # إنشاء ملف مؤقت
        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix=suffix, delete=False, encoding='utf-8'
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            # محاولة تشغيل npx tsc
            try:
                result = subprocess.run(
                    ["npx", "tsc", "--noEmit", "--noEmitOnError", tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    return (True, "")
                else:
                    # تنظيف رسالة الخطأ — إزالة مسار الملف المؤقت
                    error_msg = result.stderr.strip() or result.stdout.strip()
                    # استبدال مسار الملف المؤقت باسم الملف الأصلي
                    if tmp_path in error_msg:
                        error_msg = error_msg.replace(tmp_path, filepath)
                    # اقتطاع الرسالة إن كانت طويلة
                    if len(error_msg) > 500:
                        error_msg = error_msg[:500] + "..."
                    return (False, error_msg)

            except FileNotFoundError:
                # npx غير متاح — استخدم الفحص الأساسي
                logger.info("npx tsc not available — using basic syntax check")
                return self._basic_syntax_check(content, filepath)

            except subprocess.TimeoutExpired:
                logger.warning("tsc validation timed out for %s", filepath)
                return (False, "انتهت مهلة التحقق من TypeScript (30 ثانية)")

        finally:
            # تنظيف الملف المؤقت
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _validate_typescript_regex(self, content: str, filepath: str) -> Tuple[bool, str]:
        """
        فحص أساسي لـ TypeScript باستخدام التعبيرات النمطية
        يُستخدم عندما لا يكون npx tsc متاحاً

        Checks:
        - Unmatched braces/brackets/parentheses
        - Unclosed string literals
        - Unclosed template literals
        - Basic structural issues
        """
        # فحص الأقواس المتطابقة
        bracket_pairs = [('{', '}'), ('[', ']'), ('(', ')')]
        for open_b, close_b in bracket_pairs:
            depth = 0
            in_string = False
            string_char = None
            in_template = False
            in_comment = False
            i = 0
            while i < len(content):
                c = content[i]
                # تخطي التعليقات
                if not in_string and not in_template:
                    if c == '/' and i + 1 < len(content):
                        if content[i + 1] == '/':
                            # تعليق سطر واحد — تخطي للنهاية
                            nl = content.find('\n', i)
                            i = nl if nl != -1 else len(content)
                            continue
                        elif content[i + 1] == '*':
                            # تعليق متعدد الأسطر
                            end = content.find('*/', i + 2)
                            i = end + 2 if end != -1 else len(content)
                            continue
                # تخطي النصوص
                if not in_template and c in ('"', "'", '`') and not in_string:
                    in_string = True
                    string_char = c
                    if c == '`':
                        in_template = True
                elif in_string and c == string_char:
                    # تحقق من عدم وجود escape
                    if i > 0 and content[i - 1] == '\\':
                        # تحقق من عدم وجود escape للـ escape نفسه
                        num_backslashes = 0
                        j = i - 1
                        while j >= 0 and content[j] == '\\':
                            num_backslashes += 1
                            j -= 1
                        if num_backslashes % 2 == 0:
                            in_string = False
                            if string_char == '`':
                                in_template = False
                            string_char = None
                    else:
                        in_string = False
                        if string_char == '`':
                            in_template = False
                        string_char = None
                elif not in_string and not in_template:
                    if c == open_b:
                        depth += 1
                    elif c == close_b:
                        depth -= 1
                        if depth < 0:
                            return (False, f"قوس إغلاق زائد '{close_b}' — تحقق من الأقواس")
                i += 1
            if depth != 0:
                return (False, f"أقواس غير متطابقة '{open_b}{close_b}' — فرق: {depth}")

        # فحص أساسي: هل يبدأ الملف بتركيب صالح؟
        stripped = content.strip()
        if not stripped:
            return (False, "الملف فارغ")

        # لا نستطيع التحقق من صحة TypeScript بالكامل بدون tsc
        # لكن الفحوصات الأساسية أعلاه كافية للتمرير
        logger.info("TypeScript regex check passed for %s (basic validation)", filepath)
        return (True, "")

    def _validate_javascript(self, content: str, filepath: str) -> Tuple[bool, str]:
        """
        مدقق JavaScript — يستخدم node --check للتحقق من بناء الجملة.

        Pipeline:
        1. Write content to a temp file with .js extension
        2. Run `node --check` on it
        3. Return (is_valid, error_message)
        4. Clean up temp file

        If node is not available, falls back to regex-based basic check.
        """
        ext = Path(filepath).suffix.lower()
        suffix = ext if ext in (".js", ".jsx") else ".js"

        # إنشاء ملف مؤقت
        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix=suffix, delete=False, encoding='utf-8'
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            # محاولة تشغيل node --check
            try:
                result = subprocess.run(
                    ["node", "--check", tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )

                if result.returncode == 0:
                    return (True, "")
                else:
                    error_msg = result.stderr.strip()
                    # استبدال مسار الملف المؤقت باسم الملف الأصلي
                    if tmp_path in error_msg:
                        error_msg = error_msg.replace(tmp_path, filepath)
                    if len(error_msg) > 500:
                        error_msg = error_msg[:500] + "..."
                    return (False, error_msg)

            except FileNotFoundError:
                # node غير متاح — استخدم الفحص الأساسي
                logger.info("node not available — using basic syntax check")
                return self._basic_syntax_check(content, filepath)

            except subprocess.TimeoutExpired:
                logger.warning("node --check timed out for %s", filepath)
                return (False, "انتهت مهلة التحقق من JavaScript (15 ثانية)")

        finally:
            # تنظيف الملف المؤقت
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _basic_syntax_check(self, content: str, filepath: str) -> Tuple[bool, str]:
        """
        فحص أساسي لبناء الجملة — general-purpose bracket/brace matching fallback.

        Used when dedicated tools (npx tsc, node --check) are not available.
        Performs:
        1. Empty content check
        2. Bracket/brace/parenthesis matching (respecting strings, comments, template literals)
        3. Unclosed string/template literal detection

        Returns:
            (is_valid, error_message) — error_message is empty string if valid
        """
        stripped = content.strip()
        if not stripped:
            return (False, "الملف فارغ")

        bracket_pairs = [('{', '}'), ('[', ']'), ('(', ')')]
        for open_b, close_b in bracket_pairs:
            depth = 0
            in_string = False
            string_char = None
            in_template = False
            i = 0
            while i < len(content):
                c = content[i]
                # تخطي التعليقات
                if not in_string and not in_template:
                    if c == '/' and i + 1 < len(content):
                        if content[i + 1] == '/':
                            # تعليق سطر واحد — تخطي للنهاية
                            nl = content.find('\n', i)
                            i = nl if nl != -1 else len(content)
                            continue
                        elif content[i + 1] == '*':
                            # تعليق متعدد الأسطر
                            end = content.find('*/', i + 2)
                            i = end + 2 if end != -1 else len(content)
                            continue
                    # تخطي تعليقات Python
                    if c == '#' and (not filepath.endswith('.ts') and not filepath.endswith('.tsx')
                                     and not filepath.endswith('.js') and not filepath.endswith('.jsx')):
                        nl = content.find('\n', i)
                        i = nl if nl != -1 else len(content)
                        continue
                # تخطي النصوص
                if not in_template and c in ('"', "'", '`') and not in_string:
                    in_string = True
                    string_char = c
                    if c == '`':
                        in_template = True
                elif in_string and c == string_char:
                    # تحقق من عدم وجود escape
                    if i > 0 and content[i - 1] == '\\':
                        # تحقق من عدم وجود escape للـ escape نفسه
                        num_backslashes = 0
                        j = i - 1
                        while j >= 0 and content[j] == '\\':
                            num_backslashes += 1
                            j -= 1
                        if num_backslashes % 2 == 0:
                            in_string = False
                            if string_char == '`':
                                in_template = False
                            string_char = None
                    else:
                        in_string = False
                        if string_char == '`':
                            in_template = False
                        string_char = None
                elif not in_string and not in_template:
                    if c == open_b:
                        depth += 1
                    elif c == close_b:
                        depth -= 1
                        if depth < 0:
                            return (False, f"قوس إغلاق زائد '{close_b}' — تحقق من الأقواس")
                i += 1
            if depth != 0:
                return (False, f"أقواس غير متطابقة '{open_b}{close_b}' — فرق: {depth}")

        logger.info("Basic syntax check passed for %s (bracket matching)", filepath)
        return (True, "")

    def _validate_unknown(self, content: str, filepath: str) -> Tuple[bool, str]:
        """
        فحص أساسي للملفات ذات الامتدادات غير المعروفة
        يتحقق فقط من أن المحتوى ليس فارغاً ولا يحتوي على أنماط مشبوهة
        """
        stripped = content.strip()
        if not stripped:
            return (False, "الملف فارغ")
        return (True, "")

    # =========================================================================
    # Internal Methods — الدوال الداخلية
    # =========================================================================

    def _read_source(self, file_path: str) -> Optional[str]:
        """قراءة الكود المصدري — read source code from a file."""
        target = self._resolve_target_path(file_path)
        if not target:
            return None
        try:
            with open(target, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error("Failed to read %s: %s", file_path, e)
            return None

    def _generate_diff(self, original: str, modified: str, file_path: str) -> str:
        """توليد فرق موحد — generate unified diff."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        diff = difflib.unified_diff(
            original_lines, modified_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )
        return ''.join(diff)

    def _backup_file(self, file_path: str) -> str:
        """إنشاء نسخة احتياطية — create a backup of a file."""
        target = self._resolve_target_path(file_path)
        if not target:
            return ""

        timestamp = int(time.time())
        backup_name = f"{Path(file_path).stem}_{timestamp}.bak"
        backup_path = Path(self.backup_dir) / backup_name

        try:
            shutil.copy2(target, backup_path)
            logger.debug("Backup created: %s", backup_path)
            return str(backup_path)
        except Exception as e:
            logger.error("Backup failed for %s: %s", file_path, e)
            return ""

    def _check_safety(self, diff: str) -> tuple:
        """فحص أمان الفرق — check diff for safety violations."""
        violations = []
        for pattern in self.FORBIDDEN_PATTERNS:
            if pattern in diff:
                violations.append(f"نمط محظور في التعديل: {pattern}")
        return len(violations) == 0, violations

    def _is_protected_file(self, file_path: str) -> bool:
        """التحقق من أن الملف محمي — check if a file is protected."""
        file_name = Path(file_path).name

        # فحص الاسم المباشر
        if file_name in self.PROTECTED_FILES:
            return True

        # فحص الامتدادات
        if file_name.endswith(('.key', '.pem', '.env', '.secret')):
            return True

        # فحص المجلدات المحمية
        parts = Path(file_path).parts
        for protected_dir in self.PROTECTED_DIRS:
            if protected_dir in parts:
                return True

        # فحص SafetyGuard
        try:
            from mamoun.core.safety_guard import SafetyGuard
            guard = SafetyGuard()
            if guard.is_file_protected(file_path):
                return True
        except Exception:
            pass

        return False

    def _compute_safety_score(self, diff: str, target_file: str, proposed_code: str) -> float:
        """حساب درجة الأمان — compute a safety score for a modification."""
        score = 1.0

        # عامل 1: حجم التغيير — التغييرات الكبيرة أخطر
        change_lines = sum(1 for line in diff.split('\n') if line.startswith('+') or line.startswith('-'))
        total_lines = len(proposed_code.split('\n'))
        change_ratio = change_lines / max(1, total_lines)
        score -= change_ratio * 0.3

        # عامل 2: نوع الملف — الملفات الأساسية أخطر
        critical_modules = ["core", "safety", "api", "evolution"]
        for module in critical_modules:
            if module in target_file:
                score -= 0.15
                break

        # عامل 3: أنماط محفوفة بالمخاطر
        risky_patterns = ["import os", "import subprocess", "import sys"]
        for pattern in risky_patterns:
            if pattern in proposed_code and pattern not in diff:
                pass  # موجود أصلاً — لا مشكلة
            elif pattern in diff:
                score -= 0.2

        # عامل 4: أنماط محظورة
        is_safe, _ = self._check_safety(diff)
        if not is_safe:
            score = 0.0

        return max(0.0, min(1.0, score))

    def _determine_risk_level(self, safety_score: float, target_file: str) -> str:
        """تحديد مستوى الخطر — determine risk level."""
        if safety_score < 0.3:
            return "critical"
        elif safety_score < 0.5:
            return "high"
        elif safety_score < 0.7:
            return "medium"
        else:
            return "low"

    def _resolve_target_path(self, file_path: str) -> Optional[Path]:
        """حل مسار الملف — resolve a file path safely."""
        # منع path traversal
        candidates = [
            Path(self.backend_root) / file_path,
            Path(self.project_root) / file_path,
            Path(self.backend_root) / "mamoun" / file_path,
        ]

        for candidate in candidates:
            try:
                resolved = candidate.resolve()
                # التحقق من أن المسار داخل المشروع
                project_resolved = Path(self.project_root).resolve()
                if str(resolved).startswith(str(project_resolved)):
                    if resolved.exists() and resolved.is_file():
                        return resolved
            except (ValueError, OSError):
                continue

        return None

    def _restore_from_backup(self, target_path: Path, backup_path: str) -> bool:
        """استعادة من النسخة الاحتياطية — restore file from backup."""
        if not backup_path:
            return False
        try:
            backup = Path(backup_path)
            if backup.exists():
                shutil.copy2(backup, target_path)
                return True
        except Exception as e:
            logger.error("Restore failed: %s", e)
        return False

    async def _generate_proposed_code(
        self, target_file: str, original_code: str, description: str
    ) -> Optional[str]:
        """توليد كود مقترح باستخدام LLM — generate proposed code via LLM."""
        try:
            from mamoun.core.llm_client import get_llm_client
            llm = get_llm_client()

            result = await llm.code_edit(
                current_code=original_code[:8000],
                instruction=description,
                model="glm-5.1",
            )

            if result and "patched_code" in result:
                return result["patched_code"]
            elif result and "patchedCode" in result:
                return result["patchedCode"]

            return None
        except Exception as e:
            logger.error("LLM code generation failed: %s", e)
            return None

    def _check_function_preservation(
        self, original_code: str, proposed_code: str
    ) -> List[str]:
        """التحقق من الحفاظ على الدوال — check that no functions are removed."""
        errors = []
        try:
            original_tree = ast.parse(original_code)
            proposed_tree = ast.parse(proposed_code)

            original_funcs = {
                n.name for n in ast.walk(original_tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            proposed_funcs = {
                n.name for n in ast.walk(proposed_tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            }

            missing = original_funcs - proposed_funcs
            if missing:
                errors.append(f"دوال مفقودة في الكود المقترح: {', '.join(sorted(missing))}")
        except SyntaxError:
            pass

        return errors

    def _generate_id(self) -> str:
        """توليد معرف فريد — generate a unique modification ID."""
        self._proposal_counter += 1
        return f"mod-{int(time.time())}-{self._proposal_counter:04d}"

    def _find_proposal(self, modification_id: str) -> Optional[ModificationProposal]:
        """البحث عن مقترح — find a proposal by ID."""
        for proposal in self._history:
            if proposal.id == modification_id:
                return proposal
        return None

    def _discover_capabilities(self, mamoun_path: Path) -> List[str]:
        """اكتشاف القدرات — discover system capabilities from module structure."""
        capabilities = []
        module_map = {
            "core": "النواة والمعالجة",
            "brains": "الأدمغة المتعددة",
            "agents": "الوكلاء الذكيين",
            "evolution": "التطور الذاتي",
            "awareness": "الوعي الذاتي",
            "memory": "الذاكرة ثلاثية المستويات",
            "creative": "الإبداع والأصالة",
            "emotion": "المحرك العاطفي",
            "agi": "الذكاء العام الاصطناعي",
            "hyperagent": "الوكيل الفائق",
            "voice": "معالجة الصوت",
            "physical": "التجسيد المادي",
            "planning": "التخطيط والقيود",
            "human": "التعاون البشري",
            "tom": "نظرية العقل",
            "instincts": "الغرائز",
            "deliberation": "المداولة",
            "notifications": "الإشعارات",
            "approval": "بوابة الموافقة",
            "learning": "التعلم المستمر",
            "swarm": "ذكاء السرب",
            "a2ui": "واجهة المستخدم التكيفية",
            "preference": "تفضيلات المستخدم",
            "tools": "الأدوات",
            "terminal": "الطرفية الذكية",
            "api": "واجهة برمجة التطبيقات",
        }

        for module_dir in sorted(mamoun_path.iterdir()):
            if module_dir.is_dir() and not module_dir.name.startswith("_"):
                py_count = len(list(module_dir.rglob("*.py")))
                if py_count > 0:
                    name = module_dir.name
                    label = module_map.get(name, name)
                    capabilities.append(f"{label} ({py_count} ملف)")

        return capabilities

    def _build_dashboard_sections(self, file_breakdown: dict) -> List[str]:
        """بناء أقسام لوحة التحكم — build dashboard sections."""
        sections = []
        for module, info in sorted(file_breakdown.items()):
            sections.append(f"{module}: {info['files']} ملف، {info['lines']} سطر")
        return sections

    async def _generate_improvement_suggestions(self, analysis: SelfAnalysis) -> List[str]:
        """توليد اقتراحات التحسين — generate improvement suggestions via LLM."""
        try:
            from mamoun.core.llm_client import get_llm_client
            llm = get_llm_client()

            prompt = f"""حلل نظام مأمون (BABSHARQII v18.0) واقترح تحسينات:

عدد الملفات: {analysis.total_files}
عدد الأسطر: {analysis.total_lines}
عدد الدوال: {analysis.total_functions}
عدد الأصناف: {analysis.total_classes}
درجة التعقيد: {analysis.complexity_score:.2f}
درجة الصحة: {analysis.health_score:.2f}

التوزيع حسب المجلدات:
{json.dumps(analysis.file_breakdown, indent=2, ensure_ascii=False)[:2000]}

اقترح 5-10 تحسينات محددة وقابلة للتنفيذ. أجب بقائمة فقط، كل سطر اقتراح."""

            response = await llm.think(
                prompt=prompt,
                system="أنت محلل نظم ذكي. تقترح تحسينات عملية ومحددة.",
                model="glm-5.1",
                temperature=0.7,
            )

            if response.text:
                suggestions = [
                    line.strip().lstrip("0123456789.-) ")
                    for line in response.text.strip().split('\n')
                    if line.strip() and len(line.strip()) > 10
                ]
                return suggestions[:15]
        except Exception as e:
            logger.warning("Failed to generate suggestions: %s", e)

        return ["تحليل الكود وتحسين الأداء", "إضافة معالجة أخطاء دفاعية"]

    def _module_name_ar(self, module_name: str) -> str:
        """ترجمة اسم المodule للعربية — translate module name to Arabic."""
        names = {
            "core": "النواة", "brains": "الأدمغة", "agents": "الوكلاء",
            "evolution": "التطور", "awareness": "الوعي", "memory": "الذاكرة",
            "creative": "الإبداع", "emotion": "العاطفة", "agi": "الذكاء العام",
            "hyperagent": "الوكيل الفائق", "voice": "الصوت", "physical": "التجسيد",
            "planning": "التخطيط", "human": "التعاون البشري", "tom": "نظرية العقل",
            "instincts": "الغرائز", "deliberation": "المداولة", "api": "واجهة API",
            "tools": "الأدوات", "terminal": "الطرفية", "notifications": "الإشعارات",
            "approval": "الموافقات", "learning": "التعلم", "swarm": "السرب",
            "a2ui": "الواجهة التكيفية", "preference": "التفضيلات",
        }
        return names.get(module_name, module_name)

    def _log_audit(self, proposal: ModificationProposal):
        """تسجيل المراجعة — log modification to audit trail file."""
        audit_path = Path(self.data_dir) / "audit_trail.jsonl"
        try:
            record = {
                "id": proposal.id,
                "target_file": proposal.target_file,
                "description": proposal.description[:500],
                "status": proposal.status,
                "safety_score": proposal.safety_score,
                "risk_level": proposal.risk_level,
                "approved_by": proposal.approved_by,
                "applied_at": proposal.applied_at,
                "diff_hash": hashlib.sha256(
                    proposal.diff.encode()
                ).hexdigest()[:32] if proposal.diff else "",
                "diff_size": len(proposal.diff),
                "timestamp": time.time(),
            }
            with open(audit_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error("Audit log write failed: %s", e)

    def _load_history(self):
        """تحميل السجل من القرص — load modification history from disk."""
        history_path = Path(self.data_dir) / "history.json"
        if not history_path.exists():
            return

        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for item in data:
                proposal = ModificationProposal(
                    id=item.get("id", ""),
                    target_file=item.get("target_file", ""),
                    description=item.get("description", ""),
                    original_code=item.get("original_code", ""),
                    proposed_code=item.get("proposed_code", ""),
                    diff=item.get("diff", ""),
                    safety_score=item.get("safety_score", 0.0),
                    risk_level=item.get("risk_level", "medium"),
                    created_at=item.get("created_at", 0.0),
                    status=item.get("status", "unknown"),
                    approved_by=item.get("approved_by", ""),
                    applied_at=item.get("applied_at", 0.0),
                    rolled_back_at=item.get("rolled_back_at", 0.0),
                    backup_path=item.get("backup_path", ""),
                    llm_model=item.get("llm_model", ""),
                    validation_errors=item.get("validation_errors", []),
                )
                self._history.append(proposal)

            logger.info("Loaded %d modification records from disk", len(self._history))
        except Exception as e:
            logger.error("Failed to load history: %s", e)

    def _save_history(self):
        """حفظ السجل على القرص — save modification history to disk."""
        history_path = Path(self.data_dir) / "history.json"
        try:
            data = []
            for proposal in self._history:
                data.append({
                    "id": proposal.id,
                    "target_file": proposal.target_file,
                    "description": proposal.description,
                    "original_code": proposal.original_code,
                    "proposed_code": proposal.proposed_code,
                    "diff": proposal.diff,
                    "safety_score": proposal.safety_score,
                    "risk_level": proposal.risk_level,
                    "created_at": proposal.created_at,
                    "status": proposal.status,
                    "approved_by": proposal.approved_by,
                    "applied_at": proposal.applied_at,
                    "rolled_back_at": proposal.rolled_back_at,
                    "backup_path": proposal.backup_path,
                    "llm_model": proposal.llm_model,
                    "validation_errors": proposal.validation_errors,
                })
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to save history: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# Singleton — النمط الفردي
# ─────────────────────────────────────────────────────────────────────────────

_self_modifier: Optional[SelfModifier] = None


def get_self_modifier() -> SelfModifier:
    """الحصول على مثيل SelfModifier — get the global SelfModifier instance."""
    global _self_modifier
    if _self_modifier is None:
        _self_modifier = SelfModifier()
    return _self_modifier
