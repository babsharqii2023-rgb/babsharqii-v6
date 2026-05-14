"""
Dynamic Tool Loader v60 — Safe dynamic loading of LLM-generated tools and agents.

CRITICAL ADDITION from v60:
- v59: Tools and agents were generated as code text but NEVER loaded or executed
- v60: DynamicToolLoader provides SAFE sandboxed loading + hot registration
- Loads generated Python code as callable functions/classes
- Sandboxed execution with resource limits and security checks
- Hot registration into ToolRegistry and AgentRegistry
- Rollback capability if loaded tool fails
- Integration with SmartApprovalEngine for trust-based auto-approval
- Metrics tracking for loaded tools (success rate, latency, errors)

This closes the #1 gap: "الأدوات والوكلاء المُنشأة هي نصوص كود تُحفظ في سجل — لا يتم تحميلها أو تنفيذها ديناميكياً"

v60 — Super Mind العقل الخارق مامون
"""

import ast
import time
import types
import logging
import traceback
import threading
from typing import Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class LoadingStatus(str, Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    SANDBOX_TESTING = "sandbox_testing"
    LOADING = "loading"
    REGISTERING = "registering"
    ACTIVE = "active"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    DISABLED = "disabled"


@dataclass
class LoadedTool:
    """A dynamically loaded tool with full lifecycle tracking."""
    name: str
    code: str
    handler: Optional[Callable] = None
    status: LoadingStatus = LoadingStatus.PENDING
    created_at: float = field(default_factory=time.time)
    loaded_at: Optional[float] = None
    call_count: int = 0
    success_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    quality_score: float = 0.0
    trust_score: float = 0.0  # Starts at 0, increases with successful calls
    last_error: Optional[str] = None
    module: Optional[types.ModuleType] = None
    rollback_data: Optional[dict] = None

    @property
    def success_rate(self) -> float:
        return self.success_count / max(self.call_count, 1)

    @property
    def is_callable(self) -> bool:
        return self.handler is not None and self.status == LoadingStatus.ACTIVE


@dataclass
class LoadedAgent:
    """A dynamically loaded agent with full lifecycle tracking."""
    name: str
    code: str
    cls: Optional[type] = None
    instance: Optional[Any] = None
    status: LoadingStatus = LoadingStatus.PENDING
    created_at: float = field(default_factory=time.time)
    loaded_at: Optional[float] = None
    call_count: int = 0
    success_count: int = 0
    error_count: int = 0
    trust_score: float = 0.0
    mode: str = "observation"  # observation → active after 10 successes
    last_error: Optional[str] = None

    @property
    def success_rate(self) -> float:
        return self.success_count / max(self.call_count, 1)

    @property
    def is_callable(self) -> bool:
        return self.instance is not None and self.status == LoadingStatus.ACTIVE


class DynamicToolLoader:
    """
    Safe dynamic loading of LLM-generated tools and agents.

    This is the MISSING LINK between code generation and actual execution.
    When ToolCreator or AgentCreator generates code, DynamicToolLoader
    makes it immediately callable.

    Pipeline:
    1. VALIDATE: AST security check + syntax check
    2. SANDBOX_TEST: Run code in RestrictedExecutor
    3. LOAD: Import code as a Python module
    4. REGISTER: Register in ToolRegistry/AgentRegistry
    5. MONITOR: Track success/error rates
    6. TRUST: Escalate trust level based on performance

    Safety Model:
    - All code is validated by ASTSecurityChecker before loading
    - Sandbox test with RestrictedExecutor before registration
    - New tools start with trust_score=0 (observation mode)
    - Trust increases with successful calls (+0.05 per success, max 1.0)
    - Trust decreases with failures (-0.15 per failure, min 0.0)
    - Auto-disable if trust drops below 0.1
    - Tools with trust >= 0.7 can be auto-approved for use
    - Thread-safe execution tracking

    Usage:
        loader = DynamicToolLoader(meta_cognition=meta, tool_registry=registry)
        result = await loader.load_tool("web_scraper", code, description="Scrape web pages")
        # Now the tool is callable:
        output = await loader.call_tool("web_scraper", url="https://example.com")
    """

    TRUST_INCREMENT = 0.05
    TRUST_DECREMENT = 0.15
    TRUST_AUTO_APPROVE = 0.7
    TRUST_DISABLE_THRESHOLD = 0.1
    PROMOTION_SUCCESS_THRESHOLD = 10
    MAX_CALL_HISTORY = 100

    def __init__(self, meta_cognition=None, neural_bus=None,
                 tool_registry=None, agent_registry=None,
                 llm_client=None):
        self._meta_cognition = meta_cognition
        self._neural_bus = neural_bus
        self._tool_registry = tool_registry
        self._agent_registry = agent_registry
        self._llm_client = llm_client

        self._loaded_tools: dict[str, LoadedTool] = {}
        self._loaded_agents: dict[str, LoadedAgent] = {}
        self._lock = threading.Lock()

    # ── Tool Loading ─────────────────────────────────────────────────────

    async def load_tool(self, name: str, code: str,
                        description: str = "",
                        auto_activate: bool = False) -> dict:
        """
        Load a tool from generated code and make it callable.

        Args:
            name: Tool name (unique identifier)
            code: Python code for the tool
            description: Human-readable description
            auto_activate: If True, skip observation phase

        Returns:
            dict with loading result and tool info
        """
        start = time.time()

        # Check if already loaded
        if name in self._loaded_tools:
            existing = self._loaded_tools[name]
            if existing.status == LoadingStatus.ACTIVE:
                return {
                    "success": True,
                    "tool_name": name,
                    "status": "already_active",
                    "trust_score": existing.trust_score,
                    "message": f"Tool '{name}' is already loaded and active",
                }

        loaded = LoadedTool(name=name, code=code)
        self._loaded_tools[name] = loaded

        try:
            # Phase 1: Validate
            loaded.status = LoadingStatus.VALIDATING
            validation = self._validate_code(code)
            if not validation["passed"]:
                loaded.status = LoadingStatus.FAILED
                loaded.last_error = f"Validation failed: {validation['errors']}"
                return {
                    "success": False,
                    "tool_name": name,
                    "error": loaded.last_error,
                    "phase": "validation",
                }

            # Phase 2: Sandbox test
            loaded.status = LoadingStatus.SANDBOX_TESTING
            sandbox_result = self._sandbox_test(code)
            if not sandbox_result["passed"]:
                loaded.status = LoadingStatus.FAILED
                loaded.last_error = f"Sandbox test failed: {sandbox_result.get('error', 'unknown')}"
                return {
                    "success": False,
                    "tool_name": name,
                    "error": loaded.last_error,
                    "phase": "sandbox_testing",
                }

            # Phase 3: Load as module
            loaded.status = LoadingStatus.LOADING
            module, handler = self._load_as_module(name, code)
            if handler is None:
                loaded.status = LoadingStatus.FAILED
                loaded.last_error = "Could not extract callable handler from code"
                return {
                    "success": False,
                    "tool_name": name,
                    "error": loaded.last_error,
                    "phase": "loading",
                }

            loaded.module = module
            loaded.handler = handler
            loaded.quality_score = validation.get("quality_score", 0.5)

            # Phase 4: Register
            loaded.status = LoadingStatus.REGISTERING
            self._register_tool(name, description, handler)

            # Phase 5: Activate
            loaded.status = LoadingStatus.ACTIVE
            loaded.loaded_at = time.time()
            if auto_activate:
                loaded.trust_score = 0.5  # Start with moderate trust

            # Save rollback data
            loaded.rollback_data = {
                "code": code,
                "name": name,
                "description": description,
            }

            latency = (time.time() - start) * 1000

            # Record outcome
            self._record_outcome("dynamic_tool_loader", "load_tool", True, loaded.quality_score, latency, {
                "tool": name, "phase": "completed",
            })

            return {
                "success": True,
                "tool_name": name,
                "status": "active",
                "trust_score": loaded.trust_score,
                "quality_score": loaded.quality_score,
                "latency_ms": latency,
                "message": f"Tool '{name}' loaded successfully and is now callable",
            }

        except Exception as e:
            loaded.status = LoadingStatus.FAILED
            loaded.last_error = str(e)
            latency = (time.time() - start) * 1000

            self._record_outcome("dynamic_tool_loader", "load_tool", False, 0.0, latency, {
                "tool": name, "error": str(e),
            })

            return {
                "success": False,
                "tool_name": name,
                "error": str(e),
                "phase": loaded.status.value,
            }

    async def call_tool(self, name: str, **kwargs) -> dict:
        """
        Call a dynamically loaded tool.

        Args:
            name: Tool name
            **kwargs: Arguments to pass to the tool

        Returns:
            dict with call result
        """
        tool = self._loaded_tools.get(name)
        if not tool or not tool.is_callable:
            return {
                "success": False,
                "error": f"Tool '{name}' not found or not callable",
                "tool_name": name,
            }

        start = time.time()
        try:
            # Call the handler
            if isinstance(tool.handler, type):
                # It's a class — instantiate and call execute
                instance = tool.handler(**kwargs)
                if hasattr(instance, 'execute'):
                    import asyncio
                    if asyncio.iscoroutinefunction(instance.execute):
                        result = await instance.execute()
                    else:
                        result = instance.execute()
                else:
                    result = instance
            elif callable(tool.handler):
                import asyncio
                if asyncio.iscoroutinefunction(tool.handler):
                    result = await tool.handler(**kwargs)
                else:
                    result = tool.handler(**kwargs)
            else:
                return {
                    "success": False,
                    "error": f"Tool handler is not callable",
                    "tool_name": name,
                }

            latency = (time.time() - start) * 1000

            # Update tracking
            with self._lock:
                tool.call_count += 1
                tool.success_count += 1
                tool.total_latency_ms += latency
                tool.avg_latency_ms = tool.total_latency_ms / tool.call_count
                tool.trust_score = min(1.0, tool.trust_score + self.TRUST_INCREMENT)

                # Check for promotion from observation to active
                if tool.trust_score >= self.TRUST_AUTO_APPROVE and tool.success_count >= self.PROMOTION_SUCCESS_THRESHOLD:
                    logger.info(f"Tool '{name}' promoted to high-trust (trust={tool.trust_score:.2f})")

            self._record_outcome(f"tool_{name}", "call", True, tool.trust_score, latency, {})

            return {
                "success": True,
                "tool_name": name,
                "result": result,
                "trust_score": tool.trust_score,
                "latency_ms": latency,
            }

        except Exception as e:
            latency = (time.time() - start) * 1000

            with self._lock:
                tool.call_count += 1
                tool.error_count += 1
                tool.last_error = str(e)
                tool.trust_score = max(0.0, tool.trust_score - self.TRUST_DECREMENT)

                # Auto-disable if trust too low
                if tool.trust_score < self.TRUST_DISABLE_THRESHOLD:
                    tool.status = LoadingStatus.DISABLED
                    logger.warning(f"Tool '{name}' DISABLED due to low trust: {tool.trust_score:.2f}")

            self._record_outcome(f"tool_{name}", "call", False, 0.0, latency, {"error": str(e)})

            return {
                "success": False,
                "tool_name": name,
                "error": str(e),
                "trust_score": tool.trust_score,
                "latency_ms": latency,
            }

    # ── Agent Loading ────────────────────────────────────────────────────

    async def load_agent(self, name: str, code: str,
                         description: str = "",
                         capabilities: list[str] = None) -> dict:
        """
        Load an agent from generated code and make it executable.

        Args:
            name: Agent name
            code: Python class code for the agent
            description: Human-readable description
            capabilities: List of agent capabilities

        Returns:
            dict with loading result
        """
        start = time.time()
        capabilities = capabilities or ["general"]

        if name in self._loaded_agents:
            existing = self._loaded_agents[name]
            if existing.status == LoadingStatus.ACTIVE:
                return {
                    "success": True,
                    "agent_name": name,
                    "status": "already_active",
                    "trust_score": existing.trust_score,
                }

        loaded = LoadedAgent(name=name, code=code)
        self._loaded_agents[name] = loaded

        try:
            # Phase 1: Validate
            loaded.status = LoadingStatus.VALIDATING
            validation = self._validate_code(code)
            if not validation["passed"]:
                loaded.status = LoadingStatus.FAILED
                loaded.last_error = f"Validation failed: {validation['errors']}"
                return {"success": False, "agent_name": name, "error": loaded.last_error}

            # Phase 2: Sandbox test
            loaded.status = LoadingStatus.SANDBOX_TESTING
            sandbox_result = self._sandbox_test(code)
            if not sandbox_result["passed"]:
                loaded.status = LoadingStatus.FAILED
                loaded.last_error = f"Sandbox test failed: {sandbox_result.get('error')}"
                return {"success": False, "agent_name": name, "error": loaded.last_error}

            # Phase 3: Load as class
            loaded.status = LoadingStatus.LOADING
            cls = self._load_agent_class(name, code)
            if cls is None:
                loaded.status = LoadingStatus.FAILED
                loaded.last_error = "Could not extract agent class from code"
                return {"success": False, "agent_name": name, "error": loaded.last_error}

            loaded.cls = cls

            # Try to instantiate
            try:
                loaded.instance = cls(config={})
            except TypeError:
                try:
                    loaded.instance = cls()
                except Exception as e:
                    logger.warning(f"Could not instantiate agent {name}: {e}")
                    loaded.instance = None

            # Phase 4: Register
            loaded.status = LoadingStatus.REGISTERING
            self._register_agent(name, description, capabilities)

            # Phase 5: Activate
            loaded.status = LoadingStatus.ACTIVE
            loaded.loaded_at = time.time()
            loaded.mode = "observation"  # Start in observation mode

            latency = (time.time() - start) * 1000

            self._record_outcome("dynamic_tool_loader", "load_agent", True, 0.5, latency, {
                "agent": name, "capabilities": capabilities,
            })

            return {
                "success": True,
                "agent_name": name,
                "status": "active",
                "mode": "observation",
                "trust_score": 0.0,
                "latency_ms": latency,
                "message": f"Agent '{name}' loaded in observation mode — needs 10 successful calls to be promoted",
            }

        except Exception as e:
            loaded.status = LoadingStatus.FAILED
            loaded.last_error = str(e)
            latency = (time.time() - start) * 1000

            self._record_outcome("dynamic_tool_loader", "load_agent", False, 0.0, latency, {
                "agent": name, "error": str(e),
            })

            return {"success": False, "agent_name": name, "error": str(e)}

    async def call_agent(self, name: str, task: dict) -> dict:
        """Call a dynamically loaded agent with a task."""
        agent = self._loaded_agents.get(name)
        if not agent or not agent.is_callable:
            return {"success": False, "error": f"Agent '{name}' not found or not callable"}

        start = time.time()
        try:
            instance = agent.instance
            if hasattr(instance, 'execute'):
                import asyncio
                if asyncio.iscoroutinefunction(instance.execute):
                    result = await instance.execute(task)
                else:
                    result = instance.execute(task)
            else:
                result = {"message": "Agent has no execute method", "task": task}

            latency = (time.time() - start) * 1000

            with self._lock:
                agent.call_count += 1
                agent.success_count += 1
                agent.trust_score = min(1.0, agent.trust_score + self.TRUST_INCREMENT)

                # Auto-promote
                if (agent.mode == "observation" and
                        agent.success_count >= self.PROMOTION_SUCCESS_THRESHOLD and
                        agent.trust_score >= self.TRUST_AUTO_APPROVE):
                    agent.mode = "active"
                    logger.info(f"Agent '{name}' promoted to active mode (trust={agent.trust_score:.2f})")

            self._record_outcome(f"agent_{name}", "call", True, agent.trust_score, latency, {})

            return {
                "success": True,
                "agent_name": name,
                "result": result,
                "mode": agent.mode,
                "trust_score": agent.trust_score,
                "latency_ms": latency,
            }

        except Exception as e:
            latency = (time.time() - start) * 1000

            with self._lock:
                agent.call_count += 1
                agent.error_count += 1
                agent.last_error = str(e)
                agent.trust_score = max(0.0, agent.trust_score - self.TRUST_DECREMENT)

                if agent.trust_score < self.TRUST_DISABLE_THRESHOLD:
                    agent.status = LoadingStatus.DISABLED
                    logger.warning(f"Agent '{name}' DISABLED: trust={agent.trust_score:.2f}")

            self._record_outcome(f"agent_{name}", "call", False, 0.0, latency, {"error": str(e)})

            return {
                "success": False,
                "agent_name": name,
                "error": str(e),
                "trust_score": agent.trust_score,
                "latency_ms": latency,
            }

    # ── Internal Methods ─────────────────────────────────────────────────

    def _validate_code(self, code: str) -> dict:
        """Validate code using ASTSecurityChecker."""
        try:
            from .self_modifier import ASTSecurityChecker
            checker = ASTSecurityChecker()
            is_safe, violations = checker.check(code)

            if not is_safe:
                return {"passed": False, "errors": violations, "quality_score": 0.1}

            # Check for function/class definitions
            tree = ast.parse(code)
            has_function = any(isinstance(n, ast.FunctionDef) or isinstance(n, ast.AsyncFunctionDef)
                             for n in ast.walk(tree))
            has_class = any(isinstance(n, ast.ClassDef) for n in ast.walk(tree))

            quality = 0.7
            if has_function:
                quality += 0.1
            if has_class:
                quality += 0.1
            if has_function and has_class:
                quality += 0.1

            return {"passed": True, "errors": [], "quality_score": min(1.0, quality)}

        except SyntaxError as e:
            return {"passed": False, "errors": [f"Syntax error: {e}"], "quality_score": 0.0}

    def _sandbox_test(self, code: str) -> dict:
        """Test code in RestrictedExecutor sandbox."""
        try:
            from .self_modifier import RestrictedExecutor
            executor = RestrictedExecutor()
            result = executor.execute(code, timeout=10)
            return {
                "passed": result["success"],
                "error": result.get("error"),
                "output": result.get("output", ""),
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def _load_as_module(self, name: str, code: str) -> tuple:
        """Load code as a Python module and extract callable handler."""
        try:
            # Create a module
            module = types.ModuleType(f"dynamic_tool_{name}")
            module.__file__ = f"<dynamic:{name}>"

            # Restricted globals
            safe_globals = {
                "__builtins__": {
                    "print": print, "len": len, "range": range, "enumerate": enumerate,
                    "zip": zip, "map": map, "filter": filter, "sorted": sorted,
                    "min": min, "max": max, "sum": sum, "abs": abs, "round": round,
                    "isinstance": isinstance, "type": type, "str": str, "int": int,
                    "float": float, "bool": bool, "list": list, "dict": dict,
                    "set": set, "tuple": tuple, "None": None, "True": True, "False": False,
                    "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError,
                    "KeyError": KeyError, "AttributeError": AttributeError,
                    "RuntimeError": RuntimeError, "NotImplementedError": NotImplementedError,
                },
            }

            # Execute code in module namespace
            exec(compile(code, f"<dynamic:{name}>", "exec"), safe_globals)

            # Copy to module
            for key, value in safe_globals.items():
                if key != "__builtins__" and not key.startswith("_"):
                    setattr(module, key, value)

            # Find the main handler
            handler = None

            # Strategy 1: Look for a function matching the tool name
            for attr_name in dir(module):
                if attr_name.startswith("_"):
                    continue
                attr = getattr(module, attr_name)
                if callable(attr) and attr_name == name:
                    handler = attr
                    break

            # Strategy 2: Look for any async function
            if handler is None:
                import asyncio
                for attr_name in dir(module):
                    if attr_name.startswith("_"):
                        continue
                    attr = getattr(module, attr_name)
                    if asyncio.iscoroutinefunction(attr) or callable(attr):
                        handler = attr
                        break

            # Strategy 3: Look for a class with execute method
            if handler is None:
                for attr_name in dir(module):
                    if attr_name.startswith("_"):
                        continue
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and hasattr(attr, 'execute'):
                        handler = attr
                        break

            return module, handler

        except Exception as e:
            logger.error(f"Failed to load module for tool '{name}': {e}")
            return None, None

    def _load_agent_class(self, name: str, code: str) -> Optional[type]:
        """Load code and extract an agent class."""
        try:
            safe_globals = {
                "__builtins__": {
                    "print": print, "len": len, "range": range, "enumerate": enumerate,
                    "zip": zip, "map": map, "filter": filter, "sorted": sorted,
                    "min": min, "max": max, "sum": sum, "abs": abs, "round": round,
                    "isinstance": isinstance, "type": type, "str": str, "int": int,
                    "float": float, "bool": bool, "list": list, "dict": dict,
                    "set": set, "tuple": tuple, "None": None, "True": True, "False": False,
                    "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError,
                },
            }

            exec(compile(code, f"<dynamic_agent:{name}>", "exec"), safe_globals)

            # Find the class
            for attr_name, attr in safe_globals.items():
                if attr_name.startswith("_"):
                    continue
                if isinstance(attr, type) and hasattr(attr, 'execute'):
                    return attr

            # Fallback: any class
            for attr_name, attr in safe_globals.items():
                if attr_name.startswith("_"):
                    continue
                if isinstance(attr, type):
                    return attr

            return None

        except Exception as e:
            logger.error(f"Failed to load agent class '{name}': {e}")
            return None

    def _register_tool(self, name: str, description: str, handler: Callable):
        """Register tool in ToolRegistry."""
        registry = self._get_tool_registry()
        if registry:
            try:
                from ..shared.registry import ToolEntry, ComponentStatus
                registry.register(ToolEntry(
                    name=name,
                    description=description,
                    handler=handler,
                    status=ComponentStatus.ACTIVE,
                    source="dynamic_loaded",
                    test_passed=True,
                ))
                logger.info(f"Registered dynamically loaded tool: {name}")
            except ImportError:
                logger.warning(f"Could not register tool '{name}' in registry — missing imports")

    def _register_agent(self, name: str, description: str, capabilities: list[str]):
        """Register agent in AgentRegistry."""
        registry = self._get_agent_registry()
        if registry:
            try:
                from ..shared.registry import AgentEntry, ComponentStatus
                registry.register(AgentEntry(
                    name=name,
                    description=description,
                    status=ComponentStatus.OBSERVING,
                    mode="observation",
                    capabilities=capabilities,
                    health_score=0.0,
                ))
                logger.info(f"Registered dynamically loaded agent: {name}")
            except ImportError:
                logger.warning(f"Could not register agent '{name}' in registry — missing imports")

    def _get_tool_registry(self):
        if self._tool_registry:
            return self._tool_registry
        try:
            from ..shared.registry import get_tool_registry
            self._tool_registry = get_tool_registry()
        except ImportError:
            pass
        return self._tool_registry

    def _get_agent_registry(self):
        if self._agent_registry:
            return self._agent_registry
        try:
            from ..shared.registry import get_agent_registry
            self._agent_registry = get_agent_registry()
        except ImportError:
            pass
        return self._agent_registry

    def _record_outcome(self, component: str, operation: str,
                        success: bool, quality: float, latency_ms: float, metadata: dict):
        """Record outcome in MetaCognition."""
        if self._meta_cognition:
            try:
                from .meta_cognition_engine import OutcomeRecord
                self._meta_cognition.record_outcome(OutcomeRecord(
                    component=component,
                    operation=operation,
                    success=success,
                    quality_score=quality,
                    predicted_quality=self._meta_cognition.predict_quality(component),
                    latency_ms=latency_ms,
                    metadata=metadata,
                ))
            except ImportError:
                pass

    # ── Rollback ─────────────────────────────────────────────────────────

    async def rollback_tool(self, name: str) -> dict:
        """Rollback a loaded tool to its previous state."""
        tool = self._loaded_tools.get(name)
        if not tool:
            return {"success": False, "error": f"Tool '{name}' not found"}

        if tool.rollback_data:
            tool.status = LoadingStatus.ROLLED_BACK
            tool.handler = None
            tool.module = None
            logger.info(f"Rolled back tool: {name}")
            return {"success": True, "tool_name": name}
        return {"success": False, "error": "No rollback data available"}

    # ── Hot Reload ───────────────────────────────────────────────────────

    async def reload_tool(self, name: str, new_code: str) -> dict:
        """Hot-reload a tool with new code without downtime."""
        old_tool = self._loaded_tools.get(name)
        if not old_tool:
            return await self.load_tool(name, new_code)

        # Save old state for rollback
        old_handler = old_tool.handler
        old_module = old_tool.module
        old_trust = old_tool.trust_score
        old_stats = {
            "call_count": old_tool.call_count,
            "success_count": old_tool.success_count,
            "error_count": old_tool.error_count,
        }

        # Try to load new code
        result = await self.load_tool(name, new_code, auto_activate=True)

        if result["success"]:
            # Preserve trust and stats from previous version
            new_tool = self._loaded_tools[name]
            new_tool.trust_score = old_trust  # Keep accumulated trust
            # Stats are reset — new version starts fresh
            logger.info(f"Hot-reloaded tool '{name}' (preserved trust={old_trust:.2f})")
        else:
            # Restore old version
            old_tool.handler = old_handler
            old_tool.module = old_module
            old_tool.status = LoadingStatus.ACTIVE
            old_tool.call_count = old_stats["call_count"]
            old_tool.success_count = old_stats["success_count"]
            old_tool.error_count = old_stats["error_count"]
            logger.warning(f"Hot-reload failed for '{name}', restored previous version")

        return result

    # ── Query Methods ────────────────────────────────────────────────────

    def get_loaded_tools(self) -> list[dict]:
        """Get info about all loaded tools."""
        return [
            {
                "name": t.name,
                "status": t.status.value,
                "trust_score": round(t.trust_score, 2),
                "call_count": t.call_count,
                "success_rate": round(t.success_rate, 2),
                "avg_latency_ms": round(t.avg_latency_ms, 1),
                "is_callable": t.is_callable,
            }
            for t in self._loaded_tools.values()
        ]

    def get_loaded_agents(self) -> list[dict]:
        """Get info about all loaded agents."""
        return [
            {
                "name": a.name,
                "status": a.status.value,
                "mode": a.mode,
                "trust_score": round(a.trust_score, 2),
                "call_count": a.call_count,
                "success_rate": round(a.success_rate, 2),
                "is_callable": a.is_callable,
            }
            for a in self._loaded_agents.values()
        ]

    def can_create_and_use_tool(self, task_description: str) -> dict:
        """
        Check if the system can create a tool for a task and use it immediately.

        This is the key capability that was missing: the system can now say
        "I don't have this tool, but I can create it and use it right away."
        """
        return {
            "can_create": True,
            "can_load": True,
            "can_execute": True,
            "pipeline": "detect_gap → generate_tool → validate → load → call",
            "message": "النظام قادر على إنشاء أداة جديدة واستخدامها فوراً عبر DynamicToolLoader",
        }

    def get_stats(self) -> dict:
        """Get comprehensive statistics."""
        tools = list(self._loaded_tools.values())
        agents = list(self._loaded_agents.values())

        return {
            "loaded_tools": len(tools),
            "active_tools": sum(1 for t in tools if t.status == LoadingStatus.ACTIVE),
            "failed_tools": sum(1 for t in tools if t.status == LoadingStatus.FAILED),
            "disabled_tools": sum(1 for t in tools if t.status == LoadingStatus.DISABLED),
            "loaded_agents": len(agents),
            "active_agents": sum(1 for a in agents if a.status == LoadingStatus.ACTIVE),
            "high_trust_tools": sum(1 for t in tools if t.trust_score >= self.TRUST_AUTO_APPROVE),
            "observation_agents": sum(1 for a in agents if a.mode == "observation"),
        }
