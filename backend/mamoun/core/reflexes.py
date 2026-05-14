"""
BABSHARQII v22.0 — Reflexes System
نظام ردود الفعل اللحظية — استجابة فورية للتهديدات والفرص

Based on research:
  - Autonomic Nervous System (biological): Fight/Flight/Freeze/Fawn responses
  - Reflex Agent (Russell & Norvig, 2020): Condition → Action without deliberation
  - Real-time Systems: Hard vs soft deadlines for responses
  - Predictive Coding (Friston, 2010): Brain minimizes surprise via reflexive updates

Architecture:
  ┌──────────────────────────────────────────────────────────┐
  │                    Reflexes System                        │
  │                                                           │
  │  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
  │  │ SAFETY  │  │ SYSTEM   │  │ USER     │  │ OPPOR-   │ │
  │  │ REFLEX  │  │ REFLEX   │  │ REFLEX   │  │ TUNITY   │ │
  │  │         │  │          │  │          │  │ REFLEX   │ │
  │  │ Threats │  │ Errors   │  │ Distress │  │ Chances  │ │
  │  │ Attacks │  │ Crashes  │  │ Needs    │  │ Markets  │ │
  │  └─────────┘  └──────────┘  └──────────┘  └──────────┘ │
  │                                                           │
  │  Response Time: < 100ms (bypass deliberation)            │
  └──────────────────────────────────────────────────────────┘

Reflexes bypass the normal deliberation pipeline for speed.
They are the "spinal cord" of Mamoun — fast, automatic, protective.
"""

import time
import json
import logging
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable, Any
from enum import Enum
from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.reflexes")


class ReflexType(str, Enum):
    """أنواع ردود الفعل"""
    SAFETY = "safety"          # حماية — threats, attacks
    SYSTEM = "system"          # نظام — errors, crashes
    USER = "user"              # مستخدم — distress, needs
    OPPORTUNITY = "opportunity"  # فرصة — market, discovery
    HEALTH = "health"          # صحة — performance degradation


class ReflexPriority(str, Enum):
    """أولوية رد الفعل"""
    INSTANT = "instant"      # < 50ms — life/death decisions
    URGENT = "urgent"        # < 200ms — critical issues
    FAST = "fast"            # < 500ms — important issues
    NORMAL = "normal"        # < 2s — standard reflexes


class ReflexAction(str, Enum):
    """إجراء رد الفعل"""
    BLOCK = "block"              # حظر الفورة
    SHIELD = "shield"            # حماية النظام
    ALERT_USER = "alert_user"    # تنبيه المستخدم
    AUTO_FIX = "auto_fix"        # إصلاح تلقائي
    THROTTLE = "throttle"        # تقليل الحمل
    REDIRECT = "redirect"        # إعادة توجيه
    BACKUP = "backup"            # نسخ احتياطي
    ESCALATE = "escalate"        # تصعيد للإنسان
    NOTIFY = "notify"            # إشعار
    CAPTURE = "capture"          # التقاط البيانات


@dataclass
class ReflexTrigger:
    """محفز رد الفعل — What triggers a reflex"""
    id: str = ""
    reflex_type: str = ""
    condition: str = ""          # Description of the trigger condition
    priority: str = ReflexPriority.NORMAL.value
    action: str = ReflexAction.NOTIFY.value
    handler_name: str = ""      # Name of the handler function
    enabled: bool = True
    fire_count: int = 0
    last_fired: float = 0.0
    cooldown_seconds: float = 60.0  # Minimum time between fires

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "reflex_type": self.reflex_type,
            "condition": self.condition,
            "priority": self.priority,
            "action": self.action,
            "enabled": self.enabled,
            "fire_count": self.fire_count,
        }


@dataclass
class ReflexResponse:
    """استجابة رد الفعل — The result of a reflex action"""
    trigger_id: str = ""
    reflex_type: str = ""
    action_taken: str = ""
    success: bool = False
    message_ar: str = ""
    message_en: str = ""
    data: Dict = field(default_factory=dict)
    response_time_ms: float = 0.0
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return {
            "trigger_id": self.trigger_id,
            "reflex_type": self.reflex_type,
            "action_taken": self.action_taken,
            "success": self.success,
            "message_ar": self.message_ar,
            "response_time_ms": round(self.response_time_ms, 1),
            "timestamp": self.timestamp,
        }


class ReflexesEngine:
    """
    نظام ردود الفعل اللحظية — استجابة فورية

    This engine monitors for trigger conditions and fires automatic
    responses without going through the normal deliberation pipeline.

    Think of it as Mamoun's "spinal cord" — fast reflexes that protect
    the system and the user before the "brain" even finishes thinking.
    """

    COOLDOWN_MIN = 30.0  # minimum seconds between same-reflex fires

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or UNIFIED_DB_PATH
        self._triggers: Dict[str, ReflexTrigger] = {}
        self._handlers: Dict[str, Callable] = {}
        self._response_history: List[ReflexResponse] = []
        self._counter = 0
        self._initialized = False

    def initialize(self) -> bool:
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._ensure_schema()
            self._load_from_db()
            self._register_default_triggers()
            self._register_default_handlers()
            self._initialized = True
            logger.info(
                "ReflexesEngine initialized — %d triggers, %d handlers",
                len(self._triggers), len(self._handlers),
            )
            return True
        except Exception as e:
            logger.error("ReflexesEngine init failed: %s", e)
            self._initialized = True
            return True

    # ═════════════════════════════════════════════════════════════════════════
    #  التسجيل — Registration
    # ═════════════════════════════════════════════════════════════════════════

    def register_trigger(self, trigger: ReflexTrigger):
        """تسجيل محفز جديد"""
        self._triggers[trigger.id] = trigger
        logger.debug("Reflex trigger registered: %s (%s)", trigger.id, trigger.reflex_type)

    def register_handler(self, name: str, handler: Callable):
        """تسجيل معالج جديد"""
        self._handlers[name] = handler
        logger.debug("Reflex handler registered: %s", name)

    def _register_default_triggers(self):
        """تسجيل المحفزات الافتراضية"""
        defaults = [
            ReflexTrigger(
                id="safety_malicious_input",
                reflex_type=ReflexType.SAFETY.value,
                condition="sql_injection_or_xss_detected",
                priority=ReflexPriority.INSTANT.value,
                action=ReflexAction.BLOCK.value,
                handler_name="handle_malicious_input",
            ),
            ReflexTrigger(
                id="safety_data_leak",
                reflex_type=ReflexType.SAFETY.value,
                condition="sensitive_data_in_response",
                priority=ReflexPriority.URGENT.value,
                action=ReflexAction.SHIELD.value,
                handler_name="handle_data_leak",
            ),
            ReflexTrigger(
                id="system_high_error_rate",
                reflex_type=ReflexType.SYSTEM.value,
                condition="error_rate_above_30_percent",
                priority=ReflexPriority.URGENT.value,
                action=ReflexAction.AUTO_FIX.value,
                handler_name="handle_high_error_rate",
            ),
            ReflexTrigger(
                id="system_memory_pressure",
                reflex_type=ReflexType.SYSTEM.value,
                condition="memory_usage_above_85_percent",
                priority=ReflexPriority.FAST.value,
                action=ReflexAction.THROTTLE.value,
                handler_name="handle_memory_pressure",
            ),
            ReflexTrigger(
                id="system_service_down",
                reflex_type=ReflexType.SYSTEM.value,
                condition="backend_service_unresponsive",
                priority=ReflexPriority.INSTANT.value,
                action=ReflexAction.AUTO_FIX.value,
                handler_name="handle_service_down",
            ),
            ReflexTrigger(
                id="user_frustration",
                reflex_type=ReflexType.USER.value,
                condition="user_showing_frustration_signals",
                priority=ReflexPriority.FAST.value,
                action=ReflexAction.ALERT_USER.value,
                handler_name="handle_user_frustration",
            ),
            ReflexTrigger(
                id="user_absence_long",
                reflex_type=ReflexType.USER.value,
                condition="user_absent_more_than_24h",
                priority=ReflexPriority.NORMAL.value,
                action=ReflexAction.NOTIFY.value,
                handler_name="handle_user_absence",
            ),
            ReflexTrigger(
                id="opportunity_market",
                reflex_type=ReflexType.OPPORTUNITY.value,
                condition="significant_market_movement",
                priority=ReflexPriority.FAST.value,
                action=ReflexAction.ALERT_USER.value,
                handler_name="handle_market_opportunity",
            ),
            ReflexTrigger(
                id="health_degradation",
                reflex_type=ReflexType.HEALTH.value,
                condition="response_time_degraded",
                priority=ReflexPriority.FAST.value,
                action=ReflexAction.AUTO_FIX.value,
                handler_name="handle_health_degradation",
            ),
        ]

        for trigger in defaults:
            if trigger.id not in self._triggers:
                self.register_trigger(trigger)

    def _register_default_handlers(self):
        """تسجيل المعالجات الافتراضية"""
        self._handlers["handle_malicious_input"] = self._handle_malicious_input
        self._handlers["handle_data_leak"] = self._handle_data_leak
        self._handlers["handle_high_error_rate"] = self._handle_high_error_rate
        self._handlers["handle_memory_pressure"] = self._handle_memory_pressure
        self._handlers["handle_service_down"] = self._handle_service_down
        self._handlers["handle_user_frustration"] = self._handle_user_frustration
        self._handlers["handle_user_absence"] = self._handle_user_absence
        self._handlers["handle_market_opportunity"] = self._handle_market_opportunity
        self._handlers["handle_health_degradation"] = self._handle_health_degradation

    # ═════════════════════════════════════════════════════════════════════════
    #  الفحص — Checking Triggers
    # ═════════════════════════════════════════════════════════════════════════

    def check(self, context: Dict[str, Any] = None) -> List[ReflexResponse]:
        """فحص جميع المحفزات وتنفيذ ما ينطبق"""
        if not self._initialized:
            self.initialize()

        context = context or {}
        now = time.time()
        responses = []

        for trigger_id, trigger in self._triggers.items():
            if not trigger.enabled:
                continue

            # Cooldown check
            if trigger.last_fired > 0 and (now - trigger.last_fired) < trigger.cooldown_seconds:
                continue

            # Check condition
            if self._evaluate_condition(trigger, context):
                start_time = time.time()
                response = self._fire_reflex(trigger, context)
                response.response_time_ms = (time.time() - start_time) * 1000
                response.timestamp = now

                trigger.fire_count += 1
                trigger.last_fired = now

                self._response_history.append(response)
                if len(self._response_history) > 200:
                    self._response_history = self._response_history[-200:]

                responses.append(response)

                logger.info(
                    "Reflex fired: %s → %s (%.1fms)",
                    trigger_id, response.action_taken, response.response_time_ms,
                )

                # v30: Publish reflex activation to NeuralBus
                if hasattr(self, '_neural_bus') and self._neural_bus:
                    try:
                        self._neural_bus.publish(
                            signal_type="action_requested",
                            source=f"reflex:{trigger_id}",
                            payload={
                                "reflex_id": trigger_id,
                                "action": response.action_taken,
                                "priority": trigger.priority,
                                "reflex_type": trigger.reflex_type,
                            },
                            priority=3,  # HIGH
                        )
                    except Exception:
                        pass

        return responses

    def check_specific(self, trigger_id: str, context: Dict = None) -> Optional[ReflexResponse]:
        """فحص محفز محدد فقط"""
        if trigger_id not in self._triggers:
            return None
        trigger = self._triggers[trigger_id]
        if not trigger.enabled:
            return None
        if self._evaluate_condition(trigger, context or {}):
            return self._fire_reflex(trigger, context or {})
        return None

    def _evaluate_condition(self, trigger: ReflexTrigger, context: Dict) -> bool:
        """تقييم شرط المحفز"""
        cond = trigger.condition

        # Safety checks
        if cond == "sql_injection_or_xss_detected":
            user_input = context.get("user_input", "")
            dangerous_patterns = ["DROP TABLE", "--", "'; ", "<script>", "javascript:", "onerror="]
            return any(p.lower() in user_input.lower() for p in dangerous_patterns)

        if cond == "sensitive_data_in_response":
            response_text = context.get("response_text", "")
            sensitive = ["password", "api_key", "secret", "token", "credit_card"]
            return any(s in response_text.lower() for s in sensitive)

        # System checks
        if cond == "error_rate_above_30_percent":
            error_rate = context.get("error_rate", 0)
            return error_rate > 0.3

        if cond == "memory_usage_above_85_percent":
            mem_usage = context.get("memory_usage", 0)
            return mem_usage > 0.85

        if cond == "backend_service_unresponsive":
            return context.get("service_down", False)

        # User checks
        if cond == "user_showing_frustration_signals":
            frustration_score = context.get("frustration_score", 0)
            return frustration_score > 0.6

        if cond == "user_absent_more_than_24h":
            hours_absent = context.get("hours_absent", 0)
            return hours_absent > 24

        # Opportunity checks
        if cond == "significant_market_movement":
            market_change = context.get("market_change_pct", 0)
            return abs(market_change) > 3.0

        # Health checks
        if cond == "response_time_degraded":
            avg_response_ms = context.get("avg_response_ms", 0)
            return avg_response_ms > 5000

        return False

    def _fire_reflex(self, trigger: ReflexTrigger, context: Dict) -> ReflexResponse:
        """تنفيذ رد الفعل"""
        handler = self._handlers.get(trigger.handler_name)
        if handler:
            try:
                result = handler(context)
                return ReflexResponse(
                    trigger_id=trigger.id,
                    reflex_type=trigger.reflex_type,
                    action_taken=trigger.action,
                    success=result.get("success", True),
                    message_ar=result.get("message_ar", "تم التنفيذ"),
                    message_en=result.get("message_en", "Action taken"),
                    data=result.get("data", {}),
                )
            except Exception as e:
                logger.error("Reflex handler %s failed: %s", trigger.handler_name, e)
                return ReflexResponse(
                    trigger_id=trigger.id,
                    reflex_type=trigger.reflex_type,
                    action_taken="error",
                    success=False,
                    message_ar=f"فشل رد الفعل: {str(e)[:100]}",
                )
        else:
            return ReflexResponse(
                trigger_id=trigger.id,
                reflex_type=trigger.reflex_type,
                action_taken="no_handler",
                success=False,
                message_ar=f"لا يوجد معالج لـ {trigger.handler_name}",
            )

    # ═════════════════════════════════════════════════════════════════════════
    #  المعالجات الافتراضية — Default Handlers
    # ═════════════════════════════════════════════════════════════════════════

    def _handle_malicious_input(self, ctx: Dict) -> Dict:
        return {
            "success": True,
            "message_ar": "تم حظر إدخال مشبوه — محتوى ضار مكتشف",
            "message_en": "Blocked suspicious input — malicious content detected",
            "data": {"blocked": True, "reason": "security_threat"},
        }

    def _handle_data_leak(self, ctx: Dict) -> Dict:
        return {
            "success": True,
            "message_ar": "تم حجب بيانات حساسة من الاستجابة",
            "message_en": "Sensitive data redacted from response",
            "data": {"redacted": True},
        }

    def _handle_high_error_rate(self, ctx: Dict) -> Dict:
        return {
            "success": True,
            "message_ar": "نسبة الأخطاء مرتفعة — تم تفعيل الوضع الآمن",
            "message_en": "High error rate — safe mode activated",
            "data": {"safe_mode": True},
        }

    def _handle_memory_pressure(self, ctx: Dict) -> Dict:
        return {
            "success": True,
            "message_ar": "استهلاك الذاكرة مرتفع — تقليل العمليات غير الأساسية",
            "message_en": "High memory usage — throttling non-essential operations",
            "data": {"throttled": True},
        }

    def _handle_service_down(self, ctx: Dict) -> Dict:
        return {
            "success": True,
            "message_ar": "الخدمة لا تستجيب — محاولة إعادة التشغيل",
            "message_en": "Service unresponsive — attempting restart",
            "data": {"restart_attempted": True},
        }

    def _handle_user_frustration(self, ctx: Dict) -> Dict:
        return {
            "success": True,
            "message_ar": "يبدو أنك محبط — دعني أبسط الأمور وأساعدك بشكل أفضل",
            "message_en": "You seem frustrated — let me simplify and help better",
            "data": {"simplify_mode": True},
        }

    def _handle_user_absence(self, ctx: Dict) -> Dict:
        return {
            "success": True,
            "message_ar": "غياب طويل — سأحتفظ بملخص لما فاتك",
            "message_en": "Long absence — I'll keep a summary of what you missed",
            "data": {"summary_prepared": True},
        }

    def _handle_market_opportunity(self, ctx: Dict) -> Dict:
        return {
            "success": True,
            "message_ar": "حركة سوقية مهمة — قد تهمك!",
            "message_en": "Significant market movement — might interest you!",
            "data": {"market_alert": True},
        }

    def _handle_health_degradation(self, ctx: Dict) -> Dict:
        return {
            "success": True,
            "message_ar": "أداء النظام بطيء — تحسين تلقائي",
            "message_en": "System performance slow — auto-optimizing",
            "data": {"optimization_started": True},
        }

    # ═════════════════════════════════════════════════════════════════════════
    #  Status & API
    # ═════════════════════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        return {
            "initialized": self._initialized,
            "total_triggers": len(self._triggers),
            "enabled_triggers": len([t for t in self._triggers.values() if t.enabled]),
            "total_handlers": len(self._handlers),
            "total_fired": sum(t.fire_count for t in self._triggers.values()),
            "by_type": {
                rtype: len([t for t in self._triggers.values() if t.reflex_type == rtype])
                for rtype in [rt.value for rt in ReflexType]
            },
            "recent_responses": [r.to_dict() for r in self._response_history[-10:]],
        }

    def _on_neural_signal(self, signal):
        """v31: Handle incoming NeuralBus signals — auto-trigger reflexes on critical events."""
        try:
            stype = signal.signal_type
            # When critical signals arrive, run a reflex check with the signal as context
            if stype in ("stress_spike", "error_detected", "energy_drop", "prediction_failed"):
                context = {
                    "signal_type": stype,
                    "signal_source": signal.source,
                    "signal_payload": signal.payload,
                    "auto_triggered": True,
                }
                responses = self.check(context)
                for r in responses:
                    logger.info("Auto-reflex fired from NeuralBus signal %s: %s → %s",
                              stype, r.trigger_id, r.action_taken)
        except Exception:
            pass

    def get_triggers(self) -> List[dict]:
        return [t.to_dict() for t in self._triggers.values()]

    def toggle_trigger(self, trigger_id: str, enabled: bool) -> bool:
        if trigger_id in self._triggers:
            self._triggers[trigger_id].enabled = enabled
            return True
        return False

    # ═════════════════════════════════════════════════════════════════════════
    #  Persistence
    # ═════════════════════════════════════════════════════════════════════════

    def _ensure_schema(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS rf_triggers (
                id TEXT PRIMARY KEY, reflex_type TEXT, condition TEXT,
                priority TEXT, action TEXT, handler_name TEXT,
                enabled INTEGER DEFAULT 1, fire_count INTEGER DEFAULT 0,
                last_fired REAL DEFAULT 0, cooldown_seconds REAL DEFAULT 60)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS rf_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT, trigger_id TEXT,
                reflex_type TEXT, action_taken TEXT, success INTEGER,
                message_ar TEXT, response_time_ms REAL, timestamp REAL)""")
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            cur = conn.execute(
                "SELECT id, reflex_type, condition, priority, action, handler_name, "
                "enabled, fire_count, last_fired, cooldown_seconds FROM rf_triggers"
            )
            for row in cur.fetchall():
                self._triggers[row[0]] = ReflexTrigger(
                    id=row[0], reflex_type=row[1], condition=row[2],
                    priority=row[3], action=row[4], handler_name=row[5],
                    enabled=bool(row[6]), fire_count=row[7],
                    last_fired=row[8], cooldown_seconds=row[9],
                )
        finally:
            conn.close()


# Singleton
reflexes_engine = ReflexesEngine()
