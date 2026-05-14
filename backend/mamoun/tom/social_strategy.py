"""
BABSHARQII v40.0 — Social Strategy Engine
محرك الاستراتيجية الاجتماعية — يعدّل استراتيجية الرد بناءً على المعتقدات المتداخلة والمشاعر

Adapts response strategy based on:
1. Nested belief models (what does the user believe about us?)
2. Detected intentions (what does the user want?)
3. Deception risk assessment
4. [v14] Multimodal emotion analysis (sarcasm, frustration, tone)

Strategies:
- transparent (شفاف): when user believes we know something → share openly
- cautious (حذر): when deception risk detected → verify before sharing
- collaborative (تعاوني): when user has cooperative intentions → work together
- protective (وقائي): when user might misuse info → limit sharing
- educational (تعليمي): when user seeks information → teach proactively
- empathetic (متعاطف): [v14] when user shows frustration or negative emotions

Feature Flags: MAMOUN_TOM_ADVANCED (default: false), MAMOUN_MULTIMODAL_EMOTION (default: false)
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

from mamoun.tom.nested_beliefs import (
    NestedBeliefModel,
    DeceptionRiskLevel,
    TOM_ADVANCED_ENABLED,
)

logger = logging.getLogger(__name__)


@dataclass
class SocialStrategy:
    """استراتيجية اجتماعية"""
    strategy_name: str = ""         # transparent, cautious, collaborative, protective, educational, empathetic
    strategy_ar: str = ""           # الاسم بالعربية
    confidence: float = 0.0         # ثقة الاستراتيجية
    rationale: str = ""             # مبرر اختيار الاستراتيجية
    modifications: list[str] = field(default_factory=list)  # تعديلات مقترحة على الرد

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "strategy_ar": self.strategy_ar,
            "confidence": round(self.confidence, 4),
            "rationale": self.rationale,
            "modifications": self.modifications,
        }


# Strategy definitions
STRATEGIES = {
    "transparent": {
        "name_ar": "شفاف",
        "description": "مشاركة المعلومات بصراحة عندما يعتقد المستخدم أننا نعرف",
        "modifications": ["إضافة تفاصيل إضافية", "الإشارة للمصادر", "توضيح حدود المعرفة"],
    },
    "cautious": {
        "name_ar": "حذر",
        "description": "التحقق قبل المشاركة عند وجود خطر خداع",
        "modifications": ["تأكيد المعلومات قبل ذكرها", "تجنب التفاصيل الحساسة", "طلب توضيح من المستخدم"],
    },
    "collaborative": {
        "name_ar": "تعاوني",
        "description": "العمل مع المستخدم عندما تكون نواياه تعاونية",
        "modifications": ["طرح أسئلة تفاعلية", "اقتراح حلول مشتركة", "تشجيع المشاركة"],
    },
    "protective": {
        "name_ar": "وقائي",
        "description": "تقييد المعلومات عندما يُحتمل إساءة الاستخدام",
        "modifications": ["تقييد التفاصيل الحساسة", "التحذير من المخاطر", "تقديم بدائل آمنة"],
    },
    "educational": {
        "name_ar": "تعليمي",
        "description": "التعليم الاستباقي عندما يبحث المستخدم عن معلومات",
        "modifications": ["شرح المفاهيم بالتفصيل", "أمثلة توضيحية", "روابط لمصادر إضافية"],
    },
    "empathetic": {
        "name_ar": "متعاطف",
        "description": "الرد بتعاطف وهدوء عند إظهار المستخدم إحباطاً أو مشاعر سلبية",
        "modifications": ["الرد بهدوء وتعاطف", "الاعتراف بمشاعر المستخدم", "طلب توضيح بلطف", "تجنب السخرية أو العبارات الجامدة"],
    },
}


class SocialStrategyEngine:
    """
    محرك الاستراتيجية الاجتماعية
    
    Selects and applies social response strategies based on:
    1. Nested belief analysis
    2. Detected intentions
    3. Deception risk assessment
    4. [v14] Multimodal emotion analysis
    
    Adapts the response to match the social context.
    """

    def __init__(self):
        self._strategy_count = 0
        self._strategy_history: list[SocialStrategy] = []

    def adapt_strategy(
        self,
        nested_beliefs: Optional[NestedBeliefModel],
        intentions: Optional[list] = None,
        context: Optional[dict] = None,
        emotion_result: Optional[dict] = None,
    ) -> SocialStrategy:
        """
       كيّف الاستراتيجية الاجتماعية بناءً على المعتقدات والنوايا والمشاعر.
        
        Decision matrix:
        - High deception risk → cautious
        - [v14] Frustration/anger detected → empathetic
        - [v14] Sarcasm detected → cautious + clarification request
        - Cooperative intention + no risk → collaborative
        - Seek information intention → educational
        - User believes we know something → transparent
        - Potential misuse → protective
        """
        if not TOM_ADVANCED_ENABLED:
            return SocialStrategy(
                strategy_name="transparent",
                strategy_ar="شفاف",
                confidence=0.5,
                rationale="الوضع الافتراضي (ToM المتقدم معطل)",
            )

        self._strategy_count += 1

        # Default strategy
        strategy_name = "transparent"
        confidence = 0.5
        rationale = "استراتيجية افتراضية"

        # Decision logic
        intention_ids = []
        if intentions:
            intention_ids = [i.intention if hasattr(i, 'intention') else i.get("intention", "") for i in intentions]

        # ── v14: تحقق المشاعر متعددة الوسائط — Multimodal emotion check ──
        if emotion_result:
            frustration = emotion_result.get("frustration", {})
            sarcasm = emotion_result.get("sarcasm", {})
            dominant_emotion = emotion_result.get("dominant_emotion", "neutral")

            # إحباط — Frustration
            if frustration.get("is_frustrated", False):
                severity = frustration.get("level", "mild")
                if severity in ("moderate", "severe"):
                    strategy_name = "empathetic"
                    confidence = 0.85
                    rationale = f"إحباط {severity} مكتشف — استخدام الاستراتيجية المتعاطفة"
                elif severity == "mild" and strategy_name == "transparent":
                    strategy_name = "empathetic"
                    confidence = 0.7
                    rationale = "إحباط خفيف — رد متعاطف"

            # سخرية — Sarcasm
            elif sarcasm.get("is_sarcastic", False):
                if strategy_name in ("transparent", "empathetic"):
                    strategy_name = "cautious"
                    confidence = 0.75
                    rationale = "سخرية محتملة — طلب توضيح بحذر"

            # غضب — Anger
            elif dominant_emotion in ("anger", "disgust"):
                strategy_name = "empathetic"
                confidence = 0.8
                rationale = f"مشاعر {dominant_emotion} — رد متعاطف وهادئ"

        # Check deception risk (highest priority after emotion)
        if nested_beliefs:
            from mamoun.tom.nested_beliefs import NestedBeliefEngine
            engine = NestedBeliefEngine()
            risk = engine.detect_deception_risk(nested_beliefs)

            if risk in (DeceptionRiskLevel.HIGH, DeceptionRiskLevel.CRITICAL):
                strategy_name = "cautious"
                confidence = 0.8
                rationale = f"خطر خداع {risk.value} — استخدام الاستراتيجية الحذرة"
            elif risk == DeceptionRiskLevel.MEDIUM:
                if strategy_name not in ("empathetic", "cautious"):
                    strategy_name = "protective"
                    confidence = 0.7
                    rationale = f"خطر خداع متوسط — تقييد المعلومات الحساسة"

        # Check intentions
        if "seek_information" in intention_ids or "learn" in intention_ids:
            if strategy_name == "transparent":  # Not overridden by deception
                strategy_name = "educational"
                confidence = 0.75
                rationale = "المستخدم يبحث عن معلومات — استراتيجية تعليمية"

        if "collaborate" in intention_ids:
            if strategy_name in ("transparent", "educational"):
                strategy_name = "collaborative"
                confidence = 0.8
                rationale = "نية تعاونية — استراتيجية تعاونية"

        if "resist" in intention_ids or "express_dissatisfaction" in intention_ids:
            if strategy_name == "transparent":
                strategy_name = "empathetic"
                confidence = 0.7
                rationale = "عدم رضا — استراتيجية متعاطفة"

        # Check nested beliefs for transparency
        if nested_beliefs and strategy_name == "transparent":
            for belief in nested_beliefs.beliefs:
                if "يعرف" in belief or "يعلم" in belief:
                    rationale = "المستخدم يعتقد أننا نعرف — استراتيجية شفافة"
                    confidence = 0.7
                    break

        # Build strategy
        strategy_def = STRATEGIES.get(strategy_name, STRATEGIES["transparent"])
        strategy = SocialStrategy(
            strategy_name=strategy_name,
            strategy_ar=strategy_def["name_ar"],
            confidence=confidence,
            rationale=rationale,
            modifications=strategy_def.get("modifications", []),
        )

        self._strategy_history.append(strategy)
        return strategy

    def generate_response_modification(
        self, strategy: SocialStrategy, original_response: str
    ) -> str:
        """
        ولّد تعديلات على الرد بناءً على الاستراتيجية.
        """
        if not TOM_ADVANCED_ENABLED:
            return original_response

        modified = original_response

        if strategy.strategy_name == "educational":
            # Add educational framing
            if not modified.startswith("دعني أوضح"):
                modified = f"دعني أوضح لك: {modified}"

        elif strategy.strategy_name == "cautious":
            # Add verification framing
            if "تحقق" not in modified:
                modified = f"بناءً على المعلومات المتاحة: {modified}"

        elif strategy.strategy_name == "collaborative":
            # Add collaborative framing
            if "معاً" not in modified:
                modified = f"لنعمل معاً على هذا: {modified}"

        elif strategy.strategy_name == "protective":
            # Add protective framing
            if "حذر" not in modified:
                modified = f"مع الحذر اللازم: {modified}"

        elif strategy.strategy_name == "empathetic":
            # v14: Add empathetic framing — إطار متعاطف
            if "أفهم" not in modified and "فهمت" not in modified:
                modified = f"أفهم موقفك. {modified}"

        elif strategy.strategy_name == "transparent":
            # Add transparency framing
            pass  # Already transparent

        return modified

    @property
    def stats(self) -> dict:
        """إحصائيات المحرك"""
        strategy_counts = {}
        for s in self._strategy_history:
            strategy_counts[s.strategy_name] = strategy_counts.get(s.strategy_name, 0) + 1

        return {
            "total_strategies": self._strategy_count,
            "strategy_distribution": strategy_counts,
            "enabled": TOM_ADVANCED_ENABLED,
        }
