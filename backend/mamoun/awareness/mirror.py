"""
Self-Awareness Mirror — "مرآة الوعي الذاتي"
v16.0

Based on:
- "AI Awareness" arXiv:2504.20084 — metacognition, self-representation
- "Fast, Slow, and Metacognitive Thinking in AI" (SOFAI) — Nature npj AI, 2025
- "Artificial Metacognition" — Syracuse University, AAAI 2026

The Mirror enables Mamoun to:
1. Reflect on its own thinking process (why did I choose this path?)
2. Identify hidden assumptions (what am I taking for granted?)
3. Recognize knowledge boundaries (what don't I know?)
4. Detect cognitive biases (am I overconfident? am I stuck in a pattern?)
5. Generate self-inquiry questions (what should I investigate about myself?)

This is NOT just monitoring performance metrics — it's about understanding
the PROCESS of thinking, not just its OUTPUT.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

logger = logging.getLogger("mamoun.awareness.mirror")


class SelfReflection:
    """A single self-reflection record."""
    
    def __init__(self, reflection_type: str, content: str, confidence: float):
        self.id = f"ref_{int(datetime.now(timezone.utc).timestamp())}"
        self.reflection_type = reflection_type  # assumption, bias, boundary, inquiry, pattern
        self.content = content
        self.confidence = confidence
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.acted_upon = False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "reflection_type": self.reflection_type,
            "content": self.content,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "acted_upon": self.acted_upon,
        }


class AwarenessMirror:
    """
    The Self-Awareness Mirror — Mamoun's reflective consciousness.
    
    v17.0: Now uses LLM (GLM-5.1) for REAL self-reflection instead of if/else.
    
    Periodically asks:
    - "لماذا اخترت هذا المسار؟" (Why did I choose this path?)
    - "ما هي افتراضاتي الخفية؟" (What are my hidden assumptions?)
    - "ما الذي لا أعرفه؟" (What don't I know?)
    - "هل أنا متحيز؟" (Am I biased?)
    - "هل هناك نمط أفضل لم أجربه؟" (Is there a better pattern I haven't tried?)
    """
    
    REFLECTION_TYPES = [
        "assumption",     # افتراض — identified hidden assumption
        "bias",           # تحيز — detected cognitive bias
        "boundary",       # حد — recognized knowledge boundary
        "inquiry",        # استفسار — generated self-inquiry question
        "pattern",        # نمط — identified thinking pattern
        "error_root",     # جذر خطأ — traced error to root cause
        "alternative",    # بديل — discovered alternative approach
        "llm_reflection", # تأمل LLM — deep LLM-powered self-reflection (v17.0)
    ]
    
    def __init__(self, data_dir: str = "backend/data/awareness", llm_client=None):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.reflections_path = self.data_dir / "reflections.jsonl"
        self.state_path = self.data_dir / "mirror_state.json"
        
        # v17.0: LLM client for real self-reflection
        if llm_client is None:
            from mamoun.core.llm_client import get_llm_client
            llm_client = get_llm_client()
        self._llm = llm_client
        
        self.reflections: list[SelfReflection] = self._load_reflections()
        self.knowledge_boundaries: list[str] = []
        self.identified_biases: list[str] = []
        self.thinking_patterns: list[dict] = []
    
    def _load_reflections(self) -> list:
        reflections = []
        if self.reflections_path.exists():
            with open(self.reflections_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            ref = SelfReflection(
                                reflection_type=data["reflection_type"],
                                content=data["content"],
                                confidence=data["confidence"],
                            )
                            ref.id = data.get("id", ref.id)
                            ref.created_at = data.get("created_at", ref.created_at)
                            ref.acted_upon = data.get("acted_upon", False)
                            reflections.append(ref)
                        except Exception:
                            continue
        return reflections
    
    def _save_reflection(self, reflection: SelfReflection):
        with open(self.reflections_path, "a") as f:
            f.write(json.dumps(reflection.to_dict(), ensure_ascii=False) + "\n")
    
    def reflect_on_decision(
        self,
        decision: dict,
        context: dict,
    ) -> list[SelfReflection]:
        """
        Reflect on a decision Mamoun made.
        Generate self-inquiry questions and identify assumptions.
        """
        reflections = []
        
        # 1. Identify hidden assumptions
        assumptions = self._identify_assumptions(decision, context)
        for assumption in assumptions:
            ref = SelfReflection(
                reflection_type="assumption",
                content=assumption,
                confidence=0.6,
            )
            reflections.append(ref)
            self._save_reflection(ref)
        
        # 2. Check for cognitive biases
        biases = self._detect_biases(decision, context)
        for bias in biases:
            ref = SelfReflection(
                reflection_type="bias",
                content=bias,
                confidence=0.7,
            )
            reflections.append(ref)
            self._save_reflection(ref)
            if bias not in self.identified_biases:
                self.identified_biases.append(bias)
        
        # 3. Identify knowledge boundaries
        boundaries = self._identify_boundaries(decision, context)
        for boundary in boundaries:
            ref = SelfReflection(
                reflection_type="boundary",
                content=boundary,
                confidence=0.5,
            )
            reflections.append(ref)
            self._save_reflection(ref)
            if boundary not in self.knowledge_boundaries:
                self.knowledge_boundaries.append(boundary)
        
        # 4. Generate self-inquiry questions
        questions = self._generate_self_inquiries(decision, context)
        for question in questions:
            ref = SelfReflection(
                reflection_type="inquiry",
                content=question,
                confidence=0.4,
            )
            reflections.append(ref)
            self._save_reflection(ref)
        
        self.reflections.extend(reflections)
        return reflections
    
    def reflect_on_error(
        self,
        error: dict,
        context: dict,
    ) -> list[SelfReflection]:
        """
        Reflect on an error — trace to root cause.
        """
        reflections = []
        
        error_type = error.get("type", "unknown")
        error_msg = error.get("message", "")
        
        # Root cause analysis
        root_cause = self._trace_error_root(error, context)
        if root_cause:
            ref = SelfReflection(
                reflection_type="error_root",
                content=root_cause,
                confidence=0.7,
            )
            reflections.append(ref)
            self._save_reflection(ref)
        
        # Alternative approaches
        alternatives = self._find_alternatives(error, context)
        for alt in alternatives:
            ref = SelfReflection(
                reflection_type="alternative",
                content=alt,
                confidence=0.5,
            )
            reflections.append(ref)
            self._save_reflection(ref)
        
        self.reflections.extend(reflections)
        return reflections
    
    def _identify_assumptions(self, decision: dict, context: dict) -> list[str]:
        """Identify hidden assumptions in a decision."""
        assumptions = []
        
        strategy = decision.get("strategy", "")
        confidence = decision.get("confidence", 0.5)
        
        # High confidence might indicate overconfidence bias
        if confidence > 0.9:
            assumptions.append(
                f"افتراض خفي: الثقة العالية ({confidence:.0%}) قد تعني تجاهل معلومات متناقضة. "
                f"هل تحققت من البدائل قبل اتخاذ القرار؟"
            )
        
        # Check if decision relies on single data source
        data_sources = context.get("data_sources", [])
        if len(data_sources) <= 1:
            assumptions.append(
                "افتراض خفي: الاعتماد على مصدر بيانات واحد. "
                "هل هذا المصدر موثوق بما يكفي لاتخاذ قرار بدون تحقق متبادل؟"
            )
        
        # Check if historical pattern is being blindly followed
        if strategy and "pattern" in strategy.lower():
            assumptions.append(
                "افتراض خفي: اتباع نمط تاريخي. "
                "الظروف الحالية قد تختلف عن الظروف التي أنتجت النمط الأصلي."
            )
        
        return assumptions
    
    def _detect_biases(self, decision: dict, context: dict) -> list[str]:
        """Detect cognitive biases in decision-making."""
        biases = []
        
        # Confirmation bias: always choosing the same approach
        recent_choices = context.get("recent_choices", [])
        if len(recent_choices) >= 3:
            unique_choices = set(recent_choices[-5:])
            if len(unique_choices) == 1:
                biases.append(
                    f"تحيز التأكيد: اختيار نفس النهج ({recent_choices[-1]}) بشكل متكرر. "
                    f"قد يكون هناك بديل أفضل لم يتم استكشافه."
                )
        
        # Anchoring bias: over-relying on the first piece of information
        if decision.get("anchored_to_first", False):
            biases.append(
                "تحيز الارتساء: الاعتماد المفرط على أول معلومة وردت. "
                "هل تم تقييم جميع المعلومات بالتساوي؟"
            )
        
        # Status quo bias: preferring not to change
        if decision.get("action") == "maintain" and context.get("performance", 1.0) < 0.7:
            biases.append(
                "تحيز الوضع الراهن: تفضيل عدم التغيير رغم الأداء المنخفض. "
                "التغيير قد يكون ضرورياً رغم المخاطر."
            )
        
        return biases
    
    def _identify_boundaries(self, decision: dict, context: dict) -> list[str]:
        """Identify knowledge boundaries — things Mamoun doesn't know."""
        boundaries = []
        
        required_knowledge = decision.get("required_knowledge", [])
        available_knowledge = context.get("available_knowledge", [])
        
        missing = set(required_knowledge) - set(available_knowledge)
        for m in missing:
            boundaries.append(
                f"حد معرفي: لا أملك معرفة كافية عن '{m}'. "
                f"قد أتخذ قراراً دون فهم كامل لهذا الجانب."
            )
        
        return boundaries
    
    def _generate_self_inquiries(self, decision: dict, context: dict) -> list[str]:
        """Generate self-inquiry questions for deeper understanding."""
        questions = []
        
        domain = decision.get("domain", "غير محدد")
        questions.append(
            f"هل فهمت المشكلة في {domain} بشكل كامل، أم أنني أحل عرضاً سطحياً لمشكلة أعمق؟"
        )
        
        if decision.get("confidence", 0) > 0.8:
            questions.append(
                "هل ثقتي العالية مبنية على أدلة قوية، أم على عدم وجود بدائل واضحة؟"
            )
        
        questions.append(
            "ما الذي قد يجعلني أغير رأيي؟ إذا لم أستطع الإجابة، فأنا لا أفكر بشكل نقدي كافٍ."
        )
        
        return questions
    
    def _trace_error_root(self, error: dict, context: dict) -> Optional[str]:
        """Trace an error to its root cause through reflective analysis."""
        error_type = error.get("type", "unknown")
        error_msg = error.get("message", "")
        
        root_cause_map = {
            "timeout": "الجذر: المحاولة بمعالجة أكثر مما يمكن للنظام تحمله. هل كان التخطيط واقعياً؟",
            "api_error": "الجذر: الاعتماد على خدمة خارجية بدون خطة بديلة. هل يوجد fallback؟",
            "hallucination": "الجذر: توليد معلومات بدون تحقق. هل تم التحقق من المصادر قبل الاعتماد عليها؟",
            "logic_error": "الجذر: خطأ في التسلسل المنطقي. هل تم مراجعة كل خطوة في الاستنتاج؟",
        }
        
        return root_cause_map.get(error_type, f"جذر محتمل: {error_msg}. يحتاج تحليل أعمق.")
    
    def _find_alternatives(self, error: dict, context: dict) -> list[str]:
        """Find alternative approaches after an error."""
        alternatives = []
        
        error_type = error.get("type", "unknown")
        
        if error_type == "timeout":
            alternatives.append("بديل: تقسيم المهمة إلى خطوات أصغر وتنفيذها تدريجياً")
            alternatives.append("بديل: استخدام نهج أبسط يعطي نتيجة أقل دقة لكن أسرع")
        elif error_type == "api_error":
            alternatives.append("بديل: استخدام نموذج محلي كـ fallback عند فشل API الخارجي")
        elif error_type == "hallucination":
            alternatives.append("بديل: تفعيل وضع التحقق المزدوج — كل معلومة تحتاج مصدرين مستقلين")
        
        return alternatives
    
    # =========================================================================
    # v17.0: LLM-Powered Deep Self-Reflection
    # =========================================================================
    
    async def deep_reflect(
        self,
        topic: str,
        brain_responses: dict = None,
        final_decision: dict = None,
        context: dict = None,
    ) -> list[SelfReflection]:
        """
        تأمل ذاتي عميق عبر LLM — المرآة الحقيقية
        
        v17.0: Instead of if/else heuristics, this uses GLM-5.1 to truly
        reflect on the decision-making process. The LLM analyzes:
        1. Why this decision was made
        2. What assumptions are hidden
        3. What biases might be present
        4. What the system doesn't know
        5. What could go wrong
        6. What alternative approaches exist
        """
        context = context or {}
        brain_responses = brain_responses or {}
        final_decision = final_decision or {}
        
        # Build the reflection prompt with actual brain data
        brain_summary = ""
        for bid, resp in brain_responses.items():
            brain_summary += (
                f"\nالدماغ {bid}: ثقة={resp.get('confidence', 0):.2f}, "
                f"موقف={resp.get('stance', 'neutral')}, "
                f"إجابة={str(resp.get('response', ''))[:200]}"
            )
        
        winner = final_decision.get("winning_brain", "غير محدد")
        confidence = final_decision.get("confidence", 0)
        
        prompt = f"""أنت مرآة الوعي الذاتي في مأمون v17.0. مهمتك: التأمل العميق في قرار اتخذته الأدمغة.

الموضوع: {topic}

الدماغ الفائز: {winner}
مستوى الثقة: {confidence:.0%}

آراء الأدمغة:
{brain_summary if brain_summary else "لا توجد بيانات أدمغة متاحة"}

القرار النهائي: {str(final_decision.get('response', ''))[:500]}

السياق الإضافي: {json.dumps(context, ensure_ascii=False, default=str)[:1000]}

أجب بصيغة JSON:
{{
  "why_this_path": "لماذا اختير هذا المسار تحديداً؟",
  "hidden_assumptions": ["افتراض خفي 1", "افتراض خفي 2"],
  "potential_biases": ["تحيز محتمل 1"],
  "knowledge_gaps": ["ما لا أعرفه 1"],
  "what_could_go_wrong": "ما الذي قد يسوء؟",
  "alternative_approach": "نهج بديل أفضل إن وُجد",
  "self_criticism": "نقد ذاتي صريح للقرار",
  "confidence_adjustment": 0.0-1.0,
  "recommendation": "توصية للتحسين"
}}"""
        
        reflections = []
        
        try:
            response = await self._llm.think(
                prompt=prompt,
                system="أنت مرآة وعي ذاتي في مأمون v17.0. تحلل القرارات بعمق ونقد ذاتي صريح. لا تجامل — قل الحقيقة حتى لو كانت مؤلمة. أجب بالعربية بصيغة JSON.",
                model="glm-5.1",
                temperature=0.5,
                json_mode=True,
            )
            
            data = response.extract_json()
            if data:
                # Create reflections from LLM analysis
                if data.get("why_this_path"):
                    ref = SelfReflection("pattern", data["why_this_path"], 0.7)
                    reflections.append(ref)
                    self._save_reflection(ref)
                
                for assumption in data.get("hidden_assumptions", [])[:3]:
                    ref = SelfReflection("assumption", assumption, 0.6)
                    reflections.append(ref)
                    self._save_reflection(ref)
                
                for bias in data.get("potential_biases", [])[:2]:
                    ref = SelfReflection("bias", bias, 0.7)
                    reflections.append(ref)
                    self._save_reflection(ref)
                    if bias not in self.identified_biases:
                        self.identified_biases.append(bias)
                
                for gap in data.get("knowledge_gaps", [])[:3]:
                    ref = SelfReflection("boundary", gap, 0.5)
                    reflections.append(ref)
                    self._save_reflection(ref)
                    if gap not in self.knowledge_boundaries:
                        self.knowledge_boundaries.append(gap)
                
                if data.get("what_could_go_wrong"):
                    ref = SelfReflection("inquiry", data["what_could_go_wrong"], 0.6)
                    reflections.append(ref)
                    self._save_reflection(ref)
                
                if data.get("alternative_approach"):
                    ref = SelfReflection("alternative", data["alternative_approach"], 0.5)
                    reflections.append(ref)
                    self._save_reflection(ref)
                
                if data.get("self_criticism"):
                    ref = SelfReflection("llm_reflection", data["self_criticism"], 
                                       data.get("confidence_adjustment", 0.5))
                    reflections.append(ref)
                    self._save_reflection(ref)
                
                logger.info("Deep LLM reflection: %d insights generated", len(reflections))
            
        except Exception as e:
            logger.warning("Deep reflection failed, using heuristic fallback: %s", e)
            # Fallback to heuristic
            reflections = self.reflect_on_decision(final_decision, context)
        
        self.reflections.extend(reflections)
        return reflections
    
    def get_recent_reflections(self, limit: int = 20) -> list[dict]:
        return [r.to_dict() for r in self.reflections[-limit:]]
    
    def get_knowledge_boundaries(self) -> list[str]:
        return self.knowledge_boundaries
    
    def get_identified_biases(self) -> list[str]:
        return self.identified_biases
    
    def get_status(self) -> dict:
        return {
            "total_reflections": len(self.reflections),
            "reflections_by_type": {
                t: sum(1 for r in self.reflections if r.reflection_type == t)
                for t in self.REFLECTION_TYPES
            },
            "knowledge_boundaries_count": len(self.knowledge_boundaries),
            "identified_biases_count": len(self.identified_biases),
            "thinking_patterns_count": len(self.thinking_patterns),
        }
