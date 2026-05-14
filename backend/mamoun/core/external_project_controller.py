"""
BABSHARQII v62 — ExternalProjectController (BACKWARD-COMPATIBLE ADAPTER)

Redirects to super_brain/external_project_controller.py.
Note: The old version (2073 lines) had a full project manager.
The new version (442 lines) is simpler. Missing functionality
is being tracked for migration.

v62 FIX: Added get_external_project_controller() singleton getter
(used by external_project.py, main.py).
"""

import logging
from typing import Optional

logger = logging.getLogger("mamoun.core.external_project_controller")

from mamoun.core.super_brain.external_project_controller import (
    ExternalProjectController,
    ProjectInfo,
    FileChange,
)


# ── Singleton ───────────────────────────────────────────────────────────
_external_project_controller: Optional[ExternalProjectController] = None

def get_external_project_controller(llm_client=None, neural_bus=None,
                                     meta_cognition=None) -> ExternalProjectController:
    """Get the singleton ExternalProjectController instance (backward-compatible)."""
    global _external_project_controller
    if _external_project_controller is None:
        _external_project_controller = ExternalProjectController(
            llm_client=llm_client,
            neural_bus=neural_bus,
            meta_cognition=meta_cognition,
        )
    return _external_project_controller


logger.info("external_project_controller → redirected to super_brain/external_project_controller (v62 full adapter)")
