from unittest.mock import Mock

from app.llm.prompt_templates import STRICT_LEGAL_SYSTEM_PROMPT
from app.services.qa_service import GroundedQAService, needs_grounded_retry

REFUSAL = "Văn bản hiện tại không quy định về trường hợp này."
CHUNK = {
    "id": "c1",
    "document_id": "thông_tư_105",
    "document_name": "Thông tư 105",
    "content": "Cận thị từ -3D đến dưới -4D | 4 điểm",
    "breadcrumb": "Thông tư 105 > Chương V > Bảng phụ lục",
    "page_number": 23,
}


def _service(chunks, answers):
    searcher = Mock()
    searcher.search.return_value = []
    reranker = Mock()
    reranker.rerank.return_value = chunks
    router = Mock()
    router.classify_complexity.return_value = "complex"
    router.generate.side_effect = [
        {"content": answer, "provider": "groq_cloud", "model": "qwen"} for answer in answers
    ]
    return GroundedQAService(searcher, reranker, router), router


def test_refusal_with_evidence_is_regenerated_once():
    service, router = _service([CHUNK], [REFUSAL, "Cận thị -3D đến -4D: 4 điểm [TT105, Trang 23]"])
    result = service.answer_query("Cận thị -3D đến dưới -4D mấy điểm?")
    assert REFUSAL not in result["answer"]
    assert router.generate.call_count == 2
    assert "giá trị cụ thể" in router.generate.call_args_list[1].kwargs["prompt"]


def test_refusal_without_evidence_is_kept():
    service, router = _service([], [REFUSAL])
    result = service.answer_query("Câu hỏi ngoài phạm vi")
    assert result["answer"] == REFUSAL
    assert router.generate.call_count == 1


def test_regeneration_is_bounded():
    service, router = _service([CHUNK], [REFUSAL, REFUSAL, "should not be used"])
    result = service.answer_query("So sánh TT105 và TT106")
    assert router.generate.call_count == 2
    assert result["answer"] == REFUSAL
    assert needs_grounded_retry(REFUSAL, [CHUNK]) is True
    assert "GIÁ TRỊ CỤ THỂ" in STRICT_LEGAL_SYSTEM_PROMPT
