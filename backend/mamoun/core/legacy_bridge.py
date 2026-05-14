"""
BABSHARQII v63 — Legacy Imports Bridge
This module provides backward-compatible imports for all old code paths
while delegating to the new super_brain/ and shared/ implementations.

MIGRATION STATUS: All old imports from core/ are redirected here
  - core/neural_bus → core/shared/neural_bus
  - core/llm_client → core/shared/multi_provider_llm
  - core/self_healing → core/super_brain/self_healing_bridge
  - core/mamoun_kernel → core/super_brain/mamoun_kernel (when available)
  - core/improvement_engine → core/super_brain/improvement_proposer (unified)

This file is the SINGLE SOURCE OF TRUTH for import compatibility.
"""

import warnings
import logging

logger = logging.getLogger("mamoun.core.legacy_bridge")

# ── NeuralBus: Unified → shared/neural_bus ──────────────────────────
# Old: from mamoun.core.neural_bus import neural_bus, NeuralBus
# New: from mamoun.core.shared.neural_bus import get_neural_bus
# The core/neural_bus.py file now acts as a full adapter (already done in v62)

# ── LLM Client: Unified → shared/multi_provider_llm ────────────────
# Old: from mamoun.core.llm_client import LLMClient, get_llm_client
# New: from mamoun.core.shared.multi_provider_llm import MultiProviderLLMClient, get_multi_provider_llm

def _bridge_llm_client():
    """Bridge LLMClient to MultiProviderLLMClient."""
    try:
        from mamoun.core.shared.multi_provider_llm import MultiProviderLLMClient
        return MultiProviderLLMClient
    except ImportError:
        try:
            from mamoun.core.llm_client import LLMClient
            return LLMClient
        except ImportError:
            return None

def get_llm_client():
    """Get the unified LLM client — tries shared first, falls back to legacy."""
    try:
        from mamoun.core.shared.multi_provider_llm import get_multi_provider_llm
        return get_multi_provider_llm()
    except (ImportError, Exception):
        try:
            from mamoun.core.llm_client import get_llm_client as _get_legacy
            return _get_legacy()
        except (ImportError, Exception):
            logger.warning("No LLM client available — neither shared nor legacy")
            return None

# ── Self-Healing: Unified → super_brain/self_healing_bridge ────────
def get_self_healing():
    """Get the self-healing engine — tries super_brain first, falls back to legacy."""
    try:
        from mamoun.core.super_brain.self_healing_bridge import SelfHealingBridge
        return SelfHealingBridge()
    except (ImportError, Exception):
        try:
            from mamoun.core.self_healing import self_healing
            return self_healing
        except (ImportError, Exception):
            logger.warning("No self-healing engine available")
            return None

# ── MamounKernel: Unified → super_brain/mamoun_kernel ──────────────
def get_kernel():
    """Get the MamounKernel — tries super_brain first, falls back to legacy."""
    try:
        from mamoun.core.mamoun_kernel import get_kernel as _get_legacy
        return _get_legacy()
    except (ImportError, Exception):
        try:
            from mamoun.core.super_brain.mamoun_kernel import MamounKernel
            return MamounKernel()
        except (ImportError, Exception):
            logger.warning("No kernel available")
            return None

# ── ImprovementProposer: Unified → super_brain/improvement_proposer ─
# This resolves the 3-version duplication:
#   1. core/improvement_engine.py (old)
#   2. core/super_brain/improvement_proposer.py (new canonical)
#   3. evolution/improvement_proposer.py (duplicate)
def get_improvement_proposer():
    """Get the unified improvement proposer."""
    try:
        from mamoun.core.super_brain.improvement_proposer import ImprovementProposer
        return ImprovementProposer
    except (ImportError, Exception):
        try:
            from mamoun.core.improvement_engine import ImprovementEngine
            return ImprovementEngine
        except (ImportError, Exception):
            return None

# ── Import Compatibility Registry ──────────────────────────────────
# Maps old import paths to new ones
IMPORT_MIGRATION_MAP = {
    'mamoun.core.neural_bus': 'mamoun.core.shared.neural_bus',
    'mamoun.core.llm_client': 'mamoun.core.shared.multi_provider_llm',
    'mamoun.core.self_healing': 'mamoun.core.super_brain.self_healing_bridge',
    'mamoun.core.mamoun_kernel': 'mamoun.core.super_brain.mamoun_kernel',
    'mamoun.core.improvement_engine': 'mamoun.core.super_brain.improvement_proposer',
    'mamoun.core.experiential_rlhf': 'mamoun.core.super_brain.rlhf_bridge',
    'mamoun.core.deep_research_engine': 'mamoun.core.super_brain.deep_research_engine',
}

def warn_deprecated_import(old_path: str):
    """Issue a deprecation warning for old import paths."""
    new_path = IMPORT_MIGRATION_MAP.get(old_path)
    if new_path:
        warnings.warn(
            f"Importing from '{old_path}' is deprecated. "
            f"Use '{new_path}' instead. "
            f"The old path will be removed in a future version.",
            DeprecationWarning,
            stacklevel=3,
        )

logger.info("Legacy bridge initialized — all old imports redirected to super_brain/shared")
