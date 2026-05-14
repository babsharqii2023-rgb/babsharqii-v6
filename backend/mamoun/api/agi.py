"""
BABSHARQII v40.0 — AGI Capability Routes
Privacy Guard, System2, Fluid Reasoner, Common Sense, Hallucination Detection,
Intent Drift, Skill Discovery, Swarm Intelligence, Theory of Mind, Continual Learning,
Cultural Alignment, AGI Overview, and AGI Bridge routes.
"""

import os as _os
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from mamoun.api.deps import require_auth, _is_agi_module_enabled, _persist_env_var

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Module-Level Singletons — lazy, cached instances to persist state across requests
# =============================================================================

_privacy_guard = None
def _get_privacy_guard():
    global _privacy_guard
    if _privacy_guard is None:
        from mamoun.agi.privacy_guard import PrivacyGuard
        _privacy_guard = PrivacyGuard()
    return _privacy_guard

_system2_reasoner = None
def _get_system2_reasoner():
    global _system2_reasoner
    if _system2_reasoner is None:
        from mamoun.core.system2_reasoner import System2Reasoner
        _system2_reasoner = System2Reasoner()
    return _system2_reasoner

_fluid_reasoner = None
def _get_fluid_reasoner():
    global _fluid_reasoner
    if _fluid_reasoner is None:
        from mamoun.agi.fluid_reasoner import FluidReasoner
        _fluid_reasoner = FluidReasoner()
    return _fluid_reasoner

_common_sense_filter = None
def _get_common_sense_filter():
    global _common_sense_filter
    if _common_sense_filter is None:
        from mamoun.agi.common_sense import CommonSenseFilter
        _common_sense_filter = CommonSenseFilter()
    return _common_sense_filter

_hallucination_detector = None
def _get_hallucination_detector():
    global _hallucination_detector
    if _hallucination_detector is None:
        from mamoun.agi.hallucination_detector import HallucinationDetector
        _hallucination_detector = HallucinationDetector()
    return _hallucination_detector

_intent_drift_detector = None
def _get_intent_drift_detector():
    global _intent_drift_detector
    if _intent_drift_detector is None:
        from mamoun.agi.intent_drift import IntentDriftDetector
        _intent_drift_detector = IntentDriftDetector()
    return _intent_drift_detector

_continual_learning_engine = None
def _get_continual_learning_engine():
    global _continual_learning_engine
    if _continual_learning_engine is None:
        from mamoun.reasoning.continual_learning import ContinualLearningEngine
        _continual_learning_engine = ContinualLearningEngine()
    return _continual_learning_engine

_skill_discovery = None
def _get_skill_discovery():
    global _skill_discovery
    if _skill_discovery is None:
        from mamoun.agi.skill_discovery import SkillDiscovery
        _skill_discovery = SkillDiscovery()
    return _skill_discovery

_theory_of_mind = None
def _get_theory_of_mind():
    global _theory_of_mind
    if _theory_of_mind is None:
        from mamoun.agi.theory_of_mind import TheoryOfMind
        _theory_of_mind = TheoryOfMind()
    return _theory_of_mind


# =============================================================================
# AGI Request Models
# =============================================================================

class AGIProcessRequest(BaseModel):
    """طلب معالجة AGI موحد."""
    query: str
    context: dict = {}
    brain_responses: list[dict] = []


class AGICapabilityToggleRequest(BaseModel):
    """طلب تفعيل/تعطيل قدرة AGI."""
    capability_key: str
    enabled: bool = True

class System2ReasonRequest(BaseModel):
    """طلب استدلال System 2."""
    message: str
    context: dict = {}

class FluidReasonRequest(BaseModel):
    """طلب استدلال سائب."""
    message: str
    context: dict = {}

class PrivacyScanRequest(BaseModel):
    """طلب فحص خصوصية."""
    data: str

class HallucinationDetectRequest(BaseModel):
    """طلب كشف هلوسة."""
    text: str
    context: dict = {}

class CommonSenseFilterRequest(BaseModel):
    """طلب تصفية منطق عام."""
    text: str

class IntentDriftTrackRequest(BaseModel):
    """طلب تتبع انحراف نية."""
    goal: str
    actions: list = []

class ContinualLearnRequest(BaseModel):
    """طلب تعلم مستمر."""
    interaction: dict = {}

class SkillDiscoverRequest(BaseModel):
    """طلب اكتشاف مهارة."""
    error: dict = {}
    context: dict = {}

class TheoryOfMindModelRequest(BaseModel):
    """طلب بناء نموذج عقلي."""
    agent_id: str
    observations: list = []

class TheoryOfMindPredictRequest(BaseModel):
    """طلب تنبؤ."""
    agent_id: str
    context: dict = {}


# =============================================================================
# 1. Privacy Guard Routes
# =============================================================================

@router.get("/privacy/status")
async def get_privacy_status():
    """حالة حارس الخصوصية."""
    if not _is_agi_module_enabled("MAMOUN_PRIVACY_GUARD_ENABLED"):
        return {
            "enabled": False,
            "message": "وحدة حارس الخصوصية غير مفعّلة. قم بتعيين MAMOUN_PRIVACY_GUARD_ENABLED=true لتفعيلها.",
            "encryption_status": "غير متاح",
            "audit_count": 0,
        }
    try:
        guard = _get_privacy_guard()
        status = guard.get_status()
        return {
            "enabled": True,
            "encryption_status": status.get("encryption_status", "غير معروف"),
            "audit_count": status.get("audit_count", 0),
            "details": status,
        }
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة حارس الخصوصية غير مثبتة")
    except Exception as e:
        return {
            "enabled": True,
            "error": f"فشل في قراءة حالة حارس الخصوصية: {str(e)}",
            "encryption_status": "غير معروف",
            "audit_count": 0,
        }


@router.get("/privacy/audit-log", dependencies=[Depends(require_auth)])
async def get_privacy_audit_log(limit: int = 50):
    """سجل تدقيق الخصوصية."""
    if not _is_agi_module_enabled("MAMOUN_PRIVACY_GUARD_ENABLED"):
        raise HTTPException(status_code=403, detail="وحدة حارس الخصوصية غير مفعّلة. قم بتعيين MAMOUN_PRIVACY_GUARD_ENABLED=true لتفعيلها.")
    try:
        guard = _get_privacy_guard()
        log = guard.get_audit_log(limit=limit)
        return {"audit_log": log, "count": len(log)}
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة حارس الخصوصية غير مثبتة")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل في جلب سجل التدقيق: {str(e)}")


@router.post("/privacy/scan", dependencies=[Depends(require_auth)])
async def scan_data_privacy(request: PrivacyScanRequest):
    """فحص بيانات للكشف عن معلومات حساسة."""
    if not _is_agi_module_enabled("MAMOUN_PRIVACY_GUARD_ENABLED"):
        raise HTTPException(status_code=403, detail="وحدة حارس الخصوصية غير مفعّلة. قم بتعيين MAMOUN_PRIVACY_GUARD_ENABLED=true لتفعيلها.")
    try:
        guard = _get_privacy_guard()
        result = guard.scan_data(request.data)
        return {"scan_result": result}
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة حارس الخصوصية غير مثبتة")
    except Exception as e:
        return {
            "scan_result": {"sensitive_found": False, "error": f"فشل في فحص البيانات: {str(e)}"},
        }


# =============================================================================
# 2. System 2 Reasoner Routes
# =============================================================================

@router.post("/system2/reason", dependencies=[Depends(require_auth)])
async def system2_reason(request: System2ReasonRequest):
    """استدلال مع System 2 — مسار مزدوج سريع/عميق."""
    if not _is_agi_module_enabled("MAMOUN_SYSTEM2_ENABLED"):
        return {
            "enabled": False,
            "message": "وحدة System 2 غير مفعّلة. قم بتعيين MAMOUN_SYSTEM2_ENABLED=true لتفعيلها.",
            "result": None,
        }
    try:
        reasoner = _get_system2_reasoner()
        result = await reasoner.reason(topic=request.message, context=request.context)
        return {"enabled": True, "result": result.to_dict() if hasattr(result, 'to_dict') else str(result)}
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة System 2 غير مثبتة")
    except Exception as e:
        return {
            "enabled": True,
            "error": f"فشل في استدلال System 2: {str(e)}",
            "result": None,
        }


@router.get("/system2/stats", dependencies=[Depends(require_auth)])
async def get_system2_stats():
    """إحصائيات مسار System 2."""
    if not _is_agi_module_enabled("MAMOUN_SYSTEM2_ENABLED"):
        return {
            "enabled": False,
            "message": "وحدة System 2 غير مفعّلة. قم بتعيين MAMOUN_SYSTEM2_ENABLED=true لتفعيلها.",
        }
    try:
        reasoner = _get_system2_reasoner()
        stats = reasoner.get_stats() if hasattr(reasoner, 'get_stats') else {}
        return {"enabled": True, "stats": stats}
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة System 2 غير مثبتة")
    except Exception as e:
        return {"enabled": True, "error": f"فشل في جلب إحصائيات System 2: {str(e)}"}


# =============================================================================
# 3. Fluid Reasoner Routes
# =============================================================================

@router.post("/fluid-reasoner/think", dependencies=[Depends(require_auth)])
async def fluid_reasoner_think(request: FluidReasonRequest):
    """تفكير الاستدلال السائب."""
    if not _is_agi_module_enabled("MAMOUN_FLUID_REASONER_ENABLED"):
        return {
            "enabled": False,
            "message": "وحدة الاستدلال السائب غير مفعّلة. قم بتعيين MAMOUN_FLUID_REASONER_ENABLED=true لتفعيلها.",
            "result": None,
        }
    try:
        reasoner = _get_fluid_reasoner()
        result = reasoner.think(request.message, context=request.context)
        return {"enabled": True, "result": result}
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة الاستدلال السائب غير مثبتة")
    except Exception as e:
        return {
            "enabled": True,
            "error": f"فشل في تفكير الاستدلال السائب: {str(e)}",
            "result": None,
        }


@router.get("/fluid-reasoner/stats", dependencies=[Depends(require_auth)])
async def get_fluid_reasoner_stats():
    """إحصائيات الاستدلال السائب."""
    if not _is_agi_module_enabled("MAMOUN_FLUID_REASONER_ENABLED"):
        return {
            "enabled": False,
            "message": "وحدة الاستدلال السائب غير مفعّلة. قم بتعيين MAMOUN_FLUID_REASONER_ENABLED=true لتفعيلها.",
        }
    try:
        reasoner = _get_fluid_reasoner()
        stats = reasoner.get_stats()
        return {"enabled": True, "stats": stats}
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة الاستدلال السائب غير مثبتة")
    except Exception as e:
        return {"enabled": True, "error": f"فشل في جلب إحصائيات الاستدلال السائب: {str(e)}"}


# =============================================================================
# 4. Common Sense Routes
# =============================================================================

@router.post("/common-sense/filter", dependencies=[Depends(require_auth)])
async def common_sense_filter(request: CommonSenseFilterRequest):
    """تصفية المنطق العام — كشف الادعاءات غير المنطقية."""
    if not _is_agi_module_enabled("MAMOUN_COMMON_SENSE_ENABLED"):
        return {
            "enabled": False,
            "message": "وحدة المنطق العام غير مفعّلة. قم بتعيين MAMOUN_COMMON_SENSE_ENABLED=true لتفعيلها.",
            "filtered": None,
        }
    try:
        cs_filter = _get_common_sense_filter()
        result = cs_filter.filter(request.text)
        return {"enabled": True, "filtered": result}
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة المنطق العام غير مثبتة")
    except Exception as e:
        return {
            "enabled": True,
            "error": f"فشل في تصفية المنطق العام: {str(e)}",
            "filtered": None,
        }


@router.get("/common-sense/rules", dependencies=[Depends(require_auth)])
async def get_common_sense_rules():
    """قواعد المنطق العام الحالية."""
    if not _is_agi_module_enabled("MAMOUN_COMMON_SENSE_ENABLED"):
        return {
            "enabled": False,
            "message": "وحدة المنطق العام غير مفعّلة. قم بتعيين MAMOUN_COMMON_SENSE_ENABLED=true لتفعيلها.",
            "rules": [],
        }
    try:
        cs_filter = _get_common_sense_filter()
        rules = cs_filter.get_rules()
        return {"enabled": True, "rules": rules}
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة المنطق العام غير مثبتة")
    except Exception as e:
        return {"enabled": True, "error": f"فشل في جلب قواعد المنطق العام: {str(e)}", "rules": []}


# =============================================================================
# 5. Hallucination Detection Routes
# =============================================================================

@router.post("/hallucination/detect", dependencies=[Depends(require_auth)])
async def detect_hallucination(request: HallucinationDetectRequest):
    """كشف الهلوسة في النص."""
    if not _is_agi_module_enabled("MAMOUN_HALLUCINATION_DETECTION_ENABLED"):
        return {
            "enabled": False,
            "message": "وحدة كشف الهلوسة غير مفعّلة. قم بتعيين MAMOUN_HALLUCINATION_DETECTION_ENABLED=true لتفعيلها.",
            "detection": None,
        }
    try:
        detector = _get_hallucination_detector()
        result = detector.detect(request.text, context=request.context)
        return {"enabled": True, "detection": result}
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة كشف الهلوسة غير مثبتة")
    except Exception as e:
        return {
            "enabled": True,
            "error": f"فشل في كشف الهلوسة: {str(e)}",
            "detection": None,
        }


@router.get("/hallucination/stats", dependencies=[Depends(require_auth)])
async def get_hallucination_stats():
    """إحصائيات كشف الهلوسة."""
    if not _is_agi_module_enabled("MAMOUN_HALLUCINATION_DETECTION_ENABLED"):
        return {
            "enabled": False,
            "message": "وحدة كشف الهلوسة غير مفعّلة. قم بتعيين MAMOUN_HALLUCINATION_DETECTION_ENABLED=true لتفعيلها.",
        }
    try:
        detector = _get_hallucination_detector()
        stats = detector.get_stats()
        return {"enabled": True, "stats": stats}
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة كشف الهلوسة غير مثبتة")
    except Exception as e:
        return {"enabled": True, "error": f"فشل في جلب إحصائيات كشف الهلوسة: {str(e)}"}


# =============================================================================
# 6. Intent Drift Detection Routes
# =============================================================================

@router.post("/intent-drift/track", dependencies=[Depends(require_auth)])
async def track_intent_drift(request: IntentDriftTrackRequest):
    """تتبع انحراف النية."""
    if not _is_agi_module_enabled("MAMOUN_INTENT_DRIFT_ENABLED"):
        return {
            "enabled": False,
            "message": "وحدة تتبع انحراف النية غير مفعّلة. قم بتعيين MAMOUN_INTENT_DRIFT_ENABLED=true لتفعيلها.",
            "drift": None,
        }
    try:
        detector = _get_intent_drift_detector()
        result = detector.track(request.goal, request.actions)
        return {"enabled": True, "drift": result}
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة تتبع انحراف النية غير مثبتة")
    except Exception as e:
        return {
            "enabled": True,
            "error": f"فشل في تتبع انحراف النية: {str(e)}",
            "drift": None,
        }


@router.get("/intent-drift/report", dependencies=[Depends(require_auth)])
async def get_intent_drift_report():
    """تقرير انحراف النية."""
    if not _is_agi_module_enabled("MAMOUN_INTENT_DRIFT_ENABLED"):
        return {
            "enabled": False,
            "message": "وحدة تتبع انحراف النية غير مفعّلة. قم بتعيين MAMOUN_INTENT_DRIFT_ENABLED=true لتفعيلها.",
        }
    try:
        detector = _get_intent_drift_detector()
        report = detector.get_report()
        return {"enabled": True, "report": report}
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة تتبع انحراف النية غير مثبتة")
    except Exception as e:
        return {"enabled": True, "error": f"فشل في جلب تقرير انحراف النية: {str(e)}"}


# =============================================================================
# 7. Continual Learning Routes
# =============================================================================

@router.post("/continual-learning/learn", dependencies=[Depends(require_auth)])
async def continual_learn(request: ContinualLearnRequest):
    """التعلم من تفاعل جديد."""
    if not _is_agi_module_enabled("MAMOUN_CONTINUAL_LEARNING_ENABLED"):
        return {
            "enabled": False,
            "message": "وحدة التعلم المستمر غير مفعّلة. قم بتعيين MAMOUN_CONTINUAL_LEARNING_ENABLED=true لتفعيلها.",
            "learned": False,
        }
    try:
        learner = _get_continual_learning_engine()
        result = learner.learn(request.interaction)
        return {"enabled": True, "learned": True, "result": result}
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة التعلم المستمر غير مثبتة")
    except Exception as e:
        return {
            "enabled": True,
            "error": f"فشل في التعلم المستمر: {str(e)}",
            "learned": False,
        }


@router.get("/continual-learning/stats", dependencies=[Depends(require_auth)])
async def get_continual_learning_stats():
    """إحصائيات التعلم المستمر."""
    if not _is_agi_module_enabled("MAMOUN_CONTINUAL_LEARNING_ENABLED"):
        return {
            "enabled": False,
            "message": "وحدة التعلم المستمر غير مفعّلة. قم بتعيين MAMOUN_CONTINUAL_LEARNING_ENABLED=true لتفعيلها.",
        }
    try:
        learner = _get_continual_learning_engine()
        stats = learner.get_stats()
        return {"enabled": True, "stats": stats}
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة التعلم المستمر غير مثبتة")
    except Exception as e:
        return {"enabled": True, "error": f"فشل في جلب إحصائيات التعلم المستمر: {str(e)}"}


# =============================================================================
# 8. Skill Discovery Routes
# =============================================================================

@router.post("/skill-discovery/discover", dependencies=[Depends(require_auth)])
async def discover_skill(request: SkillDiscoverRequest):
    """اكتشاف مهارة من فشل."""
    if not _is_agi_module_enabled("MAMOUN_SKILL_DISCOVERY_ENABLED"):
        return {
            "enabled": False,
            "message": "وحدة اكتشاف المهارات غير مفعّلة. قم بتعيين MAMOUN_SKILL_DISCOVERY_ENABLED=true لتفعيلها.",
            "skill": None,
        }
    try:
        discoverer = _get_skill_discovery()
        result = discoverer.discover(request.error, context=request.context)
        return {"enabled": True, "skill": result}
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة اكتشاف المهارات غير مثبتة")
    except Exception as e:
        return {
            "enabled": True,
            "error": f"فشل في اكتشاف المهارة: {str(e)}",
            "skill": None,
        }


@router.get("/skill-discovery/skills", dependencies=[Depends(require_auth)])
async def get_discovered_skills():
    """المهارات المكتشفة."""
    if not _is_agi_module_enabled("MAMOUN_SKILL_DISCOVERY_ENABLED"):
        return {
            "enabled": False,
            "message": "وحدة اكتشاف المهارات غير مفعّلة. قم بتعيين MAMOUN_SKILL_DISCOVERY_ENABLED=true لتفعيلها.",
            "skills": [],
        }
    try:
        discoverer = _get_skill_discovery()
        skills = discoverer.get_discovered_skills()
        return {"enabled": True, "skills": skills}
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة اكتشاف المهارات غير مثبتة")
    except Exception as e:
        return {"enabled": True, "error": f"فشل في جلب المهارات المكتشفة: {str(e)}", "skills": []}


# =============================================================================
# 9. Theory of Mind Routes
# =============================================================================

@router.post("/theory-of-mind/model", dependencies=[Depends(require_auth)])
async def model_agent(request: TheoryOfMindModelRequest):
    """بناء نموذج عقلي لوكيل آخر."""
    if not _is_agi_module_enabled("MAMOUN_THEORY_OF_MIND_ENABLED"):
        return {
            "enabled": False,
            "message": "وحدة نظرية العقل غير مفعّلة. قم بتعيين MAMOUN_THEORY_OF_MIND_ENABLED=true لتفعيلها.",
            "model": None,
        }
    try:
        tom = _get_theory_of_mind()
        model = tom.build_model(request.agent_id, request.observations)
        return {"enabled": True, "model": model}
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة نظرية العقل غير مثبتة")
    except Exception as e:
        return {
            "enabled": True,
            "error": f"فشل في بناء النموذج العقلي: {str(e)}",
            "model": None,
        }


@router.post("/theory-of-mind/predict", dependencies=[Depends(require_auth)])
async def predict_agent_action(request: TheoryOfMindPredictRequest):
    """التنبؤ بعمل وكيل آخر."""
    if not _is_agi_module_enabled("MAMOUN_THEORY_OF_MIND_ENABLED"):
        return {
            "enabled": False,
            "message": "وحدة نظرية العقل غير مفعّلة. قم بتعيين MAMOUN_THEORY_OF_MIND_ENABLED=true لتفعيلها.",
            "prediction": None,
        }
    try:
        tom = _get_theory_of_mind()
        prediction = tom.predict_action(request.agent_id, context=request.context)
        return {"enabled": True, "prediction": prediction}
    except ImportError:
        raise HTTPException(status_code=501, detail="وحدة نظرية العقل غير مثبتة")
    except Exception as e:
        return {
            "enabled": True,
            "error": f"فشل في التنبؤ بعمل الوكيل: {str(e)}",
            "prediction": None,
        }


# =============================================================================
# 10. AGI Overview Route
# =============================================================================

@router.get("/agi/capabilities", dependencies=[Depends(require_auth)])
async def get_agi_capabilities():
    """نظرة شاملة على قدرات AGI الحالية."""
    capabilities = {
        "privacy_guard": {
            "enabled": _is_agi_module_enabled("MAMOUN_PRIVACY_GUARD_ENABLED"),
            "readiness": 0.0,
            "description": "حارس الخصوصية — تشفير وتدقيق البيانات الحساسة",
        },
        "system2_reasoner": {
            "enabled": _is_agi_module_enabled("MAMOUN_SYSTEM2_ENABLED"),
            "readiness": 0.0,
            "description": "استدلال System 2 — مسار مزدوج سريع/عميق",
        },
        "fluid_reasoner": {
            "enabled": _is_agi_module_enabled("MAMOUN_FLUID_REASONER_ENABLED"),
            "readiness": 0.0,
            "description": "الاستدلال السائب — تفكير مرن ومتكيف",
        },
        "common_sense": {
            "enabled": _is_agi_module_enabled("MAMOUN_COMMON_SENSE_ENABLED"),
            "readiness": 0.0,
            "description": "المنطق العام — كشف الادعاءات غير المنطقية",
        },
        "hallucination_detection": {
            "enabled": _is_agi_module_enabled("MAMOUN_HALLUCINATION_DETECTION_ENABLED"),
            "readiness": 0.0,
            "description": "كشف الهلوسة — التحقق من دقة المعلومات",
        },
        "intent_drift": {
            "enabled": _is_agi_module_enabled("MAMOUN_INTENT_DRIFT_ENABLED"),
            "readiness": 0.0,
            "description": "تتبع انحراف النية — الحفاظ على الأهداف",
        },
        "continual_learning": {
            "enabled": _is_agi_module_enabled("MAMOUN_CONTINUAL_LEARNING_ENABLED"),
            "readiness": 0.0,
            "description": "التعلم المستمر — التطور من التفاعلات",
        },
        "skill_discovery": {
            "enabled": _is_agi_module_enabled("MAMOUN_SKILL_DISCOVERY_ENABLED"),
            "readiness": 0.0,
            "description": "اكتشاف المهارات — التعلم من الفشل",
        },
        "theory_of_mind": {
            "enabled": _is_agi_module_enabled("MAMOUN_THEORY_OF_MIND_ENABLED"),
            "readiness": 0.0,
            "description": "نظرية العقل — فهم وكلاء آخرين",
        },
    }

    # Attempt to get readiness scores from enabled modules
    for module_key, module_info in capabilities.items():
        if not module_info["enabled"]:
            continue
        try:
            if module_key == "privacy_guard":
                guard = _get_privacy_guard()
                module_info["readiness"] = guard.get_status().get("readiness", 0.0)
            elif module_key == "system2_reasoner":
                reasoner = _get_system2_reasoner()
                module_info["readiness"] = reasoner.get_stats().get("readiness", 0.0)
            elif module_key == "fluid_reasoner":
                reasoner = _get_fluid_reasoner()
                module_info["readiness"] = reasoner.get_stats().get("readiness", 0.0)
            elif module_key == "common_sense":
                cs_filter = _get_common_sense_filter()
                module_info["readiness"] = cs_filter.get_rules().get("readiness", 0.0) if isinstance(cs_filter.get_rules(), dict) else 0.0
            elif module_key == "hallucination_detection":
                detector = _get_hallucination_detector()
                module_info["readiness"] = detector.get_stats().get("readiness", 0.0)
            elif module_key == "intent_drift":
                detector = _get_intent_drift_detector()
                module_info["readiness"] = detector.get_report().get("readiness", 0.0)
            elif module_key == "continual_learning":
                learner = _get_continual_learning_engine()
                module_info["readiness"] = learner.get_stats().get("readiness", 0.0)
            elif module_key == "skill_discovery":
                discoverer = _get_skill_discovery()
                module_info["readiness"] = discoverer.get_discovered_skills().get("readiness", 0.0) if isinstance(discoverer.get_discovered_skills(), dict) else 0.0
            elif module_key == "theory_of_mind":
                tom = _get_theory_of_mind()
                module_info["readiness"] = tom.get_stats().get("readiness", 0.0) if hasattr(tom, "get_stats") else 0.0
        except (ImportError, Exception):
            # Module not installed or failed — keep readiness at 0.0
            pass

    enabled_count = sum(1 for c in capabilities.values() if c["enabled"])
    total_count = len(capabilities)

    return {
        "version": "6.0",
        "capabilities": capabilities,
        "summary": {
            "total_modules": total_count,
            "enabled_modules": enabled_count,
            "overall_readiness": sum(c["readiness"] for c in capabilities.values()) / total_count if total_count > 0 else 0.0,
        },
    }


# =============================================================================
# v40.0 AGI Bridge Routes — جسر AGI الموحد
# =============================================================================

@router.get("/agi/status")
async def get_agi_bridge_status():
    """حالة جسر AGI الموحد — System2 + Causal + Capabilities."""
    try:
        from mamoun.core.agi_bridge import get_agi_bridge
        bridge = get_agi_bridge()
        return bridge.get_status()
    except Exception as e:
        return {
            "version": "7.0.0",
            "error": f"فشل في تحميل جسر AGI: {str(e)}",
            "system2_enabled": _is_agi_module_enabled("MAMOUN_SYSTEM2_ENABLED"),
            "total_queries": 0,
        }


@router.post("/agi/process", dependencies=[Depends(require_auth)])
async def agi_process(request: AGIProcessRequest):
    """معالجة استعلام موحدة عبر جسر AGI — System1/System2 + Causal + Capabilities."""
    try:
        from mamoun.core.agi_bridge import get_agi_bridge
        bridge = get_agi_bridge()
        result = await bridge.process(
            query=request.query,
            context=request.context,
            brains_responses=request.brain_responses,
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"فشل في معالجة AGI: {str(e)}")


@router.get("/agi/capability/{cap_key}")
async def get_agi_capability_status(cap_key: str):
    """حالة قدرة AGI محددة."""
    try:
        from mamoun.core.agi_bridge import get_agi_bridge
        bridge = get_agi_bridge()
        status = bridge.get_capability_status(cap_key)
        if status is None:
            raise HTTPException(status_code=404, detail=f"قدرة غير معروفة: {cap_key}")
        return status
    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e), "key": cap_key}


@router.post("/agi/capability/toggle", dependencies=[Depends(require_auth)])
async def toggle_agi_capability(request: AGICapabilityToggleRequest):
    """تفعيل أو تعطيل قدرة AGI."""
    try:
        from mamoun.core.agi_bridge import get_agi_bridge
        bridge = get_agi_bridge()
        if request.enabled:
            success = bridge.enable_capability(request.capability_key)
        else:
            success = bridge.disable_capability(request.capability_key)

        if not success:
            raise HTTPException(status_code=404, detail=f"قدرة غير معروفة: {request.capability_key}")

        # Persist to .env
        from mamoun.core.agi_bridge import AGIBridge
        info = AGIBridge.CAPABILITY_REGISTRY.get(request.capability_key)
        if info:
            env_val = "true" if request.enabled else "false"
            _os.environ[info["env_toggle"]] = env_val
            env_path = _os.path.join(
                _os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))),
                ".env"
            )
            _persist_env_var(env_path, info["env_toggle"], env_val)

        return {
            "success": True,
            "capability": request.capability_key,
            "enabled": request.enabled,
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/agi/uncertainty/stats")
async def get_uncertainty_stats():
    """إحصائيات عدم اليقين."""
    try:
        from mamoun.core.agi_bridge import get_agi_bridge
        bridge = get_agi_bridge()
        return bridge.get_uncertainty_stats()
    except Exception as e:
        return {"error": str(e)}


@router.get("/agi/uncertainty/drift")
async def get_uncertainty_drift():
    """كشف انحراف عدم اليقين."""
    try:
        from mamoun.core.agi_bridge import get_agi_bridge
        bridge = get_agi_bridge()
        return bridge.get_uncertainty_drift()
    except Exception as e:
        return {"error": str(e)}
