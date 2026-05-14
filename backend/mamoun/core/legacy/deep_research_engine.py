"""
BABSHARQII v21.0 — Deep Research Engine (محرك البحث العميق)
بحث عميق مع تحقق وتبادل مصادر وتحليل متعدد المراحل

المراحل:
  1. استعلام أولي — بحث عام عن الموضوع
  2. استعلامات فرعية — تفكيك الموضوع لأسئلة فرعية
  3. جمع المصادر — البحث عن مصادر متعددة
  4. التحقق — مقارنة المصادر والتأكد من الحقائق
  5. التحليل — استنتاجات وتوصيات
  6. التقرير — تقرير شامل مع مراجع

يعتمد على:
  - Web Search API (z-ai-web-dev-sdk)
  - LLM للتحليل والتركيب
  - التحقق المتقاطع من المصادر
"""

import os
import time
import json
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum
from pathlib import Path

import httpx

logger = logging.getLogger("mamoun.core.deep_research_engine")


class ResearchDepth(int, Enum):
    QUICK = 1       # بحث سريع — مصدر واحد
    STANDARD = 2    # بحث قياسي — 3 مصادر
    DEEP = 3        # بحث عميق — 5+ مصادر + تحقق
    EXHAUSTIVE = 4  # بحث شامل — 10+ مصادر + تحليل كامل


class SourceCredibility(str, Enum):
    HIGH = "high"          # مصادر أكاديمية/رسمية
    MEDIUM = "medium"      # مصادر إخبارية/مقالات
    LOW = "low"            # مدونات/منتديات
    UNVERIFIED = "unverified"  # غير محقق


@dataclass
class ResearchSource:
    """مصدر بحثي"""
    url: str = ""
    title: str = ""
    snippet: str = ""
    credibility: SourceCredibility = SourceCredibility.UNVERIFIED
    relevance_score: float = 0.0
    fact_check_status: str = "unchecked"  # unchecked, verified, disputed, false
    extracted_facts: list = field(default_factory=list)
    retrieved_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet[:300],
            "credibility": self.credibility.value,
            "relevance_score": round(self.relevance_score, 3),
            "fact_check_status": self.fact_check_status,
            "extracted_facts": self.extracted_facts[:5],
        }


@dataclass
class ResearchFact:
    """حقيقة مستخرجة"""
    claim: str = ""
    source_url: str = ""
    confidence: float = 0.0
    supporting_sources: int = 0
    contradicting_sources: int = 0
    verification_status: str = "unverified"

    def to_dict(self) -> dict:
        return {
            "claim": self.claim,
            "confidence": round(self.confidence, 3),
            "supporting_sources": self.supporting_sources,
            "contradicting_sources": self.contradicting_sources,
            "verification_status": self.verification_status,
        }


@dataclass
class ResearchReport:
    """تقرير بحثي شامل"""
    query: str = ""
    depth: ResearchDepth = ResearchDepth.STANDARD
    sources: list = field(default_factory=list)  # ResearchSource
    facts: list = field(default_factory=list)     # ResearchFact
    summary: str = ""
    analysis: str = ""
    recommendations: list = field(default_factory=list)
    contradictions: list = field(default_factory=list)
    confidence_score: float = 0.0
    research_time_seconds: float = 0.0
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "depth": self.depth.value,
            "sources": [s.to_dict() for s in self.sources],
            "facts": [f.to_dict() for f in self.facts],
            "summary": self.summary,
            "analysis": self.analysis,
            "recommendations": self.recommendations,
            "contradictions": self.contradictions,
            "confidence_score": round(self.confidence_score, 3),
            "research_time_seconds": round(self.research_time_seconds, 2),
            "source_count": len(self.sources),
            "fact_count": len(self.facts),
            "timestamp": self.timestamp,
        }


class DeepResearchEngine:
    """
    محرك البحث العميق — بحث مع تحقق وتبادل مصادر

    يستخدم:
    1. ويب سيرش لجمع المصادر
    2. LLM لتحليل وتركيب المعلومات
    3. التحقق المتقاطع من المصادر
    4. كشف التناقضات
    5. تقييم مصداقية المصادر
    """

    SEARCH_API_URL = os.getenv("MAMOUN_SEARCH_API_URL", "https://api.search.brave.com/res/v1/web/search")
    SEARCH_API_KEY = os.getenv("MAMOUN_BRAVE_API_KEY", "")

    # Credibility indicators
    HIGH_CREDIBILITY_DOMAINS = [
        ".gov", ".edu", ".org", "wikipedia.org", "nature.com",
        "sciencedirect.com", "arxiv.org", "pubmed.ncbi.nlm.nih.gov",
        "reuters.com", "apnews.com", "bbc.com",
    ]
    LOW_CREDIBILITY_DOMAINS = [
        "reddit.com", "quora.com", "facebook.com", "twitter.com",
        "tiktok.com", "pinterest.com",
    ]

    def __init__(self, llm_client=None):
        self._llm = llm_client
        self._search_cache: Dict[str, list] = {}
        self._report_counter = 0

    async def research(self, query: str, depth: int = 3, verify: bool = True) -> dict:
        """
        بحث عميق — المراحل الكاملة

        Args:
            query: سؤال البحث
            depth: عمق البحث (1-4)
            verify: هل يتم التحقق من الحقائق؟
        """
        start_time = time.time()
        research_depth = ResearchDepth(min(depth, 4))

        report = ResearchReport(
            query=query,
            depth=research_depth,
            timestamp=time.time(),
        )

        # Phase 1: Initial search
        sources = await self._search_web(query, num_results=min(5 * research_depth.value, 20))
        report.sources = sources

        # Phase 2: Sub-queries (if depth > 1)
        if research_depth.value >= 2 and self._llm:
            sub_queries = await self._generate_sub_queries(query)
            for sq in sub_queries[:research_depth.value]:
                sub_sources = await self._search_web(sq, num_results=3)
                report.sources.extend(sub_sources)

        # Deduplicate sources
        report.sources = self._deduplicate_sources(report.sources)

        # Phase 3: Extract facts
        if self._llm and report.sources:
            facts = await self._extract_facts(query, report.sources)
            report.facts = facts

        # Phase 4: Verify facts (if requested)
        if verify and self._llm and report.facts:
            verified_facts = await self._verify_facts(report.facts, report.sources)
            report.facts = verified_facts

            # Detect contradictions
            contradictions = await self._detect_contradictions(report.facts)
            report.contradictions = contradictions

        # Phase 5: Generate analysis and summary
        if self._llm:
            analysis_result = await self._generate_analysis(query, report)
            report.summary = analysis_result.get("summary", "")
            report.analysis = analysis_result.get("analysis", "")
            report.recommendations = analysis_result.get("recommendations", [])
            report.confidence_score = analysis_result.get("confidence", 0.5)

        report.research_time_seconds = time.time() - start_time

        # Save report
        self._report_counter += 1
        report_dir = Path(__file__).parent.parent.parent.parent / "download" / "research"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"research_{int(time.time())}_{self._report_counter}.json"
        report_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return report.to_dict()

    async def _search_web(self, query: str, num_results: int = 10) -> list:
        """بحث في الويب"""
        sources = []

        # Try using z-ai web search SDK
        try:
            from mamoun.core.web_search_client import search_web
            results = await search_web(query, num=num_results)
            for r in results:
                credibility = self._assess_credibility(r.get("url", ""))
                sources.append(ResearchSource(
                    url=r.get("url", ""),
                    title=r.get("name", r.get("title", "")),
                    snippet=r.get("snippet", ""),
                    credibility=credibility,
                    relevance_score=0.7,
                    retrieved_at=time.time(),
                ))
        except ImportError:
            pass

        # Fallback: direct HTTP search
        if not sources:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    # Use DuckDuckGo HTML (no API key needed)
                    resp = await client.get(
                        "https://html.duckduckgo.com/html/",
                        params={"q": query},
                        headers={"User-Agent": "Mozilla/5.0"},
                    )
                    if resp.status_code == 200:
                        # Parse basic results
                        import re
                        results = re.findall(
                            r'<a rel="nofollow" class="result__a" href="([^"]+)">(.*?)</a>.*?<a class="result__snippet".*?>(.*?)</a>',
                            resp.text, re.DOTALL
                        )
                        for url, title, snippet in results[:num_results]:
                            clean_title = re.sub(r'<[^>]+>', '', title).strip()
                            clean_snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                            credibility = self._assess_credibility(url)
                            sources.append(ResearchSource(
                                url=url,
                                title=clean_title,
                                snippet=clean_snippet[:300],
                                credibility=credibility,
                                relevance_score=0.6,
                                retrieved_at=time.time(),
                            ))
            except Exception as e:
                logger.warning("Web search error: %s", e)

        return sources

    async def _generate_sub_queries(self, query: str) -> list:
        """توليد استعلامات فرعية"""
        if not self._llm:
            return []

        response = await self._llm.think(
            prompt=f"""حلّل هذا السؤال البحثي إلى 5 أسئلة فرعية تغطي جوانب مختلفة:

السؤال: {query}

أجب بقائمة فقط، كل سؤال في سطر:
1. ...
2. ...
3. ...
4. ...
5. ...""",
            system="أنت باحث محترف. حلّل الأسئلة بدقة.",
            temperature=0.3,
        )

        sub_queries = []
        for line in response.text.split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                # Remove numbering
                cleaned = line.lstrip("0123456789.-) ")
                if len(cleaned) > 5:
                    sub_queries.append(cleaned)

        return sub_queries[:5]

    async def _extract_facts(self, query: str, sources: list) -> list:
        """استخراج الحقائق من المصادر"""
        if not self._llm:
            return []

        sources_text = "\n".join([
            f"[{i+1}] {s.title}: {s.snippet}"
            for i, s in enumerate(sources[:10])
        ])

        response = await self._llm.think(
            prompt=f"""استخرج أهم الحقائق من هذه المصادر حول: {query}

المصادر:
{sources_text}

استخرج 5-10 حقائق رئيسية مع ذكر المصدر لكل حقيقة.
أجب بصيغة JSON:
[
    {{"claim": "الحقيقة", "source_index": 1, "confidence": 0.8}},
    ...
]""",
            system="أنت محلل بيانات محترف. استخرج الحقائق بدقة واعتدال.",
            temperature=0.2,
            json_mode=True,
        )

        facts = []
        result = response.extract_json()
        if isinstance(result, list):
            for item in result[:10]:
                src_idx = item.get("source_index", 0) - 1
                src_url = sources[src_idx].url if 0 <= src_idx < len(sources) else ""
                facts.append(ResearchFact(
                    claim=item.get("claim", ""),
                    source_url=src_url,
                    confidence=item.get("confidence", 0.5),
                    supporting_sources=1,
                ))

        return facts

    async def _verify_facts(self, facts: list, sources: list) -> list:
        """التحقق من الحقائق عبر المصادر المتقاطعة"""
        for fact in facts:
            # Count supporting sources
            supporting = 0
            contradicting = 0

            for source in sources:
                if source.snippet and fact.claim[:20].lower() in source.snippet.lower():
                    supporting += 1

            fact.supporting_sources = supporting
            fact.contradicting_sources = contradicting

            if supporting >= 3:
                fact.verification_status = "verified"
                fact.confidence = min(1.0, fact.confidence + 0.2)
            elif supporting >= 1:
                fact.verification_status = "partially_verified"
            else:
                fact.verification_status = "unverified"
                fact.confidence = max(0.1, fact.confidence - 0.1)

        return facts

    async def _detect_contradictions(self, facts: list) -> list:
        """كشف التناقضات بين الحقائق"""
        if not self._llm or len(facts) < 2:
            return []

        claims = [f.claim for f in facts]
        response = await self._llm.think(
            prompt=f"""هل توجد تناقضات بين هذه الحقائق؟

الحقائق:
{json.dumps(claims, ensure_ascii=False)}

إذا وُجدت تناقضات، أجب بصيغة JSON:
[
    {{"fact_1": "الحقيقة الأولى", "fact_2": "الحقيقة الثانية", "contradiction": "شرح التناقض"}},
    ...
]

إذا لم توجد تناقضات، أجب: []""",
            system="أنت مدقق حقائق محترف. اكتشف التناقضات بدقة.",
            temperature=0.2,
            json_mode=True,
        )

        result = response.extract_json()
        return result if isinstance(result, list) else []

    async def _generate_analysis(self, query: str, report) -> dict:
        """توليد التحليل والتوصيات"""
        if not self._llm:
            return {"summary": "", "analysis": "", "recommendations": [], "confidence": 0.5}

        facts_text = "\n".join([f"- {f.claim} (ثقة: {f.confidence:.0%})" for f in report.facts[:10]])
        sources_text = "\n".join([f"- [{s.credibility.value}] {s.title}" for s in report.sources[:10]])

        response = await self._llm.think(
            prompt=f"""حلّل نتائج البحث حول: {query}

الحقائق المستخرجة:
{facts_text}

المصادر:
{sources_text}

التناقضات: {json.dumps(report.contradictions, ensure_ascii=False)[:500]}

قدّم:
1. ملخص شامل (3 فقرات على الأقل)
2. تحليل معمّق
3. توصيات عملية
4. درجة الثقة العامة (0-1)

أجب بصيغة JSON:
{{
    "summary": "الملخص",
    "analysis": "التحليل",
    "recommendations": ["توصية 1", "توصية 2"],
    "confidence": 0.8
}}""",
            system="أنت باحث و محلل محترف. قدّم تحليلاً معمقاً وموثوقاً.",
            temperature=0.3,
            json_mode=True,
        )

        return response.extract_json() or {
            "summary": response.text[:500],
            "analysis": "",
            "recommendations": [],
            "confidence": 0.5,
        }

    def _assess_credibility(self, url: str) -> SourceCredibility:
        """تقييم مصداقية المصدر"""
        url_lower = url.lower()

        for domain in self.HIGH_CREDIBILITY_DOMAINS:
            if domain in url_lower:
                return SourceCredibility.HIGH

        for domain in self.LOW_CREDIBILITY_DOMAINS:
            if domain in url_lower:
                return SourceCredibility.LOW

        # HTTPS = slightly more credible
        if url_lower.startswith("https://"):
            return SourceCredibility.MEDIUM

        return SourceCredibility.UNVERIFIED

    @staticmethod
    def _deduplicate_sources(sources: list) -> list:
        """إزالة المصادر المكررة"""
        seen_urls = set()
        unique = []
        for source in sources:
            if source.url not in seen_urls:
                seen_urls.add(source.url)
                unique.append(source)
        return unique

    def get_status(self) -> dict:
        return {
            "initialized": True,
            "search_cache_size": len(self._search_cache),
            "reports_generated": self._report_counter,
        }
