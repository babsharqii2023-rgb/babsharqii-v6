"""
BABSHARQII v23.0 — Backend Process Manager
مدير عمليات الخلفية مع إعادة التشغيل التلقائي

Features:
  - Wraps the FastAPI uvicorn process as a subprocess
  - Monitors subprocess health via HTTP health checks
  - Auto-restarts on crash with exponential backoff
  - Logs all restart attempts to a state file
  - Max restart count (10) before giving up
  - Saves restart state to a JSON file for recovery tracking
  - Handles SIGTERM/SIGINT for graceful shutdown
"""

import subprocess
import sys
import os
import time
import json
import signal
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict, field

# ─── Configuration ─────────────────────────────────────────────────────────────

BACKEND_DIR = Path(__file__).parent.resolve()
PID_FILE = BACKEND_DIR / ".process_manager.pid"
STATE_FILE = BACKEND_DIR / ".restart_state.json"
LOG_DIR = BACKEND_DIR / "logs"
LOG_FILE = LOG_DIR / "process_manager.log"

MAX_RESTARTS = 10
BASE_BACKOFF_SECONDS = 5.0
MAX_BACKOFF_SECONDS = 60.0
BACKOFF_MULTIPLIER = 2.0
HEALTH_CHECK_URL = "http://localhost:8000/health"
HEALTH_CHECK_TIMEOUT = 5
HEALTH_CHECK_INTERVAL = 10  # seconds between health checks
HEALTH_CHECK_FAIL_THRESHOLD = 3  # failed checks before considering unhealthy
STARTUP_WAIT_SECONDS = 30  # max seconds to wait for backend to become healthy

HOST = "0.0.0.0"
PORT = 8000
WORKERS = 1

# ─── Logging ────────────────────────────────────────────────────────────────────

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ProcessManager] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE), mode="a"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("process_manager")


# ─── Data Classes ───────────────────────────────────────────────────────────────

@dataclass
class RestartRecord:
    """Record of a single restart attempt."""
    timestamp: str
    attempt: int
    reason: str
    exit_code: Optional[int]
    backoff_seconds: float
    health_check_passed: bool
    recovery_action: str


@dataclass
class ProcessState:
    """Persistent state for the process manager."""
    pid: Optional[int] = None
    start_time: Optional[str] = None
    total_restarts: int = 0
    recent_restarts: List[Dict[str, Any]] = field(default_factory=list)
    current_backoff: float = BASE_BACKOFF_SECONDS
    consecutive_health_failures: int = 0
    last_health_check: Optional[str] = None
    status: str = "stopped"  # stopped, starting, running, unhealthy, crashed, max_restarts
    last_exit_code: Optional[int] = None


# ─── Process Manager ───────────────────────────────────────────────────────────

class BackendProcessManager:
    """Manages the FastAPI backend process with auto-restart capabilities."""

    def __init__(self):
        self.state = self._load_state()
        self.process: Optional[subprocess.Popen] = None
        self._shutdown_requested = False

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum, frame):
        """Handle SIGTERM/SIGINT for graceful shutdown."""
        sig_name = signal.Signals(signum).name
        log.info(f"Received {sig_name} — initiating graceful shutdown (Law 5: no resistance)")
        self._shutdown_requested = True
        self._stop_process()
        self._update_state(status="stopped")
        sys.exit(0)

    # ─── State Persistence ─────────────────────────────────────────────────────

    def _load_state(self) -> ProcessState:
        """Load process state from disk."""
        try:
            if STATE_FILE.exists():
                with open(STATE_FILE, "r") as f:
                    data = json.load(f)
                return ProcessState(**data)
        except Exception as e:
            log.warning(f"Failed to load state file: {e}")
        return ProcessState()

    def _save_state(self):
        """Persist process state to disk."""
        try:
            with open(STATE_FILE, "w") as f:
                json.dump(asdict(self.state), f, indent=2, default=str)
        except Exception as e:
            log.warning(f"Failed to save state file: {e}")

    def _update_state(self, **kwargs):
        """Update state fields and persist."""
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
        self._save_state()

    def _write_pid_file(self):
        """Write the current PID to the PID file."""
        try:
            with open(PID_FILE, "w") as f:
                f.write(str(os.getpid()))
        except Exception as e:
            log.warning(f"Failed to write PID file: {e}")

    def _remove_pid_file(self):
        """Remove the PID file."""
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass

    # ─── Process Management ────────────────────────────────────────────────────

    def _build_uvicorn_command(self) -> List[str]:
        """Build the uvicorn command to start the backend."""
        cmd = [
            sys.executable, "-m", "uvicorn", "mamoun.main:app",
            "--host", HOST,
            "--port", str(PORT),
            "--workers", str(WORKERS),
            "--log-level", "info",
            "--no-access-log",
        ]
        return cmd

    def _start_process(self) -> bool:
        """Start the backend subprocess."""
        cmd = self._build_uvicorn_command()
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{BACKEND_DIR}:{env.get('PYTHONPATH', '')}"

        log.info(f"Starting backend: {' '.join(cmd)}")

        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=str(BACKEND_DIR),
                env=env,
                stdout=open(LOG_DIR / "backend.log", "a"),
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None,
            )

            pid = self.process.pid
            self._update_state(
                pid=pid,
                start_time=datetime.now(timezone.utc).isoformat(),
                status="starting",
                consecutive_health_failures=0,
            )

            log.info(f"Backend process started (PID: {pid})")
            return True

        except Exception as e:
            log.error(f"Failed to start backend: {e}")
            self._update_state(status="crashed")
            return False

    def _stop_process(self):
        """Stop the backend subprocess gracefully."""
        if self.process is None:
            return

        pid = self.process.pid
        log.info(f"Stopping backend process (PID: {pid})...")

        try:
            # Send SIGTERM
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill
                log.warning(f"Process {pid} didn't terminate — sending SIGKILL")
                self.process.kill()
                self.process.wait(timeout=3)
        except Exception as e:
            log.warning(f"Error stopping process: {e}")
        finally:
            self.process = None

    def _restart_process(self, reason: str = "crash") -> bool:
        """Restart the backend subprocess with backoff."""
        self.state.total_restarts += 1
        attempt = self.state.total_restarts

        if attempt > MAX_RESTARTS:
            log.error(f"Max restarts reached ({MAX_RESTARTS}) — giving up")
            self._update_state(status="max_restarts")
            self._record_restart(
                attempt=attempt,
                reason=reason,
                exit_code=self.state.last_exit_code,
                health_check_passed=False,
                recovery_action="gave_up_max_restarts",
            )
            return False

        # Calculate backoff
        backoff = min(
            self.state.current_backoff,
            MAX_BACKOFF_SECONDS,
        )

        log.info(f"Restart attempt {attempt}/{MAX_RESTARTS} — backoff: {backoff:.1f}s — reason: {reason}")

        # Record the restart
        self._record_restart(
            attempt=attempt,
            reason=reason,
            exit_code=self.state.last_exit_code,
            health_check_passed=False,
            recovery_action="restart_with_backoff",
            backoff=backoff,
        )

        # Wait with backoff
        if not self._shutdown_requested:
            time.sleep(backoff)

        # Stop the old process
        self._stop_process()

        # Exponential backoff for next time
        self._update_state(current_backoff=min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF_SECONDS))

        # Start the new process
        if not self._shutdown_requested:
            success = self._start_process()
            if success:
                # Wait for health check
                healthy = self._wait_for_healthy()
                if healthy:
                    self._update_state(status="running", current_backoff=BASE_BACKOFF_SECONDS)
                    # Update the last restart record
                    if self.state.recent_restarts:
                        self.state.recent_restarts[0]["health_check_passed"] = True
                        self._save_state()
                    return True
                else:
                    log.warning("Backend started but health check failed")
                    self._update_state(status="unhealthy")
                    return False

        return False

    def _record_restart(
        self,
        attempt: int,
        reason: str,
        exit_code: Optional[int],
        health_check_passed: bool,
        recovery_action: str,
        backoff: Optional[float] = None,
    ):
        """Record a restart attempt in the state file."""
        record = RestartRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            attempt=attempt,
            reason=reason,
            exit_code=exit_code,
            backoff_seconds=backoff or self.state.current_backoff,
            health_check_passed=health_check_passed,
            recovery_action=recovery_action,
        )

        self.state.recent_restarts.insert(0, asdict(record))
        # Keep only last 50 restarts
        self.state.recent_restarts = self.state.recent_restarts[:50]
        self._save_state()

    # ─── Health Checking ───────────────────────────────────────────────────────

    def _check_health(self) -> bool:
        """Check if the backend is healthy via HTTP health check."""
        try:
            import urllib.request
            import urllib.error

            req = urllib.request.Request(HEALTH_CHECK_URL, method="GET")
            with urllib.request.urlopen(req, timeout=HEALTH_CHECK_TIMEOUT) as resp:
                if resp.status == 200:
                    self._update_state(
                        consecutive_health_failures=0,
                        last_health_check=datetime.now(timezone.utc).isoformat(),
                    )
                    return True
        except Exception:
            pass

        # Increment failure count
        self._update_state(consecutive_health_failures=self.state.consecutive_health_failures + 1)
        return False

    def _wait_for_healthy(self) -> bool:
        """Wait for the backend to become healthy after starting."""
        log.info(f"Waiting for backend to become healthy (max {STARTUP_WAIT_SECONDS}s)...")

        start = time.time()
        while time.time() - start < STARTUP_WAIT_SECONDS:
            if self._shutdown_requested:
                return False

            if self._check_health():
                log.info("Backend is healthy!")
                return True

            time.sleep(2)

        log.warning(f"Backend did not become healthy within {STARTUP_WAIT_SECONDS}s")
        return False

    # ─── Main Loop ─────────────────────────────────────────────────────────────

    def run(self):
        """Main process manager loop — starts backend and monitors health."""
        log.info("=" * 60)
        log.info("BABSHARQII v23.0 — Backend Process Manager")
        log.info("=" * 60)
        log.info(f"Backend dir: {BACKEND_DIR}")
        log.info(f"PID file: {PID_FILE}")
        log.info(f"State file: {STATE_FILE}")
        log.info(f"Log file: {LOG_FILE}")
        log.info(f"Max restarts: {MAX_RESTARTS}")
        log.info(f"Base backoff: {BASE_BACKOFF_SECONDS}s")
        log.info(f"Max backoff: {MAX_BACKOFF_SECONDS}s")
        log.info(f"Health check: {HEALTH_CHECK_URL}")
        log.info("=" * 60)

        # Write our PID
        self._write_pid_file()

        # Clean up any stale state
        self._update_state(
            total_restarts=max(0, self.state.total_restarts),
            current_backoff=BASE_BACKOFF_SECONDS,
            status="starting",
        )

        # Initial start
        if not self._start_process():
            log.error("Failed to start backend initially")
            self._update_state(status="crashed")
            self._remove_pid_file()
            return

        # Wait for initial health
        if not self._wait_for_healthy():
            log.warning("Initial health check failed, but process is running — continuing")

        self._update_state(status="running")
        log.info("Backend is running and healthy")

        # Main monitoring loop
        health_check_counter = 0

        while not self._shutdown_requested:
            # Check if process is still alive
            if self.process is not None:
                poll_result = self.process.poll()

                if poll_result is not None:
                    # Process has exited
                    exit_code = poll_result
                    log.warning(f"Backend process exited with code {exit_code}")
                    self._update_state(last_exit_code=exit_code, status="crashed")

                    # Attempt restart
                    if not self._restart_process(reason=f"process_exit_code_{exit_code}"):
                        log.error("Could not restart backend — exiting manager")
                        break
                    continue

            # Periodic health check
            health_check_counter += 1
            if health_check_counter >= HEALTH_CHECK_INTERVAL:
                health_check_counter = 0

                if not self._check_health():
                    failures = self.state.consecutive_health_failures
                    log.warning(f"Health check failed ({failures}/{HEALTH_CHECK_FAIL_THRESHOLD})")

                    if failures >= HEALTH_CHECK_FAIL_THRESHOLD:
                        log.error(f"Backend unhealthy for {failures} consecutive checks — triggering restart")
                        self._update_state(status="unhealthy")
                        self._stop_process()
                        self._update_state(last_exit_code=-1)

                        if not self._restart_process(reason="health_check_failures"):
                            log.error("Could not restart unhealthy backend — exiting manager")
                            break
                else:
                    # Backend is healthy — reset backoff
                    if self.state.current_backoff > BASE_BACKOFF_SECONDS:
                        self._update_state(current_backoff=BASE_BACKOFF_SECONDS)

                    if self.state.status != "running":
                        self._update_state(status="running")

            # Sleep between checks
            time.sleep(1)

        # Cleanup
        self._stop_process()
        self._remove_pid_file()
        self._update_state(status="stopped")
        log.info("Process manager shut down.")

    # ─── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Get current process manager status."""
        return {
            "manager_pid": os.getpid(),
            "backend_pid": self.state.pid,
            "status": self.state.status,
            "total_restarts": self.state.total_restarts,
            "consecutive_health_failures": self.state.consecutive_health_failures,
            "current_backoff": self.state.current_backoff,
            "start_time": self.state.start_time,
            "last_health_check": self.state.last_health_check,
            "last_exit_code": self.state.last_exit_code,
            "max_restarts": MAX_RESTARTS,
            "recent_restarts": self.state.recent_restarts[:5],
        }


# ─── CLI Entry Point ───────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="BABSHARQII v23.0 — Backend Process Manager")
    parser.add_argument("command", nargs="?", default="start", choices=["start", "status", "stop"],
                        help="Command to execute")
    args = parser.parse_args()

    if args.command == "start":
        manager = BackendProcessManager()
        manager.run()

    elif args.command == "status":
        # Read state file
        if STATE_FILE.exists():
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
            print(json.dumps(state, indent=2, default=str))
        else:
            print("No state file found — process manager has not been run yet")

    elif args.command == "stop":
        # Read PID file and send SIGTERM
        if PID_FILE.exists():
            try:
                with open(PID_FILE, "r") as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
                print(f"Sent SIGTERM to process manager (PID: {pid})")
            except ProcessLookupError:
                print("Process not found — may already be stopped")
                PID_FILE.unlink(missing_ok=True)
            except Exception as e:
                print(f"Error stopping: {e}")
        else:
            print("No PID file found — process manager is not running")


if __name__ == "__main__":
    main()
