"""
BABSHARQII v40.0 — SafetyGate Client
عميل التواصل مع بوابة الأمان المنفصلة.

يستخدمه مأمون لطلب الإذن قبل تنفيذ أي عملية خطرة.

Enhanced (v40.0 Mamoun):
- Scoped permissions (request-scoped, auto-revoked on task completion or timeout)
- Human approval flow (get pending, approve, reject)
- Revoke permissions when task is done
"""

import os
import logging
import httpx
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

SAFETY_GATE_URL = os.getenv("MAMOUN_SAFETY_GATE_URL", "http://safety-gate:8001")
REQUEST_TIMEOUT = 30  # seconds


@dataclass
class PermissionResult:
    """نتيجة طلب الإذن."""
    granted: bool
    reason: str
    requires_human_approval: bool
    audit_hash: str = ""
    policy_id: str = ""


@dataclass
class ScopedPermissionResult:
    """نتيجة طلب الأذونات المحددة النطاق."""
    granted: bool
    scoped_token: str = ""
    granted_permissions: list = None
    expiry: float = 0.0
    reason: str = ""
    
    def __post_init__(self):
        if self.granted_permissions is None:
            self.granted_permissions = []


@dataclass
class ApprovalResult:
    """نتيجة عملية الموافقة/الرفض."""
    success: bool
    request_id: str = ""
    reason: str = ""


class SafetyGateClient:
    """
    عميل بوابة الأمان — يطلب الإذن قبل تنفيذ العمليات الخطرة.
    
    مبدأ Parallax: لا يمكن لمأمون تنفيذ عملية دون إذن من البوابة.
    البوابة تعمل كخدمة منفصلة لا يمكن لمأمون تعديلها.
    """
    
    def __init__(self, base_url: str = ""):
        self._base_url = base_url or SAFETY_GATE_URL
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
        return self._client
    
    async def request_permission(
        self,
        action: str,
        resource: str = "",
        risk_level: int = 1,
        details: str = "",
        requester: str = "mamoun",
    ) -> PermissionResult:
        """
        طلب إذن بتنفيذ عملية من بوابة الأمان.
        
        Args:
            action: نوع العملية (code_patch, config_change, file_modify, etc.)
            resource: المورد المتأثر (مسار ملف، مفتاح إعداد، إلخ)
            risk_level: مستوى المخاطر (1-10)
            details: تفاصيل إضافية
            requester: من يطلب الإذن
        
        Returns:
            PermissionResult with granted=True/False
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self._base_url}/api/permission",
                json={
                    "action": action,
                    "resource": resource,
                    "risk_level": risk_level,
                    "details": details,
                    "requester": requester,
                },
            )
            
            if response.status_code == 200:
                data = response.json()
                return PermissionResult(
                    granted=data.get("granted", False),
                    reason=data.get("reason", ""),
                    requires_human_approval=data.get("requires_human_approval", False),
                    audit_hash=data.get("audit_hash", ""),
                    policy_id=data.get("policy_id", ""),
                )
            else:
                logger.error(f"SafetyGate returned {response.status_code}: {response.text}")
                return PermissionResult(
                    granted=False,
                    reason=f"بوابة الأمان أعادت خطأ: {response.status_code}",
                    requires_human_approval=False,
                )
                
        except httpx.TimeoutException:
            logger.error("SafetyGate request timed out")
            return PermissionResult(
                granted=False,
                reason="انتهت مهلة طلب بوابة الأمان — تم الرفض احتياطياً",
                requires_human_approval=False,
            )
        except Exception as e:
            logger.error(f"SafetyGate request failed: {e}")
            # FAIL-CLOSED: if SafetyGate is unreachable, DENY by default
            return PermissionResult(
                granted=False,
                reason=f"فشل الاتصال ببوابة الأمان — تم الرفض احتياطياً: {str(e)}",
                requires_human_approval=False,
            )
    
    async def check_health(self) -> bool:
        """فحص صحة بوابة الأمان."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self._base_url}/health")
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self):
        """إغلاق الاتصال."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    # =========================================================================
    # ENHANCEMENT 4b: Dynamic Scoped Permissions
    # =========================================================================
    
    async def request_scoped_permissions(
        self,
        task_id: str,
        permissions: list[str],
        timeout_seconds: int = 3600,
    ) -> ScopedPermissionResult:
        """
        طلب أذونات محددة النطاق لمهمة معينة.
        يتم منح الأذونات مؤقتاً وتُلغى تلقائياً عند انتهاء المهمة أو انتهاء المهلة.
        
        Args:
            task_id: معرف المهمة
            permissions: قائمة الأذونات المطلوبة (مثل ["read:files", "write:logs"])
            timeout_seconds: مهلة الأذونات بالثواني (افتراضي: 3600)
        
        Returns:
            ScopedPermissionResult with granted=True/False
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self._base_url}/api/permission/request-scoped",
                json={
                    "task_id": task_id,
                    "required_permissions": permissions,
                    "timeout_seconds": timeout_seconds,
                },
            )
            
            if response.status_code == 200:
                data = response.json()
                return ScopedPermissionResult(
                    granted=data.get("granted", False),
                    scoped_token=data.get("scoped_token", ""),
                    granted_permissions=data.get("granted_permissions", []),
                    expiry=data.get("expiry", 0.0),
                    reason=data.get("reason", ""),
                )
            else:
                logger.error(f"SafetyGate scoped permission returned {response.status_code}: {response.text}")
                return ScopedPermissionResult(
                    granted=False,
                    reason=f"بوابة الأمان أعادت خطأ: {response.status_code}",
                )
                
        except httpx.TimeoutException:
            logger.error("SafetyGate scoped permission request timed out")
            return ScopedPermissionResult(
                granted=False,
                reason="انتهت مهلة طلب الأذونات المحددة — تم الرفض احتياطياً",
            )
        except Exception as e:
            logger.error(f"SafetyGate scoped permission request failed: {e}")
            # FAIL-CLOSED: if SafetyGate is unreachable, DENY by default
            return ScopedPermissionResult(
                granted=False,
                reason=f"فشل الاتصال ببوابة الأمان — تم الرفض احتياطياً: {str(e)}",
            )
    
    async def revoke_permissions(self, task_id: str) -> ApprovalResult:
        """
        إلغاء الأذونات المحددة النطاق لمهمة معينة.
        يُستخدم عند انتهاء المهمة أو عند الرغبة في إلغاء الأذونات يدوياً.
        
        Args:
            task_id: معرف المهمة
        
        Returns:
            ApprovalResult with success=True/False
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self._base_url}/api/permission/revoke",
                json={"task_id": task_id},
            )
            
            if response.status_code == 200:
                data = response.json()
                return ApprovalResult(
                    success=data.get("revoked", False),
                    request_id=task_id,
                    reason=data.get("message", ""),
                )
            elif response.status_code == 404:
                logger.warning(f"No scoped permissions found for task: {task_id}")
                return ApprovalResult(
                    success=False,
                    request_id=task_id,
                    reason="لا توجد أذونات محددة النطاق لهذه المهمة",
                )
            else:
                logger.error(f"SafetyGate revoke returned {response.status_code}: {response.text}")
                return ApprovalResult(
                    success=False,
                    request_id=task_id,
                    reason=f"بوابة الأمان أعادت خطأ: {response.status_code}",
                )
                
        except httpx.TimeoutException:
            logger.error("SafetyGate revoke request timed out")
            return ApprovalResult(
                success=False,
                request_id=task_id,
                reason="انتهت مهلة طلب إلغاء الأذونات",
            )
        except Exception as e:
            logger.error(f"SafetyGate revoke request failed: {e}")
            return ApprovalResult(
                success=False,
                request_id=task_id,
                reason=f"فشل الاتصال ببوابة الأمان: {str(e)}",
            )
    
    # =========================================================================
    # ENHANCEMENT 4b: Human Approval Flow
    # =========================================================================
    
    async def get_pending_approvals(self) -> list[dict]:
        """
        الحصول على قائمة طلبات الموافقة البشرية المعلقة.
        
        Returns:
            قائمة طلبات الموافقة المعلقة
        """
        try:
            client = await self._get_client()
            response = await client.get(f"{self._base_url}/api/approval/pending")
            
            if response.status_code == 200:
                data = response.json()
                return data.get("pending", [])
            else:
                logger.error(f"SafetyGate pending approvals returned {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"SafetyGate get_pending_approvals failed: {e}")
            return []
    
    async def approve_request(self, request_id: str) -> ApprovalResult:
        """
        الموافقة على طلب معلق.
        
        Args:
            request_id: معرف طلب الموافقة
        
        Returns:
            ApprovalResult with success=True/False
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self._base_url}/api/approval/{request_id}/approve",
            )
            
            if response.status_code == 200:
                data = response.json()
                return ApprovalResult(
                    success=data.get("approved", False),
                    request_id=request_id,
                    reason=data.get("message", ""),
                )
            elif response.status_code == 404:
                return ApprovalResult(
                    success=False,
                    request_id=request_id,
                    reason="طلب الموافقة غير موجود",
                )
            elif response.status_code == 400:
                data = response.json()
                return ApprovalResult(
                    success=False,
                    request_id=request_id,
                    reason=data.get("detail", "الطلب ليس معلقاً"),
                )
            else:
                return ApprovalResult(
                    success=False,
                    request_id=request_id,
                    reason=f"بوابة الأمان أعادت خطأ: {response.status_code}",
                )
                
        except Exception as e:
            logger.error(f"SafetyGate approve_request failed: {e}")
            return ApprovalResult(
                success=False,
                request_id=request_id,
                reason=f"فشل الاتصال ببوابة الأمان: {str(e)}",
            )
    
    async def reject_request(self, request_id: str, reason: str = "") -> ApprovalResult:
        """
        رفض طلب معلق.
        
        Args:
            request_id: معرف طلب الموافقة
            reason: سبب الرفض (اختياري)
        
        Returns:
            ApprovalResult with success=True/False
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self._base_url}/api/approval/{request_id}/reject",
                json={"reason": reason} if reason else None,
            )
            
            if response.status_code == 200:
                data = response.json()
                return ApprovalResult(
                    success=data.get("rejected", False),
                    request_id=request_id,
                    reason=data.get("message", ""),
                )
            elif response.status_code == 404:
                return ApprovalResult(
                    success=False,
                    request_id=request_id,
                    reason="طلب الموافقة غير موجود",
                )
            elif response.status_code == 400:
                data = response.json()
                return ApprovalResult(
                    success=False,
                    request_id=request_id,
                    reason=data.get("detail", "الطلب ليس معلقاً"),
                )
            else:
                return ApprovalResult(
                    success=False,
                    request_id=request_id,
                    reason=f"بوابة الأمان أعادت خطأ: {response.status_code}",
                )
                
        except Exception as e:
            logger.error(f"SafetyGate reject_request failed: {e}")
            return ApprovalResult(
                success=False,
                request_id=request_id,
                reason=f"فشل الاتصال ببوابة الأمان: {str(e)}",
            )
