"""
BABSHARQII v50.0 — External Project Controller API
نقاط الاتصال لمتحكم المشاريع الخارجية
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/external-project", tags=["External Projects"])


class CloneRequest(BaseModel):
    url: str
    branch: str = "main"
    name: Optional[str] = None


class FileWriteRequest(BaseModel):
    project_id: str
    file_path: str
    content: str


class CommandRequest(BaseModel):
    project_id: str
    command: str


class LLMBditRequest(BaseModel):
    project_id: str
    file_path: str
    instruction: str


class PRRequest(BaseModel):
    project_id: str
    title: str
    description: str = ""


@router.post("/clone")
async def clone_repo(request: CloneRequest):
    """استنساخ مستودع"""
    try:
        from mamoun.core.external_project_controller import get_external_project_controller
        controller = get_external_project_controller()
        result = await controller.clone_repo(request.url, request.branch)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/read-file")
async def read_file(project_id: str, file_path: str):
    """قراءة ملف من مشروع خارجي"""
    try:
        from mamoun.core.external_project_controller import get_external_project_controller
        controller = get_external_project_controller()
        content = await controller.read_file(project_id, file_path)
        return {"project_id": project_id, "file_path": file_path, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/write-file")
async def write_file(request: FileWriteRequest):
    """كتابة ملف في مشروع خارجي"""
    try:
        from mamoun.core.external_project_controller import get_external_project_controller
        controller = get_external_project_controller()
        result = await controller.write_file(request.project_id, request.file_path, request.content)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-command")
async def run_command(request: CommandRequest):
    """تنفيذ أمر في مشروع خارجي"""
    try:
        from mamoun.core.external_project_controller import get_external_project_controller
        controller = get_external_project_controller()
        result = await controller.run_command(request.project_id, request.command)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/build")
async def build_project(project_id: str):
    """بناء مشروع خارجي"""
    try:
        from mamoun.core.external_project_controller import get_external_project_controller
        controller = get_external_project_controller()
        result = await controller.build_project(project_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_project(project_id: str):
    """اختبار مشروع خارجي"""
    try:
        from mamoun.core.external_project_controller import get_external_project_controller
        controller = get_external_project_controller()
        result = await controller.test_project(project_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deploy")
async def deploy_project(project_id: str, target: str = "preview"):
    """نشر مشروع خارجي"""
    try:
        from mamoun.core.external_project_controller import get_external_project_controller
        controller = get_external_project_controller()
        result = await controller.deploy_project(project_id, target)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/llm-edit")
async def llm_edit_file(request: LLMBditRequest):
    """تعديل ملف عبر LLM"""
    try:
        from mamoun.core.external_project_controller import get_external_project_controller
        controller = get_external_project_controller()
        result = await controller.llm_edit_file(request.project_id, request.file_path, request.instruction)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pull-request")
async def create_pull_request(request: PRRequest):
    """إنشاء طلب سحب"""
    try:
        from mamoun.core.external_project_controller import get_external_project_controller
        controller = get_external_project_controller()
        result = await controller.create_pull_request(request.project_id, request.title, request.description)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_projects():
    """قائمة المشاريع الخارجية"""
    try:
        from mamoun.core.external_project_controller import get_external_project_controller
        controller = get_external_project_controller()
        return await controller.list_projects()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_project_status(project_id: str):
    """حالة مشروع خارجي"""
    try:
        from mamoun.core.external_project_controller import get_external_project_controller
        controller = get_external_project_controller()
        return await controller.get_project_status(project_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/controller-status")
async def get_controller_status():
    """حالة المتحكم"""
    try:
        from mamoun.core.external_project_controller import get_external_project_controller
        controller = get_external_project_controller()
        return controller.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollback")
async def rollback(project_id: str, snapshot_id: str):
    """التراجع عن تغيير"""
    try:
        from mamoun.core.external_project_controller import get_external_project_controller
        controller = get_external_project_controller()
        return await controller.rollback(project_id, snapshot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
