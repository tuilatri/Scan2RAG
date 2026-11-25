"""Core Grounded QA Service linking Retrieval (Hybrid + Reranker) and Generation (LLM Router).

Ensures:
1. Retrieval Latency & Quality tracking.
2. In-line and Structured Citation mapping back to original PDF pages and articles.
3. Fallback when LLM is unavailable or context is insufficient.
"""

import re
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
            p_num = c.get("page_number", 0)
            if not p_num:
                p_nums = c.get("page_numbers", [])
                p_num = p_nums[0] if p_nums else 0
            if not p_num:
                # Fallback: extract page number from breadcrumb, e.g. "(Trang 23)"
                m = re.search(r"Trang\s+(\d+)", c.get("breadcrumb", "") or "")
                if m:
                    p_num = int(m.group(1))

            citations.append({
                "id": c.get("id"),
                "document_id": c.get("document_id"),
                "document_name": c.get("document_name"),
                "breadcrumb": c.get("breadcrumb"),
                "page_number": p_num,
                "is_table": c.get("is_table", False),
                "rerank_score": c.get("rerank_score", 0.0),
                "snippet": c.get("content", "")[:250],
            })

        # 4. Determine Query Complexity & Generate Answer
        complexity = self.model_router.classify_complexity(query, top_chunks)
        user_prompt = GroundedPromptBuilder.build_qa_prompt(query, top_chunks)
        llm_result = self.model_router.generate(
            prompt=user_prompt,
            system_prompt=STRICT_LEGAL_SYSTEM_PROMPT,
            complexity=complexity,
            temperature=0.0,
        )

        latency_total_ms = (time.time() - t_start) * 1000

        return {
            "query": query,
            "answer": llm_result.get("content", ""),
            "citations": citations,
            "provider": llm_result.get("provider", "unknown"),
            "model": llm_result.get("model", "unknown"),
            "complexity": complexity,
            "latency_retrieval_ms": round(latency_retrieval_ms, 1),
            "latency_rerank_ms": round(latency_rerank_ms, 1),
            "latency_total_ms": round(latency_total_ms, 1),
        }

    def stream_answer_query(
        self,
        query: str,
        top_k_retrieval: int = 15,
        top_k_rerank: int = 5,
        filter_superseded: bool = True,
    ) -> Any:
        """Stream answer via SSE events: 'citations', 'token', 'done'."""
        import json

        t_start = time.time()

        # Emit immediate status event for <1.0s SSE TTFT
        yield f"data: {json.dumps({'event': 'status', 'status': 'retrieving'}, ensure_ascii=False)}\n\n"

        # 1. Hybrid Search
        candidates = self.hybrid_searcher.search(
            query=query,
            top_k=top_k_retrieval,
            filter_superseded=filter_superseded,
        )
        latency_retrieval_ms = (time.time() - t_start) * 1000

        # 2. Cross-Encoder Rerank
        t_rerank_start = time.time()
        top_chunks = self.reranker.rerank(
            query=query,
            candidates=candidates,
            top_k=top_k_rerank,
        )
        latency_rerank_ms = (time.time() - t_rerank_start) * 1000

        # 3. Format Citations
        citations = []
        for c in top_chunks:
            p_num = c.get("page_number", 0)
            if not p_num:
                p_nums = c.get("page_numbers", [])
                p_num = p_nums[0] if p_nums else 0

            citations.append({
                "id": c.get("id"),
                "document_id": c.get("document_id"),
                "document_name": c.get("document_name"),
                "breadcrumb": c.get("breadcrumb"),
                "page_number": p_num,
                "is_table": c.get("is_table", False),
                "rerank_score": c.get("rerank_score", 0.0),
                "snippet": c.get("content", "")[:250],
            })

        # Yield citations event immediately (TTFB < 1.0s)
        yield f"data: {json.dumps({'event': 'citations', 'citations': citations, 'latency_retrieval_ms': round(latency_retrieval_ms, 1), 'latency_rerank_ms': round(latency_rerank_ms, 1)}, ensure_ascii=False)}\n\n"

        # 4. Stream LLM Generation
        complexity = self.model_router.classify_complexity(query, top_chunks)
        user_prompt = GroundedPromptBuilder.build_qa_prompt(query, top_chunks)

        last_meta = {}
        try:
            for tok, meta in self.model_router.generate_stream(
                prompt=user_prompt,
                system_prompt=STRICT_LEGAL_SYSTEM_PROMPT,
                complexity=complexity,
                temperature=0.0,
            ):
                last_meta = meta
                yield f"data: {json.dumps({'event': 'token', 'token': tok}, ensure_ascii=False)}\n\n"
        except Exception:
            yield f"data: {json.dumps({'event': 'error', 'message': 'Đã xảy ra lỗi khi sinh câu trả lời.'}, ensure_ascii=False)}\n\n"
            return

        latency_total_ms = (time.time() - t_start) * 1000

        # Yield done event
        done_payload = {
            "event": "done",
            "provider": last_meta.get("provider", "unknown"),
            "model": last_meta.get("model", "unknown"),
            "complexity": complexity,
            "latency_total_ms": round(latency_total_ms, 1),
        }
        yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
