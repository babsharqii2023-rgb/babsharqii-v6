"""
BABSHARQII v38.0 — Brain Control Matrix
مصفوفة التحكم بالأدمغة — تحكم كامل بكل دماغ

الطبقة 4 من آلية التحكم الشاملة:
- تفعيل/إيقاف كل دماغ على حدة
- تعديل temperature و weight
- إرسال استعلام لدماغ محدد
- عرض استجابة كل دماغ
- مراقبة tokens وتكلفة
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("mamoun.api.brain_control")

router = APIRouter(prefix="/v2/brains", tags=["brain_control"])


class BrainQueryRequest(BaseModel):
    query: str
    brain_id: Optional[str] = None  # إذا None → كل الأدمغة


class BrainConfigRequest(BaseModel):
    temperature: Optional[float] = None
    weight: Optional[float] = None


@router.get("/matrix")
async def brain_matrix():
    """
    مصفوفة الأدمغة الكاملة — كل بيانات كل دماغ
    """
    from mamoun.core.mamoun_kernel import get_kernel
    kernel = get_kernel()

    if not kernel._brains:
        raise HTTPException(status_code=503, detail="لم يتم تسجيل أي أدمغة")

    matrix = {}
    for brain_id, brain in kernel._brains.items():
        state = brain.state
        matrix[brain_id] = {
            "id": state.id,
            "name_ar": state.name_ar if hasattr(state, 'name_ar') else state.id,
            "name_en": state.name_en if hasattr(state, 'name_en') else state.id,
            "model": state.model,
            "provider": state.provider if hasattr(state, 'provider') else "unknown",
            "status": state.status,
            "confidence": state.confidence,
            "temperature": state.temperature if hasattr(state, 'temperature') else 0.7,
            "weight": state.weight if hasattr(state, 'weight') else 0.2,
            "specialty": brain.get_specialty() if hasattr(brain, 'get_specialty') else "",
            "total_interactions": state.total_interactions if hasattr(state, 'total_interactions') else 0,
            "successful_interactions": state.successful_interactions if hasattr(state, 'successful_interactions') else 0,
        }

    # حالة Workspace
    workspace_status = kernel.workspace.get_status()

    # إحصائيات LLM
    try:
        from mamoun.core.llm_client import get_llm_client
        llm = get_llm_client()
        llm_stats = llm.get_stats()
    except:
        llm_stats = {}

    return {
        "brains": matrix,
        "total": len(matrix),
        "active": sum(1 for b in matrix.values() if b["status"] == "active"),
        "workspace": workspace_status,
        "llm_stats": llm_stats,
    }


@router.post("/{brain_id}/query")
async def query_brain(brain_id: str, req: BrainQueryRequest):
    """
    إرسال استعلام لدماغ محدد — يُرجع الاستجابة من ذلك الدماغ فقط
    """
    from mamoun.core.mamoun_kernel import get_kernel
    kernel = get_kernel()

    brain = kernel._brains.get(brain_id)
    if not brain:
        raise HTTPException(status_code=404, detail=f"دماغ غير موجود: {brain_id}")

    if brain.state.status != "active":
        raise HTTPException(status_code=400, detail=f"الدماغ {brain_id} غير مُفعّل — فعّله أولاً")

    try:
        result = await brain.think(query=req.query)
        return {
            "brain_id": brain_id,
            "model": brain.state.model,
            "response": result.get("response", ""),
            "confidence": result.get("confidence", 0),
            "reasoning": result.get("reasoning", ""),
            "stance": result.get("stance", "neutral"),
            "latency_ms": result.get("latency_ms", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في الدماغ {brain_id}: {e}")


@router.post("/{brain_id}/config")
async def configure_brain(brain_id: str, req: BrainConfigRequest):
    """
    تعديل إعدادات دماغ — temperature و weight
    """
    from mamoun.core.mamoun_kernel import get_kernel
    kernel = get_kernel()

    brain = kernel._brains.get(brain_id)
    if not brain:
        raise HTTPException(status_code=404, detail=f"دماغ غير موجود: {brain_id}")

    changes = {}

    if req.temperature is not None:
        if not 0 <= req.temperature <= 2:
            raise HTTPException(status_code=400, detail="درجة الحرارة يجب أن تكون بين 0 و 2")
        old_temp = brain.state.temperature if hasattr(brain.state, 'temperature') else 0.7
        brain.state.temperature = req.temperature
        changes["temperature"] = {"from": old_temp, "to": req.temperature}

    if req.weight is not None:
        if not 0 <= req.weight <= 1:
            raise HTTPException(status_code=400, detail="الوزن يجب أن يكون بين 0 و 1")
        old_weight = brain.state.weight if hasattr(brain.state, 'weight') else 0.2
        brain.state.weight = req.weight
        changes["weight"] = {"from": old_weight, "to": req.weight}

    # إرسال إشارة NeuralBus
    try:
        from mamoun.core.neural_bus import neural_bus
        neural_bus.publish({
            "type": "vital_change",
            "source": "brain_control",
            "data": {"brain_id": brain_id, "changes": changes},
            "priority": 1,
        })
    except:
        pass

    return {
        "success": True,
        "brain_id": brain_id,
        "changes": changes,
        "current": {
            "temperature": brain.state.temperature if hasattr(brain.state, 'temperature') else None,
            "weight": brain.state.weight if hasattr(brain.state, 'weight') else None,
        },
    }


@router.post("/{brain_id}/activate")
async def activate_brain(brain_id: str):
    """تفعيل دماغ"""
    from mamoun.core.mamoun_kernel import get_kernel
    kernel = get_kernel()

    brain = kernel._brains.get(brain_id)
    if not brain:
        raise HTTPException(status_code=404, detail=f"دماغ غير موجود: {brain_id}")

    brain.activate()
    return {"success": True, "brain_id": brain_id, "status": "active"}


@router.post("/{brain_id}/deactivate")
async def deactivate_brain(brain_id: str):
    """إيقاف دماغ"""
    from mamoun.core.mamoun_kernel import get_kernel
    kernel = get_kernel()

    brain = kernel._brains.get(brain_id)
    if not brain:
        raise HTTPException(status_code=404, detail=f"دماغ غير موجود: {brain_id}")

    brain.deactivate()
    return {"success": True, "brain_id": brain_id, "status": "inactive"}


@router.post("/query-all")
async def query_all_brains(req: BrainQueryRequest):
    """
    إرسال استعلام لكل الأدمغة — يعود ب استجابة كل دماغ
    """
    import asyncio
    from mamoun.core.mamoun_kernel import get_kernel
    kernel = get_kernel()

    if not kernel._brains:
        raise HTTPException(status_code=503, detail="لم يتم تسجيل أي أدمغة")

    results = {}
    tasks = []

    for brain_id, brain in kernel._brains.items():
        if brain.state.status != "active":
            results[brain_id] = {"status": "inactive", "brain_id": brain_id}
            continue

        async def _query(bid, b, q):
            try:
                r = await b.think(query=q)
                results[bid] = {
                    "status": "ok",
                    "brain_id": bid,
                    "model": b.state.model,
                    "response": r.get("response", "")[:500],
                    "confidence": r.get("confidence", 0),
                    "stance": r.get("stance", "neutral"),
                }
            except Exception as e:
                results[bid] = {"status": "error", "brain_id": bid, "error": str(e)[:200]}

        tasks.append(_query(brain_id, brain, req.query))

    await asyncio.gather(*tasks)

    # إيجاد الفائز
    winner = max(
        ((bid, r) for bid, r in results.items() if r.get("status") == "ok"),
        key=lambda x: x[1].get("confidence", 0),
        default=(None, {}),
    )

    return {
        "query": req.query,
        "brain_responses": results,
        "total": len(results),
        "winner_brain": winner[0],
        "winner_confidence": winner[1].get("confidence", 0),
    }


@router.get("/{brain_id}/stats")
async def brain_stats(brain_id: str):
    """إحصائيات دماغ مفصّلة"""
    from mamoun.core.mamoun_kernel import get_kernel
    kernel = get_kernel()

    brain = kernel._brains.get(brain_id)
    if not brain:
        raise HTTPException(status_code=404, detail=f"دماغ غير موجود: {brain_id}")

    state = brain.state
    total = state.total_interactions if hasattr(state, 'total_interactions') else 0
    success = state.successful_interactions if hasattr(state, 'successful_interactions') else 0

    return {
        "brain_id": brain_id,
        "model": state.model,
        "status": state.status,
        "confidence": state.confidence,
        "total_interactions": total,
        "successful_interactions": success,
        "success_rate": success / max(1, total),
        "temperature": state.temperature if hasattr(state, 'temperature') else 0.7,
        "weight": state.weight if hasattr(state, 'weight') else 0.2,
    }
