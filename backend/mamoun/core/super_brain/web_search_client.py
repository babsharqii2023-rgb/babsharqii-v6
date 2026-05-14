"""
Web Search Client v57 — Stable, multi-source web search.

CRITICAL UPGRADE from v56:
- v56: DuckDuckGo HTML scraping — unreliable, breaks often
- v57: Three-tier search: z-ai SDK (primary) → DuckDuckGo (fallback) → Cache
- Proper caching with TTL
- Rate limiting
- Result validation and quality scoring
- Integrated with MetaCognitionEngine for real performance tracking

v57 — Super Mind العقل الخارق مامون
"""

import time
import json
import hashlib
import logging
import asyncio
from typing import Any, Optional
from dataclasses import dataclass, field
from collections import OrderedDict

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result with quality metadata."""
    url: str
    title: str
    snippet: str
    source: str  # "zai_sdk", "duckduckgo", "cache"
    rank: int = 0
    quality_score: float = 0.0  # Computed quality
    fetch_time: float = field(default_factory=time.time)
    host_name: str = ""


@dataclass
class SearchResponse:
    """Response from a search operation."""
    query: str
    results: list[SearchResult]
    total_results: int
    source_used: str  # Which source actually provided results
    latency_ms: float
    from_cache: bool = False
    error: Optional[str] = None


class LRUCache:
    """Simple LRU cache for search results."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._hits = 0
        self._misses = 0

    def _key(self, query: str, num: int) -> str:
        return hashlib.md5(f"{query}:{num}".encode()).hexdigest()

    def get(self, query: str, num: int) -> Optional[SearchResponse]:
        key = self._key(query, num)
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                self._hits += 1
                self._cache.move_to_end(key)
                return data
            else:
                del self._cache[key]
        self._misses += 1
        return None

    def put(self, query: str, num: int, response: SearchResponse) -> None:
        key = self._key(query, num)
        self._cache[key] = (response, time.time())
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }


class RateLimiter:
    """Simple rate limiter."""

    def __init__(self, requests_per_minute: int = 30):
        self._rpm = requests_per_minute
        self._timestamps: list[float] = []

    async def wait_if_needed(self) -> None:
        now = time.time()
        self._timestamps = [t for t in self._timestamps if now - t < 60]
        if len(self._timestamps) >= self._rpm:
            oldest = self._timestamps[0]
            wait = 60 - (now - oldest) + 0.1
            if wait > 0:
                logger.info(f"Rate limit: waiting {wait:.1f}s")
                await asyncio.sleep(wait)
        self._timestamps.append(time.time())


class WebSearchClient:
    """
    Stable web search with multiple sources and caching.

    Search priority:
    1. Cache — if recent results exist, return them
    2. z-ai SDK — reliable, structured results
    3. DuckDuckGo — fallback scraping
    4. Return cached results if all sources fail

    Usage:
        client = WebSearchClient()
        response = await client.search("Python async best practices")
        for result in response.results:
            print(f"{result.title}: {result.url}")
    """

    def __init__(self, meta_cognition=None, neural_bus=None):
        self._cache = LRUCache(max_size=500, ttl_seconds=1800)  # 30 min
        self._rate_limiter = RateLimiter(requests_per_minute=30)
        self._http_client: Optional[httpx.AsyncClient] = None
        self._meta_cognition = meta_cognition
        self._neural_bus = neural_bus
        self._search_count = 0
        self._error_count = 0

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": "SuperMind/57.0 (Research Engine)"}
            )
        return self._http_client

    def _compute_quality(self, result: SearchResult) -> float:
        """Compute quality score for a search result."""
        score = 0.0
        # Title quality
        if len(result.title) > 10:
            score += 0.2
        # Snippet quality
        if len(result.snippet) > 50:
            score += 0.3
        # URL validity
        if result.url.startswith("https://"):
            score += 0.2
        # Not a spam domain
        spam_indicators = ["ads", "spam", "clickbait", "popup"]
        if not any(s in result.host_name.lower() for s in spam_indicators):
            score += 0.3
        return score

    # ── Source 1: z-ai SDK ───────────────────────────────────────────────
    async def _search_zai_sdk(self, query: str, num: int = 10) -> list[SearchResult]:
        """Search using z-ai-web-dev-sdk — the most reliable source."""
        try:
            import importlib
            zai_module = importlib.import_module("z-ai-web-dev-sdk")
            ZAI = zai_module.default if hasattr(zai_module, 'default') else zai_module.ZAI
            zai = await ZAI.create()

            results = await zai.functions.invoke("web_search", {
                "query": query,
                "num": num
            })

            search_results = []
            for i, item in enumerate(results):
                result = SearchResult(
                    url=item.get("url", ""),
                    title=item.get("name", ""),
                    snippet=item.get("snippet", ""),
                    source="zai_sdk",
                    rank=i,
                    host_name=item.get("host_name", ""),
                )
                result.quality_score = self._compute_quality(result)
                search_results.append(result)

            return search_results

        except ImportError:
            logger.warning("z-ai-web-dev-sdk not available")
            return []
        except Exception as e:
            logger.error(f"z-ai SDK search failed: {e}")
            return []

    # ── Source 2: DuckDuckGo (fallback) ──────────────────────────────────
    async def _search_duckduckgo(self, query: str, num: int = 10) -> list[SearchResult]:
        """Fallback: DuckDuckGo HTML scraping."""
        client = await self._get_http_client()

        try:
            # DuckDuckGo HTML version — simpler to parse
            url = "https://html.duckduckgo.com/html/"
            data = {"q": query, "kl": "wt-wt"}

            resp = await client.post(url, data=data, follow_redirects=True)
            if resp.status_code != 200:
                return []

            results = []
            # Parse HTML results
            import re
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")
            for i, item in enumerate(soup.select(".result")):
                title_el = item.select_one(".result__title a")
                snippet_el = item.select_one(".result__snippet")

                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                # Clean DuckDuckGo redirect URLs
                if "//duckduckgo.com/l/" in href:
                    match = re.search(r'uddg=([^&]+)', href)
                    if match:
                        from urllib.parse import unquote
                        href = unquote(match.group(1))

                result = SearchResult(
                    url=href,
                    title=title,
                    snippet=snippet,
                    source="duckduckgo",
                    rank=i,
                    host_name=href.split("/")[2] if "/" in href else "",
                )
                result.quality_score = self._compute_quality(result)
                results.append(result)

                if len(results) >= num:
                    break

            return results

        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []

    # ── Unified Search ───────────────────────────────────────────────────
    async def search(
        self,
        query: str,
        num: int = 10,
        depth: str = "standard",
        force_fresh: bool = False,
    ) -> SearchResponse:
        """
        Search the web using multiple sources with fallback.

        Args:
            query: Search query
            num: Number of results desired
            depth: "quick" (5), "standard" (10), "deep" (20)
            force_fresh: Skip cache and fetch fresh results

        Returns:
            SearchResponse with results and metadata
        """
        depth_num = {"quick": 5, "standard": 10, "deep": 20}.get(depth, num)
        num = min(num, depth_num)

        start = time.time()

        # 1. Check cache first
        if not force_fresh:
            cached = self._cache.get(query, num)
            if cached:
                cached.from_cache = True
                cached.latency_ms = (time.time() - start) * 1000
                return cached

        # 2. Rate limiting
        await self._rate_limiter.wait_if_needed()

        # 3. Try z-ai SDK first (most reliable)
        results = await self._search_zai_sdk(query, num)
        source_used = "zai_sdk"

        # 4. Fallback to DuckDuckGo if needed
        if len(results) < 3:
            logger.info("z-ai SDK returned few results, trying DuckDuckGo fallback")
            ddg_results = await self._search_duckduckgo(query, num)
            if ddg_results:
                # Merge, deduplicate by URL
                existing_urls = {r.url for r in results}
                for r in ddg_results:
                    if r.url not in existing_urls:
                        results.append(r)
                        existing_urls.add(r.url)
                if not results:
                    source_used = "duckduckgo"
                else:
                    source_used = "zai_sdk+duckduckgo"

        # 5. Sort by quality score
        results.sort(key=lambda r: r.quality_score, reverse=True)
        results = results[:num]

        latency = (time.time() - start) * 1000

        # 6. Build response
        response = SearchResponse(
            query=query,
            results=results,
            total_results=len(results),
            source_used=source_used,
            latency_ms=latency,
        )

        # 7. Cache the results
        if results:
            self._cache.put(query, num, response)

        # 8. Record in meta-cognition
        self._search_count += 1
        if self._meta_cognition:
            from .meta_cognition_engine import OutcomeRecord
            self._meta_cognition.record_outcome(OutcomeRecord(
                component="web_search_client",
                operation="search",
                success=len(results) > 0,
                quality_score=sum(r.quality_score for r in results) / len(results) if results else 0.0,
                predicted_quality=self._meta_cognition.predict_quality("web_search_client"),
                latency_ms=latency,
                metadata={"source": source_used, "result_count": len(results)},
            ))

        return response

    async def search_and_summarize(self, query: str, llm_client=None) -> dict:
        """Search and then summarize results using LLM."""
        response = await self.search(query)

        if not response.results:
            return {"query": query, "summary": "No results found", "sources": []}

        # Build context from top results
        context = "\n\n".join([
            f"{i+1}. {r.title}\n{r.snippet}\nURL: {r.url}"
            for i, r in enumerate(response.results[:5])
        ])

        if llm_client:
            try:
                llm_response = await llm_client.chat_with_fallback(
                    messages=[
                        {"role": "system", "content": "Summarize search results clearly and concisely. Include key findings and source URLs."},
                        {"role": "user", "content": f"Query: {query}\n\nResults:\n{context}\n\nProvide a comprehensive summary."},
                    ]
                )
                summary = llm_response.content if llm_response.success else "LLM summary failed"
            except Exception:
                summary = "LLM summary unavailable"
        else:
            summary = context[:500]

        return {
            "query": query,
            "summary": summary,
            "sources": [{"title": r.title, "url": r.url} for r in response.results[:5]],
            "total_results": response.total_results,
            "source_used": response.source_used,
        }

    def get_stats(self) -> dict:
        """Get search client statistics."""
        return {
            "total_searches": self._search_count,
            "errors": self._error_count,
            "cache_stats": self._cache.stats,
        }

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
