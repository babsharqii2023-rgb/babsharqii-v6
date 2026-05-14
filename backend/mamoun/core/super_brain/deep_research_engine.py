"""
Deep Research Engine v57 — Stable, multi-source, verified research.

CRITICAL UPGRADE from v56:
- v56: HTML scraping unreliable, shallow layers
- v57: z-ai SDK for search + page_reader for content extraction
- Cross-source verification: compare claims across multiple sources
- LLM-powered analysis: summarize, detect bias, find contradictions
- Depth levels: quick/standard/deep with real content extraction
- Integrated with MetaCognitionEngine for real performance tracking

v57 — Super Mind العقل الخارق مامون
"""

import time
import asyncio
import logging
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ResearchDepth(str, Enum):
    QUICK = "quick"       # 5 sources, 1 level
    STANDARD = "standard"  # 10 sources, 2 levels
    DEEP = "deep"         # 20 sources, 3 levels with verification


@dataclass
class ResearchSource:
    """A single research source with extracted content."""
    url: str
    title: str
    content: str
    snippet: str
    quality_score: float = 0.0
    extracted_at: float = field(default_factory=time.time)
    extraction_success: bool = True


@dataclass
class ResearchClaim:
    """A claim found in research with verification status."""
    claim: str
    sources: list[str]  # URLs supporting this claim
    contradicting_sources: list[str]  # URLs contradicting this claim
    verification: str  # "verified", "disputed", "unverified"
    confidence: float = 0.0


@dataclass
class ResearchResult:
    """Complete result of a research operation."""
    query: str
    depth: ResearchDepth
    sources: list[ResearchSource]
    claims: list[ResearchClaim]
    summary: str
    key_findings: list[str]
    contradictions: list[str]
    confidence: float
    total_latency_ms: float
    sources_searched: int
    content_extracted: int


class DeepResearchEngine:
    """
    Multi-phase deep research with verification.

    Phases:
    1. SEARCH: Find relevant sources using WebSearchClient
    2. EXTRACT: Read full content from top sources using page_reader
    3. ANALYZE: LLM analyzes content, identifies claims
    4. VERIFY: Cross-reference claims across sources
    5. SYNTHESIZE: Produce final research report

    Usage:
        engine = DeepResearchEngine(search_client=search, llm_client=llm)
        result = await engine.research("quantum computing applications 2025")
    """

    DEPTH_CONFIG = {
        ResearchDepth.QUICK: {"max_sources": 5, "max_depth": 1, "timeout": 30, "extract_pages": 3},
        ResearchDepth.STANDARD: {"max_sources": 10, "max_depth": 2, "timeout": 60, "extract_pages": 5},
        ResearchDepth.DEEP: {"max_sources": 20, "max_depth": 3, "timeout": 120, "extract_pages": 10},
    }

    def __init__(self, search_client=None, llm_client=None,
                 meta_cognition=None, neural_bus=None):
        self._search_client = search_client
        self._llm_client = llm_client
        self._meta_cognition = meta_cognition
        self._neural_bus = neural_bus
        self._research_count = 0

    def set_search_client(self, client):
        self._search_client = client

    def set_llm_client(self, client):
        self._llm_client = client

    # ── Phase 1: Search ──────────────────────────────────────────────────
    async def _search_sources(self, query: str, depth: ResearchDepth) -> list[dict]:
        """Search for sources using WebSearchClient."""
        config = self.DEPTH_CONFIG[depth]

        if not self._search_client:
            return []

        response = await self._search_client.search(
            query=query,
            num=config["max_sources"],
            depth=depth.value,
        )

        return [
            {"url": r.url, "title": r.title, "snippet": r.snippet,
             "quality_score": r.quality_score}
            for r in response.results
        ]

    # ── Phase 2: Extract Content ─────────────────────────────────────────
    async def _extract_content(self, sources: list[dict], max_pages: int) -> list[ResearchSource]:
        """Extract full content from source pages using z-ai page_reader."""
        extracted = []
        urls_to_extract = sources[:max_pages]

        for source in urls_to_extract:
            url = source.get("url", "")
            if not url:
                continue

            try:
                # Try z-ai page_reader
                import importlib
                zai_module = importlib.import_module("z-ai-web-dev-sdk")
                ZAI = zai_module.default if hasattr(zai_module, 'default') else zai_module.ZAI
                zai = await ZAI.create()

                result = await zai.functions.invoke("page_reader", {"url": url})

                content = ""
                if hasattr(result, 'data'):
                    content = result.data.get("html", "")
                    # Strip HTML to get text
                    import re
                    content = re.sub(r'<[^>]+>', ' ', content)
                    content = re.sub(r'\s+', ' ', content).strip()
                elif isinstance(result, dict):
                    content = result.get("html", "")
                    import re
                    content = re.sub(r'<[^>]+>', ' ', content)
                    content = re.sub(r'\s+', ' ', content).strip()

                extracted.append(ResearchSource(
                    url=url,
                    title=source.get("title", ""),
                    content=content[:5000],  # Limit content length
                    snippet=source.get("snippet", ""),
                    quality_score=source.get("quality_score", 0.0),
                    extraction_success=bool(content),
                ))

            except Exception as e:
                logger.warning(f"Failed to extract content from {url}: {e}")
                extracted.append(ResearchSource(
                    url=url,
                    title=source.get("title", ""),
                    content=source.get("snippet", ""),
                    snippet=source.get("snippet", ""),
                    quality_score=source.get("quality_score", 0.0),
                    extraction_success=False,
                ))

        return extracted

    # ── Phase 3: Analyze with LLM ────────────────────────────────────────
    async def _analyze_content(self, query: str, sources: list[ResearchSource]) -> dict:
        """Analyze extracted content using LLM."""
        if not self._llm_client:
            return {"summary": "No LLM client available", "claims": [], "key_findings": []}

        # Build context from sources
        context_parts = []
        for s in sources:
            if s.extraction_success and s.content:
                context_parts.append(f"Source: {s.title} ({s.url})\n{s.content[:2000]}\n")

        context = "\n---\n".join(context_parts[:5])  # Limit context size

        if not context:
            context = "\n".join(s.snippet for s in sources if s.snippet)

        try:
            response = await self._llm_client.chat_with_fallback(
                messages=[
                    {"role": "system", "content": """You are a research analyst. Analyze the provided sources and:
1. Write a comprehensive summary
2. List key findings (each as a separate point)
3. Identify any claims that need verification
4. Note any contradictions between sources
Be thorough and cite specific sources."""},
                    {"role": "user", "content": f"Research query: {query}\n\nSources:\n{context}\n\nProvide your analysis."}
                ],
                preferred_order=["deepseek", "gemini", "glm"],
            )

            if response.success:
                return {
                    "summary": response.content,
                    "claims": self._extract_claims(response.content),
                    "key_findings": self._extract_findings(response.content),
                }

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")

        return {"summary": "Analysis failed", "claims": [], "key_findings": []}

    def _extract_claims(self, text: str) -> list[str]:
        """Extract verifiable claims from analysis."""
        claims = []
        for line in text.split("\n"):
            line = line.strip()
            if any(kw in line.lower() for kw in ["claim", "states", "according to", "asserts", "reports"]):
                clean = line.lstrip("-*•0123456789. ").strip()
                if clean:
                    claims.append(clean)
        return claims[:10]

    def _extract_findings(self, text: str) -> list[str]:
        """Extract key findings from analysis."""
        findings = []
        in_findings = False
        for line in text.split("\n"):
            line = line.strip()
            if "key finding" in line.lower() or "finding" in line.lower():
                in_findings = True
                continue
            if in_findings and line.startswith(("-", "*", "•")):
                clean = line.lstrip("-*• ").strip()
                if clean:
                    findings.append(clean)
            elif in_findings and line and not line.startswith(("-", "*", "•")):
                in_findings = False
        return findings[:10]

    # ── Phase 4: Cross-source Verification ───────────────────────────────
    async def _verify_claims(self, claims: list[str], sources: list[ResearchSource]) -> list[ResearchClaim]:
        """Verify claims by cross-referencing sources."""
        verified_claims = []

        for claim in claims[:5]:  # Verify top 5 claims
            supporting = []
            contradicting = []

            # Simple keyword matching (could be enhanced with LLM)
            claim_keywords = set(claim.lower().split())

            for source in sources:
                if not source.content:
                    continue
                source_keywords = set(source.content.lower().split())
                overlap = claim_keywords & source_keywords

                if len(overlap) > len(claim_keywords) * 0.3:
                    # More than 30% keyword overlap = potential support
                    # Check for negation words
                    negation = any(w in source.content.lower() for w in
                                   ["not", "however", "disputed", "contradicted", "false"])
                    if negation:
                        contradicting.append(source.url)
                    else:
                        supporting.append(source.url)

            if supporting and contradicting:
                verification = "disputed"
            elif supporting:
                verification = "verified"
            else:
                verification = "unverified"

            confidence = len(supporting) / max(len(sources), 1)

            verified_claims.append(ResearchClaim(
                claim=claim,
                sources=supporting,
                contradicting_sources=contradicting,
                verification=verification,
                confidence=confidence,
            ))

        return verified_claims

    # ── Phase 5: Synthesize ──────────────────────────────────────────────
    async def _synthesize_report(self, query: str, analysis: dict,
                                  claims: list[ResearchClaim],
                                  sources: list[ResearchSource]) -> dict:
        """Synthesize final research report."""
        contradictions = [c.claim for c in claims if c.verification == "disputed"]
        key_findings = analysis.get("key_findings", [])

        # If no key findings extracted, generate from claims
        if not key_findings:
            key_findings = [c.claim for c in claims if c.verification == "verified"][:5]

        # Overall confidence
        verified_count = sum(1 for c in claims if c.verification == "verified")
        total_claims = max(len(claims), 1)
        confidence = verified_count / total_claims

        return {
            "summary": analysis.get("summary", ""),
            "key_findings": key_findings,
            "contradictions": contradictions,
            "confidence": confidence,
        }

    # ── Main research method ─────────────────────────────────────────────
    async def research(self, query: str, depth: str = "standard") -> ResearchResult:
        """
        Conduct deep research on a topic.

        Args:
            query: Research question
            depth: "quick", "standard", or "deep"

        Returns:
            ResearchResult with sources, claims, and analysis
        """
        start = time.time()
        self._research_count += 1

        research_depth = ResearchDepth(depth)
        config = self.DEPTH_CONFIG[research_depth]

        # Phase 1: Search
        raw_sources = await self._search_sources(query, research_depth)

        if not raw_sources:
            return ResearchResult(
                query=query, depth=research_depth, sources=[], claims=[],
                summary="No sources found", key_findings=[], contradictions=[],
                confidence=0.0, total_latency_ms=(time.time() - start) * 1000,
                sources_searched=0, content_extracted=0,
            )

        # Phase 2: Extract content
        sources = await self._extract_content(raw_sources, config["extract_pages"])

        # Phase 3: Analyze
        analysis = await self._analyze_content(query, sources)

        # Phase 4: Verify (only for standard and deep)
        claims = []
        if research_depth != ResearchDepth.QUICK:
            claims = await self._verify_claims(analysis.get("claims", []), sources)

        # Phase 5: Synthesize
        synthesis = await self._synthesize_report(query, analysis, claims, sources)

        total_latency = (time.time() - start) * 1000

        result = ResearchResult(
            query=query,
            depth=research_depth,
            sources=sources,
            claims=claims,
            summary=synthesis["summary"],
            key_findings=synthesis["key_findings"],
            contradictions=synthesis["contradictions"],
            confidence=synthesis["confidence"],
            total_latency_ms=total_latency,
            sources_searched=len(raw_sources),
            content_extracted=sum(1 for s in sources if s.extraction_success),
        )

        # Record in meta-cognition
        if self._meta_cognition:
            from .meta_cognition_engine import OutcomeRecord
            self._meta_cognition.record_outcome(OutcomeRecord(
                component="deep_research_engine",
                operation="research",
                success=result.sources_searched > 0,
                quality_score=result.confidence,
                predicted_quality=self._meta_cognition.predict_quality("deep_research_engine"),
                latency_ms=total_latency,
                metadata={
                    "depth": depth,
                    "sources_found": len(raw_sources),
                    "content_extracted": result.content_extracted,
                },
            ))

        return result

    def get_stats(self) -> dict:
        return {"total_researches": self._research_count}
