"""
BABSHARQII v18.0 — Project Orchestrator
منسّق المشاريع — يحول الفكرة إلى مشروع كامل

When the user says "ما رأيك بمشروع تطبيق توصيل؟"
The orchestrator:
1. RESEARCH — يبحث عن السوق والمنافسين
2. NOTIFY — يرسل تنبيه "انتهى البحث" + ملخص
3. WAIT APPROVAL — ينتظر موافقة المستخدم
4. PLAN — يكتب خطة تشغيلية + تسويقية + جدوى
5. BUILD — يبني المواقع والصفحات والسوشيل ميديا
6. DELIVER — يقدم كل شيء جاهزاً

State Machine:
  IDEA → RESEARCHING → RESEARCH_DONE → PLANNING → PLAN_DONE → BUILDING → DELIVERED

Based on:
- ReAct (Yao et al., 2023): Multi-step reasoning with tool use
- Plan-and-Solve (Wang et al., 2023): Decompose → Plan → Execute
- Self-Refine (Madaan et al., 2023): Generate → Reflect → Refine

Model Strategy (Balanced Distribution):
  Neural/Primary (creativity, code):       glm-5.1
  Causal/Reasoning (analysis, CoT):        deepseek-reasoner
  Symbolic/Logic (math, verification):     glm-4-plus
  Bayesian/Probabilistic (estimation):     gemini-2.0-flash
  WorldModel/Scenario (forecasting):       deepseek-chat
"""

import asyncio
import json
import logging
import time
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger("mamoun.core.project_orchestrator")


# ═══════════════════════════════════════════════════════════════════════════════
# State Machine
# ═══════════════════════════════════════════════════════════════════════════════

class ProjectPhase(str, Enum):
    """مراحل المشروع"""
    IDEA = "idea"                      # الفكرة الأولية
    RESEARCHING = "researching"        # جاري البحث
    RESEARCH_DONE = "research_done"    # البحث انتهى — ينتظر موافقة
    PLANNING = "planning"              # جاري التخطيط
    PLAN_DONE = "plan_done"            # الخطة جاهزة — ينتظر موافقة
    BUILDING = "building"              # جاري البناء
    BUILD_DONE = "build_done"          # البناء انتهى
    DELIVERING = "delivering"          # جاري التسليم
    DELIVERED = "delivered"            # تم التسليم
    PAUSED = "paused"                  # متوقف مؤقتاً
    CANCELLED = "cancelled"            # ملغى


@dataclass
class ProjectStep:
    """خطوة في المشروع"""
    id: str = ""
    name: str = ""
    name_ar: str = ""
    phase: ProjectPhase = ProjectPhase.IDEA
    status: str = "pending"  # pending, running, completed, failed
    result: dict = field(default_factory=dict)
    artifacts: list = field(default_factory=list)
    started_at: float = 0
    completed_at: float = 0
    duration_ms: float = 0


@dataclass
class Project:
    """مشروع كامل"""
    id: str = ""
    name: str = ""
    description: str = ""
    phase: ProjectPhase = ProjectPhase.IDEA
    steps: list[ProjectStep] = field(default_factory=list)
    created_at: float = 0
    updated_at: float = 0
    owner: str = "user"
    artifacts: list = field(default_factory=list)
    research_data: dict = field(default_factory=dict)
    plan_data: dict = field(default_factory=dict)
    build_data: dict = field(default_factory=dict)
    notifications: list = field(default_factory=list)
    
    def __post_init__(self):
        if not self.id:
            self.id = f"proj_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()
        self.updated_at = time.time()


# ═══════════════════════════════════════════════════════════════════════════════
# Project Orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class ProjectOrchestrator:
    """
    منسّق المشاريع — يحول الفكرة إلى مشروع كامل
    
    Flow:
    1. User says "ما رأيك بمشروع تطبيق توصيل؟"
    2. Orchestrator creates Project → starts RESEARCH phase
    3. Research completes → sends notification "انتهى البحث" + summary
    4. User approves → starts PLAN phase
    5. Plan completes → sends notification "الخطة جاهزة" + summary
    6. User approves → starts BUILD phase
    7. Build completes → sends notification "المشروع جاهز!" + deliverables
    """
    
    def __init__(self, llm_client=None, real_tools=None, ws_manager=None, neural_bus=None):
        self._llm = llm_client
        self._tools = real_tools
        self._ws = ws_manager
        self._neural_bus = neural_bus  # v30: NeuralBus integration for project lifecycle events
        self._projects: dict[str, Project] = {}
        self._data_dir = Path(__file__).parent.parent.parent.parent / "download" / "projects"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._notification_callbacks: list[Callable] = []
    
    def register_notification_callback(self, callback: Callable):
        """تسجيل دالة إشعار — تُستدعى عند كل تحديث"""
        self._notification_callbacks.append(callback)

    # ─────────────────────────────────────────────────────────────────────────
    # NeuralBus Integration
    # ─────────────────────────────────────────────────────────────────────────

    def _publish_event(self, event_type: str, project: Project, payload: dict = None):
        """نشر حدث مشروع على الناقل العصبي — Publish a project event to NeuralBus"""
        if not self._neural_bus:
            return
        try:
            from mamoun.core.neural_bus import SignalPriority
            priority = SignalPriority.HIGH if event_type in (
                "project_created", "project_delivered",
            ) else SignalPriority.NORMAL
            self._neural_bus.publish(
                signal_type=event_type,
                source=f"project_orchestrator:{project.id}",
                payload={
                    "project_id": project.id,
                    "project_name": project.name,
                    "phase": project.phase.value,
                    "owner": project.owner,
                    **(payload or {}),
                },
                priority=priority,
            )
        except Exception as e:
            logger.warning("NeuralBus publish failed for event %s: %s", event_type, e)

    def _on_neural_signal(self, signal):
        """معالج إشارات الناقل العصبي — Handle incoming NeuralBus signals"""
        try:
            sig_type = signal.signal_type if hasattr(signal, 'signal_type') else ""
            payload = signal.payload if hasattr(signal, 'payload') else {}
            logger.debug("ProjectOrchestrator received signal: %s", sig_type)
            # React to action results that might affect projects
            if sig_type == "action_failed":
                project_id = payload.get("project_id")
                if project_id and project_id in self._projects:
                    logger.warning("Action failed for project %s", project_id)
            elif sig_type == "perception":
                # Could trigger project creation from user perception
                pass
        except Exception as e:
            logger.warning("ProjectOrchestrator signal handler error: %s", e)
    
    async def _notify(self, project: Project, message: str, data: dict = None):
        """إرسال إشعار للمستخدم"""
        notification = {
            "project_id": project.id,
            "project_name": project.name,
            "phase": project.phase.value,
            "message": message,
            "data": data or {},
            "timestamp": time.time(),
        }
        project.notifications.append(notification)
        
        # Send via WebSocket if available
        if self._ws:
            try:
                await self._ws.broadcast({
                    "type": "project_notification",
                    **notification,
                })
            except Exception:
                pass
        
        # Call registered callbacks
        for cb in self._notification_callbacks:
            try:
                await cb(notification)
            except Exception:
                pass
        
        logger.info("Project notification [%s]: %s", project.id, message[:100])
    
    # ─────────────────────────────────────────────────────────────────────────
    # Project Lifecycle
    # ─────────────────────────────────────────────────────────────────────────
    
    async def start_project(self, idea: str, owner: str = "user") -> Project:
        """
        بدء مشروع جديد من فكرة
        
        Creates the project and starts the research phase automatically.
        Returns the project immediately (research runs in background).
        """
        project = Project(
            name=idea[:100],
            description=idea,
            phase=ProjectPhase.IDEA,
            owner=owner,
        )
        
        # Add steps
        project.steps = [
            ProjectStep(id="research", name="Research", name_ar="بحث السوق", phase=ProjectPhase.RESEARCHING),
            ProjectStep(id="feasibility", name="Feasibility Study", name_ar="دراسة الجدوى", phase=ProjectPhase.RESEARCHING),
            ProjectStep(id="business_plan", name="Business Plan", name_ar="خطة الأعمال", phase=ProjectPhase.PLANNING),
            ProjectStep(id="marketing_plan", name="Marketing Plan", name_ar="الخطة التسويقية", phase=ProjectPhase.PLANNING),
            ProjectStep(id="website", name="Website Building", name_ar="بناء الموقع", phase=ProjectPhase.BUILDING),
            ProjectStep(id="social_media", name="Social Media Setup", name_ar="إعداد السوشيل ميديا", phase=ProjectPhase.BUILDING),
            ProjectStep(id="pitch_deck", name="Investor Pitch", name_ar="عرض المستثمرين", phase=ProjectPhase.BUILDING),
            ProjectStep(id="funding_plan", name="Funding Strategy", name_ar="استراتيجية التمويل", phase=ProjectPhase.BUILDING),
        ]
        
        self._projects[project.id] = project

        # v30: Publish project_created event to NeuralBus
        self._publish_event("project_created", project, {"description": idea[:200]})

        await self._notify(project, f"🚀 بدأ مشروع جديد: {idea[:50]} — جاري البحث عن السوق...")

        # Start research in background
        asyncio.create_task(self._run_research_phase(project))

        return project
    
    async def _run_research_phase(self, project: Project):
        """مرحلة البحث — تبحث عن السوق والمنافسين"""
        project.phase = ProjectPhase.RESEARCHING
        project.updated_at = time.time()

        # v30: Publish research_started event to NeuralBus
        self._publish_event("research_started", project)
        
        research_step = next((s for s in project.steps if s.id == "research"), None)
        if research_step:
            research_step.status = "running"
            research_step.started_at = time.time()
        
        try:
            # 1. Web search for market data
            market_data = {}
            if self._tools:
                search_result = await self._tools.call_tool(
                    "web_search",
                    query=f"سوق {project.description} حجم السوق المنافسين 2024 2025",
                    num_results=10,
                )
                market_data["web_search"] = search_result.output[:3000] if search_result.success else ""
            
            # 2. LLM-powered deep research
            if self._llm:
                research_response = await self._llm.think(
                    prompt=f"""أجرِ بحثاً شاملاً عن مشروع: {project.description}

يشمل البحث:
1. حجم السوق العالمي والمحلي
2. أهم المنافسين ونصيبهم السوقي
3. اتجاهات السوق الحالية
4. الفجوات في السوق
5. الجمهور المستهدف
6. التوقعات المستقبلية
7. المخاطر المحتملة
8. فرص التميز

قدّم بحثاً مفصلاً ومبنياً على بيانات.""",
                    system="أنت باحث سوق محترف. قدّم بحثاً شاملاً ومفصلاً مع أرقام وإحصائيات.",
                    model="deepseek-reasoner",  # Causal/Reasoning — deep research & analysis
                    temperature=0.3,
                )
                market_data["deep_research"] = research_response.text[:5000]
            
            project.research_data = market_data
            
            if research_step:
                research_step.status = "completed"
                research_step.completed_at = time.time()
                research_step.duration_ms = (research_step.completed_at - research_step.started_at) * 1000
                research_step.result = market_data
            
            project.phase = ProjectPhase.RESEARCH_DONE
            project.updated_at = time.time()

            # v30: Publish research_completed event to NeuralBus
            self._publish_event("research_completed", project, {
                "has_web_data": bool(market_data.get("web_search")),
                "has_deep_research": bool(market_data.get("deep_research")),
            })

            # Notify user
            summary = market_data.get("deep_research", "")[:500]
            await self._notify(
                project,
                f"✅ انتهى البحث عن مشروع: {project.name}\n\nملخص:\n{summary}\n\nهل تريد المتابعة لمرحلة التخطيط؟ (أرسل 'متابعة' أو 'موافقة')",
                {"research_data": market_data, "next_phase": "planning"},
            )
            
            # Save project state
            await self._save_project(project)
            
        except Exception as e:
            logger.error("Research phase failed for project %s: %s", project.id, e)
            project.phase = ProjectPhase.PAUSED
            if research_step:
                research_step.status = "failed"
            await self._notify(project, f"❌ فشل البحث: {str(e)}")
    
    async def approve_and_continue(self, project_id: str, phase: str = "") -> Project:
        """
        موافقة المستخدم والانتقال للمرحلة التالية
        
        When user says "متابعة" or "موافقة", this advances the project.
        """
        project = self._projects.get(project_id)
        if not project:
            raise ValueError(f"مشروع غير موجود: {project_id}")
        
        if project.phase == ProjectPhase.RESEARCH_DONE:
            asyncio.create_task(self._run_planning_phase(project))
        elif project.phase == ProjectPhase.PLAN_DONE:
            asyncio.create_task(self._run_build_phase(project))
        else:
            await self._notify(project, f"المشروع في مرحلة {project.phase.value} — لا يمكن المتابعة تلقائياً")
        
        return project
    
    async def _run_planning_phase(self, project: Project):
        """مرحلة التخطيط — خطة أعمال + تسويقية + جدوى"""
        project.phase = ProjectPhase.PLANNING
        project.updated_at = time.time()

        # v30: Publish planning_started event to NeuralBus
        self._publish_event("planning_started", project)

        await self._notify(project, "📋 جاري إعداد الخطة التشغيلية والتسويقية...")
        
        plans = {}
        
        try:
            # 1. Feasibility Study
            feas_step = next((s for s in project.steps if s.id == "feasibility"), None)
            if feas_step:
                feas_step.status = "running"
                feas_step.started_at = time.time()
            
            if self._llm:
                feas_response = await self._llm.think(
                    prompt=f"""أعد دراسة جدوى شاملة لمشروع: {project.description}

بيانات البحث:
{project.research_data.get('deep_research', '')[:3000]}

تتضمن دراسة الجدوى:
1. الملخص التنفيذي
2. التحليل المالي (التكاليف، الإيرادات المتوقعة، نقطة التعادل)
3. التحليل التشغيلي
4. المخاطر والتخفيفات
5. التوصيات النهائية""",
                    system="أنت محلل مالي ومعد دراسات جدوى خبير. أرقام واقعية ومبنية على بيانات.",
                    model="deepseek-reasoner",  # Causal/Reasoning — structured financial analysis
                    temperature=0.3,
                    json_mode=True,
                )
                feas_data = feas_response.extract_json() or {}
                plans["feasibility"] = feas_data
                if feas_step:
                    feas_step.status = "completed"
                    feas_step.result = feas_data
                    feas_step.completed_at = time.time()
                    feas_step.duration_ms = (feas_step.completed_at - feas_step.started_at) * 1000
            
            # 2. Business Plan
            bp_step = next((s for s in project.steps if s.id == "business_plan"), None)
            if bp_step:
                bp_step.status = "running"
                bp_step.started_at = time.time()
            
            if self._llm:
                bp_response = await self._llm.think(
                    prompt=f"""اكتب خطة أعمال تفصيلية لمشروع: {project.description}

بيانات البحث:
{project.research_data.get('deep_research', '')[:2000]}

دراسة الجدوى:
{json.dumps(plans.get('feasibility', {}), ensure_ascii=False)[:2000]}

الخطة تشمل:
1. الرؤية والرسالة
2. نموذج العمل (Business Model Canvas)
3. استراتيجية التسعير
4. الخطة التشغيلية
5. هيكل الفريق
6. الأهداف المرحلية (6 أشهر - سنة - سنتان)""",
                    system="أنت مستشار أعمال استراتيجي. خطط عملية وقابلة للتنفيذ.",
                    model="glm-5.1",  # Neural/Primary — creative + strategic planning
                    temperature=0.4,
                    json_mode=True,
                )
                bp_data = bp_response.extract_json() or {}
                plans["business_plan"] = bp_data
                if bp_step:
                    bp_step.status = "completed"
                    bp_step.result = bp_data
                    bp_step.completed_at = time.time()
                    bp_step.duration_ms = (bp_step.completed_at - bp_step.started_at) * 1000
            
            # 3. Marketing Plan
            mp_step = next((s for s in project.steps if s.id == "marketing_plan"), None)
            if mp_step:
                mp_step.status = "running"
                mp_step.started_at = time.time()
            
            if self._llm:
                mp_response = await self._llm.think(
                    prompt=f"""ضع خطة تسويقية شاملة لمشروع: {project.description}

الخطة تشمل:
1. استراتيجية التسويق الرقمي
2. خطة المحتوى (شهرية)
3. استراتيجية السوشيل ميديا لكل منصة
4. ميزانية التسويق
5. مؤشرات الأداء (KPIs)
6. جدول زمني للإطلاق""",
                    system="أنت استراتيجي تسويق رقمي خبير. خطط عملية بميزانيات واقعية.",
                    model="deepseek-chat",  # WorldModel/Scenario — diverse scenario building
                    temperature=0.5,
                    json_mode=True,
                )
                mp_data = mp_response.extract_json() or {}
                plans["marketing_plan"] = mp_data
                if mp_step:
                    mp_step.status = "completed"
                    mp_step.result = mp_data
                    mp_step.completed_at = time.time()
                    mp_step.duration_ms = (mp_step.completed_at - mp_step.started_at) * 1000
            
            project.plan_data = plans
            project.phase = ProjectPhase.PLAN_DONE
            project.updated_at = time.time()

            # v30: Publish planning_completed event to NeuralBus
            self._publish_event("planning_completed", project, {
                "plans": list(plans.keys()),
            })

            await self._notify(
                project,
                f"✅ الخطة جاهزة لمشروع: {project.name}\n\nتتضمن: دراسة جدوى + خطة أعمال + خطة تسويقية\n\nهل تريد المتابعة لمرحلة البناء؟ (أرسل 'متابعة' أو 'موافقة')",
                {"plans": list(plans.keys()), "next_phase": "building"},
            )
            
            await self._save_project(project)
            
        except Exception as e:
            logger.error("Planning phase failed: %s", e)
            project.phase = ProjectPhase.PAUSED
            await self._notify(project, f"❌ فشل التخطيط: {str(e)}")
    
    async def _run_build_phase(self, project: Project):
        """مرحلة البناء — بناء الموقع + السوشيل ميديا + العروض"""
        project.phase = ProjectPhase.BUILDING
        project.updated_at = time.time()

        # v30: Publish building_started event to NeuralBus
        self._publish_event("building_started", project)

        await self._notify(project, "🔨 جاري بناء المشروع...")
        
        build_results = {}
        
        try:
            # 1. Build Website
            web_step = next((s for s in project.steps if s.id == "website"), None)
            if web_step:
                web_step.status = "running"
                web_step.started_at = time.time()
            
            if self._tools and self._llm:
                # Generate website code
                web_response = await self._llm.think(
                    prompt=f"""صمّم وابنِ موقع ويب لمشروع: {project.description}

الموقع يتضمن:
1. صفحة رئيسية (Hero + Features + CTA)
2. صفحة الخدمات
3. صفحة التسعير
4. صفحة التواصل
5. صفحة عن المشروع

أعطني كود React/Next.js كامل مع Tailwind CSS.""",
                    system="أنت مطور ويب خبير. اكتب كود React/Next.js حديث وجاهز للتنفيذ مع Tailwind CSS.",
                    model="glm-5.1",  # Neural/Primary — code generation
                    temperature=0.4,
                )
                build_results["website_code"] = web_response.text[:10000]
                
                # Save the code
                project_dir = self._data_dir / project.id / "website"
                project_dir.mkdir(parents=True, exist_ok=True)
                
                # Save main page
                main_page_path = project_dir / "page.tsx"
                main_page_path.write_text(web_response.text, encoding='utf-8')
                
                project.artifacts.append({
                    "type": "website",
                    "path": str(project_dir),
                    "description": "موقع المشروع - Next.js + Tailwind",
                })
                
                if web_step:
                    web_step.status = "completed"
                    web_step.artifacts = [{"type": "website", "path": str(project_dir)}]
                    web_step.completed_at = time.time()
                    web_step.duration_ms = (web_step.completed_at - web_step.started_at) * 1000
            
            # 2. Social Media Content
            social_step = next((s for s in project.steps if s.id == "social_media"), None)
            if social_step:
                social_step.status = "running"
                social_step.started_at = time.time()
            
            if self._llm:
                social_response = await self._llm.think(
                    prompt=f"""أنشئ محتوى سوشيل ميديا كامل لمشروع: {project.description}

أنشئ:
1. 7 منشورات Instagram مع captions و hashtags
2. 5 تغريدات Twitter
3. 3 منشورات LinkedIn
4. وصف الحسابات (Bio) لكل منصة
5. أفكار لـ Stories و Reels""",
                    system="أنت مدير سوشيل ميديا خبير. محتوى جذاب واحترافي.",
                    model="deepseek-chat",  # WorldModel/Scenario — creative content generation
                    temperature=0.7,
                    json_mode=True,
                )
                social_data = social_response.extract_json() or {}
                build_results["social_media"] = social_data
                
                # Save
                social_path = self._data_dir / project.id / "social_media_plan.json"
                social_path.parent.mkdir(parents=True, exist_ok=True)
                social_path.write_text(json.dumps(social_data, ensure_ascii=False, indent=2), encoding='utf-8')
                
                if social_step:
                    social_step.status = "completed"
                    social_step.result = social_data
                    social_step.completed_at = time.time()
                    social_step.duration_ms = (social_step.completed_at - social_step.started_at) * 1000
            
            # 3. Pitch Deck
            pitch_step = next((s for s in project.steps if s.id == "pitch_deck"), None)
            if pitch_step:
                pitch_step.status = "running"
                pitch_step.started_at = time.time()
            
            if self._llm:
                pitch_response = await self._llm.think(
                    prompt=f"""اصنع عرض مستثمرين (Pitch Deck) لمشروع: {project.description}

العرض يشمل:
1. المشكلة والحل
2. حجم السوق
3. نموذج العمل
4. المنافسة وميزة التنافس
5. خطة النمو
6. الفريق المطلوب
7. الاستثمار المطلوب واستخدام الأموال""",
                    system="أنت مستشار استثمار خبير. عروض مقنعة ومبنية على أرقام.",
                    model="glm-5.1",  # Neural/Primary — strategic + creative pitch
                    temperature=0.4,
                    json_mode=True,
                )
                pitch_data = pitch_response.extract_json() or {}
                build_results["pitch_deck"] = pitch_data
                
                if pitch_step:
                    pitch_step.status = "completed"
                    pitch_step.result = pitch_data
                    pitch_step.completed_at = time.time()
                    pitch_step.duration_ms = (pitch_step.completed_at - pitch_step.started_at) * 1000
            
            # 4. Funding Strategy
            fund_step = next((s for s in project.steps if s.id == "funding_plan"), None)
            if fund_step:
                fund_step.status = "running"
                fund_step.started_at = time.time()
            
            if self._llm:
                fund_response = await self._llm.think(
                    prompt=f"""ضع استراتيجية تمويل لمشروع: {project.description}

التخطيط يشمل:
1. مصادر التمويل المناسبة
2. مراحل التمويل (Seed, Series A, etc.)
3. خطة التواصل مع المستثمرين
4. قائمة المستثمرين المحتملين في المنطقة
5. نصائح للتفاوض""",
                    system="أنت مستشار تمويل خبير. استراتيجيات عملية وقابلة للتنفيذ.",
                    model="deepseek-reasoner",  # Causal/Reasoning — analytical funding strategy
                    temperature=0.4,
                    json_mode=True,
                )
                fund_data = fund_response.extract_json() or {}
                build_results["funding_strategy"] = fund_data
                
                if fund_step:
                    fund_step.status = "completed"
                    fund_step.result = fund_data
                    fund_step.completed_at = time.time()
                    fund_step.duration_ms = (fund_step.completed_at - fund_step.started_at) * 1000
            
            project.build_data = build_results
            project.phase = ProjectPhase.DELIVERED
            project.updated_at = time.time()

            # v30: Publish project_delivered event to NeuralBus
            self._publish_event("project_delivered", project, {
                "artifacts": [a.get("type", "") for a in project.artifacts],
                "build_results": list(build_results.keys()),
            })

            # Save all project data
            await self._save_project(project)
            
            await self._notify(
                project,
                f"🎉 مشروع {project.name} جاهز!\n\nتم إنجاز:\n✅ بحث السوق\n✅ دراسة الجدوى\n✅ خطة الأعمال\n✅ الخطة التسويقية\n✅ كود الموقع\n✅ محتوى السوشيل ميديا\n✅ عرض المستثمرين\n✅ استراتيجية التمويل\n\nجميع الملفات محفوظة في: /download/projects/{project.id}/",
                {"artifacts": project.artifacts, "build_results": list(build_results.keys())},
            )
            
        except Exception as e:
            logger.error("Build phase failed: %s", e)
            project.phase = ProjectPhase.PAUSED
            await self._notify(project, f"❌ فشل البناء: {str(e)}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # Project Management
    # ─────────────────────────────────────────────────────────────────────────
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """الحصول على مشروع"""
        return self._projects.get(project_id)
    
    def list_projects(self) -> list[dict]:
        """قائمة جميع المشاريع"""
        return [
            {
                "id": p.id,
                "name": p.name,
                "phase": p.phase.value,
                "created_at": p.created_at,
                "steps_completed": sum(1 for s in p.steps if s.status == "completed"),
                "steps_total": len(p.steps),
                "artifacts_count": len(p.artifacts),
            }
            for p in self._projects.values()
        ]
    
    async def _save_project(self, project: Project):
        """حفظ حالة المشروع"""
        project_dir = self._data_dir / project.id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        state = {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "phase": project.phase.value,
            "research_data": project.research_data,
            "plan_data": project.plan_data,
            "build_data": project.build_data,
            "artifacts": project.artifacts,
            "steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "name_ar": s.name_ar,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                }
                for s in project.steps
            ],
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        }
        
        state_path = project_dir / "state.json"
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


# Singleton
_project_orchestrator: Optional[ProjectOrchestrator] = None

def get_project_orchestrator(llm_client=None, real_tools=None, ws_manager=None, neural_bus=None) -> ProjectOrchestrator:
    """الحصول على منسق المشاريع (Singleton)"""
    global _project_orchestrator
    if _project_orchestrator is None:
        _project_orchestrator = ProjectOrchestrator(
            llm_client=llm_client,
            real_tools=real_tools,
            ws_manager=ws_manager,
            neural_bus=neural_bus,
        )
    elif neural_bus and not _project_orchestrator._neural_bus:
        # Retroactively attach NeuralBus if it wasn't provided at creation
        _project_orchestrator._neural_bus = neural_bus
    return _project_orchestrator
