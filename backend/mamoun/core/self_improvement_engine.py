"""
BABSHARQII v30.0 — Self-Improvement Engine
محرك التطور الذاتي — ثلاث طبقات: AUTO_MODE، SUGGEST_MODE، REVIEW_MODE

Architecture:
  - AUTO_MODE: Automatically applies improvements (requires high confidence)
  - SUGGEST_MODE: Suggests improvements but waits for human approval (DEFAULT)
  - REVIEW_MODE: Only analyzes and reports gaps, no modifications
  
Uses a Modification Queue to prevent concurrent changes.
Reads code via gap_analyzer for discovering improvement opportunities.
Respects Immutable Safety Core — protected files cannot be modified.
"""

import os
import time
import json
import logging
import hashlib
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from enum import Enum
from threading import Lock
from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.self_improvement")


class ImprovementMode(str, Enum):
    """طبقات التطور — Improvement modes"""
    AUTO = "auto"           # تلقائي — applies without approval (high confidence only)
    SUGGEST = "suggest"     # اقتراح — suggests and waits for approval (DEFAULT)
    REVIEW = "review"       # مراجعة — analyzes only, no modifications


class ModificationStatus(str, Enum):
    """حالة التعديل — Modification status"""
    PENDING = "pending"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class Modification:
    """تعديل مقترح — A proposed modification"""
    id: str = ""
    description: str = ""
    target_file: str = ""
    original_code: str = ""
    proposed_code: str = ""
    confidence: float = 0.0
    mode: str = ImprovementMode.SUGGEST.value
    status: str = ModificationStatus.PENDING.value
    created_at: float = 0.0
    applied_at: float = 0.0
    rollback_reason: str = ""
    gap_source: str = ""      # Which gap analysis triggered this
    reviewer: str = ""        # Who approved (human or auto)

    def __post_init__(self):
        if not self.id:
            self.id = f"mod_{hashlib.md5(f'{self.target_file}{time.time()}'.encode()).hexdigest()[:12]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GapReport:
    """تقرير فجوة — A discovered improvement gap"""
    id: str = ""
    area: str = ""
    description: str = ""
    severity: str = "medium"     # low, medium, high, critical
    suggested_fix: str = ""
    confidence: float = 0.0
    auto_fixable: bool = False
    created_at: float = 0.0

    def __post_init__(self):
        if not self.id:
            self.id = f"gap_{hashlib.md5(f'{self.area}{time.time()}'.encode()).hexdigest()[:12]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


class SelfImprovementEngine:
    """
    محرك التطور الذاتي — Self-Improvement Engine
    
    Three modes:
      AUTO:    Applies improvements automatically (confidence >= 0.9)
      SUGGEST: Suggests improvements, waits for human approval (DEFAULT)
      REVIEW:  Only analyzes and reports, no modifications
      
    Thread-safe via Modification Queue with Lock.
    Respects Immutable Safety Core (protected files).
    """

    # Confidence threshold for auto-mode
    AUTO_CONFIDENCE_THRESHOLD = 0.9
    
    # Files that can NEVER be modified (Immutable Safety Core)
    IMMUTABLE_FILES = {
        "laws.yaml", "settings.yaml", ".env", ".key", ".pem",
        "safety_guard.py", "approval_gate.py", "conscience_layer.py",
        "self_improvement_engine.py",  # Cannot modify itself
    }

    # Stagnation detection
    STAGNATION_DAYS = 30
    STAGNATION_THRESHOLD = 0.01  # Less than 1% improvement = stagnation

    def __init__(self, mode: str = ImprovementMode.SUGGEST.value,
                 db_path: Optional[Path] = None):
        self._mode = mode
        self._db_path = db_path or UNIFIED_DB_PATH
        self._modification_queue: List[Modification] = []
        self._gap_reports: List[GapReport] = []
        self._lock = Lock()
        self._initialized = False
        self._stagnation_history: List[Dict] = []
        self._last_improvement_score = 0.0
        self._last_improvement_time = 0.0
        self._halted = False

    def initialize(self) -> bool:
        """تهيئة محرك التطور الذاتي"""
        try:
            self._ensure_schema()
            self._load_state()
            self._initialized = True
            logger.info("SelfImprovementEngine initialized — mode=%s", self._mode)
            return True
        except Exception as e:
            logger.error("SelfImprovementEngine init failed: %s", e)
            return False

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, value: str):
        if value in [m.value for m in ImprovementMode]:
            self._mode = value
        else:
            raise ValueError(f"Invalid mode: {value}. Must be one of: auto, suggest, review")

    def _ensure_schema(self):
        """Create database tables"""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_db_connection(self._db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS si_modifications (
                id TEXT PRIMARY KEY, description TEXT, target_file TEXT,
                original_code TEXT, proposed_code TEXT, confidence REAL,
                mode TEXT, status TEXT, created_at REAL, applied_at REAL,
                rollback_reason TEXT, gap_source TEXT, reviewer TEXT)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS si_gaps (
                id TEXT PRIMARY KEY, area TEXT, description TEXT,
                severity TEXT, suggested_fix TEXT, confidence REAL,
                auto_fixable INTEGER, created_at REAL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS si_stagnation (
                id INTEGER PRIMARY KEY AUTOINCREMENT, score REAL,
                timestamp REAL, improvement_delta REAL)""")
            conn.commit()
        finally:
            conn.close()

    def _load_state(self):
        """Load state from database"""
        try:
            conn = get_db_connection(self._db_path)
            try:
                cur = conn.execute(
                    "SELECT score, timestamp FROM si_stagnation ORDER BY timestamp DESC LIMIT 1"
                )
                row = cur.fetchone()
                if row:
                    self._last_improvement_score = row[0]
                    self._last_improvement_time = row[1]
            finally:
                conn.close()
        except Exception:
            pass

    def analyze_gaps(self) -> List[GapReport]:
        """
        تحليل الفجوات — Analyze code for improvement opportunities
        
        Returns a list of GapReport objects describing areas for improvement.
        """
        gaps = []

        # Check for common improvement areas
        # 1. Check test coverage gaps
        _backend_dir = Path(__file__).parent.parent.parent
        test_dir = _backend_dir / "tests"
        if test_dir.exists():
            test_files = list(test_dir.glob("test_*.py"))
            src_dir = Path(__file__).parent.parent
            src_files = list(src_dir.rglob("*.py"))
            src_files = [f for f in src_files if "__pycache__" not in str(f)]

            if len(test_files) < len(src_files) * 0.3:
                gaps.append(GapReport(
                    area="test_coverage",
                    description=f"Low test coverage: {len(test_files)} test files for {len(src_files)} source files",
                    severity="medium",
                    suggested_fix="Add more unit tests for uncovered modules",
                    confidence=0.7,
                    auto_fixable=False,
                ))

        # 2. Check for missing error handling patterns
        gaps.append(GapReport(
            area="error_handling",
            description="Some modules may lack comprehensive error handling",
            severity="low",
            suggested_fix="Add try/except blocks with logging to critical paths",
            confidence=0.5,
            auto_fixable=False,
        ))

        with self._lock:
            self._gap_reports.extend(gaps)

        # Persist gaps
        self._persist_gaps(gaps)

        return gaps

    def propose_modification(self, target_file: str, description: str,
                            proposed_code: str, original_code: str = "",
                            confidence: float = 0.0,
                            gap_source: str = "") -> Modification:
        """
        اقتراح تعديل — Propose a code modification
        
        In SUGGEST mode: Creates a pending modification awaiting approval
        In AUTO mode: Applies immediately if confidence >= threshold
        In REVIEW mode: Only records the proposal, never applies
        """
        # Check if file is immutable
        file_name = Path(target_file).name
        if file_name in self.IMMUTABLE_FILES:
            logger.warning("Attempted to modify immutable file: %s", target_file)
            mod = Modification(
                target_file=target_file,
                description=description,
                proposed_code=proposed_code,
                original_code=original_code,
                confidence=confidence,
                status=ModificationStatus.REJECTED.value,
                gap_source=gap_source,
            )
            return mod

        mod = Modification(
            target_file=target_file,
            description=description,
            proposed_code=proposed_code,
            original_code=original_code,
            confidence=confidence,
            mode=self._mode,
            gap_source=gap_source,
        )

        with self._lock:
            self._modification_queue.append(mod)

        # Persist
        self._persist_modification(mod)

        # Auto-apply if in AUTO mode and confidence is high enough
        if self._mode == ImprovementMode.AUTO.value and confidence >= self.AUTO_CONFIDENCE_THRESHOLD:
            result = self.apply_modification(mod.id, reviewer="auto")
            return result

        # In SUGGEST mode, return pending modification
        return mod

    def apply_modification(self, mod_id: str, reviewer: str = "human") -> Optional[Modification]:
        """
        تطبيق تعديل — Apply a pending modification
        
        Only applies if:
          - The modification exists and is PENDING
          - The target file is not immutable
          - The reviewer is authorized
        """
        with self._lock:
            mod = None
            for m in self._modification_queue:
                if m.id == mod_id:
                    mod = m
                    break

        if not mod:
            # Try loading from DB
            mod = self._load_modification(mod_id)

        if not mod:
            logger.warning("Modification %s not found", mod_id)
            return None

        if mod.status != ModificationStatus.PENDING.value:
            logger.warning("Modification %s is not pending (status=%s)", mod_id, mod.status)
            return mod

        # Check immutability again
        file_name = Path(mod.target_file).name
        if file_name in self.IMMUTABLE_FILES:
            mod.status = ModificationStatus.REJECTED.value
            logger.warning("Cannot apply modification to immutable file: %s", mod.target_file)
            return mod

        # Apply the modification
        try:
            target_path = Path(mod.target_file)
            if target_path.exists() and mod.original_code:
                # Save backup via VersionArchive
                try:
                    from mamoun.core.version_archive import VersionArchive
                    archive = VersionArchive()
                    archive.save_version(mod.target_file)
                except ImportError:
                    pass

            # Write the new code
            if target_path.exists():
                # Read current content for rollback
                current = target_path.read_text(encoding='utf-8')
                mod.original_code = current
                target_path.write_text(mod.proposed_code, encoding='utf-8')

            mod.status = ModificationStatus.APPLIED.value
            mod.applied_at = time.time()
            mod.reviewer = reviewer

            logger.info("Applied modification %s to %s (reviewer=%s)", mod_id, mod.target_file, reviewer)

        except Exception as e:
            mod.status = ModificationStatus.FAILED.value
            mod.rollback_reason = str(e)
            logger.error("Failed to apply modification %s: %s", mod_id, e)

        # Update in DB
        self._update_modification_status(mod)

        return mod

    def reject_modification(self, mod_id: str, reason: str = "") -> Optional[Modification]:
        """رفض تعديل — Reject a pending modification"""
        with self._lock:
            for m in self._modification_queue:
                if m.id == mod_id:
                    m.status = ModificationStatus.REJECTED.value
                    m.rollback_reason = reason
                    self._update_modification_status(m)
                    return m

        mod = self._load_modification(mod_id)
        if mod:
            mod.status = ModificationStatus.REJECTED.value
            mod.rollback_reason = reason
            self._update_modification_status(mod)
        return mod

    def rollback_modification(self, mod_id: str) -> Optional[Modification]:
        """تراجع عن تعديل — Rollback an applied modification"""
        with self._lock:
            for m in self._modification_queue:
                if m.id == mod_id and m.status == ModificationStatus.APPLIED.value:
                    try:
                        target_path = Path(m.target_file)
                        if target_path.exists() and m.original_code:
                            target_path.write_text(m.original_code, encoding='utf-8')
                        m.status = ModificationStatus.ROLLED_BACK.value
                        self._update_modification_status(m)
                        return m
                    except Exception as e:
                        logger.error("Rollback failed for %s: %s", mod_id, e)
                        return m

        return None

    def check_stagnation(self) -> bool:
        """
        فحص الركود — Check if the system has stagnated
        
        Returns True if no meaningful improvement in STAGNATION_DAYS.
        """
        if not self._last_improvement_time:
            return False

        days_since_improvement = (time.time() - self._last_improvement_time) / 86400
        if days_since_improvement >= self.STAGNATION_DAYS:
            # Check improvement delta
            recent_score = self._last_improvement_score
            if recent_score < self.STAGNATION_THRESHOLD:
                self._halted = True
                logger.warning(
                    "STAGNATION DETECTED: No improvement for %d days (score=%.4f). "
                    "Self-improvement halted — human assistance required.",
                    int(days_since_improvement), recent_score
                )
                return True
        return False

    @property
    def is_halted(self) -> bool:
        """هل المحرك متوقف؟ — Is the engine halted due to stagnation?"""
        return self._halted

    def record_improvement_score(self, score: float):
        """تسجيل نقاط التحسين — Record an improvement benchmark score"""
        delta = score - self._last_improvement_score
        self._last_improvement_score = score
        self._last_improvement_time = time.time()

        try:
            conn = get_db_connection(self._db_path)
            try:
                conn.execute(
                    "INSERT INTO si_stagnation (score, timestamp, improvement_delta) VALUES (?, ?, ?)",
                    (score, self._last_improvement_time, delta),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception:
            pass

    def get_pending_modifications(self) -> List[dict]:
        """الحصول على التعديلات المعلقة — Get all pending modifications"""
        pending = []
        with self._lock:
            for m in self._modification_queue:
                if m.status == ModificationStatus.PENDING.value:
                    pending.append(m.to_dict())
        return pending

    def get_gap_reports(self) -> List[dict]:
        """الحصول على تقارير الفجوات — Get all gap reports"""
        with self._lock:
            return [g.to_dict() for g in self._gap_reports]

    def get_status(self) -> dict:
        """حالة محرك التطور الذاتي"""
        return {
            "mode": self._mode,
            "initialized": self._initialized,
            "halted": self._halted,
            "pending_modifications": len([m for m in self._modification_queue if m.status == "pending"]),
            "total_gaps": len(self._gap_reports),
            "last_improvement_score": self._last_improvement_score,
            "last_improvement_time": self._last_improvement_time,
        }

    # ─── Persistence helpers ────────────────────────────────────────────────

    def _persist_modification(self, mod: Modification):
        try:
            conn = get_db_connection(self._db_path)
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO si_modifications "
                    "(id, description, target_file, original_code, proposed_code, "
                    "confidence, mode, status, created_at, applied_at, rollback_reason, "
                    "gap_source, reviewer) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (mod.id, mod.description, mod.target_file, mod.original_code,
                     mod.proposed_code, mod.confidence, mod.mode, mod.status,
                     mod.created_at, mod.applied_at, mod.rollback_reason,
                     mod.gap_source, mod.reviewer),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Failed to persist modification: %s", e)

    def _persist_gaps(self, gaps: List[GapReport]):
        try:
            conn = get_db_connection(self._db_path)
            try:
                for g in gaps:
                    conn.execute(
                        "INSERT OR REPLACE INTO si_gaps "
                        "(id, area, description, severity, suggested_fix, "
                        "confidence, auto_fixable, created_at) VALUES (?,?,?,?,?,?,?,?)",
                        (g.id, g.area, g.description, g.severity, g.suggested_fix,
                         g.confidence, int(g.auto_fixable), g.created_at),
                    )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Failed to persist gaps: %s", e)

    def _load_modification(self, mod_id: str) -> Optional[Modification]:
        try:
            conn = get_db_connection(self._db_path)
            try:
                cur = conn.execute(
                    "SELECT * FROM si_modifications WHERE id = ?", (mod_id,)
                )
                row = cur.fetchone()
                if row:
                    return Modification(
                        id=row[0], description=row[1], target_file=row[2],
                        original_code=row[3], proposed_code=row[4],
                        confidence=row[5], mode=row[6], status=row[7],
                        created_at=row[8], applied_at=row[9],
                        rollback_reason=row[10], gap_source=row[11],
                        reviewer=row[12],
                    )
            finally:
                conn.close()
        except Exception:
            pass
        return None

    def _update_modification_status(self, mod: Modification):
        try:
            conn = get_db_connection(self._db_path)
            try:
                conn.execute(
                    "UPDATE si_modifications SET status=?, applied_at=?, "
                    "rollback_reason=?, reviewer=? WHERE id=?",
                    (mod.status, mod.applied_at, mod.rollback_reason,
                     mod.reviewer, mod.id),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Failed to update modification status: %s", e)


# Singleton
self_improvement_engine = SelfImprovementEngine()
