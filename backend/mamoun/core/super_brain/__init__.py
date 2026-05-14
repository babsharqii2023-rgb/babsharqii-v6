"""
Super Brain v59.2 — Core components package for العقل الخارق مامون.

Stage 1 (v59.1) Components:
- MetaCognitionEngine: Real self-awareness through actual measurement
- SelfHealingBridge: Bridges SelfHealing ↔ MetaCognition ↔ NeuralBus
- RLHFBridge: Bridges ExperientialRLHF ↔ ImprovementProposer
- OutcomeRecorder: Decorator/context manager for automatic outcome recording

Stage 2 (v59.2) Components:
- VariantArchive: DGM-inspired code variant archive with fitness tracking
- NotificationEngine: NeuralBus-powered alert system with rate limiting
- AgentLifecycleManager: Full lifecycle management for autonomous agents
- ImprovementProposer: Data-driven improvement proposals with SelfModifier integration

Additional Components:
- EvolutionLoopV2: Coordinated self-improvement loop
- HealthMonitor: Comprehensive health monitoring (v61)
- HealthDashboard: Health visualization dashboard (v60)
- MamounKernel: Consciousness loop core (moved to super_brain path)
- SelfModifier: Safe self-modification pipeline
- FullSelfRewriter: Full self-rewriting capability
- BrainRouter: Brain routing system
- AgentCreator: Agent creation factory (AgentFactory-inspired)
- ToolCreator: Tool creation system
- DeepResearchEngine: Deep research capability
- DeliberationRoom: Multi-brain deliberation
- WebSearchClient: Web search integration
- ResearchToUpdatePipeline: Research to code update pipeline
- CognitiveFeedbackLoop: Cognitive feedback system
- SelfAuditEngine: Self-auditing capability
"""

from .meta_cognition_engine import (
    OutcomeRecord,
    ComponentProfile,
    MetaCognitionEngine,
)

from .outcome_recorder import (
    OutcomeRecorder,
    record_outcome,
)

from .self_healing_bridge import (
    HealingAction,
    HealingResultStatus,
    HealingResult,
    SelfHealingBridge,
)

from .rlhf_bridge import (
    FeedbackType,
    RLHFPattern,
    FeedbackRecord,
    ImprovementSuggestion,
    RLHFBridge,
)

from .variant_archive import (
    VariantStatus,
    CodeVariant,
    VariantArchive,
)

from .notification_engine import (
    NotificationLevel,
    NotificationChannel,
    Notification,
    NotificationEngine,
)

from .agent_lifecycle_manager import (
    AgentLifecycleState,
    AgentRecord,
    AgentLifecycleManager,
)

from .improvement_proposer import (
    ProposalPriority,
    ProposalStatus,
    ImprovementProposal,
    FeatureFlags,
    ImprovementProposer,
)

from .evolution_loop_v2 import (
    EvolutionStatus,
    EvolutionCycleResult,
    EvolutionLoopV2,
)

from .health_monitor import (
    AlertSeverity,
    ComponentHealthScore,
    SystemHealthReport,
    HealthMonitor,
)

from .health_dashboard import (
    HealthLevel,
    ComponentHealthCard,
    SystemHealthSummary,
    HealthDashboard,
)

__all__ = [
    # Stage 1 (v59.1)
    "OutcomeRecord",
    "ComponentProfile",
    "MetaCognitionEngine",
    "OutcomeRecorder",
    "record_outcome",
    "HealingAction",
    "HealingResultStatus",
    "HealingResult",
    "SelfHealingBridge",
    "FeedbackType",
    "RLHFPattern",
    "FeedbackRecord",
    "ImprovementSuggestion",
    "RLHFBridge",
    # Stage 2 (v59.2)
    "VariantStatus",
    "CodeVariant",
    "VariantArchive",
    "NotificationLevel",
    "NotificationChannel",
    "Notification",
    "NotificationEngine",
    "AgentLifecycleState",
    "AgentRecord",
    "AgentLifecycleManager",
    "ProposalPriority",
    "ProposalStatus",
    "ImprovementProposal",
    "FeatureFlags",
    "ImprovementProposer",
    # Evolution
    "EvolutionStatus",
    "EvolutionCycleResult",
    "EvolutionLoopV2",
    # Health
    "AlertSeverity",
    "ComponentHealthScore",
    "SystemHealthReport",
    "HealthMonitor",
    "HealthLevel",
    "ComponentHealthCard",
    "SystemHealthSummary",
    "HealthDashboard",
]
