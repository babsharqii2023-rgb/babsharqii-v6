"""
Research Monitor — مراقب الأبحاث العلمية المستمر
v16.0

Based on:
- "Paper Circle: An Open-source Multi-agent Research Discovery and Analysis System" (April 2026)
- "AI-Researcher: Autonomous Scientific Innovation" (github.com/hkuds/ai-researcher)

Capabilities:
1. Periodically search for new papers in relevant domains
2. Classify papers by relevance and trustworthiness
3. Extract actionable insights for Mamoun's improvement
4. Track specific researchers and conferences
5. Alert when breakthrough papers are published
6. Build an Epistemic Trust Network for source credibility

Domains to monitor:
- Self-improving AI agents (DGM, Hyperagents, SICA)
- Metacognition and self-awareness in AI
- Swarm intelligence and multi-agent systems
- Agentic UI (A2UI, AG-UI)
- Preference learning (PAHF, RLHF)
- Autonomous software engineering (SWE-agent, OpenHands)
"""

import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path
from enum import Enum

logger = logging.getLogger("mamoun.research_monitor.monitor")


class TrustLevel(str, Enum):
    UNVERIFIED = "unverified"    # لم يتم التحقق
    LOW = "low"                  # مصدر غير معروف
    MEDIUM = "medium"            # مؤتمر/مجلة معروفة
    HIGH = "high"                # مؤتمر top-tier (ICLR, ICML, NeurIPS, AAAI)
    VERY_HIGH = "very_high"      # ورقة من شركة بحثية كبرى مع مراجعة


class EpistemicTrustNetwork:
    """
    شبكة الثقة المعرفية — novel contribution of v16.0
    
    Classifies sources by trustworthiness:
    - Top-tier conferences: ICLR, ICML, NeurIPS, AAAI, IJCAI
    - Major research labs: Meta AI, Google DeepMind, OpenAI, Anthropic
    - Peer-reviewed journals: Nature, Science, JMLR, TMLR
    - Pre-print servers: arXiv (medium trust until peer-reviewed)
    - Blog posts / tutorials: Low trust
    - Random websites: Very low trust
    """
    
    TOP_TIER_VENUES = {
        "iclr", "icml", "neurips", "aaai", "ijcai",
        "nature", "science", "jmlr", "tmlr",
    }
    
    MAJOR_LABS = {
        "meta ai", "google deepmind", "openai", "anthropic",
        "microsoft research", "sakana ai", "deepseek",
    }
    
    TRUST_RULES = {
        "top_tier_venue": TrustLevel.VERY_HIGH,
        "major_lab": TrustLevel.HIGH,
        "arxiv": TrustLevel.MEDIUM,
        "peer_reviewed": TrustLevel.HIGH,
        "blog": TrustLevel.LOW,
        "social_media": TrustLevel.UNVERIFIED,
        "unknown": TrustLevel.UNVERIFIED,
    }
    
    def classify_source(self, paper: dict) -> TrustLevel:
        """Classify a paper's source trustworthiness."""
        venue = paper.get("venue", "").lower()
        authors = paper.get("authors", "").lower()
        url = paper.get("url", "").lower()
        
        # Top-tier venue
        for v in self.TOP_TIER_VENUES:
            if v in venue:
                return TrustLevel.VERY_HIGH
        
        # Major lab
        for lab in self.MAJOR_LABS:
            if lab in authors:
                return TrustLevel.HIGH
        
        # arXiv
        if "arxiv" in url:
            return TrustLevel.MEDIUM
        
        # Peer-reviewed
        if paper.get("peer_reviewed"):
            return TrustLevel.HIGH
        
        # Blog
        if "blog" in url or "medium" in url:
            return TrustLevel.LOW
        
        return TrustLevel.UNVERIFIED


class ResearchPaper:
    """Represents a discovered research paper."""
    
    def __init__(self, title: str, url: str, snippet: str = "", source_data: dict = None):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source_data = source_data or {}
        self.discovered_at = datetime.now(timezone.utc).isoformat()
        self.trust_level: TrustLevel = TrustLevel.UNVERIFIED
        self.relevance_score: float = 0.0
        self.actionable_insights: list[str] = []
        self.applied: bool = False
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "discovered_at": self.discovered_at,
            "trust_level": self.trust_level.value if isinstance(self.trust_level, TrustLevel) else self.trust_level,
            "relevance_score": self.relevance_score,
            "actionable_insights": self.actionable_insights,
            "applied": self.applied,
        }


class ResearchMonitor:
    """
    Monitors research landscape for relevant new papers and insights.
    """
    
    MONITORING_QUERIES = [
        "self-improving AI agent 2026",
        "DGM Hyperagents metacognitive self-modification",
        "A2UI agent dynamic UI generation",
        "PAHF personalized agents human feedback",
        "autonomous software engineering agent 2026",
        "swarm intelligence emergent collective AI",
        "artificial metacognition self-awareness AI",
        "AG-UI agent user interaction protocol",
    ]
    
    def __init__(self, data_dir: str = "backend/data/research_monitor"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.discovered_path = self.data_dir / "discovered_papers.jsonl"
        self.trust_network = EpistemicTrustNetwork()
        self.discovered_papers: list[ResearchPaper] = self._load_discovered()
        self.last_scan_time: Optional[str] = None
    
    def _load_discovered(self) -> list:
        papers = []
        if self.discovered_path.exists():
            with open(self.discovered_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            paper = ResearchPaper(
                                title=data["title"],
                                url=data["url"],
                                snippet=data.get("snippet", ""),
                                source_data=data.get("source_data", {}),
                            )
                            paper.trust_level = TrustLevel(data.get("trust_level", "unverified"))
                            paper.relevance_score = data.get("relevance_score", 0)
                            paper.discovered_at = data.get("discovered_at", "")
                            papers.append(paper)
                        except Exception:
                            continue
        return papers
    
    def process_search_results(self, results: list[dict]) -> list[ResearchPaper]:
        """
        Process search results, classify trust, calculate relevance.
        """
        new_papers = []
        
        for result in results:
            title = result.get("name", "")
            url = result.get("url", "")
            snippet = result.get("snippet", "")
            
            if not title or not url:
                continue
            
            # Skip duplicates
            if any(p.url == url for p in self.discovered_papers):
                continue
            
            paper = ResearchPaper(title=title, url=url, snippet=snippet, source_data=result)
            
            # Classify trust
            paper.trust_level = self.trust_network.classify_source({
                "venue": "",
                "authors": "",
                "url": url,
            })
            
            # Calculate relevance
            paper.relevance_score = self._calculate_relevance(paper)
            
            # Extract actionable insights
            paper.actionable_insights = self._extract_insights(paper)
            
            # Save
            with open(self.discovered_path, "a") as f:
                f.write(json.dumps(paper.to_dict(), ensure_ascii=False) + "\n")
            
            self.discovered_papers.append(paper)
            new_papers.append(paper)
        
        self.last_scan_time = datetime.now(timezone.utc).isoformat()
        return new_papers
    
    def _calculate_relevance(self, paper: ResearchPaper) -> float:
        """Calculate how relevant a paper is to Mamoun's improvement."""
        keywords = [
            "self-improving", "hyperagent", "DGM", "metacognitive",
            "A2UI", "agentic UI", "PAHF", "preference learning",
            "swarm", "self-awareness", "autonomous", "self-evolving",
            "SWE-agent", "code agent", "evolution",
        ]
        
        text = (paper.title + " " + paper.snippet).lower()
        matches = sum(1 for kw in keywords if kw.lower() in text)
        relevance = matches / len(keywords)
        
        # Boost by trust level
        trust_boost = {
            TrustLevel.VERY_HIGH: 1.3,
            TrustLevel.HIGH: 1.2,
            TrustLevel.MEDIUM: 1.0,
            TrustLevel.LOW: 0.7,
            TrustLevel.UNVERIFIED: 0.5,
        }
        relevance *= trust_boost.get(paper.trust_level, 1.0)
        
        return min(1.0, relevance)
    
    def _extract_insights(self, paper: ResearchPaper) -> list[str]:
        """Extract actionable insights from a paper's snippet."""
        insights = []
        snippet_lower = paper.snippet.lower()
        
        insight_patterns = [
            ("self-referential", "يمكن تعديل آلية التحسين نفسها — تطبيق Hyperagent"),
            ("cross-domain transfer", "نقل المهارات بين المجالات — تطبيق Evolution Archive"),
            ("dynamic UI", "واجهات ديناميكية — تطبيق A2UI"),
            ("preference learning", "تعلم التفضيلات — تطبيق PAHF"),
            ("collective memory", "ذاكرة جماعية — تطبيق Swarm Collective Memory"),
            ("metacognitive", "مراقبة ميتا-معرفية — تطبيق Awareness Mirror"),
        ]
        
        for pattern, insight in insight_patterns:
            if pattern.lower() in snippet_lower:
                insights.append(insight)
        
        return insights
    
    def get_high_relevance_papers(self, min_relevance: float = 0.3, limit: int = 10) -> list[dict]:
        """Get papers with high relevance scores."""
        relevant = [p for p in self.discovered_papers if p.relevance_score >= min_relevance]
        relevant.sort(key=lambda p: p.relevance_score, reverse=True)
        return [p.to_dict() for p in relevant[:limit]]
    
    def get_status(self) -> dict:
        trust_distribution = {}
        for paper in self.discovered_papers:
            level = paper.trust_level.value if isinstance(paper.trust_level, TrustLevel) else paper.trust_level
            trust_distribution[level] = trust_distribution.get(level, 0) + 1
        
        return {
            "total_papers_discovered": len(self.discovered_papers),
            "high_relevance_count": sum(1 for p in self.discovered_papers if p.relevance_score >= 0.3),
            "trust_distribution": trust_distribution,
            "last_scan_time": self.last_scan_time,
            "monitoring_queries": self.MONITORING_QUERIES,
        }
