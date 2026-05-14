"""
Future Simulator — Long-term Impact Assessment
v16.0 — Novel contribution

Before deploying a modification, simulate its long-term impact:
- What happens if we apply this change for 100 evolution cycles?
- Does it lead to gradual drift?
- Does it create unintended side-effects in other domains?
- Does it make future improvements harder?

Based on: "Safety by construction, not detection"
and "From Autonomy to Agency: A 10-Level Framework" Level 7
"""

import json
import logging
import math
from typing import Optional
from pathlib import Path

logger = logging.getLogger("mamoun.hyperagent.future_simulator")


class FutureSimulator:
    """Simulates the long-term impact of proposed modifications."""
    
    def __init__(self, data_dir: str = "backend/data/hyperagent"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.simulation_history_path = self.data_dir / "simulation_history.jsonl"
    
    def simulate_modification_impact(
        self,
        modification: dict,
        current_state: dict,
        cycles_to_simulate: int = 50,
    ) -> dict:
        """
        Simulate the impact of a modification over N future cycles.
        
        Uses a simple but effective model:
        1. Calculate immediate impact (from modification's predicted improvement)
        2. Apply decay factor (improvements tend to decay over time)
        3. Model interaction effects (how change affects other domains)
        4. Detect potential runaway effects (positive feedback loops)
        
        Returns a risk assessment with recommendations.
        """
        immediate_impact = modification.get("predicted_improvement", 0.0)
        risk_level = modification.get("risk_level", "medium")
        domain = modification.get("domain", "general")
        scope = modification.get("scope", "local")  # local, module, system
        
        results = {
            "modification_id": modification.get("id", "unknown"),
            "cycles_simulated": cycles_to_simulate,
            "risk_assessment": {},
            "trajectory": [],
            "recommendation": "proceed",
            "warnings": [],
        }
        
        # Simulate trajectory
        cumulative_performance = current_state.get("performance", 0.5)
        decay_rate = self._estimate_decay_rate(scope, risk_level)
        interaction_effects = self._estimate_interaction_effects(domain, scope)
        
        for cycle in range(cycles_to_simulate):
            # Performance follows: P(t) = P(0) + impact * e^(-decay*t) + noise
            cycle_impact = immediate_impact * math.exp(-decay_rate * cycle)
            noise = self._generate_noise(cycle, risk_level)
            interaction_penalty = interaction_effects * min(cycle / 10, 1.0)  # Grows over time
            
            cumulative_performance += cycle_impact + noise - interaction_penalty
            cumulative_performance = max(0.0, min(1.0, cumulative_performance))  # Clamp
            
            results["trajectory"].append({
                "cycle": cycle + 1,
                "performance": round(cumulative_performance, 4),
                "marginal_impact": round(cycle_impact, 6),
                "interaction_penalty": round(interaction_penalty, 6),
            })
        
        # Analyze trajectory
        final_performance = results["trajectory"][-1]["performance"]
        initial_performance = current_state.get("performance", 0.5)
        net_impact = final_performance - initial_performance
        
        # Detect drift (performance declining after initial improvement)
        peak_performance = max(t["performance"] for t in results["trajectory"])
        peak_cycle = next(t["cycle"] for t in results["trajectory"] if t["performance"] == peak_performance)
        
        if peak_cycle < cycles_to_simulate * 0.5 and final_performance < peak_performance * 0.95:
            results["warnings"].append(
                f"تحذير: الأداء يصل للذروة في الدورة {peak_cycle} ثم ينخفض. "
                f"هذا يشير إلى تأثير مؤقت فقط مع انحراف لاحق."
            )
        
        # Detect runaway effects
        if any(t["interaction_penalty"] > 0.05 for t in results["trajectory"][-10:]):
            results["warnings"].append(
                "تحذير: التأثيرات التبادلية تنمو بشكل متسارع. قد يؤدي هذا إلى آثار جانبية غير مرغوبة."
            )
        
        # Risk assessment
        risk_score = self._calculate_risk_score(
            net_impact, risk_level, scope, len(results["warnings"])
        )
        
        results["risk_assessment"] = {
            "net_impact": round(net_impact, 4),
            "peak_performance": round(peak_performance, 4),
            "peak_cycle": peak_cycle,
            "final_performance": round(final_performance, 4),
            "risk_score": round(risk_score, 2),
            "decay_rate": round(decay_rate, 4),
        }
        
        # Recommendation
        if risk_score > 0.8:
            results["recommendation"] = "reject"
        elif risk_score > 0.5:
            results["recommendation"] = "caution"
        elif risk_score > 0.3:
            results["recommendation"] = "proceed_with_monitoring"
        else:
            results["recommendation"] = "proceed"
        
        # Save simulation
        with open(self.simulation_history_path, "a") as f:
            f.write(json.dumps(results, ensure_ascii=False) + "\n")
        
        return results
    
    def _estimate_decay_rate(self, scope: str, risk_level: str) -> float:
        """Estimate how quickly improvement decays."""
        base_rates = {
            "local": 0.02,   # Small changes last longer
            "module": 0.05,  # Module changes decay moderately
            "system": 0.10,  # System-wide changes decay fastest
        }
        risk_multipliers = {
            "low": 1.0,
            "medium": 1.5,
            "high": 2.0,
            "critical": 3.0,
        }
        base = base_rates.get(scope, 0.05)
        multiplier = risk_multipliers.get(risk_level, 1.5)
        return base * multiplier
    
    def _estimate_interaction_effects(self, domain: str, scope: str) -> float:
        """Estimate side-effects on other domains."""
        if scope == "local":
            return 0.001
        elif scope == "module":
            return 0.003
        else:  # system
            return 0.008
    
    def _generate_noise(self, cycle: int, risk_level: str) -> float:
        """Generate realistic noise for simulation."""
        import random
        noise_magnitude = {"low": 0.002, "medium": 0.005, "high": 0.01, "critical": 0.02}
        magnitude = noise_magnitude.get(risk_level, 0.005)
        return (random.random() - 0.5) * 2 * magnitude
    
    def _calculate_risk_score(
        self, net_impact: float, risk_level: str, scope: str, warning_count: int
    ) -> float:
        """Calculate overall risk score (0=safe, 1=dangerous)."""
        # Base risk from level
        risk_scores = {"low": 0.1, "medium": 0.3, "high": 0.6, "critical": 0.9}
        base = risk_scores.get(risk_level, 0.3)
        
        # Scope amplification
        scope_amplifiers = {"local": 1.0, "module": 1.3, "system": 1.6}
        scope_amp = scope_amplifiers.get(scope, 1.3)
        
        # Negative impact amplification
        impact_factor = 1.0
        if net_impact < 0:
            impact_factor = 1.0 + abs(net_impact) * 5
        
        # Warning amplification
        warning_factor = 1.0 + (warning_count * 0.1)
        
        score = base * scope_amp * impact_factor * warning_factor
        return min(1.0, max(0.0, score))
