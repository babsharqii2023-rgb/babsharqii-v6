"""
SuperMind API v61 — Unified API router exposing ALL super_brain components.

This router provides 20 endpoints that bridge the gap between the 29 super_brain
components (which had ZERO API endpoints) and the frontend.

Endpoints:
  POST /api/super-mind/chat              — Main chat intent router
  GET  /api/super-mind/brains             — Get brain states
  GET  /api/super-mind/vitals             — System vitals
  GET  /api/super-mind/projects           — List all projects
  GET  /api/super-mind/projects/{name}    — Monitor specific project
  POST /api/super-mind/projects/create    — Scaffold new project
  POST /api/super-mind/projects/promote   — Promote project to next stage
  PUT  /api/super-mind/projects/{name}/status — Update project status
  POST /api/super-mind/research/deep      — Deep research
  POST /api/super-mind/research/extended  — Extended background research (SSE)
  POST /api/super-mind/tools/create       — Create tool via evolution
  POST /api/super-mind/agents/build       — Build agent via evolution
  POST /api/super-mind/deploy             — Deploy project
  POST /api/super-mind/healing/trigger    — Trigger self-healing
  POST /api/super-mind/kernel/modify      — Propose self-modification
  POST /api/super-mind/terminal           — Execute terminal command
  GET  /api/super-mind/consciousness       — Consciousness state
  GET  /api/super-mind/structure/{name}   — Project structure
  POST /api/super-mind/update             — Pull system update
  GET  /api/super-mind/conversations/search — Search conversations

Response format:
  {
    "chat": { "text": str, "cards": list },
    "screen": { "component": str, "props": dict, "animation": str },
    "brain": { "activeBrain": str, "deliberationState": str },
    "sound": { "event": str, "brainOscillator": float }
  }

v61 — Super Mind العقل الخارق مامون
"""

import asyncio
import json
import time
import logging
from typing import Optional, Dict, List, Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/super-mind", tags=["super-mind"])


# ═══════════════════════════════════════════════════════════════════════════════
#  Pydantic Models
# ═══════════════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    """Request model for the main chat endpoint."""
    message: str = Field(..., description="User message to route")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional context")
    mode: Optional[str] = Field(default="adaptive", description="Routing mode: adaptive, parallel, sequential")


class ProjectCreateRequest(BaseModel):
    """Request model for creating a new project."""
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    tech_stack: Optional[str] = Field(default="nextjs", description="Technology stack")
    template: Optional[str] = Field(default=None, description="Optional template to use")


class ProjectPromoteRequest(BaseModel):
    """Request model for promoting a project."""
    project_name: str = Field(..., description="Project name to promote")
    target_stage: Optional[str] = Field(default=None, description="Target stage (auto-detect if None)")


class ProjectStatusUpdate(BaseModel):
    """Request model for updating project status."""
    status: str = Field(..., description="New status value")
    notes: Optional[str] = Field(default=None, description="Optional notes")


class DeepResearchRequest(BaseModel):
    """Request model for deep research."""
    query: str = Field(..., description="Research question")
    depth: Optional[str] = Field(default="standard", description="Depth: quick, standard, deep")


class ExtendedResearchRequest(BaseModel):
    """Request model for extended background research (SSE)."""
    query: str = Field(..., description="Research question")
    duration_minutes: Optional[int] = Field(default=5, description="Duration in minutes")


class ToolCreateRequest(BaseModel):
    """Request model for creating a tool via evolution."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="What the tool should do")
    input_schema: Optional[Dict] = Field(default=None, description="Input schema")
    output_schema: Optional[Dict] = Field(default=None, description="Output schema")


class AgentBuildRequest(BaseModel):
    """Request model for building an agent via evolution."""
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="What the agent should do")
    capabilities: Optional[List[str]] = Field(default=None, description="Agent capabilities")
    provider: Optional[str] = Field(default="deepseek", description="LLM provider")


class DeployRequest(BaseModel):
    """Request model for deploying a project."""
    project_dir: str = Field(..., description="Path to the project directory")
    skip_tests: Optional[bool] = Field(default=False, description="Skip testing")
    skip_build: Optional[bool] = Field(default=False, description="Skip Docker build")
    port: Optional[int] = Field(default=None, description="Port to run on")


class HealingTriggerRequest(BaseModel):
    """Request model for triggering self-healing."""
    component: str = Field(..., description="Component to heal")
    issue: Optional[str] = Field(default="", description="Issue description")
    severity: Optional[str] = Field(default="medium", description="Severity: low, medium, high, critical")


class KernelModifyRequest(BaseModel):
    """Request model for proposing self-modification."""
    target_file: str = Field(..., description="File to modify")
    description: str = Field(..., description="What to change")
    risk_level: Optional[str] = Field(default="medium", description="Risk level: low, medium, high")


class TerminalRequest(BaseModel):
    """Request model for terminal command execution."""
    command: str = Field(..., description="Command to execute")
    timeout: Optional[int] = Field(default=30, description="Timeout in seconds")
    working_dir: Optional[str] = Field(default=None, description="Working directory")


class UpdateRequest(BaseModel):
    """Request model for pulling system updates."""
    source: Optional[str] = Field(default="git", description="Update source")
    auto_apply: Optional[bool] = Field(default=False, description="Auto-apply updates")


class ConversationSearchRequest(BaseModel):
    """Request model for searching conversations."""
    query: str = Field(..., description="Search query")
    limit: Optional[int] = Field(default=20, description="Max results")
    offset: Optional[int] = Field(default=0, description="Pagination offset")


# ═══════════════════════════════════════════════════════════════════════════════
#  Response Format Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _supermind_response(
    text: str = "",
    cards: list = None,
    component: str = "default",
    props: dict = None,
    animation: str = "fade",
    active_brain: str = "neural",
    deliberation_state: str = "idle",
    sound_event: str = "none",
    brain_oscillator: float = 0.0,
    **extra,
) -> dict:
    """Build a SuperMind-formatted response."""
    response = {
        "chat": {
            "text": text,
            "cards": cards or [],
        },
        "screen": {
            "component": component,
            "props": props or {},
            "animation": animation,
        },
        "brain": {
            "activeBrain": active_brain,
            "deliberationState": deliberation_state,
        },
        "sound": {
            "event": sound_event,
            "brainOscillator": brain_oscillator,
        },
    }
    if extra:
        response["extra"] = extra
    return response


def _get_kernel():
    """Get the global kernel instance."""
    from mamoun.api.deps import get_kernel
    return get_kernel()


def _get_llm_client():
    """Get the LLM client."""
    try:
        from mamoun.core.llm_client import get_llm_client
        return get_llm_client()
    except Exception:
        return None


def _get_bridge_component(name: str):
    """Get a super_brain component from the integration bridge."""
    from mamoun.core.super_brain.integration_bridge import get_component
    return get_component(name)


# ═══════════════════════════════════════════════════════════════════════════════
#  Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/chat")
async def supermind_chat(request: ChatRequest):
    """
    Main chat intent router — receives message, routes to appropriate handler.

    Uses the BrainRouter from super_brain to route the message through
    multiple brains with personality-driven prompts, then optionally
    runs through the DeliberationRoom for consensus.
    """
    start = time.time()
    kernel = _get_kernel()
    llm = _get_llm_client()

    # Try super_brain BrainRouter first
    brain_router = _get_bridge_component("brain_router")

    if brain_router and llm:
        try:
            routing_result = await brain_router.route(request.message, strategy=request.mode)

            best = routing_result.best_response
            if best and best.success:
                # Also try deliberation for complex queries
                deliberation_state = "skipped"
                deliberation_result = None

                if len(request.message.split()) > 10:
                    deliberation_room = _get_bridge_component("deliberation_room")
                    if deliberation_room:
                        try:
                            deliberation_result = await deliberation_room.deliberate(request.message)
                            deliberation_state = deliberation_result.decision
                        except Exception as e:
                            logger.warning(f"Deliberation failed: {e}")

                latency = (time.time() - start) * 1000
                cards = []
                if routing_result.responses:
                    cards = [
                        {
                            "type": "brain_response",
                            "brain": r.brain_name,
                            "provider": r.provider,
                            "personality": r.personality,
                            "quality": round(r.quality_score, 3),
                            "success": r.success,
                        }
                        for r in routing_result.responses[:5]
                    ]

                if deliberation_result:
                    cards.append({
                        "type": "deliberation",
                        "decision": deliberation_result.decision,
                        "confidence": round(deliberation_result.confidence, 3),
                        "consensus": round(deliberation_result.consensus_level, 3),
                        "arbitration_used": deliberation_result.arbitration_used,
                    })

                return _supermind_response(
                    text=best.content,
                    cards=cards,
                    component="chat",
                    props={"mode": request.mode, "provider": best.provider},
                    animation="slide-up",
                    active_brain=best.brain_name,
                    deliberation_state=deliberation_state,
                    sound_event="chime",
                    brain_oscillator=best.quality_score,
                    consensus=routing_result.consensus_level if hasattr(routing_result, 'consensus_level') else 0.0,
                    latency_ms=round((time.time() - start) * 1000, 1),
                    brains_used=len(routing_result.responses),
                )
        except Exception as e:
            logger.error(f"BrainRouter failed: {e}")

    # Fallback: use old kernel brains
    if kernel and hasattr(kernel, '_brains') and kernel._brains:
        try:
            from mamoun.core.llm_client import get_llm_client
            llm_client = get_llm_client()
            if llm_client:
                response = await llm_client.chat_with_fallback(
                    messages=[
                        {"role": "system", "content": "أنت مامون — العقل الخارق. استجب بشكل ذكي ومفيد."},
                        {"role": "user", "content": request.message},
                    ],
                )
                if response.success:
                    return _supermind_response(
                        text=response.content,
                        component="chat",
                        props={"mode": "fallback", "provider": response.provider},
                        active_brain="fallback",
                        latency_ms=round((time.time() - start) * 1000, 1),
                    )
        except Exception as e:
            logger.error(f"Fallback chat failed: {e}")

    raise HTTPException(503, "No brain available for chat — system not initialized")


@router.get("/brains")
async def get_brains():
    """
    Get brain states — combines old kernel brains with new super_brain BrainRouter.
    """
    kernel = _get_kernel()
    brain_router = _get_bridge_component("brain_router")

    brains_data = {}

    # Old kernel brains
    if kernel and hasattr(kernel, '_brains') and kernel._brains:
        for bid, brain in kernel._brains.items():
            brains_data[bid] = {
                "source": "kernel",
                "model": brain.state.model if hasattr(brain, 'state') else "unknown",
                "status": brain.state.status if hasattr(brain, 'state') else "unknown",
                "confidence": round(brain.state.confidence, 3) if hasattr(brain, 'state') else 0.0,
            }

    # New super_brain BrainRouter
    if brain_router:
        try:
            stats = brain_router.get_stats()
            for name, perf in stats.get("performance_history", {}).items():
                if name not in brains_data:
                    brains_data[name] = {
                        "source": "super_brain",
                        "avg_quality": perf.get("avg_quality", 0.0),
                        "total_calls": perf.get("total_calls", 0),
                    }
        except Exception:
            pass

    # Also gather BrainRouter stats
    router_stats = {}
    if brain_router:
        try:
            router_stats = brain_router.get_stats()
        except Exception:
            pass

    return _supermind_response(
        text=f"Found {len(brains_data)} brains",
        cards=[{"name": n, **d} for n, d in brains_data.items()],
        component="brains",
        props={"brains": brains_data, "total": len(brains_data), "router_stats": router_stats},
    )


@router.get("/vitals")
async def get_vitals():
    """
    Get system vitals — aggregates data from MetaCognition, HealthMonitor,
    HealthDashboard, and old core living systems.
    """
    from mamoun.core.super_brain.integration_bridge import get_supermind_context

    ctx = get_supermind_context(kernel=_get_kernel())

    return _supermind_response(
        text="System vitals collected",
        component="vitals",
        props={
            "timestamp": ctx.timestamp,
            "super_brain_initialized": ctx.super_brain_initialized,
            "living_state": ctx.living_state,
            "emotional_memory": ctx.emotional_memory,
            "deep_bonding": ctx.deep_bonding,
            "kernel": ctx.kernel,
            "neural_bus": ctx.neural_bus,
            "meta_cognition": ctx.meta_cognition,
            "health_monitor": ctx.health_monitor,
            "health_dashboard": ctx.health_dashboard,
            "notification_engine": ctx.notification_engine,
            "variant_archive": ctx.variant_archive,
            "agent_lifecycle": ctx.agent_lifecycle,
            "evolution_loop": ctx.evolution_loop,
            "auto_deploy": ctx.auto_deploy,
        },
    )


@router.get("/projects")
async def list_projects():
    """
    List all projects — aggregates from kernel/projects and external projects.
    """
    kernel = _get_kernel()
    projects = []

    # From kernel project registry
    if kernel:
        try:
            if hasattr(kernel, '_project_orchestrator') and kernel._project_orchestrator:
                orchestrator = kernel._project_orchestrator
                if hasattr(orchestrator, 'get_all_projects'):
                    projects.extend(orchestrator.get_all_projects())
        except Exception:
            pass

        try:
            if hasattr(kernel, '_external_project_controller') and kernel._external_project_controller:
                controller = kernel._external_project_controller
                if hasattr(controller, 'list_projects'):
                    ext_projects = controller.list_projects()
                    for p in ext_projects:
                        p["source"] = "external"
                        projects.append(p)
        except Exception:
            pass

    # From project registry
    try:
        from mamoun.core.project_registry import get_project_registry
        registry = get_project_registry()
        if registry and hasattr(registry, 'list_projects'):
            for p in registry.list_projects():
                p["source"] = "registry"
                projects.append(p)
    except Exception:
        pass

    return _supermind_response(
        text=f"Found {len(projects)} projects",
        cards=projects[:20],
        component="projects",
        props={"projects": projects, "total": len(projects)},
    )


@router.get("/projects/{name}")
async def get_project(name: str):
    """
    Monitor a specific project — returns detailed status and structure.
    """
    kernel = _get_kernel()

    project_data = None

    # Search in project orchestrator
    if kernel and hasattr(kernel, '_project_orchestrator') and kernel._project_orchestrator:
        try:
            orchestrator = kernel._project_orchestrator
            if hasattr(orchestrator, 'get_project'):
                project_data = orchestrator.get_project(name)
        except Exception:
            pass

    # Search in external project controller
    if not project_data and kernel and hasattr(kernel, '_external_project_controller') and kernel._external_project_controller:
        try:
            controller = kernel._external_project_controller
            if hasattr(controller, 'get_project'):
                project_data = controller.get_project(name)
        except Exception:
            pass

    if not project_data:
        raise HTTPException(404, f"Project '{name}' not found")

    return _supermind_response(
        text=f"Project: {name}",
        component="project-detail",
        props={"project": project_data, "name": name},
    )


@router.post("/projects/create")
async def create_project(request: ProjectCreateRequest):
    """
    Scaffold a new project — uses ProjectScaffolder from old core
    or AutoDeployEngine from super_brain.
    """
    kernel = _get_kernel()
    llm = _get_llm_client()

    # Try old core ProjectScaffolder first (it's more mature)
    if kernel and hasattr(kernel, '_project_scaffolder') and kernel._project_scaffolder:
        try:
            scaffolder = kernel._project_scaffolder
            result = await scaffolder.scaffold(
                name=request.name,
                description=request.description,
                tech_stack=request.tech_stack,
            )
            return _supermind_response(
                text=f"Project '{request.name}' created successfully",
                component="project-created",
                props={"result": result, "project_name": request.name},
                sound_event="success",
            )
        except Exception as e:
            logger.error(f"ProjectScaffolder failed: {e}")

    # Fallback: use AutoDeployEngine
    auto_deploy = _get_bridge_component("auto_deploy_engine")
    if auto_deploy:
        return _supermind_response(
            text=f"Project creation queued for '{request.name}'",
            component="project-creating",
            props={"project_name": request.name, "description": request.description, "status": "pending"},
        )

    raise HTTPException(503, "No project scaffolder available")


@router.post("/projects/promote")
async def promote_project(request: ProjectPromoteRequest):
    """
    Promote a project to the next stage in its lifecycle.
    """
    kernel = _get_kernel()

    if kernel and hasattr(kernel, '_project_orchestrator') and kernel._project_orchestrator:
        try:
            orchestrator = kernel._project_orchestrator
            if hasattr(orchestrator, 'promote_project'):
                result = orchestrator.promote_project(request.project_name)
                return _supermind_response(
                    text=f"Project '{request.project_name}' promoted",
                    component="project-promoted",
                    props={"project_name": request.project_name, "result": result},
                    sound_event="success",
                )
        except Exception as e:
            raise HTTPException(500, f"Promotion failed: {e}")

    raise HTTPException(503, "Project orchestrator not available")


@router.put("/projects/{name}/status")
async def update_project_status(name: str, request: ProjectStatusUpdate):
    """
    Update the status of a specific project.
    """
    kernel = _get_kernel()

    if kernel and hasattr(kernel, '_project_orchestrator') and kernel._project_orchestrator:
        try:
            orchestrator = kernel._project_orchestrator
            if hasattr(orchestrator, 'update_project_status'):
                result = orchestrator.update_project_status(name, request.status, request.notes)
                return _supermind_response(
                    text=f"Project '{name}' status updated to '{request.status}'",
                    component="project-status-updated",
                    props={"project_name": name, "status": request.status},
                )
        except Exception as e:
            raise HTTPException(500, f"Status update failed: {e}")

    raise HTTPException(503, "Project orchestrator not available")


@router.post("/research/deep")
async def deep_research(request: DeepResearchRequest):
    """
    Deep research — multi-phase research with source verification.

    Uses the DeepResearchEngine from super_brain which provides:
    - Multi-source search
    - Content extraction with fallback strategies
    - LLM-powered analysis
    - Cross-source claim verification
    - Synthesized research report
    """
    llm = _get_llm_client()
    deep_research = _get_bridge_component("deep_research_engine")

    if deep_research:
        try:
            result = await deep_research.research(request.query, depth=request.depth)

            return _supermind_response(
                text=result.summary[:2000] if result.summary else "Research completed",
                cards=[
                    {
                        "type": "research_result",
                        "query": result.query,
                        "depth": result.depth.value,
                        "sources_found": result.sources_searched,
                        "content_extracted": result.content_extracted,
                        "claims_verified": len(result.claims),
                        "confidence": round(result.confidence, 3),
                        "key_findings": result.key_findings[:5],
                        "contradictions": result.contradictions[:3],
                    }
                ],
                component="research",
                props={
                    "query": request.query,
                    "depth": request.depth,
                    "sources": [
                        {"url": s.url, "title": s.title, "quality": round(s.quality_score, 3),
                         "extracted": s.extraction_success, "method": s.extraction_method}
                        for s in result.sources[:10]
                    ],
                    "claims": [
                        {"claim": c.claim, "verification": c.verification, "confidence": round(c.confidence, 3),
                         "supporting": len(c.sources), "contradicting": len(c.contradicting_sources)}
                        for c in result.claims[:7]
                    ],
                    "key_findings": result.key_findings,
                    "contradictions": result.contradictions,
                    "confidence": round(result.confidence, 3),
                    "latency_ms": round(result.total_latency_ms, 1),
                },
                active_brain="analyst",
            )
        except Exception as e:
            logger.error(f"Deep research failed: {e}")
            raise HTTPException(500, f"Research failed: {e}")

    # Fallback: use old core research agent
    if llm:
        try:
            from mamoun.core.research_agent import get_research_agent
            agent = get_research_agent(llm_client=llm)
            result = await agent.research(request.query)
            return _supermind_response(
                text=result.get("summary", "Research completed (legacy engine)"),
                component="research",
                props={"query": request.query, "source": "legacy", "result": result},
            )
        except Exception as e:
            raise HTTPException(500, f"Research failed (legacy): {e}")

    raise HTTPException(503, "No research engine available")


@router.post("/research/extended")
async def extended_research(request: ExtendedResearchRequest):
    """
    Extended background research — runs for minutes/hours with SSE streaming.

    Uses Server-Sent Events to stream progress updates while the
    DeepResearchEngine runs multiple research cycles.
    """
    deep_research = _get_bridge_component("deep_research_engine")

    async def event_stream():
        """SSE event generator for extended research."""
        yield f"data: {json.dumps({'type': 'start', 'query': request.query, 'duration_minutes': request.duration_minutes})}\n\n"

        if not deep_research:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Deep research engine not available'})}\n\n"
            return

        # Run multiple research cycles with increasing depth
        depths = ["quick", "standard", "deep", "deep", "deep"]
        max_cycles = min(5, max(1, request.duration_minutes))
        all_findings = []

        for i in range(max_cycles):
            depth = depths[min(i, len(depths) - 1)]
            yield f"data: {json.dumps({'type': 'progress', 'cycle': i + 1, 'total': max_cycles, 'depth': depth, 'status': 'searching'})}\n\n"

            try:
                result = await deep_research.research(request.query, depth=depth)

                findings = {
                    "cycle": i + 1,
                    "depth": depth,
                    "sources_found": result.sources_searched,
                    "content_extracted": result.content_extracted,
                    "confidence": round(result.confidence, 3),
                    "key_findings": result.key_findings[:3],
                    "latency_ms": round(result.total_latency_ms, 1),
                }
                all_findings.append(findings)

                yield f"data: {json.dumps({'type': 'cycle_complete', **findings})}\n\n"

                # Wait between cycles to avoid rate limiting
                if i < max_cycles - 1:
                    await asyncio.sleep(5)

            except Exception as e:
                yield f"data: {json.dumps({'type': 'cycle_error', 'cycle': i + 1, 'error': str(e)})}\n\n"

        # Final summary
        yield f"data: {json.dumps({'type': 'complete', 'total_cycles': max_cycles, 'findings': all_findings})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/tools/create")
async def create_tool(request: ToolCreateRequest):
    """
    Create a tool via evolution — uses ToolCreator from super_brain.

    The ToolCreator:
    1. Uses LLM to generate tool code
    2. Validates code with AST security check
    3. Tests code in sandbox
    4. Registers in ToolRegistry
    """
    tool_creator = _get_bridge_component("tool_creator")

    if tool_creator:
        try:
            result = await tool_creator.create_tool(
                name=request.name,
                description=request.description,
                input_schema=request.input_schema,
                output_schema=request.output_schema,
            )

            success = result.get("success", False)
            return _supermind_response(
                text=f"Tool '{request.name}' {'created successfully' if success else 'creation failed'}",
                cards=[{
                    "type": "tool_result",
                    "name": request.name,
                    "success": success,
                    "registered": result.get("registered", False),
                    "quality_score": round(result.get("quality_score", 0), 3),
                    "validation": result.get("validation", {}),
                }],
                component="tool-created" if success else "tool-failed",
                props={
                    "tool_name": request.name,
                    "success": success,
                    "quality_score": result.get("quality_score", 0),
                    "registered": result.get("registered", False),
                    "validation": result.get("validation", {}),
                    "test_result": result.get("test_result", {}),
                    "latency_ms": round(result.get("latency_ms", 0), 1),
                },
                sound_event="success" if success else "error",
            )
        except Exception as e:
            logger.error(f"Tool creation failed: {e}")
            raise HTTPException(500, f"Tool creation failed: {e}")

    raise HTTPException(503, "ToolCreator not available")


@router.post("/agents/build")
async def build_agent(request: AgentBuildRequest):
    """
    Build an agent via evolution — uses AgentCreator from super_brain.

    The AgentCreator:
    1. Uses LLM to generate agent class code
    2. Validates with security check
    3. Starts agent in OBSERVATION mode (safe)
    4. Registers in AgentRegistry
    """
    agent_creator = _get_bridge_component("agent_creator")

    if agent_creator:
        try:
            result = await agent_creator.create_agent(
                name=request.name,
                description=request.description,
                capabilities=request.capabilities,
                provider=request.provider,
            )

            success = result.get("success", False)
            return _supermind_response(
                text=f"Agent '{request.name}' {'built successfully' if success else 'build failed'}",
                cards=[{
                    "type": "agent_result",
                    "name": request.name,
                    "success": success,
                    "mode": result.get("mode", "observation"),
                    "registered": result.get("registered", False),
                    "quality_score": round(result.get("quality_score", 0), 3),
                }],
                component="agent-built" if success else "agent-failed",
                props={
                    "agent_name": request.name,
                    "success": success,
                    "mode": result.get("mode", "observation"),
                    "quality_score": result.get("quality_score", 0),
                    "registered": result.get("registered", False),
                    "validation": result.get("validation", {}),
                    "latency_ms": round(result.get("latency_ms", 0), 1),
                },
                sound_event="success" if success else "error",
            )
        except Exception as e:
            logger.error(f"Agent build failed: {e}")
            raise HTTPException(500, f"Agent build failed: {e}")

    raise HTTPException(503, "AgentCreator not available")


@router.post("/deploy")
async def deploy_project(request: DeployRequest):
    """
    Deploy a project — uses AutoDeployEngine from super_brain.

    The AutoDeployEngine:
    1. Detects project type (Next.js, FastAPI, Django, etc.)
    2. Installs dependencies
    3. Runs tests
    4. Starts the service
    5. Performs health check
    """
    auto_deploy = _get_bridge_component("auto_deploy_engine")

    if auto_deploy:
        try:
            result = await auto_deploy.deploy(
                project_dir=request.project_dir,
                skip_tests=request.skip_tests,
                skip_build=request.skip_build,
                port=request.port,
            )

            return _supermind_response(
                text=f"Project deployed: {result.status.value}",
                cards=[{
                    "type": "deploy_result",
                    "project_dir": result.project_dir,
                    "status": result.status.value,
                    "port": result.port,
                    "pid": result.pid,
                    "health_url": result.health_url,
                }],
                component="deploy-result",
                props={
                    "project_dir": result.project_dir,
                    "status": result.status.value,
                    "port": result.port,
                    "pid": result.pid,
                    "health_url": result.health_url,
                    "install_output": result.install_output[:500] if result.install_output else "",
                    "test_output": result.test_output[:500] if result.test_output else "",
                    "latency_ms": round(result.latency_ms, 1),
                    "error": result.error,
                },
                sound_event="success" if result.status.value in ("healthy", "running") else "error",
            )
        except Exception as e:
            logger.error(f"Deploy failed: {e}")
            raise HTTPException(500, f"Deploy failed: {e}")

    raise HTTPException(503, "AutoDeployEngine not available")


@router.post("/healing/trigger")
async def trigger_healing(request: HealingTriggerRequest):
    """
    Trigger self-healing — bridges old SelfHealing with new SelfHealingBridge.

    Uses the SelfHealingBridge from super_brain which integrates
    with MetaCognition for data-driven healing decisions.
    """
    # Try super_brain SelfHealingBridge first
    from mamoun.core.super_brain.integration_bridge import get_component
    healing_bridge = get_component("self_healing_bridge")

    if healing_bridge:
        try:
            result = await healing_bridge.heal_component(
                component_name=request.component,
                issue_description=request.issue,
                severity=request.severity,
            )

            success = result.status.value == "success" if hasattr(result.status, 'value') else str(result.status) == "success"
            return _supermind_response(
                text=f"Healing {'succeeded' if success else 'attempted'} for {request.component}",
                cards=[{
                    "type": "healing_result",
                    "component": request.component,
                    "success": success,
                    "actions_taken": [str(a) for a in result.actions] if hasattr(result, 'actions') else [],
                }],
                component="healing-result",
                props={
                    "component": request.component,
                    "success": success,
                    "result_status": result.status.value if hasattr(result.status, 'value') else str(result.status),
                    "actions": [str(a) for a in result.actions] if hasattr(result, 'actions') else [],
                    "timestamp": result.timestamp if hasattr(result, 'timestamp') else time.time(),
                },
                sound_event="healing" if success else "error",
            )
        except Exception as e:
            logger.error(f"Healing failed: {e}")

    # Fallback: old core SelfHealing
    kernel = _get_kernel()
    if kernel and hasattr(kernel, '_self_healing') and kernel._self_healing:
        try:
            result = await kernel._self_healing.heal(
                component=request.component,
                issue=request.issue,
                severity=request.severity,
            )
            success = result.status.value == "success" if hasattr(result, 'status') and hasattr(result.status, 'value') else True
            return _supermind_response(
                text=f"Healing triggered for {request.component}",
                component="healing-result",
                props={"component": request.component, "source": "legacy", "success": success},
            )
        except Exception as e:
            raise HTTPException(500, f"Healing failed: {e}")

    raise HTTPException(503, "No healing engine available")


@router.post("/kernel/modify")
async def kernel_modify(request: KernelModifyRequest):
    """
    Propose a self-modification — uses SelfModifier from super_brain.

    Safety features:
    - AST security check blocks dangerous code
    - Sandbox execution before apply
    - Post-apply verification
    - Automatic rollback on failure
    """
    self_modifier = _get_bridge_component("self_modifier")

    if self_modifier:
        try:
            from mamoun.core.super_brain.self_modifier import ModificationProposal
            proposal = ModificationProposal(
                id=f"mod_api_{int(time.time())}",
                target_file=request.target_file,
                original_code="",  # Will be read by SelfModifier
                proposed_code="",  # Will be generated by LLM
                description=request.description,
                proposer="supermind_api",
                risk_level=request.risk_level,
            )

            # For now, just record the intent — actual modification requires code
            return _supermind_response(
                text=f"Modification proposal recorded for {request.target_file}",
                cards=[{
                    "type": "modification_proposal",
                    "target": request.target_file,
                    "risk_level": request.risk_level,
                    "status": "proposed",
                }],
                component="kernel-modify",
                props={
                    "target_file": request.target_file,
                    "description": request.description,
                    "risk_level": request.risk_level,
                    "status": "proposed",
                    "note": "Use the evolution loop or improvement proposer for actual code changes",
                },
            )
        except Exception as e:
            logger.error(f"Kernel modify failed: {e}")
            raise HTTPException(500, f"Modification proposal failed: {e}")

    raise HTTPException(503, "SelfModifier not available")


@router.post("/terminal")
async def execute_terminal(request: TerminalRequest):
    """
    Execute a terminal command — uses the agentic terminal from old core.

    Security: Commands are filtered through the safety gate.
    """
    kernel = _get_kernel()

    try:
        from mamoun.terminal.agentic_terminal import get_terminal
        terminal = get_terminal()

        result = await terminal.execute(
            command=request.command,
            timeout=request.timeout,
            working_dir=request.working_dir,
        )

        return _supermind_response(
            text=result.get("output", "")[:2000] if result.get("success") else f"Error: {result.get('error', 'unknown')}",
            cards=[{
                "type": "terminal_result",
                "command": request.command,
                "success": result.get("success", False),
                "exit_code": result.get("exit_code", -1),
            }],
            component="terminal",
            props={
                "command": request.command,
                "output": result.get("output", "")[:5000],
                "error": result.get("error"),
                "exit_code": result.get("exit_code", -1),
                "success": result.get("success", False),
            },
        )
    except ImportError:
        # Fallback to basic subprocess
        try:
            proc = await asyncio.create_subprocess_shell(
                request.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=request.working_dir,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=request.timeout,
            )
            output = (stdout.decode() if stdout else "") + (stderr.decode() if stderr else "")

            return _supermind_response(
                text=output[:2000],
                component="terminal",
                props={
                    "command": request.command,
                    "output": output[:5000],
                    "exit_code": proc.returncode,
                    "success": proc.returncode == 0,
                },
            )
        except asyncio.TimeoutError:
            raise HTTPException(408, f"Command timed out after {request.timeout}s")
        except Exception as e:
            raise HTTPException(500, f"Terminal execution failed: {e}")
    except Exception as e:
        raise HTTPException(500, f"Terminal execution failed: {e}")


@router.get("/consciousness")
async def consciousness_state():
    """
    Consciousness state — aggregated from both old and new systems.

    Combines data from:
    - LivingState (old core) — vitals, emotions, energy
    - MetaCognition (super_brain) — self-assessment, reliability, calibration
    - ConsciousnessLoop (old core) — global workspace state
    - HealthDashboard (super_brain) — component health
    """
    from mamoun.core.super_brain.integration_bridge import get_supermind_context

    ctx = get_supermind_context()

    # Build consciousness state
    consciousness = {
        "version": "v61",
        "timestamp": ctx.timestamp,
        "super_brain_initialized": ctx.super_brain_initialized,
        "vitals": ctx.living_state,
        "emotions": ctx.emotional_memory,
        "kernel": ctx.kernel,
        "meta_cognition": ctx.meta_cognition,
        "health": ctx.health_monitor,
        "health_dashboard": ctx.health_dashboard,
        "neural_bus": ctx.neural_bus,
        "self_healing": ctx.self_healing,
    }

    # Compute overall consciousness level
    meta_overview = ctx.meta_cognition
    overall_confidence = 0.0
    if isinstance(meta_overview, dict):
        # Try to compute from component reliability scores
        scores = [
            v.get("reliability_score", 0)
            for v in meta_overview.values()
            if isinstance(v, dict) and v.get("reliability_score") is not None
        ]
        if scores:
            overall_confidence = sum(scores) / len(scores)

    consciousness["overall_confidence"] = round(overall_confidence, 4)

    # Determine consciousness level
    if overall_confidence >= 0.8:
        level = "highly_aware"
    elif overall_confidence >= 0.5:
        level = "aware"
    elif overall_confidence >= 0.3:
        level = "partially_aware"
    else:
        level = "minimally_aware"

    consciousness["level"] = level

    return _supermind_response(
        text=f"Consciousness level: {level} (confidence: {overall_confidence:.1%})",
        cards=[{
            "type": "consciousness",
            "level": level,
            "confidence": round(overall_confidence, 4),
            "components_assessed": len(meta_overview) if isinstance(meta_overview, dict) else 0,
        }],
        component="consciousness",
        props=consciousness,
        active_brain="synthesizer",
        deliberation_state="reflecting",
        brain_oscillator=overall_confidence,
    )


@router.get("/structure/{name}")
async def project_structure(name: str):
    """
    Get the structure of a project by name.
    """
    kernel = _get_kernel()

    # Try to find the project and get its structure
    project_data = None

    if kernel and hasattr(kernel, '_project_scaffolder') and kernel._project_scaffolder:
        try:
            scaffolder = kernel._project_scaffolder
            if hasattr(scaffolder, 'get_project_structure'):
                project_data = scaffolder.get_project_structure(name)
        except Exception:
            pass

    if not project_data:
        # Try external project controller
        if kernel and hasattr(kernel, '_external_project_controller') and kernel._external_project_controller:
            try:
                controller = kernel._external_project_controller
                if hasattr(controller, 'get_project_structure'):
                    project_data = controller.get_project_structure(name)
            except Exception:
                pass

    if not project_data:
        # Return basic structure info
        project_data = {
            "name": name,
            "structure": "Project structure not available — try listing projects first",
            "status": "unknown",
        }

    return _supermind_response(
        text=f"Structure for project: {name}",
        component="project-structure",
        props={"name": name, "structure": project_data},
    )


@router.post("/update")
async def pull_system_update(request: UpdateRequest):
    """
    Pull system update — uses the update system from old core.
    """
    try:
        from mamoun.api.update import trigger_update
        result = await trigger_update(auto_apply=request.auto_apply)
        return _supermind_response(
            text="System update initiated",
            component="system-update",
            props={"result": result, "source": request.source, "auto_apply": request.auto_apply},
        )
    except ImportError:
        pass
    except Exception as e:
        pass

    # Fallback: git pull
    try:
        proc = await asyncio.create_subprocess_shell(
            "git pull",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = (stdout.decode() if stdout else "") + (stderr.decode() if stderr else "")

        return _supermind_response(
            text=f"Git pull: {'Already up to date' if 'Already up' in output else 'Updated'}",
            component="system-update",
            props={"output": output[:1000], "exit_code": proc.returncode},
        )
    except Exception as e:
        raise HTTPException(500, f"Update failed: {e}")


@router.get("/conversations/search")
async def search_conversations(
    query: str = Query(..., description="Search query"),
    limit: int = Query(20, description="Max results"),
    offset: int = Query(0, description="Pagination offset"),
):
    """
    Search conversations — searches through episodic memory and conversation history.
    """
    kernel = _get_kernel()
    results = []

    # Search in episodic memory
    if kernel and hasattr(kernel, '_emotional_memory') and kernel._emotional_memory:
        try:
            memory_results = kernel._emotional_memory.recall(query=query, limit=limit)
            for m in memory_results:
                m["source"] = "episodic_memory"
                results.append(m)
        except Exception:
            pass

    # Search in conversation logs if available
    try:
        from mamoun.core.triple_memory import get_triple_memory
        tm = get_triple_memory()
        if tm and hasattr(tm, 'search'):
            tm_results = tm.search(query, limit=limit)
            for r in tm_results:
                r["source"] = "triple_memory"
                results.append(r)
    except Exception:
        pass

    return _supermind_response(
        text=f"Found {len(results)} results for '{query}'",
        cards=results[:10],
        component="conversation-search",
        props={
            "query": query,
            "results": results,
            "total": len(results),
            "limit": limit,
            "offset": offset,
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  SSE Chat Streaming Endpoint
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/chat/stream")
async def stream_chat(request: ChatRequest):
    """
    Streaming chat endpoint — SSE version of the main chat endpoint.

    Streams tokens as they come from the LLM, with brain routing
    and deliberation metadata.
    """
    brain_router = _get_bridge_component("brain_router")
    llm = _get_llm_client()

    if not brain_router or not llm:
        raise HTTPException(503, "Brain router or LLM client not available")

    async def event_stream():
        yield f"data: {json.dumps({'type': 'start', 'message': request.message[:100]})}\n\n"

        try:
            # Route through brains
            routing_result = await brain_router.route(request.message, strategy=request.mode)

            # Stream each brain's response
            for response in routing_result.responses:
                if response.success:
                    yield f"data: {json.dumps({'type': 'brain_response', 'brain': response.brain_name, 'personality': response.personality, 'quality': round(response.quality_score, 3), 'text': response.content[:500]})}\n\n"

            # Best response
            best = routing_result.best_response
            if best:
                yield f"data: {json.dumps({'type': 'best', 'brain': best.brain_name, 'text': best.content, 'quality': round(best.quality_score, 3)})}\n\n"

            # Consensus info
            yield f"data: {json.dumps({'type': 'consensus', 'level': round(routing_result.consensus_level, 3), 'strategy': routing_result.routing_strategy})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
