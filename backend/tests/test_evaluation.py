"""Unit tests for Multi-Persona Evaluation Auditors (Audit Group 3)."""

import json
from pathlib import Path
from unittest.mock import patch

from app.evaluation.data_pipeline_auditor import DataPipelineAuditor
from app.evaluation.legal_domain_auditor import LegalDomainAuditor
from app.evaluation.ocr_vision_auditor import OcrVisionAuditor


def test_legal_domain_auditor_fails_when_qdrant_unavailable(tmp_path: Path):
    """LegalDomainAuditor must NOT fabricate qdrant_superseded=81 when Qdrant errors."""
    sample_doc = {
        "document_id": "thông_tư_88",
        "nodes": [
            {"id": "n1", "level": "DOCUMENT", "title": "Tiêu đề", "content": "Nội dung chuẩn NFC", "metadata": {}}
        ],
    }
    (tmp_path / "thông_tư_88.json").write_text(json.dumps(sample_doc, ensure_ascii=False), encoding="utf-8")

    auditor = LegalDomainAuditor(data_dir=tmp_path)
    with patch("app.retrieval.qdrant_client.LegalVectorStore", side_effect=RuntimeError("Qdrant down")):
        res = auditor.audit()

    assert res["qdrant_superseded_points"] == 0
    assert res["qdrant_error"] is not None
    assert res["passed"] is False


def test_ocr_vision_auditor_detects_duplicate_separator(tmp_path: Path):
    """OcrVisionAuditor flags duplicate markdown separator lines."""
    bad_table = "| TT | Bệnh tật | Điểm |\n| --- | --- | --- |\n| --- | --- | --- |\n| 1 | Cận thị | 4 |"
    sample_doc = {
        "document_id": "thông_tư_88",
        "nodes": [
            {"id": "t1", "level": "TABLE", "title": "Bảng", "content": bad_table, "metadata": {"vlm_rectified": True}}
        ],
    }
    (tmp_path / "thông_tư_88.json").write_text(json.dumps(sample_doc, ensure_ascii=False), encoding="utf-8")

    res = OcrVisionAuditor(data_dir=tmp_path).audit()
    assert res["duplicate_separators"] == 1
    assert res["passed"] is False


def test_data_pipeline_auditor_passes_clean_nodes(tmp_path: Path):
    """DataPipelineAuditor passes when nodes have valid parents and non-empty content."""
    sample_doc = {
        "document_id": "thông_tư_88",
        "nodes": [
            {"id": "d1", "level": "DOCUMENT", "parent_id": None, "content": "Thông tư 88"},
            {"id": "a1", "level": "ARTICLE", "parent_id": "d1", "content": "Điều 1 quy định chung"},
        ],
    }
    (tmp_path / "thông_tư_88.json").write_text(json.dumps(sample_doc, ensure_ascii=False), encoding="utf-8")

    res = DataPipelineAuditor(data_dir=tmp_path).audit()
    assert res["passed"] is True
    assert res["orphan_nodes"] == 0
