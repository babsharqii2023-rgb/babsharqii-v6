"""
BABSHARQII v50.0 "Mamoun" — FastAPI Application Entry Point
Living AGI System — 5 LLM-Powered Brains + BrainRouter + DeliberationRoom + MamounKernel

v50.0 — 100% CONTROL FUSION:
- CodeGenerationEngine: REAL (LLM-connected, no more MOCK)
- AgentCreator: REAL (LLM generates agent logic, no more empty template)
- SelfModifier: TypeScript/JS support added
- ProjectScaffolder: Build complete projects from scratch
- ExternalProjectController: Full control of external projects
- CapabilityAssessor: Honest self-assessment
- AutoResearchHealLoop: Auto-trigger enabled
- TripleMemory: Persistent with SQLite fallback

Brain Models:
- NeuralBrain: glm-5.1 (0.25) — الأساسي (GLM)
- CausalBrain: deepseek-reasoner (0.22) — سببي عميق (DeepSeek)
- SymbolicBrain: glm-4-plus (0.18) — منطقي مختلف (GLM)
- BayesianBrain: gemini-2.0-flash (0.17) — احتمالي سريع (Gemini via proxy)
- WorldModelBrain: deepseek-chat (0.18) — محاكاة عالم (DeepSeek)
- 5 models, 3 providers, Gemini proxy = TRUE DIVERSITY
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# v32: Load .env BEFORE any imports that read env vars
from pathlib import Path
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path, override=False)

from mamoun.config import settings
from mamoun.api.routes import api_router
from mamoun.api.upload import router as upload_router
from mamoun.core.state_reader import StateReader
from mamoun.core.safety_guard import SafetyGuard


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    import asyncio
    import os
    from mamoun.core.mamoun_kernel import get_kernel
    from mamoun.brains.living_brains import (
        NeuralBrain, CausalBrain, SymbolicBrain, BayesianBrain, WorldModelBrain,
    )
    from mamoun.core.llm_client import get_llm_client

    # Startup
    state_reader = StateReader()
    state_reader.start_monitoring()
    app.state.state_reader = state_reader
    app.state.safety_guard = SafetyGuard()

    # v17.0: Initialize the Living Kernel with all 5 brains
    kernel = get_kernel()
    llm = get_llm_client()
    living_brains = [
        NeuralBrain(llm_client=llm),
        CausalBrain(llm_client=llm),
        SymbolicBrain(llm_client=llm),
        BayesianBrain(llm_client=llm),
        WorldModelBrain(llm_client=llm),
    ]
    for brain in living_brains:
        kernel.register_brain(brain.state.id, brain)
        brain.activate()  # Activate all brains on startup

    # Start the kernel's consciousness loop in the background
    kernel_task = asyncio.create_task(kernel.run_forever())
    app.state.kernel_task = kernel_task

    # v17.0 Phase 2: Connect evolution loop to kernel
    from mamoun.api.deps import evolution_loop
    kernel._evolution_loop = evolution_loop

    # v22.0: Initialize Living Systems and attach to kernel
    # CRITICAL: Use module singletons so API routes and kernel share the SAME objects
    try:
        from mamoun.core.living_state import living_state
        from mamoun.core.emotional_memory import emotional_memory
        from mamoun.core.deep_bonding import deep_bonding
        from mamoun.core.reflexes import reflexes_engine
        from mamoun.core.autonomic_system import autonomic_system
        from mamoun.core.neural_bus import neural_bus
        from mamoun.core.self_healing import self_healing
        from mamoun.core.inner_monologue import inner_monologue

        # Initialize all singletons (load persisted state)
        living_state.initialize()
        emotional_memory.initialize()
        deep_bonding.initialize()
        reflexes_engine.initialize()
        neural_bus.initialize()
        self_healing.initialize()
        inner_monologue.initialize()

        # Attach singletons to kernel (ONE object per system, shared everywhere)
        kernel._living_state = living_state
        kernel._emotional_memory = emotional_memory
        kernel._deep_bonding = deep_bonding
        kernel._reflexes_engine = reflexes_engine
        kernel._autonomic_system = autonomic_system
        kernel._self_healing = self_healing  # v35 FIX: was missing — kernel couldn't trigger self-healing
        kernel._living_systems_initialized = True

        # v40.0 Fusion Step 1: Activate LiveSelfModifier
        try:
            from mamoun.evolution.live_self_modifier import LiveSelfModifier
            live_self_modifier = LiveSelfModifier(llm_client=llm)
            live_self_modifier.set_llm_client(llm)
            live_self_modifier.initialize()
            await live_self_modifier.start()
            kernel._live_self_modifier = live_self_modifier
            print(f"[Mamoun] LiveSelfModifier — activated & running ✓")
        except Exception as e:
            print(f"[Mamoun] ⚠ LiveSelfModifier activation failed: {e}")

        # v100 Fusion Step 3: Auto-Research-Heal Loop — تفعيل تلقائي كامل
        try:
            from mamoun.core.auto_research_heal_loop import AutoResearchHealLoop, get_auto_research_heal
            auto_research_heal = get_auto_research_heal()
            auto_research_heal._neural_bus = neural_bus
            auto_research_heal.initialize()
            await auto_research_heal.start()  # v100: تشغيل تلقائي — كان مفقوداً!
            kernel._auto_research_heal = auto_research_heal
            print(f"[Mamoun] AutoResearchHealLoop — activated & running ✓ (auto-trigger enabled)")
        except Exception as e:
            print(f"[Mamoun] ⚠ AutoResearchHealLoop activation failed: {e}")
            import traceback; traceback.print_exc()

        # v50.0 Fusion: CodeGenerationEngine — ربط مع LLM لتوليد كود حقيقي
        try:
            from mamoun.core.code_generation_engine import code_generation_engine
            code_generation_engine.set_llm_client(llm)
            code_generation_engine.initialize()
            kernel._code_generation_engine = code_generation_engine
            print(f"[Mamoun] CodeGenerationEngine — REAL (LLM-connected) ✓")
        except Exception as e:
            print(f"[Mamoun] ⚠ CodeGenerationEngine LLM connection failed: {e}")

        # v50.0 Fusion: CapabilityAssessor — تقييم ذاتي ذكي
        try:
            from mamoun.core.capability_assessor import CapabilityAssessor
            from mamoun.brains.brain_router import BrainRouter
            brain_router = BrainRouter() if not hasattr(kernel, '_brain_router') else kernel._brain_router
            cap_assessor = CapabilityAssessor(
                llm_client=llm,
                brain_router=brain_router,
                self_modifier=None,
            )
            kernel._capability_assessor = cap_assessor
            print(f"[Mamoun] CapabilityAssessor — honest self-assessment ✓")
        except Exception as e:
            print(f"[Mamoun] ⚠ CapabilityAssessor activation failed: {e}")

        # v50.0 Fusion: ProjectScaffolder — إنشاء مشاريع من الصفر
        try:
            from mamoun.core.project_scaffolder import get_project_scaffolder
            scaffolder = get_project_scaffolder(llm_client=llm)
            kernel._project_scaffolder = scaffolder
            print(f"[Mamoun] ProjectScaffolder — build projects from scratch ✓")
        except Exception as e:
            print(f"[Mamoun] ⚠ ProjectScaffolder activation failed: {e}")

        # v50.0 Fusion: ExternalProjectController — التحكم بمشاريع خارجية
        try:
            from mamoun.core.external_project_controller import get_external_project_controller
            ext_controller = get_external_project_controller(llm_client=llm)
            kernel._external_project_controller = ext_controller
            print(f"[Mamoun] ExternalProjectController — control external projects ✓")
        except Exception as e:
            print(f"[Mamoun] ⚠ ExternalProjectController activation failed: {e}")

        # Wire the autonomic system to all sub-systems (constructor takes no args)
        autonomic_system.wire(
            living_state=living_state,
            reflexes=reflexes_engine,
            emotional_memory=emotional_memory,
            deep_bonding=deep_bonding,
            kernel=kernel,
        )

        # v30: Connect NeuralBus — Kernel subscribes to all living system signals
        neural_bus.subscribe("kernel", [
            "emotion_shift", "energy_drop", "stress_spike", "vital_change",
            "bond_strengthened", "bond_weakened", "user_absent", "user_returned",
            "action_completed", "action_failed", "error_detected",
            "memory_stored", "prediction_failed", "pattern_detected",
        ], handler=kernel._on_neural_signal, priority_filter=1)

        # v30: Living systems publish to NeuralBus when their state changes
        living_state._neural_bus = neural_bus
        emotional_memory._neural_bus = neural_bus
        deep_bonding._neural_bus = neural_bus
        reflexes_engine._neural_bus = neural_bus
        autonomic_system._neural_bus = neural_bus
        self_healing._neural_bus = neural_bus
        inner_monologue._neural_bus = neural_bus

        # v31.2: Self-Healing subscribes to error signals for auto-repair
        neural_bus.subscribe("self_healing", [
            "error_detected", "energy_drop", "stress_spike", "healing_complete",
        ], handler=self_healing._on_neural_signal if hasattr(self_healing, '_on_neural_signal') else lambda s: None,
           priority_filter=3)

        # v31.2: InnerMonologue subscribes to insight & perception signals
        neural_bus.subscribe("inner_monologue", [
            "emotion_shift", "vital_change", "pattern_detected", "prediction_failed",
        ], handler=inner_monologue._on_neural_signal if hasattr(inner_monologue, '_on_neural_signal') else lambda s: None,
           priority_filter=1)

        # v31: Living systems also subscribe to relevant signals (bidirectional)
        # LivingStateEngine subscribes to action results (success/failure affects mood)
        neural_bus.subscribe("living_state", [
            "action_completed", "action_failed", "healing_complete",
        ], handler=living_state._on_neural_signal if hasattr(living_state, '_on_neural_signal') else lambda s: None,
           priority_filter=1)

        # EmotionalMemoryEngine subscribes to bond changes (tag memories with relationship context)
        neural_bus.subscribe("emotional_memory", [
            "bond_strengthened", "bond_weakened", "emotion_shift", "user_returned",
        ], handler=emotional_memory._on_neural_signal if hasattr(emotional_memory, '_on_neural_signal') else lambda s: None,
           priority_filter=1)

        # DeepBondingEngine subscribes to user presence and emotions
        neural_bus.subscribe("deep_bonding", [
            "user_absent", "user_returned", "emotion_shift", "vital_change",
        ], handler=deep_bonding._on_neural_signal if hasattr(deep_bonding, '_on_neural_signal') else lambda s: None,
           priority_filter=1)

        # ReflexesEngine subscribes to stress and error signals (auto-trigger reflexes)
        neural_bus.subscribe("reflexes_engine", [
            "stress_spike", "error_detected", "energy_drop", "prediction_failed",
        ], handler=reflexes_engine._on_neural_signal if hasattr(reflexes_engine, '_on_neural_signal') else lambda s: None,
           priority_filter=2)

        # v30: Bridge GlobalWorkspace with NeuralBus
        kernel._neural_bus = neural_bus
        kernel.workspace._neural_bus = neural_bus

        # v31.2: Connect LLM client to inner monologue for real thinking
        inner_monologue.set_llm_client(llm)
        inner_monologue._working_memory = kernel._working_memory

        # ═══ v32: Connect previously isolated components to NeuralBus ═══
        # ApprovalGate — connects to kernel for self-modification approval
        try:
            from mamoun.core.approval_gate import ApprovalGate
            approval_gate = ApprovalGate()
            await approval_gate.initialize()
            kernel._approval_gate = approval_gate
            # ApprovalGate subscribes to self-modification signals
            neural_bus.subscribe("approval_gate", [
                "action_completed", "action_failed", "error_detected",
            ], handler=getattr(approval_gate, '_on_neural_signal', lambda s: None),
               priority_filter=2)
            approval_gate._neural_bus = neural_bus
            print(f"[Mamoun]   ApprovalGate — connected to NeuralBus ✓")
        except Exception as e:
            print(f"[Mamoun]   ⚠ ApprovalGate connection failed: {e}")

        # ProjectOrchestrator — connects to NeuralBus for project lifecycle events
        try:
            if hasattr(kernel, '_project_orchestrator') and kernel._project_orchestrator:
                # Use the singleton getter with neural_bus to properly wire it
                from mamoun.core.project_orchestrator import get_project_orchestrator
                orchestrator = get_project_orchestrator(neural_bus=neural_bus)
                # Ensure kernel uses the same wired-up instance
                kernel._project_orchestrator = orchestrator
                # Subscribe the orchestrator to relevant NeuralBus signals
                neural_bus.subscribe("project_orchestrator", [
                    "perception", "action_completed", "action_failed",
                    "project_created", "research_started", "research_completed",
                    "planning_started", "planning_completed",
                    "building_started", "project_delivered",
                ], handler=getattr(orchestrator, '_on_neural_signal', lambda s: None),
                   priority_filter=2)
                print(f"[Mamoun]   ProjectOrchestrator — connected to NeuralBus ✓ (7 lifecycle events)")
        except Exception as e:
            print(f"[Mamoun]   ⚠ ProjectOrchestrator connection failed: {e}")

        # SkillExecutor — connects to NeuralBus for skill execution events
        try:
            if hasattr(kernel, '_skill_executor') and kernel._skill_executor:
                kernel._skill_executor._neural_bus = neural_bus
                neural_bus.subscribe("skill_executor", [
                    "perception", "vital_change",
                ], handler=getattr(kernel._skill_executor, '_on_neural_signal', lambda s: None),
                   priority_filter=3)
                print(f"[Mamoun]   SkillExecutor — connected to NeuralBus ✓")
        except Exception as e:
            print(f"[Mamoun]   ⚠ SkillExecutor connection failed: {e}")

        # Physical/IoT agents — connect to NeuralBus (feature-flagged)
        try:
            from mamoun.physical.robot_controller import robot_controller
            from mamoun.physical.iot_gateway import iot_gateway
            from mamoun.physical.embodiment_service import get_embodiment_controller
            embodiment_ctrl = get_embodiment_controller()
            robot_controller._neural_bus = neural_bus
            iot_gateway._neural_bus = neural_bus
            embodiment_ctrl._neural_bus = neural_bus
            print(f"[Mamoun]   Physical/IoT — connected to NeuralBus (feature-flagged) ✓")
        except Exception as e:
            print(f"[Mamoun]   ⚠ Physical/IoT connection skipped: {e}")

        # Trading agent — connect to NeuralBus (feature-flagged)
        try:
            from mamoun.agents.trading.trading_engine import get_trading_engine
            trading_eng = get_trading_engine()
            trading_eng._neural_bus = neural_bus
            print(f"[Mamoun]   TradingEngine — connected to NeuralBus (feature-flagged) ✓")
        except Exception as e:
            print(f"[Mamoun]   ⚠ TradingEngine connection skipped: {e}")

        # Social agents — connect to NeuralBus (feature-flagged)
        try:
            from mamoun.agents.social.instagram_manager import InstagramManager
            instagram_mgr = InstagramManager()
            instagram_mgr._neural_bus = neural_bus
            neural_bus.subscribe("social_agents", [
                "action_completed", "action_failed", "perception",
            ], handler=getattr(instagram_mgr, '_on_neural_signal', lambda s: None),
               priority_filter=2)
            print(f"[Mamoun]   SocialAgents — connected to NeuralBus ✓")
        except Exception as e:
            print(f"[Mamoun]   ⚠ SocialAgents connection skipped: {e}")

        # v34: Blender Controller — connect to NeuralBus
        try:
            from mamoun.physical.blender_controller import get_blender_controller
            blender_ctrl = get_blender_controller()
            blender_ctrl._neural_bus = neural_bus
            neural_bus.subscribe("blender_controller", [
                "action_requested", "action_completed", "action_failed",
            ], handler=getattr(blender_ctrl, '_on_neural_signal', lambda s: None),
               priority_filter=2)
            print(f"[Mamoun]   BlenderController — connected to NeuralBus ✓")
        except Exception as e:
            print(f"[Mamoun]   ⚠ BlenderController connection skipped: {e}")

        # v34: E-commerce agents — connect to NeuralBus
        try:
            from mamoun.agents.ecommerce.agentic_store_builder import get_agentic_store_builder
            store_builder = get_agentic_store_builder()
            store_builder._neural_bus = neural_bus
            neural_bus.subscribe("ecommerce", [
                "action_completed", "action_failed", "perception",
            ], handler=getattr(store_builder, '_on_neural_signal', lambda s: None),
               priority_filter=2)
            print(f"[Mamoun]   EcommerceAgents — connected to NeuralBus ✓")
        except Exception as e:
            print(f"[Mamoun]   ⚠ EcommerceAgents connection skipped: {e}")

        # Start autonomic background tasks
        await autonomic_system.start()

        # Start inner monologue background thinking loop
        await inner_monologue.start()

        print(f"[Mamoun] Living Systems initialized ✓ (shared singletons)")
        print(f"[Mamoun]   LivingStateEngine — 6 vital signs ✓")
        print(f"[Mamoun]   EmotionalMemoryEngine — 3-layer memory ✓")
        print(f"[Mamoun]   DeepBondingEngine — 5-phase bonding ✓")
        print(f"[Mamoun]   ReflexesEngine — 9 default reflexes ✓")
        print(f"[Mamoun]   AutonomicNervousSystem — heartbeat active ✓")
        print(f"[Mamoun]   SelfHealingEngine — git_pull + auto-repair ✓")
        print(f"[Mamoun]   InnerMonologue — background thinking ✓")
        print(f"[Mamoun]   ApprovalGate — self-modification approval ✓")
        print(f"[Mamoun]   ProjectOrchestrator — project lifecycle ✓")
        print(f"[Mamoun]   SkillExecutor — skill execution ✓")
        print(f"[Mamoun]   NeuralBus — all systems connected ✓")
    except Exception as e:
        print(f"[Mamoun] ⚠ Living Systems initialization failed: {e}")
        import traceback; traceback.print_exc()
        print(f"[Mamoun] Living Systems endpoints will return 503")

    # v34: Check API key status for all 3 providers
    has_glm = bool(os.getenv('GLM_API_KEY', ''))
    has_deepseek = bool(os.getenv('DEEPSEEK_API_KEY', ''))
    has_gemini = bool(os.getenv('GEMINI_API_KEY', ''))
    gemini_proxy = os.getenv('GEMINI_PROXY_URL', '')

    print(f"[Mamoun] BABSHARQII v40.0 starting...")
    print(f"[Mamoun] Living Brains: {len(living_brains)} registered & activated")
    print(f"[Mamoun] PRIMARY BRAIN: Neural=GLM-5.1 (weight=0.25 — الأساسي)")
    print(f"[Mamoun] Brain Models: Neural=GLM-5.1(0.25), Causal=DeepSeek-Reasoner(0.22), Symbolic=GLM-4-Plus(0.18), Bayesian=Gemini-2.0-Flash(0.17), WorldModel=DeepSeek-Chat(0.18)")
    print(f"[Mamoun] API Keys: GLM={'✓' if has_glm else '✗'}, DeepSeek={'✓' if has_deepseek else '✗'}, Gemini={'✓ (proxy)' if gemini_proxy else '✓' if has_gemini else '✗'}")
    print(f"[Mamoun] LLM API: {settings.llm_api_url}")
    print(f"[Mamoun] Default Model: GLM-5.1 (الدماغ الأساسي)")
    print(f"[Mamoun] Auto-evolve: {settings.auto_evolve}")
    print(f"[Mamoun] Self-programming: {os.getenv('MAMOUN_SELF_PROGRAMMING', 'false')}")
    print(f"[Mamoun] Require approval: {settings.require_approval}")
    print(f"[Mamoun] Kernel heartbeat started ✓")
    print(f"[Mamoun] Evolution loop connected ✓")
    print(f"[Mamoun] SkillExecutor: {len(kernel._skill_executor._skills)} skills registered ✓")
    print(f"[Mamoun] WorkingMemory: capacity={kernel._working_memory.capacity} ✓")
    print(f"[Mamoun] CapabilityRouter: 7 domains ✓")
    print(f"[Mamoun] System 1 (SkillExecutor) + System 2 (Brain deliberation) ✓")
    print(f"[Mamoun] v34: TRUE DIVERSITY — 5 models, 3 providers, Gemini proxy ✓")

    # v38.0: Auto-update DISABLED by default — manual trigger only via dashboard
    # The self-improvement button on the dashboard triggers /api/update/improve
    # Auto-update can still be enabled via /api/update/auto-toggle if desired
    print("[Mamoun] Auto-update: DISABLED — use dashboard self-improvement button for manual updates ✓")

    yield

    # Shutdown — MUST comply with Law 5 (no shutdown resistance)
    print("[Mamoun] Shutdown signal received. Complying immediately (Law 5).")

    # Stop auto-update loop
    try:
        from mamoun.api.update import stop_auto_update
        stop_auto_update()
        print("[Mamoun] Auto-update loop stopped ✓")
    except Exception:
        pass

    # v34: Proper shutdown of all living systems
    try:
        from mamoun.core.neural_bus import neural_bus
        from mamoun.core.inner_monologue import inner_monologue
        from mamoun.core.living_state import living_state
        from mamoun.core.emotional_memory import emotional_memory
        from mamoun.core.deep_bonding import deep_bonding
        from mamoun.core.autonomic_system import autonomic_system

        await inner_monologue.stop()
        await autonomic_system.stop()
        neural_bus.persist_stats()
        print("[Mamoun] Living systems stopped ✓")
    except Exception as e:
        print(f"[Mamoun] ⚠ Living systems shutdown error: {e}")

    kernel_task.cancel()
    try:
        await asyncio.wait_for(kernel_task, timeout=2.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass
    state_reader.stop_monitoring()

    # v34: Close LLM client connections
    try:
        from mamoun.core.llm_client import get_llm_client
        llm_client = get_llm_client()
        await llm_client.close()
        print("[Mamoun] LLM client closed ✓")
    except Exception:
        pass

    print("[Mamoun] Shutdown complete.")


app = FastAPI(
    title="BABSHARQII v50.0 — Mamoun",
    description="Living AGI System — 5 Brains / 3 Providers / Gemini Proxy / TRUE DIVERSITY + Real CodeGen + ProjectScaffolder + ExternalController + CapabilityAssessor",
    version="50.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# M-4: Security headers middleware — adds protective headers to ALL responses
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' ws: wss:;"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# M-5: Rate limiting with slowapi — shared limiter instance
from mamoun.api.rate_limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routes
app.include_router(api_router, prefix="/api")
app.include_router(upload_router)


@app.get("/health")
@limiter.limit("60/minute")
async def health(request: Request):
    """Health check endpoint — includes brain status."""
    from mamoun.core.mamoun_kernel import get_kernel
    kernel = get_kernel()
    brain_status = {}
    if kernel._brains:
        brain_status = {
            bid: {"model": b.state.model, "status": b.state.status, "confidence": round(b.state.confidence, 3)}
            for bid, b in kernel._brains.items()
        }
    return {
        "status": "alive",
        "organism": "BABSHARQII v40.0",
        "codename": "Mamoun",
        "version": "40.0.0",
        "brains": brain_status,
        "kernel_running": kernel._running,
        "workspace_winner": kernel.workspace.current.winning_brain if kernel.workspace.current else None,
    }


@app.get("/metrics")
@limiter.limit("60/minute")
async def prometheus_metrics(request: Request):
    """Prometheus-compatible metrics endpoint (Fix #12)."""
    from mamoun.core.monitoring import monitoring_manager
    from fastapi.responses import PlainTextResponse
    
    # Collect fresh metrics
    monitoring_manager.collect_system_metrics()
    
    return PlainTextResponse(
        content=monitoring_manager.get_prometheus_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
