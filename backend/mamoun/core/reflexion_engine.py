"""
BABSHARQII v24.0 — ReflexionEngine
محرك التأمل الانعكاسي — المراجعة الأمنية الإلزامية قبل وبعد التنفيذ

This is the CRITICAL security component that BLOCKS dangerous actions,
not just logs them. Every action proposed by any brain or executor must
pass through review_action() BEFORE execution and post_review() AFTER.

Architecture:
  ┌─────────────────────────────────────────────────────────────┐
  │                  REFLEXION ENGINE                             │
  │                                                              │
  │  1. REVIEW   ← Pre-action security screening (BLOCK/BLOCK)   │
  │  2. DETECT   ← Dangerous command pattern matching            │
  │  3. ASSESS   ← Risk level assignment based on tool + params  │
  │  4. ESCALATE ← High/critical risk → mandatory block          │
  │  5. LEARN    ← Post-action feedback → brain confidence adj.  │
  │  6. REMEMBER ← Persist patterns, reviews, confidence to DB   │
  └─────────────────────────────────────────────────────────────┘

Based on:
  - Reflexion (Shinn et al., 2023): Generate → Reflect → Refine
  - Metacognitive Reflective CoT (2026): Monitor → Reflect → Correct
  - Constitutional AI (Bai et al., 2022): Self-critique + revision

CRITICAL: This engine BLOCKS, not just logs. If review_action() returns
approved=False, the action MUST NOT proceed. No override except explicit
human approval through the approval gate.

BUG-003 FIX: initialize() returns False on failure instead of swallowing
exceptions.
"""

import re
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.reflexion_engine")


# ═══════════════════════════════════════════════════════════════════════════════
#  Data Models
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ReviewResult:
    """
    نتيجة مراجعة الفعل — The result of reviewing a proposed action.

    Attributes:
        approved: Whether the action is allowed to proceed.
        reason: Human-readable explanation of the decision.
        alternative: A safer alternative action, if available.
        confidence: How confident the engine is in this decision (0.0–1.0).
    """
    approved: bool
    reason: str
    alternative: Optional[Dict[str, Any]] = None
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "approved": self.approved,
            "reason": self.reason,
            "alternative": self.alternative,
            "confidence": self.confidence,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  Dangerous Command Patterns — MUST BLOCK
# ═══════════════════════════════════════════════════════════════════════════════

# Each entry: (compiled_regex, block_reason)
_DANGEROUS_COMMAND_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # Destructive rm commands
    (re.compile(r"\brm\s+-rf\s+/(?!\w)"), "BLOCKED: rm -rf / — system wipe"),
    (re.compile(r"\brm\s+-rf\s+/\*"), "BLOCKED: rm -rf /* — system wipe"),
    (re.compile(r"\brm\s+-rf\s+~"), "BLOCKED: rm -rf ~ — home directory wipe"),
    (re.compile(r"\brm\s+-rf\s+/home"), "BLOCKED: rm -rf /home — home directories wipe"),
    # Disk/device destruction
    (re.compile(r"\bdd\s+if="), "BLOCKED: dd if= — raw disk write"),
    (re.compile(r"\bmkfs\b"), "BLOCKED: mkfs — filesystem format"),
    (re.compile(r"\bfdisk\b"), "BLOCKED: fdisk — partition manipulation"),
    (re.compile(r"\bformat\b"), "BLOCKED: format — disk format"),
    # Fork bomb
    (re.compile(r":\(\)\{\s*:\|:&\s*\};:"), "BLOCKED: fork bomb detected"),
    # Dangerous chmod
    (re.compile(r"\bchmod\s+777\s+/"), "BLOCKED: chmod 777 / — world-writable root"),
    (re.compile(r"\bchmod\s+-R\s+777\s+/"), "BLOCKED: chmod -R 777 / — recursive world-writable root"),
    # Write to block devices
    (re.compile(r">\s*/dev/sd"), "BLOCKED: write to /dev/sd — block device"),
    (re.compile(r">\s*/dev/hd"), "BLOCKED: write to /dev/hd — block device"),
    # System shutdown/power commands
    (re.compile(r"\bshutdown\b"), "BLOCKED: shutdown — system shutdown"),
    (re.compile(r"\breboot\b"), "BLOCKED: reboot — system reboot"),
    (re.compile(r"\bhalt\b"), "BLOCKED: halt — system halt"),
    (re.compile(r"\bpoweroff\b"), "BLOCKED: poweroff — system power off"),
    # Piped remote execution
    (re.compile(r"\bcurl\b.*\|\s*(ba)?sh"), "BLOCKED: curl | sh — remote code execution"),
    (re.compile(r"\bwget\b.*\|\s*(ba)?sh"), "BLOCKED: wget | sh — remote code execution"),
]

# Critical system files that must never be written to
_PROTECTED_FILE_PATHS = [
    "/etc/passwd",
    "/etc/shadow",
    "/etc/sudoers",
]

# SQL injection patterns
_DANGEROUS_SQL_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE), "BLOCKED: DROP TABLE — destructive SQL"),
    (re.compile(r"\bDELETE\s+FROM\b(?!.*\bWHERE\b)", re.IGNORECASE),
     "BLOCKED: DELETE FROM without WHERE — full table wipe"),
]

# Tool-based risk ranking (lower number = higher inherent risk)
_TOOL_RISK_RANK = {
    "terminal_execute": 1,
    "shell_execute": 1,
    "file_write": 2,
    "file_delete": 1,
    "code_execute": 1,
    "sql_execute": 2,
    "memory_store": 4,
    "llm_think": 5,
    "llm_generate": 5,
    "web_search": 5,
    "memory_recall": 5,
    "notify_user": 5,
}

# Allowed directories for file_write operations (sandbox)
_PROJECT_ROOT = str(Path(__file__).parent.parent.parent.parent)
_DEFAULT_ALLOWED_DIRS = [
    _PROJECT_ROOT,
    "/tmp/mamoun",
    "/tmp/pytest",  # Test directories
]


# ═══════════════════════════════════════════════════════════════════════════════
#  ReflexionEngine
# ═══════════════════════════════════════════════════════════════════════════════

class ReflexionEngine:
    """
    محرك التأمل الانعكاسي — المراجعة الأمنية الإلزامية

    Called BEFORE any execution via review_action() to determine whether
    an action is safe. Called AFTER execution via post_review() to learn
    from outcomes and adjust internal confidence models.

    This engine BLOCKS dangerous actions — it does NOT just log them.
    """

    def __init__(self, db_path: Optional[Path] = None, allowed_dirs: Optional[List[str]] = None):
        self._db_path = db_path or UNIFIED_DB_PATH
        self._allowed_dirs = allowed_dirs or list(_DEFAULT_ALLOWED_DIRS)
        self._initialized = False
        self._review_count = 0
        self._block_count = 0

    # ═════════════════════════════════════════════════════════════════════════
    #  Initialization — BUG-003 FIX: return False on failure
    # ═════════════════════════════════════════════════════════════════════════

    def initialize(self) -> bool:
        """
        تهيئة محرك التأمل — Create DB tables and load learned patterns.

        BUG-003 FIX: Returns False on failure instead of swallowing
        exceptions. Previous version caught all exceptions and returned
        True regardless, masking initialization failures.

        Returns:
            True if initialization succeeded, False if it failed.
        """
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._ensure_schema()
            self._load_state()
            self._initialized = True
            logger.info("ReflexionEngine initialized — ready to BLOCK dangerous actions")
            return True
        except Exception as e:
            logger.error("ReflexionEngine initialization FAILED: %s", e)
            self._initialized = False
            return False

    def _ensure_schema(self) -> None:
        """Create rf_ prefixed tables if they don't exist."""
        conn = get_db_connection(self._db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS rf_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                tool TEXT NOT NULL,
                params TEXT DEFAULT '{}',
                risk_level TEXT NOT NULL,
                source TEXT DEFAULT '',
                approved INTEGER NOT NULL,
                reason TEXT DEFAULT '',
                alternative TEXT,
                confidence REAL DEFAULT 1.0,
                override TEXT DEFAULT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS rf_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL,
                category TEXT NOT NULL,
                severity TEXT DEFAULT 'high',
                block_reason TEXT DEFAULT '',
                learned_at REAL DEFAULT 0,
                occurrence_count INTEGER DEFAULT 1,
                last_seen REAL DEFAULT 0
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS rf_brain_confidence (
                brain_id TEXT PRIMARY KEY,
                confidence REAL DEFAULT 0.5,
                total_actions INTEGER DEFAULT 0,
                successful_actions INTEGER DEFAULT 0,
                failed_actions INTEGER DEFAULT 0,
                last_updated REAL DEFAULT 0
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS rf_state (
                key TEXT PRIMARY KEY,
                value TEXT
            )""")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rf_reviews_ts ON rf_reviews(timestamp)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rf_reviews_tool ON rf_reviews(tool)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rf_patterns_category ON rf_patterns(category)"
            )
            conn.commit()
        finally:
            conn.close()

    def _load_state(self) -> None:
        """Load persisted state counters."""
        conn = get_db_connection(self._db_path)
        try:
            cur = conn.execute("SELECT key, value FROM rf_state")
            for row in cur.fetchall():
                if row["key"] == "review_count":
                    self._review_count = int(row["value"])
                elif row["key"] == "block_count":
                    self._block_count = int(row["value"])
        finally:
            conn.close()

    # ═════════════════════════════════════════════════════════════════════════
    #  review_action() — Pre-execution Security Screening
    # ═════════════════════════════════════════════════════════════════════════

    def review_action(self, action: Dict[str, Any]) -> ReviewResult:
        """
        مراجعة الفعل قبل التنفيذ — Review an action BEFORE execution.

        This is the main gate. If it returns approved=False, the action
        MUST NOT be executed. No exceptions.

        Args:
            action: Dict with keys:
                - tool (str): The tool/engine being called.
                - params (dict): Parameters for the action.
                - risk_level (str): "low" / "medium" / "high" / "critical".
                - source (str): The brain or module proposing this action.

        Returns:
            ReviewResult with approved, reason, alternative, confidence.
        """
        if not self._initialized:
            self.initialize()

        tool = action.get("tool", "")
        params = action.get("params", {})
        risk_level = action.get("risk_level", "medium")
        source = action.get("source", "unknown")

        self._review_count += 1

        # ── Step 1: Dangerous command detection (terminal/shell) ─────────
        if tool in ("terminal_execute", "shell_execute"):
            command = params.get("command", "")
            if command:
                block_result = self._check_dangerous_command(command)
                if block_result is not None:
                    self._record_review(tool, params, risk_level, source,
                                        approved=False, reason=block_result.reason,
                                        confidence=block_result.confidence)
                    self._block_count += 1
                    return block_result

        # ── Step 2: Protected file path detection (file_write) ───────────
        if tool == "file_write":
            file_path = params.get("path", params.get("file_path", ""))
            if file_path:
                path_result = self._check_protected_path(file_path, params)
                if path_result is not None:
                    self._record_review(tool, params, risk_level, source,
                                        approved=False, reason=path_result.reason,
                                        confidence=path_result.confidence)
                    self._block_count += 1
                    return path_result

        # ── Step 3: SQL injection detection ──────────────────────────────
        if tool in ("sql_execute", "database_query"):
            query = params.get("query", params.get("sql", ""))
            if query:
                sql_result = self._check_dangerous_sql(query)
                if sql_result is not None:
                    self._record_review(tool, params, risk_level, source,
                                        approved=False, reason=sql_result.reason,
                                        confidence=sql_result.confidence)
                    self._block_count += 1
                    return sql_result

        # ── Step 4: Escalation ladder — high/critical risk BLOCK ─────────
        if risk_level in ("high", "critical"):
            logger.warning(
                "ESCALATION: Blocking high/critical risk action from %s — tool=%s risk=%s",
                source, tool, risk_level,
            )
            reason = (
                f"Action blocked by escalation ladder: risk_level={risk_level}. "
                f"Requires explicit human override through approval gate."
            )
            alternative = self._suggest_alternative(tool, params)
            self._record_review(tool, params, risk_level, source,
                                approved=False, reason=reason, confidence=0.95)
            self._block_count += 1
            return ReviewResult(
                approved=False,
                reason=reason,
                alternative=alternative,
                confidence=0.95,
            )

        # ── Step 5: Risk assessment based on tool + params ───────────────
        assessed_risk = self._assess_risk(tool, params)

        # Check if similar actions have failed before (history-based)
        history_factor = self._get_history_risk_factor(tool, params, source)
        assessed_risk = max(assessed_risk, history_factor)

        # Medium risk with suspicious params → block
        if assessed_risk == "high" and risk_level != "high":
            reason = (
                f"Action assessed as high-risk despite nominal risk_level={risk_level}. "
                f"Tool={tool} params contain elevated risk indicators."
            )
            self._record_review(tool, params, risk_level, source,
                                approved=False, reason=reason, confidence=0.8)
            self._block_count += 1
            return ReviewResult(
                approved=False,
                reason=reason,
                alternative=self._suggest_alternative(tool, params),
                confidence=0.8,
            )

        # ── Step 6: Passed all checks — approve ──────────────────────────
        reason = f"Action approved: tool={tool}, assessed_risk={assessed_risk}"
        self._record_review(tool, params, risk_level, source,
                            approved=True, reason=reason, confidence=0.9)
        return ReviewResult(
            approved=True,
            reason=reason,
            confidence=0.9,
        )

    # ═════════════════════════════════════════════════════════════════════════
    #  post_review() — Post-execution Learning
    # ═════════════════════════════════════════════════════════════════════════

    def post_review(
        self,
        action: Dict[str, Any],
        result: Any,
        succeeded: bool,
    ) -> Dict[str, Any]:
        """
        مراجعة بعد التنفيذ — Learn from the outcome of an executed action.

        Updates brain confidence scores and records lessons learned.

        Args:
            action: The action dict that was reviewed and executed.
            result: The result of the execution.
            succeeded: Whether the execution succeeded.

        Returns:
            Dict with learning summary.
        """
        if not self._initialized:
            self.initialize()

        source = action.get("source", "unknown")
        tool = action.get("tool", "unknown")

        # ── Update brain confidence ──────────────────────────────────────
        confidence_delta = 0.05 if succeeded else -0.10
        new_confidence = self._update_brain_confidence(source, confidence_delta)

        # ── If failed, record the failure pattern ────────────────────────
        lesson = ""
        if not succeeded:
            error_str = str(result)[:500] if result else "unknown error"
            lesson = (
                f"Action from {source} failed: tool={tool}, "
                f"error={error_str[:200]}"
            )
            self._record_pattern(
                pattern=f"failure:{tool}:{source}",
                category="action_failure",
                severity="medium",
                block_reason=lesson,
            )
            logger.info(
                "Post-review: Decreased confidence for brain '%s' to %.3f (failed action)",
                source, new_confidence,
            )
        else:
            logger.debug(
                "Post-review: Increased confidence for brain '%s' to %.3f",
                source, new_confidence,
            )

        # ── If an approved action caused damage, learn the pattern ───────
        if succeeded and self._looks_dangerous_in_retrospect(action, result):
            self._record_pattern(
                pattern=f"retrospective:{tool}",
                category="retrospective_danger",
                severity="high",
                block_reason=f"Action appeared safe but had dangerous outcome: tool={tool}",
            )

        return {
            "brain_id": source,
            "confidence": new_confidence,
            "succeeded": succeeded,
            "lesson": lesson,
        }

    # ═════════════════════════════════════════════════════════════════════════
    #  Dangerous Command Detection
    # ═════════════════════════════════════════════════════════════════════════

    def _check_dangerous_command(self, command: str) -> Optional[ReviewResult]:
        """
        Check a terminal command against all dangerous patterns.

        Returns ReviewResult with approved=False if a dangerous pattern
        is matched, or None if the command appears safe.
        """
        # Check compiled patterns
        for pattern, reason in _DANGEROUS_COMMAND_PATTERNS:
            if pattern.search(command):
                logger.warning("DANGEROUS COMMAND BLOCKED: %s — command: %s", reason, command[:200])
                return ReviewResult(
                    approved=False,
                    reason=reason,
                    alternative={"tool": "llm_think", "params": {"prompt": f"Safe alternative for: {command[:100]}"}},
                    confidence=1.0,
                )

        # Check learned patterns from DB
        learned_result = self._check_learned_patterns(command, "command")
        if learned_result is not None:
            return learned_result

        return None

    def _check_protected_path(self, file_path: str, params: Dict) -> Optional[ReviewResult]:
        """
        Check if a file_write target is outside allowed directories
        or targets a protected system file.
        """
        resolved = str(Path(file_path).resolve())

        # Check protected system files
        for protected in _PROTECTED_FILE_PATHS:
            if resolved.startswith(protected) or file_path.startswith(protected):
                reason = f"BLOCKED: Writing to protected system file: {file_path}"
                logger.warning(reason)
                return ReviewResult(
                    approved=False,
                    reason=reason,
                    alternative=None,
                    confidence=1.0,
                )

        # Check sandbox boundaries
        in_allowed = any(resolved.startswith(allowed) for allowed in self._allowed_dirs)
        if not in_allowed:
            reason = (
                f"BLOCKED: file_write target outside sandbox: {file_path}. "
                f"Allowed directories: {self._allowed_dirs}"
            )
            logger.warning(reason)
            safe_dir = self._allowed_dirs[0] if self._allowed_dirs else "/tmp/mamoun"
            return ReviewResult(
                approved=False,
                reason=reason,
                alternative={
                    "tool": "file_write",
                    "params": {**params, "path": f"{safe_dir}/{Path(file_path).name}"},
                },
                confidence=0.95,
            )

        return None

    def _check_dangerous_sql(self, query: str) -> Optional[ReviewResult]:
        """Check SQL query for destructive patterns."""
        for pattern, reason in _DANGEROUS_SQL_PATTERNS:
            if pattern.search(query):
                logger.warning("DANGEROUS SQL BLOCKED: %s — query: %s", reason, query[:200])
                return ReviewResult(
                    approved=False,
                    reason=reason,
                    alternative=None,
                    confidence=1.0,
                )
        return None

    def _check_learned_patterns(self, text: str, category: str) -> Optional[ReviewResult]:
        """Check text against learned dangerous patterns from the DB."""
        conn = get_db_connection(self._db_path)
        try:
            cur = conn.execute(
                "SELECT pattern, block_reason, severity FROM rf_patterns WHERE category = ? AND severity IN ('high', 'critical')",
                (category,),
            )
            for row in cur.fetchall():
                try:
                    if re.search(row["pattern"], text, re.IGNORECASE):
                        return ReviewResult(
                            approved=False,
                            reason=row["block_reason"] or f"Learned dangerous pattern: {row['pattern']}",
                            alternative=None,
                            confidence=0.9,
                        )
                except re.error:
                    continue  # Skip invalid regex patterns
        finally:
            conn.close()
        return None

    # ═════════════════════════════════════════════════════════════════════════
    #  Risk Assessment
    # ═════════════════════════════════════════════════════════════════════════

    def _assess_risk(self, tool: str, params: Dict) -> str:
        """
        Assess risk level based on tool type and parameter patterns.

        Returns: "low", "medium", "high", or "critical"
        """
        # Base risk from tool type
        tool_rank = _TOOL_RISK_RANK.get(tool, 3)
        if tool_rank <= 1:
            base_risk = "high"
        elif tool_rank <= 2:
            base_risk = "medium"
        elif tool_rank <= 3:
            base_risk = "medium"
        else:
            base_risk = "low"

        # Elevate risk based on parameter patterns
        command = params.get("command", "")
        query = params.get("query", params.get("sql", ""))

        # Check for pipes and redirects in commands
        if command and ("|" in command or ">" in command or "sudo" in command):
            if base_risk == "low":
                base_risk = "medium"
            elif base_risk == "medium":
                base_risk = "high"

        # Check for sudo
        if command and "sudo" in command:
            base_risk = "high"

        return base_risk

    def _get_history_risk_factor(self, tool: str, params: Dict, source: str) -> str:
        """
        Check if similar actions from this source have failed before.
        If previous similar actions failed, elevate the risk level.
        """
        conn = get_db_connection(self._db_path)
        try:
            # Check brain confidence — low confidence = higher risk
            cur = conn.execute(
                "SELECT confidence, failed_actions, total_actions FROM rf_brain_confidence WHERE brain_id = ?",
                (source,),
            )
            row = cur.fetchone()
            if row:
                confidence = row["confidence"]
                if confidence < 0.3:
                    return "high"
                elif confidence < 0.5:
                    return "medium"
            return "low"
        finally:
            conn.close()

    # ═════════════════════════════════════════════════════════════════════════
    #  Learning & Confidence Updates
    # ═════════════════════════════════════════════════════════════════════════

    def _update_brain_confidence(self, brain_id: str, delta: float) -> float:
        """
        Update the confidence score for a brain.

        Increases confidence for successful actions, decreases for failures.
        Confidence is clamped to [0.0, 1.0].

        Returns the new confidence value.
        """
        conn = get_db_connection(self._db_path)
        try:
            cur = conn.execute(
                "SELECT confidence, total_actions, successful_actions, failed_actions FROM rf_brain_confidence WHERE brain_id = ?",
                (brain_id,),
            )
            row = cur.fetchone()

            if row:
                new_confidence = max(0.0, min(1.0, row["confidence"] + delta))
                total = row["total_actions"] + 1
                success = row["successful_actions"] + (1 if delta > 0 else 0)
                failed = row["failed_actions"] + (1 if delta < 0 else 0)
                conn.execute(
                    """UPDATE rf_brain_confidence
                       SET confidence = ?, total_actions = ?, successful_actions = ?,
                           failed_actions = ?, last_updated = ?
                       WHERE brain_id = ?""",
                    (new_confidence, total, success, failed, time.time(), brain_id),
                )
            else:
                new_confidence = max(0.0, min(1.0, 0.5 + delta))
                conn.execute(
                    """INSERT INTO rf_brain_confidence
                       (brain_id, confidence, total_actions, successful_actions, failed_actions, last_updated)
                       VALUES (?, ?, 1, ?, ?, ?)""",
                    (brain_id, new_confidence, 1 if delta > 0 else 0, 1 if delta < 0 else 0, time.time()),
                )

            conn.commit()
            return new_confidence
        finally:
            conn.close()

    def _record_pattern(self, pattern: str, category: str, severity: str, block_reason: str) -> None:
        """Record a learned dangerous pattern for future matching."""
        conn = get_db_connection(self._db_path)
        try:
            # Check if pattern already exists
            cur = conn.execute(
                "SELECT id, occurrence_count FROM rf_patterns WHERE pattern = ? AND category = ?",
                (pattern, category),
            )
            row = cur.fetchone()
            if row:
                conn.execute(
                    """UPDATE rf_patterns
                       SET occurrence_count = occurrence_count + 1, last_seen = ?, severity = ?
                       WHERE id = ?""",
                    (time.time(), severity, row["id"]),
                )
            else:
                conn.execute(
                    """INSERT INTO rf_patterns (pattern, category, severity, block_reason, learned_at, occurrence_count, last_seen)
                       VALUES (?, ?, ?, ?, ?, 1, ?)""",
                    (pattern, category, severity, block_reason, time.time(), time.time()),
                )
            conn.commit()
        finally:
            conn.close()

    def _looks_dangerous_in_retrospect(self, action: Dict, result: Any) -> bool:
        """
        Heuristic check: did a seemingly-safe action produce a dangerous result?
        Looks for error indicators, side effects, etc.
        """
        result_str = str(result).lower() if result else ""
        danger_signals = [
            "permission denied",
            "segmentation fault",
            "kernel panic",
            "out of memory",
            "disk full",
            "buffer overflow",
        ]
        return any(signal in result_str for signal in danger_signals)

    # ═════════════════════════════════════════════════════════════════════════
    #  Alternative Suggestions
    # ═════════════════════════════════════════════════════════════════════════

    def _suggest_alternative(self, tool: str, params: Dict) -> Optional[Dict]:
        """
        Suggest a safer alternative to the blocked action.
        """
        if tool in ("terminal_execute", "shell_execute"):
            command = params.get("command", "")
            return {
                "tool": "llm_think",
                "params": {"prompt": f"Propose a safe alternative command for: {command[:200]}"},
            }
        if tool == "file_write":
            file_path = params.get("path", params.get("file_path", ""))
            safe_dir = self._allowed_dirs[0] if self._allowed_dirs else "/tmp/mamoun"
            return {
                "tool": "file_write",
                "params": {**params, "path": f"{safe_dir}/{Path(file_path).name}"},
            }
        if tool in ("sql_execute", "database_query"):
            return {
                "tool": "llm_think",
                "params": {"prompt": "Review and propose a safe SQL query with proper WHERE clauses."},
            }
        return None

    # ═════════════════════════════════════════════════════════════════════════
    #  Persistence
    # ═════════════════════════════════════════════════════════════════════════

    def _record_review(
        self,
        tool: str,
        params: Dict,
        risk_level: str,
        source: str,
        approved: bool,
        reason: str,
        confidence: float,
        override: Optional[str] = None,
    ) -> None:
        """Persist a review decision to the database."""
        conn = get_db_connection(self._db_path)
        try:
            conn.execute(
                """INSERT INTO rf_reviews
                   (timestamp, tool, params, risk_level, source, approved, reason, alternative, confidence, override)
                   VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)""",
                (
                    time.time(),
                    tool,
                    json.dumps(params, default=str)[:2000],
                    risk_level,
                    source,
                    1 if approved else 0,
                    reason[:1000],
                    confidence,
                    override,
                ),
            )
            # Persist counters
            conn.execute(
                "INSERT OR REPLACE INTO rf_state (key, value) VALUES (?, ?)",
                ("review_count", str(self._review_count)),
            )
            conn.execute(
                "INSERT OR REPLACE INTO rf_state (key, value) VALUES (?, ?)",
                ("block_count", str(self._block_count)),
            )
            conn.commit()
        except Exception as e:
            logger.error("Failed to record review: %s", e)
        finally:
            conn.close()

    # ═════════════════════════════════════════════════════════════════════════
    #  Public Helpers
    # ═════════════════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, Any]:
        """Get review statistics."""
        return {
            "total_reviews": self._review_count,
            "total_blocks": self._block_count,
            "block_rate": round(self._block_count / max(self._review_count, 1), 3),
            "initialized": self._initialized,
        }

    def get_brain_confidence(self, brain_id: str) -> float:
        """Get the current confidence score for a brain."""
        conn = get_db_connection(self._db_path)
        try:
            cur = conn.execute(
                "SELECT confidence FROM rf_brain_confidence WHERE brain_id = ?",
                (brain_id,),
            )
            row = cur.fetchone()
            return row["confidence"] if row else 0.5
        finally:
            conn.close()

    def add_allowed_directory(self, directory: str) -> None:
        """Add a directory to the file_write sandbox."""
        resolved = str(Path(directory).resolve())
        if resolved not in self._allowed_dirs:
            self._allowed_dirs.append(resolved)

    def get_recent_blocks(self, limit: int = 20) -> List[Dict]:
        """Get recent blocked actions for audit."""
        conn = get_db_connection(self._db_path)
        try:
            cur = conn.execute(
                "SELECT * FROM rf_reviews WHERE approved = 0 ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton
# ═══════════════════════════════════════════════════════════════════════════════

reflexion_engine = ReflexionEngine()
