"""
BABSHARQII v40.0 — Monitoring Manager
Centralized monitoring for system metrics, API response times,
error rates, brain performance, health checks, and alerting.
"""

import os
import time
import threading
import subprocess
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from collections import deque


@dataclass
class SystemMetrics:
    """Current system metrics."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0
    disk_percent: float = 0.0
    disk_used_gb: float = 0.0
    disk_total_gb: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    load_average_1m: float = 0.0
    uptime_seconds: float = 0.0
    timestamp: float = 0.0


@dataclass
class ApiMetrics:
    """API response time and error rate metrics."""
    total_requests: int = 0
    total_errors: int = 0
    avg_response_time_ms: float = 0.0
    p50_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    error_rate_percent: float = 0.0
    requests_per_minute: float = 0.0


@dataclass
class BrainMetrics:
    """Brain performance metrics."""
    brain_id: str = ""
    confidence: float = 0.0
    latency_ms: float = 0.0
    requests_count: int = 0
    error_count: int = 0
    last_activity: float = 0.0


@dataclass
class Alert:
    """A monitoring alert."""
    id: str = ""
    severity: str = "warning"  # info, warning, critical
    category: str = ""  # cpu, memory, disk, api, brain
    message: str = ""
    message_ar: str = ""
    timestamp: float = 0.0
    resolved: bool = False
    value: float = 0.0
    threshold: float = 0.0


# ── Alert Thresholds ─────────────────────────────────────────────

ALERT_THRESHOLDS = {
    "cpu_percent": {"warning": 80, "critical": 95},
    "memory_percent": {"warning": 85, "critical": 95},
    "disk_percent": {"warning": 85, "critical": 95},
    "api_response_time_ms": {"warning": 2000, "critical": 5000},
    "api_error_rate_percent": {"warning": 5, "critical": 15},
}


class MonitoringManager:
    """
    Centralized monitoring for BABSHARQII.
    
    Features:
    - System metrics collection (CPU, memory, disk, network)
    - API response time tracking
    - Error rate tracking
    - Brain performance tracking
    - Health check aggregation
    - Alerting with configurable thresholds
    - Prometheus-compatible metrics endpoint
    """
    
    def __init__(self):
        self._start_time = time.time()
        self._system_metrics = SystemMetrics()
        self._api_metrics = ApiMetrics()
        self._brain_metrics: dict[str, BrainMetrics] = {}
        self._alerts: list[Alert] = []
        self._response_times: deque = deque(maxlen=1000)
        self._request_timestamps: deque = deque(maxlen=1000)
        self._lock = threading.Lock()
        self._last_network_sent = 0
        self._last_network_recv = 0
        self._collection_count = 0
    
    # ── System Metrics Collection ────────────────────────────────
    
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        metrics = SystemMetrics(timestamp=time.time())
        
        try:
            # CPU usage
            result = subprocess.run(
                ["python3", "-c", "import psutil; print(psutil.cpu_percent(interval=0.1))"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                metrics.cpu_percent = float(result.stdout.strip())
        except Exception:
            # Fallback: read from /proc/stat on Linux
            try:
                metrics.cpu_percent = self._read_cpu_from_proc()
            except Exception:
                metrics.cpu_percent = 0.0
        
        try:
            # Memory usage
            result = subprocess.run(
                ["python3", "-c", 
                 "import psutil; m=psutil.virtual_memory(); "
                 "print(f'{m.percent},{m.used/1024/1024:.0f},{m.total/1024/1024:.0f}')"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(",")
                metrics.memory_percent = float(parts[0])
                metrics.memory_used_mb = float(parts[1])
                metrics.memory_total_mb = float(parts[2])
        except Exception:
            try:
                metrics.memory_percent = self._read_memory_from_proc()
            except Exception:
                metrics.memory_percent = 0.0
        
        try:
            # Disk usage
            result = subprocess.run(
                ["python3", "-c",
                 "import psutil; d=psutil.disk_usage('/'); "
                 "print(f'{d.percent},{d.used/1024/1024/1024:.1f},{d.total/1024/1024/1024:.1f}')"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(",")
                metrics.disk_percent = float(parts[0])
                metrics.disk_used_gb = float(parts[1])
                metrics.disk_total_gb = float(parts[2])
        except Exception:
            metrics.disk_percent = 0.0
        
        try:
            # Load average
            load = os.getloadavg()
            metrics.load_average_1m = load[0]
        except (AttributeError, OSError):
            metrics.load_average_1m = 0.0
        
        try:
            # Network I/O
            result = subprocess.run(
                ["python3", "-c",
                 "import psutil; n=psutil.net_io_counters(); "
                 "print(f'{n.bytes_sent},{n.bytes_recv}')"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(",")
                metrics.network_bytes_sent = int(parts[0])
                metrics.network_bytes_recv = int(parts[1])
        except Exception:
            pass
        
        metrics.uptime_seconds = time.time() - self._start_time
        
        with self._lock:
            self._system_metrics = metrics
            self._collection_count += 1
        
        # Check thresholds and generate alerts
        self._check_thresholds(metrics)
        
        return metrics
    
    def _read_cpu_from_proc(self) -> float:
        """Read CPU usage from /proc/stat (Linux fallback)."""
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline()
            values = [int(x) for x in line.split()[1:]]
            idle = values[3]
            total = sum(values)
            return round((1 - idle / total) * 100, 1) if total > 0 else 0.0
        except Exception:
            return 0.0
    
    def _read_memory_from_proc(self) -> float:
        """Read memory usage from /proc/meminfo (Linux fallback)."""
        try:
            info = {}
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split()
                    key = parts[0].rstrip(":")
                    value = int(parts[1])  # in kB
                    info[key] = value
            total = info.get("MemTotal", 0)
            available = info.get("MemAvailable", 0)
            if total > 0:
                return round((1 - available / total) * 100, 1)
        except Exception:
            pass
        return 0.0
    
    # ── API Metrics Tracking ─────────────────────────────────────
    
    def record_request(self, response_time_ms: float, is_error: bool = False):
        """Record an API request for metrics tracking."""
        with self._lock:
            self._response_times.append(response_time_ms)
            self._request_timestamps.append(time.time())
            self._api_metrics.total_requests += 1
            if is_error:
                self._api_metrics.total_errors += 1
    
    def _compute_api_metrics(self) -> ApiMetrics:
        """Compute API metrics from recorded data."""
        with self._lock:
            metrics = ApiMetrics(
                total_requests=self._api_metrics.total_requests,
                total_errors=self._api_metrics.total_errors,
            )
            
            if self._response_times:
                times = sorted(self._response_times)
                metrics.avg_response_time_ms = round(sum(times) / len(times), 1)
                metrics.p50_response_time_ms = round(times[len(times) // 2], 1)
                metrics.p95_response_time_ms = round(times[int(len(times) * 0.95)], 1)
                metrics.p99_response_time_ms = round(times[int(len(times) * 0.99)], 1)
            
            if metrics.total_requests > 0:
                metrics.error_rate_percent = round(
                    (metrics.total_errors / metrics.total_requests) * 100, 2
                )
            
            # Requests per minute (from last 60s of timestamps)
            now = time.time()
            recent = [t for t in self._request_timestamps if now - t < 60]
            metrics.requests_per_minute = round(len(recent), 1)
            
            return metrics
    
    # ── Brain Performance Tracking ───────────────────────────────
    
    def update_brain_metrics(
        self,
        brain_id: str,
        confidence: float = 0.0,
        latency_ms: float = 0.0,
        is_error: bool = False,
    ):
        """Update metrics for a specific brain."""
        with self._lock:
            if brain_id not in self._brain_metrics:
                self._brain_metrics[brain_id] = BrainMetrics(brain_id=brain_id)
            
            bm = self._brain_metrics[brain_id]
            bm.confidence = confidence
            bm.latency_ms = latency_ms
            bm.requests_count += 1
            if is_error:
                bm.error_count += 1
            bm.last_activity = time.time()
    
    # ── Health Check Aggregation ─────────────────────────────────
    
    def get_health_aggregation(self) -> dict:
        """Get aggregated health status."""
        system = self._system_metrics
        api = self._compute_api_metrics()
        
        # Compute health scores (0-100)
        cpu_health = max(0, 100 - system.cpu_percent)
        memory_health = max(0, 100 - system.memory_percent)
        disk_health = max(0, 100 - system.disk_percent)
        
        api_health = 100
        if api.error_rate_percent > 5:
            api_health = max(0, 100 - (api.error_rate_percent * 5))
        
        brain_health = 100
        if self._brain_metrics:
            avg_confidence = sum(b.confidence for b in self._brain_metrics.values()) / len(self._brain_metrics)
            brain_health = round(avg_confidence * 100)
        
        # Overall health
        overall = round(
            (cpu_health * 0.25 + memory_health * 0.2 + disk_health * 0.15 +
             api_health * 0.2 + brain_health * 0.2)
        )
        
        # Determine status
        if overall >= 90:
            status = "healthy"
            status_ar = "سليم"
        elif overall >= 70:
            status = "degraded"
            status_ar = "متدهور"
        elif overall >= 50:
            status = "warning"
            status_ar = "تحذير"
        else:
            status = "critical"
            status_ar = "حرج"
        
        return {
            "overall_score": overall,
            "status": status,
            "status_ar": status_ar,
            "components": {
                "cpu": {"score": round(cpu_health), "label": "المعالج"},
                "memory": {"score": round(memory_health), "label": "الذاكرة"},
                "disk": {"score": round(disk_health), "label": "القرص"},
                "api": {"score": round(api_health), "label": "واجهة البرمجة"},
                "brains": {"score": brain_health, "label": "الأدمغة"},
            },
            "uptime_seconds": system.uptime_seconds,
            "timestamp": time.time(),
        }
    
    # ── Alerting ─────────────────────────────────────────────────
    
    def _check_thresholds(self, metrics: SystemMetrics):
        """Check metrics against thresholds and generate alerts."""
        now = time.time()
        
        # CPU alerts
        if metrics.cpu_percent > ALERT_THRESHOLDS["cpu_percent"]["critical"]:
            self._add_alert(Alert(
                id=f"cpu_crit_{int(now)}",
                severity="critical",
                category="cpu",
                message=f"CPU usage critical: {metrics.cpu_percent:.1f}%",
                message_ar=f"استخدام المعالج حرج: {metrics.cpu_percent:.1f}%",
                timestamp=now,
                value=metrics.cpu_percent,
                threshold=ALERT_THRESHOLDS["cpu_percent"]["critical"],
            ))
        elif metrics.cpu_percent > ALERT_THRESHOLDS["cpu_percent"]["warning"]:
            self._add_alert(Alert(
                id=f"cpu_warn_{int(now)}",
                severity="warning",
                category="cpu",
                message=f"CPU usage high: {metrics.cpu_percent:.1f}%",
                message_ar=f"استخدام المعالج مرتفع: {metrics.cpu_percent:.1f}%",
                timestamp=now,
                value=metrics.cpu_percent,
                threshold=ALERT_THRESHOLDS["cpu_percent"]["warning"],
            ))
        
        # Memory alerts
        if metrics.memory_percent > ALERT_THRESHOLDS["memory_percent"]["critical"]:
            self._add_alert(Alert(
                id=f"mem_crit_{int(now)}",
                severity="critical",
                category="memory",
                message=f"Memory usage critical: {metrics.memory_percent:.1f}%",
                message_ar=f"استخدام الذاكرة حرج: {metrics.memory_percent:.1f}%",
                timestamp=now,
                value=metrics.memory_percent,
                threshold=ALERT_THRESHOLDS["memory_percent"]["critical"],
            ))
        elif metrics.memory_percent > ALERT_THRESHOLDS["memory_percent"]["warning"]:
            self._add_alert(Alert(
                id=f"mem_warn_{int(now)}",
                severity="warning",
                category="memory",
                message=f"Memory usage high: {metrics.memory_percent:.1f}%",
                message_ar=f"استخدام الذاكرة مرتفع: {metrics.memory_percent:.1f}%",
                timestamp=now,
                value=metrics.memory_percent,
                threshold=ALERT_THRESHOLDS["memory_percent"]["warning"],
            ))
        
        # Disk alerts
        if metrics.disk_percent > ALERT_THRESHOLDS["disk_percent"]["critical"]:
            self._add_alert(Alert(
                id=f"disk_crit_{int(now)}",
                severity="critical",
                category="disk",
                message=f"Disk usage critical: {metrics.disk_percent:.1f}%",
                message_ar=f"استخدام القرص حرج: {metrics.disk_percent:.1f}%",
                timestamp=now,
                value=metrics.disk_percent,
                threshold=ALERT_THRESHOLDS["disk_percent"]["critical"],
            ))
        elif metrics.disk_percent > ALERT_THRESHOLDS["disk_percent"]["warning"]:
            self._add_alert(Alert(
                id=f"disk_warn_{int(now)}",
                severity="warning",
                category="disk",
                message=f"Disk usage high: {metrics.disk_percent:.1f}%",
                message_ar=f"استخدام القرص مرتفع: {metrics.disk_percent:.1f}%",
                timestamp=now,
                value=metrics.disk_percent,
                threshold=ALERT_THRESHOLDS["disk_percent"]["warning"],
            ))
    
    def _add_alert(self, alert: Alert):
        """Add an alert, avoiding duplicates within 60 seconds."""
        with self._lock:
            # Check for duplicate
            for existing in self._alerts:
                if (existing.category == alert.category and 
                    existing.severity == alert.severity and
                    not existing.resolved and
                    alert.timestamp - existing.timestamp < 60):
                    return
            
            self._alerts.append(alert)
            # Keep only last 100 alerts
            if len(self._alerts) > 100:
                self._alerts = self._alerts[-100:]
    
    # ── Get All Metrics ──────────────────────────────────────────
    
    def get_all_metrics(self) -> dict:
        """Get all metrics in a single response."""
        system = self._system_metrics
        api = self._compute_api_metrics()
        
        # Collect fresh metrics if stale (> 10s old)
        if time.time() - system.timestamp > 10:
            system = self.collect_system_metrics()
        
        return {
            "system": {
                "cpu_percent": system.cpu_percent,
                "memory_percent": system.memory_percent,
                "memory_used_mb": round(system.memory_used_mb, 1),
                "memory_total_mb": round(system.memory_total_mb, 1),
                "disk_percent": system.disk_percent,
                "disk_used_gb": round(system.disk_used_gb, 1),
                "disk_total_gb": round(system.disk_total_gb, 1),
                "network_bytes_sent": system.network_bytes_sent,
                "network_bytes_recv": system.network_bytes_recv,
                "load_average_1m": round(system.load_average_1m, 2),
                "uptime_seconds": round(system.uptime_seconds, 1),
            },
            "api": {
                "total_requests": api.total_requests,
                "total_errors": api.total_errors,
                "avg_response_time_ms": api.avg_response_time_ms,
                "p50_response_time_ms": api.p50_response_time_ms,
                "p95_response_time_ms": api.p95_response_time_ms,
                "p99_response_time_ms": api.p99_response_time_ms,
                "error_rate_percent": api.error_rate_percent,
                "requests_per_minute": api.requests_per_minute,
            },
            "brains": {
                brain_id: {
                    "confidence": bm.confidence,
                    "latency_ms": round(bm.latency_ms, 1),
                    "requests_count": bm.requests_count,
                    "error_count": bm.error_count,
                    "last_activity_ago_seconds": round(time.time() - bm.last_activity, 1) if bm.last_activity > 0 else None,
                }
                for brain_id, bm in self._brain_metrics.items()
            },
            "collection_count": self._collection_count,
            "timestamp": time.time(),
        }
    
    def get_alerts(self) -> dict:
        """Get active alerts."""
        with self._lock:
            active = [a for a in self._alerts if not a.resolved]
            return {
                "alerts": [
                    {
                        "id": a.id,
                        "severity": a.severity,
                        "category": a.category,
                        "message": a.message,
                        "message_ar": a.message_ar,
                        "timestamp": a.timestamp,
                        "datetime": datetime.fromtimestamp(a.timestamp).isoformat(),
                        "value": round(a.value, 1),
                        "threshold": a.threshold,
                    }
                    for a in active[-20:]
                ],
                "total_active": len(active),
            }
    
    # ── Prometheus-Compatible Metrics ────────────────────────────
    
    def get_prometheus_metrics(self) -> str:
        """Generate Prometheus-compatible metrics text."""
        system = self._system_metrics
        api = self._compute_api_metrics()
        
        lines = [
            "# HELP babsharqii_cpu_percent CPU usage percentage",
            "# TYPE babsharqii_cpu_percent gauge",
            f"babsharqii_cpu_percent {system.cpu_percent}",
            "",
            "# HELP babsharqii_memory_percent Memory usage percentage",
            "# TYPE babsharqii_memory_percent gauge",
            f"babsharqii_memory_percent {system.memory_percent}",
            "",
            "# HELP babsharqii_memory_used_mb Memory used in MB",
            "# TYPE babsharqii_memory_used_mb gauge",
            f"babsharqii_memory_used_mb {system.memory_used_mb:.1f}",
            "",
            "# HELP babsharqii_disk_percent Disk usage percentage",
            "# TYPE babsharqii_disk_percent gauge",
            f"babsharqii_disk_percent {system.disk_percent}",
            "",
            "# HELP babsharqii_api_total_requests Total API requests",
            "# TYPE babsharqii_api_total_requests counter",
            f"babsharqii_api_total_requests {api.total_requests}",
            "",
            "# HELP babsharqii_api_total_errors Total API errors",
            "# TYPE babsharqii_api_total_errors counter",
            f"babsharqii_api_total_errors {api.total_errors}",
            "",
            "# HELP babsharqii_api_error_rate_percent API error rate percentage",
            "# TYPE babsharqii_api_error_rate_percent gauge",
            f"babsharqii_api_error_rate_percent {api.error_rate_percent}",
            "",
            "# HELP babsharqii_api_avg_response_time_ms Average API response time in ms",
            "# TYPE babsharqii_api_avg_response_time_ms gauge",
            f"babsharqii_api_avg_response_time_ms {api.avg_response_time_ms}",
            "",
            "# HELP babsharqii_uptime_seconds System uptime in seconds",
            "# TYPE babsharqii_uptime_seconds gauge",
            f"babsharqii_uptime_seconds {system.uptime_seconds:.1f}",
        ]
        
        # Brain metrics
        for brain_id, bm in self._brain_metrics.items():
            lines.extend([
                "",
                f'# HELP babsharqii_brain_confidence Confidence for brain "{brain_id}"',
                f'# TYPE babsharqii_brain_confidence gauge',
                f'babsharqii_brain_confidence{{brain="{brain_id}"}} {bm.confidence}',
                "",
                f'# HELP babsharqii_brain_latency_ms Latency for brain "{brain_id}"',
                f'# TYPE babsharqii_brain_latency_ms gauge',
                f'babsharqii_brain_latency_ms{{brain="{brain_id}"}} {bm.latency_ms:.1f}',
            ])
        
        return "\n".join(lines) + "\n"


# Singleton
monitoring_manager = MonitoringManager()
