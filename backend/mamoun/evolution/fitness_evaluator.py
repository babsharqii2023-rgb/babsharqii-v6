"""
BABSHARQII v40.0 — Fitness Evaluator
Evaluates the fitness of a candidate genome against benchmarks.
Measures: response quality, error rate, healing success, diversity, adaptability.
"""

import time
import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FitnessReport:
    """Detailed fitness evaluation report."""
    overall_score: float = 0.0
    response_quality: float = 0.0
    error_rate: float = 0.0
    healing_success_rate: float = 0.0
    diversity_score: float = 0.0
    adaptability_score: float = 0.0
    stability_score: float = 0.0
    improvement_vs_parent: float = 0.0
    meets_threshold: bool = False
    evaluations: int = 0
    benchmark_results: list = field(default_factory=list)
    timestamp: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 2),
            "response_quality": round(self.response_quality, 2),
            "error_rate": round(self.error_rate, 4),
            "healing_success_rate": round(self.healing_success_rate, 4),
            "diversity_score": round(self.diversity_score, 4),
            "adaptability_score": round(self.adaptability_score, 4),
            "stability_score": round(self.stability_score, 4),
            "improvement_vs_parent": round(self.improvement_vs_parent, 4),
            "meets_threshold": self.meets_threshold,
            "evaluations": self.evaluations,
        }


class FitnessEvaluator:
    """
    Evaluates organism fitness using multiple dimensions:
    
    1. Response Quality (35%): Based on pattern success rates and skill levels
    2. Error Rate (20%): Inversely proportional to system stability
    3. Healing Success (15%): How well self-healing works
    4. Diversity (15%): Shannon entropy of routing weights
    5. Adaptability (15%): Number and quality of active skills
    
    Acceptance rule: improvement >= 2% with stability and safety maintained.
    Diversity rule: if improvement < 0.5% for 3 nights, increase mutation entropy.
    """
    
    def __init__(
        self,
        fitness_threshold: float = 0.02,  # 2% improvement required
        diversity_floor: float = 0.3,
        stagnation_threshold: int = 3,
        benchmark_size: int = 150,
    ):
        self.fitness_threshold = fitness_threshold
        self.diversity_floor = diversity_floor
        self.stagnation_threshold = stagnation_threshold
        self.benchmark_size = benchmark_size
        
        self._session_errors = 0
        self._session_interactions = 0
        self._session_healing_attempts = 0
        self._session_healing_successes = 0
    
    def evaluate(self, candidate_genome: dict, parent_fitness: float = 0.0) -> FitnessReport:
        """
        Evaluate a candidate genome's fitness.
        This computes all fitness dimensions and returns a detailed report.
        """
        report = FitnessReport(timestamp=time.time())
        
        # 1. Response Quality (35%)
        report.response_quality = self._compute_response_quality(candidate_genome)
        
        # 2. Error Rate (20%)
        report.error_rate = self._compute_error_rate()
        
        # 3. Healing Success Rate (15%)
        report.healing_success_rate = self._compute_healing_success()
        
        # 4. Diversity Score (15%)
        report.diversity_score = self._compute_diversity(candidate_genome)
        
        # 5. Adaptability Score (15%)
        report.adaptability_score = self._compute_adaptability(candidate_genome)
        
        # 6. Stability Score (bonus/penalty)
        report.stability_score = self._compute_stability(candidate_genome)
        
        # Overall weighted score
        report.overall_score = (
            report.response_quality * 0.35 +
            (1 - report.error_rate) * 100 * 0.20 +
            report.healing_success_rate * 100 * 0.15 +
            report.diversity_score * 100 * 0.15 +
            report.adaptability_score * 100 * 0.15
        )
        
        # Apply stability modifier
        if report.stability_score < 0.5:
            report.overall_score *= 0.8  # Significant penalty for instability
        
        report.overall_score = max(0, min(100, report.overall_score))
        
        # Improvement vs parent
        if parent_fitness > 0:
            report.improvement_vs_parent = (report.overall_score - parent_fitness) / parent_fitness
        
        # Threshold check
        report.meets_threshold = report.improvement_vs_parent >= self.fitness_threshold
        
        return report
    
    def _compute_response_quality(self, genome: dict) -> float:
        """Compute response quality from pattern success rates and skill levels."""
        patterns = genome.get("response_patterns", [])
        skills = genome.get("skill_definitions", [])
        
        # Pattern quality
        if patterns:
            avg_pattern_success = sum(p.get("success_rate", 0.5) for p in patterns) / len(patterns)
        else:
            avg_pattern_success = 0.5
        
        # Skill quality
        if skills:
            avg_skill_level = sum(s.get("level", 50) for s in skills) / len(skills)
        else:
            avg_skill_level = 50
        
        return (avg_pattern_success * 50) + (avg_skill_level / 100 * 50)
    
    def _compute_error_rate(self) -> float:
        """Compute error rate from session statistics."""
        if self._session_interactions == 0:
            return 0.05  # Default low error rate
        return min(1.0, self._session_errors / max(1, self._session_interactions))
    
    def _compute_healing_success(self) -> float:
        """Compute healing success rate."""
        if self._session_healing_attempts == 0:
            return 0.8  # Default
        return self._session_healing_successes / self._session_healing_attempts
    
    def _compute_diversity(self, genome: dict) -> float:
        """
        Compute diversity using Shannon entropy of routing weights.
        Maximum entropy = equal weights (log2(N)).
        """
        weights = list(genome.get("routing_weights", {}).values())
        if len(weights) < 2:
            return 0.0
        
        total = sum(weights)
        if total == 0:
            return 0.0
        
        probs = [w / total for w in weights]
        entropy = -sum(p * math.log2(p) for p in probs if p > 0)
        max_entropy = math.log2(len(weights))
        
        return entropy / max_entropy if max_entropy > 0 else 0.0
    
    def _compute_adaptability(self, genome: dict) -> float:
        """Compute adaptability from active skills and their levels."""
        skills = genome.get("skill_definitions", [])
        active_skills = [s for s in skills if s.get("level", 0) > 10]
        
        if not active_skills:
            return 0.1
        
        skill_count_score = min(1.0, len(active_skills) * 0.08)
        avg_success = sum(s.get("success_rate", 0.5) for s in active_skills) / len(active_skills)
        
        return min(1.0, skill_count_score + avg_success * 0.3)
    
    def _compute_stability(self, genome: dict) -> float:
        """Compute stability score — checks if genome is well-formed."""
        score = 1.0
        
        # Check weights sum to ~1
        weights = list(genome.get("routing_weights", {}).values())
        if weights:
            total = sum(weights)
            if abs(total - 1.0) > 0.1:
                score *= 0.5
        
        # Check no weight is zero
        if any(w <= 0 for w in weights):
            score *= 0.7
        
        # Check instinct thresholds are reasonable
        thresholds = genome.get("instinct_thresholds", {})
        for inst_id, thresh in thresholds.items():
            trigger = thresh.get("trigger_at", 50) if isinstance(thresh, dict) else 50
            if trigger < 5 or trigger > 95:
                score *= 0.8
        
        return score
    
    # =========================================================================
    # Session Tracking
    # =========================================================================
    
    def record_interaction(self):
        self._session_interactions += 1
    
    def record_error(self):
        self._session_errors += 1
    
    def record_healing_attempt(self, success: bool):
        self._session_healing_attempts += 1
        if success:
            self._session_healing_successes += 1
    
    def reset_session(self):
        self._session_errors = 0
        self._session_interactions = 0
        self._session_healing_attempts = 0
        self._session_healing_successes = 0
