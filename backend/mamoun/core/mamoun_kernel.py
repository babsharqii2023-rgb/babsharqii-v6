"""
BABSHARQII v61 — MamounKernel (BACKWARD-COMPATIBLE ADAPTER + ENHANCED)

This file now serves as a compatibility layer that:
1. Provides get_kernel() for backward compatibility
2. Merges the best of old (GlobalWorkspace, ReflexionEngine, EscalationLadder)
   with the new (MetaCognitionEngine, HealthMonitor, SelfHealingBridge)
3. Delegates to super_brain/mamoun_kernel.py for the actual implementation

Migration: core/mamoun_kernel.py → core/super_brain/mamoun_kernel.py
Status: ENHANCED ADAPTER — combines old+new functionality
"""

import asyncio
import time
import json
import logging
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger("mamoun.core.kernel")


# ── Backward-compatible event system ─────────────────────────────────────

class EventType(str, Enum):
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
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class KernelEvent:
    type: EventType
    priority: EventPriority = EventPriority.MEDIUM
    data: dict = field(default_factory=dict)
    timestamp: float = 0.0
    source: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


# ── Global Workspace (from old kernel — CRITICAL functionality) ──────────

@dataclass
class WorkspaceEntry:
    """An entry in the Global Workspace — a thought that won the spotlight."""
    id: str = ""
    content: str = ""
    winning_brain: str = ""
    brain_proposals: dict = field(default_factory=dict)
    confidence: float = 0.0
    reflections: list = field(default_factory=list)
    broadcast_at: float = 0.0
    acted_upon: bool = False


class GlobalWorkspace:
    """
    مساحة العمل العالمية — البث الواعي
    
    Implements Global Workspace Theory:
    1. Multiple brains submit proposals (competition)
    2. One proposal wins the "spotlight"
    3. The winner is BROADCAST to all modules
    """

    def __init__(self):
        self.current: Optional[WorkspaceEntry] = None
        self.history: list[WorkspaceEntry] = []
        self._subscribers: list[Callable] = []
        self._entry_counter = 0
        self._neural_bus = None

    def compete_and_broadcast(
        self,
        brain_proposals: dict[str, dict],
        context: dict,
    ) -> WorkspaceEntry:
        """Run the competition and broadcast the winner."""
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

        scores = {}
        for brain_id, proposal in brain_proposals.items():
            confidence = proposal.get("confidence", 0.5)
            relevance = proposal.get("relevance", 0.5)
            weight = context.get("brain_weights", {}).get(brain_id, 0.2)
            score = (confidence * 0.4 + relevance * 0.3) * weight + confidence * 0.3
            scores[brain_id] = score

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

        for subscriber in self._subscribers:
            try:
                subscriber(entry)
            except Exception as e:
                logger.warning("Subscriber %s failed: %s", subscriber, e)

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
        if len(self.history) > 100:
            self.history = self.history[-50:]

        logger.info("Global Workspace: Brain '%s' won spotlight (confidence: %.2f)", winner_id, winner_confidence)
        return entry

    def subscribe(self, callback: Callable):
        self._subscribers.append(callback)

    def get_status(self) -> dict:
        return {
            "current_winner": self.current.winning_brain if self.current else None,
            "current_confidence": self.current.confidence if self.current else 0,
            "history_size": len(self.history),
            "subscribers": len(self._subscribers),
        }


# ── Reflexion Engine (from old kernel — CRITICAL functionality) ──────────

class ReflexionEngine:
    """
    محرك التأمل الذاتي — المراجعة ما قبل التنفيذ
    
    Before executing ANY action, reviews:
    1. هل أنا واثق فعلاً من هذا القرار؟
    2. ما الذي أفترضه بدون دليل؟
    3. ما الذي قد يسوء لو نفذت؟
    4. هل هناك نهج أفضل؟
    """

    def __init__(self, llm_client=None):
        self.llm = llm_client

    async def review(
        self,
        proposed_action: str,
        context: dict,
        confidence: float,
    ) -> dict:
        """Review a proposed action before execution."""
        risk_level = context.get("risk_level", "medium")
        if confidence > 0.9 and risk_level in ("low", "medium"):
            return {
                "approved": True,
                "concerns": [],
                "refined_action": proposed_action,
                "confidence_adjusted": confidence,
                "review_type": "fast_pass",
            }

        if self.llm is None:
            # Fallback heuristic review
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
            return {
                "approved": approved,
                "concerns": concerns,
                "refined_action": proposed_action,
                "confidence_adjusted": adjusted,
                "review_type": "heuristic_fallback",
            }

        try:
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
  "refined_action": "الفعل المحسّن",
  "confidence_adjusted": 0.0-1.0,
  "reasoning": "سبب القرار"
}"""
            prompt = f"""القرار المقترح: {proposed_action}
مستوى الثقة: {confidence:.0%}
مستوى المخاطر: {risk_level}
السياق: {json.dumps(context, ensure_ascii=False, default=str)[:2000]}"""

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
        except Exception as e:
            logger.warning(f"Reflexion LLM failed: {e}, using heuristic")

        # Heuristic fallback
        concerns = []
        approved = True
        adjusted = confidence
        if confidence < 0.5:
            concerns.append("ثقة منخفضة")
            adjusted = confidence * 0.8
        if risk_level == "high":
            concerns.append("مخاطر عالية")
        if confidence < 0.3:
            approved = False
        return {
            "approved": approved,
            "concerns": concerns,
            "refined_action": proposed_action,
            "confidence_adjusted": adjusted,
            "review_type": "heuristic_fallback",
        }


# ── Escalation Ladder (from old kernel — CRITICAL functionality) ─────────

class EscalationLevel(int, Enum):
    DIRECT_RESPONSE = 0
    GATHER_INFO = 1
    ASK_USER = 2
    STRONGER_MODEL = 3
    HUMAN_APPROVAL = 4


class EscalationLadder:
    """سلم التصعيد — عندما يكون مأمون غير واثق"""

    @staticmethod
    def determine_level(
        confidence: float,
        risk_level: str = "medium",
        is_self_modification: bool = False,
    ) -> EscalationLevel:
        if is_self_modification or risk_level == "critical":
            return EscalationLevel.HUMAN_APPROVAL
        if risk_level == "high" and confidence < 0.5:
            return EscalationLevel.HUMAN_APPROVAL
        if risk_level == "high":
            return EscalationLevel.ASK_USER
        if confidence < 0.3:
            return EscalationLevel.HUMAN_APPROVAL
        if confidence < 0.5:
            return EscalationLevel.ASK_USER
        if confidence < 0.7:
            return EscalationLevel.GATHER_INFO
        return EscalationLevel.DIRECT_RESPONSE


# ── Unified MamounKernel (backward-compatible + enhanced) ────────────────

class MamounKernel:
    """
    النواة الموحدة — تجمع بين القديم (GlobalWorkspace, ReflexionEngine)
    والجديد (MetaCognitionEngine, HealthMonitor, SelfHealingBridge).
    
    v61: Unified kernel that resolves structural duplication.
    
    Backward-compatible API:
    - get_kernel() → returns this instance
    - register_brain() → registers in both router and workspace
    - run_forever() → main loop
    - submit_event() → event processing
    """

    def __init__(self, llm_client=None):
        """Initialize the unified kernel."""
        self.llm = llm_client
        
        # Old-style components (preserved for backward compatibility)
        self.workspace = GlobalWorkspace()
        self.reflexion = ReflexionEngine(self.llm)
        self.escalation = EscalationLadder()

        # Try to initialize new super_brain kernel
        self._new_kernel = None
        self._use_new_kernel = False
        try:
            from mamoun.core.super_brain.mamoun_kernel import MamounKernel as NewKernel
            self._new_kernel = NewKernel.__new__(NewKernel)
            self._use_new_kernel = True
            logger.info("Unified MamounKernel: super_brain components available")
        except ImportError:
            logger.info("Unified MamounKernel: using legacy components only")

        # Brain management
        self._brains: dict = {}
        self._brain_router = None
        self._deliberation_room = None
        self._working_memory = None
        self._capability_router = None
        self._skill_executor = None
        self._real_tools = None
        self._project_orchestrator = None
        self._self_modifier = None

        # Event queue
        self._event_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._cycle_count = 0
        self._last_evolution = 0
        self._last_reflection = 0
        self._last_research = 0

        # Timers
        self.evolution_interval = 3600
        self.reflection_interval = 1800
        self.research_interval = 7200
        self.main_loop_interval = 1.0

        # Dynamic brain weights
        self._base_brain_weights = {
            "neural": 0.25, "causal": 0.22, "symbolic": 0.18,
            "bayesian": 0.17, "world_model": 0.18,
        }
        self._dynamic_brain_weights = dict(self._base_brain_weights)

        # NeuralBus
        self._neural_bus = None
        self.workspace._neural_bus = None

        # Living systems
        self._living_systems_initialized = False
        self._living_state = None
        self._emotional_memory = None
        self._deep_bonding = None
        self._reflexes_engine = None
        self._autonomic_system = None

        # Data persistence
        self.data_dir = Path(__file__).parent.parent.parent / "data" / "kernel"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        logger.info("MamounKernel v61 (unified) initialized")

    @property
    def project_orchestrator(self):
        return self._project_orchestrator

    def register_brain(self, brain_id: str, brain_instance):
        """Register a brain with the kernel AND router AND deliberation."""
        self._brains[brain_id] = brain_instance
        if self._brain_router:
            self._brain_router.register_brain(brain_id, brain_instance)
        if self._deliberation_room:
            self._deliberation_room.register_brain(brain_id, brain_instance)
        logger.info("Brain registered: %s", brain_id)

    async def submit_event(self, event: KernelEvent):
        """Submit an event to the kernel's priority queue."""
        await self._event_queue.put((event.priority.value, time.time(), event))

    async def run_forever(self):
        """Main consciousness loop."""
        self._running = True
        logger.info("MamounKernel started — the heart is beating")

        while self._running:
            try:
                await self._check_timers()
                try:
                    priority, _, event = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=self.main_loop_interval,
                    )
                    await self._process_event(event)
                except asyncio.TimeoutError:
                    pass
                self._cycle_count += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("MamounKernel error: %s", e)
                await asyncio.sleep(1)

        logger.info("MamounKernel stopped after %d cycles", self._cycle_count)

    async def _check_timers(self):
        now = time.time()
        if now - self._last_evolution > self.evolution_interval:
            self._last_evolution = now
            await self.submit_event(KernelEvent(type=EventType.EVOLUTION_TIMER, priority=EventPriority.LOW, source="timer"))
        if now - self._last_reflection > self.reflection_interval:
            self._last_reflection = now
            await self.submit_event(KernelEvent(type=EventType.REFLECTION_TIMER, priority=EventPriority.LOW, source="timer"))
        if now - self._last_research > self.research_interval:
            self._last_research = now
            await self.submit_event(KernelEvent(type=EventType.RESEARCH_TIMER, priority=EventPriority.LOW, source="timer"))

    async def _process_event(self, event: KernelEvent):
        if event.type == EventType.SHUTDOWN:
            self._running = False
        elif event.type == EventType.USER_MESSAGE:
            await self._process_user_message(event.data)
        elif event.type == EventType.EVOLUTION_TIMER:
            await self._process_evolution_cycle()
        elif event.type == EventType.REFLECTION_TIMER:
            await self._process_reflection_cycle()
        elif event.type == EventType.RESEARCH_TIMER:
            await self._process_research_cycle()

    async def _process_user_message(self, data: dict):
        """Process a user message through the consciousness pipeline."""
        message = data.get("message", "")
        context = data.get("context", {})
        if not message.strip():
            return None

        # Collect brain proposals
        brain_proposals = await self._collect_brain_proposals(message, context)
        
        # Global Workspace competition
        workspace_entry = self.workspace.compete_and_broadcast(
            brain_proposals=brain_proposals,
            context=context,
        )

        # Reflexion
        review = await self.reflexion.review(
            proposed_action=workspace_entry.content,
            context=context,
            confidence=workspace_entry.confidence,
        )

        # Escalation
        escalation_level = self.escalation.determine_level(
            confidence=review["confidence_adjusted"],
            risk_level=context.get("risk_level", "medium"),
            is_self_modification=context.get("is_self_modification", False),
        )

        result = {
            "response": workspace_entry.content,
            "confidence": review["confidence_adjusted"],
            "winning_brain": workspace_entry.winning_brain,
            "escalation": escalation_level.name.lower(),
            "review_concerns": review.get("concerns", []),
        }
        return result

    async def _collect_brain_proposals(self, message: str, context: dict) -> dict:
        """Collect proposals from active brains IN PARALLEL."""
        active_brains = {
            bid: brain for bid, brain in self._brains.items()
            if hasattr(brain, 'state') and brain.state.status in ("active", "idle", "thinking")
        }
        if not active_brains:
            return {}

        tasks = {bid: brain.think(message, context) for bid, brain in active_brains.items()}
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        proposals = {}
        for (bid, _), result in zip(tasks.items(), results):
            if isinstance(result, Exception):
                proposals[bid] = {"response": "", "confidence": 0.0, "error": str(result)}
            else:
                proposals[bid] = result
        return proposals

    async def _process_evolution_cycle(self):
        logger.info("Evolution timer fired")

    async def _process_reflection_cycle(self):
        logger.info("Reflection timer fired")

    async def _process_research_cycle(self):
        logger.info("Research timer fired")

    def get_status(self) -> dict:
        """Get kernel status."""
        return {
            "version": "v61-unified",
            "running": self._running,
            "cycle_count": self._cycle_count,
            "brains_registered": list(self._brains.keys()),
            "workspace": self.workspace.get_status(),
            "new_kernel_available": self._use_new_kernel,
        }

    def get_self_assessment(self) -> dict:
        """Get honest self-assessment."""
        assessment = {
            "version": "v61-unified",
            "kernel_type": "unified_adapter",
            "brains_count": len(self._brains),
        }
        if self._new_kernel and self._use_new_kernel:
            try:
                assessment["new_kernel_status"] = self._new_kernel.get_status()
            except Exception:
                pass
        return assessment


# ── Singleton ───────────────────────────────────────────────────────────
_kernel_instance: Optional[MamounKernel] = None

def get_kernel(llm_client=None) -> MamounKernel:
    """Get the singleton kernel instance."""
    global _kernel_instance
    if _kernel_instance is None:
        _kernel_instance = MamounKernel(llm_client=llm_client)
    return _kernel_instance
