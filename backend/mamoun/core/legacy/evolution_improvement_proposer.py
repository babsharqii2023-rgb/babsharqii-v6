"""
BABSHARQII v13.0 — Improvement Proposer
مقترح التحسينات — يحلل الأبحاث ويقترح تحسينات على مأمون

Flow:
1. Receive research results from TrustedResearchFetcher
2. Analyze each finding for relevance to مأمون's architecture
3. Generate improvement proposals with:
   - What to change
   - Why it would help
   - How to implement it
   - Risk assessment
4. Submit proposals through ApprovalGate for human review

Feature Flag: MAMOUN_SELF_PROGRAMMING (default: false)
"""

import os
import time
import uuid
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum

from mamoun.evolution.self_programming_loop import SELF_PROGRAMMING_ENABLED, _is_self_programming_enabled

logger = logging.getLogger(__name__)


class ProposalStatus(str, Enum):
    """حالة الاقتراح."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    FAILED = "failed"


@dataclass
class ImprovementProposal:
    """اقتراح تحسين."""
    proposal_id: str = ""
    title: str = ""
    title_ar: str = ""
    description: str = ""
    description_ar: str = ""
    source_paper: str = ""
    source_repo: str = ""
    target_module: str = ""  # Which part of مأمون to modify
    change_type: str = ""    # new_feature, optimization, bug_fix, refactoring
    implementation_steps: list = field(default_factory=list)
    risk_level: str = "medium"
    estimated_improvement: float = 0.0
    status: str = ProposalStatus.DRAFT.value
    approval_id: str = ""
    created_at: float = 0.0

    def __post_init__(self):
        if not self.proposal_id:
            self.proposal_id = f"prop_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


# Mapping of research topics to مأمون modules
TOPIC_MODULE_MAP = {
    "agentic AI": "mamoun.core.agi_bridge",
    "Arabic NLP": "mamoun.agi.specialized_pipeline",
    "self-improving": "mamoun.evolution",
    "time-bounded authorization": "safety_gate.time_bounded_policy",
    "digital organism": "mamoun.core",
    "multimodal reasoning": "mamoun.agents.omni_agent",
    "safe AI alignment": "mamoun.core.safety_guard",
    "evolutionary computation": "mamoun.evolution.mutation_engine",
}


class ImprovementProposer:
    """
    مقترح التحسينات — يحلل الأبحاث ويقترح تحسينات.

    Analysis Criteria:
    - Relevance to مأمون's current architecture
    - Potential improvement magnitude
    - Implementation complexity
    - Risk assessment
    - Alignment with safety principles

    Usage:
        proposer = ImprovementProposer()
        proposals = await proposer.analyze_and_propose(research_results)
    """

    def __init__(self, approval_gate=None):
        self._approval_gate = approval_gate
        self._proposals: list[ImprovementProposal] = []
        self._proposal_count = 0

    async def analyze_and_propose(self, research_results: list[dict]) -> list[dict]:
        """
        تحليل الأبحاث واقتراح تحسينات — Analyze research and propose improvements.

        Args:
            research_results: نتائج البحث من TrustedResearchFetcher

        Returns:
            List of ImprovementProposal dicts
        """
        if not _is_self_programming_enabled():
            return []

        proposals = []

        for item in research_results:
            try:
                proposal = self._analyze_item(item)
                if proposal:
                    proposals.append(proposal)
                    self._proposals.append(proposal)
                    self._proposal_count += 1
            except Exception as e:
                logger.warning(f"Failed to analyze research item: {e}")

        # Submit proposals for approval
        for proposal in proposals:
            if self._approval_gate:
                try:
                    from mamoun.core.approval_gate import ApprovalRequest
                    request = ApprovalRequest(
                        change_type="self_evolution_proposal",
                        target=proposal.target_module,
                        description=f"تحسين مقترح: {proposal.title_ar or proposal.title}",
                        risk_level=proposal.risk_level,
                        details=str(proposal.to_dict()),
                    )
                    result = await self._approval_gate.request_approval(request)
                    proposal.approval_id = result.get("id", "")
                    proposal.status = ProposalStatus.SUBMITTED.value
                except Exception as e:
                    logger.warning(f"Failed to submit proposal for approval: {e}")

        return [p.to_dict() for p in proposals]

    def _analyze_item(self, item: dict) -> Optional[ImprovementProposal]:
        """تحليل عنصر بحثي واحد."""
        item_type = item.get("type", "")
        title = item.get("title", "")
        abstract = item.get("abstract", item.get("description", ""))
        source = item.get("source", "")
        topics = item.get("topics", [])
        url = item.get("url", "")

        # Determine target module based on topics
        target_module = self._find_target_module(topics, title, abstract)
        if not target_module:
            return None

        # Determine change type
        change_type = self._determine_change_type(title, abstract)

        # Generate improvement proposal
        title_ar = self._translate_title(title)
        description_ar = self._generate_description_ar(title, abstract)

        # Estimate improvement
        relevance = item.get("relevance_score", 0.5)
        estimated_improvement = relevance * 0.05  # 0-5% estimated improvement

        # Risk assessment
        risk = self._assess_risk(change_type, target_module)

        # Implementation steps
        steps = self._generate_implementation_steps(change_type, target_module)

        return ImprovementProposal(
            title=title[:200],
            title_ar=title_ar,
            description=abstract[:500],
            description_ar=description_ar,
            source_paper=url if item_type == "paper" else "",
            source_repo=url if item_type == "repo" else "",
            target_module=target_module,
            change_type=change_type,
            implementation_steps=steps,
            risk_level=risk,
            estimated_improvement=estimated_improvement,
        )

    def _find_target_module(self, topics: list, title: str, abstract: str) -> str:
        """تحديد الوحدة المستهدفة."""
        text = f"{title} {abstract}".lower()

        for topic, module in TOPIC_MODULE_MAP.items():
            if topic.lower() in text:
                return module

        # Default
        if topics:
            for topic in topics:
                for key, module in TOPIC_MODULE_MAP.items():
                    if topic.lower() in key.lower():
                        return module

        return "mamoun.core"  # Default target

    def _determine_change_type(self, title: str, abstract: str) -> str:
        """تحديد نوع التغيير."""
        text = f"{title} {abstract}".lower()

        if any(w in text for w in ["optimiz", "faster", "efficient", "speed"]):
            return "optimization"
        elif any(w in text for w in ["new", "novel", "framework", "approach"]):
            return "new_feature"
        elif any(w in text for w in ["fix", "bug", "error", "issue"]):
            return "bug_fix"
        else:
            return "new_feature"

    def _translate_title(self, title: str) -> str:
        """ترجمة العنوان (مبسطة)."""
        # Simple translation mapping for common terms
        translations = {
            "advances": "تطورات",
            "framework": "إطار عمل",
            "improving": "تحسين",
            "analysis": "تحليل",
            "arabic": "العربية",
            "language": "لغة",
            "models": "نماذج",
            "challenges": "تحديات",
            "self-improving": "تحسين ذاتي",
            "agentic": "وكيلي",
            "AI": "ذكاء اصطناعي",
        }
        result = title
        for en, ar in translations.items():
            result = result.replace(en, ar)
        return result

    def _generate_description_ar(self, title: str, abstract: str) -> str:
        """توليد وصف عربي للاقتراح."""
        return f"اقتراح تحسين مستوحى من بحث: {title[:100]}. التحليل يشير إلى إمكانية تحسين الأداء عبر دمج التقنيات المذكورة."

    def _assess_risk(self, change_type: str, target_module: str) -> str:
        """تقييم المخاطر."""
        if "safety" in target_module:
            return "high"
        if change_type == "new_feature":
            return "medium"
        if change_type == "optimization":
            return "low"
        return "medium"

    def _generate_implementation_steps(self, change_type: str, target_module: str) -> list[str]:
        """توليد خطوات التنفيذ."""
        steps = [
            "1. مراجعة البحث وتحليل مدى التطابق مع بنية مأمون",
            "2. تصميم التعديلات المطلوبة وإنشاء فرع تطوير",
            "3. تنفيذ التعديلات في بيئة معزولة",
            "4. اختبار التعديلات مع مقاييس الأداء",
        ]

        if change_type == "new_feature":
            steps.append("5. إضافة Feature Flag جديد للقدرة")
            steps.append("6. كتابة اختبارات وحدة للقدرة الجديدة")
        elif change_type == "optimization":
            steps.append("5. مقارنة الأداء قبل وبعد التحسين")
            steps.append("6. التأكد من عدم وجود تراجع في الاختبارات الحالية")

        steps.append("7. طلب موافقة بشرية عبر ApprovalGate")
        steps.append("8. النشر بعد الموافقة ومراقبة الأداء")

        return steps

    def get_proposals(self, status: str = "") -> list[dict]:
        """الحصول على الاقتراحات."""
        if status:
            return [p.to_dict() for p in self._proposals if p.status == status]
        return [p.to_dict() for p in self._proposals]

    def get_status(self) -> dict:
        """حالة مقترح التحسينات."""
        return {
            "enabled": SELF_PROGRAMMING_ENABLED,
            "total_proposals": self._proposal_count,
            "pending_proposals": sum(
                1 for p in self._proposals
                if p.status in (ProposalStatus.DRAFT.value, ProposalStatus.SUBMITTED.value)
            ),
        }

    async def shutdown(self):
        """إيقاف المقترح — يتوافق مع القانون 5."""
        logger.info("ImprovementProposer: Shutdown complete (Law 5 compliant)")
