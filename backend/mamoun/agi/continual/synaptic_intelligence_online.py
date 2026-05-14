"""
BABSHARQII v10.0 — Synaptic Intelligence Engine
محرك الذكاء المشبكي — يمنع النسيان الكارثي أثناء التعلم المستمر

Implements Synaptic Intelligence (Zenke et al., 2017, 4229 citations):
- Computes parameter importance online during training
- No separate Fisher Information computation phase needed
- More efficient than EWC for online continual learning

Formula:
  Ω_i = Σ_t |∂L/∂θ_i * Δθ_i|  (accumulated over training path)
  SI Loss = L_new + λ * Σ_i Ω_i * (θ_i - θ*_i)²

Target: Catastrophic forgetting after 100 tasks < 10%

Feature Flag: MAMOUN_AUTO_EVOLVE (default: false)
"""

from __future__ import annotations

import os
import json
import time
import math
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

AUTO_EVOLVE_ENABLED: bool = os.environ.get(
    "MAMOUN_AUTO_EVOLVE", "false"
).lower() in ("true", "1", "yes")


@dataclass
class SynapseInfo:
    """معلومات المشبك — أهمية كل معلمة"""
    parameter_id: str = ""
    omega: float = 0.0              # الأهمية المتراكمة
    prev_value_hash: str = ""        # hash القيمة السابقة
    current_value_hash: str = ""     # hash القيمة الحالية
    update_count: int = 0            # عدد التحديثات
    last_updated: float = 0.0

    def to_dict(self) -> dict:
        return {
            "parameter_id": self.parameter_id,
            "omega": round(self.omega, 6),
            "update_count": self.update_count,
            "last_updated": self.last_updated,
        }


@dataclass
class SIReport:
    """تقرير حالة محرك SI"""
    total_synapses: int = 0
    avg_omega: float = 0.0
    max_omega: float = 0.0
    forgetting_estimate: float = 0.0
    tasks_learned: int = 0


class SynapticIntelligenceEngine:
    """
    محرك الذكاء المشبكي
    
    Implements Synaptic Intelligence for continual learning:
    1. Accumulate importance (omega) online during learning
    2. Compute SI penalty for proposed changes
    3. Accept/reject changes based on performance gain vs forgetting
    
    Can work alongside EWC or as a replacement.
    """

    FORGETTING_THRESHOLD = 0.12  # 12%

    def __init__(
        self,
        lambda_si: float = 1.0,
        c_si: float = 0.001,
        persist_path: Optional[str] = None,
    ):
        self.lambda_si = lambda_si
        self.c_si = c_si
        self._synapses: dict[str, SynapseInfo] = {}
        self._task_records: list[dict] = []
        self._persist_path = persist_path
        self._task_counter = 0

    def accumulate_importance(
        self, task_id: str, param_changes: list[dict]
    ) -> int:
        """
        تراكم أهمية المعلمات أثناء التعلم.
        
        Each param_change: {"parameter_id": str, "gradient": float, "delta": float}
        Omega accumulates: Ω_i += |∂L/∂θ_i * Δθ_i|
        """
        if not AUTO_EVOLVE_ENABLED:
            return 0

        count = 0
        for change in param_changes:
            pid = change.get("parameter_id", "")
            gradient = abs(change.get("gradient", 0.0))
            delta = abs(change.get("delta", 0.0))
            importance_contribution = gradient * delta

            if pid in self._synapses:
                syn = self._synapses[pid]
                syn.omega += importance_contribution
                syn.update_count += 1
                syn.current_value_hash = change.get("value_hash", "")
                syn.last_updated = time.time()
            else:
                self._synapses[pid] = SynapseInfo(
                    parameter_id=pid,
                    omega=importance_contribution + self.c_si,
                    prev_value_hash=change.get("prev_hash", ""),
                    current_value_hash=change.get("value_hash", ""),
                    update_count=1,
                    last_updated=time.time(),
                )
            count += 1

        self._task_counter += 1
        self._task_records.append({
            "task_id": task_id,
            "params_updated": count,
            "timestamp": time.time(),
        })

        self._auto_persist()
        return count

    def compute_si_penalty(self, proposed_changes: list[dict]) -> float:
        """
        احسب عقوبة SI لتغييرات مقترحة.
        
        penalty = Σ_i Ω_i * (θ_i_new - θ_i_old)²
        """
        total_penalty = 0.0
        for change in proposed_changes:
            pid = change.get("parameter_id", "")
            new_value = change.get("new_value", 0.0)
            old_value = change.get("old_value", 0.0)

            if pid in self._synapses:
                syn = self._synapses[pid]
                distance = abs(new_value - old_value)
                penalty = syn.omega * distance * distance
                total_penalty += penalty

        return total_penalty * self.lambda_si

    def should_accept_change(
        self, proposed_changes: list[dict], performance_gain: float
    ) -> bool:
        """
        هل نقبل التغيير؟
        
        Accept if: performance_gain > si_penalty * lambda AND forgetting < threshold
        """
        if not AUTO_EVOLVE_ENABLED:
            return False

        penalty = self.compute_si_penalty(proposed_changes)
        forgetting = self.get_forgetting_estimate(proposed_changes)

        accept = performance_gain > penalty and forgetting < self.FORGETTING_THRESHOLD

        logger.info(
            f"SI Decision: gain={performance_gain:.4f}, penalty={penalty:.4f}, "
            f"forgetting={forgetting:.4f}, accept={accept}"
        )

        return accept

    def get_forgetting_estimate(self, proposed_changes: list[dict]) -> float:
        """
        قدّر معدل النسيان لتغييرات مقترحة.
        
        Heuristic: sum of omega * delta for high-omega synapses.
        """
        if not self._synapses:
            return 0.0

        total_omega = sum(s.omega for s in self._synapses.values())
        affected_omega = 0.0

        for change in proposed_changes:
            pid = change.get("parameter_id", "")
            if pid in self._synapses:
                affected_omega += self._synapses[pid].omega

        if total_omega == 0:
            return 0.0

        # Forgetting estimate: ratio of affected importance to total
        forgetting = affected_omega / total_omega

        # Scale by number of tasks learned (more tasks = more risk)
        if self._task_counter > 50:
            forgetting *= 1.5
        elif self._task_counter > 100:
            forgetting *= 2.0

        return min(1.0, forgetting)

    def report(self) -> SIReport:
        """أنشئ تقريراً شاملاً"""
        synapses = list(self._synapses.values())
        avg_omega = sum(s.omega for s in synapses) / len(synapses) if synapses else 0.0
        max_omega = max((s.omega for s in synapses), default=0.0)

        return SIReport(
            total_synapses=len(synapses),
            avg_omega=avg_omega,
            max_omega=max_omega,
            forgetting_estimate=0.0,  # Computed on-demand
            tasks_learned=self._task_counter,
        )

    def _auto_persist(self) -> None:
        if self._persist_path:
            self._save(self._persist_path)

    def _save(self, path: str) -> None:
        data = {
            "synapses": {
                pid: s.to_dict() for pid, s in self._synapses.items()
            },
            "tasks": self._task_records[-100:],  # Last 100
            "config": {
                "lambda_si": self.lambda_si,
                "c_si": self.c_si,
            },
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
