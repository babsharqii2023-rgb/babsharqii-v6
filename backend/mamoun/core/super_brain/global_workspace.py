"""
GlobalWorkspace v61 — Unified Global Workspace for SuperBrain

Merges the old GlobalWorkspace from mamoun_kernel.py into the super_brain system.
The Global Workspace Theory (Baars) implements a "theater of consciousness" where
multiple specialized modules compete for access to a shared workspace.

This module:
1. Receives inputs from all 5 brains and the NeuralBus
2. Runs a competition/coalescence cycle to determine the "winner"
3. Broadcasts the winning coalition to all modules
4. Integrates with MetaCognitionEngine for self-monitoring
5. Bridges with the NeuralBus for system-wide signal distribution

v61 — Super Brain العقل الخارق مامون
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger("mamoun.super_brain.global_workspace")


@dataclass
class WorkspaceCoalition:
    """A coalition of brain outputs competing for workspace access."""
    source: str  # brain_id or module name
    content: Any
    confidence: float
    weight: float = 1.0
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    @property
    def score(self) -> float:
        """Competition score = confidence * weight."""
        return self.confidence * self.weight


class GlobalWorkspace:
    """
    Global Workspace — مساحة العمل العالمية

    Implements Baars' Global Workspace Theory where specialized brain modules
    compete for access to a shared conscious workspace. The winner is broadcast
    to all modules, enabling integrated cognition.

    This replaces the old GlobalWorkspace in mamoun_kernel.py and adds:
    - Integration with MetaCognitionEngine
    - NeuralBus broadcasting
    - Coalition formation (multiple brains can form a coalition)
    - Attention modulation based on context
    """

    def __init__(self, neural_bus=None, meta_cognition=None):
        self._neural_bus = neural_bus
        self._meta_cognition = meta_cognition
        self._coalitions: list[WorkspaceCoalition] = []
        self._current_winner: Optional[WorkspaceCoalition] = None
        self._broadcast_history: list[dict] = []
        self._listeners: list[Callable] = []
        self._attention_weight: dict[str, float] = {
            "neural": 1.0,
            "causal": 1.0,
            "symbolic": 1.0,
            "bayesian": 1.0,
            "world_model": 1.0,
        }
        self._cycle_count = 0
        self._last_broadcast_time: Optional[float] = None
        logger.info("GlobalWorkspace initialized")

    def set_neural_bus(self, bus):
        """Set the NeuralBus instance."""
        self._neural_bus = bus

    def set_meta_cognition(self, engine):
        """Set the MetaCognitionEngine instance."""
        self._meta_cognition = engine

    def submit(self, source: str, content: Any, confidence: float,
               weight: float = 1.0, metadata: Optional[dict] = None):
        """
        Submit a coalition to the workspace competition.

        Args:
            source: The brain or module that produced this content
            content: The actual content (text, dict, etc.)
            confidence: Confidence score (0-1)
            weight: Attention weight modifier
            metadata: Additional metadata
        """
        # Apply attention modulation
        attention_mod = self._attention_weight.get(source, 1.0)
        effective_weight = weight * attention_mod

        coalition = WorkspaceCoalition(
            source=source,
            content=content,
            confidence=confidence,
            weight=effective_weight,
            metadata=metadata or {},
        )
        self._coalitions.append(coalition)
        logger.debug(f"Workspace: coalition submitted from {source} "
                     f"(confidence={confidence:.2f}, weight={effective_weight:.2f})")

    def compete_and_broadcast(self) -> Optional[WorkspaceCoalition]:
        """
        Run the competition cycle: select the winning coalition and broadcast it.

        Competition rules:
        1. Highest score (confidence * weight) wins
        2. If tie, most recent coalition wins
        3. Winner is broadcast to all listeners and NeuralBus
        4. MetaCognition is notified for self-monitoring

        Returns:
            The winning coalition, or None if no coalitions submitted
        """
        if not self._coalitions:
            return None

        self._cycle_count += 1

        # Sort by score (descending), then by timestamp (most recent first)
        sorted_coalitions = sorted(
            self._coalitions,
            key=lambda c: (c.score, c.timestamp),
            reverse=True,
        )

        winner = sorted_coalitions[0]
        self._current_winner = winner

        # Record broadcast
        broadcast_record = {
            "cycle": self._cycle_count,
            "winner_source": winner.source,
            "winner_confidence": winner.confidence,
            "winner_score": winner.score,
            "num_competitors": len(self._coalitions),
            "timestamp": time.time(),
        }
        self._broadcast_history.append(broadcast_record)
        if len(self._broadcast_history) > 100:
            self._broadcast_history = self._broadcast_history[-50:]

        self._last_broadcast_time = time.time()

        # Broadcast to NeuralBus
        if self._neural_bus:
            try:
                self._neural_bus.publish(
                    signal_type="global_broadcast",
                    source=f"global_workspace:{winner.source}",
                    payload={
                        "content": winner.content,
                        "confidence": winner.confidence,
                        "score": winner.score,
                        "cycle": self._cycle_count,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast to NeuralBus: {e}")

        # Notify MetaCognition
        if self._meta_cognition:
            try:
                self._meta_cognition.record_outcome(
                    action=f"workspace_cycle_{self._cycle_count}",
                    outcome="success" if winner.confidence > 0.5 else "low_confidence",
                    confidence=winner.confidence,
                    metadata=broadcast_record,
                )
            except Exception as e:
                logger.warning(f"Failed to notify MetaCognition: {e}")

        # Notify listeners
        for listener in self._listeners:
            try:
                listener(winner)
            except Exception as e:
                logger.warning(f"Listener notification failed: {e}")

        # Clear coalitions for next cycle
        self._coalitions = []

        logger.info(f"Workspace cycle #{self._cycle_count}: winner={winner.source} "
                    f"score={winner.score:.3f} confidence={winner.confidence:.3f}")

        return winner

    def set_attention_weight(self, source: str, weight: float):
        """Modulate attention for a specific brain/source."""
        self._attention_weight[source] = max(0.0, min(2.0, weight))

    def add_listener(self, callback: Callable):
        """Add a callback to be notified on each broadcast."""
        self._listeners.append(callback)

    def get_stats(self) -> dict:
        """Get workspace statistics."""
        return {
            "cycle_count": self._cycle_count,
            "current_winner": self._current_winner.source if self._current_winner else None,
            "pending_coalitions": len(self._coalitions),
            "total_broadcasts": len(self._broadcast_history),
            "last_broadcast_time": self._last_broadcast_time,
            "attention_weights": dict(self._attention_weight),
        }

    def get_history(self, limit: int = 20) -> list[dict]:
        """Get recent broadcast history."""
        return self._broadcast_history[-limit:]


# Singleton instance
_global_workspace: Optional[GlobalWorkspace] = None


def get_global_workspace() -> GlobalWorkspace:
    """Get or create the GlobalWorkspace singleton."""
    global _global_workspace
    if _global_workspace is None:
        _global_workspace = GlobalWorkspace()
    return _global_workspace
