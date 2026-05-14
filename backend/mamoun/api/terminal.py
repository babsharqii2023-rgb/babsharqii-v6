"""Terminal API — Full Agentic Terminal endpoints.
v18.1 Fix: Added require_auth to all execution endpoints (SEC-002)."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from mamoun.api.deps import require_auth
from mamoun.terminal import AgenticTerminal

# M-5: Rate limiting for auth-sensitive endpoints
from fastapi import Request
from mamoun.api.rate_limiter import limiter

router = APIRouter(prefix="/terminal", tags=["terminal"])

_terminal: Optional[AgenticTerminal] = None


def get_terminal() -> AgenticTerminal:
    global _terminal
    if _terminal is None:
        _terminal = AgenticTerminal()
    return _terminal


class ExecuteRequest(BaseModel):
    command: str
    timeout: Optional[int] = None
    approval_id: Optional[str] = None


class GitCommitRequest(BaseModel):
    message: str
    approval_id: Optional[str] = None


class GitPushRequest(BaseModel):
    remote: str = "origin"
    branch: str = "main"
    approval_id: Optional[str] = None


@router.get("/status")
async def terminal_status():
    """GET status — no auth required (read-only)."""
    return get_terminal().get_status()


@router.post("/execute", dependencies=[Depends(require_auth)])
async def execute_command(req: ExecuteRequest):
    """Execute a terminal command — requires auth (SEC-002 fix)."""
    terminal = get_terminal()
    return await terminal.execute(
        command=req.command,
        timeout=req.timeout,
        approval_id=req.approval_id,
    )


@router.get("/git/status")
async def git_status():
    """GET git status — no auth required (read-only)."""
    return await get_terminal().git_status()


@router.post("/git/commit", dependencies=[Depends(require_auth)])
async def git_commit(req: GitCommitRequest):
    """Git commit — requires auth."""
    return await get_terminal().git_commit(req.message, req.approval_id)


@router.post("/git/push", dependencies=[Depends(require_auth)])
async def git_push(req: GitPushRequest):
    """Git push — requires auth."""
    return await get_terminal().git_push(req.remote, req.branch, req.approval_id)


@router.post("/npm/build", dependencies=[Depends(require_auth)])
async def npm_build():
    """NPM build — requires auth."""
    return await get_terminal().npm_build()


@router.post("/npm/test", dependencies=[Depends(require_auth)])
async def npm_test():
    """NPM test — requires auth."""
    return await get_terminal().npm_test()


@router.get("/approvals/pending", dependencies=[Depends(require_auth)])
@limiter.limit("20/minute")
async def pending_approvals(request: Request):
    """GET pending approvals — requires auth (M-1 fix)."""
    pending = get_terminal().get_pending_approvals()
    return {"approvals": pending, "requests": pending}


@router.post("/approvals/{approval_id}/approve", dependencies=[Depends(require_auth)])
async def approve_command(approval_id: str):
    """Approve a command — requires auth."""
    success = get_terminal().approve_command(approval_id)
    if not success:
        raise HTTPException(404, "Approval not found")
    return {"approved": True}


@router.post("/approvals/{approval_id}/reject", dependencies=[Depends(require_auth)])
async def reject_command(approval_id: str):
    """Reject a command — requires auth."""
    success = get_terminal().reject_command(approval_id)
    if not success:
        raise HTTPException(404, "Approval not found")
    return {"rejected": True}
