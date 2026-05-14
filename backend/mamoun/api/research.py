"""Research API — Research Monitor + Deep Research endpoints.

v62 FIX: Fixed parameter mismatch — research() expects depth as string,
not int. The API now maps int depth (1-4) to ResearchDepth enum values.
"""

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
    """v62: Deep research request with proper input formatting.
    
    The 'query' field accepts a clear research question or topic string.
    The 'depth' controls how thorough the research is (1-4).
    The 'verify' flag enables cross-source fact verification.
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


def _map_depth(depth_int: int) -> str:
    """Map integer depth (1-4) to ResearchDepth string."""
    mapping = {
        1: "quick",
        2: "standard", 
        3: "deep",
        4: "deep",  # 4 is comprehensive, maps to "deep" (the deepest available)
    }
    return mapping.get(depth_int, "standard")


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
    
    v62 FIX: Correctly maps integer depth to string ResearchDepth values.
    """
    try:
        from mamoun.core.deep_research_engine import DeepResearchEngine
        from mamoun.core.llm_client import get_llm_client
        
        llm = get_llm_client()
        engine = DeepResearchEngine(llm_client=llm)
        
        # Map int depth to string — THIS WAS THE BUG
        depth_str = _map_depth(req.depth)
        
        result = await engine.research(
            query=req.query,
            depth=depth_str,
        )
        
        # Build response
        response_data = {
            "status": "success",
            "message": f"تم البحث العميق عن: {req.query[:100]}",
            "report": {
                "query": result.query,
                "depth": result.depth.value if hasattr(result.depth, 'value') else str(result.depth),
                "summary": result.summary,
                "key_findings": result.key_findings,
                "contradictions": result.contradictions,
                "confidence": result.confidence,
                "sources_count": len(result.sources),
                "sources_searched": result.sources_searched,
                "content_extracted": result.content_extracted,
                "total_latency_ms": result.total_latency_ms,
                "claims": [
                    {
                        "claim": c.claim,
                        "verification": c.verification,
                        "confidence": c.confidence,
                        "supporting_sources": c.sources,
                        "contradicting_sources": c.contradicting_sources,
                    }
                    for c in result.claims
                ] if result.claims else [],
                "sources": [
                    {
                        "url": s.url,
                        "title": s.title,
                        "quality_score": s.quality_score,
                        "extraction_method": s.extraction_method,
                        "extraction_success": s.extraction_success,
                    }
                    for s in result.sources
                ] if result.sources else [],
            },
            "verify": req.verify,  # Echo back for client reference
        }
        
        return response_data
        
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
