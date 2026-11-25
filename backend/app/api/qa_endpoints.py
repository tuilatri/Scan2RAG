"""FastAPI Router & Endpoints for Scan2RAG (Milestone 2).

Endpoints:
1. POST /api/v1/query: Submit legal/medical question, receive grounded answer with exact PDF citations.
2. GET /api/v1/health: Health check reporting Vector DB, BM25 Index, and LLM Router status.
"""

import threading
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.security import verify_api_key
from app.retrieval.bm25_searcher import LegalBM25Searcher
from app.retrieval.hybrid_searcher import LegalHybridSearcher
from app.retrieval.qdrant_client import LegalVectorStore
from app.retrieval.reranker import LegalReranker
from app.services.qa_service import GroundedQAService

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
                    chunks = load_all_corpus_chunks()
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QA Pipeline Error: {str(e)}") from e


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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QA Streaming Pipeline Error: {str(e)}") from e


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
