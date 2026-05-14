"""
Research to Update Pipeline v59 — Converts deep research into improvement proposals.

CRITICAL ADDITION from v59:
- v58: DeepResearch found information but never fed it into SelfModifier
- v59: ResearchToUpdatePipeline converts research findings into proposals
- Automated pipeline: Research → Analyze → Propose → Apply
- Links DeepResearchEngine directly to ImprovementProposer
- Enables true self-update from web research

v59 — Super Mind العقل الخارق مامون
"""

import time
import logging
from typing import Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ResearchUpdateResult:
    """Result of a research-to-update operation."""
    query: str
    sources_found: int
    findings_count: int
    proposals_generated: int
    proposals_applied: int
    confidence: float
    latency_ms: float
    error: Optional[str] = None


class ResearchToUpdatePipeline:
    """
    Pipeline that converts deep research into self-improvements.

    Flow:
    1. RESEARCH: DeepResearchEngine finds information on a topic
    2. ANALYZE: Extract actionable insights from research findings
    3. PROPOSE: Convert insights into ImprovementProposals via ImprovementProposer
    4. APPLY: Apply approved proposals through SelfModifier

    This closes the loop: the system can now learn from the web and
    actually update itself based on what it finds.

    Usage:
        pipeline = ResearchToUpdatePipeline(kernel)
        result = await pipeline.research_and_update("best practices for self-healing systems")
    """

    def __init__(self, kernel):
        self.kernel = kernel
        self._history: list[ResearchUpdateResult] = []

    def _get_component(self, name: str) -> Any:
        return self.kernel.get_component(name)

    async def research_and_update(
        self,
        query: str,
        depth: str = "standard",
        auto_apply: bool = False,
    ) -> ResearchUpdateResult:
        """
        Research a topic and convert findings into improvements.

        Args:
            query: Research question
            depth: Research depth ("quick", "standard", "deep")
            auto_apply: If True, automatically apply approved proposals

        Returns:
            ResearchUpdateResult with operation details
        """
        start = time.time()

        researcher = self._get_component("deep_research")
        proposer = self._get_component("improvement_proposer")
        meta = self._get_component("meta_cognition")

        if not researcher:
            return ResearchUpdateResult(
                query=query, sources_found=0, findings_count=0,
                proposals_generated=0, proposals_applied=0,
                confidence=0.0, latency_ms=(time.time() - start) * 1000,
                error="DeepResearchEngine not available",
            )

        # Step 1: Research
        try:
            research_result = await researcher.research(query, depth=depth)
        except Exception as e:
            logger.error(f"Research failed: {e}")
            return ResearchUpdateResult(
                query=query, sources_found=0, findings_count=0,
                proposals_generated=0, proposals_applied=0,
                confidence=0.0, latency_ms=(time.time() - start) * 1000,
                error=str(e),
            )

        # Step 2: Extract actionable insights
        actionable_insights = self._extract_actionable_insights(research_result)

        if not actionable_insights:
            return ResearchUpdateResult(
                query=query,
                sources_found=research_result.sources_searched,
                findings_count=len(research_result.key_findings),
                proposals_generated=0, proposals_applied=0,
                confidence=research_result.confidence,
                latency_ms=(time.time() - start) * 1000,
            )

        # Step 3: Propose improvements based on research — WITH CODE GENERATION (v62 fix)
        proposals_generated = 0
        proposals_applied = 0

        if proposer and meta and self._llm_client:
            try:
                # v62 FIX: Generate proposals WITH ACTUAL CODE from research findings
                # Instead of just calling analyze_and_propose() which uses meta-cognition data,
                # we now feed research findings directly into code generation
                for insight in actionable_insights[:5]:  # Top 5 insights
                    try:
                        finding = insight["finding"]
                        insight_type = insight["type"]
                        confidence = insight["confidence"]

                        # Generate actual code proposal using LLM + research context
                        code_proposal = await self._generate_code_from_research(
                            finding, insight_type, research_result
                        )

                        if code_proposal.get("success"):
                            # Use SelfModifier to apply the code change
                            self_modifier = self._get_component("self_modifier")
                            if self_modifier:
                                from .self_modifier import ModificationProposal
                                proposal = ModificationProposal(
                                    id=f"research_{int(time.time())}_{proposals_generated}",
                                    target_file=code_proposal.get("target_file", ""),
                                    original_code=code_proposal.get("original_code", ""),
                                    proposed_code=code_proposal.get("proposed_code", code_proposal.get("code", "")),
                                    description=f"Research-based improvement: {finding[:200]}",
                                    proposer="research_to_update_pipeline",
                                    risk_level="medium" if confidence > 0.5 else "high",
                                )
                                result = await self_modifier.modify(proposal)
                                proposals_generated += 1
                                if result.get("success"):
                                    proposals_applied += 1
                                    logger.info(f"Applied research-based code change: {finding[:100]}")
                    except Exception as e:
                        logger.warning(f"Failed to generate code from research insight: {e}")

                # Also run the standard improvement proposer for meta-cognition-based improvements
                try:
                    proposals = await proposer.analyze_and_propose()
                    proposals_generated += len(proposals)

                    # Apply proposals if auto_apply is enabled
                    if auto_apply:
                        for proposal in proposals:
                            if proposal.status.value == "approved":
                                try:
                                    result = await proposer.apply_proposal(proposal.id)
                                    if result.get("success"):
                                        proposals_applied += 1
                                except Exception as e:
                                    logger.warning(f"Failed to apply proposal {proposal.id}: {e}")
                except Exception as e:
                    logger.error(f"Meta-cognition proposals failed: {e}")

            except Exception as e:
                logger.error(f"Proposal generation failed: {e}")

        # Record outcome
        if meta:
            try:
                from .meta_cognition_engine import OutcomeRecord
                meta.record_outcome(OutcomeRecord(
                    component="research_to_update_pipeline",
                    operation="research_and_update",
                    success=proposals_generated > 0,
                    quality_score=research_result.confidence,
                    predicted_quality=meta.predict_quality("research_to_update_pipeline"),
                    latency_ms=(time.time() - start) * 1000,
                    metadata={
                        "query": query[:100],
                        "sources_found": research_result.sources_searched,
                        "findings": len(research_result.key_findings),
                        "proposals": proposals_generated,
                        "applied": proposals_applied,
                    },
                ))
            except ImportError:
                pass

        result = ResearchUpdateResult(
            query=query,
            sources_found=research_result.sources_searched,
            findings_count=len(research_result.key_findings),
            proposals_generated=proposals_generated,
            proposals_applied=proposals_applied,
            confidence=research_result.confidence,
            latency_ms=(time.time() - start) * 1000,
        )

        self._history.append(result)
        if len(self._history) > 50:
            self._history = self._history[-50:]

        return result

    def _extract_actionable_insights(self, research_result) -> list[dict]:
        """Extract insights that can be turned into improvements."""
        insights = []

        for finding in research_result.key_findings:
            # Classify the finding
            insight_type = self._classify_finding(finding)
            if insight_type != "non_actionable":
                insights.append({
                    "finding": finding,
                    "type": insight_type,
                    "confidence": research_result.confidence,
                })

        # Add verified claims as high-confidence insights
        for claim in research_result.claims:
            if claim.verification == "verified":
                insights.append({
                    "finding": claim.claim,
                    "type": "verified_claim",
                    "confidence": claim.confidence,
                })

        return insights

    def _classify_finding(self, finding: str) -> str:
        """Classify a finding into an actionability category."""
        finding_lower = finding.lower()

        # Best practice findings
        practice_keywords = ["best practice", "recommended", "should", "optimal",
                            "أفضل ممارسة", "موصى به", "ينبغي"]
        if any(kw in finding_lower for kw in practice_keywords):
            return "best_practice"

        # Performance findings
        perf_keywords = ["performance", "faster", "efficient", "optimize", "improve",
                        "أداء", "أسرع", "كفاءة", "تحسين"]
        if any(kw in finding_lower for kw in perf_keywords):
            return "performance"

        # Security findings
        security_keywords = ["security", "vulnerability", "risk", "exploit", "patch",
                            "أمان", "ثغرة", "مخاطر", "خطر"]
        if any(kw in finding_lower for kw in security_keywords):
            return "security"

        # Error/bug findings
        error_keywords = ["bug", "error", "fix", "issue", "broken", "crash",
                         "خطأ", "عطل", "إصلاح", "مشكلة"]
        if any(kw in finding_lower for kw in error_keywords):
            return "bug_fix"

        return "non_actionable"

    async def _generate_code_from_research(self, finding: str, insight_type: str,
                                            research_result) -> dict:
        """
        v62: Generate actual code from research findings.
        This closes the critical gap where research findings were classified
        but never turned into executable code changes.
        """
        llm_client = self._get_component("llm_client")
        if not llm_client:
            return {"success": False, "error": "No LLM client available"}

        try:
            # Build context from research sources
            source_context = ""
            for source in research_result.sources[:3]:
                if source.content:
                    source_context += f"\nSource: {source.url}\n{source.content[:500]}\n"

            response = await llm_client.chat_with_fallback(
                messages=[
                    {"role": "system", "content": """You are a code improvement engine.
Based on research findings, generate a SPECIFIC code improvement.

You MUST return a JSON object with these fields:
{
    "target_file": "path/to/file.py",
    "improvement_type": "performance|security|bug_fix|best_practice",
    "description": "What this improvement does",
    "proposed_code": "the actual improved code",
    "original_code_hint": "what the original code probably looks like"
}

The proposed_code must be COMPLETE, WORKING Python code.
Focus on the most likely file and specific improvement.
If you can't determine a specific code change, return success: false."""},
                    {"role": "user", "content": f"""Research finding: {finding}
Type: {insight_type}

Research sources:
{source_context}

Generate a specific code improvement based on this finding."""}
                ],
                preferred_order=["deepseek", "gemini", "glm"],
            )

            if response.success:
                import json
                content = response.content.strip()
                # Strip markdown fences
                if content.startswith("```"):
                    lines = content.split("\n")
                    content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

                # Try to parse as JSON
                try:
                    proposal = json.loads(content)
                    if proposal.get("target_file") and proposal.get("proposed_code"):
                        return {"success": True, **proposal}
                except json.JSONDecodeError:
                    # If not JSON, treat the whole content as proposed code
                    if len(content) > 50:
                        return {
                            "success": True,
                            "target_file": "",
                            "proposed_code": content,
                            "description": finding[:200],
                        }

            return {"success": False, "error": "LLM did not generate usable code"}

        except Exception as e:
            logger.error(f"Code generation from research failed: {e}")
            return {"success": False, "error": str(e)}

    def detect_capability_gap(self, task_description: str) -> dict:
        """
        v62: Detect if the system lacks a capability and needs to create a tool.
        
        This is the key capability: "I don't have this tool, I'll create it."
        """
        dynamic_loader = self._get_component("dynamic_tool_loader")
        tool_creator = self._get_component("tool_creator")

        # Check if we have a tool for this task
        has_tool = False
        tool_name = ""

        if dynamic_loader:
            loaded_tools = dynamic_loader.get_loaded_tools()
            for tool in loaded_tools:
                if tool["is_callable"] and any(
                    kw in task_description.lower()
                    for kw in tool["name"].lower().split("_")
                ):
                    has_tool = True
                    tool_name = tool["name"]
                    break

        return {
            "task": task_description,
            "has_tool": has_tool,
            "existing_tool": tool_name,
            "can_create": tool_creator is not None,
            "can_load": dynamic_loader is not None,
            "action": "use_existing" if has_tool else "create_and_load",
            "message": (
                f"أملك الأداة '{tool_name}'، سأستخدمها مباشرة"
                if has_tool
                else "لا أملك هذه الأداة، سأنشئها وأستخدمها فوراً عبر DynamicToolLoader"
            ),
        }

    def get_stats(self) -> dict:
        """Get pipeline statistics."""
        return {
            "total_researches": len(self._history),
            "total_proposals_generated": sum(r.proposals_generated for r in self._history),
            "total_proposals_applied": sum(r.proposals_applied for r in self._history),
            "avg_confidence": (sum(r.confidence for r in self._history) / len(self._history))
                             if self._history else 0.0,
        }
