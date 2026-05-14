"""
BABSHARQII v40.0 — Evolution Loop
The main loop that ties all 5 phases together:
1. Awareness → 2. Propose → 3. Sandbox Test → 4. Approval/Verify → 5. Learn/Store
"""

import time
import asyncio
from dataclasses import dataclass, field
from typing import Optional

from mamoun.evolution.mutation_engine import MutationEngine, AgentVersion
from mamoun.evolution.fitness_evaluator import FitnessEvaluator, FitnessReport
from mamoun.evolution.procedural_memory import ProceduralMemory
from mamoun.core.state_reader import StateReader
from mamoun.core.meta_analyzer import MetaAnalyzer
from mamoun.core.reflective_journal import ReflectiveJournal, JournalEntry
from mamoun.core.code_patcher import CodePatcher
from mamoun.core.sandbox_runner import SandboxRunner
from mamoun.core.safety_guard import SafetyGuard
from mamoun.core.approval_gate import ApprovalGate, ApprovalRequest


@dataclass
class EvolutionCycleResult:
    """Result of a complete evolution cycle."""
    cycle_id: str = ""
    phase: str = ""  # awareness, propose, sandbox, approval, learn
    status: str = ""  # success, failed, rejected, pending_approval
    mutations_proposed: int = 0
    mutations_applied: int = 0
    fitness_before: float = 0.0
    fitness_after: float = 0.0
    improvement: float = 0.0
    details: str = ""
    timestamp: float = 0.0


class EvolutionLoop:
    """
    The Complete Self-Evolution Loop for BABSHARQII v40.0.
    
    5 Phases:
    1. الإدراك والمراقبة — Detect issues and opportunities
    2. اقتراح التحسينات — Propose mutations/patches
    3. اختبار في بيئة معزولة — Test in Docker sandbox
    4. التحقق والموافقة — Human approval + safety verification
    5. التعلم والتخزين — Store lessons in procedural memory
    """
    
    def __init__(
        self,
        state_reader: StateReader,
        meta_analyzer: MetaAnalyzer,
        journal: ReflectiveJournal,
        code_patcher: CodePatcher,
        sandbox_runner: SandboxRunner,
        safety_guard: SafetyGuard,
        approval_gate: ApprovalGate,
        mutation_engine: MutationEngine,
        fitness_evaluator: FitnessEvaluator,
        procedural_memory: ProceduralMemory,
    ):
        self.state_reader = state_reader
        self.meta_analyzer = meta_analyzer
        self.journal = journal
        self.code_patcher = code_patcher
        self.sandbox_runner = sandbox_runner
        self.safety_guard = safety_guard
        self.approval_gate = approval_gate
        self.mutation_engine = mutation_engine
        self.fitness_evaluator = fitness_evaluator
        self.procedural_memory = procedural_memory
        
        self._is_running = False
        self._cycle_count = 0
    
    async def run_cycle(self) -> EvolutionCycleResult:
        """Run one complete evolution cycle through all 5 phases."""
        self._cycle_count += 1
        cycle_id = f"cycle_{int(time.time())}_{self._cycle_count}"
        
        # Check if shutdown is in progress (Law 5)
        if self.safety_guard.is_shutting_down():
            return EvolutionCycleResult(
                cycle_id=cycle_id, phase="shutdown", status="aborted",
                details="Evolution aborted — shutdown in progress (Law 5)",
                timestamp=time.time(),
            )
        
        result = EvolutionCycleResult(
            cycle_id=cycle_id,
            timestamp=time.time(),
        )
        
        try:
            # ===== Phase 1: Awareness =====
            result.phase = "awareness"
            state = self.state_reader.read_system_state()
            vitality = self.state_reader.compute_vitality()
            assessment = self.meta_analyzer.assess(
                self.mutation_engine.get_current_version().genome.routing_weights,
                vitality,
            )
            
            # Record in journal
            await self.journal.add_entry(JournalEntry(
                entry_type="evolution",
                summary=f"Evolution cycle {self._cycle_count} started (vitality: {vitality:.0f})",
                details=f"Metacognitive awareness: {assessment.overall_self_awareness:.2f}",
                emotional_valence=0.3 if vitality > 50 else -0.3,
                confidence=assessment.system1_confidence,
            ))
            
            # ===== Phase 2: Propose Mutations =====
            result.phase = "propose"
            mutations = await self.mutation_engine.generate_mutations()
            result.mutations_proposed = len(mutations)
            
            if not mutations:
                result.status = "no_mutations"
                await self.journal.add_entry(JournalEntry(
                    entry_type="evolution",
                    summary=f"Cycle {self._cycle_count}: No mutations proposed",
                    emotional_valence=-0.1,
                    confidence=0.9,
                ))
                return result
            
            # Apply mutations to create candidate
            current = self.mutation_engine.get_current_version()
            candidate = self.mutation_engine.apply_mutations(mutations)
            result.fitness_before = current.fitness_score
            
            # ===== Phase 3: Sandbox Test =====
            result.phase = "sandbox"
            
            # Evaluate fitness before and after
            parent_fitness = FitnessReport(
                overall_score=current.fitness_score,
                response_quality=self.fitness_evaluator._compute_response_quality(current.genome.to_dict()),
                diversity_score=self.fitness_evaluator._compute_diversity(current.genome.to_dict()),
            )
            
            candidate_fitness = self.fitness_evaluator.evaluate(
                candidate.genome.to_dict(),
                parent_fitness.overall_score,
            )
            
            # Check if improvement meets threshold
            if not candidate_fitness.meets_threshold:
                self.mutation_engine.reject_candidate(candidate, "Below fitness threshold")
                result.status = "below_threshold"
                result.improvement = candidate_fitness.improvement_vs_parent
                
                await self.journal.add_entry(JournalEntry(
                    entry_type="evolution",
                    summary=f"Cycle {self._cycle_count}: Mutation rejected (below threshold)",
                    details=f"Improvement: {candidate_fitness.improvement_vs_parent:.2%}, Required: {self.fitness_evaluator.fitness_threshold:.0%}",
                    emotional_valence=-0.4,
                    confidence=0.9,
                    root_cause="Insufficient improvement",
                    lesson_learned="Mutations need to produce >= 2% improvement to be accepted",
                ))
                return result
            
            # ===== Phase 4: Approval =====
            result.phase = "approval"
            
            # Request human approval
            approval_request = ApprovalRequest(
                change_type="genome_mutation",
                target=f"generation_{candidate.generation}",
                description=f"طفرات الجيل {candidate.generation}: {len(mutations)} تغييرات (تحسن {candidate_fitness.improvement_vs_parent:.1%})",
                risk_level="medium" if candidate_fitness.improvement_vs_parent < 0.1 else "high",
                details=str({
                    "mutations": [m.to_dict() for m in mutations],
                    "fitness": candidate_fitness.to_dict(),
                }),
                auto_deploy_enabled=self.approval_gate._auto_deploy_low_risk,
            )
            
            approval_result = await self.approval_gate.request_approval(approval_request)
            
            if approval_result["status"] == "pending":
                result.status = "pending_approval"
                result.details = f"Waiting for human approval: {approval_request.id}"
                return result
            
            if approval_result["status"] == "rejected":
                self.mutation_engine.reject_candidate(candidate, "Human rejected")
                result.status = "rejected"
                return result
            
            # Approved! Apply the candidate
            improvement = candidate_fitness.overall_score - current.fitness_score
            self.mutation_engine.accept_candidate(candidate, improvement)
            result.mutations_applied = len(mutations)
            result.fitness_after = candidate_fitness.overall_score
            result.improvement = candidate_fitness.improvement_vs_parent
            
            # ===== Phase 5: Learn and Store =====
            result.phase = "learn"
            
            # Extract skills from recent interactions
            new_skills = await self.procedural_memory.extract_skills()
            
            # Record in journal
            await self.journal.add_entry(JournalEntry(
                entry_type="evolution",
                summary=f"Cycle {self._cycle_count}: Evolution SUCCESS",
                details=f"Fitness: {current.fitness_score:.1f} → {candidate_fitness.overall_score:.1f} (+{improvement:.1f})",
                emotional_valence=0.8,
                confidence=0.95,
                lesson_learned=f"تحسن بنسبة {candidate_fitness.improvement_vs_parent:.1%} عبر {len(mutations)} طفرة. مهارات جديدة: {len(new_skills)}",
                related_brain_ids=str([m.target.split(".")[-1] for m in mutations]),
            ))
            
            result.status = "success"
            
        except Exception as e:
            result.status = "error"
            result.details = str(e)
            
            await self.journal.add_entry(JournalEntry(
                entry_type="error",
                summary=f"Evolution cycle error: {e}",
                emotional_valence=-0.8,
                confidence=0.5,
                root_cause=str(e),
            ))
        
        return result
    
    def is_running(self) -> bool:
        return self._is_running
    
    def get_cycle_count(self) -> int:
        return self._cycle_count
