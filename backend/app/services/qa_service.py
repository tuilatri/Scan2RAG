"""Core Grounded QA Service linking Retrieval (Hybrid + Reranker) and Generation (LLM Router).

Ensures:
1. Retrieval Latency & Quality tracking.
2. In-line and Structured Citation mapping back to original PDF pages and articles.
3. Fallback when LLM is unavailable or context is insufficient.
"""

import time
from typing import Any

from app.llm.prompt_templates import STRICT_LEGAL_SYSTEM_PROMPT, GroundedPromptBuilder
from app.llm.router import ModelRouter
from app.retrieval.hybrid_searcher import LegalHybridSearcher
from app.retrieval.reranker import LegalReranker


class GroundedQAService:
    """End-to-end question answering pipeline with rigorous grounding and citations."""

    def __init__(
        self,
        hybrid_searcher: LegalHybridSearcher,
        reranker: LegalReranker,
        model_router: ModelRouter | None = None,
    ):
        self.hybrid_searcher = hybrid_searcher
        self.reranker = reranker
        self.model_router = model_router or ModelRouter()

    def answer_query(
        self,
        query: str,
        top_k_retrieval: int = 15,
        top_k_rerank: int = 5,
        filter_superseded: bool = True,
    ) -> dict[str, Any]:
        """Execute end-to-end grounded legal QA.

        Returns:
            Dict containing:
            {
                "query": str,
                "answer": str,
                "citations": list[dict],
                "provider": str,
                "model": str,
                "latency_retrieval_ms": float,
                "latency_rerank_ms": float,
                "latency_total_ms": float,
            }
        """
        t_start = time.time()

        # 1. Hybrid Retrieval (Dense Qdrant + Sparse BM25 fused via RRF)
        t_ret_start = time.time()
        candidates = self.hybrid_searcher.search(
            query=query,
            top_k=top_k_retrieval,
            filter_superseded=filter_superseded,
        )
        latency_retrieval_ms = (time.time() - t_ret_start) * 1000

        # 2. Cross-Encoder Rerank (Top 5)
        t_rerank_start = time.time()
        top_chunks = self.reranker.rerank(
            query=query,
            candidates=candidates,
            top_k=top_k_rerank,
        )
        latency_rerank_ms = (time.time() - t_rerank_start) * 1000

        # 3. Format Structured Citations
        citations = []
        for c in top_chunks:
            citations.append({
                "id": c.get("id"),
                "document_id": c.get("document_id"),
                "document_name": c.get("document_name"),
                "breadcrumb": c.get("breadcrumb"),
                "page_number": c.get("page_number", 0),
                "is_table": c.get("is_table", False),
                "rerank_score": c.get("rerank_score", 0.0),
                "snippet": c.get("content", "")[:250],
            })

        # 4. Generate LLM Answer
        user_prompt = GroundedPromptBuilder.build_qa_prompt(query, top_chunks)
        llm_result = self.model_router.generate(
            prompt=user_prompt,
            system_prompt=STRICT_LEGAL_SYSTEM_PROMPT,
            temperature=0.0,
        )

        latency_total_ms = (time.time() - t_start) * 1000

        return {
            "query": query,
            "answer": llm_result.get("content", ""),
            "citations": citations,
            "provider": llm_result.get("provider", "unknown"),
            "model": llm_result.get("model", "unknown"),
            "latency_retrieval_ms": round(latency_retrieval_ms, 1),
            "latency_rerank_ms": round(latency_rerank_ms, 1),
            "latency_total_ms": round(latency_total_ms, 1),
        }
