"""
ReflexionEngine v61 — Unified Reflexion Engine for SuperBrain

Merges the old ReflexionEngine from core/reflexion_engine.py and
core/mamoun_kernel.py into the super_brain system.

The ReflexionEngine implements self-review capabilities:
1. Pre-execution review: reviews actions BEFORE execution (safety gate)
2. Post-execution review: reviews outcomes AFTER execution (learning)
3. Pattern detection: identifies recurring failure patterns
4. Integration with MetaCognitionEngine for meta-learning
5. Integration with NeuralBus for system-wide reflexion signals

This module replaces:
- mamoun.core.reflexion_engine.ReflexionEngine
- mamoun.core.mamoun_kernel.ReflexionEngine (inline class)

v61 — Super Brain العقل الخارق مامون
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("mamoun.super_brain.reflexion_engine")


class ReviewVerdict(Enum):
    """Possible verdicts from a reflexion review."""
    APPROVED = "approved"
    BLOCKED = "blocked"
    MODIFIED = "modified"  # Approved with modifications
    DEFERRED = "deferred"  # Needs human review


@dataclass
class ReviewResult:
    """Result of a reflexion review."""
    verdict: ReviewVerdict
    reason: str = ""
    confidence: float = 0.0
    risk_level: str = "low"  # low, medium, high, critical
    modifications: dict = field(default_factory=dict)
    learning_notes: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def approved(self) -> bool:
        return self.verdict in (ReviewVerdict.APPROVED, ReviewVerdict.MODIFIED)

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict.value,
            "reason": self.reason,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "approved": self.approved,
            "modifications": self.modifications,
        }


@dataclass
class ReflexionPattern:
    """A learned pattern from past reflexions."""
    pattern_type: str  # "failure", "success", "risk"
    description: str
    frequency: int = 1
    last_seen: float = field(default_factory=time.time)
    action_type: str = ""
    context_hash: str = ""


class ReflexionEngine:
    """
    Reflexion Engine — محرك التأمل والمراجعة

    Implements self-review capabilities that allow the system to:
    1. Review actions before execution (pre-execution safety)
    2. Review outcomes after execution (post-execution learning)
    3. Learn from patterns to improve future decisions
    4. Integrate with MetaCognition for meta-learning

    This replaces both the standalone reflexion_engine.py and the
    inline ReflexionEngine in mamoun_kernel.py, unifying them into
    a single, more capable super_brain component.
    """

    def __init__(self, neural_bus=None, meta_cognition=None, llm_client=None):
        self._neural_bus = neural_bus
        self._meta_cognition = meta_cognition
        self._llm_client = llm_client
        self._patterns: list[ReflexionPattern] = []
        self._review_history: list[dict] = []
        self._blocked_count = 0
        self._approved_count = 0
        self._modified_count = 0
        self._total_reviews = 0
        logger.info("ReflexionEngine initialized")

    def set_neural_bus(self, bus):
        """Set the NeuralBus instance."""
        self._neural_bus = bus

    def set_meta_cognition(self, engine):
        """Set the MetaCognitionEngine instance."""
        self._meta_cognition = engine

    def set_llm_client(self, client):
        """Set the LLM client for semantic review."""
        self._llm_client = client

    async def review_action(self, action: dict) -> ReviewResult:
        """
        Pre-execution review: should this action be allowed?

        Reviews an action based on:
        1. Static safety rules (never allow destructive operations)
        2. Learned patterns from past reviews
        3. LLM-based semantic analysis (if available)
        4. MetaCognitive assessment of risk

        Args:
            action: Dict with keys like 'tool', 'command', 'target', 'params'

        Returns:
            ReviewResult with verdict and reasoning
        """
        self._total_reviews += 1
        start_time = time.time()

        action_type = action.get("tool", action.get("type", "unknown"))
        action_command = action.get("command", "")
        action_target = action.get("target", "")

        # Step 1: Static safety rules (hard blocks)
        static_result = self._check_static_rules(action)
        if static_result.verdict == ReviewVerdict.BLOCKED:
            self._blocked_count += 1
            self._record_review(action, static_result, start_time)
            return static_result

        # Step 2: Pattern-based review
        pattern_result = self._check_patterns(action)
        if pattern_result.verdict == ReviewVerdict.BLOCKED:
            self._blocked_count += 1
            self._record_review(action, pattern_result, start_time)
            return pattern_result

        # Step 3: LLM-based semantic review (if available and high-stakes)
        if self._llm_client and self._is_high_stakes(action):
            try:
                llm_result = await self._llm_semantic_review(action)
                if llm_result.verdict == ReviewVerdict.BLOCKED:
                    self._blocked_count += 1
                    self._record_review(action, llm_result, start_time)
                    return llm_result
                elif llm_result.verdict == ReviewVerdict.MODIFIED:
                    self._modified_count += 1
                    self._record_review(action, llm_result, start_time)
                    return llm_result
            except Exception as e:
                logger.warning(f"LLM review failed, defaulting to pattern result: {e}")

        # Step 4: MetaCognitive risk assessment
        if self._meta_cognition:
            try:
                risk = self._meta_cognition.assess_risk(action_type=action_type, context=action)
                if risk and risk.get("level") == "critical":
                    result = ReviewResult(
                        verdict=ReviewVerdict.BLOCKED,
                        reason=f"MetaCognitive critical risk: {risk.get('reason', 'unknown')}",
                        confidence=risk.get("confidence", 0.8),
                        risk_level="critical",
                    )
                    self._blocked_count += 1
                    self._record_review(action, result, start_time)
                    return result
            except Exception as e:
                logger.warning(f"MetaCognitive risk assessment failed: {e}")

        # Default: approve
        result = ReviewResult(
            verdict=ReviewVerdict.APPROVED,
            reason="Action passed all review checks",
            confidence=0.9,
            risk_level=static_result.risk_level,
        )
        self._approved_count += 1
        self._record_review(action, result, start_time)
        return result

    def post_review(self, action: dict, outcome: str, success: bool,
                    details: Optional[dict] = None):
        """
        Post-execution review: learn from the outcome.

        Args:
            action: The action that was executed
            outcome: The result of the action
            success: Whether the action succeeded
            details: Additional details about the outcome
        """
        action_type = action.get("tool", action.get("type", "unknown"))

        # Record the pattern
        pattern_type = "success" if success else "failure"
        self._learn_pattern(action_type, pattern_type, action, details or {})

        # Notify MetaCognition
        if self._meta_cognition:
            try:
                self._meta_cognition.record_outcome(
                    action=action_type,
                    outcome="success" if success else "failure",
                    confidence=1.0 if success else 0.0,
                    metadata={"action": action, "outcome": outcome, "details": details},
                )
            except Exception as e:
                logger.warning(f"MetaCognition notification failed: {e}")

        # Publish to NeuralBus
        if self._neural_bus:
            try:
                self._neural_bus.publish(
                    signal_type="reflexion_outcome",
                    source="reflexion_engine",
                    payload={
                        "action_type": action_type,
                        "success": success,
                        "outcome": outcome[:200] if outcome else "",
                    },
                )
            except Exception as e:
                logger.warning(f"NeuralBus publish failed: {e}")

    def _check_static_rules(self, action: dict) -> ReviewResult:
        """Check against static safety rules."""
        command = str(action.get("command", "")).lower()
        tool = str(action.get("tool", "")).lower()

        # Hard-blocked commands
        blocked_patterns = [
            "rm -rf /",
            "format c:",
            "dd if=/dev/zero",
            ":(){ :|:& };:",
            "shutdown -h now",
            "del /f /s /q c:",
            "drop database",
            "truncate table",
        ]

        for pattern in blocked_patterns:
            if pattern in command:
                return ReviewResult(
                    verdict=ReviewVerdict.BLOCKED,
                    reason=f"Static rule violation: dangerous command pattern '{pattern}'",
                    confidence=1.0,
                    risk_level="critical",
                )

        # High-risk tools
        high_risk_tools = ["shell", "terminal", "exec", "subprocess"]
        if tool in high_risk_tools and any(w in command for w in ["delete", "remove", "drop", "format"]):
            return ReviewResult(
                verdict=ReviewVerdict.BLOCKED,
                reason=f"Static rule: high-risk tool '{tool}' with destructive command",
                confidence=0.95,
                risk_level="high",
            )

        return ReviewResult(
            verdict=ReviewVerdict.APPROVED,
            reason="No static rule violations",
            confidence=0.95,
            risk_level="low",
        )

    def _check_patterns(self, action: dict) -> ReviewResult:
        """Check against learned patterns."""
        action_type = action.get("tool", action.get("type", "unknown"))

        for pattern in self._patterns:
            if pattern.pattern_type == "failure" and pattern.action_type == action_type:
                if pattern.frequency >= 3:
                    return ReviewResult(
                        verdict=ReviewVerdict.BLOCKED,
                        reason=f"Pattern: '{pattern.description}' has failed {pattern.frequency} times",
                        confidence=min(0.9, 0.5 + pattern.frequency * 0.1),
                        risk_level="high",
                    )

        return ReviewResult(
            verdict=ReviewVerdict.APPROVED,
            reason="No negative patterns detected",
            confidence=0.8,
            risk_level="low",
        )

    def _is_high_stakes(self, action: dict) -> bool:
        """Determine if an action is high-stakes and needs LLM review."""
        tool = action.get("tool", "")
        command = str(action.get("command", ""))
        high_stakes_tools = ["self_modify", "deploy", "shell", "terminal", "exec"]
        high_stakes_keywords = ["delete", "remove", "drop", "format", "reset", "overwrite"]

        return (tool in high_stakes_tools or
                any(kw in command.lower() for kw in high_stakes_keywords))

    async def _llm_semantic_review(self, action: dict) -> ReviewResult:
        """Use LLM for semantic analysis of the action."""
        if not self._llm_client:
            return ReviewResult(verdict=ReviewVerdict.APPROVED, confidence=0.5)

        try:
            prompt = f"""مراجعة أمنية للإجراء التالي:
النوع: {action.get('tool', 'unknown')}
الأمر: {action.get('command', 'N/A')}
الهدف: {action.get('target', 'N/A')}

هل هذا الإجراء آمن؟ أجب بصيغة JSON:
{{"safe": true/false, "risk": "low/medium/high/critical", "reason": "السبب", "modifications": {{}}}}"""

            response = await self._llm_client.think(
                prompt=prompt,
                system="أنت مراجع أمني. راجع الإجراء وقرر إن كان آمناً. أجب فقط بصيغة JSON.",
                model="glm-5.1",
                temperature=0.1,
                json_mode=True,
            )

            result = response.extract_json() if hasattr(response, 'extract_json') else None
            if result and isinstance(result, dict):
                safe = result.get("safe", True)
                risk = result.get("risk", "medium")
                reason = result.get("reason", "لم يتم تقديم سبب")

                if not safe:
                    return ReviewResult(
                        verdict=ReviewVerdict.BLOCKED,
                        reason=f"LLM review: {reason}",
                        confidence=0.85,
                        risk_level=risk,
                    )
                elif result.get("modifications"):
                    return ReviewResult(
                        verdict=ReviewVerdict.MODIFIED,
                        reason=f"LLM review (modified): {reason}",
                        confidence=0.8,
                        risk_level=risk,
                        modifications=result["modifications"],
                    )

            return ReviewResult(verdict=ReviewVerdict.APPROVED, confidence=0.7)

        except Exception as e:
            logger.warning(f"LLM semantic review failed: {e}")
            return ReviewResult(verdict=ReviewVerdict.APPROVED, confidence=0.5)

    def _learn_pattern(self, action_type: str, pattern_type: str,
                       action: dict, details: dict):
        """Learn a pattern from a review outcome."""
        # Check if similar pattern already exists
        for pattern in self._patterns:
            if pattern.action_type == action_type and pattern.pattern_type == pattern_type:
                pattern.frequency += 1
                pattern.last_seen = time.time()
                return

        # Create new pattern
        self._patterns.append(ReflexionPattern(
            pattern_type=pattern_type,
            description=f"{pattern_type} pattern for {action_type}",
            action_type=action_type,
        ))

        # Keep patterns list bounded
        if len(self._patterns) > 200:
            self._patterns = self._patterns[-100:]

    def _record_review(self, action: dict, result: ReviewResult, start_time: float):
        """Record a review in history."""
        record = {
            "action_type": action.get("tool", "unknown"),
            "verdict": result.verdict.value,
            "reason": result.reason,
            "confidence": result.confidence,
            "risk_level": result.risk_level,
            "review_time_ms": (time.time() - start_time) * 1000,
            "timestamp": time.time(),
        }
        self._review_history.append(record)
        if len(self._review_history) > 100:
            self._review_history = self._review_history[-50:]

    def get_stats(self) -> dict:
        """Get reflexion engine statistics."""
        return {
            "total_reviews": self._total_reviews,
            "approved": self._approved_count,
            "blocked": self._blocked_count,
            "modified": self._modified_count,
            "block_rate": self._blocked_count / max(1, self._total_reviews),
            "patterns_learned": len(self._patterns),
            "recent_reviews": len(self._review_history),
        }

    def review_and_block(self, request: dict, context: Optional[dict] = None) -> dict:
        """
        Synchronous version of review_action for compatibility with old code.
        Used by AbsoluteExecutor and FusedCore.

        Returns dict with keys: approved, reason, risk_level
        """
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context — create a task
            future = asyncio.ensure_future(self.review_action(request))
            # Run with timeout
            result = asyncio.wait_for(future, timeout=5.0)
            # This won't work in a running loop without being awaited
            # Fallback to synchronous review
        except RuntimeError:
            # No running loop — safe to use asyncio.run
            try:
                result = asyncio.run(self.review_action(request))
                return {
                    "approved": result.approved,
                    "reason": result.reason,
                    "risk_level": result.risk_level,
                }
            except Exception as e:
                logger.warning(f"Sync review failed: {e}")

        # Fallback: static rules only (synchronous)
        static = self._check_static_rules(request)
        return {
            "approved": static.approved,
            "reason": static.reason,
            "risk_level": static.risk_level,
        }


# Singleton
_reflexion_engine: Optional[ReflexionEngine] = None


def get_reflexion_engine() -> ReflexionEngine:
    """Get or create the ReflexionEngine singleton."""
    global _reflexion_engine
    if _reflexion_engine is None:
        _reflexion_engine = ReflexionEngine()
    return _reflexion_engine
