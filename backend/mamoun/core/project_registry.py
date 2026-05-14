"""
BABSHARQII v31.0 — Project Registry (سجل المشاريع المركزي)
فهرس مركزي لكل المشاريع — حالة كل واحد، آخر تحديث، نسبة الإنجاز

المشكلة: ProjectOrchestrator يحفظ مشاريع منفصلة في state.json بدون فهرس مركزي
الحل: ProjectRegistry — فهرس موحد يقرأ كل state.json ويقدم API مركزي

Features:
  - register_project()     # تسجيل مشروع جديد
  - get_all_projects()     # قائمة كل المشاريع + حالاتها
  - get_project_status()   # حالة مشروع واحد
  - update_project()       # تحديث حالة
  - load_from_disk()       # قراءة كل state.json عند التشغيل
  - persist_registry()     # حفظ الفهرس المركزي
  - get_summary()          # ملخص: كم مشروع نشط، كم متوقف، الخ
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.core.project_registry")


# ═══════════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class ProjectHealth(str, Enum):
    """صحة المشروع"""
    HEALTHY = "healthy"           # يعمل بشكل طبيعي
    WARNING = "warning"           # تحذيرات
    CRITICAL = "critical"         # مشاكل حرجة
    STALE = "stale"               # لم يُفحص منذ فترة
    UNKNOWN = "unknown"           # لا معلومات


class ProjectStatus(str, Enum):
    """حالة المشروع"""
    ACTIVE = "active"             # يعمل حالياً
    IDLE = "idle"                 # خامل
    BUILDING = "building"         # قيد البناء
    FAILED = "failed"             # فشل
    PAUSED = "paused"             # متوقف مؤقتاً
    DELIVERED = "delivered"       # تم التسليم
    ARCHIVED = "archived"         # مؤرشف


@dataclass
class ProjectEntry:
    """سجل مشروع في الفهرس المركزي"""
    project_id: str = ""
    name: str = ""
    description: str = ""
    status: str = ProjectStatus.IDLE.value
    health: str = ProjectHealth.UNKNOWN.value
    phase: str = ""                     # من ProjectOrchestrator: idea/researching/planning/building/delivered
    
    # GitHub
    repo_url: str = ""
    branch: str = ""
    last_commit: str = ""
    last_commit_time: float = 0.0
    
    # Metrics
    completion_pct: float = 0.0         # نسبة الإنجاز 0-100
    steps_completed: int = 0
    steps_total: int = 0
    artifacts_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    
    # Timestamps
    created_at: float = 0.0
    updated_at: float = 0.0
    last_checked_at: float = 0.0        # آخر فحص بواسطة SmartScheduler
    
    # Tags
    tags: List[str] = field(default_factory=list)
    category: str = ""
    
    # Priority (for SmartScheduler)
    priority_score: float = 0.0         # 0-1, higher = more urgent
    
    def __post_init__(self):
        if not self.project_id:
            self.project_id = f"proj_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()
        self.updated_at = time.time()
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "ProjectEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RegistrySummary:
    """ملخص الفهرس المركزي"""
    total_projects: int = 0
    active_projects: int = 0
    idle_projects: int = 0
    building_projects: int = 0
    failed_projects: int = 0
    delivered_projects: int = 0
    archived_projects: int = 0
    healthy_projects: int = 0
    warning_projects: int = 0
    critical_projects: int = 0
    stale_projects: int = 0
    avg_completion: float = 0.0
    last_updated: float = 0.0
    
    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# Project Registry — الفهرس المركزي
# ═══════════════════════════════════════════════════════════════════════════════

class ProjectRegistry:
    """
    سجل المشاريع المركزي — الملف الواحد الذي يقول:
    "لدي 200 مشروع، حالة كل واحد كذا، آخر تحديث كذا، نسبة الإنجاز كذا"
    
    This is the SINGLE SOURCE OF TRUTH for all project status.
    All other systems (SmartScheduler, SessionContext, ProjectPool, Dashboard)
    read from this registry.
    """
    
    REGISTRY_VERSION = "1.0.0"
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or UNIFIED_DB_PATH
        self._projects: Dict[str, ProjectEntry] = {}
        self._data_dir = Path(__file__).parent.parent.parent.parent / "download" / "projects"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._initialized = False
    
    def initialize(self) -> bool:
        """تهيئة الفهرس — قراءة كل state.json من القرص"""
        try:
            self._ensure_schema()
            self._load_from_db()
            self._sync_from_disk()
            self._initialized = True
            logger.info("ProjectRegistry initialized — %d projects loaded", len(self._projects))
            return True
        except Exception as e:
            logger.error("ProjectRegistry init failed: %s", e)
            return False
    
    def _ensure_schema(self):
        """إنشاء جداول قاعدة البيانات"""
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS project_registry (
                project_id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                status TEXT,
                health TEXT,
                phase TEXT,
                repo_url TEXT,
                branch TEXT,
                last_commit TEXT,
                last_commit_time REAL,
                completion_pct REAL,
                steps_completed INTEGER,
                steps_total INTEGER,
                artifacts_count INTEGER,
                error_count INTEGER,
                warning_count INTEGER,
                created_at REAL,
                updated_at REAL,
                last_checked_at REAL,
                tags TEXT,
                category TEXT,
                priority_score REAL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS registry_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )""")
            conn.commit()
        finally:
            conn.close()
    
    def _load_from_db(self):
        """تحميل من قاعدة البيانات"""
        conn = get_db_connection(self.db_path)
        try:
            cur = conn.execute("SELECT * FROM project_registry")
            columns = [desc[0] for desc in cur.description]
            for row in cur.fetchall():
                data = dict(zip(columns, row))
                # Parse tags from JSON string
                if data.get("tags"):
                    try:
                        data["tags"] = json.loads(data["tags"])
                    except (json.JSONDecodeError, TypeError):
                        data["tags"] = []
                else:
                    data["tags"] = []
                entry = ProjectEntry.from_dict(data)
                self._projects[entry.project_id] = entry
        finally:
            conn.close()
    
    def _sync_from_disk(self):
        """قراءة كل state.json من القرص ومزامنة الفهرس"""
        if not self._data_dir.exists():
            return
        
        synced = 0
        for project_dir in self._data_dir.iterdir():
            if not project_dir.is_dir():
                continue
            state_file = project_dir / "state.json"
            if not state_file.exists():
                continue
            
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                
                project_id = state.get("id", project_dir.name)
                
                # Update or create entry
                if project_id in self._projects:
                    entry = self._projects[project_id]
                else:
                    entry = ProjectEntry(project_id=project_id)
                
                # Sync from state.json
                entry.name = state.get("name", entry.name)
                entry.description = state.get("description", entry.description)
                entry.phase = state.get("phase", entry.phase)
                entry.repo_url = state.get("repo_url", entry.repo_url)
                
                # Calculate completion
                steps = state.get("steps", [])
                if steps:
                    entry.steps_completed = sum(1 for s in steps if s.get("status") == "completed")
                    entry.steps_total = len(steps)
                    entry.completion_pct = (entry.steps_completed / entry.steps_total * 100) if entry.steps_total > 0 else 0
                
                entry.artifacts_count = len(state.get("artifacts", []))
                entry.updated_at = state.get("updated_at", entry.updated_at)
                
                # Determine status from phase
                phase = entry.phase
                if phase in ("delivered",):
                    entry.status = ProjectStatus.DELIVERED.value
                elif phase in ("building",):
                    entry.status = ProjectStatus.BUILDING.value
                elif phase in ("paused",):
                    entry.status = ProjectStatus.PAUSED.value
                elif phase in ("cancelled",):
                    entry.status = ProjectStatus.FAILED.value
                elif phase in ("idea", "researching", "research_done", "planning", "plan_done"):
                    entry.status = ProjectStatus.ACTIVE.value
                else:
                    entry.status = ProjectStatus.IDLE.value
                
                # Calculate health
                entry.health = self._calculate_health(entry)
                
                self._projects[project_id] = entry
                synced += 1
                
            except Exception as e:
                logger.warning("Failed to sync project from %s: %s", project_dir, e)
        
        if synced > 0:
            self.persist_registry()
            logger.info("Synced %d projects from disk", synced)
    
    def _calculate_health(self, entry: ProjectEntry) -> str:
        """حساب صحة المشروع"""
        now = time.time()
        
        # Stale check: not checked in 24 hours
        if entry.last_checked_at > 0 and (now - entry.last_checked_at) > 86400:
            return ProjectHealth.STALE.value
        
        # Critical: too many errors
        if entry.error_count > 5:
            return ProjectHealth.CRITICAL.value
        
        # Failed status
        if entry.status == ProjectStatus.FAILED.value:
            return ProjectHealth.CRITICAL.value
        
        # Warning: has warnings or errors
        if entry.error_count > 0 or entry.warning_count > 3:
            return ProjectHealth.WARNING.value
        
        # Healthy
        if entry.status in (ProjectStatus.ACTIVE.value, ProjectStatus.BUILDING.value, ProjectStatus.DELIVERED.value):
            return ProjectHealth.HEALTHY.value
        
        return ProjectHealth.UNKNOWN.value
    
    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────
    
    def register_project(self, name: str, description: str = "", 
                         repo_url: str = "", branch: str = "",
                         tags: List[str] = None, category: str = "") -> ProjectEntry:
        """تسجيل مشروع جديد في الفهرس المركزي"""
        entry = ProjectEntry(
            name=name,
            description=description,
            repo_url=repo_url,
            branch=branch or "main",
            tags=tags or [],
            category=category,
        )
        self._projects[entry.project_id] = entry
        self.persist_registry()
        
        logger.info("Project registered: %s (%s)", name, entry.project_id)
        return entry
    
    def get_all_projects(self) -> List[ProjectEntry]:
        """قائمة كل المشاريع + حالاتها"""
        return list(self._projects.values())
    
    def get_project_status(self, project_id: str) -> Optional[ProjectEntry]:
        """حالة مشروع واحد"""
        return self._projects.get(project_id)
    
    def update_project(self, project_id: str, **kwargs) -> Optional[ProjectEntry]:
        """تحديث حالة مشروع"""
        entry = self._projects.get(project_id)
        if not entry:
            return None
        
        for key, value in kwargs.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        
        entry.updated_at = time.time()
        entry.health = self._calculate_health(entry)
        
        self._projects[project_id] = entry
        self.persist_registry()
        
        return entry
    
    def remove_project(self, project_id: str) -> bool:
        """إزالة مشروع من الفهرس"""
        if project_id in self._projects:
            del self._projects[project_id]
            # Remove from DB
            conn = get_db_connection(self.db_path)
            try:
                conn.execute("DELETE FROM project_registry WHERE project_id = ?", (project_id,))
                conn.commit()
            finally:
                conn.close()
            return True
        return False
    
    def get_projects_by_status(self, status: str) -> List[ProjectEntry]:
        """مشاريع بحالة معينة"""
        return [p for p in self._projects.values() if p.status == status]
    
    def get_projects_by_health(self, health: str) -> List[ProjectEntry]:
        """مشاريع بصحة معينة"""
        return [p for p in self._projects.values() if p.health == health]
    
    def get_projects_by_tag(self, tag: str) -> List[ProjectEntry]:
        """مشاريع بوسم معين"""
        return [p for p in self._projects.values() if tag in p.tags]
    
    def get_stale_projects(self, threshold_hours: int = 24) -> List[ProjectEntry]:
        """مشاريع لم تُفحص منذ فترة"""
        now = time.time()
        threshold = threshold_hours * 3600
        return [
            p for p in self._projects.values()
            if p.status not in (ProjectStatus.DELIVERED.value, ProjectStatus.ARCHIVED.value)
            and (now - p.last_checked_at) > threshold
        ]
    
    def get_summary(self) -> RegistrySummary:
        """ملخص شامل للفهرس"""
        projects = list(self._projects.values())
        
        summary = RegistrySummary(
            total_projects=len(projects),
            active_projects=sum(1 for p in projects if p.status == ProjectStatus.ACTIVE.value),
            idle_projects=sum(1 for p in projects if p.status == ProjectStatus.IDLE.value),
            building_projects=sum(1 for p in projects if p.status == ProjectStatus.BUILDING.value),
            failed_projects=sum(1 for p in projects if p.status == ProjectStatus.FAILED.value),
            delivered_projects=sum(1 for p in projects if p.status == ProjectStatus.DELIVERED.value),
            archived_projects=sum(1 for p in projects if p.status == ProjectStatus.ARCHIVED.value),
            healthy_projects=sum(1 for p in projects if p.health == ProjectHealth.HEALTHY.value),
            warning_projects=sum(1 for p in projects if p.health == ProjectHealth.WARNING.value),
            critical_projects=sum(1 for p in projects if p.health == ProjectHealth.CRITICAL.value),
            stale_projects=sum(1 for p in projects if p.health == ProjectHealth.STALE.value),
            last_updated=time.time(),
        )
        
        if projects:
            summary.avg_completion = sum(p.completion_pct for p in projects) / len(projects)
        
        return summary
    
    def load_from_disk(self):
        """إعادة قراءة كل state.json من القرص"""
        self._sync_from_disk()
    
    def persist_registry(self):
        """حفظ الفهرس المركزي في قاعدة البيانات"""
        conn = get_db_connection(self.db_path)
        try:
            for entry in self._projects.values():
                data = entry.to_dict()
                data["tags"] = json.dumps(data.get("tags", []), ensure_ascii=False)
                
                conn.execute("""
                    INSERT OR REPLACE INTO project_registry 
                    (project_id, name, description, status, health, phase,
                     repo_url, branch, last_commit, last_commit_time,
                     completion_pct, steps_completed, steps_total, artifacts_count,
                     error_count, warning_count,
                     created_at, updated_at, last_checked_at,
                     tags, category, priority_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data["project_id"], data["name"], data["description"],
                    data["status"], data["health"], data["phase"],
                    data["repo_url"], data["branch"], data["last_commit"], data["last_commit_time"],
                    data["completion_pct"], data["steps_completed"], data["steps_total"],
                    data["artifacts_count"], data["error_count"], data["warning_count"],
                    data["created_at"], data["updated_at"], data["last_checked_at"],
                    data["tags"], data["category"], data["priority_score"],
                ))
            
            # Save meta
            conn.execute(
                "INSERT OR REPLACE INTO registry_meta (key, value) VALUES (?, ?)",
                ("version", self.REGISTRY_VERSION),
            )
            conn.execute(
                "INSERT OR REPLACE INTO registry_meta (key, value) VALUES (?, ?)",
                ("last_persist", str(time.time())),
            )
            conn.commit()
        finally:
            conn.close()
    
    def search_projects(self, query: str) -> List[ProjectEntry]:
        """بحث في المشاريع"""
        query_lower = query.lower()
        return [
            p for p in self._projects.values()
            if query_lower in p.name.lower() 
            or query_lower in p.description.lower()
            or any(query_lower in tag.lower() for tag in p.tags)
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_project_registry: Optional[ProjectRegistry] = None

def get_project_registry() -> ProjectRegistry:
    """الحصول على سجل المشاريع المركزي (Singleton)"""
    global _project_registry
    if _project_registry is None:
        _project_registry = ProjectRegistry()
        _project_registry.initialize()
    return _project_registry
