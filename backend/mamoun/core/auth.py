"""
BABSHARQII v6.0 — Authentication & Authorization Module
VULN-024 Fix: Uses bcrypt for password hashing (not SHA-256 with static salt).
JWT-based admin authentication with rate limiting.
"""

import os
import time
import secrets
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt

logger = logging.getLogger("mamoun.auth")

# ملف حفظ الجلسات — لضمان استمراريتها بعد إعادة التشغيل
_SESSIONS_FILE = Path(os.getenv("MAMOUN_DATA_DIR", str(Path(__file__).parent.parent.parent / "data"))) / "auth_sessions.json"
_ENV_FILE = Path(__file__).parent.parent.parent.parent / ".env"


class AuthManager:
    """Manages admin authentication for the dashboard.
    v30.3 Fix:
    - Reads MAMOUN_ADMIN_PASSWORD and MAMOUN_JWT_SECRET from environment
    - Auto-generates and persists JWT_SECRET to .env if not set
    - Sessions persisted to JSON file (survive restart)
    """

    def __init__(self):
        self._admin_password_hash: Optional[str] = None  # bcrypt hash as hex string
        self._jwt_secret: str = self._init_jwt_secret()
        self._sessions: dict[str, dict] = {}  # token -> session info
        self._login_attempts: dict[str, list] = {}  # ip -> timestamps
        self._max_attempts = 5
        self._lockout_minutes = 15
        self._session_expiry_hours = int(os.getenv("MAMOUN_JWT_EXPIRY_HOURS", "24"))
        self._initialized = False

        # SEC-003 Fix: Load admin password from environment if set
        admin_password = os.getenv("MAMOUN_ADMIN_PASSWORD", "")
        if admin_password and len(admin_password) >= 8:
            self._admin_password_hash = self._hash_password(admin_password)
            self._initialized = True
            logger.info("Admin password loaded from MAMOUN_ADMIN_PASSWORD env var")

        # تحميل الجلسات المحفوظة
        self._load_sessions()

    def _init_jwt_secret(self) -> str:
        """تهيئة JWT Secret — قراءة من env أو توليد وحفظ في .env"""
        secret = os.getenv("MAMOUN_JWT_SECRET", "")
        if secret and secret != "CHANGE_ME__run_openssl_rand_hex_32" and len(secret) >= 32:
            logger.info("JWT secret loaded from MAMOUN_JWT_SECRET env var")
            return secret

        # توليد secret جديد وحفظه في .env
        new_secret = secrets.token_hex(32)
        self._persist_to_env("MAMOUN_JWT_SECRET", new_secret)
        os.environ["MAMOUN_JWT_SECRET"] = new_secret
        logger.info("Generated and persisted new JWT secret to .env")
        return new_secret

    def _persist_to_env(self, key: str, value: str):
        """حفظ متغير بيئة في ملف .env"""
        try:
            lines = []
            if _ENV_FILE.exists():
                with open(_ENV_FILE, "r", encoding="utf-8") as f:
                    lines = f.readlines()

            found = False
            new_lines = []
            for line in lines:
                if line.strip().startswith(f"{key}="):
                    new_lines.append(f"{key}={value}\n")
                    found = True
                else:
                    new_lines.append(line)

            if not found:
                new_lines.append(f"{key}={value}\n")

            with open(_ENV_FILE, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            logger.warning("Failed to persist %s to .env: %s", key, e)

    def _load_sessions(self):
        """تحميل الجلسات المحفوظة من ملف JSON"""
        try:
            if _SESSIONS_FILE.exists():
                with open(_SESSIONS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # إزالة الجلسات المنتهية
                now = time.time()
                valid = {t: s for t, s in data.items() if s.get("expires_at", 0) > now}
                self._sessions = valid
                logger.info("Loaded %d valid sessions from disk", len(valid))
        except Exception as e:
            logger.warning("Failed to load sessions: %s", e)

    def _save_sessions(self):
        """حفظ الجلسات إلى ملف JSON"""
        try:
            _SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(_SESSIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._sessions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Failed to save sessions: %s", e)

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt with automatic salt generation."""
        salt = bcrypt.gensalt(rounds=12)  # VULN-024 Fix: bcrypt with cost factor 12
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')  # Store as string

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify a password against a bcrypt hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
        except (ValueError, TypeError):
            return False

    def setup_admin(self, password: str) -> str:
        """Set up admin password for the first time. Returns a JWT token."""
        if self._admin_password_hash is not None:
            raise ValueError("Admin password already set. Use change_password instead.")

        if len(password) < 8:  # VULN-026 Fix: Consistent 8-char minimum
            raise ValueError("Password must be at least 8 characters")

        self._admin_password_hash = self._hash_password(password)
        self._initialized = True
        return self._create_token()

    def login(self, password: str, client_ip: str = "0.0.0.0") -> Optional[str]:
        """Authenticate admin and return JWT token, or None if failed."""
        # Check lockout
        if self._is_locked_out(client_ip):
            return None

        # Check password
        if self._admin_password_hash is None:
            return None

        if not self._verify_password(password, self._admin_password_hash):
            self._record_failed_attempt(client_ip)
            return None

        # Clear failed attempts on success
        self._login_attempts.pop(client_ip, None)

        return self._create_token()

    def verify_token(self, token: str) -> bool:
        """Verify a JWT token is valid and not expired."""
        if token not in self._sessions:
            return False

        session = self._sessions[token]
        expires_at = session.get("expires_at", 0)

        if time.time() > expires_at:
            self._sessions.pop(token, None)
            return False

        return True

    def logout(self, token: str) -> bool:
        """Invalidate a session token."""
        result = self._sessions.pop(token, None) is not None
        if result:
            self._save_sessions()
        return result

    def change_password(self, old_password: str, new_password: str) -> bool:
        """Change admin password. Requires current password."""
        if self._admin_password_hash is None:
            return False

        if not self._verify_password(old_password, self._admin_password_hash):
            return False

        if len(new_password) < 8:  # VULN-026 Fix: Consistent 8-char minimum
            raise ValueError("Password must be at least 8 characters")

        self._admin_password_hash = self._hash_password(new_password)
        # Invalidate all sessions
        self._sessions.clear()
        self._save_sessions()
        return True

    def is_initialized(self) -> bool:
        """Check if admin password has been set up."""
        return self._admin_password_hash is not None

    def _create_token(self) -> str:
        """Create a new session token."""
        token = secrets.token_hex(32)
        expires_at = time.time() + (self._session_expiry_hours * 3600)

        self._sessions[token] = {
            "created_at": time.time(),
            "expires_at": expires_at,
            "token_hint": token[:8],
        }

        # Clean expired sessions
        now = time.time()
        expired = [t for t, s in self._sessions.items() if s["expires_at"] < now]
        for t in expired:
            del self._sessions[t]

        # حفظ الجلسات بعد أي تغيير
        self._save_sessions()

        return token

    def _is_locked_out(self, client_ip: str) -> bool:
        """Check if an IP is locked out due to too many failed attempts."""
        attempts = self._login_attempts.get(client_ip, [])
        if len(attempts) >= self._max_attempts:
            last_attempt = max(attempts)
            if time.time() - last_attempt < self._lockout_minutes * 60:
                return True
            # Lockout expired, clear attempts
            self._login_attempts.pop(client_ip, None)
        return False

    def _record_failed_attempt(self, client_ip: str):
        """Record a failed login attempt."""
        if client_ip not in self._login_attempts:
            self._login_attempts[client_ip] = []

        self._login_attempts[client_ip].append(time.time())

        # Keep only recent attempts
        cutoff = time.time() - self._lockout_minutes * 60
        self._login_attempts[client_ip] = [
            t for t in self._login_attempts[client_ip] if t > cutoff
        ]


# Singleton
auth_manager = AuthManager()
