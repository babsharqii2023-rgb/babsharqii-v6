"""
Hyperagent Loop — Main integration loop for DGM-H Architecture
v16.0

Integrates:
- Task Agent (existing EvolutionLoop from v40.0)
- Meta Agent (Layer 2: improves improvement mechanism)
- Supra-Meta Agent (Layer 3: decides whether/where to improve)
- Evolution Archive (stores all variants for cross-domain transfer)
- Curriculum Controller (graduated improvement phases)
- Future Simulator (long-term impact assessment)

Based on: "Hyperagents" (Zhang et al., 2026) arXiv:2603.19461
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from .meta_agent import MetaAgent, MetaModification
from .supra_meta_agent import SupraMetaAgent, ImprovementDecision
from .evolution_archive import EvolutionArchive, ArchiveEntry, ArchiveEntryStatus
from .curriculum_controller import CurriculumController, CurriculumPhase
from .future_simulator import FutureSimulator

logger = logging.getLogger("mamoun.hyperagent.loop")


class HyperagentLoop:
    """
    The main DGM-H loop that integrates all three layers of awareness.
    
    Flow:
    1. SupraMetaAgent evaluates: Should we improve? Where?
    2. If IMPROVE: EvolutionLoop proposes task-level mutations
    3. MetaAgent reviews: Can we improve HOW we improve?
    4. FutureSimulator: What's the long-term impact?
    5. CurriculumController: Is this phase level allowed?
    6. Archive: Store everything for future cross-domain transfer
    7. Approval Gate: Human approval for high-risk changes
    """
    
    def __init__(self, data_dir: str = "backend/data/hyperagent"):
        self.meta_agent = MetaAgent(data_dir)
        self.supra_meta = SupraMetaAgent(data_dir)
        self.archive = EvolutionArchive(f"{data_dir}/archive")
        self.curriculum = CurriculumController(data_dir)
        self.future_sim = FutureSimulator(data_dir)
        
        self.cycle_count = 0
        self.running = False
    
    async def run_cycle(
        self,
        task_result: Optional[dict] = None,
        current_performance: float = 0.0,
        domain: str = "general",
        resource_usage: Optional[dict] = None,
    ) -> dict:
        """
        Run one complete DGM-H cycle.
        
        Returns a cycle report with all decisions and actions taken.
        """
        self.cycle_count += 1
        start_time = time.time()
        
        report = {
            "cycle": self.cycle_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "domain": domain,
            "current_performance": current_performance,
            "decisions": {},
            "meta_modifications": [],
            "archive_entries": [],
            "status": "completed",
        }
        
        try:
            # ===== Layer 3: Supra-Meta Decision =====
            decision, reasoning, context = self.supra_meta.evaluate_improvement_necessity(
                current_performance=current_performance,
                domain=domain,
                recent_improvements=[],
                resource_usage=resource_usage or {},
            )
            report["decisions"]["supra_meta"] = {
                "decision": decision.value,
                "reasoning": reasoning,
            }
            
            if decision == ImprovementDecision.PAUSE:
                report["status"] = "paused"
                report["decisions"]["action"] = "توقف للتثبيت — لا تحسين في هذه الدورة"
                return report
            
            if decision == ImprovementDecision.ROLLBACK:
                report["status"] = "rollback_needed"
                report["decisions"]["action"] = "تراجع مطلوب — كشف انحراف تدريجي"
                return report
            
            if decision == ImprovementDecision.REDIRECT:
                # Redirect energy to weaker domains
                allocations = self.supra_meta.allocate_improvement_energy(
                    {domain: current_performance}
                )
                report["decisions"]["energy_allocation"] = allocations
                report["decisions"]["action"] = f"إعادة توجيه طاقة التحسين: {allocations}"
            
            # ===== Layer 2: Meta Agent Review =====
            meta_proposal = None
            if task_result:
                meta_proposal = self.meta_agent.observe_cycle_result(task_result)
                if meta_proposal:
                    report["meta_modifications"].append(meta_proposal.to_dict())
                    
                    # Check curriculum phase for meta-modification
                    can_attempt, reason = self.curriculum.can_attempt_phase(
                        CurriculumPhase.META_MODIFICATION,
                        confidence=meta_proposal.confidence,
                        cycles_observed=self.cycle_count,
                    )
                    report["decisions"]["meta_curriculum"] = {
                        "can_attempt": can_attempt,
                        "reason": reason,
                    }
                    
                    if can_attempt:
                        # Simulate long-term impact
                        sim_result = self.future_sim.simulate_modification_impact(
                            modification=meta_proposal.to_dict(),
                            current_state={"performance": current_performance},
                            cycles_to_simulate=50,
                        )
                        report["decisions"]["meta_simulation"] = {
                            "recommendation": sim_result["recommendation"],
                            "risk_score": sim_result["risk_assessment"].get("risk_score"),
                        }
                        
                        if sim_result["recommendation"] in ["proceed", "proceed_with_monitoring"]:
                            self.meta_agent.apply_meta_modification(meta_proposal)
                            self.curriculum.record_improvement(
                                CurriculumPhase.META_MODIFICATION, success=True
                            )
            
            # ===== Archive: Record cycle =====
            if task_result:
                entry = ArchiveEntry(
                    variant_id=f"v{self.cycle_count}_{domain}_{int(time.time())}",
                    parent_id=None,
                    genome_snapshot=task_result.get("genome", {}),
                    mutation_description=task_result.get("mutation_description", ""),
                    domain=domain,
                    mutation_type=task_result.get("mutation_strategy", "unknown"),
                )
                entry.fitness_score = task_result.get("fitness_score", 0.0)
                entry.improvement_pct = task_result.get("improvement_pct", 0.0)
                entry.status = ArchiveEntryStatus.ACCEPTED if task_result.get("accepted") else ArchiveEntryStatus.REJECTED
                
                self.archive.add_entry(entry)
                report["archive_entries"].append(entry.variant_id)
            
            # ===== Energy Allocation =====
            if decision == ImprovementDecision.IMPROVE:
                allocations = self.supra_meta.allocate_improvement_energy(
                    {domain: current_performance}
                )
                report["decisions"]["energy_allocation"] = allocations
        
        except Exception as e:
            logger.error("HyperagentLoop cycle error: %s", e, exc_info=True)
            report["status"] = "error"
            report["error"] = str(e)
        
        report["duration_ms"] = round((time.time() - start_time) * 1000, 2)
        return report
    
    def get_full_status(self) -> dict:
        """Get comprehensive status of all layers."""
        return {
            "cycle_count": self.cycle_count,
            "meta_agent": self.meta_agent.get_status(),
            "supra_meta": self.supra_meta.get_status(),
            "archive": self.archive.get_statistics(),
            "curriculum": self.curriculum.get_status(),
            "running": self.running,
        }
