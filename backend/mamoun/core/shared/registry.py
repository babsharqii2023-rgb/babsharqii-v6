"""
Shared Types and Registry — Central tool/agent registration.
Every tool and agent created is registered here with real metadata.

v57 — Super Mind العقل الخارق مامون
"""

import time
import logging
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ComponentStatus(str, Enum):
    ACTIVE = "active"
    OBSERVING = "observing"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class ToolEntry:
    """Registration entry for a tool."""
    name: str
    description: str
    handler: Optional[Callable] = None
    created_at: float = field(default_factory=time.time)
    last_used: Optional[float] = None
    use_count: int = 0
    success_count: int = 0
    error_count: int = 0
    status: ComponentStatus = ComponentStatus.ACTIVE
    test_passed: bool = False
    source: str = ""  # "manual", "llm_generated", "discovered"
    schema: dict = field(default_factory=dict)  # Input/output schema


@dataclass
class AgentEntry:
    """Registration entry for an agent."""
    name: str
    description: str
    handler: Optional[Callable] = None
    created_at: float = field(default_factory=time.time)
    last_active: Optional[float] = None
    call_count: int = 0
    success_count: int = 0
    error_count: int = 0
    status: ComponentStatus = ComponentStatus.OBSERVING  # New agents start observing
    mode: str = "observation"  # "observation", "active", "suspended"
    health_score: float = 0.0
    parent_component: str = ""
    capabilities: list = field(default_factory=list)


class ToolRegistry:
    """Central registry for all tools."""

    def __init__(self):
        self._tools: dict[str, ToolEntry] = {}

    def register(self, entry: ToolEntry) -> bool:
        """Register a tool. Returns False if already registered."""
        if entry.name in self._tools:
            logger.warning(f"Tool '{entry.name}' already registered, updating...")
        self._tools[entry.name] = entry
        logger.info(f"Registered tool: {entry.name}")
        return True

    def unregister(self, name: str) -> bool:
        """Unregister a tool."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Optional[ToolEntry]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self, status: ComponentStatus = None) -> list[ToolEntry]:
        """List all tools, optionally filtered by status."""
        tools = list(self._tools.values())
        if status:
            tools = [t for t in tools if t.status == status]
        return tools

    def record_usage(self, name: str, success: bool) -> None:
        """Record tool usage."""
        tool = self._tools.get(name)
        if tool:
            tool.use_count += 1
            tool.last_used = time.time()
            if success:
                tool.success_count += 1
            else:
                tool.error_count += 1
                if tool.error_count > 5 and tool.success_count == 0:
                    tool.status = ComponentStatus.ERROR

    def search(self, query: str) -> list[ToolEntry]:
        """Search tools by name or description."""
        query_lower = query.lower()
        results = []
        for tool in self._tools.values():
            if query_lower in tool.name.lower() or query_lower in tool.description.lower():
                results.append(tool)
        return results


class AgentRegistry:
    """Central registry for all agents."""

    def __init__(self):
        self._agents: dict[str, AgentEntry] = {}

    def register(self, entry: AgentEntry) -> bool:
        """Register an agent."""
        if entry.name in self._agents:
            logger.warning(f"Agent '{entry.name}' already registered, updating...")
        self._agents[entry.name] = entry
        logger.info(f"Registered agent: {entry.name} (mode: {entry.mode})")
        return True

    def unregister(self, name: str) -> bool:
        """Unregister an agent."""
        if name in self._agents:
            del self._agents[name]
            return True
        return False

    def get(self, name: str) -> Optional[AgentEntry]:
        """Get an agent by name."""
        return self._agents.get(name)

    def list_agents(self, status: ComponentStatus = None, mode: str = None) -> list[AgentEntry]:
        """List agents, optionally filtered."""
        agents = list(self._agents.values())
        if status:
            agents = [a for a in agents if a.status == status]
        if mode:
            agents = [a for a in agents if a.mode == mode]
        return agents

    def promote(self, name: str) -> bool:
        """Promote agent from observation to active mode."""
        agent = self._agents.get(name)
        if not agent:
            return False
        if agent.mode == "observation" and agent.success_count >= 10:
            agent.mode = "active"
            agent.status = ComponentStatus.ACTIVE
            logger.info(f"Promoted agent '{name}' to active mode")
            return True
        return False

    def demote(self, name: str) -> bool:
        """Demote agent back to observation mode."""
        agent = self._agents.get(name)
        if not agent:
            return False
        agent.mode = "observation"
        agent.status = ComponentStatus.OBSERVING
        logger.warning(f"Demoted agent '{name}' to observation mode")
        return True

    def record_outcome(self, name: str, success: bool) -> None:
        """Record agent call outcome."""
        agent = self._agents.get(name)
        if agent:
            agent.call_count += 1
            agent.last_active = time.time()
            if success:
                agent.success_count += 1
                # Auto-promote if eligible
                if agent.mode == "observation" and agent.success_count >= 10:
                    self.promote(name)
            else:
                agent.error_count += 1
                # Auto-demote if too many errors
                if agent.error_count > 3 and agent.mode == "active":
                    self.demote(name)

            # Update health score
            total = agent.success_count + agent.error_count
            if total > 0:
                agent.health_score = agent.success_count / total


# Global registries
_tool_registry: Optional[ToolRegistry] = None
_agent_registry: Optional[AgentRegistry] = None


def get_tool_registry() -> ToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry


def get_agent_registry() -> AgentRegistry:
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = AgentRegistry()
    return _agent_registry
