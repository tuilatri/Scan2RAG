"""Core Grounded QA Service linking Retrieval (Hybrid + Reranker) and Generation (LLM Router).

Ensures:
1. Retrieval Latency & Quality tracking.
2. In-line and Structured Citation mapping back to original PDF pages and articles.
3. Fallback when LLM is unavailable or context is insufficient.
"""

import re
import time
from typing import Any

from app.agents.planner import DOCUMENT_TOKENS
from app.guards.scope_guard import SCOPE_REFUSAL_MESSAGE, is_out_of_scope
from app.llm.prompt_templates import STRICT_LEGAL_SYSTEM_PROMPT, GroundedPromptBuilder
from app.llm.router import ModelRouter
from app.retrieval.hybrid_searcher import LegalHybridSearcher
from app.retrieval.reranker import LegalReranker


def resolve_page_number(chunk: dict[str, Any]) -> int:
    """Resolve PDF page from metadata, falling back to '(Trang X)' in breadcrumb."""
    page_num = chunk.get("page_number") or 0
    if not page_num:
        page_nums = chunk.get("page_numbers", []) or []
        page_num = page_nums[0] if page_nums else 0
    if not page_num:
        match = re.search(r"Trang\s+(\d+)", chunk.get("breadcrumb", "") or "")
        if match:
            page_num = match.group(1)
    return int(page_num)


REFUSAL_PHRASE = "Văn bản hiện tại không quy định về trường hợp này."


def needs_grounded_retry(answer: str, chunks: list[dict[str, Any]]) -> bool:
    """A blanket refusal is wrong when relevant chunks were actually retrieved."""
    return bool(chunks) and REFUSAL_PHRASE in answer


DIOPTER_RANGE_PATTERN = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*đến\s*dưới\s*(\d+(?:[.,]\d+)?)\s*độ\b",
    re.IGNORECASE,
)


def normalize_medical_query(query: str) -> str:
    """Turn '3 đến dưới 4 độ' into the corpus form '-3D đến dưới -4D'."""
    return DIOPTER_RANGE_PATTERN.sub(
        lambda match: f"-{match.group(1)}D đến dưới -{match.group(2)}D", query
    )


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

    @staticmethod
    def _has_table_intent(query: str) -> bool:
        lowered = query.lower()
        return any(
            token in lowered
            for token in ("bảng", "phụ lục", "trang nào", "mấy điểm", "bao nhiêu điểm")
        )

    def _prepare_candidates(
        self,
        query: str,
        top_k_retrieval: int,
        filter_superseded: bool,
    ) -> list[dict[str, Any]]:
        table_intent = self._has_table_intent(query)
        effective_k = 50 if table_intent else top_k_retrieval
        candidates = self.hybrid_searcher.search(
            query=query,
            top_k=effective_k,
            filter_superseded=filter_superseded,
        )
        lowered_query = query.lower()
        table_document_ids = list(dict.fromkeys(
            document_id
            for token, document_id in DOCUMENT_TOKENS
            if token in lowered_query
        ))
        if table_intent:
            for document_id in table_document_ids:
                candidates.extend(self.hybrid_searcher.table_chunks_for(document_id))
            if "trang nào" in query.lower() and table_document_ids:
                scoped_tables = [
                    chunk for chunk in candidates
                    if chunk.get("is_table") and chunk.get("document_id") in table_document_ids
                ]
                if scoped_tables:
                    first_page = min(
                        int(chunk.get("page_number") or 0)
                        for chunk in scoped_tables
                        if chunk.get("page_number")
                    )
                    candidates = [
                        chunk for chunk in scoped_tables
                        if int(chunk.get("page_number") or 0) == first_page
                    ]
            seen: set[str] = set()
            deduped: list[dict[str, Any]] = []
            for chunk in candidates:
                chunk_id = str(chunk.get("id", ""))
                if chunk_id and chunk_id in seen:
                    continue
                seen.add(chunk_id)
                deduped.append(chunk)
            candidates = deduped
        return candidates

    def _augment_with_normalized_query(
        self,
        query: str,
        normalized_query: str,
        top_chunks: list[dict[str, Any]],
        top_k_retrieval: int,
        top_k_rerank: int,
    ) -> list[dict[str, Any]]:
        if normalized_query == query:
            return top_chunks
        candidates = self.hybrid_searcher.search(
            query=normalized_query,
            top_k=top_k_retrieval,
            filter_superseded=True,
        )
        extra = self.reranker.rerank(
            query=normalized_query, candidates=candidates, top_k=top_k_rerank
        )
        seen = {chunk.get("id") for chunk in top_chunks}
        merged = [chunk for chunk in extra if chunk.get("id") not in seen] + top_chunks
        return merged[:top_k_rerank]

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

        if is_out_of_scope(query):
            return {
                "query": query,
                "answer": SCOPE_REFUSAL_MESSAGE,
                "citations": [],
                "provider": "scope_guard",
                "model": "rule-based",
                "complexity": "simple",
                "latency_retrieval_ms": 0.0,
                "latency_rerank_ms": 0.0,
                "latency_total_ms": round((time.time() - t_start) * 1000, 1),
            }

        # 1. Hybrid Retrieval (Dense Qdrant + Sparse BM25 fused via RRF)
        t_ret_start = time.time()
        candidates = self._prepare_candidates(query, top_k_retrieval, filter_superseded)
        latency_retrieval_ms = (time.time() - t_ret_start) * 1000

        # 2. Cross-Encoder Rerank (Top 5)
        t_rerank_start = time.time()
        top_chunks = self.reranker.rerank(
            query=query,
            candidates=candidates,
            top_k=top_k_rerank,
        )
        latency_rerank_ms = (time.time() - t_rerank_start) * 1000
        normalized_query = normalize_medical_query(query)
        top_chunks = self._augment_with_normalized_query(
            query, normalized_query, top_chunks, top_k_retrieval, top_k_rerank
        )

        # 3. Format Structured Citations
        citations = []
        for c in top_chunks:
            p_num = resolve_page_number(c)

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
        if needs_grounded_retry(llm_result.get("content", ""), top_chunks):
            retry_prompt = user_prompt + (
                "\n\nCác đoạn trên có chứa dữ liệu liên quan. Hãy nêu giá trị cụ thể "
                "từ bảng hoặc điều khoản và trích dẫn; nếu vẫn thiếu, nêu rõ phần nào thiếu."
            )
            llm_result = self.model_router.generate(
                prompt=retry_prompt,
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

    def _scope_refusal_stream(self) -> Any:
        import json

        yield f"data: {json.dumps({'event': 'status', 'status': 'scope_refusal'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'event': 'citations', 'citations': []}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'event': 'token', 'token': SCOPE_REFUSAL_MESSAGE}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'event': 'done', 'provider': 'scope_guard', 'model': 'rule-based', 'complexity': 'simple', 'latency_total_ms': 0.0}, ensure_ascii=False)}\n\n"

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

        if is_out_of_scope(query):
            yield from self._scope_refusal_stream()
            return

        # Emit immediate status event for <1.0s SSE TTFT
        yield f"data: {json.dumps({'event': 'status', 'status': 'retrieving'}, ensure_ascii=False)}\n\n"

        # 1. Hybrid Search
        candidates = self._prepare_candidates(query, top_k_retrieval, filter_superseded)
        latency_retrieval_ms = (time.time() - t_start) * 1000

        # 2. Cross-Encoder Rerank
        t_rerank_start = time.time()
        top_chunks = self.reranker.rerank(
            query=query,
            candidates=candidates,
            top_k=top_k_rerank,
        )
        latency_rerank_ms = (time.time() - t_rerank_start) * 1000
        normalized_query = normalize_medical_query(query)
        top_chunks = self._augment_with_normalized_query(
            query, normalized_query, top_chunks, top_k_retrieval, top_k_rerank
        )

        # 3. Format Citations
        citations = []
        for c in top_chunks:
            p_num = resolve_page_number(c)

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
        emitted_stages: set[str] = set()
        try:
            for tok, meta in self.model_router.generate_stream(
                prompt=user_prompt,
                system_prompt=STRICT_LEGAL_SYSTEM_PROMPT,
                complexity=complexity,
                temperature=0.0,
            ):
                last_meta = meta
                stage = meta.get("stage")
                if stage and stage not in emitted_stages:
                    emitted_stages.add(stage)
                    yield f"data: {json.dumps({'event': 'status', 'status': stage}, ensure_ascii=False)}\n\n"
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
