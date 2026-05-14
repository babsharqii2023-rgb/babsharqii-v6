"""
BABSHARQII v24.0 — v24 API Routes
5 New Systems: LiveSelfModifier, InnerMonologue, BehavioralMemory, WorldMonitor, IdeaGenerator
"""

from fastapi import APIRouter, Depends
from mamoun.api.deps import require_auth

router = APIRouter(prefix="/v24", tags=["v24"])


# ═══════════════════════════════════════════════════════════════
# System 1: Live Self-Modifier
# ═══════════════════════════════════════════════════════════════

@router.get("/self-modify/status")
async def self_modify_status():
    from mamoun.evolution.live_self_modifier import live_self_modifier
    if not live_self_modifier._initialized:
        live_self_modifier.initialize()
    return live_self_modifier.get_status()


@router.get("/self-modify/weaknesses")
async def self_modify_weaknesses():
    from mamoun.evolution.live_self_modifier import live_self_modifier
    if not live_self_modifier._initialized:
        live_self_modifier.initialize()
    return {"weaknesses": live_self_modifier.get_weaknesses()}


@router.post("/self-modify/report-weakness", dependencies=[Depends(require_auth)])
async def report_weakness(area: str, description: str, severity: str = "medium", source: str = "api"):
    from mamoun.evolution.live_self_modifier import live_self_modifier
    if not live_self_modifier._initialized:
        live_self_modifier.initialize()
    w = live_self_modifier.report_weakness(area, description, severity, source)
    return {"weakness": w.to_dict()}


@router.post("/self-modify/report-success", dependencies=[Depends(require_auth)])
async def report_success(area: str):
    from mamoun.evolution.live_self_modifier import live_self_modifier
    if not live_self_modifier._initialized:
        live_self_modifier.initialize()
    live_self_modifier.report_success(area)
    return {"status": "ok"}


@router.get("/self-modify/pending")
async def self_modify_pending():
    from mamoun.evolution.live_self_modifier import live_self_modifier
    if not live_self_modifier._initialized:
        live_self_modifier.initialize()
    return {"pending": live_self_modifier.get_pending_modifications()}


@router.get("/self-modify/archive")
async def self_modify_archive(limit: int = 20):
    from mamoun.evolution.live_self_modifier import live_self_modifier
    if not live_self_modifier._initialized:
        live_self_modifier.initialize()
    return {"archive": live_self_modifier.get_archive(limit)}


# ═══════════════════════════════════════════════════════════════
# System 2: Inner Monologue
# ═══════════════════════════════════════════════════════════════

@router.get("/monologue/status")
async def monologue_status():
    from mamoun.core.inner_monologue import inner_monologue
    if not inner_monologue._initialized:
        inner_monologue.initialize()
    return inner_monologue.get_status()


@router.get("/monologue/thoughts")
async def monologue_thoughts(limit: int = 20):
    from mamoun.core.inner_monologue import inner_monologue
    if not inner_monologue._initialized:
        inner_monologue.initialize()
    return {"thoughts": inner_monologue.get_recent_thoughts(limit)}


@router.post("/monologue/inject", dependencies=[Depends(require_auth)])
async def monologue_inject(content: str, thought_type: str = "observation", urgency: str = "medium", context: str = ""):
    from mamoun.core.inner_monologue import inner_monologue
    if not inner_monologue._initialized:
        inner_monologue.initialize()
    t = inner_monologue.inject_thought(content, thought_type, urgency, context)
    return {"thought": t.to_dict()}


@router.get("/monologue/insights")
async def monologue_insights(limit: int = 10):
    from mamoun.core.inner_monologue import inner_monologue
    if not inner_monologue._initialized:
        inner_monologue.initialize()
    return {"insights": inner_monologue.get_insights(limit)}


# ═══════════════════════════════════════════════════════════════
# System 3: Behavioral Memory
# ═══════════════════════════════════════════════════════════════

@router.get("/behavioral/status")
async def behavioral_status():
    from mamoun.memory.behavioral_memory import behavioral_memory
    if not behavioral_memory._initialized:
        behavioral_memory.initialize()
    return behavioral_memory.get_status()


@router.get("/behavioral/traits")
async def behavioral_traits():
    from mamoun.memory.behavioral_memory import behavioral_memory
    if not behavioral_memory._initialized:
        behavioral_memory.initialize()
    return {"traits": behavioral_memory.get_traits()}


@router.post("/behavioral/set-trait", dependencies=[Depends(require_auth)])
async def behavioral_set_trait(name: str, value: float):
    from mamoun.memory.behavioral_memory import behavioral_memory
    if not behavioral_memory._initialized:
        behavioral_memory.initialize()
    behavioral_memory.set_trait(name, value)
    return {"status": "ok"}


@router.get("/behavioral/style")
async def behavioral_style():
    from mamoun.memory.behavioral_memory import behavioral_memory
    if not behavioral_memory._initialized:
        behavioral_memory.initialize()
    return {"style": behavioral_memory.get_response_style()}


@router.get("/behavioral/personality-prompt")
async def behavioral_personality_prompt():
    from mamoun.memory.behavioral_memory import behavioral_memory
    if not behavioral_memory._initialized:
        behavioral_memory.initialize()
    return {"prompt_addon": behavioral_memory.get_personality_prompt_addon()}


@router.get("/behavioral/summary")
async def behavioral_summary():
    from mamoun.memory.behavioral_memory import behavioral_memory
    if not behavioral_memory._initialized:
        behavioral_memory.initialize()
    return {"summary": behavioral_memory.get_personality_summary()}


# ═══════════════════════════════════════════════════════════════
# System 4: World Monitor
# ═══════════════════════════════════════════════════════════════

@router.get("/world/status")
async def world_status():
    from mamoun.awareness.world_monitor import world_monitor
    if not world_monitor._initialized:
        world_monitor.initialize()
    return world_monitor.get_status()


@router.get("/world/context")
async def world_context():
    from mamoun.awareness.world_monitor import world_monitor
    if not world_monitor._initialized:
        world_monitor.initialize()
    return world_monitor.get_current_context()


@router.get("/world/habits")
async def world_habits():
    from mamoun.awareness.world_monitor import world_monitor
    if not world_monitor._initialized:
        world_monitor.initialize()
    return {"habits": world_monitor.get_habits()}


@router.post("/world/record-activity", dependencies=[Depends(require_auth)])
async def world_record_activity(activity_type: str, pattern: str):
    from mamoun.awareness.world_monitor import world_monitor
    if not world_monitor._initialized:
        world_monitor.initialize()
    world_monitor.record_user_activity(activity_type, pattern)
    return {"status": "ok"}


# ═══════════════════════════════════════════════════════════════
# System 5: Idea Generator
# ═══════════════════════════════════════════════════════════════

@router.get("/ideas/status")
async def ideas_status():
    from mamoun.creative.idea_generator import idea_generator
    if not idea_generator._initialized:
        idea_generator.initialize()
    return idea_generator.get_status()


@router.get("/ideas/list")
async def ideas_list(limit: int = 20, min_score: float = 0.0):
    from mamoun.creative.idea_generator import idea_generator
    if not idea_generator._initialized:
        idea_generator.initialize()
    return {"ideas": idea_generator.get_ideas(limit, min_score)}


@router.get("/ideas/top")
async def ideas_top(limit: int = 5):
    from mamoun.creative.idea_generator import idea_generator
    if not idea_generator._initialized:
        idea_generator.initialize()
    return {"ideas": idea_generator.get_top_ideas(limit)}


@router.post("/ideas/create", dependencies=[Depends(require_auth)])
async def ideas_create(topic: str = ""):
    from mamoun.creative.idea_generator import idea_generator
    if not idea_generator._initialized:
        idea_generator.initialize()
    idea = await idea_generator.creative_session(topic)
    if idea:
        return {"idea": idea.to_dict()}
    return {"error": "Could not generate idea"}


# ═══════════════════════════════════════════════════════════════
# Combined: v24 Full Status
# ═══════════════════════════════════════════════════════════════

@router.get("/status")
async def v24_full_status():
    """Full status of all v24 systems"""
    from mamoun.evolution.live_self_modifier import live_self_modifier
    from mamoun.core.inner_monologue import inner_monologue
    from mamoun.memory.behavioral_memory import behavioral_memory
    from mamoun.awareness.world_monitor import world_monitor
    from mamoun.creative.idea_generator import idea_generator

    return {
        "version": "v24.0",
        "systems": {
            "live_self_modifier": live_self_modifier.get_status() if live_self_modifier._initialized else {"initialized": False},
            "inner_monologue": inner_monologue.get_status() if inner_monologue._initialized else {"initialized": False},
            "behavioral_memory": behavioral_memory.get_status() if behavioral_memory._initialized else {"initialized": False},
            "world_monitor": world_monitor.get_status() if world_monitor._initialized else {"initialized": False},
            "idea_generator": idea_generator.get_status() if idea_generator._initialized else {"initialized": False},
        }
    }
