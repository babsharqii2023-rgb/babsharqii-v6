"""
BABSHARQII v40.0 — Admin Routes
Backup, Monitoring, GDPR/Data Management, Chat Proxy, Database Status, and Agent Manifest routes.
"""

import os as _os
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from mamoun.api.deps import require_auth, _get_data_manager, _get_backup_manager, _persist_env_var

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Database Status Routes
# =============================================================================

@router.get("/db-status")
async def get_database_status():
    """Get connection status for all databases (checks real connections)."""
    from mamoun.core.triple_memory import triple_memory
    status = triple_memory.get_status()
    return {
        "sqlite": {
            "connected": status["sqlite_fallback"]["connected"],
            "purpose": status["sqlite_fallback"]["purpose"],
            "location": status["sqlite_fallback"]["location"],
        },
        "neo4j": {
            "connected": status["neo4j"]["connected"],
            "purpose": status["neo4j"]["purpose"],
            "location": "bolt://localhost:7687" if status["neo4j"]["connected"] else "غير مُعدّ",
            "setup_required": not status["neo4j"]["connected"],
            "setup_guide": "أضف MAMOUN_NEO4J_URI و MAMOUN_NEO4J_PASSWORD إلى ملف .env",
        },
        "postgresql": {
            "connected": status["postgresql"]["connected"],
            "purpose": status["postgresql"]["purpose"],
            "location": "localhost:5432/mamoun" if status["postgresql"]["connected"] else "غير مُعدّ",
            "setup_required": not status["postgresql"]["connected"],
            "setup_guide": "أضف MAMOUN_POSTGRES_HOST و MAMOUN_POSTGRES_PASSWORD إلى ملف .env",
        },
        "chromadb": {
            "connected": status["chromadb"]["connected"],
            "purpose": status["chromadb"]["purpose"],
            "location": "localhost:8000" if status["chromadb"]["connected"] else "غير مُعدّ",
            "setup_required": not status["chromadb"]["connected"],
            "setup_guide": "أضف MAMOUN_CHROMA_HOST و MAMOUN_CHROMA_PORT إلى ملف .env",
        },
    }


# =============================================================================
# GDPR / Data Management Routes
# =============================================================================

class DataExportRequest(BaseModel):
    user_id: str

class DataDeleteRequest(BaseModel):
    user_id: str
    confirm: bool = False


@router.get("/user/data-summary", dependencies=[Depends(require_auth)])
async def get_user_data_summary(user_id: str = "default"):
    """Get a summary of stored data for a user (GDPR Art. 15)."""
    dm = _get_data_manager()
    return await dm.get_data_summary(user_id)


@router.get("/user/data-export", dependencies=[Depends(require_auth)])
async def export_user_data(user_id: str = "default"):
    """Export all user data in machine-readable format (GDPR Art. 20)."""
    dm = _get_data_manager()
    data = await dm.export_user_data(user_id)
    return data


@router.delete("/user/data", dependencies=[Depends(require_auth)])
async def delete_user_data(request: DataDeleteRequest):
    """Delete all user data (GDPR Art. 17 - Right to Erasure)."""
    dm = _get_data_manager()
    result = await dm.delete_user_data(request.user_id, request.confirm)
    return result


# =============================================================================
# Chat Proxy Route (forwards to LLM via backend)
# =============================================================================

class ChatRequest(BaseModel):
    message: str
    model: str = "glm-4-plus"
    history: list = []


@router.post("/chat", dependencies=[Depends(require_auth)])
async def chat_proxy(request: ChatRequest):
    """Chat via LLMClient directly — v30.1 fix: no proxy loop.

    v30.1 Fix: كان يرسل لـ frontend اللي يعمل rewrite لـ backend = حلقة دائرية.
    الآن يستخدم LLMClient مباشرة للحديث مع نموذج LLM.
    """
    from mamoun.core.llm_client import get_llm_client, LLMMessage

    try:
        llm = get_llm_client()

        # Build conversation messages
        messages = []
        for h in (request.history or []):
            role = h.get("role", "user") if isinstance(h, dict) else "user"
            content = h.get("content", str(h)) if isinstance(h, dict) else str(h)
            messages.append(LLMMessage(role=role, content=content))

        messages.append(LLMMessage(role="user", content=request.message))

        response = await llm.chat(
            messages=messages,
            model=request.model,
        )

        return {
            "content": response.text,
            "model": response.model,
            "provider": response.provider,
            "tokensUsed": response.tokens_used,
            "latency_ms": response.latency_ms,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في LLM: {str(e)}")


# =============================================================================
# Backup Routes (Fix #9)
# =============================================================================

class BackupCreateRequest(BaseModel):
    encrypt: bool = False
    upload_s3: bool = False
    include_postgres: bool = True
    include_neo4j: bool = True
    include_chromadb: bool = True


class BackupRestoreRequest(BaseModel):
    backup_name: str
    verify_first: bool = True


@router.post("/backup/create", dependencies=[Depends(require_auth)])
async def create_backup(request: BackupCreateRequest):
    """Create a backup of all system data."""
    try:
        bm = _get_backup_manager()
        info = await bm.create_backup(
            include_postgres=request.include_postgres,
            include_neo4j=request.include_neo4j,
            include_chromadb=request.include_chromadb,
            encrypt=request.encrypt,
            upload_s3=request.upload_s3,
        )
        return {"success": True, "backup": info.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل إنشاء النسخة الاحتياطية: {str(e)}")


@router.get("/backup/list", dependencies=[Depends(require_auth)])
async def list_backups():
    """List all available backups."""
    bm = _get_backup_manager()
    backups = await bm.list_backups()
    return {"backups": [b.to_dict() for b in backups], "total": len(backups)}


@router.post("/backup/restore", dependencies=[Depends(require_auth)])
async def restore_backup(request: BackupRestoreRequest):
    """Restore from a specific backup."""
    bm = _get_backup_manager()
    result = await bm.restore_backup(request.backup_name, request.verify_first)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "فشل الاستعادة"))
    return result


# =============================================================================
# Monitoring Routes (Fix #12)
# =============================================================================

from mamoun.core.monitoring import monitoring_manager


@router.get("/monitoring/metrics")
async def get_monitoring_metrics():
    """Get all system metrics."""
    return monitoring_manager.get_all_metrics()


@router.get("/monitoring/health")
async def get_aggregated_health():
    """Get aggregated health check."""
    return monitoring_manager.get_health_aggregation()


@router.get("/monitoring/alerts")
async def get_active_alerts():
    """Get active monitoring alerts."""
    return monitoring_manager.get_alerts()


# =============================================================================
# Agent Manifest Route (Enhancement 5b)
# =============================================================================

@router.get("/agent/manifest")
async def get_agent_manifest():
    """Get the agent manifest (Agent Spec / OASF compliance)."""
    manifest_path = Path(__file__).parent.parent.parent.parent / "agent_manifest.json"
    if manifest_path.exists():
        import json
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="agent_manifest.json not found")


# NOTE: System Update routes have been moved to api/update.py (the canonical module).
# This avoids duplicate /system/update/* endpoints.
