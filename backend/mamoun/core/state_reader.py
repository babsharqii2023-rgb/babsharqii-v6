"""
BABSHARQII v40.0 — Real State Reader
Reads actual system state: CPU, memory, disk, processes, logs, API health.
"""

import time
import psutil
import threading
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import httpx


@dataclass
class SystemState:
    """Real system state snapshot."""
    cpu_percent: float = 0.0
    cpu_cores: int = 0
    memory_total_gb: float = 0.0
    memory_used_gb: float = 0.0
    memory_percent: float = 0.0
    disk_total_gb: float = 0.0
    disk_used_gb: float = 0.0
    disk_percent: float = 0.0
    process_count: int = 0
    mamoun_pid: Optional[int] = None
    mamoun_cpu_percent: float = 0.0
    mamoun_memory_mb: float = 0.0
    mamoun_threads: int = 0
    mamoun_fd_count: int = 0
    docker_running: bool = False
    docker_containers: int = 0
    api_latency_ms: float = 0.0
    api_healthy: bool = False
    llm_connectivity: bool = False
    llm_latency_ms: float = 0.0
    last_error_count: int = 0
    error_rate_per_minute: float = 0.0
    timestamp: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "cpu_percent": self.cpu_percent,
            "cpu_cores": self.cpu_cores,
            "memory_total_gb": round(self.memory_total_gb, 2),
            "memory_used_gb": round(self.memory_used_gb, 2),
            "memory_percent": round(self.memory_percent, 1),
            "disk_total_gb": round(self.disk_total_gb, 2),
            "disk_used_gb": round(self.disk_used_gb, 2),
            "disk_percent": round(self.disk_percent, 1),
            "process_count": self.process_count,
            "mamoun_pid": self.mamoun_pid,
            "mamoun_cpu_percent": round(self.mamoun_cpu_percent, 1),
            "mamoun_memory_mb": round(self.mamoun_memory_mb, 1),
            "mamoun_threads": self.mamoun_threads,
            "mamoun_fd_count": self.mamoun_fd_count,
            "docker_running": self.docker_running,
            "docker_containers": self.docker_containers,
            "api_latency_ms": round(self.api_latency_ms, 1),
            "api_healthy": self.api_healthy,
            "llm_connectivity": self.llm_connectivity,
            "llm_latency_ms": round(self.llm_latency_ms, 1),
            "last_error_count": self.last_error_count,
            "error_rate_per_minute": round(self.error_rate_per_minute, 2),
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat() if self.timestamp else None,
        }


@dataclass
class LogEntry:
    """A log entry from the application logs."""
    timestamp: float
    level: str
    message: str
    source: str = ""
    details: dict = field(default_factory=dict)


class StateReader:
    """
    Reads real system state — CPU, memory, disk, processes, Docker,
    API health, LLM connectivity, and application logs.
    """
    
    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        llm_api_url: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        logs_dir: str = "",
        check_interval: int = 15,
    ):
        self.api_url = api_url
        self.llm_api_url = llm_api_url
        self.logs_dir = logs_dir
        self.check_interval = check_interval
        
        self._state = SystemState()
        self._history: list[SystemState] = []
        self._errors: list[LogEntry] = []
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        self._max_history = 360  # 1.5 hours at 15s intervals
        self._max_errors = 1000
        
    def read_system_state(self) -> SystemState:
        """Read a complete snapshot of the real system state."""
        state = SystemState(timestamp=time.time())
        
        # --- CPU ---
        try:
            state.cpu_percent = psutil.cpu_percent(interval=0.5)
            state.cpu_cores = psutil.cpu_count(logical=True)
        except Exception:
            pass
        
        # --- Memory ---
        try:
            mem = psutil.virtual_memory()
            state.memory_total_gb = mem.total / (1024**3)
            state.memory_used_gb = mem.used / (1024**3)
            state.memory_percent = mem.percent
        except Exception:
            pass
        
        # --- Disk ---
        try:
            disk = psutil.disk_usage("/")
            state.disk_total_gb = disk.total / (1024**3)
            state.disk_used_gb = disk.used / (1024**3)
            state.disk_percent = disk.percent
        except Exception:
            pass
        
        # --- Process Count ---
        try:
            state.process_count = len(psutil.pids())
        except Exception:
            pass
        
        # --- Mamoun Process Info ---
        try:
            proc = psutil.Process()
            state.mamoun_pid = proc.pid
            state.mamoun_cpu_percent = proc.cpu_percent(interval=0.1)
            state.mamoun_memory_mb = proc.memory_info().rss / (1024**2)
            state.mamoun_threads = proc.num_threads()
            try:
                state.mamoun_fd_count = proc.num_fds()
            except (psutil.AccessDenied, AttributeError):
                state.mamoun_fd_count = -1
        except Exception:
            pass
        
        # --- Docker ---
        try:
            result = subprocess.run(
                ["docker", "info", "--format", "{{.Containers}}"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                state.docker_running = True
                try:
                    state.docker_containers = int(result.stdout.strip())
                except ValueError:
                    state.docker_containers = 0
        except Exception:
            state.docker_running = False
        
        # --- API Health ---
        try:
            start = time.time()
            resp = httpx.get(f"{self.api_url}/api/brains", timeout=5.0)
            state.api_latency_ms = (time.time() - start) * 1000
            state.api_healthy = resp.status_code == 200
        except Exception:
            state.api_healthy = False
            state.api_latency_ms = -1
        
        # --- LLM Connectivity ---
        try:
            start = time.time()
            resp = httpx.post(
                self.llm_api_url,
                json={"message": "ping", "model": "glm-4-plus", "history": []},
                timeout=10.0,
            )
            state.llm_latency_ms = (time.time() - start) * 1000
            state.llm_connectivity = resp.status_code == 200
        except Exception:
            state.llm_connectivity = False
            state.llm_latency_ms = -1
        
        # --- Error Rate ---
        state.last_error_count = len(self._errors)
        cutoff = time.time() - 300  # Last 5 minutes
        recent_errors = [e for e in self._errors if e.timestamp > cutoff]
        state.error_rate_per_minute = len(recent_errors) / 5.0
        
        # Store
        with self._lock:
            self._state = state
            self._history.append(state)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
        
        return state
    
    def read_logs(self, last_n: int = 1000) -> list[LogEntry]:
        """Read real application logs from the logs directory."""
        entries: list[LogEntry] = []
        
        if not self.logs_dir:
            return entries
        
        logs_path = Path(self.logs_dir)
        if not logs_path.exists():
            return entries
        
        for log_file in logs_path.glob("*.log"):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        # Try to parse JSON log
                        try:
                            data = json.loads(line)
                            entries.append(LogEntry(
                                timestamp=data.get("timestamp", 0),
                                level=data.get("level", "INFO"),
                                message=data.get("message", line[:200]),
                                source=data.get("source", str(log_file.name)),
                                details=data.get("details", {}),
                            ))
                        except json.JSONDecodeError:
                            # Plain text log
                            level = "INFO"
                            if "ERROR" in line:
                                level = "ERROR"
                            elif "WARNING" in line:
                                level = "WARNING"
                            entries.append(LogEntry(
                                timestamp=time.time(),
                                level=level,
                                message=line[:500],
                                source=str(log_file.name),
                            ))
            except Exception:
                continue
        
        # Sort by timestamp and limit
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:last_n]
    
    def record_error(self, message: str, source: str = "", level: str = "ERROR", details: dict = None):
        """Record an error for tracking."""
        entry = LogEntry(
            timestamp=time.time(),
            level=level,
            message=message,
            source=source,
            details=details or {},
        )
        with self._lock:
            self._errors.append(entry)
            if len(self._errors) > self._max_errors:
                self._errors = self._errors[-self._max_errors:]
    
    def get_state(self) -> SystemState:
        """Get the last known state."""
        with self._lock:
            return self._state
    
    def get_history(self, last_n: int = 60) -> list[SystemState]:
        """Get historical state snapshots."""
        with self._lock:
            return self._history[-last_n:]
    
    def get_errors(self, last_n: int = 100) -> list[LogEntry]:
        """Get recent errors."""
        with self._lock:
            return self._errors[-last_n:]
    
    def compute_vitality(self) -> float:
        """
        Compute a 0-100 vitality score based on real system metrics.
        This is the REAL vitality, not a simulation.
        """
        s = self.get_state()
        score = 100.0
        
        # LLM connectivity is critical — deduct 30 points if down
        if not s.llm_connectivity:
            score -= 30
        
        # API health
        if not s.api_healthy:
            score -= 20
        elif s.api_latency_ms > 2000:
            score -= min(15, s.api_latency_ms / 200)
        
        # Memory pressure
        if s.memory_percent > 90:
            score -= 15
        elif s.memory_percent > 80:
            score -= 8
        
        # CPU pressure
        if s.cpu_percent > 90:
            score -= 10
        elif s.cpu_percent > 80:
            score -= 5
        
        # Disk space
        if s.disk_percent > 95:
            score -= 15
        elif s.disk_percent > 90:
            score -= 8
        
        # Error rate
        score -= min(20, s.error_rate_per_minute * 5)
        
        # Process health
        if s.mamoun_memory_mb > 1000:
            score -= 5
        
        return max(0, min(100, score))
    
    def start_monitoring(self):
        """Start periodic system monitoring in a background thread."""
        if self._monitoring:
            return
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True
        )
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop the monitoring loop. Complies with Law 5."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._monitoring:
            try:
                self.read_system_state()
            except Exception as e:
                self.record_error(f"StateReader monitoring error: {e}", "state_reader")
            time.sleep(self.check_interval)
