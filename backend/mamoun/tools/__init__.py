"""
BABSHARQII v12.0 — Tools Package
أدوات مأمون الآمنة — FileSystem + Shell + Agent Tools
"""

import os

# Feature flags
FILESYSTEM_ENABLED = os.getenv("MAMOUN_FILESYSTEM_TOOLS", "false").lower() == "true"
SHELL_EXECUTOR_ENABLED = os.getenv("MAMOUN_SHELL_EXECUTOR", "false").lower() == "true"

from mamoun.tools.filesystem_tool import FileSystemTool
from mamoun.tools.shell_executor import ShellExecutor

__all__ = [
    "FileSystemTool",
    "ShellExecutor",
    "FILESYSTEM_ENABLED",
    "SHELL_EXECUTOR_ENABLED",
]
