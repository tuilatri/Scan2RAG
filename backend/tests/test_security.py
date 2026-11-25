"""Security, auth matrix, rate limiting and error redaction tests."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import qa_endpoints
from app.core.rate_limit import RateLimitMiddleware
from app.main import app, _allowed_origins
from app.retrieval.bm25_searcher import LegalBM25Searcher

client = TestClient(app)


def test_api_key_protection_when_configured(monkeypatch):
    """Protected endpoints return 401 when SCAN2RAG_API_KEY is set and header is missing/wrong."""
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED_DEV", "false")
    monkeypatch.setenv("SCAN2RAG_API_KEY", "super-secret-test-key")

    res_missing = client.post(
        "/api/v1/ocr/tables/thông_tư_88_table_p29/rectify",
        json={"content": "| A | B |\n| --- | --- |\n| 1 | 2 |"},
    )
    assert res_missing.status_code == 401

    res_wrong = client.post(
        "/api/v1/ocr/tables/thông_tư_88_table_p29/rectify",
        headers={"X-API-Key": "wrong-key"},
        json={"content": "| A | B |\n| --- | --- |\n| 1 | 2 |"},
    )
    assert res_wrong.status_code == 401


def test_fail_closed_when_key_not_configured(monkeypatch):
    """Production with no configured key never falls open."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED_DEV", "false")
    monkeypatch.setenv("SCAN2RAG_API_KEY", "")
    assert client.get("/api/v1/ocr/tables").status_code == 401


def test_business_route_auth_matrix(monkeypatch):
    """Every business endpoint requires a key; /health stays public."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED_DEV", "false")
    monkeypatch.setenv("SCAN2RAG_API_KEY", "matrix-key")

    protected = [
        ("post", "/api/v1/query", {"json": {"query": "Cận thị mấy điểm?"}}),
        ("post", "/api/v1/query/stream", {"json": {"query": "Cận thị mấy điểm?"}}),
        ("get", "/api/v1/documents", {}),
        ("get", "/api/v1/documents/thông_tư_88", {}),
        ("get", "/api/v1/documents/thông_tư_88/pdf", {}),
        ("get", "/api/v1/ocr/tables", {}),
        ("get", "/api/v1/ocr/tables/thông_tư_88_table_p29", {}),
    ]
    for method, path, kwargs in protected:
        res = getattr(client, method)(path, **kwargs)
        assert res.status_code == 401, f"{method.upper()} {path} was not protected"

    assert client.get("/api/v1/health").status_code == 200


def test_pdf_query_key_allows_iframe(monkeypatch):
    """PDF iframe can authenticate via ?api_key= without a header."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED_DEV", "false")
    monkeypatch.setenv("SCAN2RAG_API_KEY", "iframe-key")

    denied = client.get("/api/v1/documents/thông_tư_88/pdf")
    assert denied.status_code == 401

    allowed = client.get(
        "/api/v1/documents/thông_tư_88/pdf?api_key=iframe-key",
        headers={"Range": "bytes=0-10"},
    )
    assert allowed.status_code == 206
    assert len(allowed.content) == 11


def test_rate_limit_middleware_returns_429(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_OTHER_PER_MIN", "2")
    limited_app = FastAPI()
    limited_app.add_middleware(RateLimitMiddleware)

    @limited_app.get("/limited")
    def limited():
        return {"ok": True}

    limited_client = TestClient(limited_app)
    assert limited_client.get("/limited").status_code == 200
    assert limited_client.get("/limited").status_code == 200
    third = limited_client.get("/limited")
    assert third.status_code == 429
    assert third.headers["Retry-After"] == "60"


def test_internal_error_is_redacted(monkeypatch):
    class BrokenService:
        def answer_query(self, **_kwargs):
            raise RuntimeError("secret internal path /srv/private leaked")

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED_DEV", "true")
    app.dependency_overrides[qa_endpoints.get_qa_service] = lambda: BrokenService()
    try:
        res = client.post("/api/v1/query", json={"query": "Cận thị mấy điểm?"})
    finally:
        app.dependency_overrides.clear()
    assert res.status_code == 500
    assert "secret internal path" not in res.text
    assert "QA pipeline unavailable." in res.text


def test_rate_limit_route_classification():
    limiter = RateLimitMiddleware(app)
    assert limiter._route_class({"path": "/api/v1/ocr/tables/t1/rectify", "method": "POST"}) == "rectify"
    assert limiter._route_class({"path": "/api/v1/documents/d1/pdf", "method": "GET"}) == "pdf"
    assert limiter._route_class({"path": "/api/v1/query/stream", "method": "POST"}) == "query"
    assert limiter._route_class({"path": "/api/v1/health", "method": "GET"}) is None


def test_health_endpoint_is_exempt_from_rate_limit(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_OTHER_PER_MIN", "1")
    exempt_app = FastAPI()
    exempt_app.add_middleware(RateLimitMiddleware)

    @exempt_app.get("/api/v1/health")
    def health():
        return {"status": "ok"}

    @exempt_app.get("/api/v1/other")
    def other():
        return {"ok": True}

    exempt_client = TestClient(exempt_app)
    assert [exempt_client.get("/api/v1/health").status_code for _ in range(3)] == [200, 200, 200]
    assert exempt_client.get("/api/v1/other").status_code == 200
    assert exempt_client.get("/api/v1/other").status_code == 429


def test_cors_origins_are_explicit():
    assert "*" not in _allowed_origins


def test_bm25_safe_json_serialization_and_corrupt_handling(tmp_path: Path):
    """BM25Searcher persists to JSON (no pickle) and returns False on corrupted file."""
    index_file = tmp_path / "bm25_test.json"
    searcher = LegalBM25Searcher(index_path=str(index_file))
    searcher.fit_from_chunks([
        {"chunk_id": "c1", "breadcrumb": "Điều 1", "title": "Mắt", "content": "Cận thị 3 độ"},
        {"chunk_id": "c2", "breadcrumb": "Điều 2", "title": "Thể lực", "content": "Chiều cao cân nặng"},
        {"chunk_id": "c3", "breadcrumb": "Điều 3", "title": "Tim mạch", "content": "Huyết áp bình thường"},
        {"chunk_id": "c4", "breadcrumb": "Điều 4", "title": "Tai mũi họng", "content": "Thính lực tốt"},
    ])
    searcher.save()

    assert index_file.exists()
    assert "corpus_chunks" in index_file.read_text(encoding="utf-8")

    reloaded = LegalBM25Searcher(index_path=str(index_file))
    assert reloaded.load() is True
    assert len(reloaded.search("cận thị", top_k=1)) == 1

    index_file.write_text("{corrupt json", encoding="utf-8")
    assert reloaded.load() is False
