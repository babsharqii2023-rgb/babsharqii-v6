"""
BABSHARQII v18.0 — Skill Executor
منفّذ المهارات — المحرك الذي يربط كل القدرات بالنواة

The SkillExecutor is the BRIDGE between:
  - CapabilityRouter (classifies user intent)
  - MamounKernel (the consciousness loop)
  - Actual skill implementations (ProjectBuilder, ContentPipeline, etc.)

Pipeline:
  User Message → CapabilityRouter → SkillExecutor → Skill Implementation → Response

Each skill is a callable that receives (message, context, llm_client) and returns a result dict.
Skills can be:
  - LLM-powered (uses the LLM to generate content/code/analysis)
  - Tool-based (executes commands, reads files, deploys)
  - Hybrid (LLM reasoning + tool execution)

Based on:
- ReAct (Yao et al., 2023): Reason + Act loop
- Toolformer (Schick et al., 2023): LLMs that use tools
- SOFAI (Fast/Slow): System 1 for simple skills, System 2 for complex
"""

import asyncio
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from enum import Enum

from mamoun.core.llm_client import LLMClient, get_llm_client

logger = logging.getLogger("mamoun.core.skill_executor")


# ─────────────────────────────────────────────────────────────────────────────
# Skill Data Structures
# ─────────────────────────────────────────────────────────────────────────────

class SkillComplexity(str, Enum):
    """مستوى تعقيد المهارة — يحدد System 1 أو System 2"""
    SIMPLE = "simple"        # System 1 — إجابة مباشرة سريعة
    MODERATE = "moderate"    # System 1+ — إجابة مع بحث بسيط
    COMPLEX = "complex"      # System 2 — تفكير عميق + تنفيذ
    CRITICAL = "critical"    # System 2+ — تفكير عميق + مراجعة + موافقة


@dataclass
class SkillDefinition:
    """تعريف المهارة — ما هي وماذا تفعل وكيف تُنفّذ"""
    id: str
    name: str
    name_ar: str
    domain: str              # programming, content, business, site_control, tools, general, self_reflection
    complexity: SkillComplexity = SkillComplexity.MODERATE
    description: str = ""
    description_ar: str = ""
    executor: Callable = None  # async def executor(message, context, llm) -> dict
    requires_approval: bool = False
    timeout_seconds: int = 120
    tags: list = field(default_factory=list)


@dataclass
class SkillResult:
    """نتيجة تنفيذ المهارة"""
    success: bool = False
    response: str = ""
    data: dict = field(default_factory=dict)
    skill_id: str = ""
    execution_time_ms: float = 0.0
    complexity_used: str = ""
    artifacts: list = field(default_factory=list)  # ملفات، روابط، صور، إلخ
    follow_up_suggestions: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "response": self.response[:2000],
            "data": self.data,
            "skill_id": self.skill_id,
            "execution_time_ms": round(self.execution_time_ms, 1),
            "complexity": self.complexity_used,
            "artifacts": self.artifacts,
            "follow_up": self.follow_up_suggestions[:3],
        }


# ─────────────────────────────────────────────────────────────────────────────
# The Skill Executor
# ─────────────────────────────────────────────────────────────────────────────

class SkillExecutor:
    """
    منفّذ المهارات — الجسر بين النواة والقدرات الفعلية

    Responsibilities:
    1. Register all available skills
    2. Route requests to the correct skill
    3. Execute skills with appropriate System 1/System 2 strategy
    4. Handle errors and timeouts
    5. Track skill execution history
    """

    def __init__(self, llm_client: LLMClient = None):
        self._llm = llm_client or get_llm_client()
        self._skills: dict[str, SkillDefinition] = {}
        self._execution_history: list[dict] = []
        self._stats = {
            "total_executions": 0,
            "successful": 0,
            "failed": 0,
            "by_domain": {},
            "by_skill": {},
        }

    def register_skill(self, skill: SkillDefinition):
        """تسجيل مهارة جديدة"""
        self._skills[skill.id] = skill
        logger.info("Skill registered: %s (%s) — %s", skill.id, skill.domain, skill.name_ar)

    def get_skill(self, skill_id: str) -> Optional[SkillDefinition]:
        """الحصول على مهارة بالمعرّف"""
        return self._skills.get(skill_id)

    def get_skills_by_domain(self, domain: str) -> list[SkillDefinition]:
        """الحصول على مهارات بنطاق محدد"""
        return [s for s in self._skills.values() if s.domain == domain]

    def list_skills(self) -> list[dict]:
        """قائمة جميع المهارات المسجّلة"""
        return [
            {
                "id": s.id,
                "name": s.name,
                "name_ar": s.name_ar,
                "domain": s.domain,
                "complexity": s.complexity.value,
                "description_ar": s.description_ar[:200],
                "requires_approval": s.requires_approval,
            }
            for s in self._skills.values()
        ]

    async def execute(
        self,
        skill_id: str,
        message: str,
        context: dict = None,
    ) -> SkillResult:
        """
        تنفيذ مهارة محددة

        Strategy based on complexity:
        - SIMPLE: Direct LLM call (System 1)
        - MODERATE: LLM call with context enrichment
        - COMPLEX: Multi-step reasoning + tool execution (System 2)
        - CRITICAL: Complex + human approval gate
        """
        context = context or {}
        skill = self._skills.get(skill_id)

        if not skill:
            return SkillResult(
                success=False,
                response=f"المهارة '{skill_id}' غير مسجّلة",
                skill_id=skill_id,
            )

        start_time = time.time()
        logger.info("Executing skill: %s (%s) for message: %s",
                    skill.id, skill.complexity.value, message[:100])

        try:
            # Execute with timeout
            if skill.executor:
                # Use the custom executor
                result = await asyncio.wait_for(
                    skill.executor(message, context, self._llm),
                    timeout=skill.timeout_seconds,
                )
                if isinstance(result, dict):
                    skill_result = SkillResult(
                        success=result.get("success", True),
                        response=result.get("response", ""),
                        data=result.get("data", {}),
                        skill_id=skill.id,
                        execution_time_ms=(time.time() - start_time) * 1000,
                        complexity_used=skill.complexity.value,
                        artifacts=result.get("artifacts", []),
                        follow_up_suggestions=result.get("follow_up", []),
                    )
                elif isinstance(result, SkillResult):
                    skill_result = result
                    skill_result.skill_id = skill.id
                    skill_result.execution_time_ms = (time.time() - start_time) * 1000
                    skill_result.complexity_used = skill.complexity.value
                else:
                    skill_result = SkillResult(
                        success=True,
                        response=str(result),
                        skill_id=skill.id,
                        execution_time_ms=(time.time() - start_time) * 1000,
                        complexity_used=skill.complexity.value,
                    )
            else:
                # No custom executor — use LLM as fallback
                skill_result = await self._llm_execute(skill, message, context, start_time)

            # Track stats
            self._track_execution(skill, skill_result.success, (time.time() - start_time) * 1000)

            return skill_result

        except asyncio.TimeoutError:
            logger.error("Skill '%s' timed out after %ds", skill.id, skill.timeout_seconds)
            return SkillResult(
                success=False,
                response=f"انتهت مهلة تنفيذ المهارة '{skill.name_ar}' — حاول مرة أخرى",
                skill_id=skill.id,
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            logger.error("Skill '%s' failed: %s", skill.id, e)
            return SkillResult(
                success=False,
                response=f"خطأ في تنفيذ المهارة: {str(e)}",
                skill_id=skill.id,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    async def _llm_execute(
        self,
        skill: SkillDefinition,
        message: str,
        context: dict,
        start_time: float,
    ) -> SkillResult:
        """تنفيذ باستخدام LLM فقط — عندما لا يوجد منفّذ مخصص"""

        system_prompt = f"""أنت مأمون — منفّذ مهارة "{skill.name_ar}" في نطاق {skill.domain}.
{skill.description_ar}

أجب بالعربية بشكل مفصل ومنظم. قدّم نتيجة عملية يمكن استخدامها."""

        # Add context if available
        context_text = ""
        if context:
            context_text = f"\n\nالسياق:\n{json.dumps(context, ensure_ascii=False, default=str)[:2000]}"

        # Choose model based on complexity
        model = "deepseek-chat"
        temperature = 0.7
        if skill.complexity in (SkillComplexity.COMPLEX, SkillComplexity.CRITICAL):
            model = "deepseek-reasoner"
            temperature = 0.3

        response = await self._llm.think(
            prompt=f"{message}{context_text}",
            system=system_prompt,
            model=model,
            temperature=temperature,
        )

        return SkillResult(
            success=bool(response.text),
            response=response.text,
            skill_id=skill.id,
            execution_time_ms=(time.time() - start_time) * 1000,
            complexity_used=skill.complexity.value,
        )

    async def execute_by_domain(
        self,
        domain: str,
        capability: str,
        message: str,
        context: dict = None,
    ) -> SkillResult:
        """
        تنفيذ مهارة بناءً على النطاق والقدرة
        يبحث عن أفضل مهارة مطابقة
        """
        context = context or {}

        # Find the best matching skill
        best_skill = self._find_skill(domain, capability)

        if best_skill:
            return await self.execute(best_skill.id, message, context)

        # No matching skill — use LLM with domain-aware prompt
        return await self._domain_fallback(domain, capability, message, context)

    def _find_skill(self, domain: str, capability: str) -> Optional[SkillDefinition]:
        """البحث عن أفضل مهارة مطابقة"""
        # First try exact match by ID
        if capability in self._skills:
            return self._skills[capability]

        # Then try matching by domain + tags
        domain_skills = self.get_skills_by_domain(domain)
        if domain_skills:
            # Try to match capability in tags
            cap_lower = capability.lower()
            for skill in domain_skills:
                if cap_lower in skill.id.lower() or cap_lower in [t.lower() for t in skill.tags]:
                    return skill
            # Return first skill in domain as fallback
            return domain_skills[0]

        return None

    async def _domain_fallback(
        self,
        domain: str,
        capability: str,
        message: str,
        context: dict,
    ) -> SkillResult:
        """تنفيذ احتياطي عندما لا توجد مهارة مسجّلة"""
        start_time = time.time()

        domain_prompts = {
            "programming": "أنت مبرمج خبير. اكتب كوداً كاملاً وجاهزاً للتنفيذ.",
            "content": "أنت صانع محتوى إبداعي. أنشئ محتوى جذاباً ومنظماً.",
            "business": "أنت محلل أعمال استراتيجي. قدّم تحليلاً عميقاً مع أرقام وتوصيات.",
            "site_control": "أنت مطور ويب. صمّم وبنِ صفحات ويب حديثة ومتجاوبة.",
            "tools": "أنت مساعد تقني. نفّذ الأوامر والعمليات المطلوبة.",
            "self_reflection": "أنت نظام تأمل ذاتي. حلل وحاكم نفسك بموضوعية.",
            "general": "أنت مساعد ذكي. أجب بدقة وعمق.",
        }

        system = domain_prompts.get(domain, domain_prompts["general"])

        response = await self._llm.think(
            prompt=message,
            system=f"{system}\n\nالقدرة المطلوبة: {capability}\nالنطاق: {domain}",
            model="glm-5.1",
        )

        return SkillResult(
            success=bool(response.text),
            response=response.text,
            skill_id=f"{domain}_fallback",
            execution_time_ms=(time.time() - start_time) * 1000,
            complexity_used="fallback",
        )

    def _track_execution(self, skill: SkillDefinition, success: bool, duration_ms: float):
        """تتبع إحصائيات التنفيذ"""
        self._stats["total_executions"] += 1
        if success:
            self._stats["successful"] += 1
        else:
            self._stats["failed"] += 1

        self._stats["by_domain"][skill.domain] = self._stats["by_domain"].get(skill.domain, 0) + 1
        self._stats["by_skill"][skill.id] = self._stats["by_skill"].get(skill.id, 0) + 1

        self._execution_history.append({
            "skill_id": skill.id,
            "domain": skill.domain,
            "success": success,
            "duration_ms": round(duration_ms, 1),
            "timestamp": time.time(),
        })

        # Keep history bounded
        if len(self._execution_history) > 200:
            self._execution_history = self._execution_history[-100:]

    def get_stats(self) -> dict:
        """إحصائيات المنفّذ"""
        return {
            "total_skills": len(self._skills),
            "total_executions": self._stats["total_executions"],
            "success_rate": round(
                self._stats["successful"] / max(1, self._stats["total_executions"]), 3
            ),
            "by_domain": self._stats["by_domain"],
            "by_skill": self._stats["by_skill"],
            "recent_executions": self._execution_history[-10:],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Skill Registry — Build and register all skills
# ─────────────────────────────────────────────────────────────────────────────

def build_skill_registry(llm_client: LLMClient = None) -> SkillExecutor:
    """
    بناء وتسجيل جميع المهارات المتاحة
    This is called once at startup to populate the SkillExecutor.
    v18.0: All skills now have CUSTOM EXECUTORS (not just LLM fallback).
    """
    from mamoun.core.skill_executors import SKILL_EXECUTORS
    executor = SkillExecutor(llm_client=llm_client)

    # ═══════════════════════════════════════════════════════════════════════
    # الفئة 1: مهارات البرمجة (Programming)
    # ═══════════════════════════════════════════════════════════════════════

    executor.register_skill(SkillDefinition(
        id="build_project",
        name="Project Builder",
        name_ar="بناء مشروع",
        domain="programming",
        complexity=SkillComplexity.COMPLEX,
        description="Build complete software projects from specifications",
        description_ar="بناء مشاريع برمجية كاملة من المواصفات — ويب، موبايل، API، أنظمة",
        executor=SKILL_EXECUTORS.get("build_project"),
        tags=["build", "project", "saas", "app", "web", "api"],
        requires_approval=False,
        timeout_seconds=300,
    ))

    executor.register_skill(SkillDefinition(
        id="build_saas",
        name="SaaS Builder",
        name_ar="بناء نظام SaaS",
        domain="programming",
        complexity=SkillComplexity.COMPLEX,
        description="Build SaaS applications with subscriptions and dashboards",
        description_ar="بناء تطبيقات SaaS باشتراكات وداشبوردات ولوحات تحكم",
        executor=SKILL_EXECUTORS.get("build_saas"),
        tags=["saas", "subscription", "dashboard", "multi-tenant"],
        requires_approval=False,
        timeout_seconds=300,
    ))

    executor.register_skill(SkillDefinition(
        id="build_dashboard",
        name="Dashboard Builder",
        name_ar="بناء داشبورد",
        domain="programming",
        complexity=SkillComplexity.COMPLEX,
        description="Build data dashboards and analytics interfaces",
        description_ar="بناء داشبوردات بيانات وواجهات تحليل مع رسوم بيانية",
        executor=SKILL_EXECUTORS.get("build_dashboard"),
        tags=["dashboard", "analytics", "charts", "data"],
        requires_approval=False,
        timeout_seconds=240,
    ))

    executor.register_skill(SkillDefinition(
        id="fix_improve_code",
        name="Code Fixer & Improver",
        name_ar="إصلاح وتحسين الكود",
        domain="programming",
        complexity=SkillComplexity.MODERATE,
        description="Fix bugs and improve existing code",
        description_ar="إصلاح الأخطاء وتحسين الكود الموجود — أداء، أمان، بنية",
        executor=SKILL_EXECUTORS.get("fix_improve_code"),
        tags=["fix", "improve", "refactor", "debug", "optimize"],
        requires_approval=False,
        timeout_seconds=180,
    ))

    executor.register_skill(SkillDefinition(
        id="build_landing",
        name="Landing Page Builder",
        name_ar="بناء صفحة هبوط",
        domain="programming",
        complexity=SkillComplexity.MODERATE,
        description="Build landing pages with modern design",
        description_ar="بناء صفحات هبوط احترافية بتصميم عصري ومتجاوب",
        executor=SKILL_EXECUTORS.get("build_landing"),
        tags=["landing", "page", "marketing", "design"],
        requires_approval=False,
        timeout_seconds=180,
    ))

    executor.register_skill(SkillDefinition(
        id="build_workflow",
        name="Workflow Builder",
        name_ar="بناء وركفلو",
        domain="programming",
        complexity=SkillComplexity.COMPLEX,
        description="Build automated workflows and integrations",
        description_ar="بناء وركفلات آلية وتكاملات بين الأنظمة",
        executor=SKILL_EXECUTORS.get("build_workflow"),
        tags=["workflow", "automation", "integration", "zapier"],
        requires_approval=False,
        timeout_seconds=240,
    ))

    # ═══════════════════════════════════════════════════════════════════════
    # الفئة 1b: مهارات برمجية إضافية (Programming Extended)
    # ═══════════════════════════════════════════════════════════════════════

    executor.register_skill(SkillDefinition(
        id="build_mobile",
        name="Mobile App Builder",
        name_ar="بناء تطبيق موبايل",
        domain="programming",
        complexity=SkillComplexity.COMPLEX,
        description="Build mobile applications (React Native / Flutter)",
        description_ar="بناء تطبيقات موبايل — React Native أو Flutter مع شاشات وAPI",
        executor=SKILL_EXECUTORS.get("build_mobile"),
        tags=["mobile", "react-native", "flutter", "ios", "android"],
        requires_approval=False,
        timeout_seconds=300,
    ))

    executor.register_skill(SkillDefinition(
        id="code_review",
        name="Code Reviewer",
        name_ar="مراجعة الكود",
        domain="programming",
        complexity=SkillComplexity.MODERATE,
        description="Review code for security, performance, and quality",
        description_ar="مراجعة كود شاملة — أمان، أداء، جودة، بنية",
        executor=SKILL_EXECUTORS.get("code_review"),
        tags=["review", "security", "quality", "best-practices"],
        requires_approval=False,
        timeout_seconds=180,
    ))

    # ═══════════════════════════════════════════════════════════════════════
    # الفئة 2: مهارات المحتوى (Content) — 8 مهارات
    # ═══════════════════════════════════════════════════════════════════════

    executor.register_skill(SkillDefinition(
        id="create_content",
        name="Content Creator",
        name_ar="صانع محتوى",
        domain="content",
        complexity=SkillComplexity.MODERATE,
        description="Create various types of content",
        description_ar="صناعة محتوى إبداعي — مقالات، منشورات، سكربتات",
        executor=SKILL_EXECUTORS.get("create_content"),
        tags=["content", "writing", "creative", "copywriting"],
        requires_approval=False,
        timeout_seconds=120,
    ))

    executor.register_skill(SkillDefinition(
        id="social_media",
        name="Social Media Manager",
        name_ar="مدير السوشيل ميديا",
        domain="content",
        complexity=SkillComplexity.MODERATE,
        description="Create social media content and strategies",
        description_ar="إدارة محتوى السوشيل ميديا واستراتيجيات النشر",
        executor=SKILL_EXECUTORS.get("social_media"),
        tags=["social", "instagram", "twitter", "tiktok", "linkedin"],
        requires_approval=False,
        timeout_seconds=120,
    ))

    executor.register_skill(SkillDefinition(
        id="content_strategy",
        name="Content Strategist",
        name_ar="استراتيجي المحتوى",
        domain="content",
        complexity=SkillComplexity.COMPLEX,
        description="Develop content strategies and calendars",
        description_ar="تطوير استراتيجيات محتوى وخطط نشر شاملة",
        executor=SKILL_EXECUTORS.get("content_strategy"),
        tags=["strategy", "calendar", "plan", "campaign"],
        requires_approval=False,
        timeout_seconds=180,
    ))

    executor.register_skill(SkillDefinition(
        id="seo_blog",
        name="SEO & Blog Writer",
        name_ar="كاتب SEO ومدونة",
        domain="content",
        complexity=SkillComplexity.MODERATE,
        description="Write SEO-optimized blog articles",
        description_ar="كتابة مقالات مدونة محسّنة لمحركات البحث",
        executor=SKILL_EXECUTORS.get("seo_blog"),
        tags=["seo", "blog", "article", "keywords", "ranking"],
        requires_approval=False,
        timeout_seconds=150,
    ))

    executor.register_skill(SkillDefinition(
        id="video_animation",
        name="Video & Animation Creator",
        name_ar="صانع فيديو وأنيميشن",
        domain="content",
        complexity=SkillComplexity.COMPLEX,
        description="Create video scripts and animation concepts",
        description_ar="صناعة سكربتات فيديو ومفاهيم أنيميشن",
        executor=SKILL_EXECUTORS.get("video_animation"),
        tags=["video", "animation", "youtube", "motion", "script"],
        requires_approval=False,
        timeout_seconds=180,
    ))

    executor.register_skill(SkillDefinition(
        id="presentation",
        name="Presentation Builder",
        name_ar="صانع عروض تقديمية",
        domain="content",
        complexity=SkillComplexity.MODERATE,
        description="Create professional presentations",
        description_ar="صناعة عروض تقديمية احترافية",
        executor=SKILL_EXECUTORS.get("presentation"),
        tags=["presentation", "slides", "pitch", "keynote"],
        requires_approval=False,
        timeout_seconds=150,
    ))

    executor.register_skill(SkillDefinition(
        id="story_design",
        name="Story/Reel Designer",
        name_ar="مصمم ستوري/ريلز",
        domain="content",
        complexity=SkillComplexity.MODERATE,
        description="Design social media stories and reels",
        description_ar="تصميم ستوريز وريلز للسوشيل ميديا",
        executor=SKILL_EXECUTORS.get("story_design"),
        tags=["story", "reel", "design", "instagram", "tiktok"],
        requires_approval=False,
        timeout_seconds=120,
    ))

    executor.register_skill(SkillDefinition(
        id="copywriting",
        name="Copywriter",
        name_ar="كاتب إعلاني",
        domain="content",
        complexity=SkillComplexity.MODERATE,
        description="Write persuasive ad copy using AIDA, PAS, FAB frameworks",
        description_ar="كتابة إعلانية احترافية — AIDA, PAS, FAB, Before-After-Bridge",
        executor=SKILL_EXECUTORS.get("copywriting"),
        tags=["copywriting", "ad", "AIDA", "PAS", "persuasion"],
        requires_approval=False,
        timeout_seconds=120,
    ))

    # ═══════════════════════════════════════════════════════════════════════
    # الفئة 3: مهارات الأعمال (Business) — 8 مهارات
    # ═══════════════════════════════════════════════════════════════════════

    executor.register_skill(SkillDefinition(
        id="analyze_idea",
        name="Idea Analyzer",
        name_ar="محلل الأفكار",
        domain="business",
        complexity=SkillComplexity.COMPLEX,
        description="Analyze business ideas with SWOT and market data",
        description_ar="تحليل أفكار المشاريع بتحليل SWOT وبيانات السوق",
        executor=SKILL_EXECUTORS.get("analyze_idea"),
        tags=["idea", "analysis", "swot", "validation"],
        requires_approval=False,
        timeout_seconds=180,
    ))

    executor.register_skill(SkillDefinition(
        id="feasibility_study",
        name="Feasibility Study Builder",
        name_ar="صانع دراسات الجدوى",
        domain="business",
        complexity=SkillComplexity.COMPLEX,
        description="Create comprehensive feasibility studies",
        description_ar="إنشاء دراسات جدوى شاملة مع أرقام وتحليلات مالية",
        executor=SKILL_EXECUTORS.get("feasibility_study"),
        tags=["feasibility", "study", "financial", "roi", "break-even"],
        requires_approval=False,
        timeout_seconds=240,
    ))

    executor.register_skill(SkillDefinition(
        id="business_plan",
        name="Business Plan Writer",
        name_ar="كاتب خطط الأعمال",
        domain="business",
        complexity=SkillComplexity.COMPLEX,
        description="Write detailed business plans",
        description_ar="كتابة خطط أعمال تفصيلية شاملة",
        executor=SKILL_EXECUTORS.get("business_plan"),
        tags=["business plan", "strategy", "goals", "operations"],
        requires_approval=False,
        timeout_seconds=240,
    ))

    executor.register_skill(SkillDefinition(
        id="market_research",
        name="Market Researcher",
        name_ar="باحث السوق",
        domain="business",
        complexity=SkillComplexity.COMPLEX,
        description="Conduct market research and competitor analysis",
        description_ar="إجراء أبحاث سوق وتحليل منافسين",
        executor=SKILL_EXECUTORS.get("market_research"),
        tags=["market", "research", "competitor", "trends"],
        requires_approval=False,
        timeout_seconds=180,
    ))

    executor.register_skill(SkillDefinition(
        id="marketing_plan",
        name="Marketing Plan Builder",
        name_ar="صانع خطة تسويقية",
        domain="business",
        complexity=SkillComplexity.COMPLEX,
        description="Build marketing plans and strategies",
        description_ar="بناء خطط تسويقية واستراتيجيات نمو",
        executor=SKILL_EXECUTORS.get("marketing_plan"),
        tags=["marketing", "plan", "growth", "advertising"],
        requires_approval=False,
        timeout_seconds=180,
    ))

    executor.register_skill(SkillDefinition(
        id="pitch_deck",
        name="Pitch Deck Builder",
        name_ar="صانع عرض المستثمرين",
        domain="business",
        complexity=SkillComplexity.COMPLEX,
        description="Create investor pitch decks",
        description_ar="صناعة عروض تقديمية للمستثمرين",
        executor=SKILL_EXECUTORS.get("pitch_deck"),
        tags=["pitch", "investor", "funding", "startup"],
        requires_approval=False,
        timeout_seconds=180,
    ))

    executor.register_skill(SkillDefinition(
        id="business_analysis",
        name="Business Analyst",
        name_ar="محلل أعمال",
        domain="business",
        complexity=SkillComplexity.MODERATE,
        description="General business analysis and recommendations",
        description_ar="تحليل أعمال عام وتوصيات استراتيجية",
        executor=SKILL_EXECUTORS.get("business_analysis"),
        tags=["analysis", "recommendations", "strategy"],
        requires_approval=False,
        timeout_seconds=150,
    ))

    executor.register_skill(SkillDefinition(
        id="find_funding",
        name="Funding Finder",
        name_ar="باحث التمويل",
        domain="business",
        complexity=SkillComplexity.COMPLEX,
        description="Find funding sources and prepare funding strategy",
        description_ar="البحث عن مصادر تمويل وإعداد استراتيجية الاستثمار",
        executor=SKILL_EXECUTORS.get("find_funding"),
        tags=["funding", "investor", "vc", "angel", "crowdfunding"],
        requires_approval=False,
        timeout_seconds=180,
    ))

    # ═══════════════════════════════════════════════════════════════════════
    # الفئة 4: مهارات الموقع (Site Control) — 4 مهارات
    # ═══════════════════════════════════════════════════════════════════════

    executor.register_skill(SkillDefinition(
        id="site_build_modify",
        name="Site Builder & Modifier",
        name_ar="بناء وتعديل المواقع",
        domain="site_control",
        complexity=SkillComplexity.COMPLEX,
        description="Build and modify website pages",
        description_ar="بناء وتعديل صفحات الموقع بتصميم عصري",
        executor=SKILL_EXECUTORS.get("site_build_modify"),
        tags=["site", "page", "build", "modify", "web"],
        requires_approval=False,
        timeout_seconds=240,
    ))

    executor.register_skill(SkillDefinition(
        id="seo_optimize",
        name="SEO Optimizer",
        name_ar="محسّن SEO",
        domain="site_control",
        complexity=SkillComplexity.MODERATE,
        description="Optimize website for search engines",
        description_ar="تحسين الموقع لمحركات البحث",
        executor=SKILL_EXECUTORS.get("seo_optimize"),
        tags=["seo", "optimization", "ranking", "traffic"],
        requires_approval=False,
        timeout_seconds=150,
    ))

    executor.register_skill(SkillDefinition(
        id="performance_optimize",
        name="Performance Optimizer",
        name_ar="محسّن الأداء",
        domain="site_control",
        complexity=SkillComplexity.MODERATE,
        description="Optimize website performance and speed",
        description_ar="تحسين أداء وسرعة الموقع",
        executor=SKILL_EXECUTORS.get("performance_optimize"),
        tags=["performance", "speed", "core-web-vitals", "optimization"],
        requires_approval=False,
        timeout_seconds=150,
    ))

    executor.register_skill(SkillDefinition(
        id="ecommerce_store",
        name="E-commerce Store Builder",
        name_ar="بناء متجر إلكتروني",
        domain="site_control",
        complexity=SkillComplexity.COMPLEX,
        description="Build e-commerce stores with product catalogs and payment",
        description_ar="بناء متاجر إلكترونية مع كتالوج منتجات وبوابات دفع",
        executor=SKILL_EXECUTORS.get("ecommerce_store"),
        tags=["ecommerce", "store", "shop", "payment", "stripe"],
        requires_approval=False,
        timeout_seconds=300,
    ))

    # ═══════════════════════════════════════════════════════════════════════
    # الفئة 5: مهارات الأدوات (Tools) — 4 مهارات
    # ═══════════════════════════════════════════════════════════════════════

    executor.register_skill(SkillDefinition(
        id="execute_command",
        name="Command Executor",
        name_ar="منفّذ الأوامر",
        domain="tools",
        complexity=SkillComplexity.SIMPLE,
        description="Execute system commands safely",
        description_ar="تنفيذ أوامر النظام بأمان",
        executor=SKILL_EXECUTORS.get("execute_command"),
        tags=["command", "terminal", "execute", "shell"],
        requires_approval=True,
        timeout_seconds=60,
    ))

    executor.register_skill(SkillDefinition(
        id="deploy",
        name="Deployment Manager",
        name_ar="مدير النشر",
        domain="tools",
        complexity=SkillComplexity.COMPLEX,
        description="Deploy applications to various platforms",
        description_ar="نشر التطبيقات على منصات مختلفة",
        executor=SKILL_EXECUTORS.get("deploy"),
        tags=["deploy", "vercel", "railway", "production"],
        requires_approval=True,
        timeout_seconds=180,
    ))

    executor.register_skill(SkillDefinition(
        id="sandbox_test",
        name="Sandbox Tester",
        name_ar="مختبر الساندبوكس",
        domain="tools",
        complexity=SkillComplexity.MODERATE,
        description="Test code in sandbox environment",
        description_ar="اختبار الكود في بيئة آمنة معزولة",
        executor=SKILL_EXECUTORS.get("sandbox_test"),
        tags=["sandbox", "test", "safe", "execute"],
        requires_approval=False,
        timeout_seconds=120,
    ))

    executor.register_skill(SkillDefinition(
        id="api_builder",
        name="API Builder",
        name_ar="بناء APIs",
        domain="tools",
        complexity=SkillComplexity.COMPLEX,
        description="Build REST/GraphQL APIs and integrate external services",
        description_ar="بناء REST/GraphQL APIs وربط خدمات خارجية",
        executor=SKILL_EXECUTORS.get("api_builder"),
        tags=["api", "rest", "graphql", "swagger", "integration"],
        requires_approval=False,
        timeout_seconds=240,
    ))

    # ═══════════════════════════════════════════════════════════════════════
    # الفئة 6: مهارات التأمل الذاتي (Self-Reflection) — 3 مهارات
    # ═══════════════════════════════════════════════════════════════════════

    executor.register_skill(SkillDefinition(
        id="self_reflect",
        name="Self Reflector",
        name_ar="التأمل الذاتي",
        domain="self_reflection",
        complexity=SkillComplexity.COMPLEX,
        description="Deep self-reflection on system decisions and biases",
        description_ar="تأمل ذاتي عميق في قرارات النظام وتحيزاته",
        executor=SKILL_EXECUTORS.get("self_reflect"),
        tags=["reflect", "metacognition", "bias", "awareness"],
        requires_approval=False,
        timeout_seconds=180,
    ))

    executor.register_skill(SkillDefinition(
        id="system_check",
        name="System Checker",
        name_ar="فاحص النظام",
        domain="self_reflection",
        complexity=SkillComplexity.SIMPLE,
        description="Check system health and capabilities",
        description_ar="فحص صحة النظام وقدراته",
        executor=SKILL_EXECUTORS.get("system_check"),
        tags=["health", "check", "status", "diagnostics"],
        requires_approval=False,
        timeout_seconds=60,
    ))

    executor.register_skill(SkillDefinition(
        id="agent_briefing",
        name="Agent Briefing",
        name_ar="التقرير التعريفي",
        domain="self_reflection",
        complexity=SkillComplexity.MODERATE,
        description="Understand and explain system identity and capabilities",
        description_ar="فهم واستيعاب هوية مأمون وقدراته وحدوده",
        executor=SKILL_EXECUTORS.get("agent_briefing"),
        tags=["briefing", "identity", "self-knowledge", "agent_briefing"],
        requires_approval=False,
        timeout_seconds=120,
    ))

    # ═══════════════════════════════════════════════════════════════════════
    # التحقق — هل كل المهارات لها منفّذات؟
    # ═══════════════════════════════════════════════════════════════════════
    skills_with_executors = sum(1 for s in executor._skills.values() if s.executor is not None)
    skills_without_executors = [s.id for s in executor._skills.values() if s.executor is None]

    logger.info("SkillExecutor built with %d skills across %d domains (%d with custom executors)",
                len(executor._skills), len(set(s.domain for s in executor._skills.values())), skills_with_executors)

    if skills_without_executors:
        logger.warning("Skills WITHOUT custom executors (using LLM fallback): %s", skills_without_executors)

    return executor
