"""
BABSHARQII v40.0 — Metacognitive Analyzer
Analyzes confidence distributions, detects bias, and proposes reweighting.
Implements MERRCURR-style frozen model separation for self-awareness.
"""

import time
import math
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict


@dataclass
class ConfidenceCalibration:
    """Tracks how well the organism's confidence matches reality."""
    predicted: float = 0.0
    actual: float = 0.0
    calibration_error: float = 0.0
    timestamp: float = 0.0


@dataclass
class BrainBiasReport:
    """Report on brain dominance/bias."""
    dominant_brain: str = ""
    dominant_weight: float = 0.0
    dominance_ratio: float = 0.0  # How much the dominant brain exceeds fair share
    is_biased: bool = False
    recommendation: str = ""
    brain_weights: dict = field(default_factory=dict)
    entropy: float = 0.0  # Shannon entropy of weights


@dataclass
class DeliberationBiasReport:
    """Report on deliberation/voting bias."""
    brain_agreement_rate: float = 0.0
    neural_win_rate: float = 0.0  # How often Neural brain wins
    consensus_diversity: float = 0.0
    voting_patterns: dict = field(default_factory=dict)
    is_biased: bool = False
    recommendation: str = ""


@dataclass 
class MetacognitiveAssessment:
    """Full metacognitive assessment of the organism."""
    system1_confidence: float = 0.0
    system2_confidence: float = 0.0
    calibration_error: float = 0.0
    brain_bias: Optional[BrainBiasReport] = None
    deliberation_bias: Optional[DeliberationBiasReport] = None
    overall_self_awareness: float = 0.0  # 0-1
    recommendations: list = field(default_factory=list)
    timestamp: float = 0.0


class MetaAnalyzer:
    """
    Metacognitive Analyzer — the organism's self-awareness about its own cognition.
    
    Implements:
    1. Confidence calibration tracking (are we right about how right we are?)
    2. Brain bias detection (is one brain dominating?)
    3. Deliberation bias detection (are voting patterns skewed?)
    4. MERRCURR-style separation: compares a "frozen" reference model's behavior
       with the current model's behavior to detect drift and self-awareness.
    """
    
    def __init__(self):
        self._calibrations: list[ConfidenceCalibration] = []
        self._brain_weight_history: list[dict] = []
        self._deliberation_history: list[dict] = []
        self._frozen_genome: Optional[dict] = None  # Reference genome
        
        self._max_calibrations = 1000
        self._max_weight_history = 500
        self._max_deliberation_history = 500
    
    # =========================================================================
    # Confidence Calibration
    # =========================================================================
    
    def record_calibration(self, predicted_confidence: float, actual_outcome: float):
        """
        Record a calibration point.
        predicted_confidence: 0-1, how confident was the organism
        actual_outcome: 0-1, did it succeed? (1 = perfect, 0 = total failure)
        """
        error = abs(predicted_confidence - actual_outcome)
        calibration = ConfidenceCalibration(
            predicted=predicted_confidence,
            actual=actual_outcome,
            calibration_error=error,
            timestamp=time.time(),
        )
        self._calibrations.append(calibration)
        if len(self._calibrations) > self._max_calibrations:
            self._calibrations = self._calibrations[-self._max_calibrations:]
    
    def get_calibration_error(self) -> float:
        """
        Compute the average calibration error.
        Lower is better — 0 means perfect self-knowledge.
        """
        if not self._calibrations:
            return 0.5  # Unknown
        
        recent = self._calibrations[-100:]
        return sum(c.calibration_error for c in recent) / len(recent)
    
    def get_confidence_reliability(self) -> float:
        """
        How reliable is the organism's confidence signal?
        Returns 0-1 where 1 = perfectly calibrated.
        """
        return 1.0 - self.get_calibration_error()
    
    # =========================================================================
    # Brain Bias Detection
    # =========================================================================
    
    def record_brain_weights(self, weights: dict):
        """Record current brain routing weights."""
        self._brain_weight_history.append({
            "weights": dict(weights),
            "timestamp": time.time(),
        })
        if len(self._brain_weight_history) > self._max_weight_history:
            self._brain_weight_history = self._brain_weight_history[-self._max_weight_history:]
    
    def detect_brain_bias(self, current_weights: dict) -> BrainBiasReport:
        """
        Detect if one brain is dominating the routing.
        Uses Shannon entropy to measure how balanced the distribution is.
        """
        if not current_weights:
            return BrainBiasReport()
        
        weights = list(current_weights.values())
        total = sum(weights)
        if total == 0:
            return BrainBiasReport(brain_weights=current_weights)
        
        # Normalize
        probs = [w / total for w in weights]
        
        # Shannon entropy
        entropy = -sum(p * math.log2(p) for p in probs if p > 0)
        max_entropy = math.log2(len(probs)) if len(probs) > 1 else 1.0
        
        # Find dominant brain
        dominant_brain = max(current_weights, key=current_weights.get)
        dominant_weight = current_weights[dominant_brain]
        fair_share = 1.0 / len(current_weights)
        dominance_ratio = dominant_weight / fair_share if fair_share > 0 else 1.0
        
        # Bias threshold: dominance ratio > 1.5 or entropy < 80% of max
        is_biased = dominance_ratio > 1.5 or (max_entropy > 0 and entropy / max_entropy < 0.8)
        
        # Generate recommendation
        recommendation = ""
        if is_biased:
            if dominance_ratio > 2.0:
                recommendation = (
                    f"تحذير هيمنة شديدة: الدماغ {dominant_brain} يسيطر بنسبة "
                    f"{dominant_weight:.1%} (المفروض {fair_share:.1%}). "
                    f"يُنصح بتخفيض وزنه تدريجياً وزيادة أوزان الأدمغة الأضعف."
                )
            else:
                recommendation = (
                    f"تحيز طفيف: الدماغ {dominant_brain} يسيطر بنسبة "
                    f"{dominant_weight:.1%}. يُنصح بإعادة التوازن."
                )
        
        return BrainBiasReport(
            dominant_brain=dominant_brain,
            dominant_weight=dominant_weight,
            dominance_ratio=dominance_ratio,
            is_biased=is_biased,
            recommendation=recommendation,
            brain_weights=dict(current_weights),
            entropy=entropy,
        )
    
    # =========================================================================
    # Deliberation Bias Detection
    # =========================================================================
    
    def record_deliberation(self, brain_stances: dict, winner: str):
        """
        Record a deliberation result.
        brain_stances: {brain_id: stance} where stance is 'support'/'oppose'/'neutral'
        winner: the winning stance
        """
        self._deliberation_history.append({
            "stances": dict(brain_stances),
            "winner": winner,
            "timestamp": time.time(),
        })
        if len(self._deliberation_history) > self._max_deliberation_history:
            self._deliberation_history = self._deliberation_history[-self._max_deliberation_history:]
    
    def detect_deliberation_bias(self) -> DeliberationBiasReport:
        """Detect bias in deliberation patterns."""
        if len(self._deliberation_history) < 5:
            return DeliberationBiasReport()
        
        recent = self._deliberation_history[-100:]
        
        # Track how often each brain supports vs opposes
        brain_support_rates = defaultdict(lambda: {"support": 0, "oppose": 0, "neutral": 0, "total": 0})
        winner_counts = defaultdict(int)
        
        for entry in recent:
            stances = entry.get("stances", {})
            winner = entry.get("winner", "")
            winner_counts[winner] += 1
            
            for brain_id, stance in stances.items():
                brain_support_rates[brain_id][stance] += 1
                brain_support_rates[brain_id]["total"] += 1
        
        # Calculate agreement rate
        total_agreements = 0
        total_deliberations = len(recent)
        for entry in recent:
            stances = list(entry.get("stances", {}).values())
            if len(set(stances)) == 1:
                total_agreements += 1
        
        agreement_rate = total_agreements / total_deliberations if total_deliberations > 0 else 0
        
        # Calculate Neural win rate
        neural_wins = winner_counts.get("support", 0)  # proxy
        total_wins = sum(winner_counts.values()) or 1
        
        # Calculate diversity (entropy of stances)
        stance_counts = defaultdict(int)
        for entry in recent:
            for stance in entry.get("stances", {}).values():
                stance_counts[stance] += 1
        
        total_stances = sum(stance_counts.values()) or 1
        stance_probs = [c / total_stances for c in stance_counts.values()]
        diversity = -sum(p * math.log2(p) for p in stance_probs if p > 0)
        max_diversity = math.log2(3) if len(stance_counts) > 1 else 1.0  # 3 possible stances
        consensus_diversity = diversity / max_diversity if max_diversity > 0 else 0
        
        # Bias detection
        is_biased = agreement_rate > 0.9 or consensus_diversity < 0.3
        
        recommendation = ""
        if is_biased:
            if agreement_rate > 0.9:
                recommendation = "معدل اتفاق مرتفع جداً — الأدمغة لا تتنوع في آرائها. يُنصح بزيادة diversity عن طريق تعديل prompts."
            if consensus_diversity < 0.3:
                recommendation += " تنوع المداولة منخفض — يحتمل تحيز في الاستجابات."
        
        return DeliberationBiasReport(
            brain_agreement_rate=agreement_rate,
            neural_win_rate=neural_wins / total_wins,
            consensus_diversity=consensus_diversity,
            voting_patterns=dict(brain_support_rates),
            is_biased=is_biased,
            recommendation=recommendation,
        )
    
    # =========================================================================
    # MERRCURR-Style Frozen Model Comparison
    # =========================================================================
    
    def set_frozen_genome(self, genome: dict):
        """
        Set a reference "frozen" genome — a snapshot of the organism's
        configuration at a known-good point. This is the MERRCURR concept:
        comparing the organism's current behavior against a frozen reference
        to detect drift and self-awareness gaps.
        """
        import json
        self._frozen_genome = json.loads(json.dumps(genome))  # Deep copy
    
    def compare_with_frozen(self, current_genome: dict) -> dict:
        """
        Compare the current genome with the frozen reference.
        Returns a drift report showing what has changed and how much.
        """
        if not self._frozen_genome:
            return {"status": "no_frozen_reference", "drift": 0.0}
        
        drift_report = {
            "status": "compared",
            "total_drift": 0.0,
            "changed_fields": [],
            "unchanged_fields": [],
        }
        
        # Compare routing weights
        frozen_weights = self._frozen_genome.get("routingWeights", {})
        current_weights = current_genome.get("routingWeights", {})
        
        for key in set(list(frozen_weights.keys()) + list(current_weights.keys())):
            frozen_val = frozen_weights.get(key, 0)
            current_val = current_weights.get(key, 0)
            diff = abs(current_val - frozen_val)
            if diff > 0.01:
                drift_report["changed_fields"].append({
                    "field": f"routingWeights.{key}",
                    "frozen": frozen_val,
                    "current": current_val,
                    "drift": diff,
                })
                drift_report["total_drift"] += diff
            else:
                drift_report["unchanged_fields"].append(f"routingWeights.{key}")
        
        # Compare instinct thresholds
        frozen_thresholds = self._frozen_genome.get("instinctThresholds", {})
        current_thresholds = current_genome.get("instinctThresholds", {})
        
        for key in set(list(frozen_thresholds.keys()) + list(current_thresholds.keys())):
            frozen_val = frozen_thresholds.get(key, {}).get("triggerAt", 0)
            current_val = current_thresholds.get(key, {}).get("triggerAt", 0)
            diff = abs(current_val - frozen_val)
            if diff > 1:
                drift_report["changed_fields"].append({
                    "field": f"instinctThresholds.{key}.triggerAt",
                    "frozen": frozen_val,
                    "current": current_val,
                    "drift": diff / 100,  # Normalize
                })
                drift_report["total_drift"] += diff / 100
        
        return drift_report
    
    # =========================================================================
    # Full Assessment
    # =========================================================================
    
    def assess(self, current_weights: dict, vitality: float = 50.0) -> MetacognitiveAssessment:
        """
        Perform a full metacognitive assessment.
        """
        # System 1: Fast heuristic confidence
        calibration_error = self.get_calibration_error()
        system1_confidence = max(0, 1.0 - calibration_error) * (vitality / 100.0)
        
        # Brain bias
        brain_bias = self.detect_brain_bias(current_weights) if current_weights else None
        
        # Deliberation bias
        deliberation_bias = self.detect_deliberation_bias()
        
        # System 2: Deep analysis
        system2_confidence = system1_confidence
        if brain_bias and brain_bias.is_biased:
            system2_confidence *= 0.8  # Lower confidence if biased
        
        # Overall self-awareness
        awareness = system2_confidence * self.get_confidence_reliability()
        
        # Recommendations
        recommendations = []
        if brain_bias and brain_bias.is_biased:
            recommendations.append(brain_bias.recommendation)
        if deliberation_bias and deliberation_bias.is_biased:
            recommendations.append(deliberation_bias.recommendation)
        if calibration_error > 0.3:
            recommendations.append(
                "خطأ المعايرة مرتفع — الثقة لا تتطابق مع الأداء الفعلي. "
                "يُنصح بزيادة التأمل الذاتي وتسجيل المزيد من نقاط المعايرة."
            )
        
        return MetacognitiveAssessment(
            system1_confidence=system1_confidence,
            system2_confidence=system2_confidence,
            calibration_error=calibration_error,
            brain_bias=brain_bias,
            deliberation_bias=deliberation_bias,
            overall_self_awareness=awareness,
            recommendations=recommendations,
            timestamp=time.time(),
        )
