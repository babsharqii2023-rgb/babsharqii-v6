"""
BABSHARQII v25.0 — Neural Architecture Package
حزمة البنية العصبية الفعلية — أوزان تُعدّل فعلياً وليس مجرد قواعد

This package implements REAL neural networks with:
- NumPy weight matrices that are modified through experience
- Hebbian learning (fire together, wire together)
- Oja's rule (normalized Hebbian to prevent unbounded growth)
- STDP (Spike-Timing-Dependent Plasticity) for temporal learning
- Eligibility traces for credit assignment
- Synaptic consolidation (stronger synapses change slower)
- Persistent storage via SQLite
"""

from mamoun.neural.neural_mesh import NeuralMesh, neural_mesh
from mamoun.neural.hebbian_learner import HebbianLearner
from mamoun.neural.stdp_synapse import STDPSynapse, STDPConfig

__all__ = [
    "NeuralMesh",
    "neural_mesh",
    "HebbianLearner",
    "STDPSynapse",
    "STDPConfig",
]
