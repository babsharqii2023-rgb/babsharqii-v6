"""
BABSHARQII v40.0 — Team Model
نموذج الفريق — بناء نموذج معرفي لكل عضو في الفريق البشري

Builds a cognitive model for each team member (skills, preferences, workload,
trust levels) and designs work distribution plans accordingly.

Inspired by Human-Agent Collaboration and Team Science research:
  • Skill matching: optimal assignment based on competencies (Campion et al. 1993)
  • Workload balancing: prevent burnout and underutilization (Siegel et al. 2019)
  • Trust model: dynamic trust adjustment based on task outcomes (Lee & See 2004)
  • Preference learning: adapt to member preferences from feedback history

Architecture:
  ┌────────────────────────────────────────────────────────────────────┐
  │                         TeamModel                                  │
  │                                                                    │
  │  ┌────────────────────┐  ┌──────────────────────────────────────┐ │
  │  │ MemberProfileStore │  │ SkillMatcher                         │ │
  │  │ (cognitive model   │  │ (skill overlap scoring, gap           │ │
  │  │  per member)       │  │  identification, alternatives)       │ │
  │  └────────┬───────────┘  └──────────────┬───────────────────────┘ │
  │           │                             │                          │
  │  ┌────────▼─────────────────────────────▼──────────────────────┐ │
  │  │               WorkloadBalancer                               │ │
  │  │  (current load tracking, capacity estimation,               │ │
  │  │   rebalancing suggestions)                                   │ │
  │  └──────────────────────────┬──────────────────────────────────┘ │
  │                             │                                      │
  │  ┌──────────────────────────▼──────────────────────────────────┐ │
  │  │          TrustModel & PreferenceLearner                     │ │
  │  │  (dynamic trust adjustment, preference extraction           │ │
  │  │   from feedback, improvement suggestions)                   │ │
  │  └────────────────────────────────────────────────────────────┘ │
  └────────────────────────────────────────────────────────────────────┘

Env toggles:
    MAMOUN_HUMAN_COLLABORATION   — تمكين/تعطيل التعاون البشري (الافتراضي: false)
"""

from __future__ import annotations

import os
import time
import uuid
import math
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum
from collections import defaultdict

from mamoun.human import HUMAN_COLLABORATION_ENABLED

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  التعدادات — Enumerations
# ═══════════════════════════════════════════════════════════════════════════════


class MemberAvailability(str, Enum):
    """حالة توفر العضو — Member availability status."""
    AVAILABLE = "available"      # متاح
    BUSY = "busy"                # مشغول
    UNAVAILABLE = "unavailable"  # غير متاح


class ImprovementCategory(str, Enum):
    """فئة التحسين — Improvement category."""
    TRAINING = "training"              # تدريب
    HIRING = "hiring"                  # توظيف
    REBALANCING = "rebalancing"        # إعادة توازن
    PROCESS = "process"                # تحسين العملية
    TOOLING = "tooling"                # أدوات
    COMMUNICATION = "communication"    # تواصل


class ImprovementPriority(str, Enum):
    """أولوية التحسين — Improvement priority."""
    CRITICAL = "critical"    # حرج
    HIGH = "high"            # عالي
    MEDIUM = "medium"        # متوسط
    LOW = "low"              # منخفض


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج البيانات — Dataclasses
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class TeamMember:
    """
    عضو في الفريق — A human team member with a cognitive profile.
    """
    member_id: str = ""
    name: str = ""
    name_ar: str = ""
    role: str = ""
    skills: list[str] = field(default_factory=list)             # قائمة المهارات
    skill_levels: dict[str, float] = field(default_factory=dict) # مهارة → مستوى (0-1)
    preferences: dict = field(default_factory=dict)              # تفضيلات مستفادة
    current_workload: float = 0.0                                # عبء حالي (0-1)
    trust_level: float = 0.5                                     # مستوى الثقة (0-1)
    avg_response_time_hours: float = 24.0                        # متوسط وقت الاستجابة
    quality_score: float = 0.5                                   # درجة الجودة (0-1)
    completed_tasks: int = 0                                     # مهام مكتملة
    failed_tasks: int = 0                                        # مهام فاشلة
    availability: str = MemberAvailability.AVAILABLE.value       # حالة التوفر
    communication_channels: list[str] = field(default_factory=list)  # قنوات التواصل

    def __post_init__(self):
        if not self.member_id:
            self.member_id = f"member_{uuid.uuid4().hex[:8]}"
        # ضبط القيم — Clamp values
        self.current_workload = max(0.0, min(1.0, self.current_workload))
        self.trust_level = max(0.0, min(1.0, self.trust_level))
        self.quality_score = max(0.0, min(1.0, self.quality_score))

    @property
    def success_rate(self) -> float:
        """معدل النجاح — Task success rate."""
        total = self.completed_tasks + self.failed_tasks
        return self.completed_tasks / total if total > 0 else 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AssignmentRecommendation:
    """
    توصية التعيين — Recommendation for the best team member for a task.
    """
    recommended_member_id: str = ""
    match_score: float = 0.0                        # درجة التطابق (0-1)
    skill_gaps: list[str] = field(default_factory=list)   # مهارات مفقودة
    workload_after_assignment: float = 0.0           # العبء بعد التعيين
    alternative_members: list[dict] = field(default_factory=list)  # بدائل
    reasoning: str = ""                              # سبب التوصية

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TeamOverview:
    """
    نظرة عامة على الفريق — Overview of the entire team's state.
    """
    total_members: int = 0
    available_members: int = 0
    avg_workload: float = 0.0
    avg_trust: float = 0.0
    avg_quality: float = 0.0
    skill_coverage: dict = field(default_factory=dict)   # skill → count of members
    bottlenecks: list[str] = field(default_factory=list)  # مهارات نادرة

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ImprovementSuggestion:
    """
    اقتراح تحسين — A suggestion for improving team performance.
    """
    category: str = ImprovementCategory.TRAINING.value
    description: str = ""
    description_ar: str = ""
    impact: float = 0.5              # التأثير المتوقع (0-1)
    effort: float = 0.5              # الجهد المطلوب (0-1)
    priority: str = ImprovementPriority.MEDIUM.value

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
#  نموذج الفريق — TeamModel
# ═══════════════════════════════════════════════════════════════════════════════


class TeamModel:
    """
    نموذج الفريق — المحرك الرئيسي لنمذجة أعضاء الفريق البشري.

    Builds a cognitive model for each team member (skills, preferences,
    workload, trust levels) and designs work distribution plans accordingly.

    Features:
    - Member profiles with skills, preferences, workload, trust, quality
    - Skill matching: find the best member for a task based on skills and availability
    - Workload balancing: distribute tasks to avoid overload
    - Trust model: track trust level based on task completion quality
    - Preference learning: learn member preferences from feedback
    - Team performance analytics and improvement suggestions

    Usage:
        model = TeamModel()
        member_id = model.add_member(TeamMember(
            name="Ahmad",
            name_ar="أحمد",
            skills=["python", "design", "arabic_nlp"],
        ))
        rec = model.find_best_assignee(["python", "nlp"], priority="high")
        print(rec.recommended_member_id, rec.match_score)
    """

    # ثوابت — Constants
    TRUST_UPDATE_RATE = 0.15           # معدل تحديث الثقة
    WORKLOAD_INCREMENT = 0.1           # زيادة العبء لكل مهمة
    WORKLOAD_DECAY_PER_HOUR = 0.02     # تناقص العبء بالساعة
    MIN_TRUST_THRESHOLD = 0.1          # الحد الأدنى للثقة
    MAX_WORKLOAD_THRESHOLD = 0.85      # الحد الأقصى للعبء قبل الرفض
    SKILL_MATCH_WEIGHT = 0.5           # وزن تطابق المهارات
    WORKLOAD_WEIGHT = 0.3              # وزن العبء
    TRUST_WEIGHT = 0.2                 # وزن الثقة

    def __init__(self):
        """
        تهيئة نموذج الفريق — Initialize the Team Model.
        """
        self._members: dict[str, TeamMember] = {}
        self._task_history: dict[str, list[dict]] = defaultdict(list)  # member_id → [{outcome}]
        self._preference_store: dict[str, dict] = {}  # member_id → {skill: preference_score}
        self._stats = {
            "members_added": 0,
            "assignments_recommended": 0,
            "trust_updates": 0,
            "outcomes_recorded": 0,
        }

        if HUMAN_COLLABORATION_ENABLED:
            logger.info(
                "تم تفعيل نموذج الفريق — Team Model enabled"
            )

    # ─── إدارة الأعضاء — Member Management ─────────────────────────────────

    def add_member(self, member: TeamMember) -> str:
        """
        إضافة عضو — Add a new team member.

        Args:
            member: بيانات العضو — member details

        Returns:
            member_id — معرف العضو الجديد
        """
        if not HUMAN_COLLABORATION_ENABLED:
            logger.warning("التعاون البشري غير مفعّل — Human collaboration disabled")
            return member.member_id

        if member.member_id in self._members:
            logger.warning("عضو موجود بالفعل — Member already exists: %s", member.member_id)
            return member.member_id

        self._members[member.member_id] = member
        self._preference_store[member.member_id] = {}
        self._stats["members_added"] += 1

        # تهيئة مستويات المهارات — Initialize skill levels
        for skill in member.skills:
            if skill not in member.skill_levels:
                member.skill_levels[skill] = 0.6  # مستوى افتراضي — default level

        logger.info(
            "تم إضافة العضو %s (%s) — Member added: %s (%s)",
            member.member_id, member.name_ar or member.name,
            member.member_id, member.name,
        )
        return member.member_id

    def update_member(self, member_id: str, updates: dict) -> bool:
        """
        تحديث بيانات عضو — Update a team member's profile.

        Args:
            member_id: معرف العضو — member identifier
            updates: القيم المحدثة — fields to update

        Returns:
            True if the update succeeded, False otherwise
        """
        if member_id not in self._members:
            logger.warning("عضو غير موجود — Member not found: %s", member_id)
            return False

        member = self._members[member_id]

        for key, value in updates.items():
            if hasattr(member, key):
                # معالجة خاصة للقيم المقيدة — Special handling for bounded values
                if key == "current_workload":
                    value = max(0.0, min(1.0, float(value)))
                elif key in ("trust_level", "quality_score"):
                    value = max(0.0, min(1.0, float(value)))
                setattr(member, key, value)
            else:
                logger.debug(
                    "حقل غير معروف '%s' — Unknown field '%s'",
                    key, key,
                )

        logger.info(
            "تم تحديث بيانات العضو %s — Member updated: %s",
            member_id, member_id,
        )
        return True

    def get_member_profile(self, member_id: str) -> Optional[TeamMember]:
        """
        الحصول على ملف العضو — Get a team member's profile.

        Args:
            member_id: معرف العضو — member identifier

        Returns:
            TeamMember or None if not found
        """
        return self._members.get(member_id)

    # ─── مطابقة المهارات — Skill Matching ───────────────────────────────────

    def find_best_assignee(
        self,
        task_skills: list[str],
        priority: str = "medium",
    ) -> AssignmentRecommendation:
        """
        البحث عن أفضل عضو — Find the best team member for a task.

        Scores each available member based on:
        1. Skill match (50%): overlap between task skills and member skills
        2. Workload fit (30%): members with lower workload score higher
        3. Trust level (20%): more trusted members score higher

        For critical/high priority tasks, trust is weighted more heavily.

        Args:
            task_skills: المهارات المطلوبة — required skills for the task
            priority: أولوية المهمة — task priority (critical/high/medium/low)

        Returns:
            AssignmentRecommendation with the best match and alternatives
        """
        if not HUMAN_COLLABORATION_ENABLED:
            return AssignmentRecommendation(
                reasoning="التعاون البشري غير مفعّل — Human collaboration disabled",
            )

        self._stats["assignments_recommended"] += 1

        if not self._members:
            return AssignmentRecommendation(
                reasoning="لا يوجد أعضاء في الفريق — No team members available",
            )

        # تعديل الأوزان حسب الأولوية — Adjust weights by priority
        skill_weight = self.SKILL_MATCH_WEIGHT
        workload_weight = self.WORKLOAD_WEIGHT
        trust_weight = self.TRUST_WEIGHT

        if priority in ("critical", "high"):
            # المهام الحرجة تحتاج ثقة أعلى — Critical tasks need higher trust
            trust_weight = 0.4
            skill_weight = 0.4
            workload_weight = 0.2

        # تقييم كل عضو — Score each member
        scored_members: list[dict] = []
        for member_id, member in self._members.items():
            # تخطي الأعضاء غير المتاحين — Skip unavailable members
            if member.availability == MemberAvailability.UNAVAILABLE.value:
                continue

            # 1. درجة تطابق المهارات — Skill match score
            skill_score = self._compute_skill_match(member, task_skills)
            skill_gaps = [s for s in task_skills if s not in member.skills]

            # 2. درجة العبء — Workload score (lower workload = higher score)
            workload_score = 1.0 - member.current_workload

            # 3. درجة الثقة — Trust score
            trust_score = member.trust_level

            # الدرجة الإجمالية — Composite score
            composite = (
                skill_weight * skill_score
                + workload_weight * workload_score
                + trust_weight * trust_score
            )

            # تخفيض إذا كان العبء مرتفعاً جداً — Penalize if overloaded
            if member.current_workload >= self.MAX_WORKLOAD_THRESHOLD:
                composite *= 0.3  # تخفيض كبير — heavy penalty

            # تخفيض إذا كان العضو مشغولاً — Penalize busy status
            if member.availability == MemberAvailability.BUSY.value:
                composite *= 0.5

            scored_members.append({
                "member_id": member_id,
                "name": member.name,
                "name_ar": member.name_ar,
                "composite_score": composite,
                "skill_score": skill_score,
                "workload_score": workload_score,
                "trust_score": trust_score,
                "skill_gaps": skill_gaps,
                "current_workload": member.current_workload,
                "workload_after": min(1.0, member.current_workload + self.WORKLOAD_INCREMENT),
            })

        if not scored_members:
            return AssignmentRecommendation(
                reasoning="لا يوجد أعضاء متاحون — No available members",
            )

        # ترتيب حسب الدرجة — Sort by score
        scored_members.sort(key=lambda x: x["composite_score"], reverse=True)

        best = scored_members[0]
        alternatives = [
            {
                "member_id": m["member_id"],
                "name": m["name"],
                "name_ar": m["name_ar"],
                "score": round(m["composite_score"], 4),
            }
            for m in scored_members[1:4]  # أفضل 3 بدائل — top 3 alternatives
        ]

        # صياغة السبب — Compose reasoning
        reasoning_parts = []
        if best["skill_score"] >= 0.8:
            reasoning_parts.append("تطابق مهارات عالي — high skill match")
        elif best["skill_score"] >= 0.5:
            reasoning_parts.append("تطابق مهارات جزئي — partial skill match")
        else:
            reasoning_parts.append("تطابق مهارات منخفض — low skill match")

        if best["workload_score"] >= 0.7:
            reasoning_parts.append("عبء منخفض — low workload")
        elif best["workload_score"] >= 0.3:
            reasoning_parts.append("عبء متوسط — moderate workload")
        else:
            reasoning_parts.append("عبء مرتفع — high workload")

        if best["trust_score"] >= 0.7:
            reasoning_parts.append("ثقة عالية — high trust")

        reasoning = "؛ ".join(reasoning_parts)

        return AssignmentRecommendation(
            recommended_member_id=best["member_id"],
            match_score=round(best["composite_score"], 4),
            skill_gaps=best["skill_gaps"],
            workload_after_assignment=round(best["workload_after"], 4),
            alternative_members=alternatives,
            reasoning=reasoning,
        )

    def _compute_skill_match(self, member: TeamMember, task_skills: list[str]) -> float:
        """
        حساب تطابق المهارات — Compute skill overlap between member and task.
        Weighted by skill levels: a member with expert-level skill scores higher
        than one with beginner-level.
        """
        if not task_skills:
            return 1.0  # لا مهارات مطلوبة — no skills required

        matched_score = 0.0
        total_weight = 0.0

        for skill in task_skills:
            skill_lower = skill.lower()
            weight = 1.0
            total_weight += weight

            # مطابقة تامة — Exact match
            if skill_lower in [s.lower() for s in member.skills]:
                level = member.skill_levels.get(skill, 0.6)
                matched_score += weight * level
            else:
                # مطابقة جزئية — Partial match (substring)
                partial_found = False
                for member_skill in member.skills:
                    if (skill_lower in member_skill.lower()
                            or member_skill.lower() in skill_lower):
                        level = member.skill_levels.get(member_skill, 0.4)
                        matched_score += weight * level * 0.5  # تخفيض للمطابقة الجزئية
                        partial_found = True
                        break
                # لا تطابق — No match adds 0

        return matched_score / total_weight if total_weight > 0 else 0.0

    # ─── نظرة عامة على الفريق — Team Overview ──────────────────────────────

    def get_team_overview(self) -> TeamOverview:
        """
        نظرة عامة على الفريق — Get an overview of the entire team's state.

        Returns:
            TeamOverview with aggregated metrics
        """
        if not self._members:
            return TeamOverview()

        members = list(self._members.values())
        total = len(members)
        available = sum(
            1 for m in members
            if m.availability == MemberAvailability.AVAILABLE.value
        )

        # المتوسطات — Averages
        avg_workload = sum(m.current_workload for m in members) / total
        avg_trust = sum(m.trust_level for m in members) / total
        avg_quality = sum(m.quality_score for m in members) / total

        # تغطية المهارات — Skill coverage
        skill_coverage: dict[str, int] = defaultdict(int)
        for member in members:
            for skill in member.skills:
                skill_coverage[skill] += 1

        # الاختناقات — Bottlenecks (skills held by only 1 member)
        bottlenecks = [
            skill for skill, count in skill_coverage.items()
            if count <= 1
        ]

        return TeamOverview(
            total_members=total,
            available_members=available,
            avg_workload=round(avg_workload, 4),
            avg_trust=round(avg_trust, 4),
            avg_quality=round(avg_quality, 4),
            skill_coverage=dict(skill_coverage),
            bottlenecks=bottlenecks,
        )

    # ─── نموذج الثقة — Trust Model ─────────────────────────────────────────

    def update_trust(self, member_id: str, delta: float) -> bool:
        """
        تحديث الثقة — Adjust a member's trust level.

        Positive delta increases trust (e.g., successful task completion).
        Negative delta decreases trust (e.g., missed deadline, poor quality).

        The adjustment is dampened by TRUST_UPDATE_RATE to prevent
        large swings from single events.

        Args:
            member_id: معرف العضو — member identifier
            delta: مقدار التغيير — adjustment amount (positive or negative)

        Returns:
            True if the update succeeded, False otherwise
        """
        if member_id not in self._members:
            logger.warning("عضو غير موجود — Member not found: %s", member_id)
            return False

        member = self._members[member_id]
        # تطبيق معدل التحديث — Apply dampening rate
        actual_delta = delta * self.TRUST_UPDATE_RATE
        old_trust = member.trust_level
        member.trust_level = max(
            self.MIN_TRUST_THRESHOLD,
            min(1.0, member.trust_level + actual_delta),
        )
        self._stats["trust_updates"] += 1

        logger.info(
            "تحديث ثقة العضو %s: %.3f → %.3f (delta=%.3f) — Trust update for %s: %.3f → %.3f",
            member_id, old_trust, member.trust_level, delta,
            member_id, old_trust, member.trust_level,
        )
        return True

    # ─── تسجيل نتائج المهام — Record Task Outcomes ─────────────────────────

    def record_task_outcome(self, member_id: str, task_id: str, outcome: dict) -> None:
        """
        تسجيل نتيجة مهمة — Record the outcome of a task for a member.

        Updates trust level, quality score, workload, and preferences
        based on the task outcome.

        Args:
            member_id: معرف العضو — member identifier
            task_id: معرف المهمة — task identifier
            outcome: النتيجة — dict with keys:
                - "status": completed/rejected (str)
                - "rating": تقييم الجودة 1-5 (int, optional)
                - "comments": ملاحظات (str, optional)
                - "suggestions": اقتراحات (str, optional)
                - "on_time": هل تم في الوقت؟ (bool, optional)
                - "skills_used": المهارات المستخدمة (list[str], optional)
        """
        if member_id not in self._members:
            logger.warning("عضو غير موجود — Member not found: %s", member_id)
            return

        member = self._members[member_id]
        self._task_history[member_id].append({
            "task_id": task_id,
            "outcome": outcome,
            "recorded_at": time.time(),
        })
        self._stats["outcomes_recorded"] += 1

        status = outcome.get("status", "")
        rating = outcome.get("rating", 3)
        on_time = outcome.get("on_time", True)
        skills_used = outcome.get("skills_used", [])

        # 1. تحديث الثقة — Update trust
        if status == "completed":
            # ثقة إيجابية للمهام المكتملة — Positive trust for completed tasks
            trust_delta = 0.1
            if rating >= 4:
                trust_delta = 0.3
            elif rating <= 2:
                trust_delta = -0.2  # مكتملة بجودة منخفضة — completed but low quality
            if not on_time:
                trust_delta *= 0.5  # تخفيض لتأخير التسليم — penalty for late delivery
            self.update_trust(member_id, trust_delta)
            member.completed_tasks += 1
        elif status == "rejected":
            # ثقة سلبية للمهام المرفوضة — Negative trust for rejected tasks
            self.update_trust(member_id, -0.3)
            member.failed_tasks += 1

        # 2. تحديث الجودة — Update quality score
        if rating > 0:
            quality_delta = (rating / 5.0 - member.quality_score) * 0.2
            member.quality_score = max(0.0, min(1.0, member.quality_score + quality_delta))

        # 3. تحديث العبء — Update workload
        member.current_workload = max(
            0.0, member.current_workload - self.WORKLOAD_INCREMENT
        )

        # 4. تعلم التفضيلات — Preference learning from feedback
        suggestions = outcome.get("suggestions", "")
        comments = outcome.get("comments", "")
        if suggestions or comments:
            self._learn_preferences(member_id, skills_used, rating, comments)

        # 5. تحديث مستويات المهارات — Update skill levels based on usage
        for skill in skills_used:
            if skill in member.skill_levels:
                # تحسين طفيف لاستخدام المهارة — Slight improvement for using skill
                current = member.skill_levels[skill]
                improvement = 0.02 if rating >= 3 else -0.01
                member.skill_levels[skill] = max(0.0, min(1.0, current + improvement))

        logger.info(
            "تم تسجيل نتيجة المهمة %s للعضو %s (حالة: %s، تقييم: %s) — Outcome recorded for task %s, member %s",
            task_id, member_id, status, rating, task_id, member_id,
        )

    # ─── تعلم التفضيلات — Preference Learning ──────────────────────────────

    def _learn_preferences(
        self,
        member_id: str,
        skills_used: list[str],
        rating: int,
        comments: str,
    ) -> None:
        """
        تعلم التفضيلات — Learn member preferences from feedback.

        If a member gives high ratings for tasks involving certain skills,
        we increase their preference score for those skills. Low ratings
        decrease preference.
        """
        if member_id not in self._preference_store:
            self._preference_store[member_id] = {}

        prefs = self._preference_store[member_id]
        preference_delta = 0.1 if rating >= 4 else (-0.1 if rating <= 2 else 0.0)

        for skill in skills_used:
            current = prefs.get(skill, 0.5)
            prefs[skill] = max(0.0, min(1.0, current + preference_delta))

        # تحليل التعليقات للكلمات المفتاحية — Analyze comments for keywords
        positive_keywords = ["أحب", "ممتاز", "رائع", "enjoy", "great", "love", "excellent"]
        negative_keywords = ["صعب", "ممل", "لا أحب", "difficult", "boring", "hate", "hard"]

        comment_lower = comments.lower()
        for skill in skills_used:
            if any(kw in comment_lower for kw in positive_keywords):
                current = prefs.get(skill, 0.5)
                prefs[skill] = min(1.0, current + 0.05)
            elif any(kw in comment_lower for kw in negative_keywords):
                current = prefs.get(skill, 0.5)
                prefs[skill] = max(0.0, current - 0.05)

    def get_member_preferences(self, member_id: str) -> dict:
        """
        الحصول على تفضيلات العضو — Get learned preferences for a member.
        """
        return self._preference_store.get(member_id, {})

    # ─── اقتراحات التحسين — Improvement Suggestions ─────────────────────────

    def suggest_team_improvements(self) -> list[ImprovementSuggestion]:
        """
        اقتراحات تحسين الفريق — Suggest improvements for team performance.

        Analyzes skill coverage, workload distribution, trust levels,
        and quality scores to generate actionable improvement suggestions.

        Returns:
            List of ImprovementSuggestion objects
        """
        suggestions: list[ImprovementSuggestion] = []
        overview = self.get_team_overview()

        # 1. مهارات نادرة — Rare skills (bottlenecks)
        for skill in overview.bottlenecks:
            suggestions.append(ImprovementSuggestion(
                category=ImprovementCategory.TRAINING.value,
                description=f"Skill bottleneck: only 1 member has '{skill}'. Consider cross-training.",
                description_ar=f"اختناق مهارات: عضو واحد فقط يمتلك '{skill}'. يُنصح بالتدريب المتقاطع.",
                impact=0.8,
                effort=0.5,
                priority=ImprovementPriority.HIGH.value,
            ))

        # 2. توظيف لأدوار مفقودة — Hiring for missing roles
        if overview.total_members < 3:
            suggestions.append(ImprovementSuggestion(
                category=ImprovementCategory.HIRING.value,
                description="Team is very small (<3 members). Consider hiring to improve resilience.",
                description_ar="الفريق صغير جداً (أقل من 3 أعضاء). يُنصح بالتوظيف لتحسين المرونة.",
                impact=0.9,
                effort=0.7,
                priority=ImprovementPriority.HIGH.value,
            ))

        # 3. عدم توازن العبء — Workload imbalance
        workloads = [m.current_workload for m in self._members.values()]
        if workloads:
            max_wl = max(workloads)
            min_wl = min(workloads)
            if max_wl - min_wl > 0.4:
                suggestions.append(ImprovementSuggestion(
                    category=ImprovementCategory.REBALANCING.value,
                    description=(
                        f"Workload imbalance detected: max={max_wl:.1%}, min={min_wl:.1%}. "
                        f"Redistribute tasks more evenly."
                    ),
                    description_ar=(
                        f"عدم توازن في العبء: الأعلى={max_wl:.1%}، الأدنى={min_wl:.1%}. "
                        f"يُنصح بإعادة توزيع المهام بشكل أكثر عدالة."
                    ),
                    impact=0.7,
                    effort=0.3,
                    priority=ImprovementPriority.MEDIUM.value,
                ))

        # 4. أعضاء بثقة منخفضة — Low-trust members
        for member_id, member in self._members.items():
            if member.trust_level < 0.3:
                suggestions.append(ImprovementSuggestion(
                    category=ImprovementCategory.PROCESS.value,
                    description=(
                        f"Member '{member.name_ar or member.name}' has low trust ({member.trust_level:.1%}). "
                        f"Consider mentorship or clearer task definitions."
                    ),
                    description_ar=(
                        f"العضو '{member.name_ar or member.name}' لديه ثقة منخفضة ({member.trust_level:.1%}). "
                        f"يُنصح بالإرشاد أو توضيح المهام بشكل أفضل."
                    ),
                    impact=0.6,
                    effort=0.4,
                    priority=ImprovementPriority.MEDIUM.value,
                ))

        # 5. جودة منخفضة — Low quality scores
        for member_id, member in self._members.items():
            if member.quality_score < 0.4 and member.completed_tasks > 3:
                suggestions.append(ImprovementSuggestion(
                    category=ImprovementCategory.TOOLING.value,
                    description=(
                        f"Member '{member.name_ar or member.name}' has low quality score "
                        f"({member.quality_score:.1%}). Consider providing better tools or review process."
                    ),
                    description_ar=(
                        f"العضو '{member.name_ar or member.name}' لديه درجة جودة منخفضة "
                        f"({member.quality_score:.1%}). يُنصح بتوفير أدوات أفضل أو عملية مراجعة."
                    ),
                    impact=0.5,
                    effort=0.4,
                    priority=ImprovementPriority.LOW.value,
                ))

        # 6. فجوات في قنوات التواصل — Communication channel gaps
        members_without_channels = [
            m for m in self._members.values()
            if not m.communication_channels
        ]
        if members_without_channels and overview.total_members > 1:
            suggestions.append(ImprovementSuggestion(
                category=ImprovementCategory.COMMUNICATION.value,
                description=(
                    f"{len(members_without_channels)} members have no communication channels configured."
                ),
                description_ar=(
                    f"{len(members_without_channels)} أعضاء ليس لديهم قنوات تواصل مهيأة."
                ),
                impact=0.6,
                effort=0.2,
                priority=ImprovementPriority.MEDIUM.value,
            ))

        # ترتيب حسب التأثير — Sort by impact
        suggestions.sort(key=lambda s: s.impact, reverse=True)

        return suggestions

    # ─── الواجهة القياسية — Standard Interface ─────────────────────────────

    def get_status(self) -> dict:
        """
        حالة الوحدة — Get the current status of the team model.

        Returns:
            dict with module status information
        """
        overview = self.get_team_overview()
        return {
            "enabled": HUMAN_COLLABORATION_ENABLED,
            "module": "TeamModel",
            "version": "14.0",
            "total_members": len(self._members),
            "overview": overview.to_dict(),
            "stats": dict(self._stats),
            "preference_profiles": len(self._preference_store),
            "task_histories": sum(len(v) for v in self._task_history.values()),
        }

    def shutdown(self) -> None:
        """
        إيقاف الوحدة — Gracefully shut down the team model.

        Clears state and logs final statistics.
        Complies with Law 5 (القانون 5 — orderly shutdown).
        """
        logger.info(
            "إيقاف نموذج الفريق — Team Model shutdown "
            "(members=%d, outcomes=%d) — Law 5 compliant",
            len(self._members),
            self._stats.get("outcomes_recorded", 0),
        )
        self._preference_store.clear()
        self._task_history.clear()
        logger.info("تم إيقاف نموذج الفريق بنجاح — Team Model shutdown complete")
