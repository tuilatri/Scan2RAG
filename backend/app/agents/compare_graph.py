"""Additive LangGraph workflow for multi-document legal comparison."""

from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.state import CompareState
from app.llm.prompt_templates import STRICT_LEGAL_SYSTEM_PROMPT, GroundedPromptBuilder
from app.services.qa_service import resolve_page_number

MAX_RETRIES = 1
DOCUMENT_TOKENS = (
    ("105", "thông_tư_105"),
    ("106", "thông_tư_106"),
    ("88", "thông_tư_88"),
    ("hợp nhất", "thông_tư_88"),
)
FALLBACK_DOCS = ("thông_tư_105", "thông_tư_106")


def detect_documents(query: str) -> list[str]:
    lowered = query.lower()
    found: list[str] = []
    for token, document_id in DOCUMENT_TOKENS:
        if token in lowered and document_id not in found:
            found.append(document_id)
    for document_id in FALLBACK_DOCS:
        if len(found) >= 2:
            break
        if document_id not in found:
            found.append(document_id)
    return found


def _citation(chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": chunk.get("id"),
        "document_id": chunk.get("document_id"),
        "document_name": chunk.get("document_name"),
        "breadcrumb": chunk.get("breadcrumb"),
        "page_number": resolve_page_number(chunk),
        "is_table": chunk.get("is_table", False),
        "rerank_score": chunk.get("rerank_score", 0.0),
        "snippet": chunk.get("content", "")[:250],
    }


def build_compare_graph(
    hybrid_searcher: Any,
    reranker: Any,
    model_router: Any,
    top_k_retrieval: int = 15,
    top_k_rerank: int = 5,
):
    def retrieve_for(sub_query: str, limit: int):
        candidates = hybrid_searcher.search(
            query=sub_query, top_k=limit, filter_superseded=True
        )
        chunks = reranker.rerank(
            query=sub_query, candidates=candidates, top_k=top_k_rerank
        )
        return chunks, [_citation(chunk) for chunk in chunks]

    def plan(state: CompareState):
        documents = detect_documents(state["query"])
        return {
            "target_docs": documents,
            "sub_queries": [f'{state["query"]} — {document_id}' for document_id in documents],
            "retry_count": 0,
        }

    def retrieve(state: CompareState):
        evidence: list[dict[str, Any]] = []
        citations: list[dict[str, Any]] = []
        for sub_query in state["sub_queries"]:
            chunks, cites = retrieve_for(sub_query, top_k_retrieval)
            evidence.append({"sub_query": sub_query, "chunks": chunks, "citations": cites})
            citations.extend(cites)
        return {"evidence": evidence, "citations": citations}

    def evidence_check(state: CompareState):
        covered = {
            citation.get("document_id")
            for citation in state["citations"]
            if citation.get("document_id")
        }
        return {
            "missing": [
                document_id
                for document_id in state["target_docs"]
                if document_id not in covered
            ]
        }

    def route(state: CompareState):
        if state["missing"] and state["retry_count"] < MAX_RETRIES:
            return "retry"
        return "synthesize"

    def retry(state: CompareState):
        evidence = list(state["evidence"])
        for document_id in state["missing"]:
            chunks, cites = retrieve_for(
                f'{state["query"]} — {document_id}', min(top_k_retrieval * 2, 50)
            )
            evidence.append({"sub_query": document_id, "chunks": chunks, "citations": cites})
        citations = [citation for item in evidence for citation in item["citations"]]
        return {"evidence": evidence, "citations": citations, "retry_count": state["retry_count"] + 1}

    def synthesize(state: CompareState):
        chunks = [chunk for item in state["evidence"] for chunk in item["chunks"]]
        prompt = GroundedPromptBuilder.build_qa_prompt(state["query"], chunks)
        result = model_router.generate(
            prompt=prompt,
            system_prompt=STRICT_LEGAL_SYSTEM_PROMPT,
            complexity="complex",
            temperature=0.0,
        )
        summary = []
        for document_id in state["target_docs"]:
            cites = [c for c in state["citations"] if c.get("document_id") == document_id]
            summary.append({
                "document_id": document_id,
                "chunk_count": len(cites),
                "citation_ids": [c.get("id") for c in cites],
            })
        return {
            "answer": result.get("content", ""),
            "provider": result.get("provider", "unknown"),
            "model": result.get("model", "unknown"),
            "evidence_summary": summary,
        }

    graph = StateGraph(CompareState)
    graph.add_node("plan", plan)
    graph.add_node("retrieve", retrieve)
    graph.add_node("evidence_check", evidence_check)
    graph.add_node("retry", retry)
    graph.add_node("synthesize", synthesize)
    graph.set_entry_point("plan")
    graph.add_edge("plan", "retrieve")
    graph.add_edge("retrieve", "evidence_check")
    graph.add_conditional_edges(
        "evidence_check", route, {"retry": "retry", "synthesize": "synthesize"}
    )
    graph.add_edge("retry", "evidence_check")
    graph.add_edge("synthesize", END)
    return graph.compile()
