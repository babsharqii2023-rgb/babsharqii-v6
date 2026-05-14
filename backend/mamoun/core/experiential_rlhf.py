"""
BABSHARQII v61 — ExperientialRLHF (BACKWARD-COMPATIBLE ADAPTER)

Redirects to super_brain/rlhf_bridge.py.
Old: core/experiential_rlhf.py → New: core/super_brain/rlhf_bridge.py
"""

import logging

logger = logging.getLogger("mamoun.core.experiential_rlhf")

from mamoun.core.super_brain.rlhf_bridge import (
    FeedbackType,
    RLHFPattern,
    FeedbackRecord,
    ImprovementSuggestion,
    RLHFBridge as ExperientialRLHF,
)

logger.info("experiential_rlhf → redirected to super_brain/rlhf_bridge")
