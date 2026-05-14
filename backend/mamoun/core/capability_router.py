"""
BABSHARQII v18.0 — Capability Router
موجّه القدرات — يحدد أي قدرة تُفعّل بناءً على طلب المستخدم

The CapabilityRouter sits between the Kernel and the CapabilityEngine.
It classifies user requests into capability domains and routes them
to the appropriate executor.

Capability Domains:
1. programming   — بناء مشاريع، SaaS، داشبوردات، workflows
2. content       — صناعة محتوى، سوشيل ميديا، SEO، عروض
3. business      — تحليل أفكار، دراسات جدوى، خطط عمل، تسويق
4. site_control  — بناء/تعديل صفحات، SEO، أداء
5. tools         — Terminal، ملفات، Sandbox، نشر، APIs
6. general       — محادثة عامة، أسئلة، معلومات
7. self_reflection — تأمل ذاتي، فحص النظام
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from mamoun.core.llm_client import LLMClient, get_llm_client

logger = logging.getLogger("mamoun.core.capability_router")


@dataclass
class CapabilityRoute:
    """نتيجة توجيه القدرة — يحدد أي منفّذ يتعامل مع الطلب"""
    domain: str = "general"
    capability: str = "chat"
    confidence: float = 0.5
    executor: str = "kernel"  # kernel, skill_executor, project_builder, content_pipeline, business_os, site_controller
    parameters: dict = field(default_factory=dict)
    reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "capability": self.capability,
            "confidence": round(self.confidence, 3),
            "executor": self.executor,
            "reasoning": self.reasoning[:300],
        }


class CapabilityRouter:
    """
    موجّه القدرات — يصنّف طلبات المستخدم ويوجّهها للمنفّذ المناسب

    Pipeline:
    1. Keyword analysis (fast, local)
    2. LLM classification (deep, when keywords ambiguous)
    3. Route to appropriate executor
    """

    # Domain keywords — Arabic + English
    DOMAIN_PATTERNS = {
        "programming": {
            "keywords": [
                # Arabic
                "ابنِ مشروع", "بناء مشروع", "اكتب مشروع", "سافت", "saas", "داشبورد",
                "dashboard", "وركفلو", "workflow", "صفحة هبوط", "landing page",
                "تطبيق موبايل", "react native", "flutter", "أصلح الكود", "حسّن الكود",
                "برمج", "كود", "api", "بروجكت", "ابنِ", "صمّم نظام",
                "أنشئ تطبيق", "اكتب كود", "بناء نظام", "نظام إدارة",
                # English
                "build project", "create app", "write code", "fix code",
                "improve code", "develop", "implement", "deploy",
            ],
            "executor": "project_builder",
        },
        "content": {
            "keywords": [
                # Arabic
                "محتوى", "منشور", "ستوري", "سوشيل ميديا", "instagram", "تويتر",
                "seo", "مدونة", "مقال", "عرض تقديمي", "فيديو", "أنيميشن",
                "استراتيجية محتوى", "كتابة", "كامبون", "حملة", "هاشتاق",
                "يوتيوب", "تيك توك", "لينكد إن", "نشر", "محتوى إبداعي",
                "اكتب مقال", "صمم ستوري", "اصنع فيديو",
                # English
                "content", "social media", "blog", "article", "video",
                "animation", "presentation", "marketing content",
            ],
            "executor": "content_pipeline",
        },
        "business": {
            "keywords": [
                # Arabic
                "فكرة مشروع", "دراسة جدوى", "خطة عمل", "business plan",
                "بحث سوق", "منافس", "مستثمر", "pitch deck", "تمويل",
                "تسويق", "خطة تسويقية", "ميزانية", "إيرادات", "تكاليف",
                "شركة", "مقاولات", "مطعم", "عيادة", "مؤسسة",
                "أرباح", "ROI", "نقطة التعادل",
                # English
                "feasibility", "business plan", "market research",
                "startup", "funding", "investor", "marketing plan",
            ],
            "executor": "business_os",
        },
        "site_control": {
            "keywords": [
                # Arabic
                "أضف صفحة", "عدّل الصفحة", "غيّر الألوان", "الموقع",
                "seo للموقع", "أداء الموقع", "سرعة الموقع",
                "أضف عنصر", "غيّر التصميم", "الصفحة الرئيسية",
                # English
                "add page", "modify page", "site speed", "website",
                "landing page build", "change design",
            ],
            "executor": "site_controller",
        },
        "tools": {
            "keywords": [
                # Arabic
                "شغّل أمر", "terminal", "نفّذ", "انشر", "deploy",
                "vercel", "railway", "اختبر", "sandbox", "ملف",
                "اقرأ الملف", "اكتب ملف", "api خارجية",
                # English
                "run command", "execute", "deploy", "test",
                "file system", "api connect",
            ],
            "executor": "tool_layer",
        },
        "self_reflection": {
            "keywords": [
                "من أنت", "كيف تفكر", "تأمل ذاتي", "فحص النظام",
                "agent_briefing", "الخطة التعريفية", "ماذا تعرف عن نفسك",
                "who are you", "self-reflect", "system check",
            ],
            "executor": "kernel",
        },
    }

    def __init__(self, llm_client: LLMClient = None):
        self._llm = llm_client or get_llm_client()
        self._history: list[CapabilityRoute] = []

    async def route(self, user_message: str, context: dict = None) -> CapabilityRoute:
        """
        توجيه رسالة المستخدم — يحدد القدرة والمنفّذ

        Strategy:
        1. Quick keyword scan (O(1))
        2. If ambiguous → LLM classification
        3. Return route
        """
        context = context or {}

        # Step 1: Keyword-based classification (fast)
        domain_scores = {}
        for domain, config in self.DOMAIN_PATTERNS.items():
            score = 0
            msg_lower = user_message.lower()
            for keyword in config["keywords"]:
                if keyword.lower() in msg_lower:
                    score += 1
            if score > 0:
                domain_scores[domain] = score

        # Step 2: If clear winner → route directly
        if domain_scores:
            best_domain = max(domain_scores, key=domain_scores.get)
            best_score = domain_scores[best_domain]

            # If high confidence (2+ keyword matches)
            if best_score >= 2:
                route = CapabilityRoute(
                    domain=best_domain,
                    capability=self._infer_capability(best_domain, user_message),
                    confidence=min(0.95, 0.6 + best_score * 0.1),
                    executor=self.DOMAIN_PATTERNS[best_domain]["executor"],
                    reasoning=f"تصنيف سريع: {best_score} كلمات مفتاحية في نطاق '{best_domain}'",
                )
                self._history.append(route)
                return route

        # Step 3: Ambiguous or no keywords → LLM classification
        try:
            llm_route = await self._llm_classify(user_message, context)
            if llm_route:
                self._history.append(llm_route)
                return llm_route
        except Exception as e:
            logger.warning("LLM classification failed: %s", e)

        # Step 4: Fallback → general chat via kernel
        route = CapabilityRoute(
            domain="general",
            capability="chat",
            confidence=0.5,
            executor="kernel",
            reasoning="لم يتطابق مع نطاق محدد — محادثة عامة",
        )
        self._history.append(route)
        return route

    async def _llm_classify(self, message: str, context: dict) -> Optional[CapabilityRoute]:
        """تصنيف بالـ LLM عندما تكون الكلمات المفتاحية غير كافية"""
        response = await self._llm.think(
            prompt=f"""صنّف هذا الطلب في أحد النطاقات التالية:
- programming: بناء مشاريع، كتابة كود، تطبيقات، أنظمة
- content: صناعة محتوى، سوشيل ميديا، مقالات، فيديو
- business: أفكار مشاريع، دراسات جدوى، خطط عمل، تسويق
- site_control: تعديل موقع، إضافة صفحات، SEO
- tools: تنفيذ أوامر، ملفات، نشر
- self_reflection: أسئلة عن النظام نفسه
- general: محادثة عامة

الطلب: {message}

أجب بصيغة JSON:
{{
  "domain": "programming | content | business | site_control | tools | self_reflection | general",
  "capability": "القدرة المحددة (مثلاً: build_project, write_content, market_research)",
  "confidence": 0.0-1.0,
  "reasoning": "لماذا اخترت هذا النطاق"
}}""",
            system="أنت موجّه قدرات في مأمون v18. تصنّف طلبات المستخدم بدقة.",
            model="glm-5.1",
            temperature=0.2,
            json_mode=True,
        )

        result = response.extract_json()
        if result:
            data = result
            domain = data.get("domain", "general")
            executor = self.DOMAIN_PATTERNS.get(domain, {}).get("executor", "kernel")

            return CapabilityRoute(
                domain=domain,
                capability=data.get("capability", "chat"),
                confidence=float(data.get("confidence", 0.5)),
                executor=executor,
                reasoning=data.get("reasoning", "تصنيف LLM"),
            )

        return None

    def _infer_capability(self, domain: str, message: str) -> str:
        """استنتاج القدرة المحددة من النطاق والرسالة"""
        # Simple keyword-based capability inference
        msg_lower = message.lower()

        if domain == "programming":
            if "saas" in msg_lower or "اشتراك" in msg_lower:
                return "build_saas"
            if "داشبورد" in msg_lower or "dashboard" in msg_lower:
                return "build_dashboard"
            if "workflow" in msg_lower or "وركفلو" in msg_lower:
                return "build_workflow"
            if "هبوط" in msg_lower or "landing" in msg_lower:
                return "build_landing"
            if "موبايل" in msg_lower or "mobile" in msg_lower:
                return "build_mobile"
            if "أصلح" in msg_lower or "حسّن" in msg_lower or "fix" in msg_lower:
                return "fix_improve_code"
            return "build_project"

        if domain == "content":
            if "استراتيج" in msg_lower:
                return "content_strategy"
            if "سوشيل" in msg_lower or "instagram" in msg_lower or "منشور" in msg_lower:
                return "social_media"
            if "ستوري" in msg_lower or "story" in msg_lower:
                return "story_design"
            if "فيديو" in msg_lower or "أنيميشن" in msg_lower:
                return "video_animation"
            if "seo" in msg_lower or "مدونة" in msg_lower:
                return "seo_blog"
            if "عرض تقديمي" in msg_lower or "presentation" in msg_lower:
                return "presentation"
            return "create_content"

        if domain == "business":
            if "فكرة" in msg_lower or "idea" in msg_lower:
                return "analyze_idea"
            if "سوق" in msg_lower or "market" in msg_lower or "منافس" in msg_lower:
                return "market_research"
            if "جدوى" in msg_lower or "feasibility" in msg_lower:
                return "feasibility_study"
            if "خطة عمل" in msg_lower or "business plan" in msg_lower:
                return "business_plan"
            if "pitch" in msg_lower or "مستثمر" in msg_lower:
                return "pitch_deck"
            if "ممول" in msg_lower or "funding" in msg_lower:
                return "find_funding"
            if "تسويق" in msg_lower or "marketing" in msg_lower:
                return "marketing_plan"
            return "business_analysis"

        if domain == "site_control":
            if "seo" in msg_lower:
                return "seo_optimize"
            if "أداء" in msg_lower or "سرعة" in msg_lower or "performance" in msg_lower:
                return "performance_optimize"
            return "site_build_modify"

        if domain == "tools":
            if "انشر" in msg_lower or "deploy" in msg_lower:
                return "deploy"
            if "اختبر" in msg_lower or "test" in msg_lower:
                return "sandbox_test"
            return "execute_command"

        return "chat"

    def get_stats(self) -> dict:
        """إحصائيات التوجيه"""
        if not self._history:
            return {"total_routes": 0}

        domain_counts = {}
        for route in self._history:
            domain_counts[route.domain] = domain_counts.get(route.domain, 0) + 1

        return {
            "total_routes": len(self._history),
            "domain_distribution": domain_counts,
            "avg_confidence": round(sum(r.confidence for r in self._history) / len(self._history), 3),
        }
