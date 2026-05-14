"""
BABSHARQII v61 — ImprovementEngine (BACKWARD-COMPATIBLE ADAPTER)

Redirects to super_brain/improvement_proposer.py.
Old: core/improvement_engine.py → New: core/super_brain/improvement_proposer.py
"""

import logging

logger = logging.getLogger("mamoun.core.improvement_engine")

# Re-export from new module with backward-compatible names
from mamoun.core.super_brain.improvement_proposer import (
    ProposalPriority,
    ProposalStatus,
    ImprovementProposal,
    FeatureFlags,
    ImprovementProposer as ImprovementEngine,
)

logger.info("improvement_engine → redirected to super_brain/improvement_proposer")
