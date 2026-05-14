"""
BABSHARQII v28.0-stable — Legacy Core Modules

This directory is for modules that are rarely used and will be
gradually phased out or refactored. Do NOT add new modules here.

Modules to migrate here in future versions:
  - desktop_controller.py (requires physical device)
  - embodiment_controller.py (requires robot/IoT)
  - state_reader.py (replaced by unified_db queries)
  - dashboard_builder.py (low usage)

Rule: Before moving a module here, update ALL import paths
      across the codebase and run tests to verify.
"""
