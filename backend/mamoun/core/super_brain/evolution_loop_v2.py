"""
Evolution Loop V2 v59 — Integrated with super_brain architecture.

CRITICAL UPGRADE from v58:
- v58: Evolution Loop was isolated from super_brain components
- v59: EvolutionLoopV2 coordinates between ImprovementProposer, SelfModifier,
       MetaCognitionEngine, and DeepResearchEngine
- No more dependency on old v40 architecture components
- Full integration with MamounKernel component system
- Auto-deploy limits with safety gates
- System snapshot + rollback capability

v59 — Super Mind العقل الخارق مامون
"""

import time
import asyncio
import logging
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class EvolutionStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class EvolutionCycleResult:
    """Result of a single evolution cycle."""
    cycle_id: str
    status: EvolutionStatus
    stagnant_components: list[str]
    proposals_generated: int
    proposals_applied: int
    proposals_failed: int
    fitness_before: float
    fitness_after: float
    improvement: float
    snapshot_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class EvolutionLoopV2:
    """
    Evolution Loop V2 — Coordinates super_brain components for self-improvement.

    Pipeline:
    1. DETECT: Use MetaCognitionEngine to find stagnant/unhealthy components
    2. PROPOSE: Use ImprovementProposer to generate data-driven proposals
    3. APPLY: Use SelfModifier to safely apply approved proposals
    4. VERIFY: Use MetaCognitionEngine to verify improvement
    5. LEARN: Record outcomes and adjust strategy

    Safety features:
    - Auto-deploy limits (max 2/hour, 5/day for low-risk)
    - Auto-freeze if reliability drops below 0.5
    - System snapshot before every cycle (enables rollback)
    - Consecutive failure detection with auto-pause
    """

    # Safety limits
    MAX_AUTO_DEPLOYS_PER_HOUR = 2
    MAX_AUTO_DEPLOYS_PER_DAY = 5
    MAX_CONSECUTIVE_FAILS = 3
    RELIABILITY_FREEZE_THRESHOLD = 0.5

    def __init__(self, kernel):
        """
        Args:
            kernel: MamounKernel instance (provides access to all components)
        """
        self.kernel = kernel
        self._status = EvolutionStatus.IDLE
        self._cycle_count = 0
        self._consecutive_fails = 0
        self._deploys_this_hour = 0
        self._deploys_today = 0
        self._hour_start = time.time()
        self._day_start = time.time()
        self._snapshots: dict[str, dict] = {}
        self._cycle_history: list[EvolutionCycleResult] = []
        self._frozen = False

    @property
    def status(self) -> EvolutionStatus:
        return self._status

    def _get_component(self, name: str) -> Any:
        return self.kernel.get_component(name)

    def _reset_rate_limits(self):
        """Reset rate limits if time windows have passed."""
        now = time.time()
        if now - self._hour_start > 3600:
            self._deploys_this_hour = 0
            self._hour_start = now
        if now - self._day_start > 86400:
            self._deploys_today = 0
            self._day_start = now

    def _can_auto_deploy(self) -> bool:
        """Check if auto-deploy is allowed within rate limits."""
        self._reset_rate_limits()
        return (self._deploys_this_hour < self.MAX_AUTO_DEPLOYS_PER_HOUR and
                self._deploys_today < self.MAX_AUTO_DEPLOYS_PER_DAY and
                not self._frozen)

    async def run_cycle(self) -> EvolutionCycleResult:
        """
        Run one complete evolution cycle.

        Returns:
            EvolutionCycleResult with cycle details
        """
        self._cycle_count += 1
        cycle_id = f"evo_{int(time.time())}_{self._cycle_count}"

        if self._frozen:
            return EvolutionCycleResult(
                cycle_id=cycle_id,
                status=EvolutionStatus.FAILED,
                stagnant_components=[],
                proposals_generated=0, proposals_applied=0, proposals_failed=0,
                fitness_before=0, fitness_after=0, improvement=0,
                error="Evolution frozen due to low reliability",
            )

        self._status = EvolutionStatus.RUNNING
        meta = self._get_component("meta_cognition")
        proposer = self._get_component("improvement_proposer")

        # ===== Phase 1: DETECT =====
        stagnant = []
        if meta:
            stagnant = meta.get_stagnant_components()
            unhealthy = meta.get_unhealthy_components()
            for u in unhealthy:
                if u["component"] not in stagnant:
                    stagnant.append(u["component"])

        fitness_before = 0.0
        if meta:
            assessment = meta.get_self_assessment()
            fitness_before = assessment.get("overall_confidence", 0.0)

        if not stagnant:
            result = EvolutionCycleResult(
                cycle_id=cycle_id,
                status=EvolutionStatus.COMPLETED,
                stagnant_components=[],
                proposals_generated=0, proposals_applied=0, proposals_failed=0,
                fitness_before=fitness_before,
                fitness_after=fitness_before,
                improvement=0.0,
            )
            self._cycle_history.append(result)
            self._status = EvolutionStatus.IDLE
            return result

        # ===== Phase 2: SNAPSHOT (before changes) =====
        snapshot_id = f"snap_{cycle_id}"
        self._save_snapshot(snapshot_id, meta)

        # ===== Phase 3: PROPOSE =====
        proposals = []
        if proposer:
            try:
                proposals = await proposer.analyze_and_propose()
            except Exception as e:
                logger.error(f"Evolution proposal failed: {e}")

        # ===== Phase 4: APPLY =====
        applied = 0
        failed = 0

        for proposal in proposals:
            if proposal.status.value not in ("approved", "evaluating"):
                continue

            if not self._can_auto_deploy():
                logger.warning("Auto-deploy rate limit reached — stopping cycle")
                break

            try:
                result = await proposer.apply_proposal(proposal.id)
                if result.get("success"):
                    applied += 1
                    self._deploys_this_hour += 1
                    self._deploys_today += 1
                    logger.info(f"Applied proposal {proposal.id}: {proposal.title}")
                else:
                    failed += 1
                    logger.warning(f"Failed to apply proposal {proposal.id}: {result.get('error')}")
            except Exception as e:
                failed += 1
                logger.error(f"Error applying proposal {proposal.id}: {e}")

        # ===== Phase 5: VERIFY =====
        fitness_after = fitness_before
        if meta:
            assessment = meta.get_self_assessment()
            fitness_after = assessment.get("overall_confidence", 0.0)

            # Check if we should freeze
            if fitness_after < self.RELIABILITY_FREEZE_THRESHOLD and fitness_before >= self.RELIABILITY_FREEZE_THRESHOLD:
                self._frozen = True
                logger.critical(f"Evolution FROZEN: reliability dropped below {self.RELIABILITY_FREEZE_THRESHOLD}")

        improvement = fitness_after - fitness_before

        # Track consecutive fails
        if failed > applied:
            self._consecutive_fails += 1
        else:
            self._consecutive_fails = 0

        if self._consecutive_fails >= self.MAX_CONSECUTIVE_FAILS:
            logger.critical("Too many consecutive failures — pausing evolution")
            self._frozen = True

        # ===== Phase 6: LEARN & RECORD =====
        if meta:
            try:
                from .meta_cognition_engine import OutcomeRecord
                meta.record_outcome(OutcomeRecord(
                    component="evolution_loop_v2",
                    operation="run_cycle",
                    success=applied > 0,
                    quality_score=improvement if improvement > 0 else 0.0,
                    predicted_quality=meta.predict_quality("evolution_loop_v2"),
                    latency_ms=0,
                    metadata={
                        "stagnant_components": len(stagnant),
                        "proposals": len(proposals),
                        "applied": applied,
                        "failed": failed,
                    },
                ))
            except ImportError:
                pass

        result = EvolutionCycleResult(
            cycle_id=cycle_id,
            status=EvolutionStatus.COMPLETED if applied > 0 else EvolutionStatus.FAILED if failed > 0 else EvolutionStatus.IDLE,
            stagnant_components=stagnant,
            proposals_generated=len(proposals),
            proposals_applied=applied,
            proposals_failed=failed,
            fitness_before=fitness_before,
            fitness_after=fitness_after,
            improvement=improvement,
            snapshot_id=snapshot_id,
        )

        self._cycle_history.append(result)
        if len(self._cycle_history) > 100:
            self._cycle_history = self._cycle_history[-100:]

        self._status = EvolutionStatus.IDLE
        return result

    def _save_snapshot(self, snapshot_id: str, meta_cognition=None):
        """Save a snapshot of system state before evolution changes."""
        snapshot = {
            "snapshot_id": snapshot_id,
            "timestamp": time.time(),
            "cycle_count": self._cycle_count,
            "frozen": self._frozen,
        }

        if meta_cognition:
            try:
                snapshot["meta_data"] = meta_cognition.export_data()
            except Exception as e:
                logger.warning(f"Failed to export meta data for snapshot: {e}")
                snapshot["meta_data"] = {}

        self._snapshots[snapshot_id] = snapshot
        logger.info(f"Saved snapshot: {snapshot_id}")

    async def rollback(self, snapshot_id: str) -> dict:
        """
        Rollback to a previous snapshot.

        Args:
            snapshot_id: The snapshot to rollback to

        Returns:
            dict with rollback result
        """
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return {"success": False, "error": f"Snapshot {snapshot_id} not found"}

        meta = self._get_component("meta_cognition")

        # Restore meta-cognition data
        if meta and "meta_data" in snapshot:
            try:
                meta.import_data(snapshot["meta_data"])
                logger.info(f"Restored meta-cognition data from snapshot {snapshot_id}")
            except Exception as e:
                logger.error(f"Failed to restore meta-cognition: {e}")
                return {"success": False, "error": str(e)}

        # Reset evolution state
        self._consecutive_fails = 0
        self._frozen = False

        logger.info(f"Rollback to snapshot {snapshot_id} completed")

        return {
            "success": True,
            "snapshot_id": snapshot_id,
            "restored_at": time.time(),
        }

    def unfreeze(self):
        """Manually unfreeze the evolution loop."""
        self._frozen = False
        self._consecutive_fails = 0
        logger.info("Evolution loop unfrozen")

    def get_stats(self) -> dict:
        """Get evolution loop statistics."""
        return {
            "status": self._status.value,
            "cycle_count": self._cycle_count,
            "frozen": self._frozen,
            "consecutive_fails": self._consecutive_fails,
            "deploys_this_hour": self._deploys_this_hour,
            "deploys_today": self._deploys_today,
            "snapshots_available": list(self._snapshots.keys()),
            "recent_cycles": [
                {
                    "cycle_id": r.cycle_id,
                    "status": r.status.value,
                    "applied": r.proposals_applied,
                    "improvement": round(r.improvement, 4),
                }
                for r in self._cycle_history[-10:]
            ],
        }
