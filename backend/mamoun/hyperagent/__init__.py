"""
DGM-Hyperagent Architecture — v16.0
Based on: "Hyperagents" (Zhang et al., 2026) — arXiv:2603.19461
Meta AI Research — facebookresearch/hyperagents

Core Insight: "By integrating both functions into a single, self-referential program,
the framework enables the agent to modify any part of its own codebase."

Three-Layer Architecture (Triple Awareness Loop):
  Layer 1 (Task Agent): Performs tasks — current Mamoun behavior
  Layer 2 (Meta Agent): Monitors and improves the improvement mechanism itself
  Layer 3 (Supra-Meta Agent): Decides WHETHER to improve, WHERE to direct improvement energy,
                              and validates improvement trajectories long-term

Key Distinction from v40.0:
  - v40.0: SelfProgrammingLoop modifies code, but the mechanism of modification is FIXED
  - v16.0: MetaAgent can modify the mechanism of modification itself (metacognitive self-modification)
  - v16.0: SupraMetaAgent decides when NOT to modify (cognitive economy)
"""

from .meta_agent import MetaAgent
from .supra_meta_agent import SupraMetaAgent
from .hyperagent_loop import HyperagentLoop
from .evolution_archive import EvolutionArchive
from .curriculum_controller import CurriculumController
from .future_simulator import FutureSimulator

__all__ = [
    "MetaAgent",
    "SupraMetaAgent",
    "HyperagentLoop",
    "EvolutionArchive",
    "CurriculumController",
    "FutureSimulator",
]
