"""
BABSHARQII v40.0 — Budget Monitor
مراقب الميزانية — يراقب استهلاك واجهات البرمجة والوقت والموارد،
يتنبأ بالتجاوزات، ويقترح تعديلات وسيطة.

Monitors real API consumption, execution time, and server resources,
predicts overruns, and suggests intermediate adjustments.

Feature Flag: MAMOUN_BUDGET_MONITOR_ENABLED (default: false)
"""

import os
import time
import uuid
import logging
import threading
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)

# ── Feature Flag ────────────────────────────────────────────────────
BUDGET_MONITOR_ENABLED = os.getenv(
    "MAMOUN_BUDGET_MONITOR_ENABLED", "false"
).lower() in ("true", "1", "yes")

# ── Alert Thresholds — عتبات التنبيه ─────────────────────────────
ALERT_THRESHOLDS = [0.80, 0.90, 0.95]


class SpendingCategory(Enum):
    """فئات الإنفاق — Spending categories."""
    API = "api"
    COMPUTE = "compute"
    STORAGE = "storage"
    OTHER = "other"


class AlertSeverity(Enum):
    """مستوى خطورة التنبيه — Alert severity levels."""
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    """نوع التنبيه — Alert type."""
    BUDGET = "budget"
    TIME = "time"
    RESOURCE = "resource"


# ═══════════════════════════════════════════════════════════════════
#  Data Classes — فئات البيانات
# ═══════════════════════════════════════════════════════════════════

@dataclass
class SpendingEntry:
    """
    سجل إنفاق — A single spending record.
    """
    entry_id: str = ""
    category: str = "api"        # SpendingCategory value
    amount: float = 0.0
    unit: str = "USD"
    description: str = ""
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.entry_id:
            self.entry_id = f"spe_{uuid.uuid4().hex[:8]}"
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BudgetStatus:
    """
    حالة الميزانية — Current budget status snapshot.
    """
    total_budget: float = 0.0
    spent: float = 0.0
    remaining: float = 0.0
    usage_percentage: float = 0.0
    by_category: dict = field(default_factory=dict)  # category -> amount
    period: str = "daily"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TaskEstimate:
    """
    تقدير المهمة — Estimated resource consumption for a task.
    """
    estimated_cost: float = 0.0
    estimated_duration: float = 0.0    # seconds
    estimated_api_calls: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PredictionResult:
    """
    نتيجة التنبؤ — Prediction of whether a task can complete within budget.
    """
    can_complete: bool = True
    budget_remaining_after: float = 0.0
    time_remaining_after: float = 0.0
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BudgetAlert:
    """
    تنبيه الميزانية — A budget/time/resource alert.
    """
    alert_type: str = "budget"       # AlertType value
    severity: str = "warning"        # AlertSeverity value
    message: str = ""
    message_ar: str = ""
    current_value: float = 0.0
    limit_value: float = 0.0
    suggested_action: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class OptimizationSuggestion:
    """
    اقتراح تحسين — Suggestion to optimize spending or resource usage.
    """
    category: str = ""
    current_cost: float = 0.0
    optimized_cost: float = 0.0
    savings: float = 0.0
    description: str = ""
    description_ar: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════
#  Budget Monitor — مراقب الميزانية
# ═══════════════════════════════════════════════════════════════════

class BudgetMonitor:
    """
    مراقب الميزانية — Budget Monitor.

    Tracks spending (API calls, compute time, monetary costs),
    monitors time (task duration, remaining time), monitors resources
    (memory, CPU — simulated), predicts overruns, and suggests
    optimizations when budget is running low.

    Usage:
        monitor = BudgetMonitor()
        monitor.set_budget_limit("budget", 100.0)
        monitor.set_budget_limit("time", 3600.0)
        monitor.record_spending(SpendingEntry(
            category="api", amount=2.50, description="LLM call",
        ))
        alerts = monitor.check_alerts()
        status = monitor.get_current_budget()
    """

    def __init__(self):
        self._spending: list[SpendingEntry] = []
        self._limits: dict[str, float] = {}       # limit_type -> value
        self._spent: dict[str, float] = {}         # limit_type -> total spent
        self._alerts: list[BudgetAlert] = []
        self._fired_thresholds: dict[str, set] = {} # limit_type -> set of crossed thresholds
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._active = True

        # Default limits — حدود افتراضية
        self._limits["budget"] = 0.0    # No budget limit until set
        self._limits["time"] = 0.0      # No time limit until set
        self._limits["api_calls"] = 0   # No API call limit until set
        self._limits["cpu_percent"] = 0.0
        self._limits["memory_mb"] = 0.0

        for key in self._limits:
            self._spent[key] = 0.0
            self._fired_thresholds[key] = set()

    # ── Recording — التسجيل ──────────────────────────────────────

    def record_spending(self, entry: SpendingEntry) -> None:
        """
        تسجيل إنفاق — Record a spending entry.

        Updates the spent totals for the appropriate category and
        checks for threshold crossings.
        """
        with self._lock:
            self._spending.append(entry)

            # Map category to budget — ربط الفئة بالميزانية
            cat = entry.category
            if cat in (SpendingCategory.API.value, SpendingCategory.COMPUTE.value,
                       SpendingCategory.STORAGE.value, SpendingCategory.OTHER.value):
                self._spent["budget"] = self._spent.get("budget", 0.0) + entry.amount

            # Track API calls specifically
            if cat == SpendingCategory.API.value:
                self._spent["api_calls"] = self._spent.get("api_calls", 0.0) + 1

            # Track time (if unit is seconds)
            if entry.unit.lower() in ("seconds", "secs", "s"):
                self._spent["time"] = self._spent.get("time", 0.0) + entry.amount

        logger.debug(
            f"BudgetMonitor: Recorded {entry.amount} {entry.unit} "
            f"for '{entry.description}' [{cat}]"
        )

        # Check alerts after recording — فحص التنبيهات بعد التسجيل
        self._check_thresholds()

    # ── Budget Status — حالة الميزانية ───────────────────────────

    def get_current_budget(self) -> BudgetStatus:
        """
        الحصول على حالة الميزانية الحالية — Get current budget status.
        """
        with self._lock:
            total = self._limits.get("budget", 0.0)
            spent = self._spent.get("budget", 0.0)
            remaining = max(0.0, total - spent)
            pct = (spent / total * 100) if total > 0 else 0.0

            # Breakdown by category — تفصيل حسب الفئة
            by_category: dict[str, float] = {}
            for entry in self._spending:
                by_category[entry.category] = by_category.get(
                    entry.category, 0.0
                ) + entry.amount

            elapsed = time.time() - self._start_time
            period = "daily" if elapsed < 86400 else "multi-day"

            return BudgetStatus(
                total_budget=total,
                spent=round(spent, 4),
                remaining=round(remaining, 4),
                usage_percentage=round(pct, 2),
                by_category={k: round(v, 4) for k, v in by_category.items()},
                period=period,
            )

    # ── Prediction — التنبؤ ──────────────────────────────────────

    def predict_remaining(self, task_estimate: TaskEstimate) -> PredictionResult:
        """
        التنبؤ بالباقي — Predict whether a task can complete within
        remaining budget and time.

        Args:
            task_estimate: Estimated cost, duration, and API calls for the task.

        Returns:
            PredictionResult with can_complete flag and confidence.
        """
        with self._lock:
            budget_total = self._limits.get("budget", 0.0)
            budget_spent = self._spent.get("budget", 0.0)
            budget_remaining = max(0.0, budget_total - budget_spent)

            time_total = self._limits.get("time", 0.0)
            time_spent = self._spent.get("time", 0.0)
            time_remaining = max(0.0, time_total - time_spent)

            api_total = self._limits.get("api_calls", 0)
            api_spent = self._spent.get("api_calls", 0.0)
            api_remaining = max(0, api_total - api_spent)

        # Check if task fits — فحص إذا كانت المهمة تناسب
        budget_ok = (
            budget_total <= 0  # No limit set
            or task_estimate.estimated_cost <= budget_remaining
        )
        time_ok = (
            time_total <= 0
            or task_estimate.estimated_duration <= time_remaining
        )
        api_ok = (
            api_total <= 0
            or task_estimate.estimated_api_calls <= api_remaining
        )

        can_complete = budget_ok and time_ok and api_ok

        # Confidence based on how much headroom remains — الثقة بناءً على الهامش المتبقي
        confidences = []
        if budget_total > 0:
            headroom = budget_remaining / max(0.01, task_estimate.estimated_cost)
            confidences.append(min(1.0, max(0.0, headroom / 2.0)))
        if time_total > 0:
            headroom = time_remaining / max(0.01, task_estimate.estimated_duration)
            confidences.append(min(1.0, max(0.0, headroom / 2.0)))
        if api_total > 0:
            headroom = api_remaining / max(1, task_estimate.estimated_api_calls)
            confidences.append(min(1.0, max(0.0, headroom / 2.0)))

        confidence = (
            sum(confidences) / len(confidences)
            if confidences else 1.0
        )

        return PredictionResult(
            can_complete=can_complete,
            budget_remaining_after=round(
                budget_remaining - task_estimate.estimated_cost, 4
            ),
            time_remaining_after=round(
                time_remaining - task_estimate.estimated_duration, 2
            ),
            confidence=round(confidence, 4),
        )

    # ── Alerts — التنبيهات ───────────────────────────────────────

    def check_alerts(self) -> list:
        """
        فحص التنبيهات — Check for and return current budget/time/resource alerts.
        """
        self._check_thresholds()
        with self._lock:
            return list(self._alerts)

    def _check_thresholds(self):
        """
        فحص عتبات التنبيه — Check spending against thresholds.
        Generates alerts at 80%, 90%, 95% usage.
        """
        with self._lock:
            for limit_type, limit_value in self._limits.items():
                if limit_value <= 0:
                    continue

                spent = self._spent.get(limit_type, 0.0)
                pct = spent / limit_value if limit_value > 0 else 0.0

                for threshold in ALERT_THRESHOLDS:
                    if pct >= threshold and threshold not in self._fired_thresholds.get(limit_type, set()):
                        self._fired_thresholds.setdefault(limit_type, set()).add(threshold)
                        severity = (
                            AlertSeverity.CRITICAL.value
                            if threshold >= 0.90
                            else AlertSeverity.WARNING.value
                        )
                        alert_type = self._map_alert_type(limit_type)
                        suggested = self._suggest_for_threshold(
                            limit_type, pct, threshold
                        )

                        # Arabic / English messages
                        msg_en = (
                            f"{limit_type} usage at {pct*100:.1f}% "
                            f"(threshold {threshold*100:.0f}%)"
                        )
                        msg_ar = (
                            f"استخدام {self._limit_name_ar(limit_type)} "
                            f"عند {pct*100:.1f}% "
                            f"(عتبة {threshold*100:.0f}%)"
                        )

                        alert = BudgetAlert(
                            alert_type=alert_type,
                            severity=severity,
                            message=msg_en,
                            message_ar=msg_ar,
                            current_value=round(spent, 4),
                            limit_value=limit_value,
                            suggested_action=suggested,
                        )
                        self._alerts.append(alert)

                        logger.warning(
                            f"BudgetAlert: [{severity}] {msg_en}"
                        )

    @staticmethod
    def _map_alert_type(limit_type: str) -> str:
        """تحويل نوع الحد إلى نوع تنبيه — Map limit type to alert type."""
        mapping = {
            "budget": AlertType.BUDGET.value,
            "time": AlertType.TIME.value,
            "api_calls": AlertType.BUDGET.value,
            "cpu_percent": AlertType.RESOURCE.value,
            "memory_mb": AlertType.RESOURCE.value,
        }
        return mapping.get(limit_type, AlertType.BUDGET.value)

    @staticmethod
    def _limit_name_ar(limit_type: str) -> str:
        """اسم الحد بالعربية — Arabic name for a limit type."""
        names = {
            "budget": "الميزانية",
            "time": "الوقت",
            "api_calls": "استدعاءات واجهة البرمجة",
            "cpu_percent": "المعالج",
            "memory_mb": "الذاكرة",
        }
        return names.get(limit_type, limit_type)

    @staticmethod
    def _suggest_for_threshold(limit_type: str, pct: float, threshold: float) -> str:
        """اقتراح إجراء — Suggest an action for a threshold breach."""
        if threshold >= 0.95:
            actions = {
                "budget": "Halt non-essential operations immediately — أوقف العمليات غير الضرورية فوراً",
                "time": "Terminate long-running tasks — أنهِ المهام طويلة التشغيل",
                "api_calls": "Cache aggressively and reduce API calls — خزّن مؤقتاً وقلّل الاستدعاءات",
                "cpu_percent": "Scale horizontally or reduce load — توسع أفقي أو خفض الحمل",
                "memory_mb": "Free memory and restart heavy services — حرر الذاكرة وأعد تشغيل الخدمات الثقيلة",
            }
            return actions.get(limit_type, "Reduce usage — خفّض الاستخدام")
        elif threshold >= 0.90:
            actions = {
                "budget": "Switch to cheaper models and batch requests — انتقل لنماذج أرخص وجمع الطلبات",
                "time": "Prioritize critical tasks only — ركّز على المهام الحرجة فقط",
                "api_calls": "Enable response caching — فعّل التخزين المؤقت للاستجابات",
                "cpu_percent": "Defer non-critical computation — أجّل الحوسبة غير الحرجة",
                "memory_mb": "Release unused resources — حرر الموارد غير المستخدمة",
            }
            return actions.get(limit_type, "Optimize usage — حسّن الاستخدام")
        else:
            actions = {
                "budget": "Monitor closely and optimize soon — راقب عن كثب وحسّن قريباً",
                "time": "Track remaining time carefully — تتبع الوقت المتبقي بعناية",
                "api_calls": "Consider caching responses — فكّر في تخزين الاستجابات مؤقتاً",
                "cpu_percent": "Watch for spikes — راقب الارتفاعات المفاجئة",
                "memory_mb": "Monitor allocation — راقب التخصيص",
            }
            return actions.get(limit_type, "Keep monitoring — استمر في المراقبة")

    # ── Limits — الحدود ──────────────────────────────────────────

    def set_budget_limit(self, limit_type: str, limit_value: float) -> None:
        """
        تعيين حد الميزانية — Set a budget/time/resource limit.

        Args:
            limit_type: One of "budget", "time", "api_calls", "cpu_percent", "memory_mb".
            limit_value: The maximum allowed value.
        """
        with self._lock:
            self._limits[limit_type] = limit_value
            if limit_type not in self._spent:
                self._spent[limit_type] = 0.0
            # Reset fired thresholds so new alerts can fire
            self._fired_thresholds[limit_type] = set()

        logger.info(
            f"BudgetMonitor: Set limit '{limit_type}' = {limit_value}"
        )

    # ── Spending History — سجل الإنفاق ───────────────────────────

    def get_spending_history(self, time_range: str = "24h") -> list:
        """
        الحصول على سجل الإنفاق — Get spending entries within a time range.

        Args:
            time_range: "1h", "24h", "7d", "30d", or "all".

        Returns:
            List of spending entry dicts.
        """
        range_seconds = {
            "1h": 3600,
            "24h": 86400,
            "7d": 604800,
            "30d": 2592000,
            "all": float("inf"),
        }
        seconds = range_seconds.get(time_range, 86400)
        cutoff = time.time() - seconds

        with self._lock:
            entries = [
                e.to_dict() for e in self._spending if e.timestamp >= cutoff
            ]
        return entries

    # ── Optimization — التحسين ───────────────────────────────────

    def suggest_optimizations(self, current_plan: dict = None) -> list:
        """
        اقتراح تحسينات — Suggest optimizations based on current spending.

        Analyzes spending patterns and suggests ways to reduce costs
        when budget is running low.

        Args:
            current_plan: Optional dict with plan details (steps, costs).

        Returns:
            List of OptimizationSuggestion objects.
        """
        suggestions: list[OptimizationSuggestion] = []
        status = self.get_current_budget()

        # Only suggest if over 50% usage — اقترح فقط إذا تجاوز الاستخدام 50%
        if status.usage_percentage < 50.0 and status.total_budget > 0:
            return suggestions

        # Analyze by category — تحليل حسب الفئة
        for category, amount in status.by_category.items():
            if category == SpendingCategory.API.value and amount > 0:
                # Suggest caching — اقتراح التخزين المؤقت
                savings = amount * 0.30  # Assume 30% cache hit rate
                suggestions.append(OptimizationSuggestion(
                    category=category,
                    current_cost=round(amount, 4),
                    optimized_cost=round(amount - savings, 4),
                    savings=round(savings, 4),
                    description=(
                        f"Enable API response caching to reduce redundant calls "
                        f"(est. {savings:.2f} savings)"
                    ),
                    description_ar=(
                        f"فعّل التخزين المؤقت لاستجابات واجهة البرمجة لتقليل الاستدعاءات "
                        f"المتكررة (توفير مقدر {savings:.2f})"
                    ),
                ))

            elif category == SpendingCategory.COMPUTE.value and amount > 0:
                # Suggest lighter models — اقتراح نماذج أخف
                savings = amount * 0.25
                suggestions.append(OptimizationSuggestion(
                    category=category,
                    current_cost=round(amount, 4),
                    optimized_cost=round(amount - savings, 4),
                    savings=round(savings, 4),
                    description=(
                        f"Switch to lighter compute options where possible "
                        f"(est. {savings:.2f} savings)"
                    ),
                    description_ar=(
                        f"انتقل لخيارات حوسبة أخف حيثما أمكن "
                        f"(توفير مقدر {savings:.2f})"
                    ),
                ))

            elif category == SpendingCategory.STORAGE.value and amount > 0:
                # Suggest cleanup — اقتراح التنظيف
                savings = amount * 0.20
                suggestions.append(OptimizationSuggestion(
                    category=category,
                    current_cost=round(amount, 4),
                    optimized_cost=round(amount - savings, 4),
                    savings=round(savings, 4),
                    description=(
                        f"Clean up unused storage and compress data "
                        f"(est. {savings:.2f} savings)"
                    ),
                    description_ar=(
                        f"نظّف التخزين غير المستخدم واضغط البيانات "
                        f"(توفير مقدر {savings:.2f})"
                    ),
                ))

        # Sort by savings descending — ترتيب حسب التوفير تنازلياً
        suggestions.sort(key=lambda s: s.savings, reverse=True)
        return suggestions

    # ── Lifecycle — دورة الحياة ──────────────────────────────────

    def get_status(self) -> dict:
        """
        حالة المراقب — Get monitor status.
        """
        with self._lock:
            return {
                "enabled": BUDGET_MONITOR_ENABLED,
                "active": self._active,
                "limits": dict(self._limits),
                "spent": {k: round(v, 4) for k, v in self._spent.items()},
                "spending_entries": len(self._spending),
                "alerts_generated": len(self._alerts),
                "uptime_seconds": round(time.time() - self._start_time, 1),
            }

    async def shutdown(self):
        """
        إيقاف المراقب — Shutdown the budget monitor.
        Clears all spending records, limits, and alerts.
        Compliant with Law 5 (shutdown protocol).
        """
        logger.info(
            "BudgetMonitor: Shutting down — clearing spending and alerts "
            "(Law 5 compliant)"
        )
        with self._lock:
            self._spending.clear()
            self._limits.clear()
            self._spent.clear()
            self._alerts.clear()
            self._fired_thresholds.clear()
            self._active = False


# ── Singleton — النمط المفرد ────────────────────────────────────
budget_monitor = BudgetMonitor()
