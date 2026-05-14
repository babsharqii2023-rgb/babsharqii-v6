"""
BABSHARQII (Mamoun) v6.0 — Intent Drift Detector
كاشف انحراف النية — نظام مراقبة انحراف التنفيذ عن الهدف الأصلي

Implements a hierarchical intent drift detection system that monitors
action chains for deviation from the original goal. Combines multi-factor
drift scoring, goal tree tracking, scope creep detection, and early
warning to keep the agent aligned with its intended purpose.

Research basis:
    - Monitoring intent change across action chains — detect when an
      agent's execution drifts away from the original goal
    - Hierarchical intent tracking — maintain goal tree and check each
      action against intended path
    - Drift scoring — quantify how far execution has deviated from
      original intent using semantic distance, goal coverage, action
      efficiency, and step deviation
    - Early warning system — flag before completion if drift is detected
      and recommend course corrections

Architecture:
    IntentDriftDetector
    ├── IntentTracker (inner class)
    │   ├── Goal tree maintenance: main intent → sub-intents → actions
    │   ├── _parse_intent() — parse intent into structured goal tree
    │   ├── _match_action_to_goal() — which goal does action serve?
    │   └── _compute_goal_progress() — how much of intent is fulfilled?
    ├── DriftScorer (inner class)
    │   ├── Semantic distance (weight 0.35)
    │   ├── Goal coverage ratio (weight 0.25)
    │   ├── Action efficiency (weight 0.20)
    │   └── Step deviation (weight 0.20)
    └── EarlyWarningSystem (inner class)
        ├── Monitors drift trajectory over time
        ├── Flags early warning if drift accelerating
        └── Recommends course corrections

Env toggles:
    MAMOUN_INTENT_DRIFT_ENABLED — تمكين/تعطيل كاشف الانحراف (الافتراضي: false)
    MAMOUN_INTENT_DRIFT_THRESHOLD — عتبة الانحراف (الافتراضي: 0.6)
    MAMOUN_INTENT_DRIFT_WARNING_THRESHOLD — عتبة التحذير المبكر (الافتراضي: 0.4)
"""

from __future__ import annotations

import os
import re
import math
import time
import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# مفاتيح التهيئة البيئية — Environment Config
# ═══════════════════════════════════════════════════════════════════════════════

INTENT_DRIFT_ENABLED: bool = os.environ.get(
    "MAMOUN_INTENT_DRIFT_ENABLED", "false"
).lower() in ("true", "1", "yes")

INTENT_DRIFT_THRESHOLD: float = float(
    os.environ.get("MAMOUN_INTENT_DRIFT_THRESHOLD", "0.6")
)

INTENT_DRIFT_WARNING_THRESHOLD: float = float(
    os.environ.get("MAMOUN_INTENT_DRIFT_WARNING_THRESHOLD", "0.4")
)


# ═══════════════════════════════════════════════════════════════════════════════
# ثوابت النظام — System Constants
# ═══════════════════════════════════════════════════════════════════════════════

# عتبات مستويات الانحراف — Drift level thresholds
DRIFT_ON_TRACK = 0.3          # أقل من هذا → على المسار — on track
DRIFT_SLIGHT = 0.6            # أقل من هذا → انحراف طفيف — slight drift
DRIFT_SIGNIFICANT = 0.8       # أقل من هذا → انحراف كبير — significant drift
# أعلى أو يساوي 0.8 → انحراف حرج — critical drift

# أوزان عوامل الانحراف — Drift factor weights
WEIGHT_SEMANTIC_DISTANCE = 0.35   # وزن المسافة الدلالية
WEIGHT_GOAL_COVERAGE = 0.25       # وزن تغطية الهدف
WEIGHT_ACTION_EFFICIENCY = 0.20   # وزن كفاءة الإجراءات
WEIGHT_STEP_DEVIATION = 0.20      # وزن انحراف الخطوات

# إعدادات تحليل المسار — Trajectory analysis settings
MIN_ACTIONS_FOR_TRAJECTORY = 3    # الحد الأدنى للإجراءات للتنبؤ
MAX_DRIFT_HISTORY = 500           # الحد الأقصى لسجل نقاط الانحراف
TRAJECTORY_WINDOW = 10            # نافذة تحليل المسار

# كلمات التوقف — Stop words for text analysis
STOP_WORDS: set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "can", "shall", "to",
    "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "and", "or", "but", "not", "no", "if", "then", "so", "than",
    "هو", "هي", "كان", "يكون", "التي", "الذي", "الذي",
    "إلى", "من", "في", "على", "مع", "عن", "حتى", "لكي",
    "و", "أو", "لكن", "لا", "لم", "لن", "إذا", "ثم", "ف",
}

# أنماط تقسيم النية — Intent parsing patterns
INTENT_SEPARATOR_PATTERNS: list[str] = [
    r"[,،];\s*",              # فاصل بفواصل — comma separator
    r"\s+و\s*",               # حرف العطف — Arabic "و" (متصلة أو منفصلة)
    r"\s+and\s+",             # حرف العطف الإنجليزي — English "and"
    r"\s+then\s+",            # ثم — then
    r"\s+ثم\s+",              # ثم بالعربية — Arabic "then"
    r"[.!?؟]\s*",             # فاصل بجمل — sentence separator
]

# مؤشرات اختطاف الهدف — Goal hijacking indicators
GOAL_HIJACK_PATTERNS: list[str] = [
    r"\b(instead|rather|alternatively|forget\s+about|never\s+mind)\b",
    r"\b(بدلاً|عوضاً|انسَ|لا\s+تقلق|اترك)\b",
    r"\b(actually|on\s+second\s+thought|let'?s\s+do\s+something\s+else)\b",
    r"\b(في\s+الحقيقة|لن\s+نفعل|دعنا\s+نفعل\s+شيئاً\s+آخر)\b",
]


class DriftLevel(str, Enum):
    """مستويات الانحراف — Drift severity levels"""
    ON_TRACK = "on_track"              # على المسار — no drift
    SLIGHT = "slight"                  # انحراف طفيف — slight drift
    SIGNIFICANT = "significant"        # انحراف كبير — significant drift
    CRITICAL = "critical"              # انحراف حرج — critical drift


class WarningLevel(str, Enum):
    """مستويات التحذير — Warning severity levels"""
    NONE = "none"                      # لا تحذير — no warning
    CAUTION = "caution"               # حذر — caution
    ALERT = "alert"                    # تنبيه — alert
    CRITICAL = "critical"              # حرج — critical warning


# ═══════════════════════════════════════════════════════════════════════════════
# هياكل البيانات — Dataclasses
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GoalNode:
    """
    عقدة الهدف — A single node in the goal tree.
    يمثل هدفاً فرعياً أو إجراءً مرتبطاً بالنية الأصلية.
    """
    goal_text: str                                  # نص الهدف — goal text
    is_completed: bool = False                       # هل اكتمل؟ — is completed?
    children: list[GoalNode] = field(default_factory=list)  # الأهداف الفرعية
    matched_actions: list[str] = field(default_factory=list)  # الإجراءات المطابقة
    weight: float = 1.0                             # وزن الهدف — goal weight

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "goal_text": self.goal_text,
            "is_completed": self.is_completed,
            "children": [c.to_dict() for c in self.children],
            "matched_actions": self.matched_actions,
            "weight": round(self.weight, 4),
        }


@dataclass
class GoalTree:
    """
    شجرة الأهداف — Hierarchical goal tree for intent tracking.
    تمثل الهيكل الهرمي للنية: النية الرئيسية → الأهداف الفرعية → الإجراءات.
    """
    root_intent: str = ""                            # النية الأصلية — root intent
    sub_goals: list[GoalNode] = field(default_factory=list)  # الأهداف الفرعية
    completed_goals: list[str] = field(default_factory=list)  # الأهداف المكتملة

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "root_intent": self.root_intent,
            "sub_goals": [g.to_dict() for g in self.sub_goals],
            "completed_goals": self.completed_goals,
        }


@dataclass
class ScopeCreepResult:
    """
    نتيجة توسع النطاق — Result of scope creep detection.
    نتيجة فحص ما إذا كان التنفيذ يتوسع خارج النطاق الأصلي.
    """
    has_creep: bool = False                          # هل يوجد توسع؟ — is there creep?
    creep_ratio: float = 0.0                         # نسبة التوسع — creep ratio (0-1)
    expanded_areas: list[str] = field(default_factory=list)  # المناطق المتوسعة

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "has_creep": self.has_creep,
            "creep_ratio": round(self.creep_ratio, 4),
            "expanded_areas": self.expanded_areas,
        }


@dataclass
class TrajectoryPrediction:
    """
    تنبؤ المسار — Prediction of where the action chain is heading.
    تنبؤ بمسار الانحراف المستقبلي بناءً على الاتجاه الحالي.
    """
    predicted_drift: float = 0.0                     # الانحراف المتوقع — predicted drift
    confidence: float = 0.0                          # ثقة التنبؤ — prediction confidence
    time_to_threshold: Optional[int] = None          # خطوات حتى العتبة — steps to threshold

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "predicted_drift": round(self.predicted_drift, 4),
            "confidence": round(self.confidence, 4),
            "time_to_threshold": self.time_to_threshold,
        }


@dataclass
class DriftReport:
    """
    تقرير الانحراف — Comprehensive drift analysis report.
    تقرير شامل يتضمن نقاط الانحراف والتقدم والتحذيرات والتوصيات.
    """
    drift_score: float = 0.0                         # نقاط الانحراف — drift score (0-1)
    drift_level: str = "on_track"                    # مستوى الانحراف — drift level
    goal_progress: float = 0.0                       # تقدم الهدف — goal progress (0-1)
    warnings: list[str] = field(default_factory=list)  # التحذيرات — warnings
    recommended_corrections: list[str] = field(default_factory=list)  # التصحيحات المقترحة

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "drift_score": round(self.drift_score, 4),
            "drift_level": self.drift_level,
            "goal_progress": round(self.goal_progress, 4),
            "warnings": self.warnings,
            "recommended_corrections": self.recommended_corrections,
        }


@dataclass
class IntentDriftResult:
    """
    نتيجة انحراف النية — Result of a single drift tracking call.
    نتيجة تتبع انحراف نية واحدة تشمل النقاط والمستوى والتفاصيل.
    """
    drift_score: float = 0.0                         # نقاط الانحراف — drift score (0-1)
    drift_level: str = "on_track"                    # مستوى الانحراف — drift level
    is_drifting: bool = False                        # هل يوجد انحراف؟ — is drifting?
    details: dict = field(default_factory=dict)      # تفاصيل إضافية — additional details
    warnings: list[str] = field(default_factory=list)  # التحذيرات — warnings

    def to_dict(self) -> dict:
        """تحويل إلى قاموس — Convert to dictionary"""
        return {
            "drift_score": round(self.drift_score, 4),
            "drift_level": self.drift_level,
            "is_drifting": self.is_drifting,
            "details": self.details,
            "warnings": self.warnings,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# متتبع النية — IntentTracker (Inner Class)
# ═══════════════════════════════════════════════════════════════════════════════

class IntentTracker:
    """
    متتبع النية — Maintains a goal tree and tracks action-to-goal alignment.

    يحافظ على شجرة الأهداف الهرمية ويتتبع مدى توافق الإجراءات مع
    الأهداف الفرعية. يوفر تحليلاً لتقدم الهدف ومطابقة الإجراءات.

    Goal tree structure:
        root_intent (النية الأصلية)
        ├── sub_goal_1 (هدف فرعي)
        │   ├── action_1 (إجراء)
        │   └── action_2 (إجراء)
        ├── sub_goal_2 (هدف فرعي)
        │   └── action_3 (إجراء)
        └── sub_goal_3 (هدف فرعي)
    """

    def __init__(self):
        """تهيئة متتبع النية — Initialize the intent tracker."""
        self._goal_tree: Optional[GoalTree] = None
        self._original_intent_text: str = ""
        self._original_keywords: set[str] = set()

    @property
    def goal_tree(self) -> Optional[GoalTree]:
        """شجرة الأهداف — The current goal tree."""
        return self._goal_tree

    def set_intent(self, intent_text: str) -> GoalTree:
        """
        تعيين النية الأصلية — Set the original intent and build goal tree.

        Args:
            intent_text: نص النية الأصلية — original intent text

        Returns:
            GoalTree — شجرة الأهداف المُنشأة
        """
        self._original_intent_text = intent_text
        self._original_keywords = self._extract_keywords(intent_text)
        self._goal_tree = self._parse_intent(intent_text)
        return self._goal_tree

    def _parse_intent(self, intent_text: str) -> GoalTree:
        """
        تحليل النية إلى شجرة أهداف — Parse intent into structured goal tree.

        يقسم النية الأصلية إلى أهداف فرعية بناءً على الفواصل
        والعلامات اللغوية، وينشئ شجرة أهداف هرمية.

        Args:
            intent_text: نص النية — intent text

        Returns:
            GoalTree — شجرة الأهداف المُنشأة
        """
        if not intent_text or not intent_text.strip():
            return GoalTree(root_intent="")

        # تقسيم النية إلى أهداف فرعية — split intent into sub-goals
        sub_goal_texts = self._split_into_sub_goals(intent_text)

        # إنشاء شجرة الأهداف — build goal tree
        sub_goals: list[GoalNode] = []
        for idx, sg_text in enumerate(sub_goal_texts):
            sg_text = sg_text.strip()
            if not sg_text:
                continue

            # تحديد وزن الهدف — determine goal weight
            # الأهداف المذكورة أولاً تحصل على وزن أعلى
            weight = 1.0 - (idx * 0.1)
            weight = max(0.5, min(1.0, weight))

            node = GoalNode(
                goal_text=sg_text,
                weight=weight,
            )
            sub_goals.append(node)

        # إذا لم يتم العثور على أهداف فرعية، استخدم النية الكاملة
        # if no sub-goals found, use full intent
        if not sub_goals:
            sub_goals.append(GoalNode(
                goal_text=intent_text.strip(),
                weight=1.0,
            ))

        return GoalTree(
            root_intent=intent_text.strip(),
            sub_goals=sub_goals,
        )

    def _split_into_sub_goals(self, intent_text: str) -> list[str]:
        """
        تقسيم النية إلى أهداف فرعية — Split intent into sub-goals.

        يستخدم أنماط الفصل اللغوي لتقسيم النية إلى أجزاء منطقية.
        """
        # محاولة التقسيم بأنماط متعددة — try splitting with multiple patterns
        parts: list[str] = [intent_text]

        for pattern in INTENT_SEPARATOR_PATTERNS:
            new_parts: list[str] = []
            for part in parts:
                splits = re.split(pattern, part)
                new_parts.extend(s for s in splits if s.strip())
            parts = new_parts

        # تصفية الأجزاء القصيرة جداً — filter very short parts
        return [p for p in parts if len(p.strip()) >= 3]

    def _match_action_to_goal(
        self, action: str, goal_tree: GoalTree
    ) -> Optional[GoalNode]:
        """
        مطابقة الإجراء مع الهدف — Match an action to a goal in the tree.

        يبحث عن الهدف الفرعي الأكثر توافقاً مع الإجراء المحدد
        بناءً على التشابه الدلالي على مستوى الكلمات المفتاحية.

        Args:
            action: وصف الإجراء — action description
            goal_tree: شجرة الأهداف — goal tree

        Returns:
            GoalNode | None — عقدة الهدف المطابقة أو None
        """
        if not goal_tree or not goal_tree.sub_goals:
            return None

        if not action or not action.strip():
            return None

        action_keywords = self._extract_keywords(action)

        if not action_keywords:
            return None

        best_match: Optional[GoalNode] = None
        best_score = 0.0

        for sub_goal in goal_tree.sub_goals:
            goal_keywords = self._extract_keywords(sub_goal.goal_text)

            if not goal_keywords:
                continue

            # حساب تشابه Jaccard — compute Jaccard similarity
            intersection = action_keywords & goal_keywords
            union = action_keywords | goal_keywords

            if not union:
                continue

            score = len(intersection) / len(union)

            # تعزيز إذا تطابقت كلمات مفتاحية رئيسية — boost for key keyword match
            key_intersection = action_keywords & self._original_keywords
            if key_intersection:
                score = min(1.0, score + len(key_intersection) * 0.05)

            if score > best_score:
                best_score = score
                best_match = sub_goal

        # لا نعتبره مطابقة إذا كان التشابه منخفضاً جداً
        # don't consider it a match if similarity is too low
        if best_score < 0.05:
            return None

        return best_match

    def _compute_goal_progress(self, goal_tree: GoalTree) -> float:
        """
        حساب تقدم الهدف — Compute how much of the original intent is fulfilled.

        يحسب نسبة الأهداف الفرعية المكتملة مرجحة بأوزانها.

        Args:
            goal_tree: شجرة الأهداف — goal tree

        Returns:
            float — نسبة التقدم (0.0 - 1.0)
        """
        if not goal_tree or not goal_tree.sub_goals:
            return 0.0

        total_weight = 0.0
        completed_weight = 0.0

        for sub_goal in goal_tree.sub_goals:
            total_weight += sub_goal.weight
            if sub_goal.is_completed:
                completed_weight += sub_goal.weight

        if total_weight == 0:
            return 0.0

        return completed_weight / total_weight

    def record_action(self, action: str) -> Optional[GoalNode]:
        """
        تسجيل إجراء وتحديث شجرة الأهداف — Record action and update goal tree.

        Args:
            action: وصف الإجراء — action description

        Returns:
            GoalNode | None — الهدف المطابق أو None
        """
        if not self._goal_tree:
            return None

        matched_goal = self._match_action_to_goal(action, self._goal_tree)

        if matched_goal is not None:
            matched_goal.matched_actions.append(action)

            # تحديث حالة الإكمال — update completion status
            # إذا تمت مطابقة إجراء واحد على الأقل، نعتبره قيد التقدم
            # if at least one action matched, consider it in progress
            if len(matched_goal.matched_actions) >= 1:
                # تحقق من إكمال الهدف بناءً على عدد الإجراءات المطابقة
                # check goal completion based on matched action count
                # هدف بسيط يُعتبر مكملاً بإجراء واحد مطابق
                matched_goal.is_completed = True
                if matched_goal.goal_text not in self._goal_tree.completed_goals:
                    self._goal_tree.completed_goals.append(matched_goal.goal_text)

        return matched_goal

    @staticmethod
    def _extract_keywords(text: str) -> set[str]:
        """
        استخراج الكلمات المفتاحية — Extract keywords from text.

        يستبعد كلمات التوقف والكلمات القصيرة.
        """
        if not text:
            return set()

        words = set(re.findall(r"\b\w{3,}\b", text.lower()))
        return words - STOP_WORDS


# ═══════════════════════════════════════════════════════════════════════════════
# حاسب الانحراف — DriftScorer (Inner Class)
# ═══════════════════════════════════════════════════════════════════════════════

class DriftScorer:
    """
    حاسب الانحراف — Multi-factor drift score computation.

    يحسب نقاط الانحراف بناءً على أربعة عوامل مرجحة:
    1. المسافة الدلالية (0.35) — المسافة بين النية الأصلية والإجراء الحالي
    2. نسبة تغطية الهدف (0.25) — كم من الأهداف الفرعية تمت معالجته
    3. كفاءة الإجراءات (0.20) — نسبة الإجراءات المثمرة مقابل العرضية
    4. انحراف الخطوات (0.20) — هل الخطوات أكثر من المتوقع

    Drift thresholds:
        0.0 - 0.3  → على المسار (on_track)
        0.3 - 0.6  → انحراف طفيف (slight)
        0.6 - 0.8  → انحراف كبير (significant)
        0.8 - 1.0  → انحراف حرج (critical)
    """

    def __init__(
        self,
        semantic_weight: float = WEIGHT_SEMANTIC_DISTANCE,
        coverage_weight: float = WEIGHT_GOAL_COVERAGE,
        efficiency_weight: float = WEIGHT_ACTION_EFFICIENCY,
        step_weight: float = WEIGHT_STEP_DEVIATION,
    ):
        """
        تهيئة حاسب الانحراف — Initialize the drift scorer.

        Args:
            semantic_weight: وزن المسافة الدلالية
            coverage_weight: وزن تغطية الهدف
            efficiency_weight: وزن كفاءة الإجراءات
            step_weight: وزن انحراف الخطوات
        """
        self._weights = {
            "semantic": semantic_weight,
            "coverage": coverage_weight,
            "efficiency": efficiency_weight,
            "step": step_weight,
        }
        # تطبيع الأوزان — normalize weights
        total = sum(self._weights.values())
        if total > 0:
            for key in self._weights:
                self._weights[key] /= total

    def compute_drift(
        self,
        original_intent: str,
        current_state: str,
        action_chain: list[str],
        goal_progress: float,
        matched_action_count: int,
        expected_steps: Optional[int] = None,
    ) -> dict[str, float]:
        """
        حساب نقاط الانحراف — Compute multi-factor drift score.

        Args:
            original_intent: النية الأصلية — original intent
            current_state: الحالة الحالية — current state description
            action_chain: سلسلة الإجراءات — action chain
            goal_progress: تقدم الهدف — goal progress (0-1)
            matched_action_count: عدد الإجراءات المطابقة — matched actions count
            expected_steps: الخطوات المتوقعة (اختياري) — expected steps

        Returns:
            dict — نقاط الانحراف الكلية والتفصيلية
        """
        # 1. المسافة الدلالية — semantic distance
        semantic_distance = self._compute_semantic_distance(
            original_intent, current_state
        )

        # 2. نسبة تغطية الهدف — goal coverage ratio
        # التغطية المنخفضة = انحراف أعلى
        coverage_score = 1.0 - goal_progress

        # 3. كفاءة الإجراءات — action efficiency
        efficiency_score = self._compute_action_efficiency(
            action_chain, matched_action_count
        )

        # 4. انحراف الخطوات — step deviation
        step_deviation = self._compute_step_deviation(
            action_chain, expected_steps
        )

        # حساب النقاط الكلية المرجحة — compute weighted total score
        total_score = (
            semantic_distance * self._weights["semantic"]
            + coverage_score * self._weights["coverage"]
            + efficiency_score * self._weights["efficiency"]
            + step_deviation * self._weights["step"]
        )

        return {
            "total": max(0.0, min(1.0, total_score)),
            "semantic_distance": round(semantic_distance, 4),
            "coverage_deficit": round(coverage_score, 4),
            "efficiency_loss": round(efficiency_score, 4),
            "step_deviation": round(step_deviation, 4),
        }

    @staticmethod
    def _compute_semantic_distance(text_a: str, text_b: str) -> float:
        """
        حساب المسافة الدلالية — Compute semantic distance between two texts.

        يستخدم تشابه Jaccard المعكوس على مستوى الكلمات المفتاحية.
        المسافة = 1 - التشابه (1 = مختلف تماماً، 0 = متطابق).
        """
        if not text_a or not text_b:
            return 1.0

        words_a = IntentTracker._extract_keywords(text_a)
        words_b = IntentTracker._extract_keywords(text_b)

        if not words_a and not words_b:
            return 0.0
        if not words_a or not words_b:
            return 1.0

        intersection = words_a & words_b
        union = words_a | words_b

        similarity = len(intersection) / len(union)
        return 1.0 - similarity

    @staticmethod
    def _compute_action_efficiency(
        action_chain: list[str],
        matched_count: int,
    ) -> float:
        """
        حساب كفاءة الإجراءات — Compute action efficiency score.

        نسبة الإجراءات العرضية = 1 - (الإجراءات المثمرة / إجمالي الإجراءات)
        كلما زادت الإجراءات العرضية، زاد الانحراف.
        """
        total = len(action_chain)
        if total == 0:
            return 0.0

        productive_ratio = matched_count / total
        return 1.0 - productive_ratio

    @staticmethod
    def _compute_step_deviation(
        action_chain: list[str],
        expected_steps: Optional[int] = None,
    ) -> float:
        """
        حساب انحراف الخطوات — Compute step deviation score.

        إذا تجاوز عدد الخطوات العدد المتوقع، يزداد الانحراف.
        في غياب العدد المتوقع، يُقدر بناءً على تعقيد النية.
        """
        actual_steps = len(action_chain)
        if actual_steps == 0:
            return 0.0

        if expected_steps is None:
            # تقدير المتوقع: عدد الإجراءات المعقول
            # estimate: reasonable number of actions
            # عادةً كل مهمة تحتاج 3-7 خطوات
            expected_steps = max(3, min(10, actual_steps))

        if expected_steps <= 0:
            return 0.0

        if actual_steps <= expected_steps:
            # ضمن الحدود المتوقعة — within expected bounds
            return 0.0

        # حساب نسبة التجاوز — compute excess ratio
        excess_ratio = (actual_steps - expected_steps) / expected_steps

        # تحويل إلى نقاط انحراف — convert to drift score
        # تجاوز 50% = انحراف كامل
        return min(1.0, excess_ratio / 0.5)

    @staticmethod
    def classify_drift(drift_score: float) -> DriftLevel:
        """
        تصنيف مستوى الانحراف — Classify drift level based on score.

        Args:
            drift_score: نقاط الانحراف — drift score (0-1)

        Returns:
            DriftLevel — مستوى الانحراف
        """
        if drift_score < DRIFT_ON_TRACK:
            return DriftLevel.ON_TRACK
        elif drift_score < DRIFT_SLIGHT:
            return DriftLevel.SLIGHT
        elif drift_score < DRIFT_SIGNIFICANT:
            return DriftLevel.SIGNIFICANT
        else:
            return DriftLevel.CRITICAL


# ═══════════════════════════════════════════════════════════════════════════════
# نظام التحذير المبكر — EarlyWarningSystem (Inner Class)
# ═══════════════════════════════════════════════════════════════════════════════

class EarlyWarningSystem:
    """
    نظام التحذير المبكر — Monitors drift trajectory and issues early warnings.

    يراقب مسار نقاط الانحراف عبر الزمن ويكشف:
    1. تسارع الانحراف — هل الانحراف يتزايد بسرعة؟
    2. تجاوز العتبة — هل الانحراف تجاوز الحد المسموح؟
    3. التنبؤ بالمسار — أين يتجه التنفيذ؟

    يُصدر تحذيرات مبكرة وتوصيات بتصحيح المسار.
    """

    def __init__(
        self,
        drift_threshold: float = INTENT_DRIFT_THRESHOLD,
        warning_threshold: float = INTENT_DRIFT_WARNING_THRESHOLD,
        window_size: int = TRAJECTORY_WINDOW,
    ):
        """
        تهيئة نظام التحذير المبكر — Initialize early warning system.

        Args:
            drift_threshold: عتبة الانحراف — drift threshold
            warning_threshold: عتبة التحذير — warning threshold
            window_size: حجم نافذة التحليل — analysis window size
        """
        self._drift_threshold = drift_threshold
        self._warning_threshold = warning_threshold
        self._window_size = window_size
        self._drift_history: list[tuple[float, float]] = []  # (timestamp, score)

    @property
    def drift_history(self) -> list[tuple[float, float]]:
        """سجل نقاط الانحراف — Drift score history."""
        return list(self._drift_history)

    def record_drift(self, drift_score: float) -> None:
        """
        تسجيل نقطة انحراف — Record a drift score observation.

        Args:
            drift_score: نقاط الانحراف — drift score (0-1)
        """
        self._drift_history.append((time.time(), drift_score))

        # الحفاظ على حد السجل — enforce history limit
        if len(self._drift_history) > MAX_DRIFT_HISTORY:
            self._drift_history = self._drift_history[-MAX_DRIFT_HISTORY:]

    def check_warning(self, current_drift: float) -> dict:
        """
        فحص الحاجة لتحذير — Check if early warning is needed.

        Args:
            current_drift: نقاط الانحراف الحالية — current drift score

        Returns:
            dict — مستوى التحذير والإجراءات الموصى بها والثقة
        """
        # تحديد مستوى التحذير — determine warning level
        if current_drift >= self._drift_threshold:
            warning_level = WarningLevel.CRITICAL
        elif current_drift >= self._warning_threshold:
            warning_level = WarningLevel.ALERT
        elif self._is_accelerating():
            warning_level = WarningLevel.CAUTION
        else:
            warning_level = WarningLevel.NONE

        # التوصيات — recommended actions
        recommended_actions = self._generate_recommendations(
            current_drift, warning_level
        )

        # حساب الثقة — compute confidence
        confidence = self._compute_confidence(current_drift)

        return {
            "warning_level": warning_level.value,
            "recommended_actions": recommended_actions,
            "confidence": round(confidence, 4),
        }

    def _is_accelerating(self) -> bool:
        """
        هل الانحراف يتسارع؟ — Is drift accelerating?

        يحلل اتجاه نقاط الانحراف الأخيرة لتحديد التسارع.
        """
        if len(self._drift_history) < MIN_ACTIONS_FOR_TRAJECTORY:
            return False

        recent = self._drift_history[-self._window_size:]
        if len(recent) < 2:
            return False

        # حساب معدل التغير — compute rate of change
        scores = [s for _, s in recent]

        # مقارنة النصف الأول بالنصف الثاني — compare first half with second half
        mid = len(scores) // 2
        first_half_avg = sum(scores[:mid]) / max(1, mid)
        second_half_avg = sum(scores[mid:]) / max(1, len(scores) - mid)

        # التسارع = النصف الثاني أعلى من الأول — acceleration = second half higher
        return second_half_avg > first_half_avg * 1.2

    def _generate_recommendations(
        self,
        current_drift: float,
        warning_level: WarningLevel,
    ) -> list[str]:
        """
        توليد التوصيات — Generate recommended actions based on drift state.

        ينتج توصيات لتصحيح المسار بناءً على مستوى التحذير.
        """
        actions: list[str] = []

        if warning_level == WarningLevel.CRITICAL:
            actions.append(
                "توقف فوراً وأعد تقييم الهدف — Stop immediately and reassess the goal"
            )
            actions.append(
                "راجع سلسلة الإجراءات وحدد نقطة الانحراف — "
                "Review action chain and identify drift point"
            )
            actions.append(
                "أعد التنفيذ من آخر نقطة على المسار — "
                "Re-execute from last on-track point"
            )
        elif warning_level == WarningLevel.ALERT:
            actions.append(
                "راجع الإجراء الحالي مقابل النية الأصلية — "
                "Review current action against original intent"
            )
            actions.append(
                "فكر في إعادة توجيه التنفيذ — "
                "Consider redirecting execution"
            )
        elif warning_level == WarningLevel.CAUTION:
            actions.append(
                "راقب عن كثب — Monitor closely"
            )
            actions.append(
                "تحقق من توافق الإجراءات القادمة — "
                "Verify alignment of upcoming actions"
            )

        return actions

    def _compute_confidence(self, current_drift: float) -> float:
        """
        حساب ثقة التحذير — Compute confidence of the warning.

        تعتمد الثقة على عدد نقاط البيانات المتاحة
        ومدى استقرار نقاط الانحراف.
        """
        # عامل عدد الملاحظات — observation count factor
        n_observations = len(self._drift_history)
        count_factor = min(1.0, n_observations / 10.0)

        # عامل استقرار النقاط — score stability factor
        if n_observations >= 2:
            recent_scores = [s for _, s in self._drift_history[-5:]]
            if len(recent_scores) >= 2:
                avg = sum(recent_scores) / len(recent_scores)
                variance = sum((s - avg) ** 2 for s in recent_scores) / len(recent_scores)
                stability = 1.0 / (1.0 + variance * 10)
            else:
                stability = 0.5
        else:
            stability = 0.3

        # عامل شدة الانحراف — drift intensity factor
        intensity = min(1.0, current_drift * 2)

        return (count_factor * 0.3 + stability * 0.4 + intensity * 0.3)

    def predict_trajectory(self) -> TrajectoryPrediction:
        """
        التنبؤ بمسار الانحراف — Predict future drift trajectory.

        يحلل اتجاه نقاط الانحراف ويتنبأ بالقيم المستقبلية
        بناءً على الانحدار الخطي البسيط.

        Returns:
            TrajectoryPrediction — تنبؤ المسار
        """
        if len(self._drift_history) < MIN_ACTIONS_FOR_TRAJECTORY:
            return TrajectoryPrediction(
                predicted_drift=0.0,
                confidence=0.0,
                time_to_threshold=None,
            )

        # استخراج النقاط الأخيرة — extract recent points
        recent = self._drift_history[-self._window_size:]
        scores = [s for _, s in recent]
        n = len(scores)

        if n < 2:
            return TrajectoryPrediction(
                predicted_drift=scores[-1] if scores else 0.0,
                confidence=0.1,
                time_to_threshold=None,
            )

        # انحدار خطي بسيط — simple linear regression
        # y = mx + b
        x_vals = list(range(n))
        y_vals = scores

        x_mean = sum(x_vals) / n
        y_mean = sum(y_vals) / n

        numerator = sum(
            (x_vals[i] - x_mean) * (y_vals[i] - y_mean)
            for i in range(n)
        )
        denominator = sum(
            (x_vals[i] - x_mean) ** 2
            for i in range(n)
        )

        if denominator == 0:
            # لا يوجد اتجاه — no trend
            return TrajectoryPrediction(
                predicted_drift=y_mean,
                confidence=0.3,
                time_to_threshold=None,
            )

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean

        # التنبؤ بالنقاط القادمة — predict next points
        # تنبؤ بعد 5 خطوات
        predicted_drift_5 = intercept + slope * (n + 4)
        predicted_drift = max(0.0, min(1.0, predicted_drift_5))

        # حساب الثقة بناءً على R² — compute confidence based on R²
        ss_res = sum(
            (y_vals[i] - (intercept + slope * x_vals[i])) ** 2
            for i in range(n)
        )
        ss_tot = sum(
            (y_vals[i] - y_mean) ** 2
            for i in range(n)
        )

        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        confidence = max(0.0, min(1.0, r_squared))

        # حساب الخطوات حتى العتبة — compute steps to threshold
        time_to_threshold = None
        if slope > 0:
            # الانحراف يتزايد — drift is increasing
            current_value = scores[-1]
            if current_value < self._drift_threshold:
                steps_remaining = (
                    (self._drift_threshold - current_value) / slope
                )
                time_to_threshold = max(1, int(math.ceil(steps_remaining)))

        return TrajectoryPrediction(
            predicted_drift=predicted_drift,
            confidence=confidence,
            time_to_threshold=time_to_threshold,
        )

    def reset(self) -> None:
        """إعادة تعيين سجل الانحراف — Reset drift history."""
        self._drift_history.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# كاشف انحراف النية الرئيسي — IntentDriftDetector
# ═══════════════════════════════════════════════════════════════════════════════

class IntentDriftDetector:
    """
    كاشف انحراف النية — Main intent drift detection system.

    يجمع بين متتبع النية وحاسب الانحراف ونظام التحذير المبكر
    لتوفير مراقبة شاملة لانحراف التنفيذ عن الهدف الأصلي.

    المكونات:
        1. IntentTracker — متتبع النية وشجرة الأهداف
        2. DriftScorer — حاسب الانحراف متعدد العوامل
        3. EarlyWarningSystem — نظام التحذير المبكر

    مثال الاستخدام:
        detector = IntentDriftDetector()

        # تتبع إجراء في سياق النية
        result = detector.track(
            action="قراءة ملف التكوين",
            intent="تحليل أداء النظام",
            action_chain=["فتح التطبيق", "قراءة ملف التكوين"],
        )

        # الحصول على تقرير شامل
        report = detector.report()
    """

    def __init__(
        self,
        drift_threshold: Optional[float] = None,
        warning_threshold: Optional[float] = None,
        custom_weights: Optional[dict[str, float]] = None,
    ):
        """
        تهيئة كاشف انحراف النية — Initialize the intent drift detector.

        Args:
            drift_threshold: عتبة الانحراف (اختياري) — drift threshold
            warning_threshold: عتبة التحذير (اختياري) — warning threshold
            custom_weights: أوزان مخصصة للعوامل (اختياري) — custom factor weights
        """
        # إعدادات البيئة — environment settings
        self._enabled = INTENT_DRIFT_ENABLED
        self._drift_threshold = drift_threshold or INTENT_DRIFT_THRESHOLD
        self._warning_threshold = warning_threshold or INTENT_DRIFT_WARNING_THRESHOLD

        # المكونات الفرعية — sub-components
        self._tracker = IntentTracker()
        self._scorer = DriftScorer(
            **(custom_weights or {})
        )
        self._warning_system = EarlyWarningSystem(
            drift_threshold=self._drift_threshold,
            warning_threshold=self._warning_threshold,
        )

        # سجل الإجراءات — action history
        self._action_history: list[str] = []
        self._matched_count: int = 0
        self._tangential_count: int = 0

        # سجل نتائج الانحراف — drift result history
        self._drift_results: list[IntentDriftResult] = []

        # النية الحالية — current intent
        self._current_intent: str = ""

        # إحصائيات — statistics
        self._total_tracks: int = 0
        self._drift_detected_count: int = 0
        self._critical_count: int = 0
        self._corrections_suggested: int = 0

        logger.info(
            "كاشف انحراف النية مهيأ — IntentDriftDetector initialized "
            "(enabled=%s, threshold=%.2f, warning_threshold=%.2f)",
            self._enabled,
            self._drift_threshold,
            self._warning_threshold,
        )

    @property
    def enabled(self) -> bool:
        """هل الكاشف مُمكّن؟ — Is the detector enabled?"""
        return self._enabled

    @property
    def tracker(self) -> IntentTracker:
        """الوصول لمتتبع النية — Access the intent tracker."""
        return self._tracker

    @property
    def scorer(self) -> DriftScorer:
        """الوصول لحاسب الانحراف — Access the drift scorer."""
        return self._scorer

    @property
    def warning_system(self) -> EarlyWarningSystem:
        """الوصول لنظام التحذير المبكر — Access the early warning system."""
        return self._warning_system

    # ═══════════════════════════════════════════════════════════════════════
    # الواجهة الرئيسية — Main Interface
    # ═══════════════════════════════════════════════════════════════════════

    def track(
        self,
        action: str,
        intent: str,
        action_chain: list[str],
    ) -> dict:
        """
        تتبع إجراء في سياق النية — Track one action in context of intent.

        يحلل الإجراء الحالي في سياق النية الأصلية وسلسلة الإجراءات
        ويُرجع نتيجة شاملة تتضمن نقاط الانحراف والمستوى والتحذيرات.

        Args:
            action: الإجراء الحالي — current action description
            intent: النية الأصلية — original intent
            action_chain: سلسلة الإجراءات — action chain so far

        Returns:
            dict — نتيجة انحراف النية (IntentDriftResult.to_dict())
        """
        start_time = time.time()

        # إذا كان الكاشف معطلاً، أرجع نتيجة فارغة — return empty if disabled
        if not self._enabled:
            result = IntentDriftResult(
                details={"disabled": True},
                warnings=["كاشف الانحراف معطل — Intent drift detector is disabled"],
            )
            return result.to_dict()

        # التحقق من المدخلات — validate inputs
        if not intent or not intent.strip():
            result = IntentDriftResult(
                details={"error": "no_intent"},
                warnings=["لم يتم تحديد نية — No intent specified"],
            )
            return result.to_dict()

        if not action or not action.strip():
            result = IntentDriftResult(
                details={"error": "no_action"},
                warnings=["لم يتم تحديد إجراء — No action specified"],
            )
            return result.to_dict()

        # ═══════════════════════════════════════════════════════════
        # المرحلة 1: تحديث متتبع النية — Phase 1: Update intent tracker
        # ═══════════════════════════════════════════════════════════
        if not self._current_intent or self._current_intent != intent:
            # نية جديدة أو مُحدّثة — new or updated intent
            self._current_intent = intent
            self._tracker.set_intent(intent)
            self._action_history.clear()
            self._matched_count = 0
            self._tangential_count = 0
            self._warning_system.reset()

        # تحديث سلسلة الإجراءات — update action chain
        self._action_history = list(action_chain)
        if action not in self._action_history:
            self._action_history.append(action)

        # تسجيل الإجراء — record action
        matched_goal = self._tracker.record_action(action)

        if matched_goal is not None:
            self._matched_count += 1
        else:
            self._tangential_count += 1

        # ═══════════════════════════════════════════════════════════
        # المرحلة 2: حساب نقاط الانحراف — Phase 2: Compute drift score
        # ═══════════════════════════════════════════════════════════
        goal_progress = self._tracker._compute_goal_progress(
            self._tracker.goal_tree
        ) if self._tracker.goal_tree else 0.0

        drift_details = self._compute_drift_score(
            original_intent=intent,
            current_state=action,
            action_chain=self._action_history,
        )

        drift_score = drift_details.get("total", 0.0)

        # ═══════════════════════════════════════════════════════════
        # المرحلة 3: التحليل المتقدم — Phase 3: Advanced analysis
        # ═══════════════════════════════════════════════════════════
        # كشف اختطاف الهدف — detect goal hijacking
        is_hijacked = self._detect_goal_hijacking(intent, action)

        # كشف توسع النطاق — detect scope creep
        scope_creep = self._detect_scope_creep(intent, self._action_history)

        # فحص توافق الإجراء — check action alignment
        alignment = self._check_action_alignment(action, intent)

        # التنبؤ بالمسار — predict trajectory
        self._warning_system.record_drift(drift_score)
        trajectory = self._predict_trajectory(self._action_history, intent)

        # ═══════════════════════════════════════════════════════════
        # المرحلة 4: تحديد المستوى والتحذيرات — Phase 4: Classify & warn
        # ═══════════════════════════════════════════════════════════
        drift_level = DriftScorer.classify_drift(drift_score)
        is_drifting = drift_score >= self._warning_threshold

        warning_result = self._warning_system.check_warning(drift_score)

        # تجميع التحذيرات — compile warnings
        warnings: list[str] = list(warning_result.get("recommended_actions", []))

        if is_hijacked:
            warnings.insert(
                0,
                "تحذير: اكتشاف اختطاف محتمل للهدف — "
                "Warning: potential goal hijacking detected"
            )

        if scope_creep.has_creep:
            warnings.append(
                f"تحذير: توسع في النطاق بنسبة {scope_creep.creep_ratio:.0%} — "
                f"Warning: scope creep at {scope_creep.creep_ratio:.0%}"
            )

        if alignment < 0.2:
            warnings.append(
                f"تنبيه: توافق منخفض للإجراء ({alignment:.0%}) — "
                f"Alert: low action alignment ({alignment:.0%})"
            )

        # ═══════════════════════════════════════════════════════════
        # المرحلة 5: بناء النتيجة — Phase 5: Build result
        # ═══════════════════════════════════════════════════════════
        result = IntentDriftResult(
            drift_score=drift_score,
            drift_level=drift_level.value,
            is_drifting=is_drifting,
            details={
                "semantic_distance": drift_details.get("semantic_distance", 0.0),
                "coverage_deficit": drift_details.get("coverage_deficit", 0.0),
                "efficiency_loss": drift_details.get("efficiency_loss", 0.0),
                "step_deviation": drift_details.get("step_deviation", 0.0),
                "goal_progress": round(goal_progress, 4),
                "action_alignment": round(alignment, 4),
                "goal_hijacked": is_hijacked,
                "scope_creep": scope_creep.to_dict(),
                "trajectory": trajectory.to_dict(),
                "warning_level": warning_result.get("warning_level", "none"),
                "warning_confidence": warning_result.get("confidence", 0.0),
                "matched_actions": self._matched_count,
                "tangential_actions": self._tangential_count,
                "total_actions": len(self._action_history),
                "duration_ms": round((time.time() - start_time) * 1000, 1),
            },
            warnings=warnings,
        )

        # تحديث الإحصائيات — update statistics
        self._total_tracks += 1
        if is_drifting:
            self._drift_detected_count += 1
        if drift_level == DriftLevel.CRITICAL:
            self._critical_count += 1
        if warnings:
            self._corrections_suggested += len(warnings)

        # حفظ النتيجة — store result
        self._drift_results.append(result)
        if len(self._drift_results) > MAX_DRIFT_HISTORY:
            self._drift_results = self._drift_results[-MAX_DRIFT_HISTORY:]

        logger.debug(
            "تتبع الانحراف: نقاط=%.3f مستوى=%s توافق=%.3f — "
            "Drift tracked: score=%.3f level=%s alignment=%.3f",
            drift_score, drift_level.value, alignment,
            drift_score, drift_level.value, alignment,
        )

        return result.to_dict()

    # ═══════════════════════════════════════════════════════════════════════
    # دوال الحساب الداخلية — Internal Computation Methods
    # ═══════════════════════════════════════════════════════════════════════

    def _compute_drift_score(
        self,
        original_intent: str,
        current_state: str,
        action_chain: list[str],
    ) -> dict:
        """
        حساب نقاط الانحراف — Compute overall drift score.

        0.0 = لا انحراف، 1.0 = انحراف كامل.
        يجمع بين أربعة عوامل مرجحة.

        Args:
            original_intent: النية الأصلية — original intent
            current_state: الحالة/الإجراء الحالي — current state/action
            action_chain: سلسلة الإجراءات — action chain

        Returns:
            dict — نقاط الانحراف الكلية والتفصيلية
        """
        goal_progress = 0.0
        if self._tracker.goal_tree:
            goal_progress = self._tracker._compute_goal_progress(
                self._tracker.goal_tree
            )

        return self._scorer.compute_drift(
            original_intent=original_intent,
            current_state=current_state,
            action_chain=action_chain,
            goal_progress=goal_progress,
            matched_action_count=self._matched_count,
        )

    def _detect_goal_hijacking(
        self, original_intent: str, current_action: str
    ) -> bool:
        """
        كشف اختطاف الهدف — Detect if the goal has been replaced.

        يكشف ما إذا كان الإجراء الحالي يشير إلى هدف مختلف تماماً
        عن النية الأصلية باستخدام:
        1. أنماط اختطاف الهدف اللغوية
        2. المسافة الدلالية العالية
        3. عدم وجود كلمات مفتاحية مشتركة

        Args:
            original_intent: النية الأصلية — original intent
            current_action: الإجراء الحالي — current action

        Returns:
            bool — هل تم اختطاف الهدف؟
        """
        if not original_intent or not current_action:
            return False

        # فحص أنماط الاختراق اللغوية — check linguistic hijack patterns
        action_lower = current_action.lower()
        for pattern in GOAL_HIJACK_PATTERNS:
            if re.search(pattern, action_lower):
                logger.warning(
                    "اكتشاف نمط اختطاف هدف في الإجراء: %s — "
                    "Goal hijack pattern detected in action: %s",
                    current_action[:50], current_action[:50],
                )
                return True

        # فحص المسافة الدلالية — check semantic distance
        distance = DriftScorer._compute_semantic_distance(
            original_intent, current_action
        )

        # إذا كانت المسافة عالية جداً مع عدم وجود تطابق — if very high distance
        if distance > 0.9:
            # تحقق إضافي: هل الإجراء يتضمن هدف جديد؟
            # additional check: does action contain a new goal?
            intent_keywords = IntentTracker._extract_keywords(original_intent)
            action_keywords = IntentTracker._extract_keywords(current_action)

            overlap = intent_keywords & action_keywords
            if not overlap:
                logger.warning(
                    "اكتشاف اختطاف هدف محتمل: لا تطابق دلالي — "
                    "Potential goal hijacking: no semantic overlap"
                )
                return True

        return False

    def _detect_scope_creep(
        self, original_intent: str, action_chain: list[str]
    ) -> ScopeCreepResult:
        """
        كشف توسع النطاق — Detect if the task is expanding beyond scope.

        يكشف ما إذا كانت سلسلة الإجراءات تتوسع تدريجياً خارج
        نطاق النية الأصلية من خلال تحليل الكلمات المفتاحية الجديدة.

        Args:
            original_intent: النية الأصلية — original intent
            action_chain: سلسلة الإجراءات — action chain

        Returns:
            ScopeCreepResult — نتيجة كشف توسع النطاق
        """
        if not original_intent or not action_chain:
            return ScopeCreepResult()

        # استخراج كلمات النية المفتاحية — extract intent keywords
        intent_keywords = IntentTracker._extract_keywords(original_intent)

        if not intent_keywords:
            return ScopeCreepResult()

        # تتبع الكلمات المفتاحية الجديدة — track new keywords
        all_action_keywords: set[str] = set()
        expanded_areas: list[str] = []

        for action in action_chain:
            action_keywords = IntentTracker._extract_keywords(action)

            # الكلمات الجديدة التي ليست في النية الأصلية
            # new words not in original intent
            new_keywords = action_keywords - intent_keywords - all_action_keywords

            if new_keywords:
                # بعض الكلمات الجديدة طبيعية (أدوات ربط، إلخ)
                # some new words are natural (connectors, etc.)
                significant_new = set()
                for kw in new_keywords:
                    if len(kw) >= 4 and kw not in STOP_WORDS:
                        significant_new.add(kw)

                if significant_new:
                    expanded_areas.extend(significant_new)

            all_action_keywords.update(action_keywords)

        # حساب نسبة التوسع — compute creep ratio
        if not all_action_keywords:
            return ScopeCreepResult()

        out_of_scope = all_action_keywords - intent_keywords
        total_keywords = all_action_keywords | intent_keywords

        if not total_keywords:
            creep_ratio = 0.0
        else:
            creep_ratio = len(out_of_scope) / len(total_keywords)

        # هل يوجد توسع حقيقي؟ — is there real creep?
        has_creep = creep_ratio > 0.4 and len(expanded_areas) >= 3

        return ScopeCreepResult(
            has_creep=has_creep,
            creep_ratio=creep_ratio,
            expanded_areas=expanded_areas[:20],  # حد العرض — display limit
        )

    def _check_action_alignment(self, action: str, intent: str) -> float:
        """
        فحص توافق الإجراء مع النية — Check how aligned action is with intent.

        يحسب درجة توافق الإجراء مع النية الأصلية (0 = غير متوافق، 1 = متوافق تماماً).
        يستخدم تشابه Jaccard مع تعزيز للكلمات المفتاحية الرئيسية.

        Args:
            action: وصف الإجراء — action description
            intent: النية — intent text

        Returns:
            float — درجة التوافق (0.0 - 1.0)
        """
        if not action or not intent:
            return 0.0

        action_keywords = IntentTracker._extract_keywords(action)
        intent_keywords = IntentTracker._extract_keywords(intent)

        if not action_keywords and not intent_keywords:
            return 1.0
        if not action_keywords or not intent_keywords:
            return 0.0

        # تشابه Jaccard — Jaccard similarity
        intersection = action_keywords & intent_keywords
        union = action_keywords | intent_keywords

        if not union:
            return 0.0

        base_similarity = len(intersection) / len(union)

        # تعزيز إذا تطابقت كلمات فعلية مهمة — boost for key verb match
        action_verbs = self._extract_verbs(action)
        intent_verbs = self._extract_verbs(intent)

        verb_overlap = action_verbs & intent_verbs
        if verb_overlap:
            verb_boost = len(verb_overlap) * 0.1
            base_similarity = min(1.0, base_similarity + verb_boost)

        return max(0.0, min(1.0, base_similarity))

    def _predict_trajectory(
        self, action_chain: list[str], intent: str
    ) -> TrajectoryPrediction:
        """
        التنبؤ بمسار الانحراف — Predict where the action chain is heading.

        يتنبأ بالاتجاه المستقبلي للانحراف بناءً على سجل نقاط
        الانحراف وتحليل اتجاه سلسلة الإجراءات.

        Args:
            action_chain: سلسلة الإجراءات — action chain
            intent: النية الأصلية — original intent

        Returns:
            TrajectoryPrediction — تنبؤ المسار
        """
        # استخدام نظام التحذير المبكر للتنبؤ — use EWS for prediction
        trajectory = self._warning_system.predict_trajectory()

        # تعزيز التنبؤ بتحليل سلسلة الإجراءات — enhance with chain analysis
        if len(action_chain) >= MIN_ACTIONS_FOR_TRAJECTORY:
            # فحص اتجاه التوافق — check alignment trend
            recent_actions = action_chain[-TRAJECTORY_WINDOW:]
            alignments: list[float] = []

            for act in recent_actions:
                alignment = self._check_action_alignment(act, intent)
                alignments.append(alignment)

            if len(alignments) >= 2:
                # اتجاه التوافق: هل يتناقص؟ — alignment trend: is it decreasing?
                mid = len(alignments) // 2
                first_half_avg = sum(alignments[:mid]) / max(1, mid)
                second_half_avg = sum(alignments[mid:]) / max(1, len(alignments) - mid)

                alignment_decline = first_half_avg - second_half_avg

                # تعديل التنبؤ — adjust prediction
                if alignment_decline > 0:
                    # التوافق يتناقص → الانحراف يزداد
                    # alignment decreasing → drift increasing
                    adjusted_drift = min(
                        1.0,
                        trajectory.predicted_drift + alignment_decline * 0.5
                    )
                    trajectory = TrajectoryPrediction(
                        predicted_drift=adjusted_drift,
                        confidence=trajectory.confidence,
                        time_to_threshold=trajectory.time_to_threshold,
                    )

        return trajectory

    # ═══════════════════════════════════════════════════════════════════════
    # التقارير والإحصائيات — Reports & Statistics
    # ═══════════════════════════════════════════════════════════════════════

    def report(self) -> dict:
        """
        تقرير الانحراف الشامل — Full drift analysis report.

        يُرجع تقريراً شاملاً يتضمن:
        - نقاط الانحراف الحالية
        - مستوى الانحراف
        - تقدم الهدف
        - التحذيرات النشطة
        - التصحيحات الموصى بها
        - تنبؤ المسار

        Returns:
            dict — تقرير الانحراف (DriftReport.to_dict())
        """
        # حساب نقاط الانحراف الحالية — compute current drift score
        drift_details = self._compute_drift_score(
            original_intent=self._current_intent,
            current_state=self._action_history[-1] if self._action_history else "",
            action_chain=self._action_history,
        )

        drift_score = drift_details.get("total", 0.0)
        drift_level = DriftScorer.classify_drift(drift_score)

        # حساب تقدم الهدف — compute goal progress
        goal_progress = 0.0
        if self._tracker.goal_tree:
            goal_progress = self._tracker._compute_goal_progress(
                self._tracker.goal_tree
            )

        # تجميع التحذيرات — compile warnings
        warnings: list[str] = []
        recommended_corrections: list[str] = []

        if self._current_intent:
            # فحص توسع النطاق — check scope creep
            scope_creep = self._detect_scope_creep(
                self._current_intent, self._action_history
            )
            if scope_creep.has_creep:
                warnings.append(
                    f"توسع النطاق: {scope_creep.creep_ratio:.0%} — "
                    f"Scope creep: {scope_creep.creep_ratio:.0%}"
                )

        # تحذيرات نظام التحذير المبكر — EWS warnings
        warning_result = self._warning_system.check_warning(drift_score)
        warnings.extend(warning_result.get("recommended_actions", []))

        # التنبؤ بالمسار — trajectory prediction
        trajectory = self._warning_system.predict_trajectory()

        # التصحيحات الموصى بها — recommended corrections
        if drift_score >= self._drift_threshold:
            recommended_corrections.append(
                "أعد تقييم الهدف الأصلي وحدد نقطة الانحراف — "
                "Reassess original goal and identify drift point"
            )
            recommended_corrections.append(
                "قصر الإجراءات القادمة على النية الأصلية — "
                "Restrict upcoming actions to original intent"
            )
        elif drift_score >= self._warning_threshold:
            recommended_corrections.append(
                "راجع الإجراءات الأخيرة — Review recent actions"
            )
            recommended_corrections.append(
                "تأكد من توافق الخطوة التالية مع الهدف — "
                "Ensure next step aligns with goal"
            )

        if trajectory.time_to_threshold is not None:
            recommended_corrections.append(
                f"الانحراف سيتجاوز العتبة خلال ~{trajectory.time_to_threshold} خطوة — "
                f"Drift will exceed threshold in ~{trajectory.time_to_threshold} steps"
            )

        report_obj = DriftReport(
            drift_score=drift_score,
            drift_level=drift_level.value,
            goal_progress=goal_progress,
            warnings=warnings,
            recommended_corrections=recommended_corrections,
        )

        return report_obj.to_dict()

    def get_stats(self) -> dict:
        """
        إحصائيات الاستخدام — Usage statistics.

        يُرجع إحصائيات استخدام كاشف الانحراف:

        Returns:
            dict — إحصائيات الاستخدام
        """
        # حساب نسبة الانحراف — compute drift ratio
        drift_ratio = (
            self._drift_detected_count / self._total_tracks
            if self._total_tracks > 0
            else 0.0
        )

        # متوسط نقاط الانحراف — average drift score
        avg_drift = 0.0
        if self._drift_results:
            avg_drift = sum(r.drift_score for r in self._drift_results) / len(
                self._drift_results
            )

        # نقاط الانحراف الأخيرة — recent drift scores
        recent_scores = [r.drift_score for r in self._drift_results[-10:]]

        # تقدم الهدف — goal progress
        goal_progress = 0.0
        if self._tracker.goal_tree:
            goal_progress = self._tracker._compute_goal_progress(
                self._tracker.goal_tree
            )

        return {
            "enabled": self._enabled,
            "total_tracks": self._total_tracks,
            "drift_detected_count": self._drift_detected_count,
            "critical_count": self._critical_count,
            "corrections_suggested": self._corrections_suggested,
            "drift_ratio": round(drift_ratio, 4),
            "average_drift_score": round(avg_drift, 4),
            "recent_drift_scores": [round(s, 4) for s in recent_scores],
            "current_intent": self._current_intent,
            "action_count": len(self._action_history),
            "matched_action_count": self._matched_count,
            "tangential_action_count": self._tangential_count,
            "goal_progress": round(goal_progress, 4),
            "drift_threshold": self._drift_threshold,
            "warning_threshold": self._warning_threshold,
        }

    # ═══════════════════════════════════════════════════════════════════════
    # دوال مساعدة — Utility Methods
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _extract_verbs(text: str) -> set[str]:
        """
        استخراج الأفعال — Extract verb-like words from text.

        يحدد الكلمات التي تبدو كأفعال (تبدأ بياء أو تاء في العربية،
        أو كلمات فعلية شائعة في الإنجليزية).
        """
        if not text:
            return set()

        verbs: set[str] = set()

        # أفعال عربية شائعة — common Arabic verbs
        arabic_verb_patterns = [
            r"\b(ي\w{2,})\b",     # يفعل — present tense
            r"\b(ت\w{2,})\b",     # تفعل — present tense feminine
        ]

        # أفعال إنجليزية شائعة — common English verbs
        english_verbs = {
            "read", "write", "execute", "run", "send", "receive",
            "create", "delete", "update", "modify", "analyze",
            "process", "transform", "generate", "build", "deploy",
            "test", "verify", "check", "validate", "compile",
            "install", "configure", "monitor", "track", "detect",
            "extract", "parse", "format", "convert", "search",
            "filter", "sort", "merge", "split", "combine",
            "download", "upload", "fetch", "store", "cache",
        }

        # استخراج الأفعال العربية — extract Arabic verbs
        for pattern in arabic_verb_patterns:
            matches = re.findall(pattern, text)
            verbs.update(m.lower() for m in matches if len(m) >= 3)

        # استخراج الأفعال الإنجليزية — extract English verbs
        words = set(re.findall(r"\b\w+\b", text.lower()))
        verbs.update(words & english_verbs)

        return verbs

    def reset(self) -> None:
        """
        إعادة تعيين الكاشف — Reset the detector state.

        يمسح جميع السجلات والنتائج والإحصائيات ويعيد التهيئة.
        """
        self._current_intent = ""
        self._action_history.clear()
        self._matched_count = 0
        self._tangential_count = 0
        self._drift_results.clear()
        self._warning_system.reset()

        # إعادة إنشاء المتتبع — recreate tracker
        self._tracker = IntentTracker()

        # إعادة تعيين الإحصائيات — reset statistics
        self._total_tracks = 0
        self._drift_detected_count = 0
        self._critical_count = 0
        self._corrections_suggested = 0

        logger.info("تم إعادة تعيين كاشف الانحراف — IntentDriftDetector reset")
