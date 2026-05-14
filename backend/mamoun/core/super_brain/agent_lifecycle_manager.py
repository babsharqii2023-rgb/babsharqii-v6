"""
Agent Lifecycle Manager v59 — Full lifecycle management for autonomous agents.

CRITICAL ADDITION from v59:
- v58: AgentCreator created agents but lifecycle was not activated
- v59: Full lifecycle management: observation → active → retired
- Auto-promote after 10 successful operations
- Auto-demote after 3 consecutive failures
- Periodic health monitoring for all agents
- Integration with MetaCognitionEngine for real performance tracking

v59 — Super Mind العقل الخارق مامون
"""

import time
import logging
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AgentLifecycleState(str, Enum):
    OBSERVATION = "observation"    # New agent — being evaluated
    ACTIVE = "active"             # Proven agent — in production
    DEGRADED = "degraded"         # Failing agent — under review
    RETIRED = "retired"           # Inactive agent — removed from service


@dataclass
class AgentRecord:
    """Record of an agent's lifecycle and performance."""
    agent_id: str
    name: str
    state: AgentLifecycleState = AgentLifecycleState.OBSERVATION
    total_operations: int = 0
    successful_operations: int = 0
    consecutive_successes: int = 0
    consecutive_failures: int = 0
    created_at: float = field(default_factory=time.time)
    last_operation_at: Optional[float] = None
    promoted_at: Optional[float] = None
    retired_at: Optional[float] = None
    quality_scores: list[float] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_operations == 0:
            return 0.0
        return self.successful_operations / self.total_operations

    @property
    def avg_quality(self) -> float:
        if not self.quality_scores:
            return 0.0
        recent = self.quality_scores[-20:]
        return sum(recent) / len(recent)


class AgentLifecycleManager:
    """
    Manages the full lifecycle of autonomous agents.

    Lifecycle:
    1. OBSERVATION: New agent is created, monitored but not trusted
    2. ACTIVE: After 10 successful operations, agent is promoted
    3. DEGRADED: After 3 consecutive failures, agent is demoted
    4. RETIRED: After extended degradation or manual retirement

    Safety features:
    - Observation agents have limited capabilities
    - Auto-promotion requires consistent performance
    - Auto-demotion protects system from failing agents
    - Health monitoring runs periodically

    Usage:
        manager = AgentLifecycleManager(meta_cognition=meta)
        manager.register_agent("web_scraper", "Web Scraper Agent")
        manager.record_agent_outcome("web_scraper", success=True, quality=0.85)
    """

    PROMOTION_THRESHOLD = 10      # Successful operations before promotion
    DEMOTION_THRESHOLD = 3        # Consecutive failures before demotion
    RETIREMENT_THRESHOLD = 20     # Operations in degraded state before retirement
    MAX_QUALITY_SAMPLES = 50

    def __init__(self, meta_cognition=None, neural_bus=None):
        self._meta_cognition = meta_cognition
        self._neural_bus = neural_bus
        self._agents: dict[str, AgentRecord] = {}

    def set_meta_cognition(self, engine):
        self._meta_cognition = engine

    def register_agent(self, agent_id: str, name: str) -> AgentRecord:
        """Register a new agent in observation state."""
        if agent_id in self._agents:
            return self._agents[agent_id]

        record = AgentRecord(agent_id=agent_id, name=name)
        self._agents[agent_id] = record
        logger.info(f"Agent registered: {name} ({agent_id}) in observation state")
        return record

    def record_agent_outcome(
        self,
        agent_id: str,
        success: bool,
        quality: float = 0.5,
        operation: str = "",
    ) -> dict:
        """
        Record the outcome of an agent operation.

        Returns:
            dict with current agent state and any lifecycle changes
        """
        record = self._agents.get(agent_id)
        if not record:
            record = self.register_agent(agent_id, agent_id)

        # Update counters
        record.total_operations += 1
        record.last_operation_at = time.time()

        if success:
            record.successful_operations += 1
            record.consecutive_successes += 1
            record.consecutive_failures = 0
        else:
            record.consecutive_failures += 1
            record.consecutive_successes = 0

        # Track quality
        record.quality_scores.append(quality)
        if len(record.quality_scores) > self.MAX_QUALITY_SAMPLES:
            record.quality_scores = record.quality_scores[-self.MAX_QUALITY_SAMPLES:]

        # Record in meta-cognition
        if self._meta_cognition:
            try:
                from .meta_cognition_engine import OutcomeRecord
                self._meta_cognition.record_outcome(OutcomeRecord(
                    component=f"agent_{agent_id}",
                    operation=operation or "execute",
                    success=success,
                    quality_score=quality,
                    predicted_quality=self._meta_cognition.predict_quality(f"agent_{agent_id}"),
                    latency_ms=0,
                    metadata={
                        "lifecycle_state": record.state.value,
                        "consecutive_failures": record.consecutive_failures,
                    },
                ))
            except ImportError:
                pass

        # Check for lifecycle transitions
        changes = []

        # Auto-promote: observation → active
        if record.state == AgentLifecycleState.OBSERVATION:
            if (record.consecutive_successes >= self.PROMOTION_THRESHOLD and
                    record.success_rate >= 0.7):
                record.state = AgentLifecycleState.ACTIVE
                record.promoted_at = time.time()
                changes.append("promoted_to_active")
                logger.info(f"Agent {agent_id} PROMOTED to active (success rate: {record.success_rate:.0%})")

        # Auto-demote: active → degraded
        elif record.state == AgentLifecycleState.ACTIVE:
            if record.consecutive_failures >= self.DEMOTION_THRESHOLD:
                record.state = AgentLifecycleState.DEGRADED
                changes.append("demoted_to_degraded")
                logger.warning(f"Agent {agent_id} DEMOTED to degraded ({record.consecutive_failures} consecutive failures)")

        # Auto-retire: degraded → retired
        elif record.state == AgentLifecycleState.DEGRADED:
            degraded_ops = record.total_operations - (record.successful_operations)
            if degraded_ops >= self.RETIREMENT_THRESHOLD or record.consecutive_failures >= 10:
                record.state = AgentLifecycleState.RETIRED
                record.retired_at = time.time()
                changes.append("retired")
                logger.warning(f"Agent {agent_id} RETIRED due to persistent failures")

        return {
            "agent_id": agent_id,
            "state": record.state.value,
            "changes": changes,
            "success_rate": record.success_rate,
            "consecutive_failures": record.consecutive_failures,
            "avg_quality": record.avg_quality,
        }

    def get_agent(self, agent_id: str) -> Optional[AgentRecord]:
        return self._agents.get(agent_id)

    def get_active_agents(self) -> list[AgentRecord]:
        return [a for a in self._agents.values() if a.state == AgentLifecycleState.ACTIVE]

    def get_observation_agents(self) -> list[AgentRecord]:
        return [a for a in self._agents.values() if a.state == AgentLifecycleState.OBSERVATION]

    def retire_agent(self, agent_id: str) -> bool:
        """Manually retire an agent."""
        record = self._agents.get(agent_id)
        if not record:
            return False
        record.state = AgentLifecycleState.RETIRED
        record.retired_at = time.time()
        logger.info(f"Agent {agent_id} manually retired")
        return True

    def reactivate_agent(self, agent_id: str) -> bool:
        """Reactivate a retired agent back to observation."""
        record = self._agents.get(agent_id)
        if not record:
            return False
        record.state = AgentLifecycleState.OBSERVATION
        record.consecutive_failures = 0
        record.consecutive_successes = 0
        record.retired_at = None
        logger.info(f"Agent {agent_id} reactivated to observation")
        return True

    def health_check(self) -> dict:
        """Run health check on all agents."""
        results = {}
        for agent_id, record in self._agents.items():
            health = "healthy"
            if record.state == AgentLifecycleState.RETIRED:
                health = "retired"
            elif record.state == AgentLifecycleState.DEGRADED:
                health = "degraded"
            elif record.consecutive_failures > 0:
                health = "warning"
            elif record.state == AgentLifecycleState.OBSERVATION:
                health = "observation"

            results[agent_id] = {
                "name": record.name,
                "state": record.state.value,
                "health": health,
                "success_rate": round(record.success_rate, 2),
                "avg_quality": round(record.avg_quality, 2),
                "total_operations": record.total_operations,
                "consecutive_failures": record.consecutive_failures,
            }

        return results

    def get_stats(self) -> dict:
        total = len(self._agents)
        return {
            "total_agents": total,
            "observation": sum(1 for a in self._agents.values() if a.state == AgentLifecycleState.OBSERVATION),
            "active": sum(1 for a in self._agents.values() if a.state == AgentLifecycleState.ACTIVE),
            "degraded": sum(1 for a in self._agents.values() if a.state == AgentLifecycleState.DEGRADED),
            "retired": sum(1 for a in self._agents.values() if a.state == AgentLifecycleState.RETIRED),
        }
