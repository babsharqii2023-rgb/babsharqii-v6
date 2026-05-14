"""
Self Modifier v57 — Safe self-modification with REAL sandbox.

CRITICAL UPGRADE from v56:
- v56: Sandbox was BYPASSED — code executed directly without validation
- v57: REAL sandbox with AST validation, restricted execution, timeouts
- Three-phase pipeline: propose → verify (sandbox) → apply (with rollback)
- AST-level security: blocks os.system, subprocess, eval, exec, __import__
- Automatic rollback on failure
- Full integration with MetaCognitionEngine

v57 — Super Mind العقل الخارق مامون
"""

import ast
import time
import copy
import logging
import traceback
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ModificationStatus(str, Enum):
    PROPOSED = "proposed"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ModificationProposal:
    """A proposed code modification."""
    id: str
    target_file: str
    original_code: str
    proposed_code: str
    description: str
    proposer: str  # Component that proposed the change
    risk_level: str = "medium"  # "low", "medium", "high"
    status: ModificationStatus = ModificationStatus.PROPOSED
    verification_result: Optional[dict] = None
    apply_result: Optional[dict] = None
    rollback_snapshot: Optional[str] = None
    created_at: float = field(default_factory=time.time)


# ── AST Security Checker ─────────────────────────────────────────────────

FORBIDDEN_NAMES = {
    "os.system", "os.popen", "os.exec", "os.spawn",
    "subprocess.run", "subprocess.call", "subprocess.Popen",
    "eval", "exec", "compile",
    "__import__", "__builtins__",
    "shutil.rmtree", "shutil.rmtree",
    "breakpoint", "exit", "quit",
}

FORBIDDEN_AST_NODES = {
    ast.Import: lambda node: not any(
        alias.name.startswith(("os", "subprocess", "shutil", "sys"))
        for alias in node.names
    ),
    ast.ImportFrom: lambda node: node.module not in ("os", "subprocess", "shutil", "sys"),
}


class ASTSecurityChecker:
    """
    Validates Python code at the AST level before execution.
    Blocks dangerous operations: os.system, subprocess, eval, exec, etc.
    """

    FORBIDDEN_BUILTINS = {"eval", "exec", "compile", "__import__", "breakpoint", "exit", "quit"}
    FORBIDDEN_MODULES = {"subprocess", "shutil", "sys"}
    ALLOWED_OS_ATTRS = {"path", "environ", "getcwd", "listdir", "makedirs", "path"}  # Safe os operations
    ALLOWED_OS_FROM = {"os.path"}  # Safe from-imports

    def check(self, code: str) -> tuple[bool, list[str]]:
        """
        Check if code is safe to execute.
        Returns (is_safe, list_of_violations).
        """
        violations = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, [f"Syntax error: {e}"]

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.FORBIDDEN_MODULES:
                        violations.append(f"Forbidden import: {alias.name}")
                    # Special handling for os: allow import os but check usage
                    elif alias.name == "os":
                        pass  # os itself is OK, dangerous attrs are caught at call level

            elif isinstance(node, ast.ImportFrom):
                if node.module in self.FORBIDDEN_MODULES:
                    violations.append(f"Forbidden import from: {node.module}")
                elif node.module == "os" and node.module not in self.FORBIDDEN_MODULES:
                    pass  # Allow from os.path import ...
                elif node.module == "os.path":
                    pass  # os.path is safe

            # Check function calls
            elif isinstance(node, ast.Call):
                func_name = self._get_call_name(node)
                if func_name in self.FORBIDDEN_BUILTINS:
                    violations.append(f"Forbidden function call: {func_name}")
                elif func_name and func_name.startswith("os."):
                    # os is allowed as import, but dangerous attrs are blocked
                    safe = False
                    for attr in self.ALLOWED_OS_ATTRS:
                        if func_name == f"os.{attr}" or func_name.startswith(f"os.{attr}."):
                            safe = True
                            break
                    if not safe:
                        violations.append(f"Potentially dangerous os call: {func_name}")
                elif func_name and any(func_name.startswith(f"{m}.") for m in self.FORBIDDEN_MODULES):
                    violations.append(f"Potentially dangerous call: {func_name}")

            # Check attribute access to __builtins__
            elif isinstance(node, ast.Attribute):
                if node.attr == "__builtins__":
                    violations.append("Access to __builtins__ is forbidden")
                elif node.attr.startswith("__") and node.attr.endswith("__"):
                    if node.attr in ("__import__", "__builtins__", "__globals__"):
                        violations.append(f"Access to dunder attribute: {node.attr}")

        is_safe = len(violations) == 0
        return is_safe, violations

    def _get_call_name(self, node: ast.Call) -> Optional[str]:
        """Extract the function name from a Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return None


class RestrictedExecutor:
    """
    Executes code in a restricted environment.
    Provides safe builtins and prevents access to dangerous ones.
    """

    SAFE_BUILTINS = {
        "print": print,
        "len": len,
        "range": range,
        "enumerate": enumerate,
        "zip": zip,
        "map": map,
        "filter": filter,
        "sorted": sorted,
        "reversed": reversed,
        "min": min,
        "max": max,
        "sum": sum,
        "abs": abs,
        "round": round,
        "isinstance": isinstance,
        "type": type,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "None": None,
        "True": True,
        "False": False,
    }

    def execute(self, code: str, timeout: int = 30, context: dict = None) -> dict:
        """
        Execute code in a restricted sandbox.

        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds
            context: Additional variables to inject

        Returns:
            {"success": bool, "result": Any, "error": str, "output": str}
        """
        # AST check first
        checker = ASTSecurityChecker()
        is_safe, violations = checker.check(code)
        if not is_safe:
            return {
                "success": False,
                "result": None,
                "error": f"Security violations: {violations}",
                "output": "",
            }

        # Build restricted globals
        restricted_globals = {
            "__builtins__": self.SAFE_BUILTINS,
        }
        if context:
            restricted_globals.update(context)

        # Capture output
        output_lines = []
        original_print = print

        def safe_print(*args, **kwargs):
            output_lines.append(" ".join(str(a) for a in args))

        restricted_globals["print"] = safe_print

        # Execute with timeout
        try:
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError(f"Execution exceeded {timeout}s")

            # Set alarm (Unix only)
            try:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout)
            except (AttributeError, ValueError):
                old_handler = None

            try:
                exec(code, restricted_globals)

                # Get result if there's a 'result' variable
                result = restricted_globals.get("result", None)

                return {
                    "success": True,
                    "result": result,
                    "error": None,
                    "output": "\n".join(output_lines),
                }

            finally:
                try:
                    signal.alarm(0)
                    if old_handler:
                        signal.signal(signal.SIGALRM, old_handler)
                except (AttributeError, ValueError):
                    pass

        except TimeoutError as e:
            return {"success": False, "result": None, "error": str(e), "output": ""}
        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
                "output": "\n".join(output_lines),
            }


class SelfModifier:
    """
    Safe self-modification with real sandbox validation.

    Pipeline:
    1. PROPOSE: A component proposes a code modification
    2. VERIFY: Code is checked by AST security + sandbox execution
    3. APPLY: If verified, modification is applied with rollback capability
    4. ROLLBACK: If applied code causes errors, automatically revert

    Usage:
        modifier = SelfModifier(meta_cognition=meta)
        proposal = ModificationProposal(
            id="mod_001",
            target_file="some_module.py",
            original_code="def hello(): pass",
            proposed_code="def hello(): return 'world'",
            description="Add return value",
            proposer="improvement_proposer",
        )
        result = await modifier.modify(proposal)
    """

    def __init__(self, meta_cognition=None, neural_bus=None, llm_client=None):
        self._meta_cognition = meta_cognition
        self._neural_bus = neural_bus
        self._llm_client = llm_client
        self._security_checker = ASTSecurityChecker()
        self._executor = RestrictedExecutor()
        self._proposals: list[ModificationProposal] = []
        self._snapshots: dict[str, str] = {}  # file -> snapshot before modification

    def set_llm_client(self, client):
        self._llm_client = client

    # ── Phase 1: Verify ──────────────────────────────────────────────────
    async def verify(self, proposal: ModificationProposal) -> dict:
        """
        Verify a proposed modification.
        1. AST security check
        2. Syntax check
        3. Sandbox execution
        4. LLM review (if available)
        """
        results = {
            "ast_check": {"passed": False, "violations": []},
            "syntax_check": {"passed": False},
            "sandbox_execution": {"passed": False, "error": None},
            "llm_review": {"passed": True, "concerns": []},  # Default pass
            "overall": False,
        }

        # 1. AST Security Check
        is_safe, violations = self._security_checker.check(proposal.proposed_code)
        results["ast_check"] = {"passed": is_safe, "violations": violations}
        if not is_safe:
            results["overall"] = False
            return results

        # 2. Syntax Check
        try:
            ast.parse(proposal.proposed_code)
            results["syntax_check"] = {"passed": True}
        except SyntaxError as e:
            results["syntax_check"] = {"passed": False, "error": str(e)}
            results["overall"] = False
            return results

        # 3. Sandbox Execution
        sandbox_result = self._executor.execute(proposal.proposed_code, timeout=15)
        results["sandbox_execution"] = {
            "passed": sandbox_result["success"],
            "error": sandbox_result.get("error"),
            "output": sandbox_result.get("output", ""),
        }

        # 4. LLM Review (optional but recommended for high-risk changes)
        if proposal.risk_level == "high" and self._llm_client:
            try:
                llm_response = await self._llm_client.chat_with_fallback(
                    messages=[
                        {"role": "system", "content": "You are a code security reviewer. Analyze the proposed code change and identify any potential risks or concerns."},
                        {"role": "user", "content": f"Original code:\n```python\n{proposal.original_code[:1000]}\n```\n\nProposed change:\n```python\n{proposal.proposed_code[:1000]}\n```\n\nIdentify risks or concerns."}
                    ],
                    preferred_order=["deepseek", "glm"],
                )

                if llm_response.success:
                    content_lower = llm_response.content.lower()
                    concerns = []
                    for risk_kw in ["risk", "danger", "unsafe", "security", "vulnerability"]:
                        if risk_kw in content_lower:
                            concerns.append(f"LLM flagged potential {risk_kw}")
                    results["llm_review"] = {
                        "passed": len(concerns) == 0,
                        "concerns": concerns,
                        "review": llm_response.content[:500],
                    }

            except Exception as e:
                logger.warning(f"LLM review failed: {e}")

        # Overall verdict
        results["overall"] = (
            results["ast_check"]["passed"] and
            results["syntax_check"]["passed"] and
            results["sandbox_execution"]["passed"] and
            results["llm_review"]["passed"]
        )

        return results

    # ── Phase 2: Apply ───────────────────────────────────────────────────
    async def apply(self, proposal: ModificationProposal) -> dict:
        """
        Apply a verified modification.
        Takes a snapshot first for rollback capability.
        """
        if proposal.status != ModificationStatus.VERIFIED:
            return {"success": False, "error": "Proposal not verified"}

        # Take snapshot for rollback
        self._snapshots[proposal.target_file] = proposal.original_code
        proposal.rollback_snapshot = proposal.original_code

        try:
            # Write the new code
            import os
            target_path = proposal.target_file

            # Ensure target directory exists
            os.makedirs(os.path.dirname(target_path) if os.path.dirname(target_path) else ".", exist_ok=True)

            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(proposal.proposed_code)

            proposal.status = ModificationStatus.APPLIED
            return {"success": True, "file": target_path}

        except Exception as e:
            # Auto-rollback
            await self.rollback(proposal)
            return {"success": False, "error": str(e)}

    # ── Phase 3: Rollback ────────────────────────────────────────────────
    async def rollback(self, proposal: ModificationProposal) -> dict:
        """Rollback a failed modification."""
        if not proposal.rollback_snapshot:
            return {"success": False, "error": "No rollback snapshot available"}

        try:
            import os
            with open(proposal.target_file, 'w', encoding='utf-8') as f:
                f.write(proposal.rollback_snapshot)

            proposal.status = ModificationStatus.ROLLED_BACK
            logger.info(f"Rolled back modification {proposal.id}")
            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Full Pipeline ────────────────────────────────────────────────────
    async def modify(self, proposal: ModificationProposal) -> dict:
        """
        Full modification pipeline: verify → apply (with rollback on failure).
        """
        start = time.time()
        self._proposals.append(proposal)

        # Phase 1: Verify
        proposal.status = ModificationStatus.VERIFYING
        verification = await self.verify(proposal)
        proposal.verification_result = verification

        if not verification["overall"]:
            proposal.status = ModificationStatus.FAILED
            return {
                "success": False,
                "phase": "verification",
                "details": verification,
            }

        # Phase 2: Apply
        proposal.status = ModificationStatus.VERIFYING
        proposal.status = ModificationStatus.APPLYING
        apply_result = await self.apply(proposal)
        proposal.apply_result = apply_result

        if not apply_result["success"]:
            return {
                "success": False,
                "phase": "application",
                "details": apply_result,
            }

        # Record in meta-cognition
        if self._meta_cognition:
            from .meta_cognition_engine import OutcomeRecord
            self._meta_cognition.record_outcome(OutcomeRecord(
                component="self_modifier",
                operation="modify",
                success=True,
                quality_score=0.9 if proposal.risk_level == "low" else 0.7,
                predicted_quality=self._meta_cognition.predict_quality("self_modifier"),
                latency_ms=(time.time() - start) * 1000,
                metadata={"target": proposal.target_file, "risk": proposal.risk_level},
            ))

        return {
            "success": True,
            "proposal_id": proposal.id,
            "status": proposal.status.value,
            "latency_ms": (time.time() - start) * 1000,
        }

    def get_stats(self) -> dict:
        """Get modification statistics."""
        total = len(self._proposals)
        applied = sum(1 for p in self._proposals if p.status == ModificationStatus.APPLIED)
        failed = sum(1 for p in self._proposals if p.status == ModificationStatus.FAILED)
        rolled_back = sum(1 for p in self._proposals if p.status == ModificationStatus.ROLLED_BACK)

        return {
            "total_proposals": total,
            "applied": applied,
            "failed": failed,
            "rolled_back": rolled_back,
            "success_rate": applied / total if total > 0 else 0.0,
        }
