"""
BABSHARQII v41.0 — API Keys Management Routes
FIXED: 
  1. Auto-reloads LLMClient keys after saving (no restart needed)
  2. Creates .env file if missing
  3. Uses same .env path as main.py and config.py
  4. Returns instant activation status
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from pathlib import Path
import os
import logging

logger = logging.getLogger("mamoun.api.api_keys")

router = APIRouter(prefix="/v2/api-keys", tags=["API Keys"])

# ─── .env path: same resolution as main.py and config.py ──────────────────
BACKEND_DIR = Path(__file__).parent.parent.parent  # backend/
ENV_PATH = BACKEND_DIR / ".env"


class ApiKeyUpdate(BaseModel):
    brain_id: str
    api_key: str


class ApiKeysBulkUpdate(BaseModel):
    keys: Dict[str, str]  # brain_id -> api_key
    gemini_proxy_url: Optional[str] = None
    github_token: Optional[str] = None
    admin_password: Optional[str] = None


BRAIN_KEY_MAP = {
    "neural": "GLM_API_KEY",
    "causal": "DEEPSEEK_API_KEY",
    "symbolic": "GLM_API_KEY",      # shares with neural
    "bayesian": "GEMINI_API_KEY",
    "worldmodel": "DEEPSEEK_API_KEY", # shares with causal
}

# Friendly names for the response
BRAIN_NAMES = {
    "neural": "العصبي (GLM-5.1)",
    "causal": "السببي (DeepSeek-Reasoner)",
    "symbolic": "الرمزي (GLM-4-Plus)",
    "bayesian": "الاحتمالي (Gemini-2.0-Flash)",
    "worldmodel": "نموذج العالم (DeepSeek-Chat)",
}


def _ensure_env_file():
    """Create .env file if it doesn't exist."""
    if not ENV_PATH.exists():
        ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
        ENV_PATH.write_text("# BABSHARQII v41.0 — Environment Variables\n# Auto-created by API Keys manager\n\n")
        logger.info(f"Created .env file at {ENV_PATH}")


def _read_env_lines() -> list[str]:
    """Read .env file lines, return empty list if not found."""
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            return f.readlines()
    return []


def _write_env_lines(lines: list[str]):
    """Write lines to .env file."""
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)


def _update_env_vars(updates: Dict[str, str]):
    """Update .env file with new key=value pairs, and set os.environ immediately."""
    _ensure_env_file()
    lines = _read_env_lines()

    updated_keys = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        updated = False
        for key, value in updates.items():
            if stripped.startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                updated_keys.add(key)
                updated = True
                break
        if not updated:
            new_lines.append(line)

    # Add new keys that weren't in the file
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}\n")

    _write_env_lines(new_lines)

    # Update current process environment IMMEDIATELY
    for key, value in updates.items():
        os.environ[key] = value

    logger.info(f"Updated .env with keys: {list(updates.keys())}")


def _reload_llm_client():
    """Reload the LLM client so new keys take effect instantly — no restart needed."""
    try:
        from mamoun.core.llm_client import reload_llm_client_keys
        reload_llm_client_keys()
        logger.info("LLMClient keys reloaded successfully — instant activation")
        return True
    except Exception as e:
        logger.warning(f"Could not reload LLMClient: {e}")
        # Try alternative method
        try:
            from mamoun.core.llm_client import get_llm_client
            llm = get_llm_client()
            llm.reload_keys()
            logger.info("LLMClient keys reloaded via get_llm_client()")
            return True
        except Exception as e2:
            logger.warning(f"Alternative reload also failed: {e2}")
            return False


@router.get("")
async def get_api_keys_status():
    """Get status of all API keys (masked for security)."""
    status = {}
    for brain_id, env_var in BRAIN_KEY_MAP.items():
        key = os.getenv(env_var, "")
        status[brain_id] = {
            "has_key": bool(key),
            "key_masked": f"{key[:4]}...{key[-4:]}" if len(key) > 8 else ("***" if key else ""),
            "env_var": env_var,
            "brain_name": BRAIN_NAMES.get(brain_id, brain_id),
        }
    return {
        "brains": status,
        "gemini_proxy": bool(os.getenv("GEMINI_PROXY_URL", "")),
        "github_token": bool(os.getenv("MAMOUN_GITHUB_TOKEN", "")),
        "admin_password_set": bool(os.getenv("MAMOUN_ADMIN_PASSWORD", "")),
        "env_file": str(ENV_PATH),
        "env_file_exists": ENV_PATH.exists(),
    }


@router.post("")
async def update_api_keys(data: ApiKeysBulkUpdate):
    """Update API keys — saves to .env AND reloads LLMClient instantly (no restart needed)."""
    # Build update map: brain_id → env_var → api_key
    updates = {}
    activated_brains = []
    for brain_id, api_key in data.keys.items():
        if brain_id in BRAIN_KEY_MAP:
            env_var = BRAIN_KEY_MAP[brain_id]
            updates[env_var] = api_key
            if api_key:
                activated_brains.append(brain_id)

    if data.gemini_proxy_url:
        updates["GEMINI_PROXY_URL"] = data.gemini_proxy_url
    if data.github_token:
        updates["MAMOUN_GITHUB_TOKEN"] = data.github_token
    if data.admin_password:
        updates["MAMOUN_ADMIN_PASSWORD"] = data.admin_password

    if not updates:
        return {"success": True, "updated_keys": [], "activated_brains": [], "message": "لا توجد مفاتيح جديدة للحفظ"}

    # 1) Save to .env file
    _update_env_vars(updates)

    # 2) Reload LLMClient instantly — NO RESTART NEEDED
    reload_ok = _reload_llm_client()

    # 3) Check which brains are now active
    active_brains = []
    for brain_id, env_var in BRAIN_KEY_MAP.items():
        if os.getenv(env_var, ""):
            active_brains.append({
                "id": brain_id,
                "name": BRAIN_NAMES.get(brain_id, brain_id),
                "status": "active",
            })

    brain_names_str = "، ".join(BRAIN_NAMES.get(b, b) for b in activated_brains)

    if reload_ok:
        message = f"✅ تم حفظ وتفعيل المفاتيح فوراً — {len(activated_brains)} أدمغة نشطة: {brain_names_str}"
    else:
        message = f"⚠️ تم الحفظ — أعد تشغيل الخادم لتفعيل: {brain_names_str}"

    return {
        "success": True,
        "updated_keys": list(updates.keys()),
        "activated_brains": activated_brains,
        "active_brains": active_brains,
        "total_active": len(active_brains),
        "reload_ok": reload_ok,
        "message": message,
    }


@router.post("/test/{brain_id}")
async def test_api_key(brain_id: str):
    """Test if an API key works by making a simple API call to the provider."""
    if brain_id not in BRAIN_KEY_MAP:
        raise HTTPException(404, f"Brain {brain_id} not found")

    env_var = BRAIN_KEY_MAP[brain_id]
    key = os.getenv(env_var, "")

    if not key:
        return {"brain_id": brain_id, "status": "missing_key", "message": "لا يوجد مفتاح"}

    try:
        import httpx
        if "GLM" in env_var:
            resp = httpx.post("https://open.bigmodel.cn/api/paas/v4/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": "glm-4-flash", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
                timeout=10)
        elif "DEEPSEEK" in env_var:
            resp = httpx.post("https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
                timeout=10)
        elif "GEMINI" in env_var:
            proxy = os.getenv("GEMINI_PROXY_URL", "")
            if proxy:
                resp = httpx.post(f"{proxy}/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": "gemini-2.0-flash", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
                    timeout=10)
            else:
                resp = httpx.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}", timeout=10)
        else:
            return {"brain_id": brain_id, "status": "unknown", "message": "مزود غير معروف"}

        if resp.status_code in (200, 201):
            return {"brain_id": brain_id, "status": "valid", "message": "✅ المفتاح صالح ويعمل"}
        elif resp.status_code == 401:
            return {"brain_id": brain_id, "status": "invalid", "message": "❌ المفتاح غير صالح"}
        else:
            return {"brain_id": brain_id, "status": "error", "message": f"⚠️ خطأ: HTTP {resp.status_code}"}
    except Exception as e:
        return {"brain_id": brain_id, "status": "error", "message": f"⚠️ خطأ في الاتصال: {str(e)[:80]}"}


@router.post("/reload")
async def reload_keys():
    """Force reload all API keys into the LLMClient."""
    ok = _reload_llm_client()
    
    # Count active brains
    active = sum(1 for env_var in BRAIN_KEY_MAP.values() if os.getenv(env_var, ""))
    
    if ok:
        return {"success": True, "active_brains": active, "message": f"✅ تم إعادة تحميل المفاتيح — {active}/5 أدمغة نشطة"}
    else:
        return {"success": False, "active_brains": active, "message": "⚠️ لم يتم العثور على LLMClient — حاول إعادة التشغيل"}
