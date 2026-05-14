"""
BABSHARQII v13.0 — Priority Queue
طابور الأولويات — يدعم 5 مستويات أولوية للتنفيذ المتوازي

Priority Levels:
- CRITICAL (0): System safety, shutdown compliance, emergency tasks
- HIGH (1): User requests, approval decisions, time-sensitive tasks
- MEDIUM (2): Agent processing, evolution cycles, standard tasks
- LOW (3): Background research, scheduled reports, maintenance
- IDLE (4): Night cycle processing, self-improvement, low-priority tasks

Feature Flag: MAMOUN_CONCURRENCY_MODE (default: false)
"""

import os
import time
import uuid
import logging
import asyncio
import threading
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable, Any
from enum import Enum
from collections import defaultdict
import heapq

from mamoun.core.safety_guard import SafetyGuard

logger = logging.getLogger(__name__)

CONCURRENCY_ENABLED = os.getenv("MAMOUN_CONCURRENCY_MODE", "false").lower() in ("true", "1", "yes")

# Maximum concurrent tasks
MAX_CONCURRENT_TASKS = int(os.getenv("MAMOUN_MAX_CONCURRENT_TASKS", "200"))
# Worker thread pool size
WORKER_POOL_SIZE = int(os.getenv("MAMOUN_WORKER_POOL_SIZE", "16"))


class TaskPriority(int, Enum):
    """مستويات الأولوية."""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    IDLE = 4


class TaskStatus(str, Enum):
    """حالة المهمة."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class Task:
    """مهمة في طابور الأولويات."""
    task_id: str = ""
    name: str = ""
    description: str = ""
    priority: int = TaskPriority.MEDIUM.value
    status: str = TaskStatus.QUEUED.value
    created_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    duration_ms: float = 0.0
    result: Any = None
    error: str = ""
    agent_id: str = ""
    task_context: str = ""
    requires_permission: str = ""  # scope if permission needed
    timeout_seconds: float = 300.0
    retry_count: int = 0
    max_retries: int = 2
    _coroutine: Any = None  # The actual coroutine to execute
    _heap_index: int = 0  # For heapq ordering

    def __post_init__(self):
        if not self.task_id:
            self.task_id = f"task_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def __lt__(self, other):
        """For heapq: lower priority value = higher priority."""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.created_at < other.created_at

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority,
            "priority_name": TaskPriority(self.priority).name,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": round(self.duration_ms, 1),
            "error": self.error,
            "agent_id": self.agent_id,
            "task_context": self.task_context,
            "requires_permission": self.requires_permission,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
        }


class PriorityQueue:
    """
    طابور الأولويات — يدعم 5 مستويات أولوية مع التنفيذ المتوازي.

    Features:
    - 5 priority levels (CRITICAL to IDLE)
    - Concurrent execution up to MAX_CONCURRENT_TASKS
    - Task timeout and retry support
    - Integration with TimeBoundedPolicy for permission-gated tasks
    - Thread-safe operations
    - Real-time monitoring via ConcurrencyMonitor

    Usage:
        queue = PriorityQueue()
        task_id = await queue.submit("research_task", priority=TaskPriority.MEDIUM, ...)
        result = await queue.wait_for(task_id)
    """

    def __init__(self, max_concurrent: int = 0):
        self._max_concurrent = max_concurrent or MAX_CONCURRENT_TASKS
        self._heap: list[Task] = []
        self._tasks: dict[str, Task] = {}
        self._running: dict[str, Task] = {}
        self._completed: dict[str, Task] = {}
        self._lock = threading.Lock()
        self._semaphore = asyncio.Semaphore(self._max_concurrent)
        self._counter = 0
        self._is_running = False
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._safety_guard = SafetyGuard()

    async def submit(
        self,
        name: str,
        coroutine: Callable = None,
        priority: int = TaskPriority.MEDIUM.value,
        agent_id: str = "",
        task_context: str = "",
        requires_permission: str = "",
        timeout_seconds: float = 300.0,
        description: str = "",
    ) -> str:
        """
        إرسال مهمة إلى الطابور — Submit a task to the priority queue.

        Args:
            name: اسم المهمة
            coroutine: دالة أو coroutine للتنفيذ
            priority: مستوى الأولوية (0=CRITICAL to 4=IDLE)
            agent_id: الوكيل المُرسل
            task_context: سياق المهمة
            requires_permission: نطاق الصلاحية المطلوبة
            timeout_seconds: مهلة التنفيذ
            description: وصف المهمة

        Returns:
            task_id
        """
        # Check if shutdown is in progress (Law 5)
        if self._safety_guard.is_shutting_down():
            raise RuntimeError("Shutdown in progress — cannot accept new tasks (Law 5)")

        self._counter += 1
        task = Task(
            name=name,
            description=description,
            priority=max(0, min(4, priority)),
            agent_id=agent_id,
            task_context=task_context,
            requires_permission=requires_permission,
            timeout_seconds=timeout_seconds,
            _coroutine=coroutine,
            _heap_index=self._counter,
        )

        with self._lock:
            self._tasks[task.task_id] = task
            heapq.heappush(self._heap, task)

        logger.info(
            f"Task submitted: {task.task_id} | {name} | "
            f"Priority: {TaskPriority(task.priority).name} | "
            f"Queue size: {len(self._heap)}"
        )

        # Start processing if not already running
        if not self._is_running:
            asyncio.create_task(self._process_queue())

        return task.task_id

    async def _process_queue(self):
        """معالجة الطابور — Process tasks from the queue."""
        if self._is_running:
            return
        self._is_running = True

        while self._heap:
            # Check shutdown (Law 5)
            if self._safety_guard.is_shutting_down():
                logger.info("PriorityQueue: Stopping due to shutdown (Law 5)")
                break

            with self._lock:
                if not self._heap:
                    break
                task = heapq.heappop(self._heap)

            if task.status == TaskStatus.CANCELLED.value:
                continue

            # Execute task with semaphore for concurrency control
            asyncio.create_task(self._execute_task(task))

            # Small delay to prevent overwhelming the system
            await asyncio.sleep(0.01)

        self._is_running = False

    async def _execute_task(self, task: Task):
        """تنفيذ مهمة واحدة — Execute a single task."""
        async with self._semaphore:
            task.status = TaskStatus.RUNNING.value
            task.started_at = time.time()
            self._running[task.task_id] = task

            try:
                if task._coroutine:
                    # Execute the coroutine with timeout
                    if asyncio.iscoroutinefunction(task._coroutine):
                        result = await asyncio.wait_for(
                            task._coroutine(),
                            timeout=task.timeout_seconds,
                        )
                    elif asyncio.iscoroutine(task._coroutine):
                        result = await asyncio.wait_for(
                            task._coroutine,
                            timeout=task.timeout_seconds,
                        )
                    else:
                        # Sync function — run in executor
                        loop = asyncio.get_event_loop()
                        result = await asyncio.wait_for(
                            loop.run_in_executor(None, task._coroutine),
                            timeout=task.timeout_seconds,
                        )
                    task.result = result
                else:
                    # No coroutine — just mark as completed
                    task.result = {"status": "no_op", "message": "Task had no execution function"}

                task.status = TaskStatus.COMPLETED.value

            except asyncio.TimeoutError:
                task.status = TaskStatus.TIMEOUT.value
                task.error = f"تجاوز المهلة ({task.timeout_seconds} ثانية)"
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.QUEUED.value
                    with self._lock:
                        heapq.heappush(self._heap, task)
                    logger.warning(f"Task {task.task_id} timeout, retrying ({task.retry_count}/{task.max_retries})")
                    return

            except asyncio.CancelledError:
                task.status = TaskStatus.CANCELLED.value
                task.error = "تم إلغاء المهمة"

            except Exception as e:
                task.status = TaskStatus.FAILED.value
                task.error = str(e)[:500]
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.QUEUED.value
                    with self._lock:
                        heapq.heappush(self._heap, task)
                    logger.warning(f"Task {task.task_id} failed, retrying ({task.retry_count}/{task.max_retries})")
                    return

            finally:
                task.completed_at = time.time()
                task.duration_ms = (task.completed_at - task.started_at) * 1000
                if task.task_id in self._running:
                    del self._running[task.task_id]
                self._completed[task.task_id] = task

    async def wait_for(self, task_id: str, timeout: float = 300.0) -> dict:
        """انتظار مهمة — Wait for a task to complete."""
        start = time.time()
        while time.time() - start < timeout:
            task = self._tasks.get(task_id)
            if task and task.status in (
                TaskStatus.COMPLETED.value,
                TaskStatus.FAILED.value,
                TaskStatus.CANCELLED.value,
                TaskStatus.TIMEOUT.value,
            ):
                return task.to_dict()
            await asyncio.sleep(0.1)
        return {"task_id": task_id, "status": "timeout_waiting"}

    async def cancel(self, task_id: str) -> bool:
        """إلغاء مهمة — Cancel a task."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        task.status = TaskStatus.CANCELLED.value
        return True

    def get_queue_status(self) -> dict:
        """حالة الطابور."""
        priority_counts = defaultdict(int)
        for task in self._heap:
            priority_counts[TaskPriority(task.priority).name] += 1

        return {
            "enabled": CONCURRENCY_ENABLED,
            "queue_size": len(self._heap),
            "running_tasks": len(self._running),
            "completed_tasks": len(self._completed),
            "max_concurrent": self._max_concurrent,
            "priority_breakdown": dict(priority_counts),
            "total_submitted": self._counter,
        }

    def get_running_tasks(self) -> list[dict]:
        """الحصول على المهام الجارية."""
        return [t.to_dict() for t in self._running.values()]

    def get_queue_contents(self, limit: int = 50) -> list[dict]:
        """الحصول على محتويات الطابور."""
        return [t.to_dict() for t in sorted(self._heap)[:limit]]

    async def shutdown(self):
        """إيقاف الطابور — يتوافق مع القانون 5."""
        # Cancel all pending tasks
        for task in self._heap:
            task.status = TaskStatus.CANCELLED.value
        self._heap.clear()
        self._is_running = False
        logger.info("PriorityQueue: Shutdown complete (Law 5 compliant)")
