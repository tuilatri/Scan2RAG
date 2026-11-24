"""Hard Constraint Tests for Grounded QA Service & FastAPI Query Endpoints (Lauren Tan Methodology).

Defines invariant assertions that MUST pass:
1. INV-LLM-01: ModelRouter handles offline local server by falling back or returning deterministic offline response.
2. INV-CITE-01: GroundedQAService attaches structured citations containing document_name, breadcrumb, and page_number.
3. INV-API-01: POST /api/v1/query returns valid schema with citations matching ground truth.
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.api.qa_endpoints import get_qa_service
from app.llm.router import ModelRouter
from app.main import app
from app.services.qa_service import GroundedQAService


def test_hard_constraint_model_router_offline_resilience():
    """Bất biến 1: ModelRouter phải có phản ứng kiên cường khi Local Server offline, không văng unhandled exception."""
    # Point to nonexistent port and mock cloud failure
    router = ModelRouter(local_base_url="http://localhost:9999/v1")
    assert not router.is_local_available(), "Nonexistent port must report unavailable"

    with patch.object(router, "_call_provider", side_effect=Exception("Offline")):
        res = router.generate(prompt="Test prompt", system_prompt="Test sys")
        assert "content" in res
        assert res["provider"] == "deterministic_offline"


def test_hard_constraint_qa_service_citation_integrity():
    """Bất biến 2: QAService phải gán đúng cấu trúc dẫn chứng trang PDF và điều khoản."""
    mock_hybrid = MagicMock()
    mock_hybrid.search.return_value = [
        {
            "id": "thông_tư_105_table_p23",
            "document_id": "thông_tư_105",
            "document_name": "Thông tư 105",
            "breadcrumb": "Thông tư 105 > Chương V > Bảng phụ lục (Trang 23)",
            "page_number": 23,
            "is_table": True,
            "content": "| Cận thị từ -3D đến dưới -4D | 4 |",
            "rrf_score": 0.03,
        }
    ]

    mock_reranker = MagicMock()
    mock_reranker.rerank.return_value = [
        {
            "id": "thông_tư_105_table_p23",
            "document_id": "thông_tư_105",
            "document_name": "Thông tư 105",
            "breadcrumb": "Thông tư 105 > Chương V > Bảng phụ lục (Trang 23)",
            "page_number": 23,
            "is_table": True,
            "content": "| Cận thị từ -3D đến dưới -4D | 4 |",
            "rerank_score": 0.95,
        }
    ]

    mock_router = MagicMock()
    mock_router.generate.return_value = {
        "content": "Cận thị từ -3D đến dưới -4D được chấm Điểm 4 [Thông tư 105, Trang 23].",
        "provider": "mock_test_llm",
        "model": "test-model",
    }

    qa_service = GroundedQAService(
        hybrid_searcher=mock_hybrid,
        reranker=mock_reranker,
        model_router=mock_router,
    )

    res = qa_service.answer_query("Cận thị từ -3D đến dưới -4D mấy điểm?")
    assert "Điểm 4" in res["answer"]
    assert len(res["citations"]) == 1
    cite = res["citations"][0]
    assert cite["document_id"] == "thông_tư_105"
    assert cite["page_number"] == 23
    assert cite["is_table"] is True
    assert cite["rerank_score"] == 0.95


def test_hard_constraint_fastapi_query_endpoint():
    """Bất biến 3: Endpoint POST /api/v1/query phải trả về status 200 và khớp schema."""
    # Mock QAService
    mock_qa = MagicMock()
    mock_qa.answer_query.return_value = {
        "query": "Tiêu chuẩn sức khỏe Điều 4",
        "answer": "Tiêu chuẩn chung đạt loại 1, 2, 3 [Thông tư 105, Điều 4, Trang 3].",
        "citations": [
            {
                "id": "c1",
                "document_id": "thông_tư_105",
                "document_name": "Thông tư 105",
                "breadcrumb": "Thông tư 105 > Điều 4",
                "page_number": 3,
                "is_table": False,
                "rerank_score": 0.88,
                "snippet": "tiêu chuẩn chung: Đạt sức khỏe loại 1, 2, 3",
            }
        ],
        "provider": "mock_provider",
        "model": "mock-model",
        "latency_retrieval_ms": 45.2,
        "latency_rerank_ms": 12.1,
        "latency_total_ms": 57.3,
    }

    app.dependency_overrides[get_qa_service] = lambda: mock_qa
    client = TestClient(app)

    # Test Health
    resp_health = client.get("/api/v1/health")
    assert resp_health.status_code == 200
    assert resp_health.json()["status"] == "ok"

    # Test Query
    resp_query = client.post("/api/v1/query", json={"query": "Tiêu chuẩn sức khỏe Điều 4"})
    assert resp_query.status_code == 200
    data = resp_query.json()
    assert data["query"] == "Tiêu chuẩn sức khỏe Điều 4"
    assert "Điêu 4" in data["answer"] or "Điều 4" in data["answer"]
    assert len(data["citations"]) == 1
    assert data["citations"][0]["page_number"] == 3

    app.dependency_overrides.clear()
