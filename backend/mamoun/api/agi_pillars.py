"""
BABSHARQII v24.1 — AGI Pillars API Routes
مسارات API لركائز الذكاء العام السبعة
"""
from fastapi import APIRouter, Depends, HTTPException

from mamoun.api.deps import require_auth

router = APIRouter(prefix="/agi", tags=["AGI Pillars"])


# ═══════════════════════════════════════════════════════════════
# Lazy-load helpers — prevents broken deps from crashing the router
# ═══════════════════════════════════════════════════════════════

_causal_graph = None

def _get_causal_graph():
    global _causal_graph
    if _causal_graph is None:
        from mamoun.core.causal_graph import causal_graph
        _causal_graph = causal_graph
    if hasattr(_causal_graph, '_initialized') and not _causal_graph._initialized:
        _causal_graph.initialize()
    return _causal_graph

_episodic_memory_v2 = None

def _get_episodic_memory_v2():
    global _episodic_memory_v2
    if _episodic_memory_v2 is None:
        from mamoun.memory.episodic_memory_v2 import episodic_memory_v2
        _episodic_memory_v2 = episodic_memory_v2
    if hasattr(_episodic_memory_v2, '_initialized') and not _episodic_memory_v2._initialized:
        _episodic_memory_v2.initialize()
    return _episodic_memory_v2

_metacognitive_engine = None

def _get_metacognitive_engine():
    global _metacognitive_engine
    if _metacognitive_engine is None:
        from mamoun.core.metacognitive_engine import metacognitive_engine
        _metacognitive_engine = metacognitive_engine
    if hasattr(_metacognitive_engine, '_initialized') and not _metacognitive_engine._initialized:
        _metacognitive_engine.initialize()
    return _metacognitive_engine

_hierarchical_planner = None

def _get_hierarchical_planner():
    global _hierarchical_planner
    if _hierarchical_planner is None:
        from mamoun.core.hierarchical_planner import hierarchical_planner
        _hierarchical_planner = hierarchical_planner
    if hasattr(_hierarchical_planner, '_initialized') and not _hierarchical_planner._initialized:
        _hierarchical_planner.initialize()
    return _hierarchical_planner

_world_knowledge_graph = None

def _get_world_knowledge_graph():
    global _world_knowledge_graph
    if _world_knowledge_graph is None:
        from mamoun.awareness.world_knowledge_graph import world_knowledge_graph
        _world_knowledge_graph = world_knowledge_graph
    if hasattr(_world_knowledge_graph, '_initialized') and not _world_knowledge_graph._initialized:
        _world_knowledge_graph.initialize()
    return _world_knowledge_graph

_consequence_learning = None

def _get_consequence_learning():
    global _consequence_learning
    if _consequence_learning is None:
        from mamoun.core.consequence_learning import consequence_learning
        _consequence_learning = consequence_learning
    if hasattr(_consequence_learning, '_initialized') and not _consequence_learning._initialized:
        _consequence_learning.initialize()
    return _consequence_learning

_selective_attention = None

def _get_selective_attention():
    global _selective_attention
    if _selective_attention is None:
        from mamoun.core.selective_attention import selective_attention
        _selective_attention = selective_attention
    if hasattr(_selective_attention, '_initialized') and not _selective_attention._initialized:
        _selective_attention.initialize()
    return _selective_attention


# ═══════════════════════════════════════════════════════════════
# Overview
# ═══════════════════════════════════════════════════════════════

@router.get("/pillars/status")
async def agi_pillars_status():
    """حالة ركائز AGI"""
    return {
        "version": "24.1.0",
        "pillars": {
            "causal_graph": _get_causal_graph().get_stats(),
            "episodic_memory": _get_episodic_memory_v2().get_stats(),
            "metacognitive": _get_metacognitive_engine().get_stats(),
            "planner": _get_hierarchical_planner().get_stats(),
            "world_graph": _get_world_knowledge_graph().get_stats(),
            "consequence_learning": _get_consequence_learning().get_stats(),
            "attention": _get_selective_attention().get_stats(),
        },
    }


# ═══════════════════════════════════════════════════════════════
# Pillar 1: Causal Graph
# ═══════════════════════════════════════════════════════════════

@router.post("/causal/add-cause", dependencies=[Depends(require_auth)])
async def add_cause(source: str, target: str, confidence: float = 0.5,
                    edge_type: str = "causes"):
    edge = _get_causal_graph().add_cause(source, target, edge_type=edge_type, confidence=confidence)
    return {"edge_id": edge.edge_id, "confidence": edge.confidence}


@router.get("/causal/explain")
async def explain_cause(source: str, target: str):
    return _get_causal_graph().explain(source, target).to_dict()


@router.get("/causal/intervene")
async def intervene(action: str):
    result = _get_causal_graph().intervene(action)
    return {"intervention": result.intervention, "effects": result.predicted_effects,
            "confidence": result.confidence}


@router.get("/causal/counterfactual")
async def counterfactual(observed: str, prevented: str):
    return _get_causal_graph().counterfactual(observed, prevented)


@router.post("/causal/learn", dependencies=[Depends(require_auth)])
async def causal_learn(cause: str, effect: str, happened: bool):
    return _get_causal_graph().learn_from_outcome(cause, effect, happened)


@router.get("/causal/subgraph")
async def causal_subgraph(center: str, depth: int = 2):
    return _get_causal_graph().get_subgraph(center, depth)


@router.get("/causal/stats")
async def causal_stats():
    return _get_causal_graph().get_stats()


# ═══════════════════════════════════════════════════════════════
# Pillar 2: Episodic Memory V2
# ═══════════════════════════════════════════════════════════════

@router.post("/memory/record", dependencies=[Depends(require_auth)])
async def record_episode(situation: str, action_taken: str, outcome: str,
                         positive: bool = True, action_type: str = "",
                         user_reaction: str = "", importance: float = 0.5):
    ep = _get_episodic_memory_v2().record(
        situation=situation, action_taken=action_taken,
        outcome=outcome, outcome_positive=positive,
        action_type=action_type, outcome_user_reaction=user_reaction,
        importance=importance,
    )
    return {"episode_id": ep.episode_id, "lesson": ep.lesson}


@router.get("/memory/recall")
async def recall_memory(situation: str, top_k: int = 5):
    return {"results": _get_episodic_memory_v2().recall_by_analogy(situation, top_k)}


@router.get("/memory/lessons")
async def get_lessons(positive_only: bool = None, limit: int = 20):
    return {"lessons": _get_episodic_memory_v2().get_lessons(positive_only, limit)}


# ═══════════════════════════════════════════════════════════════
# Pillar 3: Metacognitive Engine
# ═══════════════════════════════════════════════════════════════

@router.post("/meta/assess", dependencies=[Depends(require_auth)])
async def meta_assess(topic: str, confidence: float = 0.5):
    a = _get_metacognitive_engine().assess(topic, confidence)
    return {"assessment_id": a.assessment_id, "strategy": a.strategy,
            "confidence": a.confidence, "gaps": a.knowledge_gaps}


@router.post("/meta/reflect", dependencies=[Depends(require_auth)])
async def meta_reflect(assessment_id: str, expected: str, actual: str, success: bool):
    r = _get_metacognitive_engine().reflect(assessment_id, expected, actual, success)
    return {"calibrated": r.confidence_was_calibrated, "error": r.calibration_error,
            "lesson": r.lesson}


@router.get("/meta/calibration")
async def meta_calibration():
    return {"calibration_score": _get_metacognitive_engine().get_calibration_score()}


# ═══════════════════════════════════════════════════════════════
# Pillar 4: Hierarchical Planner
# ═══════════════════════════════════════════════════════════════

@router.post("/plan/create", dependencies=[Depends(require_auth)])
async def create_plan(title: str, level: str = "strategic", description: str = ""):
    p = _get_hierarchical_planner().create_plan(title, description, level)
    return {"plan_id": p.node_id, "title": p.title, "level": p.level}


@router.post("/plan/add-subplan", dependencies=[Depends(require_auth)])
async def add_subplan(parent_id: str, title: str, level: str = "operational"):
    p = _get_hierarchical_planner().add_subplan(parent_id, title, level=level)
    if not p:
        raise HTTPException(status_code=404, detail="Parent not found")
    return {"plan_id": p.node_id, "title": p.title}


@router.post("/plan/update", dependencies=[Depends(require_auth)])
async def update_plan(plan_id: str, progress: float = None, status: str = None):
    p = _get_hierarchical_planner().update_progress(plan_id, progress, status)
    if not p:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"plan_id": p.node_id, "progress": p.progress, "status": p.status}


@router.get("/plan/next-action")
async def next_action():
    action = _get_hierarchical_planner().get_next_action()
    return action or {"message": "No actionable steps available"}


@router.get("/plan/tree")
async def plan_tree(root_id: str = None):
    return _get_hierarchical_planner().get_plan_tree(root_id)


# ═══════════════════════════════════════════════════════════════
# Pillar 5: World Knowledge Graph
# ═══════════════════════════════════════════════════════════════

@router.post("/world/add-entity", dependencies=[Depends(require_auth)])
async def add_entity(name: str, entity_type: str = "concept"):
    e = _get_world_knowledge_graph().add_entity(name, entity_type)
    return {"entity_id": e.entity_id, "name": e.name}


@router.post("/world/add-relation", dependencies=[Depends(require_auth)])
async def add_relation(source: str, target: str, relation_type: str, confidence: float = 0.7):
    r = _get_world_knowledge_graph().add_relation(source, target, relation_type, confidence)
    if not r:
        raise HTTPException(status_code=500, detail="Failed to add relation")
    return {"relation_id": r.relation_id, "type": r.relation_type}


@router.get("/world/connections")
async def get_connections(entity: str, depth: int = 1):
    return _get_world_knowledge_graph().get_connections(entity, depth)


@router.get("/world/path")
async def find_path(source: str, target: str):
    return {"path": _get_world_knowledge_graph().find_path(source, target)}


# ═══════════════════════════════════════════════════════════════
# Pillar 6: Consequence Learning
# ═══════════════════════════════════════════════════════════════

@router.post("/learn/register-action", dependencies=[Depends(require_auth)])
async def register_action(action_type: str, context: str = "",
                          expected: str = "", confidence: float = 0.5):
    a = _get_consequence_learning().register_action(action_type, context, expected, confidence)
    return {"action_id": a.action_id}


@router.post("/learn/record-outcome", dependencies=[Depends(require_auth)])
async def record_outcome(action_id: str, outcome: str, positive: bool = True,
                         user_reaction: str = ""):
    o = _get_consequence_learning().record_outcome(action_id, outcome, positive, user_reaction)
    if not o:
        raise HTTPException(status_code=404, detail="Action not found")
    return {"lessons_extracted": o.lessons_extracted, "surprise": o.surprise}


@router.get("/learn/stats")
async def learn_stats():
    return _get_consequence_learning().get_stats()


# ═══════════════════════════════════════════════════════════════
# Pillar 7: Selective Attention
# ═══════════════════════════════════════════════════════════════

@router.post("/attention/classify", dependencies=[Depends(require_auth)])
async def classify_signal(content: str, source: str = "user"):
    s = _get_selective_attention().classify(content, source)
    return {"signal_id": s.signal_id, "level": s.level, "score": s.score}


@router.get("/attention/pending")
async def pending_signals(min_level: str = "medium", limit: int = 20):
    return {"signals": _get_selective_attention().get_pending(min_level, limit)}


@router.post("/attention/process/{signal_id}", dependencies=[Depends(require_auth)])
async def process_signal(signal_id: str):
    ok = _get_selective_attention().mark_processed(signal_id)
    return {"processed": ok}
