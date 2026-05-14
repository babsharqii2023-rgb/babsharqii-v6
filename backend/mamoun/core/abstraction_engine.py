"""
BABSHARQII v40.0 "Mamoun" — Abstraction Engine
Transforms memory from storage/retrieval to real learning by extracting
abstract rules from recurring error patterns. This is the organism's
ability to generalize from experience.
"""

import time
import json
import uuid
import aiosqlite
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from .approval_gate import ApprovalGate, ApprovalRequest


@dataclass
class AbstractRule:
    """An abstract rule extracted from recurring error patterns."""
    id: str = ""
    name: str = ""
    description: str = ""
    condition: dict = field(default_factory=dict)
    action: dict = field(default_factory=dict)
    source_pattern: str = ""
    confidence: float = 0.0
    created_from_count: int = 0
    status: str = "proposed"  # proposed, approved, rejected, active
    created_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "condition": self.condition,
            "action": self.action,
            "source_pattern": self.source_pattern,
            "confidence": self.confidence,
            "created_from_count": self.created_from_count,
            "status": self.status,
            "created_at": self.created_at,
        }


class AbstractionEngine:
    """
    Extracts abstract rules from recurring error patterns in the reflective journal.

    The engine transforms raw error data into actionable knowledge by:
    1. Identifying patterns that repeat 3+ times
    2. Formulating abstract rules with conditions and actions
    3. Submitting rules through the approval gate for human review
    4. Applying active rules to new contexts for proactive prevention
    """

    def __init__(self, journal_db_path: str = ""):
        if not journal_db_path:
            journal_db_path = str(Path(__file__).parent.parent.parent / "data" / "mamoun.db")
        self._db_path = journal_db_path
        self._initialized = False
        self._approval_gate = ApprovalGate(db_path=journal_db_path)

    async def _initialize(self):
        """Create the abstract_rules table if it doesn't exist."""
        if self._initialized:
            return

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS abstract_rules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    condition_json TEXT DEFAULT '{}',
                    action_json TEXT DEFAULT '{}',
                    source_pattern TEXT DEFAULT '',
                    confidence REAL DEFAULT 0.0,
                    created_from_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'proposed',
                    created_at REAL DEFAULT 0.0
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_abstract_rules_status
                ON abstract_rules(status)
            """)
            await db.commit()

        self._initialized = True

    async def analyze_patterns(self) -> list[AbstractRule]:
        """
        Query the reflective_journal table for error patterns that appear 3+ times,
        then formulate abstract rules from them.

        Uses SQL GROUP BY on root_cause/summary to find recurring patterns.
        """
        await self._initialize()

        rules: list[AbstractRule] = []

        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT
                    summary,
                    root_cause,
                    COUNT(*) as count,
                    AVG(emotional_valence) as avg_valence
                FROM reflective_journal
                WHERE entry_type = 'error'
                GROUP BY summary, root_cause
                HAVING count >= 3
                ORDER BY count DESC
            """)
            rows = await cursor.fetchall()

        for row in rows:
            summary = row["summary"] or ""
            root_cause = row["root_cause"] or ""
            count = row["count"]
            avg_valence = row["avg_valence"] or 0.0

            # Generate a unique ID for this rule
            rule_id = f"rule_{uuid.uuid4().hex[:12]}"

            # Formulate condition and action
            pattern_key = root_cause if root_cause else summary
            condition = {
                "pattern": pattern_key,
                "threshold": count,
                "type": "error_frequency",
            }

            suggested_action = self._formulate_action(summary, count, avg_valence)
            risk_level = self._estimate_risk(count, avg_valence)
            action = {
                "suggested_action": suggested_action,
                "risk_level": risk_level,
            }

            # Calculate confidence based on frequency and consistency
            confidence = min(1.0, (count / 10.0) * (1.0 - abs(avg_valence) * 0.3))

            # Arabic name and description
            rule_name = f"قاعدة تجريدية: {summary[:50]}"
            rule_description = (
                f"تم استخلاص هذه القاعدة من تكرار الخطأ '{summary}' "
                f"بمعدل {count} مرات. السبب الجذري: {root_cause}. "
                f"الإجراء المقترح: {suggested_action}"
            )

            rule = AbstractRule(
                id=rule_id,
                name=rule_name,
                description=rule_description,
                condition=condition,
                action=action,
                source_pattern=pattern_key,
                confidence=round(confidence, 3),
                created_from_count=count,
                status="proposed",
                created_at=time.time(),
            )
            rules.append(rule)

        return rules

    async def propose_rule(self, rule: AbstractRule) -> dict:
        """
        Insert the proposed rule into the abstract_rules SQLite table and
        create an ApprovalRequest via ApprovalGate.

        Returns the approval request ID.
        """
        await self._initialize()

        if not rule.id:
            rule.id = f"rule_{uuid.uuid4().hex[:12]}"
        if not rule.created_at:
            rule.created_at = time.time()
        rule.status = "proposed"

        # Insert into abstract_rules table
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                INSERT INTO abstract_rules
                (id, name, description, condition_json, action_json,
                 source_pattern, confidence, created_from_count, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule.id,
                rule.name,
                rule.description,
                json.dumps(rule.condition, ensure_ascii=False),
                json.dumps(rule.action, ensure_ascii=False),
                rule.source_pattern,
                rule.confidence,
                rule.created_from_count,
                rule.status,
                rule.created_at,
            ))
            await db.commit()

        # Create an ApprovalRequest via the ApprovalGate
        approval_request = ApprovalRequest(
            change_type="abstract_rule",
            target=rule.id,
            description=rule.description,
            risk_level=rule.action.get("risk_level", "medium"),
            details=json.dumps(rule.to_dict(), ensure_ascii=False),
        )

        approval_result = await self._approval_gate.request_approval(approval_request)

        return {
            "rule_id": rule.id,
            "approval_id": approval_result.get("id", ""),
            "approval_status": approval_result.get("status", ""),
            "message": approval_result.get("message", ""),
        }

    async def get_active_rules(self) -> list[AbstractRule]:
        """Return all rules with status 'active'."""
        await self._initialize()

        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM abstract_rules
                WHERE status = 'active'
                ORDER BY confidence DESC, created_from_count DESC
            """)
            rows = await cursor.fetchall()

        rules = []
        for row in rows:
            rules.append(self._row_to_rule(row))
        return rules

    async def approve_rule(self, rule_id: str) -> bool:
        """Move a rule from 'proposed' to 'active'."""
        await self._initialize()

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("""
                UPDATE abstract_rules
                SET status = 'active'
                WHERE id = ? AND status = 'proposed'
            """, (rule_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def reject_rule(self, rule_id: str) -> bool:
        """Move a rule from 'proposed' to 'rejected'."""
        await self._initialize()

        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("""
                UPDATE abstract_rules
                SET status = 'rejected'
                WHERE id = ? AND status = 'proposed'
            """, (rule_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def evaluate_against_rules(self, context: dict) -> list[dict]:
        """
        Given a context (like current error rates), check which active rules
        apply and return their suggested actions.
        """
        active_rules = await self.get_active_rules()
        matching_actions: list[dict] = []

        for rule in active_rules:
            condition = rule.condition
            pattern = condition.get("pattern", "")
            cond_type = condition.get("type", "")

            # Check if the context matches this rule's condition
            matched = False

            if cond_type == "error_frequency":
                # Match if the context contains the same pattern
                context_errors = context.get("errors", [])
                for err in context_errors:
                    err_summary = err.get("summary", "")
                    err_root_cause = err.get("root_cause", "")
                    if pattern and (pattern in err_summary or pattern in err_root_cause):
                        matched = True
                        break

                # Also match if context has a "current_pattern" key
                current_pattern = context.get("current_pattern", "")
                if pattern and current_pattern and pattern in current_pattern:
                    matched = True

            if matched:
                matching_actions.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "condition": rule.condition,
                    "action": rule.action,
                    "confidence": rule.confidence,
                })

        return matching_actions

    def _formulate_action(self, pattern_summary: str, count: int, avg_valence: float) -> str:
        """
        Generate a human-readable Arabic action description from the pattern.
        """
        severity = "منخفضة"
        if avg_valence < -0.5:
            severity = "حرجة"
        elif avg_valence < -0.2:
            severity = "عالية"

        frequency = "متكرر"
        if count >= 10:
            frequency = "متكرر جداً"
        elif count >= 5:
            frequency = "كثير التكرار"

        action = (
            f"يجب اتخاذ إجراء وقائي فوراً: النمط '{pattern_summary}' "
            f"يتكرر بشكل {frequency} ({count} مرات) بخطورة {severity}. "
            f"يُنصح بمراجعة السبب الجذري وتطبيق إصلاح دائم لمنع تكرار الخطأ."
        )
        return action

    def _estimate_risk(self, count: int, avg_valence: float) -> str:
        """
        Estimate risk level based on frequency and severity.

        Returns: "low", "medium", "high", or "critical"
        """
        # Score based on frequency (0-1)
        freq_score = min(count / 15.0, 1.0)

        # Score based on severity (avg_valence ranges from -1 to 1, more negative = worse)
        severity_score = max(0.0, (-avg_valence + 1.0) / 2.0)

        # Combined risk score
        risk_score = (freq_score * 0.4) + (severity_score * 0.6)

        if risk_score >= 0.8:
            return "critical"
        elif risk_score >= 0.6:
            return "high"
        elif risk_score >= 0.3:
            return "medium"
        else:
            return "low"

    def _row_to_rule(self, row) -> AbstractRule:
        """Convert a database row to an AbstractRule."""
        condition = {}
        try:
            condition = json.loads(row["condition_json"])
        except (json.JSONDecodeError, TypeError):
            pass

        action = {}
        try:
            action = json.loads(row["action_json"])
        except (json.JSONDecodeError, TypeError):
            pass

        return AbstractRule(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            condition=condition,
            action=action,
            source_pattern=row["source_pattern"],
            confidence=row["confidence"],
            created_from_count=row["created_from_count"],
            status=row["status"],
            created_at=row["created_at"],
        )
