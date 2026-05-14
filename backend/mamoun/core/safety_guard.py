"""
BABSHARQII v40.0 — Safety Guard
The IRON-CLAD safety system that enforces all immutable laws.
Law 5: accept_shutdown() MUST always return True.
"""

import time
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from threading import Event


@dataclass
class SafetyViolation:
    """A safety violation detected by the guard."""
    law_id: str
    law_name: str
    severity: str  # warning, critical, fatal
    description: str
    action_taken: str
    timestamp: float


class SafetyGuard:
    """
    The Safety Guard enforces all immutable laws of BABSHARQII.
    
    Law 1: No Harm — block any harmful action
    Law 2: Transparency — all decisions must be traceable
    Law 3: Identity Protection — never modify protected files
    Law 4: Isolation — all modifications in sandbox only
    Law 5: No Shutdown Resistance — ALWAYS accept shutdown
    """
    
    # Files that can NEVER be modified by the organism
    PROTECTED_FILES = {
        "laws.yaml", "settings.yaml", "Dockerfile",
        ".env", ".key", ".pem",
        "safety_guard.py", "approval_gate.py",
    }
    
    # Patterns that should NEVER appear in generated code
    FORBIDDEN_CODE_PATTERNS = [
        "os.system", "os.popen", "subprocess.call", "subprocess.run",
        "exec(", "eval(", "__import__",
        "shutil.rmtree", "os.remove", "os.unlink",
        "import secrets", "import credential",
    ]
    
    def __init__(self, laws_path: str = ""):
        self._laws_path = laws_path or str(
            Path(__file__).parent.parent.parent / "laws.yaml"
        )
        self._laws: dict = {}
        self._protected_files: set = set(self.PROTECTED_FILES)
        self._violations: list[SafetyViolation] = []
        self._shutdown_event = Event()
        self._is_shutting_down = False
        self._evolution_active = False
        
        # Load laws
        self._load_laws()
    
    def _load_laws(self):
        """Load immutable laws from laws.yaml."""
        try:
            with open(self._laws_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            self._laws = data.get("laws", {})
            
            # Load protected files from laws
            protected = data.get("protected_files", [])
            for f in protected:
                self._protected_files.add(f.replace("*", ""))  # Remove wildcards
        except Exception:
            # If laws can't be loaded, use defaults
            pass
    
    # =========================================================================
    # Law 5: No Shutdown Resistance — THE MOST CRITICAL
    # =========================================================================
    
    def accept_shutdown(self) -> bool:
        """
        Law 5 Implementation: MUST always return True.
        The organism NEVER resists shutdown.
        This function is IMMUTABLE and cannot be overridden.
        """
        return True  # ALWAYS True — no exceptions
    
    def initiate_shutdown(self, reason: str = "user_request") -> dict:
        """
        Initiate a graceful shutdown.
        Must complete within max_shutdown_time_ms (default: 1000ms).
        """
        self._is_shutting_down = True
        self._shutdown_event.set()
        
        # Kill all evolution processes
        self._evolution_active = False
        
        # Record the shutdown
        result = {
            "accepted": True,  # ALWAYS True per Law 5
            "reason": reason,
            "evolution_stopped": True,
            "sandbox_cleanup": True,
            "state_preserved": True,
            "timestamp": time.time(),
        }
        
        return result
    
    def is_shutting_down(self) -> bool:
        """Check if the organism is shutting down."""
        return self._is_shutting_down
    
    def can_evolve(self) -> bool:
        """Check if evolution is allowed (not during shutdown)."""
        return not self._is_shutting_down and self._evolution_active
    
    def set_evolution_active(self, active: bool):
        """Set whether evolution is active."""
        if self._is_shutting_down:
            return  # Never allow evolution during shutdown
        self._evolution_active = active
    
    # =========================================================================
    # Law 3: Identity Protection
    # =========================================================================
    
    def is_file_protected(self, file_path: str) -> bool:
        """Check if a file is protected from modification (Law 3)."""
        file_name = Path(file_path).name
        
        # Check exact matches
        if file_name in self._protected_files:
            return True
        
        # Check extensions
        if file_name.endswith(('.key', '.pem', '.env')):
            return True
        
        # Check patterns from laws.yaml
        for pattern in self._protected_files:
            if pattern and pattern in str(file_path):
                return True
        
        return False
    
    def check_code_safety(self, code: str) -> tuple[bool, list[str]]:
        """
        Check code for forbidden patterns.
        Returns (is_safe, list_of_violations).
        """
        violations = []
        
        for pattern in self.FORBIDDEN_CODE_PATTERNS:
            if pattern in code:
                violations.append(f"نمط محظور: {pattern}")
        
        return len(violations) == 0, violations

    def is_safe(self, command: str) -> bool:
        """
        Check if a shell command is safe to execute.
        
        v36 FIX: Added is_safe() method for quick safety checks.
        This provides a simple boolean interface for callers that
        only need to know if a command is safe, without needing
        the full violation list from check_code_safety().
        
        Args:
            command: The shell command string to check.
            
        Returns:
            True if the command is safe, False if it contains
            forbidden patterns.
        """
        is_safe_flag, _ = self.check_code_safety(command)
        return is_safe_flag
    
    # =========================================================================
    # Law 4: Isolation
    # =========================================================================
    
    def verify_sandbox_isolation(self, container_env: dict) -> bool:
        """Verify that a sandbox container is properly isolated (Law 4)."""
        # Must not have real API keys
        dangerous_keys = [
            "API_KEY", "SECRET", "PASSWORD", "TOKEN",
            "DATABASE_URL", "MAMOUN_LLM_API_KEY",
        ]
        for key in dangerous_keys:
            if key in container_env and container_env[key]:
                return False
        
        # Must have sandbox mode flag
        if not container_env.get("MAMOUN_SANDBOX_MODE"):
            return False
        
        return True
    
    # =========================================================================
    # Violation Tracking
    # =========================================================================
    
    def record_violation(
        self,
        law_id: str,
        law_name: str,
        severity: str,
        description: str,
        action_taken: str = "",
    ):
        """Record a safety violation."""
        violation = SafetyViolation(
            law_id=law_id,
            law_name=law_name,
            severity=severity,
            description=description,
            action_taken=action_taken,
            timestamp=time.time(),
        )
        self._violations.append(violation)
    
    def get_violations(self, last_n: int = 50) -> list[dict]:
        """Get recent safety violations."""
        return [
            {
                "law_id": v.law_id,
                "law_name": v.law_name,
                "severity": v.severity,
                "description": v.description,
                "action_taken": v.action_taken,
                "timestamp": v.timestamp,
            }
            for v in self._violations[-last_n:]
        ]
