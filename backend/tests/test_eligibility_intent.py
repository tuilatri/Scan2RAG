from unittest.mock import Mock

from app.services.qa_service import GroundedQAService


def _service():
    return GroundedQAService(
        hybrid_searcher=Mock(), reranker=Mock(), model_router=Mock(), corpus_graph=Mock()
    )


def test_eligibility_intent_detection():
    assert GroundedQAService._has_eligibility_intent("viễn thị có phải đi nghĩa vụ quân sự không")
    assert GroundedQAService._has_eligibility_intent("loạn thị có được tạm hoãn không")
    assert not GroundedQAService._has_eligibility_intent("cận thị -3D đến -4D mấy điểm")


def test_graph_candidates_normalize_payload():
    qa = _service()
    qa.corpus_graph.supporting_chunks.return_value = [
        {
            "chunk_id": "rule-p2",
            "content": "Không gọi nhập ngũ",
            "document_id": "hướng_dẫn_cục_quân_y",
            "document_name": "Hướng dẫn Cục quân y",
            "breadcrumb": "Trang 2",
            "page_numbers": [2],
        }
    ]
    chunks = qa._graph_candidates("viễn thị có phải đi không")
    assert len(chunks) == 1
    assert chunks[0]["id"] == "rule-p2"
    assert chunks[0]["page_number"] == 2
    qa.corpus_graph.supporting_chunks.assert_called_once()


def test_chain_summary_appends_canonical_docx_graph():
    qa = _service()
    qa.corpus_graph.summaries_for.return_value = []
    qa.eligibility_graph = Mock()
    qa.eligibility_graph.summary.return_value = "CANONICAL RULE CHAIN (DOCX source): - rule"
    result = qa._with_chain_summary("BASE", "viễn thị có phải đi không")
    assert "CANONICAL RULE CHAIN (DOCX source)" in result
    assert result.startswith("BASE")


def test_merge_graph_chunks_dedups():
    top = [{"id": "a"}, {"id": "b"}]
    graph = [{"id": "b"}, {"id": "c"}]
    merged = GroundedQAService._merge_graph_chunks(top, graph)
    assert [chunk["id"] for chunk in merged] == ["a", "b", "c"]
