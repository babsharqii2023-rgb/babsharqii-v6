"""
BABSHARQII v13.0 — Notifications Module
وحدة الإشعارات — إرسال إشعارات عبر قنوات متعددة

Feature Flag: MAMOUN_NOTIFICATIONS_ENABLED (default: false)
"""

import os

NOTIFICATIONS_ENABLED = os.getenv("MAMOUN_NOTIFICATIONS_ENABLED", "false").lower() in ("true", "1", "yes")
