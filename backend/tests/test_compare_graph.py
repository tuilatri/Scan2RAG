from unittest.mock import Mock

from app.agents.compare_graph import build_compare_graph

CHUNK_105 = {"id": "c105", "document_id": "thông_tư_105", "content": "Cận thị -3D đến -4D: 3 điểm", "breadcrumb": "TT105 > Chương V"}
CHUNK_106 = {"id": "c106", "document_id": "thông_tư_106", "content": "Thông tư 106 sửa đổi", "breadcrumb": "TT106 > Điều 1"}
GENERATION = {"content": "So sánh...", "provider": "lm_studio_local", "model": "qwen2.5-1.5b-instruct"}


def _mocks(rerank_results):
    searcher = Mock()
    searcher.search.return_value = []
    searcher.table_chunks_for.return_value = []
    reranker = Mock()
    reranker.rerank.side_effect = list(rerank_results)
    router = Mock()
    router.generate.return_value = GENERATION
    return searcher, reranker, router


def test_plan_extracts_documents():
    searcher, reranker, router = _mocks([[CHUNK_105], [CHUNK_106]])
    result = build_compare_graph(searcher, reranker, router).invoke(
        {"query": "So sánh Thông tư 105 và Thông tư 106 về cận thị"}
    )
    assert result["target_docs"] == ["thông_tư_105", "thông_tư_106"]
    assert len(result["sub_queries"]) == 2


def test_missing_evidence_triggers_one_retry():
    searcher, reranker, router = _mocks([[CHUNK_105], [CHUNK_105], [CHUNK_106]])
    result = build_compare_graph(searcher, reranker, router).invoke(
        {"query": "So sánh Thông tư 105 và Thông tư 106"}
    )
    assert result["retry_count"] == 1
    assert reranker.rerank.call_count == 3
    assert {c["document_id"] for c in result["citations"]} == {
        "thông_tư_105",
        "thông_tư_106",
    }


def test_retry_is_bounded():
    searcher, reranker, router = _mocks([[CHUNK_105], [CHUNK_105], [CHUNK_105]])
    result = build_compare_graph(searcher, reranker, router).invoke(
        {"query": "So sánh Thông tư 105 và Thông tư 106"}
    )
    assert result["retry_count"] == 1
    assert reranker.rerank.call_count == 3
    assert result["answer"] == GENERATION["content"]


def test_citation_page_number_is_not_flagged_as_unsupported():
    chunk_with_page = {
        "id": "c50",
        "document_id": "thông_tư_105",
        "content": "Cận thị -3D đến -4D: 4 điểm",
        "breadcrumb": "TT105 > Bảng phụ lục",
        "page_number": 50,
    }
    searcher, reranker, router = _mocks([[chunk_with_page], [CHUNK_106]])
    router.generate.return_value = {
        "content": "Cận thị -3D đến -4D: 4 điểm [Thông tư 105, Trang 50]",
        "provider": "lm_studio_local",
        "model": "qwen2.5-1.5b-instruct",
    }
    result = build_compare_graph(searcher, reranker, router).invoke(
        {"query": "So sánh Thông tư 105 và Thông tư 106"}
    )
    assert result["verification"]["passed"] is True
    assert result["verification"]["unsupported_numbers"] == {}
