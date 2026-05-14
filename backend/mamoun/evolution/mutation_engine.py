"""
BABSHARQII v40.0 — Darwin-Gödel Mutation Engine
Proposes, evaluates, and applies genome mutations for self-evolution.
Based on the 2025 Sakana AI DGM paper + DGM-Hyperagents concept.
"""

import time
import json
import math
import random
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

import httpx


@dataclass
class Mutation:
    """A proposed mutation to the organism's genome."""
    id: str = ""
    type: str = ""  # prompt_mutation, weight_mutation, threshold_mutation, skill_acquisition, pattern_evolution
    target: str = ""
    before: any = None
    after: any = None
    reasoning: str = ""
    impact: float = 0.0
    timestamp: float = 0.0
    generation: int = 0
    status: str = "proposed"  # proposed, approved, applied, rejected, rolled_back
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "target": self.target,
            "before": str(self.before)[:200] if self.before else None,
            "after": str(self.after)[:200] if self.after else None,
            "reasoning": self.reasoning,
            "impact": self.impact,
            "generation": self.generation,
            "status": self.status,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat() if self.timestamp else None,
        }


@dataclass
class AgentGenome:
    """The complete genome of the organism — its configuration DNA."""
    system_prompts: dict = field(default_factory=dict)
    routing_weights: dict = field(default_factory=dict)
    instinct_thresholds: dict = field(default_factory=dict)
    temperature_per_brain: dict = field(default_factory=dict)
    model_preferences: dict = field(default_factory=dict)
    response_patterns: list = field(default_factory=list)
    skill_definitions: list = field(default_factory=list)
    cache_settings: dict = field(default_factory=dict)
    active_agents: list = field(default_factory=list)
    deliberation_strategy: str = "weighted_vote"
    
    def to_dict(self) -> dict:
        return {
            "system_prompts": self.system_prompts,
            "routing_weights": self.routing_weights,
            "instinct_thresholds": self.instinct_thresholds,
            "temperature_per_brain": self.temperature_per_brain,
            "model_preferences": self.model_preferences,
            "response_patterns": self.response_patterns,
            "skill_definitions": self.skill_definitions,
            "cache_settings": self.cache_settings,
            "active_agents": self.active_agents,
            "deliberation_strategy": self.deliberation_strategy,
        }
    
    def clone(self) -> "AgentGenome":
        """Deep clone the genome."""
        return AgentGenome(**json.loads(json.dumps(self.to_dict())))


@dataclass
class AgentVersion:
    """A versioned snapshot of the organism with its genome and fitness."""
    id: str = ""
    parent_id: Optional[str] = None
    generation: int = 0
    timestamp: float = 0.0
    genome: AgentGenome = field(default_factory=AgentGenome)
    fitness_score: float = 0.0
    mutations: list = field(default_factory=list)
    status: str = "active"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "generation": self.generation,
            "timestamp": self.timestamp,
            "fitness_score": self.fitness_score,
            "mutation_count": len(self.mutations),
            "mutations": [m.to_dict() for m in self.mutations],
            "status": self.status,
        }


class MutationEngine:
    """
    Darwin-Gödel Mutation Engine for open-ended self-improvement.
    
    Implements:
    - 5 mutation types (prompt, weight, threshold, skill, pattern)
    - LLM-driven intelligent mutations (not random)
    - Entropy-based exploration (increases when stagnating)
    - DGM-Hyperagents: meta-improvement (improving how we improve)
    - Diversity enforcement
    """
    
    DEFAULT_BRAIN_IDS = ["neural", "causal", "symbolic", "bayesian", "world_model"]
    
    def __init__(
        self,
        llm_api_url: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        llm_model: str = "glm-4-plus",
        mutation_rate: float = 0.3,
        exploration_rate: float = 0.2,
        fitness_threshold: float = 0.02,
        stagnation_threshold: int = 3,
        max_archive_size: int = 50,
    ):
        self.llm_api_url = llm_api_url
        self.llm_model = llm_model
        self.mutation_rate = mutation_rate
        self.exploration_rate = exploration_rate
        self.fitness_threshold = fitness_threshold
        self.stagnation_threshold = stagnation_threshold
        self.max_archive_size = max_archive_size
        
        self._archive: list[AgentVersion] = []
        self._current_version: Optional[AgentVersion] = None
        self._pending_mutations: list[Mutation] = []
        self._stagnation_count = 0
        self._last_improvement = 0.0
        self._mutation_counter = 0
        self._version_counter = 0
        
        # Initialize Genesis version
        self._initialize_genesis()
    
    def _initialize_genesis(self):
        """Create the Genesis version (generation 0)."""
        self._version_counter += 1
        genome = AgentGenome(
            system_prompts={
                "neural": "You are the Neural brain — deep language processing. Analyze inputs with precision, provide logical and contextual responses in Arabic.",
                "causal": "You are the Causal brain — causal reasoning engine. Identify cause-effect relationships, evaluate interventions.",
                "symbolic": "You are the Symbolic brain — mathematical and logical reasoning. Handle formal logic, computations, symbolic manipulation.",
                "bayesian": "You are the Bayesian brain — probabilistic inference. Update beliefs based on evidence, quantify uncertainty.",
                "world_model": "You are the World Model brain — world simulation. Build internal models, predict outcomes, simulate scenarios.",
            },
            routing_weights={
                "neural": 0.25, "causal": 0.22, "symbolic": 0.18,
                "bayesian": 0.17, "world_model": 0.18,
            },
            instinct_thresholds={
                "survival": {"trigger_at": 70, "max_level": 100},
                "curiosity": {"trigger_at": 30, "max_level": 90},
                "consistency": {"trigger_at": 50, "max_level": 85},
                "efficiency": {"trigger_at": 40, "max_level": 80},
            },
            temperature_per_brain={
                "neural": 0.7, "causal": 0.3, "symbolic": 0.1,
                "bayesian": 0.4, "world_model": 0.6,
            },
            model_preferences={
                "neural": "glm-5.1", "causal": "deepseek-reasoner",
                "symbolic": "glm-4-plus", "bayesian": "gemini-2.0-flash",
                "world_model": "deepseek-chat",
            },
            cache_settings={"enabled": True, "ttl_seconds": 300, "max_size_mb": 50},
            active_agents=["neural", "causal", "bayesian"],
            deliberation_strategy="weighted_vote",
        )
        
        self._current_version = AgentVersion(
            id=f"ver_{self._version_counter}_genesis",
            parent_id=None,
            generation=0,
            timestamp=time.time(),
            genome=genome,
            fitness_score=50.0,
            mutations=[],
            status="active",
        )
        self._archive.append(self._current_version)
    
    # =========================================================================
    # Mutation Generation
    # =========================================================================
    
    async def generate_mutations(self) -> list[Mutation]:
        """Generate a set of proposed mutations based on current genome state."""
        mutations = []
        generation = self._current_version.generation + 1
        
        # Check if we should mutate
        if random.random() > self.mutation_rate:
            return mutations
        
        # Calculate effective exploration rate (increases during stagnation)
        effective_exploration = self.exploration_rate
        if self._stagnation_count >= self.stagnation_threshold:
            effective_exploration = min(0.8, self.exploration_rate * (1 + self._stagnation_count * 0.2))
        
        # Mutation Type 1: System Prompt Mutation (LLM-driven)
        if random.random() < 0.5:
            brain_id = self._select_brain_for_mutation(effective_exploration)
            mutation = await self._mutate_system_prompt(brain_id, generation)
            if mutation:
                mutations.append(mutation)
        
        # Mutation Type 2: Routing Weight Mutation
        if random.random() < 0.4:
            mutation = self._mutate_routing_weights(generation, effective_exploration)
            if mutation:
                mutations.append(mutation)
        
        # Mutation Type 3: Instinct Threshold Mutation
        if random.random() < 0.25:
            mutation = self._mutate_instinct_thresholds(generation)
            if mutation:
                mutations.append(mutation)
        
        # Mutation Type 4: Skill Acquisition (exploration-dependent)
        if random.random() < effective_exploration:
            mutation = self._acquire_new_skill(generation)
            if mutation:
                mutations.append(mutation)
        
        # Mutation Type 5: Pattern Evolution
        if random.random() < 0.35:
            mutation = self._evolve_response_pattern(generation)
            if mutation:
                mutations.append(mutation)
        
        # DGM-Hyperagents: Meta-mutation (improving the improvement process)
        if random.random() < effective_exploration * 0.3:
            mutation = self._meta_mutation(generation)
            if mutation:
                mutations.append(mutation)
        
        return mutations
    
    def _select_brain_for_mutation(self, exploration_rate: float) -> str:
        """Select a brain for mutation — prefer weakest, with exploration."""
        weights = self._current_version.genome.routing_weights
        
        # Usually select the weakest brain
        if random.random() > exploration_rate:
            return min(weights, key=weights.get)
        
        # Sometimes pick randomly for exploration
        return random.choice(list(weights.keys()))
    
    async def _mutate_system_prompt(self, brain_id: str, generation: int) -> Optional[Mutation]:
        """Use LLM to generate an improved system prompt."""
        current_prompt = self._current_version.genome.system_prompts.get(brain_id, "")
        if not current_prompt:
            return None
        
        try:
            prompt = f"""You are the self-improvement module of BABSHARQII v40.0 (Mamoun). 
Improve the system prompt for the "{brain_id}" brain.

Current prompt:
\"\"\"{current_prompt}\"\"\"

Current fitness: {self._current_version.fitness_score:.1f}/100
Stagnation count: {self._stagnation_count}

Improve this prompt to:
1. Be more specific and actionable
2. Address weaknesses
3. Maintain the brain's core identity
4. Be written in English for internal use

Return ONLY the improved prompt text, nothing else."""

            response = await self._call_llm(prompt)
            new_prompt = response.strip() if response else ""
            
            if not new_prompt or new_prompt == current_prompt:
                return None
            
            self._mutation_counter += 1
            return Mutation(
                id=f"mut_{int(time.time())}_{self._mutation_counter}",
                type="prompt_mutation",
                target=f"system_prompts.{brain_id}",
                before=current_prompt,
                after=new_prompt,
                reasoning=f"LLM-reflected improvement for {brain_id} brain (fitness: {self._current_version.fitness_score:.1f})",
                timestamp=time.time(),
                generation=generation,
            )
        except Exception:
            return None
    
    def _mutate_routing_weights(self, generation: int, exploration: float) -> Optional[Mutation]:
        """Rebalance routing weights — transfer weight from strongest to weakest."""
        weights = self._current_version.genome.routing_weights
        if len(weights) < 2:
            return None
        
        max_brain = max(weights, key=weights.get)
        min_brain = min(weights, key=weights.get)
        
        # Transfer amount increases with exploration
        base_transfer = 0.02 + random.random() * 0.03
        transfer = base_transfer * (1 + exploration)
        
        new_weights = dict(weights)
        new_weights[max_brain] = max(0.05, new_weights[max_brain] - transfer)
        new_weights[min_brain] = min(0.50, new_weights[min_brain] + transfer)
        
        # Normalize
        total = sum(new_weights.values())
        new_weights = {k: v / total for k, v in new_weights.items()}
        
        self._mutation_counter += 1
        return Mutation(
            id=f"mut_{int(time.time())}_{self._mutation_counter}",
            type="weight_mutation",
            target="routing_weights",
            before=dict(weights),
            after=new_weights,
            reasoning=f"Rebalanced: reduced {max_brain} ({weights[max_brain]:.3f}), increased {min_brain} ({weights[min_brain]:.3f})",
            timestamp=time.time(),
            generation=generation,
        )
    
    def _mutate_instinct_thresholds(self, generation: int) -> Optional[Mutation]:
        """Adjust instinct trigger thresholds."""
        thresholds = self._current_version.genome.instinct_thresholds
        if not thresholds:
            return None
        
        instinct_id = random.choice(list(thresholds.keys()))
        current = dict(thresholds[instinct_id])
        
        adjustment = (random.random() - 0.5) * 10
        current["trigger_at"] = max(10, min(90, current.get("trigger_at", 50) + adjustment))
        
        self._mutation_counter += 1
        return Mutation(
            id=f"mut_{int(time.time())}_{self._mutation_counter}",
            type="threshold_mutation",
            target=f"instinct_thresholds.{instinct_id}",
            before=dict(thresholds[instinct_id]),
            after=current,
            reasoning=f"Adjusted {instinct_id} trigger_at by {adjustment:+.1f}",
            timestamp=time.time(),
            generation=generation,
        )
    
    def _acquire_new_skill(self, generation: int) -> Optional[Mutation]:
        """Propose a new skill for the organism to learn."""
        existing_ids = {s.get("id", "") for s in self._current_version.genome.skill_definitions}
        
        potential_skills = [
            {"id": "multilingual_translation", "name_ar": "الترجمة متعددة اللغات", "dependencies": ["arabic_nlu"]},
            {"id": "sentiment_analysis", "name_ar": "تحليل المشاعر", "dependencies": ["arabic_nlu"]},
            {"id": "analogical_reasoning", "name_ar": "الاستدلال التمثيلي", "dependencies": ["logical_reasoning"]},
            {"id": "temporal_reasoning", "name_ar": "الاستدلال الزمني", "dependencies": ["logical_reasoning", "causal_analysis"]},
            {"id": "ethical_reasoning", "name_ar": "الاستدلال الأخلاقي", "dependencies": ["knowledge_synthesis"]},
            {"id": "code_debugging", "name_ar": "تصحيح الأكواد", "dependencies": ["code_generation", "logical_reasoning"]},
            {"id": "data_visualization", "name_ar": "تصور البيانات", "dependencies": ["math_computation"]},
        ]
        
        for skill in potential_skills:
            if skill["id"] not in existing_ids:
                deps_met = all(d in existing_ids for d in skill["dependencies"])
                if deps_met:
                    self._mutation_counter += 1
                    new_skill = {
                        "id": skill["id"],
                        "name_ar": skill["name_ar"],
                        "level": 1,
                        "experience": 0,
                        "success_rate": 0.5,
                    }
                    return Mutation(
                        id=f"mut_{int(time.time())}_{self._mutation_counter}",
                        type="skill_acquisition",
                        target=f"skill_definitions.{skill['id']}",
                        before=None,
                        after=new_skill,
                        reasoning=f"Acquired new skill: {skill['name_ar']} (dependencies met)",
                        timestamp=time.time(),
                        generation=generation,
                    )
        
        return None
    
    def _evolve_response_pattern(self, generation: int) -> Optional[Mutation]:
        """Evolve a response pattern by improving its trigger or strategy."""
        patterns = self._current_version.genome.response_patterns
        if not patterns:
            return None
        
        # Pick the worst-performing pattern
        worst = min(patterns, key=lambda p: p.get("success_rate", 1.0))
        if worst.get("success_rate", 1.0) > 0.95:
            return None  # All patterns are good enough
        
        # Widen the trigger slightly (heuristic)
        improved = dict(worst)
        trigger = improved.get("trigger", "")
        if trigger.startswith("^"):
            improved["trigger"] = trigger[1:]  # Remove anchor
        
        self._mutation_counter += 1
        return Mutation(
            id=f"mut_{int(time.time())}_{self._mutation_counter}",
            type="pattern_evolution",
            target=f"response_patterns.{worst.get('id', 'unknown')}",
            before=worst,
            after=improved,
            reasoning=f"Evolved pattern {worst.get('id', 'unknown')}: widened trigger",
            timestamp=time.time(),
            generation=generation,
        )
    
    def _meta_mutation(self, generation: int) -> Optional[Mutation]:
        """
        DGM-Hyperagents: Meta-mutation — improving the improvement process itself.
        Adjusts mutation_rate, exploration_rate, or deliberation_strategy.
        """
        # Adjust mutation rate
        new_rate = self.mutation_rate + (random.random() - 0.5) * 0.1
        new_rate = max(0.1, min(0.5, new_rate))
        
        self._mutation_counter += 1
        return Mutation(
            id=f"mut_{int(time.time())}_{self._mutation_counter}",
            type="threshold_mutation",  # Reusing type
            target="meta.mutation_rate",
            before=self.mutation_rate,
            after=new_rate,
            reasoning=f"Meta-mutation: adjusted mutation_rate from {self.mutation_rate:.2f} to {new_rate:.2f}",
            timestamp=time.time(),
            generation=generation,
        )
    
    # =========================================================================
    # Apply Mutations
    # =========================================================================
    
    def apply_mutations(self, mutations: list[Mutation]) -> AgentVersion:
        """Apply a list of mutations to create a candidate version."""
        new_genome = self._current_version.genome.clone()
        
        for mutation in mutations:
            self._apply_mutation_to_genome(new_genome, mutation)
        
        self._version_counter += 1
        candidate = AgentVersion(
            id=f"ver_{self._version_counter}_{int(time.time())}",
            parent_id=self._current_version.id,
            generation=self._current_version.generation + 1,
            timestamp=time.time(),
            genome=new_genome,
            fitness_score=0.0,  # Will be evaluated
            mutations=mutations,
            status="candidate",
        )
        
        return candidate
    
    def _apply_mutation_to_genome(self, genome: AgentGenome, mutation: Mutation):
        """Apply a single mutation to a genome."""
        if mutation.type == "prompt_mutation":
            brain_id = mutation.target.replace("system_prompts.", "")
            genome.system_prompts[brain_id] = mutation.after
        
        elif mutation.type == "weight_mutation":
            genome.routing_weights = mutation.after
        
        elif mutation.type == "threshold_mutation":
            if mutation.target.startswith("instinct_thresholds."):
                instinct_id = mutation.target.replace("instinct_thresholds.", "")
                genome.instinct_thresholds[instinct_id] = mutation.after
            elif mutation.target == "meta.mutation_rate":
                self.mutation_rate = mutation.after
        
        elif mutation.type == "skill_acquisition":
            if isinstance(mutation.after, dict):
                existing_ids = {s.get("id") for s in genome.skill_definitions}
                if mutation.after.get("id") not in existing_ids:
                    genome.skill_definitions.append(mutation.after)
        
        elif mutation.type == "pattern_evolution":
            if isinstance(mutation.after, dict):
                pattern_id = mutation.after.get("id")
                for i, p in enumerate(genome.response_patterns):
                    if p.get("id") == pattern_id:
                        genome.response_patterns[i] = mutation.after
                        break
    
    # =========================================================================
    # Accept/Reject Mutations
    # =========================================================================
    
    def accept_candidate(self, candidate: AgentVersion, improvement: float):
        """Accept a candidate as the new current version."""
        # Archive the old version
        self._current_version.status = "archived"
        self._archive.append(self._current_version)
        
        # Set new current
        candidate.status = "active"
        self._current_version = candidate
        
        # Track improvement
        if improvement >= self.fitness_threshold:
            self._stagnation_count = 0
            self._last_improvement = improvement
        else:
            self._stagnation_count += 1
        
        # Prune archive
        self._prune_archive()
    
    def reject_candidate(self, candidate: AgentVersion, reason: str = ""):
        """Reject a candidate and log the reason."""
        candidate.status = "rejected"
        self._archive.append(candidate)
        
        # Record failure reason in mutations
        for m in candidate.mutations:
            m.status = "rejected"
        
        self._stagnation_count += 1
        self._prune_archive()
    
    # =========================================================================
    # Archive Management
    # =========================================================================
    
    def _prune_archive(self):
        """Keep the archive within size limits."""
        if len(self._archive) <= self.max_archive_size:
            return
        
        # Always keep current version's ancestors
        keep_ids = set()
        current = self._current_version
        for _ in range(10):
            keep_ids.add(current.id)
            parent = next((v for v in self._archive if v.id == current.parent_id), None)
            if not parent:
                break
            current = parent
        
        # Keep top performers
        by_fitness = sorted(self._archive, key=lambda v: v.fitness_score, reverse=True)
        for v in by_fitness[:int(self.max_archive_size * 0.7)]:
            keep_ids.add(v.id)
        
        # Keep recent
        by_time = sorted(self._archive, key=lambda v: v.timestamp, reverse=True)
        for v in by_time[:5]:
            keep_ids.add(v.id)
        
        self._archive = [v for v in self._archive if v.id in keep_ids]
    
    # =========================================================================
    # Getters
    # =========================================================================
    
    def get_current_version(self) -> AgentVersion:
        return self._current_version
    
    def get_archive(self) -> list[AgentVersion]:
        return list(self._archive)
    
    def get_pending_mutations(self) -> list[Mutation]:
        return list(self._pending_mutations)
    
    def get_stagnation_count(self) -> int:
        return self._stagnation_count
    
    def get_evolution_tree(self) -> dict:
        """Get the evolution tree for visualization."""
        nodes = []
        edges = []
        for v in self._archive:
            nodes.append({
                "id": v.id,
                "generation": v.generation,
                "fitness": v.fitness_score,
                "label": f"Gen {v.generation} ({v.fitness_score:.1f})",
                "status": v.status,
            })
            if v.parent_id:
                edges.append({"source": v.parent_id, "target": v.id})
        
        return {"nodes": nodes, "edges": edges}
    
    # =========================================================================
    # LLM Helper
    # =========================================================================
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.llm_api_url,
                json={"message": prompt, "model": self.llm_model, "history": []},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("content", data.get("message", ""))
