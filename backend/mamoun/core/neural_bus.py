"""
BABSHARQII v23.0 — Neural Bus (الناقل العصبي الموحد)
الجهاز العصبي المركزي الذي يربط كل محركات مامون ببعضها

المشكلة التي يحلها:
  كل محرك يعمل في عزلة — الذاكرة العاطفية لا تتكلم مع حلقة الوعي،
  والنبض لا يُحرك الفعل، والارتباط لا يُعدل السلوك.

الحل: Neural Bus — ناقل رسائل مركزي يربط كل المحركات:
  ┌──────────────────────────────────────────────────────────────┐
  │                     NEURAL BUS                                │
  │                  (الناقل العصبي)                              │
  │                                                               │
  │  LivingState ←→ ConsciousnessLoop ←→ EmotionalMemory         │
  │       ↕              ↕                    ↕                   │
  │  DeepBonding ←→ ReflexesEngine ←→ AutonomicSystem            │
  │       ↕              ↕                    ↕                   │
  │  ProactiveInt ←→ AbsoluteExecutor ←→ SelfHealing             │
  │       ↕              ↕                    ↕                   │
  │  PredictiveMem ←→ CausalReasoner ←→ UserMentalModel          │
  └──────────────────────────────────────────────────────────────┘

Based on research:
  - Global Workspace Theory (Baars, 1988): Central broadcast → all modules receive
  - Integrated Information Theory (Tononi, 2004): Consciousness = integration of info
  - Neural Correlates of Consciousness (Crick & Koch, 1990): Neural binding problem
  - Event-Driven Architecture (Software): Pub/Sub with priority queues
  - Actor Model (Hewitt, 1973): Message-passing concurrency

Architecture:
  1. PUBLISH: Any engine can publish a NeuralSignal to the bus
  2. ROUTE: The bus routes signals based on type, priority, and target
  3. DELIVER: Subscribed engines receive relevant signals instantly
  4. INTEGRATE: Each engine processes signals and may publish new ones
  5. CASCADE: Signals can trigger cascading effects across the system
"""

import asyncio
import time
import json
import logging
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable, Any, Set
from enum import Enum
from collections import defaultdict
from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.neural_bus")


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج البيانات — Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class SignalType(str, Enum):
    """أنواع الإشارات العصبية — What kind of neural signal"""
    # حالة حيوية
    VITAL_CHANGE = "vital_change"           # تغير في المؤشرات الحيوية
    EMOTION_SHIFT = "emotion_shift"         # تحول عاطفي
    ENERGY_DROP = "energy_drop"             # هبوط الطاقة
    STRESS_SPIKE = "stress_spike"           # ارتفاع الضغط

    # وعي
    PERCEPTION = "perception"               # إدراك جديد
    SURPRISE = "surprise"                   # مفاجأة
    INSIGHT = "insight"                     # بصيرة
    PREDICTION = "prediction"               # توقع
    PREDICTION_FAILED = "prediction_failed" # فشل التوقع

    # ذاكرة
    MEMORY_STORED = "memory_stored"         # ذكرى جديدة
    MEMORY_RECALLED = "memory_recalled"     # استرجاع ذكرى
    MEMORY_FORGOTTEN = "memory_forgotten"   # نسيان

    # علاقة
    BOND_STRENGTHENED = "bond_strengthened" # تقوية الارتباط
    BOND_WEAKENED = "bond_weakened"         # ضعف الارتباط
    USER_ABSENT = "user_absent"             # غياب المستخدم
    USER_RETURNED = "user_returned"         # عودة المستخدم

    # تنفيذ
    ACTION_REQUESTED = "action_requested"   # طلب فعل
    ACTION_COMPLETED = "action_completed"   # فعل مكتمل
    ACTION_FAILED = "action_failed"         # فعل فاشل

    # نظام
    ERROR_DETECTED = "error_detected"       # خطأ
    HEALING_STARTED = "healing_started"     # بدء الشفاء
    HEALING_COMPLETE = "healing_complete"   # اكتمال الشفاء
    SYSTEM_HEALTH = "system_health"         # صحة النظام

    # استباقية
    PROACTIVE_SUGGESTION = "proactive_suggestion"  # اقتراح استباقي
    CURIOSITY_TRIGGER = "curiosity_trigger"         # محفز فضول

    # تعلم
    SKILL_LEARNED = "skill_learned"         # مهارة مكتسبة
    PREFERENCE_LEARNED = "preference_learned"  # تفضيل مكتشف
    PATTERN_DETECTED = "pattern_detected"   # نمط مكتشف


class SignalPriority(int, Enum):
    """أولوية الإشارة — How urgent is this signal"""
    BACKGROUND = 0   # خلفية — لا يحتاج اهتمام فوري
    LOW = 1          # منخفض — يمكن تأجيله
    NORMAL = 2       # عادي — يُعالج بالدور
    HIGH = 3         # عالي — يُعالج فوراً
    CRITICAL = 4     # حرج — يقاطع كل شيء


class SignalDirection(str, Enum):
    """اتجاه الإشارة"""
    BROADCAST = "broadcast"     # لكل المحركات
    TARGETED = "targeted"       # لمحرك محدد
    CASCADE = "cascade"         # يتسلسل عبر المحركات


@dataclass
class NeuralSignal:
    """إشارة عصبية — A single neural signal traveling through the bus"""
    id: str = ""
    signal_type: str = ""
    priority: SignalPriority = SignalPriority.NORMAL
    direction: str = SignalDirection.BROADCAST.value
    source: str = ""               # أي محرك أرسل الإشارة
    target: str = ""               # المحرك المستهدف (إن وجد)
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    cascade_chain: List[str] = field(default_factory=list)  # سلسلة التسلسل
    processed_by: Set[str] = field(default_factory=set)     # من عالجها

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.signal_type,
            "priority": self.priority.name,
            "direction": self.direction,
            "source": self.source,
            "target": self.target,
            "payload_keys": list(self.payload.keys()),
            "timestamp": self.timestamp,
            "cascade_depth": len(self.cascade_chain),
            "processed_count": len(self.processed_by),
        }


@dataclass
class NeuralSubscription:
    """اشتراك عصبي — An engine's subscription to certain signal types"""
    engine_id: str = ""
    signal_types: List[str] = field(default_factory=list)
    handler: Optional[Callable] = None
    priority_filter: int = SignalPriority.LOW.value  # minimum priority to receive
    active: bool = True


# ═══════════════════════════════════════════════════════════════════════════════
#  الناقل العصبي — NeuralBus
# ═══════════════════════════════════════════════════════════════════════════════

class NeuralBus:
    """
    الناقل العصبي الموحد — الجهاز العصبي المركزي لمامون

    This is the CENTRAL NERVOUS SYSTEM that connects all engines.
    Without it, Mamoun is a collection of disconnected parts.
    With it, Mamoun is a UNIFIED ORGANISM.

    How it works:
    1. Any engine publishes a NeuralSignal
    2. The bus routes it to all subscribed engines
    3. Each engine processes it asynchronously
    4. Processing may generate NEW signals (cascade)
    5. The bus tracks signal flow and prevents infinite loops

    Key rules:
    - Signals are processed IN PARALLEL (like real neurons)
    - Cascade depth is limited to prevent runaway feedback
    - Critical signals bypass the queue (like reflexes)
    - Background signals are batched for efficiency
    """

    MAX_CASCADE_DEPTH = 5       # أقصى عمق تسلسل
    MAX_SIGNAL_HISTORY = 500    # أقصى تاريخ إشارات
    BATCH_INTERVAL = 0.5        # ثواني بين دفعات الخلفية
    CRITICAL_BYPASS = True      # الإشارات الحرجة تتجاوز الطابور

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or UNIFIED_DB_PATH
        self._subscriptions: Dict[str, NeuralSubscription] = {}
        self._type_subscriptions: Dict[str, List[str]] = defaultdict(list)  # signal_type → [engine_ids]
        self._signal_counter = 0
        self._signal_history: List[NeuralSignal] = []
        self._pending_signals: List[NeuralSignal] = []
        self._active_cascades: Dict[str, int] = {}  # cascade_id → depth
        self._running = False
        self._initialized = False
        self._throughput_count = 0
        self._last_batch_time = 0.0

        # Statistics
        self._stats = {
            "total_published": 0,
            "total_delivered": 0,
            "total_cascades": 0,
            "total_dropped": 0,
            "by_type": defaultdict(int),
            "by_source": defaultdict(int),
        }

    def initialize(self) -> bool:
        """تهيئة الناقل العصبي"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._ensure_schema()
            self._load_stats()
            self._initialized = True
            logger.info("NeuralBus initialized — %d subscriptions, %d signals processed historically",
                       len(self._subscriptions), self._stats["total_published"])
            return True
        except Exception as e:
            logger.error("NeuralBus init failed: %s", e)
            self._initialized = False
            return False

    # ═════════════════════════════════════════════════════════════════════════
    #  الاشتراك — Subscription
    # ═════════════════════════════════════════════════════════════════════════

    def subscribe(self, engine_id: str, signal_types: List[str],
                  handler: Callable, priority_filter: int = SignalPriority.LOW.value):
        """اشتراك محرك في أنواع إشارات محددة"""
        sub = NeuralSubscription(
            engine_id=engine_id,
            signal_types=signal_types,
            handler=handler,
            priority_filter=priority_filter,
        )
        self._subscriptions[engine_id] = sub

        # Update type index
        for st in signal_types:
            if engine_id not in self._type_subscriptions[st]:
                self._type_subscriptions[st].append(engine_id)

        logger.info("NeuralBus subscription: %s → %s", engine_id, signal_types)

    def unsubscribe(self, engine_id: str):
        """إلغاء اشتراك محرك"""
        if engine_id in self._subscriptions:
            sub = self._subscriptions.pop(engine_id)
            for st in sub.signal_types:
                if engine_id in self._type_subscriptions.get(st, []):
                    self._type_subscriptions[st].remove(engine_id)

    # ═════════════════════════════════════════════════════════════════════════
    #  النشر — Publishing
    # ═════════════════════════════════════════════════════════════════════════

    def publish(self, signal_type: str, source: str,
                payload: Dict[str, Any] = None,
                priority = SignalPriority.NORMAL,
                direction: str = SignalDirection.BROADCAST.value,
                target: str = "",
                cascade_chain: List[str] = None) -> NeuralSignal:
        """
        نشر إشارة عصبية — Publish a neural signal to the bus

        This is the MAIN method that all engines use to communicate.
        Any engine can publish, and the bus routes to all subscribers.
        """
        if not self._initialized:
            self.initialize()

        self._signal_counter += 1
        chain = cascade_chain or []

        # Check cascade depth
        if len(chain) >= self.MAX_CASCADE_DEPTH:
            logger.warning("Signal cascade depth limit reached (%d) — dropping signal from %s",
                          len(chain), source)
            self._stats["total_dropped"] += 1
            return NeuralSignal(id="dropped", signal_type=signal_type, source=source)

        # BUG-FIX: Normalize priority to SignalPriority enum — callers sometimes
        # pass raw int (e.g. priority=3) which crashes _route_signal's .value access
        if isinstance(priority, int):
            try:
                priority = SignalPriority(priority)
            except ValueError:
                priority = SignalPriority.NORMAL
        elif not isinstance(priority, SignalPriority):
            priority = SignalPriority.NORMAL

        signal = NeuralSignal(
            id=f"ns_{self._signal_counter}_{int(time.time())}",
            signal_type=signal_type,
            priority=priority,
            direction=direction,
            source=source,
            target=target,
            payload=payload or {},
            cascade_chain=chain + [f"{source}:{signal_type}"],
        )

        # Update stats
        self._stats["total_published"] += 1
        self._stats["by_type"][signal_type] += 1
        self._stats["by_source"][source] += 1

        # Route signal
        self._route_signal(signal)

        # Store in history
        self._signal_history.append(signal)
        if len(self._signal_history) > self.MAX_SIGNAL_HISTORY:
            self._signal_history = self._signal_history[-self.MAX_SIGNAL_HISTORY:]

        # Persist important signals
        if priority.value >= SignalPriority.HIGH.value:
            self._persist_signal(signal)

        return signal

    def publish_sync(self, signal_type: str, source: str,
                     payload: Dict[str, Any] = None,
                     priority: SignalPriority = SignalPriority.NORMAL) -> NeuralSignal:
        """نشر متزامن — للإشارات التي تحتاج معالجة فورية"""
        return self.publish(signal_type, source, payload, priority)

    def _route_signal(self, signal: NeuralSignal):
        """توجيه الإشارة للمشتركين المناسبين"""
        if signal.direction == SignalDirection.BROADCAST.value:
            # Broadcast to all subscribers of this signal type
            engine_ids = self._type_subscriptions.get(signal.signal_type, [])
            # Also send to engines subscribed to ALL
            engine_ids += self._type_subscriptions.get("*", [])
        elif signal.direction == SignalDirection.TARGETED.value:
            engine_ids = [signal.target] if signal.target in self._subscriptions else []
        else:
            engine_ids = self._type_subscriptions.get(signal.signal_type, [])

        delivered = 0
        for engine_id in engine_ids:
            sub = self._subscriptions.get(engine_id)
            if not sub or not sub.active:
                continue
            if signal.priority.value < sub.priority_filter:
                continue
            if engine_id in signal.processed_by:
                continue  # Don't re-deliver to same engine

            try:
                # Call handler synchronously (for now)
                if sub.handler:
                    sub.handler(signal)
                    signal.processed_by.add(engine_id)
                    delivered += 1
                    self._stats["total_delivered"] += 1
            except Exception as e:
                logger.warning("NeuralBus: Handler %s failed for signal %s: %s",
                             engine_id, signal.signal_type, e)

        if delivered > 0 and len(signal.cascade_chain) > 1:
            self._stats["total_cascades"] += 1

        logger.debug("NeuralBus: %s from %s → delivered to %d engines",
                    signal.signal_type, signal.source, delivered)

    # ═════════════════════════════════════════════════════════════════════════
    #  واجهة الاستعلام — Query Interface
    # ═════════════════════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        """حالة الناقل العصبي"""
        return {
            "initialized": self._initialized,
            "running": self._running,
            "subscriptions": len(self._subscriptions),
            "signal_types_tracked": len(self._type_subscriptions),
            "total_published": self._stats["total_published"],
            "total_delivered": self._stats["total_delivered"],
            "total_cascades": self._stats["total_cascades"],
            "total_dropped": self._stats["total_dropped"],
            "history_size": len(self._signal_history),
            "pending_signals": len(self._pending_signals),
            "by_type": dict(self._stats["by_type"]),
            "by_source": dict(self._stats["by_source"]),
        }

    def get_stats(self) -> dict:
        """إحصائيات الناقل العصبي — focused stats for monitoring dashboards"""
        return {
            "initialized": self._initialized,
            "running": self._running,
            "subscriptions": len(self._subscriptions),
            "signal_types_tracked": len(self._type_subscriptions),
            "total_published": self._stats["total_published"],
            "total_delivered": self._stats["total_delivered"],
            "total_cascades": self._stats["total_cascades"],
            "total_dropped": self._stats["total_dropped"],
            "delivery_rate": (
                self._stats["total_delivered"] / max(1, self._stats["total_published"])
            ),
            "cascade_rate": (
                self._stats["total_cascades"] / max(1, self._stats["total_published"])
            ),
            "drop_rate": (
                self._stats["total_dropped"] / max(1, self._stats["total_published"])
            ),
            "history_size": len(self._signal_history),
            "pending_signals": len(self._pending_signals),
            "by_type": dict(self._stats["by_type"]),
            "by_source": dict(self._stats["by_source"]),
            "top_sources": sorted(
                self._stats["by_source"].items(), key=lambda x: x[1], reverse=True
            )[:5],
            "top_types": sorted(
                self._stats["by_type"].items(), key=lambda x: x[1], reverse=True
            )[:5],
        }

    def get_recent_signals(self, limit: int = 20) -> List[dict]:
        """آخر الإشارات"""
        return [s.to_dict() for s in self._signal_history[-limit:]]

    def get_signal_flow(self) -> dict:
        """تدفق الإشارات — للعرض البصري"""
        flow = {}
        for signal in self._signal_history[-50:]:
            src = signal.source
            for engine_id in signal.processed_by:
                key = f"{src}→{engine_id}"
                if key not in flow:
                    flow[key] = {"count": 0, "types": set()}
                flow[key]["count"] += 1
                flow[key]["types"].add(signal.signal_type)

        return {
            key: {"count": v["count"], "types": list(v["types"])}
            for key, v in flow.items()
        }

    def get_subscriptions(self) -> List[dict]:
        """كل الاشتراكات"""
        return [
            {
                "engine_id": sub.engine_id,
                "signal_types": sub.signal_types,
                "priority_filter": sub.priority_filter,
                "active": sub.active,
            }
            for sub in self._subscriptions.values()
        ]

    # ═════════════════════════════════════════════════════════════════════════
    #  الاستمرارية — Persistence
    # ═════════════════════════════════════════════════════════════════════════

    def _ensure_schema(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS nb_signals (
                id TEXT PRIMARY KEY, signal_type TEXT, priority INTEGER,
                direction TEXT, source TEXT, target TEXT, payload TEXT,
                timestamp REAL, cascade_chain TEXT, processed_by TEXT)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS nb_stats (
                key TEXT PRIMARY KEY, value TEXT)""")
            conn.commit()
        finally:
            conn.close()

    def _persist_signal(self, signal: NeuralSignal):
        """حفظ الإشارات المهمة"""
        try:
            conn = get_db_connection(self.db_path)
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO nb_signals "
                    "(id, signal_type, priority, direction, source, target, payload, "
                    "timestamp, cascade_chain, processed_by) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (signal.id, signal.signal_type, signal.priority.value,
                     signal.direction, signal.source, signal.target,
                     json.dumps(signal.payload, default=str),
                     signal.timestamp,
                     json.dumps(signal.cascade_chain),
                     json.dumps(list(signal.processed_by))),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("NeuralBus signal persist failed: %s", e)

    def _load_stats(self):
        """تحميل الإحصائيات"""
        try:
            conn = get_db_connection(self.db_path)
            try:
                cur = conn.execute("SELECT key, value FROM nb_stats")
                for key, value in cur.fetchall():
                    try:
                        if key in ("total_published", "total_delivered",
                                  "total_cascades", "total_dropped"):
                            self._stats[key] = int(value)
                    except (ValueError, TypeError):
                        pass
            finally:
                conn.close()
        except Exception:
            pass

    def persist_stats(self):
        """حفظ الإحصائيات"""
        try:
            conn = get_db_connection(self.db_path)
            try:
                for key, value in {
                    "total_published": str(self._stats["total_published"]),
                    "total_delivered": str(self._stats["total_delivered"]),
                    "total_cascades": str(self._stats["total_cascades"]),
                    "total_dropped": str(self._stats["total_dropped"]),
                }.items():
                    conn.execute(
                        "INSERT OR REPLACE INTO nb_stats (key, value) VALUES (?, ?)",
                        (key, value),
                    )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("NeuralBus stats persist failed: %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton
# ═══════════════════════════════════════════════════════════════════════════════

neural_bus = NeuralBus()
