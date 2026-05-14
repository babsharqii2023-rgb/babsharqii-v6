"""
BABSHARQII v40.0 — Human Collaboration Module
وحدة القيادة والتعاون مع البشر

Feature Flag: MAMOUN_HUMAN_COLLABORATION (default: false)
"""

import os

HUMAN_COLLABORATION_ENABLED = os.getenv(
    "MAMOUN_HUMAN_COLLABORATION", "false"
).lower() in ("true", "1", "yes")

from mamoun.human.collaboration_orchestrator import CollaborationOrchestrator
from mamoun.human.team_model import TeamModel

__all__ = ["CollaborationOrchestrator", "TeamModel"]
