"""
BABSHARQII v25.0 — v25 API Routes
مسارات API للركائز الجديدة:
1. Neural Architecture (real weights)
2. Transfer Learning (domain adaptation)
3. Long-Term Planning (months/years)
4. Causal World Model (no LLM)
"""
from fastapi import APIRouter, Body, Depends, HTTPException
from typing import Dict, List, Any, Optional
import time


def _np():
    """Lazy numpy import — prevents ImportError if numpy is not installed."""
    try:
        import numpy as np
        return np
    except ImportError:
        raise HTTPException(500, "numpy غير مثبت — لا يمكن تنفيذ عمليات الشبكة العصبية")

from mamoun.api.deps import require_auth


# ── Lazy imports: prevent module-level crash if numpy/optional deps missing ──

def _get_neural_mesh():
    from mamoun.neural.neural_mesh import neural_mesh
    return neural_mesh

def _get_hebbian():
    from mamoun.neural.hebbian_learner import HebbianLearner, LearningConfig
    return HebbianLearner, LearningConfig

def _get_stdp():
    from mamoun.neural.stdp_synapse import STDPSynapse, STDPConfig
    return STDPSynapse, STDPConfig

def _get_synaptic_intelligence():
    from mamoun.transfer.synaptic_intelligence import synaptic_intelligence
    return synaptic_intelligence

def _get_domain_adapter():
    from mamoun.transfer.domain_adapter import domain_adapter
    return domain_adapter

def _get_knowledge_bridge():
    from mamoun.transfer.knowledge_bridge import knowledge_bridge
    return knowledge_bridge

def _get_long_term_planner():
    from mamoun.core.long_term_planner import long_term_planner, TemporalHorizon
    return long_term_planner, TemporalHorizon

def _get_causal_world_model():
    from mamoun.awareness.causal_world_model import causal_world_model
    return causal_world_model

router = APIRouter(prefix="/v25", tags=["v25 — Neural Architecture + Transfer Learning + Long-Term Planning + Causal World Model"])


# ═══════════════════════════════════════════════════════════════
# Pillar 1: Neural Architecture (Real Weights)
# ═══════════════════════════════════════════════════════════════

@router.post("/neural/create-layer", dependencies=[Depends(require_auth)])
async def create_neural_layer(name: str, input_size: int = 64, output_size: int = 32,
                              activation: str = "sigmoid", learning_rate: float = 0.01):
    """إنشاء طبقة عصبية بأوزان فعلية"""
    layer = _get_neural_mesh().create_layer(name, input_size, output_size, activation, learning_rate)
    return {"layer_id": layer.layer_id, "name": name,
            "shape": f"{input_size}→{output_size}",
            "total_weights": input_size * output_size}


@router.post("/neural/learn", dependencies=[Depends(require_auth)])
async def neural_learn(layer_name: str, input_data: List[float] = Body(...),
                       target_data: List[float] = Body(default=None)):
    """تعلم نمط — الأوزان تتعدل فعلياً"""
    x = _np().array(input_data, dtype=_np().float64)
    target = _np().array(target_data, dtype=_np().float64) if target_data else None
    result = _get_neural_mesh().learn_pattern(layer_name, x, target)
    return result


@router.post("/neural/recall", dependencies=[Depends(require_auth)])
async def neural_recall(layer_name: str, input_data: List[float] = Body(...),
                        iterations: int = 5):
    """استرجاع ذاتي — إكمال النمط من مدخل جزئي"""
    x = _np().array(input_data, dtype=_np().float64)
    return _get_neural_mesh().recall(layer_name, x, iterations)


@router.post("/neural/associate", dependencies=[Depends(require_auth)])
async def neural_associate(source_layer: str, target_layer: str,
                           source_data: List[float] = Body(...),
                           target_data: List[float] = Body(...),
                           strength: float = 0.5):
    """ربط نمطين عبر طبقتين"""
    src = _np().array(source_data, dtype=_np().float64)
    tgt = _np().array(target_data, dtype=_np().float64)
    return _get_neural_mesh().associate(source_layer, target_layer, src, tgt, strength)


@router.post("/neural/cross-activate", dependencies=[Depends(require_auth)])
async def neural_cross_activate(source_layer: str, target_layer: str,
                                source_data: List[float] = Body(...)):
    """تنشيط متقاطع عبر ارتباط"""
    src = _np().array(source_data, dtype=_np().float64)
    return _get_neural_mesh().cross_activate(source_layer, target_layer, src)


@router.post("/neural/transfer-knowledge", dependencies=[Depends(require_auth)])
async def neural_transfer_knowledge(source_layer: str, target_layer: str,
                                    freeze_ratio: float = 0.7):
    """نقل المعرفة — نسخ أوزان مع تجميد جزئي"""
    return _get_neural_mesh().transfer_knowledge(source_layer, target_layer, freeze_ratio)


@router.get("/neural/layer/{layer_name}")
async def get_neural_layer(layer_name: str):
    """إحصائيات طبقة عصبية — شكل الأوزان الفعلية"""
    result = _get_neural_mesh().get_layer(layer_name)
    if not result:
        raise HTTPException(status_code=404, detail="Layer not found")
    return result


@router.get("/neural/stats")
async def neural_stats():
    """إحصائيات الشبكة العصبية"""
    return _get_neural_mesh().get_stats()


@router.post("/neural/hebbian-learn", dependencies=[Depends(require_auth)])
async def hebbian_learn(layer_name: str, input_data: List[float] = Body(...),
                        target_data: List[float] = Body(...),
                        rule: str = "oja_rule", learning_rate: float = 0.01):
    """تعلم هيبي — قاعدة تعلم عصبية فعلية"""
    layer = _get_neural_mesh()._find_layer_by_name(layer_name)
    if not layer:
        raise HTTPException(status_code=404, detail=f"Layer '{layer_name}' not found")

    x = _np().array(input_data, dtype=_np().float64)
    y = _np().array(target_data, dtype=_np().float64)

    config = _get_hebbian()[1](rule=rule, learning_rate=learning_rate)
    learner = _get_hebbian()[0](config)
    result = learner.learn(layer.weight_matrix, x, y, layer.consolidation_matrix)

    _get_neural_mesh()._persist_layer(layer)

    return {
        "layer": layer_name,
        "rule": rule,
        "weight_updates": result.weight_updates,
        "mean_delta": result.mean_delta,
        "max_delta": result.max_delta,
        "weight_sparsity": result.weight_sparsity,
    }


@router.post("/neural/stdp-learn", dependencies=[Depends(require_auth)])
async def stdp_learn(layer_name: str, pre_data: List[float] = Body(...),
                     post_data: List[float] = Body(...),
                     time_delta: float = 0.01):
    """تعلم STDP — التعلم المعتمد على التوقيت"""
    layer = _get_neural_mesh()._find_layer_by_name(layer_name)
    if not layer:
        raise HTTPException(status_code=404, detail=f"Layer '{layer_name}' not found")

    pre = _np().array(pre_data, dtype=_np().float64)
    post = _np().array(post_data, dtype=_np().float64)

    synapse = _get_stdp()[0]()
    synapse.pre_fire(pre, time.time() - time_delta)
    event = synapse.post_fire(post, time.time(), layer.weight_matrix, pre, layer.consolidation_matrix)

    _get_neural_mesh()._persist_layer(layer)

    return {
        "layer": layer_name,
        "event_type": event.get("type", "unknown"),
        "time_delta": time_delta,
        "mean_delta": event.get("mean_delta", 0),
    }


# ═══════════════════════════════════════════════════════════════
# Pillar 2: Transfer Learning
# ═══════════════════════════════════════════════════════════════

@router.post("/transfer/register-domain", dependencies=[Depends(require_auth)])
async def register_domain(name: str, layer_name: str = "", description: str = ""):
    """تسجيل نطاق معرفي جديد"""
    domain = _get_domain_adapter().register_domain(name, layer_name, description=description)
    return {"domain_id": domain.domain_id, "name": name}


@router.post("/transfer/start-task", dependencies=[Depends(require_auth)])
async def start_transfer_task(task_id: str, domain: str, layer_name: str = "default"):
    """بدء مهمة نقل تعلم"""
    layer = _get_neural_mesh()._find_layer_by_name(layer_name)
    if not layer:
        raise HTTPException(status_code=404, detail=f"Layer '{layer_name}' not found")

    _get_synaptic_intelligence().start_task(task_id, domain, layer.weight_matrix, layer_name)
    return {"task_id": task_id, "domain": domain, "status": "started"}


@router.post("/transfer/end-task", dependencies=[Depends(require_auth)])
async def end_transfer_task(task_id: str, layer_name: str = "default"):
    """إنهاء مهمة — حساب أهمية الأوزان"""
    layer = _get_neural_mesh()._find_layer_by_name(layer_name)
    if not layer:
        raise HTTPException(status_code=404, detail=f"Layer '{layer_name}' not found")

    report = _get_synaptic_intelligence().end_task(task_id, layer.weight_matrix, layer_name)
    return {
        "task_id": report.task_id,
        "important_synapses": report.important_synapses,
        "si_penalty": report.si_penalty,
        "transfer_score": report.transfer_score,
    }


@router.post("/transfer/domain-transfer", dependencies=[Depends(require_auth)])
async def domain_transfer(source: str, target: str,
                          source_layer: str = "", target_layer: str = "",
                          freeze_ratio: float = 0.6):
    """نقل معرفة بين نطاقين"""
    src_layer = _get_neural_mesh()._find_layer_by_name(source_layer) if source_layer else None
    tgt_layer = _get_neural_mesh()._find_layer_by_name(target_layer) if target_layer else None

    if not src_layer or not tgt_layer:
        raise HTTPException(status_code=404, detail="Source or target layer not found")

    result = _get_domain_adapter().transfer(
        source, target,
        tgt_layer.weight_matrix,
        src_layer.weight_matrix,
        tgt_layer.consolidation_matrix,
        freeze_ratio,
    )
    _get_neural_mesh()._persist_layer(tgt_layer)
    return {
        "transfer_id": result.transfer_id,
        "frozen": result.weights_frozen,
        "plastic": result.weights_plastic,
        "alignment": result.alignment_score,
        "benefit": result.estimated_benefit,
    }


@router.post("/transfer/align", dependencies=[Depends(require_auth)])
async def align_domains(source: str, target: str,
                        source_data: List[float] = Body(...),
                        target_data: List[float] = Body(...)):
    """محاذاة نطاقين"""
    src = _np().array(source_data, dtype=_np().float64)
    tgt = _np().array(target_data, dtype=_np().float64)
    return _get_domain_adapter().align_domains(source, target, src, tgt)


@router.post("/bridge/register-concept", dependencies=[Depends(require_auth)])
async def register_concept(name: str, domain: str,
                           embedding: List[float] = Body(default=None)):
    """تسجيل مفهوم في جسر المعرفة"""
    emb = _np().array(embedding, dtype=_np().float64) if embedding else None
    return _get_knowledge_bridge().register_concept(name, domain, emb)


@router.get("/bridge/find-analogies")
async def find_analogies(concept: str, source_domain: str,
                         target_domain: str = None, top_k: int = 5):
    """إيجاد تشبيهات بين النطاقات"""
    return _get_knowledge_bridge().find_analogies(concept, source_domain, target_domain, top_k)


@router.get("/transfer/stats")
async def transfer_stats():
    """إحصائيات نقل التعلم"""
    return {
        "synaptic_intelligence": _get_synaptic_intelligence().get_stats(),
        "domain_adapter": _get_domain_adapter().get_stats(),
        "knowledge_bridge": _get_knowledge_bridge().get_stats(),
    }


# ═══════════════════════════════════════════════════════════════
# Pillar 3: Long-Term Planning
# ═══════════════════════════════════════════════════════════════

@router.post("/ltp/create-goal", dependencies=[Depends(require_auth)])
async def create_goal(title: str, vision: str = "",
                      horizon: str = "this_year",
                      target_date: float = 0, resources_estimated: float = 0):
    """إنشاء هدف استراتيجي طويل المدى"""
    goal = _get_long_term_planner()[0].create_goal(title, vision=vision, horizon=horizon,
                                         target_date=target_date,
                                         resources_estimated=resources_estimated)
    return {"goal_id": goal.goal_id, "title": goal.title, "horizon": horizon}


@router.post("/ltp/add-milestone", dependencies=[Depends(require_auth)])
async def add_milestone(goal_id: str, title: str,
                        horizon: str = "this_month",
                        deadline: float = 0, priority: float = 0.5,
                        estimated_hours: float = 0):
    """إضافة معلم للهدف"""
    ms = _get_long_term_planner()[0].add_milestone(goal_id, title, horizon=horizon,
                                          deadline=deadline, priority=priority,
                                          estimated_hours=estimated_hours)
    if not ms:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"milestone_id": ms.milestone_id, "title": title, "horizon": horizon}


@router.post("/ltp/add-dependency", dependencies=[Depends(require_auth)])
async def add_milestone_dependency(milestone_id: str, depends_on: str):
    """إضافة تبعية بين معلمين"""
    ok = _get_long_term_planner()[0].add_milestone_dependency(milestone_id, depends_on)
    return {"success": ok}


@router.post("/ltp/update-milestone", dependencies=[Depends(require_auth)])
async def update_milestone(milestone_id: str, progress: float = None,
                           status: str = None, actual_hours: float = None,
                           risk_level: float = None):
    """تحديث معلم"""
    ms = _get_long_term_planner()[0].update_milestone(milestone_id, progress, status,
                                            actual_hours, risk_level)
    if not ms:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return {"milestone_id": ms.milestone_id, "progress": ms.progress, "status": ms.status}


@router.get("/ltp/forecast/{goal_id}")
async def forecast_goal(goal_id: str):
    """تنبؤ — هل سنصل للهدف؟"""
    return _get_long_term_planner()[0].forecast(goal_id).to_dict()


@router.post("/ltp/replan/{goal_id}", dependencies=[Depends(require_auth)])
async def replan_goal(goal_id: str):
    """إعادة تخطيط — تعديل الخطة"""
    return _get_long_term_planner()[0].replan(goal_id)


@router.get("/ltp/tree")
async def goal_tree(goal_id: str = None):
    """شجرة الأهداف والمعالم"""
    return _get_long_term_planner()[0].get_goal_tree(goal_id)


@router.get("/ltp/stats")
async def ltp_stats():
    """إحصائيات التخطيط طويل المدى"""
    return _get_long_term_planner()[0].get_stats()


# ═══════════════════════════════════════════════════════════════
# Pillar 4: Causal World Model (No LLM)
# ═══════════════════════════════════════════════════════════════

@router.post("/cwm/add-variable", dependencies=[Depends(require_auth)])
async def cwm_add_variable(name: str, var_type: str = "continuous",
                           description: str = ""):
    """إضافة متغير سببي"""
    var = _get_causal_world_model().add_variable(name, var_type, description)
    return {"var_id": var.var_id, "name": name}


@router.post("/cwm/add-observation", dependencies=[Depends(require_auth)])
async def cwm_add_observation(data: Dict[str, float] = Body(...)):
    """إضافة ملاحظة"""
    _get_causal_world_model().add_observation(data)
    return {"status": "recorded"}


@router.post("/cwm/add-observations-batch", dependencies=[Depends(require_auth)])
async def cwm_add_observations_batch(observations: List[Dict[str, float]] = Body(...)):
    """إضافة مجموعة ملاحظات"""
    _get_causal_world_model().add_observations_batch(observations)
    return {"status": "recorded", "count": len(observations)}


@router.post("/cwm/discover-structure", dependencies=[Depends(require_auth)])
async def cwm_discover_structure(alpha: float = 0.05, max_cond_size: int = 3):
    """اكتشاف البنية السببية — بدون LLM"""
    return _get_causal_world_model().discover_structure(alpha, max_cond_size)


@router.post("/cwm/do-intervention", dependencies=[Depends(require_auth)])
async def cwm_do_intervention(variable: str, value: float):
    """do-calculus رياضي — بدون LLM"""
    return _get_causal_world_model().do_intervention(variable, value)


@router.post("/cwm/counterfactual", dependencies=[Depends(require_auth)])
async def cwm_counterfactual(observed: Dict[str, float] = Body(...),
                             intervention: Dict[str, float] = Body(...)):
    """استدلال مضاد للواقع — بدون LLM"""
    return _get_causal_world_model().counterfactual(observed, intervention)


@router.get("/cwm/explain")
async def cwm_explain(cause: str, effect: str):
    """تفسير سببي — بدون LLM"""
    return _get_causal_world_model().explain_effect(cause, effect)


@router.get("/cwm/stats")
async def cwm_stats():
    """إحصائيات النموذج السببي العالمي"""
    return _get_causal_world_model().get_stats()


# ═══════════════════════════════════════════════════════════════
# Overview
# ═══════════════════════════════════════════════════════════════

@router.get("/status")
async def v25_status():
    """حالة ركائز v25"""
    return {
        "version": "25.0.0",
        "pillars": {
            "neural_architecture": {
                "status": "active",
                "layers": len(_get_neural_mesh()._layers),
                "stats": _get_neural_mesh().get_stats(),
            },
            "transfer_learning": {
                "status": "active",
                "synaptic_intelligence": _get_synaptic_intelligence().get_stats(),
                "domain_adapter": _get_domain_adapter().get_stats(),
            },
            "long_term_planning": {
                "status": "active",
                "stats": _get_long_term_planner()[0].get_stats(),
            },
            "causal_world_model": {
                "status": "active",
                "llm_used": False,
                "stats": _get_causal_world_model().get_stats(),
            },
        },
    }
