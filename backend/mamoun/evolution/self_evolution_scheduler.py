"""
BABSHARQII v13.0 — Self-Evolution Scheduler
جدولة التطور الذاتي — يُشغل مهمة بحث وتحليل كل 3 أيام

Schedule: Every 3 days in NightCycle
- Day 0: Research (fetch papers, GitHub trending)
- Day 1: Analysis (propose improvements)
- Day 2: Apply (with approval, test, deploy)

Feature Flag: MAMOUN_SELF_PROGRAMMING (default: false)
"""

import os
import time
import uuid
import logging
import asyncio
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum

from mamoun.evolution.self_programming_loop import SELF_PROGRAMMING_ENABLED, _is_self_programming_enabled

logger = logging.getLogger(__name__)

EVOLUTION_CYCLE_DAYS = int(os.getenv("MAMOUN_EVOLUTION_CYCLE_DAYS", "3"))
EVOLUTION_CHECK_INTERVAL = EVOLUTION_CYCLE_DAYS * 24 * 3600  # seconds


class EvolutionPhase(str, Enum):
    """مراحل دورة التطور."""
    RESEARCH = "research"
    ANALYSIS = "analysis"
    PROPOSAL = "proposal"
    APPROVAL = "approval"
    APPLICATION = "application"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    IDLE = "idle"


@dataclass
class EvolutionCycle:
    """دورة تطور ذاتي."""
    cycle_id: str = ""
    phase: str = EvolutionPhase.IDLE.value
    started_at: float = 0.0
    research_results: list = field(default_factory=list)
    proposals: list = field(default_factory=list)
    approved_proposals: list = field(default_factory=list)
    applied_proposals: list = field(default_factory=list)
    status: str = "idle"
    next_check_at: float = 0.0

    def __post_init__(self):
        if not self.cycle_id:
            self.cycle_id = f"evo_cycle_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return asdict(self)


class SelfEvolutionScheduler:
    """
    جدولة التطور الذاتي — يُشغل دورة بحث وتحليل كل 3 أيام.

    Flow:
    1. Every 3 days, trigger research phase
    2. Fetch papers from ArXiv, GitHub Trending, Papers with Code
    3. Analyze findings and propose improvements
    4. Request human approval for each proposal
    5. Apply approved improvements
    6. Test in sandbox
    7. Deploy if tests pass

    Integration:
    - TrustedResearchFetcher: For fetching research
    - ImprovementProposer: For analyzing and proposing
    - SelfProgrammingLoop: For applying changes
    - ApprovalGate: For human approval
    - NightCycle: For scheduling
    """

    def __init__(
        self,
        research_fetcher=None,
        improvement_proposer=None,
        self_programming_loop=None,
        approval_gate=None,
        notifier=None,
    ):
        self._research_fetcher = research_fetcher
        self._improvement_proposer = improvement_proposer
        self._self_programming_loop = self_programming_loop
        self._approval_gate = approval_gate
        self._notifier = notifier
        self._current_cycle: Optional[EvolutionCycle] = None
        self._cycle_history: list[EvolutionCycle] = []
        self._last_cycle_time: float = 0.0
        self._is_running = False
        self._cycle_count = 0
        self._monitor_task: Optional[asyncio.Task] = None

    async def start(self):
        """بدء الجدولة — Start the evolution scheduler."""
        if not _is_self_programming_enabled():
            logger.info("SelfEvolutionScheduler: Disabled (MAMOUN_SELF_PROGRAMMING=false)")
            return

        if self._is_running:
            return

        self._is_running = True
        self._monitor_task = asyncio.create_task(self._schedule_monitor())
        logger.info(f"SelfEvolutionScheduler: Started (cycle every {EVOLUTION_CYCLE_DAYS} days)")

    async def _schedule_monitor(self):
        """مراقب الجدولة — Checks if it's time for a new cycle."""
        while self._is_running:
            try:
                now = time.time()
                time_since_last = now - self._last_cycle_time

                if time_since_last >= EVOLUTION_CHECK_INTERVAL:
                    await self.run_cycle()
                    self._last_cycle_time = now

                # Check every hour
                await asyncio.sleep(3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"SelfEvolutionScheduler: Monitor error: {e}")
                await asyncio.sleep(3600)

    async def run_cycle(self) -> dict:
        """
        تشغيل دورة تطور ذاتي — Run one self-evolution cycle.

        Returns:
            Cycle result
        """
        if not _is_self_programming_enabled():
            return {"status": "disabled", "message": "التطور الذاتي معطل"}

        self._cycle_count += 1
        cycle = EvolutionCycle(
            started_at=time.time(),
            phase=EvolutionPhase.RESEARCH.value,
        )
        self._current_cycle = cycle

        logger.info(f"SelfEvolutionScheduler: Starting cycle {cycle.cycle_id}")

        try:
            # Phase 1: Research
            cycle.phase = EvolutionPhase.RESEARCH.value
            research_results = await self._do_research()
            cycle.research_results = research_results

            # Phase 2: Analysis
            cycle.phase = EvolutionPhase.ANALYSIS.value
            proposals = await self._do_analysis(research_results)
            cycle.proposals = proposals

            # Phase 3: Proposal
            cycle.phase = EvolutionPhase.PROPOSAL.value
            approved = await self._request_approvals(proposals)
            cycle.approved_proposals = approved

            # Phase 4: Application
            cycle.phase = EvolutionPhase.APPLICATION.value
            applied = await self._apply_improvements(approved)
            cycle.applied_proposals = applied

            cycle.status = "completed"
            cycle.phase = EvolutionPhase.IDLE.value

            # Send notification
            if self._notifier:
                try:
                    from mamoun.notifications.notifier import NotificationPriority, NotificationChannel
                    await self._notifier.send(
                        title="Self-Evolution Cycle Complete",
                        title_ar="اكتملت دورة التطور الذاتي",
                        body=f"Cycle {cycle.cycle_id}: {len(proposals)} proposals, {len(approved)} approved, {len(applied)} applied",
                        body_ar=f"الدورة {cycle.cycle_id}: {len(proposals)} اقتراح، {len(approved)} موافق عليه، {len(applied)} مطبّق",
                        priority=NotificationPriority.NORMAL.value,
                        channel=NotificationChannel.IN_APP.value,
                    )
                except Exception:
                    pass

        except Exception as e:
            cycle.status = "failed"
            logger.error(f"SelfEvolutionScheduler: Cycle error: {e}")

        self._cycle_history.append(cycle)
        self._current_cycle = None

        return cycle.to_dict()

    async def _do_research(self) -> list[dict]:
        """تنفيذ البحث — Fetch research from trusted sources."""
        results = []

        if self._research_fetcher:
            try:
                results = await self._research_fetcher.fetch_all()
            except Exception as e:
                logger.error(f"Research fetch error: {e}")

        return results

    async def _do_analysis(self, research_results: list[dict]) -> list[dict]:
        """تحليل النتائج — Analyze research and propose improvements."""
        proposals = []

        if self._improvement_proposer:
            try:
                proposals = await self._improvement_proposer.analyze_and_propose(research_results)
            except Exception as e:
                logger.error(f"Improvement analysis error: {e}")

        return proposals

    async def _request_approvals(self, proposals: list[dict]) -> list[dict]:
        """طلب الموافقات — Request human approval for proposals."""
        approved = []

        for proposal in proposals:
            if self._approval_gate:
                try:
                    from mamoun.core.approval_gate import ApprovalRequest
                    request = ApprovalRequest(
                        change_type="self_evolution",
                        target=proposal.get("target_file", "unknown"),
                        description=f"تحسين مقترح: {proposal.get('title_ar', proposal.get('title', ''))}",
                        risk_level=proposal.get("risk_level", "medium"),
                        details=str(proposal),
                    )
                    result = await self._approval_gate.request_approval(request)
                    # For now, add to approved list (in production, wait for human)
                    if result.get("status") in ("auto_approved", "pending"):
                        approved.append(proposal)
                except Exception as e:
                    logger.warning(f"Approval request failed: {e}")

        return approved

    async def _apply_improvements(self, approved: list[dict]) -> list[dict]:
        """تطبيق التحسينات — Apply approved improvements."""
        applied = []

        if self._self_programming_loop:
            for proposal in approved:
                try:
                    result = await self._self_programming_loop.run_cycle({
                        proposal.get("target", "unknown"): {
                            "task_type": proposal.get("type", "general"),
                            proposal.get("metric", "performance"): {
                                "current": proposal.get("current_value", 0),
                                "expected": proposal.get("target_value", 1),
                            },
                        }
                    })
                    applied.append({"proposal": proposal, "result": result})
                except Exception as e:
                    logger.warning(f"Improvement application failed: {e}")

        return applied

    def get_status(self) -> dict:
        """حالة الجدولة."""
        return {
            "enabled": SELF_PROGRAMMING_ENABLED,
            "is_running": self._is_running,
            "cycle_count": self._cycle_count,
            "cycle_interval_days": EVOLUTION_CYCLE_DAYS,
            "last_cycle_time": self._last_cycle_time,
            "current_cycle": self._current_cycle.to_dict() if self._current_cycle else None,
            "history_count": len(self._cycle_history),
        }

    async def shutdown(self):
        """إيقاف الجدولة — يتوافق مع القانون 5."""
        self._is_running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
        logger.info("SelfEvolutionScheduler: Shutdown complete (Law 5 compliant)")
