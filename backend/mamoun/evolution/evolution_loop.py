"""
BABSHARQII v61 — EvolutionLoop (BACKWARD-COMPATIBLE ADAPTER)

Redirects to super_brain/evolution_loop_v2.py.
Old: evolution/evolution_loop.py → New: core/super_brain/evolution_loop_v2.py

The old EvolutionLoop (v40, 5-phase loop with MutationEngine, FitnessEvaluator,
ProceduralMemory, etc.) has been superseded by EvolutionLoopV2 which integrates
with the super_brain kernel architecture.

The old implementation remains in the git history for reference.
New code should use EvolutionLoopV2 from super_brain.

Migration: evolution/evolution_loop.py → core/super_brain/evolution_loop_v2.py
Status: ADAPTER — re-exports EvolutionLoopV2 as EvolutionLoop for compatibility
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Re-export from the canonical super_brain implementation
from mamoun.core.super_brain.evolution_loop_v2 import (
    EvolutionStatus,
    EvolutionCycleResult,
    EvolutionLoopV2,
)

# Backward-compatible alias
EvolutionLoop = EvolutionLoopV2

logger.info("evolution/evolution_loop → redirected to super_brain/evolution_loop_v2")
