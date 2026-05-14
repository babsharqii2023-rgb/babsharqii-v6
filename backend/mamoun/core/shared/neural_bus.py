"""
Neural Bus — Event-driven communication backbone for Super Mind.
All components publish and subscribe to events through this bus.
No more polling — components react to events in real-time.

v57 — Super Mind العقل الخارق مامون
"""

import asyncio
import logging
import time
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    # Core lifecycle
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    HEARTBEAT = "system.heartbeat"

    # Brain events
    BRAIN_QUERY = "brain.query"
    BRAIN_RESPONSE = "brain.response"
    BRAIN_ERROR = "brain.error"

    # Deliberation events
    DELIBERATION_START = "deliberation.start"
    DELIBERATION_VOTE = "deliberation.vote"
    DELIBERATION_RESULT = "deliberation.result"

    # Meta-cognition events
    META_RECORD_OUTCOME = "meta.record_outcome"
    META_ASSESSMENT = "meta.assessment"
    META_STAGNATION = "meta.stagnation"

    # Self-modification events
    SELF_MODIFY_PROPOSE = "self_modify.propose"
    SELF_MODIFY_VERIFY = "self_modify.verify"
    SELF_MODIFY_APPLY = "self_modify.apply"
    SELF_MODIFY_ROLLBACK = "self_modify.rollback"

    # Research events
    RESEARCH_START = "research.start"
    RESEARCH_RESULT = "research.result"
    RESEARCH_ERROR = "research.error"

    # Tool/Agent events
    TOOL_CREATED = "tool.created"
    TOOL_REGISTERED = "tool.registered"
    AGENT_CREATED = "agent.created"
    AGENT_HEALTH = "agent.health"

    # Healing events
    HEALING_CHECK = "healing.check"
    HEALING_REPAIR = "healing.repair"
    HEALTH_CRITICAL = "health.critical"  # v59.1: Critical health alert


@dataclass
class Event:
    """An event on the Neural Bus."""
    event_type: str
    source: str
    data: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None


class NeuralBus:
    """
    Event bus for inter-component communication.
    Replaces polling with event-driven architecture.

    Usage:
        bus = NeuralBus()
        bus.subscribe("meta.record_outcome", my_handler)
        bus.publish(Event(event_type="meta.record_outcome", source="brain", data={...}))
    """

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._event_log: list[Event] = []
        self._max_log_size = 10000
        self._running = False
        self._stats = {
            "total_published": 0,
            "total_delivered": 0,
            "total_errors": 0,
        }

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe a handler to an event type."""
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed {handler.__name__} to {event_type}")

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]

    async def publish(self, event: Event) -> int:
        """
        Publish an event to all subscribers.
        Returns the number of handlers notified.
        """
        self._stats["total_published"] += 1

        # Log the event
        self._event_log.append(event)
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]

        # Notify subscribers
        handlers = self._subscribers.get(event.event_type, [])
        delivered = 0

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
                delivered += 1
            except Exception as e:
                self._stats["total_errors"] += 1
                logger.error(f"Error in handler {handler.__name__} for {event.event_type}: {e}")

        self._stats["total_delivered"] += delivered
        return delivered

    def publish_sync(self, event: Event) -> int:
        """Publish an event synchronously (for non-async contexts).
        Returns the number of handlers notified.
        """
        self._stats["total_published"] += 1
        self._event_log.append(event)
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]

        handlers = self._subscribers.get(event.event_type, [])
        delivered = 0
        for handler in handlers:
            try:
                if not asyncio.iscoroutinefunction(handler):
                    handler(event)
                    delivered += 1
            except Exception as e:
                self._stats["total_errors"] += 1
                logger.error(f"Error in sync handler: {e}")
        self._stats["total_delivered"] += delivered
        return delivered

    def get_recent_events(self, event_type: str = None, limit: int = 100) -> list[Event]:
        """Get recent events, optionally filtered by type."""
        events = self._event_log
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def get_stats(self) -> dict:
        """Get bus statistics."""
        return {
            **self._stats,
            "subscriber_count": sum(len(h) for h in self._subscribers.values()),
            "event_types_with_subscribers": list(self._subscribers.keys()),
            "log_size": len(self._event_log),
        }


# Global singleton
_neural_bus: Optional[NeuralBus] = None


def get_neural_bus() -> NeuralBus:
    """Get the global NeuralBus instance."""
    global _neural_bus
    if _neural_bus is None:
        _neural_bus = NeuralBus()
    return _neural_bus
