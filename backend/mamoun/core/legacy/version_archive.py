"""
BABSHARQII v30.0 — Version Archive
أرشيف الإصدارات — يحفظ كل إصدار من الكود قبل التعديل

Features:
  - Saves every version of code before modification
  - Enables instant rollback if tests fail
  - Learns from failures (records failure + cause)
  - SQLite-backed for persistence across restarts
"""

import os
import time
import json
import logging
import hashlib
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.version_archive")


@dataclass
class VersionEntry:
    """إصدار — A version of a file"""
    id: str = ""
    file_path: str = ""
    version_number: int = 1
    content_hash: str = ""
    content: str = ""
    timestamp: float = 0.0
    reason: str = ""
    test_result: str = ""      # pass, fail, unknown
    failure_cause: str = ""
    rolled_back: bool = False

    def __post_init__(self):
        if not self.id:
            self.id = f"v_{hashlib.md5(f'{self.file_path}{self.version_number}{time.time()}'.encode()).hexdigest()[:12]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        d = asdict(self)
        # Don't include full content in dict to save space
        d["content_length"] = len(self.content)
        d.pop("content", None)
        return d


class VersionArchive:
    """
    أرشيف الإصدارات — Version Archive
    
    Saves every version of code before modification.
    Enables instant rollback if tests fail.
    Learns from failures.
    """

    MAX_VERSIONS_PER_FILE = 50

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or UNIFIED_DB_PATH
        self._initialized = False

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._initialized = True
            logger.info("VersionArchive initialized")
            return True
        except Exception as e:
            logger.error("VersionArchive init failed: %s", e)
            return False

    def _ensure_schema(self):
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_db_connection(self._db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS va_versions (
                id TEXT PRIMARY KEY, file_path TEXT, version_number INTEGER,
                content_hash TEXT, content TEXT, timestamp REAL, reason TEXT,
                test_result TEXT, failure_cause TEXT, rolled_back INTEGER)""")
            conn.execute("""CREATE INDEX IF NOT EXISTS idx_va_file ON va_versions (file_path)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS va_lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT, file_path TEXT,
                failure_cause TEXT, lesson TEXT, timestamp REAL)""")
            conn.commit()
        finally:
            conn.close()

    def save_version(self, file_path: str, reason: str = "pre_modification") -> Optional[VersionEntry]:
        """
        حفظ إصدار — Save current version of a file
        
        Reads the file, creates a hash, and stores it.
        Returns the VersionEntry or None if file doesn't exist.
        """
        path = Path(file_path)
        if not path.exists():
            logger.warning("File not found for versioning: %s", file_path)
            return None

        try:
            content = path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error("Failed to read file for versioning: %s", e)
            return None

        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        version_number = self._get_next_version(file_path)

        entry = VersionEntry(
            file_path=str(path),
            version_number=version_number,
            content_hash=content_hash,
            content=content,
            reason=reason,
        )

        self._persist_entry(entry)
        self._cleanup_old_versions(file_path)

        logger.info("Saved version #%d of %s (hash=%s)", version_number, file_path, content_hash)
        return entry

    def rollback(self, file_path: str, version_number: Optional[int] = None) -> bool:
        """
        تراجع — Rollback to a specific version
        
        If version_number is None, rolls back to the previous version.
        """
        if version_number is None:
            version_number = self._get_latest_version(file_path) - 1
            if version_number < 1:
                logger.warning("No previous version to rollback to for %s", file_path)
                return False

        entry = self._load_entry(file_path, version_number)
        if not entry:
            logger.warning("Version %d not found for %s", version_number, file_path)
            return False

        try:
            path = Path(file_path)
            path.write_text(entry.content, encoding='utf-8')

            # Mark as rolled back
            entry.rolled_back = True
            self._update_entry(entry)

            # Record lesson
            self._record_lesson(file_path, entry.failure_cause or "manual_rollback")

            logger.info("Rolled back %s to version %d", file_path, version_number)
            return True
        except Exception as e:
            logger.error("Rollback failed for %s: %s", file_path, e)
            return False

    def record_test_result(self, file_path: str, version_number: int,
                           result: str, failure_cause: str = ""):
        """تسجيل نتيجة الاختبار — Record test result for a version"""
        entry = self._load_entry(file_path, version_number)
        if entry:
            entry.test_result = result
            entry.failure_cause = failure_cause
            self._update_entry(entry)

            # If failed, record lesson
            if result == "fail" and failure_cause:
                self._record_lesson(file_path, failure_cause)

    def get_versions(self, file_path: str) -> List[dict]:
        """الحصول على إصدارات ملف — Get all versions of a file"""
        versions = []
        try:
            conn = get_db_connection(self._db_path)
            try:
                cur = conn.execute(
                    "SELECT id, file_path, version_number, content_hash, "
                    "timestamp, reason, test_result, failure_cause, rolled_back "
                    "FROM va_versions WHERE file_path = ? ORDER BY version_number DESC",
                    (str(Path(file_path)),),
                )
                for row in cur.fetchall():
                    versions.append({
                        "id": row[0],
                        "file_path": row[1],
                        "version_number": row[2],
                        "content_hash": row[3],
                        "timestamp": row[4],
                        "reason": row[5],
                        "test_result": row[6],
                        "failure_cause": row[7],
                        "rolled_back": bool(row[8]),
                    })
            finally:
                conn.close()
        except Exception:
            pass
        return versions

    def get_lessons(self, file_path: str = "") -> List[dict]:
        """الحصول على الدروس المستفادة — Get learned lessons"""
        lessons = []
        try:
            conn = get_db_connection(self._db_path)
            try:
                if file_path:
                    cur = conn.execute(
                        "SELECT file_path, failure_cause, lesson, timestamp "
                        "FROM va_lessons WHERE file_path = ? ORDER BY timestamp DESC",
                        (str(Path(file_path)),),
                    )
                else:
                    cur = conn.execute(
                        "SELECT file_path, failure_cause, lesson, timestamp "
                        "FROM va_lessons ORDER BY timestamp DESC LIMIT 50",
                    )
                for row in cur.fetchall():
                    lessons.append({
                        "file_path": row[0],
                        "failure_cause": row[1],
                        "lesson": row[2],
                        "timestamp": row[3],
                    })
            finally:
                conn.close()
        except Exception:
            pass
        return lessons

    def get_status(self) -> dict:
        try:
            conn = get_db_connection(self._db_path)
            try:
                cur = conn.execute("SELECT COUNT(*) FROM va_versions")
                total = cur.fetchone()[0]
                cur = conn.execute("SELECT COUNT(DISTINCT file_path) FROM va_versions")
                files = cur.fetchone()[0]
                cur = conn.execute("SELECT COUNT(*) FROM va_lessons")
                lessons = cur.fetchone()[0]
                return {
                    "initialized": self._initialized,
                    "total_versions": total,
                    "tracked_files": files,
                    "lessons_learned": lessons,
                }
            finally:
                conn.close()
        except Exception:
            return {"initialized": self._initialized}

    # ─── Internal helpers ────────────────────────────────────────────────────

    def _get_next_version(self, file_path: str) -> int:
        latest = self._get_latest_version(file_path)
        return latest + 1

    def _get_latest_version(self, file_path: str) -> int:
        try:
            conn = get_db_connection(self._db_path)
            try:
                cur = conn.execute(
                    "SELECT MAX(version_number) FROM va_versions WHERE file_path = ?",
                    (str(Path(file_path)),),
                )
                row = cur.fetchone()
                return row[0] if row and row[0] else 0
            finally:
                conn.close()
        except Exception:
            return 0

    def _load_entry(self, file_path: str, version_number: int) -> Optional[VersionEntry]:
        try:
            conn = get_db_connection(self._db_path)
            try:
                cur = conn.execute(
                    "SELECT id, file_path, version_number, content_hash, content, "
                    "timestamp, reason, test_result, failure_cause, rolled_back "
                    "FROM va_versions WHERE file_path = ? AND version_number = ?",
                    (str(Path(file_path)), version_number),
                )
                row = cur.fetchone()
                if row:
                    return VersionEntry(
                        id=row[0], file_path=row[1], version_number=row[2],
                        content_hash=row[3], content=row[4], timestamp=row[5],
                        reason=row[6], test_result=row[7], failure_cause=row[8],
                        rolled_back=bool(row[9]),
                    )
            finally:
                conn.close()
        except Exception:
            pass
        return None

    def _persist_entry(self, entry: VersionEntry):
        try:
            conn = get_db_connection(self._db_path)
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO va_versions "
                    "(id, file_path, version_number, content_hash, content, "
                    "timestamp, reason, test_result, failure_cause, rolled_back) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (entry.id, entry.file_path, entry.version_number,
                     entry.content_hash, entry.content, entry.timestamp,
                     entry.reason, entry.test_result, entry.failure_cause,
                     int(entry.rolled_back)),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Failed to persist version entry: %s", e)

    def _update_entry(self, entry: VersionEntry):
        try:
            conn = get_db_connection(self._db_path)
            try:
                conn.execute(
                    "UPDATE va_versions SET test_result=?, failure_cause=?, rolled_back=? "
                    "WHERE id=?",
                    (entry.test_result, entry.failure_cause, int(entry.rolled_back), entry.id),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception:
            pass

    def _cleanup_old_versions(self, file_path: str):
        """Remove old versions beyond MAX_VERSIONS_PER_FILE"""
        try:
            conn = get_db_connection(self._db_path)
            try:
                cur = conn.execute(
                    "SELECT COUNT(*) FROM va_versions WHERE file_path = ?",
                    (str(Path(file_path)),),
                )
                count = cur.fetchone()[0]
                if count > self.MAX_VERSIONS_PER_FILE:
                    # Delete oldest versions, keeping the latest
                    conn.execute(
                        "DELETE FROM va_versions WHERE file_path = ? AND version_number < "
                        "(SELECT MIN(version_number) FROM (SELECT version_number FROM va_versions "
                        "WHERE file_path = ? ORDER BY version_number DESC LIMIT ?))",
                        (str(Path(file_path)), str(Path(file_path)), self.MAX_VERSIONS_PER_FILE),
                    )
                    conn.commit()
            finally:
                conn.close()
        except Exception:
            pass

    def _record_lesson(self, file_path: str, failure_cause: str):
        """تسجيل درس مستفاد — Record a lesson from a failure"""
        lesson = f"Avoid: {failure_cause} in {Path(file_path).name}"
        try:
            conn = get_db_connection(self._db_path)
            try:
                conn.execute(
                    "INSERT INTO va_lessons (file_path, failure_cause, lesson, timestamp) "
                    "VALUES (?, ?, ?, ?)",
                    (str(Path(file_path)), failure_cause, lesson, time.time()),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception:
            pass


# Singleton
version_archive = VersionArchive()
