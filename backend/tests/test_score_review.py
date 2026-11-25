"""Tests for reviewed medical score exceptions (1B-review)."""

import json
from pathlib import Path

from app.evaluation import ocr_vision_auditor as module
from app.evaluation.ocr_vision_auditor import OcrVisionAuditor

NODE_ID = "test_table_p1"
CONTENT = (
    "| TT | Bệnh tật | Mức | Điểm |\n"
    "| --- | --- | --- | --- |\n"
    "| 1 | Cận thị | 3T | 4 |\n"
)
KEY = {"node_id": NODE_ID, "page_number": 1, "row": 0, "col": 2, "cell_value": "3T"}


def _setup(tmp_path: Path, items: list[dict], monkeypatch) -> OcrVisionAuditor:
    data_dir = tmp_path / "processed"
    data_dir.mkdir()
    (data_dir / "doc.json").write_text(
        json.dumps({
            "document_id": "doc",
            "nodes": [{
                "id": NODE_ID, "level": "TABLE", "title": "Bảng",
                "page_number": 1, "content": CONTENT, "metadata": {},
            }],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    decisions = tmp_path / "decisions.json"
    decisions.write_text(
        json.dumps({"version": 1, "items": items}, ensure_ascii=False), encoding="utf-8"
    )
    monkeypatch.setattr(module, "DECISIONS_PATH", decisions)
    return OcrVisionAuditor(data_dir=data_dir)


def _decision(**overrides: object) -> dict:
    item = {
        **KEY,
        "reason": "multi_score",
        "reviewer": "agent",
        "timestamp": "2026-11-26T00:00:00+00:00",
    }
    item.update(overrides)
    return item


def test_valid_exception_passes(tmp_path: Path, monkeypatch):
    result = _setup(tmp_path, [_decision()], monkeypatch).audit()
    assert result["shifted_score_cells"] == 1
    assert result["reviewed_exceptions"] == 1
    assert result["passed"] is True


def test_exception_without_reviewer_fails(tmp_path: Path, monkeypatch):
    item = _decision()
    item.pop("reviewer")
    result = _setup(tmp_path, [item], monkeypatch).audit()
    assert result["reviewed_exceptions"] == 0
    assert result["passed"] is False


def test_shifted_cell_without_decision_fails(tmp_path: Path, monkeypatch):
    result = _setup(tmp_path, [], monkeypatch).audit()
    assert result["shifted_score_cells"] == 1
    assert result["reviewed_exceptions"] == 0
    assert result["passed"] is False


def test_more_shifted_than_reviewed_fails(tmp_path: Path, monkeypatch):
    item = _decision()
    item["page_number"] = 99
    result = _setup(tmp_path, [item], monkeypatch).audit()
    assert result["shifted_score_cells"] == 1
    assert result["reviewed_exceptions"] == 0
    assert result["passed"] is False


def test_decision_needing_human_is_not_auto_accepted(tmp_path: Path, monkeypatch):
    result = _setup(tmp_path, [_decision(needs_human=True)], monkeypatch).audit()
    assert result["invalid_decisions"] == 1
    assert result["reviewed_exceptions"] == 0
    assert result["passed"] is False
