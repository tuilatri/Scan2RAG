"""Security and safe serialization tests for Scan2RAG (Audit Group 2)."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.retrieval.bm25_searcher import LegalBM25Searcher

client = TestClient(app)


def test_api_key_protection_when_configured(monkeypatch):
    """Protected endpoints return 401 when SCAN2RAG_API_KEY is set and header is missing/wrong."""
    monkeypatch.setenv("SCAN2RAG_API_KEY", "super-secret-test-key")

    # Missing key -> 401
    res_missing = client.post(
        "/api/v1/ocr/tables/thông_tư_88_table_p29/rectify",
        json={"content": "| A | B |\n| --- | --- |\n| 1 | 2 |"},
    )
    assert res_missing.status_code == 401

    # Wrong key -> 401
    res_wrong = client.post(
        "/api/v1/ocr/tables/thông_tư_88_table_p29/rectify",
        headers={"X-API-Key": "wrong-key"},
        json={"content": "| A | B |\n| --- | --- |\n| 1 | 2 |"},
    )
    assert res_wrong.status_code == 401


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
    # Verify it is valid UTF-8 JSON, not binary pickle
    raw_text = index_file.read_text(encoding="utf-8")
    assert "corpus_chunks" in raw_text

    reloaded = LegalBM25Searcher(index_path=str(index_file))
    assert reloaded.load() is True
    assert len(reloaded.search("cận thị", top_k=1)) == 1

    # Corrupt file -> returns False instead of crashing
    index_file.write_text("{corrupt json", encoding="utf-8")
    assert reloaded.load() is False
