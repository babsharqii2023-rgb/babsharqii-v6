"""
BABSHARQII v62 — NeuralBus (BACKWARD-COMPATIBLE ADAPTER)

This file now serves as a compatibility layer that redirects to
the new shared/neural_bus.py while preserving the old publish() API.

Migration: core/neural_bus.py → core/shared/neural_bus.py
Status: ADAPTER — all calls forwarded to shared NeuralBus

v62 FIX: Added ALL missing exports called by v23.py, project_orchestrator.py, dashboard_bridge.py:
- SignalPriority enum, NeuralBus class alias
- get_status(), get_recent_signals(), get_signal_flow(), get_subscriptions()
- _initialized flag, get_instance() classmethod
- subscribe() with list-of-signals support (main.py compatibility)
"""

import warnings
import time
import json
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional, Any, Callable, Union
from enum import Enum

logger = logging.getLogger("mamoun.core.neural_bus")

# Import new NeuralBus
from mamoun.core.shared.neural_bus import (
    NeuralBus as _NewNeuralBus,
    Event as _NewEvent,
    EventType as _NewEventType,
    get_neural_bus as _get_new_neural_bus,
)


# ── Backward-compatible signal types ─────────────────────────────────────

class SignalType(str, Enum):
    """Signal types (backward-compatible with old NeuralBus)."""
    PERCEPTION = "perception"
    ACTION = "action"
    HEALING = "healing"
    EVOLUTION = "evolution"
    LEARNING = "learning"
    REFLECTION = "reflection"
    RESEARCH = "research"
    SYSTEM = "system"
    HEARTBEAT = "heartbeat"
    META_ASSESSMENT = "meta_assessment"
    META_STAGNATION = "meta_stagnation"
    HEALTH_CRITICAL = "health_critical"
    HEALING_CHECK = "healing_check"


class SignalPriority(int, Enum):
    """Signal priority levels (backward-compatible with v23.py, project_orchestrator.py)."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 5
    LOW = 8
    BACKGROUND = 10


@dataclass
class NeuralSignal:
    """A signal on the NeuralBus (backward-compatible)."""
    signal_type: str
    source: str
    payload: dict = field(default_factory=dict)
    timestamp: float = 0.0
    priority: int = 5
    id: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.id:
            self.id = f"sig_{int(self.timestamp * 1000)}_{hash(self.signal_type) % 10000:04d}"


class NeuralBusCompat:
    """
    Backward-compatible NeuralBus that delegates to the new shared NeuralBus.
    
    Old API: neural_bus.publish(signal_type, source, payload)
    New API: neural_bus.publish(Event(event_type, source, data))
    
    This adapter translates between the two.
    
    v62: Added full API compatibility with v23.py endpoints and main.py.
    """

    def __init__(self):
        self._new_bus = _get_new_neural_bus()
        self._subscribers: dict[str, list[Callable]] = {}
        self._signal_history: list[NeuralSignal] = []
        self._max_history = 1000
        self._initialized = True  # v62: flag checked by v23.py
        logger.info("NeuralBusCompat initialized — delegating to shared NeuralBus")

    def publish(
        self,
        signal_type: str,
        source: str = "",
        payload: dict = None,
        priority: Union[int, SignalPriority] = 5,
    ) -> NeuralSignal:
        """
        Publish a signal (old API compatibility).
        Translates to new Event and publishes on shared NeuralBus.
        """
        # Convert SignalPriority to int if needed
        if isinstance(priority, SignalPriority):
            priority = priority.value

        signal = NeuralSignal(
            signal_type=signal_type,
            source=source,
            payload=payload or {},
            priority=priority,
        )

        # Record in history
        self._signal_history.append(signal)
        if len(self._signal_history) > self._max_history:
            self._signal_history = self._signal_history[-500:]

        # Convert to new Event format and publish on shared bus
        try:
            event_type = self._map_signal_to_event(signal_type)
            event = _NewEvent(
                event_type=event_type,
                source=source,
                data=payload or {},
            )
            # Publish asynchronously (fire and forget for sync compatibility)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self._new_bus.publish(event))
                else:
                    loop.run_until_complete(self._new_bus.publish(event))
            except RuntimeError:
                # No event loop — queue for later
                pass
        except Exception as e:
            logger.debug(f"Failed to publish on new NeuralBus: {e}")

        # Notify local subscribers (old-style)
        callbacks = self._subscribers.get(signal_type, [])
        for callback in callbacks:
            try:
                callback(signal)
            except Exception as e:
                logger.warning(f"Subscriber callback failed: {e}")

        return signal

    def subscribe(
        self,
        subscriber_id_or_signal_type: str,
        signal_types_or_callback: Union[list[str], str, Callable] = None,
        callback: Callable = None,
        handler: Callable = None,
        priority_filter: int = None,
    ) -> None:
        """
        Subscribe to signal types (backward-compatible with BOTH old and main.py APIs).
        
        Old API: subscribe(signal_type, callback)
        Main.py API: subscribe(subscriber_id, signal_types_list, handler=fn, priority_filter=N)
        """
        # Detect main.py-style call: subscribe("name", ["sig1", "sig2"], handler=fn)
        if isinstance(signal_types_or_callback, list) and (handler or callback):
            # Main.py style: subscriber_id, list of signal types, handler
            actual_handler = handler or callback
            for sig_type in signal_types_or_callback:
                if sig_type not in self._subscribers:
                    self._subscribers[sig_type] = []
                self._subscribers[sig_type].append(actual_handler)
                # Also subscribe on new bus
                try:
                    event_type = self._map_signal_to_event(sig_type)
                    self._new_bus.subscribe(event_type.value, actual_handler)
                except Exception:
                    pass
            return

        # Old API: subscribe(signal_type, callback)
        if isinstance(signal_types_or_callback, (str, Callable)):
            if callable(signal_types_or_callback):
                # subscribe(signal_type, callback) where signal_type is first arg
                sig_type = subscriber_id_or_signal_type
                cb = signal_types_or_callback
            else:
                # subscribe(subscriber_id, signal_type_string)
                sig_type = signal_types_or_callback
                cb = callback or handler
        else:
            sig_type = subscriber_id_or_signal_type
            cb = callback or handler

        if not cb:
            return

        if sig_type not in self._subscribers:
            self._subscribers[sig_type] = []
        self._subscribers[sig_type].append(cb)

        # Also subscribe on new bus
        try:
            event_type = self._map_signal_to_event(sig_type)
            self._new_bus.subscribe(event_type.value, cb)
        except Exception:
            pass

    def unsubscribe(self, signal_type: str, callback: Callable) -> None:
        """Unsubscribe from a signal type."""
        if signal_type in self._subscribers:
            self._subscribers[signal_type] = [
                cb for cb in self._subscribers[signal_type] if cb != callback
            ]

    def get_history(self, signal_type: str = None, limit: int = 50) -> list:
        """Get signal history."""
        if signal_type:
            filtered = [s for s in self._signal_history if s.signal_type == signal_type]
        else:
            filtered = self._signal_history
        return filtered[-limit:]

    def get_stats(self) -> dict:
        """Get bus statistics."""
        new_stats = {}
        try:
            new_stats = self._new_bus.get_stats()
        except Exception:
            pass

        return {
            "total_signals": len(self._signal_history),
            "subscriber_count": sum(len(cbs) for cbs in self._subscribers.values()),
            "signal_types": list(self._subscribers.keys()),
            "new_bus_stats": new_stats,
        }

    # ── v62: Methods required by v23.py API endpoints ────────────────────

    def get_status(self) -> dict:
        """حالة الناقل العصبي — called by /v23/neural-bus/status."""
        return {
            "initialized": self._initialized,
            "total_signals": len(self._signal_history),
            "subscribers": sum(len(cbs) for cbs in self._subscribers.values()),
            "signal_types": list(self._subscribers.keys()),
            "stats": self.get_stats(),
        }

    def get_recent_signals(self, limit: int = 20) -> list[dict]:
        """آخر الإشارات العصبية — called by /v23/neural-bus/signals."""
        recent = self._signal_history[-limit:]
        return [
            {
                "id": s.id,
                "type": s.signal_type,
                "source": s.source,
                "priority": s.priority,
                "timestamp": s.timestamp,
                "payload_preview": str(s.payload)[:200] if s.payload else "",
            }
            for s in recent
        ]

    def get_signal_flow(self) -> dict:
        """تدفق الإشارات بين المحركات — called by /v23/neural-bus/flow."""
        flow = {}
        for signal in self._signal_history[-100:]:
            source = signal.source.split(":")[0] if signal.source else "unknown"
            target_types = signal.signal_type
            if source not in flow:
                flow[source] = {}
            flow[source][target_types] = flow[source].get(target_types, 0) + 1
        return {"flow": flow, "total_sources": len(flow)}

    def get_subscriptions(self) -> dict:
        """كل الاشتراكات العصبية — called by /v23/neural-bus/subscriptions."""
        subs = {}
        for sig_type, callbacks in self._subscribers.items():
            subs[sig_type] = len(callbacks)
        return subs

    def persist_stats(self):
        """Persist NeuralBus stats (called during shutdown)."""
        try:
            self._new_bus.persist_stats()
        except Exception:
            pass

    @classmethod
    def get_instance(cls):
        """Get the singleton instance (called by dashboard_bridge.py)."""
        return _get_neural_bus_module()

    def _map_signal_to_event(self, signal_type: str):
        """Map old signal type string to new EventType."""
        mapping = {
            "perception": _NewEventType.PERCEPTION,
            "action": _NewEventType.ACTION,
            "healing": _NewEventType.HEALING_CHECK,
            "evolution": _NewEventType.EVOLUTION,
            "learning": _NewEventType.LEARNING,
            "reflection": _NewEventType.REFLECTION,
            "research": _NewEventType.RESEARCH,
            "system": _NewEventType.SYSTEM,
            "heartbeat": _NewEventType.HEARTBEAT,
            "meta_assessment": _NewEventType.META_ASSESSMENT,
            "meta_stagnation": _NewEventType.META_STAGNATION,
            "health_critical": _NewEventType.HEALTH_CRITICAL,
            "healing_check": _NewEventType.HEALING_CHECK,
            "emotion_shift": _NewEventType.SYSTEM,
            "energy_drop": _NewEventType.SYSTEM,
            "stress_spike": _NewEventType.SYSTEM,
            "vital_change": _NewEventType.SYSTEM,
            "bond_strengthened": _NewEventType.SYSTEM,
            "bond_weakened": _NewEventType.SYSTEM,
            "user_absent": _NewEventType.SYSTEM,
            "user_returned": _NewEventType.SYSTEM,
            "action_completed": _NewEventType.SYSTEM,
            "action_failed": _NewEventType.SYSTEM,
            "error_detected": _NewEventType.SYSTEM,
            "memory_stored": _NewEventType.SYSTEM,
            "prediction_failed": _NewEventType.SYSTEM,
            "pattern_detected": _NewEventType.SYSTEM,
        }
        return mapping.get(signal_type, _NewEventType.SYSTEM)


# ── Backward-compatible NeuralBus class alias ────────────────────────────
NeuralBus = NeuralBusCompat


# ── Singleton ───────────────────────────────────────────────────────────
_neural_bus_instance: Optional[NeuralBusCompat] = None

def get_neural_bus() -> NeuralBusCompat:
    """Get the singleton NeuralBus instance."""
    global _neural_bus_instance
    if _neural_bus_instance is None:
        _neural_bus_instance = NeuralBusCompat()
    return _neural_bus_instance

# Backward-compatible module-level instance
neural_bus = None

def _get_neural_bus_module():
    """Lazy initialization of module-level neural_bus."""
    global neural_bus
    if neural_bus is None:
        neural_bus = get_neural_bus()
    return neural_bus

# Override module getattr for `neural_bus` access
def __getattr__(name):
    if name == "neural_bus":
        return _get_neural_bus_module()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

logger.info("neural_bus → redirected to shared/neural_bus (v62 full adapter)")
