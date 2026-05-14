"""
BABSHARQII v30.0 — Research Agent
وكيل الأبحاث — يبحث عن تطبيقات عملية لقدرات AGI المفقودة

Strategies:
  - Daily: Quick scan of recent developments
  - Weekly: Deep dive into specific topics
  - Monthly: Comprehensive landscape analysis
"""

import os
import time
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from enum import Enum
from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.research_agent")


class ResearchStrategy(str, Enum):
    """استراتيجيات البحث — Research strategies"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class ResearchFinding:
    """نتيجة بحثية — A research finding"""
    id: str = ""
    title: str = ""
    summary: str = ""
    source: str = ""
    url: str = ""
    relevance: float = 0.0
    actionable: bool = False
    strategy: str = ResearchStrategy.DAILY.value
    gap_addressed: str = ""
    created_at: float = 0.0

    def __post_init__(self):
        if not self.id:
            import hashlib
            self.id = f"res_{hashlib.md5(f'{self.title}{time.time()}'.encode()).hexdigest()[:12]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ResearchReport:
    """تقرير بحثي — A research report"""
    id: str = ""
    strategy: str = ResearchStrategy.DAILY.value
    findings: List[Dict] = field(default_factory=list)
    gaps_identified: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    created_at: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


class ResearchAgent:
    """
    وكيل الأبحاث — Searches for practical applications of missing AGI capabilities
    
    Uses three strategies:
      DAILY: Quick scan — looks at recent papers, GitHub trending
      WEEKLY: Deep dive — focused analysis on specific capability gaps
      MONTHLY: Comprehensive — full landscape review
    """

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or UNIFIED_DB_PATH
        self._findings: List[ResearchFinding] = []
        self._initialized = False

    def initialize(self) -> bool:
        """تهيئة وكيل الأبحاث"""
        try:
            self._ensure_schema()
            self._initialized = True
            logger.info("ResearchAgent initialized")
            return True
        except Exception as e:
            logger.error("ResearchAgent init failed: %s", e)
            return False

    def _ensure_schema(self):
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_db_connection(self._db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS ra_findings (
                id TEXT PRIMARY KEY, title TEXT, summary TEXT, source TEXT,
                url TEXT, relevance REAL, actionable INTEGER, strategy TEXT,
                gap_addressed TEXT, created_at REAL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS ra_reports (
                id TEXT PRIMARY KEY, strategy TEXT, findings TEXT,
                gaps_identified TEXT, recommendations TEXT, created_at REAL)""")
            conn.commit()
        finally:
            conn.close()

    def research_daily(self) -> ResearchReport:
        """
        بحث يومي — Daily quick scan for recent developments
        
        In production, this would call web search APIs.
        For now, it returns a structured report with mock findings
        based on known AGI capability gaps.
        """
        findings = self._generate_daily_findings()

        report = ResearchReport(
            strategy=ResearchStrategy.DAILY.value,
            findings=[f.to_dict() for f in findings],
            gaps_identified=self._extract_gaps(findings),
            recommendations=self._generate_recommendations(findings),
        )

        self._persist_report(report)
        self._findings.extend(findings)

        return report

    def research_weekly(self, focus_area: str = "") -> ResearchReport:
        """
        بحث أسبوعي — Weekly deep dive into specific topics
        """
        findings = self._generate_weekly_findings(focus_area)

        report = ResearchReport(
            strategy=ResearchStrategy.WEEKLY.value,
            findings=[f.to_dict() for f in findings],
            gaps_identified=self._extract_gaps(findings),
            recommendations=self._generate_recommendations(findings),
        )

        self._persist_report(report)
        self._findings.extend(findings)

        return report

    def research_monthly(self) -> ResearchReport:
        """
        بحث شهري — Monthly comprehensive landscape analysis
        """
        findings = self._generate_monthly_findings()

        report = ResearchReport(
            strategy=ResearchStrategy.MONTHLY.value,
            findings=[f.to_dict() for f in findings],
            gaps_identified=self._extract_gaps(findings),
            recommendations=self._generate_recommendations(findings),
        )

        self._persist_report(report)
        self._findings.extend(findings)

        return report

    def _generate_daily_findings(self) -> List[ResearchFinding]:
        """Generate daily research findings based on known AGI gaps"""
        return [
            ResearchFinding(
                title="Chain-of-Thought prompting improves reasoning",
                summary="Recent research shows CoT prompting significantly improves multi-step reasoning in LLMs",
                source="arxiv",
                url="https://arxiv.org/abs/...",
                relevance=0.8,
                actionable=True,
                strategy=ResearchStrategy.DAILY.value,
                gap_addressed="fluid_reasoning",
            ),
            ResearchFinding(
                title="EWC prevents catastrophic forgetting in continual learning",
                summary="Elastic Weight Consolidation technique shows promise for lifelong learning systems",
                source="arxiv",
                url="https://arxiv.org/abs/...",
                relevance=0.9,
                actionable=True,
                strategy=ResearchStrategy.DAILY.value,
                gap_addressed="continual_learning",
            ),
        ]

    def _generate_weekly_findings(self, focus_area: str = "") -> List[ResearchFinding]:
        """Generate weekly deep-dive findings"""
        area = focus_area or "general_agi"
        return [
            ResearchFinding(
                title=f"Weekly deep dive: {area} improvement strategies",
                summary=f"Comprehensive analysis of current approaches to improving {area} capabilities",
                source="internal_analysis",
                relevance=0.85,
                actionable=True,
                strategy=ResearchStrategy.WEEKLY.value,
                gap_addressed=area,
            ),
        ]

    def _generate_monthly_findings(self) -> List[ResearchFinding]:
        """Generate monthly comprehensive findings"""
        return [
            ResearchFinding(
                title="Monthly AGI landscape review",
                summary="Comprehensive review of AGI research landscape, key developments and emerging patterns",
                source="aggregated",
                relevance=0.9,
                actionable=True,
                strategy=ResearchStrategy.MONTHLY.value,
                gap_addressed="general_agi",
            ),
        ]

    def _extract_gaps(self, findings: List[ResearchFinding]) -> List[str]:
        gaps = set()
        for f in findings:
            if f.gap_addressed:
                gaps.add(f.gap_addressed)
        return list(gaps)

    def _generate_recommendations(self, findings: List[ResearchFinding]) -> List[str]:
        recs = []
        for f in findings:
            if f.actionable and f.relevance >= 0.7:
                recs.append(f"Consider implementing: {f.title} (relevance: {f.relevance:.1f})")
        return recs

    def _persist_report(self, report: ResearchReport):
        try:
            conn = get_db_connection(self._db_path)
            try:
                import hashlib
                report_id = report.id or f"rpt_{hashlib.md5(f'{report.strategy}{time.time()}'.encode()).hexdigest()[:12]}"
                conn.execute(
                    "INSERT OR REPLACE INTO ra_reports "
                    "(id, strategy, findings, gaps_identified, recommendations, created_at) "
                    "VALUES (?,?,?,?,?,?)",
                    (report_id, report.strategy,
                     json.dumps(report.findings), json.dumps(report.gaps_identified),
                     json.dumps(report.recommendations), report.created_at),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Failed to persist report: %s", e)

    def get_findings(self, limit: int = 50) -> List[dict]:
        with self._db_path:
            pass
        return [f.to_dict() for f in self._findings[-limit:]]

    def get_status(self) -> dict:
        return {
            "initialized": self._initialized,
            "total_findings": len(self._findings),
        }


# Singleton
research_agent = ResearchAgent()
