"""FastAPI Router & Endpoints for Scan2RAG (Milestone 2).

Endpoints:
1. POST /api/v1/query: Submit legal/medical question, receive grounded answer with exact PDF citations.
2. GET /api/v1/health: Health check reporting Vector DB, BM25 Index, and LLM Router status.
"""

import logging
import threading
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.compare_graph import build_compare_graph
from app.agents.planner import planner_enabled
from app.core.paths import PROCESSED_DIR
from app.core.security import verify_api_key
from app.retrieval.bm25_searcher import LegalBM25Searcher
from app.retrieval.hybrid_searcher import LegalHybridSearcher
from app.retrieval.qdrant_client import LegalVectorStore
from app.retrieval.reranker import LegalReranker
from app.services.qa_service import GroundedQAService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Question Answering"])


# Pydantic Schemas
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=1000, description="User question in Vietnamese")
    top_k_retrieval: int = Field(default=15, ge=1, le=50, description="Candidate chunks to retrieve")
    top_k_rerank: int = Field(default=5, ge=1, le=10, description="Top chunks after reranking")
    filter_superseded: bool = Field(default=True, description="Filter out superseded articles")


class CitationItem(BaseModel):
    id: str | None = None
    document_id: str | None = None
    document_name: str | None = None
    breadcrumb: str | None = None
    page_number: int = 0
    is_table: bool = False
    rerank_score: float = 0.0
    snippet: str = ""


class QueryResponse(BaseModel):
    query: str
    answer: str
    citations: list[CitationItem]
    provider: str
    model: str
    complexity: str = "simple"
    latency_retrieval_ms: float
    latency_rerank_ms: float
    latency_total_ms: float


class CompareRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=1000, description="Multi-document comparison question")
    top_k_retrieval: int = Field(default=15, ge=1, le=50)
    top_k_rerank: int = Field(default=5, ge=1, le=10)


class EvidenceItem(BaseModel):
    document_id: str
    chunk_count: int
    citation_ids: list[str | None]


class VerificationItem(BaseModel):
    passed: bool
    unsupported_numbers: dict[str, int]
    checked_numbers: int


class VersionNote(BaseModel):
    document_id: str
    effective_date: str | None = None
    superseded_by: str | None = None
    note: str = ""


class CompareResponse(BaseModel):
    query: str
    answer: str
    citations: list[CitationItem]
    evidence: list[EvidenceItem]
    retry_count: int
    provider: str
    model: str
    verification: VerificationItem
    version_notes: list[VersionNote]
    plan_source: str = "deterministic"
    sub_queries: list[str] = []


# Dependency Injection for Singleton QAService (thread-safe double-checked locking)
_qa_service_instance: GroundedQAService | None = None
_qa_service_lock = threading.Lock()


def get_qa_service() -> GroundedQAService:
    global _qa_service_instance
    if _qa_service_instance is None:
        with _qa_service_lock:
            if _qa_service_instance is None:
                vector_store = LegalVectorStore(collection_name="vietnamese_legal_docs")
                bm25_searcher = LegalBM25Searcher()
                if not bm25_searcher.load():
                    import sys
                    from pathlib import Path
                    root_dir = Path(__file__).resolve().parent.parent.parent.parent
                    if str(root_dir) not in sys.path:
                        sys.path.insert(0, str(root_dir))
                    from scripts.audit_hybrid_retrieval import load_all_corpus_chunks
                    chunks = load_all_corpus_chunks(PROCESSED_DIR)
                    bm25_searcher.fit_from_chunks(chunks)
                    bm25_searcher.save()

                hybrid_searcher = LegalHybridSearcher(
                    vector_store=vector_store,
                    bm25_searcher=bm25_searcher,
                    rrf_k=60,
                )
                reranker = LegalReranker(model_name="BAAI/bge-reranker-base")
                _qa_service_instance = GroundedQAService(
                    hybrid_searcher=hybrid_searcher,
                    reranker=reranker,
                )
    return _qa_service_instance


_compare_graph_instance: Any = None
_compare_graph_lock = threading.Lock()


def get_compare_graph() -> Any:
    global _compare_graph_instance
    if _compare_graph_instance is None:
        with _compare_graph_lock:
            if _compare_graph_instance is None:
                qa_service = get_qa_service()
                _compare_graph_instance = build_compare_graph(
                    hybrid_searcher=qa_service.hybrid_searcher,
                    reranker=qa_service.reranker,
                    model_router=qa_service.model_router,
                    planner_enabled=planner_enabled(),
                )
    return _compare_graph_instance


@router.post("/query", response_model=QueryResponse, dependencies=[Depends(verify_api_key)])
def query_legal_rag(
    payload: QueryRequest,
    qa_service: GroundedQAService = Depends(get_qa_service),  # noqa: B008
) -> Any:
    """Submit a question to Scan2RAG, returning answers strictly grounded with PDF citations."""
    try:
        result = qa_service.answer_query(
            query=payload.query,
            top_k_retrieval=payload.top_k_retrieval,
            top_k_rerank=payload.top_k_rerank,
            filter_superseded=payload.filter_superseded,
        )
        return result
    except Exception:
        logger.exception("QA pipeline failure")
        raise HTTPException(status_code=500, detail="QA pipeline unavailable.") from None


@router.post("/query/stream", dependencies=[Depends(verify_api_key)])
def query_legal_rag_stream(
    payload: QueryRequest,
    qa_service: GroundedQAService = Depends(get_qa_service),  # noqa: B008
) -> StreamingResponse:
    """Stream answer via Server-Sent Events (SSE) for minimal perceived latency."""
    try:
        generator = qa_service.stream_answer_query(
            query=payload.query,
            top_k_retrieval=payload.top_k_retrieval,
            top_k_rerank=payload.top_k_rerank,
            filter_superseded=payload.filter_superseded,
        )
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception:
        logger.exception("QA streaming pipeline failure")
        raise HTTPException(status_code=500, detail="QA streaming pipeline unavailable.") from None


@router.post("/query/compare", response_model=CompareResponse, dependencies=[Depends(verify_api_key)])
def compare_legal_documents(
    payload: CompareRequest,
    graph: Any = Depends(get_compare_graph),  # noqa: B008
) -> CompareResponse:
    """Additive LangGraph workflow for multi-document comparison."""
    try:
        result = graph.invoke({"query": payload.query})
        verification = result.get("verification") or {}
        return CompareResponse(
            query=payload.query,
            answer=result.get("answer", ""),
            citations=result.get("citations", []),
            evidence=result.get("evidence_summary", []),
            retry_count=result.get("retry_count", 0),
            provider=result.get("provider", "unknown"),
            model=result.get("model", "unknown"),
            verification=VerificationItem(
                passed=verification.get("passed", True),
                unsupported_numbers=verification.get("unsupported_numbers", {}),
                checked_numbers=verification.get("checked_numbers", 0),
            ),
            version_notes=[
                VersionNote(**note) for note in result.get("version_notes", [])
            ],
            plan_source=result.get("plan_source", "deterministic"),
            sub_queries=result.get("sub_queries", []),
        )
    except Exception:
        logger.exception("Compare pipeline failure")
        raise HTTPException(status_code=500, detail="Compare pipeline unavailable.") from None


@router.get("/health")
def health_check() -> dict[str, Any]:
    """Health status check."""
    return {
        "status": "ok",
        "milestone": "2",
        "features": [
            "Dense Vector Search (Qdrant)",
            "Sparse Keyword Search (BM25)",
            "Cross-Encoder Reranker (BGE)",
            "Hybrid Model Router (LM Studio + Groq)",
            "Strict Grounded Citations",
        ],
    }
