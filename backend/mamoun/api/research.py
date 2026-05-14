"""Research API — Research Monitor + Deep Research endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional

from mamoun.api.deps import require_auth
from mamoun.research_monitor import ResearchMonitor

router = APIRouter(prefix="/research", tags=["research"])

_monitor: Optional[ResearchMonitor] = None


def get_monitor() -> ResearchMonitor:
    global _monitor
    if _monitor is None:
        _monitor = ResearchMonitor()
    return _monitor


class ProcessResultsRequest(BaseModel):
    results: list[dict]


class ResearchDeepRequest(BaseModel):
    """v40.0 Fusion: Deep research request (simplified model)."""
    query: str
    depth: int = 3
    verify: bool = True


class DeepResearchRequest(BaseModel):
    """v36.1: Deep research request with proper input formatting.
    
    The 'query' field accepts a clear research question or topic string.
    The 'depth' controls how thorough the research is (1-4).
    The 'verify' flag enables cross-source fact verification.
    
    Example:
        query: "How does transformer attention mechanism work?"
        depth: 3
        verify: True
    
    The query should be a single clear question, not a list of keywords.
    For best results, write the query as a full question in the language
    of your choice (Arabic or English).
    """
    query: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="سؤال البحث — A clear research question or topic (3-2000 chars)",
        examples=[
            "كيف تعمل آلية الانتباه في المحولات؟",
            "How does iterative self-improvement work in AI systems?",
        ]
    )
    depth: int = Field(
        default=3,
        ge=1,
        le=4,
        description="عمق البحث: 1=سريع، 2=قياسي، 3=عميق، 4=شامل"
    )
    verify: bool = Field(
        default=True,
        description="التحقق المتقاطع من الحقائق"
    )


@router.get("/status")
async def research_status():
    return get_monitor().get_status()


@router.post("/process", dependencies=[Depends(require_auth)])
async def process_results(req: ProcessResultsRequest):
    new_papers = get_monitor().process_search_results(req.results)
    return {
        "new_papers_count": len(new_papers),
        "papers": [p.to_dict() for p in new_papers],
    }


@router.get("/papers")
async def get_papers(min_relevance: float = 0.3, limit: int = 10):
    papers = get_monitor().get_high_relevance_papers(min_relevance, limit)
    return {"papers": papers}


@router.get("/trust-network")
async def trust_network_info():
    from mamoun.research_monitor import EpistemicTrustNetwork
    net = EpistemicTrustNetwork()
    return {
        "trust_levels": [l.value for l in EpistemicTrustNetwork.TRUST_RULES.values()],
        "top_tier_venues": list(net.TOP_TIER_VENUES),
        "major_labs": list(net.MAJOR_LABS),
    }


@router.post("/deep", dependencies=[Depends(require_auth)])
async def deep_research(req: DeepResearchRequest):
    """بحث عميق — Run a deep research query with multi-source verification.
    
    Accepts a structured request with:
    - query: A clear research question (not keywords)
    - depth: How thorough the search should be (1-4)
    - verify: Whether to cross-verify facts across sources
    
    Returns a comprehensive research report with:
    - Sources with credibility ratings
    - Extracted facts with confidence scores
    - Contradiction detection
    - Analysis and recommendations
    """
    try:
        from mamoun.core.deep_research_engine import DeepResearchEngine
        from mamoun.core.llm_client import get_llm_client
        
        llm = get_llm_client()
        engine = DeepResearchEngine(llm_client=llm)
        
        result = await engine.research(
            query=req.query,
            depth=req.depth,
            verify=req.verify,
        )
        
        return {
            "status": "success",
            "message": f"تم البحث العميق عن: {req.query[:100]}",
            "report": result,
        }
        
    except ImportError as e:
        return {
            "status": "error",
            "message": f"محرك البحث العميق غير متوفر: {str(e)}",
            "report": None,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"خطأ في البحث العميق: {str(e)}",
            "report": None,
        }
