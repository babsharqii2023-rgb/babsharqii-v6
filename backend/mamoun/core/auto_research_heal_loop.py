"""
BABSHARQII v40.0 — Auto Research-Heal Loop
حلقة البحث والشفاء التلقائية — تربط DeepResearch بـ SelfHealing تلقائياً

v40.0 Fusion Step 3: Connect Auto-Research-Heal Automatically
When a health issue is detected:
  1. DeepResearch searches for solutions
  2. SelfHealing applies the best solution
  3. Verification confirms the fix

This loop runs automatically when MAMOUN_AUTO_RESEARCH_HEAL=true
(default: true, since this is a core fusion feature)

Architecture:
  ┌──────────────────────────────────────────────────────────┐
  │              AUTO RESEARCH-HEAL LOOP                       │
  │                                                            │
  │  1. LISTEN    — يسمع إشارات NeuralBus (error_detected)   │
  │  2. RESEARCH  — يبحث عن حلول عبر DeepResearchEngine      │
  │  3. ANALYZE   — يحلل الحلول ويختار الأنسب               │
  │  4. HEAL      — يطبق الحل عبر SelfHealingEngine          │
  │  5. VERIFY    — يتحقق من نجاح الإصلاح                   │
  │  6. LEARN     — يتعلّم للمرات القادمة                    │
  └──────────────────────────────────────────────────────────┘
"""

import asyncio
import time
import logging
import os
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from pathlib import Path

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.auto_research_heal")


# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

AUTO_RESEARCH_HEAL_ENABLED = os.environ.get(
    "MAMOUN_AUTO_RESEARCH_HEAL", "true"
).lower() in ("true", "1", "yes")

CHECK_INTERVAL_SECONDS = int(os.environ.get(
    "MAMOUN_AUTO_RESEARCH_HEAL_INTERVAL", "60"
))

MAX_CONCURRENT_HEALS = int(os.environ.get(
    "MAMOUN_MAX_CONCURRENT_HEALS", "3"
))


@dataclass
class ResearchHealCycle:
    """دورة بحث-شفاء واحدة"""
    cycle_id: str = ""
    issue_component: str = ""
    issue_description: str = ""
    research_query: str = ""
    research_findings: str = ""
    healing_action: str = ""
    healing_success: bool = False
    verification_result: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "cycle_id": self.cycle_id,
            "issue_component": self.issue_component,
            "issue_description": self.issue_description[:200],
            "research_query": self.research_query[:200],
            "healing_action": self.healing_action,
            "healing_success": self.healing_success,
            "verification_result": self.verification_result[:200],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": round(self.duration_ms, 1),
        }


class AutoResearchHealLoop:
    """
    حلقة البحث والشفاء التلقائية

    When a health issue is detected by SelfHealingEngine,
    this loop automatically:
    1. Researches the issue using DeepResearchEngine
    2. Analyzes findings and selects best solution
    3. Applies the solution through SelfHealingEngine
    4. Verifies the fix worked
    5. Learns from the experience
    """

    def __init__(self, neural_bus=None, db_path: Optional[Path] = None):
        self._neural_bus = neural_bus
        self.db_path = db_path or UNIFIED_DB_PATH
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._cycle_count = 0
        self._success_count = 0
        self._failure_count = 0
        self._history: List[ResearchHealCycle] = []
        self._active_cycles: Dict[str, ResearchHealCycle] = {}
        self._initialized = False
        self._llm_client = None
        self._self_healing = None
        self._deep_research = None

    def initialize(self) -> bool:
        """تهيئة الحلقة"""
        try:
            self._ensure_schema()
            self._load_state()

            # Connect to SelfHealingEngine
            try:
                from mamoun.core.self_healing import SelfHealingEngine
                self._self_healing = SelfHealingEngine(
                    neural_bus=self._neural_bus, db_path=self.db_path
                )
                if not self._self_healing._initialized:
                    self._self_healing.initialize()
            except Exception as e:
                logger.warning("Could not connect to SelfHealingEngine: %s", e)

            # Connect to DeepResearchEngine
            try:
                from mamoun.core.deep_research_engine import DeepResearchEngine
                self._deep_research = DeepResearchEngine()
            except Exception as e:
                logger.warning("Could not connect to DeepResearchEngine: %s", e)

            # Connect to LLM client
            try:
                from mamoun.core.llm_client import get_llm_client
                self._llm_client = get_llm_client()
            except Exception as e:
                logger.warning("Could not connect to LLM client: %s", e)

            # Subscribe to NeuralBus signals
            if self._neural_bus:
                self._neural_bus.subscribe(
                    "error_detected",
                    self._on_error_signal,
                )
                self._neural_bus.subscribe(
                    "stress_spike",
                    self._on_stress_signal,
                )

            self._initialized = True
            logger.info(
                "AutoResearchHealLoop initialized — self_healing=%s, deep_research=%s, llm=%s",
                self._self_healing is not None,
                self._deep_research is not None,
                self._llm_client is not None,
            )
            return True
        except Exception as e:
            logger.error("AutoResearchHealLoop init failed: %s", e)
            return False

    def _on_error_signal(self, signal):
        """يتفاعل مع إشارات الخطأ — يبدأ دورة بحث-شفاء تلقائياً"""
        try:
            payload = getattr(signal, 'data', {}) or {}
            component = payload.get('component', '')
            description = payload.get('description', '')
            severity = payload.get('severity', 'medium')

            if severity in ('high', 'critical') and component:
                logger.info(
                    "Auto-Research-Heal triggered by error signal: %s (%s)",
                    component, severity,
                )
                # Schedule a research-heal cycle
                asyncio.create_task(
                    self.run_cycle(component, description, severity)
                )
        except Exception as e:
            logger.error("Error in signal handler: %s", e)

    def _on_stress_signal(self, signal):
        """يتفاعل مع إشارات الضغط — يبدأ بحث عن حل"""
        try:
            payload = getattr(signal, 'data', {}) or {}
            component = payload.get('component', 'system')
            logger.info("Auto-Research-Heal triggered by stress: %s", component)
            asyncio.create_task(
                self.run_cycle(component, "ضغط نظام مكتشف", "medium")
            )
        except Exception as e:
            logger.error("Error in stress handler: %s", e)

    async def run_cycle(
        self, component: str, description: str, severity: str = "medium"
    ) -> ResearchHealCycle:
        """
        تشغيل دورة بحث-شفاء واحدة

        1. Research the issue
        2. Analyze findings
        3. Apply healing
        4. Verify result
        """
        self._cycle_count += 1
        cycle_id = f"arh_{self._cycle_count}_{int(time.time())}"

        cycle = ResearchHealCycle(
            cycle_id=cycle_id,
            issue_component=component,
            issue_description=description,
            started_at=time.time(),
        )

        self._active_cycles[cycle_id] = cycle
        logger.info("Starting Auto-Research-Heal cycle %s for: %s", cycle_id, component)

        # Step 1: Research the issue
        research_result = await self._research_issue(component, description, severity)
        cycle.research_query = research_result.get("query", "")
        cycle.research_findings = research_result.get("findings", "")

        # Step 2: Analyze and select best solution
        solution = await self._analyze_findings(component, description, research_result)

        # Step 3: Apply healing
        healing_result = await self._apply_healing(component, solution)
        cycle.healing_action = healing_result.get("action", "")
        cycle.healing_success = healing_result.get("success", False)

        # Step 4: Verify
        verification = await self._verify_healing(component)
        cycle.verification_result = verification.get("status", "unknown")

        # Complete cycle
        cycle.completed_at = time.time()
        cycle.duration_ms = (cycle.completed_at - cycle.started_at) * 1000

        if cycle.healing_success:
            self._success_count += 1
        else:
            self._failure_count += 1

        self._history.append(cycle)
        del self._active_cycles[cycle_id]
        self._persist_cycle(cycle)
        self._update_state()

        logger.info(
            "Auto-Research-Heal cycle %s completed: success=%s, duration=%.0fms",
            cycle_id, cycle.healing_success, cycle.duration_ms,
        )

        return cycle

    async def _research_issue(
        self, component: str, description: str, severity: str
    ) -> dict:
        """البحث عن حلول عبر DeepResearchEngine"""
        query = f"كيفية إصلاح مشكلة {component} في نظام مأمون: {description}"

        # Try DeepResearchEngine first
        if self._deep_research:
            try:
                result = await self._deep_research.research(query)
                if result:
                    return {
                        "query": query,
                        "findings": str(result.get("summary", result.get("analysis", "")))[:1000],
                        "sources": result.get("sources", []),
                        "confidence": result.get("confidence_score", 0.5),
                    }
            except Exception as e:
                logger.warning("DeepResearch failed: %s", e)

        # Fallback: Use LLM for research
        if self._llm_client:
            try:
                research_prompt = f"""أنت باحث في نظام مأمون الذكاء الاصطناعي. ابحث عن حل للمشكلة التالية:

المكون: {component}
الوصف: {description}
الخطورة: {severity}

قدم تحليلاً وحلولاً مقترحة بصيغة JSON:
{{
    "root_cause": "السبب الجذري",
    "solutions": ["حل 1", "حل 2", "حل 3"],
    "recommended_action": "الحل الموصى به",
    "confidence": 0.0-1.0
}}"""
                response = await self._llm_client.think(
                    prompt=research_prompt,
                    model="glm-5.1",
                    temperature=0.3,
                )
                return {
                    "query": query,
                    "findings": str(response)[:1000] if response else "",
                    "sources": [],
                    "confidence": 0.6,
                }
            except Exception as e:
                logger.warning("LLM research failed: %s", e)

        return {"query": query, "findings": "فشل البحث — لا محرك بحث متاح", "confidence": 0.0}

    async def _analyze_findings(
        self, component: str, description: str, research: dict
    ) -> dict:
        """تحليل نتائج البحث واختيار أفضل حل"""
        findings = research.get("findings", "")

        if self._llm_client and findings:
            try:
                analysis_prompt = f"""حلّل نتائج البحث التالية واختر أفضل حل:

المكون: {component}
المشكلة: {description}
نتائج البحث: {findings[:2000]}

أجب بصيغة JSON:
{{
    "recommended_solution": "الحل الموصى به",
    "repair_strategy": "اسم استراتيجية الإصلاح",
    "confidence": 0.0-1.0,
    "reasoning": "سبب الاختيار"
}}"""
                response = await self._llm_client.think_json(
                    analysis_prompt, model="glm-5.1"
                )
                if response:
                    return response
            except Exception as e:
                logger.warning("LLM analysis failed: %s", e)

        # Default solution
        return {
            "recommended_solution": "إعادة تشغيل المكون",
            "repair_strategy": "restart_service",
            "confidence": 0.5,
            "reasoning": "حل افتراضي — فشل التحليل المتقدم",
        }

    async def _apply_healing(self, component: str, solution: dict) -> dict:
        """تطبيق الإصلاح عبر SelfHealingEngine"""
        if self._self_healing:
            try:
                # Run health check first
                self._self_healing.run_health_check()

                # Check if the issue was auto-repaired
                active_issues = self._self_healing.get_active_issues()
                issue_exists = any(
                    i.get("component") == component for i in active_issues
                )

                if not issue_exists:
                    return {
                        "action": "auto_repaired",
                        "success": True,
                        "message": "تم الإصلاح تلقائياً",
                    }

                # If still broken, try the recommended strategy
                strategy = solution.get("repair_strategy", "restart_service")
                if strategy in self._self_healing._repair_strategies:
                    from mamoun.core.self_healing import HealthIssue
                    issue = HealthIssue(
                        component=component,
                        severity="high",
                        description=solution.get("recommended_solution", ""),
                        root_cause=strategy,
                    )
                    success = self._self_healing._auto_repair(issue)
                    return {
                        "action": f"strategy:{strategy}",
                        "success": success,
                        "message": "تم تطبيق استراتيجية الإصلاح" if success else "فشل الإصلاح",
                    }
            except Exception as e:
                logger.error("Healing failed: %s", e)
                return {"action": "failed", "success": False, "message": str(e)[:200]}

        return {
            "action": "no_healing_engine",
            "success": False,
            "message": "محرك الشفاء غير متاح",
        }

    async def _verify_healing(self, component: str) -> dict:
        """التحقق من نجاح الإصلاح"""
        if self._self_healing:
            try:
                # Run health check to see if the issue is resolved
                result = self._self_healing.run_health_check()
                component_results = result.get("components", {}).get(component, {})
                healthy = component_results.get("healthy", True)

                return {
                    "status": "healthy" if healthy else "still_degraded",
                    "component": component,
                    "details": component_results,
                }
            except Exception as e:
                return {"status": "verification_failed", "error": str(e)[:100]}

        return {"status": "no_verification_available"}

    # ═══════════════════════════════════════════════════════════════
    # Background Loop
    # ═══════════════════════════════════════════════════════════════

    async def start(self):
        """بدء حلقة البحث والشفاء التلقائية في الخلفية"""
        if not AUTO_RESEARCH_HEAL_ENABLED:
            logger.info("AutoResearchHealLoop: Disabled (MAMOUN_AUTO_RESEARCH_HEAL=false)")
            return

        if self._running:
            return

        if not self._initialized:
            self.initialize()

        self._running = True
        self._task = asyncio.create_task(self._background_loop())
        logger.info(
            "AutoResearchHealLoop started — interval=%ds",
            CHECK_INTERVAL_SECONDS,
        )

    async def _background_loop(self):
        """حلقة الخلفية — تفحص المشاكل وتبحث عن حلول دورياً"""
        while self._running:
            try:
                # Check for active health issues
                if self._self_healing and self._self_healing._initialized:
                    issues = self._self_healing.get_active_issues()

                    # Process high/critical issues
                    for issue in issues:
                        if issue.get("severity") in ("high", "critical"):
                            component = issue.get("component", "")
                            desc = issue.get("description", "")
                            # Only start a cycle if not already processing this component
                            already_processing = any(
                                c.issue_component == component
                                for c in self._active_cycles.values()
                            )
                            if not already_processing and len(self._active_cycles) < MAX_CONCURRENT_HEALS:
                                await self.run_cycle(component, desc, issue.get("severity", "medium"))

                await asyncio.sleep(CHECK_INTERVAL_SECONDS)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Background loop error: %s", e)
                await asyncio.sleep(30)

    async def shutdown(self):
        """إيقاف الحلقة"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info(
            "AutoResearchHealLoop shutdown — cycles=%d, successes=%d, failures=%d",
            self._cycle_count, self._success_count, self._failure_count,
        )

    # ═══════════════════════════════════════════════════════════════
    # Status & Persistence
    # ═══════════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        """حالة حلقة البحث والشفاء"""
        return {
            "enabled": AUTO_RESEARCH_HEAL_ENABLED,
            "running": self._running,
            "initialized": self._initialized,
            "total_cycles": self._cycle_count,
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "success_rate": round(
                self._success_count / max(1, self._cycle_count), 3
            ),
            "active_cycles": len(self._active_cycles),
            "check_interval_seconds": CHECK_INTERVAL_SECONDS,
            "has_self_healing": self._self_healing is not None,
            "has_deep_research": self._deep_research is not None,
            "has_llm": self._llm_client is not None,
        }

    def get_history(self, limit: int = 20) -> list:
        """سجل دورات البحث-الشفاء"""
        return [c.to_dict() for c in self._history[-limit:]]

    def _ensure_schema(self):
        """إنشاء جداول قاعدة البيانات"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS arh_cycles (
                    cycle_id TEXT PRIMARY KEY,
                    issue_component TEXT,
                    issue_description TEXT,
                    research_query TEXT,
                    research_findings TEXT,
                    healing_action TEXT,
                    healing_success INTEGER,
                    verification_result TEXT,
                    started_at REAL,
                    completed_at REAL,
                    duration_ms REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS arh_state (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _load_state(self):
        """تحميل الحالة من قاعدة البيانات"""
        try:
            conn = get_db_connection(self.db_path)
            try:
                cur = conn.execute("SELECT key, value FROM arh_state")
                for key, value in cur.fetchall():
                    try:
                        if key == "cycle_count":
                            self._cycle_count = int(value)
                        elif key == "success_count":
                            self._success_count = int(value)
                        elif key == "failure_count":
                            self._failure_count = int(value)
                    except (ValueError, TypeError):
                        pass
            finally:
                conn.close()
        except Exception:
            pass

    def _persist_cycle(self, cycle: ResearchHealCycle):
        """حفظ دورة في قاعدة البيانات"""
        try:
            conn = get_db_connection(self.db_path)
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO arh_cycles
                    (cycle_id, issue_component, issue_description, research_query,
                     research_findings, healing_action, healing_success,
                     verification_result, started_at, completed_at, duration_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cycle.cycle_id, cycle.issue_component,
                    cycle.issue_description[:500], cycle.research_query[:500],
                    cycle.research_findings[:2000], cycle.healing_action,
                    int(cycle.healing_success), cycle.verification_result[:500],
                    cycle.started_at, cycle.completed_at, cycle.duration_ms,
                ))
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Persist cycle failed: %s", e)

    def _update_state(self):
        """تحديث الحالة في قاعدة البيانات"""
        try:
            conn = get_db_connection(self.db_path)
            try:
                for key, value in [
                    ("cycle_count", str(self._cycle_count)),
                    ("success_count", str(self._success_count)),
                    ("failure_count", str(self._failure_count)),
                ]:
                    conn.execute(
                        "INSERT OR REPLACE INTO arh_state (key, value) VALUES (?, ?)",
                        (key, value),
                    )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("State update failed: %s", e)


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

_auto_research_heal: Optional[AutoResearchHealLoop] = None


def get_auto_research_heal() -> AutoResearchHealLoop:
    """الحصول على النسخة العامة من حلقة البحث-الشفاء"""
    global _auto_research_heal
    if _auto_research_heal is None:
        _auto_research_heal = AutoResearchHealLoop()
    return _auto_research_heal
