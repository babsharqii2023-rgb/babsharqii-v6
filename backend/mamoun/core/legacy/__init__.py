"""
BABSHARQII v61 — Legacy Core Modules

This directory contains the OLD implementations (v18-v40) that have been
superseded by the new super_brain/ and shared/ implementations.

These files are kept for REFERENCE ONLY and should NOT be imported
by any production or test code. All imports should go through the
backward-compatible adapters in core/ (which delegate to super_brain/).

Files moved here:
- llm_client.py (v35) → replaced by shared/multi_provider_llm.py
- mamoun_kernel.py (v18) → replaced by super_brain/mamoun_kernel.py
- neural_bus.py (v30) → replaced by shared/neural_bus.py
- self_modifier.py (v18) → replaced by super_brain/self_modifier.py
- self_healing.py (v23) → replaced by super_brain/self_healing_bridge.py
- metacognitive_engine.py (v24) → replaced by super_brain/meta_cognition_engine.py
- improvement_engine.py (v24) → replaced by super_brain/improvement_proposer.py
- deep_research_engine.py (v40) → replaced by super_brain/deep_research_engine.py
- external_project_controller.py (v40) → replaced by super_brain/external_project_controller.py
- web_search_client.py (v40) → replaced by super_brain/web_search_client.py
- experiential_rlhf.py (v58) → replaced by super_brain/rlhf_bridge.py

Rule: Do NOT add new modules here. All new development goes to super_brain/ or shared/.
"""

import warnings

warnings.warn(
    "mamoun.core.legacy is deprecated. Use mamoun.core.super_brain or mamoun.core.shared instead.",
    DeprecationWarning,
    stacklevel=2,
)
