from unittest.mock import Mock

from app.services.qa_service import GroundedQAService, normalize_medical_query

QUERY = "Cận thị từ 3 đến dưới 4 độ khám sức khỏe nghĩa vụ quân sự mấy điểm?"
CHUNK_105 = {
    "id": "thông_tư_105_chunk_0863_w2",
    "document_id": "thông_tư_105",
    "content": "cận thị từ - 3D đến dưới - 4D | 4",
}
CHUNK_88 = {
    "id": "thông_tư_88_chunk_1101_w2",
    "document_id": "thông_tư_88",
    "content": "cận thị từ - 4D đến dưới - 5D | 5",
}


def test_normalize_medical_query():
    normalized = normalize_medical_query(QUERY)
    assert "-3D đến dưới -4D" in normalized
    assert normalize_medical_query("Cận thị từ -3D đến dưới -4D mấy điểm?") == (
        "Cận thị từ -3D đến dưới -4D mấy điểm?"
    )


def test_normalized_search_promotes_matching_chunk():
    searcher = Mock()
    searcher.search.return_value = [{"id": "candidate-105"}]
    reranker = Mock()
    reranker.rerank.return_value = [CHUNK_105]
    service = GroundedQAService(searcher, reranker, Mock())

    merged = service._augment_with_normalized_query(
        QUERY, normalize_medical_query(QUERY), [CHUNK_88], 15, 5
    )
    assert merged[0]["id"] == CHUNK_105["id"]
    assert searcher.search.call_count == 1
    assert searcher.search.call_args.kwargs["query"] == normalize_medical_query(QUERY)


def test_no_extra_search_when_query_already_normalized():
    searcher = Mock()
    reranker = Mock()
    service = GroundedQAService(searcher, reranker, Mock())
    query = "Cận thị từ -3D đến dưới -4D mấy điểm?"

    merged = service._augment_with_normalized_query(
        query, normalize_medical_query(query), [CHUNK_88], 15, 5
    )
    assert merged == [CHUNK_88]
    searcher.search.assert_not_called()
    reranker.rerank.assert_not_called()
