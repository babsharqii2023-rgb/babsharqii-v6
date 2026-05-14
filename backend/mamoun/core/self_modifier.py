"""
BABSHARQII v61 — SelfModifier (BACKWARD-COMPATIBLE ADAPTER)

Redirects to super_brain/self_modifier.py.
Old: core/self_modifier.py → New: core/super_brain/self_modifier.py

The old SelfModifier implementation (with SelfAnalysis, independent
analyze/propose/validate/apply) has been moved to core/legacy/self_modifier.py.
All functionality now delegates to the canonical super_brain implementation.

Migration: core/self_modifier.py → core/super_brain/self_modifier.py
Status: ADAPTER — all calls forwarded to super_brain SelfModifier
"""

import logging
from typing import Optional

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
# Old API used different class names — map them to the new ones
ValidationResult = ModificationProposal  # Old: ValidationResult → New: Use ModificationProposal
ApplyResult = ModificationProposal       # Old: ApplyResult → New: Use ModificationProposal
RollbackResult = ModificationProposal    # Old: RollbackResult → New: Use ModificationProposal


class SelfAnalysis:
    """Backward-compatible SelfAnalysis (preserved for old API)."""
    def __init__(self, file_path: str = "", issues: list = None,
                 opportunities: list = None, risk_level: str = "low",
                 confidence: float = 0.0):
        self.file_path = file_path
        self.issues = issues or []
        self.opportunities = opportunities or []
        self.risk_level = risk_level
        self.confidence = confidence


class ModificationRecord:
    """Backward-compatible ModificationRecord (preserved for old API)."""
    def __init__(self, proposal=None, validation=None, apply_result=None,
                 timestamp: float = 0.0, rolled_back: bool = False):
        self.proposal = proposal
        self.validation = validation
        self.apply_result = apply_result
        self.timestamp = timestamp
        self.rolled_back = rolled_back


# ── Singleton ───────────────────────────────────────────────────────────
_self_modifier_instance: Optional[SelfModifier] = None

def get_self_modifier(meta_cognition=None, neural_bus=None, llm_client=None) -> SelfModifier:
    """Get the singleton self modifier instance."""
    global _self_modifier_instance
    if _self_modifier_instance is None:
        _self_modifier_instance = SelfModifier(
            meta_cognition=meta_cognition,
            neural_bus=neural_bus,
            llm_client=llm_client,
        )
    return _self_modifier_instance

logger.info("self_modifier → redirected to super_brain/self_modifier")
