"""Additive LangGraph workflow for multi-document legal comparison."""

from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.planner import detect_documents, plan_subqueries
from app.agents.state import CompareState
from app.agents.verification import extract_numbers, unsupported_numbers
from app.chunking.semantic_chunker import SemanticLegalChunker
from app.llm.prompt_templates import STRICT_LEGAL_SYSTEM_PROMPT, GroundedPromptBuilder
from app.services.qa_service import resolve_page_number

MAX_RETRIES = 1
MAX_VERIFY_RETRIES = 1
PREFERRED_DOC = "thông_tư_88"
SUPERSEDED_BY = {"thông_tư_105": "thông_tư_106"}
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
    planner_enabled: bool = False,
    checkpointer: Any = None,
):
    def retrieve_for(sub_query: str, limit: int, document_id: str | None = None):
        candidates = hybrid_searcher.search(
            query=sub_query,
            top_k=limit,
            filter_superseded=True,
            document_id=document_id,
        )
        if document_id and any(
            token in sub_query.lower() for token in ("bảng", "điểm", "cận thị", "thị lực")
        ):
            seen = {str(item.get("id")) for item in candidates}
            for table_chunk in hybrid_searcher.table_chunks_for(document_id):
                if str(table_chunk.get("id")) not in seen:
                    candidates.append(table_chunk)
        chunks = reranker.rerank(
            query=sub_query, candidates=candidates, top_k=top_k_rerank
        )
        return chunks, [_citation(chunk) for chunk in chunks]

    def plan(state: CompareState):
        if planner_enabled:
            planned = plan_subqueries(state["query"], model_router)
            documents = planned["documents"]
            sub_queries = planned["sub_queries"]
            source = planned["source"]
        else:
            documents = detect_documents(state["query"])
            sub_queries = [f'{state["query"]} — {document_id}' for document_id in documents]
            source = "deterministic"
        sub_query_docs = (
            [documents[index % len(documents)] for index in range(len(sub_queries))]
            if documents
            else []
        )
        history = list(state.get("history", []))
        history.append({"query": state["query"], "plan_source": source})
        return {
            "target_docs": documents,
            "sub_queries": sub_queries,
            "sub_query_docs": sub_query_docs,
            "plan_source": source,
            "retry_count": 0,
            "history": history,
        }

    def retrieve(state: CompareState):
        evidence: list[dict[str, Any]] = []
        citations: list[dict[str, Any]] = []
        for sub_query, document_id in zip(
            state["sub_queries"], state["sub_query_docs"], strict=False
        ):
            chunks, cites = retrieve_for(sub_query, top_k_retrieval, document_id)
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
                f'{state["query"]} — {document_id}',
                min(top_k_retrieval * 2, 50),
                document_id,
            )
            evidence.append({"sub_query": document_id, "chunks": chunks, "citations": cites})
        citations = [citation for item in evidence for citation in item["citations"]]
        return {"evidence": evidence, "citations": citations, "retry_count": state["retry_count"] + 1}

    def synthesize(state: CompareState):
        chunks = [chunk for item in state["evidence"] for chunk in item["chunks"]]
        prompt = GroundedPromptBuilder.build_qa_prompt(state["query"], chunks)
        notes = state.get("version_notes") or []
        if notes:
            lines = []
            for note in notes:
                line = f"- {note['document_id']}: hiệu lực {note['effective_date'] or 'không rõ'}"
                if note.get("superseded_by"):
                    line += f", bị thay thế bởi {note['superseded_by']}"
                if note.get("note"):
                    line += f". {note['note']}"
                lines.append(line)
            prompt += "\n\nTHÔNG TIN HIỆU LỰC:\n" + "\n".join(lines)
        if state.get("verify_count", 0) > 0:
            prompt += (
                "\n\nCHỈ dùng số liệu có trong các đoạn trích trên. "
                "Nếu không có dữ liệu, hãy nói rõ là không có."
            )
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

    def resolve_versions(state: CompareState):
        dates = SemanticLegalChunker.OFFICIAL_EFFECTIVE_DATES
        notes = []
        for document_id in state["target_docs"]:
            note = {
                "document_id": document_id,
                "effective_date": dates.get(document_id),
                "superseded_by": SUPERSEDED_BY.get(document_id),
                "note": "",
            }
            if document_id == "thông_tư_105":
                note["note"] = (
                    "Chỉ dùng quy định còn hiệu lực; phần đã bị TT106 sửa đổi "
                    "không được trình bày là hiện hành."
                )
            if document_id == PREFERRED_DOC:
                note["note"] = "VBHN 88 là văn bản hợp nhất, được ưu tiên đối chiếu."
            notes.append(note)
        return {"version_notes": notes}

    def verify_answer(state: CompareState):
        # Use the same full chunk content the LLM saw in the prompt, not the
        # 250-char citation snippets (which would flag valid numbers as hallucinations).
        version_text = " ".join(
            f"{note.get('effective_date') or ''} {note.get('superseded_by') or ''}"
            for note in state.get("version_notes", [])
        )
        chunk_texts = []
        for item in state["evidence"]:
            for chunk in item["chunks"]:
                header = " ".join(
                    str(chunk[key])
                    for key in ("document_name", "document_id", "breadcrumb", "page_number")
                    if chunk.get(key)
                )
                chunk_texts.append(f"{header} {chunk.get('content', '')}")
        evidence_text = state["query"] + " " + version_text + " " + " ".join(chunk_texts)
        unsupported = unsupported_numbers(state["answer"], evidence_text)
        return {
            "verification": {
                "passed": not unsupported,
                "unsupported_numbers": unsupported,
                "checked_numbers": len(extract_numbers(state["answer"])),
            },
            "verify_count": state.get("verify_count", 0) + 1,
        }

    def route_verify(state: CompareState):
        if not state["verification"]["passed"] and state["verify_count"] <= MAX_VERIFY_RETRIES:
            return "synthesize"
        return "end"

    graph = StateGraph(CompareState)
    graph.add_node("plan", plan)
    graph.add_node("retrieve", retrieve)
    graph.add_node("evidence_check", evidence_check)
    graph.add_node("retry", retry)
    graph.add_node("synthesize", synthesize)
    graph.add_node("resolve_versions", resolve_versions)
    graph.add_node("verify_answer", verify_answer)
    graph.set_entry_point("plan")
    graph.add_edge("plan", "retrieve")
    graph.add_edge("retrieve", "evidence_check")
    graph.add_conditional_edges(
        "evidence_check", route, {"retry": "retry", "synthesize": "resolve_versions"}
    )
    graph.add_edge("resolve_versions", "synthesize")
    graph.add_edge("retry", "evidence_check")
    graph.add_edge("synthesize", "verify_answer")
    graph.add_conditional_edges(
        "verify_answer", route_verify, {"synthesize": "synthesize", "end": END}
    )
    return graph.compile(checkpointer=checkpointer) if checkpointer else graph.compile()
