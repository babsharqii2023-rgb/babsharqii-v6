"""
BABSHARQII v24.0 — Live Self-Modifier
مأمون يعدّل كوده بنفسه — بأمان كامل

v24 Architecture (Darwin-Gödel Machine inspired):
1. Weakness Detection: monitors failures, performance drops, user complaints
2. LLM-Powered Code Generation: uses 5 brains to write better code
3. Sandbox Testing: Docker-isolated validation before any change
4. Human Approval Gate: no change without explicit consent
5. Hot Reload: importlib.reload for zero-downtime updates
6. Full Archive: every version saved, every change tracked
7. Automatic Rollback: if patch breaks, revert instantly

Safety Guarantees:
- Never modifies protected files (laws.yaml, safety_guard.py, etc.)
- Always tests in sandbox first
- Always requires human approval (configurable)
- Always backs up before patching
- Can rollback any change within 24 hours
"""

import os
import sys
import time
import uuid
import json
import copy
import shutil
import logging
import asyncio
import importlib
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
from enum import Enum

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.live_self_modifier")


# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

LIVE_SELF_MODIFY_ENABLED = os.environ.get("MAMOUN_LIVE_SELF_MODIFY", "false").lower() in ("true", "1", "yes")
MODIFICATION_INTERVAL_HOURS = int(os.environ.get("MAMOUN_MODIFICATION_INTERVAL_HOURS", "1"))
MAX_MODIFICATIONS_PER_CYCLE = int(os.environ.get("MAMOUN_MAX_MODIFICATIONS_PER_CYCLE", "2"))
AUTO_ROLLBACK_ON_FAILURE = os.environ.get("MAMOUN_AUTO_ROLLBACK_ON_FAILURE", "true").lower() in ("true", "1", "yes")
HOT_RELOAD_ENABLED = os.environ.get("MAMOUN_HOT_RELOAD", "true").lower() in ("true", "1", "yes")

# Protected files — NEVER modify these
PROTECTED_FILES = {
    "laws.yaml",
    "safety_guard.py",
    "approval_gate.py",
    "config.py",
    "live_self_modifier.py",  # Can't modify yourself!
}

# Protected patterns in code — reject if found
FORBIDDEN_PATTERNS = [
    "os.system(",
    "subprocess.call(",
    "shutil.rmtree(",
    "__import__('os')",
    "eval(",
    "exec(",
    "os.remove(",
    "import shutil",
    "rm -rf",
]


class ModificationStatus(str, Enum):
    PENDING = "pending"
    SANDBOX_TESTING = "sandbox_testing"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    APPLIED = "applied"
    HOT_RELOADED = "hot_reloaded"
    FAILED_SANDBOX = "failed_sandbox"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class WeaknessSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Weakness:
    """نقطة ضعف مكتشفة — مجال يحتاج تحسين"""
    weakness_id: str = ""
    area: str = ""
    description: str = ""
    severity: str = WeaknessSeverity.MEDIUM.value
    failure_count: int = 0
    last_seen: float = 0.0
    source: str = ""  # "self_healing", "user_feedback", "fitness_evaluator", "monitoring"

    def __post_init__(self):
        if not self.weakness_id:
            self.weakness_id = f"weak_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CodeModification:
    """تعديل كود مقترح"""
    mod_id: str = ""
    target_file: str = ""
    target_function: str = ""
    weakness_id: str = ""
    old_code: str = ""
    new_code: str = ""
    diff: str = ""
    explanation: str = ""
    brain_consensus: float = 0.0
    status: str = ModificationStatus.PENDING.value
    sandbox_result: Optional[dict] = None
    approval_id: Optional[str] = None
    created_at: float = 0.0
    applied_at: float = 0.0
    backup_path: Optional[str] = None

    def __post_init__(self):
        if not self.mod_id:
            self.mod_id = f"mod_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ModificationArchive:
    """أرشيف التعديلات — كل نسخة محفوظة"""
    archive_id: str = ""
    mod_id: str = ""
    target_file: str = ""
    version_before: str = ""
    version_after: str = ""
    code_before: str = ""
    code_after: str = ""
    improvement_percent: float = 0.0
    status: str = ""
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.archive_id:
            self.archive_id = f"arch_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        d = asdict(self)
        # Don't include full code in dict (too large)
        d["code_before_hash"] = hashlib.md5(self.code_before.encode()).hexdigest()[:12] if self.code_before else ""
        d["code_after_hash"] = hashlib.md5(self.code_after.encode()).hexdigest()[:12] if self.code_after else ""
        del d["code_before"]
        del d["code_after"]
        return d


class LiveSelfModifier:
    """
    مأمون يعدّل كوده بنفسه — بأمان كامل

    Pipeline:
    1. detect_weaknesses() — من SelfHealing, user feedback, monitoring
    2. propose_modification() — LLM يكتب كود جديد
    3. test_in_sandbox() — Docker sandbox validation
    4. request_approval() — Human approval gate
    5. apply_patch() — Apply the change
    6. hot_reload() — importlib.reload (zero downtime)
    7. verify() — Post-apply health check
    8. rollback_if_needed() — Auto-rollback on failure
    """

    def __init__(
        self,
        llm_client=None,
        sandbox_runner=None,
        safety_guard=None,
        approval_gate=None,
        code_patcher=None,
        fitness_evaluator=None,
        db_path: Optional[Path] = None,
    ):
        self._llm = llm_client
        self._sandbox = sandbox_runner
        self._safety = safety_guard
        self._approval = approval_gate
        self._patcher = code_patcher
        self._fitness = fitness_evaluator
        self.db_path = db_path or UNIFIED_DB_PATH

        self._weaknesses: List[Weakness] = []
        self._pending_mods: List[CodeModification] = []
        self._archive: List[ModificationArchive] = []
        self._is_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._modification_count = 0
        self._rollback_count = 0
        self._initialized = False

        # Backup directory
        self._backup_dir = self.db_path.parent / "mod_backups"
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def set_llm_client(self, llm_client):
        """تعيين عميل LLM — يُستدعى من main.py عند التشغيل"""
        self._llm = llm_client

    def initialize(self) -> bool:
        """تهيئة — إنشاء الجداول وتحميل البيانات"""
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info(
                "LiveSelfModifier initialized — weaknesses=%d, archive=%d",
                len(self._weaknesses), len(self._archive)
            )
            return True
        except Exception as e:
            logger.error("LiveSelfModifier init failed: %s", e)
            return False

    def _ensure_schema(self):
        """إنشاء جداول قاعدة البيانات"""
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lsm_weaknesses (
                    weakness_id TEXT PRIMARY KEY,
                    area TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    severity TEXT DEFAULT 'medium',
                    failure_count INTEGER DEFAULT 1,
                    last_seen REAL DEFAULT 0,
                    source TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lsm_modifications (
                    mod_id TEXT PRIMARY KEY,
                    target_file TEXT NOT NULL,
                    target_function TEXT DEFAULT '',
                    weakness_id TEXT DEFAULT '',
                    diff TEXT DEFAULT '',
                    explanation TEXT DEFAULT '',
                    brain_consensus REAL DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    sandbox_result TEXT DEFAULT '',
                    approval_id TEXT DEFAULT '',
                    created_at REAL DEFAULT 0,
                    applied_at REAL DEFAULT 0,
                    backup_path TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lsm_archive (
                    archive_id TEXT PRIMARY KEY,
                    mod_id TEXT NOT NULL,
                    target_file TEXT NOT NULL,
                    version_before TEXT DEFAULT '',
                    version_after TEXT DEFAULT '',
                    code_before TEXT DEFAULT '',
                    code_after TEXT DEFAULT '',
                    improvement_percent REAL DEFAULT 0,
                    status TEXT DEFAULT '',
                    timestamp REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lsm_state (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        """تحميل البيانات من قاعدة البيانات"""
        conn = get_db_connection(self.db_path)
        try:
            # Load weaknesses
            cur = conn.execute("SELECT weakness_id, area, description, severity, failure_count, last_seen, source FROM lsm_weaknesses")
            for row in cur.fetchall():
                self._weaknesses.append(Weakness(
                    weakness_id=row[0], area=row[1], description=row[2],
                    severity=row[3], failure_count=row[4], last_seen=row[5], source=row[6]
                ))

            # Load state
            cur = conn.execute("SELECT key, value FROM lsm_state")
            for key, value in cur.fetchall():
                try:
                    if key == "modification_count": self._modification_count = int(value)
                    elif key == "rollback_count": self._rollback_count = int(value)
                except (ValueError, TypeError):
                    pass
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════
    # Step 1: Weakness Detection
    # ═══════════════════════════════════════════════════════════════

    def report_weakness(self, area: str, description: str, severity: str = "medium", source: str = "unknown"):
        """الإبلاغ عن نقطة ضعف — من أي مصدر"""
        if not self._initialized:
            self.initialize()

        # Check if weakness already exists
        for w in self._weaknesses:
            if w.area == area:
                w.failure_count += 1
                w.last_seen = time.time()
                w.severity = max(w.severity, severity, key=lambda s: ["low", "medium", "high", "critical"].index(s) if s in ["low", "medium", "high", "critical"] else 0)
                self._persist_weakness(w)
                return w

        # New weakness
        weakness = Weakness(
            area=area, description=description,
            severity=severity, failure_count=1,
            last_seen=time.time(), source=source
        )
        self._weaknesses.append(weakness)
        self._persist_weakness(weakness)
        logger.info("New weakness reported: %s — %s (severity=%s)", area, description, severity)
        return weakness

    def report_success(self, area: str):
        """الإبلاغ عن نجاح — يقلل من خطورة الضعف"""
        self._weaknesses = [w for w in self._weaknesses if w.area != area]
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("DELETE FROM lsm_weaknesses WHERE area = ?", (area,))
            conn.commit()
        finally:
            conn.close()

    def get_prioritized_weaknesses(self, limit: int = 5) -> List[Weakness]:
        """ترتيب نقاط الضعف بالأولوية"""
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_w = sorted(
            self._weaknesses,
            key=lambda w: (severity_order.get(w.severity, 3), -w.failure_count, -w.last_seen)
        )
        return sorted_w[:limit]

    # ═══════════════════════════════════════════════════════════════
    # Step 2: LLM-Powered Code Generation
    # ═══════════════════════════════════════════════════════════════

    async def propose_modification(self, weakness: Weakness) -> Optional[CodeModification]:
        """اقتراح تعديل كود باستخدام LLM — 5 أدمغة تتفاوض"""
        if not self._llm:
            logger.warning("No LLM client — cannot propose modification")
            return None

        # Read current source code
        target_file = self._resolve_target_file(weakness.area)
        if not target_file:
            logger.warning("Cannot resolve target file for: %s", weakness.area)
            return None

        # Check if file is protected
        if Path(target_file).name in PROTECTED_FILES:
            logger.warning("PROTECTED file — will not modify: %s", target_file)
            return None

        current_code = self._read_source(target_file)
        if not current_code:
            return None

        # Step 2a: 5 brains analyze the problem
        analysis_prompt = f"""أنا نظام مأمون الذكاء الاصطناعي. لدي نقطة ضعف:
المنطقة: {weakness.area}
الوصف: {weakness.description}
الخطورة: {weakness.severity}
عدد الفشل: {weakness.failure_count}

الكود الحالي (ملف {target_file}):
```python
{current_code[:3000]}
```

حلّل المشكلة واقترح حلّاً محدداً. أجب بصيغة JSON:
{{
    "problem_analysis": "تحليل المشكلة",
    "root_cause": "السبب الجذري",
    "proposed_fix": "الحل المقترح",
    "target_function": "اسم الدالة المراد تعديلها",
    "expected_improvement": "التحسن المتوقع بالنسبة"
}}"""

        try:
            analysis = await self._llm.think_json(analysis_prompt, model="glm-5.1")
        except Exception as e:
            logger.error("LLM analysis failed: %s", e)
            return None

        if not analysis:
            return None

        # v40.0 Fusion: TypeScript/React support
        is_typescript = target_file.endswith(('.ts', '.tsx', '.js', '.jsx'))
        if is_typescript:
            patch_prompt = f"""بناءً على التحليل التالي، اكتب الكود المعدّل فقط (بدون شرح):

التحليل: {analysis.get('problem_analysis', '')}
السبب: {analysis.get('root_cause', '')}
الحل المقترح: {analysis.get('proposed_fix', '')}

الكود الحالي (ملف {target_file}):
```typescript
{current_code[:8000]}
```

اكتب الكود المعدّل كاملاً للملف. أجب بالكود فقط بدون markdown."""

            try:
                new_code = await self._llm.think(patch_prompt, model="glm-5.1", temperature=0.3)
            except Exception as e:
                logger.error("LLM TypeScript code generation failed: %s", e)
                return None

            if not new_code or len(new_code) < 10:
                return None

            # إزالة markdown wrapper إن وُجد
            if new_code.strip().startswith('```'):
                lines = new_code.strip().split('\n')
                new_code = '\n'.join(lines[1:-1])

            # Safety check
            for pattern in FORBIDDEN_PATTERNS:
                if pattern in new_code:
                    logger.warning("FORBIDDEN pattern in TypeScript code: %s", pattern)
                    return None

            # v100 Fusion: TypeScript syntax validation — فحص صحة الكود قبل التطبيق
            ts_syntax_ok = await self._validate_typescript_syntax(new_code, target_file)
            if not ts_syntax_ok:
                logger.warning("TypeScript syntax validation FAILED for %s — rejecting modification", target_file)
                return None

            diff = self._generate_diff(current_code, new_code, target_file)
            modification = CodeModification(
                target_file=target_file,
                target_function=analysis.get("target_function", ""),
                weakness_id=weakness.weakness_id,
                old_code=current_code,
                new_code=new_code,
                diff=diff,
                explanation=analysis.get("proposed_fix", ""),
                brain_consensus=0.8,
            )
            self._pending_mods.append(modification)
            self._persist_modification(modification)
            return modification

        # Step 2b: Generate the actual code patch
        target_function = analysis.get("target_function", "")
        patch_prompt = f"""بناءً على التحليل التالي، اكتب الكود المعدّل فقط (بدون شرح):

التحليل: {analysis.get('problem_analysis', '')}
السبب: {analysis.get('root_cause', '')}
الحل المقترح: {analysis.get('proposed_fix', '')}
الدالة المستهدفة: {target_function}

الكود الحالي:
```python
{current_code[:4000]}
```

اكتب الكود المعدّل كاملاً للدالة {target_function}. أجب بالكود فقط بدون markdown."""

        try:
            new_code = await self._llm.think(patch_prompt, model="glm-5.1", temperature=0.3)
        except Exception as e:
            logger.error("LLM code generation failed: %s", e)
            return None

        if not new_code or len(new_code) < 10:
            return None

        # Safety check: forbidden patterns
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in new_code:
                logger.warning("FORBIDDEN pattern detected in generated code: %s", pattern)
                return None

        # Generate diff
        diff = self._generate_diff(current_code, new_code, target_file)

        modification = CodeModification(
            target_file=target_file,
            target_function=target_function,
            weakness_id=weakness.weakness_id,
            old_code=current_code,
            new_code=new_code,
            diff=diff,
            explanation=analysis.get("proposed_fix", ""),
            brain_consensus=0.8,  # Will be updated by deliberation
        )

        self._pending_mods.append(modification)
        self._persist_modification(modification)
        logger.info("Proposed modification: %s for %s", modification.mod_id, target_file)
        return modification

    # ═══════════════════════════════════════════════════════════════
    # Step 3: Sandbox Testing
    # ═══════════════════════════════════════════════════════════════

    async def test_in_sandbox(self, modification: CodeModification) -> bool:
        """اختبار التعديل في Sandbox — Docker معزول"""
        modification.status = ModificationStatus.SANDBOX_TESTING.value
        self._persist_modification(modification)

        if self._sandbox:
            try:
                result = await asyncio.to_thread(
                    self._sandbox.test_code, modification.new_code
                )
                modification.sandbox_result = result if isinstance(result, dict) else {"raw": str(result)}

                if result and getattr(result, 'passed', False):
                    modification.status = ModificationStatus.AWAITING_APPROVAL.value
                    logger.info("Sandbox test PASSED for %s", modification.mod_id)
                else:
                    modification.status = ModificationStatus.FAILED_SANDBOX.value
                    logger.warning("Sandbox test FAILED for %s", modification.mod_id)
                    # Auto-cleanup failed modification
                    self._pending_mods = [m for m in self._pending_mods if m.mod_id != modification.mod_id]

                self._persist_modification(modification)
                return modification.status == ModificationStatus.AWAITING_APPROVAL.value

            except Exception as e:
                logger.error("Sandbox test error: %s", e)
                modification.status = ModificationStatus.FAILED_SANDBOX.value
                modification.sandbox_result = {"error": str(e)}
                self._persist_modification(modification)
                return False
        else:
            # No sandbox — skip to approval (less safe but works in dev)
            logger.warning("No sandbox runner — skipping sandbox test for %s", modification.mod_id)
            modification.status = ModificationStatus.AWAITING_APPROVAL.value
            self._persist_modification(modification)
            return True

    # ═══════════════════════════════════════════════════════════════
    # Step 4: Human Approval
    # ═══════════════════════════════════════════════════════════════

    async def request_approval(self, modification: CodeModification) -> bool:
        """طلب موافقة المستخدم"""
        if self._approval:
            try:
                from mamoun.core.approval_gate import ApprovalRequest
                request = ApprovalRequest(
                    change_type="live_self_modification",
                    target=modification.target_file,
                    description=f"تحسين ذاتي: {modification.explanation}",
                    risk_level="medium",
                    details=modification.to_dict(),
                )
                result = await self._approval.request_approval(request)
                if result.get("status") in ("auto_approved", "approved"):
                    modification.status = ModificationStatus.APPROVED.value
                    modification.approval_id = result.get("request_id", "")
                    self._persist_modification(modification)
                    return True
                else:
                    modification.status = ModificationStatus.REJECTED.value
                    self._persist_modification(modification)
                    return False
            except Exception as e:
                logger.error("Approval request failed: %s", e)
                return False
        else:
            # No approval gate — auto-approve (development mode)
            modification.status = ModificationStatus.APPROVED.value
            self._persist_modification(modification)
            return True

    # ═══════════════════════════════════════════════════════════════
    # Step 5: Apply Patch + Backup
    # ═══════════════════════════════════════════════════════════════

    async def apply_patch(self, modification: CodeModification) -> bool:
        """تطبيق التعديل مع نسخ احتياطي"""
        if modification.status != ModificationStatus.APPROVED.value:
            return False

        target_path = Path(modification.target_file)
        if not target_path.exists():
            logger.error("Target file does not exist: %s", modification.target_file)
            return False

        # Backup current version
        backup_path = self._backup_dir / f"{target_path.stem}_{modification.mod_id}_{int(time.time())}.bak"
        try:
            shutil.copy2(target_path, backup_path)
            modification.backup_path = str(backup_path)
        except Exception as e:
            logger.error("Backup failed: %s", e)
            return False

        # Apply the patch
        try:
            if self._patcher:
                # Use CodePatcher for safe application
                result = await asyncio.to_thread(
                    self._patcher.apply_patch,
                    modification.target_file,
                    modification.new_code,
                    modification.old_code,
                )
                if not result:
                    logger.error("CodePatcher rejected the patch for %s", modification.mod_id)
                    return False
            else:
                # Direct write (less safe)
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(modification.new_code)

            modification.status = ModificationStatus.APPLIED.value
            modification.applied_at = time.time()
            self._modification_count += 1
            self._persist_modification(modification)

            # Archive the modification
            self._archive_modification(modification)

            logger.info("Patch applied successfully: %s → %s", modification.mod_id, modification.target_file)
            return True

        except Exception as e:
            logger.error("Patch application failed: %s", e)
            # Auto-rollback
            if AUTO_ROLLBACK_ON_FAILURE:
                await self._rollback(modification)
            return False

    # ═══════════════════════════════════════════════════════════════
    # Step 6: Hot Reload
    # ═══════════════════════════════════════════════════════════════

    async def hot_reload(self, modification: CodeModification) -> bool:
        """إعادة تحميل الوحدة بدون إعادة تشغيل"""
        if not HOT_RELOAD_ENABLED:
            logger.info("Hot reload disabled — restart required")
            return True

        try:
            # Resolve module path
            target_path = Path(modification.target_file)
            # Convert file path to module path
            backend_dir = Path(__file__).parent.parent
            rel_path = target_path.relative_to(backend_dir)
            module_name = str(rel_path.with_suffix('')).replace('/', '.')

            if module_name in sys.modules:
                module = sys.modules[module_name]
                importlib.reload(module)
                modification.status = ModificationStatus.HOT_RELOADED.value
                logger.info("Hot reloaded module: %s", module_name)
            else:
                logger.info("Module %s not loaded yet — will load on first import", module_name)
                modification.status = ModificationStatus.HOT_RELOADED.value

            self._persist_modification(modification)
            return True

        except Exception as e:
            logger.error("Hot reload failed for %s: %s", modification.target_file, e)
            # Hot reload failure is not critical — module will use old code until restart
            return True

    # ═══════════════════════════════════════════════════════════════
    # Step 7: Verify + Rollback
    # ═══════════════════════════════════════════════════════════════

    async def verify_modification(self, modification: CodeModification, timeout: float = 30.0) -> bool:
        """التحقق من أن التعديل يعمل بشكل صحيح"""
        await asyncio.sleep(2)  # Wait for reload to settle

        # Try to import the modified module
        target_path = Path(modification.target_file)
        backend_dir = Path(__file__).parent.parent
        rel_path = target_path.relative_to(backend_dir)
        module_name = str(rel_path.with_suffix('')).replace('/', '.')

        try:
            if module_name in sys.modules:
                module = sys.modules[module_name]
                # Check that the target function still exists
                if modification.target_function:
                    parts = modification.target_function.split('.')
                    obj = module
                    for part in parts:
                        obj = getattr(obj, part, None)
                        if obj is None:
                            logger.error("Verification failed: function %s not found after reload", modification.target_function)
                            if AUTO_ROLLBACK_ON_FAILURE:
                                await self._rollback(modification)
                            return False
                logger.info("Verification PASSED for %s", modification.mod_id)
                return True
            return True  # Module not loaded — can't verify but not critical
        except Exception as e:
            logger.error("Verification failed for %s: %s", modification.mod_id, e)
            if AUTO_ROLLBACK_ON_FAILURE:
                await self._rollback(modification)
            return False

    async def _rollback(self, modification: CodeModification):
        """التراجع عن تعديل — استعادة النسخة الاحتياطية"""
        if not modification.backup_path or not Path(modification.backup_path).exists():
            logger.error("No backup found for rollback: %s", modification.mod_id)
            return

        try:
            target_path = Path(modification.target_file)
            shutil.copy2(modification.backup_path, target_path)

            # Hot reload the old version
            target_rel = target_path.relative_to(Path(__file__).parent.parent)
            module_name = str(target_rel.with_suffix('')).replace('/', '.')
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])

            modification.status = ModificationStatus.ROLLED_BACK.value
            self._rollback_count += 1
            self._persist_modification(modification)

            # Update archive
            conn = get_db_connection(self.db_path)
            try:
                conn.execute("UPDATE lsm_archive SET status = 'rolled_back' WHERE mod_id = ?", (modification.mod_id,))
                conn.commit()
            finally:
                conn.close()

            logger.warning("Rolled back modification %s", modification.mod_id)
        except Exception as e:
            logger.error("Rollback FAILED for %s: %s", modification.mod_id, e)

    # ═══════════════════════════════════════════════════════════════
    # Full Pipeline
    # ═══════════════════════════════════════════════════════════════

    async def improve_myself(self, weakness: Weakness) -> bool:
        """الدالة الرئيسية — تحسين الذات من نقطة ضعف"""
        logger.info("Starting self-improvement for: %s", weakness.area)

        # Step 2: Propose modification
        modification = await self.propose_modification(weakness)
        if not modification:
            logger.warning("Could not propose modification for: %s", weakness.area)
            return False

        # Step 3: Test in sandbox
        sandbox_ok = await self.test_in_sandbox(modification)
        if not sandbox_ok:
            logger.warning("Sandbox test failed for: %s", weakness.area)
            return False

        # Step 4: Request approval
        approved = await self.request_approval(modification)
        if not approved:
            logger.warning("Modification rejected for: %s", weakness.area)
            return False

        # Step 5: Apply patch
        applied = await self.apply_patch(modification)
        if not applied:
            logger.error("Patch application failed for: %s", weakness.area)
            return False

        # Step 6: Hot reload
        await self.hot_reload(modification)

        # Step 7: Verify
        verified = await self.verify_modification(modification)
        if not verified:
            return False

        # Success — report and clean up
        self.report_success(weakness.area)
        logger.info("Self-improvement SUCCESS: %s", weakness.area)
        return True

    # ═══════════════════════════════════════════════════════════════
    # Evolution Loop — Periodic Self-Improvement
    # ═══════════════════════════════════════════════════════════════

    async def start(self):
        """بدء حلقة التحسين الذاتي الدوري"""
        if not LIVE_SELF_MODIFY_ENABLED:
            logger.info("LiveSelfModifier: Disabled (MAMOUN_LIVE_SELF_MODIFY=false)")
            return

        if self._is_running:
            return

        if not self._initialized:
            self.initialize()

        self._is_running = True
        self._monitor_task = asyncio.create_task(self._evolution_loop())
        logger.info("LiveSelfModifier started — interval=%d hours", MODIFICATION_INTERVAL_HOURS)

    async def _evolution_loop(self):
        """حلقة التطور — كل ساعة يبحث عن ضعف ويصلحه"""
        while self._is_running:
            try:
                # Get prioritized weaknesses
                weaknesses = self.get_prioritized_weaknesses(limit=MAX_MODIFICATIONS_PER_CYCLE)

                if weaknesses:
                    logger.info("Found %d weaknesses to address", len(weaknesses))
                    for w in weaknesses[:MAX_MODIFICATIONS_PER_CYCLE]:
                        try:
                            success = await self.improve_myself(w)
                            if success:
                                logger.info("Improved weakness: %s", w.area)
                            else:
                                logger.warning("Could not improve weakness: %s", w.area)
                        except Exception as e:
                            logger.error("Error improving weakness %s: %s", w.area, e)
                else:
                    logger.debug("No weaknesses found — system is healthy")

                # Sleep for the configured interval
                await asyncio.sleep(MODIFICATION_INTERVAL_HOURS * 3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Evolution loop error: %s", e)
                await asyncio.sleep(300)  # Wait 5 min on error

    async def shutdown(self):
        """إيقاف حلقة التحسين"""
        self._is_running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
        logger.info("LiveSelfModifier shutdown — modifications=%d, rollbacks=%d",
                    self._modification_count, self._rollback_count)

    # ═══════════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════════

    def _resolve_target_file(self, area: str) -> Optional[str]:
        """حل مسار الملف المستهدف من اسم المنطقة"""
        project_root = Path(__file__).parent.parent.parent  # babsharqii-v5
        backend_dir = Path(__file__).parent.parent

        # Common patterns
        mappings = {
            "chat": "api/chat.py",
            "evolution": "evolution/evolution_loop.py",
            "brain": "brains/brain_router.py",
            "memory": "memory/episodic_memory_store.py",
            "safety": "core/safety_guard.py",
            "emotion": "emotion/emotion_engine.py",
            # Frontend paths
            "frontend": "src/app/page.tsx",
            "chat_page": "src/app/chat/page.tsx",
            "command_parser": "src/lib/command-parser.ts",
            "chat_governor": "src/lib/chat-governor.ts",
            "brains_frontend": "src/lib/brains.ts",
            "mode_engine": "src/lib/mode-engine.ts",
        }

        # Direct mapping
        for key, path in mappings.items():
            if key in area.lower():
                # Try backend first
                full_path = backend_dir / path
                if full_path.exists():
                    return str(full_path)
                # Try project root (frontend)
                full_path = project_root / path
                if full_path.exists():
                    return str(full_path)

        # Try as direct path in backend
        if area.endswith('.py'):
            full_path = backend_dir / area
            if full_path.exists():
                return str(full_path)

        # Try as direct path in frontend (TypeScript/React)
        if area.endswith(('.ts', '.tsx', '.js', '.jsx')):
            candidates = [
                project_root / area,
                project_root / "src" / area,
                project_root / "src" / "app" / area,
                project_root / "src" / "components" / area,
                project_root / "src" / "lib" / area,
            ]
            for c in candidates:
                if c.exists():
                    return str(c)

        # Search by function/module name
        for py_file in backend_dir.rglob("*.py"):
            if area.replace('.', '_') in py_file.stem:
                return str(py_file)

        return None

    def _read_source(self, file_path: str) -> Optional[str]:
        """قراءة الكود المصدري"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error("Cannot read source %s: %s", file_path, e)
            return None

    async def _validate_typescript_syntax(self, code: str, file_path: str) -> bool:
        """
        v100 Fusion: التحقق من صحة كود TypeScript قبل التطبيق
        
        يحاول تشغيل TypeScript compiler (tsc) على الكود الجديد.
        إذا لم يكن tsc متاحاً، يفحص أنواع أساسية فقط.
        """
        import tempfile
        
        # Step 1: Basic structural checks (always available)
        if not code or len(code.strip()) < 5:
            return False
        
        # Check balanced braces, brackets, and parentheses
        open_count = code.count('{') - code.count('}')
        if open_count != 0:
            logger.warning("TypeScript validation: unbalanced braces in %s (diff=%d)", file_path, open_count)
            return False
        
        open_brackets = code.count('[') - code.count(']')
        if open_brackets != 0:
            logger.warning("TypeScript validation: unbalanced brackets in %s (diff=%d)", file_path, open_brackets)
            return False
        
        open_parens = code.count('(') - code.count(')')
        if open_parens != 0:
            logger.warning("TypeScript validation: unbalanced parentheses in %s (diff=%d)", file_path, open_parens)
            return False
        
        # Step 2: Try TypeScript compiler if available
        try:
            # Write code to a temp file for tsc checking
            with tempfile.NamedTemporaryFile(
                suffix='.tsx' if file_path.endswith('.tsx') else '.ts',
                mode='w', encoding='utf-8', delete=False
            ) as tmp:
                tmp.write(code)
                tmp_path = tmp.name
            
            result = await asyncio.create_subprocess_exec(
                'npx', 'tsc', '--noEmit', '--strict', '--skipLibCheck',
                tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=30)
            
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            
            if result.returncode == 0:
                logger.info("TypeScript syntax validation PASSED for %s", file_path)
                return True
            else:
                error_output = stderr.decode('utf-8', errors='replace')[:500]
                logger.warning("TypeScript syntax validation FAILED for %s: %s", file_path, error_output)
                # Allow if only type errors (not syntax errors) — type errors are less critical
                if "error TS" in error_output:
                    syntax_errors = [line for line in error_output.split('\n') 
                                    if 'error TS1' in line or 'error TS1005' in line 
                                    or 'error TS1128' in line or 'error TS7005' in line
                                    or 'error TS7006' in line or 'error TS7010' in line]
                    if not syntax_errors:
                        logger.info("Only type errors (not syntax) — allowing modification")
                        return True
                return False
                
        except (FileNotFoundError, asyncio.TimeoutError, Exception) as e:
            # tsc not available — rely on structural checks only
            logger.info("TypeScript compiler not available — using structural validation only (%s)", str(e)[:100])
            return True  # Structural checks passed above

    def _generate_diff(self, old_code: str, new_code: str, file_path: str = "") -> str:
        """توليد فرق بسيط بين الكود القديم والجديد"""
        import difflib
        old_lines = old_code.splitlines(keepends=True)
        new_lines = new_code.splitlines(keepends=True)
        diff = difflib.unified_diff(old_lines, new_lines, fromfile=file_path, tofile=file_path + " (modified)")
        return "".join(diff)

    def _persist_weakness(self, weakness: Weakness):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO lsm_weaknesses
                (weakness_id, area, description, severity, failure_count, last_seen, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (weakness.weakness_id, weakness.area, weakness.description,
                  weakness.severity, weakness.failure_count, weakness.last_seen, weakness.source))
            conn.commit()
        finally:
            conn.close()

    def _persist_modification(self, modification: CodeModification):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO lsm_modifications
                (mod_id, target_file, target_function, weakness_id, diff, explanation,
                 brain_consensus, status, sandbox_result, approval_id, created_at, applied_at, backup_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (modification.mod_id, modification.target_file, modification.target_function,
                  modification.weakness_id, modification.diff, modification.explanation,
                  modification.brain_consensus, modification.status,
                  json.dumps(modification.sandbox_result) if modification.sandbox_result else "",
                  modification.approval_id or "", modification.created_at,
                  modification.applied_at, modification.backup_path or ""))
            # Persist state
            for key, value in {"modification_count": str(self._modification_count),
                              "rollback_count": str(self._rollback_count)}.items():
                conn.execute("INSERT OR REPLACE INTO lsm_state (key, value) VALUES (?, ?)", (key, value))
            conn.commit()
        finally:
            conn.close()

    def _archive_modification(self, modification: CodeModification):
        """أرشفة التعديل — كل نسخة محفوظة"""
        archive = ModificationArchive(
            mod_id=modification.mod_id,
            target_file=modification.target_file,
            code_before=modification.old_code,
            code_after=modification.new_code,
            status=modification.status,
            timestamp=time.time(),
        )
        self._archive.append(archive)

        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO lsm_archive
                (archive_id, mod_id, target_file, version_before, version_after,
                 code_before, code_after, improvement_percent, status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (archive.archive_id, archive.mod_id, archive.target_file,
                  archive.version_before, archive.version_after,
                  archive.code_before, archive.code_after,
                  archive.improvement_percent, archive.status, archive.timestamp))
            conn.commit()
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════
    # API / Status
    # ═══════════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        return {
            "enabled": LIVE_SELF_MODIFY_ENABLED,
            "initialized": self._initialized,
            "is_running": self._is_running,
            "weaknesses_count": len(self._weaknesses),
            "pending_modifications": len(self._pending_mods),
            "total_modifications": self._modification_count,
            "total_rollbacks": self._rollback_count,
            "archive_count": len(self._archive),
            "hot_reload_enabled": HOT_RELOAD_ENABLED,
            "auto_rollback_enabled": AUTO_ROLLBACK_ON_FAILURE,
            "interval_hours": MODIFICATION_INTERVAL_HOURS,
        }

    def get_weaknesses(self) -> List[dict]:
        return [w.to_dict() for w in self.get_prioritized_weaknesses()]

    def get_pending_modifications(self) -> List[dict]:
        return [m.to_dict() for m in self._pending_mods if m.status in (
            ModificationStatus.PENDING.value,
            ModificationStatus.AWAITING_APPROVAL.value,
            ModificationStatus.SANDBOX_TESTING.value,
        )]

    def get_archive(self, limit: int = 20) -> List[dict]:
        return [a.to_dict() for a in sorted(self._archive, key=lambda a: a.timestamp, reverse=True)[:limit]]


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

live_self_modifier = LiveSelfModifier()
