"""
MetaCognition Engine v57 — REAL self-awareness through actual measurement.

CRITICAL UPGRADE from v56:
- v56: All scores were hardcoded in quality_map = FAKE
- v57: All scores come from REAL measurements via record_outcome()
- Rolling averages from actual operation results
- Confidence calibration comparing predictions vs reality
- Stagnation detection when a component stops improving
- Self-critique via LLM analysis of own performance

This is NOT fake awareness — every score reflects real data.

v57 — Super Mind العقل الخارق مامون
"""

import time
import logging
import statistics
from typing import Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class OutcomeRecord:
    """Record of a single operation outcome — the atomic unit of measurement."""
    component: str
    operation: str
    success: bool
    quality_score: float  # 0.0 to 1.0 — how good was the result?
    predicted_quality: float  # 0.0 to 1.0 — what did we predict?
    latency_ms: float
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ComponentProfile:
    """Real-time profile of a component based on actual measurements."""
    name: str
    total_operations: int = 0
    success_count: int = 0
    failure_count: int = 0
    quality_samples: list[float] = field(default_factory=list)  # Last N quality scores
    latency_samples: list[float] = field(default_factory=list)  # Last N latencies
    prediction_samples: list[float] = field(default_factory=list)  # What we predicted
    last_operation_time: Optional[float] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    stagnation_count: int = 0  # How many stagnation checks detected no improvement
    last_improvement_time: Optional[float] = None

    # ── Computed metrics (from real data) ──
    @property
    def success_rate(self) -> float:
        """Real success rate from actual operations."""
        if self.total_operations == 0:
            return 0.0
        return self.success_count / self.total_operations

    @property
    def quality_average(self) -> float:
        """Rolling average of quality scores (last 100)."""
        if not self.quality_samples:
            return 0.0
        return statistics.mean(self.quality_samples)

    @property
    def quality_trend(self) -> float:
        """Trend: positive = improving, negative = degrading."""
        if len(self.quality_samples) < 5:
            return 0.0
        recent = self.quality_samples[-10:]
        older = self.quality_samples[-20:-10] if len(self.quality_samples) >= 20 else self.quality_samples[:10]
        if not older:
            return 0.0
        return statistics.mean(recent) - statistics.mean(older)

    @property
    def confidence_calibration(self) -> float:
        """
        How well do our predictions match reality?
        1.0 = perfectly calibrated, 0.0 = no calibration at all.
        This measures whether the system knows its own limits.
        """
        if len(self.prediction_samples) < 3 or len(self.quality_samples) < 3:
            return 0.0
        # Compare last N predictions vs actual outcomes
        n = min(len(self.prediction_samples), len(self.quality_samples), 20)
        predictions = self.prediction_samples[-n:]
        actuals = self.quality_samples[-n:]
        # Mean absolute error between predictions and actuals
        mae = statistics.mean(abs(p - a) for p, a in zip(predictions, actuals))
        # Calibration = 1 - MAE (perfect calibration when MAE = 0)
        return max(0.0, 1.0 - mae)

    @property
    def is_stagnant(self) -> bool:
        """Is this component not improving?"""
        return self.stagnation_count >= 3

    @property
    def latency_average(self) -> float:
        """Average latency in ms."""
        if not self.latency_samples:
            return 0.0
        return statistics.mean(self.latency_samples)

    @property
    def reliability_score(self) -> float:
        """
        Overall reliability: combines success rate, quality, and calibration.
        This is the REAL score — no hardcoded values.
        """
        if self.total_operations == 0:
            return 0.0  # Unknown = 0, not a fake percentage

        weights = {
            "success_rate": 0.3,
            "quality": 0.4,
            "calibration": 0.2,
            "trend": 0.1,
        }

        trend_bonus = max(0.0, min(1.0, 0.5 + self.quality_trend))  # 0-1

        score = (
            weights["success_rate"] * self.success_rate +
            weights["quality"] * self.quality_average +
            weights["calibration"] * self.confidence_calibration +
            weights["trend"] * trend_bonus
        )
        return round(score, 4)


class MetaCognitionEngine:
    """
    REAL Meta-Cognition Engine — measures actual performance, not fake scores.

    Key principles:
    1. EVERY score comes from real operation outcomes
    2. record_outcome() MUST be called by every component after each operation
    3. Rolling averages prevent old data from dominating
    4. Confidence calibration measures self-awareness accuracy
    5. Stagnation detection triggers improvement proposals

    Usage:
        engine = MetaCognitionEngine()
        # After any operation:
        engine.record_outcome(OutcomeRecord(
            component="brain_router",
            operation="route_query",
            success=True,
            quality_score=0.85,
            predicted_quality=0.80,
            latency_ms=150,
        ))
        # Get real assessment:
        profile = engine.get_profile("brain_router")
        print(f"Real reliability: {profile.reliability_score}")
    """

    MAX_SAMPLES = 100  # Rolling window size
    STAGNATION_THRESHOLD = 50  # Operations without improvement = stagnation
    MIN_SAMPLES_BEFORE_ASSESSMENT = 5  # Need at least 5 operations before scoring

    def __init__(self, neural_bus=None):
        self._profiles: dict[str, ComponentProfile] = {}
        self._outcomes_log: list[OutcomeRecord] = []
        self._max_log_size = 10000
        self._neural_bus = neural_bus
        self._llm_client = None  # Injected later for self-critique

        # Subscribe to events if bus is provided
        if self._neural_bus:
            self._neural_bus.subscribe("meta.record_outcome", self._handle_outcome_event)

    def set_llm_client(self, client):
        """Inject the multi-provider LLM client for self-critique."""
        self._llm_client = client

    # ── Core: Record Outcome ─────────────────────────────────────────────
    def record_outcome(self, outcome: OutcomeRecord) -> None:
        """
        THE most important method. Every component MUST call this after each operation.
        This is what makes the scores REAL instead of hardcoded.
        """
        # Log the outcome
        self._outcomes_log.append(outcome)
        if len(self._outcomes_log) > self._max_log_size:
            self._outcomes_log = self._outcomes_log[-self._max_log_size:]

        # Get or create profile
        profile = self._get_or_create_profile(outcome.component)

        # Update counters
        profile.total_operations += 1
        profile.last_operation_time = outcome.timestamp

        if outcome.success:
            profile.success_count += 1
            profile.consecutive_successes += 1
            profile.consecutive_failures = 0
        else:
            profile.failure_count += 1
            profile.consecutive_failures += 1
            profile.consecutive_successes = 0

        # Rolling quality samples
        profile.quality_samples.append(outcome.quality_score)
        if len(profile.quality_samples) > self.MAX_SAMPLES:
            profile.quality_samples = profile.quality_samples[-self.MAX_SAMPLES:]

        # Rolling latency samples
        profile.latency_samples.append(outcome.latency_ms)
        if len(profile.latency_samples) > self.MAX_SAMPLES:
            profile.latency_samples = profile.latency_samples[-self.MAX_SAMPLES:]

        # Rolling prediction samples (for calibration)
        profile.prediction_samples.append(outcome.predicted_quality)
        if len(profile.prediction_samples) > self.MAX_SAMPLES:
            profile.prediction_samples = profile.prediction_samples[-self.MAX_SAMPLES:]

        # Track improvement
        if len(profile.quality_samples) >= 10:
            current_avg = statistics.mean(profile.quality_samples[-10:])
            if profile.last_improvement_time is None or current_avg > statistics.mean(profile.quality_samples[-20:-10]) if len(profile.quality_samples) >= 20 else True:
                profile.last_improvement_time = time.time()
                profile.stagnation_count = 0
            else:
                profile.stagnation_count += 1

        # Publish event
        if self._neural_bus:
            from .shared.neural_bus import Event, EventType
            self._neural_bus.publish_sync(
                Event(
                    event_type=EventType.META_RECORD_OUTCOME,
                    source="meta_cognition",
                    data={
                        "component": outcome.component,
                        "success": outcome.success,
                        "quality_score": outcome.quality_score,
                        "reliability": profile.reliability_score,
                    }
                )
            )

        logger.debug(
            f"Recorded outcome for {outcome.component}: "
            f"success={outcome.success}, quality={outcome.quality_score:.2f}, "
            f"reliability={profile.reliability_score:.2f}"
        )

    async def _handle_outcome_event(self, event) -> None:
        """Handle outcome events from the Neural Bus."""
        data = event.data
        self.record_outcome(OutcomeRecord(
            component=data.get("component", "unknown"),
            operation=data.get("operation", "unknown"),
            success=data.get("success", False),
            quality_score=data.get("quality_score", 0.0),
            predicted_quality=data.get("predicted_quality", 0.5),
            latency_ms=data.get("latency_ms", 0.0),
            error=data.get("error"),
        ))

    # ── Profile Management ───────────────────────────────────────────────
    def _get_or_create_profile(self, component: str) -> ComponentProfile:
        if component not in self._profiles:
            self._profiles[component] = ComponentProfile(name=component)
        return self._profiles[component]

    def get_profile(self, component: str) -> Optional[ComponentProfile]:
        """Get the real profile for a component."""
        return self._profiles.get(component)

    def get_all_profiles(self) -> dict[str, ComponentProfile]:
        """Get all component profiles."""
        return dict(self._profiles)

    # ── Self-Assessment ──────────────────────────────────────────────────
    def get_system_overview(self) -> dict:
        """
        Get a real overview of the entire system.
        No fake percentages — only scores from actual measurements.
        """
        overview = {}
        for name, profile in self._profiles.items():
            if profile.total_operations < self.MIN_SAMPLES_BEFORE_ASSESSMENT:
                reliability = None  # Not enough data yet
                status = "insufficient_data"
            else:
                reliability = profile.reliability_score
                if profile.is_stagnant:
                    status = "stagnant"
                elif profile.quality_trend > 0.05:
                    status = "improving"
                elif profile.quality_trend < -0.05:
                    status = "degrading"
                else:
                    status = "stable"

            overview[name] = {
                "reliability_score": reliability,
                "status": status,
                "total_operations": profile.total_operations,
                "success_rate": profile.success_rate,
                "quality_average": profile.quality_average,
                "confidence_calibration": profile.confidence_calibration,
                "quality_trend": profile.quality_trend,
                "is_stagnant": profile.is_stagnant,
                "consecutive_failures": profile.consecutive_failures,
                "avg_latency_ms": profile.latency_average,
            }

        return overview

    def get_self_assessment(self) -> dict:
        """
        Honest self-assessment: what can I do, what can't I do?
        Based on REAL data, not wishful thinking.
        """
        overview = self.get_system_overview()

        capabilities = {}
        limitations = {}

        for component, data in overview.items():
            if data["reliability_score"] is None:
                capabilities[component] = "unknown — not enough operations yet"
                limitations[component] = "cannot assess — need more usage data"
            elif data["reliability_score"] >= 0.8:
                capabilities[component] = f"reliable ({data['reliability_score']:.0%})"
            elif data["reliability_score"] >= 0.5:
                capabilities[component] = f"moderate ({data['reliability_score']:.0%})"
                limitations[component] = f"success rate {data['success_rate']:.0%}, quality {data['quality_average']:.0%}"
            else:
                limitations[component] = f"unreliable ({data['reliability_score']:.0%}) — needs improvement"

            if data.get("is_stagnant"):
                limitations[f"{component}_stagnation"] = "component has stopped improving"

        return {
            "capabilities": capabilities,
            "limitations": limitations,
            "overall_confidence": self._compute_overall_confidence(),
            "components_assessed": len(overview),
            "components_with_data": sum(
                1 for d in overview.values() if d["reliability_score"] is not None
            ),
        }

    def _compute_overall_confidence(self) -> float:
        """Compute overall system confidence from real data."""
        scores = [
            p.reliability_score
            for p in self._profiles.values()
            if p.total_operations >= self.MIN_SAMPLES_BEFORE_ASSESSMENT
        ]
        if not scores:
            return 0.0
        return statistics.mean(scores)

    # ── Predict Quality ──────────────────────────────────────────────────
    def predict_quality(self, component: str) -> float:
        """
        Predict the quality of the next operation for a component.
        This prediction is later compared to actual quality for calibration.
        """
        profile = self._profiles.get(component)
        if not profile or profile.total_operations < self.MIN_SAMPLES_BEFORE_ASSESSMENT:
            return 0.5  # Honest default: uncertain

        # Prediction = weighted combination of recent performance + trend
        prediction = (
            0.6 * profile.quality_average +
            0.2 * (profile.quality_average + profile.quality_trend) +
            0.2 * profile.success_rate
        )
        return max(0.0, min(1.0, prediction))

    # ── LLM Self-Critique ────────────────────────────────────────────────
    async def self_critique(self, component: str) -> dict:
        """
        Use LLM to analyze a component's performance and suggest improvements.
        This is the deepest form of self-awareness: the system critiques itself.
        """
        profile = self._profiles.get(component)
        if not profile or profile.total_operations < self.MIN_SAMPLES_BEFORE_ASSESSMENT:
            return {"critique": "insufficient data for self-critique", "suggestions": []}

        if not self._llm_client:
            return {"critique": "no LLM client available", "suggestions": []}

        # Build performance summary
        summary = f"""Component: {component}
Total operations: {profile.total_operations}
Success rate: {profile.success_rate:.2%}
Quality average: {profile.quality_average:.2%}
Quality trend: {'improving' if profile.quality_trend > 0.02 else 'degrading' if profile.quality_trend < -0.02 else 'stable'}
Confidence calibration: {profile.confidence_calibration:.2%}
Consecutive failures: {profile.consecutive_failures}
Is stagnant: {profile.is_stagnant}
Recent errors: {profile.failure_count} out of {profile.total_operations}"""

        try:
            response = await self._llm_client.chat_with_fallback(
                messages=[
                    {"role": "system", "content": "You are a system performance analyst. Analyze the component metrics and provide specific, actionable suggestions for improvement. Be honest and precise."},
                    {"role": "user", "content": f"Analyze this component's performance and suggest improvements:\n\n{summary}"}
                ],
                preferred_order=["deepseek", "gemini", "glm"],
            )

            if response.success:
                return {
                    "critique": response.content,
                    "suggestions": self._extract_suggestions(response.content),
                    "provider_used": response.provider,
                }
            else:
                return {"critique": f"LLM critique failed: {response.error}", "suggestions": []}

        except Exception as e:
            return {"critique": f"Self-critique error: {e}", "suggestions": []}

    def _extract_suggestions(self, critique_text: str) -> list[str]:
        """Extract actionable suggestions from LLM critique."""
        suggestions = []
        for line in critique_text.split("\n"):
            line = line.strip()
            if line.startswith(("- ", "* ", "• ", "1.", "2.", "3.", "4.", "5.")):
                clean = line.lstrip("-*•0123456789. ").strip()
                if clean:
                    suggestions.append(clean)
        return suggestions[:10]  # Max 10 suggestions

    # ── Stagnation Detection ─────────────────────────────────────────────
    def get_stagnant_components(self) -> list[str]:
        """Get list of components that are stagnating."""
        return [
            name for name, profile in self._profiles.items()
            if profile.is_stagnant and profile.total_operations >= self.MIN_SAMPLES_BEFORE_ASSESSMENT
        ]

    # ── Export / Import ──────────────────────────────────────────────────
    def export_data(self) -> dict:
        """Export all measurement data for persistence."""
        return {
            "profiles": {
                name: {
                    "total_operations": p.total_operations,
                    "success_count": p.success_count,
                    "failure_count": p.failure_count,
                    "quality_samples": p.quality_samples[-20:],  # Last 20
                    "latency_samples": p.latency_samples[-20:],
                    "prediction_samples": p.prediction_samples[-20:],
                    "consecutive_failures": p.consecutive_failures,
                    "stagnation_count": p.stagnation_count,
                }
                for name, p in self._profiles.items()
            },
            "exported_at": time.time(),
        }

    def import_data(self, data: dict) -> None:
        """Import measurement data from persistence."""
        for name, pdata in data.get("profiles", {}).items():
            profile = self._get_or_create_profile(name)
            profile.total_operations = pdata.get("total_operations", 0)
            profile.success_count = pdata.get("success_count", 0)
            profile.failure_count = pdata.get("failure_count", 0)
            profile.quality_samples = pdata.get("quality_samples", [])
            profile.latency_samples = pdata.get("latency_samples", [])
            profile.prediction_samples = pdata.get("prediction_samples", [])
            profile.consecutive_failures = pdata.get("consecutive_failures", 0)
            profile.stagnation_count = pdata.get("stagnation_count", 0)
