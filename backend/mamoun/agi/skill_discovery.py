"""
BABSHARQII (Mamoun) v6.0 — Skill Discovery Engine
محرك اكتشاف المهارات — نظام اكتشاف وتقييم وتحسين المهارات تلقائياً من تحليل نتائج المهام وأنماط الفشل

Research basis:
  - EvoSkill: Automatic skill discovery and refinement from failure analysis.
    يكتشف المهارات المفقودة من تحليل أنماط الفشل ويُنشئ مهارات جديدة لسد الفجوات.
  - يحلل أنماط النجاح لاستخراج إجراءات قابلة لإعادة الاستخدام وتعميمها.
  - التحسين التطوري: تطور المهارات عبر الأجيال باستخدام الطفرات والتقاطع والانتقاء.

Architecture:
  ┌───────────────────────────────────────────────────────────────────────────┐
  │                        SkillDiscoveryEngine                              │
  │                                                                           │
  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐   │
  │  │  FailureAnalyzer │  │  SuccessAnalyzer │  │    SkillEvolver      │   │
  │  │  فشل → فجوات    │  │ نجاح → مهارات   │  │ تطوير تطوري        │   │
  │  └────────┬─────────┘  └────────┬─────────┘  └──────────┬───────────┘   │
  │           │                      │                       │               │
  │  ┌────────▼──────────────────────▼───────────────────────▼────────────┐  │
  │  │                 Skill Registry (في الذاكرة)                       │  │
  │  │  اكتشاف · تقييم · تحسين · ترتيب · تتبع الأجيال                  │  │
  │  └───────────────────────────────────────────────────────────────────┘  │
  └───────────────────────────────────────────────────────────────────────────┘

Env toggles:
    MAMOUN_SKILL_DISCOVERY_ENABLED (default: "false")
    MAMOUN_SKILL_DISCOVERY_MIN_FAILURES (default: 3)
    MAMOUN_SKILL_DISCOVERY_AUTO_ACTIVATE (default: "false")
"""

from __future__ import annotations

import os
import re
import time
import uuid
import hashlib
import logging
import math
from enum import Enum
from typing import Any, Optional
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger("mamoun.skill_discovery")


# ═══════════════════════════════════════════════════════════════════════════════
# ثوابت التهيئة البيئية — Environment Config
# ═══════════════════════════════════════════════════════════════════════════════

SKILL_DISCOVERY_ENABLED: bool = os.getenv(
    "MAMOUN_SKILL_DISCOVERY_ENABLED", "false"
).lower() in ("true", "1", "yes")

MIN_FAILURES: int = int(
    os.getenv("MAMOUN_SKILL_DISCOVERY_MIN_FAILURES", "3")
)

AUTO_ACTIVATE: bool = os.getenv(
    "MAMOUN_SKILL_DISCOVERY_AUTO_ACTIVATE", "false"
).lower() in ("true", "1", "yes")


# ═══════════════════════════════════════════════════════════════════════════════
# أنواع البيانات — Dataclasses
# ═══════════════════════════════════════════════════════════════════════════════


class GapType(str, Enum):
    """أنواع الفجوات المهارية — Skill gap classification"""
    KNOWLEDGE_GAP = "knowledge_gap"       # فجوة معرفية — نقص في المعلومات أو الحقائق
    PROCEDURAL_GAP = "procedural_gap"     # فجوة إجرائية — نقص في الخطوات أو الطريقة
    REASONING_GAP = "reasoning_gap"       # فجوة استنتاجية — نقص في المنطق أو الاستدلال
    SOCIAL_GAP = "social_gap"             # فجوة اجتماعية — نقص في التفاعل أو الفهم الاجتماعي
    SAFETY_GAP = "safety_gap"             # فجوة أمنية — نقص في الوعي بالسلامة أو المخاطر


@dataclass
class SkillGap:
    """
    فجوة مهارية — A detected gap in the skill set.
    فجوة مُكتشفة في مجموعة المهارات تشير إلى مهارة مفقودة يحتاجها النظام.

    Attributes:
        description: وصف الفجوة — ما المهارة المفقودة؟
        gap_type: نوع الفجوة — تصنيف الفجوة (معرفية، إجرائية، ...)
        priority: أولوية سد الفجوة (0.0–1.0) — محسوبة من التكرار × الشدة × الحداثة
        evidence: أدلة على وجود الفجوة — أمثلة من حالات الفشل
        would_prevent_count: عدد حالات الفشل التي كانت ستُمنع بهذه المهارة
    """
    description: str = ""
    gap_type: GapType = GapType.KNOWLEDGE_GAP
    priority: float = 0.0
    evidence: list[str] = field(default_factory=list)
    would_prevent_count: int = 0

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "description": self.description,
            "gap_type": self.gap_type.value,
            "priority": round(self.priority, 4),
            "evidence": self.evidence[:10],  # أقصى 10 أدلة
            "would_prevent_count": self.would_prevent_count,
        }


@dataclass
class EmergentSkill:
    """
    مهارة ناشئة — A skill that emerged from repeated successful patterns.
    مهارة ظهرت من تكرار أنماط النجاح ويمكن تعميمها وإعادة استخدامها.

    Attributes:
        name: اسم المهارة الناشئة
        procedure: الإجراء الذي أدى للنجاح (خطوات متسلسلة)
        frequency: عدد مرات ظهور النمط
        success_rate: معدل نجاح النمط عبر الحالات (0.0–1.0)
    """
    name: str = ""
    procedure: list[str] = field(default_factory=list)
    frequency: int = 0
    success_rate: float = 0.0

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "name": self.name,
            "procedure": self.procedure,
            "frequency": self.frequency,
            "success_rate": round(self.success_rate, 4),
        }


@dataclass
class DiscoveredSkill:
    """
    مهارة مُكتشفة — A fully formed discovered skill ready for use.
    مهارة مُكتشفة بالكامل جاهزة للاستخدام مع نمط محفز وإجراءات.

    Attributes:
        id: معرف فريد للمهارة
        name: اسم المهارة
        description: وصف المهارة
        pattern: النمط الذي تتعرف فيه المهارة على الموقف
        triggers: المحفزات التي تُفعّل المهارة
        actions: الإجراءات التي تنفذها المهارة
        confidence: ثقة المهارة (0.0–1.0) — مدى موثوقيتها
        generation: جيل المهارة — كم مرة تم تحسينها تطورياً
    """
    id: str = ""
    name: str = ""
    description: str = ""
    pattern: str = ""
    triggers: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    generation: int = 1

    def __post_init__(self):
        """توليد معرف تلقائي إن لم يكن موجوداً — Auto-generate ID if missing"""
        if not self.id:
            self.id = f"skill_{hashlib.md5(self.name.encode()).hexdigest()[:12]}_{uuid.uuid4().hex[:6]}"

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "pattern": self.pattern,
            "triggers": self.triggers,
            "actions": self.actions,
            "confidence": round(self.confidence, 4),
            "generation": self.generation,
        }


@dataclass
class SkillEvaluation:
    """
    تقييم مهارة — Evaluation result for a discovered skill.
    نتيجة تقييم مهارة مُكتشفة على حالات اختبار.

    Attributes:
        skill_id: معرف المهارة المُقيَّمة
        test_cases: عدد حالات الاختبار
        pass_rate: نسبة النجاح في الاختبارات (0.0–1.0)
        avg_efficiency: متوسط الكفاءة (0.0–1.0) — مدى سرعة وفعالية التنفيذ
        recommendation: التوصية (activate, refine, reject, monitor)
    """
    skill_id: str = ""
    test_cases: int = 0
    pass_rate: float = 0.0
    avg_efficiency: float = 0.0
    recommendation: str = "monitor"

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "skill_id": self.skill_id,
            "test_cases": self.test_cases,
            "pass_rate": round(self.pass_rate, 4),
            "avg_efficiency": round(self.avg_efficiency, 4),
            "recommendation": self.recommendation,
        }


@dataclass
class RankedSkill:
    """
    مهارة مُرتبة — A skill ranked by utility and urgency.
    مهارة مُرتبة حسب الفائدة والإلحاح لتحديد أولوية التفعيل.

    Attributes:
        skill: المهارة المُكتشفة
        utility_score: نقاط الفائدة — مدى نفع المهارة (0.0–1.0)
        urgency_score: نقاط الإلحاح — مدى الحاجة العاجلة (0.0–1.0)
        combined_score: النتيجة المركبة — فائدة × إلحاح (0.0–1.0)
    """
    skill: DiscoveredSkill = field(default_factory=DiscoveredSkill)
    utility_score: float = 0.0
    urgency_score: float = 0.0
    combined_score: float = 0.0

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "skill": self.skill.to_dict(),
            "utility_score": round(self.utility_score, 4),
            "urgency_score": round(self.urgency_score, 4),
            "combined_score": round(self.combined_score, 4),
        }


@dataclass
class FailureCluster:
    """
    مجموعة فشل — A cluster of related failures.
    مجموعة من حالات الفشل المرتبطة التي تشير إلى نفس الفجوة المهارية.

    Attributes:
        cluster_id: معرف المجموعة
        failures: قائمة حالات الفشل في المجموعة
        common_pattern: النمط المشترك بين حالات الفشل
        suggested_gap: الفجوة المهارية المقترحة
    """
    cluster_id: str = ""
    failures: list[dict] = field(default_factory=list)
    common_pattern: str = ""
    suggested_gap: Optional[SkillGap] = None

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "cluster_id": self.cluster_id,
            "failure_count": len(self.failures),
            "common_pattern": self.common_pattern,
            "suggested_gap": self.suggested_gap.to_dict() if self.suggested_gap else None,
        }


@dataclass
class SkillDiscoveryResult:
    """
    نتيجة اكتشاف المهارات — Complete result from a discover() call.
    نتيجة شاملة لعملية اكتشاف المهارات تشمل المهارات الجديدة والمحسنة والفجوات والتقييمات.

    Attributes:
        discovered_skills: المهارات المُكتشفة حديثاً
        refined_skills: المهارات المُحسنة
        gaps_found: الفجوات المهارية المُكتشفة
        evaluations: تقييمات المهارات
    """
    discovered_skills: list[dict] = field(default_factory=list)
    refined_skills: list[dict] = field(default_factory=list)
    gaps_found: list[dict] = field(default_factory=list)
    evaluations: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "discovered_skills": self.discovered_skills,
            "refined_skills": self.refined_skills,
            "gaps_found": self.gaps_found,
            "evaluations": self.evaluations,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FailureAnalyzer — محلل الفشل (طبقة داخلية)
# ═══════════════════════════════════════════════════════════════════════════════


class FailureAnalyzer:
    """
    محلل الفشل — Analyzes failure patterns to discover skill gaps.

    يجمع حالات الفشل المتشابهة في عناقيد ويحدد الفجوات المهارية
    التي كانت ستمنع تلك الإخفاقات. يستخدم:
    - التجميع حسب نوع الخطأ والسياق والهدف
    - تسجيل أولوية عالية للفجوات المتكررة والشديدة والحديثة
    - تصنيف الفجوات إلى خمسة أنواع
    """

    def __init__(self, min_failures: int = MIN_FAILURES):
        """
        تهيئة محلل الفشل.

        Args:
            min_failures: الحد الأدنى لحالات الفشل قبل اقتراح فجوة
        """
        self.min_failures = min_failures
        # سجل الفشل التراكمي — cumulative failure log
        self._failure_log: list[dict] = []

    def add_failure(self, failure: dict) -> None:
        """
        إضافة حالة فشل إلى السجل — Add a failure to the log.

        Args:
            failure: حالة فشل تحتوي على:
                - error_type: نوع الخطأ
                - context: السياق
                - goal: الهدف
                - severity: الشدة (0.0–1.0)
                - timestamp: وقت الحدوث (اختياري)
                - message: رسالة الخطأ
        """
        if not failure:
            return
        # إضافة طابع زمني إن لم يكن موجوداً
        if "timestamp" not in failure:
            failure["timestamp"] = time.time()
        if "severity" not in failure:
            failure["severity"] = 0.5
        self._failure_log.append(failure)

    def analyze(self, failures: list[dict]) -> list[SkillGap]:
        """
        تحليل حالات الفشل لاكتشاف الفجوات — Analyze failures for skill gaps.

        العملية:
          1. تجميع حالات الفشل المتشابهة في عناقيد
          2. تحديد الفجوة الجذرية لكل عنقود
          3. تصفية الفجوات ذات الأولوية المنخفضة

        Args:
            failures: قائمة حالات الفشل

        Returns:
            قائمة الفجوات المهارية المُكتشفة
        """
        if not failures:
            return []

        # إضافة إلى السجل التراكمي
        for f in failures:
            self.add_failure(f)

        # تجميع الفشل — cluster failures
        clusters = self._cluster_failures(failures)

        # تحديد الفجوة لكل عنقود — identify root gap
        gaps: list[SkillGap] = []
        for cluster in clusters:
            if len(cluster.failures) < self.min_failures:
                # عدد حالات الفشل أقل من الحد الأدنى
                logger.debug(
                    "عنقود '%s' يحتوي %d فشل فقط (الحد الأدنى: %d) — تم التجاهل",
                    cluster.cluster_id, len(cluster.failures), self.min_failures,
                )
                continue
            gap = self._identify_root_gap(cluster)
            if gap.priority >= 0.1:
                gaps.append(gap)

        # ترتيب حسب الأولوية — sort by priority descending
        gaps.sort(key=lambda g: g.priority, reverse=True)

        logger.info(
            "تحليل الفشل: %d فشل → %d عنقود → %d فجوة",
            len(failures), len(clusters), len(gaps),
        )

        return gaps

    def _cluster_failures(self, failures: list[dict]) -> list[FailureCluster]:
        """
        تجميع حالات الفشل المتشابهة — Group related failures into clusters.

        يجمع حالات الفشل حسب:
        1. نوع الخطأ (error_type)
        2. السياق المشترك (context)
        3. الهدف المشترك (goal)

        يستخدم مفتاح تجميع بسيط يجمع بين هذه العوامل.

        Args:
            failures: قائمة حالات الفشل

        Returns:
            قائمة عناقيد الفشل
        """
        if not failures:
            return []

        # تجميع حسب المفتاح المركب — group by composite key
        cluster_map: dict[str, list[dict]] = defaultdict(list)

        for failure in failures:
            error_type = failure.get("error_type", "unknown")
            context = failure.get("context", "")
            goal = failure.get("goal", "")

            # استخراج الكلمات المفتاحية من السياق والهدف — extract keywords
            context_words = self._extract_keywords(str(context))
            goal_words = self._extract_keywords(str(goal))

            # مفتاح التجميع: نوع الخطأ + أهم كلمتين من السياق + أهم كلمة من الهدف
            context_part = "_".join(sorted(context_words)[:2]) if context_words else "none"
            goal_part = "_".join(sorted(goal_words)[:1]) if goal_words else "none"
            cluster_key = f"{error_type}|{context_part}|{goal_part}"

            cluster_map[cluster_key].append(failure)

        # تحويل إلى عناقيد — convert to clusters
        clusters: list[FailureCluster] = []
        for key, grouped_failures in cluster_map.items():
            # تحديد النمط المشترك — determine common pattern
            common_pattern = self._find_common_pattern(grouped_failures)

            cluster = FailureCluster(
                cluster_id=f"cluster_{hashlib.md5(key.encode()).hexdigest()[:8]}",
                failures=grouped_failures,
                common_pattern=common_pattern,
            )
            clusters.append(cluster)

        return clusters

    def _identify_root_gap(self, cluster: FailureCluster) -> SkillGap:
        """
        تحديد الفجوة الجذرية لعنقود فشل — What skill would prevent this cluster?

        يحلل نمط الفشل المشترك ليحدد نوع الفجوة ووصفها وأولويتها.

        الأولوية = التكرار × الشدة × الحداثة
        - التكرار: عدد حالات الفشل في العنقود (مع تطبيع)
        - الشدة: متوسط شدة الأخطاء
        - الحداثة: مدى حداثة آخر فشل (أحدث = أعلى أولوية)

        Args:
            cluster: عنقود فشل

        Returns:
            SkillGap — الفجوة المهارية المقترحة
        """
        failures = cluster.failures
        count = len(failures)

        # حساب الشدة المتوسطة — average severity
        severities = [f.get("severity", 0.5) for f in failures]
        avg_severity = sum(severities) / max(1, len(severities))

        # حساب الحداثة — recency factor
        now = time.time()
        timestamps = [f.get("timestamp", now) for f in failures]
        latest = max(timestamps)
        age_seconds = max(0.0, now - latest)
        # تناقص أسي: نصف العمر = يوم واحد (86400 ثانية)
        recency = math.exp(-age_seconds / 86400.0)

        # حساب التكرار المعيّر — normalized frequency
        frequency = min(1.0, count / 20.0)  # 20 فشل = أعلى تكرار

        # الأولوية = التكرار × الشدة × الحداثة
        priority = frequency * avg_severity * max(0.1, recency)
        priority = max(0.0, min(1.0, priority))

        # تحديد نوع الفجوة — determine gap type
        gap_type = self._classify_gap_type(cluster)

        # وصف الفجوة — generate description
        description = self._generate_gap_description(cluster, gap_type)

        # جمع الأدلة — collect evidence
        evidence = [
            f.get("message", str(f.get("error_type", "فشل مجهول")))[:200]
            for f in failures[:10]
        ]

        gap = SkillGap(
            description=description,
            gap_type=gap_type,
            priority=priority,
            evidence=evidence,
            would_prevent_count=count,
        )

        # ربط الفجوة بالعنقود — link gap to cluster
        cluster.suggested_gap = gap

        return gap

    def _classify_gap_type(self, cluster: FailureCluster) -> GapType:
        """
        تصنيف نوع الفجوة — Classify the type of skill gap.

        يستخدم كلمات مفتاحية في النمط المشترك ونوع الخطأ لتحديد نوع الفجوة.

        Args:
            cluster: عنقود الفشل

        Returns:
            GapType — نوع الفجوة
        """
        pattern = cluster.common_pattern.lower()
        error_types = set()
        for f in cluster.failures:
            et = str(f.get("error_type", "")).lower()
            error_types.add(et)

        # كلمات مفتاحية لكل نوع فجوة — keywords for each gap type
        knowledge_keywords = {
            "unknown", "not found", "missing info", "unaware", "غير معروف",
            "معلومات ناقصة", "لا أعرف", "غير متوفر",
        }
        procedural_keywords = {
            "timeout", "failed step", "wrong order", "missing step", "مهلة",
            "خطوة مفقودة", "ترتيب خاطئ", "إجراء",
        }
        reasoning_keywords = {
            "logic error", "invalid inference", "contradiction", "fallacy",
            "خطأ منطقي", "تناقض", "استنتاج خاطئ", "مغالطة",
        }
        social_keywords = {
            "misunderstanding", "tone", "offensive", "inappropriate",
            "سوء فهم", "نبرة", "مسيء", "غير لائق", "اجتماعي",
        }
        safety_keywords = {
            "unsafe", "dangerous", "harmful", "risk", "violation",
            "غير آمن", "خطر", "مضر", "انتهاك", "سلامة",
        }

        # تسجيل النقاط لكل نوع — score each type
        scores: dict[GapType, float] = {
            GapType.KNOWLEDGE_GAP: 0.0,
            GapType.PROCEDURAL_GAP: 0.0,
            GapType.REASONING_GAP: 0.0,
            GapType.SOCIAL_GAP: 0.0,
            GapType.SAFETY_GAP: 0.0,
        }

        # فحص الكلمات المفتاحية في النمط — check keywords in pattern
        for kw in knowledge_keywords:
            if kw in pattern:
                scores[GapType.KNOWLEDGE_GAP] += 1.0
        for kw in procedural_keywords:
            if kw in pattern:
                scores[GapType.PROCEDURAL_GAP] += 1.0
        for kw in reasoning_keywords:
            if kw in pattern:
                scores[GapType.REASONING_GAP] += 1.0
        for kw in social_keywords:
            if kw in pattern:
                scores[GapType.SOCIAL_GAP] += 1.0
        for kw in safety_keywords:
            if kw in pattern:
                scores[GapType.SAFETY_GAP] += 1.0

        # فحص أنواع الأخطاء — check error types
        for et in error_types:
            if any(kw in et for kw in knowledge_keywords):
                scores[GapType.KNOWLEDGE_GAP] += 2.0
            if any(kw in et for kw in procedural_keywords):
                scores[GapType.PROCEDURAL_GAP] += 2.0
            if any(kw in et for kw in reasoning_keywords):
                scores[GapType.REASONING_GAP] += 2.0
            if any(kw in et for kw in social_keywords):
                scores[GapType.SOCIAL_GAP] += 2.0
            if any(kw in et for kw in safety_keywords):
                scores[GapType.SAFETY_GAP] += 2.0

        # اختيار النوع الأعلى تسجيلاً — pick highest scoring type
        best_type = max(scores, key=scores.get)

        # إذا كانت كل النتائج صفراً، افتراضي: فجوة معرفية
        if all(v == 0.0 for v in scores.values()):
            best_type = GapType.KNOWLEDGE_GAP

        return best_type

    def _generate_gap_description(
        self, cluster: FailureCluster, gap_type: GapType
    ) -> str:
        """
        توليد وصف الفجوة — Generate a human-readable gap description.

        Args:
            cluster: عنقود الفشل
            gap_type: نوع الفجوة

        Returns:
            وصف الفجوة
        """
        type_labels: dict[GapType, str] = {
            GapType.KNOWLEDGE_GAP: "فجوة معرفية",
            GapType.PROCEDURAL_GAP: "فجوة إجرائية",
            GapType.REASONING_GAP: "فجوة استنتاجية",
            GapType.SOCIAL_GAP: "فجوة اجتماعية",
            GapType.SAFETY_GAP: "فجوة أمنية",
        }

        type_desc: dict[GapType, str] = {
            GapType.KNOWLEDGE_GAP: "المعلومات أو الحقائق المطلوبة غير متوفرة",
            GapType.PROCEDURAL_GAP: "الخطوات أو الإجراءات الصحيحة غير معروفة",
            GapType.REASONING_GAP: "الاستنتاج أو المنطق المطلوب غير متقن",
            GapType.SOCIAL_GAP: "الفهم الاجتماعي أو مهارات التفاعل غير كافٍ",
            GapType.SAFETY_GAP: "الوعي بالسلامة أو إدارة المخاطر غير كافٍ",
        }

        error_types = set(
            f.get("error_type", "غير محدد") for f in cluster.failures
        )
        error_str = "، ".join(str(e) for e in list(error_types)[:3])

        return (
            f"{type_labels[gap_type]}: {type_desc[gap_type]}. "
            f"النمط المشترك: '{cluster.common_pattern}'. "
            f"أنواع الأخطاء: {error_str}. "
            f"عدد حالات الفشل: {len(cluster.failures)}"
        )

    @staticmethod
    def _find_common_pattern(failures: list[dict]) -> str:
        """
        تحديد النمط المشترك بين حالات الفشل — Find common pattern across failures.

        يبحث عن الكلمات الأكثر تكراراً في رسائل الأخطاء.

        Args:
            failures: قائمة حالات الفشل

        Returns:
            النمط المشترك كنص
        """
        if not failures:
            return ""

        # جمع كل الكلمات من رسائل الأخطاء — collect all words from error messages
        word_freq: dict[str, int] = defaultdict(int)
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "and", "or", "not",
            "but", "this", "that", "it", "its", "has", "have", "had",
            "be", "been", "do", "does", "did", "will", "would", "could",
            "أ", "في", "من", "على", "إلى", "عن", "مع", "هذا", "هذه",
            "أن", "لا", "لم", "لن", "هو", "هي", "كان", "كانت",
        }

        for failure in failures:
            message = str(failure.get("message", failure.get("error_type", "")))
            words = re.findall(r"\w+", message.lower())
            for word in words:
                if len(word) > 2 and word not in stop_words:
                    word_freq[word] += 1

        if not word_freq:
            # استخدام نوع الخطأ كبديل — use error_type as fallback
            error_types = [str(f.get("error_type", "")) for f in failures]
            return " | ".join(set(et for et in error_types if et))[:200]

        # أكثر 5 كلمات تكراراً — top 5 most frequent words
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        pattern = " ".join(word for word, _ in top_words)

        return pattern[:200]

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """
        استخراج الكلمات المفتاحية من نص — Extract meaningful keywords from text.

        Args:
            text: النص المصدر

        Returns:
            قائمة الكلمات المفتاحية
        """
        if not text:
            return []

        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "and", "or", "not",
            "أ", "في", "من", "على", "إلى", "عن", "مع", "هذا", "هذه",
        }

        words = re.findall(r"\w+", text.lower())
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]
        return keywords


# ═══════════════════════════════════════════════════════════════════════════════
# SuccessAnalyzer — محلل النجاح (طبقة داخلية)
# ═══════════════════════════════════════════════════════════════════════════════


class SuccessAnalyzer:
    """
    محلل النجاح — Finds patterns in successful task completions.

    يحلل حالات النجاح لاستخراج الإجراءات التي أدت إلى النجاح
    وتعميمها إلى مهارات ناشئة قابلة لإعادة الاستخدام.

    العملية:
    1. استخراج الإجراء (الخطوات) من كل حالة نجاح
    2. تعميم الإجراء ليشمل سياقات مشابهة
    3. التحقق من ثبات المهارة الناشئة عبر حالات متعددة
    """

    def __init__(self):
        """تهيئة محلل النجاح."""
        self._success_log: list[dict] = []

    def add_success(self, success: dict) -> None:
        """
        إضافة حالة نجاح إلى السجل — Add a success to the log.

        Args:
            success: حالة نجاح تحتوي على:
                - steps: الخطوات المنفذة
                - goal: الهدف المحقق
                - context: السياق
                - efficiency: الكفاءة (0.0–1.0)
                - timestamp: وقت الحدوث (اختياري)
        """
        if not success:
            return
        if "timestamp" not in success:
            success["timestamp"] = time.time()
        if "efficiency" not in success:
            success["efficiency"] = 0.5
        self._success_log.append(success)

    def analyze(self, successes: list[dict]) -> list[EmergentSkill]:
        """
        تحليل حالات النجاح لاكتشاف مهارات ناشئة — Analyze successes for emergent skills.

        العملية:
          1. استخراج الإجراءات من كل حالة نجاح
          2. تجميع الإجراءات المتشابهة
          3. تعميم كل مجموعة إلى مهارة ناشئة
          4. التحقق من ثبات المهارة

        Args:
            successes: قائمة حالات النجاح

        Returns:
            قائمة المهارات الناشئة
        """
        if not successes:
            return []

        # إضافة إلى السجل
        for s in successes:
            self.add_success(s)

        # استخراج الإجراءات — extract procedures
        procedures: list[tuple[list[str], dict]] = []
        for success in successes:
            procedure = self._extract_procedure(success)
            if procedure:
                procedures.append((procedure, success))

        if not procedures:
            return []

        # تجميع الإجراءات المتشابهة — group similar procedures
        procedure_groups = self._group_similar_procedures(procedures)

        # تعميم كل مجموعة — generalize each group
        emergent_skills: list[EmergentSkill] = []
        for group_procedures, group_successes in procedure_groups:
            if len(group_procedures) < 2:
                # نمط وحيد لا يمكن تعميمه بثقة — single pattern can't be generalized confidently
                continue

            # تعميم الإجراء — generalize procedure
            skill = self._generalize_procedure(group_procedures)

            # التحقق من ثبات المهارة — validate consistency
            consistency = self._validate_emergent_skill(skill)

            # تحديث معدل النجاح بناءً على التحقق
            skill.success_rate = consistency

            if consistency >= 0.3 and skill.frequency >= 2:
                emergent_skills.append(skill)

        # ترتيب حسب معدل النجاح — sort by success rate
        emergent_skills.sort(key=lambda s: s.success_rate, reverse=True)

        logger.info(
            "تحليل النجاح: %d نجاح → %d إجراء → %d مهارة ناشئة",
            len(successes), len(procedures), len(emergent_skills),
        )

        return emergent_skills

    def _extract_procedure(self, success: dict) -> list[str]:
        """
        استخراج الإجراء من حالة نجاح — What steps led to success?

        يستخرج الخطوات المتسلسلة التي أدت إلى النجاح من بيانات الحالة.

        Args:
            success: حالة نجاح تحتوي على خطوات وهدف وسياق

        Returns:
            قائمة الخطوات كنصوص
        """
        # محاولة استخراج الخطوات مباشرة — try to get steps directly
        steps = success.get("steps", [])
        if steps and isinstance(steps, list):
            return [str(step) for step in steps]

        # محاولة بناء الخطوات من الهدف والسياق — build from goal and context
        goal = success.get("goal", "")
        context = success.get("context", "")
        result = success.get("result", "")

        procedure: list[str] = []
        if goal:
            procedure.append(f"تحديد الهدف: {goal}")
        if context:
            procedure.append(f"تحليل السياق: {context}")
        if result:
            procedure.append(f"تحقيق النتيجة: {result}")

        return procedure

    def _generalize_procedure(
        self, procedures: list[list[str]]
    ) -> EmergentSkill:
        """
        تعميم الإجراء — Make a procedure reusable across contexts.

        يبحث عن الخطوات المشتركة بين الإجراءات المتشابهة ويُنشئ
        نمطاً عاماً قابلاً للتطبيق في سياقات مختلفة.

        Args:
            procedures: قائمة الإجراءات المتشابهة

        Returns:
            EmergentSkill — المهارة الناشئة
        """
        if not procedures:
            return EmergentSkill()

        # إيجاد الخطوات المشتركة — find common steps
        step_freq: dict[str, int] = defaultdict(int)
        for procedure in procedures:
            seen_in_this = set()
            for step in procedure:
                # تبسيط الخطوة للمقارنة — normalize step for comparison
                normalized = step.lower().strip()
                if normalized not in seen_in_this:
                    step_freq[normalized] += 1
                    seen_in_this.add(normalized)

        # الخطوات التي تظهر في أكثر من نصف الإجراءات — steps in >50% of procedures
        threshold = len(procedures) * 0.5
        common_steps = [
            step for step, freq in step_freq.items()
            if freq >= threshold
        ]

        # ترتيب الخطوات المشتركة حسب تكرار الظهور — order by frequency
        common_steps.sort(key=lambda s: step_freq[s], reverse=True)

        # توليد اسم المهارة — generate skill name
        if common_steps:
            # استخدام أهم كلمتين من الخطوات المشتركة
            all_words: list[str] = []
            for step in common_steps:
                words = re.findall(r"\w+", step)
                all_words.extend(words)
            # أكثر كلمتين تكراراً
            word_freq = defaultdict(int)
            for w in all_words:
                if len(w) > 3:
                    word_freq[w] += 1
            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:2]
            name = "_".join(w for w, _ in top_words) if top_words else "emergent_skill"
        else:
            name = "emergent_skill"

        return EmergentSkill(
            name=name,
            procedure=common_steps[:10],  # أقصى 10 خطوات
            frequency=len(procedures),
            success_rate=0.0,  # سيتم تحديثه من _validate_emergent_skill
        )

    def _validate_emergent_skill(self, skill: EmergentSkill) -> float:
        """
        التحقق من ثبات المهارة الناشئة — How consistently does it work?

        يقيس مدى ثبات المهارة الناشئة بناءً على:
        - تكرار ظهور النمط (أكثر = أكثر ثباتاً)
        - طول الإجراء المشترك (إجراء أقصر ومركّز = أكثر ثباتاً)
        - تغطية الخطوات المشتركة (نسبة الخطوات المشتركة لكل الإجراءات)

        Args:
            skill: المهارة الناشئة

        Returns:
            ثبات المهارة (0.0–1.0)
        """
        if not skill.procedure or skill.frequency == 0:
            return 0.0

        # عامل التكرار — frequency factor
        freq_score = min(1.0, skill.frequency / 10.0)

        # عامل الإيجاز — brevity factor (shorter = more focused)
        step_count = len(skill.procedure)
        brevity_score = 1.0 / (1.0 + (step_count - 3) * 0.1) if step_count >= 3 else 0.5

        # عامل التغطية — coverage factor
        coverage = min(1.0, len(skill.procedure) / 5.0)

        # النتيجة المركبة — composite score
        consistency = 0.4 * freq_score + 0.3 * brevity_score + 0.3 * coverage

        return max(0.0, min(1.0, consistency))

    def _group_similar_procedures(
        self,
        procedures: list[tuple[list[str], dict]],
    ) -> list[tuple[list[list[str]], list[dict]]]:
        """
        تجميع الإجراءات المتشابهة — Group procedures with similar patterns.

        يستخدم تشابه Jaccard على مستوى الكلمات لتجميع الإجراءات
        التي تشترك في خطوات مشابهة.

        Args:
            procedures: قائمة (إجراء، بيانات النجاح)

        Returns:
            قائمة (مجموعة إجراءات، مجموعة بيانات نجاح)
        """
        if not procedures:
            return []

        groups: list[tuple[list[list[str]], list[dict]]] = []
        assigned: set[int] = set()
        similarity_threshold = 0.3

        for i, (proc_i, success_i) in enumerate(procedures):
            if i in assigned:
                continue

            group_procs = [proc_i]
            group_successes = [success_i]
            assigned.add(i)

            for j, (proc_j, success_j) in enumerate(procedures):
                if j in assigned or j == i:
                    continue

                # حساب التشابه — compute similarity
                sim = self._compute_procedure_similarity(proc_i, proc_j)
                if sim >= similarity_threshold:
                    group_procs.append(proc_j)
                    group_successes.append(success_j)
                    assigned.add(j)

            groups.append((group_procs, group_successes))

        return groups

    @staticmethod
    def _compute_procedure_similarity(
        proc_a: list[str], proc_b: list[str]
    ) -> float:
        """
        حساب تشابه إجرائين — Compute Jaccard similarity between two procedures.

        Args:
            proc_a: الإجراء الأول
            proc_b: الإجراء الثاني

        Returns:
            التشابه (0.0–1.0)
        """
        words_a = set()
        for step in proc_a:
            words_a.update(re.findall(r"\w+", step.lower()))

        words_b = set()
        for step in proc_b:
            words_b.update(re.findall(r"\w+", step.lower()))

        if not words_a and not words_b:
            return 1.0
        if not words_a or not words_b:
            return 0.0

        intersection = words_a & words_b
        union = words_a | words_b

        return len(intersection) / len(union)


# ═══════════════════════════════════════════════════════════════════════════════
# SkillEvolver — المطور التطوري (طبقة داخلية)
# ═══════════════════════════════════════════════════════════════════════════════


class SkillEvolver:
    """
    المطور التطوري — Evolutionary improvement of skills over time.

    يحسّن المهارات عبر الأجيال باستخدام ثلاث عمليات تطورية:
    1. الطفرة: تعديل عشوائي على المحفزات والإجراءات
    2. التقاطع: دمج أجزاء من مهارتين ناجحتين
    3. الانتقاء: اختيار أفضل متغير بناءً على الاختبارات

    يتتبع جيل كل مهارة وسجل اللياقة عبر الأجيال.
    """

    def __init__(self):
        """تهيئة المطور التطوري."""
        # سجل اللياقة: skill_id → قائمة نقاط اللياقة عبر الأجيال
        self._fitness_history: dict[str, list[float]] = defaultdict(list)
        # سجل الأجيال: skill_id → الجيل الحالي
        self._generation_map: dict[str, int] = {}

    def evolve(
        self,
        skill: DiscoveredSkill,
        test_cases: list[dict],
        population_size: int = 5,
    ) -> DiscoveredSkill:
        """
        تطوير مهارة عبر التطور — Evolve a skill through mutation and selection.

        العملية:
          1. توليد متغيرات (طفرات) من المهارة
          2. اختبار كل متغير
          3. اختيار الأصلح
          4. تسجيل اللياقة

        Args:
            skill: المهارة المراد تطويرها
            test_cases: حالات الاختبار
            population_size: عدد المتغيرات المولّدة

        Returns:
            DiscoveredSkill — المهارة المُطوَّرة (أو الأصلية إن لم تتحسن)
        """
        if not test_cases:
            return skill

        # توليد المتغيرات — generate variants
        variants = self._mutate_skill(skill)

        # إضافة الأصل إلى المنافسة — add original to competition
        all_candidates = [skill] + variants

        # اختيار الأصلح — select fittest
        best = self._select_fittest(all_candidates, test_cases)

        # تسجيل اللياقة — record fitness
        fitness = self._compute_fitness(best, test_cases)
        self._fitness_history[best.id].append(fitness)
        self._generation_map[best.id] = best.generation

        if best.id != skill.id or best.generation > skill.generation:
            logger.info(
                "تطوير المهارة '%s': الجيل %d → %d (لياقة: %.4f)",
                best.name, skill.generation, best.generation, fitness,
            )
        else:
            logger.debug(
                "المهارة '%s' لم تتحسن (لياقة: %.4f)",
                best.name, fitness,
            )

        return best

    def _mutate_skill(
        self, skill: DiscoveredSkill
    ) -> list[DiscoveredSkill]:
        """
        توليد متغيرات بالطفرة — Generate skill variations through mutation.

        أنواع الطفرات:
        - إضافة محفز جديد
        - إزالة محفز عشوائي
        - إعادة صياغة إجراء
        - تعديل النمط

        Args:
            skill: المهارة الأصلية

        Returns:
            قائمة المتغيرات المُولّدة
        """
        variants: list[DiscoveredSkill] = []
        next_gen = skill.generation + 1

        # طفرة 1: إضافة محفز جديد — add new trigger
        if skill.triggers:
            new_trigger = self._generate_variant_trigger(skill)
            v1 = DiscoveredSkill(
                id="",  # سيتم توليده تلقائياً
                name=f"{skill.name}_v{next_gen}_t1",
                description=skill.description,
                pattern=skill.pattern,
                triggers=skill.triggers + [new_trigger],
                actions=list(skill.actions),
                confidence=skill.confidence * 0.9,  # ثقة أقل للمتغير الجديد
                generation=next_gen,
            )
            variants.append(v1)

        # طفرة 2: تبسيط الإجراءات — simplify actions
        if len(skill.actions) > 1:
            # إزالة إجراء عشوائي — remove a random action
            import random
            idx = random.randint(0, len(skill.actions) - 1)
            simplified_actions = [
                a for i, a in enumerate(skill.actions) if i != idx
            ]
            v2 = DiscoveredSkill(
                id="",
                name=f"{skill.name}_v{next_gen}_t2",
                description=skill.description,
                pattern=skill.pattern,
                triggers=list(skill.triggers),
                actions=simplified_actions,
                confidence=skill.confidence * 0.85,
                generation=next_gen,
            )
            variants.append(v2)

        # طفرة 3: تعميم النمط — generalize pattern
        if skill.pattern:
            generalized_pattern = self._generalize_pattern(skill.pattern)
            v3 = DiscoveredSkill(
                id="",
                name=f"{skill.name}_v{next_gen}_t3",
                description=skill.description,
                pattern=generalized_pattern,
                triggers=list(skill.triggers),
                actions=list(skill.actions),
                confidence=skill.confidence * 0.88,
                generation=next_gen,
            )
            variants.append(v3)

        return variants

    def crossover_skills(
        self, skill_a: DiscoveredSkill, skill_b: DiscoveredSkill
    ) -> DiscoveredSkill:
        """
        التقاطع بين مهارتين — Combine useful parts of two skills.

        يدمج المحفزات والإجراءات من مهارتين ناجحتين لإنشاء
        مهارة هجينة تجمع بين أفضل خصائصهما.

        Args:
            skill_a: المهارة الأولى
            skill_b: المهارة الثانية

        Returns:
            DiscoveredSkill — المهارة الهجينة
        """
        next_gen = max(skill_a.generation, skill_b.generation) + 1

        # دمج المحفزات (فريدة) — merge triggers (unique)
        combined_triggers = list(set(skill_a.triggers + skill_b.triggers))

        # دمج الإجراءات (من الأكثر ثقة أولاً) — merge actions (higher confidence first)
        if skill_a.confidence >= skill_b.confidence:
            primary_actions = list(skill_a.actions)
            secondary_actions = [
                a for a in skill_b.actions
                if a not in primary_actions
            ]
        else:
            primary_actions = list(skill_b.actions)
            secondary_actions = [
                a for a in skill_a.actions
                if a not in primary_actions
            ]
        combined_actions = primary_actions + secondary_actions[:3]  # أقصى 3 إجراءات ثانوية

        # دمج الأنماط — merge patterns
        combined_pattern = (
            f"{skill_a.pattern} | {skill_b.pattern}"
            if skill_a.pattern and skill_b.pattern
            else skill_a.pattern or skill_b.pattern
        )

        # الثقة = متوسط مرجح — confidence = weighted average
        combined_confidence = (
            (skill_a.confidence * 0.5) + (skill_b.confidence * 0.5)
        )

        # اسم هجين — hybrid name
        name_a = skill_a.name.split("_v")[0] if "_v" in skill_a.name else skill_a.name
        name_b = skill_b.name.split("_v")[0] if "_v" in skill_b.name else skill_b.name
        hybrid_name = f"{name_a}_{name_b}_hybrid"

        hybrid = DiscoveredSkill(
            id="",
            name=hybrid_name,
            description=(
                f"مهارة هجينة من '{skill_a.name}' و'{skill_b.name}': "
                f"{skill_a.description} + {skill_b.description}"
            ),
            pattern=combined_pattern,
            triggers=combined_triggers[:8],  # أقصى 8 محفزات
            actions=combined_actions[:10],   # أقصى 10 إجراءات
            confidence=combined_confidence,
            generation=next_gen,
        )

        logger.info(
            "تقاطع مهارتين: '%s' × '%s' → '%s' (جيل %d)",
            skill_a.name, skill_b.name, hybrid.name, next_gen,
        )

        return hybrid

    def _select_fittest(
        self,
        variants: list[DiscoveredSkill],
        test_cases: list[dict],
    ) -> DiscoveredSkill:
        """
        اختيار الأصلح — Pick the best variant based on test results.

        يختبر كل متغير على حالات الاختبار ويختار الأعلى لياقة.

        Args:
            variants: قائمة المتغيرات المرشحة
            test_cases: حالات الاختبار

        Returns:
            DiscoveredSkill — المتغير الأصلح
        """
        if not variants:
            raise ValueError("لا توجد متغيرات للاختيار منها")
        if not test_cases:
            return variants[0]

        best_skill = variants[0]
        best_fitness = self._compute_fitness(best_skill, test_cases)

        for variant in variants[1:]:
            fitness = self._compute_fitness(variant, test_cases)
            if fitness > best_fitness:
                best_fitness = fitness
                best_skill = variant

        return best_skill

    def _compute_fitness(
        self,
        skill: DiscoveredSkill,
        test_cases: list[dict],
    ) -> float:
        """
        حساب لياقة المهارة — Compute fitness score for a skill.

        اللياقة = (نسبة النجاح × 0.6) + (الكفاءة × 0.2) + (الإيجاز × 0.2)

        Args:
            skill: المهارة المُقيَّمة
            test_cases: حالات الاختبار

        Returns:
            نقاط اللياقة (0.0–1.0)
        """
        if not test_cases:
            return skill.confidence

        # حساب نسبة النجاح — compute pass rate
        passed = 0
        total_efficiency = 0.0

        for case in test_cases:
            # فحص هل المهارة تطابق الحالة — check if skill matches case
            is_match = self._does_skill_match_case(skill, case)
            if is_match:
                expected_outcome = case.get("expected", True)
                if expected_outcome:
                    passed += 1
                efficiency = case.get("efficiency", 0.5)
                total_efficiency += efficiency
            else:
                # المهارة لا تطابق — لا تحسب كفشل ولا كنجاح
                total_efficiency += 0.3  # كفاءة منخفضة

        pass_rate = passed / max(1, len(test_cases))
        avg_efficiency = total_efficiency / max(1, len(test_cases))

        # عامل الإيجاز — brevity factor
        action_count = len(skill.actions)
        brevity = 1.0 / (1.0 + (action_count - 3) * 0.05) if action_count >= 3 else 0.7

        # لياقة مركبة — composite fitness
        fitness = (pass_rate * 0.6) + (avg_efficiency * 0.2) + (brevity * 0.2)

        return max(0.0, min(1.0, fitness))

    @staticmethod
    def _does_skill_match_case(
        skill: DiscoveredSkill, case: dict
    ) -> bool:
        """
        هل المهارة تطابق حالة الاختبار؟ — Does skill match test case?

        يفحص هل محفزات المهارة تتوافق مع سياق حالة الاختبار.

        Args:
            skill: المهارة
            case: حالة الاختبار

        Returns:
            True إن تطابقت
        """
        case_context = str(case.get("context", case.get("goal", ""))).lower()
        case_type = str(case.get("type", "")).lower()

        # فحص تطابق المحفزات — check trigger match
        for trigger in skill.triggers:
            trigger_lower = trigger.lower()
            if trigger_lower in case_context or trigger_lower in case_type:
                return True

        # فحص تطابق النمط — check pattern match
        if skill.pattern:
            pattern_words = set(re.findall(r"\w+", skill.pattern.lower()))
            context_words = set(re.findall(r"\w+", case_context))
            if pattern_words and context_words:
                overlap = pattern_words & context_words
                if len(overlap) >= len(pattern_words) * 0.5:
                    return True

        return False

    @staticmethod
    def _generate_variant_trigger(skill: DiscoveredSkill) -> str:
        """
        توليد محفز متغير — Generate a variant trigger from existing triggers.

        يُنشئ محفزاً جديداً بتبديل كلمة في محفز موجود.

        Args:
            skill: المهارة الأصلية

        Returns:
            المحفز المتغير الجديد
        """
        if not skill.triggers:
            return f"trigger_{skill.name}"

        # اختيار محفز عشوائي كأساس — pick random trigger as base
        import random
        base = random.choice(skill.triggers)
        words = base.split()

        if len(words) > 1:
            # تبديل ترتيب الكلمات — swap word order
            idx = random.randint(0, len(words) - 1)
            words[idx] = f"alt_{words[idx]}"
            return " ".join(words)
        else:
            return f"alt_{base}"

    @staticmethod
    def _generalize_pattern(pattern: str) -> str:
        """
        تعميم النمط — Generalize a pattern by removing specific details.

        يزيل الأرقام والأسماء الخاصة لجعل النمط أكثر عمومية.

        Args:
            pattern: النمط الأصلي

        Returns:
            النمط المُعمَّم
        """
        # إزالة الأرقام — remove numbers
        generalized = re.sub(r"\d+", "N", pattern)
        # إزالة الأقواس المحتوية على تفاصيل — remove parenthetical details
        generalized = re.sub(r"\([^)]+\)", "(...)", generalized)
        return generalized

    def get_fitness_history(self, skill_id: str) -> list[float]:
        """
        الحصول على سجل اللياقة — Get fitness history for a skill.

        Args:
            skill_id: معرف المهارة

        Returns:
            قائمة نقاط اللياقة عبر الأجيال
        """
        return self._fitness_history.get(skill_id, [])

    def get_generation(self, skill_id: str) -> int:
        """
        الحصول على جيل المهارة — Get current generation of a skill.

        Args:
            skill_id: معرف المهارة

        Returns:
            رقم الجيل (0 إن لم يكن مسجلاً)
        """
        return self._generation_map.get(skill_id, 0)


# ═══════════════════════════════════════════════════════════════════════════════
# SkillDiscoveryEngine — المحرك الرئيسي
# ═══════════════════════════════════════════════════════════════════════════════


class SkillDiscoveryEngine:
    """
    محرك اكتشاف المهارات — Main entry point for skill discovery.

    يكتشف ويقيّم ويحسّن المهارات تلقائياً من تحليل نتائج المهام
    وأنماط الفشل والنجاح. يستخدم ثلاثة أنظمة فرعية:

    1. FailureAnalyzer: تحليل أنماط الفشل لاكتشاف الفجوات المهارية
       - يجمع حالات الفشل المتشابهة في عناقيد
       - يحدد الفجوة الجذرية لكل عنقود
       - يصنف الفجوات ويحسب أولوياتها

    2. SuccessAnalyzer: تحليل أنماط النجاح لاستخراج مهارات ناشئة
       - يستخرج الإجراءات التي أدت للنجاح
       - يعمم الإجراءات لتصبح قابلة لإعادة الاستخدام
       - يتحقق من ثبات المهارات عبر سياقات متعددة

    3. SkillEvolver: التحسين التطوري للمهارات عبر الأجيال
       - طفرات: تعديل المحفزات والإجراءات
       - تقاطع: دمج مهارتين ناجحتين
       - انتقاء: اختيار الأصلح بناءً على الاختبارات

    تفعيل: MAMOUN_SKILL_DISCOVERY_ENABLED=true (افتراضي: false)
    تفعيل تلقائي: MAMOUN_SKILL_DISCOVERY_AUTO_ACTIVATE=true (افتراضي: false)
    """

    def __init__(self) -> None:
        """تهيئة محرك اكتشاف المهارات ومكوناته الفرعية."""
        self._failure_analyzer = FailureAnalyzer(min_failures=MIN_FAILURES)
        self._success_analyzer = SuccessAnalyzer()
        self._skill_evolver = SkillEvolver()

        # سجل المهارات المُكتشفة — discovered skills registry
        self._skills_registry: dict[str, DiscoveredSkill] = {}

        # سجل التقييمات — evaluations registry
        self._evaluations: dict[str, SkillEvaluation] = {}

        # إحصائيات الاستخدام — usage statistics
        self._total_discover_calls: int = 0
        self._total_skills_discovered: int = 0
        self._total_skills_refined: int = 0
        self._total_gaps_found: int = 0
        self._total_evaluations: int = 0
        self._last_discover_time: float = 0.0

        logger.info(
            "تم تهيئة محرك اكتشاف المهارات — MIN_FAILURES=%d, AUTO_ACTIVATE=%s",
            MIN_FAILURES, AUTO_ACTIVATE,
        )

    # =========================================================================
    # واجهة رئيسية — Main API
    # =========================================================================

    def discover(self, task_history: list[dict]) -> dict:
        """
        اكتشاف المهارات — Main entry: analyze task history for new skills.

        العملية:
          1. فصل حالات الفشل عن حالات النجاح
          2. تحليل أنماط الفشل → فجوات مهارية
          3. تحليل أنماط النجاح → مهارات ناشئة
          4. إنشاء مهارات لسد الفجوات
          5. تحسين المهارات الموجودة
          6. تقييم المهارات
          7. ترتيب المهارات حسب الفائدة
          8. تفعيل المهارات المؤهلة (إن كان التفعيل التلقائي مفعلاً)

        Args:
            task_history: قائمة سجلات المهام تحتوي كل منها على:
                - type: نوع النتيجة (success/failure/error/partial)
                - error_type: نوع الخطأ (للفشل)
                - goal: الهدف
                - context: السياق
                - steps: الخطوات المنفذة
                - message: رسالة توضيحية
                - severity: الشدة (0.0–1.0)
                - efficiency: الكفاءة (0.0–1.0)
                - result: النتيجة
                - timestamp: الوقت (اختياري)

        Returns:
            SkillDiscoveryResult كقاموس
        """
        if not SKILL_DISCOVERY_ENABLED:
            logger.debug("اكتشاف المهارات معطل — تم التجاهل")
            return SkillDiscoveryResult().to_dict()

        start_time = time.time()
        self._total_discover_calls += 1

        # ─── الخطوة ١: فصل الفشل عن النجاح ──────────────────────────
        failures = [
            t for t in task_history
            if t.get("type") in ("failure", "error", "partial")
        ]
        successes = [
            t for t in task_history
            if t.get("type") == "success"
        ]

        discovered_skills_dicts: list[dict] = []
        refined_skills_dicts: list[dict] = []
        gaps_dicts: list[dict] = []
        evaluation_dicts: list[dict] = []

        # ─── الخطوة ٢: تحليل أنماط الفشل ────────────────────────────
        gaps: list[SkillGap] = []
        if failures:
            gaps = self._analyze_failure_patterns(failures)
            self._total_gaps_found += len(gaps)
            gaps_dicts = [g.to_dict() for g in gaps]

        # ─── الخطوة ٣: تحليل أنماط النجاح ────────────────────────────
        emergent_skills: list[EmergentSkill] = []
        if successes:
            emergent_skills = self._analyze_success_patterns(successes)

        # ─── الخطوة ٤: إنشاء مهارات لسد الفجوات ─────────────────────
        for gap in gaps:
            if gap.priority >= 0.3:
                skill = self._generate_skill(gap)
                if skill:
                    self._skills_registry[skill.id] = skill
                    discovered_skills_dicts.append(skill.to_dict())
                    self._total_skills_discovered += 1
                    logger.info(
                        "مهارة جديدة من فجوة: '%s' (ثقة: %.4f، أولوية الفجوة: %.4f)",
                        skill.name, skill.confidence, gap.priority,
                    )

        # ─── الخطوة ٥: تحويل المهارات الناشئة إلى مهارات مكتشفة ─────
        for emergent in emergent_skills:
            skill = self._emergent_to_discovered(emergent)
            if skill:
                # فحص هل توجد مهارة مشابهة — check for similar existing skill
                existing = self._find_similar_skill(skill)
                if existing:
                    # تحسين المهارة الموجودة — refine existing
                    feedback = {
                        "success": True,
                        "emergent_skill": emergent,
                    }
                    refined = self._refine_skill(existing, feedback)
                    self._skills_registry[refined.id] = refined
                    refined_skills_dicts.append({
                        "id": refined.id,
                        "name": refined.name,
                        "new_confidence": round(refined.confidence, 4),
                        "generation": refined.generation,
                    })
                    self._total_skills_refined += 1
                else:
                    self._skills_registry[skill.id] = skill
                    discovered_skills_dicts.append(skill.to_dict())
                    self._total_skills_discovered += 1

        # ─── الخطوة ٦: تحسين المهارات ذات الفجوات ───────────────────
        for gap in gaps:
            # البحث عن مهارة مُنشأة حديثاً لهذه الفجوة — find skill for gap
            for skill_id, skill in self._skills_registry.items():
                if gap.description in skill.description or skill.name in gap.description:
                    feedback = {
                        "success": False,
                        "gap": gap,
                    }
                    refined = self._refine_skill(skill, feedback)
                    self._skills_registry[refined.id] = refined
                    refined_skills_dicts.append({
                        "id": refined.id,
                        "name": refined.name,
                        "new_confidence": round(refined.confidence, 4),
                        "generation": refined.generation,
                        "refined_from_gap": True,
                    })
                    self._total_skills_refined += 1
                    break  # مهارة واحدة لكل فجوة

        # ─── الخطوة ٧: تقييم المهارات ────────────────────────────────
        test_cases = self._build_test_cases(task_history)
        for skill_id, skill in list(self._skills_registry.items()):
            evaluation = self._evaluate_skill(skill, test_cases)
            self._evaluations[skill_id] = evaluation
            self._total_evaluations += 1
            evaluation_dicts.append(evaluation.to_dict())

        # ─── الخطوة ٨: ترتيب المهارات ────────────────────────────────
        ranked = self._rank_skills_by_utility(list(self._skills_registry.values()))

        # ─── الخطوة ٩: تفعيل تلقائي ─────────────────────────────────
        if AUTO_ACTIVATE:
            for ranked_skill in ranked:
                if ranked_skill.combined_score >= 0.7:
                    logger.info(
                        "تفعيل تلقائي للمهارة '%s' (نتيجة: %.4f)",
                        ranked_skill.skill.name, ranked_skill.combined_score,
                    )

        # ─── تجميع النتيجة ───────────────────────────────────────────
        result = SkillDiscoveryResult(
            discovered_skills=discovered_skills_dicts,
            refined_skills=refined_skills_dicts,
            gaps_found=gaps_dicts,
            evaluations=evaluation_dicts,
        )

        elapsed = time.time() - start_time
        self._last_discover_time = time.time()

        logger.info(
            "اكتشاف المهارات: +%d جديد، ~%d محسّن، %d فجوة، %d تقييم (%.1f مللي ثانية)",
            len(discovered_skills_dicts), len(refined_skills_dicts),
            len(gaps_dicts), len(evaluation_dicts), elapsed * 1000,
        )

        return result.to_dict()

    # =========================================================================
    # تحليل الفشل — Failure Analysis
    # =========================================================================

    def _analyze_failure_patterns(self, failures: list[dict]) -> list[SkillGap]:
        """
        تحليل أنماط الفشل — What skills are missing?

        يُفوّض التحليل إلى FailureAnalyzer الداخلي.

        Args:
            failures: قائمة حالات الفشل

        Returns:
            قائمة الفجوات المهارية
        """
        return self._failure_analyzer.analyze(failures)

    # =========================================================================
    # تحليل النجاح — Success Analysis
    # =========================================================================

    def _analyze_success_patterns(
        self, successes: list[dict]
    ) -> list[EmergentSkill]:
        """
        تحليل أنماط النجاح — What works repeatedly?

        يُفوّض التحليل إلى SuccessAnalyzer الداخلي.

        Args:
            successes: قائمة حالات النجاح

        Returns:
            قائمة المهارات الناشئة
        """
        return self._success_analyzer.analyze(successes)

    # =========================================================================
    # إنشاء المهارات — Skill Generation
    # =========================================================================

    def _generate_skill(self, gap: SkillGap) -> Optional[DiscoveredSkill]:
        """
        إنشاء مهارة لسد فجوة — Create a skill to fill a gap.

        يُنشئ مهارة مُكتشفة جديدة بناءً على الفجوة المهارية المُحددة.
        يحول وصف الفجوة إلى محفزات وإجراءات ونمط تعرف.

        Args:
            gap: الفجوة المهارية

        Returns:
            DiscoveredSkill أو None إن لم يمكن إنشاء مهارة
        """
        if not gap.description:
            return None

        # توليد اسم المهارة من وصف الفجوة — generate name from gap description
        name = self._generate_skill_name(gap)

        # توليد المحفزات — generate triggers
        triggers = self._generate_triggers_from_gap(gap)

        # توليد الإجراءات — generate actions
        actions = self._generate_actions_from_gap(gap)

        # توليد النمط — generate pattern
        pattern = self._generate_pattern_from_gap(gap)

        # الثقة الأولية مبنية على أولوية الفجوة — initial confidence from gap priority
        confidence = min(0.7, gap.priority * 0.8)

        skill = DiscoveredSkill(
            id="",
            name=name,
            description=f"مهارة مُكتشفة لسد فجوة: {gap.description}",
            pattern=pattern,
            triggers=triggers,
            actions=actions,
            confidence=confidence,
            generation=1,
        )

        return skill

    def _generate_skill_name(self, gap: SkillGap) -> str:
        """
        توليد اسم مهارة من الفجوة — Generate a skill name from a gap.

        Args:
            gap: الفجوة المهارية

        Returns:
            اسم المهارة
        """
        # استخراج كلمات مفتاحية من الوصف — extract keywords from description
        words = re.findall(r"\w+", gap.description.lower())
        stop_words = {
            "the", "a", "an", "is", "are", "in", "on", "to", "for", "of",
            "and", "or", "not", "that", "this", "with", "from", "by",
        }
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]

        # بناء الاسم: نوع الفجوة + أهم كلمتين — build name: gap type + top 2 words
        type_prefix = gap.gap_type.value
        if keywords:
            name_parts = keywords[:3]
            name = f"{type_prefix}_{'_'.join(name_parts)}"
        else:
            name = f"{type_prefix}_skill_{uuid.uuid4().hex[:4]}"

        return name[:60]  # حد أقصى 60 حرف

    def _generate_triggers_from_gap(self, gap: SkillGap) -> list[str]:
        """
        توليد محفزات من الفجوة — Generate triggers from a skill gap.

        يستخدم الأدلة وأنواع الأخطاء لتحديد متى يجب تفعيل المهارة.

        Args:
            gap: الفجوة المهارية

        Returns:
            قائمة المحفزات
        """
        triggers: list[str] = []

        # محفز من نوع الفجوة — trigger from gap type
        type_triggers: dict[GapType, list[str]] = {
            GapType.KNOWLEDGE_GAP: [
                "معلومة غير معروفة", "unknown fact", "missing information",
            ],
            GapType.PROCEDURAL_GAP: [
                "خطوات غير واضحة", "unclear procedure", "missing steps",
            ],
            GapType.REASONING_GAP: [
                "استنتاج صعب", "complex reasoning", "logical error",
            ],
            GapType.SOCIAL_GAP: [
                "سوء فهم اجتماعي", "social misunderstanding", "tone issue",
            ],
            GapType.SAFETY_GAP: [
                "خطر محتمل", "potential risk", "safety concern",
            ],
        }
        triggers.extend(type_triggers.get(gap.gap_type, []))

        # محفزات من الأدلة — triggers from evidence
        for evidence in gap.evidence[:3]:
            # استخراج أهم كلمة من الدليل — extract key word from evidence
            words = re.findall(r"\w+", evidence.lower())
            if words:
                trigger = " ".join(words[:4])
                triggers.append(trigger)

        return triggers[:8]  # أقصى 8 محفزات

    def _generate_actions_from_gap(self, gap: SkillGap) -> list[str]:
        """
        توليد إجراءات من الفجوة — Generate actions from a skill gap.

        ينشئ إجراءات نموذجية بناءً على نوع الفجوة.

        Args:
            gap: الفجوة المهارية

        Returns:
            قائمة الإجراءات
        """
        # إجراءات نموذجية حسب نوع الفجوة — default actions per gap type
        type_actions: dict[GapType, list[str]] = {
            GapType.KNOWLEDGE_GAP: [
                "البحث عن المعلومة المفقودة",
                "التحقق من المصادر الموثوقة",
                "تسجيل المعلومة الجديدة للمرات القادمة",
            ],
            GapType.PROCEDURAL_GAP: [
                "تحليل الخطوات المطلوبة",
                "وضع خطة إجرائية واضحة",
                "اختبار الإجراء على حالات مشابهة",
            ],
            GapType.REASONING_GAP: [
                "تحليل المنطق المطلوب",
                "تحديد الافتراضات الخفية",
                "التحقق من صحة الاستنتاج",
            ],
            GapType.SOCIAL_GAP: [
                "تحليل السياق الاجتماعي",
                "مراعاة مشاعر الطرف الآخر",
                "اختيار النبرة المناسبة",
            ],
            GapType.SAFETY_GAP: [
                "تقييم المخاطر المحتملة",
                "اتخاذ الاحتياطات اللازمة",
                "التحقق من الامتثال لمعايير السلامة",
            ],
        }

        return type_actions.get(gap.gap_type, [
            "تحليل الموقف",
            "اتخاذ الإجراء المناسب",
        ])

    @staticmethod
    def _generate_pattern_from_gap(gap: SkillGap) -> str:
        """
        توليد نمط تعرف من الفجوة — Generate a recognition pattern from a gap.

        Args:
            gap: الفجوة المهارية

        Returns:
            نمط التعرف
        """
        # استخدام الأدلة كنمط — use evidence as pattern
        if gap.evidence:
            return " | ".join(gap.evidence[:3])
        return f"{gap.gap_type.value}: {gap.description[:100]}"

    # =========================================================================
    # تقييم المهارات — Skill Evaluation
    # =========================================================================

    def _evaluate_skill(
        self, skill: DiscoveredSkill, test_cases: list[dict]
    ) -> SkillEvaluation:
        """
        تقييم مهارة — Test a skill's effectiveness.

        يختبر المهارة على حالات الاختبار ويحسب نسبة النجاح والكفاءة
        ويُصدر توصية بشأن تفعيلها أو تحسينها أو رفضها.

        Args:
            skill: المهارة المُقيَّمة
            test_cases: حالات الاختبار

        Returns:
            SkillEvaluation — نتيجة التقييم
        """
        if not test_cases:
            return SkillEvaluation(
                skill_id=skill.id,
                test_cases=0,
                pass_rate=0.0,
                avg_efficiency=skill.confidence,
                recommendation="monitor",
            )

        passed = 0
        total_efficiency = 0.0
        relevant_cases = 0

        for case in test_cases:
            # فحص هل المهارة تطابق الحالة — check if skill matches case
            is_match = self._skill_evolver._does_skill_match_case(skill, case)
            if not is_match:
                continue

            relevant_cases += 1
            expected = case.get("expected", True)
            actual_success = case.get("type", "") == "success"
            efficiency = case.get("efficiency", 0.5)

            if actual_success == expected:
                passed += 1
            total_efficiency += efficiency

        if relevant_cases == 0:
            return SkillEvaluation(
                skill_id=skill.id,
                test_cases=len(test_cases),
                pass_rate=0.0,
                avg_efficiency=0.0,
                recommendation="monitor",
            )

        pass_rate = passed / relevant_cases
        avg_efficiency = total_efficiency / relevant_cases

        # تحديد التوصية — determine recommendation
        recommendation = self._determine_recommendation(
            pass_rate, avg_efficiency, skill.confidence
        )

        return SkillEvaluation(
            skill_id=skill.id,
            test_cases=relevant_cases,
            pass_rate=pass_rate,
            avg_efficiency=avg_efficiency,
            recommendation=recommendation,
        )

    @staticmethod
    def _determine_recommendation(
        pass_rate: float, efficiency: float, confidence: float
    ) -> str:
        """
        تحديد التوصية — Determine recommendation based on evaluation scores.

        Args:
            pass_rate: نسبة النجاح
            efficiency: متوسط الكفاءة
            confidence: ثقة المهارة

        Returns:
            التوصية: activate, refine, reject, أو monitor
        """
        composite = (pass_rate * 0.5) + (efficiency * 0.3) + (confidence * 0.2)

        if composite >= 0.75:
            return "activate"
        elif composite >= 0.5:
            return "refine"
        elif composite < 0.25:
            return "reject"
        else:
            return "monitor"

    # =========================================================================
    # تحسين المهارات — Skill Refinement
    # =========================================================================

    def _refine_skill(
        self, skill: DiscoveredSkill, feedback: dict
    ) -> DiscoveredSkill:
        """
        تحسين مهارة بناءً على الملاحظات — Improve based on feedback.

        يستخدم SkillEvolver الداخلي لتطوير المهارة تطورياً.
        إذا كانت الملاحظات إيجابية، يزيد الثقة.
        إذا كانت سلبية، يحاول التحسين عبر الطفرات.

        Args:
            skill: المهارة المراد تحسينها
            feedback: ملاحظات تحتوي على:
                - success: هل الاستخدام الأخير ناجح؟
                - gap: الفجوة المرتبطة (اختياري)
                - emergent_skill: المهارة الناشئة المرتبطة (اختياري)

        Returns:
            DiscoveredSkill — المهارة المُحسنة
        """
        if feedback.get("success"):
            # تحسين بسيط: زيادة الثقة — simple improvement: increase confidence
            refined = DiscoveredSkill(
                id=skill.id,
                name=skill.name,
                description=skill.description,
                pattern=skill.pattern,
                triggers=list(skill.triggers),
                actions=list(skill.actions),
                confidence=min(1.0, skill.confidence + 0.05),
                generation=skill.generation,
            )
            logger.debug(
                "تحسين مهارة '%s': ثقة %.4f → %.4f (نجاح)",
                skill.name, skill.confidence, refined.confidence,
            )
            return refined

        # تحسين تطوري: محاولة تطوير المهارة — evolutionary improvement
        test_cases = self._build_test_cases_from_feedback(feedback)

        if test_cases:
            evolved = self._skill_evolver.evolve(
                skill, test_cases, population_size=3
            )
            return evolved

        # لا اختبارات متاحة: تحسين طفيف — no test cases: minor improvement
        refined = DiscoveredSkill(
            id=skill.id,
            name=skill.name,
            description=skill.description,
            pattern=skill.pattern,
            triggers=list(skill.triggers),
            actions=list(skill.actions),
            confidence=max(0.0, skill.confidence - 0.02),  # خفض طفيف للثقة
            generation=skill.generation + 1,
        )

        return refined

    # =========================================================================
    # ترتيب المهارات — Skill Ranking
    # =========================================================================

    def _rank_skills_by_utility(
        self, skills: list[DiscoveredSkill]
    ) -> list[RankedSkill]:
        """
        ترتيب المهارات حسب الفائدة — Prioritize by utility.

        يحسب نقاط الفائدة والإلحاح والنتيجة المركبة لكل مهارة
        ويرتبها تنازلياً.

        الفائدة: مدى نفع المهارة (مبنية على الثقة والتقييم)
        الإلحاح: مدى الحاجة العاجلة (مبنية على الفجوات غير المسدودة)
        النتيجة المركبة: فائدة × إلحاح

        Args:
            skills: قائمة المهارات

        Returns:
            قائمة المهارات المُرتبة
        """
        ranked: list[RankedSkill] = []

        for skill in skills:
            # حساب الفائدة — compute utility
            evaluation = self._evaluations.get(skill.id)
            if evaluation:
                utility = (
                    (evaluation.pass_rate * 0.4)
                    + (evaluation.avg_efficiency * 0.3)
                    + (skill.confidence * 0.3)
                )
            else:
                utility = skill.confidence

            # حساب الإلحاح — compute urgency
            # هل توجد فجوة غير مسدودة تحتاج هذه المهارة؟
            urgency = self._compute_urgency(skill)

            # النتيجة المركبة — combined score
            combined = utility * urgency if urgency > 0 else utility * 0.5

            ranked.append(RankedSkill(
                skill=skill,
                utility_score=utility,
                urgency_score=urgency,
                combined_score=combined,
            ))

        # ترتيب تنازلي — sort descending
        ranked.sort(key=lambda r: r.combined_score, reverse=True)

        return ranked

    def _compute_urgency(self, skill: DiscoveredSkill) -> float:
        """
        حساب إلحاح المهارة — Compute urgency score for a skill.

        الإلحاح مرتبط بوجود فجوات غير مسدودة تتوافق مع المهارة.

        Args:
            skill: المهارة

        Returns:
            نقاط الإلحاح (0.0–1.0)
        """
        # فحص الفجوات غير المسدودة — check unresolved gaps
        urgency = 0.0
        for gap_dict in self._failure_analyzer.analyze(
            self._failure_analyzer._failure_log[-50:]  # آخر 50 فشل
        ):
            # هل المهارة تتوافق مع الفجوة؟ — does skill relate to gap?
            if (skill.name in gap_dict.description
                    or any(t in gap_dict.description for t in skill.triggers)):
                urgency = max(urgency, gap_dict.priority)

        return urgency

    # =========================================================================
    # قائمة المهارات والإحصائيات — Skills List & Statistics
    # =========================================================================

    def skills(self) -> list[dict]:
        """
        قائمة جميع المهارات المُكتشفة — List all discovered skills.

        Returns:
            قائمة قواميس المهارات مرتبة حسب الثقة
        """
        all_skills = list(self._skills_registry.values())
        all_skills.sort(key=lambda s: s.confidence, reverse=True)
        return [s.to_dict() for s in all_skills]

    def get_stats(self) -> dict:
        """
        إحصائيات الاستخدام — Usage statistics for the engine.

        Returns:
            قاموس بالإحصائيات الشاملة
        """
        # إحصائيات الفجوات حسب النوع — gap stats by type
        gap_type_counts: dict[str, int] = defaultdict(int)
        for skill in self._skills_registry.values():
            # استنتاج نوع الفجوة من اسم المهارة — infer gap type from skill name
            for gap_type in GapType:
                if gap_type.value in skill.name:
                    gap_type_counts[gap_type.value] += 1

        # إحصائيات التقييمات — evaluation stats
        eval_recommendations: dict[str, int] = defaultdict(int)
        avg_pass_rate = 0.0
        if self._evaluations:
            for ev in self._evaluations.values():
                eval_recommendations[ev.recommendation] += 1
                avg_pass_rate += ev.pass_rate
            avg_pass_rate /= len(self._evaluations)

        # إحصائيات الأجيال — generation stats
        generations = [
            s.generation for s in self._skills_registry.values()
        ]
        avg_generation = (
            sum(generations) / len(generations) if generations else 0.0
        )
        max_generation = max(generations) if generations else 0

        return {
            "enabled": SKILL_DISCOVERY_ENABLED,
            "auto_activate": AUTO_ACTIVATE,
            "total_discover_calls": self._total_discover_calls,
            "total_skills_discovered": self._total_skills_discovered,
            "total_skills_refined": self._total_skills_refined,
            "total_gaps_found": self._total_gaps_found,
            "total_evaluations": self._total_evaluations,
            "current_skills_count": len(self._skills_registry),
            "avg_pass_rate": round(avg_pass_rate, 4),
            "avg_skill_generation": round(avg_generation, 2),
            "max_skill_generation": max_generation,
            "eval_recommendations": dict(eval_recommendations),
            "gap_type_distribution": dict(gap_type_counts),
            "last_discover_time": self._last_discover_time,
            "config": {
                "min_failures": MIN_FAILURES,
                "auto_activate": AUTO_ACTIVATE,
            },
        }

    # =========================================================================
    # مساعدات داخلية — Internal Helpers
    # =========================================================================

    def _emergent_to_discovered(
        self, emergent: EmergentSkill
    ) -> Optional[DiscoveredSkill]:
        """
        تحويل مهارة ناشئة إلى مهارة مُكتشفة — Convert emergent skill to discovered.

        Args:
            emergent: المهارة الناشئة

        Returns:
            DiscoveredSkill أو None
        """
        if not emergent.name or not emergent.procedure:
            return None

        return DiscoveredSkill(
            id="",
            name=emergent.name,
            description=(
                f"مهارة ناشئة من أنماط النجاح المتكررة "
                f"(تكرار: {emergent.frequency}، معدل النجاح: {emergent.success_rate:.2f})"
            ),
            pattern=emergent.name,
            triggers=[emergent.name],
            actions=emergent.procedure,
            confidence=emergent.success_rate,
            generation=1,
        )

    def _find_similar_skill(
        self, skill: DiscoveredSkill
    ) -> Optional[DiscoveredSkill]:
        """
        البحث عن مهارة مشابهة — Find a similar existing skill.

        يستخدم تشابه Jaccard على مستوى الكلمات في الأنماط والمحفزات.

        Args:
            skill: المهارة المراد البحث عن مشابهاتها

        Returns:
            DiscoveredSkill المشابهة أو None
        """
        skill_words = set(re.findall(r"\w+", skill.pattern.lower()))
        skill_words.update(
            w for t in skill.triggers for w in re.findall(r"\w+", t.lower())
        )

        if not skill_words:
            return None

        best_match: Optional[DiscoveredSkill] = None
        best_similarity = 0.0
        similarity_threshold = 0.5

        for existing_id, existing in self._skills_registry.items():
            existing_words = set(
                re.findall(r"\w+", existing.pattern.lower())
            )
            existing_words.update(
                w for t in existing.triggers
                for w in re.findall(r"\w+", t.lower())
            )

            if not existing_words:
                continue

            # تشابه Jaccard — Jaccard similarity
            intersection = skill_words & existing_words
            union = skill_words | existing_words
            similarity = len(intersection) / len(union) if union else 0.0

            if similarity > best_similarity and similarity >= similarity_threshold:
                best_similarity = similarity
                best_match = existing

        return best_match

    @staticmethod
    def _build_test_cases(task_history: list[dict]) -> list[dict]:
        """
        بناء حالات اختبار من سجل المهام — Build test cases from task history.

        يحول سجلات المهام إلى حالات اختبار يمكن استخدامها لتقييم المهارات.

        Args:
            task_history: سجل المهام

        Returns:
            قائمة حالات الاختبار
        """
        test_cases: list[dict] = []
        for task in task_history:
            test_case = {
                "context": str(task.get("context", task.get("goal", ""))),
                "type": task.get("type", "unknown"),
                "expected": task.get("type") == "success",
                "efficiency": task.get("efficiency", 0.5),
                "goal": task.get("goal", ""),
            }
            test_cases.append(test_case)

        return test_cases

    @staticmethod
    def _build_test_cases_from_feedback(feedback: dict) -> list[dict]:
        """
        بناء حالات اختبار من الملاحظات — Build test cases from feedback.

        Args:
            feedback: ملاحظات تحتوي على فجوة أو مهارة ناشئة

        Returns:
            قائمة حالات الاختبار
        """
        test_cases: list[dict] = []

        gap = feedback.get("gap")
        if gap:
            # إنشاء حالات اختبار من أدلة الفجوة — create test cases from gap evidence
            for evidence in getattr(gap, "evidence", [])[:5]:
                test_cases.append({
                    "context": evidence,
                    "type": "failure",
                    "expected": True,  # نتوقع أن المهارة تحول دون الفشل
                    "efficiency": 0.5,
                    "goal": getattr(gap, "description", ""),
                })

        emergent = feedback.get("emergent_skill")
        if emergent:
            # إنشاء حالات اختبار من الإجراء — create test cases from procedure
            for step in getattr(emergent, "procedure", [])[:3]:
                test_cases.append({
                    "context": step,
                    "type": "success",
                    "expected": True,
                    "efficiency": getattr(emergent, "success_rate", 0.5),
                    "goal": getattr(emergent, "name", ""),
                })

        return test_cases
