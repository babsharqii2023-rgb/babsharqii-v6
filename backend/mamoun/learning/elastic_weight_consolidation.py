"""
BABSHARQII v29.0-symphony — Elastic Weight Consolidation (تجميد الأوزان المرن)
منع النسيان الكارثي أثناء التعلم المستمر

Based on:
  - Kirkpatrick et al. (2017): "Overcoming catastrophic forgetting in neural networks"
  - EWC computes Fisher information matrix for each task
  - Penalizes changes to important weights during new task learning

Architecture:
  ┌────────────────────────────────────────────┐
  │           ELASTIC WEIGHT CONSOLIDATION      │
  │                                             │
  │  Task 1 → Fisher Matrix 1 → θ*1            │
  │  Task 2 → Fisher Matrix 2 → θ*2            │
  │  ...                                        │
  │  EWC Penalty = Σ λ_i * F_i * (θ - θ*_i)²  │
  └────────────────────────────────────────────┘
"""

import json
import time
import logging
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List, Any

logger = logging.getLogger("mamoun.elastic_weight_consolidation")


class ElasticWeightConsolidation:
    """
    تجميد الأوزان المرن — منع النسيان الكارثي

    Computes Fisher information matrices for learned tasks
    and calculates EWC penalty to prevent catastrophic forgetting.
    """

    def __init__(self, db_path: Optional[Path] = None, lambda_ewc: float = 5000.0):
        self._db_path = db_path or Path("/tmp/mamoun/ewc.json")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lambda = lambda_ewc

        # Storage: task_id → {"fisher": np.array, "params": np.array}
        self._tasks: Dict[str, Dict] = {}
        self._load()

    def compute_fisher(self, task_id: str, params: np.ndarray,
                       data_loader=None, model=None) -> Dict[str, Any]:
        """
        حساب مصفوفة Fisher — Compute Fisher information matrix for a task.

        In a full implementation, this would compute the diagonal of the
        Fisher information matrix using the gradient of the log-likelihood.
        For now, we use a simplified approximation based on parameter magnitudes.

        Args:
            task_id: Unique identifier for the task.
            params: The model parameters after training on this task.
            data_loader: Optional data loader for computing true Fisher.
            model: Optional model for computing true Fisher.

        Returns:
            Dict with task_id and fisher_norm.
        """
        # Simplified Fisher: approximate as |params| (diagonal approximation)
        # In practice, this would be computed from gradients
        fisher = np.abs(params) + 1e-6  # Avoid zero Fisher values

        self._tasks[task_id] = {
            "fisher": fisher.astype(np.float32),
            "params": params.astype(np.float32).copy(),
            "computed_at": time.time(),
        }

        self._save()
        fisher_norm = float(np.linalg.norm(fisher))

        logger.info("Fisher matrix computed for task '%s' — norm: %.4f, params: %d",
                    task_id, fisher_norm, len(params))

        return {
            "task_id": task_id,
            "fisher_norm": fisher_norm,
            "param_count": len(params),
        }

    def ewc_penalty(self, current_params: np.ndarray) -> float:
        """
        عقوبة EWC — Calculate the EWC penalty for current parameters.

        Penalty = Σ_i λ * F_i * (θ - θ*_i)²

        This penalty should be ADDED to the loss function during training
        on new tasks to prevent catastrophic forgetting.

        Args:
            current_params: The current model parameters.

        Returns:
            The EWC penalty value (float).
        """
        if not self._tasks:
            return 0.0

        penalty = 0.0
        for task_id, task_data in self._tasks.items():
            fisher = task_data["fisher"]
            optimal_params = task_data["params"]

            # Ensure shapes match
            min_len = min(len(current_params), len(fisher), len(optimal_params))
            diff = current_params[:min_len] - optimal_params[:min_len]
            penalty += float(self._lambda * np.sum(fisher[:min_len] * diff ** 2))

        return penalty

    def protected_update(self, current_params: np.ndarray,
                         gradient: np.ndarray,
                         learning_rate: float = 0.001) -> np.ndarray:
        """
        تحديث محمي — Update parameters with EWC protection.

        θ_new = θ - lr * (gradient + ewc_penalty_gradient)

        Args:
            current_params: Current parameters.
            gradient: Gradient from the new task.
            learning_rate: Learning rate.

        Returns:
            Updated parameters.
        """
        # Compute EWC gradient contribution
        ewc_grad = np.zeros_like(current_params, dtype=np.float32)
        for task_id, task_data in self._tasks.items():
            fisher = task_data["fisher"]
            optimal = task_data["params"]
            min_len = min(len(current_params), len(fisher), len(optimal))
            ewc_grad[:min_len] += self._lambda * fisher[:min_len] * (current_params[:min_len] - optimal[:min_len])

        # Apply protected update
        new_params = current_params - learning_rate * (gradient + ewc_grad)
        return new_params

    def task_count(self) -> int:
        """عدد المهام المحفوظة"""
        return len(self._tasks)

    def get_task_ids(self) -> List[str]:
        """معرفات المهام"""
        return list(self._tasks.keys())

    def get_stats(self) -> Dict[str, Any]:
        """إحصائيات EWC"""
        return {
            "task_count": len(self._tasks),
            "lambda": self._lambda,
            "task_ids": list(self._tasks.keys()),
        }

    # ═════════════════════════════════════════════════════════════════════════
    #  Persistence
    # ═════════════════════════════════════════════════════════════════════════

    def _save(self):
        """حفظ البيانات"""
        try:
            data = {}
            for task_id, task_data in self._tasks.items():
                data[task_id] = {
                    "fisher": task_data["fisher"].tolist(),
                    "params": task_data["params"].tolist(),
                    "computed_at": task_data.get("computed_at", 0),
                }
            with open(str(self._db_path), "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning("EWC save failed: %s", e)

    def _load(self):
        """تحميل البيانات"""
        try:
            if self._db_path.exists():
                with open(str(self._db_path), "r") as f:
                    data = json.load(f)
                for task_id, task_data in data.items():
                    self._tasks[task_id] = {
                        "fisher": np.array(task_data["fisher"], dtype=np.float32),
                        "params": np.array(task_data["params"], dtype=np.float32),
                        "computed_at": task_data.get("computed_at", 0),
                    }
        except Exception as e:
            logger.warning("EWC load failed: %s", e)


class ExperienceReplay:
    """
    إعادة تشغيل الخبرة — مخزن مؤقت محدود لإعادة التدريب

    Stores experiences and samples them for replay during training
    to prevent catastrophic forgetting.
    """

    def __init__(self, memory_size: int = 10000):
        self._memory_size = memory_size
        self._buffer: List[Dict[str, Any]] = []
        self._position = 0

    def store(self, experience: Dict[str, Any]):
        """
        تخزين خبرة — Store an experience.

        If buffer is full, overwrites the oldest experience (circular buffer).
        """
        if len(self._buffer) < self._memory_size:
            self._buffer.append(experience)
        else:
            self._buffer[self._position] = experience
        self._position = (self._position + 1) % self._memory_size

    def sample(self, n: int) -> List[Dict[str, Any]]:
        """
        أخذ عينة — Sample n experiences randomly.

        Args:
            n: Number of experiences to sample.

        Returns:
            List of sampled experiences.
        """
        if not self._buffer:
            return []

        import random
        n = min(n, len(self._buffer))
        return random.sample(self._buffer, n)

    @property
    def size(self) -> int:
        """حجم المخزن"""
        return len(self._buffer)

    def clear(self):
        """مسح المخزن"""
        self._buffer = []
        self._position = 0

    def get_stats(self) -> Dict[str, Any]:
        """إحصائيات المخزن"""
        return {
            "size": len(self._buffer),
            "capacity": self._memory_size,
            "usage": round(len(self._buffer) / self._memory_size, 3),
        }
