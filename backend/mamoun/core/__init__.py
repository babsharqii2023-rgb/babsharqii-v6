"""
BABSHARQII v61 — Mamoun Core Package (UNIFIED)

This package now exports from BOTH old paths and new super_brain/shared paths.
All core/ modules redirect to their super_brain/ or shared/ equivalents
while maintaining backward compatibility.

Architecture:
  core/           → Backward-compatible adapters → delegate to super_brain/ or shared/
  core/super_brain/ → New v58-v61 components (THE CANONICAL implementation)
  core/shared/    → Shared infrastructure (NeuralBus, LLM, Registry)
  core/legacy/    → Old v18-v40 implementations (reference only, NOT imported)
"""

# ── Old exports (backward-compatible — now delegate to super_brain/shared) ──
from .code_patcher import CodePatcher, CodePatch, FileAnalysis
from .sandbox_runner import SandboxRunner, SandboxResult
from .safety_guard import SafetyGuard, SafetyViolation
from .triple_memory import TripleMemoryManager, triple_memory, MemoryEntry, SearchResult
from .self_modifier import (
    SelfModifier,
    ModificationProposal,
    ValidationResult,
    ApplyResult,
    RollbackResult,
    SelfAnalysis,
    ModificationRecord,
    get_self_modifier,
)

# ── New exports from super_brain (v59-v61 components) ──────────────────
from .super_brain import (
    # Stage 1 (v59.1)
    OutcomeRecord,
    ComponentProfile,
    MetaCognitionEngine,
    OutcomeRecorder,
    record_outcome,
    HealingAction,
    HealingResultStatus,
    HealingResult,
    SelfHealingBridge,
    FeedbackType,
    RLHFPattern,
    FeedbackRecord,
    ImprovementSuggestion,
    RLHFBridge,
    # Stage 2 (v59.2)
    VariantStatus,
    CodeVariant,
    VariantArchive,
    NotificationLevel,
    NotificationChannel,
    Notification,
    NotificationEngine,
    AgentLifecycleState,
    AgentRecord,
    AgentLifecycleManager,
    ProposalPriority,
    ProposalStatus,
    ImprovementProposal,
    FeatureFlags,
    ImprovementProposer,
    # Evolution
    EvolutionStatus,
    EvolutionCycleResult,
    EvolutionLoopV2,
    # Health
    AlertSeverity,
    ComponentHealthScore,
    SystemHealthReport,
    HealthMonitor,
    HealthLevel,
    ComponentHealthCard,
    SystemHealthSummary,
    HealthDashboard,
)

__all__ = [
    # Backward-compatible (from core/)
    "CodePatcher",
    "CodePatch",
    "FileAnalysis",
    "SandboxRunner",
    "SandboxResult",
    "SafetyGuard",
    "SafetyViolation",
    "TripleMemoryManager",
    "triple_memory",
    "MemoryEntry",
    "SearchResult",
    "SelfModifier",
    "ModificationProposal",
    "ValidationResult",
    "ApplyResult",
    "RollbackResult",
    "SelfAnalysis",
    "ModificationRecord",
    "get_self_modifier",
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
