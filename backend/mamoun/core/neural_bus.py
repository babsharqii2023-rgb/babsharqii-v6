"""
BABSHARQII v61 — NeuralBus (BACKWARD-COMPATIBLE ADAPTER)

This file now serves as a compatibility layer that redirects to
the new shared/neural_bus.py while preserving the old publish() API.

Migration: core/neural_bus.py → core/shared/neural_bus.py
Status: ADAPTER — all calls forwarded to shared NeuralBus
"""

import warnings
import time
import json
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional, Any, Callable
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


@dataclass
class NeuralSignal:
    """A signal on the NeuralBus (backward-compatible)."""
    signal_type: str
    source: str
    payload: dict = field(default_factory=dict)
    timestamp: float = 0.0
    priority: int = 5

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


class NeuralBusCompat:
    """
    Backward-compatible NeuralBus that delegates to the new shared NeuralBus.
    
    Old API: neural_bus.publish(signal_type, source, payload)
    New API: neural_bus.publish(Event(event_type, source, data))
    
    This adapter translates between the two.
    """

    def __init__(self):
        self._new_bus = _get_new_neural_bus()
        self._subscribers: dict[str, list[Callable]] = {}
        self._signal_history: list[NeuralSignal] = []
        self._max_history = 1000
        logger.info("NeuralBusCompat initialized — delegating to shared NeuralBus")

    def publish(
        self,
        signal_type: str,
        source: str = "",
        payload: dict = None,
        priority: int = 5,
    ) -> NeuralSignal:
        """
        Publish a signal (old API compatibility).
        Translates to new Event and publishes on shared NeuralBus.
        """
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

    def subscribe(self, signal_type: str, callback: Callable) -> None:
        """Subscribe to a signal type (old API compatibility)."""
        if signal_type not in self._subscribers:
            self._subscribers[signal_type] = []
        self._subscribers[signal_type].append(callback)

        # Also subscribe on new bus
        try:
            event_type = self._map_signal_to_event(signal_type)
            self._new_bus.subscribe(event_type.value, callback)
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
        }
        return mapping.get(signal_type, _NewEventType.SYSTEM)


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
