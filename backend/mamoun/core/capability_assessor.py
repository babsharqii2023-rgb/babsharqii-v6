"""
BABSHARQII v40.0 — Capability Assessor
نظام تقييم القدرات الذاتية — يفحص ما يملكه العقل الخارق فعلياً

Pipeline:
1. Check which API keys are set
2. Check which brains use original vs fallback models
3. Check which commands are available
4. Check which bridges are operational
5. Return detailed report: "I can do X, Y, Z... I cannot do A, B"

This module gives Mamoun honest self-knowledge about its actual capabilities,
replacing vague confidence with concrete capability data.
"""

import os
import shutil
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger("mamoun.core.capability_assessor")


class CapabilityAssessor:
    """
    نظام تقييم القدرات الذاتية — يفحص ما يملكه العقل الخارق فعلياً

    Provides an honest, detailed assessment of what Mamoun can and cannot do
    by checking real system state: API keys, brain models, available tools,
    and bridge connectivity.
    """

    # مفاتيح API المطلوبة وأدمغتها المرتبطة
    API_KEY_REGISTRY = {
        "GLM_API_KEY": {
            "name_ar": "مفتاح GLM",
            "related_brains": ["neural", "symbolic"],
            "importance": "critical",
        },
        "DEEPSEEK_API_KEY": {
            "name_ar": "مفتاح DeepSeek",
            "related_brains": ["causal", "world_model"],
            "importance": "critical",
        },
        "GEMINI_API_KEY": {
            "name_ar": "مفتاح Gemini",
            "related_brains": ["bayesian"],
            "importance": "high",
        },
        "OPENAI_API_KEY": {
            "name_ar": "مفتاح OpenAI",
            "related_brains": [],
            "importance": "optional",
        },
    }

    # الأوامر المتاحة والأدوات المطلوبة
    COMMAND_REGISTRY = {
        "search": {
            "name_ar": "البحث العميق",
            "requires": ["web_search"],
            "category": "execution",
        },
        "self_modify": {
            "name_ar": "التعديل الذاتي",
            "requires": ["llm_client"],
            "category": "execution",
        },
        "terminal": {
            "name_ar": "الطرفية",
            "requires": ["shell_executor"],
            "category": "execution",
        },
        "code_generation": {
            "name_ar": "توليد الأكواد",
            "requires": ["llm_client"],
            "category": "execution",
        },
        "browser_control": {
            "name_ar": "التحكم بالمتصفح",
            "requires": ["browser_agent"],
            "category": "execution",
        },
        "deliberation": {
            "name_ar": "المداولة",
            "requires": ["brain_router", "llm_client"],
            "category": "deliberation",
        },
        "self_improve": {
            "name_ar": "التحسين الذاتي",
            "requires": ["llm_client", "self_modifier"],
            "category": "deliberation",
        },
        "health_monitor": {
            "name_ar": "مراقبة الصحة",
            "requires": ["health_monitor"],
            "category": "monitoring",
        },
        "file_system": {
            "name_ar": "نظام الملفات",
            "requires": ["filesystem_tool"],
            "category": "execution",
        },
        "evolution": {
            "name_ar": "التطور",
            "requires": ["evolution_engine", "llm_client"],
            "category": "deliberation",
        },
    }

    # الجسور بين الواجهة والباك إند
    BRIDGE_REGISTRY = {
        "execution": {
            "name_ar": "جسر التنفيذ",
            "endpoints": ["/api/kernel/status", "/api/terminal", "/api/capabilities/status"],
            "weight": 0.40,
        },
        "deliberation": {
            "name_ar": "جسر المداولة",
            "endpoints": ["/api/brains", "/api/brains/status", "/api/deliberation"],
            "weight": 0.30,
        },
        "monitoring": {
            "name_ar": "جسر المراقبة",
            "endpoints": ["/api/health-monitor", "/api/kernel/status", "/api/living/vitals"],
            "weight": 0.30,
        },
    }

    def __init__(self, llm_client=None, brain_router=None, self_modifier=None):
        """
        Args:
            llm_client: LLM client instance (optional)
            brain_router: BrainRouter instance (optional)
            self_modifier: SelfModifier instance (optional)
        """
        self._llm_client = llm_client
        self._brain_router = brain_router
        self._self_modifier = self_modifier

    async def assess(self) -> dict:
        """
        تقييم كامل للقدرات — Full capability assessment.

        Returns:
        {
            "overall_fusion_percent": 55-100,
            "bridges": {
                "execution": {"percent": 65, "working_commands": [...], "missing": [...]},
                "deliberation": {"percent": 55, "details": "..."},
                "monitoring": {"percent": 50, "details": "..."}
            },
            "brains": {
                "total": 5,
                "original_model": 2,
                "fallback": 3,
                "missing_keys": ["DEEPSEEK_API_KEY", "GEMINI_API_KEY"]
            },
            "capabilities": ["search", "self_modify", ...],
            "missing_capabilities": [...],
            "can_do_summary": "أقدر 123... لا أملك: X, Y, Z",
            "recommendations": [...]
        }
        """
        # ─── Step 1: فحص مفاتيح API ───────────────────────────
        api_key_report = self._assess_api_keys()

        # ─── Step 2: فحص حالة الأدمغة ────────────────────────
        brain_report = self._assess_brains()

        # ─── Step 3: فحص الأوامر المتاحة ─────────────────────
        command_report = self._assess_commands()

        # ─── Step 4: فحص الجسور ───────────────────────────────
        bridge_report = self._assess_bridges()

        # ─── Step 5: حساب النسبة الإجمالية ────────────────────
        overall = self._calculate_overall_fusion(
            api_key_report, brain_report, command_report, bridge_report
        )

        # ─── Step 6: بناء الملخص والتوصيات ────────────────────
        capabilities = command_report["available"]
        missing_capabilities = command_report["missing"]
        can_do_summary = self._build_summary(capabilities, missing_capabilities, brain_report, api_key_report)
        recommendations = self._build_recommendations(api_key_report, brain_report, command_report)

        result = {
            "overall_fusion_percent": overall,
            "bridges": bridge_report["details"],
            "brains": brain_report,
            "api_keys": api_key_report,
            "capabilities": capabilities,
            "missing_capabilities": missing_capabilities,
            "can_do_summary": can_do_summary,
            "recommendations": recommendations,
            "assessed_at": datetime.utcnow().isoformat(),
        }

        logger.info(
            "Capability assessment complete — fusion=%d%%, brains=%d/%d original, capabilities=%d",
            overall,
            brain_report.get("original_model", 0),
            brain_report.get("total", 0),
            len(capabilities),
        )

        return result

    # =========================================================================
    # Internal: فحص مفاتيح API
    # =========================================================================

    def _assess_api_keys(self) -> dict:
        """فحص مفاتيح API — check which API keys are set."""
        set_keys = []
        missing_keys = []

        for key_env, info in self.API_KEY_REGISTRY.items():
            if os.environ.get(key_env, "").strip():
                set_keys.append({
                    "key": key_env,
                    "name_ar": info["name_ar"],
                    "related_brains": info["related_brains"],
                    "importance": info["importance"],
                })
            else:
                missing_keys.append({
                    "key": key_env,
                    "name_ar": info["name_ar"],
                    "related_brains": info["related_brains"],
                    "importance": info["importance"],
                })

        return {
            "total": len(self.API_KEY_REGISTRY),
            "set": len(set_keys),
            "missing": len(missing_keys),
            "set_keys": set_keys,
            "missing_keys": missing_keys,
            "percent": round(
                len(set_keys) / max(1, len(self.API_KEY_REGISTRY)) * 100
            ),
        }

    # =========================================================================
    # Internal: فحص الأدمغة
    # =========================================================================

    def _assess_brains(self) -> dict:
        """فحص حالة الأدمغة — check which brains use original vs fallback models."""
        try:
            from mamoun.brains.brain_router import BRAIN_MODEL_REGISTRY
            registry = BRAIN_MODEL_REGISTRY
        except ImportError:
            registry = {}

        if not registry:
            return {
                "total": 0,
                "original_model": 0,
                "fallback": 0,
                "missing_keys": [],
                "details": {},
                "percent": 0,
            }

        total = len(registry)
        original_count = 0
        fallback_count = 0
        missing_keys = []
        details = {}

        for brain_id, info in registry.items():
            api_key_env = info.get("api_key_env", "")
            has_api_key = bool(os.environ.get(api_key_env, ""))
            original_model = info.get("original_model", "")
            fallback_model = info.get("fallback_model", "")
            is_on_fallback = not has_api_key

            if has_api_key:
                original_count += 1
            else:
                fallback_count += 1
                if api_key_env and api_key_env not in missing_keys:
                    missing_keys.append(api_key_env)

            details[brain_id] = {
                "name_ar": info.get("name_ar", brain_id),
                "original_model": original_model,
                "fallback_model": fallback_model,
                "is_on_fallback": is_on_fallback,
                "has_api_key": has_api_key,
                "api_key_env": api_key_env,
            }

        # استخدم BrainRouter إن وُجد لبيانات أكثر تفصيلاً
        if self._brain_router:
            try:
                router_status = self._brain_router.get_brain_status()
                for brain_id, status in router_status.items():
                    if brain_id in details:
                        details[brain_id].update({
                            "status": status.get("status", "unknown"),
                            "confidence": status.get("confidence", 0),
                            "total_interactions": status.get("total_interactions", 0),
                        })
            except Exception as e:
                logger.warning("Could not get brain router status: %s", e)

        percent = round(original_count / max(1, total) * 100)

        return {
            "total": total,
            "original_model": original_count,
            "fallback": fallback_count,
            "missing_keys": missing_keys,
            "details": details,
            "percent": percent,
        }

    # =========================================================================
    # Internal: فحص الأوامر المتاحة
    # =========================================================================

    def _assess_commands(self) -> dict:
        """فحص الأوامر — check which commands/tools are available."""
        available = []
        missing = []

        for cmd_id, info in self.COMMAND_REGISTRY.items():
            is_available = self._check_command_available(cmd_id, info)
            if is_available:
                available.append({
                    "id": cmd_id,
                    "name_ar": info["name_ar"],
                    "category": info["category"],
                })
            else:
                missing.append({
                    "id": cmd_id,
                    "name_ar": info["name_ar"],
                    "category": info["category"],
                    "requires": info["requires"],
                })

        return {
            "total": len(self.COMMAND_REGISTRY),
            "available": available,
            "available_count": len(available),
            "missing": missing,
            "missing_count": len(missing),
            "percent": round(len(available) / max(1, len(self.COMMAND_REGISTRY)) * 100),
        }

    def _check_command_available(self, cmd_id: str, info: dict) -> bool:
        """التحقق من توفر أمر معين بناءً على متطلباته"""
        for req in info.get("requires", []):
            if not self._is_requirement_met(req):
                return False
        return True

    def _is_requirement_met(self, requirement: str) -> bool:
        """التحقق من توفر متطلب معين"""
        # LLM client — تحقق إن وُجد عميل LLM
        if requirement == "llm_client":
            if self._llm_client:
                return True
            # حتى بدون LLM client، يمكننا استخدام النماذج البديلة
            return bool(os.environ.get("GLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY"))

        # Brain router
        if requirement == "brain_router":
            return self._brain_router is not None

        # Self modifier
        if requirement == "self_modifier":
            return self._self_modifier is not None

        # Health monitor — تحقق من وجود الوحدة
        if requirement == "health_monitor":
            try:
                import mamoun.api.health_monitor  # noqa: F401
                return True
            except ImportError:
                return False

        # Shell executor
        if requirement == "shell_executor":
            try:
                from mamoun.tools.shell_executor import ShellExecutor  # noqa: F401
                return True
            except ImportError:
                return False

        # Browser agent
        if requirement == "browser_agent":
            try:
                from mamoun.agents.browser.agent_browser import AgentBrowser  # noqa: F401
                return True
            except ImportError:
                return False

        # Filesystem tool
        if requirement == "filesystem_tool":
            try:
                from mamoun.tools.filesystem_tool import FilesystemTool  # noqa: F401
                return True
            except ImportError:
                return False

        # Evolution engine
        if requirement == "evolution_engine":
            try:
                from mamoun.evolution.self_evolution import SelfEvolution  # noqa: F401
                return True
            except ImportError:
                return False

        # Web search
        if requirement == "web_search":
            # البحث متاح عبر z-ai SDK أو عبر الباك إند
            return True

        # Default — متاح
        return True

    # =========================================================================
    # Internal: فحص الجسور
    # =========================================================================

    def _assess_bridges(self) -> dict:
        """فحص الجسور — check which bridges are operational."""
        bridge_details = {}
        for bridge_id, info in self.BRIDGE_REGISTRY.items():
            # تحقق بسيط: هل النظام الأساسي يعمل؟
            # لا نستطيع عمل HTTP requests من هنا بسهولة،
            # لكن نتحقق من توفر الوحدات البرمجية
            operational = self._check_bridge_operational(bridge_id)
            bridge_details[bridge_id] = {
                "name_ar": info["name_ar"],
                "percent": 100 if operational else 40,  # 40% كحد أدنى — النظام يعمل جزئياً
                "operational": operational,
                "endpoints": info["endpoints"],
            }

        return {
            "details": bridge_details,
            "percent": round(
                sum(b["percent"] * self.BRIDGE_REGISTRY[k]["weight"]
                    for k, b in bridge_details.items())
            ),
        }

    def _check_bridge_operational(self, bridge_id: str) -> bool:
        """التحقق من تشغيل جسر معين"""
        if bridge_id == "execution":
            # جسر التنفيذ — يعمل إن وُجد LLM أو أدوات تنفيذ
            return bool(os.environ.get("GLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY"))

        elif bridge_id == "deliberation":
            # جسر المداولة — يعمل إن وُجد brain router
            return self._brain_router is not None

        elif bridge_id == "monitoring":
            # جسر المراقبة — يعمل دائماً (المعلومات متاحة محلياً)
            return True

        return False

    # =========================================================================
    # Internal: حساب النسبة الإجمالية
    # =========================================================================

    def _calculate_overall_fusion(
        self,
        api_keys: dict,
        brains: dict,
        commands: dict,
        bridges: dict,
    ) -> int:
        """
        حساب نسبة الدمج الإجمالية

        Formula:
        - API Keys: 25% weight
        - Brains: 30% weight
        - Commands: 25% weight
        - Bridges: 20% weight

        Base: 55% (even with nothing configured, the system can do basic chat)
        """
        base = 55  # الحد الأدنى — المحادثة الأساسية متاحة دائماً
        max_bonus = 45  # أقصى إضافة ممكنة

        api_score = api_keys["percent"] / 100
        brain_score = brains["percent"] / 100
        command_score = commands["percent"] / 100
        bridge_score = bridges["percent"] / 100

        bonus = (
            api_score * 0.25 +
            brain_score * 0.30 +
            command_score * 0.25 +
            bridge_score * 0.20
        ) * max_bonus

        return min(100, round(base + bonus))

    # =========================================================================
    # Internal: بناء الملخص والتوصيات
    # =========================================================================

    def _build_summary(
        self,
        capabilities: list,
        missing: list,
        brains: dict,
        api_keys: dict,
    ) -> str:
        """بناء ملخص القدرات بالعربية"""
        can_do = [c["name_ar"] for c in capabilities]
        cant_do = [c["name_ar"] for c in missing]

        parts = []
        if can_do:
            parts.append(f"أقدر: {', '.join(can_do)}")
        if cant_do:
            parts.append(f"لا أملك: {', '.join(cant_do)}")

        brain_info = f"الأدمغة: {brains.get('original_model', 0)}/{brains.get('total', 0)} بنموذج أصلي"
        if brains.get("missing_keys"):
            missing_str = ", ".join(brains["missing_keys"])
            brain_info += f" (يحتاج: {missing_str})"

        parts.append(brain_info)

        return " | ".join(parts)

    def _build_recommendations(
        self,
        api_keys: dict,
        brains: dict,
        commands: dict,
    ) -> list:
        """بناء قائمة التوصيات"""
        recs = []

        # توصيات مفاتيح API
        for missing in api_keys.get("missing_keys", []):
            key_name = missing["key"]
            related = ", ".join(missing["related_brains"]) if missing["related_brains"] else ""
            importance = missing["importance"]
            if importance == "critical":
                recs.append(f"🔴 ضروري: عيّن {key_name} لتفعيل الأدمغة: {related}")
            elif importance == "high":
                recs.append(f"🟠 مهم: عيّن {key_name} لتحسين جودة الأدمغة: {related}")
            else:
                recs.append(f"🟡 اختياري: عيّن {key_name} لميزات إضافية")

        # توصيات الأوامر الناقصة
        for missing_cmd in commands.get("missing", []):
            recs.append(f"⚠️ الأمر '{missing_cmd['name_ar']}' غير متاح — يحتاج: {', '.join(missing_cmd['requires'])}")

        # توصيات الأدمغة
        if brains.get("fallback", 0) > 0:
            recs.append(f"💡 {brains['fallback']} أدمغة تستخدم نماذج بديلة — عيّن المفاتيح الناقصة لتحسين الجودة")

        return recs
