"""Tests for metadata-only legal tree normalization on processed JSON."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from normalize_legal_tree import normalize_document  # noqa: E402


def _doc() -> dict:
    return {
        "document_id": "thông_tư_88",
        "nodes": [
            {"id": "root", "level": "DOCUMENT", "content": "Thông tư", "order": 0, "metadata": {}},
            {"id": "chap", "level": "CHAPTER", "title": "Chương I", "content": "Chương I", "order": 1, "parent_id": "root", "metadata": {}},
            {"id": "art", "level": "ARTICLE", "title": "Điều 1", "content": "Điều 1", "order": 2, "metadata": {}},
            {"id": "orphan", "level": "SECTION", "title": "Mục 1", "content": "Mục 1", "order": 3, "metadata": {}},
        ],
    }


def test_orphan_gets_nearest_ancestor():
    data = _doc()
    stats = normalize_document(data)
    assert stats["parents_fixed"] == 2
    assert data["nodes"][2]["parent_id"] == "chap"
    assert data["nodes"][3]["parent_id"] == "art"


def test_superseded_and_consolidated_flags_are_set():
    data = _doc()
    data["nodes"][2]["id"] = "thông_tư_105_clause_61"
    data["document_id"] = "thông_tư_105"
    stats = normalize_document(data)
    assert stats["superseded"] >= 1
    assert data["nodes"][2]["metadata"]["superseded_by"] == "thông_tư_106"

    consolidated = _doc()
    stats2 = normalize_document(consolidated)
    assert stats2["consolidated"] == 4
    assert all(n["metadata"]["is_consolidated"] for n in consolidated["nodes"])


def test_table_compaction_preserves_numbers():
    table = (
        "| TT | Bệnh tật | Điểm |\n"
        "| --- | --- | --- |\n"
        "| 1 | Cận thị | 2 |\n"
        "|  |  |  |\n"
    )
    data = {
        "document_id": "thông_tư_88",
        "nodes": [{
            "id": "t1", "level": "TABLE", "content": table, "order": 0,
            "metadata": {"raw_content_backup": table, "content_numbers": ["1", "2"]},
        }],
    }
    stats = normalize_document(data)
    assert stats["tables_compacted"] == 1
    assert "|  |  |  |" not in data["nodes"][0]["content"]
    assert "2" in data["nodes"][0]["content"]
