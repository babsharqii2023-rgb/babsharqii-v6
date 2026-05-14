"""
BABSHARQII v62 — MetacognitiveEngine (BACKWARD-COMPATIBLE ADAPTER)

Redirects to super_brain/meta_cognition_engine.py.
Old: core/metacognitive_engine.py → New: core/super_brain/meta_cognition_engine.py

v62 FIX: Added metacognitive_engine module-level singleton (used by agi_pillars.py, agi_orchestrator.py).
"""

import logging
from typing import Optional

logger = logging.getLogger("mamoun.core.metacognitive_engine")

# Re-export everything from the new module
from mamoun.core.super_brain.meta_cognition_engine import (
    OutcomeRecord,
    ComponentProfile,
    MetaCognitionEngine,
)


# ── Singleton ───────────────────────────────────────────────────────────
_metacognitive_engine: Optional[MetaCognitionEngine] = None

def get_metacognitive_engine() -> MetaCognitionEngine:
    """Get the global metacognitive engine singleton."""
    global _metacognitive_engine
    if _metacognitive_engine is None:
        _metacognitive_engine = MetaCognitionEngine()
    return _metacognitive_engine


# Module-level singleton for backward compatibility (imported by agi_pillars.py, agi_orchestrator.py)
class _MetacognitiveEngineModuleProxy:
    """Lazy proxy that provides module-level metacognitive_engine access."""
    def __getattr__(self, name):
        engine = get_metacognitive_engine()
        return getattr(engine, name)

metacognitive_engine = _MetacognitiveEngineModuleProxy()

logger.info("metacognitive_engine → redirected to super_brain/meta_cognition_engine (v62 full adapter)")
