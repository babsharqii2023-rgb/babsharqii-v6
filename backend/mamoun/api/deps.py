"""
BABSHARQII v40.0 — Shared API Dependencies
Authentication, component singletons, and helper utilities used across all sub-routers.
VULN-023 Fix: Auth dependency added for sensitive routes.
v18.1 Fix: Removed module-level side effects — components now created lazily via getters.
  This prevents duplicate object creation between deps.py and main.py.
"""

import os as _os
import logging
from functools import lru_cache
from fastapi import APIRouter, HTTPException, Depends, Cookie, Header

logger = logging.getLogger(__name__)


# =============================================================================
# VULN-023 Fix: Authentication Dependency
# =============================================================================

from mamoun.core.auth import auth_manager


async def require_auth(
    mamoun_session: str = Cookie(default=""),
    authorization: str = Header(default=""),
):
    """FastAPI dependency that requires a valid admin session.
    v30.1 Fix: يدعم Cookie AND Bearer Token.
    Apply with: @router.get("/path", dependencies=[Depends(require_auth)])

    Accepts auth via:
    1. Cookie: mamoun_session=<token>
    2. Header: Authorization: Bearer <token>
    """
    token = mamoun_session

    # Fallback to Bearer token from Authorization header
    if not token and authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        elif authorization.startswith("bearer "):
            token = authorization[7:]

    if not token or not auth_manager.verify_token(token):
        raise HTTPException(
            status_code=401,
            detail="مطلوب تسجيل الدخول — جلسة غير صالحة. أرسل Cookie أو Bearer Token.",
        )
    return token


# =============================================================================
# Core Component Singletons — LAZY INITIALIZATION (v18.1 Fix)
# =============================================================================
# Previously these were module-level instantiations that caused duplicate objects
# when main.py also created them. Now they use @lru_cache to ensure singletons.

@lru_cache(maxsize=1)
def _get_state_reader():
    from mamoun.core.state_reader import StateReader
    return StateReader()

@lru_cache(maxsize=1)
def _get_meta_analyzer():
    from mamoun.core.meta_analyzer import MetaAnalyzer
    return MetaAnalyzer()

@lru_cache(maxsize=1)
def _get_journal():
    from mamoun.core.reflective_journal import ReflectiveJournal
    return ReflectiveJournal()

@lru_cache(maxsize=1)
def _get_code_patcher():
    from mamoun.core.code_patcher import CodePatcher
    return CodePatcher()

@lru_cache(maxsize=1)
def _get_sandbox_runner():
    from mamoun.core.sandbox_runner import SandboxRunner
    return SandboxRunner()

@lru_cache(maxsize=1)
def _get_safety_guard():
    from mamoun.core.safety_guard import SafetyGuard
    return SafetyGuard()

@lru_cache(maxsize=1)
def _get_approval_gate():
    from mamoun.core.approval_gate import ApprovalGate
    return ApprovalGate()

@lru_cache(maxsize=1)
def _get_data_manager():
    from mamoun.core.data_manager import data_manager
    return data_manager

@lru_cache(maxsize=1)
def _get_backup_manager():
    from mamoun.core.backup_manager import backup_manager
    return backup_manager

@lru_cache(maxsize=1)
def _get_mutation_engine():
    from mamoun.evolution.mutation_engine import MutationEngine
    return MutationEngine()

@lru_cache(maxsize=1)
def _get_fitness_evaluator():
    from mamoun.evolution.fitness_evaluator import FitnessEvaluator
    return FitnessEvaluator()

@lru_cache(maxsize=1)
def _get_procedural_memory():
    from mamoun.evolution.procedural_memory import ProceduralMemory
    return ProceduralMemory()

@lru_cache(maxsize=1)
def _get_evolution_loop():
    # v61: Use canonical super_brain EvolutionLoopV2 instead of old evolution_loop
    from mamoun.core.super_brain.evolution_loop_v2 import EvolutionLoopV2
    return EvolutionLoopV2(kernel=None)


# Module-level references — use lazy getters for backward compatibility
# Other modules import these, so they must exist. But they now delegate to cached getters.
# NOTE: We avoid calling the getters at module level to prevent import-time side effects.
# Instead, we create lightweight proxy objects that delegate on first use.

class _LazyProxy:
    """Lazy proxy that delegates to the real object on first attribute access."""
    def __init__(self, factory):
        object.__setattr__(self, '_factory', factory)
        object.__setattr__(self, '_instance', None)

    def _get_instance(self):
        inst = object.__getattribute__(self, '_instance')
        if inst is None:
            inst = object.__getattribute__(self, '_factory')()
            object.__setattr__(self, '_instance', inst)
        return inst

    def __getattr__(self, name):
        return getattr(self._get_instance(), name)

    def __setattr__(self, name, value):
        setattr(self._get_instance(), name, value)


# Backward-compatible module-level attributes — now lazy
state_reader = _LazyProxy(_get_state_reader)
meta_analyzer = _LazyProxy(_get_meta_analyzer)
journal = _LazyProxy(_get_journal)
code_patcher = _LazyProxy(_get_code_patcher)
sandbox_runner = _LazyProxy(_get_sandbox_runner)
safety_guard = _LazyProxy(_get_safety_guard)
approval_gate = _LazyProxy(_get_approval_gate)
mutation_engine = _LazyProxy(_get_mutation_engine)
fitness_evaluator = _LazyProxy(_get_fitness_evaluator)
procedural_memory = _LazyProxy(_get_procedural_memory)
evolution_loop = _LazyProxy(_get_evolution_loop)

# v17.0: Living brains — do NOT create here; main.py creates and registers them
# These are kept as None since main.py owns brain lifecycle
brains = []
instincts = []

# Master API router — sub-modules attach their own routers here
api_router = APIRouter()


# =============================================================================
# Helper: AGI module availability check
# =============================================================================

def _is_agi_module_enabled(env_var: str) -> bool:
    """Check if an AGI module is enabled via environment variable."""
    return _os.getenv(env_var, "false").lower() == "true"


# =============================================================================
# Helper: Persist environment variable to .env file
# =============================================================================

def _persist_env_var(env_path: str, key: str, value: str):
    """Persist an environment variable to .env file."""
    lines = []
    if _os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


# =============================================================================
# Kernel Access — central brain reference
# =============================================================================

@lru_cache(maxsize=1)
def get_kernel():
    """Get the global kernel instance — delegates to mamoun_kernel.get_kernel()."""
    from mamoun.core.mamoun_kernel import get_kernel as _get_kernel
    return _get_kernel()
