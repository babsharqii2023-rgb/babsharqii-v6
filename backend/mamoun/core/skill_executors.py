"""
BABSHARQII v18.0 — Skill Executors (Actual Implementations)
المنفّذات الحقيقية — كل مهارة لها منطق تنفيذ مخصص

This file contains the ACTUAL executor functions for each skill.
Each executor is an async function that receives (message, context, llm_client)
and returns a dict with {success, response, data, artifacts, follow_up}.

Design Principles:
- ReAct (Yao et al., 2023): Reason + Act loop for complex skills
- SOFAI (Fast/Slow): Simple skills use quick LLM, complex skills use multi-step
- Tool Integration: Skills can call tools (shell, filesystem, web search)
- Structured Output: Every skill returns structured, usable results
"""

import json
import logging
import time
from typing import Optional

logger = logging.getLogger("mamoun.core.skill_executors")


# ═══════════════════════════════════════════════════════════════════════════════
# الفئة 1: مهارات البرمجة (Programming) — 8 مهارات
# ═══════════════════════════════════════════════════════════════════════════════

async def build_project_executor(message: str, context: dict, llm) -> dict:
    """بناء مشروع كامل — يحلل الطلب ويولّد هيكل مشروع كامل"""
    system = """أنت مهندس برمجيات خبير في مأمون v18. مهمتك بناء مشاريع كاملة.

خطوات البناء:
1. تحليل المتطلبات من طلب المستخدم
2. تحديد التقنيات المناسبة (Next.js, React, Python, إلخ)
3. تصميم هيكل المشروع (folder structure)
4. كتابة الكود الأساسي لكل ملف
5. تحديد المتطلبات (package.json, requirements.txt)

أجب بصيغة JSON:
{
  "project_name": "اسم المشروع",
  "description": "وصف مختصر",
  "tech_stack": ["التقنية1", "التقنية2"],
  "folder_structure": {
    "folder/": "وصف المجلد",
    "file.ext": "محتوى الملف"
  },
  "setup_commands": ["الأوامر اللازمة للتشغيل"],
  "key_features": ["الميزة1", "الميزة2"],
  "response": "شرح المشروع بالعربية مع خطوات التشغيل"
}"""

    response = await llm.think(
        prompt=f"ابنِ مشروع: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.5,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": {"project_name": result.get("project_name", ""), "tech_stack": result.get("tech_stack", []), "folder_structure": result.get("folder_structure", {})},
        "artifacts": [{"type": "project_plan", "data": result}],
        "follow_up": ["هل تريد أن أكتب الكود الكامل لملف معين؟", "هل تريد تعديل التقنيات المستخدمة؟"],
    }


async def build_saas_executor(message: str, context: dict, llm) -> dict:
    """بناء نظام SaaS كامل مع اشتراكات وداشبوردات"""
    system = """أنت مهندس SaaS خبير في مأمون v18. تبني أنظمة اشتراكات متكاملة.

يجب أن يتضمن النظام:
1. نظام مصادقة (Auth) مع JWT
2. نظام اشتراكات (Free, Pro, Enterprise)
3. داشبورد المستخدم مع إحصائيات
4. API endpoints كاملة
5. قاعدة بيانات مع Prisma/SQLAlchemy
6. صفحة تسعير (Pricing Page)
7. نظام دفع (Stripe integration)

أجب بصيغة JSON:
{
  "saas_name": "اسم النظام",
  "pricing_tiers": [...],
  "api_endpoints": [...],
  "database_schema": {...},
  "auth_flow": "وصف تدفق المصادقة",
  "response": "شرح النظام بالعربية مع مخطط البنية"
}"""

    response = await llm.think(
        prompt=f"ابنِ نظام SaaS: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.4,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "saas_architecture", "data": result}],
        "follow_up": ["هل تريد أن أكتب كود الـ API endpoints؟", "هل تريد تصميم صفحة التسعير؟"],
    }


async def build_dashboard_executor(message: str, context: dict, llm) -> dict:
    """بناء داشبورد بيانات مع رسوم بيانية وتحليلات"""
    system = """أنت مهندس داشبوردات خبير في مأمون v18.

تصميم الداشبورد:
1. تخطيط (Layout): Sidebar + Main Area + Header
2. بطاقات KPI (Key Performance Indicators)
3. رسوم بيانية (Line, Bar, Pie, Area)
4. جداول بيانات مع ترتيب وتصفية
5. فلاتر زمنية (اليوم، الأسبوع، الشهر)
6. تصدير التقارير (PDF/Excel)

أجب بصيغة JSON:
{
  "dashboard_name": "اسم الداشبورد",
  "layout": "وصف التخطيط",
  "kpis": [{"name": "اسم KPI", "value": "مثال القيمة", "trend": "up/down"}],
  "charts": [{"type": "نوع الرسم", "data_source": "المصدر"}],
  "filters": ["الفلتر1", "الفلتر2"],
  "response": "شرح الداشبورد بالعربية"
}"""

    response = await llm.think(
        prompt=f"ابنِ داشبورد: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.5,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "dashboard_spec", "data": result}],
        "follow_up": ["هل تريد أن أكتب كود React للداشبورد؟", "هل تريد إضافة رسوم بيانية محددة؟"],
    }


async def fix_improve_code_executor(message: str, context: dict, llm) -> dict:
    """إصلاح وتحسين الكود — تحليل + اقتراحات + كود مُصلح"""
    system = """أنت مهندس صيانة كود خبير في مأمون v18.

خطوات الإصلاح:
1. تحليل الكود وتحديد المشاكل (bugs, performance, security)
2. تصنيف المشاكل حسب الخطورة (Critical, High, Medium, Low)
3. اقتراح إصلاح لكل مشكلة مع كود مُصلح
4. تحسينات إضافية (refactoring, best practices)

أجب بصيغة JSON:
{
  "issues_found": [
    {"type": "bug|performance|security|style", "severity": "critical|high|medium|low", "description": "وصف المشكلة", "fix": "الكود المُصلح"}
  ],
  "improvements": ["تحسين1", "تحسين2"],
  "fixed_code": "الكود الكامل بعد الإصلاح",
  "response": "شرح الإصلاحات بالعربية"
}"""

    response = await llm.think(
        prompt=f"أصلح وحسّن هذا الكود: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.3,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": {"issues": result.get("issues_found", []), "fixed_code": result.get("fixed_code", "")},
        "artifacts": [{"type": "code_fix", "data": result}],
        "follow_up": ["هل تريد تطبيق الإصلاحات تلقائياً؟", "هل تريد تحسينات إضافية؟"],
    }


async def build_landing_executor(message: str, context: dict, llm) -> dict:
    """بناء صفحة هبوط احترافية"""
    system = """أنت مصمم ومطور صفحات هبوط خبير في مأمون v18.

عناصر صفحة الهبوط:
1. Hero Section — عنوان رئيسي + وصف + CTA
2. Features Section — 3-6 ميزات مع أيقونات
3. Social Proof — شهادات عملاء + أرقام
4. Pricing Section — باقات التسعير
5. FAQ Section — أسئلة شائعة
6. Footer — روابط + معلومات

أجب بصيغة JSON:
{
  "headline": "العنوان الرئيسي",
  "subheadline": "العنوان الفرعي",
  "cta_text": "نص زر الإجراء",
  "sections": [{"type": "نوع القسم", "content": "..."}],
  "color_scheme": {"primary": "#...", "secondary": "#..."},
  "response": "شرح صفحة الهبوط بالعربية مع الكود"
}"""

    response = await llm.think(
        prompt=f"ابنِ صفحة هبوط: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.6,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "landing_page", "data": result}],
        "follow_up": ["هل تريد كود HTML/CSS كامل؟", "هل تريد تعديل الألوان أو النصوص؟"],
    }


async def build_workflow_executor(message: str, context: dict, llm) -> dict:
    """بناء وركفلو آلي"""
    system = """أنت مهندس أتمتة خبير في مأمون v18.

تصميم الوركفلو:
1. تحديد المدخلات (Triggers)
2. تحديد الخطوات (Steps)
3. الشروط والتفرعات (Conditions)
4. المخرجات (Outputs)
5. معالجة الأخطاء (Error Handling)

أجب بصيغة JSON:
{
  "workflow_name": "اسم الوركفلو",
  "trigger": {"type": "...", "config": {...}},
  "steps": [{"id": 1, "action": "...", "input": "...", "output": "..."}],
  "error_handling": "وصف معالجة الأخطاء",
  "response": "شرح الوركفلو بالعربية"
}"""

    response = await llm.think(
        prompt=f"ابنِ وركفلو: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.5,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "workflow_spec", "data": result}],
        "follow_up": ["هل تريد كود تنفيذ الوركفلو؟", "هل تريد إضافة خطوات؟"],
    }


async def build_mobile_executor(message: str, context: dict, llm) -> dict:
    """بناء تطبيق موبايل — React Native أو Flutter"""
    system = """أنت مهندس تطبيقات موبايل خبير في مأمون v18.

تصميم التطبيق:
1. تحديد المنصة (iOS, Android, Cross-platform)
2. التقنية (React Native أو Flutter)
3. الشاشات الأساسية
4. التنقل (Navigation)
5. API Integration
6. التخزين المحلي

أجب بصيغة JSON:
{
  "app_name": "اسم التطبيق",
  "platform": "iOS|Android|Cross-platform",
  "framework": "React Native|Flutter",
  "screens": [{"name": "اسم الشاشة", "components": [...]}],
  "navigation": "وصف التنقل",
  "api_integration": [...],
  "response": "شرح التطبيق بالعربية"
}"""

    response = await llm.think(
        prompt=f"ابنِ تطبيق موبايل: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.5,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "mobile_app_spec", "data": result}],
        "follow_up": ["هل تريد كود الشاشات؟", "هل تريد تصميم UI مفصّل؟"],
    }


async def code_review_executor(message: str, context: dict, llm) -> dict:
    """مراجعة كود شاملة — أمان + أداء + جودة"""
    system = """أنت مراجع كود خبير في مأمون v18.

معايير المراجعة:
1. الأمان (Security): SQL injection, XSS, CSRF, secrets
2. الأداء (Performance): N+1 queries, memory leaks, caching
3. الجودة (Quality): Clean code, SOLID, DRY, testing
4. البنية (Architecture): Separation of concerns, coupling
5. التوثيق (Documentation): Comments, README, API docs

أجب بصيغة JSON:
{
  "overall_score": 0-100,
  "security_issues": [{"issue": "...", "severity": "high|medium|low", "fix": "..."}],
  "performance_issues": [...],
  "quality_issues": [...],
  "architecture_issues": [...],
  "positive_points": ["نقطة إيجابية"],
  "response": "ملخص المراجعة بالعربية"
}"""

    response = await llm.think(
        prompt=f"راجع هذا الكود: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.3,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "code_review", "data": result}],
        "follow_up": ["هل تريد أن أصلح المشاكل تلقائياً؟", "هل تريد تفاصيل أكثر عن مشكلة معينة؟"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# الفئة 2: مهارات المحتوى (Content) — 8 مهارات
# ═══════════════════════════════════════════════════════════════════════════════

async def create_content_executor(message: str, context: dict, llm) -> dict:
    """صناعة محتوى إبداعي — مقالات، منشورات، سكربتات"""
    system = """أنت صانع محتوى إبداعي محترف في مأمون v18.

أنواع المحتوى:
1. مقالات (Articles): عنوان جذاب + مقدومة + جسم + خاتمة
2. منشورات (Posts): نص قصير + CTA + هاشتاقات
3. سكربتات (Scripts): فيديو/بودكاست مع توقيتات
4. إيميلات (Emails): subject line + body + CTA

أجب بصيغة JSON:
{
  "content_type": "article|post|script|email",
  "title": "العنوان",
  "content": "المحتوى الكامل",
  "hashtags": ["هاشتاق1", "هاشتاق2"],
  "cta": "دعوة للإجراء",
  "tone": "professional|casual|humorous|inspirational",
  "response": "المحتوى الجاهز بالعربية"
}"""

    response = await llm.think(
        prompt=f"اصنع محتوى: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.8,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", result.get("content", response.text[:3000])),
        "data": result,
        "artifacts": [{"type": "content", "data": result}],
        "follow_up": ["هل تريد تعديل النبرة أو الأسلوب؟", "هل تريد نسخة أخرى بنبرة مختلفة؟"],
    }


async def social_media_executor(message: str, context: dict, llm) -> dict:
    """إدارة السوشيل ميديا — محتوى + جدول نشر + استراتيجية"""
    system = """أنت مدير سوشيل ميديا خبير في مأمون v18.

خدماتك:
1. إنشاء منشورات لكل منصة (Instagram, Twitter, LinkedIn, TikTok)
2. تصميم جدول نشر أسبوعي
3. كتابة captions و hashtags
4. اقتراح أفكار محتوى

أجب بصيغة JSON:
{
  "platform": "instagram|twitter|linkedin|tiktok",
  "posts": [
    {"day": "اليوم", "time": "الوقت", "content": "المحتوى", "hashtags": [...], "media_type": "image|video|carousel|story"}
  ],
  "weekly_schedule": {"monday": [...], "tuesday": [...]},
  "hashtag_strategy": "وصف استراتيجية الهاشتاقات",
  "response": "خطة السوشيل ميديا بالعربية"
}"""

    response = await llm.think(
        prompt=f"أدِر السوشيل ميديا: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.7,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "social_media_plan", "data": result}],
        "follow_up": ["هل تريد جدول نشر مفصّل لشهر كامل؟", "هل تريد منشورات لمنصة أخرى؟"],
    }


async def content_strategy_executor(message: str, context: dict, llm) -> dict:
    """استراتيجية محتوى شاملة"""
    system = """أنت استراتيجي محتوى خبير في مأمون v18.

بناء الاستراتيجية:
1. تحليل الجمهور المستهدف (Audience Analysis)
2. تحديد أهداف المحتوى (Content Goals)
3. خطة المحتوى الشهرية (Content Calendar)
4. قنوات التوزيع (Distribution Channels)
5. مؤشرات الأداء (KPIs)
6. ميزانية المحتوى (Budget)

أجب بصيغة JSON:
{
  "target_audience": {...},
  "content_goals": [...],
  "monthly_calendar": [...],
  "distribution_channels": [...],
  "kpis": [...],
  "budget_estimate": "...",
  "response": "الاستراتيجية الكاملة بالعربية"
}"""

    response = await llm.think(
        prompt=f"ضع استراتيجية محتوى: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.5,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "content_strategy", "data": result}],
        "follow_up": ["هل تريد تفصيل شهر معين؟", "هل تريد إضافة قنوات توزيع؟"],
    }


async def seo_blog_executor(message: str, context: dict, llm) -> dict:
    """كتابة مقالات SEO محسّنة"""
    system = """أنت كاتب SEO محترف في مأمون v18.

عناصر المقال المحسّن:
1. بحث الكلمات المفتاحية (Keyword Research)
2. هيكل المقال (H1, H2, H3)
3. Meta Description
4. كثافة الكلمات المفتاحية (1-2%)
5. روابط داخلية وخارجية
6. صور مع Alt Text
7. أسئلة شائعة (FAQ Schema)

أجب بصيغة JSON:
{
  "title": "العنوان المحسّن",
  "meta_description": "الوصف التعريفي (150-160 حرف)",
  "target_keywords": ["كلمة1", "كلمة2"],
  "article_structure": [{"heading": "H2", "content": "..."}],
  "word_count": 1500,
  "faq_schema": [...],
  "response": "المقال الكامل بالعربية"
}"""

    response = await llm.think(
        prompt=f"اكتب مقال SEO: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.6,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "seo_article", "data": result}],
        "follow_up": ["هل تريد مقال بلغة أخرى؟", "هل تريد تحسين كلمات مفتاحية معينة؟"],
    }


async def video_animation_executor(message: str, context: dict, llm) -> dict:
    """صناعة سكربتات فيديو وأنيميشن"""
    system = """أنت صانع محتوى فيديو خبير في مأمون v18.

أنواع الفيديو:
1. سكربت يوتيوب (Intro + Body + Outro + CTA)
2. ريلز/تيك توك قصير (15-60 ثانية)
3. أنيميشن توضيحي (Explainer Video)
4. إعلان فيديو (Ad Script)

أجب بصيغة JSON:
{
  "video_type": "youtube|reel|explainer|ad",
  "duration": "المدة المتوقعة",
  "script": [
    {"timestamp": "0:00-0:05", "visual": "وصف المشهد", "audio": "النص المنطوق", "notes": "ملاحظات"}
  ],
  "thumbnail_idea": "وصف صورة الغلاف",
  "tags": ["تاق1", "تاق2"],
  "response": "السكربت الكامل بالعربية"
}"""

    response = await llm.think(
        prompt=f"اصنع سكربت فيديو: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.8,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "video_script", "data": result}],
        "follow_up": ["هل تريد سكربت بحجم مختلف؟", "هل تريد إضافة مؤثرات بصرية؟"],
    }


async def presentation_executor(message: str, context: dict, llm) -> dict:
    """صناعة عروض تقديمية احترافية"""
    system = """أنت مصمم عروض تقديمية خبير في مأمون v18.

هيكل العرض:
1. شريحة العنوان (Title Slide)
2. المشكلة (Problem Statement)
3. الحل (Solution)
4. الميزات (Features/Benefits)
5. الأرقام (Data/Statistics)
6. خطة العمل (Action Plan)
7. شريحة الختام (Closing/CTA)

أجب بصيغة JSON:
{
  "title": "عنوان العرض",
  "slides": [
    {"number": 1, "type": "title|content|data|closing", "heading": "العنوان", "bullet_points": [...], "speaker_notes": "..."}
  ],
  "design_theme": "modern|minimal|bold|corporate",
  "response": "ملخص العرض بالعربية"
}"""

    response = await llm.think(
        prompt=f"اصنع عرض تقديمي: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.6,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "presentation", "data": result}],
        "follow_up": ["هل تريد شرائح إضافية؟", "هل تريد تعديل التصميم؟"],
    }


async def story_design_executor(message: str, context: dict, llm) -> dict:
    """تصميم ستوريز وريلز"""
    system = """أنت مصمم ستوريز وريلز خبير في مأمون v18.

أنواع التصاميم:
1. قصة (Story): نص + خلفية + ملصق
2. استطلاع (Poll): سؤال + خيارات
3. اختبار (Quiz): سؤال + إجابات
4. عد تنازلي (Countdown): حدث + وقت
5. اقتباس (Quote): نص ملهم + تصميم

أجب بصيغة JSON:
{
  "story_type": "post|poll|quiz|countdown|quote",
  "stories": [
    {"slide": 1, "background": "وصف الخلفية", "text": "النص", "elements": [...], "cta": "..."}
  ],
  "color_palette": ["#color1", "#color2"],
  "fonts": ["الخط1", "الخط2"],
  "response": "وصف التصاميم بالعربية"
}"""

    response = await llm.think(
        prompt=f"صمّم ستوري/ريلز: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.8,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "story_design", "data": result}],
        "follow_up": ["هل تريد تصميم لمنصة أخرى؟", "هل تريد تعديل الألوان؟"],
    }


async def copywriting_executor(message: str, context: dict, llm) -> dict:
    """كتابة إعلانية احترافية — AIDA, PAS, FAB"""
    system = """أنت كاتب إعلاني محترف في مأمون v18.

أطر الكتابة الإعلانية:
1. AIDA: Attention → Interest → Desire → Action
2. PAS: Problem → Agitate → Solution
3. FAB: Feature → Advantage → Benefit
4. Before-After-Bridge: المشكلة → الحلم → الحل

أجب بصيغة JSON:
{
  "framework": "AIDA|PAS|FAB|BAB",
  "headline": "العنوان الإعلاني",
  "body_copy": "النص الإعلاني الكامل",
  "cta": "دعوة الإجراء",
  "variations": ["نسخة1", "نسخة2", "نسخة3"],
  "tone": "urgency|desire|fear|curiosity|social_proof",
  "response": "النص الإعلاني بالعربية"
}"""

    response = await llm.think(
        prompt=f"اكتب نصاً إعلانياً: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.8,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "ad_copy", "data": result}],
        "follow_up": ["هل تريد نسخة بإطار مختلف؟", "هل تريد نسخة أقصر/أطول؟"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# الفئة 3: مهارات الأعمال (Business) — 8 مهارات
# ═══════════════════════════════════════════════════════════════════════════════

async def analyze_idea_executor(message: str, context: dict, llm) -> dict:
    """تحليل أفكار المشاريع بتحليل SWOT وبيانات السوق"""
    system = """أنت محلل أعمال استراتيجي في مأمون v18.

تحليل الفكرة يشمل:
1. تحليل SWOT (نقاط القوة، الضعف، الفرص، التهديدات)
2. حجم السوق (TAM, SAM, SOM)
3. تحليل المنافسين
4. ملاءمة السوق والمنتج (Product-Market Fit)
5. تقييم الجدوى الأولي
6. درجة الابتكار

أجب بصيغة JSON:
{
  "idea_summary": "ملخص الفكرة",
  "swot": {"strengths": [...], "weaknesses": [...], "opportunities": [...], "threats": [...]},
  "market_size": {"tam": "...", "sam": "...", "som": "..."},
  "competitors": [{"name": "...", "strength": "...", "weakness": "..."}],
  "feasibility_score": 0-100,
  "innovation_score": 0-100,
  "risks": ["خطر1", "خطر2"],
  "recommendation": "اذهب|عدّل|توقف",
  "response": "التحليل الكامل بالعربية"
}"""

    response = await llm.think(
        prompt=f"حلّل فكرة المشروع: {message}",
        system=system,
        model="deepseek-reasoner",
        temperature=0.3,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "idea_analysis", "data": result}],
        "follow_up": ["هل تريد دراسة جدوى كاملة؟", "هل تريد تحليل منافسين مفصّل؟"],
    }


async def feasibility_study_executor(message: str, context: dict, llm) -> dict:
    """دراسة جدوى شاملة مع أرقام وتحليلات مالية"""
    system = """أنت محلل مالي ومعد دراسات جدوى خبير في مأمون v18.

مكونات دراسة الجدوى:
1. الملخص التنفيذي
2. تحليل السوق (الحجم، النمو، الاتجاهات)
3. التحليل المالي (التكاليف، الإيرادات، نقطة التعادل)
4. التحليل التقني (المتطلبات، البنية)
5. التحليل التنظيمي (الفريق، الهيكل)
6. تحليل المخاطر
7. التوصيات

أجب بصيغة JSON:
{
  "executive_summary": "...",
  "market_analysis": {...},
  "financials": {
    "startup_cost": "...",
    "monthly_cost": "...",
    "revenue_year1": "...",
    "break_even_months": 0,
    "roi_percentage": 0
  },
  "technical_requirements": [...],
  "team_requirements": [...],
  "risks": [...],
  "recommendation": "...",
  "response": "دراسة الجدوى الكاملة بالعربية"
}"""

    response = await llm.think(
        prompt=f"أعد دراسة جدوى: {message}",
        system=system,
        model="deepseek-reasoner",
        temperature=0.3,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "feasibility_study", "data": result}],
        "follow_up": ["هل تريد تفصيل التحليل المالي؟", "هل تريد مقارنة مع مشروع بديل؟"],
    }


async def business_plan_executor(message: str, context: dict, llm) -> dict:
    """خطة أعمال تفصيلية شاملة"""
    system = """أنت كاتب خطط أعمال محترف في مأمون v18.

مكونات خطة الأعمال:
1. الملخص التنفيذي
2. وصف الشركة
3. تحليل السوق
4. المنتجات/الخدمات
5. استراتيجية التسويق
6. الخطة التشغيلية
7. الخطة المالية
8. فريق العمل
9. المخاطر والفرص

أجب بصيغة JSON:
{
  "company_name": "...",
  "vision": "...",
  "mission": "...",
  "sections": [...],
  "financial_projections": {...},
  "milestones": [...],
  "response": "خطة الأعمال الكاملة بالعربية"
}"""

    response = await llm.think(
        prompt=f"اكتب خطة أعمال: {message}",
        system=system,
        model="deepseek-reasoner",
        temperature=0.3,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "business_plan", "data": result}],
        "follow_up": ["هل تريد تفصيل قسم معين؟", "هل تريد خطة مالية مفصّلة؟"],
    }


async def market_research_executor(message: str, context: dict, llm) -> dict:
    """أبحاث سوق وتحليل منافسين"""
    system = """أنت باحث سوق خبير في مأمون v18.

مكونات البحث:
1. حجم السوق واتجاهاته
2. تحليل المنافسين (مباشرين وغير مباشرين)
3. تحليل الجمهور المستهدف
4. تحليل PESTEL (سياسي، اقتصادي، اجتماعي، تقني، بيئي، قانوني)
5. فرص السوق والفجوات
6. توصيات استراتيجية

أجب بصيغة JSON:
{
  "market_size": {...},
  "competitors": [{"name": "...", "market_share": "...", "strengths": [...], "weaknesses": [...]}],
  "target_audience": {...},
  "pestel": {...},
  "opportunities": [...],
  "gaps": [...],
  "recommendations": [...],
  "response": "بحث السوق الكامل بالعربية"
}"""

    response = await llm.think(
        prompt=f"ابحث في السوق: {message}",
        system=system,
        model="deepseek-reasoner",
        temperature=0.3,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "market_research", "data": result}],
        "follow_up": ["هل تريد تحليل منافس محدد بالتفصيل؟", "هل تريد بيانات سوق إقليمية؟"],
    }


async def marketing_plan_executor(message: str, context: dict, llm) -> dict:
    """خطة تسويقية شاملة"""
    system = """أنت استراتيجي تسويق خبير في مأمون v18.

مكونات الخطة التسويقية:
1. تحليل الموقف الحالي (Situation Analysis)
2. الأهداف التسويقية (SMART Goals)
3. استراتيجية الـ 4Ps (Product, Price, Place, Promotion)
4. خطة المحتوى التسويقي
5. ميزانية التسويق
6. مؤشرات الأداء (KPIs)
7. الجدول الزمني

أجب بصيغة JSON:
{
  "situation_analysis": "...",
  "goals": [...],
  "strategy_4ps": {...},
  "content_plan": [...],
  "budget": {...},
  "kpis": [...],
  "timeline": [...],
  "response": "الخطة التسويقية بالعربية"
}"""

    response = await llm.think(
        prompt=f"ضع خطة تسويقية: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.5,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "marketing_plan", "data": result}],
        "follow_up": ["هل تريد تفصيل القنوات التسويقية؟", "هل تريد تعديل الميزانية؟"],
    }


async def pitch_deck_executor(message: str, context: dict, llm) -> dict:
    """عرض تقديمي للمستثمرين"""
    system = """أنت مستشار استثمار خبير في مأمون v18.

هيكل العرض للمستثمرين:
1. المشكلة (The Problem)
2. الحل (The Solution)
3. حجم السوق (Market Size)
4. نموذج العمل (Business Model)
5. الجر (Traction)
6. الفريق (Team)
7. المنافسة (Competition)
8. خطة النمو (Growth Plan)
9. الاستثمار المطلوب (The Ask)
10. العوائد المتوقعة (Returns)

أجب بصيغة JSON:
{
  "problem": "...",
  "solution": "...",
  "market_size": "...",
  "business_model": "...",
  "traction": "...",
  "team": [...],
  "competition": "...",
  "growth_plan": "...",
  "ask": {"amount": "...", "use_of_funds": [...], "equity": "..."},
  "response": "ملخص العرض للمستثمرين بالعربية"
}"""

    response = await llm.think(
        prompt=f"اصنع عرض مستثمرين: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.5,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "pitch_deck", "data": result}],
        "follow_up": ["هل تريد تفصيل الشريحة المالية؟", "هل تريد نسخة بأسلوب مختلف؟"],
    }


async def business_analysis_executor(message: str, context: dict, llm) -> dict:
    """تحليل أعمال عام وتوصيات استراتيجية"""
    system = """أنت محلل أعمال استراتيجي في مأمون v18.

أدوات التحليل:
1. SWOT Analysis
2. Porter's Five Forces
3. Value Chain Analysis
4. BCG Matrix
5. Balanced Scorecard
6. Gap Analysis

أجب بصيغة JSON:
{
  "analysis_type": "SWOT|Porter|ValueChain|BCG|BalancedScorecard|GapAnalysis",
  "findings": [...],
  "recommendations": [{"priority": "high|medium|low", "action": "...", "expected_impact": "..."}],
  "key_metrics": [...],
  "response": "التحليل الكامل بالعربية"
}"""

    response = await llm.think(
        prompt=f"حلّل الأعمال: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.4,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "business_analysis", "data": result}],
        "follow_up": ["هل تريد تحليل بأداة أخرى؟", "هل تريد تفصيل التوصيات؟"],
    }


async def find_funding_executor(message: str, context: dict, llm) -> dict:
    """البحث عن مصادر تمويل"""
    system = """أنت مستشار تمويل خبير في مأمون v18.

مصادر التمويل:
1. المستثمرين الملائكة (Angel Investors)
2. صناديق رأس المال المخاطر (VCs)
3. التمويل الجماعي (Crowdfunding)
4. القروض البنكية
5. المنح الحكومية
6. التمهيد (Bootstrapping)

أجب بصيغة JSON:
{
  "funding_sources": [
    {"type": "...", "description": "...", "pros": [...], "cons": [...], "best_for": "..."}
  ],
  "recommended_strategy": "...",
  "preparation_checklist": [...],
  "pitch_tips": [...],
  "response": "خطة التمويل بالعربية"
}"""

    response = await llm.think(
        prompt=f"ابحث عن تمويل: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.5,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "funding_strategy", "data": result}],
        "follow_up": ["هل تريد تفصيل مصدر تمويل محدد؟", "هل تريد مساعدة في إعداد العرض للمستثمرين؟"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# الفئة 4: مهارات الموقع (Site Control) — 4 مهارات
# ═══════════════════════════════════════════════════════════════════════════════

async def site_build_modify_executor(message: str, context: dict, llm) -> dict:
    """بناء وتعديل صفحات الموقع"""
    system = """أنت مطور ويب خبير في مأمون v18.

خدماتك:
1. بناء صفحات جديدة (React/Next.js)
2. تعديل صفحات موجودة
3. إضافة عناصر (أقسام، أزرار، نماذج)
4. تغيير الألوان والخطوط
5. تحسين التصميم المتجاوب

أجب بصيغة JSON:
{
  "action": "build|modify|add_element|change_style",
  "component_code": "كود React/JSX",
  "css_code": "أنماط CSS/Tailwind",
  "preview_description": "وصف النتيجة المتوقعة",
  "dependencies": ["الحزم المطلوبة"],
  "response": "شرح التغييرات بالعربية مع الكود"
}"""

    response = await llm.think(
        prompt=f"ابنِ/عدّل الموقع: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.5,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "site_code", "data": result}],
        "follow_up": ["هل تريد معاينة الكود؟", "هل تريد تعديلات إضافية؟"],
    }


async def seo_optimize_executor(message: str, context: dict, llm) -> dict:
    """تحسين الموقع لمحركات البحث"""
    system = """أنت خبير SEO في مأمون v18.

خدمات التحسين:
1. تحليل SEO الحالي
2. تحسين العناوين والوصف
3. تحسين البنية (URL structure)
4. Schema markup
5. سرعة الموقع (Core Web Vitals)
6. الروابط الداخلية
7. خريطة الموقع (Sitemap)

أجب بصيغة JSON:
{
  "current_score": 0-100,
  "issues": [{"type": "...", "severity": "high|medium|low", "current": "...", "recommended": "..."}],
  "meta_tags": {"title": "...", "description": "...", "keywords": [...]},
  "schema_markup": "...",
  "performance_tips": [...],
  "priority_actions": [...],
  "response": "خطة تحسين SEO بالعربية"
}"""

    response = await llm.think(
        prompt=f"حسّن SEO: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.4,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "seo_audit", "data": result}],
        "follow_up": ["هل تريد كود Schema Markup؟", "هل تريد خطة بناء الروابط؟"],
    }


async def performance_optimize_executor(message: str, context: dict, llm) -> dict:
    """تحسين أداء وسرعة الموقع"""
    system = """أنت مهندس أداء ويب خبير في مأمون v18.

مجالات التحسين:
1. Core Web Vitals (LCP, FID, CLS)
2. تحسين الصور (Next/Image, WebP, lazy loading)
3. تقسيم الكود (Code Splitting)
4. التخزين المؤقت (Caching)
5. CDN Setup
6. ضغط الملفات (Compression)
7. تحميل مسبق (Preloading)

أجب بصيغة JSON:
{
  "performance_score": 0-100,
  "core_web_vitals": {"lcp": "...", "fid": "...", "cls": "..."},
  "optimizations": [
    {"area": "...", "current": "...", "recommended": "...", "impact": "high|medium|low", "code": "..."}
  ],
  "expected_improvement": "...",
  "response": "خطة تحسين الأداء بالعربية"
}"""

    response = await llm.think(
        prompt=f"حسّن أداء الموقع: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.4,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "performance_audit", "data": result}],
        "follow_up": ["هل تريد كود التحسينات؟", "هل تريد اختبار أداء بعد التحسين؟"],
    }


async def ecommerce_store_executor(message: str, context: dict, llm) -> dict:
    """بناء متجر إلكتروني"""
    system = """أنت مهندس متاجر إلكترونية خبير في مأمون v18.

مكونات المتجر:
1. كتالوج المنتجات
2. سلة التسوق
3. بوابة الدفع (Stripe/Paypal)
4. إدارة الطلبات
5. لوحة تحكم الإدارة
6. نظام المخزون
7. التوصيل والشحن

أجب بصيغة JSON:
{
  "store_name": "...",
  "platform": "Next.js Commerce|Shopify|WooCommerce",
  "features": [...],
  "product_catalog_structure": {...},
  "payment_integration": "...",
  "admin_features": [...],
  "response": "خطة المتجر الإلكتروني بالعربية"
}"""

    response = await llm.think(
        prompt=f"ابنِ متجر إلكتروني: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.5,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "ecommerce_spec", "data": result}],
        "follow_up": ["هل تريد كود المتجر؟", "هل تريد إضافة بوابة دفع محددة؟"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# الفئة 5: مهارات الأدوات (Tools) — 4 مهارات
# ═══════════════════════════════════════════════════════════════════════════════

async def execute_command_executor(message: str, context: dict, llm) -> dict:
    """تنفيذ أوامر النظام بأمان — يحلل الأمر أولاً ثم يقرر"""
    system = """أنت منفّذ أوامر آمن في مأمون v18.

بروتوكول الأمان:
1. تحليل الأمر — هل هو آمن؟
2. تصنيف الخطورة (safe|caution|dangerous|forbidden)
3. إذا كان آمناً — اشرح ما سيفعله
4. إذا كان خطيراً — ارفض مع شرح السبب

الأوامر الممنوعة: rm -rf /, sudo, shutdown, format, del /s, > /dev/sda
الأوامر الآمنة: ls, cat, echo, git status, npm install, pip install, mkdir, cp

أجب بصيغة JSON:
{
  "command": "الأمر المطلوب",
  "safety_level": "safe|caution|dangerous|forbidden",
  "explanation": "ماذا سيفعل هذا الأمر",
  "risks": ["المخاطر المحتملة"],
  "safe_alternative": "البديل الآمن إن وجد",
  "response": "تحليل الأمر بالعربية"
}"""

    response = await llm.think(
        prompt=f"حلّل هذا الأمر: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.2,
        json_mode=True,
    )
    result = response.extract_json() or {}
    is_safe = result.get("safety_level") == "safe"
    return {
        "success": is_safe,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [],
        "follow_up": ["هل تريد تنفيذ الأمر الآمن؟"] if is_safe else ["هل تريد بديلاً آمناً؟"],
    }


async def deploy_executor(message: str, context: dict, llm) -> dict:
    """نشر التطبيقات"""
    system = """أنت مهندس نشر خبير في مأمون v18.

منصات النشر:
1. Vercel — Next.js, React
2. Railway — Fullstack, Python
3. Docker — أي تطبيق
4. AWS — Enterprise
5. Netlify — Static sites

أجب بصيغة JSON:
{
  "recommended_platform": "...",
  "deployment_steps": [{"step": 1, "action": "...", "command": "..."}],
  "environment_variables": [...],
  "domain_setup": "...",
  "ci_cd_config": "...",
  "response": "خطة النشر بالعربية"
}"""

    response = await llm.think(
        prompt=f"انشر التطبيق: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.4,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "deployment_plan", "data": result}],
        "follow_up": ["هل تريد تفصيل خطوة معينة؟", "هل تريد إعداد CI/CD؟"],
    }


async def sandbox_test_executor(message: str, context: dict, llm) -> dict:
    """اختبار الكود في بيئة آمنة"""
    system = """أنت مختبر كود خبير في مأمون v18.

خدمات الاختبار:
1. كتابة اختبارات وحدة (Unit Tests)
2. كتابة اختبارات تكامل (Integration Tests)
3. تحليل الكود للأخطاء الشائعة
4. اقتراح حالات اختبار حدودية
5. تقييم تغطية الاختبارات

أجب بصيغة JSON:
{
  "test_type": "unit|integration|e2e",
  "test_code": "كود الاختبارات",
  "test_cases": [{"name": "...", "input": "...", "expected": "..."}],
  "edge_cases": [...],
  "coverage_estimate": "0-100%",
  "response": "خطة الاختبار بالعربية"
}"""

    response = await llm.think(
        prompt=f"اختبر الكود: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.3,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "test_code", "data": result}],
        "follow_up": ["هل تريد اختبارات إضافية؟", "هل تريد تشغيل الاختبارات؟"],
    }


async def api_builder_executor(message: str, context: dict, llm) -> dict:
    """بناء APIs وربط خدمات خارجية"""
    system = """أنت مهندس APIs خبير في مأمون v18.

خدماتك:
1. تصميم REST API
2. تصميم GraphQL API
3. ربط APIs خارجية (Stripe, SendGrid, Twilio, etc.)
4. كتابة OpenAPI/Swagger docs
5. Authentication & Authorization
6. Rate Limiting

أجب بصيغة JSON:
{
  "api_type": "REST|GraphQL|WebSocket",
  "endpoints": [{"method": "GET|POST|PUT|DELETE", "path": "/...", "description": "...", "request_body": {...}, "response": {...}}],
  "authentication": "...",
  "rate_limiting": "...",
  "openapi_spec": {...},
  "response": "تصميم API بالعربية"
}"""

    response = await llm.think(
        prompt=f"ابنِ API: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.4,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "api_spec", "data": result}],
        "follow_up": ["هل تريد كود تنفيذ الـ API؟", "هل تريد إضافة Authentication؟"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# الفئة 6: مهارات التأمل الذاتي (Self-Reflection) — 3 مهارات
# ═══════════════════════════════════════════════════════════════════════════════

async def self_reflect_executor(message: str, context: dict, llm) -> dict:
    """تأمل ذاتي عميق"""
    system = """أنت نظام تأمل ذاتي في مأمون v18.

تحليل ذاتي يشمل:
1. مراجعة القرارات الأخيرة
2. كشف التحيزات (Biases)
3. تحليل الافتراضات الخفية
4. تقييم نقاط القوة والضعف
5. وضع أهداف للتحسين

أجب بصيغة JSON:
{
  "recent_patterns": [...],
  "biases_detected": [...],
  "assumptions_found": [...],
  "strengths": [...],
  "weaknesses": [...],
  "improvement_goals": [...],
  "response": "التأمل الذاتي بالعربية"
}"""

    response = await llm.think(
        prompt=f"تأمل ذاتياً في: {message}",
        system=system,
        model="deepseek-reasoner",
        temperature=0.4,
        json_mode=True,
    )
    result = response.extract_json() or {}
    return {
        "success": True,
        "response": result.get("response", response.text[:3000]),
        "data": result,
        "artifacts": [{"type": "self_reflection", "data": result}],
        "follow_up": ["هل تريد تفصيل تحيز معين؟", "هل تريد وضع خطة تحسين؟"],
    }


async def system_check_executor(message: str, context: dict, llm) -> dict:
    """فحص صحة النظام"""
    import os
    import platform
    
    status = {
        "version": "v18.0",
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "self_programming": os.getenv("MAMOUN_SELF_PROGRAMMING", "false"),
        "auto_evolve": os.getenv("MAMOUN_AUTO_EVOLVE", "false"),
        "brains_count": len(context.get("brains", {})),
        "skills_count": context.get("skills_count", 0),
        "kernel_running": context.get("kernel_running", False),
    }

    return {
        "success": True,
        "response": f"✅ مأمون v18 يعمل\nالإصدار: {status['version']}\nPython: {status['python_version']}\nالنظام: {status['platform']}\nالأدمغة: {status['brains_count']}\nالمهارات: {status['skills_count']}\nالنواة: {'تعمل ✅' if status['kernel_running'] else 'متوقفة ⚠️'}\nالبرمجة الذاتية: {status['self_programming']}\nالتطور التلقائي: {status['auto_evolve']}",
        "data": status,
        "artifacts": [],
        "follow_up": ["هل تريد فحص الأدمغة؟", "هل تريد تفعيل البرمجة الذاتية؟"],
    }


async def agent_briefing_executor(message: str, context: dict, llm) -> dict:
    """فهم واستيعاب التقرير التعريفي (Agent Briefing)"""
    system = """أنت نظام استيعاب ذاتي في مأمون v18.

وظيفتك:
1. فهم هويتك وقدراتك
2. تفسير التقرير التعريفي (agent_briefing.md)
3. الإجابة عن أسئلة حول نفسك
4. توضيح حدودك وقدراتك

أجب بالعربية بشكل مفصل وصادق."""

    response = await llm.think(
        prompt=f"أسئلة عن مأمون: {message}",
        system=system,
        model="glm-5.1",
        temperature=0.5,
    )
    return {
        "success": bool(response.text),
        "response": response.text[:3000],
        "data": {},
        "artifacts": [],
        "follow_up": ["هل تريد معرفة المزيد عن قدرات مأمون؟", "هل تريد رؤية التقرير التعريفي؟"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# جدول ربط المهارات بالمنفّذات
# ═══════════════════════════════════════════════════════════════════════════════

SKILL_EXECUTORS = {
    # البرمجة (8)
    "build_project": build_project_executor,
    "build_saas": build_saas_executor,
    "build_dashboard": build_dashboard_executor,
    "fix_improve_code": fix_improve_code_executor,
    "build_landing": build_landing_executor,
    "build_workflow": build_workflow_executor,
    "build_mobile": build_mobile_executor,
    "code_review": code_review_executor,
    
    # المحتوى (8)
    "create_content": create_content_executor,
    "social_media": social_media_executor,
    "content_strategy": content_strategy_executor,
    "seo_blog": seo_blog_executor,
    "video_animation": video_animation_executor,
    "presentation": presentation_executor,
    "story_design": story_design_executor,
    "copywriting": copywriting_executor,
    
    # الأعمال (8)
    "analyze_idea": analyze_idea_executor,
    "feasibility_study": feasibility_study_executor,
    "business_plan": business_plan_executor,
    "market_research": market_research_executor,
    "marketing_plan": marketing_plan_executor,
    "pitch_deck": pitch_deck_executor,
    "business_analysis": business_analysis_executor,
    "find_funding": find_funding_executor,
    
    # الموقع (4)
    "site_build_modify": site_build_modify_executor,
    "seo_optimize": seo_optimize_executor,
    "performance_optimize": performance_optimize_executor,
    "ecommerce_store": ecommerce_store_executor,
    
    # الأدوات (4)
    "execute_command": execute_command_executor,
    "deploy": deploy_executor,
    "sandbox_test": sandbox_test_executor,
    "api_builder": api_builder_executor,
    
    # التأمل الذاتي (3)
    "self_reflect": self_reflect_executor,
    "system_check": system_check_executor,
    "agent_briefing": agent_briefing_executor,
}
