"""
BABSHARQII v13.0 — Voice Module
وحدة الصوت — تمكين مأمون من التحدث والاستماع بالعربية

Feature Flags:
- MAMOUN_TTS_ENABLED (default: false)
- MAMOUN_STT_ENABLED (default: false)
"""

import os

TTS_ENABLED = os.getenv("MAMOUN_TTS_ENABLED", "false").lower() in ("true", "1", "yes")
STT_ENABLED = os.getenv("MAMOUN_STT_ENABLED", "false").lower() in ("true", "1", "yes")
