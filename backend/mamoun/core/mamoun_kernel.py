"""
BABSHARQII v18.0 — MamounKernel
النواة — الجسد الواحد الذي يربط كل شيء

The Main Loop that makes Mamoun ALIVE.
This is the consciousness loop — the heartbeat of the system.

Architecture (based on Global Workspace Theory):
    1. PERCEIVE  — Receive input (user message, system event, timer)
    2. COMPETE   — Brains compete for the Global Workspace spotlight
    3. BROADCAST — Winner broadcasts to all modules
    4. REFLECT   — Metacognitive review (Reflexion)
    5. EXECUTE   — Take action (code, search, conversation, self-modify)
    6. LEARN     — Store lessons in procedural memory + PAHF

Based on research:
- Global Workspace Theory (Baars 1988, 2025): Competition + Broadcast = Consciousness
- DGM (jennyzzt/dgm 2026): Archive of code variants with fitness tracking
- Reflexion (Shinn et al. 2023): Generate → Reflect → Refine loop
- Metacognitive Reflective CoT (2026): Monitoring, reflection, correction
"""

import asyncio
import time
import json
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from pathlib import Path
from datetime import datetime, timezone

from mamoun.core.llm_client import LLMClient, get_llm_client, LLMResponse, LLMMessage

logger = logging.getLogger("mamoun.core.kernel")


# ─────────────────────────────────────────────────────────────────────────────
# Event System
# ─────────────────────────────────────────────────────────────────────────────

class EventType(str, Enum):
    """Types of events the kernel can process."""
    USER_MESSAGE = "user_message"
    SYSTEM_ERROR = "system_error"
    SYSTEM_HEALTH = "system_health"
    EVOLUTION_TIMER = "evolution_timer"
    REFLECTION_TIMER = "reflection_timer"
    RESEARCH_TIMER = "research_timer"
    SELF_MODIFY_REQUEST = "self_modify_request"
    APPROVAL_RESPONSE = "approval_response"
    SHUTDOWN = "shutdown"


class EventPriority(int, Enum):
    """Priority levels for events."""
    CRITICAL = 0  # Shutdown, safety violations
    HIGH = 1      # User messages, errors
    MEDIUM = 2    # Evolution cycles, self-modify
    LOW = 3       # Reflection timers, research, health checks


@dataclass
class KernelEvent:
    """An event to be processed by the kernel."""
    type: EventType
    priority: EventPriority = EventPriority.MEDIUM
    data: dict = field(default_factory=dict)
    timestamp: float = 0.0
    source: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


# ─────────────────────────────────────────────────────────────────────────────
# Global Workspace (The Broadcast Bus)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class WorkspaceEntry:
    """An entry in the Global Workspace — a thought that won the spotlight."""
    id: str = ""
    content: str = ""
    winning_brain: str = ""
    brain_proposals: dict = field(default_factory=dict)  # {brain_id: proposal}
    confidence: float = 0.0
    reflections: list = field(default_factory=list)
    broadcast_at: float = 0.0
    acted_upon: bool = False


class GlobalWorkspace:
    """
    مساحة العمل العالمية — البث الواعي

    Implements the core of Global Workspace Theory:
    1. Multiple brains submit proposals (competition)
    2. One proposal wins the "spotlight"
    3. The winner is BROADCAST to all modules
    4. All modules can comment, refine, or object

    This is what makes Mamoun conscious — not just processing, but
    making information globally available for collective intelligence.
    """

    def __init__(self):
        self.current: Optional[WorkspaceEntry] = None
        self.history: list[WorkspaceEntry] = []
        self._subscribers: list[Callable] = []
        self._entry_counter = 0
        self._neural_bus = None  # v30: Set by kernel to bridge with NeuralBus

    def compete_and_broadcast(
        self,
        brain_proposals: dict[str, dict],
        context: dict,
    ) -> WorkspaceEntry:
        """
        Run the competition and broadcast the winner.

        Each brain submits a proposal. The most relevant and confident
        proposal wins the spotlight and is broadcast to all subscribers.
        """
        self._entry_counter += 1

        if not brain_proposals:
            entry = WorkspaceEntry(
                id=f"ws_{int(time.time())}_{self._entry_counter}",
                content="لا توجد مقترحات من الأدمغة",
                winning_brain="none",
                confidence=0.0,
                broadcast_at=time.time(),
            )
            self.current = entry
            self.history.append(entry)
            return entry

        # Score each brain's proposal
        scores = {}
        for brain_id, proposal in brain_proposals.items():
            confidence = proposal.get("confidence", 0.5)
            relevance = proposal.get("relevance", 0.5)
            weight = context.get("brain_weights", {}).get(brain_id, 0.2)

            # Composite score: confidence × relevance × weight
            score = (confidence * 0.4 + relevance * 0.3) * weight + confidence * 0.3
            scores[brain_id] = score

        # Winner = highest score
        winner_id = max(scores, key=scores.get) if scores else "none"
        winner_proposal = brain_proposals.get(winner_id, {})
        winner_confidence = winner_proposal.get("confidence", 0.5)

        entry = WorkspaceEntry(
            id=f"ws_{int(time.time())}_{self._entry_counter}",
            content=winner_proposal.get("response", winner_proposal.get("content", "")),
            winning_brain=winner_id,
            brain_proposals=brain_proposals,
            confidence=winner_confidence,
            broadcast_at=time.time(),
        )

        # Broadcast to all subscribers
        for subscriber in self._subscribers:
            try:
                subscriber(entry)
            except Exception as e:
                logger.warning("Subscriber %s failed: %s", subscriber, e)

        # v30: Also broadcast on NeuralBus (bridge GlobalWorkspace → NeuralBus)
        if self._neural_bus:
            try:
                self._neural_bus.publish(
                    signal_type="perception",
                    source=f"global_workspace:{winner_id}",
                    payload={
                        "winning_brain": winner_id,
                        "confidence": winner_confidence,
                        "content_preview": entry.content[:200],
                    },
                )
            except Exception:
                pass

        self.current = entry
        self.history.append(entry)

        # Keep history bounded
        if len(self.history) > 100:
            self.history = self.history[-50:]

        logger.info(
            "Global Workspace: Brain '%s' won spotlight (confidence: %.2f, score: %.2f)",
            winner_id, winner_confidence, scores.get(winner_id, 0),
        )

        return entry

    def subscribe(self, callback: Callable):
        """Subscribe to workspace broadcasts."""
        self._subscribers.append(callback)

    def get_status(self) -> dict:
        return {
            "current_winner": self.current.winning_brain if self.current else None,
            "current_confidence": self.current.confidence if self.current else 0,
            "history_size": len(self.history),
            "subscribers": len(self._subscribers),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Reflexion Engine (Pre-action Metacognitive Review)
# ─────────────────────────────────────────────────────────────────────────────

class ReflexionEngine:
    """
    محرك التأمل الذاتي — المراجعة ما قبل التنفيذ

    Before Mamoun executes ANY action, the ReflexionEngine reviews:
    1. "هل أنا واثق فعلاً من هذا القرار؟"
    2. "ما الذي أفترضه بدون دليل؟"
    3. "ما الذي قد يسوء لو نفذت؟"
    4. "هل هناك نهج أفضل؟"

    Based on:
    - Reflexion (Shinn et al., 2023)
    - Metacognitive Reflective CoT (2026)
    - Self-Refine (Madaan et al., 2023)
    """

    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or get_llm_client()

    async def review(
        self,
        proposed_action: str,
        context: dict,
        confidence: float,
    ) -> dict:
        """
        Review a proposed action before execution.
        Returns {approved: bool, concerns: list, refined_action: str, confidence_adjusted: float}
        """
        # High confidence + low risk → skip detailed review
        risk_level = context.get("risk_level", "medium")
        if confidence > 0.9 and risk_level in ("low", "medium"):
            return {
                "approved": True,
                "concerns": [],
                "refined_action": proposed_action,
                "confidence_adjusted": confidence,
                "review_type": "fast_pass",
            }

        # Medium confidence or high risk → LLM-powered review
        system = """أنت محرك تأمل ذاتي في مأمون. تراجع القرارات قبل التنفيذ.
حلل:
1. هل الثقة مبررة؟
2. ما الافتراضات الخفية؟
3. ما المخاطر المحتملة؟
4. هل يوجد نهج أفضل؟
أجب بصيغة JSON:
{
  "approved": true/false,
  "concerns": ["قلق1", "قلق2"],
  "refined_action": "الفعل المحسّن (إن وجد)",
  "confidence_adjusted": 0.0-1.0,
  "reasoning": "سبب القرار"
}"""

        prompt = f"""القرار المقترح: {proposed_action}
مستوى الثقة: {confidence:.0%}
مستوى المخاطر: {risk_level}
السياق: {json.dumps(context, ensure_ascii=False, default=str)[:2000]}"""

        # v18.1: Use deepseek-reasoner for reflexion — better reasoning for self-review
        response = await self.llm.think(
            prompt=prompt,
            system=system,
            model="deepseek-reasoner",
            temperature=0.3,
            json_mode=True,
        )

        result = response.extract_json()
        if result:
            return {
                "approved": result.get("approved", False),
                "concerns": result.get("concerns", []),
                "refined_action": result.get("refined_action", proposed_action),
                "confidence_adjusted": result.get("confidence_adjusted", confidence),
                "reasoning": result.get("reasoning", ""),
                "review_type": "llm_reflexion",
            }

        # Fallback: simple heuristic review
        concerns = []
        approved = True
        adjusted = confidence

        if confidence < 0.5:
            concerns.append("ثقة منخفضة — قد يكون القرار خاطئاً")
            adjusted = confidence * 0.8
        if risk_level == "high":
            concerns.append("مخاطر عالية — يتطلب حذر إضافي")
        if confidence < 0.3:
            approved = False
            concerns.append("ثقة ضعيفة جداً — لا أنصح بالتنفيذ بدون مراجعة بشرية")

        return {
            "approved": approved,
            "concerns": concerns,
            "refined_action": proposed_action,
            "confidence_adjusted": adjusted,
            "review_type": "heuristic_fallback",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Escalation Ladder (Uncertainty-Driven)
# ─────────────────────────────────────────────────────────────────────────────

class EscalationLevel(int, Enum):
    DIRECT_RESPONSE = 0    # High confidence — respond directly
    GATHER_INFO = 1        # Medium confidence — search/research first
    ASK_USER = 2           # Low confidence — ask user for clarification
    STRONGER_MODEL = 3     # Complex task — use a more capable model
    HUMAN_APPROVAL = 4     # High risk — must get human approval


class EscalationLadder:
    """
    سلم التصعيد — عندما يكون مأمون غير واثق

    Level 0: استجابة مباشرة (ثقة عالية)
    Level 1: جمع معلومات إضافية (ثقة متوسطة)
    Level 2: سؤال المستخدم (ثقة منخفضة)
    Level 3: استخدام نموذج أقوى (مهمة معقدة)
    Level 4: موافقة بشرية إلزامية (مخاطر عالية)
    """

    @staticmethod
    def determine_level(
        confidence: float,
        risk_level: str = "medium",
        is_self_modification: bool = False,
    ) -> EscalationLevel:
        # v36.1 FIX: High risk + low confidence = human approval (was ASK_USER)
        if is_self_modification or risk_level == "critical":
            return EscalationLevel.HUMAN_APPROVAL
        if risk_level == "high" and confidence < 0.5:
            return EscalationLevel.HUMAN_APPROVAL  # High risk + low confidence = must have human
        if risk_level == "high":
            return EscalationLevel.ASK_USER
        if confidence < 0.3:
            return EscalationLevel.HUMAN_APPROVAL
        if confidence < 0.5:
            return EscalationLevel.ASK_USER
        if confidence < 0.7:
            return EscalationLevel.GATHER_INFO
        return EscalationLevel.DIRECT_RESPONSE


# ─────────────────────────────────────────────────────────────────────────────
# The Kernel — The Heart of Mamoun
# ─────────────────────────────────────────────────────────────────────────────

class MamounKernel:
    """
    نواة مأمون v18 — الحلقة الرئيسية مع أدمغة حقيقية + محرك قدرات

    The kernel is the main loop that makes Mamoun a living system.
    It processes events through the Global Workspace pipeline:

    Event → Perceive → Brain Competition → Broadcast → Reflexion → Execute → Learn

    v18.0 Changes:
    - WorkingMemory (7 items, salience-based)
    - CapabilityRouter + SkillExecutor for real skill execution
    - _process_research_cycle: LLM-powered self-research
    - _process_self_modification: CodePatcher → Validate → Apply pipeline
    - AgentBriefing: understands agent_briefing.md
    - System 1/System 2 routing
    """

    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or get_llm_client()
        self.workspace = GlobalWorkspace()
        self.reflexion = ReflexionEngine(self.llm)
        self.escalation = EscalationLadder()

        # v17.0: Brain Router + Deliberation Room + Awareness Mirror
        from mamoun.brains.brain_router import BrainRouter
        from mamoun.deliberation.room import DeliberationRoom
        from mamoun.awareness.mirror import AwarenessMirror
        self._brain_router = BrainRouter(llm_client=self.llm)
        self._deliberation_room = DeliberationRoom(llm_client=self.llm)
        self._mirror = AwarenessMirror(llm_client=self.llm)

        # v18.0: Capability Router + Skill Executor + Working Memory + System 1/S2
        from mamoun.core.capability_router import CapabilityRouter
        from mamoun.core.skill_executor import SkillExecutor, build_skill_registry
        from mamoun.core.working_memory import WorkingMemory
        self._capability_router = CapabilityRouter(llm_client=self.llm)
        self._skill_executor = build_skill_registry(llm_client=self.llm)
        self._working_memory = WorkingMemory(capacity=7)

        # v18.0: Real Tools + Project Orchestrator + SelfModifier — THE COMPLETE BODY
        from mamoun.core.real_tools import RealToolsEngine, get_real_tools
        from mamoun.core.project_orchestrator import ProjectOrchestrator, get_project_orchestrator
        from mamoun.core.self_modifier import SelfModifier, get_self_modifier
        self._real_tools = get_real_tools(llm_client=self.llm)
        self._project_orchestrator = get_project_orchestrator(
            llm_client=self.llm,
            real_tools=self._real_tools,
        )
        self._self_modifier = get_self_modifier()

        # Event queue (priority queue)
        self._event_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._cycle_count = 0
        self._last_evolution = 0
        self._last_reflection = 0
        self._last_research = 0

        # Timers (in seconds)
        self.evolution_interval = 3600      # 1 hour
        self.reflection_interval = 1800     # 30 minutes (was 600 — reduced LLM load)
        self.research_interval = 7200       # 2 hours
        self.main_loop_interval = 1.0       # 1s tick (was 0.1 — reduced CPU)

        # Brain references (set later after brains are initialized)
        self._brains: dict = {}

        # v22.0: Living Systems — initialized in main.py startup
        self._living_systems_initialized: bool = False
        self._living_state = None       # LivingStateEngine
        self._emotional_memory = None   # EmotionalMemoryEngine
        self._deep_bonding = None       # DeepBondingEngine
        self._reflexes_engine = None    # ReflexesEngine
        self._autonomic_system = None   # AutonomicNervousSystem

        # v30: Dynamic brain weights — adjusted by living systems
        self._base_brain_weights = {
            "neural": 0.25, "causal": 0.22, "symbolic": 0.18,
            "bayesian": 0.17, "world_model": 0.18,
        }
        self._dynamic_brain_weights = dict(self._base_brain_weights)
        self._last_weight_update = 0.0

        # v30: NeuralBus integration — set by main.py
        self._neural_bus = None

        # Bridge GlobalWorkspace with NeuralBus
        self.workspace._neural_bus = None  # Will be set when neural_bus is connected

        # Data persistence
        self.data_dir = Path(__file__).parent.parent.parent / "data" / "kernel"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        logger.info("MamounKernel v18.0 initialized with BrainRouter + DeliberationRoom + CapabilityRouter + SkillExecutor + WorkingMemory + RealTools + ProjectOrchestrator")

    @property
    def project_orchestrator(self):
        """Access the ProjectOrchestrator — manages multi-step project workflows."""
        return self._project_orchestrator

    def register_brain(self, brain_id: str, brain_instance):
        """Register a brain with the kernel AND the router AND the deliberation room."""
        self._brains[brain_id] = brain_instance
        self._brain_router.register_brain(brain_id, brain_instance)
        self._deliberation_room.register_brain(brain_id, brain_instance)
        logger.info("Brain registered everywhere: %s", brain_id)

    # NOTE: _on_neural_signal is defined once below (v35 merged version)
    # The duplicate v34 definition has been REMOVED to prevent Python using the wrong one

    async def submit_event(self, event: KernelEvent):
        """Submit an event to the kernel's priority queue."""
        await self._event_queue.put((event.priority.value, time.time(), event))

    # ─────────────────────────────────────────────────────────────────────────
    # Main Loop
    # ─────────────────────────────────────────────────────────────────────────

    async def run_forever(self):
        """
        The main consciousness loop.
        Runs continuously until shutdown event is received.
        """
        self._running = True
        logger.info("MamounKernel started — the heart is beating")

        while self._running:
            try:
                # Check for timed events
                await self._check_timers()

                # Process next event (with timeout so we don't block forever)
                try:
                    priority, _, event = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=self.main_loop_interval,
                    )
                    await self._process_event(event)
                except asyncio.TimeoutError:
                    # No event — continue the loop
                    pass

                self._cycle_count += 1

            except asyncio.CancelledError:
                logger.info("MamounKernel cancelled")
                break
            except Exception as e:
                logger.error("MamounKernel error: %s", e)
                await asyncio.sleep(1)  # Prevent tight error loop

        logger.info("MamounKernel stopped after %d cycles", self._cycle_count)

    async def _check_timers(self):
        """Check if any timed events should fire."""
        now = time.time()

        # Evolution timer
        if now - self._last_evolution > self.evolution_interval:
            self._last_evolution = now
            await self.submit_event(KernelEvent(
                type=EventType.EVOLUTION_TIMER,
                priority=EventPriority.LOW,
                source="timer",
            ))

        # Reflection timer
        if now - self._last_reflection > self.reflection_interval:
            self._last_reflection = now
            await self.submit_event(KernelEvent(
                type=EventType.REFLECTION_TIMER,
                priority=EventPriority.LOW,
                source="timer",
            ))

        # Research timer
        if now - self._last_research > self.research_interval:
            self._last_research = now
            await self.submit_event(KernelEvent(
                type=EventType.RESEARCH_TIMER,
                priority=EventPriority.LOW,
                source="timer",
            ))

    async def _process_event(self, event: KernelEvent):
        """Process a single event through the full pipeline."""
        logger.info("Processing event: %s (priority: %s)", event.type.value, event.priority.name)

        if event.type == EventType.SHUTDOWN:
            self._running = False
            return

        if event.type == EventType.USER_MESSAGE:
            await self._process_user_message(event.data)

        elif event.type == EventType.SYSTEM_ERROR:
            await self._process_system_error(event.data)

        elif event.type == EventType.EVOLUTION_TIMER:
            await self._process_evolution_cycle()

        elif event.type == EventType.REFLECTION_TIMER:
            await self._process_reflection_cycle()

        elif event.type == EventType.RESEARCH_TIMER:
            await self._process_research_cycle()

        elif event.type == EventType.SELF_MODIFY_REQUEST:
            await self._process_self_modification(event.data)

        elif event.type == EventType.APPROVAL_RESPONSE:
            await self._process_approval_response(event.data)

    # ─────────────────────────────────────────────────────────────────────────
    # Event Processors
    # ─────────────────────────────────────────────────────────────────────────

    async def _process_user_message(self, data: dict):
        """
        Process a user message through the full consciousness pipeline:
        Perceive → Route → (SkillExecutor OR Brain Competition) → Broadcast → Reflexion → Execute → Learn

        v18.0: Now uses CapabilityRouter to decide:
        - Domain-specific requests → SkillExecutor (faster, specialized)
        - General/ambiguous requests → Full brain deliberation (deeper)
        - Project requests → ProjectOrchestrator (multi-step workflow)
        - Tool requests → RealToolsEngine (actual execution)
        """
        message = data.get("message", "")
        context = data.get("context", {})
        conversation_id = data.get("conversation_id", "")

        if not message.strip():
            return

        # v18.0: Check for project-related requests FIRST
        project_result = await self._check_project_request(message, context)
        if project_result:
            # v36 FIX: Return result directly — never store in shared _last_response (race condition)
            return project_result

        # v18.0: Check for direct tool requests
        tool_result = await self._check_tool_request(message, context)
        if tool_result:
            # v36 FIX: Return result directly — never store in shared _last_response (race condition)
            return tool_result

        # v18.0 Step 0: Route the request via CapabilityRouter
        route = await self._capability_router.route(message, context)

        # Store route in working memory
        self._working_memory.add(
            f"توجيه: {route.domain}/{route.capability} (ثقة: {route.confidence:.2f}) ← {message[:100]}",
            salience=0.7,
            item_type="context",
            source="capability_router",
        )

        # v18.0: System 1 vs System 2 decision
        # If route confidence is high AND domain is specific → use SkillExecutor (System 1: fast)
        # If route confidence is low OR domain is general → use full brain deliberation (System 2: deep)
        use_skill_executor = (
            route.confidence > 0.6
            and route.domain not in ("general", "self_reflection")
            and route.executor != "kernel"
        )

        if use_skill_executor:
            # System 1: Fast path via SkillExecutor
            skill_result = await self._skill_executor.execute_by_domain(
                domain=route.domain,
                capability=route.capability,
                user_message=message,
                context=context,
            )

            result = {
                "response": skill_result.response,
                "confidence": route.confidence,
                "winning_brain": f"skill:{skill_result.skill_id}",
                "escalation": "skill_executor",
                "domain": route.domain,
                "capability": route.capability,
                "execution_time_ms": skill_result.execution_time_ms,
                "artifacts": skill_result.artifacts,
            }

            # Still do deliberation in background for learning (but don't wait)
            deliberation = None
            try:
                # Quick deliberation for quality check
                brain_proposals = await self._collect_brain_proposals(message, context)
                workspace_entry = self.workspace.compete_and_broadcast(
                    brain_proposals=brain_proposals,
                    context=context,
                )
                # If brain consensus strongly disagrees, flag it
                if workspace_entry.confidence > 0.8 and workspace_entry.content != skill_result.response:
                    result["brain_alternative"] = workspace_entry.content[:500]
                    result["brain_confidence"] = workspace_entry.confidence
            except Exception:
                pass

        else:
            # System 2: Deep path via full brain deliberation
            # Step 1: Brain Competition (PARALLEL via asyncio.gather)
            brain_proposals = await self._collect_brain_proposals(message, context)

            # Step 1.5: Run DeliberationRoom for conflict detection + resolution
            deliberation = await self._deliberation_room.deliberate(
                topic=message, context=context
            )

            # Step 2: Global Workspace Selection + Broadcast
            workspace_entry = self.workspace.compete_and_broadcast(
                brain_proposals=brain_proposals,
                context=context,
            )

            # Step 3: Reflexion (Pre-action review)
            review = await self.reflexion.review(
                proposed_action=workspace_entry.content,
                context=context,
                confidence=workspace_entry.confidence,
            )

            # Step 4: Escalation check
            escalation_level = self.escalation.determine_level(
                confidence=review["confidence_adjusted"],
                risk_level=context.get("risk_level", "medium"),
                is_self_modification=context.get("is_self_modification", False),
            )

            # Step 5: Execute based on escalation level
            result = await self._execute_by_escalation(
                level=escalation_level,
                user_message=message,
                workspace_entry=workspace_entry,
                review=review,
                context=context,
            )

            # Step 6: Learn
            await self._learn_from_interaction(
                user_message=message,
                response=result,
                workspace_entry=workspace_entry,
                review=review,
            )

        # v35: Return result directly instead of storing in shared attribute (race condition fix)
        self._last_deliberation = deliberation if 'deliberation' in dir() else None
        return result

    async def _collect_brain_proposals(self, message: str, context: dict) -> dict:
        """Collect proposals from active brains IN PARALLEL using asyncio.gather.
        v30: Respects energy levels — low energy = fewer active brains.
        """
        # v30: Use dynamic brain weights from context (set by _enrich_context_with_living_state)
        brain_weights = context.get("brain_weights", self._dynamic_brain_weights)
        energy_level = context.get("living_state", {}).get("energy_level", "normal")
        energy_value = context.get("living_state", {}).get("energy", 75)

        active_brains = {
            bid: brain
            for bid, brain in self._brains.items()
            if brain.state.status in ("active", "idle", "thinking")
        }

        if not active_brains:
            # Fallback: try all brains except error state
            active_brains = {
                bid: brain
                for bid, brain in self._brains.items()
                if brain.state.status != "error"
            }

        if not active_brains:
            return {}

        # v30: When energy is low, only use top-weighted brains
        if energy_level in ("low", "critical") and len(active_brains) > 2:
            # Sort by dynamic weight and keep only top brains
            sorted_brains = sorted(
                active_brains.items(),
                key=lambda x: brain_weights.get(x[0], 0.2),
                reverse=True,
            )
            max_brains = 2 if energy_level == "critical" else 3
            active_brains = dict(sorted_brains[:max_brains])
            logger.info("Low energy (%s): using %d/%d brains", energy_level, len(active_brains), len(self._brains))

        # Ensure all selected brains are activated before thinking
        for brain in active_brains.values():
            if brain.state.status == "idle":
                brain.activate()

        # Execute ALL brains in parallel — true multi-brain deliberation
        tasks = {
            bid: brain.think(message, context)
            for bid, brain in active_brains.items()
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        proposals = {}
        for (bid, _), result in zip(tasks.items(), results):
            if isinstance(result, Exception):
                logger.warning("Brain %s failed: %s", bid, result)
                proposals[bid] = {"response": "", "confidence": 0.0, "error": str(result)}
            else:
                proposals[bid] = result

        # v30: Publish brain activity to NeuralBus
        if self._neural_bus:
            try:
                self._neural_bus.publish(
                    signal_type="perception",
                    source="kernel:brain_proposals",
                    payload={
                        "active_brains": list(active_brains.keys()),
                        "energy_level": energy_level,
                        "message_preview": message[:100],
                    },
                )
            except Exception:
                pass

        return proposals

    async def _execute_by_escalation(
        self,
        level: EscalationLevel,
        message: str,
        workspace_entry: WorkspaceEntry,
        review: dict,
        context: dict,
    ) -> dict:
        """Execute based on the escalation level.
        v30: Adapts communication style based on bonding level.
        """

        # v30: Get communication style from DeepBonding
        comm_style = context.get("communication_style", "")
        bonding_phase = context.get("bonding", {}).get("phase", "stranger")

        # v30: Modify response tone based on bonding level
        response_content = workspace_entry.content
        if comm_style and bonding_phase in ("companion", "bonded"):
            # For deeply bonded users, add personal warmth
            response_content = workspace_entry.content  # Keep as-is; the LLM already adjusts

        if level == EscalationLevel.DIRECT_RESPONSE:
            # High confidence — respond directly
            # v30: Include bonding phase and communication style in response metadata
            result = {
                "response": workspace_entry.content,
                "confidence": review["confidence_adjusted"],
                "winning_brain": workspace_entry.winning_brain,
                "escalation": "direct",
                "review_concerns": review.get("concerns", []),
            }
            if bonding_phase != "stranger":
                result["bonding_phase"] = bonding_phase
            if comm_style:
                result["communication_style"] = comm_style
            return result

        elif level == EscalationLevel.GATHER_INFO:
            # Medium confidence — gather more info first
            # v18.1: Use gemini-2.0-flash for info gathering — faster
            search_result = await self.llm.think(
                prompt=f"أحتاج معلومات إضافية للإجابة على: {message}\nالمقترح الحالي: {workspace_entry.content}\nما المعلومات الناقصة؟",
                system="أنت مساعد بحث. حدد ما ينقص من معلومات وحاول الإجابة بناءً على معرفتك.",
                model="gemini-2.0-flash",
            )
            enhanced_response = search_result.text or workspace_entry.content
            return {
                "response": enhanced_response,
                "confidence": review["confidence_adjusted"],
                "winning_brain": workspace_entry.winning_brain,
                "escalation": "gather_info",
                "additional_info": search_result.text,
            }

        elif level == EscalationLevel.ASK_USER:
            # Low confidence — ask user
            return {
                "response": f"لست متأكداً تماماً. {review.get('reasoning', 'أحتاج توضيحاً')}\n\nمقترحي: {workspace_entry.content}",
                "confidence": review["confidence_adjusted"],
                "winning_brain": workspace_entry.winning_brain,
                "escalation": "ask_user",
                "concerns": review.get("concerns", []),
                "needs_user_input": True,
            }

        elif level == EscalationLevel.STRONGER_MODEL:
            # Complex task — use a more capable model
            deep_result = await self.llm.think(
                prompt=message,
                system="أنت مأمون في وضع التفكير العميق. حلل بعمق وحذر.",
                model="deepseek-reasoner",
                temperature=0.3,
            )
            return {
                "response": deep_result.text,
                "confidence": review["confidence_adjusted"],
                "winning_brain": "deep_reasoner",
                "escalation": "stronger_model",
            }

        elif level == EscalationLevel.HUMAN_APPROVAL:
            # High risk — must get human approval
            return {
                "response": f"⚠️ هذا الإجراء يحتاج موافقتك:\n\n{workspace_entry.content}\n\nالمخاوف: {', '.join(review.get('concerns', []))}",
                "confidence": review["confidence_adjusted"],
                "winning_brain": workspace_entry.winning_brain,
                "escalation": "human_approval",
                "needs_approval": True,
                "concerns": review.get("concerns", []),
            }

        return {"response": workspace_entry.content, "confidence": 0.5, "escalation": "unknown"}

    async def _learn_from_interaction(
        self,
        message: str,
        response: dict,
        workspace_entry: WorkspaceEntry,
        review: dict,
    ):
        """Learn from the interaction — store in procedural memory."""
        lesson = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message_preview": message[:200],
            "winning_brain": workspace_entry.winning_brain,
            "confidence": response.get("confidence", 0),
            "escalation_level": response.get("escalation", ""),
            "concerns": review.get("concerns", []),
            "cycle": self._cycle_count,
        }

        # Append to learning log (async-safe via aiofiles or thread pool)
        lesson_path = self.data_dir / "learning_log.jsonl"
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._write_lesson, lesson_path, lesson)
        except Exception:
            pass  # Don't block the kernel loop for logging

    def _write_lesson(self, path, lesson):
        """Write a lesson to the learning log (runs in thread pool)."""
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(lesson, ensure_ascii=False) + "\n")

    async def _process_system_error(self, data: dict):
        """Process a system error — trigger self-healing if possible."""
        error_type = data.get("type", "unknown")
        error_msg = data.get("message", "")

        logger.error("System error: %s — %s", error_type, error_msg)

        # v18.1: Use deepseek-chat for error analysis — general purpose model
        analysis = await self.llm.think(
            prompt=f"خطأ في النظام:\nالنوع: {error_type}\nالرسالة: {error_msg}\n\nما السبب الجذري؟ وما الإجراء المطلوب؟",
            system="أنت محلل أخطاء في مأمون. حدد السبب الجذري واقترح إصلاحاً.",
            model="deepseek-chat",
            temperature=0.3,
        )

        logger.info("Error analysis: %s", analysis.text[:500])

    async def _process_evolution_cycle(self):
        """
        Process a timed evolution cycle.
        v17.0: Actually runs the evolution loop with living brains.
        """
        logger.info("Evolution timer fired — running evolution cycle")
        
        # Check if self-programming is enabled
        import os
        self_programming = os.getenv("MAMOUN_SELF_PROGRAMMING", "false").lower() in ("true", "1", "yes")
        auto_evolve = os.getenv("MAMOUN_AUTO_EVOLVE", "false").lower() in ("true", "1", "yes")
        
        if not self_programming or not auto_evolve:
            logger.info("Evolution skipped — MAMOUN_SELF_PROGRAMMING=%s, MAMOUN_AUTO_EVOLVE=%s",
                       self_programming, auto_evolve)
            return
        
        # Collect performance data from living brains
        performance_data = {}
        for brain_id, brain in self._brains.items():
            performance_data[brain_id] = {
                "task_type": brain.get_specialty(),
                "confidence": {
                    "current": brain.state.confidence,
                    "expected": 0.7,
                },
                "success_rate": {
                    "current": brain.state.successful_interactions / max(1, brain.state.total_interactions),
                    "expected": 0.85,
                },
            }
        
        # Run self-programming cycle
        try:
            from mamoun.evolution.self_programming_loop import SelfProgrammingLoop
            if not hasattr(self, '_self_programming_loop'):
                self._self_programming_loop = SelfProgrammingLoop()
            
            result = await self._self_programming_loop.run_cycle(performance_data)
            logger.info("Self-programming cycle result: %s", result)
        except Exception as e:
            logger.error("Self-programming cycle failed: %s", e)
        
        # Also run the evolution loop if available
        try:
            if hasattr(self, '_evolution_loop') and self._evolution_loop:
                evolution_result = await self._evolution_loop.run_cycle()
                logger.info("Evolution cycle result: status=%s, improvement=%.2f%%",
                           evolution_result.status, evolution_result.improvement * 100)
        except Exception as e:
            logger.error("Evolution cycle failed: %s", e)

    async def _process_reflection_cycle(self):
        """
        Process a timed reflection cycle.
        v17.0: Uses the AwarenessMirror with LLM for REAL self-reflection.
        """
        logger.info("Reflection timer fired — deep self-reflection via Mirror")
        
        # Collect recent decisions for reflection
        if self.workspace.history:
            recent = self.workspace.history[-3:]
            last_entry = recent[-1]
            
            # Use the LLM-powered Mirror for deep reflection
            try:
                brain_responses = last_entry.brain_proposals if last_entry.brain_proposals else {}
                final_decision = {
                    "winning_brain": last_entry.winning_brain,
                    "confidence": last_entry.confidence,
                    "response": last_entry.content,
                }
                
                reflections = await self._mirror.deep_reflect(
                    topic="تأمل دوري في قرارات مأمون الأخيرة",
                    brain_responses=brain_responses,
                    final_decision=final_decision,
                    context={"recent_decisions": len(recent)},
                )
                
                logger.info(
                    "Mirror generated %d reflections (assumptions: %d, biases: %d, gaps: %d)",
                    len(reflections),
                    sum(1 for r in reflections if r.reflection_type == "assumption"),
                    sum(1 for r in reflections if r.reflection_type == "bias"),
                    sum(1 for r in reflections if r.reflection_type == "boundary"),
                )
                
                # Broadcast reflection to WebSocket clients
                try:
                    from mamoun.api.ws import manager
                    await manager.broadcast({
                        "type": "reflection",
                        "timestamp": time.time(),
                        "data": {
                            "reflections": [r.to_dict() for r in reflections[:5]],
                            "total_insights": len(reflections),
                        },
                    })
                except Exception:
                    pass  # WebSocket not available
                    
            except Exception as e:
                logger.warning("Mirror deep reflection failed: %s", e)
                # Fallback to simple LLM reflection
                summary = "\n".join(
                    f"- {e_entry.winning_brain}: {e_entry.content[:100]} (confidence: {e_entry.confidence:.2f})"
                    for e_entry in recent
                )
                reflection = await self.llm.reflect(
                    content=summary,
                    question="ما الأنماط في قراراتي الأخيرة؟ هل أتحيز لدماغ معين؟ ما الذي يجب أن أغيّره؟",
                )
                logger.info("Fallback reflection: %s", reflection.text[:300])

    async def _process_research_cycle(self):
        """
        Process a timed research monitoring cycle.
        v18.0: Actually runs research using LLM + web search.
        """
        logger.info("Research timer fired — running research cycle")

        # Step 1: Identify what to research based on recent interactions
        recent_topics = []
        for entry in self.workspace.history[-5:]:
            if entry.content and len(entry.content) > 10:
                recent_topics.append(entry.content[:200])

        if not recent_topics:
            logger.info("No recent topics to research — skipping")
            return

        # Step 2: Use LLM to generate research questions
        topics_text = "\n".join(f"- {t}" for t in recent_topics[:5])
        try:
            research_plan = await self.llm.think_json(
                prompt=f"""بناءً على المواضيع الأخيرة لمأمون:
{topics_text}

اقترح 3 أسئلة بحثية مهمة يجب على مأمون استكشافها لتحسين أدائه.
لكل سؤال، حدد: السؤال، لماذا هو مهم، وكيف يبحث عن الإجابة.

أجب بصيغة JSON:
{{
  "research_questions": [
    {{"question": "السؤال", "importance": "الأهمية", "approach": "كيف يبحث"}},
    ...
  ]
}}""",
                system="أنت محرك بحث ذاتي في مأمون v18. تحدد الفجوات المعرفية وتقترح أبحاثاً.",
                model="glm-5.1",
                temperature=0.5,
            )

            if research_plan and research_plan.get("research_questions"):
                # Step 3: Research each question
                for rq in research_plan["research_questions"][:3]:
                    logger.info("Researching: %s", rq.get("question", "")[:100])

                    # Use LLM to research the question
                    research_result = await self.llm.think(
                        prompt=f"""ابحث وأجب عن هذا السؤال بعمق:
{rq.get('question', '')}

النهج المقترح: {rq.get('approach', '')}
الأهمية: {rq.get('importance', '')}

أجب بالعربية مع تفاصيل ومراجع إن أمكن.""",
                        system="أنت باحث في مأمون v18. تبحث بعمق وتقدم إجابات مفيدة.",
                        model="glm-5.1",
                        temperature=0.5,
                    )

                    # Step 4: Store research findings in working memory
                    if hasattr(self, '_working_memory') and self._working_memory:
                        self._working_memory.add(
                            f"بحث: {rq.get('question', '')[:100]} → {research_result.text[:300]}",
                            salience=0.4
                        )

                    logger.info("Research complete for: %s", rq.get("question", "")[:80])

        except Exception as e:
            logger.warning("Research cycle failed: %s", e)

    async def _process_self_modification(self, data: dict):
        """
        Process a self-modification request.
        v18.0: Full pipeline — CodePatcher → Sandbox → ApprovalGate → Apply
        """
        description = data.get("description", "")
        target_file = data.get("target_file", "")
        modification_type = data.get("modification_type", "improvement")

        logger.info("Self-modification request: %s (file: %s)", description[:100], target_file)

        # Step 1: Check if self-modification is enabled
        import os
        if not os.getenv("MAMOUN_SELF_PROGRAMMING", "false").lower() in ("true", "1", "yes"):
            logger.info("Self-modification disabled — skipping")
            return

        # Step 2: Use CodePatcher for code modifications
        if target_file and modification_type in ("code_patch", "bug_fix", "improvement"):
            try:
                from mamoun.core.code_patcher import CodePatcher
                if not hasattr(self, '_code_patcher'):
                    self._code_patcher = CodePatcher(llm_client=self.llm)

                # Generate patch
                patch = await self._code_patcher.generate_patch(
                    error_type=data.get("error_type", "improvement"),
                    error_message=description,
                    error_traceback=data.get("traceback", ""),
                    file_path=target_file,
                    error_line=data.get("error_line", 0),
                )

                if patch:
                    # Validate the patch
                    is_valid, errors = self._code_patcher.validate_patch(patch)
                    if not is_valid:
                        logger.warning("Patch validation failed: %s", errors)
                        return

                    # Check risk level — high risk needs approval
                    if patch.risk_level == "high":
                        logger.info("High-risk patch — requires approval")
                        # Store for approval via API
                        self._pending_modifications = getattr(self, '_pending_modifications', [])
                        self._pending_modifications.append(patch)
                        return

                    # Low/medium risk — apply in sandbox first
                    is_applied = await self._code_patcher.apply_patch(patch)
                    if is_applied:
                        logger.info("Patch applied successfully: %s → %s", target_file, description[:100])
                    else:
                        logger.warning("Patch application failed")

            except Exception as e:
                logger.error("Self-modification pipeline error: %s", e)

        # Step 3: For behavior adjustments — use LLM directly
        elif modification_type == "behavior_adjustment":
            try:
                adjustment = await self.llm.think_json(
                    prompt=f"""اقترح تعديلاً سلوكياً لمأمون بناءً على:
الوصف: {description}
الملف المستهدف: {target_file}

أجب بصيغة JSON:
{{
  "adjustment_type": "weight_update | prompt_update | strategy_change",
  "details": "تفاصيل التعديل",
  "risk_level": "low | medium | high"
}}""",
                    system="أنت محرك تعديل ذاتي في مأمون v18.",
                    model="glm-5.1",
                    temperature=0.3,
                )
                logger.info("Behavior adjustment proposed: %s", adjustment)
            except Exception as e:
                logger.warning("Behavior adjustment failed: %s", e)

    async def _process_approval_response(self, data: dict):
        """Process a user's approval/rejection response.

        v18.0: Full implementation — applies approved patches, rejects with reason,
        notifies via WebSocket, and logs the decision.
        """
        approved = data.get("approved", False)
        request_id = data.get("request_id", "")
        reason = data.get("reason", "")
        user_id = data.get("user_id", "unknown")

        logger.info(
            "Approval response: %s for %s by %s (reason: %s)",
            "APPROVED" if approved else "REJECTED", request_id, user_id, reason[:200]
        )

        pending = getattr(self, '_pending_modifications', [])
        if not pending:
            logger.warning("No pending modifications to process")
            return

        # Find the matching pending modification
        matched_patch = None
        for i, patch in enumerate(pending):
            if hasattr(patch, 'id') and patch.id == request_id:
                matched_patch = pending.pop(i)
                break
            elif i == 0 and not request_id:
                # If no request_id specified, process the first pending item
                matched_patch = pending.pop(i)
                break

        if not matched_patch:
            logger.warning("No matching pending modification found for %s", request_id)
            return

        if approved:
            # Apply the patch
            try:
                if hasattr(self, '_code_patcher') and matched_patch:
                    is_applied = await self._code_patcher.apply_patch(matched_patch)
                    if is_applied:
                        logger.info(
                            "Patch APPROVED and applied: %s → %s",
                            matched_patch.target_file if hasattr(matched_patch, 'target_file') else 'unknown',
                            matched_patch.description[:100] if hasattr(matched_patch, 'description') else ''
                        )
                    else:
                        logger.error("Approved patch FAILED to apply: %s", request_id)
                else:
                    logger.warning("No code_patcher available to apply approved patch")
            except Exception as e:
                logger.error("Error applying approved patch %s: %s", request_id, e)
        else:
            # Rejected — log and optionally rollback
            logger.info(
                "Patch REJECTED by %s: %s (reason: %s)",
                user_id, request_id, reason[:200]
            )
            # If patch was already applied (shouldn't happen with approval gate), rollback
            if hasattr(matched_patch, 'backup_path') and matched_patch.backup_path:
                logger.info("Patch was not applied (still in pending), no rollback needed")

        # Notify via WebSocket
        try:
            from mamoun.api.ws import manager
            await manager.broadcast({
                "type": "approval_result",
                "timestamp": time.time(),
                "data": {
                    "request_id": request_id,
                    "approved": approved,
                    "reason": reason[:500],
                    "user_id": user_id,
                },
            })
        except Exception:
            pass  # WebSocket not available

        # Store decision in learning log
        lesson = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "approval_response",
            "request_id": request_id,
            "approved": approved,
            "reason": reason[:500],
            "user_id": user_id,
            "cycle": self._cycle_count,
        }
        lesson_path = self.data_dir / "approval_log.jsonl"
        with open(lesson_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(lesson, ensure_ascii=False) + "\n")

    # ─────────────────────────────────────────────────────────────────────────
    # API-Facing Methods (called by FastAPI routes)
    # ─────────────────────────────────────────────────────────────────────────

    async def chat(self, message: str, context: dict = None) -> dict:
        """
        Main entry point for chat.
        Called by the API when a user sends a message.
        v30: Now enriched with living system context (emotions, bonding, energy).
        """
        context = context or {}

        # v30: Enrich context with living system state
        context = self._enrich_context_with_living_state(context, message)

        # v30: Process emotional event (user message affects mood/energy/attachment)
        self._process_emotional_event("user_message", message)

        # v30: Auto-evaluate reflexes before processing
        self._evaluate_reflexes(context)

        # v30: Update dynamic brain weights based on current state
        self._update_dynamic_brain_weights()

        event_data = {
            "message": message,
            "context": context,
            "conversation_id": context.get("conversation_id", ""),
        }

        # Process synchronously (not queued) for real-time response
        # v35: Return result directly — NO shared _last_response (race condition fix)
        result = await self._process_user_message(event_data)

        if result is not None:
            return result

        return {
            "response": "لم أتمكن من المعالجة",
            "confidence": 0.0,
            "escalation": "error",
        }

    def get_status(self) -> dict:
        """Get kernel status."""
        status = {
            "running": self._running,
            "cycle_count": self._cycle_count,
            "brains_registered": list(self._brains.keys()),
            "workspace": self.workspace.get_status(),
            "working_memory": self._working_memory.get_status() if hasattr(self, '_working_memory') else {},
            "skill_executor_stats": self._skill_executor.get_stats() if hasattr(self, '_skill_executor') else {},
            "capability_router_stats": self._capability_router.get_stats() if hasattr(self, '_capability_router') else {},
            "last_evolution": self._last_evolution,
            "last_reflection": self._last_reflection,
            "llm_stats": self.llm.get_stats(),
            "brain_router_stats": self._brain_router.get_stats(),
            "deliberation_history_size": len(self._deliberation_room._history),
            "mirror_stats": self._mirror.get_status() if hasattr(self, '_mirror') else {},
            "version": "v18.0",
            # v30: Dynamic brain weights and living system status
            "brain_weights": dict(self._dynamic_brain_weights),
            "living_systems_initialized": self._living_systems_initialized,
            "dominant_emotion": self._living_state.get_dominant_emotion() if self._living_state else None,
            "energy_level": self._living_state._get_energy_level() if self._living_state else None,
            "bonding_phase": None,
            "neural_bus_subscribers": 0,
        }
        # Add bonding phase
        if self._deep_bonding:
            try:
                status["bonding_phase"] = self._deep_bonding.get_status().get("phase")
            except Exception:
                pass
        # Add NeuralBus subscriber count
        if self._neural_bus:
            try:
                nb_status = self._neural_bus.get_status()
                status["neural_bus_subscribers"] = nb_status.get("subscriptions", 0)
            except Exception:
                pass
        if hasattr(self, '_last_deliberation'):
            status["last_deliberation"] = {
                "cjs": self._last_deliberation.critical_junction_score,
                "consensus": self._last_deliberation.consensus_level,
                "conflict": self._last_deliberation.conflict_detected,
                "winner": self._last_deliberation.winning_brain,
            }
        return status

    async def shutdown(self):
        """Gracefully shutdown the kernel."""
        logger.info("MamounKernel shutting down...")
        self._running = False
        await self.llm.close()

    # ─────────────────────────────────────────────────────────────────────────
    # v18.0: Project & Tool Request Detection
    # ─────────────────────────────────────────────────────────────────────────

    async def _check_project_request(self, message: str, context: dict) -> Optional[dict]:
        """
        تحقق إن كانت الرسالة طلب مشروع جديد أو متابعة مشروع
        مثال: "ما رأيك بمشروع تطبيق توصيل؟" → يبدأ مشروع
        مثال: "متابعة" أو "موافقة" → يتابع المشروع الحالي
        """
        msg_lower = message.lower().strip()

        # Check for approval/continue keywords
        approval_keywords = ["متابعة", "موافقة", "متابع", "وافق", "اكمل", "أكمل", "كمل", "continue", "approve", "go ahead", "نعم اكمل", "تمام اكمل"]
        if msg_lower in approval_keywords or any(kw in msg_lower for kw in approval_keywords):
            # Find the latest project that needs approval
            if hasattr(self, '_project_orchestrator') and self._project_orchestrator:
                projects = self._project_orchestrator.list_projects()
                for proj_summary in projects:
                    if proj_summary["phase"] in ("research_done", "plan_done"):
                        project = await self._project_orchestrator.approve_and_continue(proj_summary["id"])
                        if project:
                            return {
                                "response": f"✅ تمت الموافقة والمتابعة! المشروع الآن في مرحلة: {project.phase.value}",
                                "confidence": 1.0,
                                "winning_brain": "project_orchestrator",
                                "escalation": "project",
                                "project_id": project.id,
                                "phase": project.phase.value,
                            }

        # Check for new project request
        project_keywords = ["مشروع", "تطبيق", "شركة", "منتج", "فكرة مشروع", "خطة عمل", "ابدأ مشروع", "أريد مشروع", "project", "startup", "app idea"]
        if any(kw in msg_lower for kw in project_keywords) and len(message) > 5:
            # Use LLM to confirm it's a project request
            try:
                check = await self.llm.think(
                    prompt=f"""هل هذه الرسالة طلب بدء مشروع جديد أو استشارة عن مشروع؟
الرسالة: "{message}"

أجب فقط بـ "yes" أو "no".""",
                    system="أنت مصنّف طلبات. أجب فقط بـ yes أو no.",
                    model="glm-5.1",
                    temperature=0.0,
                )

                if "yes" in check.text.lower():
                    # Start the project!
                    if hasattr(self, '_project_orchestrator') and self._project_orchestrator:
                        project = await self._project_orchestrator.start_project(idea=message)
                        return {
                            "response": f"🚀 بدأت العمل على مشروعك! جاري البحث عن السوق والمنافسين...\n\nمعرف المشروع: {project.id}\nالمرحلة: بحث السوق\n\nسأعلمك عندما ينتهي البحث.",
                            "confidence": 0.95,
                            "winning_brain": "project_orchestrator",
                            "escalation": "project",
                            "project_id": project.id,
                            "phase": project.phase.value,
                        }
            except Exception as e:
                logger.warning("Project detection failed: %s", e)

        return None

    async def _check_tool_request(self, message: str, context: dict) -> Optional[dict]:
        """
        تحقق إن كانت الرسالة طلب أداة حقيقية
        مثال: "ابحث عن..." → web search
        مثال: "أنشئ صورة..." → image generation
        مثال: "نفذ أمر..." → server control
        مثال: "ابنِ وركفلو..." → n8n workflow
        مثال: "حلل الفيديو..." → video analysis
        """
        if not hasattr(self, '_real_tools') or not self._real_tools:
            return None

        msg_lower = message.lower().strip()

        # Map keywords to tools
        tool_patterns = {
            "web_search": ["ابحث عن", "بحث عن", "ابحث لي", "سيرش", "search", "ويب سيرش"],
            "image_gen": ["أنشئ صورة", "اصنع صورة", "ارسم", "صورة من", "generate image", "create image"],
            "video_analysis": ["حلل الفيديو", "حلل هذا الفيديو", "تحليل فيديو", "analyze video", "الفيديو ده"],
            "n8n_workflow": ["وركفلو", "n8n", "workflow", "أتمتة", "اتمتة", "automation"],
            "blender": ["بلندر", "blender", "3d", "نموذج ثلاثي", "تصميم معماري"],
            "server_control": ["نفذ أمر", "شغل أمر", "run command", "تنفيذ أمر", "على السيرفر"],
            "code_gen": ["اكتب كود", "ابنِ سكربت", "برمج", "write code", "كود", "برنامج"],
            "system_info": ["معلومات النظام", "حالة السيرفر", "system info", "server status"],
        }

        for tool_name, keywords in tool_patterns.items():
            if any(kw in msg_lower for kw in keywords):
                try:
                    # Build kwargs based on tool
                    kwargs = {}
                    if tool_name == "web_search":
                        kwargs = {"query": message, "num_results": 10}
                    elif tool_name == "image_gen":
                        kwargs = {"prompt": message}
                    elif tool_name == "video_analysis":
                        kwargs = {"video_path": context.get("video_path", message), "question": message}
                    elif tool_name == "n8n_workflow":
                        kwargs = {"description": message}
                    elif tool_name == "blender":
                        kwargs = {"script_description": message}
                    elif tool_name == "server_control":
                        kwargs = {"command": message, "working_dir": context.get("working_dir", "")}
                    elif tool_name == "code_gen":
                        kwargs = {"description": message, "language": context.get("language", "python"), "execute": context.get("execute", False)}
                    elif tool_name == "system_info":
                        kwargs = {}

                    result = await self._real_tools.call_tool(tool_name, **kwargs)

                    return {
                        "response": result.output[:5000] if result.success else f"فشل التنفيذ: {result.error}",
                        "confidence": 0.9 if result.success else 0.3,
                        "winning_brain": f"real_tool:{tool_name}",
                        "escalation": "real_tool",
                        "tool_name": tool_name,
                        "artifacts": result.artifacts,
                        "execution_time_ms": result.duration_ms,
                    }
                except Exception as e:
                    logger.error("Tool execution failed: %s", e)
                    return {
                        "response": f"خطأ في تنفيذ الأداة: {str(e)}",
                        "confidence": 0.1,
                        "escalation": "error",
                    }

        return None

    # ─────────────────────────────────────────────────────────────────────────
    # v30: NeuralBus + Living System Integration
    # ─────────────────────────────────────────────────────────────────────────

    def _on_neural_signal(self, signal):
        """
        v35: MERGED NeuralBus signal handler — single definition (no duplicates).
        Handles: vital signals → working memory, error → self-healing,
        emotion/bond → brain weights + emotional memory, actions → vitals.
        """
        try:
            signal_type = getattr(signal, 'signal_type', str(signal))
            payload = getattr(signal, 'payload', getattr(signal, 'data', {}))

            # ── Route vital signals to working memory ──
            if signal_type in ("vital_change", "energy_drop", "stress_spike"):
                if hasattr(self, '_working_memory') and self._working_memory:
                    self._working_memory.add(
                        f"إشارة حيوية: {signal_type} — {json.dumps(payload, ensure_ascii=False)[:200] if isinstance(payload, dict) else str(payload)[:200]}",
                        salience=0.6,
                        item_type="vital",
                        source="neural_bus",
                    )

            # ── Route error signals to self-healing ──
            if signal_type == "error_detected" and hasattr(self, '_self_healing') and self._self_healing:
                # SelfHealingEngine has run_health_check(), not heal()
                try:
                    self._self_healing.run_health_check()
                    logger.info("NeuralBus → Kernel: error_detected → self-healing health check triggered")
                except Exception as heal_err:
                    logger.warning("Self-healing trigger failed: %s", heal_err)

            # ── Emotion/vital shifts → update dynamic brain weights ──
            if signal_type in ("emotion_shift", "vital_change", "energy_drop"):
                self._update_dynamic_brain_weights()
                logger.debug("NeuralBus → Kernel: %s → brain weights updated", signal_type)

            # ── Bond strengthened → record in emotional memory ──
            if signal_type == "bond_strengthened":
                if self._emotional_memory:
                    self._emotional_memory.store_episode(
                        content=payload.get("description", "تقوية الرابطة") if isinstance(payload, dict) else "تقوية الرابطة",
                        emotional_summary="ارتباط أعمق",
                        valence=0.8,
                        arousal=0.5,
                    )

            # ── Error detected → increment stress ──
            if signal_type == "error_detected":
                if hasattr(self, '_living_state') and self._living_state:
                    from mamoun.core.living_state import VitalSign
                    self._living_state._adjust(VitalSign.STRESS.value, 5)

            # ── Task success → boost mood and energy ──
            if signal_type == "action_completed":
                if hasattr(self, '_living_state') and self._living_state:
                    from mamoun.core.living_state import VitalSign
                    self._living_state._adjust(VitalSign.MOOD.value, 3)
                    self._living_state._adjust(VitalSign.ENERGY.value, 1)

            # ── Task failure → drop mood, raise stress ──
            if signal_type == "action_failed":
                if hasattr(self, '_living_state') and self._living_state:
                    from mamoun.core.living_state import VitalSign
                    self._living_state._adjust(VitalSign.MOOD.value, -5)
                    self._living_state._adjust(VitalSign.STRESS.value, 3)

        except Exception as e:
            logger.warning("NeuralBus signal handler error: %s", e)

    def _enrich_context_with_living_state(self, context: dict, message: str) -> dict:
        """
        v30: Enrich the context with living system data before processing.
        This ensures brain deliberation considers emotions, energy, and bonding.
        """
        if not self._living_systems_initialized:
            return context

        # Add dynamic brain weights to context
        context["brain_weights"] = dict(self._dynamic_brain_weights)

        # Add emotional state
        if self._living_state:
            vitals = self._living_state.get_vitals_snapshot()
            context["living_state"] = {
                "energy": vitals.get("energy", {}).get("value", 75),
                "mood": vitals.get("mood", {}).get("value", 15),
                "stress": vitals.get("stress", {}).get("value", 10),
                "arousal": vitals.get("arousal", {}).get("value", 35),
                "attachment": vitals.get("attachment", {}).get("value", 30),
                "curiosity": vitals.get("curiosity", {}).get("value", 50),
                "dominant_emotion": self._living_state.get_dominant_emotion(),
                "energy_level": self._living_state._get_energy_level(),
            }

        # Add bonding level
        if self._deep_bonding:
            try:
                status = self._deep_bonding.get_status()
                context["bonding"] = {
                    "phase": status.get("phase", "stranger"),
                    "trust": status.get("trust", 0),
                    "intimacy": status.get("intimacy", 0),
                    "interactions": status.get("total_interactions", 0),
                }
            except Exception:
                pass

        # Add communication style suggestion based on bonding
        if self._deep_bonding:
            try:
                style = self._deep_bonding.get_communication_style_suggestion()
                if style:
                    context["communication_style"] = style
            except Exception:
                pass

        return context

    def _update_dynamic_brain_weights(self):
        """
        v30: Adjust brain weights dynamically based on living system state.

        Rules:
        - When user is sad (mood < -20): neural brain weight ↑ (more empathetic)
        - When question is analytical (high curiosity): symbolic brain weight ↑
        - When energy is low: reduce active brain count (fewer weights distributed)
        - When stress is high: causal brain weight ↑ (more careful reasoning)
        - When attachment is high: neural brain weight ↑ (more personal)
        - When bonding phase is high: all brains get slight confidence boost
        """
        import time as _time
        now = _time.time()
        # Throttle: don't update more than once per 5 seconds
        if now - self._last_weight_update < 5.0:
            return
        self._last_weight_update = now

        weights = dict(self._base_brain_weights)

        if not self._living_systems_initialized or not self._living_state:
            self._dynamic_brain_weights = weights
            return

        vitals = self._living_state.get_vitals_snapshot()
        energy = vitals.get("energy", {}).get("value", 75)
        mood = vitals.get("mood", {}).get("value", 15)
        stress = vitals.get("stress", {}).get("value", 10)
        curiosity = vitals.get("curiosity", {}).get("value", 50)
        attachment = vitals.get("attachment", {}).get("value", 30)

        # Rule 1: Sad user → neural brain (empathetic) gets more weight
        if mood < -20:
            weights["neural"] += 0.08
            weights["symbolic"] -= 0.03
        # Rule 2: Happy/energetic user → all brains slight boost, especially bayesian
        elif mood > 30:
            weights["bayesian"] += 0.04
            weights["neural"] += 0.03

        # Rule 3: High curiosity → symbolic (analytical) gets more weight
        if curiosity > 70:
            weights["symbolic"] += 0.06
            weights["neural"] -= 0.02

        # Rule 4: High stress → causal (careful reasoning) gets more weight
        if stress > 50:
            weights["causal"] += 0.08
            weights["bayesian"] -= 0.03

        # Rule 5: High attachment → neural (personal) gets more weight
        if attachment > 60:
            weights["neural"] += 0.05
            weights["world_model"] -= 0.02

        # Rule 6: Low energy → reduce weight spread (fewer brains active)
        if energy < 30:
            # Focus on the top 2-3 brains
            sorted_brains = sorted(weights.items(), key=lambda x: x[1], reverse=True)
            for i, (brain_id, weight) in enumerate(sorted_brains):
                if i >= 3:  # Reduce weight for lower-priority brains
                    weights[brain_id] = max(0.05, weight * 0.5)

        # Rule 7: Bonding phase influence
        if self._deep_bonding:
            try:
                status = self._deep_bonding.get_status()
                phase = status.get("phase", "stranger")
                if phase in ("companion", "bonded"):
                    # Deep relationship → neural brain strongly preferred
                    weights["neural"] += 0.06
                elif phase == "friend":
                    weights["neural"] += 0.03
            except Exception:
                pass

        # Normalize: ensure weights sum to ~1.0
        total = sum(weights.values())
        if total > 0:
            weights = {k: round(v / total, 4) for k, v in weights.items()}

        self._dynamic_brain_weights = weights
        logger.debug("Dynamic brain weights updated: %s", weights)

    def _process_emotional_event(self, event_type: str, message: str = ""):
        """
        v30: Process an emotional event from a user message.
        Feeds the LivingStateEngine so emotions change with interaction.
        """
        if not self._living_state or not self._living_systems_initialized:
            return

        from mamoun.core.living_state import EmotionalEvent

        # Determine valence based on message content
        valence = 0.0
        intensity = 0.5
        msg_lower = message.lower()

        # Positive indicators
        positive_words = ["شكراً", "ممتاز", "رائع", "أحسنت", "thanks", "great", "awesome", "good job", "حبيبي", "يا سلام"]
        negative_words = ["غبي", "خطأ", "سيء", "رديء", "stupid", "wrong", "bad", "terrible", "لا يعمل", "فشل"]
        greeting_words = ["مرحبا", "أهلا", "السلام", "هلا", "hello", "hi", "hey", "صباح", "مساء"]

        if any(w in msg_lower for w in positive_words):
            valence = 0.8
            intensity = 0.7
            event_type = "user_praise"
        elif any(w in msg_lower for w in negative_words):
            valence = -0.6
            intensity = 0.6
            event_type = "user_criticism"
        elif any(w in msg_lower for w in greeting_words):
            valence = 0.9
            intensity = 0.8
            event_type = "greeting"
        else:
            valence = 0.2  # Neutral-slightly positive
            intensity = 0.4

        event = EmotionalEvent(
            timestamp=time.time(),
            event_type=event_type,
            intensity=intensity,
            valence=valence,
            source="user",
            description=message[:200],
        )
        self._living_state.process_event(event)

        # Also record in DeepBonding
        if self._deep_bonding:
            self._deep_bonding.record_interaction(
                user_message=message,
                valence=valence,
                response_quality=valence,  # Approximate
            )

        # Publish to NeuralBus
        if self._neural_bus:
            self._neural_bus.publish(
                signal_type="emotion_shift",
                source="kernel",
                payload={
                    "event_type": event_type,
                    "valence": valence,
                    "dominant_emotion": self._living_state.get_dominant_emotion(),
                },
            )

    def _evaluate_reflexes(self, context: dict):
        """
        v30: Auto-evaluate reflexes before processing a user message.
        If a reflex fires, it may block or modify the request.
        """
        if not self._reflexes_engine or not self._living_systems_initialized:
            return

        try:
            responses = self._reflexes_engine.check(context)
            for r in responses:
                logger.info("Reflex fired: %s → %s (priority: %s)",
                          r.trigger_id, r.action_taken, r.priority)
                # Publish reflex activation to NeuralBus
                if self._neural_bus:
                    self._neural_bus.publish(
                        signal_type="vital_change",
                        source="reflexes",
                        payload={"reflex": r.trigger_id, "action": r.action_taken},
                        priority=2,  # HIGH
                    )
        except Exception as e:
            logger.warning("Reflex evaluation error: %s", e)

    def get_v23_status(self) -> dict:
        """حالة أنظمة v23 — Neural Bus + Executor + Self-Healing"""
        result = {"version": "v23.0", "systems": {}}
        try:
            from mamoun.core.neural_bus import neural_bus
            result["systems"]["neural_bus"] = neural_bus.get_status()
        except Exception as e:
            result["systems"]["neural_bus"] = {"error": str(e)}
        try:
            from mamoun.core.absolute_executor import absolute_executor
            result["systems"]["executor"] = absolute_executor.get_status()
        except Exception as e:
            result["systems"]["executor"] = {"error": str(e)}
        try:
            from mamoun.core.self_healing import self_healing
            result["systems"]["self_healing"] = self_healing.get_status()
        except Exception as e:
            result["systems"]["self_healing"] = {"error": str(e)}
        return result

    def get_v23_data(self) -> dict:
        """بيانات v23 للواجهة"""
        return self.get_v23_status()

    def get_v24_status(self) -> dict:
        """حالة أنظمة v24"""
        result = {"version": "v24.0", "systems": {}}
        for name, module_path, attr in [
            ("live_self_modifier", "mamoun.evolution.live_self_modifier", "live_self_modifier"),
            ("inner_monologue", "mamoun.core.inner_monologue", "inner_monologue"),
            ("behavioral_memory", "mamoun.memory.behavioral_memory", "behavioral_memory"),
            ("world_monitor", "mamoun.awareness.world_monitor", "world_monitor"),
            ("idea_generator", "mamoun.creative.idea_generator", "idea_generator"),
        ]:
            try:
                mod = __import__(module_path, fromlist=[attr])
                obj = getattr(mod, attr)
                if hasattr(obj, '_initialized') and not obj._initialized:
                    obj.initialize()
                result["systems"][name] = obj.get_status()
            except Exception as e:
                result["systems"][name] = {"error": str(e)}
        return result

    def get_v25_status(self) -> dict:
        """حالة ركائز v25"""
        result = {"version": "v25.0", "pillars": {}}
        for name, module_path, attr in [
            ("neural_architecture", "mamoun.neural.neural_mesh", "neural_mesh"),
            ("transfer_learning", "mamoun.transfer.synaptic_intelligence", "synaptic_intelligence"),
            ("long_term_planning", "mamoun.core.long_term_planner", "long_term_planner"),
            ("causal_world_model", "mamoun.awareness.causal_world_model", "causal_world_model"),
        ]:
            try:
                mod = __import__(module_path, fromlist=[attr])
                obj = getattr(mod, attr)
                if hasattr(obj, 'get_stats'):
                    result["pillars"][name] = obj.get_stats()
                elif hasattr(obj, 'get_status'):
                    result["pillars"][name] = obj.get_status()
                else:
                    result["pillars"][name] = {"status": "loaded"}
            except Exception as e:
                result["pillars"][name] = {"error": str(e)}
        return result


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────

_kernel: Optional[MamounKernel] = None


def get_kernel() -> MamounKernel:
    """Get the global kernel instance."""
    global _kernel
    if _kernel is None:
        _kernel = MamounKernel()
    return _kernel
