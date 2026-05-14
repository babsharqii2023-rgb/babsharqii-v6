"""
BABSHARQII v61 — ExternalProjectController (BACKWARD-COMPATIBLE ADAPTER)

Redirects to super_brain/external_project_controller.py.
Note: The old version (2073 lines) had a full project manager.
The new version (442 lines) is simpler. Missing functionality
is being tracked for migration.
"""

import logging

logger = logging.getLogger("mamoun.core.external_project_controller")

from mamoun.core.super_brain.external_project_controller import ExternalProjectController

logger.info("external_project_controller → redirected to super_brain/external_project_controller")
