"""
BABSHARQII v31.0 — Smart Scheduler (الجدولة الذكية)
فحص دوري لكل المشاريع — سحب تحديثات GitHub، فحص الأخطاء، بناء تلقائياً

المشكلة: لا يوجد cron يفحص 200 مستودع مختلف
الحل: SmartScheduler — جدولة ذكية توزع المهام بالأولوية

Features:
  - register_project_repo()   # تسجيل مستودع مشروع
  - schedule_periodic_check() # فحص دوري لكل مشروع
  - prioritize_projects()     # ترتيب بالأولوية
  - distribute_work()         # توزيع المهام على نوى متوازية
  - report_schedule_status()  # تقرير: متى فُحص كل مشروع آخر مرة
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime, timezone

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.core.smart_scheduler")


# ═══════════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class CheckType(str, Enum):
    """أنواع الفحص"""
    GITHUB_SYNC = "github_sync"           # سحب تحديثات GitHub
    HEALTH_CHECK = "health_check"         # فحص صحة المشروع
    BUILD_TEST = "build_test"             # بناء واختبار
    ERROR_SCAN = "error_scan"             # فحص الأخطاء
    DEPENDENCY_UPDATE = "dependency_update"  # تحديث الاعتماديات


class TaskPriority(str, Enum):
    """أولوية المهمة"""
    CRITICAL = "critical"     # مشروع فاشل أو حرج
    HIGH = "high"             # مشروع فيه أخطاء
    MEDIUM = "medium"         # مشروع عادي
    LOW = "low"               # مشروع مستقر
    BACKGROUND = "background" # مهام خلفية


class TaskStatus(str, Enum):
    """حالة المهمة"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ScheduledTask:
    """مهمة مجدولة"""
    task_id: str = ""
    project_id: str = ""
    check_type: str = CheckType.HEALTH_CHECK.value
    priority: str = TaskPriority.MEDIUM.value
    status: str = TaskStatus.PENDING.value
    scheduled_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    result: dict = field(default_factory=dict)
    error: str = ""
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if not self.task_id:
            self.task_id = f"task_{uuid.uuid4().hex[:8]}"
        if not self.scheduled_at:
            self.scheduled_at = time.time()
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProjectScheduleConfig:
    """إعدادات جدولة مشروع"""
    project_id: str = ""
    repo_url: str = ""
    branch: str = "main"
    github_token: str = ""
    
    # Intervals (seconds)
    github_sync_interval: int = 300       # كل 5 دقائق
    health_check_interval: int = 600      # كل 10 دقائق
    build_test_interval: int = 3600       # كل ساعة
    error_scan_interval: int = 1800       # كل 30 دقيقة
    dependency_update_interval: int = 86400  # كل يوم
    
    # Last check timestamps
    last_github_sync: float = 0.0
    last_health_check: float = 0.0
    last_build_test: float = 0.0
    last_error_scan: float = 0.0
    last_dependency_update: float = 0.0
    
    # Priority boost
    error_count: int = 0
    consecutive_failures: int = 0
    
    enabled: bool = True
    
    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# Smart Scheduler — الجدولة الذكية
# ═══════════════════════════════════════════════════════════════════════════════

class SmartScheduler:
    """
    الجدولة الذكية — فحص دوري لكل المشاريع
    
    How it works:
    1. كل مشروع مسجل له إعدادات جدولة (فترات فحص مختلفة)
    2. المُجدول يفحص دورياً أي مشروع يحتاج فحص
    3. يرتب المشاريع بالأولوية (مشروع فيه أخطاء أولاً)
    4. يوزع المهام على ProjectPool (موازاة حقيقية)
    5. يُحدّث ProjectRegistry بالنتائج
    """
    
    CHECK_INTERVAL = 60  # فحص كل 60 ثانية: أي مشروع يحتاج فحص؟
    MAX_CONCURRENT = 5   # أقصى عدد مهام متوازية
    
    def __init__(self, project_registry=None, project_pool=None):
        self._registry = project_registry
        self._pool = project_pool
        self._schedules: Dict[str, ProjectScheduleConfig] = {}
        self._task_queue: List[ScheduledTask] = []
        self._task_history: List[ScheduledTask] = []
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._check_count = 0
        self._db_path = UNIFIED_DB_PATH
        
        # Callbacks for check execution
        self._check_handlers: Dict[str, Callable] = {}
    
    def set_registry(self, registry):
        """تعيين سجل المشاريع"""
        self._registry = registry
    
    def set_pool(self, pool):
        """تعيين حوض المشاريع"""
        self._pool = pool
    
    def register_check_handler(self, check_type: str, handler: Callable):
        """تسجيل معالج لنوع فحص"""
        self._check_handlers[check_type] = handler
    
    # ─────────────────────────────────────────────────────────────────────────
    # Schedule Management
    # ─────────────────────────────────────────────────────────────────────────
    
    def register_project_repo(self, project_id: str, repo_url: str = "",
                               branch: str = "main", github_token: str = "",
                               **intervals) -> ProjectScheduleConfig:
        """تسجيل مستودع مشروع للجدولة"""
        config = ProjectScheduleConfig(
            project_id=project_id,
            repo_url=repo_url,
            branch=branch,
            github_token=github_token,
        )
        
        # Override default intervals if provided
        for key, value in intervals.items():
            if hasattr(config, key) and isinstance(value, (int, float)):
                setattr(config, key, value)
        
        self._schedules[project_id] = config
        self._persist_schedule(config)
        
        logger.info("Project scheduled: %s (repo: %s)", project_id, repo_url[:50] if repo_url else "none")
        return config
    
    def unregister_project(self, project_id: str):
        """إلغاء جدولة مشروع"""
        if project_id in self._schedules:
            del self._schedules[project_id]
    
    def get_schedule(self, project_id: str) -> Optional[ProjectScheduleConfig]:
        """الحصول على إعدادات جدولة مشروع"""
        return self._schedules.get(project_id)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Prioritization
    # ─────────────────────────────────────────────────────────────────────────
    
    def prioritize_projects(self) -> List[str]:
        """
        ترتيب المشاريع بالأولوية
        
        Priority factors:
        1. عدد الأخطاء (أكثر أخطاء = أولوية أعلى)
        2. الفشل المتتالي (أكثر فشل = أولوية أعلى)
        3. مدة عدم الفحص (أطول مدة = أولوية أعلى)
        4. حالة المشروع (فاشل > متوقف > نشط > خامل)
        """
        now = time.time()
        scored = []
        
        for project_id, config in self._schedules.items():
            if not config.enabled:
                continue
            
            score = 0.0
            
            # Factor 1: Error count (0-30 points)
            score += min(config.error_count * 5, 30)
            
            # Factor 2: Consecutive failures (0-25 points)
            score += min(config.consecutive_failures * 8, 25)
            
            # Factor 3: Time since last check (0-25 points)
            min_last = min(
                config.last_github_sync or 0,
                config.last_health_check or 0,
            )
            hours_since = (now - min_last) / 3600 if min_last > 0 else 999
            score += min(hours_since * 2, 25)
            
            # Factor 4: Project status from registry
            if self._registry:
                entry = self._registry.get_project_status(project_id)
                if entry:
                    if entry.status == "failed":
                        score += 20
                    elif entry.status == "building":
                        score += 10
                    elif entry.status == "active":
                        score += 5
            
            scored.append((project_id, score))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return [pid for pid, _ in scored]
    
    # ─────────────────────────────────────────────────────────────────────────
    # Scheduling Engine
    # ─────────────────────────────────────────────────────────────────────────
    
    async def start(self):
        """بدء الجدولة الذكية"""
        if self._running:
            return
        
        self._running = True
        self._load_schedules()
        self._monitor_task = asyncio.create_task(self._schedule_monitor())
        logger.info("SmartScheduler started — monitoring %d projects", len(self._schedules))
    
    async def shutdown(self):
        """إيقاف الجدولة"""
        self._running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
        logger.info("SmartScheduler shutdown")
    
    async def _schedule_monitor(self):
        """المراقب الرئيسي — يفحص كل 60 ثانية"""
        while self._running:
            try:
                await self._check_and_schedule()
                self._check_count += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Scheduler monitor error: %s", e)
            
            await asyncio.sleep(self.CHECK_INTERVAL)
    
    async def _check_and_schedule(self):
        """فحص أي مشروع يحتاج فحص وجدولة المهام"""
        now = time.time()
        new_tasks = []
        
        for project_id, config in self._schedules.items():
            if not config.enabled:
                continue
            
            # Check GitHub sync
            if now - config.last_github_sync >= config.github_sync_interval:
                new_tasks.append(ScheduledTask(
                    project_id=project_id,
                    check_type=CheckType.GITHUB_SYNC.value,
                    priority=self._determine_priority(config),
                ))
                config.last_github_sync = now
            
            # Check health
            if now - config.last_health_check >= config.health_check_interval:
                new_tasks.append(ScheduledTask(
                    project_id=project_id,
                    check_type=CheckType.HEALTH_CHECK.value,
                    priority=self._determine_priority(config),
                ))
                config.last_health_check = now
            
            # Check build/test
            if now - config.last_build_test >= config.build_test_interval:
                new_tasks.append(ScheduledTask(
                    project_id=project_id,
                    check_type=CheckType.BUILD_TEST.value,
                    priority=TaskPriority.LOW.value,
                ))
                config.last_build_test = now
            
            # Check error scan
            if now - config.last_error_scan >= config.error_scan_interval:
                new_tasks.append(ScheduledTask(
                    project_id=project_id,
                    check_type=CheckType.ERROR_SCAN.value,
                    priority=self._determine_priority(config),
                ))
                config.last_error_scan = now
        
        # Add tasks to queue
        if new_tasks:
            self._task_queue.extend(new_tasks)
            # Sort by priority
            priority_order = {
                TaskPriority.CRITICAL.value: 0,
                TaskPriority.HIGH.value: 1,
                TaskPriority.MEDIUM.value: 2,
                TaskPriority.LOW.value: 3,
                TaskPriority.BACKGROUND.value: 4,
            }
            self._task_queue.sort(
                key=lambda t: priority_order.get(t.priority, 3)
            )
            
            # Execute tasks (with concurrency limit)
            await self._execute_pending_tasks()
    
    def _determine_priority(self, config: ProjectScheduleConfig) -> str:
        """تحديد أولوية مهمة بناءً على حالة المشروع"""
        if config.consecutive_failures >= 3:
            return TaskPriority.CRITICAL.value
        if config.error_count > 3:
            return TaskPriority.HIGH.value
        if config.error_count > 0:
            return TaskPriority.MEDIUM.value
        return TaskPriority.LOW.value
    
    async def _execute_pending_tasks(self):
        """تنفيذ المهام المعلقة مع موازاة محدودة"""
        tasks_to_run = self._task_queue[:self.MAX_CONCURRENT]
        self._task_queue = self._task_queue[self.MAX_CONCURRENT:]
        
        if not tasks_to_run:
            return
        
        async def _run_task(task: ScheduledTask):
            task.status = TaskStatus.RUNNING.value
            task.started_at = time.time()
            
            try:
                handler = self._check_handlers.get(task.check_type)
                if handler:
                    result = await handler(task.project_id, task.check_type)
                    task.result = result if isinstance(result, dict) else {"output": str(result)}
                    task.status = TaskStatus.COMPLETED.value
                    
                    # Update registry
                    if self._registry:
                        self._registry.update_project(
                            task.project_id,
                            last_checked_at=time.time(),
                        )
                    
                    # Reset failure count on success
                    config = self._schedules.get(task.project_id)
                    if config:
                        config.consecutive_failures = 0
                
            except Exception as e:
                task.status = TaskStatus.FAILED.value
                task.error = str(e)
                task.retry_count += 1
                
                # Update failure count
                config = self._schedules.get(task.project_id)
                if config:
                    config.consecutive_failures += 1
                    config.error_count += 1
                
                # Retry if possible
                if task.retry_count < task.max_retries:
                    self._task_queue.append(task)
            
            finally:
                task.completed_at = time.time()
                self._task_history.append(task)
                # Keep history bounded
                if len(self._task_history) > 1000:
                    self._task_history = self._task_history[-500:]
        
        # Run tasks in parallel
        await asyncio.gather(*[_run_task(t) for t in tasks_to_run], return_exceptions=True)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Reporting
    # ─────────────────────────────────────────────────────────────────────────
    
    def report_schedule_status(self) -> dict:
        """تقرير: متى فُحص كل مشروع آخر مرة"""
        now = time.time()
        project_reports = []
        
        for project_id, config in self._schedules.items():
            project_reports.append({
                "project_id": project_id,
                "enabled": config.enabled,
                "last_github_sync": config.last_github_sync,
                "last_github_sync_ago": f"{(now - config.last_github_sync) / 60:.0f}m" if config.last_github_sync else "never",
                "last_health_check": config.last_health_check,
                "last_health_check_ago": f"{(now - config.last_health_check) / 60:.0f}m" if config.last_health_check else "never",
                "last_build_test": config.last_build_test,
                "last_error_scan": config.last_error_scan,
                "error_count": config.error_count,
                "consecutive_failures": config.consecutive_failures,
            })
        
        return {
            "scheduler_running": self._running,
            "check_count": self._check_count,
            "scheduled_projects": len(self._schedules),
            "pending_tasks": len(self._task_queue),
            "completed_tasks": sum(1 for t in self._task_history if t.status == TaskStatus.COMPLETED.value),
            "failed_tasks": sum(1 for t in self._task_history if t.status == TaskStatus.FAILED.value),
            "projects": project_reports,
        }
    
    def get_status(self) -> dict:
        """حالة الجدولة"""
        return {
            "running": self._running,
            "scheduled_projects": len(self._schedules),
            "pending_tasks": len(self._task_queue),
            "total_completed": sum(1 for t in self._task_history if t.status == TaskStatus.COMPLETED.value),
            "total_failed": sum(1 for t in self._task_history if t.status == TaskStatus.FAILED.value),
            "check_count": self._check_count,
            "max_concurrent": self.MAX_CONCURRENT,
        }
    
    # ─────────────────────────────────────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────────────────────────────────────
    
    def _persist_schedule(self, config: ProjectScheduleConfig):
        """حفظ إعدادات جدولة مشروع"""
        conn = get_db_connection(self._db_path)
        try:
            data = config.to_dict()
            conn.execute("""
                INSERT OR REPLACE INTO smart_scheduler_config 
                (project_id, data) VALUES (?, ?)
            """, (config.project_id, json.dumps(data, ensure_ascii=False)))
            conn.commit()
        except Exception:
            # Table might not exist yet
            try:
                conn.execute("""CREATE TABLE IF NOT EXISTS smart_scheduler_config (
                    project_id TEXT PRIMARY KEY, data TEXT)""")
                conn.execute("""
                    INSERT OR REPLACE INTO smart_scheduler_config 
                    (project_id, data) VALUES (?, ?)
                """, (config.project_id, json.dumps(data, ensure_ascii=False)))
                conn.commit()
            except Exception as e:
                logger.warning("Failed to persist schedule: %s", e)
        finally:
            conn.close()
    
    def _load_schedules(self):
        """تحميل إعدادات الجدولة من قاعدة البيانات"""
        conn = get_db_connection(self._db_path)
        try:
            cur = conn.execute("SELECT project_id, data FROM smart_scheduler_config")
            for project_id, data_str in cur.fetchall():
                try:
                    data = json.loads(data_str)
                    self._schedules[project_id] = ProjectScheduleConfig(**data)
                except Exception as e:
                    logger.warning("Failed to load schedule for %s: %s", project_id, e)
        except Exception:
            # Table doesn't exist yet — that's OK
            pass
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_smart_scheduler: Optional[SmartScheduler] = None

def get_smart_scheduler() -> SmartScheduler:
    """الحصول على الجدولة الذكية (Singleton)"""
    global _smart_scheduler
    if _smart_scheduler is None:
        _smart_scheduler = SmartScheduler()
    return _smart_scheduler
