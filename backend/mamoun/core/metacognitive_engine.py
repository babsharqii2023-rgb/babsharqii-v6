"""
BABSHARQII v61 — MetacognitiveEngine (BACKWARD-COMPATIBLE ADAPTER)

Redirects to super_brain/meta_cognition_engine.py.
Old: core/metacognitive_engine.py → New: core/super_brain/meta_cognition_engine.py
"""

import logging

logger = logging.getLogger("mamoun.core.metacognitive_engine")

# Re-export everything from the new module
from mamoun.core.super_brain.meta_cognition_engine import (
    OutcomeRecord,
    ComponentProfile,
    MetaCognitionEngine,
)

logger.info("metacognitive_engine → redirected to super_brain/meta_cognition_engine")
