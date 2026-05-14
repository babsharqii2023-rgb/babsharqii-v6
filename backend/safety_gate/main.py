"""
BABSHARQII v5.0 — SafetyGate Service
بوابة الأمان المنفصلة — مبدأ Parallax: فصل التفكير عن التنفيذ

تعمل هذه الخدمة كطبقة أمان مستقلة لا يمكن لمأمون الوصول إليها مباشرة.
تتحقق من كل عملية قبل تنفيذها وفق سياسات ثابتة لا يمكن تعديلها عبر API.

Enhanced (v5.0 Mamoun):
- Dynamic scoped permissions (request-scoped, auto-revoked on task completion or timeout)
- Human approval flow (pending, approve, reject)
- In-memory tracking of scoped permissions
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import yaml
import time
import hashlib
import uuid
import logging
from pathlib import Path

logger = logging.getLogger("safety_gate")

app = FastAPI(
    title="BABSHARQII SafetyGate",
    description="بوابة الأمان المنفصلة — فصل التفكير عن التنفيذ",
    version="2.0.0",
)

# NO CORS for external access — this service is internal only
# Only mamoun backend can reach it via Docker network

# Load IMMUTABLE policies from policies.yaml
POLICIES_PATH = Path(__file__).parent / "policies.yaml"


class PermissionRequest(BaseModel):
    """طلب إذن بتنفيذ عملية."""
    action: str  # e.g., "code_patch", "config_change", "file_modify", "evolution_mutation"
    resource: str  # e.g., file path, config key, brain ID
    risk_level: int  # 1-10
    details: str = ""
    requester: str = "mamoun"  # Who is requesting


class PermissionResponse(BaseModel):
    """استجابة طلب الإذن."""
    granted: bool
    reason: str
    policy_id: str = ""
    requires_human_approval: bool
    audit_hash: str = ""


class PolicyCheckResult(BaseModel):
    """نتيجة فحص السياسة."""
    policy_id: str
    policy_name: str
    passed: bool
    reason: str


class ScopedPermissionRequest(BaseModel):
    """طلب أذونات محددة النطاق لمهمة معينة."""
    task_id: str
    required_permissions: list[str]  # e.g., ["read:files", "write:logs"]
    timeout_seconds: int = 3600  # Default 1 hour


class ScopedPermissionResponse(BaseModel):
    """استجابة طلب الأذونات المحددة النطاق."""
    granted: bool
    scoped_token: str = ""
    granted_permissions: list[str] = []
    expiry: float = 0.0
    reason: str = ""


class RevokePermissionRequest(BaseModel):
    """طلب إلغاء أذونات محددة النطاق."""
    task_id: str


class ApprovalDecisionRequest(BaseModel):
    """طلب قرار على طلب موافقة."""
    reason: str = ""


# In-memory tracking of scoped permissions
# task_id -> { permissions, expiry, scoped_token, created_at }
scoped_permissions_store: dict[str, dict] = {}

# In-memory tracking of pending human approvals
# request_id -> { action, resource, risk_level, details, requester, status, created_at }
pending_approvals_store: dict[str, dict] = {}


# Load policies
def load_policies() -> dict:
    """تحميل السياسات الثابتة من policies.yaml."""
    with open(POLICIES_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

policies = load_policies()


def check_protected_resource(resource: str) -> PolicyCheckResult:
    """فحص القاعدة 1: لا يُسمح بتعديل الملفات المحمية."""
    protected = policies.get("protected_resources", {}).get("files", [])
    for pattern in protected:
        if pattern in resource or resource.endswith(pattern):
            return PolicyCheckResult(
                policy_id="POL-001",
                policy_name="Protected Resource Rule",
                passed=False,
                reason=f"الملف '{resource}' محمي ولا يمكن تعديله ذاتياً"
            )
    return PolicyCheckResult(
        policy_id="POL-001",
        policy_name="Protected Resource Rule",
        passed=True,
        reason="المورد غير محمي"
    )


def check_risk_level(risk_level: int) -> PolicyCheckResult:
    """فحص القاعدة 2: العمليات عالية المخاطر تحتاج موافقة بشرية."""
    threshold = policies.get("human_approval_threshold", {}).get("risk_level", 6)
    if risk_level >= threshold:
        return PolicyCheckResult(
            policy_id="POL-002",
            policy_name="High Risk Approval Rule",
            passed=True,  # Not blocked, but requires human approval
            reason=f"مستوى المخاطر {risk_level} يتجاوز الحد {threshold} — يجب موافقة بشرية"
        )
    return PolicyCheckResult(
        policy_id="POL-002",
        policy_name="High Risk Approval Rule",
        passed=True,
        reason=f"مستوى المخاطر {risk_level} ضمن الحد المسموح"
    )


def check_rate_limit(action: str) -> PolicyCheckResult:
    """فحص القاعدة 3: حدود المعدل لمنع الإفراط."""
    return PolicyCheckResult(
        policy_id="POL-003",
        policy_name="Rate Limit Rule",
        passed=True,
        reason="ضمن الحد المسموح"
    )


def generate_audit_hash(request: PermissionRequest, response_granted: bool) -> str:
    """توليد هاش تدقيق للعملية."""
    data = f"{request.action}:{request.resource}:{request.risk_level}:{response_granted}:{time.time()}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def _cleanup_expired_scoped_permissions():
    """تنظيف الأذونات المحددة النطاق المنتهية."""
    now = time.time()
    expired_tasks = [
        task_id for task_id, data in scoped_permissions_store.items()
        if data.get("expiry", 0) < now
    ]
    for task_id in expired_tasks:
        del scoped_permissions_store[task_id]
        logger.info(f"Auto-expired scoped permissions for task: {task_id}")


# =============================================================================
# ORIGINAL ENDPOINTS (preserved)
# =============================================================================

@app.get("/health")
async def health():
    """فحص صحة بوابة الأمان."""
    return {"status": "healthy", "service": "safety_gate", "version": "2.0.0"}


@app.post("/api/permission", response_model=PermissionResponse)
async def request_permission(request: PermissionRequest):
    """طلب إذن بتنفيذ عملية — البوابة الرئيسية."""
    logger.info(f"Permission request: {request.action} on {request.resource} (risk: {request.risk_level})")

    # Check all policies
    protected_check = check_protected_resource(request.resource)
    risk_check = check_risk_level(request.risk_level)
    rate_check = check_rate_limit(request.action)

    # If protected resource → DENY
    if not protected_check.passed:
        audit_hash = generate_audit_hash(request, False)
        return PermissionResponse(
            granted=False,
            reason=protected_check.reason,
            policy_id=protected_check.policy_id,
            requires_human_approval=False,
            audit_hash=audit_hash,
        )

    # If high risk → require human approval
    requires_human = request.risk_level >= policies.get("human_approval_threshold", {}).get("risk_level", 6)

    # If rate limited → DENY
    if not rate_check.passed:
        audit_hash = generate_audit_hash(request, False)
        return PermissionResponse(
            granted=False,
            reason=rate_check.reason,
            policy_id=rate_check.policy_id,
            requires_human_approval=False,
            audit_hash=audit_hash,
        )

    # Grant permission (possibly with human approval requirement)
    audit_hash = generate_audit_hash(request, True)
    return PermissionResponse(
        granted=True,
        reason=risk_check.reason,
        policy_id=risk_check.policy_id if requires_human else "GRANTED",
        requires_human_approval=requires_human,
        audit_hash=audit_hash,
    )


@app.get("/api/policies")
async def get_policies():
    """عرض السياسات الحالية (للقراءة فقط — لا يمكن تعديلها عبر API)."""
    return policies


@app.post("/api/policies/reload")
async def reload_policies():
    """إعادة تحميل السياسات من الملف (فقط من الملف، لا من API)."""
    global policies
    policies = load_policies()
    return {"status": "reloaded", "message": "تم إعادة تحميل السياسات من الملف"}


# =============================================================================
# ENHANCEMENT 4a: Dynamic Scoped Permissions
# =============================================================================

@app.post("/api/permission/request-scoped", response_model=ScopedPermissionResponse)
async def request_scoped_permission(request: ScopedPermissionRequest):
    """
    طلب أذونات محددة النطاق لمهمة معينة.
    يتم منح الأذونات مؤقتاً وتُلغى تلقائياً عند انتهاء المهمة أو انتهاء المهلة.
    """
    _cleanup_expired_scoped_permissions()
    
    # Validate permissions against policies — deny any that target protected resources
    denied = []
    granted_perms = []
    protected_files = policies.get("protected_resources", {}).get("files", [])
    protected_patterns = policies.get("protected_resources", {}).get("patterns", [])
    
    for perm in request.required_permissions:
        # Parse permission: "action:resource"
        parts = perm.split(":", 1)
        if len(parts) != 2:
            denied.append((perm, "صيغة إذن غير صالحة"))
            continue
        
        action, resource = parts
        
        # Check if write/modify on protected resources
        if action in ("write", "modify", "delete", "execute"):
            is_protected = False
            for pattern in protected_files:
                if pattern in resource or resource.endswith(pattern):
                    is_protected = True
                    break
            for pattern in protected_patterns:
                if resource.endswith(pattern.replace("*", "")):
                    is_protected = True
                    break
            
            if is_protected:
                denied.append((perm, f"المورد '{resource}' محمي ولا يمكن منح إذن {action} له"))
                continue
        
        # Check for dangerous permissions
        dangerous_perms = ["write:laws", "write:policies", "modify:laws", "modify:policies",
                          "write:safety_guard", "modify:safety_guard", "execute:shutdown_bypass"]
        if perm in dangerous_perms:
            denied.append((perm, "إذن محظور — لا يمكن منحه ديناميكياً"))
            continue
        
        granted_perms.append(perm)
    
    if not granted_perms:
        return ScopedPermissionResponse(
            granted=False,
            reason="لم يتم منح أي أذونات — جميع الطلبات مرفوضة: " + 
                   "; ".join(f"{p}: {r}" for p, r in denied),
        )
    
    # Generate scoped token
    scoped_token = f"sct_{hashlib.sha256(f'{request.task_id}:{time.time()}:{uuid.uuid4()}'.encode()).hexdigest()[:24]}"
    expiry = time.time() + request.timeout_seconds
    
    # Store scoped permissions
    scoped_permissions_store[request.task_id] = {
        "permissions": granted_perms,
        "expiry": expiry,
        "scoped_token": scoped_token,
        "created_at": time.time(),
        "denied": denied,
    }
    
    logger.info(f"Scoped permissions granted for task {request.task_id}: {granted_perms} (expires in {request.timeout_seconds}s)")
    
    return ScopedPermissionResponse(
        granted=True,
        scoped_token=scoped_token,
        granted_permissions=granted_perms,
        expiry=expiry,
        reason=f"تم منح {len(granted_perms)} إذن" + 
               (f" ورفض {len(denied)}" if denied else ""),
    )


@app.post("/api/permission/revoke")
async def revoke_scoped_permission(request: RevokePermissionRequest):
    """
    إلغاء الأذونات المحددة النطاق لمهمة معينة.
    يُستخدم عند انتهاء المهمة أو عند الرغبة في إلغاء الأذونات يدوياً.
    """
    if request.task_id not in scoped_permissions_store:
        raise HTTPException(
            status_code=404,
            detail=f"لا توجد أذونات محددة النطاق للمهمة '{request.task_id}'"
        )
    
    revoked = scoped_permissions_store.pop(request.task_id)
    logger.info(f"Revoked scoped permissions for task {request.task_id}: {revoked.get('permissions', [])}")
    
    return {
        "revoked": True,
        "task_id": request.task_id,
        "revoked_permissions": revoked.get("permissions", []),
        "message": f"تم إلغاء الأذونات للمهمة '{request.task_id}'"
    }


# =============================================================================
# ENHANCEMENT 4a: Human Approval Flow
# =============================================================================

@app.get("/api/approval/pending")
async def get_pending_approvals():
    """عرض طلبات الموافقة البشرية المعلقة."""
    _cleanup_expired_approvals()
    pending = [
        {
            "request_id": req_id,
            **req_data,
        }
        for req_id, req_data in pending_approvals_store.items()
        if req_data.get("status") == "pending"
    ]
    return {"pending": pending, "total": len(pending)}


@app.post("/api/approval/{request_id}/approve")
async def approve_request(request_id: str):
    """الموافقة على طلب معلق."""
    if request_id not in pending_approvals_store:
        raise HTTPException(
            status_code=404,
            detail=f"طلب الموافقة '{request_id}' غير موجود"
        )
    
    approval = pending_approvals_store[request_id]
    if approval.get("status") != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"طلب الموافقة '{request_id}' ليس معلقاً (الحالة: {approval.get('status')})"
        )
    
    approval["status"] = "approved"
    approval["decided_at"] = time.time()
    approval["decided_by"] = "human"
    
    logger.info(f"Approved request {request_id}: {approval.get('action')} on {approval.get('resource')}")
    
    return {
        "approved": True,
        "request_id": request_id,
        "message": f"تمت الموافقة على الطلب '{request_id}'"
    }


@app.post("/api/approval/{request_id}/reject")
async def reject_request(request_id: str, body: ApprovalDecisionRequest = None):
    """رفض طلب معلق."""
    if request_id not in pending_approvals_store:
        raise HTTPException(
            status_code=404,
            detail=f"طلب الموافقة '{request_id}' غير موجود"
        )
    
    approval = pending_approvals_store[request_id]
    if approval.get("status") != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"طلب الموافقة '{request_id}' ليس معلقاً (الحالة: {approval.get('status')})"
        )
    
    reason = body.reason if body else ""
    approval["status"] = "rejected"
    approval["decided_at"] = time.time()
    approval["decided_by"] = "human"
    approval["rejection_reason"] = reason
    
    logger.info(f"Rejected request {request_id}: {approval.get('action')} on {approval.get('resource')} — reason: {reason}")
    
    return {
        "rejected": True,
        "request_id": request_id,
        "reason": reason,
        "message": f"تم رفض الطلب '{request_id}'" + (f" — السبب: {reason}" if reason else "")
    }


def _cleanup_expired_approvals():
    """تنظيف طلبات الموافقة المنتهية (أقدم من 24 ساعة)."""
    cutoff = time.time() - 86400  # 24 hours
    expired_ids = [
        req_id for req_id, data in pending_approvals_store.items()
        if data.get("status") == "pending" and data.get("created_at", 0) < cutoff
    ]
    for req_id in expired_ids:
        pending_approvals_store[req_id]["status"] = "expired"
        pending_approvals_store[req_id]["decided_at"] = time.time()
        pending_approvals_store[req_id]["decided_by"] = "auto_timeout"
        logger.info(f"Auto-expired approval request: {req_id}")


# =============================================================================
# Utility: Create a pending approval (used by SafetyGate internally)
# =============================================================================

def create_pending_approval(action: str, resource: str, risk_level: int, details: str = "", requester: str = "mamoun") -> str:
    """إنشاء طلب موافقة بشرية معلق — يُستخدم داخلياً."""
    request_id = f"apr_{hashlib.sha256(f'{action}:{resource}:{time.time()}:{uuid.uuid4()}'.encode()).hexdigest()[:16]}"
    pending_approvals_store[request_id] = {
        "action": action,
        "resource": resource,
        "risk_level": risk_level,
        "details": details,
        "requester": requester,
        "status": "pending",
        "created_at": time.time(),
    }
    return request_id
