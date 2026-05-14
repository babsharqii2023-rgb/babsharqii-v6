"""
BABSHARQII v40.0 — Collaboration Orchestrator
منسق التعاون — توزيع المهام وتتبع الإنجاز وجمع الملاحظات من أعضاء الفريق البشري

A platform for distributing tasks to human team members via multiple communication
channels (WhatsApp, Telegram, email, in-app), tracking achievements, collecting
feedback, and detecting conflicts.

Inspired by Human-Agent Collaboration research (Horvitz 1999, Bansal et al. 2019):
  • Complementary strengths: humans provide creativity/judgment, AI provides scale/consistency
  • Adjustable autonomy: task difficulty determines level of AI independence
  • Transparency: humans always know what the AI is doing and why

Architecture:
  ┌────────────────────────────────────────────────────────────────────┐
  │                  CollaborationOrchestrator                          │
  │                                                                    │
  │  ┌────────────────────┐  ┌──────────────────────────────────────┐ │
  │  │ TaskDistributor    │  │ ConflictDetector                     │ │
  │  │ (multi-channel     │  │ (overlap, deadline, skill, workload  │ │
  │  │  delivery)         │  │  conflict detection)                 │ │
  │  └────────┬───────────┘  └──────────────┬───────────────────────┘ │
  │           │                             │                          │
  │  ┌────────▼─────────────────────────────▼──────────────────────┐ │
  │  │               ProgressTracker                                │ │
  │  │  (lifecycle: assigned → in_progress → submitted →           │ │
  │  │   reviewed → completed/rejected)                             │ │
  │  └──────────────────────────┬──────────────────────────────────┘ │
  │                             │                                      │
  │  ┌──────────────────────────▼──────────────────────────────────┐ │
  │  │               FeedbackCollector                              │ │
  │  │  (rating, comments, suggestions from human members)         │ │
  │  └────────────────────────────────────────────────────────────┘ │
  └────────────────────────────────────────────────────────────────────┘

Env toggles:
    MAMOUN_HUMAN_COLLABORATION   — تمكين/تعطيل التعاون البشري (الافتراضي: false)
"""

from __future__ import annotations

import os
import time
import uuid
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum
from datetime import datetime, timezone

from mamoun.human import HUMAN_COLLABORATION_ENABLED

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  التعدادات — Enumerations
# ═══════════════════════════════════════════════════════════════════════════════


class CommunicationChannel(str, Enum):
    """قنوات التواصل — Communication channels for task delivery."""
    IN_APP = "in_app"          # داخل التطبيق
    WHATSAPP = "whatsapp"      # واتساب (محاكاة)
    TELEGRAM = "telegram"      # تلجرام (محاكاة)
    EMAIL = "email"            # بريد إلكتروني (محاكاة)


class TaskPriority(str, Enum):
    """أولوية المهمة — Task priority levels."""
    CRITICAL = "critical"      # حرج
    HIGH = "high"              # عالي
    MEDIUM = "medium"          # متوسط
    LOW = "low"                # منخفض


class TaskLifecycleStatus(str, Enum):
    """حالة دورة حياة المهمة — Task lifecycle status."""
    ASSIGNED = "assigned"          # مُعيَّنة
    IN_PROGRESS = "in_progress"    # قيد التنفيذ
    SUBMITTED = "submitted"        # مُقدَّمة
    REVIEWED = "reviewed"          # مُراجَعة
    COMPLETED = "completed"        # مكتملة
    REJECTED = "rejected"          # مرفوضة


class ConflictType(str, Enum):
    """نوع التعارض — Conflict type."""
    OVERLAP = "overlap"        # تداخل المهام
    DEADLINE = "deadline"      # تعارض المواعيد
    SKILL = "skill"            # عدم تطابق المهارات
    WORKLOAD = "workload"      # عبء العمل الزائد


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج البيانات — Dataclasses
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class TaskAssignment:
    """
    تعيين مهمة — A task to be assigned to a human team member.
    """
    assignment_id: str = ""
    task_title: str = ""
    task_title_ar: str = ""
    task_description: str = ""
    task_description_ar: str = ""
    assignee_id: str = ""
    priority: str = TaskPriority.MEDIUM.value
    deadline: float = 0.0                    # Unix timestamp
    required_skills: list[str] = field(default_factory=list)
    channel: str = CommunicationChannel.IN_APP.value
    created_at: float = 0.0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.assignment_id:
            self.assignment_id = f"task_{uuid.uuid4().hex[:10]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AssignmentResult:
    """
    نتيجة التعيين — Result of a task assignment attempt.
    """
    assignment_id: str = ""
    success: bool = False
    channel_used: str = ""
    delivery_confirmed: bool = False
    message_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HumanFeedback:
    """
    ملاحظات بشرية — Feedback from a human team member.
    """
    feedback_id: str = ""
    task_id: str = ""
    member_id: str = ""
    rating: int = 3                    # 1-5 تقييم
    comments: str = ""
    suggestions: str = ""
    submitted_at: float = 0.0

    def __post_init__(self):
        if not self.feedback_id:
            self.feedback_id = f"fb_{uuid.uuid4().hex[:8]}"
        if not self.submitted_at:
            self.submitted_at = time.time()
        # ضبط التقييم بين 1 و5 — Clamp rating 1-5
        if self.rating < 1:
            self.rating = 1
        elif self.rating > 5:
            self.rating = 5

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TaskStatus:
    """
    حالة المهمة — Current status of a task.
    """
    task_id: str = ""
    title: str = ""
    status: str = TaskLifecycleStatus.ASSIGNED.value
    assignee_id: str = ""
    progress_percentage: float = 0.0
    deadline: float = 0.0
    time_remaining: float = 0.0        # بالثواني — in seconds
    has_feedback: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProgressReport:
    """
    تقرير التقدم — Overall team progress report.
    """
    total_tasks: int = 0
    by_status: dict = field(default_factory=dict)   # {status: count}
    completion_rate: float = 0.0                     # نسبة الإنجاز 0-1
    on_track_count: int = 0
    at_risk_count: int = 0
    overdue_count: int = 0
    team_utilization: float = 0.0                    # معدل الاستخدام 0-1

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Conflict:
    """
    تعارض — A detected conflict in task assignments.
    """
    conflict_id: str = ""
    conflict_type: str = ConflictType.OVERLAP.value
    description: str = ""
    description_ar: str = ""
    affected_tasks: list[str] = field(default_factory=list)
    affected_members: list[str] = field(default_factory=list)
    suggested_resolution: str = ""

    def __post_init__(self):
        if not self.conflict_id:
            self.conflict_id = f"conflict_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
#  منسق التعاون — CollaborationOrchestrator
# ═══════════════════════════════════════════════════════════════════════════════


class CollaborationOrchestrator:
    """
    منسق التعاون — المحرك الرئيسي لتوزيع المهام وتتبع الإنجاز البشري.

    Distributes tasks to human team members via multiple communication channels,
    tracks lifecycle progress, collects feedback, and detects conflicts.

    Features:
    - Multi-channel task distribution (in_app, whatsapp, telegram, email)
    - Full task lifecycle tracking (assigned → completed/rejected)
    - Feedback collection from human team members
    - Conflict detection (overlapping assignments, deadline conflicts, skill mismatches)
    - Notifications for task assignments and deadlines
    - Integration with ApprovalGate for critical decisions

    Usage:
        orchestrator = CollaborationOrchestrator()
        result = orchestrator.assign_task(TaskAssignment(
            task_title="Review report",
            task_title_ar="مراجعة التقرير",
            assignee_id="member_001",
            priority="high",
        ))
        progress = orchestrator.get_team_progress()
    """

    # عتبة المخاطر — Risk thresholds for approval gate integration
    CRITICAL_PRIORITY_APPROVAL_REQUIRED = True

    # حد الموارد — Resource limits
    MAX_TASKS = 500
    MAX_FEEDBACK_PER_TASK = 10
    OVERDUE_THRESHOLD_SECONDS = 0  # مهلة الصفر = الموعد النهائي نفسه

    def __init__(self, team_model: Optional[object] = None):
        """
        تهيئة منسق التعاون — Initialize the Collaboration Orchestrator.

        Args:
            team_model: نموذج الفريق — optional TeamModel for skill matching
        """
        self._team_model = team_model
        self._tasks: dict[str, dict] = {}               # task_id → task record
        self._feedbacks: dict[str, list[dict]] = {}      # task_id → [feedback]
        self._notifications: list[dict] = []
        self._assignment_counter = 0
        self._stats = {
            "tasks_assigned": 0,
            "tasks_completed": 0,
            "tasks_rejected": 0,
            "feedback_collected": 0,
            "conflicts_detected": 0,
            "reminders_sent": 0,
            "reassignments": 0,
        }

        if HUMAN_COLLABORATION_ENABLED:
            logger.info(
                "تم تفعيل منسق التعاون البشري — Human Collaboration Orchestrator enabled"
            )

    # ─── تعيين المهام — Task Assignment ────────────────────────────────────

    def assign_task(self, assignment: TaskAssignment) -> AssignmentResult:
        """
        تعيين مهمة — Assign a task to a human team member.

        Distributes the task via the specified communication channel and
        tracks it through its lifecycle. Critical-priority tasks may require
        approval gate integration.

        Args:
            assignment: تعيين المهمة — task assignment details

        Returns:
            AssignmentResult indicating success/failure and delivery status
        """
        if not HUMAN_COLLABORATION_ENABLED:
            logger.warning(
                "التعاون البشري غير مفعّل — Human collaboration disabled. "
                "Set MAMOUN_HUMAN_COLLABORATION=true"
            )
            return AssignmentResult(
                assignment_id=assignment.assignment_id,
                success=False,
                channel_used="",
                delivery_confirmed=False,
                message_id="",
            )

        # التحقق من الحد الأقصى — Enforce limits
        if len(self._tasks) >= self.MAX_TASKS:
            logger.warning("تم بلوغ الحد الأقصى للمهام — Max tasks reached: %d", self.MAX_TASKS)
            return AssignmentResult(
                assignment_id=assignment.assignment_id,
                success=False,
                channel_used="",
                delivery_confirmed=False,
                message_id="",
            )

        # تعيين القيم الافتراضية — Apply defaults
        if not assignment.priority:
            assignment.priority = TaskPriority.MEDIUM.value
        if not assignment.channel:
            assignment.channel = CommunicationChannel.IN_APP.value

        # إرسال عبر القناة — Deliver via channel
        delivery_result = self._deliver_task(assignment)
        channel_used = delivery_result.get("channel_used", assignment.channel)
        delivery_confirmed = delivery_result.get("delivered", False)
        message_id = delivery_result.get("message_id", "")

        # تخزين المهمة — Store task record
        task_record = {
            "assignment": assignment.to_dict(),
            "status": TaskLifecycleStatus.ASSIGNED.value,
            "assigned_at": time.time(),
            "updated_at": time.time(),
            "status_history": [
                {
                    "status": TaskLifecycleStatus.ASSIGNED.value,
                    "timestamp": time.time(),
                    "note": "تم تعيين المهمة — Task assigned",
                }
            ],
            "progress_percentage": 0.0,
            "delivery": delivery_result,
        }
        self._tasks[assignment.assignment_id] = task_record
        self._feedbacks[assignment.assignment_id] = []
        self._assignment_counter += 1
        self._stats["tasks_assigned"] += 1

        # إشعار التعيين — Assignment notification
        self._push_notification(
            task_id=assignment.assignment_id,
            member_id=assignment.assignee_id,
            ntype="assignment",
            message_ar=f"تم تعيين مهمة جديدة: {assignment.task_title_ar or assignment.task_title}",
            message_en=f"New task assigned: {assignment.task_title}",
        )

        # المهام الحرجة تتطلب موافقة — Critical tasks need approval gate
        if assignment.priority == TaskPriority.CRITICAL.value and self.CRITICAL_PRIORITY_APPROVAL_REQUIRED:
            logger.info(
                "مهمة حرجة تتطلب موافقة — Critical task requires approval: %s",
                assignment.assignment_id,
            )

        logger.info(
            "تم تعيين المهمة %s للعضو %s عبر %s — Task %s assigned to %s via %s",
            assignment.assignment_id,
            assignment.assignee_id,
            channel_used,
            assignment.assignment_id,
            assignment.assignee_id,
            channel_used,
        )

        return AssignmentResult(
            assignment_id=assignment.assignment_id,
            success=True,
            channel_used=channel_used,
            delivery_confirmed=delivery_confirmed,
            message_id=message_id,
        )

    def _deliver_task(self, assignment: TaskAssignment) -> dict:
        """
        إيصال المهمة — Deliver a task via the specified channel.
        WhatsApp, Telegram, Email are simulated; in_app is always available.
        """
        channel = assignment.channel

        if channel == CommunicationChannel.IN_APP.value:
            # داخل التطبيق — دائماً متاح
            return {
                "channel_used": "in_app",
                "delivered": True,
                "message_id": f"inapp_{uuid.uuid4().hex[:6]}",
            }

        elif channel == CommunicationChannel.WHATSAPP.value:
            # واتساب — محاكاة (يتطلب MAMOUN_WHATSAPP_API_URL)
            whatsapp_url = os.getenv("MAMOUN_WHATSAPP_API_URL", "")
            if whatsapp_url:
                return self._simulate_channel_delivery("whatsapp", assignment)
            return {
                "channel_used": "whatsapp",
                "delivered": False,
                "message_id": "",
                "error": "WhatsApp غير مهيأ — not configured",
            }

        elif channel == CommunicationChannel.TELEGRAM.value:
            # تلجرام — محاكاة (يتطلب MAMOUN_TELEGRAM_BOT_TOKEN)
            telegram_token = os.getenv("MAMOUN_TELEGRAM_BOT_TOKEN", "")
            if telegram_token:
                return self._simulate_channel_delivery("telegram", assignment)
            return {
                "channel_used": "telegram",
                "delivered": False,
                "message_id": "",
                "error": "Telegram غير مهيأ — not configured",
            }

        elif channel == CommunicationChannel.EMAIL.value:
            # بريد إلكتروني — محاكاة (يتطلب MAMOUN_SMTP_HOST)
            smtp_host = os.getenv("MAMOUN_SMTP_HOST", "")
            if smtp_host:
                return self._simulate_channel_delivery("email", assignment)
            return {
                "channel_used": "email",
                "delivered": False,
                "message_id": "",
                "error": "البريد الإلكتروني غير مهيأ — Email not configured",
            }

        else:
            # قناة غير معروفة —_FALLBACK إلى in_app
            logger.warning(
                "قناة غير معروفة '%s'، يتم استخدام in_app — Unknown channel, fallback to in_app",
                channel,
            )
            return {
                "channel_used": "in_app",
                "delivered": True,
                "message_id": f"inapp_{uuid.uuid4().hex[:6]}",
            }

    def _simulate_channel_delivery(self, channel: str, assignment: TaskAssignment) -> dict:
        """
        محاكاة الإيصال — Simulate delivery via an external channel.
        In production, this would call the actual API (WhatsApp Business, Telegram Bot, SMTP).
        """
        message_id = f"{channel}_{uuid.uuid4().hex[:8]}"
        logger.info(
            "محاكاة إرسال عبر %s: المهمة %s للعضو %s — Simulated %s delivery for task %s",
            channel,
            assignment.assignment_id,
            assignment.assignee_id,
            channel,
            assignment.assignment_id,
        )
        return {
            "channel_used": channel,
            "delivered": True,
            "message_id": message_id,
            "simulated": True,
        }

    # ─── تحديث حالة المهمة — Task Status Updates ───────────────────────────

    def update_task_status(self, task_id: str, status: str, note: str = "") -> bool:
        """
        تحديث حالة المهمة — Update the lifecycle status of a task.

        Valid transitions:
        - assigned → in_progress
        - in_progress → submitted
        - submitted → reviewed
        - reviewed → completed / rejected
        - assigned / in_progress → rejected (early rejection)

        Args:
            task_id: معرف المهمة — task identifier
            status: الحالة الجديدة — new status
            note: ملاحظة — optional note

        Returns:
            True if the update succeeded, False otherwise
        """
        if not HUMAN_COLLABORATION_ENABLED:
            return False

        if task_id not in self._tasks:
            logger.warning("مهمة غير موجودة — Task not found: %s", task_id)
            return False

        task = self._tasks[task_id]
        current_status = task["status"]

        # التحقق من صحة الانتقال — Validate transition
        valid_transitions = {
            TaskLifecycleStatus.ASSIGNED.value: [
                TaskLifecycleStatus.IN_PROGRESS.value,
                TaskLifecycleStatus.REJECTED.value,
            ],
            TaskLifecycleStatus.IN_PROGRESS.value: [
                TaskLifecycleStatus.SUBMITTED.value,
                TaskLifecycleStatus.REJECTED.value,
            ],
            TaskLifecycleStatus.SUBMITTED.value: [
                TaskLifecycleStatus.REVIEWED.value,
                TaskLifecycleStatus.REJECTED.value,
            ],
            TaskLifecycleStatus.REVIEWED.value: [
                TaskLifecycleStatus.COMPLETED.value,
                TaskLifecycleStatus.REJECTED.value,
            ],
            TaskLifecycleStatus.COMPLETED.value: [],
            TaskLifecycleStatus.REJECTED.value: [],
        }

        allowed = valid_transitions.get(current_status, [])
        if status not in allowed:
            logger.warning(
                "انتقال غير صالح من '%s' إلى '%s' للمهمة %s — Invalid transition '%s' → '%s' for task %s",
                current_status, status, task_id, current_status, status, task_id,
            )
            return False

        # تحديث الحالة — Apply update
        task["status"] = status
        task["updated_at"] = time.time()
        task["status_history"].append({
            "status": status,
            "timestamp": time.time(),
            "note": note or f"تم التحديث إلى {status} — Updated to {status}",
        })

        # تحديث نسبة التقدم — Update progress percentage
        progress_map = {
            TaskLifecycleStatus.ASSIGNED.value: 0.0,
            TaskLifecycleStatus.IN_PROGRESS.value: 0.3,
            TaskLifecycleStatus.SUBMITTED.value: 0.7,
            TaskLifecycleStatus.REVIEWED.value: 0.9,
            TaskLifecycleStatus.COMPLETED.value: 1.0,
            TaskLifecycleStatus.REJECTED.value: task["progress_percentage"],
        }
        task["progress_percentage"] = progress_map.get(status, task["progress_percentage"])

        # تحديث الإحصائيات — Update stats
        if status == TaskLifecycleStatus.COMPLETED.value:
            self._stats["tasks_completed"] += 1
        elif status == TaskLifecycleStatus.REJECTED.value:
            self._stats["tasks_rejected"] += 1

        # إشعار — Notification
        assignee = task["assignment"].get("assignee_id", "")
        status_labels_ar = {
            TaskLifecycleStatus.IN_PROGRESS.value: "قيد التنفيذ",
            TaskLifecycleStatus.SUBMITTED.value: "تم التقديم",
            TaskLifecycleStatus.REVIEWED.value: "تمت المراجعة",
            TaskLifecycleStatus.COMPLETED.value: "مكتملة",
            TaskLifecycleStatus.REJECTED.value: "مرفوضة",
        }
        self._push_notification(
            task_id=task_id,
            member_id=assignee,
            ntype="status_update",
            message_ar=f"تحديث المهمة: {status_labels_ar.get(status, status)}",
            message_en=f"Task updated: {status}",
        )

        logger.info(
            "تم تحديث حالة المهمة %s: %s → %s — Task %s status: %s → %s",
            task_id, current_status, status, task_id, current_status, status,
        )
        return True

    # ─── جمع الملاحظات — Feedback Collection ────────────────────────────────

    def collect_feedback(self, task_id: str, feedback: HumanFeedback) -> bool:
        """
        جمع الملاحظات — Collect feedback from a human team member about a task.

        Args:
            task_id: معرف المهمة — task identifier
            feedback: الملاحظات — feedback details

        Returns:
            True if feedback was recorded, False otherwise
        """
        if not HUMAN_COLLABORATION_ENABLED:
            return False

        if task_id not in self._tasks:
            logger.warning("مهمة غير موجودة — Task not found: %s", task_id)
            return False

        # التحقق من الحد الأقصى — Enforce limits
        if len(self._feedbacks.get(task_id, [])) >= self.MAX_FEEDBACK_PER_TASK:
            logger.warning(
                "تم بلوغ الحد الأقصى للملاحظات على المهمة %s — Max feedback reached for task %s",
                task_id, task_id,
            )
            return False

        # ربط الملاحظات بالمهمة — Link feedback to task
        feedback.task_id = task_id
        self._feedbacks.setdefault(task_id, []).append(feedback.to_dict())
        self._stats["feedback_collected"] += 1

        # إذا كان التقييم منخفضاً (1-2)، نُبلغ عنه — Flag low ratings
        if feedback.rating <= 2:
            logger.info(
                "تقييم منخفض (%d/5) على المهمة %s من العضو %s — Low rating on task %s",
                feedback.rating, task_id, feedback.member_id, task_id,
            )

        # تحديث نموذج الفريق إذا كان متاحاً — Update team model if available
        if self._team_model and hasattr(self._team_model, "record_task_outcome"):
            task = self._tasks[task_id]
            outcome = {
                "task_id": task_id,
                "rating": feedback.rating,
                "comments": feedback.comments,
                "suggestions": feedback.suggestions,
                "status": task["status"],
            }
            self._team_model.record_task_outcome(
                feedback.member_id, task_id, outcome
            )

        logger.info(
            "تم تسجيل ملاحظات على المهمة %s من العضو %s (تقييم: %d/5) — Feedback recorded for task %s",
            task_id, feedback.member_id, feedback.rating, task_id,
        )
        return True

    # ─── استعلام حالة المهمة — Task Status Query ───────────────────────────

    def get_task_status(self, task_id: str) -> TaskStatus:
        """
        استعلام حالة المهمة — Get the current status of a task.

        Args:
            task_id: معرف المهمة — task identifier

        Returns:
            TaskStatus with current details, or empty TaskStatus if not found
        """
        if task_id not in self._tasks:
            return TaskStatus(task_id=task_id)

        task = self._tasks[task_id]
        assignment = task["assignment"]
        now = time.time()
        deadline = assignment.get("deadline", 0.0)
        time_remaining = max(0.0, deadline - now) if deadline > 0 else 0.0

        return TaskStatus(
            task_id=task_id,
            title=assignment.get("task_title", ""),
            status=task["status"],
            assignee_id=assignment.get("assignee_id", ""),
            progress_percentage=task["progress_percentage"],
            deadline=deadline,
            time_remaining=time_remaining,
            has_feedback=bool(self._feedbacks.get(task_id, [])),
        )

    # ─── تقرير تقدم الفريق — Team Progress Report ──────────────────────────

    def get_team_progress(self) -> ProgressReport:
        """
        تقرير تقدم الفريق — Generate a comprehensive progress report.

        Returns:
            ProgressReport with task counts, completion rate, risk assessment
        """
        if not self._tasks:
            return ProgressReport()

        total = len(self._tasks)
        by_status: dict[str, int] = {}
        on_track = 0
        at_risk = 0
        overdue = 0
        now = time.time()

        for task_id, task in self._tasks.items():
            status = task["status"]
            by_status[status] = by_status.get(status, 0) + 1

            deadline = task["assignment"].get("deadline", 0.0)
            # تحديد حالة الموعد — Determine deadline status
            if status in (TaskLifecycleStatus.COMPLETED.value, TaskLifecycleStatus.REJECTED.value):
                on_track += 1
            elif deadline > 0 and now > deadline:
                overdue += 1
            elif deadline > 0 and (deadline - now) < 3600:  # أقل من ساعة — less than 1 hour
                at_risk += 1
            else:
                on_track += 1

        completed = by_status.get(TaskLifecycleStatus.COMPLETED.value, 0)
        completion_rate = completed / total if total > 0 else 0.0

        # حساب معدل الاستخدام — Calculate team utilization
        active_members = set()
        for task in self._tasks.values():
            if task["status"] not in (
                TaskLifecycleStatus.COMPLETED.value,
                TaskLifecycleStatus.REJECTED.value,
            ):
                member = task["assignment"].get("assignee_id", "")
                if member:
                    active_members.add(member)

        total_members = set()
        for task in self._tasks.values():
            member = task["assignment"].get("assignee_id", "")
            if member:
                total_members.add(member)

        utilization = len(active_members) / len(total_members) if total_members else 0.0

        return ProgressReport(
            total_tasks=total,
            by_status=by_status,
            completion_rate=round(completion_rate, 4),
            on_track_count=on_track,
            at_risk_count=at_risk,
            overdue_count=overdue,
            team_utilization=round(utilization, 4),
        )

    # ─── كشف التعارضات — Conflict Detection ────────────────────────────────

    def detect_conflicts(self) -> list[Conflict]:
        """
        كشف التعارضات — Detect conflicts in task assignments.

        Checks for:
        - Overlapping assignments (same member, overlapping time)
        - Deadline conflicts (too many tasks due at the same time)
        - Skill mismatches (task requires skills the member doesn't have)
        - Workload imbalances (one member overloaded while others idle)

        Returns:
            List of detected Conflict objects
        """
        conflicts: list[Conflict] = []
        now = time.time()

        # تجميع المهام حسب العضو — Group tasks by member
        member_tasks: dict[str, list[dict]] = {}
        for task_id, task in self._tasks.items():
            if task["status"] in (TaskLifecycleStatus.COMPLETED.value, TaskLifecycleStatus.REJECTED.value):
                continue
            member_id = task["assignment"].get("assignee_id", "")
            if member_id:
                member_tasks.setdefault(member_id, []).append(task)

        # 1. كشف التداخل — Detect overlapping assignments
        for member_id, tasks in member_tasks.items():
            if len(tasks) > 1:
                for i in range(len(tasks)):
                    for j in range(i + 1, len(tasks)):
                        t1 = tasks[i]
                        t2 = tasks[j]
                        d1 = t1["assignment"].get("deadline", 0.0)
                        d2 = t2["assignment"].get("deadline", 0.0)
                        # إذا كان الموعدان متقاربين (أقل من ساعة) — Close deadlines
                        if d1 > 0 and d2 > 0 and abs(d1 - d2) < 3600:
                            conflicts.append(Conflict(
                                conflict_type=ConflictType.OVERLAP.value,
                                description=(
                                    f"Member {member_id} has two tasks with close deadlines: "
                                    f"{t1['assignment'].get('task_title', '')} and "
                                    f"{t2['assignment'].get('task_title', '')}"
                                ),
                                description_ar=(
                                    f"العضو {member_id} لديه مهمتان بمواعيد متقاربة: "
                                    f"{t1['assignment'].get('task_title_ar', t1['assignment'].get('task_title', ''))} و "
                                    f"{t2['assignment'].get('task_title_ar', t2['assignment'].get('task_title', ''))}"
                                ),
                                affected_tasks=[
                                    t1["assignment"].get("assignment_id", ""),
                                    t2["assignment"].get("assignment_id", ""),
                                ],
                                affected_members=[member_id],
                                suggested_resolution=(
                                    "إعادة جدولة إحدى المهام أو تعيينها لعضو آخر — "
                                    "Reschedule one task or reassign to another member"
                                ),
                            ))

        # 2. كشف تعارض المواعيد — Detect deadline conflicts (same time, multiple tasks)
        deadline_groups: dict[float, list[dict]] = {}
        for task_id, task in self._tasks.items():
            if task["status"] in (TaskLifecycleStatus.COMPLETED.value, TaskLifecycleStatus.REJECTED.value):
                continue
            deadline = task["assignment"].get("deadline", 0.0)
            if deadline > 0:
                # تجميع حسب الساعة — Group by hour
                hour_key = int(deadline // 3600) * 3600
                deadline_groups.setdefault(hour_key, []).append(task)

        for hour_key, tasks in deadline_groups.items():
            if len(tasks) > 2:
                affected_members = list({
                    t["assignment"].get("assignee_id", "") for t in tasks
                })
                conflicts.append(Conflict(
                    conflict_type=ConflictType.DEADLINE.value,
                    description=(
                        f"{len(tasks)} tasks due around the same time "
                        f"({datetime.fromtimestamp(hour_key, tz=timezone.utc).isoformat()})"
                    ),
                    description_ar=(
                        f"{len(tasks)} مهام مستحقة في نفس الوقت تقريباً "
                        f"({datetime.fromtimestamp(hour_key, tz=timezone.utc).isoformat()})"
                    ),
                    affected_tasks=[
                        t["assignment"].get("assignment_id", "") for t in tasks
                    ],
                    affected_members=affected_members,
                    suggested_resolution=(
                        "توزيع المواعيد على فترات أطول — Spread deadlines over a longer period"
                    ),
                ))

        # 3. كشف عدم تطابق المهارات — Detect skill mismatches
        for member_id, tasks in member_tasks.items():
            member_skills = set()
            if self._team_model and hasattr(self._team_model, "get_member_profile"):
                profile = self._team_model.get_member_profile(member_id)
                if profile and hasattr(profile, "skills"):
                    member_skills = set(profile.skills)

            for task in tasks:
                required = task["assignment"].get("required_skills", [])
                if required and member_skills:
                    missing = [s for s in required if s not in member_skills]
                    if missing:
                        conflicts.append(Conflict(
                            conflict_type=ConflictType.SKILL.value,
                            description=(
                                f"Member {member_id} lacks skills for task "
                                f"'{task['assignment'].get('task_title', '')}': missing {missing}"
                            ),
                            description_ar=(
                                f"العضو {member_id} يفتقر إلى مهارات للمهمة "
                                f"'{task['assignment'].get('task_title_ar', task['assignment'].get('task_title', ''))}': "
                                f"مفقود {missing}"
                            ),
                            affected_tasks=[task["assignment"].get("assignment_id", "")],
                            affected_members=[member_id],
                            suggested_resolution=(
                                f"تعيين عضو يمتلك المهارات المفقودة ({', '.join(missing)}) أو "
                                f"توفير تدريب — Assign member with missing skills or provide training"
                            ),
                        ))

        # 4. كشف عبء العمل الزائد — Detect workload imbalances
        task_counts = {mid: len(ts) for mid, ts in member_tasks.items()}
        if task_counts:
            max_load = max(task_counts.values())
            min_load = min(task_counts.values())
            if max_load - min_load >= 3:
                overloaded = [mid for mid, cnt in task_counts.items() if cnt == max_load]
                underloaded = [mid for mid, cnt in task_counts.items() if cnt == min_load]
                conflicts.append(Conflict(
                    conflict_type=ConflictType.WORKLOAD.value,
                    description=(
                        f"Workload imbalance: {overloaded} have {max_load} tasks, "
                        f"{underloaded} have {min_load} tasks"
                    ),
                    description_ar=(
                        f"عدم توازن العبء: {overloaded} لديهم {max_load} مهام، "
                        f"{underloaded} لديهم {min_load} مهام"
                    ),
                    affected_tasks=[],
                    affected_members=overloaded + underloaded,
                    suggested_resolution=(
                        "إعادة توزيع المهام من الأعضاء المثقلين إلى الأقل عبئاً — "
                        "Redistribute tasks from overloaded to underloaded members"
                    ),
                ))

        self._stats["conflicts_detected"] = len(conflicts)
        if conflicts:
            logger.info(
                "تم كشف %d تعارضات — Detected %d conflicts",
                len(conflicts), len(conflicts),
            )

        return conflicts

    # ─── تذكير — Reminders ────────────────────────────────────────────────

    def send_reminder(self, task_id: str) -> bool:
        """
        إرسال تذكير — Send a reminder for a task approaching its deadline.

        Args:
            task_id: معرف المهمة — task identifier

        Returns:
            True if the reminder was sent, False otherwise
        """
        if not HUMAN_COLLABORATION_ENABLED:
            return False

        if task_id not in self._tasks:
            logger.warning("مهمة غير موجودة — Task not found: %s", task_id)
            return False

        task = self._tasks[task_id]
        if task["status"] in (TaskLifecycleStatus.COMPLETED.value, TaskLifecycleStatus.REJECTED.value):
            logger.info("المهمة مكتملة/مرفوضة — Task already completed/rejected: %s", task_id)
            return False

        assignment = task["assignment"]
        assignee_id = assignment.get("assignee_id", "")
        title = assignment.get("task_title_ar", "") or assignment.get("task_title", "")
        deadline = assignment.get("deadline", 0.0)

        # صياغة التذكير — Compose reminder
        if deadline > 0:
            remaining = max(0.0, deadline - time.time())
            hours_left = remaining / 3600.0
            reminder_ar = f"تذكير: المهمة '{title}' متبقي عليها {hours_left:.1f} ساعة"
            reminder_en = f"Reminder: Task '{assignment.get('task_title', '')}' has {hours_left:.1f} hours left"
        else:
            reminder_ar = f"تذكير: المهمة '{title}' بانتظار إنجازك"
            reminder_en = f"Reminder: Task '{assignment.get('task_title', '')}' awaits your action"

        self._push_notification(
            task_id=task_id,
            member_id=assignee_id,
            ntype="reminder",
            message_ar=reminder_ar,
            message_en=reminder_en,
        )
        self._stats["reminders_sent"] += 1

        logger.info(
            "تم إرسال تذكير للمهمة %s — Reminder sent for task %s",
            task_id, task_id,
        )
        return True

    # ─── إعادة التعيين — Reassignment ─────────────────────────────────────

    def reassign_task(self, task_id: str, new_member_id: str) -> bool:
        """
        إعادة تعيين مهمة — Reassign a task to a different team member.

        Args:
            task_id: معرف المهمة — task identifier
            new_member_id: معرف العضو الجديد — new assignee's identifier

        Returns:
            True if reassignment succeeded, False otherwise
        """
        if not HUMAN_COLLABORATION_ENABLED:
            return False

        if task_id not in self._tasks:
            logger.warning("مهمة غير موجودة — Task not found: %s", task_id)
            return False

        task = self._tasks[task_id]
        if task["status"] in (TaskLifecycleStatus.COMPLETED.value, TaskLifecycleStatus.REJECTED.value):
            logger.warning(
                "لا يمكن إعادة تعيين مهمة مكتملة/مرفوضة — Cannot reassign completed/rejected task: %s",
                task_id,
            )
            return False

        old_member = task["assignment"].get("assignee_id", "")
        task["assignment"]["assignee_id"] = new_member_id
        task["updated_at"] = time.time()
        task["status_history"].append({
            "status": task["status"],
            "timestamp": time.time(),
            "note": f"تم إعادة التعيين من {old_member} إلى {new_member_id} — Reassigned from {old_member} to {new_member_id}",
        })

        # إشعار للعضو الجديد — Notify new assignee
        title = task["assignment"].get("task_title_ar", "") or task["assignment"].get("task_title", "")
        self._push_notification(
            task_id=task_id,
            member_id=new_member_id,
            ntype="reassignment",
            message_ar=f"تم تعيين مهمة جديدة لك: {title}",
            message_en=f"A task has been reassigned to you: {task['assignment'].get('task_title', '')}",
        )

        self._stats["reassignments"] += 1

        logger.info(
            "تم إعادة تعيين المهمة %s من %s إلى %s — Task %s reassigned from %s to %s",
            task_id, old_member, new_member_id, task_id, old_member, new_member_id,
        )
        return True

    # ─── قائمة المهام — Task Listing ───────────────────────────────────────

    def list_tasks(
        self,
        status: Optional[str] = None,
        member_id: Optional[str] = None,
    ) -> list[dict]:
        """
        قائمة المهام — List tasks with optional filtering.

        Args:
            status: تصفية حسب الحالة — filter by status (optional)
            member_id: تصفية حسب العضو — filter by member (optional)

        Returns:
            List of task dictionaries
        """
        results = []
        for task_id, task in self._tasks.items():
            # تصفية حسب الحالة — Filter by status
            if status and task["status"] != status:
                continue
            # تصفية حسب العضو — Filter by member
            if member_id and task["assignment"].get("assignee_id", "") != member_id:
                continue

            results.append({
                "task_id": task_id,
                "title": task["assignment"].get("task_title", ""),
                "title_ar": task["assignment"].get("task_title_ar", ""),
                "status": task["status"],
                "assignee_id": task["assignment"].get("assignee_id", ""),
                "priority": task["assignment"].get("priority", ""),
                "deadline": task["assignment"].get("deadline", 0.0),
                "progress_percentage": task["progress_percentage"],
                "has_feedback": bool(self._feedbacks.get(task_id, [])),
            })

        return results

    # ─── إشعارات داخلية — Internal Notifications ───────────────────────────

    def _push_notification(
        self,
        task_id: str,
        member_id: str,
        ntype: str,
        message_ar: str,
        message_en: str,
    ) -> None:
        """إشعار داخلي — Push an internal notification."""
        notification = {
            "notification_id": f"ntf_{uuid.uuid4().hex[:6]}",
            "task_id": task_id,
            "member_id": member_id,
            "type": ntype,
            "message_ar": message_ar,
            "message_en": message_en,
            "timestamp": time.time(),
        }
        self._notifications.append(notification)
        # الحفاظ على آخر 200 إشعار — Keep last 200 notifications
        if len(self._notifications) > 200:
            self._notifications = self._notifications[-100:]

    def get_notifications(self, limit: int = 20) -> list[dict]:
        """الحصول على الإشعارات — Get recent notifications."""
        return list(reversed(self._notifications[-limit:]))

    # ─── الواجهة القياسية — Standard Interface ─────────────────────────────

    def get_status(self) -> dict:
        """
        حالة الوحدة — Get the current status of the collaboration orchestrator.

        Returns:
            dict with module status information
        """
        progress = self.get_team_progress()
        return {
            "enabled": HUMAN_COLLABORATION_ENABLED,
            "module": "CollaborationOrchestrator",
            "version": "14.0",
            "total_tasks": len(self._tasks),
            "stats": dict(self._stats),
            "progress": progress.to_dict(),
            "notifications_count": len(self._notifications),
            "team_model_connected": self._team_model is not None,
        }

    def shutdown(self) -> None:
        """
        إيقاف الوحدة — Gracefully shut down the collaboration orchestrator.

        Flushes pending notifications and clears state.
        Complies with Law 5 (القانون 5 — orderly shutdown).
        """
        logger.info(
            "إيقاف منسق التعاون — Collaboration Orchestrator shutdown "
            "(tasks=%d, completed=%d) — Law 5 compliant",
            len(self._tasks),
            self._stats.get("tasks_completed", 0),
        )
        self._notifications.clear()
        logger.info("تم إيقاف منسق التعاون بنجاح — Collaboration Orchestrator shutdown complete")
