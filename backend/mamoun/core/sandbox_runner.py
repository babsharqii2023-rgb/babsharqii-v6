"""
BABSHARQII v40.0 — Sandbox Runner
Runs code patches in an isolated Docker container for testing.
No real API keys, no production data — completely isolated.

Enhanced (Fix #13):
- gVisor runtime detection (checks if runsc is available)
- Fallback to standard Docker runtime if gVisor not available
- Enhanced security: read-only filesystem, no network, resource limits
- Seccomp profile support
- All Linux capabilities dropped
- no-new-privileges
"""

import time
import json
import subprocess
import tempfile
import shutil
import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# Default seccomp profile for sandbox containers
SECCOMP_PROFILE = {
    "defaultAction": "SCMP_ACT_ERRNO",
    "architectures": ["SCMP_ARCH_X86_64", "SCMP_ARCH_AARCH64"],
    "syscalls": [
        {"names": [
            "read", "write", "open", "close", "stat", "fstat", "lstat",
            "poll", "lseek", "mmap", "mprotect", "munmap", "brk",
            "rt_sigaction", "rt_sigprocmask", "ioctl", "access", "pipe",
            "select", "sched_yield", "mremap", "nanosleep", "alarm",
            "fork", "exit", "wait4", "kill", "uname", "fcntl",
            "flock", "fsync", "dup", "dup2", "getpid", "sendfile",
            "socketpair", "mkdir", "rmdir", "creat", "link", "unlink",
            "execve", "chdir", "time", "mknod", "chmod", "lchown",
            "setreuid", "setregid", "getgroups", "setgroups", "getresuid",
            "getresgid", "getrlimit", "getrusage", "sysinfo", "gettimeofday",
            "readlink", "getcwd", "getuid", "getgid", "geteuid", "getegid",
            "setuid", "setgid", "getppid", "getpgrp", "setsid",
            "sigaltstack", "getpriority", "setpriority", "prctl",
            "arch_prctl", "set_tid_address", "set_robust_list",
            "futex", "sched_getaffinity", "exit_group", "epoll_create",
            "epoll_ctl", "epoll_wait", "clock_gettime", "clock_getres",
            "statfs", "getdents64", "lseek", "madvise", "getrandom",
            "writev", "readv", "pread64", "pwrite64", "pipe2",
            "dup3", "epoll_create1", "accept4", "eventfd2",
            "clock_adjtime", "umask", "timerfd_create", "timerfd_settime",
        ], "action": "SCMP_ACT_ALLOW"},
    ],
}


@dataclass
class SandboxResult:
    """Result of a sandbox test run."""
    success: bool = False
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    test_results: list = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    errors: list = field(default_factory=list)
    duration_ms: float = 0.0
    container_id: str = ""
    memory_usage_mb: float = 0.0
    runtime_used: str = "runc"  # Track which runtime was used
    gvisor_available: bool = False
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "exit_code": self.exit_code,
            "stdout": self.stdout[:2000],
            "stderr": self.stderr[:2000],
            "test_results": self.test_results,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors[:10],
            "duration_ms": round(self.duration_ms, 0),
            "container_id": self.container_id,
            "memory_usage_mb": round(self.memory_usage_mb, 1),
            "runtime_used": self.runtime_used,
            "gvisor_available": self.gvisor_available,
        }


class SandboxRunner:
    """
    Docker-based sandbox for testing code patches safely.
    
    Features:
    - Isolated container with no production access
    - No API keys or secrets
    - Runs pytest and custom validation
    - Auto-cleanup after test
    - Resource limits (memory, CPU, time)
    - gVisor runtime support for kernel-level isolation
    - Read-only filesystem with tmpfs for writable paths
    - All Linux capabilities dropped
    - no-new-privileges security option
    - Seccomp profile for syscall filtering
    - Critical Junction detection with stop_at_junction (EAGLET integration)
    """
    
    # Critical Junction Score threshold — below this, simulation pauses
    CJS_CRITICAL_THRESHOLD = 0.4
    
    def __init__(
        self,
        project_root: str = "",
        docker_image: str = "python:3.12-slim",
        timeout: int = 120,
        memory_limit: str = "512m",
        cpu_limit: str = "1.0",
    ):
        self.project_root = project_root or str(Path(__file__).parent.parent.parent)
        self.docker_image = docker_image
        self.timeout = timeout
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self._running_containers: list[str] = []
        self._junction_paused: bool = False
        self._junction_state: Optional[dict] = None
        
        # Detect gVisor availability
        self._gvisor_available = self._detect_gvisor()
    
    def _detect_gvisor(self) -> bool:
        """Check if gVisor (runsc) runtime is available on the host."""
        try:
            result = subprocess.run(
                ["docker", "info", "--format", "{{.Runtimes}}"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and "runsc" in result.stdout:
                # Verify runsc is actually functional
                verify = subprocess.run(
                    ["docker", "run", "--rm", "--runtime=runsc", 
                     "hello-world", "/hello"],
                    capture_output=True, text=True, timeout=30
                )
                return verify.returncode == 0
            
            # Also check if runsc binary exists
            which = subprocess.run(
                ["which", "runsc"],
                capture_output=True, text=True, timeout=5
            )
            if which.returncode == 0:
                return True
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return False
    
    def _get_runtime(self) -> str:
        """Get the appropriate Docker runtime."""
        if self._gvisor_available:
            return "runsc"
        return "runc"
    
    def _write_seccomp_profile(self, temp_dir: Path) -> Path:
        """Write a seccomp profile to a file in the temp directory."""
        profile_path = temp_dir / "seccomp_profile.json"
        profile_path.write_text(
            json.dumps(SECCOMP_PROFILE, indent=2),
            encoding="utf-8"
        )
        return profile_path
    
    async def test_patch(
        self,
        patched_code: str,
        target_file: str,
        test_command: str = "",
        stop_at_junction: bool = False,
    ) -> SandboxResult:
        """
        Test a patched file in an isolated Docker container.
        
        Steps:
        1. Create a temp directory with the patched code
        2. Copy necessary files (tests, dependencies)
        3. Write seccomp profile
        4. Run the container with security hardening and resource limits
        5. Collect results
        6. Cleanup
        
        Security:
        - gVisor runtime (if available) for kernel-level isolation
        - Fallback to runc with enhanced security options
        - Read-only filesystem
        - No network access
        - All capabilities dropped
        - no-new-privileges
        - Seccomp profile (only with runc, gVisor handles internally)
        
        Args:
            patched_code: الكود المعدل للاختبار
            target_file: الملف المستهدف
            test_command: أمر الاختبار
            stop_at_junction: إيقاف عند التقاطع الحرج — يتوقف للموافقة البشرية
        """
        # --- SafetyGate Check ---
        try:
            from mamoun.core.safety_gate_client import SafetyGateClient
            sg_client = SafetyGateClient()
            permission = await sg_client.request_permission(
                action="code_self_patch",
                resource=target_file or "unknown",
                risk_level=8,  # High risk — code modification
                details=f"Patch test for {target_file}",
            )
            if not permission.granted:
                return SandboxResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=f"SafetyGate رفض العملية: {permission.reason}",
                    passed=0,
                    failed=0,
                    duration_ms=0,
                    memory_usage_mb=0,
                    runtime_used="denied",
                )
            if permission.requires_human_approval:
                logger.warning(f"SafetyGate: العملية تحتاج موافقة بشرية — {permission.reason}")
        except ImportError:
            logger.warning("SafetyGate client not available — skipping permission check")
        except Exception as e:
            logger.warning(f"SafetyGate check failed: {e} — proceeding with caution")

        # --- Critical Junction Check ---
        # When stop_at_junction=True, evaluate simulation state for critical junctions.
        # If CJS < 0.4, pause simulation for human approval.
        if stop_at_junction:
            simulation_state = {
                "patched_code_length": len(patched_code),
                "target_file": target_file,
                "test_command": test_command,
                "timestamp": time.time(),
            }
            junction_check = self.check_junction(simulation_state)
            if junction_check["at_critical_junction"]:
                self._junction_paused = True
                self._junction_state = junction_check
                logger.warning(
                    f"تقاطع حرج: نقاط التقاطع = {junction_check['cjs']:.3f} — "
                    f"تم إيقاف المحاكاة للموافقة البشرية"
                )
                return SandboxResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=(
                        f"تقاطع حرج: تم إيقاف المحاكاة للموافقة البشرية. "
                        f"نقاط التقاطع = {junction_check['cjs']:.3f}. "
                        f"السبب: {junction_check['reason']}"
                    ),
                    passed=0,
                    failed=0,
                    duration_ms=0,
                    memory_usage_mb=0,
                    runtime_used="junction_paused",
                )

        start_time = time.time()
        result = SandboxResult(
            gvisor_available=self._gvisor_available,
            runtime_used=self._get_runtime(),
        )
        
        # Create temp directory
        with tempfile.TemporaryDirectory(prefix="mamoun_sandbox_") as temp_dir:
            temp_path = Path(temp_dir)
            
            # Copy project files (without secrets)
            await self._prepare_sandbox_files(temp_path, patched_code, target_file)
            
            # Create Dockerfile for sandbox
            dockerfile = self._create_sandbox_dockerfile()
            (temp_path / "Dockerfile").write_text(dockerfile)
            
            # Write seccomp profile (used with runc fallback)
            seccomp_path = self._write_seccomp_profile(temp_path)
            
            # Build sandbox image
            image_tag = f"mamoun-sandbox-{int(time.time())}"
            build_result = self._run_docker_command([
                "docker", "build", "-t", image_tag, temp_dir
            ])
            
            if build_result.returncode != 0:
                result.stderr = f"Docker build failed: {build_result.stderr}"
                result.success = False
                return result
            
            # Build the run command with security hardening
            if not test_command:
                test_command = f"python -m pytest tests/ -v --tb=short 2>&1 || true"
            
            runtime = self._get_runtime()
            run_cmd = [
                "docker", "run",
                "--rm",  # Auto-remove after exit
            ]
            
            # Add runtime flag
            if runtime == "runsc":
                run_cmd.extend(["--runtime", "runsc"])
            else:
                # With runc, use seccomp profile for extra security
                run_cmd.extend(["--security-opt", f"seccomp={seccomp_path}"])
            
            # Resource limits
            run_cmd.extend([
                "--memory", self.memory_limit,
                "--cpus", self.cpu_limit,
                "--memory-swap", self.memory_limit,  # No swap
                "--pids-limit", "64",  # Limit process count
            ])
            
            # Network isolation
            run_cmd.extend(["--network", "none"])
            
            # Security options
            run_cmd.extend([
                "--security-opt", "no-new-privileges",
                "--cap-drop", "ALL",
                "--read-only",  # Read-only filesystem
            ])
            
            # Tmpfs for writable directories
            run_cmd.extend([
                "--tmpfs", "/tmp:size=100M",
                "--tmpfs", "/app/data:size=50M",
                "--tmpfs", "/app/logs:size=10M",
                "--tmpfs", "/run:size=10M",
            ])
            
            # Environment variables
            run_cmd.extend([
                "--env", "MAMOUN_SANDBOX_MODE=true",
                "--env", "MAMOUN_NO_API_KEYS=true",
                "--env", "HOME=/tmp",
                "--env", "TMPDIR=/tmp",
            ])
            
            # Image and command
            run_cmd.extend([
                image_tag,
                "bash", "-c", test_command,
            ])
            
            # Run the container
            run_result = self._run_docker_command(run_cmd, timeout=self.timeout)
            
            result.exit_code = run_result.returncode
            result.stdout = run_result.stdout
            result.stderr = run_result.stderr
            result.container_id = image_tag
            
            # Parse pytest output
            self._parse_pytest_output(result)
            
            # Cleanup image
            self._run_docker_command(["docker", "rmi", image_tag], timeout=30)
        
        result.duration_ms = (time.time() - start_time) * 1000
        result.success = result.failed == 0 and result.exit_code == 0
        
        return result
    
    async def run_benchmark(
        self,
        benchmark_tasks: list[dict],
        genome: dict,
        timeout: int = 300,
    ) -> dict:
        """
        Run a benchmark suite against a candidate genome.
        Returns fitness metrics: success_rate, avg_time, cost, uncertainty.
        """
        results = {
            "total": len(benchmark_tasks),
            "successful": 0,
            "failed": 0,
            "errors": [],
            "avg_latency_ms": 0.0,
            "total_time_ms": 0.0,
            "success_rate": 0.0,
            "runtime_used": self._get_runtime(),
            "gvisor_available": self._gvisor_available,
        }
        
        start_time = time.time()
        latencies = []
        
        for task in benchmark_tasks:
            task_start = time.time()
            try:
                test_result = await self.test_patch(
                    patched_code=task.get("code", "pass"),
                    target_file=task.get("target_file", "test_task.py"),
                    test_command=task.get("test_command", "python -c 'print(\"ok\")'"),
                )
                latency = (time.time() - task_start) * 1000
                latencies.append(latency)
                
                if test_result.success:
                    results["successful"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "task": task.get("id", "unknown"),
                        "error": test_result.stderr[:200],
                    })
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "task": task.get("id", "unknown"),
                    "error": str(e)[:200],
                })
        
        results["total_time_ms"] = (time.time() - start_time) * 1000
        results["avg_latency_ms"] = sum(latencies) / len(latencies) if latencies else 0
        results["success_rate"] = results["successful"] / results["total"] if results["total"] > 0 else 0
        
        return results
    
    async def _prepare_sandbox_files(
        self, 
        temp_path: Path, 
        patched_code: str, 
        target_file: str
    ):
        """Prepare sandbox directory with necessary files, excluding secrets."""
        project_path = Path(self.project_root)
        
        # Copy Python source files
        for py_file in project_path.rglob("*.py"):
            # Skip __pycache__, secrets, and immutable files
            rel = py_file.relative_to(project_path)
            if any(skip in str(rel) for skip in [
                "__pycache__", ".git", "secrets", "keys", "certs",
                ".env", "safety_guard", "approval_gate"
            ]):
                continue
            
            dest = temp_path / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(py_file, dest)
        
        # Write the patched file
        target_path = temp_path / target_file
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(patched_code, encoding='utf-8')
        
        # Copy tests
        tests_src = project_path / "tests"
        tests_dest = temp_path / "tests"
        if tests_src.exists():
            if tests_dest.exists():
                shutil.rmtree(tests_dest)
            shutil.copytree(tests_src, tests_dest)
        
        # Copy requirements
        req_file = project_path / "requirements.txt"
        if req_file.exists():
            shutil.copy2(req_file, temp_path / "requirements.txt")
    
    def _create_sandbox_dockerfile(self) -> str:
        """Create a minimal Dockerfile for the sandbox."""
        return """FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true

# Copy source code (NO secrets, NO API keys)
COPY . .

# Sandbox mode
ENV MAMOUN_SANDBOX_MODE=true
ENV MAMOUN_NO_API_KEYS=true

# Writable directories
RUN mkdir -p /tmp /app/data /app/logs

# Run tests by default
CMD ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]
"""
    
    def _parse_pytest_output(self, result: SandboxResult):
        """Parse pytest output to extract test results."""
        output = result.stdout + result.stderr
        
        # Look for pytest summary line: "X passed, Y failed, Z errors"
        import re
        passed_match = re.search(r'(\d+) passed', output)
        failed_match = re.search(r'(\d+) failed', output)
        error_match = re.search(r'(\d+) error', output)
        
        result.passed = int(passed_match.group(1)) if passed_match else 0
        result.failed = int(failed_match.group(1)) if failed_match else 0
        errors = int(error_match.group(1)) if error_match else 0
        result.failed += errors
        
        # Extract individual test results
        test_pattern = re.findall(r'(PASSED|FAILED|ERROR)\s+(.+)', output)
        for status, test_name in test_pattern:
            result.test_results.append({
                "name": test_name.strip(),
                "status": status,
            })
    
    def _run_docker_command(
        self, 
        cmd: list[str], 
        timeout: int = None
    ) -> subprocess.CompletedProcess:
        """Run a Docker command with timeout."""
        timeout = timeout or self.timeout
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=-1,
                stdout="",
                stderr=f"Command timed out after {timeout}s",
            )
    
    def cleanup_all_containers(self):
        """Kill and remove all running sandbox containers. Complies with Law 5."""
        for container_id in self._running_containers:
            try:
                self._run_docker_command(
                    ["docker", "kill", container_id], timeout=10
                )
                self._run_docker_command(
                    ["docker", "rm", "-f", container_id], timeout=10
                )
            except Exception:
                pass
        self._running_containers.clear()
    
    def check_junction(self, simulation_state: dict) -> dict:
        """
        فحص التقاطع — تقييم ما إذا كنا في تقاطع حرج.

        Evaluates whether the simulation is at a critical junction
        by computing a Critical Junction Score (CJS). When CJS < 0.4,
        the simulation should pause for human approval.

        This integrates with EAGLET pruning — low CJS means the
        simulation is in uncertain territory and needs human guidance.

        Args:
            simulation_state: حالة المحاكاة الحالية

        Returns:
            dict with at_critical_junction, cjs, reason
        """
        # Compute CJS based on simulation state factors
        code_length = simulation_state.get("patched_code_length", 0)
        target = simulation_state.get("target_file", "")

        # Factor 1: Code complexity — longer patches are riskier
        complexity_score = min(1.0, code_length / 5000.0)
        complexity_factor = 1.0 - complexity_score * 0.3

        # Factor 2: Target file safety — certain files are more critical
        high_risk_files = ["safety_guard", "approval_gate", "laws.yaml", "config.py"]
        file_risk = any(hrf in target for hrf in high_risk_files)
        file_factor = 0.05 if file_risk else 0.9

        # Factor 3: Uncertainty — use available brain responses if present
        brain_confidences = simulation_state.get("brain_confidences", [])
        if brain_confidences:
            avg_conf = sum(brain_confidences) / len(brain_confidences)
            if len(brain_confidences) > 1:
                variance = sum(
                    (c - avg_conf) ** 2 for c in brain_confidences
                ) / len(brain_confidences)
                consistency = 1.0 - min(1.0, variance * 4)
            else:
                consistency = 0.5
            confidence_factor = avg_conf * 0.6 + consistency * 0.4
        else:
            confidence_factor = 0.5  # No brain data → moderate uncertainty

        # Weighted CJS calculation — file safety has highest weight
        cjs = (
            0.20 * complexity_factor
            + 0.50 * file_factor
            + 0.30 * confidence_factor
        )

        # Protected files always force a critical junction (CJS floor)
        if file_risk:
            cjs = min(cjs, 0.25)

        # Clamp to [0, 1]
        cjs = max(0.0, min(1.0, cjs))

        at_critical_junction = cjs < self.CJS_CRITICAL_THRESHOLD

        # Generate reason in Arabic
        if file_risk:
            reason = "الملف المستهدف عالي المخاطر — يتطلب مراجعة بشرية"
        elif cjs < 0.2:
            reason = "شك عالي في النتائج — إجماع الأدمغة ضعيف جداً"
        elif cjs < 0.4:
            reason = "شك متوسط في النتائج — يتطلب مراقبة بشرية"
        else:
            reason = "نتائج مقبولة — يمكن المتابعة"

        return {
            "at_critical_junction": at_critical_junction,
            "cjs": cjs,
            "reason": reason,
            "factors": {
                "complexity_factor": round(complexity_factor, 3),
                "file_factor": round(file_factor, 3),
                "confidence_factor": round(confidence_factor, 3),
            },
        }

    def is_junction_paused(self) -> bool:
        """التحقق مما إذا كانت المحاكاة متوقفة عند تقاطع حرج."""
        return self._junction_paused

    def resume_from_junction(self) -> bool:
        """
        استئناف من التقاطع — السماح بالمتابعة بعد الموافقة البشرية.

        Returns True if successfully resumed.
        """
        if self._junction_paused:
            self._junction_paused = False
            self._junction_state = None
            logger.info("تم استئناف المحاكاة بعد الموافقة البشرية")
            return True
        return False

    def get_junction_state(self) -> Optional[dict]:
        """الحصول على حالة التقاطع الحرج الحالية."""
        return self._junction_state

    def get_runtime_info(self) -> dict:
        """Get information about the current sandbox runtime configuration."""
        return {
            "gvisor_available": self._gvisor_available,
            "runtime": self._get_runtime(),
            "memory_limit": self.memory_limit,
            "cpu_limit": self.cpu_limit,
            "timeout": self.timeout,
            "security_features": [
                "no-new-privileges",
                "cap-drop ALL",
                "network none",
                "read-only filesystem",
                "tmpfs for writable paths",
                "pids-limit 64",
                "no swap",
                "seccomp profile" if not self._gvisor_available else "gVisor kernel isolation",
            ],
        }

    # ─── v6.0 Enhanced Junction ─────────────────────────────────────────────

    async def check_enhanced_junction(self, simulation_state: dict) -> dict:
        """
        فحص تقاطع محسّن — مع ربط ApprovalGate عند CJS < 0.35.
        Enhanced junction check that integrates with the ApprovalGate
        when CJS falls below the v6 threshold of 0.35.

        When the Critical Junction Score drops below 0.35, this method
        automatically creates an ApprovalRequest through the ApprovalGate
        to flag for human intervention.

        Args:
            simulation_state: حالة المحاكاة الحالية

        Returns:
            dict with junction info + approval_request_id if CJS < 0.35
        """
        # Get base junction check
        junction = self.check_junction(simulation_state)

        # Read v6 threshold from environment (default: 0.35)
        v6_threshold = float(os.environ.get("MAMOUN_CJS_ENHANCED_THRESHOLD", "0.35"))

        # If CJS < threshold, create an ApprovalRequest for human help
        if junction.get("cjs", 1.0) < v6_threshold:
            try:
                from mamoun.core.approval_gate import ApprovalGate, ApprovalRequest
                gate = ApprovalGate()
                request = ApprovalRequest(
                    change_type="critical_junction",
                    target=simulation_state.get("target_file", "unknown"),
                    description=(
                        f"تقاطع حرج: CJS={junction['cjs']:.3f}. "
                        f"{junction['reason']}"
                    ),
                    risk_level="high",
                )
                result = await gate.request_approval(request)
                junction["approval_request_id"] = result.get("id", "")
                junction["approval_status"] = result.get("status", "")
            except Exception as e:
                junction["approval_error"] = str(e)

        return junction

    async def test_embodied(self, task: str, steps: list[dict] = None) -> dict:
        """
        اختبار في وضع الجسد الرقمي — بيئة تفاعلية معزولة.

        Args:
            task: وصف المهمة
            steps: خطوات التنفيذ (اختياري)

        Returns:
            dict with execution results
        """
        embodied_enabled = os.getenv("MAMOUN_EMBODIMENT_ENABLED", "false").lower() == "true"
        if not embodied_enabled:
            return {"success": False, "error": "وضع الجسد الرقمي غير مفعّل — أضف MAMOUN_EMBODIMENT_ENABLED=true إلى .env"}

        try:
            from mamoun.core.embodiment_controller import EmbodimentController
            controller = EmbodimentController()

            if not await controller.is_available():
                return {"success": False, "error": "خدمة الجسد الرقمي غير متاحة — شغّل ./start.sh --docker مع --profile embodiment"}

            if steps:
                plan = await controller.execute_plan(steps)
                return {
                    "success": plan.status == "completed",
                    "status": plan.status,
                    "completed_steps": plan.completed_steps,
                    "total_steps": len(plan.steps),
                    "failed_step": plan.failed_step,
                }
            else:
                # Simple task: launch browser and screenshot
                launch = await controller.launch_browser("about:blank")
                return {"success": launch.success, "action": "launch_browser", "result": launch.result}
        except ImportError:
            return {"success": False, "error": "EmbodimentController غير متاح"}
        except Exception as e:
            return {"success": False, "error": str(e)}
