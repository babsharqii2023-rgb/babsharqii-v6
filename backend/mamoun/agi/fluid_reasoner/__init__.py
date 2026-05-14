# BABSHARQII v10.0 — Fluid Reasoner Package

# Import from the original fluid_reasoner.py module (not this package)
# The original file was renamed to _core.py within this package
import sys
import os

# First, try to import from the package's own modules
from mamoun.agi.fluid_reasoner.counterfactual_simulator import (
    CounterfactualSimulator as CounterfactualSimV9,
    HypothesisType,
    RuleHypothesis,
    CounterfactualResult,
)
from mamoun.agi.fluid_reasoner.arc_adapter import (
    ARCAdapter,
    ARCAdapterConfig,
)

# Import original classes from the old fluid_reasoner module
# The agi/__init__.py imports FluidReasoner, AnalogicalReasoningEngine, etc.
# These come from the ORIGINAL fluid_reasoner.py which is now a .py file
# next to this package directory. We need to handle the import conflict.

# Since this __init__.py IS the fluid_reasoner package, we re-export
# the original module's classes by importing from the file directly
import importlib.util
_orig_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fluid_reasoner.py')
if os.path.exists(_orig_path):
    _spec = importlib.util.spec_from_file_location("mamoun.agi._fluid_reasoner_orig", _orig_path)
    _orig = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_orig)
    FluidReasoner = _orig.FluidReasoner
    AnalogicalReasoningEngine = _orig.AnalogicalReasoningEngine
    PatternCompletionEngine = _orig.PatternCompletionEngine
    CounterfactualSimulator = _orig.CounterfactualSimulator
    AnalogyMatch = _orig.AnalogyMatch
    TransformationRule = _orig.TransformationRule
    FluidReasoningResult = _orig.FluidReasoningResult
    FLUID_REASONER_ENABLED = _orig.FLUID_REASONER_ENABLED
else:
    FluidReasoner = None
    AnalogicalReasoningEngine = None
    PatternCompletionEngine = None
    CounterfactualSimulator = CounterfactualSimV9
    AnalogyMatch = None
    TransformationRule = None
    FluidReasoningResult = None
    FLUID_REASONER_ENABLED = False
