"""
BABSHARQII v13.0 — Trusted Research Fetcher
جالب الأبحاث الموثوقة — يجلب الأبحاث من مصادر موثوقة

Sources:
- ArXiv API (papers)
- GitHub Trending (repos)
- Papers with Code (benchmarks)

Feature Flag: MAMOUN_SELF_PROGRAMMING (default: false)
"""

import os
import time
import uuid
import logging
import asyncio
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum

from mamoun.evolution.self_programming_loop import SELF_PROGRAMMING_ENABLED, _is_self_programming_enabled

logger = logging.getLogger(__name__)

# Research focus areas for مأمون
RESEARCH_TOPICS = [
    "agentic AI frameworks",
    "Arabic NLP",
    "self-improving systems",
    "time-bounded authorization",
    "digital organism architecture",
    "multimodal reasoning",
    "safe AI alignment",
    "evolutionary computation",
]


@dataclass
class ResearchPaper:
    """ورقة بحثية."""
    paper_id: str = ""
    title: str = ""
    abstract: str = ""
    authors: list = field(default_factory=list)
    url: str = ""
    source: str = ""  # arxiv, github, papers_with_code
    published_date: str = ""
    relevance_score: float = 0.0
    topics: list = field(default_factory=list)

    def __post_init__(self):
        if not self.paper_id:
            self.paper_id = f"paper_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TrendingRepo:
    """مستودع رائج."""
    repo_id: str = ""
    name: str = ""
    description: str = ""
    url: str = ""
    stars: int = 0
    language: str = ""
    topics: list = field(default_factory=list)
    relevance_score: float = 0.0

    def __post_init__(self):
        if not self.repo_id:
            self.repo_id = f"repo_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return asdict(self)


class TrustedResearchFetcher:
    """
    جالب الأبحاث الموثوقة — يجلب أبحاثاً من APIs محددة.

    Sources:
    - ArXiv API: For academic papers
    - GitHub API: For trending repositories
    - Papers with Code: For benchmark results

    Usage:
        fetcher = TrustedResearchFetcher()
        results = await fetcher.fetch_all()
        # results contains papers and repos from trusted sources
    """

    def __init__(self):
        self._papers: list[ResearchPaper] = []
        self._repos: list[TrendingRepo] = []
        self._fetch_count = 0

    async def fetch_all(self) -> list[dict]:
        """
        جلب جميع المصادر — Fetch from all trusted sources.

        Returns:
            List of research items (papers and repos)
        """
        if not _is_self_programming_enabled():
            return []

        self._fetch_count += 1
        results = []

        # Fetch from ArXiv
        try:
            papers = await self.fetch_arxiv()
            results.extend([{"type": "paper", **p.to_dict()} for p in papers])
            self._papers.extend(papers)
        except Exception as e:
            logger.error(f"ArXiv fetch error: {e}")

        # Fetch from GitHub
        try:
            repos = await self.fetch_github_trending()
            results.extend([{"type": "repo", **r.to_dict()} for r in repos])
            self._repos.extend(repos)
        except Exception as e:
            logger.error(f"GitHub fetch error: {e}")

        # Fetch from Papers with Code
        try:
            pwc_papers = await self.fetch_papers_with_code()
            results.extend([{"type": "paper", **p.to_dict()} for p in pwc_papers])
            self._papers.extend(pwc_papers)
        except Exception as e:
            logger.error(f"Papers with Code fetch error: {e}")

        # If no real results from any source, return NO_RESULTS status
        if not results:
            logger.info("TrustedResearchFetcher: No real results from any source — returning NO_RESULTS")
            return [{"type": "NO_RESULTS", "message": "لم أجد نتائج حقيقية من أي مصدر — لا أريد تضليلك ببيانات مزيفة"}]

        logger.info(f"TrustedResearchFetcher: Fetched {len(results)} items")
        return results

    async def fetch_arxiv(self, max_results: int = 10) -> list[ResearchPaper]:
        """جلب أبحاث من ArXiv."""
        papers = []

        try:
            import httpx

            for topic in RESEARCH_TOPICS[:3]:  # Limit to avoid API abuse
                async with httpx.AsyncClient(timeout=15.0) as client:
                    url = "http://export.arxiv.org/api/query"
                    params = {
                        "search_query": f"all:{topic}",
                        "start": 0,
                        "max_results": max_results // 3,
                        "sortBy": "submittedDate",
                        "sortOrder": "descending",
                    }
                    resp = await client.get(url, params=params)

                    if resp.status_code == 200:
                        # Parse Atom XML response (simplified)
                        text = resp.text
                        # Extract entries (basic parsing)
                        entries = text.split("<entry>")[1:]
                        for entry in entries[:3]:
                            title = self._extract_xml(entry, "title")
                            abstract = self._extract_xml(entry, "summary")
                            paper_url = self._extract_xml(entry, "id")

                            papers.append(ResearchPaper(
                                title=title[:200],
                                abstract=abstract[:500],
                                url=paper_url,
                                source="arxiv",
                                topics=[topic],
                                relevance_score=0.7,
                            ))

        except ImportError:
            logger.warning("httpx not available for ArXiv fetch")
        except Exception as e:
            logger.warning(f"ArXiv API error: {e}")

        # No simulated/fake data — return empty if no real results
        if not papers:
            logger.info("ArXiv returned no real results — refusing to generate fake data")

        return papers

    async def fetch_github_trending(self) -> list[TrendingRepo]:
        """جلب مستودعات رائجة من GitHub."""
        repos = []

        try:
            import httpx

            headers = {"Accept": "application/vnd.github.v3+json"}
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Search for trending AI repos
                for topic in ["agentic-ai", "arabic-nlp", "self-evolving"]:
                    url = f"https://api.github.com/search/repositories?q=topic:{topic}&sort=stars&order=desc&per_page=3"
                    resp = await client.get(url, headers=headers)

                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data.get("items", [])[:3]:
                            repos.append(TrendingRepo(
                                name=item.get("full_name", ""),
                                description=item.get("description", "")[:200],
                                url=item.get("html_url", ""),
                                stars=item.get("stargazers_count", 0),
                                language=item.get("language", ""),
                                topics=item.get("topics", []),
                                relevance_score=0.6,
                            ))

        except ImportError:
            logger.warning("httpx not available for GitHub fetch")
        except Exception as e:
            logger.warning(f"GitHub API error: {e}")

        # No simulated/fake data — return empty if no real results
        if not repos:
            logger.info("GitHub returned no real results — refusing to generate fake data")

        return repos

    async def fetch_papers_with_code(self, max_results: int = 5) -> list[ResearchPaper]:
        """جلب أبحاث من Papers with Code."""
        papers = []

        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                url = "https://paperswithcode.com/api/v1/papers/"
                params = {"ordering": "-published", "page_size": max_results}
                resp = await client.get(url, params=params)

                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("results", []):
                        papers.append(ResearchPaper(
                            title=item.get("title", "")[:200],
                            abstract=item.get("abstract", "")[:500],
                            url=item.get("url", ""),
                            source="papers_with_code",
                            published_date=item.get("published", ""),
                            relevance_score=0.65,
                        ))

        except ImportError:
            logger.warning("httpx not available for Papers with Code fetch")
        except Exception as e:
            logger.warning(f"Papers with Code API error: {e}")

        # No simulated/fake data — return empty if no real results
        if not papers:
            logger.info("Papers with Code returned no real results — refusing to generate fake data")

        return papers

    def _extract_xml(self, text: str, tag: str) -> str:
        """استخراج نص من XML."""
        start = text.find(f"<{tag}>")
        end = text.find(f"</{tag}>")
        if start >= 0 and end > start:
            return text[start + len(tag) + 2:end].strip()
        return ""



    def get_status(self) -> dict:
        """حالة جالب الأبحاث."""
        return {
            "enabled": SELF_PROGRAMMING_ENABLED,
            "fetch_count": self._fetch_count,
            "papers_fetched": len(self._papers),
            "repos_fetched": len(self._repos),
            "topics": RESEARCH_TOPICS,
        }

    async def shutdown(self):
        """إيقاف الجالب — يتوافق مع القانون 5."""
        logger.info("TrustedResearchFetcher: Shutdown complete (Law 5 compliant)")
