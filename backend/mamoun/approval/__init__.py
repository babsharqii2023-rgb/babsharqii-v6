"""
BABSHARQII v13.0 — Approval Extensions
امتدادات الموافقة — طلبات الاحتياجات والفجوات المعرفية

Feature Flag: MAMOUN_METACOGNITIVE_PLANNING (default: false)
"""

import os

METACOGNITIVE_PLANNING_ENABLED = os.getenv("MAMOUN_METACOGNITIVE_PLANNING", "false").lower() in ("true", "1", "yes")
