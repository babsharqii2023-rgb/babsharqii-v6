"""
BABSHARQII v40.0 — Security Routes
Authentication, API Key management, and Safety routes.
VULN-023 Fix: Auth dependency added for sensitive routes.
"""

import os as _os
import logging
from fastapi import APIRouter, HTTPException, Request, Depends, Cookie
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from mamoun.api.deps import require_auth, auth_manager, safety_guard, _persist_env_var
from mamoun.core.llm_client import reload_llm_client_keys

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Safety Routes
# =============================================================================

@router.get("/safety/violations")
async def get_safety_violations():
    return {"violations": safety_guard.get_violations()}


@router.post("/safety/shutdown", dependencies=[Depends(require_auth)])
async def initiate_shutdown():
    """Initiate shutdown. ALWAYS succeeds per Law 5."""
    result = safety_guard.initiate_shutdown()
    return result


@router.get("/safety/laws")
async def get_laws():
    from mamoun.config import laws
    return {"laws": laws}


# =============================================================================
# Authentication Routes
# =============================================================================

class AuthSetupRequest(BaseModel):
    password: str

class AuthLoginRequest(BaseModel):
    password: str

class AuthChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.get("/auth/status")
async def auth_status():
    """Check if admin has been set up."""
    return {"initialized": auth_manager.is_initialized()}


@router.post("/auth/setup")
async def auth_setup(request: AuthSetupRequest):
    """Initial admin password setup."""
    if auth_manager.is_initialized():
        raise HTTPException(status_code=400, detail="تم إعداد كلمة المرور مسبقاً")
    try:
        token = auth_manager.setup_admin(request.password)
        response = JSONResponse({"success": True, "token": token})
        response.set_cookie(
            key="mamoun_session",
            value=token,
            httponly=True,
            max_age=86400,
            samesite="lax",
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/login")
async def auth_login(request: AuthLoginRequest, req: Request):
    """Login with admin password."""
    client_ip = req.client.host if req.client else "0.0.0.0"
    token = auth_manager.login(request.password, client_ip)
    if not token:
        raise HTTPException(status_code=401, detail="كلمة المرور غير صحيحة أو الحساب مقفل")
    response = JSONResponse({"success": True, "token": token})
    response.set_cookie(
        key="mamoun_session",
        value=token,
        httponly=True,
        max_age=86400,
        samesite="lax",
    )
    return response


@router.post("/auth/change-password")
async def auth_change_password(request: AuthChangePasswordRequest):
    """Change admin password."""
    try:
        success = auth_manager.change_password(request.old_password, request.new_password)
        if not success:
            raise HTTPException(status_code=401, detail="كلمة المرور الحالية غير صحيحة")
        return {"success": True, "message": "تم تغيير كلمة المرور بنجاح"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/verify")
async def auth_verify(mamoun_session: str = Cookie(default="")):
    """Verify session token."""
    if not mamoun_session or not auth_manager.verify_token(mamoun_session):
        raise HTTPException(status_code=401, detail="جلسة غير صالحة")
    return {"valid": True}


@router.post("/auth/logout")
async def auth_logout(mamoun_session: str = Cookie(default="")):
    """Logout and invalidate session."""
    if mamoun_session:
        auth_manager.logout(mamoun_session)
    response = JSONResponse({"success": True})
    response.delete_cookie("mamoun_session")
    return response


# =============================================================================
# Secure API Key Management Routes
# =============================================================================

class ApiKeyRequest(BaseModel):
    provider: str
    key: str


@router.get("/api-keys", dependencies=[Depends(require_auth)])
async def get_api_keys_status():
    """Get masked API key status (never return actual keys)."""
    # FIX: Use correct env var names matching backend/.env (without MAMOUN_ prefix for API keys)
    PROVIDER_ENV_MAP = {
        "glm": "GLM_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }
    keys = {provider: bool(_os.getenv(env_key, "")) for provider, env_key in PROVIDER_ENV_MAP.items()}
    masked = {}
    for provider, env_key in PROVIDER_ENV_MAP.items():
        raw = _os.getenv(env_key, "")
        if raw:
            # VULN-010 Fix: Show only first 3 chars + last 2 chars
            masked[provider] = f"{raw[:3]}{'•' * (len(raw) - 5)}{raw[-2:]}" if len(raw) > 8 else "••••••••"
        else:
            masked[provider] = ""
    return {"keys": masked, "configured": keys}


@router.post("/api-keys", dependencies=[Depends(require_auth)])
async def update_api_key(request: ApiKeyRequest):
    """Update an API key (stored in environment for current session)."""
    # FIX: Correct env var names matching backend/.env
    PROVIDER_ENV_MAP = {
        "glm": "GLM_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }
    if request.provider not in PROVIDER_ENV_MAP:
        raise HTTPException(status_code=400, detail=f"مزود غير معروف: {request.provider}")

    env_key = PROVIDER_ENV_MAP[request.provider]
    # Apply immediately to running process
    _os.environ[env_key] = request.key

    # Also persist to .env file so it survives restarts
    env_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))), ".env")
    _persist_env_var(env_path, env_key, request.key)

    # ✅ انتشار فوري — تحديث كل الأدمغة الخمسة بدون إعادة تشغيل
    reload_llm_client_keys()

    return {"success": True, "provider": request.provider, "message": f"تم حفظ مفتاح {request.provider} وتطبيقه فوراً على كل الأدمغة"}


@router.post("/api-keys/test", dependencies=[Depends(require_auth)])
async def test_api_key(request: ApiKeyRequest):
    """Test an API key by making a minimal request."""
    import httpx

    test_results = {
        "glm": {"url": "https://open.bigmodel.cn/api/paas/v4/chat/completions", "header_key": "Authorization", "prefix": "Bearer "},
        "deepseek": {"url": "https://api.deepseek.com/v1/chat/completions", "header_key": "Authorization", "prefix": "Bearer "},
        "gemini": {"url": f"https://generativelanguage.googleapis.com/v1beta/models?key={request.key}", "header_key": None, "prefix": ""},
        "wolfram": {"url": f"https://api.wolframalpha.com/v2/query?appid={request.key}&input=test&output=json", "header_key": None, "prefix": ""},
    }

    if request.provider not in test_results:
        raise HTTPException(status_code=400, detail="مزود غير معروف")

    config = test_results[request.provider]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if config["header_key"]:
                headers = {config["header_key"]: f"{config['prefix']}{request.key}"}
                resp = await client.get(config["url"], headers=headers)
            else:
                resp = await client.get(config["url"])

            if resp.status_code in [200, 401, 403]:
                if resp.status_code == 200:
                    return {"success": True, "provider": request.provider, "message": "الاتصال ناجح"}
                else:
                    return {"success": False, "provider": request.provider, "message": "المفتاح غير صالح"}
            else:
                return {"success": False, "provider": request.provider, "message": f"خطأ في الاتصال: {resp.status_code}"}
    except Exception as e:
        # VULN-006 Fix: Don't expose internal error details
        return {"success": False, "provider": request.provider, "message": "فشل الاتصال"}
