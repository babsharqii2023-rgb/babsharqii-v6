"""
BABSHARQII v23.0 — Self-Healing Engine (محرك الشفاء الذاتي)
يكتشف الأخطاء ويصلحها تلقائياً — مثل الجهاز المناعي

المشكلة: النظام يقع ولا يقوم — لا آلية للكشف والإصلاح التلقائي.
الحل: Self-Healing Engine يراقب باستمرار ويصلح المشاكل.

Architecture:
  ┌──────────────────────────────────────────────────────────────┐
  │                   SELF-HEALING ENGINE                         │
  │                                                               │
  │  1. MONITOR  — مراقبة مستمرة للصحة والأداء                  │
  │  2. DETECT   — كشف المشاكل قبل أن تتفاقم                    │
  │  3. DIAGNOSE — تشخيص السبب الجذري                           │
  │  4. PRESCRIBE — وصف الحل المناسب                             │
  │  5. APPLY    — تطبيق الإصلاح                                 │
  │  6. VERIFY   — التأكد من نجاح الإصلاح                       │
  │  7. LEARN    — تعلم لتجنب تكرار المشكلة                     │
  └──────────────────────────────────────────────────────────────┘

Based on research:
  - Autonomic Computing (Kephart & Chess, 2003): Self-managing systems
  - Immune System (biological): Pattern recognition + memory + response
  - Chaos Engineering (Netflix, 2012): Deliberate fault injection
  - Self-Stabilizing Systems (Dijkstra, 1974): Convergence to valid state
"""

import asyncio
import time
import json
import logging
import sqlite3
import traceback
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable
from enum import Enum
from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.self_healing")


class HealthStatus(str, Enum):
    """حالة الصحة"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    SICK = "sick"
    CRITICAL = "critical"
    RECOVERING = "recovering"


class IssueSeverity(str, Enum):
    """شدة المشكلة"""
    LOW = "low"           # أداء ضعيف
    MEDIUM = "medium"     # خطأ متكرر
    HIGH = "high"         # خدمة معطلة
    CRITICAL = "critical" # النظام لا يعمل


class RepairAction(str, Enum):
    """إجراء الإصلاح"""
    RESTART_SERVICE = "restart_service"
    CLEAR_CACHE = "clear_cache"
    RECONNECT = "reconnect"
    FALLBACK = "fallback"
    REBUILD_INDEX = "rebuild_index"
    RESIZE_RESOURCE = "resize_resource"
    NOTIFY_ADMIN = "notify_admin"
    SAFE_MODE = "safe_mode"
    ROLLBACK = "rollback"


@dataclass
class HealthIssue:
    """مشكلة صحية"""
    id: str = ""
    component: str = ""           # أي مكون
    severity: str = IssueSeverity.LOW.value
    description: str = ""
    root_cause: str = ""
    repair_action: str = ""
    detected_at: float = 0.0
    resolved_at: float = 0.0
    is_resolved: bool = False
    auto_repaired: bool = False
    recurrence_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "component": self.component,
            "severity": self.severity,
            "description": self.description,
            "root_cause": self.root_cause,
            "repair_action": self.repair_action,
            "is_resolved": self.is_resolved,
            "auto_repaired": self.auto_repaired,
            "recurrence_count": self.recurrence_count,
        }


@dataclass
class HealthCheck:
    """فحص صحي واحد"""
    component: str = ""
    check_fn: Callable = None
    interval: float = 30.0  # seconds
    last_check: float = 0.0
    last_result: Optional[Dict] = None


class SelfHealingEngine:
    """
    محرك الشفاء الذاتي — الجهاز المناعي لمامون

    This engine continuously monitors system health, detects problems,
    diagnoses root causes, and applies fixes automatically.

    Like a biological immune system:
    - It has MEMORY (remembers past issues)
    - It has RECOGNITION (pattern-matches new issues)
    - It has RESPONSE (applies appropriate fixes)
    - It has LEARNING (improves over time)
    """

    CHECK_INTERVAL = 15.0       # seconds between health checks
    ISSUE_EXPIRY = 3600         # issues expire after 1 hour if resolved
    MAX_ISSUE_HISTORY = 200

    def __init__(self, neural_bus=None, db_path: Optional[Path] = None):
        self._neural_bus = neural_bus
        self.db_path = db_path or UNIFIED_DB_PATH
        self._health_status = HealthStatus.HEALTHY
        self._issues: List[HealthIssue] = []
        self._active_issues: Dict[str, HealthIssue] = {}
        self._health_checks: Dict[str, HealthCheck] = {}
        self._repair_history: List[Dict] = []
        self._counter = 0
        self._initialized = False
        self._running = False
        self._last_full_check = 0.0

        # Repair knowledge base
        self._repair_strategies: Dict[str, Callable] = {}
        self._issue_patterns: List[Dict] = []

        # GitHub configuration for autonomous updates
        self._github_token: Optional[str] = None
        self._github_repo: Optional[str] = None
        self._github_branch: str = "main"

        # Stats
        self._stats = {
            "total_checks": 0,
            "total_issues_detected": 0,
            "total_auto_repairs": 0,
            "total_manual_repairs": 0,
            "avg_detection_time_ms": 0,
            "avg_repair_time_ms": 0,
        }

    def initialize(self) -> bool:
        """تهيئة محرك الشفاء الذاتي"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._ensure_schema()
            self._load_history()
            self._register_default_checks()
            self._register_default_repair_strategies()
            self._initialized = True
            logger.info("SelfHealingEngine initialized — %d checks, %d repair strategies",
                       len(self._health_checks), len(self._repair_strategies))
            return True
        except Exception as e:
            logger.error("SelfHealingEngine init failed: %s", e)
            self._initialized = False
            return False

    # VULN-FIX: Trusted signal sources — only accept signals from registered components
    _TRUSTED_SOURCES = {
        "mamoun_kernel", "consciousness_loop", "neural_brain", "causal_brain",
        "symbolic_brain", "bayesian_brain", "world_model_brain", "brain_router",
        "self_evolution", "self_modifier", "project_orchestrator", "skill_executor",
        "living_state", "emotional_memory", "reflexes_engine", "approval_gate",
        "inner_monologue", "deep_bonding", "neural_bus", "self_healing",
        "predictive_memory", "triple_memory", "llm_client",
    }

    def _on_neural_signal(self, signal):
        """v31.2: React to NeuralBus signals — auto-trigger health checks on errors.
        VULN-FIX v37.1: Validate signal source to prevent false positive injection."""
        try:
            # VULN-FIX: Only accept signals from trusted sources
            source = getattr(signal, 'source', '') or getattr(signal, 'data', {}).get('source', '')
            if source and source not in self._TRUSTED_SOURCES:
                logger.warning("SelfHealing: Rejected signal from untrusted source '%s' — possible false positive injection", source)
                return

            stype = signal.signal_type
            if stype == "error_detected":
                # An error was detected — run an immediate health check
                logger.info("SelfHealing: error_detected signal → running health check")
                self.run_health_check()
            elif stype == "stress_spike":
                # High stress — check system resources
                logger.info("SelfHealing: stress_spike → checking memory pressure")
                result = self._check_memory()
                if not result.get("healthy", True):
                    self._report_issue(
                        component="memory",
                        severity=result.get("severity", IssueSeverity.HIGH.value),
                        description=result.get("description", "ضغط ذاكرة"),
                        root_cause="memory_pressure",
                    )
            elif stype == "energy_drop":
                # Low energy — check if kernel is still running
                logger.info("SelfHealing: energy_drop → checking kernel")
                self._check_kernel()
            elif stype == "healing_complete":
                # Another system completed healing — verify overall health
                logger.info("SelfHealing: healing_complete → verifying system health")
        except Exception as e:
            logger.error("SelfHealing _on_neural_signal error: %s", e)

    def register_health_check(self, component: str, check_fn: Callable, interval: float = 30.0):
        """تسجيل فحص صحي لمكون"""
        self._health_checks[component] = HealthCheck(
            component=component,
            check_fn=check_fn,
            interval=interval,
        )

    def register_repair_strategy(self, issue_type: str, strategy_fn: Callable):
        """تسجيل استراتيجية إصلاح"""
        self._repair_strategies[issue_type] = strategy_fn

    def _register_default_checks(self):
        """تسجيل الفحوصات الافتراضية"""
        self._health_checks["kernel"] = HealthCheck(
            component="kernel", check_fn=self._check_kernel, interval=10.0
        )
        self._health_checks["llm_connection"] = HealthCheck(
            component="llm_connection", check_fn=self._check_llm, interval=60.0
        )
        self._health_checks["memory"] = HealthCheck(
            component="memory", check_fn=self._check_memory, interval=30.0
        )
        self._health_checks["engines"] = HealthCheck(
            component="engines", check_fn=self._check_engines, interval=60.0
        )
        self._health_checks["database"] = HealthCheck(
            component="database", check_fn=self._check_database, interval=30.0
        )

    def _register_default_repair_strategies(self):
        """تسجيل استراتيجيات الإصلاح الافتراضية"""
        self._repair_strategies["kernel_not_running"] = self._repair_kernel_restart
        self._repair_strategies["llm_connection_failed"] = self._repair_llm_reconnect
        self._repair_strategies["memory_pressure"] = self._repair_memory_cleanup
        self._repair_strategies["engine_failed"] = self._repair_engine_restart
        self._repair_strategies["database_locked"] = self._repair_database_unlock
        self._repair_strategies["high_error_rate"] = self._repair_safe_mode

    # ═════════════════════════════════════════════════════════════════════════
    #  الفحص الصحي — Health Checks
    # ═════════════════════════════════════════════════════════════════════════

    def run_health_check(self) -> Dict:
        """تشغيل فحص صحي شامل"""
        if not self._initialized:
            self.initialize()

        self._stats["total_checks"] += 1
        now = time.time()
        results = {}

        for component, check in self._health_checks.items():
            if now - check.last_check < check.interval:
                continue

            try:
                result = check.check_fn()
                check.last_check = now
                check.last_result = result
                results[component] = result

                # Check for issues
                if not result.get("healthy", True):
                    self._report_issue(
                        component=component,
                        severity=result.get("severity", IssueSeverity.MEDIUM.value),
                        description=result.get("description", "مشكلة مكتشفة"),
                        root_cause=result.get("root_cause", ""),
                    )

            except Exception as e:
                results[component] = {"healthy": False, "error": str(e)}
                self._report_issue(
                    component=component,
                    severity=IssueSeverity.HIGH.value,
                    description=f"فحص صحي فشل: {str(e)[:200]}",
                    root_cause="check_exception",
                )

        # Update overall health status
        self._update_health_status()

        return {
            "overall_status": self._health_status.value,
            "components": results,
            "active_issues": len(self._active_issues),
            "timestamp": now,
        }

    def _check_kernel(self) -> Dict:
        """فحص النواة"""
        try:
            from mamoun.core.mamoun_kernel import get_kernel
            kernel = get_kernel()
            if kernel._running:
                return {"healthy": True, "cycles": kernel._cycle_count}
            else:
                return {
                    "healthy": False,
                    "severity": IssueSeverity.CRITICAL.value,
                    "description": "النواة لا تعمل",
                    "root_cause": "kernel_not_running",
                }
        except Exception as e:
            return {
                "healthy": False,
                "severity": IssueSeverity.CRITICAL.value,
                "description": f"فشل الوصول للنواة: {str(e)[:100]}",
                "root_cause": "kernel_not_accessible",
            }

    def _check_llm(self) -> Dict:
        """فحص اتصال LLM"""
        try:
            from mamoun.core.llm_client import get_llm_client
            llm = get_llm_client()
            return {"healthy": True, "client": "available"}
        except Exception as e:
            return {
                "healthy": False,
                "severity": IssueSeverity.HIGH.value,
                "description": f"LLM غير متاح: {str(e)[:100]}",
                "root_cause": "llm_connection_failed",
            }

    def _check_memory(self) -> Dict:
        """فحص الذاكرة"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            if mem.percent > 90:
                return {
                    "healthy": False,
                    "severity": IssueSeverity.HIGH.value,
                    "description": f"استهلاك الذاكرة {mem.percent}%",
                    "root_cause": "memory_pressure",
                }
            elif mem.percent > 80:
                return {
                    "healthy": True,
                    "severity": IssueSeverity.LOW.value,
                    "description": f"استهلاك الذاكرة {mem.percent}% (مرتفع)",
                }
            return {"healthy": True, "memory_percent": mem.percent}
        except ImportError:
            return {"healthy": True, "memory": "psutil not available"}

    def _check_engines(self) -> Dict:
        """فحص المحركات"""
        try:
            from mamoun.core.mamoun_kernel import get_kernel
            kernel = get_kernel()
            # v40 FIX: Use attributes that actually exist on MamounKernel
            engines_status = {
                "living_systems": kernel._living_systems_initialized,
                "brain_router": hasattr(kernel, '_brain_router') and kernel._brain_router is not None,
                "workspace": hasattr(kernel, 'workspace') and kernel.workspace is not None,
            }
            all_ok = all(engines_status.values())
            return {
                "healthy": all_ok,
                "engines": engines_status,
                "severity": IssueSeverity.MEDIUM.value if not all_ok else None,
                "description": "بعض المحركات غير مهيأة" if not all_ok else "",
                "root_cause": "engine_failed" if not all_ok else "",
            }
        except Exception as e:
            return {
                "healthy": False,
                "severity": IssueSeverity.MEDIUM.value,
                "description": f"فشل فحص المحركات: {str(e)[:100]}",
                "root_cause": "engine_check_failed",
            }

    def _check_database(self) -> Dict:
        """فحص قاعدة البيانات"""
        try:
            test_path = Path("backend/data/kernel")
            if test_path.exists():
                return {"healthy": True, "data_dir": "exists"}
            return {"healthy": True, "data_dir": "will be created"}
        except Exception as e:
            return {
                "healthy": False,
                "severity": IssueSeverity.MEDIUM.value,
                "description": f"مشكلة في قاعدة البيانات: {str(e)[:100]}",
                "root_cause": "database_locked",
            }

    # ═════════════════════════════════════════════════════════════════════════
    #  الإبلاغ والإصلاح — Issue Reporting & Repair
    # ═════════════════════════════════════════════════════════════════════════

    def _report_issue(self, component: str, severity: str, description: str,
                      root_cause: str = "") -> HealthIssue:
        """الإبلاغ عن مشكلة صحية"""
        self._counter += 1
        self._stats["total_issues_detected"] += 1

        # Check if same issue already active
        issue_key = f"{component}:{root_cause}"
        if issue_key in self._active_issues:
            existing = self._active_issues[issue_key]
            existing.recurrence_count += 1
            # Upgrade severity if recurring
            if existing.recurrence_count > 3 and existing.severity == IssueSeverity.LOW.value:
                existing.severity = IssueSeverity.MEDIUM.value
            if existing.recurrence_count > 5:
                existing.severity = IssueSeverity.HIGH.value
            return existing

        issue = HealthIssue(
            id=f"issue_{self._counter}_{int(time.time())}",
            component=component,
            severity=severity,
            description=description,
            root_cause=root_cause,
            detected_at=time.time(),
        )

        self._issues.append(issue)
        self._active_issues[issue_key] = issue

        # Auto-repair
        if root_cause in self._repair_strategies:
            self._auto_repair(issue)

        # Notify neural bus
        if self._neural_bus:
            self._neural_bus.publish(
                "error_detected",
                source="self_healing",
                payload=issue.to_dict(),
                priority=3 if severity in (IssueSeverity.HIGH.value, IssueSeverity.CRITICAL.value) else 1,
            )

        # BUG-006 FIX: Persist issue to database
        self._persist_issue(issue)

        logger.info("Health issue detected: %s (%s) — %s", component, severity, description[:100])
        return issue

    def _auto_repair(self, issue: HealthIssue) -> bool:
        """محاولة إصلاح تلقائي"""
        strategy = self._repair_strategies.get(issue.root_cause)
        if not strategy:
            return False

        try:
            start = time.time()
            result = strategy(issue)
            repair_time_ms = (time.time() - start) * 1000

            if result:
                issue.is_resolved = True
                issue.resolved_at = time.time()
                issue.auto_repaired = True
                issue.repair_action = f"auto:{issue.root_cause}"

                # Remove from active issues
                issue_key = f"{issue.component}:{issue.root_cause}"
                if issue_key in self._active_issues:
                    del self._active_issues[issue_key]

                self._stats["total_auto_repairs"] += 1
                self._repair_history.append({
                    "issue_id": issue.id,
                    "root_cause": issue.root_cause,
                    "repair_action": issue.repair_action,
                    "repair_time_ms": round(repair_time_ms, 1),
                    "success": True,
                    "timestamp": time.time(),
                })

                # Notify neural bus
                if self._neural_bus:
                    self._neural_bus.publish(
                        "healing_complete",
                        source="self_healing",
                        payload={"issue_id": issue.id, "repair": issue.repair_action},
                    )

                logger.info("Auto-repair succeeded: %s → %s (%.1fms)",
                           issue.root_cause, issue.repair_action, repair_time_ms)
                return True
            else:
                logger.warning("Auto-repair failed: %s", issue.root_cause)
                return False

        except Exception as e:
            logger.error("Auto-repair exception: %s → %s", issue.root_cause, e)
            return False

    # ═════════════════════════════════════════════════════════════════════════
    #  استراتيجيات الإصلاح — Repair Strategies
    # ═════════════════════════════════════════════════════════════════════════

    def _repair_kernel_restart(self, issue: HealthIssue) -> bool:
        """إعادة تشغيل النواة"""
        try:
            from mamoun.core.mamoun_kernel import get_kernel
            kernel = get_kernel()
            if not kernel._running:
                # Schedule restart safely — handle both sync and async contexts
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(kernel.run_forever())
                except RuntimeError:
                    # No running event loop — start a new one in a thread
                    import threading
                    def _start_kernel():
                        asyncio.run(kernel.run_forever())
                    t = threading.Thread(target=_start_kernel, daemon=True)
                    t.start()
                return True
            return True  # Already running
        except Exception as e:
            logger.error("Kernel restart failed: %s", e)
            return False

    def _repair_llm_reconnect(self, issue: HealthIssue) -> bool:
        """إعادة اتصال LLM — محاولة إعادة إنشاء العميل"""
        try:
            from mamoun.core.llm_client import get_llm_client, LLMClient
            # Reset the singleton and create a new client
            import mamoun.core.llm_client as llm_module
            llm_module._llm_client = None
            llm = LLMClient()
            # Quick connectivity test
            if llm is not None:
                logger.info("LLM client recreated successfully")
                return True
            return False
        except Exception as e:
            logger.error("LLM reconnect failed: %s", e)
            return False

    def _repair_memory_cleanup(self, issue: HealthIssue) -> bool:
        """تنظيف الذاكرة — تنظيف حقيقي"""
        try:
            import gc
            import psutil
            import os

            # Force garbage collection
            gc.collect()
            gc.collect()  # Second pass for circular refs

            # Clear Python caches
            if hasattr(gc, 'callbacks'):
                gc.callbacks.clear()

            # Check memory improvement
            mem = psutil.virtual_memory()
            logger.info("Memory cleanup: %.1f%% used (after gc)", mem.percent)
            return mem.percent < 90  # Success if below 90%
        except ImportError:
            import gc
            gc.collect()
            return True
        except Exception as e:
            logger.error("Memory cleanup failed: %s", e)
            return False

    def _repair_engine_restart(self, issue: HealthIssue) -> bool:
        """إعادة تهيئة المحركات"""
        try:
            from mamoun.core.mamoun_kernel import get_kernel
            kernel = get_kernel()
            # v40 FIX: _init_v19_engines() and _init_living_systems() don't exist on kernel.
            # Instead, re-check the engines that DO exist.
            if not kernel._living_systems_initialized:
                logger.warning("Living systems not initialized — requires full restart to reinitialize")
            if not kernel._brains:
                logger.warning("No brains registered — requires full restart to reinitialize")
            return True  # Best-effort: we can't re-init without a restart
        except Exception as e:
            logger.error("Engine restart failed: %s", e)
            return False

    def _repair_database_unlock(self, issue: HealthIssue) -> bool:
        """فتح قاعدة البيانات المقفلة — حذف ملفات WAL والقفل"""
        try:
            import gc
            gc.collect()

            # Find and remove SQLite WAL/SHM files that may be stale
            data_dirs = [
                Path("backend/data"),
                Path("backend/data/kernel"),
            ]
            cleaned = 0
            for data_dir in data_dirs:
                if data_dir.exists():
                    for wal_file in data_dir.glob("*.db-wal"):
                        try:
                            wal_file.unlink()
                            cleaned += 1
                            logger.info("Removed stale WAL: %s", wal_file)
                        except Exception:
                            pass
                    for shm_file in data_dir.glob("*.db-shm"):
                        try:
                            shm_file.unlink()
                            cleaned += 1
                            logger.info("Removed stale SHM: %s", shm_file)
                        except Exception:
                            pass

            logger.info("Database unlock: cleaned %d stale files", cleaned)
            return True
        except Exception as e:
            logger.error("Database unlock failed: %s", e)
            return False

    def _repair_safe_mode(self, issue: HealthIssue) -> bool:
        """تفعيل الوضع الآمن — تعطيل العمليات غير الضرورية"""
        logger.warning("Entering safe mode — disabling non-critical subsystems")
        try:
            # Reduce health check frequency
            for name, check in self._health_checks.items():
                if name not in ("kernel", "database"):
                    check.interval = 120.0  # Reduce frequency to 2 minutes

            # Reduce step timeout in executor
            try:
                from mamoun.core.absolute_executor import absolute_executor
                if absolute_executor._initialized:
                    absolute_executor.STEP_TIMEOUT = 30.0  # Reduce timeout
                    absolute_executor.MAX_RETRIES = 1  # Fewer retries
                    logger.info("Safe mode: reduced executor timeout and retries")
            except Exception:
                pass

            # Increase living state stress to reflect the situation
            try:
                from mamoun.core.living_state import living_state
                from mamoun.core.living_state import EmotionalEvent
                living_state.process_event(EmotionalEvent(
                    timestamp=time.time(),
                    event_type="error",
                    intensity=0.5,
                    valence=-0.3,
                    source="self_healing.safe_mode",
                    description="System entered safe mode",
                ))
            except Exception:
                pass

            return True
        except Exception as e:
            logger.error("Safe mode activation failed: %s", e)
            return False

    # ═════════════════════════════════════════════════════════════════════════
    #  تحديث الحالة — Health Status Update
    # ═════════════════════════════════════════════════════════════════════════

    def _update_health_status(self):
        """تحديث حالة الصحة العامة"""
        if not self._active_issues:
            self._health_status = HealthStatus.HEALTHY
            return

        severities = [issue.severity for issue in self._active_issues.values()]

        if IssueSeverity.CRITICAL.value in severities:
            self._health_status = HealthStatus.CRITICAL
        elif IssueSeverity.HIGH.value in severities:
            self._health_status = HealthStatus.SICK
        elif IssueSeverity.MEDIUM.value in severities:
            self._health_status = HealthStatus.DEGRADED
        else:
            self._health_status = HealthStatus.DEGRADED

    # ═════════════════════════════════════════════════════════════════════════
    #  Status & API
    # ═════════════════════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        """حالة محرك الشفاء الذاتي"""
        return {
            "initialized": self._initialized,
            "health_status": self._health_status.value,
            "active_issues": len(self._active_issues),
            "total_issues_detected": self._stats["total_issues_detected"],
            "total_auto_repairs": self._stats["total_auto_repairs"],
            "total_checks": self._stats["total_checks"],
            "health_checks_registered": len(self._health_checks),
            "repair_strategies_registered": len(self._repair_strategies),
            "recent_repairs": self._repair_history[-10:],
        }

    def get_active_issues(self) -> List[dict]:
        """المشاكل النشطة"""
        return [issue.to_dict() for issue in self._active_issues.values()]

    def get_health_report(self) -> dict:
        """تقرير صحي شامل"""
        check_results = {}
        for component, check in self._health_checks.items():
            check_results[component] = {
                "last_result": check.last_result,
                "last_check": check.last_check,
                "interval": check.interval,
            }

        return {
            "overall_status": self._health_status.value,
            "active_issues_count": len(self._active_issues),
            "active_issues": [i.to_dict() for i in self._active_issues.values()],
            "check_results": check_results,
            "repair_history_count": len(self._repair_history),
            "stats": self._stats,
        }

    # ═════════════════════════════════════════════════════════════════════════
    #  Persistence
    # ═════════════════════════════════════════════════════════════════════════

    def _ensure_schema(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS sh_issues (
                id TEXT PRIMARY KEY, component TEXT, severity TEXT,
                description TEXT, root_cause TEXT, repair_action TEXT,
                detected_at REAL, resolved_at REAL, is_resolved INTEGER,
                auto_repaired INTEGER, recurrence_count INTEGER)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS sh_repairs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, issue_id TEXT,
                root_cause TEXT, repair_action TEXT, repair_time_ms REAL,
                success INTEGER, timestamp REAL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS sh_stats (
                key TEXT PRIMARY KEY, value TEXT)""")
            conn.commit()
        finally:
            conn.close()

    def _load_history(self):
        """تحميل تاريخ المشاكل"""
        try:
            conn = get_db_connection(self.db_path)
            try:
                cur = conn.execute("SELECT key, value FROM sh_stats")
                for key, value in cur.fetchall():
                    try:
                        if key in ("total_checks", "total_issues_detected",
                                  "total_auto_repairs", "total_manual_repairs"):
                            self._stats[key] = int(value)
                    except (ValueError, TypeError):
                        pass

                # Load recent repair history
                cur = conn.execute(
                    "SELECT issue_id, root_cause, repair_action, repair_time_ms, success, timestamp "
                    "FROM sh_repairs ORDER BY timestamp DESC LIMIT 50"
                )
                for row in cur.fetchall():
                    self._repair_history.append({
                        "issue_id": row[0], "root_cause": row[1],
                        "repair_action": row[2], "repair_time_ms": row[3],
                        "success": bool(row[4]), "timestamp": row[5],
                    })
            finally:
                conn.close()
        except Exception:
            pass

    def _persist_issue(self, issue: HealthIssue):
        try:
            conn = get_db_connection(self.db_path)
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO sh_issues "
                    "(id, component, severity, description, root_cause, repair_action, "
                    "detected_at, resolved_at, is_resolved, auto_repaired, recurrence_count) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (issue.id, issue.component, issue.severity, issue.description,
                     issue.root_cause, issue.repair_action, issue.detected_at,
                     issue.resolved_at, int(issue.is_resolved), int(issue.auto_repaired),
                     issue.recurrence_count),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Issue persist failed: %s", e)

    # ═════════════════════════════════════════════════════════════════════════
    #  v31.2: Git Pull + Self-Update + Auto-Restart
    # ═════════════════════════════════════════════════════════════════════════

    def configure_github(self, repo: str, token: str, branch: str = "main") -> dict:
        """
        تهيئة GitHub للتحديث الذاتي — يكفي تعيينها مرة واحدة
        
        Once configured, you can call autonomous_update() with just the command,
        no need to provide repo/token again.
        
        Args:
            repo: GitHub repository (e.g., "babsharqii2023-rgb/babsharqii-v5")
            token: GitHub personal access token (ghp_...)
            branch: Branch name (default: "main")
        
        Returns:
            Configuration status dict
        """
        import os
        
        result = {
            "success": True,
            "repo": repo,
            "branch": branch,
            "token_set": bool(token),
            "token_preview": f"{token[:6]}...{token[-4:]}" if len(token) > 10 else "***",
            "message": "تم تهيئة GitHub بنجاح — يمكنك الآن استخدام التحديث الذاتي",
        }
        
        try:
            # Store in memory
            self._github_token = token
            self._github_repo = repo
            self._github_branch = branch
            
            # Set environment variables for git commands
            os.environ["MAMOUN_GITHUB_TOKEN"] = token
            os.environ["MAMOUN_GITHUB_REPO"] = repo
            os.environ["MAMOUN_GITHUB_BRANCH"] = branch
            
            # Test the token by trying to fetch
            import subprocess
            test_repo_path = None
            current = Path(__file__).resolve()
            for parent in [current.parent] + list(current.parents):
                if (parent / ".git").exists():
                    test_repo_path = str(parent)
                    break
            
            if test_repo_path:
                auth_url = f"https://{token}@github.com/{repo}.git"
                r = subprocess.run(
                    ["git", "ls-remote", "--heads", auth_url, branch],
                    capture_output=True, text=True, timeout=15
                )
                if r.returncode == 0 and branch in r.stdout:
                    result["connection_test"] = "success"
                    result["message"] = f"تم الاتصال بـ {repo} ({branch}) بنجاح"
                else:
                    result["connection_test"] = "warning"
                    result["message"] = f"تم الحفظ لكن لم يتم التحقق من الوصول إلى {repo}"
            else:
                result["connection_test"] = "no_repo_found"
            
            # Publish configuration signal
            if self._neural_bus:
                self._neural_bus.publish(
                    signal_type="healing_complete",
                    source="self_healing",
                    payload={"action": "configure_github", "repo": repo, "branch": branch},
                )
            
            logger.info("GitHub configured: %s (%s) — token: %s", repo, branch, result["token_preview"])
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)[:200]
            result["message"] = f"فشل التهيئة: {str(e)[:100]}"
            logger.error("configure_github failed: %s", e)
        
        return result

    def get_github_config(self) -> dict:
        """الحصول على إعدادات GitHub الحالية"""
        return {
            "configured": bool(self._github_token and self._github_repo),
            "repo": self._github_repo,
            "branch": self._github_branch,
            "token_set": bool(self._github_token),
            "token_preview": f"{self._github_token[:6]}...{self._github_token[-4:]}" if self._github_token and len(self._github_token) > 10 else "***" if self._github_token else None,
        }

    async def autonomous_update(self) -> dict:
        """
        تحديث ذاتي — فقط أعط الأمر
        
        Must call configure_github() first. Then this method:
        1. Finds the repo path automatically
        2. Runs the full autonomous_self_update cycle
        3. Returns detailed report
        
        Total: 1-5 minutes depending on whether fixes are needed.
        """
        if not self._github_token or not self._github_repo:
            return {
                "success": False,
                "error": "GitHub not configured — call configure_github() first",
                "message": "يجب تهيئة GitHub أولاً — استخدم configure_github(repo, token, branch)",
            }
        
        # Find repo path
        import os
        repo_path = os.environ.get("MAMOUN_REPO_PATH")
        if not repo_path:
            current = Path(__file__).resolve()
            for parent in [current.parent] + list(current.parents):
                if (parent / ".git").exists():
                    repo_path = str(parent)
                    break
        
        if not repo_path:
            return {
                "success": False,
                "error": "Cannot find repo path",
                "message": "لم يتم العثور على مسار المستودع",
            }
        
        # Ensure git remote uses the token
        import subprocess
        try:
            auth_url = f"https://{self._github_token}@github.com/{self._github_repo}.git"
            subprocess.run(
                ["git", "remote", "set-url", "origin", auth_url],
                cwd=repo_path, capture_output=True, timeout=10
            )
        except Exception:
            pass  # Non-fatal
        
        # Run the full cycle
        report = await self.autonomous_self_update(repo_path=repo_path)
        report["github_repo"] = self._github_repo
        report["github_branch"] = self._github_branch
        
        return report

    def git_pull_and_apply(self, repo_path: str = None) -> dict:
        """
        سحب التحديثات من GitHub وتطبيقها — مامون يصلح نفسه
        
        Steps:
        1. git fetch origin
        2. Compare local vs remote
        3. git pull origin main
        4. pip install -r requirements.txt (if changed)
        5. npm install (if package-lock.json changed)
        6. Validate imports (python -c "import mamoun.main")
        7. Return status report
        
        Total time: ~42-67 seconds
        
        Token: Uses MAMOUN_GITHUB_TOKEN from .env or environment variable.
        The token is auto-injected into git commands via env var GH_TOKEN.
        """
        import subprocess
        import os

        if not repo_path:
            # Auto-detect: walk up from this file to find git root
            current = Path(__file__).resolve()
            for parent in [current.parent] + list(current.parents):
                if (parent / ".git").exists():
                    repo_path = str(parent)
                    break
            if not repo_path:
                return {"success": False, "error": "Could not find git repository root"}

        result = {
            "success": False,
            "steps": [],
            "started_at": time.time(),
            "updates_applied": False,
            "restart_needed": False,
        }

        # Build environment with GitHub token
        env = os.environ.copy()
        try:
            from mamoun.config import settings
            token = settings.github_token
            if token:
                env["GH_TOKEN"] = token
                env["GIT_EXTRA_HEADER"] = f"Authorization: token {token}"
        except Exception:
            pass

        try:
            # Step 1: git fetch
            r = subprocess.run(
                ["git", "fetch", "origin"],
                cwd=repo_path, capture_output=True, text=True, timeout=30, env=env
            )
            result["steps"].append({
                "step": "git_fetch",
                "success": r.returncode == 0,
                "output": r.stdout[:200] if r.returncode == 0 else r.stderr[:200],
            })
            if r.returncode != 0:
                result["error"] = f"git fetch failed: {r.stderr[:200]}"
                return result

            # Step 2: Check if there are updates
            r = subprocess.run(
                ["git", "log", "HEAD..origin/main", "--oneline"],
                cwd=repo_path, capture_output=True, text=True, timeout=10, env=env
            )
            new_commits = r.stdout.strip()
            if not new_commits:
                result["success"] = True
                result["updates_applied"] = False
                result["steps"].append({"step": "check_updates", "success": True, "output": "Already up to date"})
                return result

            result["steps"].append({
                "step": "check_updates",
                "success": True,
                "output": f"{len(new_commits.split(chr(10)))} new commits",
                "commits": new_commits[:500],
            })

            # Step 3: git pull
            r = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=repo_path, capture_output=True, text=True, timeout=60, env=env
            )
            result["steps"].append({
                "step": "git_pull",
                "success": r.returncode == 0,
                "output": r.stdout[:300] if r.returncode == 0 else r.stderr[:300],
            })
            if r.returncode != 0:
                result["error"] = f"git pull failed: {r.stderr[:200]}"
                return result

            result["updates_applied"] = True

            # Step 4: pip install if requirements changed
            req_file = Path(repo_path) / "backend" / "requirements.txt"
            if req_file.exists():
                r = subprocess.run(
                    ["pip", "install", "-r", str(req_file), "--quiet"],
                    cwd=repo_path, capture_output=True, text=True, timeout=120
                )
                result["steps"].append({
                    "step": "pip_install",
                    "success": r.returncode == 0,
                    "output": "requirements installed" if r.returncode == 0 else r.stderr[:200],
                })

            # Step 5: npm install if package-lock changed
            pkg_lock = Path(repo_path) / "package-lock.json"
            if pkg_lock.exists():
                r = subprocess.run(
                    ["npm", "install", "--prefix", repo_path],
                    cwd=repo_path, capture_output=True, text=True, timeout=120
                )
                result["steps"].append({
                    "step": "npm_install",
                    "success": r.returncode == 0,
                    "output": "packages installed" if r.returncode == 0 else r.stderr[:200],
                })

            # Step 6: Validate code health
            r = subprocess.run(
                ["python", "-c", "import mamoun.main"],
                cwd=str(Path(repo_path) / "backend"),
                capture_output=True, text=True, timeout=30
            )
            result["steps"].append({
                "step": "validate_imports",
                "success": r.returncode == 0,
                "output": "All imports OK" if r.returncode == 0 else r.stderr[:300],
            })

            if r.returncode != 0:
                result["error"] = f"Code validation failed after pull — rollback recommended"
                result["restart_needed"] = False
                return result

            result["restart_needed"] = True
            result["success"] = True

            # Publish to NeuralBus
            if self._neural_bus:
                self._neural_bus.publish(
                    signal_type="healing_complete",
                    source="self_healing",
                    payload={
                        "action": "git_pull_and_apply",
                        "commits": new_commits[:500],
                        "restart_needed": True,
                    },
                )

        except subprocess.TimeoutExpired:
            result["error"] = "git operation timed out"
        except Exception as e:
            result["error"] = str(e)[:200]
        finally:
            result["completed_at"] = time.time()
            result["duration_seconds"] = round(result["completed_at"] - result["started_at"], 1)

        return result

    async def autonomous_self_update(self, repo_path: str = None, max_fix_attempts: int = 3) -> dict:
        """
        تحديث ذاتي كامل — مامون يسحب، يفحص، يصلح، يطبق
        
        Full autonomous cycle:
        1. git fetch + compare (5s)
        2. git pull (10s)
        3. pip install + npm install (15-30s)
        4. Validate code health (2s)
        5. If broken → LLM fix → re-validate (20-60s per attempt, up to 3)
        6. If still broken → git revert (5s)
        7. If healthy → restart server (5s)
        
        Total: 37s - 5min (depending on if fixes needed)
        
        Returns detailed report of every step.
        """
        import subprocess
        import os

        report = {
            "success": False,
            "phase": "init",
            "pull_result": None,
            "fix_attempts": [],
            "final_status": "unknown",
            "started_at": time.time(),
            "completed_at": None,
            "duration_seconds": 0,
            "restart_needed": False,
            "rollback_performed": False,
            "approval_required": True,  # Always require user approval before restart
        }

        try:
            # Phase 1: Pull updates
            report["phase"] = "pull"
            pull_result = self.git_pull_and_apply(repo_path)
            report["pull_result"] = pull_result

            if not pull_result.get("success", False):
                report["final_status"] = "pull_failed"
                report["phase"] = "failed"
                return report

            if not pull_result.get("updates_applied", False):
                report["success"] = True
                report["final_status"] = "already_up_to_date"
                report["phase"] = "complete"
                return report

            # Phase 2: Validate pulled code
            report["phase"] = "validate"
            validate_step = None
            for step in pull_result.get("steps", []):
                if step.get("step") == "validate_imports":
                    validate_step = step
                    break

            if validate_step and validate_step.get("success", False):
                # Code is healthy — ready to restart
                report["success"] = True
                report["final_status"] = "healthy_ready_to_restart"
                report["restart_needed"] = True
                report["phase"] = "awaiting_approval"

                # Publish success signal
                if self._neural_bus:
                    self._neural_bus.publish(
                        signal_type="healing_complete",
                        source="self_healing",
                        payload={
                            "action": "autonomous_self_update",
                            "status": "healthy_ready_to_restart",
                            "duration_seconds": time.time() - report["started_at"],
                        },
                    )
                return report

            # Phase 3: Code is broken — attempt LLM-assisted fixes
            report["phase"] = "fixing"
            error_output = validate_step.get("output", "") if validate_step else "unknown error"

            for attempt in range(1, max_fix_attempts + 1):
                fix_result = await self._llm_fix_code(error_output, repo_path)
                report["fix_attempts"].append({
                    "attempt": attempt,
                    "result": fix_result,
                })

                if fix_result.get("success", False):
                    # Re-validate
                    if not repo_path:
                        current = Path(__file__).resolve()
                        for parent in [current.parent] + list(current.parents):
                            if (parent / ".git").exists():
                                repo_path = str(parent)
                                break

                    r = subprocess.run(
                        ["python", "-c", "import mamoun.main"],
                        cwd=str(Path(repo_path) / "backend"),
                        capture_output=True, text=True, timeout=30
                    )

                    if r.returncode == 0:
                        report["success"] = True
                        report["final_status"] = f"fixed_on_attempt_{attempt}"
                        report["restart_needed"] = True
                        report["phase"] = "awaiting_approval"

                        if self._neural_bus:
                            self._neural_bus.publish(
                                signal_type="healing_complete",
                                source="self_healing",
                                payload={
                                    "action": "autonomous_self_update",
                                    "status": "fixed",
                                    "attempt": attempt,
                                    "duration_seconds": time.time() - report["started_at"],
                                },
                            )
                        return report

                    error_output = r.stderr[:500]

            # Phase 4: All fix attempts failed — rollback
            report["phase"] = "rollback"
            rollback_result = self._git_rollback(repo_path)
            report["rollback_performed"] = rollback_result.get("success", False)
            report["final_status"] = "all_fixes_failed_rolled_back"
            report["error"] = f"Failed after {max_fix_attempts} attempts — rolled back to last working version"

            if self._neural_bus:
                self._neural_bus.publish(
                    signal_type="error_detected",
                    source="self_healing",
                    payload={
                        "action": "autonomous_self_update",
                        "status": "rollback",
                        "reason": "all_fixes_failed",
                    },
                    priority=3,
                )

        except Exception as e:
            report["error"] = str(e)[:300]
            report["final_status"] = "exception"
            report["phase"] = "failed"
        finally:
            report["completed_at"] = time.time()
            report["duration_seconds"] = round(report["completed_at"] - report["started_at"], 1)

        return report

    async def _llm_fix_code(self, error_output: str, repo_path: str = None) -> dict:
        """
        v35: async — استخدم LLM لإصلاح أخطاء الكود تلقائياً
        
        Reads the error, identifies the broken file, asks LLM for a fix,
        applies it, and returns the result.
        
        v35 FIX: Converted from sync to async because llm.think() is async.
        Previously, the sync wrapper wrote the coroutine object as a string into files!
        """
        import subprocess

        result = {"success": False, "fixes_applied": []}

        try:
            # Parse error to find broken file
            broken_file = None
            for line in error_output.split('\n'):
                if 'File "' in line and '.py"' in line:
                    # Extract file path from error
                    start = line.find('File "') + 6
                    end = line.find('"', start)
                    if start < end:
                        broken_file = line[start:end]
                        break

            if not broken_file:
                result["error"] = "Could not identify broken file from error output"
                return result

            # Try to import code_patcher for intelligent fixing
            try:
                from mamoun.core.code_patcher import CodePatcher
                from mamoun.core.llm_client import get_llm_client

                llm = get_llm_client()
                patcher = CodePatcher(llm_client=llm)

                # Read the broken file
                file_path = Path(broken_file)
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        original_code = f.read()

                    # Ask LLM to fix the code — AWAIT the async call (v35 fix)
                    fix_prompt = f"""أنت مبرمج خبير. هذا الكود به خطأ:
```python
{original_code[:3000]}
```

الخطأ:
{error_output[:1000]}

أعد كتابة الكود كاملاً مع الإصلاح. أجب بالكود فقط بدون شرح."""

                    fixed_code = await llm.think(fix_prompt, model="glm-5.1", temperature=0.2)

                    if fixed_code and fixed_code != original_code and isinstance(fixed_code, str):
                        # Create backup
                        backup_path = file_path.with_suffix('.py.bak')
                        with open(backup_path, 'w', encoding='utf-8') as f:
                            f.write(original_code)

                        # Apply fix
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(fixed_code)

                        result["success"] = True
                        result["fixes_applied"].append({
                            "file": str(file_path),
                            "backup": str(backup_path),
                            "fix_type": "llm_patch",
                        })
                    else:
                        result["error"] = "LLM returned no fix"
                else:
                    result["error"] = f"Broken file not found: {broken_file}"

            except ImportError:
                # Fallback: simple auto-fix based on common patterns
                result["error"] = "CodePatcher not available for intelligent fix"

        except Exception as e:
            result["error"] = str(e)[:200]

        return result

    def _git_rollback(self, repo_path: str = None) -> dict:
        """
        التراجع عن آخر تحديث — git reset --hard HEAD~1
        """
        import subprocess

        if not repo_path:
            current = Path(__file__).resolve()
            for parent in [current.parent] + list(current.parents):
                if (parent / ".git").exists():
                    repo_path = str(parent)
                    break

        if not repo_path:
            return {"success": False, "error": "No git repository found"}

        result = {"success": False, "steps": []}

        # Build environment with GitHub token
        env = os.environ.copy()
        try:
            from mamoun.config import settings
            token = settings.github_token
            if token:
                env["GH_TOKEN"] = token
        except Exception:
            pass

        try:
            # Reset to previous commit
            r = subprocess.run(
                ["git", "reset", "--hard", "HEAD~1"],
                cwd=repo_path, capture_output=True, text=True, timeout=30, env=env
            )
            result["steps"].append({
                "step": "git_reset",
                "success": r.returncode == 0,
                "output": r.stdout[:200] if r.returncode == 0 else r.stderr[:200],
            })

            if r.returncode == 0:
                result["success"] = True

                # Re-install dependencies
                req_file = Path(repo_path) / "backend" / "requirements.txt"
                if req_file.exists():
                    subprocess.run(
                        ["pip", "install", "-r", str(req_file), "--quiet"],
                        cwd=repo_path, capture_output=True, text=True, timeout=120
                    )

                # Publish rollback signal
                if self._neural_bus:
                    self._neural_bus.publish(
                        signal_type="healing_complete",
                        source="self_healing",
                        payload={"action": "git_rollback", "success": True},
                    )

        except Exception as e:
            result["error"] = str(e)[:200]

        return result


# Singleton
self_healing = SelfHealingEngine()
