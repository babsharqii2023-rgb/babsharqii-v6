"""
BABSHARQII v26.0 — Reasoning Module
وحدة الاستدلال — 7 ركائز استدلال جديدة بدون LLM
"""

from mamoun.reasoning.symbolic_reasoner import SymbolicReasoner, get_symbolic_reasoner
from mamoun.reasoning.bayesian_inference import BayesianInferenceEngine, get_bayesian_engine
from mamoun.reasoning.reinforcement_learning import ReinforcementLearningEngine, get_rl_engine
from mamoun.reasoning.abstract_generalization import AbstractGeneralizationEngine, get_abstract_generalization
from mamoun.reasoning.perception_action_loop import PerceptionActionLoop, get_pal_engine
from mamoun.reasoning.dynamic_working_memory import DynamicWorkingMemory, get_dynamic_working_memory
from mamoun.reasoning.continual_learning import ContinualLearningEngine, get_continual_learning

__all__ = [
    "SymbolicReasoner", "get_symbolic_reasoner",
    "BayesianInferenceEngine", "get_bayesian_engine",
    "ReinforcementLearningEngine", "get_rl_engine",
    "AbstractGeneralizationEngine", "get_abstract_generalization",
    "PerceptionActionLoop", "get_pal_engine",
    "DynamicWorkingMemory", "get_dynamic_working_memory",
    "ContinualLearningEngine", "get_continual_learning",
]
