"""
BABSHARQII v22.0 — Sleep Cycle API
واجهة برمجة دورة النوم — NREM, REM, Recalibration, Dreams, Knowledge Compression

API Endpoints:
  GET  /api/sleep/status   — Sleep system status (phase, cycles, dreams, compression)
  POST /api/sleep/start    — Start a sleep cycle (enter NREM phase)
  POST /api/sleep/wake     — Wake up from sleep
  POST /api/sleep/advance  — Advance sleep phase (NREM → REM → recalibration → NREM)
"""

import time
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
from enum import Enum

from mamoun.api.deps import require_auth

router = APIRouter(prefix="/sleep", tags=["sleep"])


# ═══════════════════════════════════════════════════════════════════════════════
#  مراحل النوم — Sleep Phases
# ═══════════════════════════════════════════════════════════════════════════════

class SleepPhase(str, Enum):
    AWAKE = "awake"             # مستيقظ
    NREM = "nrem"               # نوم عميق — ضغط المعرفة
    REM = "rem"                 # حركة العين السريعة — الأحلام
    RECALIBRATION = "recalibration"  # إعادة معايرة — تقييم وضبط


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج البيانات — Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class AdvancePhaseRequest(BaseModel):
    """نموذج تقديم مرحلة النوم"""
    force: bool = False  # تجاوز الفحوصات


# ═══════════════════════════════════════════════════════════════════════════════
#  حالة النوم في الذاكرة — In-Memory Sleep State
# ═══════════════════════════════════════════════════════════════════════════════

_sleep_state: Dict = {
    "phase": SleepPhase.AWAKE,
    "isSleeping": False,
    "cyclesCompleted": 0,
    "dreamsGenerated": 0,
    "knowledgeCompressed": 0,
    "currentCycleStart": 0.0,
    "lastPhaseChange": 0.0,
    "dreamLog": [],
}

# سجل الأحلام — Dream log entries
_dream_log: List[Dict] = []

# ترتيب المراحل عند التقديم
_PHASE_ORDER = [SleepPhase.NREM, SleepPhase.REM, SleepPhase.RECALIBRATION]


def _advance_to_next_phase() -> Dict:
    """التقدم للمرحلة التالية في دورة النوم"""
    current = _sleep_state["phase"]
    now = time.time()

    if current == SleepPhase.AWAKE:
        return {"error": "لا يمكن التقديم أثناء الاستيقاظ — استخدم /start أولاً"}

    try:
        idx = _PHASE_ORDER.index(current)
    except ValueError:
        idx = -1

    # إذا كان في آخر مرحلة (recalibration) → يكمل الدورة ويعود لـ NREM
    if idx >= len(_PHASE_ORDER) - 1:
        _sleep_state["cyclesCompleted"] += 1
        next_phase = SleepPhase.NREM
    else:
        next_phase = _PHASE_ORDER[idx + 1]

    # معالجة المرحلة الحالية قبل الانتقال
    effects = _process_phase_effects(current)

    _sleep_state["phase"] = next_phase
    _sleep_state["lastPhaseChange"] = now

    return {
        "previous_phase": current.value,
        "new_phase": next_phase.value,
        "effects": effects,
        "cycles_completed": _sleep_state["cyclesCompleted"],
    }


def _process_phase_effects(phase: SleepPhase) -> Dict:
    """معالجة تأثيرات المرحلة — ضغط معرفة، توليد أحلام، إلخ"""
    effects = {}

    if phase == SleepPhase.NREM:
        # ضغط المعرفة — محاكاة ضغط المعلومات
        compressed = len(str(_sleep_state["knowledgeCompressed"])) + 1
        _sleep_state["knowledgeCompressed"] += compressed
        effects["knowledge_compressed"] = compressed
        effects["description"] = "ضغط المعرفة وإعادة تنظيم الذاكرة"

    elif phase == SleepPhase.REM:
        # توليد حلم — محاكاة توليد حلم
        _sleep_state["dreamsGenerated"] += 1
        dream = {
            "id": f"dream_{_sleep_state['dreamsGenerated']}",
            "cycle": _sleep_state["cyclesCompleted"] + 1,
            "timestamp": time.time(),
            "content": f"حلم #{_sleep_state['dreamsGenerated']} — معالجة الإبداع والذكريات",
            "phase": "rem",
        }
        _dream_log.append(dream)
        _sleep_state["dreamLog"] = _dream_log[-20:]  # آخر 20 حلم
        effects["dream_generated"] = dream["id"]
        effects["description"] = "توليد حلم — معالجة الإبداع والذكريات"

    elif phase == SleepPhase.RECALIBRATION:
        # إعادة معايرة — تقييم وضبط النظام
        effects["calibrated"] = True
        effects["description"] = "إعادة معايرة — تقييم وضبط الأنظمة الداخلية"

    return effects


# ═══════════════════════════════════════════════════════════════════════════════
#  Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/status")
async def sleep_status():
    """حالة نظام النوم — Sleep cycle status including phase, dreams, compression"""
    # محاولة الحصول على بيانات إضافية من autonomic_system
    autonomic_status = {}
    try:
        from mamoun.core.autonomic_system import autonomic_system
        autonomic_status = autonomic_system.get_status()
    except Exception:
        pass

    return {
        "version": "v22.0",
        "phase": _sleep_state["phase"].value,
        "isSleeping": _sleep_state["isSleeping"],
        "cyclesCompleted": _sleep_state["cyclesCompleted"],
        "dreamsGenerated": _sleep_state["dreamsGenerated"],
        "knowledgeCompressed": _sleep_state["knowledgeCompressed"],
        "currentCycleStart": _sleep_state["currentCycleStart"],
        "lastPhaseChange": _sleep_state["lastPhaseChange"],
        "dreamLog": _sleep_state["dreamLog"][-10:],
        "autonomic": autonomic_status,
    }


@router.post("/start", dependencies=[Depends(require_auth)])
async def start_sleep():
    """بدء دورة نوم — Enter NREM (deep sleep) phase"""
    if _sleep_state["isSleeping"]:
        raise HTTPException(400, "مأمون نائم بالفعل — استخدم /advance أو /wake")

    now = time.time()
    _sleep_state["isSleeping"] = True
    _sleep_state["phase"] = SleepPhase.NREM
    _sleep_state["currentCycleStart"] = now
    _sleep_state["lastPhaseChange"] = now

    # ضغط أولي عند بدء النوم
    _sleep_state["knowledgeCompressed"] += 1

    return {
        "started": True,
        "phase": _sleep_state["phase"].value,
        "message": "مأمون بدأ دورة النوم — مرحلة NREM (ضغط المعرفة)",
        "timestamp": now,
    }


@router.post("/wake", dependencies=[Depends(require_auth)])
async def wake_up():
    """الاستيقاظ من النوم — Wake up from sleep cycle"""
    if not _sleep_state["isSleeping"]:
        raise HTTPException(400, "مأمون مستيقظ بالفعل")

    was_sleeping = _sleep_state["phase"].value
    cycles = _sleep_state["cyclesCompleted"]
    dreams = _sleep_state["dreamsGenerated"]

    _sleep_state["isSleeping"] = False
    _sleep_state["phase"] = SleepPhase.AWAKE
    _sleep_state["currentCycleStart"] = 0.0

    return {
        "awake": True,
        "previous_phase": was_sleeping,
        "cycles_completed": cycles,
        "dreams_generated": dreams,
        "message": f"مأمون استيقظ — أكمل {cycles} دورة نوم وولّد {dreams} حلم",
        "timestamp": time.time(),
    }


@router.post("/advance", dependencies=[Depends(require_auth)])
async def advance_phase(req: AdvancePhaseRequest = None):
    """التقدم لمرحلة النوم التالية — NREM → REM → recalibration → NREM"""
    if not _sleep_state["isSleeping"]:
        raise HTTPException(400, "مأمون مستيقظ — استخدم /start أولاً")

    result = _advance_to_next_phase()
    if "error" in result:
        raise HTTPException(400, result["error"])

    return {
        "advanced": True,
        **result,
        "timestamp": time.time(),
    }
