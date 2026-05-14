"""
BABSHARQII v40.0 — Continuous Learner
نظام التعلم المستمر — يبحث دورياً عن تحسينات ويُطبّقها

Features:
- Periodic deep research (every hour by default)
- Searches for: library updates, security patches, performance improvements
- Stores results in knowledge base
- Proposes modifications via LiveSelfModifier
- Converts Mamoun from reactive to proactive system

v40.0 Fusion Step 8: Continuous Learner
"""

import asyncio
import json
import logging
import time
import os
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from pathlib import Path

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.core.continuous_learner")


# ═══════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════

@dataclass
class LearningEntry:
    """سجل تعلّم — نتيجة بحث في مجال معيّن"""
    entry_id: str = ""
    area: str = ""
    query: str = ""
    findings: str = ""
    proposals: str = ""  # JSON list of modification proposals
    confidence: float = 0.0
    sources_count: int = 0
    created_at: float = 0.0

    def __post_init__(self):
        if not self.entry_id:
            import uuid
            self.entry_id = f"learn_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LearningCycleResult:
    """نتيجة دورة تعلّم كاملة"""
    cycle_id: str = ""
    areas_researched: int = 0
    total_findings: int = 0
    total_proposals: int = 0
    duration_seconds: float = 0.0
    timestamp: float = 0.0
    findings_by_area: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.cycle_id:
            import uuid
            self.cycle_id = f"cycle_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════
# Continuous Learner
# ═══════════════════════════════════════════════════════════════

class ContinuousLearner:
    """
    نظام التعلم المستمر — يبحث دورياً عن تحسينات ويُطبّقها

    Pipeline:
    1. learn_cycle() — Runs one full cycle: search → analyze → propose
    2. research_area() — Deep research on a specific area
    3. propose_from_findings() — Generate modification proposals
    4. Stores everything in knowledge base
    5. Optionally connects to LiveSelfModifier for auto-improvement
    """

    # Research areas to monitor periodically
    DEFAULT_AREAS = [
        "library_updates",      # تحديثات المكتبات
        "security_patches",     # تصحيحات أمنية
        "performance_tips",     # نصائح أداء
        "best_practices",       # أفضل الممارسات
        "api_changes",          # تغييرات API
    ]

    # Area-specific search queries (used for deep research)
    AREA_QUERIES = {
        "library_updates": [
            "latest Python library updates 2025",
            "FastAPI latest version changes",
            "Next.js 16 new features",
            "Pydantic v2 migration guide",
        ],
        "security_patches": [
            "Python security vulnerabilities 2025",
            "npm security advisories",
            "OWASP top 10 2025 updates",
            "FastAPI security best practices",
        ],
        "performance_tips": [
            "Python async performance optimization",
            "LLM inference optimization techniques",
            "React server components performance",
            "FastAPI performance tuning 2025",
        ],
        "best_practices": [
            "AI agent architecture patterns 2025",
            "RAG best practices production",
            "embedding models comparison 2025",
            "Mixture of Experts implementation",
        ],
        "api_changes": [
            "OpenAI API changes 2025",
            "GLM API updates",
            "DeepSeek API new features",
            "Gemini API v2 changes",
        ],
    }

    def __init__(self, llm_client=None, live_self_modifier=None, db_path: Optional[Path] = None):
        self._llm = llm_client
        self._lsm = live_self_modifier
        self.db_path = db_path or UNIFIED_DB_PATH
        self._knowledge_base: Dict[str, List[LearningEntry]] = {}  # area → entries
        self._learning_history: List[LearningCycleResult] = []
        self._interval_seconds = int(os.environ.get("MAMOUN_LEARNING_INTERVAL", "3600"))
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._total_cycles = 0
        self._initialized = False

    # ═══════════════════════════════════════════════════════════════
    # Initialization
    # ═══════════════════════════════════════════════════════════════

    def initialize(self) -> bool:
        """تهيئة — إنشاء الجداول وتحميل البيانات"""
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info(
                "ContinuousLearner initialized — knowledge areas=%d, history=%d",
                len(self._knowledge_base), len(self._learning_history)
            )
            return True
        except Exception as e:
            logger.error("ContinuousLearner init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cl_knowledge (
                    entry_id TEXT PRIMARY KEY,
                    area TEXT NOT NULL,
                    query TEXT DEFAULT '',
                    findings TEXT DEFAULT '',
                    proposals TEXT DEFAULT '',
                    confidence REAL DEFAULT 0,
                    sources_count INTEGER DEFAULT 0,
                    created_at REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cl_history (
                    cycle_id TEXT PRIMARY KEY,
                    areas_researched INTEGER DEFAULT 0,
                    total_findings INTEGER DEFAULT 0,
                    total_proposals INTEGER DEFAULT 0,
                    duration_seconds REAL DEFAULT 0,
                    timestamp REAL DEFAULT 0,
                    findings_by_area TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cl_state (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            # Load knowledge entries
            cur = conn.execute(
                "SELECT entry_id, area, query, findings, proposals, confidence, sources_count, created_at FROM cl_knowledge ORDER BY created_at DESC"
            )
            for row in cur.fetchall():
                entry = LearningEntry(
                    entry_id=row[0], area=row[1], query=row[2],
                    findings=row[3], proposals=row[4], confidence=row[5],
                    sources_count=row[6], created_at=row[7],
                )
                if entry.area not in self._knowledge_base:
                    self._knowledge_base[entry.area] = []
                # Keep only latest 20 entries per area
                if len(self._knowledge_base[entry.area]) < 20:
                    self._knowledge_base[entry.area].append(entry)

            # Load state
            cur = conn.execute("SELECT key, value FROM cl_state")
            for key, value in cur.fetchall():
                try:
                    if key == "total_cycles":
                        self._total_cycles = int(value)
                except (ValueError, TypeError):
                    pass
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════
    # Core: Learning Cycle
    # ═══════════════════════════════════════════════════════════════

    async def learn_cycle(self) -> LearningCycleResult:
        """
        دورة تعلّم كاملة: بحث → تحليل → اقتراح

        1. Research library updates
        2. Research security patches
        3. Research performance improvements
        4. Analyze findings with LLM
        5. Propose modifications
        6. Store in knowledge base
        """
        if not self._initialized:
            self.initialize()

        start_time = time.time()
        result = LearningCycleResult()
        total_findings = 0
        total_proposals = 0

        logger.info("Starting learning cycle...")

        for area in self.DEFAULT_AREAS:
            try:
                # Research the area
                research_result = await self.research_area(area)

                findings_count = research_result.get("findings_count", 0)
                proposals = research_result.get("proposals", [])

                total_findings += findings_count
                total_proposals += len(proposals)
                result.findings_by_area[area] = research_result

                # Store in knowledge base
                entry = LearningEntry(
                    area=area,
                    query=research_result.get("query", ""),
                    findings=research_result.get("summary", ""),
                    proposals=json.dumps(proposals, ensure_ascii=False),
                    confidence=research_result.get("confidence", 0.5),
                    sources_count=research_result.get("sources_count", 0),
                )

                if area not in self._knowledge_base:
                    self._knowledge_base[area] = []
                self._knowledge_base[area].insert(0, entry)
                # Keep only 20 per area
                self._knowledge_base[area] = self._knowledge_base[area][:20]
                self._persist_entry(entry)

                # If proposals exist, optionally report to LiveSelfModifier
                if proposals and self._lsm:
                    await self._report_proposals_to_lsm(area, proposals)

            except Exception as e:
                logger.error("Learning cycle error for area '%s': %s", area, e)
                result.findings_by_area[area] = {"error": str(e)[:200]}

        result.areas_researched = len(self.DEFAULT_AREAS)
        result.total_findings = total_findings
        result.total_proposals = total_proposals
        result.duration_seconds = time.time() - start_time

        self._learning_history.insert(0, result)
        self._learning_history = self._learning_history[:50]  # Keep last 50 cycles
        self._total_cycles += 1

        self._persist_cycle(result)
        self._persist_state("total_cycles", str(self._total_cycles))

        logger.info(
            "Learning cycle complete — areas=%d, findings=%d, proposals=%d, duration=%.1fs",
            result.areas_researched, total_findings, total_proposals, result.duration_seconds,
        )

        return result

    async def research_area(self, area: str) -> dict:
        """
        بحث عميق في مجال معيّن

        Uses DeepResearchEngine for thorough research, falls back to LLM analysis.
        """
        if not self._initialized:
            self.initialize()

        queries = self.AREA_QUERIES.get(area, [f"latest {area} developments 2025"])
        primary_query = queries[0]

        # Try DeepResearchEngine first
        try:
            from mamoun.core.deep_research_engine import DeepResearchEngine
            from mamoun.core.llm_client import get_llm_client
            llm = self._llm or get_llm_client()
            engine = DeepResearchEngine(llm_client=llm)
            report = await engine.research(primary_query, depth=2, verify=True)

            # Generate proposals from the research findings
            proposals = await self.propose_from_findings({
                "area": area,
                "query": primary_query,
                "summary": report.get("summary", ""),
                "analysis": report.get("analysis", ""),
                "facts": report.get("facts", []),
                "recommendations": report.get("recommendations", []),
                "sources_count": report.get("source_count", 0),
            })

            return {
                "area": area,
                "query": primary_query,
                "summary": report.get("summary", ""),
                "analysis": report.get("analysis", ""),
                "confidence": report.get("confidence_score", 0.5),
                "sources_count": report.get("source_count", 0),
                "findings_count": len(report.get("facts", [])),
                "proposals": proposals,
                "method": "deep_research",
            }

        except ImportError:
            logger.warning("DeepResearchEngine not available — using LLM-only research")
        except Exception as e:
            logger.warning("DeepResearch failed for '%s': %s — falling back to LLM", area, e)

        # Fallback: LLM-based research
        if self._llm:
            try:
                prompt = f"""أنت باحث تقني خبير. ابحث عن أحدث التطورات في:

المجال: {area}
الاستعلام: {primary_query}

قدّم:
1. ملخص لأهم التطورات (3-5 نقاط)
2. تأثيرها على نظام مأمون (نظام ذكاء اصطناعي بـ 5 أدمغة)
3. توصيات عملية للتحسين
4. درجة الثقة (0-1)

أجب بصيغة JSON:
{{
    "summary": "ملخص التطورات",
    "impact": "التأثير على مأمون",
    "recommendations": ["توصية 1", "توصية 2"],
    "confidence": 0.8
}}"""

                response = await self._llm.think(
                    prompt, model="glm-5.1", temperature=0.3,
                )

                raw = response if isinstance(response, str) else str(response)
                analysis = {}
                try:
                    start = raw.find('{')
                    end = raw.rfind('}') + 1
                    if start >= 0 and end > start:
                        analysis = json.loads(raw[start:end])
                except json.JSONDecodeError:
                    analysis = {"summary": raw[:500], "confidence": 0.5}

                proposals = await self.propose_from_findings({
                    "area": area,
                    "query": primary_query,
                    "summary": analysis.get("summary", ""),
                    "recommendations": analysis.get("recommendations", []),
                })

                return {
                    "area": area,
                    "query": primary_query,
                    "summary": analysis.get("summary", ""),
                    "analysis": analysis.get("impact", ""),
                    "confidence": analysis.get("confidence", 0.5),
                    "sources_count": 0,
                    "findings_count": len(analysis.get("recommendations", [])),
                    "proposals": proposals,
                    "method": "llm_only",
                }

            except Exception as e:
                logger.error("LLM research failed for '%s': %s", area, e)
                return {
                    "area": area, "query": primary_query,
                    "error": str(e)[:200], "proposals": [],
                    "findings_count": 0, "confidence": 0.0,
                }

        return {
            "area": area, "query": primary_query,
            "error": "No LLM client available", "proposals": [],
            "findings_count": 0, "confidence": 0.0,
        }

    async def propose_from_findings(self, findings: dict) -> list:
        """
        توليد اقتراحات تعديل من نتائج البحث

        Takes research findings and generates actionable proposals
        that could be applied to improve the system.
        """
        area = findings.get("area", "general")
        summary = findings.get("summary", "")
        recommendations = findings.get("recommendations", [])
        facts = findings.get("facts", [])

        if not summary and not recommendations and not facts:
            return []

        proposals = []

        # Convert recommendations to proposals
        for rec in recommendations[:5]:
            if isinstance(rec, str) and len(rec) > 5:
                proposals.append({
                    "area": area,
                    "type": "recommendation",
                    "description": rec,
                    "priority": "medium",
                    "source": "continuous_learner",
                })

        # If we have facts, convert key ones to proposals
        for fact in facts[:3]:
            if isinstance(fact, dict) and fact.get("claim"):
                proposals.append({
                    "area": area,
                    "type": "fact_insight",
                    "description": fact["claim"],
                    "confidence": fact.get("confidence", 0.5),
                    "priority": "low" if fact.get("confidence", 0) < 0.7 else "medium",
                    "source": "continuous_learner",
                })

        # Use LLM to generate more specific proposals
        if self._llm and summary:
            try:
                prompt = f"""بناءً على نتائج البحث التالية، اقترح تحسينات محددة لنظام مأمون:

المجال: {area}
النتائج: {summary[:1000]}

اقترح 2-3 تحسينات محددة وقابلة للتنفيذ. أجب بصيغة JSON:
[
    {{
        "area": "{area}",
        "type": "improvement",
        "description": "وصف التحسين",
        "priority": "high|medium|low",
        "target_file": "الملف المستهدف إن عُرف"
    }}
]"""

                response = await self._llm.think(
                    prompt, model="glm-5.1", temperature=0.3,
                )

                raw = response if isinstance(response, str) else str(response)
                try:
                    start = raw.find('[')
                    end = raw.rfind(']') + 1
                    if start >= 0 and end > start:
                        parsed = json.loads(raw[start:end])
                        if isinstance(parsed, list):
                            for p in parsed[:3]:
                                p["source"] = "continuous_learner_llm"
                                proposals.append(p)
                except json.JSONDecodeError:
                    pass

            except Exception as e:
                logger.warning("LLM proposal generation failed: %s", e)

        return proposals

    # ═══════════════════════════════════════════════════════════════
    # LSM Integration
    # ═══════════════════════════════════════════════════════════════

    async def _report_proposals_to_lsm(self, area: str, proposals: list):
        """الإبلاغ عن اقتراحات التعلم لـ LiveSelfModifier"""
        if not self._lsm:
            return

        for proposal in proposals[:3]:  # Top 3 per area
            try:
                description = proposal.get("description", "")
                priority = proposal.get("priority", "medium")
                target = proposal.get("target_file", area)

                severity = "high" if priority == "high" else "medium" if priority == "medium" else "low"
                self._lsm.report_weakness(
                    area=target,
                    description=f"[ContinuousLearner] {description}",
                    severity=severity,
                    source="continuous_learner",
                )
            except Exception as e:
                logger.warning("Failed to report proposal to LSM: %s", e)

    # ═══════════════════════════════════════════════════════════════
    # Background Loop
    # ═══════════════════════════════════════════════════════════════

    async def start(self):
        """بدء حلقة التعلم المستمر في الخلفية"""
        if self._running:
            return

        if not self._initialized:
            self.initialize()

        self._running = True
        self._task = asyncio.create_task(self._learning_loop())
        logger.info("ContinuousLearner started — interval=%d seconds", self._interval_seconds)

    async def stop(self):
        """إيقاف حلقة التعلم"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ContinuousLearner stopped — total_cycles=%d", self._total_cycles)

    async def _learning_loop(self):
        """حلقة التعلم الدوري"""
        while self._running:
            try:
                await self.learn_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Learning loop error: %s", e)

            # Wait for the configured interval
            try:
                await asyncio.sleep(self._interval_seconds)
            except asyncio.CancelledError:
                break

    # ═══════════════════════════════════════════════════════════════
    # Accessors
    # ═══════════════════════════════════════════════════════════════

    def get_knowledge_base(self) -> dict:
        """Return current knowledge base"""
        return {
            area: [e.to_dict() for e in entries]
            for area, entries in self._knowledge_base.items()
        }

    def get_status(self) -> dict:
        """Return learner status"""
        return {
            "running": self._running,
            "initialized": self._initialized,
            "interval_seconds": self._interval_seconds,
            "total_cycles": self._total_cycles,
            "knowledge_areas": list(self._knowledge_base.keys()),
            "knowledge_entries": sum(len(v) for v in self._knowledge_base.values()),
            "last_cycle": self._learning_history[0].to_dict() if self._learning_history else None,
            "has_llm": self._llm is not None,
            "has_lsm": self._lsm is not None,
        }

    # ═══════════════════════════════════════════════════════════════
    # Persistence
    # ═══════════════════════════════════════════════════════════════

    def _persist_entry(self, entry: LearningEntry):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO cl_knowledge
                (entry_id, area, query, findings, proposals, confidence, sources_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.entry_id, entry.area, entry.query,
                entry.findings, entry.proposals, entry.confidence,
                entry.sources_count, entry.created_at,
            ))
            conn.commit()
        finally:
            conn.close()

    def _persist_cycle(self, cycle: LearningCycleResult):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO cl_history
                (cycle_id, areas_researched, total_findings, total_proposals,
                 duration_seconds, timestamp, findings_by_area)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                cycle.cycle_id, cycle.areas_researched, cycle.total_findings,
                cycle.total_proposals, cycle.duration_seconds, cycle.timestamp,
                json.dumps(cycle.findings_by_area, ensure_ascii=False, default=str)[:5000],
            ))
            conn.commit()
        finally:
            conn.close()

    def _persist_state(self, key: str, value: str):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO cl_state (key, value) VALUES (?, ?)",
                (key, value),
            )
            conn.commit()
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

_continuous_learner: Optional[ContinuousLearner] = None


def get_continuous_learner() -> ContinuousLearner:
    """Get the global ContinuousLearner instance."""
    global _continuous_learner
    if _continuous_learner is None:
        _continuous_learner = ContinuousLearner()
    return _continuous_learner
