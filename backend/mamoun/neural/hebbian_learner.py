"""
BABSHARQII v25.0 — Hebbian Learner
متعلم هيبي — قواعد التعلم العصبية الفعلية

Implements multiple Hebbian learning rules:
1. Classic Hebb: Δw = η · x · y (fire together, wire together)
2. Oja's Rule: Δw = η · y · (x - β · y · w) (normalized)
3. Generalized Hebb: Δw = η · (y - θ) · (x - μ) (with thresholds)
4. Covariance Rule: Δw = η · (y - ȳ) · (x - x̄) (zero-mean)

Each rule modifies ACTUAL weight values in the NeuralMesh.
"""

import numpy as np
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum

logger = logging.getLogger("mamoun.hebbian_learner")


class LearningRule(str, Enum):
    CLASSIC = "classic_hebb"
    OJA = "oja_rule"
    GENERALIZED = "generalized_hebb"
    COVARIANCE = "covariance_rule"


@dataclass
class LearningConfig:
    """إعدادات التعلم"""
    rule: str = LearningRule.OJA.value
    learning_rate: float = 0.01
    oja_beta: float = 0.01
    pre_threshold: float = 0.0   # θ for generalized Hebb
    post_threshold: float = 0.0  # μ for generalized Hebb
    weight_decay: float = 0.0001
    max_weight: float = 5.0
    min_weight: float = -5.0


@dataclass
class LearningResult:
    """نتيجة خطوة تعلم"""
    weight_updates: int = 0
    mean_delta: float = 0.0
    max_delta: float = 0.0
    pre_activation_norm: float = 0.0
    post_activation_norm: float = 0.0
    weight_sparsity: float = 0.0


class HebbianLearner:
    """
    متعلم هيبي — يُعدّل الأوزان فعلياً

    Usage:
        learner = HebbianLearner(config=LearningConfig(rule="oja_rule"))
        result = learner.learn(weight_matrix, pre_activation, post_activation)
        # weight_matrix is modified in-place!
    """

    def __init__(self, config: LearningConfig = None):
        self.config = config or LearningConfig()
        self._running_mean_pre = 0.0
        self._running_mean_post = 0.0
        self._step_count = 0

    def learn(self, weight_matrix: np.ndarray,
              pre_activation: np.ndarray,
              post_activation: np.ndarray,
              consolidation: np.ndarray = None,
              config: LearningConfig = None) -> LearningResult:
        """
        تطبيق قاعدة التعلم — الأوزان تُعدّل فعلياً في weight_matrix

        Args:
            weight_matrix: (output_size, input_size) — يُعدّل في المكان
            pre_activation: (input_size,) — تنشيط الطبقة السابقة
            post_activation: (output_size,) — تنشيط الطبقة الحالية
            consolidation: (output_size, input_size) — قوة التثبيت
            config: إعدادات بديلة (اختياري)
        """
        cfg = config or self.config
        x = np.array(pre_activation, dtype=np.float64)
        y = np.array(post_activation, dtype=np.float64)
        W = weight_matrix

        # Compute weight delta based on rule
        if cfg.rule == LearningRule.CLASSIC.value:
            # Δw = η · y · x^T
            delta = cfg.learning_rate * np.outer(y, x)

        elif cfg.rule == LearningRule.OJA.value:
            # Δw = η * (y * x^T - β * y^2 * W)  [Oja's rule]
            delta = cfg.learning_rate * (
                np.outer(y, x) - cfg.oja_beta * np.outer(y, y) @ W
            )

        elif cfg.rule == LearningRule.GENERALIZED.value:
            # Δw = η · (y - θ) · (x - μ)^T
            delta = cfg.learning_rate * np.outer(
                y - cfg.post_threshold, x - cfg.pre_threshold
            )

        elif cfg.rule == LearningRule.COVARIANCE.value:
            # Δw = η · (y - ȳ) · (x - x̄)^T
            # Update running means
            alpha = 0.01
            self._running_mean_pre = (1 - alpha) * self._running_mean_pre + alpha * np.mean(x)
            self._running_mean_post = (1 - alpha) * self._running_mean_post + alpha * np.mean(y)
            delta = cfg.learning_rate * np.outer(
                y - self._running_mean_post,
                x - self._running_mean_pre
            )
        else:
            delta = np.zeros_like(W)

        # Apply consolidation mask (well-established weights change slower)
        if consolidation is not None:
            effective_rate = 1.0 / (1.0 + consolidation * 10.0)
            delta *= effective_rate

        # Apply weight decay
        delta -= cfg.weight_decay * W

        # Clip delta to prevent explosion
        delta = np.clip(delta, -0.1, 0.1)

        # Apply update in-place
        W += delta

        # Clip weights to range
        np.clip(W, cfg.min_weight, cfg.max_weight, out=W)

        self._step_count += 1

        return LearningResult(
            weight_updates=int(np.sum(np.abs(delta) > 1e-8)),
            mean_delta=float(np.mean(np.abs(delta))),
            max_delta=float(np.max(np.abs(delta))),
            pre_activation_norm=float(np.linalg.norm(x)),
            post_activation_norm=float(np.linalg.norm(y)),
            weight_sparsity=float(np.sum(np.abs(W) < 0.01) / W.size),
        )

    def compute_importance(self, weight_matrix: np.ndarray,
                           trace_matrix: np.ndarray) -> np.ndarray:
        """
        حساب أهمية كل وزن (لـ Synaptic Intelligence)
        Ω_i = Σ |Δw_i| عبر الخطوات

        الأوزان التي تغيرت كثيراً هي الأكثر أهمية
        """
        # Importance = accumulated absolute weight changes
        omega = trace_matrix.copy()
        # Normalize by update count to get average importance
        if self._step_count > 0:
            omega /= self._step_count
        return omega

    def compute_si_penalty(self, weight_matrix: np.ndarray,
                           optimal_weights: np.ndarray,
                           omega: np.ndarray,
                           lambda_si: float = 1.0) -> float:
        """
        حساب عقاب Synaptic Intelligence
        L_SI = λ · Σ Ω_i · (w_i - w*_i)²

        هذا يمنع النسيان الكارثي — الأوزان المهمة لا تتغير كثيراً
        """
        diff = weight_matrix - optimal_weights
        penalty = lambda_si * np.sum(omega * diff ** 2)
        return float(penalty)

    def get_config(self) -> Dict:
        return {
            "rule": self.config.rule,
            "learning_rate": self.config.learning_rate,
            "oja_beta": self.config.oja_beta,
            "step_count": self._step_count,
            "running_mean_pre": self._running_mean_pre,
            "running_mean_post": self._running_mean_post,
        }
