"""
Tool Creator v58 — LLM-powered tool creation with real registration and auto-testing.

CRITICAL UPGRADE from v57:
- v57: Import paths for registry were broken (.shared.registry)
- v58: Fixed all import paths with proper fallback
- Added tool versioning and dependency tracking
- Added auto-test execution with real results
- Better validation with security + docstring + type hints check
- Integrated with MetaCognitionEngine for real performance tracking

v58 — Super Mind العقل الخارق مامون
"""

import time
import ast
import logging
from typing import Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class ToolSpecification:
    """Specification for a tool to be created."""
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    purpose: str
    constraints: list[str] = field(default_factory=list)


class ToolCreator:
    """
    Creates tools using LLM and registers them automatically.

    Pipeline:
    1. SPECIFY: Define what the tool should do
    2. GENERATE: LLM generates the tool code
    3. VALIDATE: Check code safety, syntax, docstrings, type hints
    4. TEST: Run basic tests on the tool in sandbox
    5. REGISTER: Add to ToolRegistry with metadata
    6. DOCUMENT: Tool is self-documenting via docstrings

    Usage:
        creator = ToolCreator(llm_client=client, tool_registry=registry)
        tool = await creator.create_tool("web_scraper", "Scrape web pages for data")
    """

    def __init__(self, llm_client=None, tool_registry=None,
                 meta_cognition=None, neural_bus=None):
        self._llm_client = llm_client
        self._tool_registry = tool_registry
        self._meta_cognition = meta_cognition
        self._neural_bus = neural_bus
        self._created_tools: list[dict] = []

    def set_llm_client(self, client):
        self._llm_client = client

    def set_tool_registry(self, registry):
        self._tool_registry = registry

    def _get_registry(self):
        """Get the tool registry with proper import handling."""
        if self._tool_registry:
            return self._tool_registry
        try:
            from ..shared.registry import get_tool_registry
            self._tool_registry = get_tool_registry()
        except ImportError:
            try:
                from shared.registry import get_tool_registry
                self._tool_registry = get_tool_registry()
            except ImportError:
                pass
        return self._tool_registry

    async def create_tool(self, name: str, description: str,
                          input_schema: dict = None,
                          output_schema: dict = None,
                          constraints: list[str] = None) -> dict:
        """Create a new tool using LLM."""
        start = time.time()

        if not self._llm_client:
            return {"success": False, "error": "No LLM client", "tool_name": name}

        schema_info = ""
        if input_schema:
            schema_info += f"\nInput schema: {input_schema}"
        if output_schema:
            schema_info += f"\nOutput schema: {output_schema}"
        if constraints:
            schema_info += f"\nConstraints: {constraints}"

        try:
            response = await self._llm_client.chat_with_fallback(
                messages=[
                    {"role": "system", "content": """You are a Python tool developer.
Create a complete, working Python function for the specified tool.
The function must:
1. Have proper type hints on all parameters and return type
2. Include a comprehensive docstring with Args, Returns, and Examples sections
3. Handle errors gracefully with try/except
4. Return a dict with 'success' (bool) and 'result' or 'error' keys
5. Be safe — no os.system, subprocess, eval, or exec

Return ONLY the Python code — no markdown fences, no explanations."""},
                    {"role": "user", "content": f"""Tool name: {name}
Description: {description}{schema_info}

Write the complete Python function:"""}
                ],
                preferred_order=["deepseek", "gemini", "glm"],
            )

            if not response.success:
                return {"success": False, "error": response.error, "tool_name": name}

            code = response.content.strip()
            # Strip markdown fences
            if code.startswith("```"):
                lines = code.split("\n")
                code = "\n".join(lines[1:])
                if code.endswith("```"):
                    code = code[:-3]
                code = code.strip()

        except Exception as e:
            return {"success": False, "error": str(e), "tool_name": name}

        # Validate code
        validation = self._validate_tool_code(code)

        if not validation["passed"]:
            return {
                "success": False,
                "error": f"Validation failed: {validation['errors']}",
                "tool_name": name,
                "code": code,
            }

        # Test code in sandbox
        test_result = self._test_tool_code(code, name)

        # Register in tool registry
        registry = self._get_registry()
        registered = False
        if registry and (validation["passed"] or test_result.get("success", False)):
            try:
                from ..shared.registry import ToolEntry, ComponentStatus
                registry.register(ToolEntry(
                    name=name,
                    description=description,
                    test_passed=test_result.get("success", False),
                    source="llm_generated",
                    schema={"input": input_schema or {}, "output": output_schema or {}},
                ))
                registered = True
            except ImportError:
                try:
                    from shared.registry import ToolEntry, ComponentStatus
                    registry.register(ToolEntry(
                        name=name,
                        description=description,
                        test_passed=test_result.get("success", False),
                        source="llm_generated",
                        schema={"input": input_schema or {}, "output": output_schema or {}},
                    ))
                    registered = True
                except ImportError:
                    logger.warning("Could not import ToolEntry — tool registered without full metadata")
                    registry.register(type('ToolEntry', (), {
                        'name': name, 'description': description,
                        'test_passed': test_result.get("success", False),
                        'source': "llm_generated",
                    }))
                    registered = True

        # Compute quality score from validation + test
        quality = 0.0
        if validation["passed"]:
            quality += 0.5
        if test_result.get("success", False):
            quality += 0.3
        if validation.get("has_type_hints"):
            quality += 0.1
        if validation.get("has_docstring"):
            quality += 0.1

        result = {
            "success": validation["passed"] or test_result.get("success", False),
            "tool_name": name,
            "code": code,
            "validation": validation,
            "test_result": test_result,
            "registered": registered,
            "quality_score": quality,
            "latency_ms": (time.time() - start) * 1000,
        }

        self._created_tools.append(result)

        # Record in meta-cognition
        if self._meta_cognition:
            try:
                from .meta_cognition_engine import OutcomeRecord
                self._meta_cognition.record_outcome(OutcomeRecord(
                    component="tool_creator",
                    operation="create_tool",
                    success=result["success"],
                    quality_score=quality,
                    predicted_quality=self._meta_cognition.predict_quality("tool_creator"),
                    latency_ms=result["latency_ms"],
                ))
            except ImportError:
                pass

        return result

    def _validate_tool_code(self, code: str) -> dict:
        """Validate generated tool code with comprehensive checks."""
        errors = []

        # Syntax check
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {"passed": False, "errors": [f"Syntax error: {e}"]}

        # Security check
        from .self_modifier import ASTSecurityChecker
        checker = ASTSecurityChecker()
        is_safe, violations = checker.check(code)
        if not is_safe:
            errors.extend(violations)

        # Check for function definition
        has_function = any(isinstance(node, ast.FunctionDef) for node in ast.walk(tree))
        if not has_function:
            errors.append("No function definition found")

        # Check for docstring
        has_docstring = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                docstring = ast.get_docstring(node)
                if docstring:
                    has_docstring = True
        if not has_docstring:
            errors.append("No docstring found (required for documentation)")

        # Check for type hints
        has_type_hints = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.returns is not None:
                    has_type_hints = True
                for arg in node.args.args:
                    if arg.annotation is not None:
                        has_type_hints = True
                        break

        return {
            "passed": len(errors) == 0,
            "errors": errors,
            "has_type_hints": has_type_hints,
            "has_docstring": has_docstring,
        }

    def _test_tool_code(self, code: str, name: str) -> dict:
        """Run basic test on generated tool code in sandbox."""
        from .self_modifier import RestrictedExecutor
        executor = RestrictedExecutor()

        result = executor.execute(code, timeout=10)

        return {
            "success": result["success"],
            "error": result.get("error"),
            "output": result.get("output", ""),
        }

    def get_stats(self) -> dict:
        return {
            "total_tools_created": len(self._created_tools),
            "successful": sum(1 for t in self._created_tools if t.get("success")),
            "registered": sum(1 for t in self._created_tools if t.get("registered")),
            "avg_quality": (sum(t.get("quality_score", 0) for t in self._created_tools) /
                          len(self._created_tools)) if self._created_tools else 0.0,
        }
