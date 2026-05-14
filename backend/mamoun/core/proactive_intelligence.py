"""
BABSHARQII v19.0 — Proactive Intelligence
المبادرة الذكية — Background monitoring + rule triggers + LLM suggestions

Detects patterns and proactively notifies:
- "لاحظت إنك كتبت نفس الكود 3 مرات — ممكن نعمل دالة؟"
- "مشروعك ما تحدث من أسبوع"
- "في مكتبة جديدة تناسب احتياجك"
- Rule-based triggers + LLM-generated suggestions
"""

import time
import json
import logging
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum

logger = logging.getLogger("mamoun.proactive_intelligence")


class TriggerType(str, Enum):
    REPETITION = "repetition"     # تكرار
    INACTIVITY = "inactivity"     # خمول
    ERROR_PATTERN = "error_pattern"  # نمط أخطاء
    OPPORTUNITY = "opportunity"    # فرصة
    DEADLINE = "deadline"         # موعد
    RESEARCH = "research"         # بحث جديد


@dataclass
class ProactiveRule:
    """قاعدة استباقية"""
    id: str = ""
    trigger_type: str = ""
    condition: str = ""  # description of trigger condition
    message_ar: str = ""
    message_en: str = ""
    priority: str = "low"
    enabled: bool = True
    fire_count: int = 0
    last_fired: float = 0.0

    def to_dict(self) -> dict:
        return {"id": self.id, "trigger_type": self.trigger_type, "condition": self.condition,
                "message_ar": self.message_ar, "priority": self.priority, "enabled": self.enabled}


@dataclass
class ProactiveNotification:
    """إشعار استباقي"""
    id: str = ""
    trigger_type: str = ""
    message_ar: str = ""
    message_en: str = ""
    priority: str = "low"
    source_rule_id: str = ""
    timestamp: float = field(default_factory=time.time)
    dismissed: bool = False

    def to_dict(self) -> dict:
        return {"id": self.id, "trigger_type": self.trigger_type, "message_ar": self.message_ar,
                "priority": self.priority, "timestamp": self.timestamp, "dismissed": self.dismissed}


class ProactiveIntelligenceEngine:
    """
    محرك المبادرة الذكية — يراقب وينبه استباقياً
    """

    COOLDOWN_SECONDS = 3600  # 1 hour between same-rule fires

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path("/tmp/proactive_intelligence.db")
        self._rules: List[ProactiveRule] = []
        self._notifications: List[ProactiveNotification] = []
        self._counter = 0
        self._initialized = False
        self._last_interaction_content: List[str] = []
        self._last_errors: List[str] = []
        self._default_rules_loaded = False

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            if not self._default_rules_loaded:
                self._load_default_rules()
            self._initialized = True
            logger.info("ProactiveIntelligenceEngine initialized — %d rules, %d notifications",
                       len(self._rules), len(self._notifications))
            return True
        except Exception as e:
            logger.error("ProactiveIntelligenceEngine init failed: %s", e)
            return False

    def _ensure_schema(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS pi_rules (
                id TEXT PRIMARY KEY, trigger_type TEXT DEFAULT '',
                condition TEXT DEFAULT '', message_ar TEXT DEFAULT '',
                message_en TEXT DEFAULT '', priority TEXT DEFAULT 'low',
                enabled INTEGER DEFAULT 1, fire_count INTEGER DEFAULT 0,
                last_fired REAL DEFAULT 0)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS pi_notifications (
                id TEXT PRIMARY KEY, trigger_type TEXT DEFAULT '',
                message_ar TEXT DEFAULT '', message_en TEXT DEFAULT '',
                priority TEXT DEFAULT 'low', source_rule_id TEXT DEFAULT '',
                timestamp REAL DEFAULT 0, dismissed INTEGER DEFAULT 0)""")
            conn.commit()
        finally: conn.close()

    def _load_from_db(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            cur = conn.execute("SELECT id, trigger_type, condition, message_ar, message_en, priority, enabled, fire_count, last_fired FROM pi_rules")
            for row in cur.fetchall():
                self._rules.append(ProactiveRule(id=row[0], trigger_type=row[1], condition=row[2],
                                                  message_ar=row[3], message_en=row[4], priority=row[5],
                                                  enabled=bool(row[6]), fire_count=row[7], last_fired=row[8]))

            cur = conn.execute("SELECT id, trigger_type, message_ar, message_en, priority, source_rule_id, timestamp, dismissed FROM pi_notifications ORDER BY timestamp DESC LIMIT 50")
            for row in cur.fetchall():
                self._notifications.append(ProactiveNotification(id=row[0], trigger_type=row[1], message_ar=row[2],
                                                                  message_en=row[3], priority=row[4],
                                                                  source_rule_id=row[5], timestamp=row[6],
                                                                  dismissed=bool(row[7])))
            if self._rules:
                self._default_rules_loaded = True
        finally: conn.close()

    def _load_default_rules(self):
        """تحميل القواعد الافتراضية"""
        defaults = [
            ProactiveRule(id="rep_code", trigger_type=TriggerType.REPETITION.value,
                         condition="same_code_3x", message_ar="لاحظت إنك كتبت نفس الكود 3 مرات — ممكن نعمل دالة؟",
                         message_en="I noticed you wrote the same code 3 times — can we make a function?",
                         priority="medium"),
            ProactiveRule(id="rep_topic", trigger_type=TriggerType.REPETITION.value,
                         condition="same_topic_5x", message_ar="سألت عن هذا الموضوع كثيراً — ممكن أساعدك أحل الموضوع كله؟",
                         message_en="You've asked about this topic a lot — can I help solve it completely?",
                         priority="medium"),
            ProactiveRule(id="inactive_project", trigger_type=TriggerType.INACTIVITY.value,
                         condition="project_inactive_7d", message_ar="مشروعك ما تحدث من أسبوع — تحتاج مساعدة؟",
                         message_en="Your project hasn't been updated in a week — need help?",
                         priority="high"),
            ProactiveRule(id="repeated_error", trigger_type=TriggerType.ERROR_PATTERN.value,
                         condition="error_3x", message_ar="هذا الخطأ يتكرر 3 مرات — خلينا نحل السبب الجذري",
                         message_en="This error repeated 3 times — let's fix the root cause",
                         priority="high"),
            ProactiveRule(id="api_key_missing", trigger_type=TriggerType.ERROR_PATTERN.value,
                         condition="api_key_missing", message_ar="مفتاح API ناقص — أضفه من الإعدادات",
                         message_en="API key missing — add it from settings",
                         priority="critical"),
        ]
        self._rules.extend(defaults)
        self._default_rules_loaded = True

        # Persist
        conn = sqlite3.connect(str(self.db_path))
        try:
            for r in defaults:
                conn.execute("INSERT OR IGNORE INTO pi_rules (id, trigger_type, condition, message_ar, message_en, priority, enabled, fire_count, last_fired) VALUES (?,?,?,?,?,?,?,?,0)",
                           (r.id, r.trigger_type, r.condition, r.message_ar, r.message_en, r.priority, 1 if r.enabled else 0, r.fire_count))
            conn.commit()
        finally: conn.close()

    # ─── Core: Check Triggers ──────────────────────────────────────────────

    def check(self, content: str = "", topics: List[str] = None,
              errors: List[str] = None, days_inactive: float = 0.0) -> List[ProactiveNotification]:
        """فحص القواعد وإطلاق الإشعارات"""
        if not self._initialized:
            self.initialize()

        now = time.time()
        new_notifications = []

        # Track content for repetition detection
        if content:
            self._last_interaction_content.append(content)
            if len(self._last_interaction_content) > 20:
                self._last_interaction_content = self._last_interaction_content[-20:]

        # Track errors
        if errors:
            self._last_errors.extend(errors)
            if len(self._last_errors) > 20:
                self._last_errors = self._last_errors[-20:]

        # Check each rule
        for rule in self._rules:
            if not rule.enabled:
                continue
            # Cooldown check
            if rule.last_fired and (now - rule.last_fired) < self.COOLDOWN_SECONDS:
                continue

            fired = False

            # Repetition checks
            if rule.trigger_type == TriggerType.REPETITION.value:
                if rule.condition == "same_code_3x" and content:
                    # Check if same content repeated 3+ times
                    same_count = sum(1 for c in self._last_interaction_content if c == content)
                    if same_count >= 3:
                        fired = True
                elif rule.condition == "same_topic_5x" and topics:
                    for topic in topics:
                        topic_count = sum(1 for c in self._last_interaction_content if topic.lower() in c.lower())
                        if topic_count >= 5:
                            fired = True

            # Inactivity checks
            elif rule.trigger_type == TriggerType.INACTIVITY.value:
                if rule.condition == "project_inactive_7d" and days_inactive >= 7:
                    fired = True

            # Error pattern checks
            elif rule.trigger_type == TriggerType.ERROR_PATTERN.value:
                if rule.condition == "error_3x" and errors:
                    for error in errors:
                        error_count = sum(1 for e in self._last_errors if e == error)
                        if error_count >= 3:
                            fired = True
                elif rule.condition == "api_key_missing" and errors:
                    if any("api_key" in e.lower() or "api key" in e.lower() for e in errors):
                        fired = True

            if fired:
                self._counter += 1
                notif = ProactiveNotification(
                    id=f"notif_{self._counter}",
                    trigger_type=rule.trigger_type,
                    message_ar=rule.message_ar,
                    message_en=rule.message_en,
                    priority=rule.priority,
                    source_rule_id=rule.id,
                )
                self._notifications.append(notif)
                new_notifications.append(notif)

                # Update rule stats
                rule.fire_count += 1
                rule.last_fired = now

                # Persist
                self._persist_notification(notif)
                self._persist_rules()

        return new_notifications

    # ─── Persistence ───────────────────────────────────────────────────────

    def _persist_notification(self, n: ProactiveNotification):
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("INSERT OR REPLACE INTO pi_notifications (id, trigger_type, message_ar, message_en, priority, source_rule_id, timestamp, dismissed) VALUES (?,?,?,?,?,?,?,?)",
                        (n.id, n.trigger_type, n.message_ar, n.message_en, n.priority, n.source_rule_id, n.timestamp, 1 if n.dismissed else 0))
            conn.commit()
        finally: conn.close()

    def _persist_rules(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            for r in self._rules:
                conn.execute("INSERT OR REPLACE INTO pi_rules (id, trigger_type, condition, message_ar, message_en, priority, enabled, fire_count, last_fired) VALUES (?,?,?,?,?,?,?,?,?)",
                           (r.id, r.trigger_type, r.condition, r.message_ar, r.message_en, r.priority,
                            1 if r.enabled else 0, r.fire_count, r.last_fired))
            conn.commit()
        finally: conn.close()

    # ─── Status & API ──────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "initialized": self._initialized,
            "rules_count": len(self._rules),
            "active_rules": len([r for r in self._rules if r.enabled]),
            "notifications_count": len(self._notifications),
            "unread_count": len([n for n in self._notifications if not n.dismissed]),
        }

    def get_notifications(self, limit: int = 20, include_dismissed: bool = False) -> List[dict]:
        notifs = self._notifications if include_dismissed else [n for n in self._notifications if not n.dismissed]
        return [n.to_dict() for n in sorted(notifs, key=lambda n: n.timestamp, reverse=True)[:limit]]

    def dismiss_notification(self, notif_id: str):
        for n in self._notifications:
            if n.id == notif_id:
                n.dismissed = True
                break

    def get_rules(self) -> List[dict]:
        return [r.to_dict() for r in self._rules]

    def toggle_rule(self, rule_id: str, enabled: bool):
        for r in self._rules:
            if r.id == rule_id:
                r.enabled = enabled
                self._persist_rules()
                return True
        return False


proactive_intelligence = ProactiveIntelligenceEngine()
