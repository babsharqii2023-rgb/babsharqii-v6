"""
BABSHARQII v61 — MamounKernel (BACKWARD-COMPATIBLE ADAPTER)

This file serves as a compatibility layer that:
1. Provides get_kernel() for backward compatibility
2. Preserves GlobalWorkspace, ReflexionEngine, EscalationLadder (unique to this path)
3. MamounKernel delegates to super_brain/mamoun_kernel.py for actual operations

The old MamounKernel (with independent brain competition, event processing)
has been consolidated. The canonical kernel is in super_brain/mamoun_kernel.py.
This adapter preserves the old API while delegating to the new kernel.

Migration: core/mamoun_kernel.py → core/super_brain/mamoun_kernel.py
Status: ADAPTER — delegates to super_brain MamounKernel
"""

import asyncio
import time
import json
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Any

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


# ── Global Workspace (unique to this path — no duplicate in super_brain) ──

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


# ── Reflexion Engine (unique to this path — no duplicate in super_brain) ──

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


# ── Escalation Ladder (unique to this path — no duplicate in super_brain) ──

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


# ── MamounKernel Adapter ────────────────────────────────────────────────

class MamounKernel:
    """
    Backward-compatible MamounKernel that delegates to super_brain.

    Preserves old API (get_kernel, register_brain, run_forever, submit_event)
    while delegating actual operations to super_brain/mamoun_kernel.py.

    Old-style components (GlobalWorkspace, ReflexionEngine, EscalationLadder)
    are still available for backward compatibility.
    """

    def __init__(self, llm_client=None):
        """Initialize the adapter kernel."""
        self.llm = llm_client

        # Old-style components (preserved for backward compatibility — NOT duplicated)
        self.workspace = GlobalWorkspace()
        self.reflexion = ReflexionEngine(self.llm)
        self.escalation = EscalationLadder()

        # Delegate to super_brain kernel
        self._new_kernel = None
        try:
            from mamoun.core.super_brain.mamoun_kernel import MamounKernel as _NewKernel
            self._new_kernel = _NewKernel()
            logger.info("MamounKernel: delegating to super_brain kernel")
        except ImportError:
            logger.info("MamounKernel: super_brain not available, using legacy mode")

        # Brain management
        self._brains: dict = {}
        self._running = False
        self._cycle_count = 0

        # Event queue (backward-compatible)
        self._event_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()

        # Dynamic brain weights
        self._base_brain_weights = {
            "neural": 0.25, "causal": 0.22, "symbolic": 0.18,
            "bayesian": 0.17, "world_model": 0.18,
        }
        self._dynamic_brain_weights = dict(self._base_brain_weights)

        logger.info("MamounKernel v61 (adapter) initialized")

    def register_brain(self, brain_id: str, brain_instance):
        """Register a brain with the kernel."""
        self._brains[brain_id] = brain_instance
        logger.info("Brain registered: %s", brain_id)

    async def submit_event(self, event: KernelEvent):
        """Submit an event to the kernel's priority queue."""
        await self._event_queue.put((event.priority.value, time.time(), event))

    async def run_forever(self):
        """Main consciousness loop — delegates to super_brain if available."""
        if self._new_kernel:
            try:
                await self._new_kernel.initialize()
                await self._new_kernel.run()
                return
            except Exception as e:
                logger.error(f"super_brain kernel failed: {e}, falling back to legacy")

        # Legacy fallback loop
        self._running = True
        logger.info("MamounKernel started (legacy mode)")
        while self._running:
            try:
                self._cycle_count += 1
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("MamounKernel error: %s", e)
                await asyncio.sleep(1)
        logger.info("MamounKernel stopped after %d cycles", self._cycle_count)

    def get_status(self) -> dict:
        """Get kernel status."""
        status = {
            "version": "v61-adapter",
            "running": self._running,
            "cycle_count": self._cycle_count,
            "brains_registered": list(self._brains.keys()),
            "workspace": self.workspace.get_status(),
            "new_kernel_available": self._new_kernel is not None,
        }
        if self._new_kernel:
            try:
                status["new_kernel_status"] = self._new_kernel.get_status()
            except Exception:
                pass
        return status

    def get_self_assessment(self) -> dict:
        """Get honest self-assessment."""
        if self._new_kernel:
            try:
                return self._new_kernel.get_self_assessment()
            except Exception:
                pass
        return {
            "version": "v61-adapter",
            "kernel_type": "adapter",
            "brains_count": len(self._brains),
        }

    @property
    def project_orchestrator(self):
        if self._new_kernel:
            return self._new_kernel.get_component("external_project_controller")
        return None


# ── Singleton ───────────────────────────────────────────────────────────
_kernel_instance: Optional[MamounKernel] = None

def get_kernel(llm_client=None) -> MamounKernel:
    """Get the singleton kernel instance."""
    global _kernel_instance
    if _kernel_instance is None:
        _kernel_instance = MamounKernel(llm_client=llm_client)
    return _kernel_instance
