"""Unit tests for OCR HITL Endpoints in Scan2RAG (Milestone 3)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_ocr_tables():
    """Test GET /api/v1/ocr/tables returns full list of 111 tables."""
    response = client.get("/api/v1/ocr/tables")
    assert response.status_code == 200
    tables = response.json()
    assert isinstance(tables, list)
    assert len(tables) >= 110  # 111 extracted medical tables

    first_table = tables[0]
    assert "id" in first_table
    assert "document_id" in first_table
    assert "page_number" in first_table
    assert "rows_count" in first_table


def test_get_ocr_table_detail():
    """Test GET /api/v1/ocr/tables/{node_id} returns accurate matrix and markdown."""
    node_id = "thông_tư_88_table_p29"
    response = client.get(f"/api/v1/ocr/tables/{node_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == node_id
    assert data["document_id"] == "thông_tư_88"
    assert data["page_number"] == 29
    assert len(data["headers"]) >= 2
    assert len(data["rows"]) >= 10
    assert "content" in data


def test_get_ocr_table_detail_not_found():
    """Test 404 for unknown table."""
    response = client.get("/api/v1/ocr/tables/unknown_table_node")
    assert response.status_code == 404


def test_rectify_ocr_table_invalid_format():
    """Test 422 error when submitting invalid table markdown."""
    node_id = "thông_tư_88_table_p29"
    payload = {"content": "not a markdown table"}
    response = client.post(f"/api/v1/ocr/tables/{node_id}/rectify", json=payload)
    assert response.status_code == 422


def test_rectify_ocr_table_success():
    """Test submitting rectification for a table."""
    node_id = "thông_tư_88_table_p29"
    # First get original content
    orig_res = client.get(f"/api/v1/ocr/tables/{node_id}")
    orig_data = orig_res.json()
    orig_content = orig_data["content"]

    # Submit slight revision (e.g. keeping content and marking approved)
    payload = {
        "content": orig_content,
        "approved": True,
        "reviewer_notes": "Kiểm tra chuyên môn: Điểm thị lực chuẩn xác theo Thông tư 88.",
    }
    response = client.post(f"/api/v1/ocr/tables/{node_id}/rectify", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert res_data["hitl_approved"] is True
