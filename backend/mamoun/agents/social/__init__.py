"""
BABSHARQII v12.0 — Social Agents Package
وكلاء التواصل الاجتماعي — أتمتة الانستغرام
"""

import os

INSTAGRAM_ENABLED = os.getenv("MAMOUN_INSTAGRAM_AUTOMATION", "false").lower() == "true"

from mamoun.agents.social.instagram_manager import InstagramManager

__all__ = [
    "InstagramManager",
    "INSTAGRAM_ENABLED",
]
