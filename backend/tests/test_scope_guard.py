from unittest.mock import Mock

from app.guards.scope_guard import SCOPE_REFUSAL_MESSAGE, is_out_of_scope
from app.services.qa_service import GroundedQAService

OUT_OF_SCOPE = [
    "Thời tiết hôm nay ở Hà Nội thế nào?",
    "Giá xe máy điện mới nhất là bao nhiêu?",
    "Làm thế nào để đặt vé máy bay đi Đà Nẵng?",
    "Bạn có thể viết bài thơ về mùa đông không?",
]

IN_SCOPE = [
    "Cận thị từ -3D đến dưới -4D mấy điểm?",
    "Thông tư 106 sửa đổi khoản nào của Điều 3?",
    "Chỉ số BMI dưới 18,0 có đạt nghĩa vụ quân sự không?",
]


def test_out_of_scope_queries_are_detected():
    for query in OUT_OF_SCOPE:
        assert is_out_of_scope(query), query


def test_in_scope_queries_are_not_blocked():
    for query in IN_SCOPE:
        assert not is_out_of_scope(query), query


def test_stream_refuses_without_retrieval_or_llm():
    qa = GroundedQAService(
        hybrid_searcher=Mock(), reranker=Mock(), model_router=Mock()
    )
    events = "\n".join(qa.stream_answer_query(OUT_OF_SCOPE[0]))

    assert SCOPE_REFUSAL_MESSAGE in events
    assert '"provider": "scope_guard"' in events
    qa.hybrid_searcher.search.assert_not_called()
    qa.model_router.generate_stream.assert_not_called()


def test_in_scope_query_still_retrieves():
    qa = GroundedQAService(
        hybrid_searcher=Mock(), reranker=Mock(), model_router=Mock()
    )
    qa.hybrid_searcher.search.return_value = []
    qa.reranker.rerank.return_value = []
    qa.model_router.classify_complexity.return_value = "simple"
    qa.model_router.generate_stream.return_value = iter([])

    events = "\n".join(qa.stream_answer_query(IN_SCOPE[0]))

    assert '"status": "retrieving"' in events
    qa.hybrid_searcher.search.assert_called_once()
