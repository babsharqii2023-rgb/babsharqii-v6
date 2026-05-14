"""
BABSHARQII v6.0 — AGI Capabilities Package
طبقة قدرات AGI — Advanced General Intelligence modules

Modules:
  - fluid_reasoner: الاستدلال السائب (Fluid Reasoning)
  - common_sense: المنطق العام (Common Sense Reasoning)
  - hallucination_detector: كاشف الهلوسة (Hallucination Detection)
  - intent_drift: كاشف انحراف النية (Intent Drift Detection)
  - theory_of_mind: نظرية العقل (Theory of Mind)
  - continual_learning: التعلم المستمر (Continual Learning)
  - privacy_guard: حارس الخصوصية (Privacy Guard)
  - skill_discovery: اكتشاف المهارات (Skill Discovery)
  - swarm_intelligence: ذكاء السرب (Swarm Intelligence)
  - cultural_alignment: المواءمة الثقافية (Cultural Value Alignment)
  - specialized_pipeline: خط أنابيب الوكلاء المتخصصين (Specialized Agent Pipeline)
  - social_perception: الإدراك الاجتماعي (Social Perception)
"""

from mamoun.agi.fluid_reasoner import (
    FluidReasoner,
    AnalogicalReasoningEngine,
    PatternCompletionEngine,
    CounterfactualSimulator,
)
from mamoun.agi.common_sense import CommonSenseFilter
from mamoun.agi.hallucination_detector import HallucinationDetector
from mamoun.agi.intent_drift import IntentDriftDetector
from mamoun.agi.theory_of_mind import TheoryOfMindEngine
from mamoun.agi.continual_learning_bridge import ContinualLearningEngine as ContinualLearningBridge
from mamoun.agi.privacy_guard import PrivacyGuard
from mamoun.agi.skill_discovery import SkillDiscoveryEngine
from mamoun.agi.swarm_intelligence import SwarmIntelligenceEngine
from mamoun.agi.cultural_alignment import CulturalAlignmentEngine
from mamoun.agi.specialized_pipeline import SpecializedAgentPipeline
from mamoun.agi.social_perception import SocialPerceptionEngine

__all__ = [
    "FluidReasoner",
    "AnalogicalReasoningEngine",
    "PatternCompletionEngine",
    "CounterfactualSimulator",
    "CommonSenseFilter",
    "HallucinationDetector",
    "IntentDriftDetector",
    "TheoryOfMindEngine",
    "ContinualLearningBridge",
    "PrivacyGuard",
    "SkillDiscoveryEngine",
    "SwarmIntelligenceEngine",
    "CulturalAlignmentEngine",
    "SpecializedAgentPipeline",
    "SocialPerceptionEngine",
]

# سجل قدرات AGI — AGI Capability Registry
# 15 قدرة لخريطة طريق AGI — 15 capabilities for the AGI roadmap
AGI_CAPABILITIES = {
    "fluid_reasoning": {
        "name_ar": "الاستدلال السائب",
        "name_en": "Fluid Reasoning",
        "module": "mamoun.agi.fluid_reasoner",
        "class": "FluidReasoner",
        "env_toggle": "MAMOUN_FLUID_REASONER_ENABLED",
        "default_enabled": True,
        "readiness": 85,
        "description": "استدلال سائب مستوحى من ARC-AGI و Causal-JEPA — analogical transfer, pattern completion, counterfactual simulation",
    },
    "common_sense": {
        "name_ar": "المنطق العام",
        "name_en": "Common Sense Reasoning",
        "module": "mamoun.agi.common_sense",
        "class": "CommonSenseFilter",
        "env_toggle": "MAMOUN_COMMON_SENSE_ENABLED",
        "default_enabled": True,
        "readiness": 85,
        "description": "مرشح ثلاثي المراحل: فيزيائي + اجتماعي + سخرية — 52+ قاعدة فيزيائية، 30+ قاعدة اجتماعية",
    },
    "hallucination_detection": {
        "name_ar": "كشف الهلوسة",
        "name_en": "Hallucination Detection",
        "module": "mamoun.agi.hallucination_detector",
        "class": "HallucinationDetector",
        "env_toggle": "MAMOUN_HALLUCINATION_DETECTION_ENABLED",
        "default_enabled": True,
        "readiness": 90,
        "description": "كشف هلوسة متعدد الإشارات: اتساق ذاتي + تأصيل واقعي + كيانات مختلقة + معايرة ثقة",
    },
    "intent_drift": {
        "name_ar": "كشف انحراف النية",
        "name_en": "Intent Drift Detection",
        "module": "mamoun.agi.intent_drift",
        "class": "IntentDriftDetector",
        "env_toggle": "MAMOUN_INTENT_DRIFT_ENABLED",
        "default_enabled": True,
        "readiness": 80,
        "description": "مراقبة انحراف التنفيذ عن الهدف الأصلي — شجرة أهداف + تنقيط متعدد العوامل + تحذير مبكر",
    },
    "theory_of_mind": {
        "name_ar": "نظرية العقل",
        "name_en": "Theory of Mind",
        "module": "mamoun.agi.theory_of_mind",
        "class": "TheoryOfMindEngine",
        "env_toggle": "MAMOUN_THEORY_OF_MIND_ENABLED",
        "default_enabled": True,
        "readiness": 80,
        "description": "نمذجة الحالات العقلية للآخرين — Adaptive ToM + MetaMind + BDI architecture",
    },
    "continual_learning": {
        "name_ar": "التعلم المستمر",
        "name_en": "Continual Learning",
        "module": "mamoun.agi.continual_learning",
        "class": "ContinualLearningEngine",
        "env_toggle": "MAMOUN_CONTINUAL_LEARNING_ENABLED",
        "default_enabled": True,
        "readiness": 80,
        "description": "تعلم مستمر مع منع النسيان الكارثي — EvoSkill + Ctx2Skill + MetaClaw (EWC)",
    },
    "privacy_guard": {
        "name_ar": "حارس الخصوصية",
        "name_en": "Privacy Guard",
        "module": "mamoun.agi.privacy_guard",
        "class": "PrivacyGuard",
        "env_toggle": "MAMOUN_PRIVACY_GUARD_ENABLED",
        "default_enabled": True,
        "readiness": 90,
        "description": "حماية البيانات الشخصية — مسح + تشفير + تدقيق + إخفاء",
    },
    "skill_discovery": {
        "name_ar": "اكتشاف المهارات",
        "name_en": "Skill Discovery",
        "module": "mamoun.agi.skill_discovery",
        "class": "SkillDiscoveryEngine",
        "env_toggle": "MAMOUN_SKILL_DISCOVERY_ENABLED",
        "default_enabled": True,
        "readiness": 80,
        "description": "اكتشاف تلقائي لفجوات المهارات وإنشاء مهارات جديدة",
    },
    "swarm_intelligence": {
        "name_ar": "ذكاء السرب",
        "name_en": "Swarm Intelligence",
        "module": "mamoun.agi.swarm_intelligence",
        "class": "SwarmIntelligenceEngine",
        "env_toggle": "MAMOUN_SWARM_INTELLIGENCE_ENABLED",
        "default_enabled": True,
        "readiness": 80,
        "description": "ذكاء جماعي لامركزي — PSO + إجماع + ستيغميرجي + خوارزمية النحل",
    },
    "cultural_alignment": {
        "name_ar": "المواءمة الثقافية",
        "name_en": "Cultural Value Alignment",
        "module": "mamoun.agi.cultural_alignment",
        "class": "CulturalAlignmentEngine",
        "env_toggle": "MAMOUN_CULTURAL_ALIGNMENT_ENABLED",
        "default_enabled": True,
        "readiness": 85,
        "description": "محاذاة سلوك الكائن الرقمي مع القيم الثقافية — دستور قيمي + أبعاد هوفستيد + مقاصد الشريعة",
    },
    "specialized_pipeline": {
        "name_ar": "خط أنابيب الوكلاء المتخصصين",
        "name_en": "Specialized Agent Pipeline",
        "module": "mamoun.agi.specialized_pipeline",
        "class": "SpecializedAgentPipeline",
        "env_toggle": "MAMOUN_SPECIALIZED_PIPELINE_ENABLED",
        "default_enabled": True,
        "readiness": 87,
        "description": "توجيه ديناميكي تكيّفي للمهام إلى الوكلاء المتخصصين — CodeAgent + AnalysisAgent + CreativeAgent + MathAgent + ResearchAgent + توجيه تكيّفي + تخزين مؤقت + تعاون بين الوكلاء",
    },
    "social_perception": {
        "name_ar": "الإدراك الاجتماعي",
        "name_en": "Social Perception",
        "module": "mamoun.agi.social_perception",
        "class": "SocialPerceptionEngine",
        "env_toggle": "MAMOUN_SOCIAL_PERCEPTION_ENABLED",
        "default_enabled": True,
        "readiness": 87,
        "description": "إدراك اجتماعي شامل — نفي + شدة + رموز تعبيرية + لهجات + سخرية + مؤشرات إعرابية + أدوار اجتماعية + ذاكرة محادثة — 120+ كلمة عاطفية عربية + إنجليزية",
    },
}
