"""
BABSHARQII v31.0 — Session Context (ذاكرة مستمرة بين الجلسات)
ملف سياق يُقرأ تلقائياً عند بدء أي جلسة AI جديدة

المشكلة: كل جلسة تبدأ من الصفر — لا ذاكرة مستمرة بين الجلسات
الحل: SessionContext — ملف JSON يُحدّث باستمرار ويُقرأ عند بدء أي جلسة

Features:
  - auto_generate()       # توليد تلقائي من ProjectRegistry + SmartScheduler
  - get_context()         # قراءة السياق الحالي
  - update_context()      # تحديث السياق
  - mark_project_action() # تسجيل فعل على مشروع
  - get_session_prompt()  # سياق جاهز لإدراجه في prompt الـ AI
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone

logger = logging.getLogger("mamoun.core.session_context")


# ═══════════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ProjectAction:
    """فعل على مشروع"""
    project_id: str = ""
    action: str = ""          # build, check, fix, deploy, etc.
    result: str = ""          # success, failed, pending
    timestamp: float = 0.0
    details: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PendingApproval:
    """موافقة معلقة"""
    project_id: str = ""
    description: str = ""
    risk_level: str = "medium"
    requested_at: float = 0.0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SessionContextData:
    """بيانات سياق الجلسة — كل ما يحتاجه AI لبدء جلسة بوعي كامل"""
    # System
    system_name: str = "Mamoun AI v31.0"
    total_projects: int = 0
    system_health: str = "healthy"
    last_session_time: float = 0.0
    
    # Project counts
    active_projects: int = 0
    building_projects: int = 0
    failed_projects: int = 0
    idle_projects: int = 0
    delivered_projects: int = 0
    
    # Critical info
    failed_project_ids: List[str] = field(default_factory=list)
    stale_project_ids: List[str] = field(default_factory=list)
    critical_project_ids: List[str] = field(default_factory=list)
    
    # Recent actions (last 20)
    last_actions: List[dict] = field(default_factory=list)
    
    # Pending approvals
    pending_approvals: List[dict] = field(default_factory=list)
    
    # Scheduler status
    scheduler_running: bool = False
    last_scheduled_check: float = 0.0
    
    # Metrics
    avg_completion_pct: float = 0.0
    total_errors: int = 0
    
    # Timestamps
    generated_at: float = 0.0
    version: str = "1.0.0"
    
    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# Session Context Manager
# ═══════════════════════════════════════════════════════════════════════════════

class SessionContextManager:
    """
    مدير سياق الجلسة — يضمن أن كل جلسة AI تبدأ بوعي كامل
    
    How it works:
    1. عند كل تحديث (فعل، فحص، خطأ)، يُحدّث السياق
    2. عند بدء جلسة AI جديدة، يُقرأ السياق تلقائياً
    3. السياق يحتوي: عدد المشاريع، حالاتها، آخر الأفعال، الموافقات المعلقة
    4. AI يستخدم السياق كـ system prompt prefix
    """
    
    CONTEXT_FILE = Path(__file__).parent.parent.parent.parent / "download" / "session_context.json"
    MAX_LAST_ACTIONS = 20
    MAX_PENDING_APPROVALS = 50
    
    def __init__(self, project_registry=None, smart_scheduler=None):
        self._registry = project_registry
        self._scheduler = smart_scheduler
        self._context: Optional[SessionContextData] = None
    
    def set_registry(self, registry):
        self._registry = registry
    
    def set_scheduler(self, scheduler):
        self._scheduler = scheduler
    
    def auto_generate(self) -> SessionContextData:
        """
        توليد تلقائي للسياق من ProjectRegistry + SmartScheduler
        
        This is called:
        1. At system startup
        2. After any significant action
        3. Before starting a new AI session
        """
        context = SessionContextData()
        
        # From ProjectRegistry
        if self._registry:
            summary = self._registry.get_summary()
            context.total_projects = summary.total_projects
            context.active_projects = summary.active_projects
            context.building_projects = summary.building_projects
            context.failed_projects = summary.failed_projects
            context.idle_projects = summary.idle_projects
            context.delivered_projects = summary.delivered_projects
            context.avg_completion_pct = round(summary.avg_completion, 1)
            
            # Critical projects
            context.failed_project_ids = [
                p.project_id for p in self._registry.get_projects_by_status("failed")
            ]
            context.stale_project_ids = [
                p.project_id for p in self._registry.get_stale_projects()
            ]
            context.critical_project_ids = [
                p.project_id for p in self._registry.get_projects_by_health("critical")
            ]
            
            # Determine system health
            if summary.critical_projects > 0 or summary.failed_projects > summary.total_projects * 0.3:
                context.system_health = "critical"
            elif summary.warning_projects > 0 or summary.stale_projects > 3:
                context.system_health = "warning"
            else:
                context.system_health = "healthy"
        
        # From SmartScheduler
        if self._scheduler:
            sched_status = self._scheduler.get_status()
            context.scheduler_running = sched_status.get("running", False)
            context.total_errors = sched_status.get("total_failed", 0)
        
        # Preserve last actions from previous context
        if self._context:
            context.last_actions = self._context.last_actions
            context.pending_approvals = self._context.pending_approvals
            context.last_session_time = self._context.generated_at
        
        context.generated_at = time.time()
        self._context = context
        self._save_to_disk()
        
        return context
    
    def get_context(self) -> SessionContextData:
        """قراءة السياق الحالي — من الذاكرة أو من القرص"""
        if self._context:
            return self._context
        
        # Try loading from disk
        loaded = self._load_from_disk()
        if loaded:
            self._context = loaded
            return loaded
        
        # Generate fresh
        return self.auto_generate()
    
    def update_context(self, **kwargs):
        """تحديث حقول محددة في السياق"""
        context = self.get_context()
        for key, value in kwargs.items():
            if hasattr(context, key):
                setattr(context, key, value)
        context.generated_at = time.time()
        self._context = context
        self._save_to_disk()
    
    def mark_project_action(self, project_id: str, action: str, 
                            result: str = "success", details: str = ""):
        """تسجيل فعل على مشروع"""
        context = self.get_context()
        
        action_entry = ProjectAction(
            project_id=project_id,
            action=action,
            result=result,
            timestamp=time.time(),
            details=details,
        ).to_dict()
        
        context.last_actions.insert(0, action_entry)
        # Keep bounded
        if len(context.last_actions) > self.MAX_LAST_ACTIONS:
            context.last_actions = context.last_actions[:self.MAX_LAST_ACTIONS]
        
        self._context = context
        self._save_to_disk()
    
    def add_pending_approval(self, project_id: str, description: str, 
                             risk_level: str = "medium"):
        """إضافة موافقة معلقة"""
        context = self.get_context()
        
        approval = PendingApproval(
            project_id=project_id,
            description=description,
            risk_level=risk_level,
            requested_at=time.time(),
        ).to_dict()
        
        context.pending_approvals.insert(0, approval)
        if len(context.pending_approvals) > self.MAX_PENDING_APPROVALS:
            context.pending_approvals = context.pending_approvals[:self.MAX_PENDING_APPROVALS]
        
        self._context = context
        self._save_to_disk()
    
    def remove_pending_approval(self, project_id: str):
        """إزالة موافقة معلقة"""
        context = self.get_context()
        context.pending_approvals = [
            a for a in context.pending_approvals 
            if a.get("project_id") != project_id
        ]
        self._context = context
        self._save_to_disk()
    
    def get_session_prompt(self) -> str:
        """
        سياق جاهز لإدراجه في بداية prompt أي جلسة AI
        
        When a new AI session starts, prepend this to the system prompt
        so the AI immediately knows the state of all projects.
        """
        context = self.get_context()
        
        # Calculate time since last session
        if context.last_session_time > 0:
            hours_ago = (time.time() - context.last_session_time) / 3600
            time_info = f"آخر جلسة قبل {hours_ago:.1f} ساعة"
        else:
            time_info = "هذه أول جلسة"
        
        prompt = f"""أنت مأمون — نظام ذكاء اصطناعي يدير مشاريع متعددة.
حالة النظام الحالية ({time_info}):

📊 إحمالية: {context.total_projects} مشروع
  ✅ نشط: {context.active_projects}
  🔨 قيد البناء: {context.building_projects}
  ❌ فاشل: {context.failed_projects} {context.failed_project_ids[:5]}
  💤 خامل: {context.idle_projects}
  📦 مُسلّم: {context.delivered_projects}

📈 متوسط الإنجاز: {context.avg_completion_pct}%
🏥 صحة النظام: {context.system_health}
📋 موافقات معلقة: {len(context.pending_approvals)}
⏰ الجدولة: {'تعمل' if context.scheduler_running else 'متوقفة'}

آخر 5 أفعال:
{self._format_actions(context.last_actions[:5])}

مشاريع تحتاج اهتمام عاجل:
  فاشلة: {context.failed_project_ids[:5]}
  حرجة: {context.critical_project_ids[:5]}
  لم تُفحص: {context.stale_project_ids[:5]}
"""
        return prompt
    
    def _format_actions(self, actions: List[dict]) -> str:
        """تنسيق الأفعال"""
        if not actions:
            return "  (لا أفعال مسجلة)"
        
        lines = []
        for a in actions:
            time_str = datetime.fromtimestamp(
                a.get("timestamp", 0), tz=timezone.utc
            ).strftime("%H:%M") if a.get("timestamp") else "?"
            lines.append(
                f"  {time_str} — {a.get('project_id', '?')}: "
                f"{a.get('action', '?')} → {a.get('result', '?')}"
            )
        return "\n".join(lines)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────────────────────────────────────
    
    def _save_to_disk(self):
        """حفظ السياق على القرص"""
        if not self._context:
            return
        
        try:
            self.CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.CONTEXT_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._context.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Failed to save session context: %s", e)
    
    def _load_from_disk(self) -> Optional[SessionContextData]:
        """تحميل السياق من القرص"""
        try:
            if not self.CONTEXT_FILE.exists():
                return None
            
            with open(self.CONTEXT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return SessionContextData(**{
                k: v for k, v in data.items() 
                if k in SessionContextData.__dataclass_fields__
            })
        except Exception as e:
            logger.warning("Failed to load session context: %s", e)
            return None
    
    def get_status(self) -> dict:
        """حالة مدير السياق"""
        context = self.get_context()
        return {
            "initialized": self._context is not None,
            "context_file_exists": self.CONTEXT_FILE.exists(),
            "total_projects": context.total_projects,
            "system_health": context.system_health,
            "last_actions_count": len(context.last_actions),
            "pending_approvals_count": len(context.pending_approvals),
            "generated_at": context.generated_at,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_session_context_manager: Optional[SessionContextManager] = None

def get_session_context_manager() -> SessionContextManager:
    """الحصول على مدير سياق الجلسة (Singleton)"""
    global _session_context_manager
    if _session_context_manager is None:
        _session_context_manager = SessionContextManager()
    return _session_context_manager
