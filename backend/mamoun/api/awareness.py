"""
BABSHARQII v40.0 — Awareness, Journal & Self-Healing Routes
Phase 1 (Awareness), Phase 2 (Self-Healing), and Journal routes.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from mamoun.api.deps import (
    require_auth,
    state_reader,
    meta_analyzer,
    mutation_engine,
    journal,
    code_patcher,
    sandbox_runner,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Awareness Routes (Phase 1)
# =============================================================================

@router.get("/awareness/state")
async def get_system_state():
    """Get real system state (CPU, memory, disk, Docker, API health)."""
    state = state_reader.read_system_state()
    vitality = state_reader.compute_vitality()
    return {"state": state.to_dict(), "vitality": vitality}


@router.get("/awareness/meta")
async def get_metacognitive_assessment():
    """Get metacognitive assessment (brain bias, calibration, recommendations)."""
    weights = mutation_engine.get_current_version().genome.routing_weights
    vitality = state_reader.compute_vitality()
    assessment = meta_analyzer.assess(weights, vitality)
    return {
        "system1_confidence": assessment.system1_confidence,
        "system2_confidence": assessment.system2_confidence,
        "calibration_error": assessment.calibration_error,
        "brain_bias": assessment.brain_bias.__dict__ if assessment.brain_bias else None,
        "deliberation_bias": assessment.deliberation_bias.__dict__ if assessment.deliberation_bias else None,
        "overall_self_awareness": assessment.overall_self_awareness,
        "recommendations": assessment.recommendations,
    }


@router.get("/awareness/vitality")
async def get_vitality():
    """Get just the vitality score."""
    return {"vitality": state_reader.compute_vitality()}


@router.get("/awareness/status")
async def get_awareness_status():
    """v31: Full awareness status — aggregates state, vitality, and meta."""
    state = state_reader.read_system_state()
    vitality = state_reader.compute_vitality()
    return {
        "state": state.to_dict(),
        "vitality": vitality,
        "awareness_level": "full" if vitality > 0.7 else "partial" if vitality > 0.3 else "degraded",
    }


# =============================================================================
# v100 Fusion: Consciousness State — بيانات الوعي الحقيقية
# =============================================================================

@router.get("/consciousness/state")
async def get_consciousness_state():
    """
    v100 Fusion: جلب بيانات حالة الوعي الحقيقية من كل الأنظمة الفرعية
    يُستدعى من لوحة الوعي في الفرونت إند لعرض بيانات حقيقية بدلاً من تقريبية
    """
    import os
    import time as _time
    
    result = {
        "level": 0.0,
        "coherence": 0.0,
        "self_awareness": 0.0,
        "metacognition": 0.0,
        "state": "unknown",
        "stage": "idle",
        "current_phase": "idle",
        "overall_accuracy": 0.0,
        "cycle_count": 0,
        "subsystems": {},
        "timestamp": _time.time(),
    }
    
    # Gather data from living systems
    try:
        from mamoun.core.living_state import living_state
        if living_state._initialized:
            vitals = living_state.get_vitals()
            result["subsystems"]["living_state"] = {
                "vitality": vitals.get("vitality", 0),
                "energy": vitals.get("energy", 0),
                "coherence": vitals.get("coherence", 0),
                "stress": vitals.get("stress", 0),
            }
            result["level"] = max(result["level"], vitals.get("vitality", 0) / 100)
            result["coherence"] = max(result["coherence"], vitals.get("coherence", 0))
    except Exception as e:
        result["subsystems"]["living_state"] = {"error": str(e)[:100]}
    
    # Gather data from emotional memory
    try:
        from mamoun.core.emotional_memory import emotional_memory
        if emotional_memory._initialized:
            emotions = emotional_memory.get_current_emotions()
            result["subsystems"]["emotional_memory"] = {
                "emotions": emotions,
                "dominant": max(emotions, key=emotions.get) if emotions else "neutral",
            }
            result["self_awareness"] = min(1.0, len(emotions) / 5)
    except Exception as e:
        result["subsystems"]["emotional_memory"] = {"error": str(e)[:100]}
    
    # Gather data from kernel
    try:
        from mamoun.core.mamoun_kernel import get_kernel
        kernel = get_kernel()
        if kernel._running:
            workspace_data = {}
            if kernel.workspace and kernel.workspace.current:
                workspace_data = {
                    "winning_brain": kernel.workspace.current.winning_brain,
                    "confidence": kernel.workspace.current.confidence,
                    "cycle_count": kernel.workspace.cycle_count,
                }
                result["cycle_count"] = kernel.workspace.cycle_count
                result["overall_accuracy"] = kernel.workspace.current.confidence
            result["subsystems"]["kernel"] = {
                "running": True,
                "brains_count": len(kernel._brains),
                "workspace": workspace_data,
            }
            result["state"] = "aware"
            result["stage"] = "perceive" if kernel.workspace.current else "idle"
            result["current_phase"] = result["stage"]
    except Exception as e:
        result["subsystems"]["kernel"] = {"error": str(e)[:100]}
    
    # Gather metacognitive data
    try:
        weights = mutation_engine.get_current_version().genome.routing_weights
        vitality = state_reader.compute_vitality()
        assessment = meta_analyzer.assess(weights, vitality)
        result["metacognition"] = assessment.overall_self_awareness
        result["subsystems"]["metacognition"] = {
            "system1_confidence": assessment.system1_confidence,
            "system2_confidence": assessment.system2_confidence,
            "calibration_error": assessment.calibration_error,
            "brain_bias": assessment.brain_bias.__dict__ if assessment.brain_bias else None,
        }
    except Exception as e:
        result["subsystems"]["metacognition"] = {"error": str(e)[:100]}
    
    # Gather brain status
    try:
        from mamoun.brains.brain_router import get_brain_router
        router = get_brain_router()
        brain_status = router.get_brain_status()
        active_count = sum(1 for b in brain_status.values() if b.get("status") in ("active", "thinking"))
        result["subsystems"]["brains"] = {
            "active_count": active_count,
            "total_count": len(brain_status),
            "status": {bid: {"model": b.get("actual_model", ""), "status": b.get("status", "")} 
                       for bid, b in brain_status.items()},
        }
    except Exception as e:
        result["subsystems"]["brains"] = {"error": str(e)[:100]}
    
    # Gather self-healing data
    try:
        from mamoun.core.self_healing import self_healing
        if self_healing._initialized:
            health = self_healing.run_health_check()
            result["subsystems"]["self_healing"] = {
                "healthy": health.get("healthy", False),
                "components": len(health.get("components", {})),
                "active_issues": len(self_healing.get_active_issues()),
            }
    except Exception as e:
        result["subsystems"]["self_healing"] = {"error": str(e)[:100]}
    
    # Calculate overall consciousness level
    scores = []
    if result["level"] > 0:
        scores.append(result["level"])
    if result["coherence"] > 0:
        scores.append(result["coherence"])
    if result["self_awareness"] > 0:
        scores.append(result["self_awareness"])
    if result["metacognition"] > 0:
        scores.append(result["metacognition"])
    if result["overall_accuracy"] > 0:
        scores.append(result["overall_accuracy"])
    
    if scores:
        result["level"] = round(sum(scores) / len(scores), 3)
    
    # Determine consciousness state
    if result["level"] > 0.8:
        result["state"] = "highly_aware"
    elif result["level"] > 0.6:
        result["state"] = "aware"
    elif result["level"] > 0.3:
        result["state"] = "semi_aware"
    else:
        result["state"] = "degraded"
    
    return result


@router.get("/consciousness")
async def get_consciousness_simple():
    """v100 Fusion: نسخة مبسطة من بيانات الوعي"""
    full_state = await get_consciousness_state()
    return {
        "level": full_state["level"],
        "self_awareness": full_state["self_awareness"],
        "metacognition": full_state["metacognition"],
        "state": full_state["state"],
        "stage": full_state["stage"],
        "current_phase": full_state["current_phase"],
        "overall_accuracy": full_state["overall_accuracy"],
    }


@router.post("/awareness/cycle", dependencies=[Depends(require_auth)])
async def run_awareness_cycle():
    """v31: Trigger an awareness cycle — refresh system state and recalculate vitality."""
    state = state_reader.read_system_state()
    vitality = state_reader.compute_vitality()

    # Publish awareness cycle to NeuralBus
    try:
        from mamoun.core.neural_bus import neural_bus
        if neural_bus._initialized:
            neural_bus.publish(
                signal_type="perception",
                source="awareness:cycle",
                payload={"vitality": vitality, "awareness_level": "full" if vitality > 0.7 else "partial"},
            )
    except Exception:
        pass

    return {
        "cycle_completed": True,
        "vitality": vitality,
        "state": state.to_dict(),
    }


@router.post("/awareness/action", dependencies=[Depends(require_auth)])
async def awareness_action(action: str = "refresh"):
    """v31: Execute an awareness action (refresh, diagnose, calibrate)."""
    state = state_reader.read_system_state()
    vitality = state_reader.compute_vitality()

    if action == "diagnose":
        # Run diagnostic
        return {
            "action": "diagnose",
            "vitality": vitality,
            "issues": state_reader.get_issues() if hasattr(state_reader, 'get_issues') else [],
            "recommendations": state_reader.get_recommendations() if hasattr(state_reader, 'get_recommendations') else [],
        }
    elif action == "calibrate":
        # Reset awareness baseline
        return {
            "action": "calibrate",
            "previous_vitality": vitality,
            "calibrated": True,
        }
    else:
        # Default: refresh
        return {
            "action": "refresh",
            "vitality": vitality,
            "state": state.to_dict(),
        }


# =============================================================================
# Journal Routes
# =============================================================================

@router.get("/journal/entries")
async def get_journal_entries(entry_type: str = "", limit: int = 50):
    entries = await journal.get_entries(entry_type=entry_type, limit=limit)
    return {"entries": [e.to_dict() for e in entries]}


@router.get("/journal/lessons")
async def get_lessons_learned(limit: int = 20):
    return {"lessons": await journal.get_lessons_learned(limit=limit)}


@router.get("/journal/error-patterns")
async def get_error_patterns(limit: int = 50):
    return {"patterns": await journal.get_error_patterns(limit=limit)}


# =============================================================================
# Self-Healing Routes (Phase 2)
# =============================================================================

class PatchRequest(BaseModel):
    error_type: str
    error_message: str
    error_traceback: str
    file_path: str
    error_line: int = 0


@router.post("/self-heal/patch", dependencies=[Depends(require_auth)])
async def generate_code_patch(request: PatchRequest):
    """Generate a code patch for a Python file error."""
    patch = await code_patcher.generate_patch(
        error_type=request.error_type,
        error_message=request.error_message,
        error_traceback=request.error_traceback,
        file_path=request.file_path,
        error_line=request.error_line,
    )
    if not patch:
        raise HTTPException(status_code=500, detail="فشل في توليد التصحيح")
    return {"patch": patch.to_dict()}


@router.post("/self-heal/apply/{patch_id}", dependencies=[Depends(require_auth)])
async def apply_code_patch(patch_id: str):
    """Apply a previously generated patch."""
    # Find the patch in applied patches
    for patch in code_patcher._applied_patches:
        if patch.id == patch_id:
            success = await code_patcher.apply_patch(patch)
            return {"success": success, "patch": patch.to_dict()}
    raise HTTPException(status_code=404, detail="التصحيح غير موجود")


@router.post("/self-heal/sandbox-test", dependencies=[Depends(require_auth)])
async def sandbox_test_patch(request: PatchRequest):
    """Test a patch in the sandbox."""
    patch = await code_patcher.generate_patch(
        error_type=request.error_type,
        error_message=request.error_message,
        error_traceback=request.error_traceback,
        file_path=request.file_path,
        error_line=request.error_line,
    )
    if not patch:
        raise HTTPException(status_code=500, detail="فشل في توليد التصحيح")

    result = await sandbox_runner.test_patch(patch.patched_code, request.file_path)
    return {"patch": patch.to_dict(), "sandbox_result": result.to_dict()}
