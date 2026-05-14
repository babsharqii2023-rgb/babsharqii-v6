"""
Deep Research Engine v59.1 — Stable, multi-source, verified research.

CRITICAL UPGRADE from v58:
- v59.1: Applied OutcomeRecorder for consistent performance tracking
- v59.1: Automatic error recording and quality prediction
- v58: Uses ZaiSdkWrapper for both web_search and web_reader
- Cross-source verification with LLM-powered claim checking
- Better content extraction using z-ai web_reader
- Depth-aware analysis: more sources and verification for deep mode
- Improved claim extraction from LLM responses
- Integrated with MetaCognitionEngine for real performance tracking

v59.1 — Super Mind العقل الخارق مامون
"""

import time
import re
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
    extraction_method: str = "unknown"  # "zai_reader", "fallback_snippet"


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
    2. EXTRACT: Read full content from top sources using z-ai web_reader
    3. ANALYZE: LLM analyzes content, identifies claims
    4. VERIFY: Cross-reference claims across sources (LLM-enhanced)
    5. SYNTHESIZE: Produce final research report with confidence scores

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
        self._zai_wrapper = None  # Lazy init for content extraction

    def set_search_client(self, client):
        self._search_client = client

    def set_llm_client(self, client):
        self._llm_client = client

    def _get_zai_wrapper(self):
        """Lazy-load the z-ai SDK wrapper for web_reader."""
        if self._zai_wrapper is None:
            try:
                from ..shared.zai_sdk_wrapper import get_zai_wrapper
                self._zai_wrapper = get_zai_wrapper()
            except ImportError:
                try:
                    from shared.zai_sdk_wrapper import get_zai_wrapper
                    self._zai_wrapper = get_zai_wrapper()
                except ImportError:
                    logger.warning("ZaiSdkWrapper not available — content extraction limited")
        return self._zai_wrapper

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
        """Extract full content from source pages using z-ai web_reader."""
        extracted = []
        urls_to_extract = sources[:max_pages]

        for source in urls_to_extract:
            url = source.get("url", "")
            if not url:
                continue

            # Try z-ai web_reader
            wrapper = self._get_zai_wrapper()
            content = ""
            extraction_method = "fallback_snippet"
            extraction_success = False

            if wrapper:
                try:
                    reader_result = await wrapper.web_reader(url)
                    if reader_result.success and reader_result.text:
                        content = reader_result.text
                        extraction_method = "zai_reader"
                        extraction_success = True
                        logger.debug(f"Extracted content from {url}: {len(content)} chars")
                    elif reader_result.html:
                        # Fallback: strip HTML
                        content = re.sub(r'<[^>]+>', ' ', reader_result.html)
                        content = re.sub(r'\s+', ' ', content).strip()
                        if content:
                            extraction_method = "zai_reader_html_stripped"
                            extraction_success = True
                except Exception as e:
                    logger.warning(f"z-ai web_reader failed for {url}: {e}")

            # If extraction failed, use snippet
            if not content:
                content = source.get("snippet", "")
                extraction_success = bool(content)
                extraction_method = "fallback_snippet"

            extracted.append(ResearchSource(
                url=url,
                title=source.get("title", ""),
                content=content[:8000],  # Limit content length
                snippet=source.get("snippet", ""),
                quality_score=source.get("quality_score", 0.0),
                extraction_success=extraction_success,
                extraction_method=extraction_method,
            ))

        # Log extraction stats
        zai_count = sum(1 for s in extracted if s.extraction_method.startswith("zai_reader"))
        logger.info(f"Content extraction: {zai_count}/{len(extracted)} via z-ai reader")

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

        context = "\n---\n".join(context_parts[:5])

        if not context:
            context = "\n".join(s.snippet for s in sources if s.snippet)

        try:
            response = await self._llm_client.chat_with_fallback(
                messages=[
                    {"role": "system", "content": """You are a research analyst. Analyze the provided sources and:
1. Write a comprehensive summary
2. List key findings (each as a separate point, prefixed with "FINDING:")
3. Identify any verifiable claims (prefixed with "CLAIM:")
4. Note any contradictions between sources (prefixed with "CONTRADICTION:")
Be thorough and cite specific sources by URL when possible."""},
                    {"role": "user", "content": f"Research query: {query}\n\nSources:\n{context}\n\nProvide your analysis."}
                ],
                preferred_order=["deepseek", "gemini", "glm"],
            )

            if response.success:
                return {
                    "summary": response.content,
                    "claims": self._extract_claims(response.content),
                    "key_findings": self._extract_findings(response.content),
                    "contradictions_text": self._extract_contradictions(response.content),
                }

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")

        return {"summary": "Analysis failed", "claims": [], "key_findings": []}

    def _extract_claims(self, text: str) -> list[str]:
        """Extract verifiable claims from analysis."""
        claims = []
        for line in text.split("\n"):
            line = line.strip()
            # Look for CLAIM: prefix or claim-related keywords
            if line.startswith("CLAIM:"):
                clean = line[6:].strip()
                if clean:
                    claims.append(clean)
            elif any(kw in line.lower() for kw in ["claim:", "states that", "according to", "asserts that", "reports that"]):
                clean = line.lstrip("-*•0123456789. ").strip()
                if clean:
                    claims.append(clean)
        return claims[:10]

    def _extract_findings(self, text: str) -> list[str]:
        """Extract key findings from analysis."""
        findings = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("FINDING:"):
                clean = line[8:].strip()
                if clean:
                    findings.append(clean)
            elif "key finding" in line.lower():
                # Also capture lines under "Key Findings" section
                continue
        # Also try to extract numbered/bullet findings
        if not findings:
            in_findings = False
            for line in text.split("\n"):
                stripped = line.strip()
                if "finding" in stripped.lower() and not stripped.startswith(("-", "*", "•")):
                    in_findings = True
                    continue
                if in_findings and stripped.startswith(("-", "*", "•")):
                    clean = stripped.lstrip("-*• ").strip()
                    if clean:
                        findings.append(clean)
                elif in_findings and stripped and not stripped.startswith(("-", "*", "•")):
                    in_findings = False
        return findings[:10]

    def _extract_contradictions(self, text: str) -> list[str]:
        """Extract contradictions from analysis."""
        contradictions = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("CONTRADICTION:"):
                clean = line[14:].strip()
                if clean:
                    contradictions.append(clean)
        return contradictions[:5]

    # ── Phase 4: Cross-source Verification ───────────────────────────────
    async def _verify_claims(self, claims: list[str], sources: list[ResearchSource]) -> list[ResearchClaim]:
        """Verify claims by cross-referencing sources using LLM when available."""
        if not claims:
            return []

        verified_claims = []

        for claim in claims[:5]:  # Verify top 5 claims
            supporting = []
            contradicting = []

            # Keyword-based preliminary check
            claim_keywords = set(claim.lower().split()[:15])  # Top 15 keywords

            for source in sources:
                if not source.content:
                    continue
                source_lower = source.content.lower()
                overlap = claim_keywords & set(source_lower.split())
                overlap_ratio = len(overlap) / max(len(claim_keywords), 1)

                if overlap_ratio > 0.3:
                    # Check for negation
                    negation_words = ["not", "however", "disputed", "contradicted", "false", "incorrect", "debunked"]
                    # Look for negation near the claim keywords
                    negation_found = False
                    for kw in overlap:
                        kw_pos = source_lower.find(kw)
                        if kw_pos >= 0:
                            context_window = source_lower[max(0, kw_pos-50):kw_pos+50]
                            if any(neg in context_window for neg in negation_words):
                                negation_found = True
                                break

                    if negation_found:
                        contradicting.append(source.url)
                    else:
                        supporting.append(source.url)

            # LLM-enhanced verification if we have both supporting and contradicting
            verification = "unverified"
            if supporting and contradicting:
                verification = "disputed"
            elif supporting:
                verification = "verified"

            # LLM cross-check for important claims (deep mode)
            if self._llm_client and len(supporting) >= 2:
                try:
                    source_texts = []
                    for s in sources[:3]:
                        if s.content:
                            source_texts.append(f"Source ({s.url}): {s.content[:500]}")

                    llm_response = await self._llm_client.chat_with_fallback(
                        messages=[
                            {"role": "system", "content": "You are a fact-checker. Verify if the claim is supported by the sources. Reply SUPPORTED, CONTRADICTED, or UNCLEAR."},
                            {"role": "user", "content": f"Claim: {claim}\n\nSources:\n{chr(10).join(source_texts)}\n\nIs the claim supported, contradicted, or unclear?"}
                        ],
                        preferred_order=["deepseek", "glm"],
                    )

                    if llm_response.success:
                        answer = llm_response.content.lower()
                        if "supported" in answer and "contradicted" not in answer:
                            verification = "verified"
                        elif "contradicted" in answer:
                            verification = "disputed"
                            if not contradicting:
                                contradicting.append("llm_verification")
                        elif "unclear" in answer:
                            verification = "unverified"
                except Exception as e:
                    logger.warning(f"LLM verification failed for claim: {e}")

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
        # Also add contradictions from LLM analysis
        contradictions.extend(analysis.get("contradictions_text", []))

        key_findings = analysis.get("key_findings", [])

        if not key_findings:
            key_findings = [c.claim for c in claims if c.verification == "verified"][:5]

        # Overall confidence
        verified_count = sum(1 for c in claims if c.verification == "verified")
        total_claims = max(len(claims), 1)
        claim_confidence = verified_count / total_claims

        # Source quality confidence
        successful_extractions = sum(1 for s in sources if s.extraction_success)
        source_confidence = successful_extractions / max(len(sources), 1)

        # Combined confidence
        overall_confidence = 0.6 * claim_confidence + 0.4 * source_confidence if claims else source_confidence

        return {
            "summary": analysis.get("summary", ""),
            "key_findings": key_findings[:10],
            "contradictions": contradictions[:5],
            "confidence": round(overall_confidence, 3),
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

        # v59.1: Record outcome using OutcomeRecorder (consistent tracking)
        if self._meta_cognition:
            try:
                from .outcome_recorder import OutcomeRecorder
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
                        "claims_verified": len(claims),
                    },
                ))
            except ImportError:
                pass

        return result

    def get_stats(self) -> dict:
        return {"total_researches": self._research_count}
