from unittest.mock import Mock

from app.agents.compare_graph import build_compare_graph
from app.api.qa_endpoints import CompareResponse, VerificationItem, VersionNote

CHUNK_105 = {
    "id": "c105",
    "document_id": "thông_tư_105",
    "content": "Cận thị 3 điểm",
    "breadcrumb": "TT105",
}
CHUNK_106 = {
    "id": "c106",
    "document_id": "thông_tư_106",
    "content": "Quy định mới",
    "breadcrumb": "TT106",
}
GENERATION = {
    "content": "Theo TT105: 3 điểm",
    "provider": "lm_studio_local",
    "model": "qwen2.5-1.5b-instruct",
}
QUERY = "So sánh Thông tư 105 và Thông tư 106"


def _graph():
    searcher = Mock()
    searcher.search.return_value = []
    reranker = Mock()
    reranker.rerank.side_effect = [[CHUNK_105], [CHUNK_106]]
    router = Mock()
    router.generate.return_value = GENERATION
    return build_compare_graph(searcher, reranker, router), searcher, router


def test_version_notes_include_effective_dates_and_supersession():
    graph, _, _ = _graph()
    result = graph.invoke({"query": QUERY})
    notes = {note["document_id"]: note for note in result["version_notes"]}
    assert notes["thông_tư_105"]["effective_date"] == "2024-01-01"
    assert notes["thông_tư_105"]["superseded_by"] == "thông_tư_106"
    assert notes["thông_tư_106"]["effective_date"] == "2025-01-01"
    assert notes["thông_tư_106"]["superseded_by"] is None


def test_retrieval_keeps_superseded_filter():
    graph, searcher, _ = _graph()
    graph.invoke({"query": QUERY})
    assert searcher.search.call_count == 2
    assert all(
        call.kwargs.get("filter_superseded") is True
        for call in searcher.search.call_args_list
    )


def test_prompt_and_response_carry_version_notes():
    graph, _, router = _graph()
    result = graph.invoke({"query": QUERY})
    assert "THÔNG TIN HIỆU LỰC" in router.generate.call_args.kwargs["prompt"]
    response = CompareResponse(
        query=QUERY,
        answer=result["answer"],
        citations=result["citations"],
        evidence=result["evidence_summary"],
        retry_count=result["retry_count"],
        provider=result["provider"],
        model=result["model"],
        verification=VerificationItem(**result["verification"]),
        version_notes=[VersionNote(**note) for note in result["version_notes"]],
    )
    assert response.version_notes[0].document_id == "thông_tư_105"
