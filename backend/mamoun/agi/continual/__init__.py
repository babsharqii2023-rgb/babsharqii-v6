"""
BABSHARQII v36.0 — Continual Learning Package
حزمة التعلم المستمر — محركات منع النسيان الكارثي

Sub-modules:
  - ewc_engine: محرك الدمج المرن للأوزان (Elastic Weight Consolidation)
  - synaptic_intelligence: محرك الذكاء المشبكي (online importance)
  - streaming_knowledge_store: مخزن المعرفة المتدفق
  - auto_benchmark: مشغّل الاختبارات التلقائي
"""

from mamoun.agi.continual.ewc_engine import EWCEngine, KnowledgeAnchor, EWCReport
from mamoun.agi.continual.synaptic_intelligence_online import SynapticIntelligenceEngine, SynapseInfo, SIReport
from mamoun.agi.continual.streaming_knowledge_store import StreamingKnowledgeStore, KnowledgeItem
from mamoun.agi.continual.auto_benchmark import AutoBenchmarkRunner, BenchmarkEntry

__all__ = [
    "EWCEngine",
    "KnowledgeAnchor",
    "EWCReport",
    "SynapticIntelligenceEngine",
    "SynapseInfo",
    "SIReport",
    "StreamingKnowledgeStore",
    "KnowledgeItem",
    "AutoBenchmarkRunner",
    "BenchmarkEntry",
]
