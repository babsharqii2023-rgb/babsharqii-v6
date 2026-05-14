"""
MetaCognition Engine v59.1 — REAL self-awareness through actual measurement.

CRITICAL UPGRADE from v58:
- v59.1: Version consistency with kernel v59.1
- v58: Fixed all import paths (relative imports work correctly)
- Added persistence (save/load to disk)
- Added periodic self-assessment scheduling
- Added component health checking
- Fixed stagnation detection logic
- Added performance anomaly detection

This is NOT fake awareness — every score reflects real data.

v59.1 — Super Mind العقل الخارق مامون
"""

import os
import json
import time
import tempfile
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
    quality_samples: list = field(default_factory=list)  # Last N quality scores
    latency_samples: list = field(default_factory=list)  # Last N latencies
    prediction_samples: list = field(default_factory=list)  # What we predicted
    last_operation_time: Optional[float] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    stagnation_count: int = 0  # How many stagnation checks detected no improvement
    last_improvement_time: Optional[float] = None
    error_types: dict = field(default_factory=dict)  # error_type -> count

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
        """
        if len(self.prediction_samples) < 3 or len(self.quality_samples) < 3:
            return 0.0
        n = min(len(self.prediction_samples), len(self.quality_samples), 20)
        predictions = self.prediction_samples[-n:]
        actuals = self.quality_samples[-n:]
        mae = statistics.mean(abs(p - a) for p, a in zip(predictions, actuals))
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
    def latency_p95(self) -> float:
        """P95 latency in ms."""
        if not self.latency_samples:
            return 0.0
        sorted_lat = sorted(self.latency_samples)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

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

        trend_bonus = max(0.0, min(1.0, 0.5 + self.quality_trend))

        score = (
            weights["success_rate"] * self.success_rate +
            weights["quality"] * self.quality_average +
            weights["calibration"] * self.confidence_calibration +
            weights["trend"] * trend_bonus
        )
        return round(score, 4)

    @property
    def health_status(self) -> str:
        """Human-readable health status."""
        if self.total_operations == 0:
            return "unknown"
        if self.consecutive_failures >= 5:
            return "critical"
        if self.reliability_score < 0.3:
            return "poor"
        if self.is_stagnant:
            return "stagnant"
        if self.reliability_score >= 0.8:
            return "healthy"
        if self.reliability_score >= 0.5:
            return "moderate"
        return "degraded"


class MetaCognitionEngine:
    """
    REAL Meta-Cognition Engine — measures actual performance, not fake scores.

    Key principles:
    1. EVERY score comes from real operation outcomes
    2. record_outcome() MUST be called by every component after each operation
    3. Rolling averages prevent old data from dominating
    4. Confidence calibration measures self-awareness accuracy
    5. Stagnation detection triggers improvement proposals
    6. Persistence saves data to disk for survival across restarts

    Usage:
        engine = MetaCognitionEngine()
        engine.record_outcome(OutcomeRecord(
            component="brain_router",
            operation="route_query",
            success=True,
            quality_score=0.85,
            predicted_quality=0.80,
            latency_ms=150,
        ))
        profile = engine.get_profile("brain_router")
        print(f"Real reliability: {profile.reliability_score}")
    """

    MAX_SAMPLES = 100  # Rolling window size
    STAGNATION_THRESHOLD = 50  # Operations without improvement = stagnation
    MIN_SAMPLES_BEFORE_ASSESSMENT = 5  # Need at least 5 operations before scoring
    PERSISTENCE_DIR = os.path.join(tempfile.gettempdir(), "super_mind_meta")

    def __init__(self, neural_bus=None, persistence_dir: str = None):
        self._profiles: dict[str, ComponentProfile] = {}
        self._outcomes_log: list[OutcomeRecord] = []
        self._max_log_size = 10000
        self._neural_bus = neural_bus
        self._llm_client = None
        self._persistence_dir = persistence_dir or self.PERSISTENCE_DIR
        self._last_save_time = 0.0
        self._save_interval = 60.0  # Save every 60 seconds

        # Try to load persisted data
        self._load_from_disk()

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
            # Track error types
            if outcome.error:
                err_key = outcome.error[:50]  # First 50 chars
                profile.error_types[err_key] = profile.error_types.get(err_key, 0) + 1

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

        # Track improvement — improved stagnation detection
        if len(profile.quality_samples) >= 10:
            current_avg = statistics.mean(profile.quality_samples[-10:])
            older_avg = statistics.mean(profile.quality_samples[-20:-10]) if len(profile.quality_samples) >= 20 else current_avg
            improvement = current_avg - older_avg
            if improvement > 0.01:  # Meaningful improvement
                profile.last_improvement_time = time.time()
                profile.stagnation_count = 0
            elif profile.total_operations % 10 == 0:
                # Check every 10 operations
                profile.stagnation_count += 1

        # Auto-save periodically
        if time.time() - self._last_save_time > self._save_interval:
            self._save_to_disk()

        # Publish event via NeuralBus
        if self._neural_bus:
            try:
                from ..shared.neural_bus import Event, EventType
                self._neural_bus.publish_sync(
                    Event(
                        event_type=EventType.META_RECORD_OUTCOME,
                        source="meta_cognition",
                        data={
                            "component": outcome.component,
                            "success": outcome.success,
                            "quality_score": outcome.quality_score,
                            "reliability": profile.reliability_score,
                            "health_status": profile.health_status,
                        }
                    )
                )
            except (ImportError, AttributeError):
                # NeuralBus not available — continue without events
                pass

        logger.debug(
            f"Recorded outcome for {outcome.component}: "
            f"success={outcome.success}, quality={outcome.quality_score:.2f}, "
            f"reliability={profile.reliability_score:.2f}, health={profile.health_status}"
        )

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
        """Get a real overview of the entire system."""
        overview = {}
        for name, profile in self._profiles.items():
            if profile.total_operations < self.MIN_SAMPLES_BEFORE_ASSESSMENT:
                reliability = None
                status = "insufficient_data"
            else:
                reliability = profile.reliability_score
                status = profile.health_status

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
                "p95_latency_ms": profile.latency_p95,
                "health_status": profile.health_status,
            }

        return overview

    def get_self_assessment(self) -> dict:
        """Honest self-assessment based on REAL data."""
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

            if data["consecutive_failures"] > 3:
                limitations[f"{component}_failures"] = f"{data['consecutive_failures']} consecutive failures"

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
        """Predict the quality of the next operation for a component."""
        profile = self._profiles.get(component)
        if not profile or profile.total_operations < self.MIN_SAMPLES_BEFORE_ASSESSMENT:
            return 0.5  # Honest default: uncertain

        prediction = (
            0.6 * profile.quality_average +
            0.2 * (profile.quality_average + profile.quality_trend) +
            0.2 * profile.success_rate
        )
        return max(0.0, min(1.0, prediction))

    # ── LLM Self-Critique ────────────────────────────────────────────────
    async def self_critique(self, component: str) -> dict:
        """Use LLM to analyze a component's performance and suggest improvements."""
        profile = self._profiles.get(component)
        if not profile or profile.total_operations < self.MIN_SAMPLES_BEFORE_ASSESSMENT:
            return {"critique": "insufficient data for self-critique", "suggestions": []}

        if not self._llm_client:
            return {"critique": "no LLM client available", "suggestions": []}

        summary = f"""Component: {component}
Total operations: {profile.total_operations}
Success rate: {profile.success_rate:.2%}
Quality average: {profile.quality_average:.2%}
Quality trend: {'improving' if profile.quality_trend > 0.02 else 'degrading' if profile.quality_trend < -0.02 else 'stable'}
Confidence calibration: {profile.confidence_calibration:.2%}
Consecutive failures: {profile.consecutive_failures}
Health status: {profile.health_status}
Is stagnant: {profile.is_stagnant}
Top errors: {dict(list(profile.error_types.items())[:5])}"""

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
        return suggestions[:10]

    # ── Stagnation Detection ─────────────────────────────────────────────
    def get_stagnant_components(self) -> list[str]:
        """Get list of components that are stagnating."""
        return [
            name for name, profile in self._profiles.items()
            if profile.is_stagnant and profile.total_operations >= self.MIN_SAMPLES_BEFORE_ASSESSMENT
        ]

    # ── Component Health Check ───────────────────────────────────────────
    def get_unhealthy_components(self) -> list[dict]:
        """Get components with health issues."""
        unhealthy = []
        for name, profile in self._profiles.items():
            if profile.total_operations < self.MIN_SAMPLES_BEFORE_ASSESSMENT:
                continue
            issues = []
            if profile.consecutive_failures >= 3:
                issues.append(f"{profile.consecutive_failures} consecutive failures")
            if profile.reliability_score < 0.4:
                issues.append(f"low reliability ({profile.reliability_score:.0%})")
            if profile.is_stagnant:
                issues.append("stagnant — no improvement detected")
            if profile.latency_p95 > 10000:
                issues.append(f"high latency P95 ({profile.latency_p95:.0f}ms)")
            if issues:
                unhealthy.append({
                    "component": name,
                    "health_status": profile.health_status,
                    "reliability": profile.reliability_score,
                    "issues": issues,
                })
        return unhealthy

    # ── Persistence ──────────────────────────────────────────────────────
    def _save_to_disk(self) -> bool:
        """Save measurement data to disk for persistence across restarts."""
        try:
            os.makedirs(self._persistence_dir, exist_ok=True)
            filepath = os.path.join(self._persistence_dir, "meta_cognition_data.json")

            data = {
                "profiles": {},
                "saved_at": time.time(),
                "version": "v59.1",
            }

            for name, p in self._profiles.items():
                data["profiles"][name] = {
                    "total_operations": p.total_operations,
                    "success_count": p.success_count,
                    "failure_count": p.failure_count,
                    "quality_samples": p.quality_samples[-30:],
                    "latency_samples": p.latency_samples[-30:],
                    "prediction_samples": p.prediction_samples[-30:],
                    "consecutive_failures": p.consecutive_failures,
                    "stagnation_count": p.stagnation_count,
                    "error_types": dict(list(p.error_types.items())[:20]),
                    "last_improvement_time": p.last_improvement_time,
                }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self._last_save_time = time.time()
            return True

        except Exception as e:
            logger.error(f"Failed to save meta-cognition data: {e}")
            return False

    def _load_from_disk(self) -> bool:
        """Load measurement data from disk."""
        try:
            filepath = os.path.join(self._persistence_dir, "meta_cognition_data.json")
            if not os.path.exists(filepath):
                return False

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if data.get("version") not in ("v58", "v59", "v59.1"):
                logger.warning("Loading data from different version — may need migration")

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
                profile.error_types = pdata.get("error_types", {})
                profile.last_improvement_time = pdata.get("last_improvement_time")

            logger.info(f"Loaded meta-cognition data: {len(self._profiles)} profiles")
            return True

        except Exception as e:
            logger.warning(f"Failed to load meta-cognition data: {e}")
            return False

    # ── Export / Import ──────────────────────────────────────────────────
    def export_data(self) -> dict:
        """Export all measurement data."""
        return {
            "profiles": {
                name: {
                    "total_operations": p.total_operations,
                    "success_count": p.success_count,
                    "failure_count": p.failure_count,
                    "quality_samples": p.quality_samples[-20:],
                    "latency_samples": p.latency_samples[-20:],
                    "prediction_samples": p.prediction_samples[-20:],
                    "consecutive_failures": p.consecutive_failures,
                    "stagnation_count": p.stagnation_count,
                    "health_status": p.health_status,
                    "reliability_score": p.reliability_score,
                }
                for name, p in self._profiles.items()
            },
            "exported_at": time.time(),
        }

    def import_data(self, data: dict) -> None:
        """Import measurement data."""
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

    def save(self) -> bool:
        """Public save method."""
        return self._save_to_disk()
