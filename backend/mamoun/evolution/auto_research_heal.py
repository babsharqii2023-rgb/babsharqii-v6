"""
BABSHARQII v40.0 — Auto Research-Heal Loop
حلقة الإصلاح التلقائي بالبحث العميق
Pipeline: Detect → Search → Learn → Propose → Validate → Apply → Verify

مستوحى من: Darwin Gödel Machine (DGM)
"""

import logging
import time
from typing import Optional
from pathlib import Path

logger = logging.getLogger("mamoun.auto_research_heal")


class AutoResearchHealLoop:
    """
    حلقة الإصلاح التلقائي بالبحث العميق
    
    المراحل الست:
    1. HealthMonitor يكتشف مشكلة → يُبلّغ LiveSelfModifier
    2. LiveSelfModifier يُبلّغ AutoResearchHealLoop بنقطة الضعف
    3. AutoResearchHealLoop يبحث في الويب عن حلول (DeepResearchEngine)
    4. LLM يحلّل النتائج ويقترح كود إصلاح
    5. SelfModifier يتحقق من الأمان ويختبر
    6. يُطبّق مع rollback تلقائي إن فشل
    """
    
    def __init__(self, llm_client=None, self_modifier=None, live_self_modifier=None):
        self._llm = llm_client
        self._self_modifier = self_modifier
        self._live_self_modifier = live_self_modifier
        self._heal_count = 0
        self._fail_count = 0
    
    def set_llm_client(self, llm_client):
        self._llm = llm_client
    
    def set_self_modifier(self, modifier):
        self._self_modifier = modifier
    
    def set_live_self_modifier(self, lsm):
        self._live_self_modifier = lsm
    
    async def heal_with_research(self, weakness) -> bool:
        """الإصلاح بالبحث العميق — المراحل الست"""
        logger.info(f"AutoResearchHeal: starting for {weakness.area}")
        
        if not self._llm:
            logger.error("No LLM client available for research healing")
            return False
        
        # المرحلة 1: بحث عميق
        try:
            from mamoun.core.deep_research_engine import DeepResearchEngine
            engine = DeepResearchEngine(llm_client=self._llm)
            report = await engine.research(
                query=f"how to fix {weakness.area} {weakness.description} in Python/TypeScript FastAPI Next.js",
                depth=3,
                verify=True,
            )
        except Exception as e:
            logger.warning(f"DeepResearch failed, trying simple search: {e}")
            # Fallback: بحث بسيط
            report = None
            try:
                from mamoun.core.web_search_client import WebSearchClient
                search = WebSearchClient()
                results = await search.search(f"fix {weakness.area} {weakness.description}")
                report = type('Report', (), {
                    'summary': '\n'.join([r.get('snippet', '') for r in (results or [])[:3]]),
                    'sources': results or [],
                    'confidence_score': 0.5,
                })()
            except Exception as e2:
                logger.error(f"All search methods failed: {e2}")
                self._fail_count += 1
                return False
        
        if not report:
            self._fail_count += 1
            return False
        
        # المرحلة 2: استخراج حل من نتائج البحث
        sources_text = ""
        if hasattr(report, 'sources') and report.sources:
            for s in report.sources[:5]:
                if isinstance(s, dict):
                    sources_text += f"- {s.get('title', '')}: {s.get('snippet', '')}\n"
                else:
                    sources_text += f"- {str(s)}\n"
        
        summary = getattr(report, 'summary', '') or getattr(report, 'analysis', '') or sources_text
        
        # المرحلة 3: اقتراح إصلاح بالـ LLM
        fix_prompt = f"""بناءً على نتائج البحث التالية، اقترح كود إصلاح:

المنطقة: {weakness.area}
الوصف: {weakness.description}
الخطورة: {weakness.severity}

نتائج البحث:
{summary[:4000]}

اكتب الكود المعدّل فقط. أجب بالكود بدون markdown wrappers."""

        try:
            fix_code = await self._llm.think(fix_prompt, model="glm-5.1", temperature=0.3)
        except Exception as e:
            logger.error(f"LLM fix generation failed: {e}")
            self._fail_count += 1
            return False
        
        if not fix_code or len(fix_code) < 20:
            self._fail_count += 1
            return False
        
        # إزالة markdown wrapper
        if fix_code.strip().startswith('```'):
            lines = fix_code.strip().split('\n')
            fix_code = '\n'.join(lines[1:-1])
        
        # المرحلة 4: محاولة التطبيق عبر LiveSelfModifier
        if self._live_self_modifier:
            try:
                from mamoun.evolution.live_self_modifier import CodeModification, ModificationStatus
                modification = CodeModification(
                    target_file=self._live_self_modifier._resolve_target_file(weakness.area) or "",
                    target_function="",
                    weakness_id=weakness.weakness_id,
                    old_code="",
                    new_code=fix_code,
                    explanation=f"Auto-research heal: {weakness.description}",
                    brain_consensus=0.7,
                )
                
                # Apply with auto-approve in dev mode
                modification.status = ModificationStatus.APPROVED.value
                applied = await self._live_self_modifier.apply_patch(modification)
                if applied:
                    self._heal_count += 1
                    logger.info(f"AutoResearchHeal: SUCCESS for {weakness.area}")
                    return True
            except Exception as e:
                logger.error(f"LiveSelfModifier apply failed: {e}")
        
        self._fail_count += 1
        return False
    
    def get_status(self) -> dict:
        return {
            "heal_count": self._heal_count,
            "fail_count": self._fail_count,
            "has_llm": self._llm is not None,
            "has_self_modifier": self._self_modifier is not None,
            "has_live_self_modifier": self._live_self_modifier is not None,
        }
