"""
BABSHARQII v62 — SelfModifier (BACKWARD-COMPATIBLE ADAPTER)

Redirects to super_brain/self_modifier.py.
Old: core/self_modifier.py → New: core/super_brain/self_modifier.py

v62 FIX: Added ALL missing methods called by kernel.py API endpoints:
- propose_modification(), validate_modification(), test_in_sandbox()
- apply_modification(), get_history(), analyze_self()
- get_proposal(), approve_proposal(), reject_proposal()
- _rebuild_dashboard_config()

These methods translate between the old API (used by kernel.py routes)
and the new SelfModifier API (verify/apply/modify/post_check/rollback).
"""

import ast
import os
import time
import logging
import traceback
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("mamoun.core.self_modifier")

# Re-export everything from the new module
from mamoun.core.super_brain.self_modifier import (
    ModificationStatus,
    ModificationProposal,
    ASTSecurityChecker,
    RestrictedExecutor,
    SelfModifier,
)

# Backward-compatible aliases
ValidationResult = ModificationProposal
ApplyResult = ModificationProposal
RollbackResult = ModificationProposal


class SelfAnalysis:
    """Backward-compatible SelfAnalysis (preserved for old API)."""
    def __init__(self, file_path: str = "", issues: list = None,
                 opportunities: list = None, risk_level: str = "low",
                 confidence: float = 0.0, total_files: int = 0,
                 total_lines: int = 0, total_functions: int = 0,
                 health_score: float = 0.0, complexity_score: float = 0.0,
                 suggested_improvements: list = None):
        self.file_path = file_path
        self.issues = issues or []
        self.opportunities = opportunities or []
        self.risk_level = risk_level
        self.confidence = confidence
        self.total_files = total_files
        self.total_lines = total_lines
        self.total_functions = total_functions
        self.health_score = health_score
        self.complexity_score = complexity_score
        self.suggested_improvements = suggested_improvements or []

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "issues": self.issues,
            "opportunities": self.opportunities,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "total_functions": self.total_functions,
            "health_score": self.health_score,
            "complexity_score": self.complexity_score,
            "suggested_improvements": self.suggested_improvements,
        }


class ModificationRecord:
    """Backward-compatible ModificationRecord (preserved for old API)."""
    def __init__(self, proposal=None, validation=None, apply_result=None,
                 timestamp: float = 0.0, rolled_back: bool = False):
        self.proposal = proposal
        self.validation = validation
        self.apply_result = apply_result
        self.timestamp = timestamp
        self.rolled_back = rolled_back
        self.id = getattr(proposal, 'id', str(int(time.time() * 1000)))
        self.status = getattr(proposal, 'status', ModificationStatus.PROPOSED)
        self.target_file = getattr(proposal, 'target_file', '')
        self.description = getattr(proposal, 'description', '')
        self.safety_score = getattr(proposal, 'safety_score', 0.0)
        self.success = not rolled_back
        self.error = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "target_file": self.target_file,
            "description": self.description,
            "status": self.status.value if isinstance(self.status, ModificationStatus) else str(self.status),
            "safety_score": self.safety_score,
            "timestamp": self.timestamp,
            "rolled_back": self.rolled_back,
            "success": self.success,
            "error": self.error,
        }


class SelfModifierAdapter(SelfModifier):
    """
    Extended SelfModifier with backward-compatible methods for kernel.py API.
    
    Translates between the old API (propose_modification, validate_modification, etc.)
    and the new SelfModifier API (verify, apply, modify, post_check, rollback).
    """

    def __init__(self, meta_cognition=None, neural_bus=None, llm_client=None):
        super().__init__(
            meta_cognition=meta_cognition,
            neural_bus=neural_bus,
            llm_client=llm_client,
        )
        self._modification_records: list[ModificationRecord] = []
        self._proposals_by_id: dict[str, ModificationProposal] = {}
        self._approved_proposals: set[str] = set()
        self._rejected_proposals: set[str] = set()
        self._dashboard_config: dict = {}

    async def propose_modification(self, target_file: str, description: str) -> ModificationProposal:
        """
        اقتراح تعديل جديد — called by kernel.py /self-modify/propose.
        
        Creates a ModificationProposal with generated code.
        """
        proposal_id = f"mod_{int(time.time() * 1000)}"
        
        # Read original file
        original_code = ""
        try:
            if os.path.isfile(target_file):
                with open(target_file, 'r', encoding='utf-8') as f:
                    original_code = f.read()
        except Exception as e:
            logger.warning(f"Could not read {target_file}: {e}")

        # Generate proposed code using LLM
        proposed_code = original_code
        if self._llm_client:
            try:
                response = await self._llm_client.chat_with_fallback(
                    messages=[
                        {"role": "system", "content": f"""You are a Python code modification expert.
Given the original code and a description of the desired change, produce the modified code.
Only output the modified Python code, no explanations or markdown fences.
Target file: {target_file}"""},
                        {"role": "user", "content": f"Original code:\n```python\n{original_code[:3000]}\n```\n\nRequested change: {description}\n\nOutput the modified code:"},
                    ],
                    preferred_order=["deepseek", "glm"],
                )
                if response.success and response.content:
                    # Clean up response - extract code from markdown if present
                    code = response.content.strip()
                    if code.startswith("```python"):
                        code = code[9:]
                    if code.startswith("```"):
                        code = code[3:]
                    if code.endswith("```"):
                        code = code[:-3]
                    code = code.strip()
                    proposed_code = code
            except Exception as e:
                logger.warning(f"LLM code generation failed: {e}")

        # Determine risk level
        risk_level = "medium"
        if any(kw in description.lower() for kw in ["security", "auth", "password", "token"]):
            risk_level = "high"
        elif any(kw in description.lower() for kw in ["format", "style", "comment", "docstring"]):
            risk_level = "low"

        # Determine initial status based on AST check
        status = ModificationStatus.PROPOSED
        checker = ASTSecurityChecker()
        is_safe, violations = checker.check(proposed_code)
        if not is_safe:
            status = ModificationStatus.FAILED

        proposal = ModificationProposal(
            id=proposal_id,
            target_file=target_file,
            original_code=original_code,
            proposed_code=proposed_code,
            description=description,
            proposer="api",
            risk_level=risk_level,
            status=status,
        )

        self._proposals_by_id[proposal_id] = proposal
        self._proposals.append(proposal)
        
        return proposal

    async def validate_modification(self, proposal: ModificationProposal) -> dict:
        """
        التحقق من تعديل — called by kernel.py /self-modify/propose.
        
        Delegates to SelfModifier.verify().
        """
        result = await self.verify(proposal)
        proposal.verification_result = result
        
        if result.get("overall"):
            proposal.status = ModificationStatus.VERIFIED
        
        # Return a dict with to_dict() for backward compat
        validation = {
            "passed": result.get("overall", False),
            "quality_score": result.get("quality_score", 0.0),
            "ast_check": result.get("ast_check", {}),
            "sandbox_execution": result.get("sandbox_execution", {}),
            "llm_review": result.get("llm_review", {}),
            "status": "verified" if result.get("overall") else "failed",
        }
        validation["to_dict"] = lambda: validation
        return validation

    async def test_in_sandbox(self, proposal: ModificationProposal) -> dict:
        """
        اختبار في Sandbox — called by kernel.py /self-modify/{id}/approve.
        """
        executor = RestrictedExecutor()
        result = executor.execute(proposal.proposed_code, timeout=15)
        return result

    async def apply_modification(self, proposal: ModificationProposal) -> ModificationRecord:
        """
        تطبيق التعديل — called by kernel.py /self-modify/{id}/approve.
        """
        apply_result = await self.apply(proposal)
        
        record = ModificationRecord(
            proposal=proposal,
            validation=proposal.verification_result,
            apply_result=apply_result,
            timestamp=time.time(),
            rolled_back=not apply_result.get("success", False),
        )
        record.success = apply_result.get("success", False)
        record.error = apply_result.get("error")
        
        if apply_result.get("success"):
            # Run post-check
            post_check = await self.post_check(proposal)
            if not post_check.get("passed"):
                await self.rollback(proposal)
                record.rolled_back = True
                record.success = False
                record.error = f"Post-check failed: {post_check.get('error', 'unknown')}"

        self._modification_records.append(record)
        return record

    async def get_history(self) -> list[ModificationRecord]:
        """
        سجل التعديلات — called by kernel.py /self-modify/history.
        """
        return self._modification_records

    async def analyze_self(self) -> SelfAnalysis:
        """
        تحليل ذاتي — called by kernel.py /self-modify/analyze.
        
        Analyzes the system's own codebase.
        """
        total_files = 0
        total_lines = 0
        total_functions = 0
        issues = []
        opportunities = []
        suggested_improvements = []
        
        # Scan the backend directory
        backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "mamoun")
        if os.path.isdir(backend_dir):
            for root, dirs, files in os.walk(backend_dir):
                # Skip __pycache__ and legacy dirs
                dirs[:] = [d for d in dirs if d not in ("__pycache__", "legacy", ".git")]
                for fname in files:
                    if fname.endswith(".py"):
                        fpath = os.path.join(root, fname)
                        total_files += 1
                        try:
                            with open(fpath, 'r', encoding='utf-8') as f:
                                content = f.read()
                                total_lines += len(content.split("\n"))
                                # Count functions
                                try:
                                    tree = ast.parse(content)
                                    for node in ast.walk(tree):
                                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                            total_functions += 1
                                except SyntaxError:
                                    pass
                        except Exception:
                            pass

        # Generate issues and opportunities
        if total_files > 0:
            suggested_improvements = [
                "مراجعة أداء المحركات واقتراح تحسينات",
                "تحديث التوثيق والتعليقات البرمجية",
                "تحسين معالجة الأخطاء في المكونات الحرجة",
                "إضافة اختبارات وحدة للمكونات الأساسية",
                "تحسين أمان النظام ومنع الوصول غير المصرح",
            ]

        health_score = min(1.0, total_files / 200) if total_files > 0 else 0.5
        complexity_score = min(1.0, total_functions / 500) if total_functions > 0 else 0.5

        self._dashboard_config = {
            "total_files": total_files,
            "total_lines": total_lines,
            "total_functions": total_functions,
            "health_score": health_score,
            "issues": len(issues),
            "opportunities": len(opportunities),
        }

        return SelfAnalysis(
            file_path="mamoun/",
            issues=issues,
            opportunities=opportunities,
            risk_level="low",
            confidence=0.8,
            total_files=total_files,
            total_lines=total_lines,
            total_functions=total_functions,
            health_score=health_score,
            complexity_score=complexity_score,
            suggested_improvements=suggested_improvements,
        )

    def get_proposal(self, modification_id: str) -> Optional[ModificationProposal]:
        """
        الحصول على مقترح — called by kernel.py /self-modify/{id}/approve.
        """
        return self._proposals_by_id.get(modification_id)

    def approve_proposal(self, modification_id: str, approver: str = "human") -> bool:
        """
        الموافقة على مقترح — called by kernel.py /self-modify/{id}/approve.
        """
        proposal = self._proposals_by_id.get(modification_id)
        if not proposal:
            return False
        if modification_id in self._rejected_proposals:
            return False
        self._approved_proposals.add(modification_id)
        proposal.status = ModificationStatus.VERIFIED
        return True

    def reject_proposal(self, modification_id: str) -> bool:
        """
        رفض مقترح — called by kernel.py /self-modify/{id}/reject.
        """
        if modification_id not in self._proposals_by_id:
            return False
        self._rejected_proposals.add(modification_id)
        proposal = self._proposals_by_id[modification_id]
        proposal.status = ModificationStatus.FAILED
        return True

    def _rebuild_dashboard_config(self) -> dict:
        """Rebuild dashboard config from current state."""
        return self._dashboard_config


# ── Singleton ───────────────────────────────────────────────────────────
_self_modifier_instance: Optional[SelfModifierAdapter] = None

def get_self_modifier(meta_cognition=None, neural_bus=None, llm_client=None) -> SelfModifierAdapter:
    """Get the singleton self modifier instance."""
    global _self_modifier_instance
    if _self_modifier_instance is None:
        _self_modifier_instance = SelfModifierAdapter(
            meta_cognition=meta_cognition,
            neural_bus=neural_bus,
            llm_client=llm_client,
        )
    return _self_modifier_instance

logger.info("self_modifier → redirected to super_brain/self_modifier (v62 full adapter)")
