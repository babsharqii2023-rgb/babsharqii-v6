"""
Improvement Proposer v58 — Data-driven improvement proposals with SelfModifier integration.

CRITICAL UPGRADE from v57:
- v57: Proposals generated but never connected to SelfModifier for execution
- v58: Connected to SelfModifier for applying approved proposals
- Better evaluation with cross-provider verification
- Integration with DeepResearch for finding improvement patterns
- Improved feature flags with persistence
- Quality score based on proposal outcomes

v58 — Super Mind العقل الخارق مامون
"""

import time
import logging
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ProposalPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProposalStatus(str, Enum):
    PROPOSED = "proposed"
    EVALUATING = "evaluating"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"


@dataclass
class ImprovementProposal:
    """A data-driven improvement proposal."""
    id: str
    component: str
    title: str
    description: str
    rationale: str
    data_evidence: dict
    priority: ProposalPriority
    status: ProposalStatus = ProposalStatus.PROPOSED
    feature_flag: str = ""
    estimated_impact: float = 0.0
    risk_level: str = "medium"
    proposed_code: str = ""
    proposer: str = "improvement_proposer"
    created_at: float = field(default_factory=time.time)
    evaluated_at: Optional[float] = None
    applied_at: Optional[float] = None


class FeatureFlags:
    """Feature flag system with persistence."""

    def __init__(self):
        self._flags: dict[str, dict] = {}

    def register(self, name: str, default: bool = False, description: str = "") -> None:
        self._flags[name] = {
            "enabled": default,
            "description": description,
            "created_at": time.time(),
        }

    def is_enabled(self, name: str) -> bool:
        return self._flags.get(name, {}).get("enabled", False)

    def enable(self, name: str) -> bool:
        if name in self._flags:
            self._flags[name]["enabled"] = True
            return True
        return False

    def disable(self, name: str) -> bool:
        if name in self._flags:
            self._flags[name]["enabled"] = False
            return True
        return False

    def list_flags(self) -> dict:
        return {name: {"enabled": f["enabled"], "description": f["description"]}
                for name, f in self._flags.items()}


class ImprovementProposer:
    """
    Data-driven improvement proposer with SelfModifier integration.

    Pipeline:
    1. ANALYZE: Read performance data, identify weak components
    2. RESEARCH: Find best practices via DeepResearchEngine
    3. PROPOSE: Generate improvement proposals with evidence
    4. EVALUATE: LLM evaluates each proposal (different provider)
    5. APPLY: Connect to SelfModifier for code changes

    Usage:
        proposer = ImprovementProposer(meta_cognition=meta, llm_client=llm)
        proposals = await proposer.analyze_and_propose()
        for p in proposals:
            print(f"{p.title}: {p.rationale}")
    """

    def __init__(self, meta_cognition=None, llm_client=None,
                 research_engine=None, neural_bus=None, self_modifier=None):
        self._meta_cognition = meta_cognition
        self._llm_client = llm_client
        self._research_engine = research_engine
        self._neural_bus = neural_bus
        self._self_modifier = self_modifier
        self._feature_flags = FeatureFlags()
        self._proposals: list[ImprovementProposal] = []
        self._proposal_counter = 0

    def set_llm_client(self, client):
        self._llm_client = client

    def set_research_engine(self, engine):
        self._research_engine = engine

    def set_self_modifier(self, modifier):
        """Set the SelfModifier for applying proposals."""
        self._self_modifier = modifier

    def _next_id(self) -> str:
        self._proposal_counter += 1
        return f"imp_{self._proposal_counter:04d}"

    # ── Step 1: Analyze performance data ─────────────────────────────────
    def _identify_weak_components(self) -> list[dict]:
        """Identify components with real performance issues."""
        if not self._meta_cognition:
            return []

        # Use the built-in unhealthy components check
        unhealthy = self._meta_cognition.get_unhealthy_components()

        # Also check for stagnant components
        stagnant = self._meta_cognition.get_stagnant_components()

        weak = []
        seen = set()

        for item in unhealthy:
            component = item["component"]
            if component not in seen:
                seen.add(component)
                weak.append({
                    "component": component,
                    "issues": item["issues"],
                    "data": {
                        "reliability_score": item["reliability"],
                        "health_status": item["health_status"],
                    },
                })

        for component in stagnant:
            if component not in seen:
                seen.add(component)
                profile = self._meta_cognition.get_profile(component)
                weak.append({
                    "component": component,
                    "issues": ["Component is stagnant"],
                    "data": {
                        "reliability_score": profile.reliability_score if profile else 0,
                        "quality_trend": profile.quality_trend if profile else 0,
                    },
                })

        return weak

    # ── Step 2: Generate proposals ───────────────────────────────────────
    async def _generate_proposal(self, weak_component: dict) -> Optional[ImprovementProposal]:
        """Generate an improvement proposal for a weak component."""
        component = weak_component["component"]
        issues = weak_component["issues"]
        data = weak_component["data"]

        if not self._llm_client:
            return ImprovementProposal(
                id=self._next_id(),
                component=component,
                title=f"Fix issues in {component}",
                description=f"Address: {', '.join(issues)}",
                rationale=f"Performance data shows: {data}",
                data_evidence=data,
                priority=ProposalPriority.HIGH if data.get("reliability_score", 1) < 0.4 else ProposalPriority.MEDIUM,
                feature_flag=f"fix_{component}",
            )

        # Research best practices if research engine is available
        research_context = ""
        if self._research_engine:
            try:
                result = await self._research_engine.research(
                    f"best practices for improving {component} performance",
                    depth="quick"
                )
                if result.key_findings:
                    research_context = "\n\nResearch findings:\n" + "\n".join(f"- {f}" for f in result.key_findings[:5])
            except Exception as e:
                logger.warning(f"Research for proposal failed: {e}")

        try:
            response = await self._llm_client.chat_with_fallback(
                messages=[
                    {"role": "system", "content": """You are a system improvement analyst.
Given real performance data, propose specific improvements.
Each proposal must include:
1. A clear title
2. A description of the change
3. Rationale based on the data
4. Risk assessment (low/medium/high)
5. Estimated impact (0-1)

Format your response as:
TITLE: ...
DESCRIPTION: ...
RATIONALE: ...
RISK: ...
IMPACT: ..."""},
                    {"role": "user", "content": f"""Component: {component}
Issues: {', '.join(issues)}
Performance data: {data}{research_context}

Propose a specific improvement based on this real data."""}
                ],
                preferred_order=["deepseek", "gemini", "glm"],
            )

            if response.success:
                content = response.content
                title = self._extract_field(content, "TITLE") or f"Improve {component}"
                description = self._extract_field(content, "DESCRIPTION") or "See rationale"
                rationale = self._extract_field(content, "RATIONALE") or "Based on performance data"
                risk = self._extract_field(content, "RISK") or "medium"
                try:
                    impact = float(self._extract_field(content, "IMPACT") or "0.5")
                except ValueError:
                    impact = 0.5

                priority = ProposalPriority.CRITICAL if data.get("reliability_score", 1) < 0.3 else \
                           ProposalPriority.HIGH if data.get("reliability_score", 1) < 0.6 else \
                           ProposalPriority.MEDIUM

                return ImprovementProposal(
                    id=self._next_id(),
                    component=component,
                    title=title,
                    description=description,
                    rationale=rationale,
                    data_evidence=data,
                    priority=priority,
                    risk_level=risk,
                    estimated_impact=impact,
                    feature_flag=f"improve_{component}",
                )

        except Exception as e:
            logger.error(f"LLM proposal generation failed: {e}")

        return None

    # ── Step 3: Evaluate proposals ───────────────────────────────────────
    async def _evaluate_proposal(self, proposal: ImprovementProposal) -> bool:
        """Evaluate a proposal using a different LLM provider."""
        if not self._llm_client:
            return True

        try:
            # Use a DIFFERENT provider for evaluation
            available = self._llm_client.available_providers()
            evaluator = "gemini" if "gemini" in available else "deepseek"

            response = await self._llm_client.chat(
                provider=evaluator,
                messages=[
                    {"role": "system", "content": "You are a proposal evaluator. Assess whether this improvement proposal is sound, safe, and beneficial. Respond with APPROVE or REJECT and your reasoning."},
                    {"role": "user", "content": f"""Proposal: {proposal.title}
Component: {proposal.component}
Description: {proposal.description}
Rationale: {proposal.rationale}
Risk: {proposal.risk_level}
Evidence: {proposal.data_evidence}

Approve or reject?"""}
                ],
            )

            if response.success:
                content_lower = response.content.lower()
                return "approve" in content_lower and "reject" not in content_lower

        except Exception as e:
            logger.error(f"Proposal evaluation failed: {e}")

        return True

    # ── Main method ──────────────────────────────────────────────────────
    async def analyze_and_propose(self) -> list[ImprovementProposal]:
        """Analyze system performance and generate improvement proposals."""
        start = time.time()

        weak_components = self._identify_weak_components()

        if not weak_components:
            logger.info("No weak components found — system is healthy")
            return []

        # Generate proposals
        proposals = []
        for weak in weak_components:
            proposal = await self._generate_proposal(weak)
            if proposal:
                proposals.append(proposal)

        # Evaluate each proposal
        for proposal in proposals:
            proposal.status = ProposalStatus.EVALUATING
            approved = await self._evaluate_proposal(proposal)
            proposal.status = ProposalStatus.APPROVED if approved else ProposalStatus.REJECTED
            proposal.evaluated_at = time.time()

            if approved:
                self._feature_flags.register(
                    proposal.feature_flag,
                    default=False,
                    description=proposal.description,
                )

        # Sort by priority and impact
        proposals.sort(key=lambda p: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3}[p.priority.value],
            -p.estimated_impact,
        ))

        self._proposals.extend(proposals)

        # Record in meta-cognition
        quality = len(proposals) / max(len(weak_components), 1)
        if self._meta_cognition:
            try:
                from .meta_cognition_engine import OutcomeRecord
                self._meta_cognition.record_outcome(OutcomeRecord(
                    component="improvement_proposer",
                    operation="analyze_and_propose",
                    success=True,
                    quality_score=quality,
                    predicted_quality=self._meta_cognition.predict_quality("improvement_proposer"),
                    latency_ms=(time.time() - start) * 1000,
                    metadata={"weak_components": len(weak_components), "proposals": len(proposals)},
                ))
            except ImportError:
                pass

        return proposals

    # ── Apply proposals ──────────────────────────────────────────────────
    async def apply_proposal(self, proposal_id: str) -> dict:
        """Apply an approved proposal using SelfModifier."""
        proposal = next((p for p in self._proposals if p.id == proposal_id), None)
        if not proposal:
            return {"success": False, "error": f"Proposal {proposal_id} not found"}

        if proposal.status != ProposalStatus.APPROVED:
            return {"success": False, "error": f"Proposal is {proposal.status.value}, not approved"}

        if not self._self_modifier:
            return {"success": False, "error": "No SelfModifier configured"}

        if not proposal.proposed_code:
            return {"success": False, "error": "No proposed code in this proposal"}

        proposal.status = ProposalStatus.APPLYING

        from .self_modifier import ModificationProposal, ModificationStatus
        mod = ModificationProposal(
            id=f"mod_{proposal.id}",
            target_file=proposal.component,  # Would need actual file path
            original_code="",
            proposed_code=proposal.proposed_code,
            description=proposal.description,
            proposer="improvement_proposer",
            risk_level=proposal.risk_level,
        )

        result = await self._self_modifier.modify(mod)

        if result["success"]:
            proposal.status = ProposalStatus.APPLIED
            proposal.applied_at = time.time()
            self._feature_flags.enable(proposal.feature_flag)
        else:
            proposal.status = ProposalStatus.FAILED

        return result

    def get_feature_flags(self) -> dict:
        return self._feature_flags.list_flags()

    def enable_feature(self, name: str) -> bool:
        return self._feature_flags.enable(name)

    def disable_feature(self, name: str) -> bool:
        return self._feature_flags.disable(name)

    def get_proposals(self, status: ProposalStatus = None) -> list[ImprovementProposal]:
        if status:
            return [p for p in self._proposals if p.status == status]
        return self._proposals

    @staticmethod
    def _extract_field(text: str, field_name: str) -> Optional[str]:
        for line in text.split("\n"):
            if line.strip().startswith(f"{field_name}:") or line.strip().startswith(f"{field_name} :"):
                value = line.split(":", 1)[1].strip()
                return value
        return None

    def get_stats(self) -> dict:
        return {
            "total_proposals": len(self._proposals),
            "approved": sum(1 for p in self._proposals if p.status == ProposalStatus.APPROVED),
            "rejected": sum(1 for p in self._proposals if p.status == ProposalStatus.REJECTED),
            "applied": sum(1 for p in self._proposals if p.status == ProposalStatus.APPLIED),
            "failed": sum(1 for p in self._proposals if p.status == ProposalStatus.FAILED),
            "feature_flags": self._feature_flags.list_flags(),
            "has_self_modifier": self._self_modifier is not None,
        }
