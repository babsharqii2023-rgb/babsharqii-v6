"""
BABSHARQII v31.0 — Project Pool (حوض المشاريع المتوازي)
موازاة حقيقية عبر مشاريع متعددة — 5 مشاريع بالتوازي

المشكلة: ProjectOrchestrator يتعامل مع مشروع واحد في كل لحظة
الحل: ProjectPool — حوض عمليات يبني مشاريع مختلفة بالتوازي

Features:
  - submit(project_id, task)    # إرسال مهمة مشروع
  - get_results(project_id)     # نتائج مشروع
  - rebalance()                 # إعادة توزيع الموارد
  - get_pool_status()           # حالة الحوض
  - cancel(project_id)          # إلغاء مهمة
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, List, Any, Callable
from collections import defaultdict

logger = logging.getLogger("mamoun.core.project_pool")


# ═══════════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class PoolTaskStatus(str, Enum):
    """حالة مهمة الحوض"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class PoolTaskType(str, Enum):
    """أنواع مهام الحوض"""
    BUILD = "build"
    TEST = "test"
    DEPLOY = "deploy"
    CHECK = "check"
    FIX = "fix"
    SYNC = "sync"


@dataclass
class PoolTask:
    """مهمة في الحوض"""
    task_id: str = ""
    project_id: str = ""
    task_type: str = PoolTaskType.BUILD.value
    status: str = PoolTaskStatus.QUEUED.value
    priority: int = 5                  # 1 = highest, 10 = lowest
    
    # Execution
    handler_name: str = ""             # اسم المعالج المسجل
    input_data: dict = field(default_factory=dict)
    output_data: dict = field(default_factory=dict)
    error: str = ""
    
    # Timing
    submitted_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    timeout_seconds: int = 300         # 5 minutes default
    
    # Resource tracking
    cpu_estimate: float = 0.5          # 0-1, estimated CPU usage
    memory_estimate: float = 0.3       # 0-1, estimated memory usage
    
    def __post_init__(self):
        if not self.task_id:
            self.task_id = f"pool_{uuid.uuid4().hex[:8]}"
        if not self.submitted_at:
            self.submitted_at = time.time()
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass 
class WorkerSlot:
    """فتحة عامل — تمثل مكان تنفيذ واحد"""
    slot_id: int = 0
    current_task: Optional[str] = None  # task_id
    busy: bool = False
    total_completed: int = 0
    total_failed: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# Project Pool — حوض المشاريع المتوازي
# ═══════════════════════════════════════════════════════════════════════════════

class ProjectPool:
    """
    حوض المشاريع المتوازي — يبني 5 مشاريع بالتوازي
    
    How it works:
    1. المهام تُرسل عبر submit() وتوضع في طابور بأولوية
    2. MAX_CONCURRENT فتحات عمال تنفذ المهام بالتوازي
    3. كل فتحة تأخذ مهمة من الطابور وتنفذها
    4. عند اكتمال مهمة، تُعاد الفتحة للطابور
    5. rebalance() يعيد توزيع الموارد إذا كان هناك ضغط
    """
    
    MAX_CONCURRENT = 5      # 5 مشاريع بالتوازي
    MAX_QUEUE_SIZE = 100    # أقصى حجم للطابور
    TASK_TIMEOUT = 300      # 5 minutes default timeout
    
    def __init__(self):
        self._queue: List[PoolTask] = []           # Priority queue
        self._running: Dict[str, PoolTask] = {}     # task_id → task (currently running)
        self._completed: List[PoolTask] = []         # Recently completed
        self._results: Dict[str, dict] = {}          # task_id → result
        self._workers: List[WorkerSlot] = [
            WorkerSlot(slot_id=i) for i in range(self.MAX_CONCURRENT)
        ]
        self._handlers: Dict[str, Callable] = {}    # handler_name → async callable
        self._running_tasks: Dict[str, asyncio.Task] = {}  # task_id → asyncio.Task
        self._is_running = False
        self._dispatch_task: Optional[asyncio.Task] = None
        self._stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_cancelled": 0,
            "total_timeout": 0,
        }
    
    def register_handler(self, name: str, handler: Callable):
        """تسجيل معالج لمهام معينة"""
        self._handlers[name] = handler
        logger.info("Pool handler registered: %s", name)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Task Management
    # ─────────────────────────────────────────────────────────────────────────
    
    async def submit(self, project_id: str, task_type: str = PoolTaskType.BUILD.value,
                     handler_name: str = "", input_data: dict = None,
                     priority: int = 5, timeout_seconds: int = 0) -> PoolTask:
        """إرسال مهمة مشروع للحوض"""
        if len(self._queue) >= self.MAX_QUEUE_SIZE:
            raise RuntimeError("Pool queue is full (%d tasks)", self.MAX_QUEUE_SIZE)
        
        task = PoolTask(
            project_id=project_id,
            task_type=task_type,
            priority=priority,
            handler_name=handler_name,
            input_data=input_data or {},
            timeout_seconds=timeout_seconds or self.TASK_TIMEOUT,
        )
        
        self._queue.append(task)
        # Sort by priority (lower number = higher priority)
        self._queue.sort(key=lambda t: t.priority)
        
        self._stats["total_submitted"] += 1
        
        # Try to dispatch immediately
        await self._dispatch()
        
        logger.info("Task submitted: %s for project %s (priority: %d)", 
                    task.task_id, project_id, priority)
        return task
    
    def get_results(self, project_id: str) -> List[dict]:
        """نتائج مشروع"""
        return [
            t.to_dict() for t in self._completed 
            if t.project_id == project_id
        ]
    
    def get_task_result(self, task_id: str) -> Optional[dict]:
        """نتيجة مهمة واحدة"""
        return self._results.get(task_id)
    
    async def cancel(self, project_id: str) -> int:
        """إلغاء كل مهام مشروع"""
        cancelled = 0
        
        # Cancel queued tasks
        to_remove = [t for t in self._queue if t.project_id == project_id]
        for task in to_remove:
            task.status = PoolTaskStatus.CANCELLED.value
            self._queue.remove(task)
            cancelled += 1
        
        # Cancel running tasks
        for task_id, task in list(self._running.items()):
            if task.project_id == project_id:
                # Cancel the asyncio task
                atask = self._running_tasks.get(task_id)
                if atask and not atask.done():
                    atask.cancel()
                task.status = PoolTaskStatus.CANCELLED.value
                del self._running[task_id]
                cancelled += 1
        
        self._stats["total_cancelled"] += cancelled
        return cancelled
    
    # ─────────────────────────────────────────────────────────────────────────
    # Dispatch Engine
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _dispatch(self):
        """توزيع المهام على الفتحات المتاحة"""
        available_workers = [w for w in self._workers if not w.busy]
        
        while self._queue and available_workers:
            task = self._queue.pop(0)
            worker = available_workers.pop(0)
            
            # Start task execution
            worker.busy = True
            worker.current_task = task.task_id
            
            atask = asyncio.create_task(
                self._execute_task(task, worker),
                name=f"pool-{task.task_id}",
            )
            self._running_tasks[task.task_id] = atask
            self._running[task.task_id] = task
    
    async def _execute_task(self, task: PoolTask, worker: WorkerSlot):
        """تنفيذ مهمة واحدة"""
        task.status = PoolTaskStatus.RUNNING.value
        task.started_at = time.time()
        
        try:
            # Find handler
            handler = self._handlers.get(task.handler_name)
            
            if handler:
                # Execute with timeout
                result = await asyncio.wait_for(
                    handler(task.project_id, task.task_type, task.input_data),
                    timeout=task.timeout_seconds,
                )
                task.output_data = result if isinstance(result, dict) else {"output": str(result)}
                task.status = PoolTaskStatus.COMPLETED.value
                self._stats["total_completed"] += 1
                worker.total_completed += 1
            else:
                # No handler — mark as completed with default result
                task.output_data = {
                    "status": "no_handler",
                    "message": f"No handler registered for '{task.handler_name}'",
                    "task_type": task.task_type,
                }
                task.status = PoolTaskStatus.COMPLETED.value
                self._stats["total_completed"] += 1
                worker.total_completed += 1
        
        except asyncio.TimeoutError:
            task.status = PoolTaskStatus.TIMEOUT.value
            task.error = f"Task timed out after {task.timeout_seconds}s"
            self._stats["total_timeout"] += 1
            worker.total_failed += 1
        
        except asyncio.CancelledError:
            task.status = PoolTaskStatus.CANCELLED.value
            self._stats["total_cancelled"] += 1
        
        except Exception as e:
            task.status = PoolTaskStatus.FAILED.value
            task.error = str(e)
            self._stats["total_failed"] += 1
            worker.total_failed += 1
            logger.error("Pool task %s failed: %s", task.task_id, e)
        
        finally:
            task.completed_at = time.time()
            
            # Store result
            self._results[task.task_id] = task.to_dict()
            
            # Move to completed
            if task.task_id in self._running:
                del self._running[task.task_id]
            self._completed.append(task)
            
            # Keep completed list bounded
            if len(self._completed) > 200:
                self._completed = self._completed[-100:]
            
            # Free worker
            worker.busy = False
            worker.current_task = None
            
            # Remove from running tasks
            if task.task_id in self._running_tasks:
                del self._running_tasks[task.task_id]
            
            # Dispatch more tasks
            await self._dispatch()
    
    # ─────────────────────────────────────────────────────────────────────────
    # Rebalance
    # ─────────────────────────────────────────────────────────────────────────
    
    async def rebalance(self):
        """
        إعادة توزيع الموارد
        
        When called:
        1. Check if any project is hogging workers
        2. Prioritize critical/failed projects
        3. Cancel low-priority tasks if needed
        """
        # Count running tasks per project
        project_count: Dict[str, int] = defaultdict(int)
        for task in self._running.values():
            project_count[task.project_id] += 1
        
        # If any project has more than 2 workers, cancel extras (lowest priority)
        for project_id, count in project_count.items():
            if count > 2:
                project_tasks = [
                    t for t in self._running.values() 
                    if t.project_id == project_id
                ]
                # Sort by priority (highest number = lowest priority)
                project_tasks.sort(key=lambda t: t.priority, reverse=True)
                # Cancel extras
                for task in project_tasks[1:]:
                    atask = self._running_tasks.get(task.task_id)
                    if atask and not atask.done():
                        atask.cancel()
        
        # Re-prioritize queue
        self._queue.sort(key=lambda t: t.priority)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Status
    # ─────────────────────────────────────────────────────────────────────────
    
    def get_pool_status(self) -> dict:
        """حالة الحوض الكاملة"""
        return {
            "is_running": self._is_running,
            "max_concurrent": self.MAX_CONCURRENT,
            "queue_size": len(self._queue),
            "running_tasks": len(self._running),
            "available_workers": sum(1 for w in self._workers if not w.busy),
            "total_completed": self._stats["total_completed"],
            "total_failed": self._stats["total_failed"],
            "total_timeout": self._stats["total_timeout"],
            "total_cancelled": self._stats["total_cancelled"],
            "workers": [w.to_dict() for w in self._workers],
            "queued_tasks": [t.to_dict() for t in self._queue[:10]],
            "running_task_ids": list(self._running.keys()),
        }
    
    def get_status(self) -> dict:
        """حالة مختصرة"""
        return {
            "max_concurrent": self.MAX_CONCURRENT,
            "queue_size": len(self._queue),
            "running": len(self._running),
            "workers_busy": sum(1 for w in self._workers if w.busy),
            "workers_available": sum(1 for w in self._workers if not w.busy),
            "total_completed": self._stats["total_completed"],
            "total_failed": self._stats["total_failed"],
        }
    
    async def start(self):
        """بدء الحوض"""
        self._is_running = True
        logger.info("ProjectPool started — %d worker slots", self.MAX_CONCURRENT)
    
    async def shutdown(self):
        """إيقاف الحوض"""
        self._is_running = False
        
        # Cancel all running tasks
        for task_id, atask in self._running_tasks.items():
            if not atask.done():
                atask.cancel()
        
        self._running_tasks.clear()
        self._running.clear()
        logger.info("ProjectPool shutdown")


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_project_pool: Optional[ProjectPool] = None

def get_project_pool() -> ProjectPool:
    """الحصول على حوض المشاريع (Singleton)"""
    global _project_pool
    if _project_pool is None:
        _project_pool = ProjectPool()
    return _project_pool
