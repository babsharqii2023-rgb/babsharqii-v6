"""
BABSHARQII v13.0 — Gap Request (Metacognitive Planning)
طلب الاحتياجات — عندما يواجه مأمون مهمة تتجاوز معرفته، يطلب موافقة ويعدد احتياجاته

Integration:
- Uses existing ApprovalGate for human approval
- Uses existing TimeBoundedPolicy for time-limited permissions
- Modifies CuriosityInstinct and WorldModelV2 for gap detection
- Shows approval popup in chat UI via existing ApprovalGate

Feature Flag: MAMOUN_METACOGNITIVE_PLANNING (default: false)
"""

import os
import time
import json
import uuid
import logging
import asyncio
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum

from mamoun.approval import METACOGNITIVE_PLANNING_ENABLED

logger = logging.getLogger(__name__)


class GapType(str, Enum):
    """أنواع الفجوات المعرفية."""
    EXTERNAL_RESEARCH = "external_research"       # يحتاج بحث خارجي
    API_ACCESS = "api_access"                      # يحتاج مفتاح API
    PERMISSION = "permission"                      # يحتاج صلاحية
    COMPUTATION = "computation"                    # يحتاج موارد حوسبة
    KNOWLEDGE_BASE = "knowledge_base"              # يحتاج قاعدة معرفة
    TOOL_ACCESS = "tool_access"                    # يحتاج أداة غير متاحة


class GapPriority(str, Enum):
    """أولوية الفجوة."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GapRequestStatus(str, Enum):
    """حالة طلب الفجوة."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ResourceNeed:
    """احتياج مورد محدد."""
    resource_type: str = ""       # api_key, permission, computation, tool, knowledge
    resource_name: str = ""       # e.g., "Instagram API Key", "filesystem:write"
    duration_minutes: float = 0.0  # المدة المطلوبة
    reason: str = ""              # لماذا يحتاجه
    optional: bool = False        # هل يمكن بدونه؟

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GapRequest:
    """
    طلب فجوة معرفية — عندما يواجه مأمون مهمة تتجاوز معرفته.

    Contains:
    - What task triggered the gap
    - What resources are needed
    - How long they're needed
    - Why they're needed
    - Whether human approval is required
    """
    request_id: str = ""
    task_description: str = ""         # وصف المهمة التي كشفت الفجوة
    gap_type: str = GapType.EXTERNAL_RESEARCH.value
    priority: str = GapPriority.MEDIUM.value
    resources_needed: list = field(default_factory=list)  # List[ResourceNeed]
    estimated_duration_minutes: float = 0.0
    reasoning: str = ""                # شرح لماذا يحتاج هذه الموارد
    proposed_plan: str = ""            # الخطة المقترحة بعد الحصول على الموارد
    status: str = GapRequestStatus.PENDING.value
    approval_id: str = ""              # ربط بـ ApprovalGate
    created_at: float = 0.0
    decided_at: float = 0.0
    decided_by: str = ""
    expiry_at: float = 0.0
    execution_result: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.request_id:
            self.request_id = f"gap_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()
        if not self.expiry_at:
            self.expiry_at = self.created_at + 3600  # 1 hour default

    def is_expired(self) -> bool:
        """هل انتهت صلاحية الطلب؟"""
        return time.time() > self.expiry_at

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "task_description": self.task_description,
            "gap_type": self.gap_type,
            "priority": self.priority,
            "resources_needed": [r.to_dict() if isinstance(r, ResourceNeed) else r for r in self.resources_needed],
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "reasoning": self.reasoning,
            "proposed_plan": self.proposed_plan,
            "status": self.status,
            "approval_id": self.approval_id,
            "created_at": self.created_at,
            "decided_at": self.decided_at,
            "decided_by": self.decided_by,
            "expiry_at": self.expiry_at,
        }


class GapRequestManager:
    """
    مديل طلبات الفجوة — يدير اكتشاف الفجوات وطلب الموافقة.

    Flow:
    1. WorldModelV2 or CuriosityInstinct detects a knowledge gap
    2. GapRequestManager creates a GapRequest with resource needs
    3. Request is submitted through ApprovalGate for human review
    4. If approved, TimeBoundedPolicy grants temporary permissions
    5. Task continues with the granted resources
    6. Permissions auto-revoke after the time limit

    Integration Points:
    - ApprovalGate: For human approval of gap requests
    - TimeBoundedPolicy: For granting time-limited permissions
    - WorldModelV2.detect_knowledge_gap(): For gap detection
    - CuriosityInstinct: For curiosity-driven gap detection
    """

    def __init__(self, approval_gate=None, time_bounded_policy=None):
        self._approval_gate = approval_gate
        self._time_bounded_policy = time_bounded_policy
        self._requests: dict[str, GapRequest] = {}
        self._request_counter = 0

    async def detect_and_request(
        self,
        task_description: str,
        context: dict = None,
        knowledge_gaps: list[dict] = None,
    ) -> Optional[GapRequest]:
        """
        كشف الفجوة وإنشاء طلب — Detect gap and create request.

        Args:
            task_description: وصف المهمة الحالية
            context: سياق إضافي
            knowledge_gaps: فجوات معرفية مكتشفة من WorldModelV2

        Returns:
            GapRequest if gap detected and request created, None otherwise
        """
        if not METACOGNITIVE_PLANNING_ENABLED:
            logger.debug("Metacognitive planning disabled — no gap request created")
            return None

        context = context or {}
        knowledge_gaps = knowledge_gaps or []

        # Analyze context to determine gap type and resources needed
        gap_analysis = self._analyze_gap(task_description, context, knowledge_gaps)

        if not gap_analysis.get("has_gap"):
            return None

        # Create gap request
        request = GapRequest(
            task_description=task_description,
            gap_type=gap_analysis.get("gap_type", GapType.EXTERNAL_RESEARCH.value),
            priority=gap_analysis.get("priority", GapPriority.MEDIUM.value),
            resources_needed=gap_analysis.get("resources_needed", []),
            estimated_duration_minutes=gap_analysis.get("duration_minutes", 15),
            reasoning=gap_analysis.get("reasoning", ""),
            proposed_plan=gap_analysis.get("proposed_plan", ""),
        )

        # Submit for approval through existing ApprovalGate
        if self._approval_gate:
            try:
                from mamoun.core.approval_gate import ApprovalRequest
                approval_request = ApprovalRequest(
                    change_type="gap_request",
                    target=f"metacognitive:{request.gap_type}",
                    description=(
                        f"طلب احتياجات: {request.reasoning} | "
                        f"المدة: {request.estimated_duration_minutes} دقيقة | "
                        f"الموارد: {len(request.resources_needed)}"
                    ),
                    risk_level="medium" if request.priority != GapPriority.CRITICAL.value else "high",
                    details=json.dumps(request.to_dict(), ensure_ascii=False),
                )
                approval_result = await self._approval_gate.request_approval(approval_request)
                request.approval_id = approval_result.get("id", "")

                if approval_result.get("status") == "auto_approved":
                    request.status = GapRequestStatus.APPROVED.value
                    request.decided_by = "auto_low_risk"
                elif approval_result.get("status") == "pending":
                    request.status = GapRequestStatus.PENDING.value
                else:
                    request.status = GapRequestStatus.PENDING.value

            except Exception as e:
                logger.warning(f"Failed to submit gap request to ApprovalGate: {e}")
                request.status = GapRequestStatus.PENDING.value
        else:
            request.status = GapRequestStatus.PENDING.value

        # Store request
        self._requests[request.request_id] = request
        self._request_counter += 1

        logger.info(
            f"GapRequest created: {request.request_id} | "
            f"Type: {request.gap_type} | "
            f"Duration: {request.estimated_duration_minutes}min | "
            f"Status: {request.status}"
        )

        return request

    async def approve_request(self, request_id: str, granted_permissions: list = None) -> bool:
        """
        الموافقة على طلب فجوة — Approve a gap request.

        Args:
            request_id: معرف الطلب
            granted_permissions: الصلاحيات الممنوحة

        Returns:
            True if approved successfully
        """
        request = self._requests.get(request_id)
        if not request:
            return False

        request.status = GapRequestStatus.APPROVED.value
        request.decided_at = time.time()
        request.decided_by = "human"

        # Also approve in ApprovalGate if linked
        if request.approval_id and self._approval_gate:
            try:
                await self._approval_gate.approve(request.approval_id)
            except Exception as e:
                logger.warning(f"Failed to approve in ApprovalGate: {e}")

        # Grant time-bounded permissions if policy available
        if self._time_bounded_policy and granted_permissions:
            for perm in granted_permissions:
                try:
                    await self._time_bounded_policy.request_permission(
                        agent_id="gap_request_manager",
                        scope=perm.get("scope", ""),
                        permissions=perm.get("permissions", []),
                        duration_minutes=request.estimated_duration_minutes,
                        task_context=request.task_description,
                        reason=request.reasoning,
                    )
                except Exception as e:
                    logger.warning(f"Failed to grant permission: {e}")

        return True

    async def reject_request(self, request_id: str, reason: str = "") -> bool:
        """رفض طلب فجوة."""
        request = self._requests.get(request_id)
        if not request:
            return False

        request.status = GapRequestStatus.REJECTED.value
        request.decided_at = time.time()
        request.decided_by = "human"

        # Also reject in ApprovalGate if linked
        if request.approval_id and self._approval_gate:
            try:
                await self._approval_gate.reject(request.approval_id, reason)
            except Exception as e:
                logger.warning(f"Failed to reject in ApprovalGate: {e}")

        return True

    def get_pending_requests(self) -> list[dict]:
        """الحصول على الطلبات المعلقة."""
        return [
            r.to_dict() for r in self._requests.values()
            if r.status == GapRequestStatus.PENDING.value
        ]

    def get_all_requests(self) -> list[dict]:
        """الحصول على جميع الطلبات."""
        return [r.to_dict() for r in self._requests.values()]

    def get_request(self, request_id: str) -> Optional[dict]:
        """الحصول على طلب محدد."""
        request = self._requests.get(request_id)
        return request.to_dict() if request else None

    def _analyze_gap(
        self,
        task_description: str,
        context: dict,
        knowledge_gaps: list[dict],
    ) -> dict:
        """
        تحليل الفجوة — Analyze task and context to determine gap type and resources.
        """
        resources_needed = []
        gap_type = GapType.EXTERNAL_RESEARCH.value
        priority = GapPriority.MEDIUM.value
        duration_minutes = 15
        reasoning = ""
        proposed_plan = ""
        has_gap = False

        # Check for high-severity knowledge gaps
        high_gaps = [g for g in knowledge_gaps if g.get("severity") in ("high", "critical")]
        if high_gaps:
            has_gap = True
            gap_type = GapType.EXTERNAL_RESEARCH.value
            priority = GapPriority.HIGH.value
            duration_minutes = 30
            reasoning = f"اكتشاف {len(high_gaps)} فجوة معرفية عالية الخطورة: " + ", ".join(
                g.get("description", "")[:50] for g in high_gaps[:3]
            )
            resources_needed.append(ResourceNeed(
                resource_type="api_access",
                resource_name="web_search",
                duration_minutes=duration_minutes,
                reason="للبحث عن معلومات لسد الفجوات المعرفية",
            ).to_dict())
            proposed_plan = "1. البحث عن المعلومات المفقودة 2. تحليل النتائج 3. دمج المعرفة الجديدة"

        # Check for missing API keys in context
        required_apis = context.get("required_apis", [])
        missing_apis = [api for api in required_apis if not context.get(f"has_{api}_key")]
        if missing_apis:
            has_gap = True
            gap_type = GapType.API_ACCESS.value
            priority = GapPriority.HIGH.value
            reasoning = f"يحتاج مفاتيح API غير متوفرة: {', '.join(missing_apis)}"
            for api in missing_apis:
                resources_needed.append(ResourceNeed(
                    resource_type="api_key",
                    resource_name=f"{api}_api_key",
                    duration_minutes=60,
                    reason=f"مطلوب للوصول إلى {api}",
                ).to_dict())

        # Check for permission needs
        required_permissions = context.get("required_permissions", [])
        if required_permissions:
            has_gap = True
            gap_type = GapType.PERMISSION.value
            for perm in required_permissions:
                resources_needed.append(ResourceNeed(
                    resource_type="permission",
                    resource_name=perm,
                    duration_minutes=context.get("permission_duration", 30),
                    reason=f"صلاحية مطلوبة لتنفيذ المهمة",
                ).to_dict())

        # Check for computation needs
        if context.get("computation_intensive"):
            has_gap = True
            gap_type = GapType.COMPUTATION.value
            duration_minutes = 60
            resources_needed.append(ResourceNeed(
                resource_type="computation",
                resource_name="gpu_resources",
                duration_minutes=duration_minutes,
                reason="المهمة تحتاج موارد حوسبة إضافية",
            ).to_dict())

        # Check for tool needs
        required_tools = context.get("required_tools", [])
        available_tools = context.get("available_tools", [])
        missing_tools = [t for t in required_tools if t not in available_tools]
        if missing_tools:
            has_gap = True
            gap_type = GapType.TOOL_ACCESS.value
            for tool in missing_tools:
                resources_needed.append(ResourceNeed(
                    resource_type="tool",
                    resource_name=tool,
                    duration_minutes=duration_minutes,
                    reason=f"أداة مطلوبة غير متاحة: {tool}",
                ).to_dict())

        # Curiosity-driven gap (from instinct)
        if context.get("curiosity_triggered") and not has_gap:
            has_gap = True
            gap_type = GapType.KNOWLEDGE_BASE.value
            priority = GapPriority.LOW.value
            duration_minutes = 10
            reasoning = "الفضول يكشف عن فجوة معرفية — يحتاج توسيع قاعدة المعرفة"
            resources_needed.append(ResourceNeed(
                resource_type="knowledge",
                resource_name="web_search",
                duration_minutes=10,
                reason="لتوسيع نطاق المعرفة",
                optional=True,
            ).to_dict())

        return {
            "has_gap": has_gap,
            "gap_type": gap_type,
            "priority": priority,
            "resources_needed": resources_needed,
            "duration_minutes": duration_minutes,
            "reasoning": reasoning,
            "proposed_plan": proposed_plan,
        }

    def get_status(self) -> dict:
        """حالة مدير طلبات الفجوة."""
        return {
            "enabled": METACOGNITIVE_PLANNING_ENABLED,
            "total_requests": self._request_counter,
            "pending_requests": len(self.get_pending_requests()),
            "requests_by_status": {
                status.value: sum(
                    1 for r in self._requests.values() if r.status == status.value
                )
                for status in GapRequestStatus
            },
        }

    async def shutdown(self):
        """إيقاف المديل — يتوافق مع القانون 5."""
        # Expire all pending requests
        for request in self._requests.values():
            if request.status == GapRequestStatus.PENDING.value:
                request.status = GapRequestStatus.EXPIRED.value
        logger.info("GapRequestManager: Shutdown complete (Law 5 compliant)")
