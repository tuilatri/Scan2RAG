"""Unit tests for Document Serving Endpoints in Scan2RAG (Milestone 3)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_documents():
    """Test GET /api/v1/documents returns list of documents with metadata."""
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    docs = response.json()
    assert isinstance(docs, list)
    assert len(docs) >= 5

    doc_ids = [d["id"] for d in docs]
    assert "thông_tư_88" in doc_ids
    assert "thông_tư_105" in doc_ids
    assert "thông_tư_106" in doc_ids

    # Verify is_superseded flag
    doc_105 = next(d for d in docs if d["id"] == "thông_tư_105")
    assert doc_105["is_superseded"] is True

    doc_88 = next(d for d in docs if d["id"] == "thông_tư_88")
    assert doc_88["is_superseded"] is False


def test_get_document_info():
    """Test GET /api/v1/documents/{doc_id} returns accurate info."""
    response = client.get("/api/v1/documents/thông_tư_88")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "thông_tư_88"
    assert data["pages_count"] == 120
    assert data["size_bytes"] > 0


def test_get_document_info_not_found():
    """Test GET /api/v1/documents/{doc_id} 404 for unknown document."""
    response = client.get("/api/v1/documents/non_existent_doc")
    assert response.status_code == 404


def test_stream_document_pdf_full():
    """Test GET /api/v1/documents/{doc_id}/pdf without Range header."""
    response = client.get("/api/v1/documents/hướng_dẫn_cục_quân_y/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "bytes" in response.headers.get("accept-ranges", "")
    assert len(response.content) > 1000


def test_stream_document_pdf_range_request():
    """Test GET /api/v1/documents/{doc_id}/pdf with HTTP Range header (Partial Content)."""
    headers = {"Range": "bytes=0-1023"}
    response = client.get("/api/v1/documents/hướng_dẫn_cục_quân_y/pdf", headers=headers)
    assert response.status_code == 206
    assert response.headers["content-type"] == "application/pdf"
    assert "bytes 0-1023/" in response.headers["content-range"]
    assert len(response.content) == 1024


def test_stream_document_pdf_not_found():
    """Test 404 for non-existent document PDF."""
    response = client.get("/api/v1/documents/non_existent/pdf")
    assert response.status_code == 404
