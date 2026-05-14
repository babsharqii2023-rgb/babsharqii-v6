"""
BABSHARQII v18.0 — Mamoun Core Package
Phase 2: Self-Healing Engine + Self-Modification Engine
"""

from .code_patcher import CodePatcher, CodePatch, FileAnalysis
from .sandbox_runner import SandboxRunner, SandboxResult
from .safety_guard import SafetyGuard, SafetyViolation
from .triple_memory import TripleMemoryManager, triple_memory, MemoryEntry, SearchResult
from .self_modifier import (
    SelfModifier,
    ModificationProposal,
    ValidationResult,
    ApplyResult,
    RollbackResult,
    SelfAnalysis,
    ModificationRecord,
    get_self_modifier,
)

__all__ = [
    "CodePatcher",
    "CodePatch",
    "FileAnalysis",
    "SandboxRunner",
    "SandboxResult",
    "SafetyGuard",
    "SafetyViolation",
    "TripleMemoryManager",
    "triple_memory",
    "MemoryEntry",
    "SearchResult",
    "SelfModifier",
    "ModificationProposal",
    "ValidationResult",
    "ApplyResult",
    "RollbackResult",
    "SelfAnalysis",
    "ModificationRecord",
    "get_self_modifier",
]
