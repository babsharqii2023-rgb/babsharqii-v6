"""
BABSHARQII v61 — AgentCreator (BACKWARD-COMPATIBLE ADAPTER)

Redirects to super_brain/agent_creator.py.
Old: evolution/agent_creator.py → New: core/super_brain/agent_creator.py

The old AgentCreator (v13, with dynamic template generation, SandboxRunner
testing, AGIBridge registration) has been superseded by the super_brain version
which integrates with MetaCognition, NeuralBus, and health monitoring.

The old implementation remains in the git history for reference.
New code should use AgentCreator from super_brain.

Migration: evolution/agent_creator.py → core/super_brain/agent_creator.py
Status: ADAPTER — re-exports AgentCreator from super_brain
"""

import logging

logger = logging.getLogger(__name__)

# Re-export from the canonical super_brain implementation
from mamoun.core.super_brain.agent_creator import (
    AgentSpecification,
    AgentCreator,
)

# Backward-compatible constants
FORBIDDEN_CODE_PATTERNS = [
    r"os\.system\s*\(",
    r"subprocess\.",
    r"eval\s*\(",
    r"exec\s*\(",
    r"__import__\s*\(",
]

AGENTS_DIR = "agents"

logger.info("evolution/agent_creator → redirected to super_brain/agent_creator")
