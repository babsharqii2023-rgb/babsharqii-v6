"""
BABSHARQII v18.1 — API Routes (Modular)

Thin aggregator that imports and merges all sub-routers.
v16.0 additions:
  - hyperagent.py  — DGM-H Architecture (MetaAgent, SupraMeta, Archive, Curriculum, FutureSim)
  - awareness.py   — expanded with Mirror and Immune System
  - terminal.py    — Full Agentic Terminal
  - swarm.py       — Swarm Formation Agent
  - a2ui.py        — A2UI Dynamic UI Generation
  - preference.py  — PAHF Preference Learning
  - research.py    — Research Monitor + Epistemic Trust
  - dual_gate.py   — Dual Deliberation Gate
v18.1 additions:
  - v23.py         — Neural Bus, Executor, Self-Healing
  - v24.py         — Inner Monologue, Behavioral Style, World Context, Ideas Generator
  - v25.py         — Neural Layers, Transfer Learning, Long-Term Planning, Causal World Model
  - capabilities.py — Laptop Control, Trading, Instagram, Browser Control
  - agi_pillars.py  — Causal Graph, Episodic Memory, Metacognition, Hierarchical Planning
  - update.py       — GitHub Self-Update System
v22.0 additions:
  - temporal.py    — Temporal Awareness (timeline, patterns, absence, suggestions)
  - predictions.py — Predictive Memory (predictions, verification, patterns)
  - sleep_cycle.py — Sleep Cycle (NREM, REM, recalibration, dreams, compression)
  - events.py      — System Events (recent events, SSE streaming, emit)
v31.0 additions:
  - project_management.py — ProjectRegistry, SmartScheduler, SessionContext, ProjectPool
"""

from fastapi import APIRouter

from mamoun.api.awareness import router as awareness_router
from mamoun.api.evolution import router as evolution_router
from mamoun.api.brains import router as brains_router
from mamoun.api.security import router as security_router
from mamoun.api.admin import router as admin_router
from mamoun.api.embodiment import router as embodiment_router
from mamoun.api.agi import router as agi_router

# v16.0 new routers
from mamoun.api.hyperagent import router as hyperagent_router
from mamoun.api.terminal import router as terminal_router
from mamoun.api.swarm import router as swarm_router
from mamoun.api.a2ui import router as a2ui_router
from mamoun.api.preference import router as preference_router
from mamoun.api.research import router as research_router
from mamoun.api.kernel import router as kernel_router
from mamoun.api.ws import router as ws_router
from mamoun.api.living import router as living_router

# v18.1: Register previously unregistered routers
from mamoun.api.v23 import router as v23_router
from mamoun.api.v24 import router as v24_router
from mamoun.api.v25 import router as v25_router
from mamoun.api.capabilities import router as capabilities_router
from mamoun.api.agi_pillars import router as agi_pillars_router
from mamoun.api.update import router as update_router

# v22.0: Temporal, Predictions, Sleep Cycle, Events
from mamoun.api.temporal import router as temporal_router
from mamoun.api.predictions import router as predictions_router
from mamoun.api.sleep_cycle import router as sleep_cycle_router
from mamoun.api.events import router as events_router

# v31.0: Project Management (Registry, Scheduler, SessionContext, Pool)
from mamoun.api.project_management import router as project_management_router

# v5.0: Dashboard Bridge — fills missing frontend-expected routes
from mamoun.api.dashboard_bridge import router as dashboard_bridge_router

# v38.0: Unified Control Mechanism — 4 layers
from mamoun.api.command_bus import router as command_bus_router
from mamoun.api.feature_flags import router as feature_flags_router
from mamoun.api.event_bridge import router as event_bridge_router
from mamoun.api.brain_control import router as brain_control_router

# v40.0: API Keys Management
from mamoun.api.api_keys import router as api_keys_router

# v40.0: Health Monitor — auto-heal, alerts, brain monitoring
from mamoun.api.health_monitor import router as health_monitor_router

# v40.0 Fusion: File System API + External Controller
from mamoun.api.file_system import router as file_system_router
from mamoun.api.external_controller import router as external_controller_router

# v40.0 Fusion: Brain Status API — fallback warnings and API key diversification
from mamoun.api.brain_status import router as brain_status_router

# v40.0 Fusion: Capability Assessor — self-assessment of system capabilities
from mamoun.api.capability_assessor import router as capability_assessor_router

# v40.0 Fusion Step 8: Continuous Learner — periodic deep research and self-improvement
from mamoun.api.continuous_learner import router as continuous_learner_router

# v40.0 Fusion Step 9: Semantic Router — embedding-based query classification
from mamoun.api.semantic_router import router as semantic_router_api

# v40.0 Fusion Step 10: Predictive Healer — predicts failures before they happen
from mamoun.api.predictive_healer import router as predictive_healer_router

# v40.0 Fusion Step 11: Self-Tester — comprehensive self-testing system
from mamoun.api.self_tester import router as self_tester_router

# v40.0 Fusion Step 12: Unified Mind — single entry point connecting all systems
from mamoun.api.unified_mind import router as unified_mind_router

# v40.0 Fusion Step 3: Auto Research-Heal Loop — connects DeepResearch with SelfHealing
from mamoun.api.auto_research_heal import router as auto_research_heal_router

# v50.0 Fusion: Project Scaffolder + External Project Controller
from mamoun.api.project_scaffold import router as project_scaffold_router
from mamoun.api.external_project import router as external_project_router

api_router = APIRouter()
api_router.include_router(awareness_router)
api_router.include_router(evolution_router)
api_router.include_router(brains_router)
api_router.include_router(security_router)
api_router.include_router(admin_router)
api_router.include_router(embodiment_router)
api_router.include_router(agi_router)

# v16.0
api_router.include_router(hyperagent_router)
api_router.include_router(terminal_router)
api_router.include_router(swarm_router)
api_router.include_router(a2ui_router)
api_router.include_router(preference_router)
api_router.include_router(research_router)
api_router.include_router(kernel_router)

# v17.0: WebSocket for real-time communication
api_router.include_router(ws_router)

# v18.1: Living Systems (heartbeat, vitals, emotions, bonding, identity)
api_router.include_router(living_router)

# v18.1: Previously unregistered routers — +103 endpoints
api_router.include_router(v23_router)
api_router.include_router(v24_router)
api_router.include_router(v25_router)
api_router.include_router(capabilities_router)
api_router.include_router(agi_pillars_router)

# v18.1: GitHub Self-Update system
api_router.include_router(update_router)

# v22.0: Temporal Awareness, Predictive Memory, Sleep Cycle, System Events
api_router.include_router(temporal_router)
api_router.include_router(predictions_router)
api_router.include_router(sleep_cycle_router)
api_router.include_router(events_router)

# v31.0: Project Management — Registry, SmartScheduler, SessionContext, ProjectPool
api_router.include_router(project_management_router)

# v5.0: Dashboard Bridge — fills missing frontend-expected routes
api_router.include_router(dashboard_bridge_router)

# v38.0: Unified Control Mechanism — 4 layers
api_router.include_router(command_bus_router)
api_router.include_router(feature_flags_router)
api_router.include_router(event_bridge_router)
api_router.include_router(brain_control_router)

# v40.0: API Keys Management
api_router.include_router(api_keys_router)

# v40.0: Health Monitor — auto-heal, alerts, brain monitoring
api_router.include_router(health_monitor_router)

# v40.0 Fusion: File System API + External Controller
api_router.include_router(file_system_router)
api_router.include_router(external_controller_router)

# v40.0 Fusion: Brain Status API — fallback warnings and API key diversification
api_router.include_router(brain_status_router)

# v40.0 Fusion: Capability Assessor — self-assessment of system capabilities
api_router.include_router(capability_assessor_router)

# v40.0 Fusion Step 8: Continuous Learner — periodic deep research and self-improvement
api_router.include_router(continuous_learner_router)

# v40.0 Fusion Step 9: Semantic Router — embedding-based query classification
api_router.include_router(semantic_router_api)

# v40.0 Fusion Step 10: Predictive Healer
api_router.include_router(predictive_healer_router)

# v40.0 Fusion Step 11: Self-Tester
api_router.include_router(self_tester_router)

# v40.0 Fusion Step 12: Unified Mind
api_router.include_router(unified_mind_router)

# v40.0 Fusion Step 3: Auto Research-Heal Loop — connects DeepResearch with SelfHealing
api_router.include_router(auto_research_heal_router)

# v50.0 Fusion: Project Scaffolder + External Project Controller
api_router.include_router(project_scaffold_router)
api_router.include_router(external_project_router)
