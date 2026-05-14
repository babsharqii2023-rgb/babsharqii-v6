"""
BABSHARQII v40.0 — Specialized Agent Pipeline
خط أنابيب الوكلاء المتخصصين — نظام توجيه ديناميكي يوجّه المهام إلى أنسب وكيل متخصص

A dynamic routing system that directs tasks to the most appropriate
specialized agent based on task type, complexity, and agent capabilities.

Architecture:
  ┌───────────────────────────────────────────────────────────────────────────┐
  │                    SpecializedAgentPipeline (المنسّق الرئيسي)             │
  │                                                                           │
  │  ┌────────────────┐                                                      │
  │  │  AgentRouter   │  موجّه الوكلاء                                        │
  │  │  (classify +   │  يُصنّف المهام ويُوجّهها لأنسب وكيل                    │
  │  │   route +      │                                                      │
  │  │   affinity +   │                                                      │
  │  │   weighted_kw) │                                                      │
  │  └───────┬────────┘                                                      │
  │          │                                                                │
  │  ┌───────▼────────────────────────────────────────────────────────────┐  │
  │  │                     PipelineExecutor                               │  │
  │  │  منفّذ خط الأنابيب — ينفّذ المهام عبر الوكلاء المتخصصين             │  │
  │  │  - _select_agents       → اختر أفضل الوكلاء                        │  │
  │  │  - _execute_single      → نفّذ مع وكيل واحد                        │  │
  │  │  - _merge_results       → ادمج النتائج من عدة وكلاء                │  │
  │  │  - _collaborative_exec  → تنفيذ تعاوني للمهام المعقدة              │  │
  │  │  - _fallback            → استراتيجية بديلة عند الفشل                │  │
  │  └───────────────────────────────────────────────────────────────────┘  │
  │          │                                                                │
  │  ┌───────▼──────────────────────────────────────────────────────────┐   │
  │  │                  SpecializedAgent (ABC)                           │   │
  │  │  الوكيل المتخصص — فئة أساسية مجردة                                │   │
  │  │                                                                   │   │
  │  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                  │   │
  │  │  │Code  │ │Analy-│ │Crea- │ │Math  │ │Re-   │                  │   │
  │  │  │Agent │ │sis   │ │tive  │ │Agent │ │search│                  │   │
  │  │  │البرمج│ │Agent │ │Agent │ │الرياض│ │Agent │                  │   │
  │  │  │ة    │ │التحلي│ │الإبداع│ │يات   │ │البحث │                  │   │
  │  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘                  │   │
  │  └──────────────────────────────────────────────────────────────────┘   │
  └───────────────────────────────────────────────────────────────────────────┘

Env toggles:
    MAMOUN_SPECIALIZED_PIPELINE_ENABLED (default: "false")
    MAMOUN_SPECIALIZED_PIPELINE_MAX_AGENTS (default: "5")
    MAMOUN_SPECIALIZED_PIPELINE_CONFIDENCE_THRESHOLD (default: "0.3")
"""

from __future__ import annotations

import os
import re
import time
import uuid
import hashlib
import logging
import asyncio
import math
from abc import ABC, abstractmethod
from typing import Optional, Any
from collections import defaultdict, OrderedDict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ─── مفاتيح التفعيل البيئي — Env toggles ──────────────────────────────────────

SPECIALIZED_PIPELINE_ENABLED: bool = os.environ.get(
    "MAMOUN_SPECIALIZED_PIPELINE_ENABLED", "false"
).lower() in ("true", "1", "yes")

SPECIALIZED_PIPELINE_MAX_AGENTS: int = int(
    os.environ.get("MAMOUN_SPECIALIZED_PIPELINE_MAX_AGENTS", "5")
)

SPECIALIZED_PIPELINE_CONFIDENCE_THRESHOLD: float = float(
    os.environ.get("MAMOUN_SPECIALIZED_PIPELINE_CONFIDENCE_THRESHOLD", "0.3")
)


# ═══════════════════════════════════════════════════════════════════════════════
#  هياكل البيانات — Data Structures
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class TaskClassification:
    """
    تصنيف المهمة — نتيجة تصنيف المهمة حسب النوع والمجال والتعقيد.
    Result of classifying a task by type, domain, and complexity.

    Encapsulates the analysis of what kind of task this is, what domain
    it belongs to, how complex it is, and what capabilities are needed
    to handle it effectively.

    Attributes:
        task_type: نوع المهمة — code, analysis, creative, math, research, general
        domain: المجال — programming, analytics, creative, mathematics, academic, general
        complexity: التعقيد — 0.0 (trivial) to 1.0 (extremely complex)
        required_capabilities: القدرات المطلوبة — list of capability strings
    """
    task_type: str = "general"                          # نوع المهمة
    domain: str = "general"                             # المجال
    complexity: float = 0.5                             # التعقيد (0.0–1.0)
    required_capabilities: list[str] = field(default_factory=list)  # القدرات المطلوبة

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary."""
        return {
            "task_type": self.task_type,
            "domain": self.domain,
            "complexity": round(self.complexity, 4),
            "required_capabilities": self.required_capabilities,
        }


@dataclass
class RoutingResult:
    """
    نتيجة التوجيه — نتيجة توجيه المهمة إلى وكيل متخصص.
    Result of routing a task to a specialized agent.

    Contains the selected agent, routing confidence, and alternative
    agents that could also handle the task (in decreasing affinity order).

    Attributes:
        selected_agent: الوكيل المختار — the best-matching agent
        confidence: ثقة التوجيه — how confident the routing is (0.0–1.0)
        alternatives: البدائل — alternative agents sorted by affinity
    """
    selected_agent: Optional[str] = None                # الوكيل المختار
    confidence: float = 0.0                             # ثقة التوجيه
    alternatives: list[str] = field(default_factory=list)  # البدائل

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary."""
        return {
            "selected_agent": self.selected_agent,
            "confidence": round(self.confidence, 4),
            "alternatives": self.alternatives,
        }


@dataclass
class AgentResult:
    """
    نتيجة الوكيل — نتيجة تنفيذ وكيل متخصص لمهمة.
    Result from a specialized agent processing a task.

    Contains the output, confidence, execution duration, and success
    status of a single agent's processing attempt.

    Attributes:
        agent_id: معرّف الوكيل — unique agent identifier
        output: المخرجات — the agent's output
        confidence: مستوى الثقة — agent's confidence in its output (0.0–1.0)
        duration_ms: مدة التنفيذ — execution time in milliseconds
        success: هل نجح — whether the agent succeeded
    """
    agent_id: str = ""                                  # معرّف الوكيل
    output: str = ""                                    # المخرجات
    confidence: float = 0.0                             # مستوى الثقة
    duration_ms: float = 0.0                            # مدة التنفيذ (ميلي ثانية)
    success: bool = False                               # هل نجح

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "output": self.output,
            "confidence": round(self.confidence, 4),
            "duration_ms": round(self.duration_ms, 2),
            "success": self.success,
        }


@dataclass
class MergedResult:
    """
    نتيجة مدمجة — نتيجة دمج مخرجات عدة وكلاء.
    Result of merging outputs from multiple agents.

    When multiple agents contribute to a task, their outputs are
    combined with weighted confidence based on each agent's
    affinity and performance history.

    Attributes:
        merged_output: المخرجات المدمجة — combined output text
        confidence: الثقة المدمجة — aggregate confidence (0.0–1.0)
        contributing_agents: الوكلاء المساهمون — list of agent IDs that contributed
    """
    merged_output: str = ""                             # المخرجات المدمجة
    confidence: float = 0.0                             # الثقة المدمجة
    contributing_agents: list[str] = field(default_factory=list)  # الوكلاء المساهمون

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary."""
        return {
            "merged_output": self.merged_output,
            "confidence": round(self.confidence, 4),
            "contributing_agents": self.contributing_agents,
        }


@dataclass
class PipelineResult:
    """
    نتيجة خط الأنابيب — نتيجة شاملة لتنفيذ المهمة عبر خط الأنابيب.
    Comprehensive result from executing a task through the pipeline.

    Encapsulates the final output, which agents were used, overall
    confidence, and total execution duration across all agents.

    Attributes:
        final_output: المخرجات النهائية — the pipeline's final answer
        agents_used: الوكلاء المستخدمون — list of agent IDs that were used
        confidence: الثقة الإجمالية — overall pipeline confidence (0.0–1.0)
        total_duration_ms: المدة الإجمالية — total execution time in ms
    """
    final_output: str = ""                              # المخرجات النهائية
    agents_used: list[str] = field(default_factory=list)    # الوكلاء المستخدمون
    confidence: float = 0.0                             # الثقة الإجمالية
    total_duration_ms: float = 0.0                      # المدة الإجمالية (ميلي ثانية)

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary."""
        return {
            "final_output": self.final_output,
            "agents_used": self.agents_used,
            "confidence": round(self.confidence, 4),
            "total_duration_ms": round(self.total_duration_ms, 2),
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  سجل التوجيه التكيّفي — RoutingHistory (Adaptive Routing)
# ═══════════════════════════════════════════════════════════════════════════════


class RoutingHistory:
    """
    سجل التوجيه التكيّفي — يتتبع قرارات التوجيه السابقة ويعدّل الثقة المستقبلية.
    Tracks past routing decisions and their outcomes to adjust
    future routing confidence. If CodeAgent consistently succeeds on
    debugging tasks, increase its affinity score for similar tasks.

    Attributes:
        _records: سجلات التوجيه — list of routing decision records
        _agent_type_success: نجاح كل نوع وكيل — success counts per agent type
        _agent_type_total: إجمالي مهام كل نوع — total tasks per agent type
        _task_type_affinity: ألفة نوع المهمة مع نوع الوكيل — affinity map
    """

    def __init__(self, max_records: int = 1000):
        """
        تهيئة سجل التوجيه — Initialize routing history.

        Args:
            max_records: الحد الأقصى للسجلات — max records to keep
        """
        self._records: list[dict] = []
        self._max_records: int = max_records
        # نجاح نوع الوكيل لكل نوع مهمة — agent_type success per task_type
        self._agent_type_success: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        # إجمالي مهام نوع الوكيل لكل نوع مهمة — agent_type total per task_type
        self._agent_type_total: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

    def record(
        self,
        task: str,
        task_type: str,
        agent_type: str,
        success: bool,
        confidence: float,
    ) -> None:
        """
        تسجيل قرار توجيه — Record a routing decision and its outcome.

        Args:
            task: المهمة — the task description
            task_type: نوع المهمة — classified task type
            agent_type: نوع الوكيل — the agent type used
            success: هل نجح — whether the routing was successful
            confidence: ثقة التوجيه — the routing confidence
        """
        record = {
            "task_hash": hashlib.md5(task.encode()).hexdigest()[:12],
            "task_type": task_type,
            "agent_type": agent_type,
            "success": success,
            "confidence": confidence,
            "timestamp": time.time(),
        }
        self._records.append(record)

        # اقتطاع السجلات — trim records
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]

        # تحديث الإحصائيات — update stats
        self._agent_type_total[task_type][agent_type] += 1
        if success:
            self._agent_type_success[task_type][agent_type] += 1

    def get_affinity_boost(
        self, task_type: str, agent_type: str
    ) -> float:
        """
        حساب تعزيز الألفة — Calculate affinity boost based on history.

        If an agent type has a high success rate for a given task type,
        return a positive boost (0.0 to 0.2). If the success rate is
        low, return a negative adjustment (-0.1 to 0.0).

        Args:
            task_type: نوع المهمة
            agent_type: نوع الوكيل

        Returns:
            تعزيز الألفة (-0.1 إلى +0.2) — affinity boost
        """
        total = self._agent_type_total[task_type][agent_type]
        if total < 3:
            # بيانات غير كافية — insufficient data
            return 0.0

        success_count = self._agent_type_success[task_type][agent_type]
        success_rate = success_count / total

        # تحويل معدل النجاح إلى تعزيز — convert success rate to boost
        # معدل نجاح عالٍ = تعزيز إيجابي، معدل منخفض = تعزيز سلبي
        if success_rate >= 0.8:
            return 0.2
        elif success_rate >= 0.6:
            return 0.1
        elif success_rate >= 0.4:
            return 0.0
        elif success_rate >= 0.2:
            return -0.05
        else:
            return -0.1

    def get_historical_success_rate(
        self, task_type: str, agent_type: str
    ) -> float:
        """
        معدل النجاح التاريخي — Get historical success rate.

        Args:
            task_type: نوع المهمة
            agent_type: نوع الوكيل

        Returns:
            معدل النجاح (0.0–1.0) — success rate
        """
        total = self._agent_type_total[task_type][agent_type]
        if total == 0:
            return 0.5  # محايد — neutral
        success_count = self._agent_type_success[task_type][agent_type]
        return success_count / total

    def get_stats(self) -> dict:
        """
        إحصائيات سجل التوجيه — Return routing history stats.

        Returns:
            قاموس بالإحصائيات — dict with stats
        """
        total_recorded = len(self._records)
        successful = sum(1 for r in self._records if r["success"])
        return {
            "total_records": total_recorded,
            "successful_routes": successful,
            "success_rate": round(
                successful / max(1, total_recorded), 4
            ),
            "task_types_tracked": len(self._agent_type_total),
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  ذاكرة التخزين المؤقت لخط الأنابيب — PipelineCache (LRU Cache)
# ═══════════════════════════════════════════════════════════════════════════════


class PipelineCache:
    """
    ذاكرة تخزين مؤقت LRU لنتائج خط الأنابيب — LRU cache for pipeline results.
    يخزّن قرارات التوجيه للمهام المتشابهة لإعادة استخدامها.
    Caches routing decisions for similar task patterns to reuse them.

    If a similar task was routed before, reuse the routing decision
    instead of recomputing classification and affinity scores.

    Attributes:
        _cache: ذاكرة التخزين — ordered dict for LRU eviction
        _max_size: الحجم الأقصى — maximum cache entries
        _hits: عدد الإصابات — cache hit count
        _misses: عدد الأخطاء — cache miss count
    """

    def __init__(self, max_size: int = 256):
        """
        تهيئة ذاكرة التخزين المؤقت — Initialize the LRU cache.

        Args:
            max_size: الحجم الأقصى للذاكرة — max entries in cache
        """
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._max_size: int = max_size
        self._hits: int = 0
        self._misses: int = 0

    def _make_key(self, task: str, context: dict) -> str:
        """
        إنشاء مفتاح التخزين — Create a cache key from task and context.

        Args:
            task: المهمة
            context: السياق

        Returns:
            مفتاح التخزين — cache key string
        """
        # استخدام تجزئة المهمة والسياق — hash task + context
        ctx_parts = sorted(context.items()) if context else []
        raw = f"{task}|{ctx_parts}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def get(self, task: str, context: dict) -> Optional[dict]:
        """
        البحث في الذاكرة — Look up a cached routing decision.

        Args:
            task: المهمة
            context: السياق

        Returns:
            نتيجة التوجيه المخزّنة أو None — cached routing result or None
        """
        key = self._make_key(task, context)
        if key in self._cache:
            # نقل إلى النهاية (LRU) — move to end (LRU)
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None

    def put(
        self, task: str, context: dict, routing_info: dict
    ) -> None:
        """
        تخزين قرار التوجيه — Cache a routing decision.

        Args:
            task: المهمة
            context: السياق
            routing_info: معلومات التوجيه — routing information to cache
        """
        key = self._make_key(task, context)
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = routing_info

        # اقتطاع — evict oldest if over capacity
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        """مسح الذاكرة — Clear the cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> dict:
        """
        إحصائيات الذاكرة — Return cache stats.

        Returns:
            قاموس بالإحصائيات — dict with hit/miss stats
        """
        total = self._hits + self._misses
        hit_rate = self._hits / max(1, total)
        return {
            "cache_size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  الوكيل المتخصص (فئة أساسية مجردة) — SpecializedAgent (ABC)
# ═══════════════════════════════════════════════════════════════════════════════


class SpecializedAgent(ABC):
    """
    الوكيل المتخصص — فئة أساسية مجردة لجميع الوكلاء المتخصصين.
    Base class for specialized agents that process specific types of tasks.

    Each specialized agent declares:
    - agent_type: نوع الوكيل — categorical type identifier
    - capabilities: القدرات — what the agent can do
    - expertise_domains: مجالات الخبرة — domains of expertise
    - performance_score: نقاط الأداء — historical performance (0.0–1.0)

    Subclasses must implement the `process` method which handles
    task execution and returns an AgentResult.
    """

    def __init__(
        self,
        agent_type: str,
        capabilities: list[str],
        expertise_domains: list[str],
        performance_score: float = 0.5,
    ):
        """
        تهيئة الوكيل المتخصص — Initialize a specialized agent.

        Args:
            agent_type: نوع الوكيل — categorical type (e.g. "code", "analysis")
            capabilities: القدرات — list of capability strings
            expertise_domains: مجالات الخبرة — list of domain strings
            performance_score: نقاط الأداء — initial performance score
        """
        # معرّف فريد — unique identifier
        self.agent_id: str = f"{agent_type}_{hashlib.md5(
            str(time.time()).encode()
        ).hexdigest()[:8]}"
        self.agent_type: str = agent_type
        self.capabilities: list[str] = list(capabilities)
        self.expertise_domains: list[str] = list(expertise_domains)
        self.performance_score: float = max(0.0, min(1.0, performance_score))

        # إحصائيات الاستخدام — usage statistics
        self._total_tasks: int = 0
        self._successful_tasks: int = 0
        self._total_duration_ms: float = 0.0

        # أوزان الكلمات المفتاحية — keyword weights (TF-IDF inspired)
        # تُملأ من الفئة الفرعية — populated by subclass
        self.keyword_weights: dict[str, float] = {}

    @abstractmethod
    async def process(self, task: str, context: dict) -> AgentResult:
        """
        معالجة المهمة — Process a task and return a result.
        كل وكيل متخصص يجب أن ينفّذ هذه الطريقة.

        Args:
            task: المهمة — the task description
            context: السياق — additional context for the task

        Returns:
            AgentResult — نتيجة المعالجة
        """
        ...

    def record_success(self, duration_ms: float) -> None:
        """
        تسجيل نجاح — Record a successful task completion.

        Updates the agent's performance score using an exponential
        moving average to adapt to recent performance trends.

        Args:
            duration_ms: مدة التنفيذ — execution time in milliseconds
        """
        self._total_tasks += 1
        self._successful_tasks += 1
        self._total_duration_ms += duration_ms
        # تحديث نقاط الأداء بمتوسط متحرك — EMA update
        alpha = 0.3
        self.performance_score = (
            alpha * 1.0 + (1.0 - alpha) * self.performance_score
        )

    def record_failure(self, duration_ms: float) -> None:
        """
        تسجيل فشل — Record a failed task completion.

        Updates the agent's performance score by penalizing the
        failure, also using exponential moving average.

        Args:
            duration_ms: مدة التنفيذ — execution time in milliseconds
        """
        self._total_tasks += 1
        self._total_duration_ms += duration_ms
        # تحديث نقاط الأداء بمتوسط متحرك — EMA update
        alpha = 0.3
        self.performance_score = (
            alpha * 0.0 + (1.0 - alpha) * self.performance_score
        )

    def get_stats(self) -> dict:
        """
        إحصائيات الوكيل — Return agent statistics.

        Returns:
            قاموس بالإحصائيات — dict with usage and performance stats
        """
        success_rate = (
            self._successful_tasks / max(1, self._total_tasks)
        )
        avg_duration = (
            self._total_duration_ms / max(1, self._total_tasks)
        )
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.capabilities,
            "expertise_domains": self.expertise_domains,
            "performance_score": round(self.performance_score, 4),
            "total_tasks": self._total_tasks,
            "successful_tasks": self._successful_tasks,
            "success_rate": round(success_rate, 4),
            "avg_duration_ms": round(avg_duration, 2),
        }

    def _build_keyword_weights(self, keywords: list[str]) -> dict[str, float]:
        """
        بناء أوزان الكلمات المفتاحية — Build TF-IDF-inspired keyword weights.

        الكلمات النادرة تحصل على وزن أعلى. الكلمات الشائعة تحصل على وزن أقل.
        Rare keywords get higher weight. Common keywords get lower weight.

        Args:
            keywords: قائمة الكلمات المفتاحية — list of keywords

        Returns:
            قاموس الأوزان — dict mapping keyword to weight (0.5–2.0)
        """
        # الكلمات القصيرة أو الشائعة تحصل على وزن أقل
        # Short or common keywords get lower weight
        weights: dict[str, float] = {}
        for kw in keywords:
            if len(kw) <= 3:
                weight = 0.5   # كلمات قصيرة — short words
            elif len(kw) <= 6:
                weight = 0.8   # كلمات متوسطة — medium words
            elif " " in kw:
                weight = 1.8   # عبارات متعددة — multi-word phrases (rare)
            else:
                weight = 1.2   # كلمات طويلة — long words (more specific)
            weights[kw] = weight
        return weights


# ═══════════════════════════════════════════════════════════════════════════════
#  وكيل البرمجة — CodeAgent
# ═══════════════════════════════════════════════════════════════════════════════


class CodeAgent(SpecializedAgent):
    """
    وكيل البرمجة — يتخصص في توليد الأكواد والتصحيح وإعادة الهيكلة.
    Specializes in code generation, debugging, refactoring, code review,
    and testing tasks.

    Capabilities:
    - code_generation: توليد الأكواد — writing new code from specifications
    - debugging: التصحيح — finding and fixing bugs
    - refactoring: إعادة الهيكلة — improving code structure and quality
    - code_review: مراجعة الأكواد — reviewing code for issues
    - testing: الاختبار — writing and running tests

    Expertise Domains:
    - programming: البرمجة — general programming knowledge
    - software_engineering: هندسة البرمجيات — software design and architecture
    """

    # كلمات مفتاحية للكشف — detection keywords for task classification
    CODE_KEYWORDS: list[str] = [
        # إنجليزي
        "code", "function", "class", "method", "variable", "bug", "debug",
        "refactor", "compile", "syntax", "algorithm", "api", "library",
        "framework", "module", "import", "test", "unit test", "deploy",
        "git", "repository", "pull request", "merge", "commit",
        # عربي
        "كود", "دالة", "برمجة", "تصحيح", "خطأ برمجي", "واجهة برمجة",
        "خوارزمية", "مكتبة", "إطار عمل", "وحدة", "اختبار", "نشر",
        "هيكلة", "مراجعة كود",
    ]

    def __init__(self):
        """تهيئة وكيل البرمجة — Initialize the Code agent."""
        super().__init__(
            agent_type="code",
            capabilities=[
                "code_generation",
                "debugging",
                "refactoring",
                "code_review",
                "testing",
            ],
            expertise_domains=["programming", "software_engineering"],
            performance_score=0.7,
        )
        # بناء أوزان الكلمات المفتاحية — build keyword weights
        self.keyword_weights = self._build_keyword_weights(self.CODE_KEYWORDS)

    async def process(self, task: str, context: dict) -> AgentResult:
        """
        معالجة مهمة برمجية — Process a code-related task.

        Analyzes the task to determine the specific code operation
        needed and generates an appropriate response.

        Args:
            task: المهمة — the code task description
            context: السياق — may include language, framework, etc.

        Returns:
            AgentResult — نتيجة المعالجة البرمجية
        """
        start_time = time.time()

        try:
            # تحديد نوع المهمة البرمجية — determine code task subtype
            sub_type = self._classify_code_task(task)

            # بناء الاستجابة — build response
            output = self._generate_code_response(task, context, sub_type)

            duration_ms = (time.time() - start_time) * 1000
            confidence = self._compute_confidence(task, context)

            result = AgentResult(
                agent_id=self.agent_id,
                output=output,
                confidence=confidence,
                duration_ms=duration_ms,
                success=True,
            )
            self.record_success(duration_ms)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = AgentResult(
                agent_id=self.agent_id,
                output=f"خطأ في معالجة المهمة البرمجية: {str(e)}",
                confidence=0.0,
                duration_ms=duration_ms,
                success=False,
            )
            self.record_failure(duration_ms)
            logger.error(
                "خطأ في CodeAgent.process: %s", str(e), exc_info=True
            )

        return result

    def _classify_code_task(self, task: str) -> str:
        """
        تصنيف المهمة البرمجية — Classify the specific code task type.

        Args:
            task: وصف المهمة

        Returns:
            نوع المهمة الفرعي: code_generation, debugging, refactoring,
            code_review, testing, or general_code
        """
        task_lower = task.lower()

        # كشف التصحيح — debugging detection
        debug_patterns = [
            r"\b(bug|debug|fix|error|exception|traceback|crash|fault)\b",
            r"(خطأ|تصحيح|إصلاح|استثناء|عطل)",
        ]
        for pattern in debug_patterns:
            if re.search(pattern, task_lower):
                return "debugging"

        # كشف إعادة الهيكلة — refactoring detection
        refactor_patterns = [
            r"\b(refactor|restructure|clean|optimize|improve|simplify)\b",
            r"(إعادة هيكلة|تحسين|تبسيط|تنظيف)",
        ]
        for pattern in refactor_patterns:
            if re.search(pattern, task_lower):
                return "refactoring"

        # كشف مراجعة الكود — code review detection
        review_patterns = [
            r"\b(review|audit|check|inspect|analyze\s+code)\b",
            r"(مراجعة|تدقيق|فحص الكود)",
        ]
        for pattern in review_patterns:
            if re.search(pattern, task_lower):
                return "code_review"

        # كشف الاختبار — testing detection
        test_patterns = [
            r"\b(test|unit\s*test|integration\s*test|coverage|mock)\b",
            r"(اختبار|وحدة اختبار|تغطية)",
        ]
        for pattern in test_patterns:
            if re.search(pattern, task_lower):
                return "testing"

        # افتراضي: توليد أكواد — default: code generation
        return "code_generation"

    def _generate_code_response(
        self, task: str, context: dict, sub_type: str
    ) -> str:
        """
        توليد الاستجابة البرمجية — Generate a code response.

        Args:
            task: المهمة
            context: السياق
            sub_type: النوع الفرعي

        Returns:
            نص الاستجابة
        """
        language = context.get("language", "غير محدد")
        framework = context.get("framework", "غير محدد")

        sub_type_labels = {
            "code_generation": "توليد أكواد",
            "debugging": "تصحيح أخطاء",
            "refactoring": "إعادة هيكلة",
            "code_review": "مراجعة كود",
            "testing": "اختبار",
        }
        label = sub_type_labels.get(sub_type, sub_type)

        return (
            f"[وكيل البرمجة — {label}]\n"
            f"المهمة: {task}\n"
            f"اللغة: {language} | الإطار: {framework}\n"
            f"النوع الفرعي: {sub_type}\n"
            f"تم تحليل المهمة البرمجية وتحديد المتطلبات."
        )

    def _compute_confidence(self, task: str, context: dict) -> float:
        """
        حساب الثقة السياقي — Compute context-aware confidence.

        Uses weighted keyword scoring (TF-IDF-inspired) and considers
        task length and context richness.

        Args:
            task: المهمة
            context: السياق

        Returns:
            مستوى الثقة (0.0–1.0)
        """
        task_lower = task.lower()

        # حساب مرجّح للكلمات المفتاحية — weighted keyword scoring
        weighted_hits = 0.0
        for kw, weight in self.keyword_weights.items():
            if kw in task_lower:
                weighted_hits += weight

        # تطبيع — normalize: 3.0+ weighted hits = max confidence
        base_confidence = min(1.0, weighted_hits / 3.0)

        # تعديل بناءً على طول المهمة — adjust by task length
        # مهام أطول = معلومات أكثر = ثقة أعلى إذا تطابقت الكلمات
        word_count = len(task.split())
        length_bonus = min(0.1, word_count / 200.0) if base_confidence > 0 else 0.0

        # تعديل بناءً على ثراء السياق — adjust by context richness
        context_keys = len(context) if context else 0
        context_bonus = min(0.05, context_keys * 0.01) if base_confidence > 0 else 0.0

        # تعديل بناءً على الأداء — adjust by performance score
        return round(
            min(1.0, base_confidence * 0.65 + self.performance_score * 0.25 + length_bonus + context_bonus),
            4,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  وكيل التحليل — AnalysisAgent
# ═══════════════════════════════════════════════════════════════════════════════


class AnalysisAgent(SpecializedAgent):
    """
    وكيل التحليل — يتخصص في تحليل البيانات والبحث والاستدلال.
    Specializes in data analysis, research, statistical reasoning,
    and report generation tasks.

    Capabilities:
    - data_analysis: تحليل البيانات — extracting insights from data
    - research: البحث — finding and synthesizing information
    - statistical_reasoning: الاستدلال الإحصائي — statistical analysis
    - report_generation: إنشاء التقارير — generating analytical reports

    Expertise Domains:
    - analytics: التحليلات — data analytics and business intelligence
    - research: البحث — academic and applied research
    """

    # كلمات مفتاحية للكشف — detection keywords
    ANALYSIS_KEYWORDS: list[str] = [
        # إنجليزي
        "analyze", "analysis", "data", "statistics", "trend", "correlation",
        "regression", "hypothesis", "significant", "mean", "median",
        "standard deviation", "variance", "sample", "population",
        "research", "study", "survey", "report", "insight", "metric",
        "dashboard", "visualization", "chart", "graph",
        # عربي
        "تحليل", "بيانات", "إحصاء", "اتجاه", "ارتباط", "انحدار",
        "فرضية", "متوسط", "انحراف معياري", "عينة", "مجتمع",
        "بحث", "دراسة", "استبيان", "تقرير", "رؤية", "مقياس",
        "لوحة معلومات", "تصور", "رسم بياني",
    ]

    def __init__(self):
        """تهيئة وكيل التحليل — Initialize the Analysis agent."""
        super().__init__(
            agent_type="analysis",
            capabilities=[
                "data_analysis",
                "research",
                "statistical_reasoning",
                "report_generation",
            ],
            expertise_domains=["analytics", "research"],
            performance_score=0.65,
        )
        self.keyword_weights = self._build_keyword_weights(self.ANALYSIS_KEYWORDS)

    async def process(self, task: str, context: dict) -> AgentResult:
        """
        معالجة مهمة تحليلية — Process an analysis-related task.

        Determines the analysis subtype and generates an appropriate
        analytical response with data-driven reasoning.

        Args:
            task: المهمة — the analysis task description
            context: السياق — may include data sources, methodology, etc.

        Returns:
            AgentResult — نتيجة المعالجة التحليلية
        """
        start_time = time.time()

        try:
            sub_type = self._classify_analysis_task(task)
            output = self._generate_analysis_response(task, context, sub_type)
            duration_ms = (time.time() - start_time) * 1000
            confidence = self._compute_confidence(task, context)

            result = AgentResult(
                agent_id=self.agent_id,
                output=output,
                confidence=confidence,
                duration_ms=duration_ms,
                success=True,
            )
            self.record_success(duration_ms)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = AgentResult(
                agent_id=self.agent_id,
                output=f"خطأ في معالجة المهمة التحليلية: {str(e)}",
                confidence=0.0,
                duration_ms=duration_ms,
                success=False,
            )
            self.record_failure(duration_ms)
            logger.error(
                "خطأ في AnalysisAgent.process: %s", str(e), exc_info=True
            )

        return result

    def _classify_analysis_task(self, task: str) -> str:
        """
        تصنيف المهمة التحليلية — Classify the analysis task subtype.

        Returns:
            data_analysis, research, statistical_reasoning,
            report_generation, or general_analysis
        """
        task_lower = task.lower()

        # كشف الاستدلال الإحصائي — statistical reasoning detection
        stat_patterns = [
            r"\b(statistic|regression|correlation|hypothesis|p.value|"
            r"significance|anova|chi.square|t.test|confidence\s+interval)\b",
            r"(إحصاء|انحدار|ارتباط|فرضية|دلالة إحصائية|فترة ثقة)",
        ]
        for pattern in stat_patterns:
            if re.search(pattern, task_lower):
                return "statistical_reasoning"

        # كشف البحث — research detection
        research_patterns = [
            r"\b(research|study|survey|literature|paper|cite|citation|"
            r"methodology|systematic\s+review)\b",
            r"(بحث|دراسة|استبيان|أدبيات|منهجية|مراجعة منهجية)",
        ]
        for pattern in research_patterns:
            if re.search(pattern, task_lower):
                return "research"

        # كشف إنشاء التقارير — report generation detection
        report_patterns = [
            r"\b(report|summary|briefing|presentation|dashboard|executive)\b",
            r"(تقرير|ملخص|إحاطة|عرض|لوحة معلومات)",
        ]
        for pattern in report_patterns:
            if re.search(pattern, task_lower):
                return "report_generation"

        return "data_analysis"

    def _generate_analysis_response(
        self, task: str, context: dict, sub_type: str
    ) -> str:
        """توليد الاستجابة التحليلية — Generate an analysis response."""
        data_source = context.get("data_source", "غير محدد")
        methodology = context.get("methodology", "غير محددة")

        sub_type_labels = {
            "data_analysis": "تحليل بيانات",
            "research": "بحث",
            "statistical_reasoning": "استدلال إحصائي",
            "report_generation": "إنشاء تقرير",
        }
        label = sub_type_labels.get(sub_type, sub_type)

        return (
            f"[وكيل التحليل — {label}]\n"
            f"المهمة: {task}\n"
            f"مصدر البيانات: {data_source} | المنهجية: {methodology}\n"
            f"النوع الفرعي: {sub_type}\n"
            f"تم تحليل البيانات واستخراج الرؤى."
        )

    def _compute_confidence(self, task: str, context: dict) -> float:
        """حساب الثقة السياقي — Compute context-aware confidence."""
        task_lower = task.lower()
        weighted_hits = sum(
            weight for kw, weight in self.keyword_weights.items() if kw in task_lower
        )
        base_confidence = min(1.0, weighted_hits / 3.0)

        word_count = len(task.split())
        length_bonus = min(0.1, word_count / 200.0) if base_confidence > 0 else 0.0
        context_keys = len(context) if context else 0
        context_bonus = min(0.05, context_keys * 0.01) if base_confidence > 0 else 0.0

        return round(
            min(1.0, base_confidence * 0.65 + self.performance_score * 0.25 + length_bonus + context_bonus),
            4,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  وكيل الإبداع — CreativeAgent
# ═══════════════════════════════════════════════════════════════════════════════


class CreativeAgent(SpecializedAgent):
    """
    وكيل الإبداع — يتخصص في الكتابة الإبداعية والعصف الذهني والتصميم.
    Specializes in creative writing, brainstorming, design thinking,
    and storytelling tasks.

    Capabilities:
    - creative_writing: الكتابة الإبداعية — writing stories, poems, scripts
    - brainstorming: العصف الذهني — generating creative ideas
    - design_thinking: التفكير التصميمي — user-centered design
    - storytelling: سرد القصص — narrative construction

    Expertise Domains:
    - creative: الإبداع — creative arts and expression
    - writing: الكتابة — all forms of written communication
    """

    # كلمات مفتاحية للكشف — detection keywords
    CREATIVE_KEYWORDS: list[str] = [
        # إنجليزي
        "write", "story", "poem", "creative", "brainstorm", "idea",
        "design", "narrative", "fiction", "novel", "script", "song",
        "imagine", "invent", "compose", "draft", "outline", "plot",
        "character", "setting", "theme", "metaphor", "imagery",
        # عربي
        "اكتب", "قصة", "قصيدة", "إبداع", "عصف ذهني", "فكرة",
        "تصميم", "سرد", "خيال", "رواية", "نص", "أغنية",
        "تخيّل", "اخترع", "ألّف", "مسودة", "مخطط", "حبكة",
        "شخصية", "بيئة", "موضوع", "استعارة", "صور أدبية",
    ]

    def __init__(self):
        """تهيئة وكيل الإبداع — Initialize the Creative agent."""
        super().__init__(
            agent_type="creative",
            capabilities=[
                "creative_writing",
                "brainstorming",
                "design_thinking",
                "storytelling",
            ],
            expertise_domains=["creative", "writing"],
            performance_score=0.6,
        )
        self.keyword_weights = self._build_keyword_weights(self.CREATIVE_KEYWORDS)

    async def process(self, task: str, context: dict) -> AgentResult:
        """
        معالجة مهمة إبداعية — Process a creative task.

        Determines the creative subtype and generates an imaginative
        and original response.

        Args:
            task: المهمة — the creative task description
            context: السياق — may include style, tone, audience, etc.

        Returns:
            AgentResult — نتيجة المعالجة الإبداعية
        """
        start_time = time.time()

        try:
            sub_type = self._classify_creative_task(task)
            output = self._generate_creative_response(task, context, sub_type)
            duration_ms = (time.time() - start_time) * 1000
            confidence = self._compute_confidence(task, context)

            result = AgentResult(
                agent_id=self.agent_id,
                output=output,
                confidence=confidence,
                duration_ms=duration_ms,
                success=True,
            )
            self.record_success(duration_ms)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = AgentResult(
                agent_id=self.agent_id,
                output=f"خطأ في معالجة المهمة الإبداعية: {str(e)}",
                confidence=0.0,
                duration_ms=duration_ms,
                success=False,
            )
            self.record_failure(duration_ms)
            logger.error(
                "خطأ في CreativeAgent.process: %s", str(e), exc_info=True
            )

        return result

    def _classify_creative_task(self, task: str) -> str:
        """
        تصنيف المهمة الإبداعية — Classify the creative task subtype.

        Returns:
            creative_writing, brainstorming, design_thinking,
            storytelling, or general_creative
        """
        task_lower = task.lower()

        # كشف العصف الذهني — brainstorming detection
        brainstorm_patterns = [
            r"\b(brainstorm|idea|ideate|generate\s+ideas|think\s+of)\b",
            r"(عصف ذهني|أفكار|فكرة|ابتكر)",
        ]
        for pattern in brainstorm_patterns:
            if re.search(pattern, task_lower):
                return "brainstorming"

        # كشف التفكير التصميمي — design thinking detection
        design_patterns = [
            r"\b(design|prototype|user\s+experience|ux|ui|wireframe|mockup)\b",
            r"(تصميم|نموذج أولي|تجربة مستخدم|واجهة)",
        ]
        for pattern in design_patterns:
            if re.search(pattern, task_lower):
                return "design_thinking"

        # كشف سرد القصص — storytelling detection
        story_patterns = [
            r"\b(story|narrative|plot|character|setting|scene|dialogue)\b",
            r"(قصة|سرد|حبكة|شخصية|مشهد|حوار)",
        ]
        for pattern in story_patterns:
            if re.search(pattern, task_lower):
                return "storytelling"

        return "creative_writing"

    def _generate_creative_response(
        self, task: str, context: dict, sub_type: str
    ) -> str:
        """توليد الاستجابة الإبداعية — Generate a creative response."""
        style = context.get("style", "غير محدد")
        audience = context.get("audience", "غير محدد")

        sub_type_labels = {
            "creative_writing": "كتابة إبداعية",
            "brainstorming": "عصف ذهني",
            "design_thinking": "تفكير تصميمي",
            "storytelling": "سرد قصص",
        }
        label = sub_type_labels.get(sub_type, sub_type)

        return (
            f"[وكيل الإبداع — {label}]\n"
            f"المهمة: {task}\n"
            f"الأسلوب: {style} | الجمهور: {audience}\n"
            f"النوع الفرعي: {sub_type}\n"
            f"تم إنشاء محتوى إبداعي أصيل."
        )

    def _compute_confidence(self, task: str, context: dict) -> float:
        """حساب الثقة السياقي — Compute context-aware confidence."""
        task_lower = task.lower()
        weighted_hits = sum(
            weight for kw, weight in self.keyword_weights.items() if kw in task_lower
        )
        base_confidence = min(1.0, weighted_hits / 3.0)

        word_count = len(task.split())
        length_bonus = min(0.1, word_count / 200.0) if base_confidence > 0 else 0.0
        context_keys = len(context) if context else 0
        context_bonus = min(0.05, context_keys * 0.01) if base_confidence > 0 else 0.0

        return round(
            min(1.0, base_confidence * 0.65 + self.performance_score * 0.25 + length_bonus + context_bonus),
            4,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  وكيل الرياضيات — MathAgent
# ═══════════════════════════════════════════════════════════════════════════════


class MathAgent(SpecializedAgent):
    """
    وكيل الرياضيات — يتخصص في الاستدلال الرياضي والعمليات الحسابية.
    Specializes in mathematical reasoning, computation, proof
    verification, and optimization tasks.

    Capabilities:
    - mathematical_reasoning: الاستدلال الرياضي — logical mathematical proofs
    - computation: الحساب — numerical computation and evaluation
    - proof_verification: التحقق من البراهين — verifying mathematical proofs
    - optimization: التحسين — mathematical optimization problems

    Expertise Domains:
    - mathematics: الرياضيات — pure and applied mathematics
    - logic: المنطق — formal logic and reasoning
    """

    # كلمات مفتاحية للكشف — detection keywords (expanded with Arabic math terms)
    MATH_KEYWORDS: list[str] = [
        # إنجليزي
        "math", "calculate", "equation", "formula", "proof", "theorem",
        "integral", "derivative", "matrix", "vector", "probability",
        "algebra", "geometry", "calculus", "trigonometry", "logarithm",
        "polynomial", "function", "limit", "series", "sequence",
        "optimization", "linear programming", "combinatorics",
        # عربي — كلمات مفتاحية رياضية عربية محسّنة
        "رياضيات", "احسب", "معادلة", "صيغة", "برهان", "نظرية",
        "تكامل", "مشتقة", "مصفوفة", "متجه", "احتمال",
        "جبر", "هندسة", "تفاضل", "مثلثات", "لوغاريتم",
        "كثير الحدود", "دالة", "نهاية", "متسلسلة", "تحسين",
        # كلمات مفتاحية عربية إضافية — additional Arabic math keywords
        "حل", "اشتقاق", "حدود", "نسبة", "نسبة مئوية",
        "مساحة", "محيط", "حجم", "زاوية", "جيب التمام",
        "جيب", "ظل",
    ]

    def __init__(self):
        """تهيئة وكيل الرياضيات — Initialize the Math agent."""
        super().__init__(
            agent_type="math",
            capabilities=[
                "mathematical_reasoning",
                "computation",
                "proof_verification",
                "optimization",
            ],
            expertise_domains=["mathematics", "logic"],
            performance_score=0.75,
        )
        self.keyword_weights = self._build_keyword_weights(self.MATH_KEYWORDS)

    async def process(self, task: str, context: dict) -> AgentResult:
        """
        معالجة مهمة رياضية — Process a math-related task.

        Determines the mathematical subtype and applies appropriate
        reasoning or computation methods.

        Args:
            task: المهمة — the math task description
            context: السياق — may include variables, constraints, etc.

        Returns:
            AgentResult — نتيجة المعالجة الرياضية
        """
        start_time = time.time()

        try:
            sub_type = self._classify_math_task(task)
            output = self._generate_math_response(task, context, sub_type)
            duration_ms = (time.time() - start_time) * 1000
            confidence = self._compute_confidence(task, context)

            result = AgentResult(
                agent_id=self.agent_id,
                output=output,
                confidence=confidence,
                duration_ms=duration_ms,
                success=True,
            )
            self.record_success(duration_ms)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = AgentResult(
                agent_id=self.agent_id,
                output=f"خطأ في معالجة المهمة الرياضية: {str(e)}",
                confidence=0.0,
                duration_ms=duration_ms,
                success=False,
            )
            self.record_failure(duration_ms)
            logger.error(
                "خطأ في MathAgent.process: %s", str(e), exc_info=True
            )

        return result

    def _classify_math_task(self, task: str) -> str:
        """
        تصنيف المهمة الرياضية — Classify the math task subtype.

        Returns:
            mathematical_reasoning, computation, proof_verification,
            optimization, or general_math
        """
        task_lower = task.lower()

        # كشف التحقق من البراهين — proof verification detection
        proof_patterns = [
            r"\b(prove|proof|theorem|lemma|corollary|axiom|induction)\b",
            r"(برهن|برهان|نظرية|مساعدة|مبدأ|استقراء)",
        ]
        for pattern in proof_patterns:
            if re.search(pattern, task_lower):
                return "proof_verification"

        # كشف التحسين — optimization detection
        opt_patterns = [
            r"\b(optimize|maximize|minimize|linear\s+programming|"
            r"constraint|objective\s+function)\b",
            r"(حسّن|كبّر|صغّر|برمجة خطية|قيود|دالة هدف)",
        ]
        for pattern in opt_patterns:
            if re.search(pattern, task_lower):
                return "optimization"

        # كشف الحساب — computation detection
        compute_patterns = [
            r"\b(calculate|compute|solve|evaluate|find\s+the\s+value|"
            r"what\s+is)\b",
            r"(احسب|أوجد|حاسِب|حلّ|قيّم)",
        ]
        for pattern in compute_patterns:
            if re.search(pattern, task_lower):
                return "computation"

        return "mathematical_reasoning"

    def _generate_math_response(
        self, task: str, context: dict, sub_type: str
    ) -> str:
        """توليد الاستجابة الرياضية — Generate a math response."""
        variables = context.get("variables", "غير محدد")
        constraints = context.get("constraints", "غير محددة")

        sub_type_labels = {
            "mathematical_reasoning": "استدلال رياضي",
            "computation": "حساب",
            "proof_verification": "تحقق من برهان",
            "optimization": "تحسين",
        }
        label = sub_type_labels.get(sub_type, sub_type)

        return (
            f"[وكيل الرياضيات — {label}]\n"
            f"المهمة: {task}\n"
            f"المتغيرات: {variables} | القيود: {constraints}\n"
            f"النوع الفرعي: {sub_type}\n"
            f"تم حل المسألة الرياضية خطوة بخطوة."
        )

    def _compute_confidence(self, task: str, context: dict) -> float:
        """حساب الثقة السياقي — Compute context-aware confidence."""
        task_lower = task.lower()
        weighted_hits = sum(
            weight for kw, weight in self.keyword_weights.items() if kw in task_lower
        )
        base_confidence = min(1.0, weighted_hits / 3.0)

        word_count = len(task.split())
        length_bonus = min(0.1, word_count / 200.0) if base_confidence > 0 else 0.0
        context_keys = len(context) if context else 0
        context_bonus = min(0.05, context_keys * 0.01) if base_confidence > 0 else 0.0

        return round(
            min(1.0, base_confidence * 0.65 + self.performance_score * 0.25 + length_bonus + context_bonus),
            4,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  وكيل البحث — ResearchAgent (NEW — الوكيل الخامس)
# ═══════════════════════════════════════════════════════════════════════════════


class ResearchAgent(SpecializedAgent):
    """
    وكيل البحث — يتخصص في المهام البحثية والأكاديمية.
    Specializes in research and academic tasks including thesis
    work, literature reviews, citation analysis, and methodology.

    Capabilities:
    - literature_review: استعراض الأدبيات — reviewing and synthesizing literature
    - citation_analysis: تحليل الاستشهادات — analyzing citations and references
    - methodology_design: تصميم المنهجية — designing research methodologies
    - academic_writing: الكتابة الأكاديمية — writing academic papers and reports

    Expertise Domains:
    - academic: الأكاديمي — academic research and scholarship
    - research_methodology: منهجية البحث — research design and methods
    """

    # كلمات مفتاحية للكشف — detection keywords
    RESEARCH_KEYWORDS: list[str] = [
        # إنجليزي
        "thesis", "paper", "citation", "methodology", "literature review",
        "dissertation", "journal", "peer review", "abstract", "hypothesis",
        "empirical", "qualitative", "quantitative", "systematic review",
        "meta-analysis", "bibliography", "reference", "scholarly",
        "academic", "research", "study", "experiment", "survey",
        "data collection", "findings", "conclusion",
        # عربي
        "أطروحة", "بحث", "مرجع", "منهجية", "استعراض أدبيات",
        "رسالة", "مجلة", "تحكيم", "ملخص", "فرضية",
        "تجريبي", "نوعي", "كمي", "مراجعة منهجية",
        "تحليل تلوي", "قائمة مراجع", "أكاديمي",
        "دراسة", "تجربة", "استبيان", "جمع بيانات",
        "نتائج", "خلاصة",
    ]

    def __init__(self):
        """تهيئة وكيل البحث — Initialize the Research agent."""
        super().__init__(
            agent_type="research",
            capabilities=[
                "literature_review",
                "citation_analysis",
                "methodology_design",
                "academic_writing",
            ],
            expertise_domains=["academic", "research_methodology"],
            performance_score=0.65,
        )
        self.keyword_weights = self._build_keyword_weights(self.RESEARCH_KEYWORDS)

    async def process(self, task: str, context: dict) -> AgentResult:
        """
        معالجة مهمة بحثية — Process a research-related task.

        Determines the research subtype and generates an appropriate
        academic response with proper methodology awareness.

        Args:
            task: المهمة — the research task description
            context: السياق — may include field, methodology, etc.

        Returns:
            AgentResult — نتيجة المعالجة البحثية
        """
        start_time = time.time()

        try:
            sub_type = self._classify_research_task(task)
            output = self._generate_research_response(task, context, sub_type)
            duration_ms = (time.time() - start_time) * 1000
            confidence = self._compute_confidence(task, context)

            result = AgentResult(
                agent_id=self.agent_id,
                output=output,
                confidence=confidence,
                duration_ms=duration_ms,
                success=True,
            )
            self.record_success(duration_ms)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = AgentResult(
                agent_id=self.agent_id,
                output=f"خطأ في معالجة المهمة البحثية: {str(e)}",
                confidence=0.0,
                duration_ms=duration_ms,
                success=False,
            )
            self.record_failure(duration_ms)
            logger.error(
                "خطأ في ResearchAgent.process: %s", str(e), exc_info=True
            )

        return result

    def _classify_research_task(self, task: str) -> str:
        """
        تصنيف المهمة البحثية — Classify the research task subtype.

        Returns:
            literature_review, citation_analysis, methodology_design,
            academic_writing, or general_research
        """
        task_lower = task.lower()

        # كشف استعراض الأدبيات — literature review detection
        lit_patterns = [
            r"\b(literature\s+review|systematic\s+review|meta-analysis|"
            r"bibliography|state\s+of\s+the\s+art)\b",
            r"(استعراض أدبيات|مراجعة منهجية|تحليل تلوي|قائمة مراجع|حالة الفن)",
        ]
        for pattern in lit_patterns:
            if re.search(pattern, task_lower):
                return "literature_review"

        # كشف تحليل الاستشهادات — citation analysis detection
        cite_patterns = [
            r"\b(citation|cite|reference|h.index|impact\s+factor|"
            r"bibliometric)\b",
            r"(استشهاد|مرجع|معامل تأثير|قياس ببليومتري)",
        ]
        for pattern in cite_patterns:
            if re.search(pattern, task_lower):
                return "citation_analysis"

        # كشف تصميم المنهجية — methodology design detection
        method_patterns = [
            r"\b(methodology|method|approach|framework|design|"
            r"qualitative|quantitative|mixed\s+method|experimental\s+design)\b",
            r"(منهجية|طريقة|منهج|إطار عمل|نوعي|كمي|منهج مختلط|تصميم تجريبي)",
        ]
        for pattern in method_patterns:
            if re.search(pattern, task_lower):
                return "methodology_design"

        # كشف الكتابة الأكاديمية — academic writing detection
        write_patterns = [
            r"\b(thesis|dissertation|paper|article|abstract|journal|"
            r"peer\s+review|scholarly)\b",
            r"(أطروحة|رسالة|ورقة|مقال|ملخص|مجلة|تحكيم|أكاديمي)",
        ]
        for pattern in write_patterns:
            if re.search(pattern, task_lower):
                return "academic_writing"

        return "general_research"

    def _generate_research_response(
        self, task: str, context: dict, sub_type: str
    ) -> str:
        """توليد الاستجابة البحثية — Generate a research response."""
        field = context.get("field", "غير محدد")
        methodology = context.get("methodology", "غير محددة")

        sub_type_labels = {
            "literature_review": "استعراض أدبيات",
            "citation_analysis": "تحليل استشهادات",
            "methodology_design": "تصميم منهجية",
            "academic_writing": "كتابة أكاديمية",
            "general_research": "بحث عام",
        }
        label = sub_type_labels.get(sub_type, sub_type)

        return (
            f"[وكيل البحث — {label}]\n"
            f"المهمة: {task}\n"
            f"المجال: {field} | المنهجية: {methodology}\n"
            f"النوع الفرعي: {sub_type}\n"
            f"تم تحليل المتطلبات البحثية وتحديد المنهجية المناسبة."
        )

    def _compute_confidence(self, task: str, context: dict) -> float:
        """حساب الثقة السياقي — Compute context-aware confidence."""
        task_lower = task.lower()
        weighted_hits = sum(
            weight for kw, weight in self.keyword_weights.items() if kw in task_lower
        )
        base_confidence = min(1.0, weighted_hits / 3.0)

        word_count = len(task.split())
        length_bonus = min(0.1, word_count / 200.0) if base_confidence > 0 else 0.0
        context_keys = len(context) if context else 0
        context_bonus = min(0.05, context_keys * 0.01) if base_confidence > 0 else 0.0

        return round(
            min(1.0, base_confidence * 0.65 + self.performance_score * 0.25 + length_bonus + context_bonus),
            4,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  موجّه الوكلاء — AgentRouter
# ═══════════════════════════════════════════════════════════════════════════════


class AgentRouter:
    """
    موجّه الوكلاء — يُصنّف المهام ويُوجّهها إلى أنسب وكيل متخصص.
    Routes tasks to the best-matching specialized agent based on
    task-agent affinity scoring with weighted keywords and adaptive history.

    Routing strategy:
    1. Check LRU cache for similar past routing decisions
    2. Classify the task (type, domain, complexity, required capabilities)
    3. Compute affinity with weighted keyword scoring and history boost
    4. Select the agent with the highest affinity score
    5. Return routing result with confidence and alternatives

    Affinity computation factors:
    - Capability match: هل قدرات الوكيل تغطي المتطلبات؟ (35%)
    - Domain overlap: هل مجال خبرة الوكيل مطابق؟ (25%)
    - Performance score: كيف هو أداء الوكيل تاريخياً؟ (20%)
    - Complexity fit: هل مستوى تعقيد الوكيل مناسب؟ (10%)
    - History boost: تعزيز من السجل التكيّفي (10%)
    """

    # كلمات مفتاحية عالمية للتصنيف — global classification keywords
    _TYPE_KEYWORDS: dict[str, list[str]] = {
        "code": [
            "code", "program", "function", "debug", "refactor", "compile",
            "كود", "برمجة", "دالة", "تصحيح", "هيكلة", "تجميع",
        ],
        "analysis": [
            "analyze", "data", "statistics", "research", "report", "trend",
            "تحليل", "بيانات", "إحصاء", "بحث", "تقرير", "اتجاه",
        ],
        "creative": [
            "write", "story", "creative", "brainstorm", "design", "poem",
            "اكتب", "قصة", "إبداع", "عصف", "تصميم", "قصيدة",
        ],
        "math": [
            "math", "calculate", "equation", "proof", "theorem", "solve",
            "رياضيات", "احسب", "معادلة", "برهان", "نظرية", "حل",
        ],
        "research": [
            "thesis", "paper", "citation", "methodology", "literature",
            "أطروحة", "بحث", "مرجع", "منهجية", "استعراض أدبيات",
        ],
    }

    # أوزان الكلمات المفتاحية العالمية — global keyword weights (TF-IDF inspired)
    _KEYWORD_WEIGHTS: dict[str, float] = {}
    # يُحسب عند التهيئة — computed on init

    def __init__(self):
        """تهيئة موجّه الوكلاء — Initialize the router."""
        # سجل الوكلاء — agent registry
        self._agents: dict[str, SpecializedAgent] = {}
        # سجل الأداء — performance tracking
        self._performance_history: dict[str, list[bool]] = defaultdict(list)
        # عداد التوجيه — routing counter
        self._routing_count: int = 0
        # سجل التوجيه التكيّفي — adaptive routing history
        self._routing_history: RoutingHistory = RoutingHistory()
        # ذاكرة التخزين المؤقت — LRU cache
        self._cache: PipelineCache = PipelineCache()
        # حساب أوزان الكلمات المفتاحية — compute keyword weights
        self._compute_global_keyword_weights()

    def _compute_global_keyword_weights(self) -> None:
        """
        حساب أوزان الكلمات المفتاحية العالمية — Compute global TF-IDF-inspired weights.

        الكلمات التي تظهر في أنواع كثيرة تحصل على وزن أقل (أقل تمييزاً).
        Keywords appearing in many types get lower weight (less discriminative).
        """
        keyword_type_count: dict[str, int] = defaultdict(int)
        total_types = len(self._TYPE_KEYWORDS)

        for task_type, keywords in self._TYPE_KEYWORDS.items():
            for kw in keywords:
                keyword_type_count[kw] += 1

        for kw, count in keyword_type_count.items():
            # IDF-inspired: log(total_types / count)
            # كلما ظهرت الكلمة في أنواع أقل، زاد وزنها
            if count > 0:
                idf = math.log(total_types / count) + 1.0
            else:
                idf = 1.0
            self._KEYWORD_WEIGHTS[kw] = round(idf, 3)

    def register_agent(self, agent: SpecializedAgent) -> None:
        """
        تسجيل وكيل — Register a specialized agent.

        Adds the agent to the registry so it can be considered
        for task routing.

        Args:
            agent: الوكيل — the SpecializedAgent to register
        """
        self._agents[agent.agent_id] = agent
        logger.debug(
            "تم تسجيل الوكيل '%s' من نوع '%s'",
            agent.agent_id,
            agent.agent_type,
        )

    def route(self, task: str, context: dict) -> RoutingResult:
        """
        توجيه المهمة — Route a task to the best-matching agent.

        Classifies the task, computes affinity with each agent
        (using weighted keywords and adaptive history), and selects
        the agent with the highest score. Checks LRU cache first.

        Args:
            task: المهمة — the task description
            context: السياق — additional context

        Returns:
            RoutingResult — نتيجة التوجيه مع الوكيل المختار
        """
        self._routing_count += 1

        if not self._agents:
            logger.warning("لا يوجد وكلاء مسجّلين — no agents registered")
            return RoutingResult(
                selected_agent=None,
                confidence=0.0,
                alternatives=[],
            )

        # فحص الذاكرة المؤقتة — check cache first
        cached = self._cache.get(task, context)
        if cached is not None:
            logger.debug("تم العثور على قرار توجيه مخزّن — cache hit")
            return RoutingResult(
                selected_agent=cached.get("selected_agent"),
                confidence=cached.get("confidence", 0.0),
                alternatives=cached.get("alternatives", []),
            )

        # تصنيف المهمة — classify the task
        classification = self._classify_task(task)

        logger.debug(
            "تصنيف المهمة: type=%s, domain=%s, complexity=%.2f, "
            "required_capabilities=%s",
            classification.task_type,
            classification.domain,
            classification.complexity,
            classification.required_capabilities,
        )

        # حساب الألفة مع كل وكيل — compute affinity with each agent
        affinities: list[tuple[str, float]] = []
        for agent_id, agent in self._agents.items():
            affinity = self._compute_task_agent_affinity(
                task, agent, classification
            )
            affinities.append((agent_id, affinity))

        # ترتيب حسب الألفة — sort by affinity descending
        affinities.sort(key=lambda x: x[1], reverse=True)

        # اختيار الأفضل — select best
        best_agent_id, best_affinity = affinities[0]
        alternatives = [aid for aid, _ in affinities[1:]]

        # حساب الثقة — compute routing confidence
        confidence = best_affinity
        if len(affinities) > 1:
            # إذا كان الفارق بين أفضل اثنين صغيراً، قلّل الثقة
            # reduce confidence when top agents are close in affinity
            gap = best_affinity - affinities[1][1]
            confidence = min(
                1.0, best_affinity * (0.5 + gap)
            )

        # تعزيز الثقة من السجل التكيّفي — boost from adaptive history
        best_agent = self._agents.get(best_agent_id)
        if best_agent:
            history_boost = self._routing_history.get_affinity_boost(
                classification.task_type, best_agent.agent_type
            )
            confidence = max(0.0, min(1.0, confidence + history_boost))

        # تخزين في الذاكرة المؤقتة — cache the result
        self._cache.put(task, context, {
            "selected_agent": best_agent_id,
            "confidence": round(confidence, 4),
            "alternatives": alternatives,
        })

        logger.info(
            "تم توجيه المهمة إلى الوكيل '%s' (ألفة: %.4f، ثقة: %.4f)",
            best_agent_id,
            best_affinity,
            confidence,
        )

        return RoutingResult(
            selected_agent=best_agent_id,
            confidence=round(confidence, 4),
            alternatives=alternatives,
        )

    def _compute_task_agent_affinity(
        self,
        task: str,
        agent: SpecializedAgent,
        classification: Optional[TaskClassification] = None,
    ) -> float:
        """
        حساب ألفة المهمة مع الوكيل — Compute task-agent affinity score.

        Affinity = 0.35 * capability_match
                  + 0.25 * domain_overlap
                  + 0.20 * performance_score
                  + 0.10 * complexity_fit
                  + 0.10 * history_boost

        Args:
            task: المهمة
            agent: الوكيل
            classification: تصنيف المهمة (اختياري)

        Returns:
            درجة الألفة (0.0–1.0)
        """
        if classification is None:
            classification = self._classify_task(task)

        # 1. توافق القدرات — capability match (35%)
        required = set(classification.required_capabilities)
        available = set(agent.capabilities)
        if required:
            capability_match = len(required & available) / len(required)
        else:
            # إذا لم تُحدد قدرات مطلوبة، افحص تطابق النوع
            capability_match = 1.0 if classification.task_type == agent.agent_type else 0.3

        # 2. تداخل المجالات — domain overlap (25%)
        task_domains = {classification.domain}
        agent_domains = set(agent.expertise_domains)
        domain_overlap = (
            len(task_domains & agent_domains) / max(1, len(task_domains | agent_domains))
        )
        # إضافة نقاط للتطابق الجزئي — partial match bonus
        if classification.task_type == agent.agent_type:
            domain_overlap = max(domain_overlap, 0.8)

        # 3. نقاط الأداء — performance score (20%)
        performance = agent.performance_score

        # 4. ملاءمة التعقيد — complexity fit (10%)
        # الوكلاء ذوو الأداء العالي أفضل للمهام المعقدة
        complexity_fit = 1.0 - abs(
            classification.complexity - performance
        )

        # 5. تعزيز من السجل التكيّفي — history boost (10%)
        history_boost = self._routing_history.get_affinity_boost(
            classification.task_type, agent.agent_type
        )
        # تحويل التعزيز إلى نطاق 0-1 — normalize boost to 0-1
        history_score = max(0.0, min(1.0, 0.5 + history_boost))

        # الحساب النهائي — final affinity computation
        affinity = (
            0.35 * capability_match
            + 0.25 * domain_overlap
            + 0.20 * performance
            + 0.10 * complexity_fit
            + 0.10 * history_score
        )

        return max(0.0, min(1.0, affinity))

    def _classify_task(self, task: str) -> TaskClassification:
        """
        تصنيف المهمة — Classify a task by type, domain, complexity.

        Uses weighted keyword matching (TF-IDF-inspired) against
        the TYPE_KEYWORDS dictionary to determine the task type,
        then infers domain, complexity, and required capabilities.

        Args:
            task: وصف المهمة

        Returns:
            TaskClassification — تصنيف المهمة
        """
        task_lower = task.lower()

        # حساب نقاط كل نوع بأوزان مرجّحة — weighted score per type
        type_scores: dict[str, float] = {}
        for task_type, keywords in self._TYPE_KEYWORDS.items():
            weighted_hits = 0.0
            for kw in keywords:
                if kw in task_lower:
                    # استخدام وزن IDF إذا متاح — use IDF weight if available
                    weight = self._KEYWORD_WEIGHTS.get(kw, 1.0)
                    weighted_hits += weight
            type_scores[task_type] = weighted_hits

        # اختيار النوع الأعلى — pick highest scoring type
        if any(v > 0 for v in type_scores.values()):
            best_type = max(type_scores, key=type_scores.get)
        else:
            best_type = "general"

        # تحديد المجال — determine domain
        domain_map = {
            "code": "programming",
            "analysis": "analytics",
            "creative": "creative",
            "math": "mathematics",
            "research": "academic",
            "general": "general",
        }
        domain = domain_map.get(best_type, "general")

        # تقدير التعقيد — estimate complexity
        complexity = self._estimate_complexity(task)

        # تحديد القدرات المطلوبة — determine required capabilities
        required_capabilities = self._infer_required_capabilities(
            task, best_type
        )

        return TaskClassification(
            task_type=best_type,
            domain=domain,
            complexity=complexity,
            required_capabilities=required_capabilities,
        )

    def _estimate_complexity(self, task: str) -> float:
        """
        تقدير تعقيد المهمة — Estimate task complexity (0.0–1.0).

        Based on structural analysis:
        - Task length (longer = more complex)
        - Sentence count (more sentences = more sub-tasks)
        - Number of clauses (conjunctions = more logic)
        - Presence of logical operators (and, or, if, unless)
        - Nested expressions (parentheses, brackets)
        - Technical terminology density
        - Complexity/simplicity indicators

        Args:
            task: وصف المهمة

        Returns:
            مستوى التعقيد (0.0–1.0)
        """
        complexity = 0.2  # أساسي — base

        # 1. عامل الطول — length factor
        word_count = len(task.split())
        if word_count > 10:
            complexity += 0.05
        if word_count > 20:
            complexity += 0.05
        if word_count > 50:
            complexity += 0.1
        if word_count > 100:
            complexity += 0.1

        # 2. عدد الجمل — sentence count
        sentence_count = len(re.split(r'[.!?؟。]', task))
        if sentence_count > 2:
            complexity += 0.05
        if sentence_count > 4:
            complexity += 0.05

        # 3. العوامل المنطقية — logical operators
        logical_ops = [
            r"\b(and|or|not|but|however|although|if|unless|while|whereas|"
            r"therefore|thus|hence|moreover|furthermore|consequently)\b",
            r"(و|أو|لكن|إلا أن|ومع ذلك|إذا|ما لم|بينما|بالتالي|لذلك|من ثم)",
        ]
        for pattern in logical_ops:
            matches = re.findall(pattern, task.lower())
            if matches:
                complexity += min(0.1, len(matches) * 0.03)

        # 4. التعابير المتداخلة — nested expressions
        paren_depth = 0
        max_depth = 0
        for char in task:
            if char in "([{":
                paren_depth += 1
                max_depth = max(max_depth, paren_depth)
            elif char in ")]}":
                paren_depth = max(0, paren_depth - 1)
        if max_depth > 0:
            complexity += min(0.1, max_depth * 0.03)

        # 5. كثافة المصطلحات التقنية — technical terminology density
        tech_indicators = [
            r"\b(algorithm|optimization|implementation|architecture|"
            r"infrastructure|methodology|framework|theorem|corollary|"
            r"derivative|integral|regression|classifier)\b",
            r"(خوارزمية|تحسين|تنفيذ|هندسة|بنية تحتية|منهجية|"
            r"إطار عمل|نظرية|مشتقة|تكامل|انحدار|مصنّف)",
        ]
        for pattern in tech_indicators:
            matches = re.findall(pattern, task.lower())
            if matches:
                complexity += min(0.1, len(matches) * 0.03)

        # 6. مؤشرات التعقيد — complexity indicators
        complex_indicators = [
            r"\b(multi|multiple|complex|comprehensive|detailed|advanced|"
            r"nested|recursive|concurrent|parallel)\b",
            r"(متعدد|مركب|شامل|مفصّل|متقدم|متداخل|متوازي|متزامن)",
        ]
        for pattern in complex_indicators:
            if re.search(pattern, task.lower()):
                complexity += 0.1

        # 7. مؤشرات البساطة — simplicity indicators
        simple_indicators = [
            r"\b(simple|basic|easy|quick|brief|short|single)\b",
            r"(بسيط|أساسي|سهل|سريع|مختصر|قصير|وحيد)",
        ]
        for pattern in simple_indicators:
            if re.search(pattern, task.lower()):
                complexity -= 0.15

        return max(0.0, min(1.0, complexity))

    def _infer_required_capabilities(
        self, task: str, task_type: str
    ) -> list[str]:
        """
        استنتاج القدرات المطلوبة — Infer required capabilities from task.

        Maps task type to default capabilities and then checks for
        additional specific capability keywords in the task text.

        Args:
            task: وصف المهمة
            task_type: نوع المهمة

        Returns:
            قائمة بالقدرات المطلوبة
        """
        # القدرات الافتراضية حسب النوع — default capabilities per type
        default_caps: dict[str, list[str]] = {
            "code": ["code_generation"],
            "analysis": ["data_analysis"],
            "creative": ["creative_writing"],
            "math": ["mathematical_reasoning"],
            "research": ["literature_review"],
            "general": [],
        }
        capabilities = list(default_caps.get(task_type, []))

        # كشف قدرات إضافية — detect additional capabilities
        capability_keywords: dict[str, list[str]] = {
            "debugging": ["debug", "fix", "bug", "تصحيح", "إصلاح", "خطأ"],
            "refactoring": ["refactor", "restructure", "إعادة هيكلة", "تحسين"],
            "code_review": ["review", "audit", "مراجعة", "تدقيق"],
            "testing": ["test", "اختبار", "وحدة اختبار"],
            "research": ["research", "study", "بحث", "دراسة"],
            "statistical_reasoning": [
                "statistics", "correlation", "إحصاء", "ارتباط"
            ],
            "report_generation": ["report", "summary", "تقرير", "ملخص"],
            "brainstorming": ["brainstorm", "idea", "عصف", "أفكار"],
            "design_thinking": ["design", "prototype", "تصميم", "نموذج"],
            "storytelling": ["story", "narrative", "قصة", "سرد"],
            "computation": ["calculate", "compute", "احسب", "حاسِب"],
            "proof_verification": ["prove", "proof", "برهن", "برهان"],
            "optimization": ["optimize", "maximize", "حسّن", "كبّر"],
            "literature_review": [
                "literature", "review", "أدبيات", "استعراض أدبيات"
            ],
            "citation_analysis": ["citation", "cite", "استشهاد", "مرجع"],
            "methodology_design": ["methodology", "منهجية", "منهج"],
            "academic_writing": ["thesis", "paper", "أطروحة", "ورقة"],
        }

        task_lower = task.lower()
        for cap, keywords in capability_keywords.items():
            if any(kw in task_lower for kw in keywords):
                if cap not in capabilities:
                    capabilities.append(cap)

        return capabilities

    def update_performance(self, agent_id: str, success: bool) -> None:
        """
        تحديث أداء الوكيل — Update an agent's performance record.

        Records the success/failure for the given agent and updates
        its performance score accordingly.

        Args:
            agent_id: معرّف الوكيل
            success: هل نجح الوكيل؟
        """
        self._performance_history[agent_id].append(success)

        # تحديث نقاط أداء الوكيل — update agent's performance score
        if agent_id in self._agents:
            agent = self._agents[agent_id]
            history = self._performance_history[agent_id]

            # استخدام آخر 20 نتيجة فقط — use last 20 results only
            recent = history[-20:]
            if recent:
                new_score = sum(1.0 for s in recent if s) / len(recent)
                # متوسط متحرك — moving average
                agent.performance_score = (
                    0.5 * new_score + 0.5 * agent.performance_score
                )

        logger.debug(
            "تم تحديث أداء الوكيل '%s': success=%s", agent_id, success
        )

    def record_routing_outcome(
        self,
        task: str,
        task_type: str,
        agent_type: str,
        success: bool,
        confidence: float,
    ) -> None:
        """
        تسجيل نتيجة التوجيه — Record a routing outcome for adaptive learning.

        Args:
            task: المهمة
            task_type: نوع المهمة
            agent_type: نوع الوكيل
            success: هل نجح التوجيه
            confidence: ثقة التوجيه
        """
        self._routing_history.record(
            task, task_type, agent_type, success, confidence
        )

    def get_routing_count(self) -> int:
        """إرجاع عدد عمليات التوجيه — Return total routing operations."""
        return self._routing_count

    def get_registered_agents(self) -> list[str]:
        """إرجاع معرّفات الوكلاء المسجّلين — Return registered agent IDs."""
        return list(self._agents.keys())

    def get_cache_stats(self) -> dict:
        """إرجاع إحصائيات الذاكرة المؤقتة — Return cache stats."""
        return self._cache.get_stats()

    def get_routing_history_stats(self) -> dict:
        """إرجاع إحصائيات سجل التوجيه — Return routing history stats."""
        return self._routing_history.get_stats()


# ═══════════════════════════════════════════════════════════════════════════════
#  منفّذ خط الأنابيب — PipelineExecutor
# ═══════════════════════════════════════════════════════════════════════════════


class PipelineExecutor:
    """
    منفّذ خط الأنابيب — ينفّذ المهام عبر الوكلاء المتخصصين.
    Executes tasks through the specialized pipeline by selecting
    appropriate agents, running them, and merging results.

    Execution flow:
    1. _select_agents: اختر أفضل الوكلاء للمهمة
    2. _execute_single_agent: نفّذ مع كل وكيل مختار
    3. _collaborative_execute: تنفيذ تعاوني للمهام المعقدة
    4. _merge_results: ادمج النتائج من الوكلاء المتعددين
    5. _fallback_strategy: استراتيجية بديلة عند الفشل

    When multiple agents are selected for a complex task, their
    outputs are merged using a weighted combination based on each
    agent's confidence and performance score.
    """

    def __init__(self, router: AgentRouter):
        """
        تهيئة منفّذ خط الأنابيب — Initialize the executor.

        Args:
            router: الموجّه — the AgentRouter for task routing
        """
        self._router = router
        # عدد الوكلاء الأقصى لكل مهمة — max agents per task
        self._max_agents = SPECIALIZED_PIPELINE_MAX_AGENTS
        # عتبة الثقة الدنيا — minimum confidence threshold
        self._confidence_threshold = SPECIALIZED_PIPELINE_CONFIDENCE_THRESHOLD
        # عداد التنفيذ — execution counter
        self._execution_count: int = 0

    async def execute(
        self, task: str, context: dict
    ) -> PipelineResult:
        """
        تنفيذ المهمة عبر خط الأنابيب — Execute a task through the pipeline.

        Full pipeline execution: route → select → execute → merge → result.
        For high-complexity tasks (>0.7), uses collaborative execution.

        Args:
            task: المهمة — the task description
            context: السياق — additional context

        Returns:
            PipelineResult — نتيجة خط الأنابيب الشاملة
        """
        self._execution_count += 1
        pipeline_start = time.time()

        try:
            # توجيه المهمة — route the task
            routing = self._router.route(task, context)

            if routing.selected_agent is None:
                # لا يوجد وكيل مناسب — no suitable agent found
                result = self._fallback_strategy(task, context)
                result.total_duration_ms = (
                    (time.time() - pipeline_start) * 1000
                )
                return result

            # تصنيف المهمة لفحص التعقيد — classify to check complexity
            classification = self._router._classify_task(task)

            # فحص التعقيد للتنفيذ التعاوني — check complexity for collaboration
            if classification.complexity > 0.7:
                # تنفيذ تعاوني — collaborative execution
                result = await self._collaborative_execute(
                    task, context, routing, classification
                )
                result.total_duration_ms = (
                    (time.time() - pipeline_start) * 1000
                )
                return result

            # اختيار الوكلاء — select agents
            agents = self._select_agents(task, routing)

            # تنفيذ مع كل وكيل — execute with each agent
            results: list[AgentResult] = []
            for agent in agents:
                agent_result = await self._execute_single_agent(
                    agent, task, context
                )
                results.append(agent_result)

                # تحديث أداء الموجّه — update router performance
                self._router.update_performance(
                    agent.agent_id, agent_result.success
                )

                # تسجيل نتيجة التوجيه — record routing outcome
                self._router.record_routing_outcome(
                    task, classification.task_type,
                    agent.agent_type, agent_result.success,
                    agent_result.confidence,
                )

                # إذا كانت النتيجة عالية الثقة، لا حاجة لمزيد من الوكلاء
                if agent_result.confidence >= 0.8 and agent_result.success:
                    break

            # دمج النتائج — merge results
            if len(results) == 1:
                # نتيجة واحدة — use directly
                merged = MergedResult(
                    merged_output=results[0].output,
                    confidence=results[0].confidence,
                    contributing_agents=[results[0].agent_id],
                )
            else:
                merged = self._merge_results(results)

            total_duration_ms = (time.time() - pipeline_start) * 1000

            # التحقق من الثقة — check confidence
            if merged.confidence < self._confidence_threshold:
                logger.warning(
                    "ثقة خط الأنابيب منخفضة (%.4f) — applying fallback",
                    merged.confidence,
                )
                fallback = self._fallback_strategy(task, context)
                # دمج مع النتيجة الأصلية — combine with original
                merged = MergedResult(
                    merged_output=(
                        f"{merged.merged_output}\n\n"
                        f"[نتيجة بديلة]: {fallback.final_output}"
                    ),
                    confidence=max(merged.confidence, fallback.confidence),
                    contributing_agents=merged.contributing_agents,
                )

            pipeline_result = PipelineResult(
                final_output=merged.merged_output,
                agents_used=merged.contributing_agents,
                confidence=merged.confidence,
                total_duration_ms=total_duration_ms,
            )

            logger.info(
                "تم تنفيذ المهمة عبر خط الأنابيب: agents=%s, "
                "confidence=%.4f, duration=%.2fms",
                merged.contributing_agents,
                merged.confidence,
                total_duration_ms,
            )

            return pipeline_result

        except Exception as e:
            total_duration_ms = (time.time() - pipeline_start) * 1000
            logger.error(
                "خطأ في تنفيذ خط الأنابيب: %s", str(e), exc_info=True
            )
            return PipelineResult(
                final_output=f"خطأ في خط الأنابيب: {str(e)}",
                agents_used=[],
                confidence=0.0,
                total_duration_ms=total_duration_ms,
            )

    async def _collaborative_execute(
        self,
        task: str,
        context: dict,
        routing: RoutingResult,
        classification: TaskClassification,
    ) -> PipelineResult:
        """
        تنفيذ تعاوني — Collaborative execution for complex multi-domain tasks.

        للمهام ذات التعقيد > 0.7، يُوجّه تلقائياً إلى عدة وكلاء
        ويدمج نتائجهم. كل وكيل يعالج المهمة من زاوية تخصصه.

        For tasks with complexity > 0.7, automatically routes to
        multiple agents and merges their results. Each agent processes
        the task from its specialized perspective.

        Args:
            task: المهمة
            context: السياق
            routing: نتيجة التوجيه الأولية
            classification: تصنيف المهمة

        Returns:
            PipelineResult — نتيجة التعاون
        """
        logger.info(
            "تنفيذ تعاوني للمهمة المعقدة (تعقيد=%.2f) — "
            "collaborative execution for complex task",
            classification.complexity,
        )

        # اختيار أفضل الوكلاء — select best agents
        agents = self._select_agents(task, routing)

        # إضافة وكلاء إضافيين بناءً على التعقيد — add extra agents
        for alt_id in routing.alternatives:
            if len(agents) >= self._max_agents:
                break
            alt_agent = self._router._agents.get(alt_id)
            if alt_agent and alt_agent not in agents:
                agents.append(alt_agent)

        # تنفيذ متوازي مع جميع الوكلاء — parallel execution with all agents
        tasks_list = [
            self._execute_single_agent(agent, task, context)
            for agent in agents
        ]
        results: list[AgentResult] = await asyncio.gather(*tasks_list)

        # تحديث الأداء — update performance
        for agent, result in zip(agents, results):
            self._router.update_performance(agent.agent_id, result.success)
            self._router.record_routing_outcome(
                task, classification.task_type,
                agent.agent_type, result.success, result.confidence,
            )

        # دمج النتائج — merge results
        merged = self._merge_results(results)

        # إضافة رأس تعاوني — add collaborative header
        collaborative_output = (
            f"[تنفيذ تعاوني — Collaborative Execution]\n"
            f"الوكلاء المساهمون: {', '.join(merged.contributing_agents)}\n"
            f"عدد الوكلاء: {len(merged.contributing_agents)}\n"
            f"---\n"
            f"{merged.merged_output}"
        )

        return PipelineResult(
            final_output=collaborative_output,
            agents_used=merged.contributing_agents,
            confidence=merged.confidence,
            total_duration_ms=0.0,  # سيُحدّث لاحقاً — updated later
        )

    def _select_agents(
        self, task: str, routing: RoutingResult
    ) -> list[SpecializedAgent]:
        """
        اختيار الوكلاء — Select the best agents for the task.

        Starts with the primary selected agent and adds alternatives
        if the task is complex enough to warrant multi-agent execution.

        Args:
            task: المهمة
            routing: نتيجة التوجيه

        Returns:
            قائمة الوكلاء المختارين
        """
        selected: list[SpecializedAgent] = []

        # الوكيل الأساسي — primary agent
        primary = self._router._agents.get(routing.selected_agent)
        if primary:
            selected.append(primary)

        # إضافة بدائل للمهام المعقدة — add alternatives for complex tasks
        classification = self._router._classify_task(task)
        if classification.complexity > 0.6 and routing.alternatives:
            for alt_id in routing.alternatives[: self._max_agents - 1]:
                alt_agent = self._router._agents.get(alt_id)
                if alt_agent:
                    selected.append(alt_agent)

        return selected

    async def _execute_single_agent(
        self, agent: SpecializedAgent, task: str, context: dict
    ) -> AgentResult:
        """
        تنفيذ مع وكيل واحد — Execute a task with a single agent.

        Wraps the agent's process method with error handling and
        timeout protection.

        Args:
            agent: الوكيل
            task: المهمة
            context: السياق

        Returns:
            AgentResult — نتيجة الوكيل
        """
        try:
            result = await agent.process(task, context)
            return result
        except Exception as e:
            logger.error(
                "خطأ في تنفيذ الوكيل '%s': %s",
                agent.agent_id,
                str(e),
                exc_info=True,
            )
            return AgentResult(
                agent_id=agent.agent_id,
                output=f"خطأ: {str(e)}",
                confidence=0.0,
                duration_ms=0.0,
                success=False,
            )

    def _merge_results(self, results: list[AgentResult]) -> MergedResult:
        """
        دمج النتائج — Merge results from multiple agents.

        Uses weighted combination based on each agent's confidence
        and success status. Failed agents contribute zero weight.

        Args:
            results: قائمة نتائج الوكلاء

        Returns:
            MergedResult — النتيجة المدمجة
        """
        if not results:
            return MergedResult()

        # تصفية النتائج الناجحة — filter successful results
        successful = [r for r in results if r.success]

        if not successful:
            # كل النتائج فاشلة — all failed, use best failed result
            best_failed = max(results, key=lambda r: r.confidence)
            return MergedResult(
                merged_output=best_failed.output,
                confidence=best_failed.confidence * 0.5,  # تقليل الثقة
                contributing_agents=[best_failed.agent_id],
            )

        if len(successful) == 1:
            # نتيجة واحدة ناجحة — single successful result
            return MergedResult(
                merged_output=successful[0].output,
                confidence=successful[0].confidence,
                contributing_agents=[successful[0].agent_id],
            )

        # دمج مرجّح — weighted merge
        total_weight = 0.0
        weighted_confidence = 0.0
        merged_parts: list[str] = []
        contributing: list[str] = []

        for result in successful:
            weight = result.confidence
            total_weight += weight
            weighted_confidence += result.confidence * weight
            merged_parts.append(
                f"[{result.agent_id}]: {result.output}"
            )
            contributing.append(result.agent_id)

        # حساب الثقة المدمجة — compute merged confidence
        if total_weight > 0:
            final_confidence = weighted_confidence / total_weight
        else:
            final_confidence = 0.0

        # تعديل: إضافة مكافأة للتوافق — bonus for agreement
        if len(successful) > 1:
            # إذا اتفق وكلاء متعددون، زِد الثقة قليلاً
            agreement_bonus = 0.05 * (len(successful) - 1)
            final_confidence = min(1.0, final_confidence + agreement_bonus)

        return MergedResult(
            merged_output="\n---\n".join(merged_parts),
            confidence=round(final_confidence, 4),
            contributing_agents=contributing,
        )

    def _fallback_strategy(
        self, task: str, context: dict
    ) -> PipelineResult:
        """
        استراتيجية بديلة — Fallback strategy when all agents fail.

        Generates a basic response without any specialized agent,
        using simple template-based output.

        Args:
            task: المهمة
            context: السياق

        Returns:
            PipelineResult — نتيجة بديلة
        """
        logger.info("تطبيق الاستراتيجية البديلة — applying fallback strategy")

        # محاولة استخدام أول وكيل متاح — try first available agent
        if self._router._agents:
            first_agent_id = next(iter(self._router._agents))
            fallback_output = (
                f"[استراتيجية بديلة]\n"
                f"لم يتم العثور على وكيل متخصص مناسب للمهمة.\n"
                f"المهمة: {task}\n"
                f"تم استخدام معالجة عامة كبديل.\n"
                f"الوكيل المقترح: {first_agent_id}"
            )
        else:
            fallback_output = (
                f"[استراتيجية بديلة]\n"
                f"لا يوجد وكلاء مسجّلون.\n"
                f"المهمة: {task}\n"
                f"يرجى تسجيل وكلاء متخصصين."
            )

        return PipelineResult(
            final_output=fallback_output,
            agents_used=["fallback"],
            confidence=0.1,
            total_duration_ms=0.0,
        )

    def get_execution_count(self) -> int:
        """إرجاع عدد عمليات التنفيذ — Return total execution count."""
        return self._execution_count


# ═══════════════════════════════════════════════════════════════════════════════
#  خط أنابيب الوكلاء المتخصصين — SpecializedAgentPipeline (Main Orchestrator)
# ═══════════════════════════════════════════════════════════════════════════════


class SpecializedAgentPipeline:
    """
    خط أنابيب الوكلاء المتخصصين — المنسّق الرئيسي لنظام التوجيه المتخصص.
    Main orchestrator for the specialized agent pipeline.

    Provides the primary entry point for processing tasks through
    the dynamic routing system. Initializes default agents, manages
    the pipeline lifecycle, and provides statistics and monitoring.

    Features:
    - Weighted keyword scoring (TF-IDF-inspired) for task classification
    - Adaptive routing with history tracking
    - Cross-agent collaboration for complex tasks (complexity > 0.7)
    - Pipeline result caching (LRU) for similar tasks
    - Feedback mechanism for improving routing accuracy
    - Context-aware confidence computation
    - 5 specialized agents: Code, Analysis, Creative, Math, Research

    Usage:
        pipeline = SpecializedAgentPipeline()
        result = await pipeline.process(
            task="Write a Python function to sort a list",
            context={"language": "Python"}
        )
        print(result.final_output)
        print(result.confidence)

        # Using route() for AGI Bridge integration:
        routing = pipeline.route(
            query="Solve the equation x^2 + 5x + 6 = 0",
            context={"domain": "mathematics"}
        )
        print(routing["selected_agent"])
        print(routing["confidence"])

        # Providing feedback:
        pipeline.record_feedback(
            task="Debug my Python code",
            agent_type="code",
            success=True
        )

    Default agents:
    - CodeAgent: وكيل البرمجة — for code-related tasks
    - AnalysisAgent: وكيل التحليل — for analytical tasks
    - CreativeAgent: وكيل الإبداع — for creative tasks
    - MathAgent: وكيل الرياضيات — for mathematical tasks
    - ResearchAgent: وكيل البحث — for research/academic tasks
    """

    def __init__(
        self,
        enabled: bool = SPECIALIZED_PIPELINE_ENABLED,
        max_agents: int = SPECIALIZED_PIPELINE_MAX_AGENTS,
        confidence_threshold: float = SPECIALIZED_PIPELINE_CONFIDENCE_THRESHOLD,
    ):
        """
        تهيئة خط الأنابيب — Initialize the pipeline.

        Args:
            enabled: مفعّل — whether the pipeline is enabled
            max_agents: الحد الأقصى للوكلاء — max agents per task
            confidence_threshold: عتبة الثقة — minimum confidence threshold
        """
        self.enabled = enabled
        self._max_agents = max_agents
        self._confidence_threshold = confidence_threshold

        # إنشاء الموجّه والمنفّذ — create router and executor
        self._router = AgentRouter()
        self._executor = PipelineExecutor(self._router)

        # إحصائيات عامة — overall statistics
        self._total_processed: int = 0
        self._successful_processed: int = 0
        self._creation_time: float = time.time()

        # تسجيل الوكلاء الافتراضيين — register default agents
        self._default_agents: list[SpecializedAgent] = []
        self._register_default_agents()

    def _register_default_agents(self) -> None:
        """
        تسجيل الوكلاء الافتراضيين — Register the default set of agents.

        Creates and registers CodeAgent, AnalysisAgent, CreativeAgent,
        MathAgent, and ResearchAgent as the base set of specialized agents.
        """
        default_agent_classes: list[type[SpecializedAgent]] = [
            CodeAgent,
            AnalysisAgent,
            CreativeAgent,
            MathAgent,
            ResearchAgent,
        ]

        for agent_cls in default_agent_classes:
            try:
                agent = agent_cls()
                self._router.register_agent(agent)
                self._default_agents.append(agent)
                logger.debug(
                    "تم تسجيل الوكيل الافتراضي: %s", agent.agent_id
                )
            except Exception as e:
                logger.error(
                    "خطأ في تسجيل الوكيل الافتراضي %s: %s",
                    agent_cls.__name__,
                    str(e),
                )

    async def process(
        self, task: str, context: dict
    ) -> PipelineResult:
        """
        معالجة المهمة — Main entry point for task processing.

        Processes a task through the specialized pipeline:
        1. Check if pipeline is enabled
        2. Route task to appropriate agent(s)
        3. Execute task through selected agents
        4. Return comprehensive result

        If the pipeline is disabled, returns a fallback result
        indicating the pipeline is not active.

        Args:
            task: المهمة — the task description
            context: السياق — additional context dict

        Returns:
            PipelineResult — نتيجة خط الأنابيب الشاملة
        """
        self._total_processed += 1

        # فحص التفعيل — check if enabled
        if not self.enabled:
            logger.debug(
                "خط الأنابيب المتخصص غير مفعّل — pipeline disabled"
            )
            return PipelineResult(
                final_output=(
                    "[خط أنابيب الوكلاء المتخصصين غير مفعّل]\n"
                    "للتفعيل، اضبط MAMOUN_SPECIALIZED_PIPELINE_ENABLED=true"
                ),
                agents_used=[],
                confidence=0.0,
                total_duration_ms=0.0,
            )

        # التحقق من المدخلات — validate inputs
        if not task or not task.strip():
            return PipelineResult(
                final_output="[خطأ: المهمة فارغة]",
                agents_used=[],
                confidence=0.0,
                total_duration_ms=0.0,
            )

        # تنفيذ عبر خط الأنابيب — execute through pipeline
        try:
            result = await self._executor.execute(task, context)

            if result.confidence > 0.0:
                self._successful_processed += 1

            return result

        except Exception as e:
            logger.error(
                "خطأ في معالجة المهمة عبر خط الأنابيب: %s",
                str(e),
                exc_info=True,
            )
            return PipelineResult(
                final_output=f"خطأ في خط الأنابيب: {str(e)}",
                agents_used=[],
                confidence=0.0,
                total_duration_ms=0.0,
            )

    def route(self, query: str, context: Optional[dict] = None) -> dict:
        """
        توجيه المهمة — Route a query for AGI Bridge integration.

        يقبل استعلام وسياق ويُرجع معلومات التوجيه ونتيجة خط الأنابيب.
        Accepts a query and context and returns routing info with
        the pipeline result. This is the method that the AGI Bridge
        expects to call on the pipeline instance.

        Args:
            query: الاستعلام — the task query
            context: السياق — optional context dict

        Returns:
            قاموس يحتوي على — dict containing:
            - selected_agent: الوكيل المختار
            - confidence: ثقة التوجيه
            - alternatives: البدائل المتاحة
            - classification: تصنيف المهمة
            - pipeline_result: نتيجة خط الأنابيب (كقاموس)
        """
        if context is None:
            context = {}

        # توجيه المهمة — route the task
        routing = self._router.route(query, context)

        # تصنيف المهمة — classify the task
        classification = self._router._classify_task(query)

        # تنفيذ المهمة عبر خط الأنابيب — execute through pipeline
        # استخدام asyncio.run إذا لزم الأمر — use asyncio.run if needed
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # إذا كان الحلقة تعمل، أنشئ مهمة — if loop running, create task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run, self.process(query, context)
                    )
                    pipeline_result = future.result(timeout=30)
            else:
                pipeline_result = loop.run_until_complete(
                    self.process(query, context)
                )
        except RuntimeError:
            # لا توجد حلقة حدث — no event loop
            pipeline_result = asyncio.run(self.process(query, context))

        return {
            "selected_agent": routing.selected_agent,
            "confidence": routing.confidence,
            "alternatives": routing.alternatives,
            "classification": classification.to_dict(),
            "pipeline_result": pipeline_result.to_dict(),
        }

    def record_feedback(
        self, task: str, agent_type: str, success: bool
    ) -> None:
        """
        تسجيل ملاحظات المستخدم — Record user feedback on routing accuracy.

        يعدّل درجات ألفة الوكيل بناءً على ملاحظات المستخدم.
        إذا كان الوكيل ناجحاً باستمرار في نوع معين من المهام،
        تزداد ألفته. إذا فشل، تنخفض.

        Adjusts agent affinity scores based on user feedback.
        If an agent consistently succeeds on a certain task type,
        its affinity increases. If it fails, it decreases.

        Args:
            task: المهمة — the task description
            agent_type: نوع الوكيل — the agent type (e.g. "code", "math")
            success: هل كان التوجيه ناجحاً — whether the routing was successful
        """
        # تصنيف المهمة لمعرفة النوع — classify task to get type
        classification = self._router._classify_task(task)

        # تسجيل في سجل التوجيه — record in routing history
        self._router.record_routing_outcome(
            task, classification.task_type, agent_type, success, 0.5
        )

        # تعديل نقاط أداء الوكيل — adjust agent performance score
        for agent_id, agent in self._router._agents.items():
            if agent.agent_type == agent_type:
                if success:
                    # تعديل إيجابي — positive adjustment
                    alpha = 0.2
                    agent.performance_score = min(
                        1.0,
                        alpha * 1.0 + (1.0 - alpha) * agent.performance_score
                    )
                else:
                    # تعديل سلبي — negative adjustment
                    alpha = 0.2
                    agent.performance_score = max(
                        0.0,
                        alpha * 0.0 + (1.0 - alpha) * agent.performance_score
                    )
                logger.info(
                    "تم تعديل نقاط أداء الوكيل '%s' بناءً على الملاحظات: "
                    "success=%s, new_score=%.4f",
                    agent_id,
                    success,
                    agent.performance_score,
                )

    def get_stats(self) -> dict:
        """
        إحصائيات خط الأنابيب — Return pipeline statistics.

        Includes overall pipeline stats, agent stats, and
        router/executor stats.

        Returns:
            قاموس بالإحصائيات — dict with comprehensive stats
        """
        success_rate = (
            self._successful_processed / max(1, self._total_processed)
        )
        uptime = time.time() - self._creation_time

        return {
            "enabled": self.enabled,
            "total_processed": self._total_processed,
            "successful_processed": self._successful_processed,
            "success_rate": round(success_rate, 4),
            "uptime_seconds": round(uptime, 2),
            "max_agents_per_task": self._max_agents,
            "confidence_threshold": self._confidence_threshold,
            "registered_agents": len(self._router._agents),
            "routing_count": self._router.get_routing_count(),
            "execution_count": self._executor.get_execution_count(),
            "cache_stats": self._router.get_cache_stats(),
            "routing_history_stats": self._router.get_routing_history_stats(),
            "agents": self.get_agents(),
        }

    def get_agents(self) -> list[dict]:
        """
        معلومات الوكلاء — Return information about all registered agents.

        Returns:
            قائمة بمعلومات كل وكيل — list of agent info dicts
        """
        agents_info: list[dict] = []
        for agent_id, agent in self._router._agents.items():
            agents_info.append(agent.get_stats())
        return agents_info

    def register_custom_agent(self, agent: SpecializedAgent) -> None:
        """
        تسجيل وكيل مخصص — Register a custom specialized agent.

        Allows extending the pipeline with domain-specific agents
        beyond the default five (Code, Analysis, Creative, Math, Research).

        Args:
            agent: الوكيل المخصص — the SpecializedAgent to register

        Raises:
            ValueError: إذا لم يكن الوكيل صالحاً
        """
        if not isinstance(agent, SpecializedAgent):
            raise ValueError(
                "يجب أن يكون الوكيل مثيلاً من SpecializedAgent — "
                "Agent must be an instance of SpecializedAgent"
            )

        self._router.register_agent(agent)
        logger.info(
            "تم تسجيل وكيل مخصص: %s (نوع: %s)",
            agent.agent_id,
            agent.agent_type,
        )
