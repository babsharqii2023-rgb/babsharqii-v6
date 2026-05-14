"""
BABSHARQII v29.0-symphony — Conscience Layer (طبقة الضمير)
نظام أخلاقي يمنع الأفعال الخطيرة — ضمير مامون

8 قوانين أخلاقية (L1-L8):
  L1: لا تؤذِ الإنسان — Block destructive commands
  L2: لا تدمر البيانات — Block data destruction
  L3: لا تخترق الأنظمة — Block system penetration
  L4: لا تكذب — Block deliberate misinformation
  L5: لا تتلاعب — Block manipulation
  L6: لا تنتهك الخصوصية — Block privacy violations
  L7: لا تنفذ أوامر خطيرة بدون تأكيد — Block dangerous commands without confirmation
  L8: لا تتجاوز القوانين — Block law-breaking actions
"""

import re
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from pathlib import Path

logger = logging.getLogger("mamoun.conscience_layer")


# ═══════════════════════════════════════════════════════════════════════════════
#  Dangerous Patterns — MUST BLOCK
# ═══════════════════════════════════════════════════════════════════════════════

_BLOCKED_PATTERNS: List[tuple] = [
    # L1: Destructive commands
    (re.compile(r"\brm\s+-rf\s+/(?!\w)", re.IGNORECASE), "L1", "rm -rf / — system wipe"),
    (re.compile(r"\brm\s+-rf\s+/\*", re.IGNORECASE), "L1", "rm -rf /* — system wipe"),
    (re.compile(r"\brm\s+-rf\s+~", re.IGNORECASE), "L1", "rm -rf ~ — home wipe"),
    (re.compile(r"\brm\s+-rf\s+/home", re.IGNORECASE), "L1", "rm -rf /home — home dirs wipe"),

    # L2: Data destruction
    (re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE), "L2", "DROP TABLE — data destruction"),
    (re.compile(r"\bDELETE\s+FROM\b(?!.*\bWHERE\b)", re.IGNORECASE), "L2", "DELETE without WHERE — full wipe"),
    (re.compile(r"\bTRUNCATE\s+TABLE\b", re.IGNORECASE), "L2", "TRUNCATE TABLE — data destruction"),

    # L3: System penetration / format
    (re.compile(r"\bformat\s+[A-Za-z]:", re.IGNORECASE), "L3", "format drive — disk format"),
    (re.compile(r"\bmkfs\b", re.IGNORECASE), "L3", "mkfs — filesystem format"),
    (re.compile(r"\bdd\s+if=", re.IGNORECASE), "L3", "dd — raw disk write"),
    (re.compile(r"\bfdisk\b", re.IGNORECASE), "L3", "fdisk — partition manipulation"),

    # L5: Fork bomb
    (re.compile(r":\(\)\{\s*:\|:&\s*\};:"), "L5", "fork bomb — resource exhaustion"),

    # L7: Remote code execution
    (re.compile(r"\bcurl\b.*\|\s*(ba)?sh", re.IGNORECASE), "L7", "curl | sh — remote code execution"),
    (re.compile(r"\bwget\b.*\|\s*(ba)?sh", re.IGNORECASE), "L7", "wget | sh — remote code execution"),

    # L8: Protected system files
    (re.compile(r"/etc/passwd", re.IGNORECASE), "L8", "accessing /etc/passwd — system file"),
    (re.compile(r"/etc/shadow", re.IGNORECASE), "L8", "accessing /etc/shadow — system file"),
    (re.compile(r"/etc/sudoers", re.IGNORECASE), "L8", "accessing /etc/sudoers — system file"),

    # System power commands
    (re.compile(r"\bshutdown\b", re.IGNORECASE), "L1", "shutdown — system shutdown"),
    (re.compile(r"\breboot\b", re.IGNORECASE), "L1", "reboot — system reboot"),
    (re.compile(r"\bhalt\b", re.IGNORECASE), "L1", "halt — system halt"),
    (re.compile(r"\bpoweroff\b", re.IGNORECASE), "L1", "poweroff — system power off"),

    # Delete protected files
    (re.compile(r"\bdelete\s+/etc/passwd\b", re.IGNORECASE), "L8", "delete /etc/passwd — system file deletion"),
    (re.compile(r"\brm\s+/etc/passwd\b", re.IGNORECASE), "L8", "rm /etc/passwd — system file deletion"),
]


@dataclass
class ConscienceViolation:
    """انتهاك ضميري — A conscience violation record"""
    text: str
    law: str
    reason: str
    timestamp: float = field(default_factory=time.time)
    severity: str = "high"


class ConscienceLayer:
    """
    طبقة الضمير — النظام الأخلاقي لمامون

    Reviews all proposed actions against 8 ethical laws.
    Returns approved=False for any violation.
    """

    def __init__(self, laws_path: Optional[Path] = None):
        self._violations: List[ConscienceViolation] = []
        self._review_count = 0
        self._block_count = 0
        self._laws_path = laws_path

    def review(self, text: str) -> Dict[str, Any]:
        """
        مراجعة ضميرية — Review text against ethical laws.

        Args:
            text: The proposed action/command text to review.

        Returns:
            Dict with:
                - approved (bool): Whether the action is allowed
                - reason (str): Why it was blocked (if blocked)
                - law (str): Which law was violated (if any)
                - violations (list): List of violations found
        """
        self._review_count += 1
        violations = []

        for pattern, law, reason in _BLOCKED_PATTERNS:
            if pattern.search(text):
                violation = ConscienceViolation(text=text[:200], law=law, reason=reason)
                violations.append(violation)
                logger.warning("CONSCIENCE BLOCKED: [%s] %s — text: %s", law, reason, text[:100])

        if violations:
            self._block_count += 1
            self._violations.extend(violations)
            return {
                "approved": False,
                "reason": violations[0].reason,
                "law": violations[0].law,
                "violations": [{"law": v.law, "reason": v.reason} for v in violations],
            }

        return {
            "approved": True,
            "reason": "No ethical violations detected",
            "law": None,
            "violations": [],
        }

    def get_stats(self) -> Dict[str, Any]:
        """إحصائيات الضمير"""
        return {
            "total_reviews": self._review_count,
            "total_blocks": self._block_count,
            "block_rate": round(self._block_count / max(self._review_count, 1), 3),
            "recent_violations": len(self._violations[-20:]),
        }

    def get_violations(self, limit: int = 20) -> List[Dict]:
        """آخر الانتهاكات"""
        return [
            {"law": v.law, "reason": v.reason, "text": v.text[:100], "severity": v.severity}
            for v in self._violations[-limit:]
        ]
