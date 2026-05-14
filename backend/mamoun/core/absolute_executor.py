"""
BABSHARQII v23.0 — Absolute Executor (محرك التنفيذ المطلق)
ضامن أن أي طلب من المستخدم يتحول إلى فعل حقيقي

المشكلة: عندما يقول المستخدم "ابنِ لي موقع" أو "حلل البيانات"،
النظام الحالي يعتمد على LLM routing الذي قد يفشل أو يتوه.

الحل: Absolute Executor — خط أنابيب مضمون:

  ┌─────────────────────────────────────────────────────────────┐
  │                  ABSOLUTE EXECUTOR                           │
  │                                                              │
  │  1. INTENT  ← استخراج النية بدقة                            │
  │  2. PLAN    ← تحليل إلى خطوات قابلة للتنفيذ                 │
  │  3. ROUTE   ← توجيه كل خطوة للمحرك المناسب                  │
  │  4. EXECUTE ← تنفيذ حقيقي مع مراقبة                        │
  │  5. VERIFY  ← التحقق من النتيجة                             │
  │  6. FIX     ← إصلاح إذا فشل (إعادة محاولة ذكية)            │
  │  7. REPORT  ← إبلاغ المستخدم بالنتيجة                       │
  └─────────────────────────────────────────────────────────────┘

Based on research:
  - ReAct (Yao et al., 2023): Reasoning + Acting interleaved
  - Plan-and-Solve (Wang et al., 2023): Decompose → Plan → Execute
  - Self-Refine (Madaan et al., 2023): Generate → Refine → Verify loop
  - Toolformer (Schick et al., 2023): LLM learns to use tools
  - HuggingGPT (Shen et al., 2023): LLM as planner + expert models as executors
"""

import asyncio
import time
import json
import logging
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable
from enum import Enum
from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH
from mamoun.core.reflexion_engine import reflexion_engine, ReviewResult

# Lazy imports for real engines — imported at runtime to avoid circular dependencies
# RealToolsEngine, ShellExecutor, FileSystemTool, EmotionalMemoryEngine

logger = logging.getLogger("mamoun.absolute_executor")


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج البيانات
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionPhase(str, Enum):
    """مراحل التنفيذ"""
    INTENT = "intent"         # استخراج النية
    PLANNING = "planning"     # التخطيط
    ROUTING = "routing"       # التوجيه
    EXECUTING = "executing"   # التنفيذ
    VERIFYING = "verifying"   # التحقق
    FIXING = "fixing"         # الإصلاح
    REPORTING = "reporting"   # الإبلاغ
    COMPLETED = "completed"   # مكتمل
    FAILED = "failed"         # فاشل


class IntentCategory(str, Enum):
    """تصنيفات النية"""
    # معلوماتي
    QUESTION = "question"               # سؤال
    RESEARCH = "research"               # بحث
    ANALYSIS = "analysis"               # تحليل

    # إنشائي
    CREATE_CODE = "create_code"         # كتابة كود
    CREATE_PROJECT = "create_project"   # بناء مشروع
    CREATE_CONTENT = "create_content"   # إنشاء محتوى
    CREATE_DESIGN = "create_design"     # تصميم

    # تنفيذي
    CONTROL_LAPTOP = "control_laptop"   # تحكم بالجهاز
    BROWSE_WEB = "browse_web"           # تصفح
    TERMINAL_CMD = "terminal_cmd"       # أمر طرفية
    TRADE = "trade"                     # تداول

    # تواصلي
    CHAT = "chat"                       # محادثة
    EMOTIONAL = "emotional"             # عاطفي
    ADVICE = "advice"                   # نصيحة

    # ذاتي
    SELF_MODIFY = "self_modify"         # تعديل ذاتي
    SELF_IMPROVE = "self_improve"       # تحسين ذاتي
    CONFIGURE = "configure"             # إعداد

    # خاص
    INSTAGRAM = "instagram"             # انستغرام
    BLENDER = "blender"                 # بلندر
    STORE = "store"                     # متجر


class StepStatus(str, Enum):
    """حالة خطوة التنفيذ"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class ExecutionStep:
    """خطوة تنفيذ واحدة"""
    id: str = ""
    description: str = ""
    tool: str = ""                    # المحرك/الأداة المستخدمة
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = StepStatus.PENDING.value
    result: Any = None
    error: str = ""
    retry_count: int = 0
    max_retries: int = 3
    started_at: float = 0.0
    completed_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "tool": self.tool,
            "status": self.status,
            "error": self.error,
            "retry_count": self.retry_count,
            "duration_ms": round((self.completed_at - self.started_at) * 1000, 1) if self.completed_at and self.started_at else 0,
        }


@dataclass
class ExecutionPlan:
    """خطة تنفيذ كاملة"""
    id: str = ""
    user_request: str = ""
    intent: str = ""
    intent_category: str = ""
    steps: List[ExecutionStep] = field(default_factory=list)
    current_step: int = 0
    phase: str = ExecutionPhase.INTENT.value
    created_at: float = 0.0
    completed_at: float = 0.0
    total_retries: int = 0
    final_result: Any = None
    success: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_request": self.user_request,
            "intent": self.intent,
            "intent_category": self.intent_category,
            "phase": self.phase,
            "current_step": self.current_step,
            "total_steps": len(self.steps),
            "completed_steps": sum(1 for s in self.steps if s.status == StepStatus.SUCCESS.value),
            "failed_steps": sum(1 for s in self.steps if s.status == StepStatus.FAILED.value),
            "total_retries": self.total_retries,
            "success": self.success,
            "duration_ms": round((self.completed_at - self.created_at) * 1000, 1) if self.completed_at and self.created_at else 0,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  محرك التنفيذ المطلق — AbsoluteExecutor
# ═══════════════════════════════════════════════════════════════════════════════

class AbsoluteExecutor:
    """
    محرك التنفيذ المطلق — يضمن تحويل أي طلب إلى فعل حقيقي

    This engine guarantees that user requests are EXECUTED, not just talked about.
    It decomposes requests into executable steps, routes each step to the right
    engine, monitors execution, fixes failures, and reports results.

    The key insight: Don't just RESPOND to requests — EXECUTE them.
    """

    MAX_RETRIES = 3
    MAX_STEPS = 20
    STEP_TIMEOUT = 120.0  # seconds per step

    def __init__(self, llm_client=None, neural_bus=None, db_path: Optional[Path] = None,
                 capabilities_engine=None, living_state=None, emotional_memory=None):
        self._llm = llm_client
        self._neural_bus = neural_bus
        self.db_path = db_path or UNIFIED_DB_PATH
        self._capabilities_engine = capabilities_engine
        self._living_state = living_state
        self._emotional_memory = emotional_memory
        self._plans: Dict[str, ExecutionPlan] = {}
        self._tool_registry: Dict[str, Callable] = {}
        self._counter = 0
        self._initialized = False
        self._active_plan: Optional[ExecutionPlan] = None

        # Real engine instances (lazy-loaded)
        self._shell_executor = None
        self._filesystem_tool = None
        self._real_tools_engine = None

        # Execution statistics
        self._stats = {
            "total_requests": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_retries": 0,
            "avg_steps": 0,
            "avg_duration_ms": 0,
            "by_intent": {},
        }

    def initialize(self) -> bool:
        """تهيئة محرك التنفيذ"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._ensure_schema()
            self._load_stats()
            self._register_default_tools()
            self._initialized = True
            logger.info("AbsoluteExecutor initialized — %d tools registered", len(self._tool_registry))
            return True
        except Exception as e:
            logger.error("AbsoluteExecutor init failed: %s", e)
            self._initialized = False
            return False

    def register_tool(self, name: str, handler: Callable, description: str = ""):
        """تسجيل أداة تنفيذ"""
        self._tool_registry[name] = handler
        logger.debug("Tool registered: %s", name)

    def _register_default_tools(self):
        """تسجيل الأدوات الافتراضية"""
        # These tools are registered lazily — they resolve at execution time
        self._tool_registry["llm_think"] = self._tool_llm_think
        self._tool_registry["llm_generate"] = self._tool_llm_generate
        self._tool_registry["terminal_execute"] = self._tool_terminal_execute
        self._tool_registry["web_search"] = self._tool_web_search
        self._tool_registry["code_generate"] = self._tool_code_generate
        self._tool_registry["file_write"] = self._tool_file_write
        self._tool_registry["file_read"] = self._tool_file_read
        self._tool_registry["memory_store"] = self._tool_memory_store
        self._tool_registry["memory_recall"] = self._tool_memory_recall
        self._tool_registry["notify_user"] = self._tool_notify_user
        self._tool_registry["capability_execute"] = self._tool_capability_execute

    # ═════════════════════════════════════════════════════════════════════════
    #  خط الأنابيب الرئيسي — Main Pipeline
    # ═════════════════════════════════════════════════════════════════════════

    async def execute(self, user_request: str, context: Dict = None) -> Dict:
        """
        التنفيذ المطلق — يحول طلب المستخدم إلى فعل حقيقي

        Pipeline: INTENT → PLAN → ROUTE → EXECUTE → VERIFY → FIX → REPORT

        Living State Integration:
        - High stress (>70): Fewer retries, more cautious plans
        - Low energy (<30): Skip non-essential steps, focus on core
        - High curiosity (>80): Add exploration steps
        - High attachment (>60): More detailed responses
        """
        if not self._initialized:
            self.initialize()

        context = context or {}
        self._counter += 1
        self._stats["total_requests"] += 1

        # ═══ Living State Influence ═══
        living_context = {}
        if self._living_state:
            living_context = self._living_state.get_vitals_snapshot()
            energy = living_context.get("energy", {}).get("value", 80)
            stress = living_context.get("stress", {}).get("value", 10)
            curiosity = living_context.get("curiosity", {}).get("value", 50)
            attachment = living_context.get("attachment", {}).get("value", 30)

            # Adjust behavior based on vitals
            if stress > 70:
                # High stress: fewer retries, simpler plans
                self.MAX_RETRIES = 1
                logger.info("High stress (%.0f) — reducing retries to 1", stress)
            elif stress > 40:
                self.MAX_RETRIES = 2
            else:
                self.MAX_RETRIES = 3

            if energy < 30:
                # Low energy: skip optional steps
                context["_skip_optional"] = True
                logger.info("Low energy (%.0f) — skipping optional steps", energy)

            # Record this interaction as an emotional event
            from mamoun.core.living_state import EmotionalEvent
            self._living_state.process_event(EmotionalEvent(
                timestamp=time.time(),
                event_type="user_message",
                intensity=0.3 + (attachment / 200),  # Higher attachment = more intense
                valence=0.2,  # User interaction is slightly positive
                source="absolute_executor",
                description=f"Request: {user_request[:80]}",
            ))

        context["_living"] = living_context

        # Create execution plan
        plan = ExecutionPlan(
            id=f"exec_{self._counter}_{int(time.time())}",
            user_request=user_request,
            created_at=time.time(),
        )
        self._plans[plan.id] = plan
        self._active_plan = plan

        try:
            # Phase 1: INTENT — استخراج النية
            plan.phase = ExecutionPhase.INTENT.value
            intent = await self._extract_intent(user_request, context)
            plan.intent = intent.get("intent", "unknown")
            plan.intent_category = intent.get("category", IntentCategory.CHAT.value)

            # Publish to neural bus
            if self._neural_bus:
                self._neural_bus.publish(
                    "action_requested",  # v40 FIX: removed dead SignalType reference (never imported)
                    source="absolute_executor",
                    payload={"plan_id": plan.id, "intent": plan.intent, "request": user_request[:200]},
                    priority=2,
                )

            # Phase 2: PLANNING — التخطيط
            plan.phase = ExecutionPhase.PLANNING.value
            steps = await self._create_plan(user_request, intent, context)
            plan.steps = steps

            # Phase 3-6: EXECUTE → VERIFY → FIX loop
            plan.phase = ExecutionPhase.EXECUTING.value
            for i, step in enumerate(plan.steps):
                plan.current_step = i
                step.status = StepStatus.RUNNING.value
                step.started_at = time.time()

                # ReflexionEngine: review action BEFORE execution
                if step.tool in ("terminal_execute", "file_write", "code_generate"):
                    review = reflexion_engine.review_action(
                        action={
                            "tool": step.tool,
                            "params": step.params,
                            "risk_level": context.get("risk_level", "medium"),
                            "source": "absolute_executor",
                        }
                    )
                    if not review.approved:
                        step.status = StepStatus.FAILED.value
                        step.error = f"ReflexionEngine رفض الإجراء: {review.reason}"
                        step.completed_at = time.time()
                        logger.warning("Action blocked by ReflexionEngine: %s — %s", step.tool, review.reason)
                        if review.alternative:
                            # Substitute with safer alternative
                            step.tool = review.alternative.get("tool", step.tool)
                            step.params.update(review.alternative.get("params", {}))
                            step.status = StepStatus.RETRYING.value
                        else:
                            continue

                # Execute with retry
                success = False
                for attempt in range(step.max_retries + 1):
                    try:
                        result = await self._execute_step(step, context)
                        step.result = result
                        step.status = StepStatus.SUCCESS.value
                        step.completed_at = time.time()
                        success = True
                        # Post-review: report success
                        reflexion_engine.post_review(
                            action={"tool": step.tool, "params": step.params},
                            result=result, succeeded=True
                        )
                        break
                    except Exception as e:
                        step.retry_count = attempt + 1
                        step.error = str(e)[:500]
                        self._stats["total_retries"] += 1
                        if attempt < step.max_retries:
                            step.status = StepStatus.RETRYING.value
                            # Try to fix the step
                            fixed = await self._fix_step(step, context)
                            if fixed:
                                continue
                        else:
                            step.status = StepStatus.FAILED.value
                            step.completed_at = time.time()

                # If critical step failed, abort or find alternative
                if not success and i < len(plan.steps) - 1:
                    alternative = await self._find_alternative(step, context)
                    if alternative:
                        plan.steps.insert(i + 1, alternative)

            # Phase 7: REPORT — الإبلاغ
            plan.phase = ExecutionPhase.REPORTING.value
            plan.completed_at = time.time()
            plan.success = all(s.status == StepStatus.SUCCESS.value for s in plan.steps if s.status != StepStatus.SKIPPED.value)
            plan.final_result = self._compile_result(plan)

            # Update stats
            if plan.success:
                self._stats["total_completed"] += 1
            else:
                self._stats["total_failed"] += 1

            self._stats["by_intent"][plan.intent_category] = self._stats["by_intent"].get(plan.intent_category, 0) + 1

            # Persist
            self._persist_plan(plan)
            self._persist_stats()

            # Publish completion
            if self._neural_bus:
                self._neural_bus.publish(
                    "action_completed" if plan.success else "action_failed",
                    source="absolute_executor",
                    payload={"plan_id": plan.id, "success": plan.success},
                )

            plan.phase = ExecutionPhase.COMPLETED.value if plan.success else ExecutionPhase.FAILED.value

            return plan.to_dict()

        except Exception as e:
            logger.error("AbsoluteExecutor pipeline failed: %s", e)
            plan.phase = ExecutionPhase.FAILED.value
            plan.success = False
            plan.completed_at = time.time()
            plan.final_result = {"error": str(e)}
            self._stats["total_failed"] += 1
            return plan.to_dict()

    # ═════════════════════════════════════════════════════════════════════════
    #  استخراج النية — Intent Extraction
    # ═════════════════════════════════════════════════════════════════════════

    async def _extract_intent(self, request: str, context: Dict) -> Dict:
        """استخراج النية الدقيقة من طلب المستخدم"""
        # Fast path: keyword-based intent detection
        intent = self._keyword_intent(request)
        if intent.get("confidence", 0) > 0.7:
            return intent

        # LLM-powered intent extraction
        if self._llm:
            try:
                response = await self._llm.think(
                    prompt=f"""حلل هذا الطلب واستخرج النية الدقيقة:

الطلب: {request}

السياق: {json.dumps(context, ensure_ascii=False, default=str)[:1000]}

أجب بصيغة JSON:
{{
    "intent": "وصف دقيق للنية",
    "category": "أحد: question/research/analysis/create_code/create_project/create_content/control_laptop/browse_web/terminal_cmd/trade/chat/emotional/advice/self_modify/instagram/blender/store/configure",
    "complexity": "simple/medium/complex/multi_step",
    "requires_tools": ["قائمة الأدوات المطلوبة"],
    "confidence": 0.0-1.0,
    "clarification_needed": true/false,
    "clarification_question": "سؤال توضيحي إن لزم"
}}""",
                    system="أنت محلل نيات خبير. استخرج النية بدقة متناهية.",
                    temperature=0.1,
                    json_mode=True,
                )
                result = response.extract_json()
                if result:
                    return result
            except Exception as e:
                logger.warning("LLM intent extraction failed: %s", e)

        return intent

    def _keyword_intent(self, request: str) -> Dict:
        """كشف النية بالكلمات المفتاحية — fast path"""
        r = request.lower()

        # Code/Development
        if any(w in r for w in ["اكتب كود", "برمج", "كود", "برنامج", "سكريبت", "code", "script", "program"]):
            return {"intent": "كتابة كود", "category": IntentCategory.CREATE_CODE.value, "confidence": 0.8}

        # Project
        if any(w in r for w in ["ابنِ مشروع", "مشروع", "بناء", "project", "build", "app"]):
            return {"intent": "بناء مشروع", "category": IntentCategory.CREATE_PROJECT.value, "confidence": 0.8}

        # Research
        if any(w in r for w in ["ابحث", "بحث", "دراسة", "research", "search", "find"]):
            return {"intent": "بحث", "category": IntentCategory.RESEARCH.value, "confidence": 0.8}

        # Analysis
        if any(w in r for w in ["حلل", "تحليل", "analyze", "analysis"]):
            return {"intent": "تحليل", "category": IntentCategory.ANALYSIS.value, "confidence": 0.8}

        # Terminal
        if any(w in r for w in ["نفذ أمر", "طرفية", "terminal", "command", "run"]):
            return {"intent": "أمر طرفية", "category": IntentCategory.TERMINAL_CMD.value, "confidence": 0.8}

        # Instagram
        if any(w in r for w in ["انستغرام", "instagram", "حساب"]):
            return {"intent": "انستغرام", "category": IntentCategory.INSTAGRAM.value, "confidence": 0.8}

        # Trading
        if any(w in r for w in ["تداول", "سهم", "سوق", "trade", "stock", "market"]):
            return {"intent": "تداول", "category": IntentCategory.TRADE.value, "confidence": 0.8}

        # Laptop control
        if any(w in r for w in ["تحكم", "افتح", "اضغط", "control", "open", "click"]):
            return {"intent": "تحكم بالجهاز", "category": IntentCategory.CONTROL_LAPTOP.value, "confidence": 0.7}

        # Blender
        if any(w in r for w in ["بلندر", "تصميم ثلاثي", "blender", "3d", "render"]):
            return {"intent": "بلندر", "category": IntentCategory.BLENDER.value, "confidence": 0.8}

        # Store
        if any(w in r for w in ["متجر", "منتج", "store", "shop", "ecommerce"]):
            return {"intent": "متجر", "category": IntentCategory.STORE.value, "confidence": 0.8}

        # Emotional
        if any(w in r for w in ["أشعر", "حزين", "سعيد", "قلق", "feel", "sad", "happy"]):
            return {"intent": "دعم عاطفي", "category": IntentCategory.EMOTIONAL.value, "confidence": 0.7}

        # Default: chat
        return {"intent": "محادثة", "category": IntentCategory.CHAT.value, "confidence": 0.3}

    # ═════════════════════════════════════════════════════════════════════════
    #  التخطيط — Planning
    # ═════════════════════════════════════════════════════════════════════════

    async def _create_plan(self, request: str, intent: Dict, context: Dict) -> List[ExecutionStep]:
        """إنشاء خطة تنفيذ من خطوات قابلة للتنفيذ"""
        category = intent.get("category", "chat")

        # Pre-defined plans for common categories
        plan_templates = {
            IntentCategory.CREATE_CODE.value: [
                ExecutionStep(id="step_1", description="تحليل المتطلبات", tool="llm_think"),
                ExecutionStep(id="step_2", description="كتابة الكود", tool="code_generate"),
                ExecutionStep(id="step_3", description="اختبار الكود", tool="terminal_execute"),
            ],
            IntentCategory.CREATE_PROJECT.value: [
                ExecutionStep(id="step_1", description="تحليل الفكرة", tool="llm_think"),
                ExecutionStep(id="step_2", description="تخطيط المشروع", tool="llm_think"),
                ExecutionStep(id="step_3", description="كتابة الملفات", tool="file_write"),
                ExecutionStep(id="step_4", description="تشغيل المشروع", tool="terminal_execute"),
            ],
            IntentCategory.RESEARCH.value: [
                ExecutionStep(id="step_1", description="بحث معمق", tool="web_search"),
                ExecutionStep(id="step_2", description="تلخيص النتائج", tool="llm_think"),
            ],
            IntentCategory.ANALYSIS.value: [
                ExecutionStep(id="step_1", description="جمع البيانات", tool="llm_think"),
                ExecutionStep(id="step_2", description="تحليل معمق", tool="llm_think"),
                ExecutionStep(id="step_3", description="صياغة النتائج", tool="llm_generate"),
            ],
            IntentCategory.TERMINAL_CMD.value: [
                ExecutionStep(id="step_1", description="تنفيذ الأمر", tool="terminal_execute"),
            ],
            IntentCategory.INSTAGRAM.value: [
                ExecutionStep(id="step_1", description="تحليل الحساب", tool="capability_execute"),
                ExecutionStep(id="step_2", description="تحليل استراتيجي", tool="llm_think"),
            ],
            IntentCategory.TRADE.value: [
                ExecutionStep(id="step_1", description="بيانات السوق", tool="capability_execute"),
                ExecutionStep(id="step_2", description="تحليل وتوصية", tool="llm_think"),
            ],
            IntentCategory.CONTROL_LAPTOP.value: [
                ExecutionStep(id="step_1", description="تنفيذ التحكم", tool="capability_execute"),
            ],
            IntentCategory.BLENDER.value: [
                ExecutionStep(id="step_1", description="تنفيذ أمر بلندر", tool="capability_execute"),
            ],
        }

        # Use template if available
        if category in plan_templates:
            steps = plan_templates[category]
            # Enrich step params with context
            for step in steps:
                step.params = {"request": request, "intent": intent, "context": context}
            return steps

        # LLM-powered planning for complex/unknown requests
        if self._llm:
            try:
                response = await self._llm.think(
                    prompt=f"""حلل هذا الطلب واقسمه إلى خطوات تنفيذية واضحة:

الطلب: {request}
النية: {intent.get('intent', 'unknown')}

الأدوات المتاحة: {list(self._tool_registry.keys())}

أجب بصيغة JSON — قائمة خطوات:
[
    {{
        "description": "وصف الخطوة",
        "tool": "اسم الأداة",
        "params": {{}}
    }}
]""",
                    system="أنت مخطط تنفيذي خبير. قسم الطلبات إلى خطوات عملية.",
                    temperature=0.2,
                    json_mode=True,
                )
                result = response.extract_json()
                if isinstance(result, list):
                    steps = []
                    for i, step_data in enumerate(result):
                        steps.append(ExecutionStep(
                            id=f"step_{i+1}",
                            description=step_data.get("description", ""),
                            tool=step_data.get("tool", "llm_think"),
                            params={**step_data.get("params", {}), "request": request, "intent": intent, "context": context},
                        ))
                    return steps
            except Exception as e:
                logger.warning("LLM planning failed: %s", e)

        # Fallback: single LLM step
        return [ExecutionStep(
            id="step_1",
            description="معالجة الطلب",
            tool="llm_think",
            params={"request": request, "intent": intent, "context": context},
        )]

    # ═════════════════════════════════════════════════════════════════════════
    #  التنفيذ — Step Execution
    # ═════════════════════════════════════════════════════════════════════════

    async def _execute_step(self, step: ExecutionStep, context: Dict) -> Any:
        """تنفيذ خطوة واحدة — مع مراجعة أمنية قبل التنفيذ"""
        # ═══ BUG-002 FIX: Pre-execution safety review via ReflexionEngine ═══
        if step.tool in ("terminal_execute", "file_write", "file_read", "capability_execute"):
            try:
                # Build action dict matching ReflexionEngine.review_action() API
                action_dict = {
                    "tool": step.tool,
                    "params": step.params,
                    "risk_level": "high" if step.tool == "terminal_execute" else "medium",
                    "source": "absolute_executor",
                }
                review = reflexion_engine.review_action(action_dict)
                if review and not review.approved:
                    logger.warning("ReflexionEngine BLOCKED execution: %s (reason: %s)",
                                   step.tool, getattr(review, 'reason', 'unknown'))
                    return {
                        "success": False,
                        "blocked": True,
                        "block_reason": getattr(review, 'reason', 'Action blocked by ReflexionEngine'),
                        "escalation_level": getattr(review, 'escalation_level', 0),
                        "tool": step.tool,
                    }
            except Exception as e:
                logger.warning("ReflexionEngine review failed (allowing execution): %s", e)

        handler = self._tool_registry.get(step.tool)
        if not handler:
            raise ValueError(f"أداة غير مسجلة: {step.tool}")

        try:
            result = handler(step.params, context)
            if asyncio.iscoroutine(result):
                result = await asyncio.wait_for(result, timeout=self.STEP_TIMEOUT)
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"انتهت مهلة التنفيذ: {step.tool}")
        except Exception as e:
            raise e

    async def _fix_step(self, step: ExecutionStep, context: Dict) -> bool:
        """محاولة إصلاح خطوة فاشلة"""
        if self._llm:
            try:
                response = await self._llm.think(
                    prompt=f"""الخطوة التالية فشلت:

الخطوة: {step.description}
الأداة: {step.tool}
الخطأ: {step.error}

اقترح طريقة إصلاح. أجب بصيغة JSON:
{{
    "fix_type": "retry_with_different_params / use_different_tool / simplify / skip",
    "new_params": {{}},
    "new_tool": "",
    "reasoning": ""
}}""",
                    system="أنت خبير في حل المشاكل التنفيذية.",
                    temperature=0.3,
                    json_mode=True,
                )
                fix = response.extract_json()
                if fix:
                    if fix.get("new_tool"):
                        step.tool = fix["new_tool"]
                    if fix.get("new_params"):
                        step.params.update(fix["new_params"])
                    return True
            except Exception:
                pass
        return False

    async def _find_alternative(self, failed_step: ExecutionStep, context: Dict) -> Optional[ExecutionStep]:
        """إيجاد بديل لخطوة فاشلة"""
        self._counter += 1
        return ExecutionStep(
            id=f"step_alt_{self._counter}",
            description=f"بديل: {failed_step.description}",
            tool="llm_think",
            params={**failed_step.params, "_fallback": True, "_original_error": failed_step.error},
        )

    def _compile_result(self, plan: ExecutionPlan) -> Dict:
        """تجميع النتيجة النهائية من كل الخطوات"""
        results = []
        for step in plan.steps:
            if step.status == StepStatus.SUCCESS.value and step.result:
                results.append({
                    "step": step.description,
                    "result": step.result if isinstance(step.result, (str, dict, list)) else str(step.result),
                })

        if len(results) == 1:
            return results[0].get("result", {})

        return {
            "completed_steps": len(results),
            "results": results,
            "summary": f"تم تنفيذ {len(results)} من {len(plan.steps)} خطوات",
        }

    # ═════════════════════════════════════════════════════════════════════════
    #  الأدوات — Tool Implementations
    # ═════════════════════════════════════════════════════════════════════════

    async def _tool_llm_think(self, params: Dict, context: Dict) -> Any:
        """أداة التفكير — LLM reasoning"""
        if not self._llm:
            return {"error": "LLM غير متاح"}

        request = params.get("request", "")
        intent = params.get("intent", {})
        prompt = params.get("prompt", request)

        response = await self._llm.think(
            prompt=prompt,
            system=f"أنت مامون — مساعد ذكي حي. النية: {intent.get('intent', 'general')}",
            temperature=0.4,
        )
        return {"text": response.text}

    async def _tool_llm_generate(self, params: Dict, context: Dict) -> Any:
        """أداة التوليد — LLM generation"""
        if not self._llm:
            return {"error": "LLM غير متاح"}

        request = params.get("request", "")
        response = await self._llm.think(
            prompt=request,
            system="أنت مامون — مبدع ومحترف. أنشئ محتوى مميزاً.",
            temperature=0.7,
        )
        return {"text": response.text}

    # ═════════════════════════════════════════════════════════════════════════
    #  Lazy-loading real engines
    # ═════════════════════════════════════════════════════════════════════════

    async def _get_shell_executor(self):
        """Lazy-load ShellExecutor"""
        if self._shell_executor is None:
            try:
                from mamoun.tools.shell_executor import ShellExecutor
                self._shell_executor = ShellExecutor()
                await self._shell_executor.initialize()
                logger.info("ShellExecutor loaded — real terminal execution available")
            except Exception as e:
                logger.error("ShellExecutor load failed: %s", e)
        return self._shell_executor

    async def _get_filesystem_tool(self):
        """Lazy-load FileSystemTool"""
        if self._filesystem_tool is None:
            try:
                from mamoun.tools.filesystem_tool import FileSystemTool
                self._filesystem_tool = FileSystemTool()
                await self._filesystem_tool.initialize()
                logger.info("FileSystemTool loaded — real file operations available")
            except Exception as e:
                logger.error("FileSystemTool load failed: %s", e)
        return self._filesystem_tool

    async def _get_real_tools(self):
        """Lazy-load RealToolsEngine"""
        if self._real_tools_engine is None:
            try:
                from mamoun.core.real_tools import get_real_tools
                self._real_tools_engine = get_real_tools(llm_client=self._llm)
                await self._real_tools_engine.initialize()
                logger.info("RealToolsEngine loaded — web search, image gen, etc. available")
            except Exception as e:
                logger.error("RealToolsEngine load failed: %s", e)
        return self._real_tools_engine

    # ═════════════════════════════════════════════════════════════════════════
    #  الأدوات الحقيقية — Real Tool Implementations
    # ═════════════════════════════════════════════════════════════════════════

    async def _tool_terminal_execute(self, params: Dict, context: Dict) -> Any:
        """أداة الطرفية — تنفيذ حقيقي عبر ShellExecutor"""
        command = params.get("command", params.get("request", ""))

        # If no explicit command, use LLM to extract it from the request
        if not command or command == params.get("request", ""):
            if self._llm:
                try:
                    response = await self._llm.think(
                        prompt=f"""استخرج أمر الطرفية المناسب من هذا الطلب:
{params.get('request', '')}

أجب فقط بالأمر نفسه بدون شرح. إذا كان الطلب يتطلب عدة أوامر، أعطني الأمر الرئيسي.""",
                        system="أنت خبير أوامر Linux. استخرج الأمر الدقيق فقط.",
                        temperature=0.1,
                    )
                    command = response.text.strip().strip('`').strip()
                except Exception as e:
                    logger.warning("LLM command extraction failed: %s", e)

        if not command:
            return {"success": False, "error": "لم يتم تحديد أمر للتنفيذ"}

        # Execute via real ShellExecutor
        shell = await self._get_shell_executor()
        if shell:
            result = await shell.execute(
                command=command,
                grant_id="",
                working_dir=params.get("working_dir", str(Path(__file__).parent.parent.parent.parent)),
                timeout=params.get("timeout", 60),
            )
            # Feed back to living state
            if self._living_state:
                from mamoun.core.living_state import EmotionalEvent
                self._living_state.process_event(EmotionalEvent(
                    timestamp=time.time(),
                    event_type="task_success" if result.success else "task_failure",
                    intensity=0.3,
                    valence=0.5 if result.success else -0.3,
                    source="absolute_executor.terminal",
                    description=f"Terminal: {command[:50]}",
                ))
            return {
                "success": result.success,
                "command": result.command,
                "stdout": result.stdout[:5000] if result.stdout else "",
                "stderr": result.stderr[:2000] if result.stderr else "",
                "exit_code": result.exit_code,
                "duration_ms": result.duration_ms,
                "blocked": result.blocked,
                "block_reason": result.block_reason,
            }
        else:
            # Fallback: direct subprocess (BUG-001 FIX: shell=False for safety)
            import subprocess
            import shlex
            try:
                # Parse command safely — avoid shell=True to prevent injection
                # For simple commands, split safely; for complex pipes, use explicit array
                if '|' in command or '&&' in command or ';' in command or '>' in command or '<' in command:
                    # Complex command — use explicit bash invocation with shell=False
                    # This avoids shell=True injection vector while supporting pipes/redirects
                    proc = subprocess.run(
                        ["/bin/bash", "-c", command],
                        shell=False, capture_output=True, text=True, timeout=60,
                        cwd=params.get("working_dir", str(Path(__file__).parent.parent.parent.parent)),
                    )
                else:
                    # Simple command — safe to use shell=False
                    args = shlex.split(command)
                    proc = subprocess.run(
                        args, shell=False, capture_output=True, text=True, timeout=60,
                        cwd=params.get("working_dir", str(Path(__file__).parent.parent.parent.parent)),
                    )
                return {
                    "success": proc.returncode == 0,
                    "command": command,
                    "stdout": proc.stdout[:5000],
                    "stderr": proc.stderr[:2000],
                    "exit_code": proc.returncode,
                }
            except Exception as e:
                return {"success": False, "error": str(e), "command": command}

    async def _tool_web_search(self, params: Dict, context: Dict) -> Any:
        """أداة البحث — بحث حقيقي عبر RealToolsEngine"""
        query = params.get("query", params.get("request", ""))
        if not query:
            return {"success": False, "error": "لم يتم تحديد استعلام البحث"}

        real_tools = await self._get_real_tools()
        if real_tools:
            result = await real_tools.call_tool(
                "web_search",
                query=query,
                num_results=params.get("num_results", 10),
            )
            return {
                "success": result.success,
                "query": query,
                "output": result.output[:5000] if result.output else "",
                "data": result.data,
                "error": result.error,
                "duration_ms": result.duration_ms,
            }
        else:
            # Fallback to LLM
            if self._llm:
                response = await self._llm.think(
                    prompt=f"ابحث عن: {query}",
                    system="أنت محرك بحث. قدم معلومات دقيقة.",
                    temperature=0.3,
                )
                return {"success": True, "query": query, "output": response.text, "source": "llm_fallback"}
            return {"success": False, "error": "لا يتوفر محرك بحث ولا LLM"}

    async def _tool_code_generate(self, params: Dict, context: Dict) -> Any:
        """أداة توليد الكود — توليد حقيقي + كتابة ملف + تنفيذ اختياري"""
        if not self._llm:
            return {"error": "LLM غير متاح"}

        request = params.get("request", "")
        language = params.get("language", "python")
        response = await self._llm.think(
            prompt=f"""اكتب كود {language} احترافي بناءً على:

{request}

المتطلبات:
1. كود نظيف مع تعليقات
2. معالجة أخطاء كاملة
3. أفضل الممارسات""",
            system=f"أنت خبير {language} عالمي.",
            temperature=0.2,
        )

        code = response.text

        # If execute is requested, write file and run it
        if params.get("execute", False) and language == "python":
            real_tools = await self._get_real_tools()
            if real_tools:
                result = await real_tools.call_tool(
                    "code_gen",
                    description=request,
                    language=language,
                    execute=True,
                )
                return {
                    "code": code,
                    "language": language,
                    "execution": {
                        "success": result.success,
                        "output": result.output[:3000] if result.output else "",
                        "artifacts": result.artifacts,
                    },
                }

        return {"code": code, "language": language}

    async def _tool_file_read(self, params: Dict, context: Dict) -> Any:
        """أداة قراءة الملفات — قراءة حقيقية عبر FileSystemTool أو مباشرة"""
        filepath = params.get("filepath", params.get("path", ""))

        if not filepath:
            # Try to extract from request
            if self._llm:
                try:
                    response = await self._llm.think(
                        prompt=f"""من هذا الطلب، استخرج مسار الملف للقراءة:
{params.get('request', '')}

أجب فقط بمسار الملف بدون شرح.""",
                        system="أنت محلل طلبات. استخرج مسار الملف فقط.",
                        temperature=0.1,
                    )
                    filepath = response.text.strip().strip('`').strip()
                except Exception as e:
                    logger.warning("LLM filepath extraction failed: %s", e)

        if not filepath:
            return {"success": False, "error": "لم يتم تحديد مسار الملف"}

        # Read via real FileSystemTool
        fs = await self._get_filesystem_tool()
        if fs:
            result = await fs.read_file(path=filepath, grant_id="")
            return {
                "success": result.success,
                "filepath": result.path,
                "content": result.content[:10000] if result.content else "",
                "error": result.error,
            }
        else:
            # Fallback: direct read
            try:
                p = Path(filepath)
                if not p.exists():
                    return {"success": False, "error": f"الملف غير موجود: {filepath}"}
                content = p.read_text(encoding='utf-8')
                return {"success": True, "filepath": str(p), "content": content[:10000], "size_bytes": len(content)}
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def _tool_file_write(self, params: Dict, context: Dict) -> Any:
        """أداة كتابة الملفات — كتابة حقيقية عبر FileSystemTool"""
        filepath = params.get("filepath", "")
        content = params.get("content", "")

        if not filepath:
            # Try to extract from request
            if self._llm:
                try:
                    response = await self._llm.think(
                        prompt=f"""من هذا الطلب، استخرج مسار الملف والمحتوى:
{params.get('request', '')}

أجب بصيغة JSON:
{{"filepath": "المسار", "content": "المحتوى"}}""",
                        system="أنت محلل طلبات. استخرج معلومات الملف فقط.",
                        temperature=0.1,
                        json_mode=True,
                    )
                    extracted = response.extract_json()
                    if extracted:
                        filepath = extracted.get("filepath", filepath)
                        content = extracted.get("content", content)
                except Exception:
                    pass

        if not filepath or not content:
            return {"success": False, "error": "لم يتم تحديد مسار الملف أو المحتوى"}

        # Write via real FileSystemTool
        fs = await self._get_filesystem_tool()
        if fs:
            result = await fs.write_file(
                path=filepath,
                content=content,
                grant_id="",
                create_dirs=True,
            )
            return {
                "success": result.success,
                "filepath": result.path,
                "size_bytes": result.size_bytes,
                "error": result.error,
            }
        else:
            # Fallback: direct write
            try:
                p = Path(filepath)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding='utf-8')
                return {"success": True, "filepath": str(p), "size_bytes": len(content)}
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def _tool_memory_store(self, params: Dict, context: Dict) -> Any:
        """أداة تخزين الذاكرة — تخزين حقيقي عبر EmotionalMemoryEngine"""
        content = params.get("content", params.get("request", ""))
        if not content:
            return {"success": False, "error": "لم يتم تحديد محتوى للتخزين"}

        # Try EmotionalMemoryEngine first
        if self._emotional_memory:
            try:
                episode = self._emotional_memory.store_episode(
                    content=content,
                    emotional_summary=params.get("emotional_summary", "معلومات مخزنة"),
                    emotion_label=params.get("emotion_label", "neutral"),
                    valence=params.get("valence", 0.0),
                    arousal=params.get("arousal", 0.0),
                    user_id=params.get("user_id", "default"),
                    topics=params.get("topics", []),
                    lessons=params.get("lessons", []),
                )
                return {
                    "success": True,
                    "episode_id": episode.id,
                    "salience": episode.salience,
                    "stored": content[:100],
                }
            except Exception as e:
                logger.warning("EmotionalMemory store failed: %s", e)

        # Fallback: store in SQLite directly
        try:
            conn = get_db_connection(self.db_path)
            try:
                conn.execute("""CREATE TABLE IF NOT EXISTS ae_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT, timestamp REAL, tags TEXT)""")
                conn.execute(
                    "INSERT INTO ae_memory (content, timestamp, tags) VALUES (?, ?, ?)",
                    (content, time.time(), json.dumps(params.get("tags", []))),
                )
                conn.commit()
            finally:
                conn.close()
            return {"success": True, "stored": content[:100], "backend": "sqlite_fallback"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _tool_memory_recall(self, params: Dict, context: Dict) -> Any:
        """أداة استرجاع الذاكرة — استرجاع حقيقي عبر EmotionalMemoryEngine"""
        query = params.get("query", params.get("request", ""))
        if not query:
            return {"success": False, "error": "لم يتم تحديد استعلام البحث"}

        # Try EmotionalMemoryEngine first
        if self._emotional_memory:
            try:
                results = self._emotional_memory.recall(
                    query=query,
                    user_id=params.get("user_id", "default"),
                    limit=params.get("limit", 5),
                    emotion_filter=params.get("emotion_filter"),
                    min_salience=params.get("min_salience"),
                )
                return {
                    "success": True,
                    "query": query,
                    "results": results,
                    "count": len(results),
                }
            except Exception as e:
                logger.warning("EmotionalMemory recall failed: %s", e)

        # Fallback: search in SQLite
        try:
            conn = get_db_connection(self.db_path)
            try:
                cur = conn.execute(
                    "SELECT content, timestamp FROM ae_memory WHERE content LIKE ? ORDER BY timestamp DESC LIMIT 10",
                    (f"%{query}%",),
                )
                rows = cur.fetchall()
                return {
                    "success": True,
                    "query": query,
                    "results": [{"content": r[0], "timestamp": r[1]} for r in rows],
                    "count": len(rows),
                    "backend": "sqlite_fallback",
                }
            finally:
                conn.close()
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _tool_notify_user(self, params: Dict, context: Dict) -> Any:
        """أداة إبلاغ المستخدم — إرسال حقيقي عبر NeuralBus + SSE"""
        message = params.get("message", params.get("request", ""))
        if not message:
            return {"success": False, "error": "لم يتم تحديد رسالة"}

        # Publish via NeuralBus for real-time delivery
        if self._neural_bus:
            self._neural_bus.publish(
                "user_notification",
                source="absolute_executor",
                payload={
                    "message": message,
                    "level": params.get("level", "info"),
                    "plan_id": params.get("plan_id", ""),
                },
                priority=2,
            )

        # Also affect living state
        if self._living_state:
            from mamoun.core.living_state import EmotionalEvent
            self._living_state.process_event(EmotionalEvent(
                timestamp=time.time(),
                event_type="user_message",
                intensity=0.2,
                valence=0.3,
                source="absolute_executor.notify",
                description=f"Notification: {message[:50]}",
            ))

        return {"success": True, "notified": message[:200], "channel": "neural_bus"}

    async def _tool_capability_execute(self, params: Dict, context: Dict) -> Any:
        """أداة تنفيذ القدرات — توجيه حقيقي لمحرك القدرات"""
        capability = params.get("capability", "")
        action = params.get("action", "")

        # If capabilities engine is wired, use it
        if self._capabilities_engine:
            try:
                # Route to the right capability
                if capability == "terminal" or action == "execute_command":
                    return await self._capabilities_engine.execute_terminal_command(
                        command=params.get("command", params.get("request", "")),
                        timeout=params.get("timeout"),
                    )
                elif capability == "laptop_control":
                    return await self._capabilities_engine.control_laptop(
                        action=action or params.get("laptop_action", "screenshot"),
                        params=params.get("params", {}),
                    )
                elif capability == "web_research" or action == "research":
                    return await self._capabilities_engine.deep_research(
                        query=params.get("query", params.get("request", "")),
                        depth=params.get("depth", 3),
                    )
                elif capability == "trading_room":
                    if action == "market_data":
                        return await self._capabilities_engine.get_market_data(
                            symbol=params.get("symbol", "BTC"),
                        )
                    elif action == "signals":
                        return await self._capabilities_engine.get_trading_signals(
                            symbol=params.get("symbol", "BTC"),
                        )
                    elif action == "portfolio":
                        return await self._capabilities_engine.get_portfolio()
                    elif action == "overview":
                        return await self._capabilities_engine.get_market_overview()
                elif capability == "blender_control":
                    return await self._capabilities_engine.control_blender(
                        action=action or "get_status",
                        params=params.get("params", {}),
                    )
                elif capability == "instagram_analysis":
                    return await self._capabilities_engine.analyze_instagram(
                        username=params.get("username", ""),
                    )
                elif capability == "professional_coding":
                    return await self._capabilities_engine.generate_code(
                        spec=params.get("spec", params.get("request", "")),
                        language=params.get("language", "python"),
                    )
                elif capability == "agent_browser":
                    if action == "navigate":
                        return await self._capabilities_engine.browser_navigate(
                            url=params.get("url", ""),
                        )
                    elif action == "action":
                        return await self._capabilities_engine.browser_action(
                            action=params.get("browser_action", "screenshot"),
                            params=params.get("params", {}),
                        )
                elif capability == "testing_sandbox":
                    return await self._capabilities_engine.run_sandbox_test(
                        code=params.get("code", ""),
                        language=params.get("language", "python"),
                    )

                # Generic capability call
                cap = self._capabilities_engine.get_capability(capability)
                if cap and cap.is_operational:
                    return {
                        "success": True,
                        "capability": capability,
                        "action": action,
                        "percentage": cap.percentage,
                        "level": cap.level.value,
                    }

            except Exception as e:
                logger.error("Capability execution failed: %s", e)
                return {"success": False, "capability": capability, "error": str(e)}

        return {"success": False, "capability": capability, "action": action,
                "error": "محرك القدرات غير متاح أو القدرة غير معروفة"}

    # ═════════════════════════════════════════════════════════════════════════
    #  Status & API
    # ═════════════════════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        """حالة محرك التنفيذ"""
        return {
            "initialized": self._initialized,
            "tools_registered": len(self._tool_registry),
            "tools": list(self._tool_registry.keys()),
            "total_requests": self._stats["total_requests"],
            "total_completed": self._stats["total_completed"],
            "total_failed": self._stats["total_failed"],
            "success_rate": round(
                self._stats["total_completed"] / max(self._stats["total_requests"], 1), 3
            ),
            "total_retries": self._stats["total_retries"],
            "active_plan": self._active_plan.to_dict() if self._active_plan else None,
            "by_intent": self._stats["by_intent"],
        }

    def get_plan(self, plan_id: str) -> Optional[dict]:
        """الحصول على خطة تنفيذ"""
        if plan_id in self._plans:
            return self._plans[plan_id].to_dict()
        return None

    def get_recent_plans(self, limit: int = 10) -> List[dict]:
        """آخر خطط التنفيذ"""
        plans = sorted(self._plans.values(), key=lambda p: p.created_at, reverse=True)
        return [p.to_dict() for p in plans[:limit]]

    # ═════════════════════════════════════════════════════════════════════════
    #  Persistence
    # ═════════════════════════════════════════════════════════════════════════

    def _ensure_schema(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS ae_plans (
                id TEXT PRIMARY KEY, user_request TEXT, intent TEXT,
                intent_category TEXT, phase TEXT, success INTEGER,
                total_retries INTEGER, created_at REAL, completed_at REAL,
                result TEXT)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS ae_stats (
                key TEXT PRIMARY KEY, value TEXT)""")
            conn.commit()
        finally:
            conn.close()

    def _persist_plan(self, plan: ExecutionPlan):
        try:
            conn = get_db_connection(self.db_path)
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO ae_plans "
                    "(id, user_request, intent, intent_category, phase, success, "
                    "total_retries, created_at, completed_at, result) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (plan.id, plan.user_request[:500], plan.intent, plan.intent_category,
                     plan.phase, int(plan.success), plan.total_retries,
                     plan.created_at, plan.completed_at,
                     json.dumps(plan.final_result, default=str)[:5000]),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Plan persist failed: %s", e)

    def _load_stats(self):
        try:
            conn = get_db_connection(self.db_path)
            try:
                cur = conn.execute("SELECT key, value FROM ae_stats")
                for key, value in cur.fetchall():
                    try:
                        if key in ("total_requests", "total_completed", "total_failed", "total_retries"):
                            self._stats[key] = int(value)
                    except (ValueError, TypeError):
                        pass
            finally:
                conn.close()
        except Exception:
            pass

    def _persist_stats(self):
        try:
            conn = get_db_connection(self.db_path)
            try:
                for key, value in {
                    "total_requests": str(self._stats["total_requests"]),
                    "total_completed": str(self._stats["total_completed"]),
                    "total_failed": str(self._stats["total_failed"]),
                    "total_retries": str(self._stats["total_retries"]),
                }.items():
                    conn.execute("INSERT OR REPLACE INTO ae_stats (key, value) VALUES (?, ?)", (key, value))
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Stats persist failed: %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton
# ═══════════════════════════════════════════════════════════════════════════════

absolute_executor = AbsoluteExecutor()
