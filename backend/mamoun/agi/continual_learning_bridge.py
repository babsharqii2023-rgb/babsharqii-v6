"""
BABSHARQII v36.0 — Continual Learning Bridge Module
جسر التعلم المستمر — يربط وحدة AGI بمحرك التعلم المستمر الحقيقي

This module acts as the bridge between the AGI capability layer
(mamoun.agi.continual_learning) and the actual continual learning
implementation in mamoun.reasoning.continual_learning.

It also integrates the continual/ subpackage engines:
  - EWCEngine (Elastic Weight Consolidation)
  - SynapticIntelligenceEngine (online importance)
  - StreamingKnowledgeStore (auto-indexed knowledge)
  - AutoBenchmarkRunner (post-task regression detection)

v36 FIX: Added backward-compatible dataclasses and enums that were
referenced by tests but missing from this bridge module:
  - Skill, SkillGap, Pattern, MetaBalance, EWCResult,
    ConsolidationResult, ContinualLearningResult (dataclasses)
  - SkillStatus, SkillLifecycle (enums)
  - CONTINUAL_LEARNING_ENABLED (constant)
"""

import os
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# ─── v36 FIX: Backward-compatible dataclasses and enums ────────────────────
# These classes are referenced by test_agi_modules.py and other consumers
# that import from mamoun.agi.continual_learning directly.


class SkillStatus(str, Enum):
    """حالة المهارة — Skill lifecycle status"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    FORGOTTEN = "forgotten"
    DRAFT = "draft"


class SkillLifecycle(str, Enum):
    """دورة حياة المهارة — Skill lifecycle phase"""
    DISCOVERY = "discovery"
    LEARNING = "learning"
    MASTERY = "mastery"
    DECAY = "decay"
    ARCHIVAL = "archival"


@dataclass
class Skill:
    """مهارة — A learned skill in the continual learning system."""
    id: str = ""
    name: str = ""
    category: str = ""
    success_rate: float = 0.0
    pattern: str = ""
    tags: List[str] = field(default_factory=list)
    status: str = SkillStatus.ACTIVE.value
    created_at: float = 0.0
    last_used: float = 0.0
    use_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "success_rate": self.success_rate,
            "pattern": self.pattern,
            "tags": self.tags,
            "status": self.status,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "use_count": self.use_count,
        }


@dataclass
class SkillGap:
    """فجوة مهارة — A gap in the system's skill coverage."""
    description: str = ""
    failure_count: int = 0
    priority: float = 0.0
    domain: str = ""
    suggested_skill: str = ""

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "failure_count": self.failure_count,
            "priority": self.priority,
            "domain": self.domain,
            "suggested_skill": self.suggested_skill,
        }


@dataclass
class Pattern:
    """نمط — A recognized pattern in experience data."""
    id: str = ""
    name: str = ""
    pattern_type: str = ""
    frequency: int = 0
    confidence: float = 0.0
    examples: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "pattern_type": self.pattern_type,
            "frequency": self.frequency,
            "confidence": self.confidence,
            "examples": self.examples,
        }


@dataclass
class MetaBalance:
    """توازن التعلم — Balance between plasticity and stability."""
    plasticity: float = 0.5
    stability: float = 0.5
    learning_rate: float = 0.01

    def to_dict(self) -> dict:
        return {
            "plasticity": self.plasticity,
            "stability": self.stability,
            "learning_rate": self.learning_rate,
        }


@dataclass
class EWCResult:
    """نتيجة EWC — Result of Elastic Weight Consolidation check."""
    penalty: float = 0.0
    protected_params: int = 0
    fisher_norm: float = 0.0
    interference_detected: bool = False

    def to_dict(self) -> dict:
        return {
            "penalty": self.penalty,
            "protected_params": self.protected_params,
            "fisher_norm": self.fisher_norm,
            "interference_detected": self.interference_detected,
        }


@dataclass
class ConsolidationResult:
    """نتيجة التوحيد — Result of memory consolidation."""
    consolidated: int = 0
    archived: int = 0
    forgotten: int = 0
    total_skills_before: int = 0
    total_skills_after: int = 0

    def to_dict(self) -> dict:
        return {
            "consolidated": self.consolidated,
            "archived": self.archived,
            "forgotten": self.forgotten,
            "total_skills_before": self.total_skills_before,
            "total_skills_after": self.total_skills_after,
        }


@dataclass
class ContinualLearningResult:
    """نتيجة التعلم المستمر — Result of a learn() call."""
    new_skills: List[dict] = field(default_factory=list)
    refined_skills: List[dict] = field(default_factory=list)
    archived: List[dict] = field(default_factory=list)
    forgotten: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "new_skills": self.new_skills,
            "refined_skills": self.refined_skills,
            "archived": self.archived,
            "forgotten": self.forgotten,
        }


# v36 FIX: Constant for env toggle
CONTINUAL_LEARNING_ENABLED = os.environ.get(
    "MAMOUN_CONTINUAL_LEARNING_ENABLED", "true"
).lower() in ("true", "1", "yes")


# ─── Import the main ContinualLearningEngine from reasoning module ─────────
try:
    from mamoun.reasoning.continual_learning import (
        ContinualLearningEngine,
        TaskRecord,
        ReplayExample,
        get_continual_learning,
    )
except ImportError as e:
    logger.warning("Cannot import ContinualLearningEngine from reasoning: %s", e)
    # Fallback: create a stub that won't crash the system
    ContinualLearningEngine = None
    TaskRecord = None
    ReplayExample = None
    get_continual_learning = None

# ─── Import EWC and SI engines from continual/ subpackage ──────────────────
try:
    from mamoun.agi.continual.ewc_engine import (
        EWCEngine,
        KnowledgeAnchor,
        EWCReport,
    )
except ImportError as e:
    logger.warning("Cannot import EWCEngine: %s", e)
    EWCEngine = None
    KnowledgeAnchor = None
    EWCReport = None

try:
    from mamoun.agi.continual.synaptic_intelligence_online import (
        SynapticIntelligenceEngine,
        SynapseInfo,
        SIReport,
    )
except ImportError as e:
    logger.warning("Cannot import SynapticIntelligenceEngine: %s", e)
    SynapticIntelligenceEngine = None
    SynapseInfo = None
    SIReport = None

try:
    from mamoun.agi.continual.streaming_knowledge_store import (
        StreamingKnowledgeStore,
        KnowledgeItem,
    )
except ImportError as e:
    logger.warning("Cannot import StreamingKnowledgeStore: %s", e)
    StreamingKnowledgeStore = None
    KnowledgeItem = None

try:
    from mamoun.agi.continual.auto_benchmark import (
        AutoBenchmarkRunner,
        BenchmarkEntry,
    )
except ImportError as e:
    logger.warning("Cannot import AutoBenchmarkRunner: %s", e)
    AutoBenchmarkRunner = None
    BenchmarkEntry = None


__all__ = [
    # v36 FIX: Added backward-compatible classes
    "Skill",
    "SkillGap",
    "Pattern",
    "MetaBalance",
    "EWCResult",
    "ConsolidationResult",
    "SkillStatus",
    "SkillLifecycle",
    "ContinualLearningResult",
    "CONTINUAL_LEARNING_ENABLED",
    # Original exports
    "ContinualLearningEngine",
    "TaskRecord",
    "ReplayExample",
    "get_continual_learning",
    "EWCEngine",
    "KnowledgeAnchor",
    "EWCReport",
    "SynapticIntelligenceEngine",
    "SynapseInfo",
    "SIReport",
    "StreamingKnowledgeStore",
    "KnowledgeItem",
    "AutoBenchmarkRunner",
    "BenchmarkEntry",
]
