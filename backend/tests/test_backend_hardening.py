"""Unit tests for Backend Hardening (C-H3, C-H4, C-H5)."""

from app.api import qa_endpoints
from app.llm.prompt_templates import GroundedPromptBuilder


def test_build_qa_prompt_avoids_trang_0_and_wraps_user_query():
    """Prompt builder must not emit '(Trang 0)' and must wrap query in <user_query> tags."""
    chunks = [
        {
            "document_name": "Thông tư 88",
            "breadcrumb": "Thông tư 88 > Bảng phụ lục (Trang 29)",
            "page_number": 29,
            "content": "Cận thị 3 độ.",
        },
        {
            "document_name": "Thông tư 68",
            "breadcrumb": "Thông tư 68 > Điều 1",
            "page_number": 0,
            "content": "Quy định chung.",
        },
    ]
    prompt = GroundedPromptBuilder.build_qa_prompt("Cận thị mấy điểm?", chunks)
    assert "(Trang 0)" not in prompt
    assert "(Trang 29) (Trang 29)" not in prompt
    assert "<user_query>\nCận thị mấy điểm?\n</user_query>" in prompt


def test_qa_service_has_thread_lock():
    """qa_endpoints must define _qa_service_lock for thread-safe singleton initialization."""
    assert hasattr(qa_endpoints, "_qa_service_lock")
