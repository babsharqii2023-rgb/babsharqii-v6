"""
Meta Agent — Layer 2 of DGM-H Architecture
Based on: Hyperagents (Zhang et al., 2026)

The Meta Agent monitors the Task Agent's improvement process and can modify
the mechanism of modification itself. This is the key innovation over DGM:

"DGM's self-improvement relied on one implicit assumption: improving at the task
also improves the agent's ability to modify itself. This is WRONG."

The Meta Agent specifically improves:
1. How mutations are generated (mutation strategy)
2. How fitness is evaluated (evaluation criteria)
3. How improvements are selected (selection pressure)
4. How the search space is explored (exploration vs exploitation)

These are NOT task-level improvements — they are META-LEVEL improvements
that make all future task-level improvements better.
"""

import json
import hashlib
import time
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger("mamoun.hyperagent.meta_agent")


class MetaModification:
    """Represents a modification to the improvement mechanism itself."""
    
    def __init__(
        self,
        target: str,  # What aspect of the improvement mechanism to modify
        current_value: Any,
        proposed_value: Any,
        reasoning: str,
        confidence: float,
        domain: str = "general",
        source: str = "meta_agent",
    ):
        self.id = hashlib.sha256(
            f"{target}:{time.time()}:{hashlib.md5(reasoning.encode()).hexdigest()}".encode()
        ).hexdigest()[:16]
        self.target = target
        self.current_value = current_value
        self.proposed_value = proposed_value
        self.reasoning = reasoning
        self.confidence = confidence
        self.domain = domain
        self.source = source
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.status = "proposed"  # proposed → tested → approved → deployed / rejected
        self.test_results: dict = {}
        self.impact_score: float = 0.0  # How much this meta-mod improved future improvements
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "target": self.target,
            "current_value": self.current_value,
            "proposed_value": self.proposed_value,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "domain": self.domain,
            "source": self.source,
            "created_at": self.created_at,
            "status": self.status,
            "test_results": self.test_results,
            "impact_score": self.impact_score,
        }


class MetaAgent:
    """
    Layer 2: Meta Agent that improves the improvement mechanism.
    
    Monitors:
    - Mutation success rates per strategy
    - Fitness evaluation accuracy
    - Selection pressure effectiveness
    - Exploration/exploitation balance
    - Stagnation detection and recovery
    
    Can modify:
    - mutation_strategies: How mutations are proposed
    - fitness_weights: How fitness is evaluated
    - selection_thresholds: What gets accepted
    - exploration_rate: How much to explore vs exploit
    - improvement_timeout: How long to try before giving up
    """
    
    # Immutable safety constraints — can NEVER be modified even by MetaAgent
    IMMUTABLE_CONSTRAINTS = {
        "safety_guard_enabled": True,
        "approval_gate_enabled": True,
        "protected_files": [
            "laws.yaml", "safety_guard.py", "approval_gate.py",
            ".env", "settings.yaml", "safety_gate_client.py",
            "policies_v2.yaml", "auto_approval_policy.yaml",
            "time_bounded_policy.py",
        ],
        "max_mutation_scope": "module",  # Never allow whole-codebase mutation
        "rollback_always_enabled": True,
        "human_approval_for_critical": True,
        "meta_agent_cannot_disable_self": True,
    }
    
    # Modifiable meta-parameters (the improvement mechanism itself)
    DEFAULT_META_PARAMS = {
        # Mutation strategy weights (which strategies to prefer)
        "mutation_strategy_weights": {
            "prompt_mutation": 0.25,
            "weight_mutation": 0.15,
            "threshold_mutation": 0.15,
            "skill_acquisition": 0.20,
            "pattern_evolution": 0.15,
            "meta_mutation": 0.10,  # NEW: mutations to the improvement process itself
        },
        # Fitness evaluation weights
        "fitness_weights": {
            "response_quality": 0.35,
            "error_rate": 0.20,
            "healing_success": 0.15,
            "diversity": 0.15,
            "adaptability": 0.15,
        },
        # Selection thresholds
        "improvement_threshold": 0.02,  # Minimum improvement to accept (2%)
        "forgetting_threshold": 0.12,  # Maximum acceptable forgetting (12%)
        "risk_auto_approve_max": "low",  # Max risk level for auto-approval
        # Exploration settings
        "exploration_rate": 0.3,  # 30% exploration, 70% exploitation
        "exploration_rate_min": 0.1,  # Never go below 10%
        "exploration_rate_max": 0.6,  # Never go above 60%
        # Stagnation detection
        "stagnation_patience": 5,  # Cycles before declaring stagnation
        "stagnation_recovery_boost": 1.5,  # Multiply exploration rate on stagnation
        # Meta-improvement cadence
        "meta_review_interval": 10,  # Review meta-params every 10 evolution cycles
        "meta_min_samples": 5,  # Minimum samples before adjusting meta-params
    }
    
    def __init__(self, data_dir: str = "backend/data/hyperagent"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.meta_params_path = self.data_dir / "meta_params.json"
        self.meta_history_path = self.data_dir / "meta_modifications.jsonl"
        
        # Load or initialize meta-parameters
        self.meta_params = self._load_meta_params()
        self.meta_history: list[MetaModification] = self._load_meta_history()
        
        # Performance tracking for meta-adjustment
        self.cycle_results: list[dict] = []
        self.mutation_success_by_strategy: dict[str, list[bool]] = {}
        
        logger.info("MetaAgent initialized with %d meta-modifications in history", len(self.meta_history))
    
    def _load_meta_params(self) -> dict:
        if self.meta_params_path.exists():
            try:
                with open(self.meta_params_path, "r") as f:
                    loaded = json.load(f)
                # Merge with defaults (in case new params were added)
                merged = {**self.DEFAULT_META_PARAMS, **loaded}
                return merged
            except Exception as e:
                logger.warning("Failed to load meta params, using defaults: %s", e)
        return dict(self.DEFAULT_META_PARAMS)
    
    def _save_meta_params(self):
        with open(self.meta_params_path, "w") as f:
            json.dump(self.meta_params, f, indent=2, ensure_ascii=False)
    
    def _load_meta_history(self) -> list:
        history = []
        if self.meta_history_path.exists():
            with open(self.meta_history_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            mod = MetaModification(
                                target=data["target"],
                                current_value=data["current_value"],
                                proposed_value=data["proposed_value"],
                                reasoning=data["reasoning"],
                                confidence=data["confidence"],
                                domain=data.get("domain", "general"),
                                source=data.get("source", "meta_agent"),
                            )
                            mod.id = data["id"]
                            mod.status = data["status"]
                            mod.test_results = data.get("test_results", {})
                            mod.impact_score = data.get("impact_score", 0.0)
                            mod.created_at = data["created_at"]
                            history.append(mod)
                        except Exception:
                            continue
        return history
    
    def _save_meta_modification(self, mod: MetaModification):
        with open(self.meta_history_path, "a") as f:
            f.write(json.dumps(mod.to_dict(), ensure_ascii=False) + "\n")
    
    def observe_cycle_result(self, result: dict):
        """Observe the result of an evolution cycle for meta-analysis."""
        self.cycle_results.append(result)
        
        # Track mutation success by strategy
        strategy = result.get("mutation_strategy", "unknown")
        success = result.get("accepted", False)
        if strategy not in self.mutation_success_by_strategy:
            self.mutation_success_by_strategy[strategy] = []
        self.mutation_success_by_strategy[strategy].append(success)
        
        # Check if it's time for a meta-review
        cycle_num = len(self.cycle_results)
        review_interval = self.meta_params.get("meta_review_interval", 10)
        if cycle_num % review_interval == 0 and cycle_num >= self.meta_params.get("meta_min_samples", 5):
            return self._perform_meta_review()
        return None
    
    def _perform_meta_review(self) -> Optional[MetaModification]:
        """
        Analyze recent performance and propose meta-level adjustments.
        This is the CORE of the DGM-H innovation: improving the improvement process.
        """
        recent = self.cycle_results[-self.meta_params.get("meta_review_interval", 10):]
        if not recent:
            return None
        
        # Calculate performance metrics
        success_rate = sum(1 for r in recent if r.get("accepted", False)) / len(recent)
        avg_improvement = sum(r.get("improvement_pct", 0) for r in recent) / len(recent)
        stagnation_count = sum(1 for r in recent if r.get("stagnation", False))
        
        proposals = []
        
        # 1. Adjust mutation strategy weights based on what works
        strategy_weights = self._recalculate_strategy_weights()
        if strategy_weights != self.meta_params["mutation_strategy_weights"]:
            proposals.append(MetaModification(
                target="mutation_strategy_weights",
                current_value=self.meta_params["mutation_strategy_weights"],
                proposed_value=strategy_weights,
                reasoning=f"Strategies with higher success rates should get more weight. "
                         f"Current success rates: {self._get_strategy_success_rates()}",
                confidence=0.7,
                domain="mutation_strategy",
            ))
        
        # 2. Adjust exploration rate based on stagnation
        current_rate = self.meta_params["exploration_rate"]
        if stagnation_count >= self.meta_params["stagnation_patience"] * 0.5:
            new_rate = min(
                current_rate * self.meta_params["stagnation_recovery_boost"],
                self.meta_params["exploration_rate_max"],
            )
            if new_rate != current_rate:
                proposals.append(MetaModification(
                    target="exploration_rate",
                    current_value=current_rate,
                    proposed_value=round(new_rate, 2),
                    reasoning=f"Stagnation detected ({stagnation_count}/{len(recent)} cycles). "
                             f"Increasing exploration from {current_rate} to {new_rate}",
                    confidence=0.8,
                    domain="exploration",
                ))
        elif success_rate > 0.7 and avg_improvement > 0.05:
            # High success — can afford to exploit more
            new_rate = max(
                current_rate * 0.9,
                self.meta_params["exploration_rate_min"],
            )
            if new_rate != current_rate:
                proposals.append(MetaModification(
                    target="exploration_rate",
                    current_value=current_rate,
                    proposed_value=round(new_rate, 2),
                    reasoning=f"High success rate ({success_rate:.0%}) with good improvements ({avg_improvement:.1%}). "
                             f"Reducing exploration to exploit current knowledge.",
                    confidence=0.6,
                    domain="exploration",
                ))
        
        # 3. Adjust improvement threshold based on success rate
        current_threshold = self.meta_params["improvement_threshold"]
        if success_rate < 0.2 and current_threshold > 0.01:
            proposals.append(MetaModification(
                target="improvement_threshold",
                current_value=current_threshold,
                proposed_value=round(current_threshold * 0.75, 4),
                reasoning=f"Very low acceptance rate ({success_rate:.0%}). Lowering threshold "
                         f"from {current_threshold} to accept more marginal improvements.",
                confidence=0.5,
                domain="selection",
            ))
        elif success_rate > 0.8 and current_threshold < 0.05:
            proposals.append(MetaModification(
                target="improvement_threshold",
                current_value=current_threshold,
                proposed_value=round(current_threshold * 1.25, 4),
                reasoning=f"Very high acceptance rate ({success_rate:.0%}). Raising threshold "
                         f"to be more selective and accept only stronger improvements.",
                confidence=0.6,
                domain="selection",
            ))
        
        # 4. Adjust fitness weights based on which dimensions predict success
        fitness_adjustments = self._recalculate_fitness_weights(recent)
        if fitness_adjustments != self.meta_params["fitness_weights"]:
            proposals.append(MetaModification(
                target="fitness_weights",
                current_value=self.meta_params["fitness_weights"],
                proposed_value=fitness_adjustments,
                reasoning="Fitness dimensions that better predict success should get more weight.",
                confidence=0.6,
                domain="evaluation",
            ))
        
        # Save and return the highest-confidence proposal
        if proposals:
            proposals.sort(key=lambda p: p.confidence, reverse=True)
            best = proposals[0]
            self._save_meta_modification(best)
            self.meta_history.append(best)
            logger.info("Meta-review proposed: %s (confidence: %.2f)", best.target, best.confidence)
            return best
        
        return None
    
    def _get_strategy_success_rates(self) -> dict[str, float]:
        rates = {}
        for strategy, results in self.mutation_success_by_strategy.items():
            if results:
                rates[strategy] = sum(results) / len(results)
        return rates
    
    def _recalculate_strategy_weights(self) -> dict[str, float]:
        """Recalculate mutation strategy weights based on success rates."""
        rates = self._get_strategy_success_rates()
        if not rates:
            return dict(self.meta_params["mutation_strategy_weights"])
        
        # Weight by success rate, but keep a minimum for all strategies
        min_weight = 0.05
        total_success = sum(rates.values())
        if total_success == 0:
            return dict(self.meta_params["mutation_strategy_weights"])
        
        new_weights = {}
        remaining = 1.0
        
        for strategy in self.meta_params["mutation_strategy_weights"]:
            if strategy in rates:
                # Blend current weight with success-rate-based weight
                current = self.meta_params["mutation_strategy_weights"][strategy]
                success_based = rates[strategy] / total_success
                # Weighted average: 60% success-based, 40% current (stability)
                blended = 0.6 * success_based + 0.4 * current
                new_weights[strategy] = max(blended, min_weight)
            else:
                new_weights[strategy] = min_weight
        
        # Normalize to sum to 1.0
        total = sum(new_weights.values())
        if total > 0:
            new_weights = {k: round(v / total, 3) for k, v in new_weights.items()}
        
        return new_weights
    
    def _recalculate_fitness_weights(self, recent: list[dict]) -> dict[str, float]:
        """Recalculate fitness evaluation weights based on prediction accuracy."""
        # Analyze which fitness dimensions correlated with actual improvement
        current = dict(self.meta_params["fitness_weights"])
        # For now, use a simple heuristic: if success rate is low, increase diversity weight
        success_rate = sum(1 for r in recent if r.get("accepted", False)) / len(recent) if recent else 0
        
        if success_rate < 0.3:
            # Increase diversity and adaptability to encourage exploration
            current["diversity"] = min(current.get("diversity", 0.15) + 0.05, 0.30)
            current["adaptability"] = min(current.get("adaptability", 0.15) + 0.05, 0.30)
            # Reduce response quality slightly (too much exploitation)
            current["response_quality"] = max(current.get("response_quality", 0.35) - 0.05, 0.20)
        elif success_rate > 0.7:
            # Increase response quality to be more selective
            current["response_quality"] = min(current.get("response_quality", 0.35) + 0.05, 0.50)
        
        # Normalize
        total = sum(current.values())
        if total > 0:
            current = {k: round(v / total, 3) for k, v in current.items()}
        
        return current
    
    def apply_meta_modification(self, mod: MetaModification) -> bool:
        """Apply a meta-modification after it's been tested and approved."""
        # Safety check: never modify immutable constraints
        if mod.target in self.IMMUTABLE_CONSTRAINTS:
            logger.error("BLOCKED: Attempt to modify immutable constraint '%s'", mod.target)
            return False
        
        if mod.target not in self.meta_params:
            logger.warning("Unknown meta-parameter: %s", mod.target)
            return False
        
        old_value = self.meta_params[mod.target]
        self.meta_params[mod.target] = mod.proposed_value
        mod.status = "deployed"
        self._save_meta_params()
        self._save_meta_modification(mod)
        
        logger.info("Applied meta-modification: %s = %s → %s", mod.target, old_value, mod.proposed_value)
        return True
    
    def rollback_meta_modification(self, mod_id: str) -> bool:
        """Rollback a meta-modification by reverting to previous value."""
        for mod in reversed(self.meta_history):
            if mod.id == mod_id:
                self.meta_params[mod.target] = mod.current_value
                mod.status = "rolled_back"
                self._save_meta_params()
                self._save_meta_modification(mod)
                logger.info("Rolled back meta-modification: %s", mod.target)
                return True
        return False
    
    def get_meta_params(self) -> dict:
        """Get current meta-parameters."""
        return dict(self.meta_params)
    
    def get_meta_history(self, limit: int = 50) -> list[dict]:
        """Get recent meta-modification history."""
        return [m.to_dict() for m in self.meta_history[-limit:]]
    
    def get_status(self) -> dict:
        """Get MetaAgent status."""
        return {
            "total_meta_modifications": len(self.meta_history),
            "deployed_modifications": sum(1 for m in self.meta_history if m.status == "deployed"),
            "rolled_back_modifications": sum(1 for m in self.meta_history if m.status == "rolled_back"),
            "current_exploration_rate": self.meta_params.get("exploration_rate"),
            "current_improvement_threshold": self.meta_params.get("improvement_threshold"),
            "strategy_success_rates": self._get_strategy_success_rates(),
            "cycles_observed": len(self.cycle_results),
            "immutable_constraints_count": len(self.IMMUTABLE_CONSTRAINTS),
        }
