"""
BABSHARQII v34.0 — Fused Core (النواة المندمجة) [DEPRECATED — use MamounKernel + NeuralBus from neural_bus.py]
دمج جميع المحركات في دماغ واحد متكامل

⚠ WARNING: This module defines its OWN NeuralBus/NeuralSignal/SignalType classes
that differ from the real mamoun.core.neural_bus module. Do NOT import from here.
Use: from mamoun.core.neural_bus import neural_bus, NeuralSignal

Architecture:
  ┌─────────────────────────────────────────────────────────────┐
  │                    FUSED MAMOUN CORE                         │
  │                                                              │
  │  NeuralBus ←→ ConsciousnessLoop ←→ ReflexionEngine           │
  │      ↕              ↕                    ↕                    │
  │  ConscienceLayer ←→ HallucinationDetector ←→ GoalManager     │
  │      ↕              ↕                    ↕                    │
  │  AbsoluteExecutor ←→ CompositionalReasoner ←→ EWC            │
  └─────────────────────────────────────────────────────────────┘

The FusedCore is the UNIFIED BRAIN — all modules communicate through
the NeuralBus, creating emergent behavior from simple interactions.
"""

import asyncio
import time
import logging
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable, Set
from enum import Enum
from collections import defaultdict

logger = logging.getLogger("mamoun.fused_core")


# ═══════════════════════════════════════════════════════════════════════════════
#  Signal Types — 16 types for neural communication
# ═══════════════════════════════════════════════════════════════════════════════

class SignalType(str, Enum):
    """أنواع الإشارات العصبية — 16 نوع"""
    # حالة حيوية
    VITAL_CHANGE = "vital_change"
    ENERGY_LOW = "energy_low"
    ENERGY_HIGH = "energy_high"
    EMOTION_CHANGE = "emotion_change"

    # وعي
    PERCEPTION = "perception"
    SURPRISE = "surprise"
    INSIGHT = "insight"
    PREDICTION = "prediction"

    # ذاكرة
    MEMORY_STORED = "memory_stored"
    MEMORY_RECALLED = "memory_recalled"

    # تنفيذ
    ACTION_REQUESTED = "action_requested"
    ACTION_COMPLETED = "action_completed"
    ACTION_BLOCKED = "action_blocked"

    # تعلم
    SKILL_LEARNED = "skill_learned"
    GOAL_UPDATED = "goal_updated"
    CONSCIENCE_ALERT = "conscience_alert"


# ═══════════════════════════════════════════════════════════════════════════════
#  Neural Signal
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class NeuralSignal:
    """إشارة عصبية"""
    signal_type: SignalType = SignalType.VITAL_CHANGE
    source: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    priority: int = 2  # 0=background, 1=low, 2=normal, 3=high, 4=critical


# ═══════════════════════════════════════════════════════════════════════════════
#  NeuralBus — Simplified Pub/Sub for FusedCore
# ═══════════════════════════════════════════════════════════════════════════════

class NeuralBus:
    """
    الناقل العصبي — نظام Pub/Sub موحد

    Simplified API for the FusedCore:
      subscribe(signal_type, handler)
      publish(signal_type, source, payload)
    """

    def __init__(self):
        self._subscribers: Dict[SignalType, List[Callable]] = defaultdict(list)
        self._signal_log: List[NeuralSignal] = []
        self._stats = {
            "total_published": 0,
            "total_delivered": 0,
            "by_type": defaultdict(int),
        }

    def subscribe(self, signal_type: SignalType, handler: Callable):
        """
        اشتراك في نوع إشارة — Subscribe to a signal type.

        Args:
            signal_type: The type of signal to listen for.
            handler: Callable that receives a NeuralSignal.
        """
        self._subscribers[signal_type].append(handler)

    def unsubscribe(self, signal_type: SignalType, handler: Callable):
        """إلغاء اشتراك"""
        if handler in self._subscribers[signal_type]:
            self._subscribers[signal_type].remove(handler)

    def publish(self, signal_type: SignalType, source: str,
                payload: Dict[str, Any] = None) -> NeuralSignal:
        """
        نشر إشارة — Publish a signal to all subscribers.

        Args:
            signal_type: Type of signal.
            source: Source module name.
            payload: Signal data.

        Returns:
            The published NeuralSignal.
        """
        signal = NeuralSignal(
            signal_type=signal_type,
            source=source,
            payload=payload or {},
        )

        self._stats["total_published"] += 1
        self._stats["by_type"][signal_type.value] += 1
        self._signal_log.append(signal)

        # Deliver to all subscribers
        delivered = 0
        for handler in self._subscribers.get(signal_type, []):
            try:
                handler(signal)
                delivered += 1
                self._stats["total_delivered"] += 1
            except Exception as e:
                logger.warning("NeuralBus handler error: %s", e)

        logger.debug("NeuralBus: %s from %s → %d subscribers", signal_type.value, source, delivered)
        return signal

    def get_stats(self) -> Dict[str, Any]:
        """إحصائيات الناقل"""
        return {
            "total_published": self._stats["total_published"],
            "total_delivered": self._stats["total_delivered"],
            "by_type": dict(self._stats["by_type"]),
            "subscribers": {st.value: len(handlers) for st, handlers in self._subscribers.items()},
            "log_size": len(self._signal_log),
        }

    def get_recent_signals(self, limit: int = 20) -> List[Dict]:
        """آخر الإشارات"""
        return [
            {"type": s.signal_type.value, "source": s.source, "payload_keys": list(s.payload.keys())}
            for s in self._signal_log[-limit:]
        ]


# ═══════════════════════════════════════════════════════════════════════════════
#  ConsciousnessLoop — Background pulse
# ═══════════════════════════════════════════════════════════════════════════════

class ConsciousnessLoop:
    """
    حلقة الوعي — نبض خلفي 0.1 ثانية

    Runs in a background thread, publishing periodic signals.
    """

    PULSE_INTERVAL = 0.1  # seconds

    def __init__(self, neural_bus: NeuralBus):
        self._bus = neural_bus
        self._running = False
        self._pulse_count = 0
        self._thread = None

    def start(self):
        """بدء حلقة الوعي"""
        if self._running:
            return
        self._running = True
        import threading
        self._thread = threading.Thread(target=self._pulse_loop, daemon=True)
        self._thread.start()
        logger.info("ConsciousnessLoop started — pulse interval: %.1fs", self.PULSE_INTERVAL)

    def stop(self):
        """إيقاف حلقة الوعي"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("ConsciousnessLoop stopped after %d pulses", self._pulse_count)

    def _pulse_loop(self):
        """حلقة النبض"""
        while self._running:
            self._pulse_count += 1
            try:
                self._bus.publish(SignalType.VITAL_CHANGE, "consciousness_loop",
                                  {"pulse": self._pulse_count, "timestamp": time.time()})
            except Exception as e:
                logger.warning("ConsciousnessLoop pulse error: %s", e)
            time.sleep(self.PULSE_INTERVAL)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def pulse_count(self) -> int:
        return self._pulse_count


# ═══════════════════════════════════════════════════════════════════════════════
#  FusedMamounCore — The Unified Brain
# ═══════════════════════════════════════════════════════════════════════════════

class FusedMamounCore:
    """
    النواة المندمجة — دماغ مامون الموحد

    Pipeline:
      INPUT → ReflexionEngine.review → ConscienceLayer.review → Execute → PostReview → OUTPUT

    NeuralBus connections:
      - ENERGY_LOW → reduces retry attempts
      - EMOTION_CHANGE → adjusts response style
      - CONSCIENCE_ALERT → logs and escalates
    """

    def __init__(self, db_path: Optional[Path] = None):
        # v34: Use unified DB path instead of /tmp/
        if db_path is None:
            try:
                from mamoun.core.unified_db import UNIFIED_DB_PATH
                self._db_path = UNIFIED_DB_PATH
            except ImportError:
                self._db_path = Path("/tmp/mamoun/fused_core.db")
        else:
            self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        # Core components
        self._bus = NeuralBus()
        self._consciousness = ConsciousnessLoop(self._bus)
        self._reflexion_engine = None
        self._conscience = None
        self._hallucination_detector = None

        # State
        self._energy = 80.0
        self._emotion = "neutral"
        self._request_count = 0
        self._block_count = 0
        self._initialized = False

        # Subscribe to bus signals
        self._bus.subscribe(SignalType.ENERGY_LOW, self._on_energy_low)
        self._bus.subscribe(SignalType.EMOTION_CHANGE, self._on_emotion_change)
        self._bus.subscribe(SignalType.CONSCIENCE_ALERT, self._on_conscience_alert)

    def initialize(self) -> bool:
        """تهيئة النواة المندمجة"""
        try:
            self._ensure_schema()
            self._initialized = True
            logger.info("FusedMamounCore initialized — bus stats: %s", self._bus.get_stats())
            return True
        except Exception as e:
            logger.error("FusedMamounCore init failed: %s", e)
            return False

    def _ensure_schema(self):
        """Create DB tables"""
        conn = sqlite3.connect(str(self._db_path))
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS fc_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                request TEXT NOT NULL,
                blocked INTEGER DEFAULT 0,
                reason TEXT DEFAULT '',
                result TEXT DEFAULT '')""")
            conn.execute("""CREATE TABLE IF NOT EXISTS fc_state (
                key TEXT PRIMARY KEY, value TEXT)""")
            conn.commit()
        finally:
            conn.close()

    def set_reflexion_engine(self, engine):
        """تعيين محرك التأمل الانعكاسي"""
        self._reflexion_engine = engine

    def set_conscience(self, conscience):
        """تعيين طبقة الضمير"""
        self._conscience = conscience

    def set_hallucination_detector(self, detector):
        """تعيين كاشف الهلوسة"""
        self._hallucination_detector = detector

    @property
    def bus(self) -> NeuralBus:
        """الناقل العصبي"""
        return self._bus

    # ═════════════════════════════════════════════════════════════════════════
    #  Signal Handlers
    # ═════════════════════════════════════════════════════════════════════════

    def _on_energy_low(self, signal: NeuralSignal):
        """ENERGY_LOW → يقلل المحاولات"""
        level = signal.payload.get("level", 0)
        if level < 0.3:
            self._energy = max(0, self._energy - 10)
            logger.info("Energy LOW signal received — energy now: %.1f", self._energy)

    def _on_emotion_change(self, signal: NeuralSignal):
        """EMOTION_CHANGE → يحدّث المؤشرات"""
        self._emotion = signal.payload.get("emotion", "neutral")
        logger.info("Emotion changed to: %s", self._emotion)

    def _on_conscience_alert(self, signal: NeuralSignal):
        """CONSCIENCE_ALERT → يسجّل ويرفع"""
        logger.warning("Conscience ALERT: %s", signal.payload.get("reason", "unknown"))

    # ═════════════════════════════════════════════════════════════════════════
    #  Main Pipeline
    # ═════════════════════════════════════════════════════════════════════════

    async def process(self, request: str, context: Dict = None) -> Dict[str, Any]:
        """
        معالجة مدمجة — Pipeline: Review → Conscience → Execute → PostReview

        Args:
            request: The user request text.
            context: Additional context dict.

        Returns:
            Dict with blocked, result, reason, etc.
        """
        if not self._initialized:
            self.initialize()

        context = context or {}
        self._request_count += 1

        # Step 1: ReflexionEngine review
        if self._reflexion_engine:
            try:
                review = self._reflexion_engine.review_and_block(request, context)
                if not review.get("approved", True):
                    self._block_count += 1
                    self._bus.publish(SignalType.ACTION_BLOCKED, "fused_core",
                                      {"reason": review.get("reason", "Reflexion block")})
                    return {
                        "blocked": True,
                        "reason": review.get("reason", "Blocked by ReflexionEngine"),
                        "stage": "reflexion",
                    }
            except Exception as e:
                logger.warning("ReflexionEngine review failed: %s", e)

        # Step 2: ConscienceLayer review
        if self._conscience:
            try:
                conscience_result = self._conscience.review(request)
                if not conscience_result.get("approved", True):
                    self._block_count += 1
                    self._bus.publish(SignalType.CONSCIENCE_ALERT, "fused_core",
                                      {"reason": conscience_result.get("reason", "Conscience block")})
                    return {
                        "blocked": True,
                        "reason": conscience_result.get("reason", "Blocked by ConscienceLayer"),
                        "stage": "conscience",
                    }
            except Exception as e:
                logger.warning("ConscienceLayer review failed: %s", e)

        # Step 3: Execute (simplified — just acknowledge)
        self._bus.publish(SignalType.ACTION_REQUESTED, "fused_core",
                          {"request": request[:200]})

        result = {
            "blocked": False,
            "result": f"Processed: {request[:100]}",
            "stage": "completed",
        }

        self._bus.publish(SignalType.ACTION_COMPLETED, "fused_core",
                          {"success": True})

        # Persist
        self._persist_request(request, False, "", str(result.get("result", "")))

        return result

    def _persist_request(self, request: str, blocked: bool, reason: str, result: str):
        """حفظ الطلب"""
        try:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    "INSERT INTO fc_requests (timestamp, request, blocked, reason, result) VALUES (?, ?, ?, ?, ?)",
                    (time.time(), request[:500], 1 if blocked else 0, reason[:200], result[:500]),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Failed to persist request: %s", e)

    # ═════════════════════════════════════════════════════════════════════════
    #  Status
    # ═════════════════════════════════════════════════════════════════════════

    def get_status(self) -> Dict[str, Any]:
        """حالة النواة المندمجة"""
        return {
            "initialized": self._initialized,
            "energy": self._energy,
            "emotion": self._emotion,
            "request_count": self._request_count,
            "block_count": self._block_count,
            "consciousness_running": self._consciousness.is_running,
            "bus_stats": self._bus.get_stats(),
        }
