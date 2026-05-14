"""
BABSHARQII (Mamoun) v6.0 — Swarm Intelligence Engine
محرك الذكاء السربي — نظام الذكاء الجماعي اللامركزي لطبقة AGI

Implements a comprehensive Swarm Intelligence system for the Arabic digital
organism BABSHARQII, inspired by:

  • Particle Swarm Optimization (Kennedy & Eberhart, 1995) — solution-space
    exploration through collective particle movement with adaptive inertia.
  • Ant Colony Optimization (Dorigo & Gambardella, 1997) — stigmergic
    communication via pheromone trails for path-finding and resource allocation.
  • Consensus Dynamics (Renyi, 1955; Lamport, 1998) — distributed
    decision-making protocols with Byzantine fault tolerance.
  • Bee Algorithm (Pham et al., 2005) — foraging-inspired task allocation
    with scout/forager/worker roles.

Architecture:
  ┌──────────────────────────────────────────────────────────────────────┐
  │                     SwarmIntelligenceEngine                           │
  │                                                                      │
  │  ┌────────────────────────┐  ┌────────────────────────────────────┐ │
  │  │ ParticleSwarmOptimizer │  │ ConsensusEngine                    │ │
  │  │ (multi-objective PSO,  │  │ (voting protocols, conflict       │ │
  │  │  adaptive inertia,     │  │  resolution, Byzantine fault       │ │
  │  │  convergence detect)   │  │  tolerance)                        │ │
  │  └───────────┬────────────┘  └──────────────┬─────────────────────┘ │
  │              │                               │                       │
  │  ┌───────────▼───────────────────────────────▼───────────────────┐ │
  │  │               StigmergyChannel                                │ │
  │  │  (pheromone deposit/evaporate, trail following, environment  │ │
  │  │   state sharing for indirect agent communication)            │ │
  │  └───────────────────────────┬───────────────────────────────────┘ │
  │                              │                                       │
  │  ┌──────────────────────────▼───────────────────────────────────┐ │
  │  │               TaskAllocator                                   │ │
  │  │  (bee-algorithm inspired: scout→explore, forager→exploit,   │ │
  │  │   worker→execute, dynamic reallocation)                      │ │
  │  └──────────────────────────────────────────────────────────────┘ │
  └──────────────────────────────────────────────────────────────────────┘

Env toggles:
    MAMOUN_SWARM_INTELLIGENCE_ENABLED    — تمكين/تعطيل الذكاء السربي (الافتراضي: "true")
    MAMOUN_SWARM_PARTICLE_COUNT          — عدد الجسيمات (الافتراضي: "30")
    MAMOUN_SWARM_CONSENSUS_THRESHOLD     — عتبة الإجماع (الافتراضي: "0.6")
    MAMOUN_SWARM_PHEROMONE_DECAY         — معدل تبخر الفيرومون (الافتراضي: "0.1")
"""

from __future__ import annotations

import os
import math
import time
import uuid
import random
import logging
from dataclasses import dataclass, field
from typing import Optional, Callable
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# مفاتيح التهيئة البيئية — Environment Configuration Toggles
# ═══════════════════════════════════════════════════════════════════════════════

SWARM_ENABLED: bool = os.environ.get(
    "MAMOUN_SWARM_INTELLIGENCE_ENABLED", "true"
).lower() in ("true", "1", "yes")

SWARM_PARTICLE_COUNT: int = int(
    os.environ.get("MAMOUN_SWARM_PARTICLE_COUNT", "30")
)

SWARM_CONSENSUS_THRESHOLD: float = float(
    os.environ.get("MAMOUN_SWARM_CONSENSUS_THRESHOLD", "0.6")
)

SWARM_PHEROMONE_DECAY: float = float(
    os.environ.get("MAMOUN_SWARM_PHEROMONE_DECAY", "0.1")
)


# ═══════════════════════════════════════════════════════════════════════════════
# ثوابت النظام — System Constants
# ═══════════════════════════════════════════════════════════════════════════════

# ثوابت PSO — PSO Constants
PSO_INERTIA_MAX: float = 0.9            # أقصى وزن بالقصور الذاتي — max inertia weight
PSO_INERTIA_MIN: float = 0.4            # أدنى وزن بالقصور الذاتي — min inertia weight
PSO_COGNITIVE_COEFF: float = 2.0        # معامل التعلم المعرفي — cognitive learning coefficient (c1)
PSO_SOCIAL_COEFF: float = 2.0           # معامل التعلم الاجتماعي — social learning coefficient (c2)
PSO_MAX_VELOCITY: float = 0.5           # أقصى سرعة — max velocity clamp
PSO_CONVERGENCE_PATIENCE: int = 20      # صبر التقارب — iterations without improvement before convergence
PSO_DEFAULT_ITERATIONS: int = 100       # عدد التكرارات الافتراضي — default max iterations

# ثوابت الإجماع — Consensus Constants
CONSENSUS_QUORUM_MIN: float = 0.5       # الحد الأدنى للنصاب — minimum quorum ratio
CONSENSUS_BYZANTINE_THRESHOLD: float = 0.33  # عتبة التحمل البيزنطي — Byzantine fault threshold
CONSENSUS_MEDIATION_ROUNDS: int = 3     # جولات الوساطة — mediation rounds for conflict resolution

# ثوابت الفيرومون — Pheromone Constants
PHEROMONE_INITIAL_STRENGTH: float = 1.0  # القوة الأولية — initial pheromone strength
PHEROMONE_DEPOSIT_BASE: float = 0.5      # قاعدة إيداع الفيرومون — base pheromone deposit
PHEROMONE_ALPHA: float = 1.0             # معامل تأثير الفيرومون — pheromone influence exponent
PHEROMONE_BETA: float = 2.0              # معامل جاذبية المسار — trail attractiveness exponent

# ثوابت تخصيص المهام — Task Allocation Constants
TASK_SCOUT_RATIO: float = 0.15          # نسبة الكشافة — scout agent ratio
TASK_FORAGER_RATIO: float = 0.50        # نسبة الجوّالة — forager agent ratio
TASK_WORKER_RATIO: float = 0.35         # نسبة العمال — worker agent ratio
TASK_REALLOCATION_INTERVAL: float = 5.0  # فترة إعادة التخصيص — reallocation check interval (seconds)


# ═══════════════════════════════════════════════════════════════════════════════
# التعدادات — Enumerations
# ═══════════════════════════════════════════════════════════════════════════════

class VotingProtocol(str, Enum):
    """
    بروتوكول التصويت — نوع بروتوكول التصويت المستخدم للإجماع.
    Type of voting protocol used for consensus.
    """
    SIMPLE_MAJORITY = "simple_majority"      # أغلبية بسيطة
    WEIGHTED = "weighted"                     # مرجح بالخبرة
    QUORUM = "quorum"                         # نصاب مطلوب
    UNANIMOUS = "unanimous"                   # إجماع كامل


class AgentRole(str, Enum):
    """
    دور الوكيل — دور الوكيل في خوارزمية النحل.
    Agent role in the bee-algorithm task allocation.
    """
    SCOUT = "scout"       # كشاف — يستكشف حلولاً جديدة
    FORAGER = "forager"   # جوّال — يستغل حلولاً معروفة
    WORKER = "worker"     # عامل — ينفذ المهام المخصصة


class PheromoneType(str, Enum):
    """
    نوع الفيرومون — نوع الرسالة البيئية غير المباشرة.
    Type of stigmergic pheromone marker.
    """
    PATH = "path"             # مسار — يدل على طريق واعد
    DANGER = "danger"         # خطر — يحذر من منطقة خطرة
    RESOURCE = "resource"     # مورد — يشير إلى مورد متاح
    COMPLETED = "completed"   # مُنجز — يشير إلى اكتمال مهمة


class ConflictResolutionStrategy(str, Enum):
    """
    استراتيجية حل النزاعات — كيفية حل الخلافات بين الوكلاء.
    Strategy for resolving conflicts during consensus.
    """
    MEDIATION = "mediation"           # وساطة — توسط الأكثر خبرة
    VOTING_OVERRIDE = "voting_override"  # تجاوز بالتصويت
    WEIGHTED_AVERAGE = "weighted_average"  # متوسط مرجح
    RANDOM_TIEBREAK = "random_tiebreak"    # كسر عشوائي للتعادل


# ═══════════════════════════════════════════════════════════════════════════════
# هياكل البيانات — Dataclasses
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Particle:
    """
    جسيم — عنصر في سرب تحسين الجسيمات.
    A particle in the Particle Swarm Optimizer.

    يمثل حلاً محتملاً في فضاء الحل مع موقعه وسرعته وأفضل موقع شخصي.
    Represents a candidate solution with position, velocity, and personal best.
    """
    id: str = ""                                      # معرف الجسيم
    position: list[float] = field(default_factory=list)  # الموقع الحالي
    velocity: list[float] = field(default_factory=list)  # السرعة الحالية
    personal_best: list[float] = field(default_factory=list)  # أفضل موقع شخصي
    personal_best_fitness: float = float("inf")         # لياقة أفضل موقع شخصي
    fitness: float = float("inf")                       # اللياقة الحالية
    dimensions: int = 0                                 # عدد الأبعاد

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "id": self.id,
            "position": [round(v, 6) for v in self.position],
            "velocity": [round(v, 6) for v in self.velocity],
            "personal_best": [round(v, 6) for v in self.personal_best],
            "personal_best_fitness": round(self.personal_best_fitness, 6),
            "fitness": round(self.fitness, 6),
            "dimensions": self.dimensions,
        }


@dataclass
class PheromoneTrail:
    """
    مسار فيرومون — مسار اتصال غير مباشر بين الوكلاء.
    A pheromone trail for stigmergic communication.

    يستخدم للاتصال غير المباشر بين الوكلاء عبر تعديل البيئة المشتركة.
    Used for indirect inter-agent communication through environment modification.
    """
    id: str = ""                                       # معرف المسار
    path: list[str] = field(default_factory=list)      # المسار (تسلسل عقد)
    strength: float = PHEROMONE_INITIAL_STRENGTH        # قوة الفيرومون (0-∞)
    decay_rate: float = SWARM_PHEROMONE_DECAY           # معدل التبخر
    pheromone_type: PheromoneType = PheromoneType.PATH  # نوع الفيرومون
    creator_id: str = ""                                # معرف المنشئ
    created_at: float = 0.0                             # وقت الإنشاء
    last_reinforced: float = 0.0                        # آخر تعزيز
    visit_count: int = 0                                # عدد الزيارات

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "id": self.id,
            "path": self.path,
            "strength": round(self.strength, 6),
            "decay_rate": round(self.decay_rate, 6),
            "pheromone_type": self.pheromone_type.value,
            "creator_id": self.creator_id,
            "created_at": round(self.created_at, 3),
            "last_reinforced": round(self.last_reinforced, 3),
            "visit_count": self.visit_count,
        }


@dataclass
class SwarmVote:
    """
    تصويت سربي — تصويت واحد في عملية الإجماع.
    A single vote in the swarm consensus process.

    يمثل رأي وكيل واحد مع وزنه وثقته.
    Represents one agent's vote with weight and confidence.
    """
    voter_id: str = ""              # معرف المُصوّت
    choice: str = ""                # الخيار المُختار
    weight: float = 1.0             # وزن التصويت (يعكس الخبرة)
    confidence: float = 1.0         # ثقة المُصوّت في اختياره (0-1)
    reasoning: str = ""             # سبب التصويت
    timestamp: float = 0.0          # وقت التصويت

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "voter_id": self.voter_id,
            "choice": self.choice,
            "weight": round(self.weight, 4),
            "confidence": round(self.confidence, 4),
            "reasoning": self.reasoning,
            "timestamp": round(self.timestamp, 3),
        }


@dataclass
class ConsensusResult:
    """
    نتيجة الإجماع — نتيجة عملية اتخاذ القرار الجماعي.
    Result of a distributed consensus process.

    تتضمن القرار النهائي ومستوى الثقة ونسبة المعارضة.
    Includes the final decision, confidence level, and dissent ratio.
    """
    decision: str = ""                  # القرار المتخذ
    confidence: float = 0.0             # ثقة القرار (0-1)
    dissent_ratio: float = 0.0          # نسبة المعارضة (0-1)
    protocol_used: VotingProtocol = VotingProtocol.SIMPLE_MAJORITY  # البروتوكول المستخدم
    total_votes: int = 0                # إجمالي الأصوات
    agreement_count: int = 0            # عدد الموافقين
    dissenting_opinions: list[str] = field(default_factory=list)  # آراء المعارضين
    byzantine_detected: bool = False    # هل تم كشف سلوك بيزنطي؟
    mediation_rounds: int = 0           # عدد جولات الوساطة
    timestamp: float = 0.0              # وقت النتيجة

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "decision": self.decision,
            "confidence": round(self.confidence, 4),
            "dissent_ratio": round(self.dissent_ratio, 4),
            "protocol_used": self.protocol_used.value,
            "total_votes": self.total_votes,
            "agreement_count": self.agreement_count,
            "dissenting_opinions": self.dissenting_opinions,
            "byzantine_detected": self.byzantine_detected,
            "mediation_rounds": self.mediation_rounds,
            "timestamp": round(self.timestamp, 3),
        }


@dataclass
class TaskAssignment:
    """
    تخصيص مهمة — تعيين مهمة لوكيل بناءً على اللياقة والأولوية.
    Task assignment to an agent based on fitness and priority.

    يمثل تعيين مهمة واحدة لوكيل واحد مع تقييم ملاءمته.
    Represents one task-to-agent mapping with fitness evaluation.
    """
    agent_id: str = ""                  # معرف الوكيل
    task_id: str = ""                   # معرف المهمة
    fitness: float = 0.0                # لياقة الوكيل للمهمة (0-1)
    priority: float = 0.5               # أولوية المهمة (0-1)
    role: AgentRole = AgentRole.WORKER   # دور الوكيل
    estimated_duration: float = 0.0     # المدة المقدرة (ثوانٍ)
    assigned_at: float = 0.0            # وقت التخصيص

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "fitness": round(self.fitness, 4),
            "priority": round(self.priority, 4),
            "role": self.role.value,
            "estimated_duration": round(self.estimated_duration, 3),
            "assigned_at": round(self.assigned_at, 3),
        }


@dataclass
class OptimizationResult:
    """
    نتيجة التحسين — نتيجة عملية تحسين سرب الجسيمات.
    Result of a PSO optimization run.

    تتضمن أفضل حل وجدته وقيمة اللياقة ومعلومات التقارب.
    Includes the best solution found, fitness value, and convergence info.
    """
    best_position: list[float] = field(default_factory=list)   # أفضل موقع
    best_fitness: float = float("inf")                          # أفضل لياقة
    iterations_used: int = 0                                    # التكرارات المستخدمة
    converged: bool = False                                     # هل تقارب السرب؟
    particle_count: int = 0                                     # عدد الجسيمات
    pareto_front: list[list[float]] = field(default_factory=list)  # جبهة باريتو (متعدد الأهداف)
    diversity: float = 0.0                                      # تنوع السرب
    elapsed_time: float = 0.0                                   # الوقت المستغرق (ثوانٍ)

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "best_position": [round(v, 6) for v in self.best_position],
            "best_fitness": round(self.best_fitness, 6),
            "iterations_used": self.iterations_used,
            "converged": self.converged,
            "particle_count": self.particle_count,
            "pareto_front": [[round(v, 6) for v in row] for row in self.pareto_front],
            "diversity": round(self.diversity, 6),
            "elapsed_time": round(self.elapsed_time, 3),
        }


@dataclass
class StigmergyMessage:
    """
    رسالة ستيغميرجي — رسالة اتصال غير مباشر عبر البيئة.
    Stigmergic message deposited in the shared environment.

    تمثل علامة بيئية يتركها وكيل ليقرأها وكلاء آخرون لاحقاً.
    Represents an environment marker left by one agent for others to read later.
    """
    id: str = ""                                  # معرف الرسالة
    sender_id: str = ""                            # معرف المُرسل
    channel: str = "default"                       # قناة الاتصال
    content: str = ""                              # محتوى الرسالة
    pheromone_type: PheromoneType = PheromoneType.PATH  # نوع الفيرومون
    strength: float = PHEROMONE_INITIAL_STRENGTH    # قوة الرسالة
    created_at: float = 0.0                        # وقت الإنشاء
    ttl: float = 3600.0                            # وقت الحياة (ثوانٍ)

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "channel": self.channel,
            "content": self.content,
            "pheromone_type": self.pheromone_type.value,
            "strength": round(self.strength, 6),
            "created_at": round(self.created_at, 3),
            "ttl": round(self.ttl, 3),
        }


@dataclass
class SwarmIntelligenceResult:
    """
    نتيجة الذكاء السربي — نتيجة شاملة لعملية الذكاء السربي.
    Comprehensive result from the SwarmIntelligenceEngine.

    تجمع نتائج جميع المحركات الفرعية في بنية واحدة شاملة.
    Aggregates results from all sub-engines into one comprehensive structure.
    """
    operation: str = ""                           # نوع العملية
    success: bool = True                          # هل نجحت العملية؟
    optimization: Optional[OptimizationResult] = None   # نتيجة التحسين
    consensus: Optional[ConsensusResult] = None         # نتيجة الإجماع
    task_assignments: list[TaskAssignment] = field(default_factory=list)  # تخصيصات المهام
    stigmergy_messages: list[StigmergyMessage] = field(default_factory=list)  # رسائل ستيغميرجي
    metadata: dict = field(default_factory=dict)         # بيانات وصفية إضافية
    timestamp: float = 0.0                        # وقت النتيجة

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "operation": self.operation,
            "success": self.success,
            "optimization": self.optimization.to_dict() if self.optimization else None,
            "consensus": self.consensus.to_dict() if self.consensus else None,
            "task_assignments": [ta.to_dict() for ta in self.task_assignments],
            "stigmergy_messages": [sm.to_dict() for sm in self.stigmergy_messages],
            "metadata": self.metadata,
            "timestamp": round(self.timestamp, 3),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# محسّن سرب الجسيمات — ParticleSwarmOptimizer
# ═══════════════════════════════════════════════════════════════════════════════

class ParticleSwarmOptimizer:
    """
    محسّن سرب الجسيمات — حل مشكلات التحسين عبر الحركة الجماعية للجسيمات.
    Particle Swarm Optimization for solution-space exploration.

    مستوحى من سلوك أسراب الطيور في البحث عن الطعام:
    كل جسيم يتحرك في فضاء الحل متأثراً بأفضل موقع شخصي وأفضل موقع عالمي.

    Inspired by bird flocking behavior:
    Each particle moves through solution space influenced by its personal best
    and the global best position found by the swarm.

    الميزات:
        - وزن بالقصور الذاتي متكيف (يتناقص من 0.9 إلى 0.4)
        - كشف التقارب عند عدم التحسن لعدد تكرارات
        - دعم التحسين متعدد الأهداف مع جبهة باريتو
    """

    def __init__(
        self,
        particle_count: int = SWARM_PARTICLE_COUNT,
        dimensions: int = 2,
        bounds: list[tuple[float, float]] | None = None,
    ):
        """
        تهيئة محسّن سرب الجسيمات.

        Args:
            particle_count: عدد الجسيمات في السرب
            dimensions: عدد أبعاد فضاء الحل
            bounds: حدود كل بعد [(min, max), ...]
        """
        self.particle_count = particle_count
        self.dimensions = dimensions
        self.bounds = bounds or [(-1.0, 1.0)] * dimensions
        self.particles: list[Particle] = []
        self.global_best: list[float] = []
        self.global_best_fitness: float = float("inf")
        self.pareto_front: list[list[float]] = []
        self._iterations_without_improvement = 0

    def initialize(self) -> None:
        """
        تهيئة السرب — Initialize the swarm with random positions.
        ينشئ جسيمات بمواقع وسرعات عشوائية ضمن الحدود المحددة.
        """
        self.particles = []
        self.global_best = []
        self.global_best_fitness = float("inf")
        self.pareto_front = []
        self._iterations_without_improvement = 0

        for i in range(self.particle_count):
            position = [
                random.uniform(self.bounds[d][0], self.bounds[d][1])
                for d in range(self.dimensions)
            ]
            velocity = [
                random.uniform(-PSO_MAX_VELOCITY, PSO_MAX_VELOCITY)
                for _ in range(self.dimensions)
            ]
            particle = Particle(
                id=f"p_{i}_{uuid.uuid4().hex[:6]}",
                position=position,
                velocity=velocity,
                personal_best=list(position),
                personal_best_fitness=float("inf"),
                fitness=float("inf"),
                dimensions=self.dimensions,
            )
            self.particles.append(particle)

        logger.debug(
            "تم تهيئة سرب من %d جسيم في %d بُعد — "
            "Initialized swarm: %d particles, %d dimensions",
            len(self.particles), self.dimensions, len(self.particles), self.dimensions,
        )

    def optimize(
        self,
        objective_fn: Callable[[list[float]], float],
        max_iterations: int = PSO_DEFAULT_ITERATIONS,
        constraints: list[Callable[[list[float]], bool]] | None = None,
        multi_objective: bool = False,
        objective_fns: list[Callable[[list[float]], float]] | None = None,
    ) -> OptimizationResult:
        """
        تحسين — Execute the PSO optimization process.
        ينفذ عملية التحسين عبر تحريك الجسيمات تكرارياً.

        Args:
            objective_fn: دالة الهدف لتقليلها — objective function to minimize
            max_iterations: أقصى عدد تكرارات — maximum iterations
            constraints: قيود على الحلول — solution constraints
            multi_objective: هل التحسين متعدد الأهداف؟ — multi-objective flag
            objective_fns: دوال الأهداف المتعددة — list of objective functions

        Returns:
            OptimizationResult — نتيجة التحسين
        """
        start_time = time.time()

        # تهيئة السرب إذا لم يكن مهيأً — Initialize if not already done
        if not self.particles:
            self.initialize()

        # تقييم اللياقة الأولي — Initial fitness evaluation
        for particle in self.particles:
            particle.fitness = objective_fn(particle.position)
            particle.personal_best_fitness = particle.fitness

            # تطبيق القيود — Apply constraints
            if constraints and not all(c(particle.position) for c in constraints):
                particle.fitness = float("inf")
                particle.personal_best_fitness = float("inf")

        # تحديث الأفضل العالمي — Update global best
        self._update_global_best()

        # الحلقة الرئيسية — Main loop
        for iteration in range(max_iterations):
            # حساب وزن القصور الذاتي المتكيف — Adaptive inertia weight
            w = self._compute_inertia_weight(iteration, max_iterations)

            # تحديث كل جسيم — Update each particle
            for particle in self.particles:
                self._update_particle(particle, w)

                # تطبيق القيود — Apply constraints
                if constraints and not all(c(particle.position) for c in constraints):
                    # إعادة الجسيم ضمن الحدود — Push back within bounds
                    particle.position = self._clamp_position(particle.position)
                    particle.fitness = float("inf")
                    continue

                # تقييم اللياقة — Evaluate fitness
                particle.fitness = objective_fn(particle.position)

                # تحديث الأفضل الشخصي — Update personal best
                if particle.fitness < particle.personal_best_fitness:
                    particle.personal_best = list(particle.position)
                    particle.personal_best_fitness = particle.fitness

            # تحديث الأفضل العالمي — Update global best
            improved = self._update_global_best()

            # تحديث جبهة باريتو (متعدد الأهداف) — Update Pareto front
            if multi_objective and objective_fns:
                self._update_pareto_front(objective_fns)

            # كشف التقارب — Convergence detection
            if improved:
                self._iterations_without_improvement = 0
            else:
                self._iterations_without_improvement += 1

            if self._iterations_without_improvement >= PSO_CONVERGENCE_PATIENCE:
                logger.debug(
                    "تقارب السرب عند التكرار %d — "
                    "Swarm converged at iteration %d",
                    iteration, iteration,
                )
                return self._build_result(
                    iteration + 1, converged=True, start_time=start_time,
                )

        return self._build_result(
            max_iterations,
            converged=self._iterations_without_improvement >= PSO_CONVERGENCE_PATIENCE,
            start_time=start_time,
        )

    def _update_particle(self, particle: Particle, w: float) -> None:
        """
        تحديث جسيم — Update a particle's velocity and position.
        يحدّث سرعة وموقع الجسيم بناءً على المعادلة القياسية PSO.

        v = w*v + c1*r1*(pbest-x) + c2*r2*(gbest-x)
        x = x + v
        """
        if not self.global_best:
            return

        for d in range(self.dimensions):
            r1 = random.random()
            r2 = random.random()

            # حساب السرعة الجديدة — Compute new velocity
            cognitive = PSO_COGNITIVE_COEFF * r1 * (
                particle.personal_best[d] - particle.position[d]
            )
            social = PSO_SOCIAL_COEFF * r2 * (
                self.global_best[d] - particle.position[d]
            )
            particle.velocity[d] = w * particle.velocity[d] + cognitive + social

            # تحديد السرعة القصوى — Clamp velocity
            particle.velocity[d] = max(
                -PSO_MAX_VELOCITY, min(PSO_MAX_VELOCITY, particle.velocity[d])
            )

            # تحديث الموقع — Update position
            particle.position[d] += particle.velocity[d]

        # تقييد الموقع ضمن الحدود — Clamp position within bounds
        particle.position = self._clamp_position(particle.position)

    def _clamp_position(self, position: list[float]) -> list[float]:
        """
        تقييد الموقع — Clamp position within bounds.
        يعيد الموقع ضمن الحدود المسموحة.
        """
        clamped = []
        for d in range(self.dimensions):
            lo, hi = self.bounds[d]
            clamped.append(max(lo, min(hi, position[d])))
        return clamped

    def _update_global_best(self) -> bool:
        """
        تحديث الأفضل العالمي — Update the global best position.
        يبحث عن أفضل لياقة بين جميع الجسيمات.
        Returns True if the global best improved.
        """
        improved = False
        for particle in self.particles:
            if particle.fitness < self.global_best_fitness:
                self.global_best = list(particle.position)
                self.global_best_fitness = particle.fitness
                improved = True
        return improved

    def _compute_inertia_weight(self, iteration: int, max_iterations: int) -> float:
        """
        حساب وزن القصور الذاتي المتكيف — Compute adaptive inertia weight.
        يتناقص خطياً من PSO_INERTIA_MAX إلى PSO_INERTIA_MIN.
        Linearly decreases from 0.9 to 0.4 over iterations.
        """
        progress = iteration / max(1, max_iterations)
        w = PSO_INERTIA_MAX - (PSO_INERTIA_MAX - PSO_INERTIA_MIN) * progress
        return w

    def _update_pareto_front(
        self, objective_fns: list[Callable[[list[float]], float]]
    ) -> None:
        """
        تحديث جبهة باريتو — Update the Pareto front for multi-objective optimization.
        يحتفظ بالحلول غير المهيمنة لتحسين متعدد الأهداف.
        Maintains non-dominated solutions for multi-objective optimization.
        """
        candidates: list[list[float]] = []

        for particle in self.particles:
            if particle.fitness < float("inf"):
                objectives = [fn(particle.position) for fn in objective_fns]
                candidates.append(objectives)

        # تصفية الحلول المهيمنة — Filter dominated solutions
        pareto: list[list[float]] = []
        for i, candidate in enumerate(candidates):
            is_dominated = False
            for j, other in enumerate(candidates):
                if i == j:
                    continue
                # هل يهيمن الآخر على هذا المرشح؟ — Is candidate dominated by other?
                if all(o <= c for o, c in zip(other, candidate)) and \
                   any(o < c for o, c in zip(other, candidate)):
                    is_dominated = True
                    break
            if not is_dominated:
                pareto.append(candidate)

        self.pareto_front = pareto[:50]  # تقليم — limit Pareto front size

    def _compute_diversity(self) -> float:
        """
        حساب تنوع السرب — Compute swarm diversity.
        يقيس مدى انتشار الجسيمات في فضاء الحل.
        Measures how spread out the particles are in solution space.
        """
        if len(self.particles) < 2:
            return 0.0

        # المتوسط — Centroid
        centroid = [0.0] * self.dimensions
        for p in self.particles:
            for d in range(self.dimensions):
                centroid[d] += p.position[d]
        centroid = [c / len(self.particles) for c in centroid]

        # متوسط المسافة من المركز — Average distance from centroid
        total_dist = 0.0
        for p in self.particles:
            dist = math.sqrt(
                sum((p.position[d] - centroid[d]) ** 2 for d in range(self.dimensions))
            )
            total_dist += dist

        return total_dist / len(self.particles)

    def _build_result(
        self, iterations: int, converged: bool, start_time: float
    ) -> OptimizationResult:
        """
        بناء نتيجة التحسين — Build the optimization result.
        """
        return OptimizationResult(
            best_position=list(self.global_best),
            best_fitness=self.global_best_fitness,
            iterations_used=iterations,
            converged=converged,
            particle_count=len(self.particles),
            pareto_front=list(self.pareto_front),
            diversity=self._compute_diversity(),
            elapsed_time=time.time() - start_time,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# محرك الإجماع — ConsensusEngine
# ═══════════════════════════════════════════════════════════════════════════════

class ConsensusEngine:
    """
    محرك الإجماع — اتخاذ القرار الجماعي اللامركزي.
    Distributed decision-making engine for reaching group consensus.

    يدعم بروتوكولات تصويت متعددة مع حل النزاعات وتحمل الأخطاء البيزنطية.
    Supports multiple voting protocols with conflict resolution and
    Byzantine fault tolerance.

    البروتوكولات المدعومة:
        - أغلبية بسيطة: الخيار الأكثر أصواتاً يفوز
        - مرجح: الأصوات الموزونة بالخبرة
        - نصاب: يتطلب نسبة مشاركة دنيا
        - إجماع كامل: يتطلب موافقة الجميع
    """

    def __init__(
        self,
        threshold: float = SWARM_CONSENSUS_THRESHOLD,
        conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.MEDIATION,
    ):
        """
        تهيئة محرك الإجماع.

        Args:
            threshold: عتبة الإجماع المطلوبة (0.5-1.0)
            conflict_strategy: استراتيجية حل النزاعات
        """
        self.threshold = threshold
        self.conflict_strategy = conflict_strategy
        self._vote_history: list[list[SwarmVote]] = []
        self._byzantine_agents: set[str] = set()

    def reach_consensus(
        self,
        votes: list[SwarmVote],
        protocol: VotingProtocol = VotingProtocol.SIMPLE_MAJORITY,
        quorum_requirement: float = CONSENSUS_QUORUM_MIN,
    ) -> ConsensusResult:
        """
        الوصول للإجماع — Reach consensus from a set of votes.
        يحسب نتيجة الإجماع بناءً على البروتوكول المحدد.

        Args:
            votes: قائمة الأصوات
            protocol: بروتوكول التصويت
            quorum_requirement: متطلب النصاب (لبروتوكول النصاب)

        Returns:
            ConsensusResult — نتيجة الإجماع
        """
        if not votes:
            return ConsensusResult(
                decision="no_votes",
                confidence=0.0,
                dissent_ratio=1.0,
                protocol_used=protocol,
                timestamp=time.time(),
            )

        # كشف السلوك البيزنطي — Detect Byzantine behavior
        byzantine_detected = self._detect_byzantine(votes)

        # تصفية الأصوات المشبوهة — Filter suspicious votes
        filtered_votes = self._filter_byzantine(votes) if byzantine_detected else votes

        # حفظ سجل التصويت — Save vote history
        self._vote_history.append(list(votes))

        # تطبيق البروتوكول — Apply protocol
        if protocol == VotingProtocol.SIMPLE_MAJORITY:
            result = self._simple_majority(filtered_votes)
        elif protocol == VotingProtocol.WEIGHTED:
            result = self._weighted_voting(filtered_votes)
        elif protocol == VotingProtocol.QUORUM:
            result = self._quorum_voting(filtered_votes, quorum_requirement)
        elif protocol == VotingProtocol.UNANIMOUS:
            result = self._unanimous_voting(filtered_votes)
        else:
            result = self._simple_majority(filtered_votes)

        # حل النزاعات إذا لزم — Resolve conflicts if needed
        if result.confidence < self.threshold:
            result = self._resolve_conflict(filtered_votes, result)

        result.protocol_used = protocol
        result.byzantine_detected = byzantine_detected
        result.total_votes = len(votes)
        result.timestamp = time.time()

        logger.debug(
            "نتيجة الإجماع: قرار='%s' ثقة=%.2f معارضة=%.2f بروتوكول=%s — "
            "Consensus: decision='%s' confidence=%.2f dissent=%.2f protocol=%s",
            result.decision, result.confidence, result.dissent_ratio, protocol.value,
            result.decision, result.confidence, result.dissent_ratio, protocol.value,
        )

        return result

    def _simple_majority(self, votes: list[SwarmVote]) -> ConsensusResult:
        """
        أغلبية بسيطة — Simple majority voting.
        الخيار الحاصل على أكبر عدد أصوات يفوز.
        """
        tally: dict[str, int] = defaultdict(int)
        for vote in votes:
            tally[vote.choice] += 1

        if not tally:
            return ConsensusResult(decision="no_votes", confidence=0.0, dissent_ratio=1.0)

        winner = max(tally, key=tally.get)  # type: ignore[arg-type]
        winner_count = tally[winner]
        total = len(votes)
        agreement_count = winner_count
        dissent_count = total - winner_count

        return ConsensusResult(
            decision=winner,
            confidence=winner_count / total,
            dissent_ratio=dissent_count / total,
            agreement_count=agreement_count,
            dissenting_opinions=[
                v.choice for v in votes if v.choice != winner
            ],
        )

    def _weighted_voting(self, votes: list[SwarmVote]) -> ConsensusResult:
        """
        تصويت مرجح — Weighted voting based on agent expertise.
        كل صوت يُضرب بوزن المُصوّت وثقته.
        Each vote is multiplied by the voter's weight and confidence.
        """
        tally: dict[str, float] = defaultdict(float)
        count_per_choice: dict[str, int] = defaultdict(int)

        for vote in votes:
            weighted_score = vote.weight * vote.confidence
            tally[vote.choice] += weighted_score
            count_per_choice[vote.choice] += 1

        if not tally:
            return ConsensusResult(decision="no_votes", confidence=0.0, dissent_ratio=1.0)

        winner = max(tally, key=tally.get)  # type: ignore[arg-type]
        total_weight = sum(tally.values())
        winner_weight = tally[winner]

        return ConsensusResult(
            decision=winner,
            confidence=winner_weight / total_weight if total_weight > 0 else 0.0,
            dissent_ratio=1.0 - (winner_weight / total_weight if total_weight > 0 else 0.0),
            agreement_count=count_per_choice[winner],
            dissenting_opinions=[
                v.choice for v in votes if v.choice != winner
            ],
        )

    def _quorum_voting(
        self, votes: list[SwarmVote], quorum: float
    ) -> ConsensusResult:
        """
        تصويت بالنصاب — Quorum-based voting.
        يتطلب نسبة مشاركة دنيا لاعتماد القرار.
        Requires minimum participation ratio for decision validity.
        """
        total = len(votes)

        # فحص النصاب — Check quorum
        if total == 0 or (1.0 if total > 0 else 0.0) < quorum:
            return ConsensusResult(
                decision="quorum_not_met",
                confidence=0.0,
                dissent_ratio=1.0,
            )

        # إجراء تصويت مرجح بعد تجاوز النصاب — Weighted vote after quorum
        result = self._weighted_voting(votes)

        # التحقق من عتبة الإجماع — Check consensus threshold
        if result.confidence < self.threshold:
            result.decision = "insufficient_consensus"
            result.confidence = 0.0

        return result

    def _unanimous_voting(self, votes: list[SwarmVote]) -> ConsensusResult:
        """
        تصويت إجماعي كامل — Unanimous voting.
        يتطلب موافقة جميع المُصوّتين.
        Requires agreement from all voters.
        """
        if not votes:
            return ConsensusResult(decision="no_votes", confidence=0.0, dissent_ratio=1.0)

        choices = set(v.choice for v in votes)
        if len(choices) == 1:
            # إجماع كامل — Full consensus
            return ConsensusResult(
                decision=votes[0].choice,
                confidence=1.0,
                dissent_ratio=0.0,
                agreement_count=len(votes),
            )
        else:
            # لا إجماع — No consensus
            return ConsensusResult(
                decision="no_unanimous_consensus",
                confidence=len([v for v in votes if v.choice == max(
                    set(v.choice for v in votes),
                    key=lambda c: sum(1 for v in votes if v.choice == c),
                )]) / len(votes),
                dissent_ratio=1.0 - (
                    len([v for v in votes if v.choice == max(
                        set(v.choice for v in votes),
                        key=lambda c: sum(1 for v in votes if v.choice == c),
                    )]) / len(votes)
                ),
                agreement_count=len([v for v in votes if v.choice == max(
                    set(v.choice for v in votes),
                    key=lambda c: sum(1 for v in votes if v.choice == c),
                )]),
                dissenting_opinions=list(choices),
            )

    def _detect_byzantine(self, votes: list[SwarmVote]) -> bool:
        """
        كشف السلوك البيزنطي — Detect Byzantine (malicious) voting behavior.
        يكشف الوكلاء الذين يصوتون بشكل متناقض أو غير مبرر.
        Detects agents who vote inconsistently or without justification.
        """
        if len(votes) < 3:
            return False

        # فحص التناقض مع التاريخ — Check inconsistency with history
        if len(self._vote_history) < 2:
            return False

        recent = self._vote_history[-1]
        voter_choices: dict[str, list[str]] = defaultdict(list)

        for vote in recent:
            voter_choices[vote.voter_id].append(vote.choice)

        # الوكلاء الذين غيروا رأيهم بشكل متكرر — Frequently flipping voters
        byzantine_count = 0
        for voter_id, choices in voter_choices.items():
            unique_choices = set(choices)
            if len(unique_choices) > 1:
                byzantine_count += 1
                self._byzantine_agents.add(voter_id)

        # كشف إذا تجاوزت نسبة البيزنطيين العتبة — Check if Byzantine ratio exceeds threshold
        byzantine_ratio = byzantine_count / len(voter_choices) if voter_choices else 0.0
        if byzantine_ratio > CONSENSUS_BYZANTINE_THRESHOLD:
            logger.warning(
                "تم كشف سلوك بيزنطي: %.1f%% من المُصوّتين — "
                "Byzantine behavior detected: %.1f%% of voters",
                byzantine_ratio * 100, byzantine_ratio * 100,
            )
            return True

        return False

    def _filter_byzantine(self, votes: list[SwarmVote]) -> list[SwarmVote]:
        """
        تصفية الأصوات البيزنطية — Filter votes from suspected Byzantine agents.
        يزيل أصوات الوكلاء المشبوهين من الحساب.
        """
        filtered = [v for v in votes if v.voter_id not in self._byzantine_agents]
        if not filtered:
            # إذا تمت تصفية الجميع، نعيد الأصوات الأصلية — fallback
            logger.warning(
                "تمت تصفية جميع الأصوات البيزنطية، العودة للأصلية — "
                "All votes filtered as Byzantine, falling back to original"
            )
            return votes
        return filtered

    def _resolve_conflict(
        self, votes: list[SwarmVote], initial_result: ConsensusResult
    ) -> ConsensusResult:
        """
        حل النزاعات — Resolve conflicts when consensus threshold not met.
        يطبق استراتيجية حل النزاعات لتحسين الإجماع.
        """
        result = initial_result

        if self.conflict_strategy == ConflictResolutionStrategy.MEDIATION:
            result = self._mediate_conflict(votes, result)
        elif self.conflict_strategy == ConflictResolutionStrategy.VOTING_OVERRIDE:
            result = self._weighted_voting(votes)
        elif self.conflict_strategy == ConflictResolutionStrategy.WEIGHTED_AVERAGE:
            result = self._weighted_average_resolution(votes, result)
        elif self.conflict_strategy == ConflictResolutionStrategy.RANDOM_TIEBREAK:
            if result.confidence < self.threshold:
                # اختيار عشوائي بين الأعلى تصويتاً — Random among top choices
                tally: dict[str, int] = defaultdict(int)
                for v in votes:
                    tally[v.choice] += 1
                max_count = max(tally.values()) if tally else 0
                top_choices = [c for c, cnt in tally.items() if cnt == max_count]
                result.decision = random.choice(top_choices) if top_choices else "no_decision"
                result.mediation_rounds = 1

        return result

    def _mediate_conflict(
        self, votes: list[SwarmVote], result: ConsensusResult
    ) -> ConsensusResult:
        """
        وساطة — Mediate conflict by weighting expert opinions more.
        يعطي وزناً أكبر للمُصوّتين ذوي الخبرة العالية والثقة الكبيرة.
        """
        for round_num in range(CONSENSUS_MEDIATION_ROUNDS):
            # إعادة التصويت بوزن متزايد للخبراء — Re-vote with increased expert weight
            adjusted_votes: list[SwarmVote] = []
            for vote in votes:
                adjusted = SwarmVote(
                    voter_id=vote.voter_id,
                    choice=vote.choice,
                    weight=vote.weight * (1.0 + 0.5 * vote.confidence),
                    confidence=vote.confidence,
                    reasoning=vote.reasoning,
                    timestamp=vote.timestamp,
                )
                adjusted_votes.append(adjusted)

            result = self._weighted_voting(adjusted_votes)
            result.mediation_rounds = round_num + 1

            if result.confidence >= self.threshold:
                break

        return result

    def _weighted_average_resolution(
        self, votes: list[SwarmVote], result: ConsensusResult
    ) -> ConsensusResult:
        """
        متوسط مرجح — Weighted average resolution for numeric choices.
        يحسب المتوسط المرجح إذا كانت الخيارات رقمية.
        """
        numeric_votes: list[tuple[float, float]] = []
        non_numeric: list[SwarmVote] = []

        for vote in votes:
            try:
                value = float(vote.choice)
                numeric_votes.append((value, vote.weight * vote.confidence))
            except (ValueError, TypeError):
                non_numeric.append(vote)

        if numeric_votes:
            total_weight = sum(w for _, w in numeric_votes)
            if total_weight > 0:
                weighted_avg = sum(v * w for v, w in numeric_votes) / total_weight
                result.decision = str(round(weighted_avg, 4))
                result.mediation_rounds = 1

        return result


# ═══════════════════════════════════════════════════════════════════════════════
# قناة الستيغميرجي — StigmergyChannel
# ═══════════════════════════════════════════════════════════════════════════════

class StigmergyChannel:
    """
    قناة الستيغميرجي — الاتصال غير المباشر عبر تعديل البيئة المشتركة.
    Stigmergy channel for indirect inter-agent communication.

    مستوحى من اتصال النمل عبر الفيرومونات:
    الوكلاء يتركون علامات في البيئة المشتركة ويقرأون علامات الآخرين لاحقاً.
   Agents deposit markers in the shared environment and read others' markers later.

    الآليات:
        - إيداع الفيرومون: ترك علامة في مسار معين
        - تبخر الفيرومون: تناقص قوة العلامة مع الوقت
        - اتباع المسار: اختيار المسار بناءً على قوة الفيرومون
        - مشاركة حالة البيئة: بث حالة البيئة للوكلاء
    """

    def __init__(
        self,
        decay_rate: float = SWARM_PHEROMONE_DECAY,
        alpha: float = PHEROMONE_ALPHA,
        beta: float = PHEROMONE_BETA,
    ):
        """
        تهيئة قناة الستيغميرجي.

        Args:
            decay_rate: معدل تبخر الفيرومون (0-1)
            alpha: معامل تأثير الفيرومون على اختيار المسار
            beta: معامل جاذبية المسار
        """
        self.decay_rate = decay_rate
        self.alpha = alpha
        self.beta = beta
        self._trails: dict[str, PheromoneTrail] = {}
        self._messages: dict[str, StigmergyMessage] = {}
        self._environment_state: dict[str, dict] = defaultdict(dict)

    def deposit(
        self,
        agent_id: str,
        path: list[str],
        pheromone_type: PheromoneType = PheromoneType.PATH,
        strength: float = PHEROMONE_DEPOSIT_BASE,
        channel: str = "default",
    ) -> PheromoneTrail:
        """
        إيداع الفيرومون — Deposit pheromone on a path.
        يترك الوكيل علامة فيرومون على مسار في البيئة المشتركة.

        Args:
            agent_id: معرف الوكيل المودع
            path: المسار (تسلسل عقد)
            pheromone_type: نوع الفيرومون
            strength: قوة الفيرومون المودع
            channel: قناة الاتصال

        Returns:
            PheromoneTrail — مسار الفيرومون المُحدَّث
        """
        trail_key = f"{channel}:{':'.join(path)}"

        now = time.time()
        if trail_key in self._trails:
            # تعزيز مسار موجود — Reinforce existing trail
            trail = self._trails[trail_key]
            # τ = (1-ρ)*τ + Δτ — Pheromone update rule
            trail.strength = (1.0 - self.decay_rate) * trail.strength + strength
            trail.last_reinforced = now
            trail.visit_count += 1
            logger.debug(
                "تعزيز فيرومون على المسار %s: قوة=%.4f — "
                "Reinforced pheromone on path %s: strength=%.4f",
                trail_key, trail.strength, trail_key, trail.strength,
            )
        else:
            # إنشاء مسار جديد — Create new trail
            trail = PheromoneTrail(
                id=f"trail_{uuid.uuid4().hex[:8]}",
                path=list(path),
                strength=PHEROMONE_INITIAL_STRENGTH + strength,
                decay_rate=self.decay_rate,
                pheromone_type=pheromone_type,
                creator_id=agent_id,
                created_at=now,
                last_reinforced=now,
                visit_count=1,
            )
            self._trails[trail_key] = trail
            logger.debug(
                "إيداع فيرومون جديد على المسار %s — "
                "New pheromone deposit on path %s",
                trail_key, trail_key,
            )

        return trail

    def evaporate(self) -> int:
        """
        تبخر الفيرومون — Evaporate all pheromone trails.
        يقلل قوة جميع المسارات بنسبة التبخر ويحذف المسارات المنتهية.
        Reduces all trail strengths by decay rate and removes expired trails.

        Returns:
            عدد المسارات المتبقية — Number of remaining trails
        """
        now = time.time()
        expired_keys: list[str] = []

        for key, trail in self._trails.items():
            # τ = (1-ρ)*τ — Evaporation rule
            trail.strength *= (1.0 - self.decay_rate)

            # حذف المسارات الضعيفة جداً — Remove very weak trails
            if trail.strength < 0.01:
                expired_keys.append(key)

        for key in expired_keys:
            del self._trails[key]

        # تبخر الرسائل منتهية الصلاحية — Expire old messages
        expired_msg_keys: list[str] = []
        for key, msg in self._messages.items():
            if now - msg.created_at > msg.ttl:
                expired_msg_keys.append(key)

        for key in expired_msg_keys:
            del self._messages[key]

        if expired_keys or expired_msg_keys:
            logger.debug(
                "تبخر: حُذف %d مسار و%d رسالة — "
                "Evaporation: removed %d trails, %d messages",
                len(expired_keys), len(expired_msg_keys),
                len(expired_keys), len(expired_msg_keys),
            )

        return len(self._trails)

    def follow_trail(
        self,
        current_node: str,
        available_nodes: list[str],
        channel: str = "default",
    ) -> str:
        """
        اتباع المسار — Choose next node based on pheromone trail strengths.
        يختار العقدة التالية بناءً على احتمالية تناسبية لقوة الفيرومون.

        احتمالية الاختيار: P = τ^α / Σ(τ^α)
        Selection probability: proportional to τ^α / Σ(τ^α)

        Args:
            current_node: العقدة الحالية
            available_nodes: العقد المتاحة للانتقال إليها
            channel: قناة الاتصال

        Returns:
            العقدة المختارة — Selected next node
        """
        if not available_nodes:
            return current_node

        # حساب قوة الفيرومون لكل عقدة متاحة — Compute pheromone for each available node
        pheromone_strengths: dict[str, float] = {}

        for node in available_nodes:
            trail_key = f"{channel}:{current_node}:{node}"
            if trail_key in self._trails:
                strength = self._trails[trail_key].strength
                pheromone_strengths[node] = strength ** self.alpha
            else:
                # قيمة افتراضية صغيرة — Small default value for unexplored paths
                pheromone_strengths[node] = 0.1 ** self.alpha

        # اختيار تناسبي — Proportional selection
        total = sum(pheromone_strengths.values())
        if total <= 0:
            return random.choice(available_nodes)

        # عجلة الروليت — Roulette wheel selection
        r = random.random() * total
        cumulative = 0.0
        for node, strength in pheromone_strengths.items():
            cumulative += strength
            if r <= cumulative:
                return node

        return available_nodes[-1]

    def communicate(
        self,
        agent_id: str,
        message: str,
        channel: str = "default",
        pheromone_type: PheromoneType = PheromoneType.PATH,
        strength: float = PHEROMONE_DEPOSIT_BASE,
        ttl: float = 3600.0,
    ) -> StigmergyMessage:
        """
        تواصل ستيغميرجي — Deposit a stigmergic message in the environment.
        يترك الوكيل رسالة في البيئة المشتركة ليقرأها آخرون لاحقاً.

        Args:
            agent_id: معرف المُرسل
            message: محتوى الرسالة
            channel: قناة الاتصال
            pheromone_type: نوع الفيرومون
            strength: قوة الرسالة
            ttl: وقت الحياة بالثواني

        Returns:
            StigmergyMessage — الرسالة المُودعة
        """
        now = time.time()
        msg = StigmergyMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            sender_id=agent_id,
            channel=channel,
            content=message,
            pheromone_type=pheromone_type,
            strength=strength,
            created_at=now,
            ttl=ttl,
        )

        self._messages[msg.id] = msg

        logger.debug(
            "رسالة ستيغميرجي من %s على القناة %s: '%s' — "
            "Stigmergy message from %s on channel %s: '%s'",
            agent_id, channel, message[:50],
            agent_id, channel, message[:50],
        )

        return msg

    def read_messages(
        self,
        channel: str = "default",
        agent_id: str = "",
        limit: int = 20,
    ) -> list[StigmergyMessage]:
        """
        قراءة الرسائل — Read stigmergic messages from the environment.
        يقرأ الرسائل المتاحة في القناة المحددة.

        Args:
            channel: قناة الاتصال
            agent_id: معرف الوكيل القارئ (للتصفية)
            limit: أقصى عدد رسائل

        Returns:
            قائمة الرسائل — List of messages
        """
        now = time.time()
        messages: list[StigmergyMessage] = []

        for msg in self._messages.values():
            # تصفية حسب القناة — Filter by channel
            if msg.channel != channel:
                continue
            # تصفية حسب الصلاحية — Filter by TTL
            if now - msg.created_at > msg.ttl:
                continue
            # لا يقرأ رسائله الخاصة — Don't read own messages
            if agent_id and msg.sender_id == agent_id:
                continue

            messages.append(msg)

        # ترتيب حسب القوة — Sort by strength (strongest first)
        messages.sort(key=lambda m: m.strength, reverse=True)
        return messages[:limit]

    def update_environment_state(
        self, key: str, state: dict, channel: str = "default"
    ) -> None:
        """
        تحديث حالة البيئة — Update shared environment state.
        يحدّث حالة البيئة المشتركة ليتاح لجميع الوكلاء قراءتها.
        """
        self._environment_state[channel][key] = {
            **state,
            "_updated_at": time.time(),
        }

    def get_environment_state(
        self, channel: str = "default", key: str = ""
    ) -> dict:
        """
        الحصول على حالة البيئة — Get shared environment state.
        يقرأ الحالة الحالية للبيئة المشتركة.
        """
        channel_state = self._environment_state.get(channel, {})
        if key:
            return channel_state.get(key, {})
        return dict(channel_state)

    def get_trails(self, channel: str = "default") -> list[PheromoneTrail]:
        """
        الحصول على المسارات — Get all active pheromone trails.
        """
        return [
            trail for key, trail in self._trails.items()
            if key.startswith(f"{channel}:")
        ]

    def get_stats(self) -> dict:
        """
        إحصائيات القناة — Channel statistics.
        """
        return {
            "active_trails": len(self._trails),
            "active_messages": len(self._messages),
            "channels": list(self._environment_state.keys()),
            "decay_rate": self.decay_rate,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# مخصّص المهام — TaskAllocator
# ═══════════════════════════════════════════════════════════════════════════════

class TaskAllocator:
    """
    مخصّص المهام — تخصيص المهام المستوحى من خوارزمية النحل.
    Bee-algorithm inspired task allocator for agent-task assignment.

    مستوحى من سلوك نحل العسل في البحث عن الغذاء:
        - الكشافون: يستكشفون مناطق جديدة من فضاء الحل
        - الجوّالون: يستغلون المصادر المعروفة الواعدة
        - العمال: ينفذون المهام المخصصة بكفاءة

    Inspired by honeybee foraging behavior:
        - Scouts: explore new regions of the solution space
        - Foragers: exploit known promising sources
        - Workers: execute assigned tasks efficiently
    """

    def __init__(
        self,
        scout_ratio: float = TASK_SCOUT_RATIO,
        forager_ratio: float = TASK_FORAGER_RATIO,
        worker_ratio: float = TASK_WORKER_RATIO,
    ):
        """
        تهيئة مخصّص المهام.

        Args:
            scout_ratio: نسبة وكلاء الكشف (0-1)
            forager_ratio: نسبة وكلاء الاستغلال (0-1)
            worker_ratio: نسبة وكلاء التنفيذ (0-1)
        """
        # تطبيع النسب — Normalize ratios
        total = scout_ratio + forager_ratio + worker_ratio
        self.scout_ratio = scout_ratio / total
        self.forager_ratio = forager_ratio / total
        self.worker_ratio = worker_ratio / total

        self._assignments: dict[str, TaskAssignment] = {}
        self._task_history: list[dict] = []
        self._last_reallocation: float = 0.0
        self._completion_rates: dict[str, float] = defaultdict(float)

    def allocate_tasks(
        self,
        agents: list[dict],
        tasks: list[dict],
    ) -> list[TaskAssignment]:
        """
        تخصيص المهام — Allocate tasks to agents using bee-algorithm strategy.
        يخصص المهام للوكلاء بناءً على أدوارهم ولياقتهم.

        Args:
            agents: قائمة الوكلاء [{id, skills, expertise, workload}, ...]
            tasks: قائمة المهام [{id, type, priority, required_skills, estimated_duration}, ...]

        Returns:
            list[TaskAssignment] — قائمة التخصيصات
        """
        if not agents or not tasks:
            return []

        now = time.time()
        assignments: list[TaskAssignment] = []

        # تقسيم الوكلاء لأدوار — Assign roles to agents
        n_agents = len(agents)
        n_scouts = max(1, int(n_agents * self.scout_ratio))
        n_foragers = max(1, int(n_agents * self.forager_ratio))
        n_workers = n_agents - n_scouts - n_foragers

        # خلط الوكلاء لضمان العدالة — Shuffle for fairness
        shuffled_agents = list(agents)
        random.shuffle(shuffled_agents)

        scout_agents = shuffled_agents[:n_scouts]
        forager_agents = shuffled_agents[n_scouts:n_scouts + n_foragers]
        worker_agents = shuffled_agents[n_scouts + n_foragers:]

        # ترتيب المهام حسب الأولوية — Sort tasks by priority
        sorted_tasks = sorted(
            tasks, key=lambda t: t.get("priority", 0.5), reverse=True
        )

        # تخصيص مهام الكشافة (استكشاف) — Scout assignments (exploration)
        scout_tasks = [t for t in sorted_tasks if t.get("type") == "exploration"]
        if not scout_tasks:
            scout_tasks = sorted_tasks[:n_scouts]  # fallback

        for i, agent in enumerate(scout_agents):
            task = scout_tasks[i % len(scout_tasks)] if scout_tasks else None
            if task:
                fitness = self._compute_fitness(agent, task)
                assignment = TaskAssignment(
                    agent_id=agent.get("id", f"agent_{i}"),
                    task_id=task.get("id", f"task_{i}"),
                    fitness=fitness,
                    priority=task.get("priority", 0.5),
                    role=AgentRole.SCOUT,
                    estimated_duration=task.get("estimated_duration", 0.0),
                    assigned_at=now,
                )
                assignments.append(assignment)
                self._assignments[assignment.agent_id] = assignment

        # تخصيص مهام الجوّالين (استغلال) — Forager assignments (exploitation)
        forager_tasks = [t for t in sorted_tasks if t.get("type") != "exploration"]
        if not forager_tasks:
            forager_tasks = sorted_tasks

        for i, agent in enumerate(forager_agents):
            # اختيار المهمة الأكثر ملاءمة — Choose best-fitting task
            best_task = None
            best_fitness = -1.0
            for task in forager_tasks:
                fitness = self._compute_fitness(agent, task)
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_task = task

            if best_task:
                assignment = TaskAssignment(
                    agent_id=agent.get("id", f"agent_{i + n_scouts}"),
                    task_id=best_task.get("id", f"task_{i + n_scouts}"),
                    fitness=best_fitness,
                    priority=best_task.get("priority", 0.5),
                    role=AgentRole.FORAGER,
                    estimated_duration=best_task.get("estimated_duration", 0.0),
                    assigned_at=now,
                )
                assignments.append(assignment)
                self._assignments[assignment.agent_id] = assignment

        # تخصيص مهام العمال (تنفيذ) — Worker assignments (execution)
        remaining_tasks = [
            t for t in sorted_tasks
            if t.get("id") not in {a.task_id for a in assignments}
        ]

        for i, agent in enumerate(worker_agents):
            task = remaining_tasks[i % len(remaining_tasks)] if remaining_tasks else None
            if task:
                fitness = self._compute_fitness(agent, task)
                assignment = TaskAssignment(
                    agent_id=agent.get("id", f"agent_{i + n_scouts + n_foragers}"),
                    task_id=task.get("id", f"task_{i + n_scouts + n_foragers}"),
                    fitness=fitness,
                    priority=task.get("priority", 0.5),
                    role=AgentRole.WORKER,
                    estimated_duration=task.get("estimated_duration", 0.0),
                    assigned_at=now,
                )
                assignments.append(assignment)
                self._assignments[assignment.agent_id] = assignment

        # حفظ سجل التخصيص — Save assignment history
        self._task_history.append({
            "timestamp": now,
            "assignments": [a.to_dict() for a in assignments],
            "agent_count": len(agents),
            "task_count": len(tasks),
        })

        logger.debug(
            "تم تخصيص %d مهمة لـ %d وكيل (كشافة=%d، جوّالون=%d، عمال=%d) — "
            "Allocated %d tasks to %d agents (scouts=%d, foragers=%d, workers=%d)",
            len(assignments), len(agents), n_scouts, n_foragers, n_workers,
            len(assignments), len(agents), n_scouts, n_foragers, n_workers,
        )

        return assignments

    def _compute_fitness(self, agent: dict, task: dict) -> float:
        """
        حساب اللياقة — Compute agent-task fitness score.
        يحسب مدى ملاءمة الوكيل للمهمة بناءً على المهارات والخبرة والحمل.
        """
        agent_skills = set(agent.get("skills", []))
        required_skills = set(task.get("required_skills", []))

        if not required_skills:
            skill_match = 0.5  # لا متطلبات — no requirements
        elif not agent_skills:
            skill_match = 0.1  # لا مهارات — no skills
        else:
            # نسبة تطابق المهارات — Skill match ratio
            overlap = agent_skills & required_skills
            skill_match = len(overlap) / len(required_skills)

        # عامل الخبرة — Expertise factor
        expertise = min(1.0, agent.get("expertise", 0.5))

        # عامل الحمل — Workload factor (أقل حمل = أفضل)
        workload = agent.get("workload", 0.0)
        availability = max(0.0, 1.0 - workload)

        # لياقة مركبة — Composite fitness
        fitness = (
            0.5 * skill_match +
            0.3 * expertise +
            0.2 * availability
        )

        return max(0.0, min(1.0, fitness))

    def reallocate(
        self,
        agents: list[dict],
        tasks: list[dict],
        completion_rates: dict[str, float] | None = None,
    ) -> list[TaskAssignment]:
        """
        إعادة التخصيص — Dynamically reallocate tasks based on completion rates.
        يعيد تخصيص المهام بناءً على معدلات الإنجاز المتغيرة.

        Args:
            agents: قائمة الوكلاء المحدّثة
            tasks: قائمة المهام المحدّثة
            completion_rates: معدلات إنجاز المهام {task_id: rate}

        Returns:
            list[TaskAssignment] — التخصيصات الجديدة
        """
        now = time.time()

        # فحص إذا حان وقت إعادة التخصيص — Check if reallocation is due
        if now - self._last_reallocation < TASK_REALLOCATION_INTERVAL:
            return list(self._assignments.values())

        self._last_reallocation = now

        # تحديث معدلات الإنجاز — Update completion rates
        if completion_rates:
            self._completion_rates.update(completion_rates)

        # زيادة نسبة الكشافة إذا كان الإنجاز بطيئاً — Increase scouts if slow
        avg_completion = (
            sum(self._completion_rates.values()) / len(self._completion_rates)
            if self._completion_rates else 0.5
        )

        if avg_completion < 0.3:
            # إنجاز بطيء → مزيد من الاستكشاف — Slow completion → more exploration
            adjusted_scout_ratio = min(0.4, self.scout_ratio + 0.1)
            allocator = TaskAllocator(
                scout_ratio=adjusted_scout_ratio,
                forager_ratio=self.forager_ratio - 0.05,
                worker_ratio=self.worker_ratio - 0.05,
            )
            return allocator.allocate_tasks(agents, tasks)

        return self.allocate_tasks(agents, tasks)

    def get_assignment(self, agent_id: str) -> Optional[TaskAssignment]:
        """
        الحصول على تخصيص وكيل — Get an agent's current task assignment.
        """
        return self._assignments.get(agent_id)

    def get_stats(self) -> dict:
        """
        إحصائيات التخصيص — Allocation statistics.
        """
        role_counts: dict[str, int] = defaultdict(int)
        total_fitness = 0.0

        for assignment in self._assignments.values():
            role_counts[assignment.role.value] += 1
            total_fitness += assignment.fitness

        avg_fitness = total_fitness / len(self._assignments) if self._assignments else 0.0

        return {
            "total_assignments": len(self._assignments),
            "role_distribution": dict(role_counts),
            "average_fitness": round(avg_fitness, 4),
            "history_size": len(self._task_history),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# محرك الذكاء السربي الرئيسي — SwarmIntelligenceEngine
# ═══════════════════════════════════════════════════════════════════════════════

class SwarmIntelligenceEngine:
    """
    محرك الذكاء السربي — المحرك الرئيسي للذكاء الجماعي اللامركزي.
    Main Swarm Intelligence engine for decentralized collective intelligence.

    يجمع أربعة محركات فرعية في بنية متكاملة:
        1. ParticleSwarmOptimizer — تحسين فضاء الحلول
        2. ConsensusEngine — اتخاذ القرار الجماعي
        3. StigmergyChannel — الاتصال غير المباشر
        4. TaskAllocator — تخصيص المهام

    Integrates four sub-engines in a cohesive architecture:
        1. ParticleSwarmOptimizer — solution-space optimization
        2. ConsensusEngine — collective decision-making
        3. StigmergyChannel — indirect communication
        4. TaskAllocator — task assignment

    Usage:
        engine = SwarmIntelligenceEngine()
        result = engine.optimize(objective_fn, dimensions=3)
        consensus = engine.reach_consensus(votes, protocol="weighted")
        engine.communicate("agent_1", "found resource at node B")
        assignments = engine.allocate_tasks(agents, tasks)
        stats = engine.get_stats()
    """

    def __init__(
        self,
        particle_count: int = SWARM_PARTICLE_COUNT,
        consensus_threshold: float = SWARM_CONSENSUS_THRESHOLD,
        pheromone_decay: float = SWARM_PHEROMONE_DECAY,
    ):
        """
        تهيئة محرك الذكاء السربي — Initialize the Swarm Intelligence engine.

        Args:
            particle_count: عدد جسيمات السرب
            consensus_threshold: عتبة الإجماع (0.5-1.0)
            pheromone_decay: معدل تبخر الفيرومون (0-1)
        """
        # تهيئة المحركات الفرعية — Initialize sub-engines
        self._pso = ParticleSwarmOptimizer(particle_count=particle_count)
        self._consensus = ConsensusEngine(threshold=consensus_threshold)
        self._stigmergy = StigmergyChannel(decay_rate=pheromone_decay)
        self._allocator = TaskAllocator()

        # إحصائيات الاستخدام — Usage statistics
        self._stats = {
            "optimize_calls": 0,
            "consensus_calls": 0,
            "communicate_calls": 0,
            "allocate_calls": 0,
            "total_particles_used": 0,
            "total_votes_processed": 0,
            "total_messages_deposited": 0,
            "total_tasks_assigned": 0,
        }

        self._initialized_at = time.time()

        if SWARM_ENABLED:
            logger.info(
                "تم تفعيل محرك الذكاء السربي — Swarm Intelligence engine enabled "
                "(particles=%d, consensus_threshold=%.2f, pheromone_decay=%.2f)",
                particle_count, consensus_threshold, pheromone_decay,
            )

    # ─── الواجهة الرئيسية — Public API ────────────────────────────────────

    def optimize(
        self,
        objective_fn: Callable[[list[float]], float],
        dimensions: int = 2,
        bounds: list[tuple[float, float]] | None = None,
        max_iterations: int = PSO_DEFAULT_ITERATIONS,
        constraints: list[Callable[[list[float]], bool]] | None = None,
        multi_objective: bool = False,
        objective_fns: list[Callable[[list[float]], float]] | None = None,
    ) -> OptimizationResult:
        """
        تحسين — Optimize an objective function using Particle Swarm Optimization.
        يحسّن دالة هدف باستخدام تحسين سرب الجسيمات.

        Args:
            objective_fn: دالة الهدف لتقليلها
            dimensions: عدد أبعاد فضاء الحل
            bounds: حدود كل بعد
            max_iterations: أقصى عدد تكرارات
            constraints: قيود على الحلول
            multi_objective: تحسين متعدد الأهداف
            objective_fns: قائمة دوال الأهداف

        Returns:
            OptimizationResult — نتيجة التحسين
        """
        self._stats["optimize_calls"] += 1

        # إعادة تهيئة PSO بأبعاد جديدة — Reinitialize PSO with new dimensions
        self._pso = ParticleSwarmOptimizer(
            particle_count=SWARM_PARTICLE_COUNT,
            dimensions=dimensions,
            bounds=bounds,
        )
        self._pso.initialize()

        self._stats["total_particles_used"] += self._pso.particle_count

        # تنفيذ التحسين — Run optimization
        result = self._pso.optimize(
            objective_fn=objective_fn,
            max_iterations=max_iterations,
            constraints=constraints,
            multi_objective=multi_objective,
            objective_fns=objective_fns,
        )

        # مشاركة النتيجة عبر قناة الستيغميرجي — Share result via stigmergy
        if result.converged:
            self._stigmergy.communicate(
                agent_id="swarm_engine",
                message=f"optimization_converged:fitness={result.best_fitness:.6f}",
                channel="optimization",
                pheromone_type=PheromoneType.COMPLETED,
            )

        logger.info(
            "نتيجة التحسين: لياقة=%.6f تقارب=%s تكرارات=%d — "
            "Optimization result: fitness=%.6f converged=%s iterations=%d",
            result.best_fitness, result.converged, result.iterations_used,
            result.best_fitness, result.converged, result.iterations_used,
        )

        return result

    def reach_consensus(
        self,
        votes: list[SwarmVote],
        protocol: VotingProtocol = VotingProtocol.SIMPLE_MAJORITY,
        quorum_requirement: float = CONSENSUS_QUORUM_MIN,
    ) -> ConsensusResult:
        """
        الوصول للإجماع — Reach consensus from a set of distributed votes.
        يصل لقرار جماعي من مجموعة أصوات موزعة.

        Args:
            votes: قائمة الأصوات
            protocol: بروتوكول التصويت
            quorum_requirement: متطلب النصاب

        Returns:
            ConsensusResult — نتيجة الإجماع
        """
        self._stats["consensus_calls"] += 1
        self._stats["total_votes_processed"] += len(votes)

        result = self._consensus.reach_consensus(
            votes=votes,
            protocol=protocol,
            quorum_requirement=quorum_requirement,
        )

        # مشاركة القرار عبر الستيغميرجي — Share decision via stigmergy
        self._stigmergy.communicate(
            agent_id="consensus_engine",
            message=f"consensus_reached:decision={result.decision}:confidence={result.confidence:.4f}",
            channel="consensus",
            pheromone_type=PheromoneType.COMPLETED,
        )

        return result

    def communicate(
        self,
        agent_id: str,
        message: str,
        channel: str = "default",
        pheromone_type: PheromoneType = PheromoneType.PATH,
        strength: float = PHEROMONE_DEPOSIT_BASE,
        path: list[str] | None = None,
        ttl: float = 3600.0,
    ) -> dict:
        """
        تواصل — Communicate via stigmergy channel.
        يتواصل الوكيل عبر قناة الستيغميرجي (اتصال غير مباشر).

        Args:
            agent_id: معرف الوكيل المُرسل
            message: محتوى الرسالة
            channel: قناة الاتصال
            pheromone_type: نوع الفيرومون
            strength: قوة الرسالة
            path: مسار الفيرومون (اختياري)
            ttl: وقت الحياة

        Returns:
            قاموس يتضمن الرسالة والمسار — Dict with message and trail info
        """
        self._stats["communicate_calls"] += 1
        self._stats["total_messages_deposited"] += 1

        # إيداع رسالة ستيغميرجي — Deposit stigmergy message
        msg = self._stigmergy.communicate(
            agent_id=agent_id,
            message=message,
            channel=channel,
            pheromone_type=pheromone_type,
            strength=strength,
            ttl=ttl,
        )

        # إيداع فيرومون على المسار إذا توفر — Deposit pheromone on path if provided
        trail = None
        if path:
            trail = self._stigmergy.deposit(
                agent_id=agent_id,
                path=path,
                pheromone_type=pheromone_type,
                strength=strength,
                channel=channel,
            )

        return {
            "message": msg.to_dict(),
            "trail": trail.to_dict() if trail else None,
        }

    def allocate_tasks(
        self,
        agents: list[dict],
        tasks: list[dict],
    ) -> list[TaskAssignment]:
        """
        تخصيص المهام — Allocate tasks to agents using bee-algorithm strategy.
        يخصص المهام للوكلاء باستخدام استراتيجية خوارزمية النحل.

        Args:
            agents: قائمة الوكلاء [{id, skills, expertise, workload}, ...]
            tasks: قائمة المهام [{id, type, priority, required_skills, estimated_duration}, ...]

        Returns:
            list[TaskAssignment] — قائمة التخصيصات
        """
        self._stats["allocate_calls"] += 1

        assignments = self._allocator.allocate_tasks(agents, tasks)

        self._stats["total_tasks_assigned"] += len(assignments)

        # إيداع فيرومون اكتمال لكل تخصيص — Deposit completion pheromone per assignment
        for assignment in assignments:
            self._stigmergy.deposit(
                agent_id=assignment.agent_id,
                path=[assignment.agent_id, assignment.task_id],
                pheromone_type=PheromoneType.RESOURCE,
                strength=assignment.fitness * 0.5,
                channel="task_allocation",
            )

        return assignments

    def read_environment(
        self,
        channel: str = "default",
        agent_id: str = "",
        limit: int = 20,
    ) -> dict:
        """
        قراءة البيئة — Read the shared stigmergic environment.
        يقرأ الوكيل حالة البيئة المشتركة والرسائل المتاحة.

        Args:
            channel: قناة الاتصال
            agent_id: معرف الوكيل القارئ
            limit: أقصى عدد رسائل

        Returns:
            قاموس يتضمن الرسائل والمسارات وحالة البيئة
        """
        messages = self._stigmergy.read_messages(
            channel=channel, agent_id=agent_id, limit=limit
        )
        trails = self._stigmergy.get_trails(channel=channel)
        env_state = self._stigmergy.get_environment_state(channel=channel)

        return {
            "messages": [m.to_dict() for m in messages],
            "trails": [t.to_dict() for t in trails],
            "environment_state": env_state,
        }

    def evaporate_pheromones(self) -> int:
        """
        تبخر الفيرومونات — Trigger pheromone evaporation cycle.
        ينفذ دورة تبخر الفيرومونات لتنظيف المسارات المنتهية.

        Returns:
            عدد المسارات المتبقية — Number of remaining trails
        """
        return self._stigmergy.evaporate()

    def reallocate_tasks(
        self,
        agents: list[dict],
        tasks: list[dict],
        completion_rates: dict[str, float] | None = None,
    ) -> list[TaskAssignment]:
        """
        إعادة تخصيص المهام — Dynamically reallocate tasks.
        يعيد تخصيص المهام بناءً على معدلات الإنجاز المتغيرة.

        Args:
            agents: قائمة الوكلاء المحدّثة
            tasks: قائمة المهام المحدّثة
            completion_rates: معدلات إنجاز المهام

        Returns:
            list[TaskAssignment] — التخصيصات الجديدة
        """
        return self._allocator.reallocate(agents, tasks, completion_rates)

    def get_stats(self) -> dict:
        """
        إحصائيات المحرك — Engine statistics.
        يُرجع إحصائيات شاملة عن استخدام المحرك والمحركات الفرعية.
        """
        uptime = time.time() - self._initialized_at

        return {
            "enabled": SWARM_ENABLED,
            "uptime_seconds": round(uptime, 2),
            "engine_stats": dict(self._stats),
            "pso_stats": {
                "particle_count": self._pso.particle_count,
                "dimensions": self._pso.dimensions,
                "global_best_fitness": round(self._pso.global_best_fitness, 6)
                    if self._pso.global_best_fitness < float("inf") else None,
            },
            "consensus_stats": self._consensus.get_stats() if hasattr(self._consensus, 'get_stats') else {
                "threshold": self._consensus.threshold,
                "byzantine_agents": len(self._consensus._byzantine_agents),
                "vote_history_size": len(self._consensus._vote_history),
            },
            "stigmergy_stats": self._stigmergy.get_stats(),
            "allocator_stats": self._allocator.get_stats(),
            "env_config": {
                "MAMOUN_SWARM_INTELLIGENCE_ENABLED": SWARM_ENABLED,
                "MAMOUN_SWARM_PARTICLE_COUNT": SWARM_PARTICLE_COUNT,
                "MAMOUN_SWARM_CONSENSUS_THRESHOLD": SWARM_CONSENSUS_THRESHOLD,
                "MAMOUN_SWARM_PHEROMONE_DECAY": SWARM_PHEROMONE_DECAY,
            },
        }

    def reset(self) -> None:
        """
        إعادة تعيين — Reset all sub-engines.
        يعيد تعيين جميع المحركات الفرعية لحالة ابتدائية.
        """
        self._pso = ParticleSwarmOptimizer(particle_count=SWARM_PARTICLE_COUNT)
        self._consensus = ConsensusEngine(threshold=SWARM_CONSENSUS_THRESHOLD)
        self._stigmergy = StigmergyChannel(decay_rate=SWARM_PHEROMONE_DECAY)
        self._allocator = TaskAllocator()
        self._initialized_at = time.time()

        logger.info("تم إعادة تعيين محرك الذكاء السربي — Swarm Intelligence engine reset")


# ═══════════════════════════════════════════════════════════════════════════════
# نقطة الدخول — Module Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

def create_engine(
    particle_count: int = SWARM_PARTICLE_COUNT,
    consensus_threshold: float = SWARM_CONSENSUS_THRESHOLD,
    pheromone_decay: float = SWARM_PHEROMONE_DECAY,
) -> SwarmIntelligenceEngine:
    """
    إنشاء محرك الذكاء السربي — Factory function for creating a SwarmIntelligenceEngine.
    دالة مصنع لإنشاء محرك الذكاء السربي بالإعدادات المحددة.

    Args:
        particle_count: عدد جسيمات السرب
        consensus_threshold: عتبة الإجماع
        pheromone_decay: معدل تبخر الفيرومون

    Returns:
        SwarmIntelligenceEngine — محرك الذكاء السربي
    """
    return SwarmIntelligenceEngine(
        particle_count=particle_count,
        consensus_threshold=consensus_threshold,
        pheromone_decay=pheromone_decay,
    )


# تصدير الواجهة العامة — Public API exports
__all__ = [
    # المحرك الرئيسي — Main engine
    "SwarmIntelligenceEngine",
    "create_engine",
    # المحركات الفرعية — Sub-engines
    "ParticleSwarmOptimizer",
    "ConsensusEngine",
    "StigmergyChannel",
    "TaskAllocator",
    # هياكل البيانات — Data structures
    "Particle",
    "PheromoneTrail",
    "SwarmVote",
    "ConsensusResult",
    "TaskAssignment",
    "OptimizationResult",
    "StigmergyMessage",
    "SwarmIntelligenceResult",
    # التعدادات — Enumerations
    "VotingProtocol",
    "AgentRole",
    "PheromoneType",
    "ConflictResolutionStrategy",
    # إعدادات البيئة — Environment config
    "SWARM_ENABLED",
    "SWARM_PARTICLE_COUNT",
    "SWARM_CONSENSUS_THRESHOLD",
    "SWARM_PHEROMONE_DECAY",
]
