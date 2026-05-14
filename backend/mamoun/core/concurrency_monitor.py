"""
BABSHARQII v13.0 — Concurrency Monitor
مراقب التزامن — يتتبع المهام النشطة، زمن الاستجابة، واستهلاك الموارد

Integrates with:
- PriorityQueue: For task metrics
- MonitoringManager: For system metrics
- ConcurrencyDashboard: For real-time UI

Feature Flag: MAMOUN_CONCURRENCY_MODE (default: false)
"""

import os
import time
import logging
import threading
from dataclasses import dataclass, field, asdict
from typing import Optional
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)

CONCURRENCY_ENABLED = os.getenv("MAMOUN_CONCURRENCY_MODE", "false").lower() in ("true", "1", "yes")

# Monitoring configuration
METRICS_WINDOW_SECONDS = 300  # 5-minute rolling window
MAX_METRICS_HISTORY = 1000
ALERT_LATENCY_MS = 5000  # Alert if task takes > 5s
ALERT_QUEUE_SIZE = 150   # Alert if queue > 150


@dataclass
class TaskMetrics:
    """مقاييس مهمة."""
    task_id: str = ""
    name: str = ""
    priority: int = 2
    agent_id: str = ""
    queued_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    wait_time_ms: float = 0.0
    execution_time_ms: float = 0.0
    total_time_ms: float = 0.0
    status: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SystemResourceMetrics:
    """مقاييس موارد النظام."""
    timestamp: float = 0.0
    active_tasks: int = 0
    queued_tasks: int = 0
    completed_tasks: int = 0
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    avg_wait_time_ms: float = 0.0
    avg_execution_time_ms: float = 0.0
    throughput_per_minute: float = 0.0
    error_rate: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConcurrencyAlert:
    """تنبيه التزامن."""
    alert_id: str = ""
    alert_type: str = ""  # high_latency, queue_overload, error_spike, resource_exhaustion
    severity: str = "warning"  # warning, critical
    message: str = ""
    timestamp: float = 0.0
    resolved: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class ConcurrencyMonitor:
    """
    مراقب التزامن — يتتبع أداء المهام المتزامنة.

    Monitors:
    - Active and queued task counts
    - Average wait and execution times
    - System resource usage (CPU, memory)
    - Throughput and error rates
    - Automatic alerts for anomalies

    Usage:
        monitor = ConcurrencyMonitor()
        monitor.record_task_start(task_id, name, priority)
        monitor.record_task_complete(task_id, status)
        dashboard_data = monitor.get_dashboard_data()
    """

    def __init__(self, metrics_window: int = 0):
        self._metrics_window = metrics_window or METRICS_WINDOW_SECONDS
        self._task_metrics: dict[str, TaskMetrics] = {}
        self._metrics_history: deque = deque(maxlen=MAX_METRICS_HISTORY)
        self._alerts: list[ConcurrencyAlert] = []
        self._completed_count = 0
        self._error_count = 0
        self._start_time = time.time()
        self._lock = threading.Lock()
        self._alert_counter = 0

        # Rolling window tracking
        self._recent_completions: deque = deque(maxlen=200)
        self._recent_errors: deque = deque(maxlen=50)

    def record_task_start(self, task_id: str, name: str = "", priority: int = 2, agent_id: str = ""):
        """تسجيل بدء مهمة."""
        with self._lock:
            self._task_metrics[task_id] = TaskMetrics(
                task_id=task_id,
                name=name,
                priority=priority,
                agent_id=agent_id,
                queued_at=time.time(),
                started_at=time.time(),
                status="running",
            )

    def record_task_complete(self, task_id: str, status: str = "completed", error: str = ""):
        """تسجيل اكتمال مهمة."""
        with self._lock:
            metrics = self._task_metrics.get(task_id)
            if not metrics:
                return

            metrics.completed_at = time.time()
            metrics.status = status
            metrics.error = error[:200]

            if metrics.started_at > 0:
                metrics.execution_time_ms = (metrics.completed_at - metrics.started_at) * 1000
                metrics.wait_time_ms = (metrics.started_at - metrics.queued_at) * 1000
                metrics.total_time_ms = (metrics.completed_at - metrics.queued_at) * 1000

            self._completed_count += 1
            self._recent_completions.append(time.time())

            if status == "failed":
                self._error_count += 1
                self._recent_errors.append(time.time())

            # Check for alerts
            self._check_alerts(metrics)

    def record_system_metrics(self, active_tasks: int = 0, queued_tasks: int = 0):
        """تسجيل مقاييس النظام."""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent
        except (ImportError, Exception):
            cpu_percent = 0.0
            memory_percent = 0.0

        # Calculate averages
        avg_wait = 0.0
        avg_exec = 0.0
        recent_metrics = [
            m for m in self._task_metrics.values()
            if m.completed_at > time.time() - self._metrics_window
        ]
        if recent_metrics:
            waits = [m.wait_time_ms for m in recent_metrics if m.wait_time_ms > 0]
            execs = [m.execution_time_ms for m in recent_metrics if m.execution_time_ms > 0]
            avg_wait = sum(waits) / len(waits) if waits else 0
            avg_exec = sum(execs) / len(execs) if execs else 0

        # Throughput: completions per minute
        uptime_minutes = (time.time() - self._start_time) / 60
        throughput = self._completed_count / max(0.1, uptime_minutes)

        # Error rate
        error_rate = self._error_count / max(1, self._completed_count)

        snapshot = SystemResourceMetrics(
            timestamp=time.time(),
            active_tasks=active_tasks,
            queued_tasks=queued_tasks,
            completed_tasks=self._completed_count,
            cpu_percent=round(cpu_percent, 1),
            memory_percent=round(memory_percent, 1),
            avg_wait_time_ms=round(avg_wait, 1),
            avg_execution_time_ms=round(avg_exec, 1),
            throughput_per_minute=round(throughput, 2),
            error_rate=round(error_rate, 4),
        )

        self._metrics_history.append(snapshot)

    def _check_alerts(self, metrics: TaskMetrics):
        """فحص التنبيهات."""
        # High latency alert
        if metrics.execution_time_ms > ALERT_LATENCY_MS:
            self._create_alert(
                "high_latency",
                "warning",
                f"المهمة {metrics.name} استغرقت {metrics.execution_time_ms:.0f}ms (>{ALERT_LATENCY_MS}ms)",
            )

        # Error spike alert
        recent_errors = sum(1 for t in self._recent_errors if t > time.time() - 60)
        if recent_errors > 10:
            self._create_alert(
                "error_spike",
                "critical",
                f"ارتفاع الأخطاء: {recent_errors} في آخر دقيقة",
            )

    def _create_alert(self, alert_type: str, severity: str, message: str):
        """إنشاء تنبيه."""
        self._alert_counter += 1
        alert = ConcurrencyAlert(
            alert_id=f"alert_{self._alert_counter}",
            alert_type=alert_type,
            severity=severity,
            message=message,
            timestamp=time.time(),
        )
        self._alerts.append(alert)
        logger.warning(f"ConcurrencyAlert: [{severity}] {message}")

    def get_dashboard_data(self) -> dict:
        """بيانات لوحة التحكم."""
        # Get latest system metrics
        latest_metrics = self._metrics_history[-1] if self._metrics_history else None

        # Active tasks
        active = [m.to_dict() for m in self._task_metrics.values() if m.status == "running"]

        # Unresolved alerts
        unresolved = [a.to_dict() for a in self._alerts if not a.resolved]

        return {
            "enabled": CONCURRENCY_ENABLED,
            "uptime_seconds": round(time.time() - self._start_time, 1),
            "active_tasks": len(active),
            "active_tasks_list": active[:20],
            "completed_total": self._completed_count,
            "error_total": self._error_count,
            "system_metrics": latest_metrics.to_dict() if latest_metrics else {},
            "metrics_history": [m.to_dict() for m in list(self._metrics_history)[-50:]],
            "alerts": unresolved,
            "alerts_count": len(unresolved),
            "avg_wait_time_ms": latest_metrics.avg_wait_time_ms if latest_metrics else 0,
            "avg_execution_time_ms": latest_metrics.avg_execution_time_ms if latest_metrics else 0,
            "throughput_per_minute": latest_metrics.throughput_per_minute if latest_metrics else 0,
            "error_rate": latest_metrics.error_rate if latest_metrics else 0,
        }

    def resolve_alert(self, alert_id: str) -> bool:
        """حل تنبيه."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                return True
        return False

    def get_status(self) -> dict:
        """حالة المراقب."""
        return {
            "enabled": CONCURRENCY_ENABLED,
            "tasks_tracked": len(self._task_metrics),
            "metrics_history_size": len(self._metrics_history),
            "total_completed": self._completed_count,
            "total_errors": self._error_count,
            "active_alerts": sum(1 for a in self._alerts if not a.resolved),
        }

    async def shutdown(self):
        """إيقاف المراقب — يتوافق مع القانون 5."""
        logger.info("ConcurrencyMonitor: Shutdown complete (Law 5 compliant)")
