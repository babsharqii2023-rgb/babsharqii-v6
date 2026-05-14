"""
BABSHARQII v25.0 — Transfer Learning Package
حزمة نقل التعلم — نقل المعرفة بين النطاقات

Implements:
1. Synaptic Intelligence (SI) — Track weight importance, prevent catastrophic forgetting
2. Domain Adapter — Transfer knowledge between domains with consolidation
3. Knowledge Bridge — Map concepts between domains
"""

from mamoun.transfer.synaptic_intelligence import SynapticIntelligenceEngine, synaptic_intelligence
from mamoun.transfer.domain_adapter import DomainAdapter, domain_adapter
from mamoun.transfer.knowledge_bridge import KnowledgeBridge, knowledge_bridge

__all__ = [
    "SynapticIntelligenceEngine",
    "synaptic_intelligence",
    "DomainAdapter",
    "domain_adapter",
    "KnowledgeBridge",
    "knowledge_bridge",
]
