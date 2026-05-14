"""
BABSHARQII v25.0 — STDP Synapse
مشبك STDP — التعلم المعتمد على التوقيت

Spike-Timing-Dependent Plasticity:
- If pre fires BEFORE post → Long-Term Potentiation (LTP) → weight increases
- If post fires BEFORE pre → Long-Term Depression (LTD) → weight decreases
- The closer in time, the stronger the modification

This implements biologically-inspired temporal learning where
the ORDER and TIMING of neural events matters, not just correlation.
"""

import numpy as np
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any

logger = logging.getLogger("mamoun.stdp_synapse")


@dataclass
class STDPConfig:
    """إعدادات STDP"""
    A_plus: float = 0.005      # LTP amplitude
    A_minus: float = 0.004     # LTD amplitude
    tau_plus: float = 0.02     # LTP time constant (seconds)
    tau_minus: float = 0.02    # LTD time constant (seconds)
    weight_max: float = 5.0    # Maximum weight
    weight_min: float = -5.0   # Minimum weight
    consolidation_rate: float = 0.001  # How fast weights consolidate
    eligibility_decay: float = 0.9     # Trace decay rate


@dataclass
class STDPEvent:
    """حدث STDP — تسجيل توقيت إطلاق"""
    neuron_id: str = ""
    timestamp: float = 0.0
    activation: float = 0.0


class STDPSynapse:
    """
    مشبك STDP — التعلم المعتمد على التوقيت الفعلي

    Usage:
        synapse = STDPSynapse(config=STDPConfig())
        
        # Pre fires at t=1.0
        synapse.pre_fire(pre_activation, t=1.0)
        
        # Post fires at t=1.01 (after pre) → LTP
        synapse.post_fire(post_activation, t=1.01, weight_matrix)
        
        # Weight matrix is modified in-place!
    """

    def __init__(self, config: STDPConfig = None):
        self.config = config or STDPConfig()
        self._pre_trace = 0.0     # eligibility trace for pre-synaptic
        self._post_trace = 0.0    # eligibility trace for post-synaptic
        self._last_pre_time = 0.0
        self._last_post_time = 0.0
        self._event_history: List[Dict] = []

    def pre_fire(self, pre_activation: np.ndarray, t: float):
        """
        تسجيل إطلاق قبل المشبكي
        تحديث trace قبل المشبكي
        """
        self._pre_trace = np.mean(pre_activation)
        self._last_pre_time = t

    def post_fire(self, post_activation: np.ndarray, t: float,
                  weight_matrix: np.ndarray, pre_activation: np.ndarray,
                  consolidation: np.ndarray = None) -> Dict[str, Any]:
        """
        تسجيل إطلاق بعد المشبكي + تعديل الأوزان

        If pre fired before post → LTP (strengthen)
        If post fired before pre → LTD (weaken)
        """
        self._post_trace = np.mean(post_activation)
        dt = self._last_pre_time - t  # negative if pre fired before post

        delta = self._compute_stdp_delta(dt, pre_activation, post_activation, weight_matrix)

        # Apply consolidation
        if consolidation is not None:
            effective = 1.0 / (1.0 + consolidation * 10.0)
            delta *= effective

        # Apply in-place
        weight_matrix += delta
        np.clip(weight_matrix, self.config.weight_min, self.config.weight_max, out=weight_matrix)

        self._last_post_time = t

        # Record event
        event = {
            "dt": dt,
            "type": "LTP" if dt < 0 else "LTD",
            "mean_delta": float(np.mean(np.abs(delta))),
            "pre_trace": float(self._pre_trace),
            "post_trace": float(self._post_trace),
        }
        self._event_history.append(event)
        if len(self._event_history) > 100:
            self._event_history = self._event_history[-50:]

        return event

    def _compute_stdp_delta(self, dt: float,
                            pre: np.ndarray, post: np.ndarray,
                            W: np.ndarray) -> np.ndarray:
        """
        حساب تعديل STDP
        Δw = A+ · exp(-|dt|/τ+)  if dt < 0 (pre before post → LTP)
        Δw = -A- · exp(-|dt|/τ-) if dt > 0 (post before pre → LTD)
        """
        if dt < 0:  # Pre before post → LTP
            # dt is negative, |dt| = -dt
            stdp_value = self.config.A_plus * np.exp(dt / self.config.tau_plus)
        else:  # Post before pre → LTD
            stdp_value = -self.config.A_minus * np.exp(-dt / self.config.tau_minus)

        # Only modify connections where both neurons are active
        active_pre = pre > 0.5
        active_post = post > 0.5
        mask = np.outer(active_post.astype(float), active_pre.astype(float))

        delta = stdp_value * mask
        return delta

    def decay_traces(self):
        """اضمحال آثار الأهلية"""
        self._pre_trace *= self.config.eligibility_decay
        self._post_trace *= self.config.eligibility_decay

    def get_event_history(self, limit: int = 20) -> List[Dict]:
        return self._event_history[-limit:]

    def get_stats(self) -> Dict:
        ltp_count = sum(1 for e in self._event_history if e["type"] == "LTP")
        ltd_count = sum(1 for e in self._event_history if e["type"] == "LTD")
        return {
            "total_events": len(self._event_history),
            "ltp_events": ltp_count,
            "ltd_events": ltd_count,
            "pre_trace": float(self._pre_trace),
            "post_trace": float(self._post_trace),
        }
