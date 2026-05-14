"""
BABSHARQII v61 — Evolution ImprovementProposer (BACKWARD-COMPATIBLE ADAPTER)

This file now redirects to super_brain/improvement_proposer.py.
The old evolution-specific logic is preserved in legacy/ for reference.

Migration: evolution/improvement_proposer.py → core/super_brain/improvement_proposer.py
Status: ADAPTER
"""

import logging

logger = logging.getLogger(__name__)

# Re-export from super_brain with backward compatibility
from mamoun.core.super_brain.improvement_proposer import (
    ProposalStatus,
    ImprovementProposal,
    ImprovementProposer,
)

# Also export the old status values that the evolution code may use
# Map old status values to new ones
DRAFT = ProposalStatus.DRAFT
SUBMITTED = ProposalStatus.SUBMITTED
APPROVED = ProposalStatus.APPROVED
REJECTED = ProposalStatus.REJECTED
APPLIED = ProposalStatus.APPLIED

logger.info("evolution/improvement_proposer → redirected to super_brain/improvement_proposer")
