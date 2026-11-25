"""Unit tests for the index consistency gate."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from audit_index_consistency import REQUIRED_FIELDS, check_consistency  # noqa: E402


def _chunk(chunk_id: str) -> dict:
    return {field: "" for field in REQUIRED_FIELDS} | {"id": chunk_id}


def _point(point_id: int, chunk_id: str) -> dict:
    return {
        "id": point_id,
        "payload": {
            "chunk_id": chunk_id,
            "breadcrumb": "Doc > CHAPTER",
            "superseded_by": "",
            "effective_date": "2024-01-01",
        },
    }


def test_consistent_indexes_pass():
    chunks = [_chunk("c1"), _chunk("c2")]
    ok, summary = check_consistency(chunks, list(chunks), [_point(1, "c1"), _point(2, "c2")])
    assert ok is True
    assert summary["chunk_ids_equal"] is True
    assert summary["errors"] == []


def test_missing_chunk_fails():
    chunks = [_chunk("c1"), _chunk("c2")]
    ok, summary = check_consistency(chunks, [_chunk("c1")], [_point(1, "c1"), _point(2, "c2")])
    assert ok is False
    assert "count_mismatch" in summary["errors"]
    assert "chunk_id_set_mismatch" in summary["errors"]


def test_missing_bm25_contract_field_fails():
    chunks = [_chunk("c1")]
    bm = [_chunk("c1")]
    bm[0].pop("superseded_by")
    ok, summary = check_consistency(chunks, bm, [_point(1, "c1")])
    assert ok is False
    assert "bm25_fields_missing" in summary["errors"]


def test_missing_field_in_second_chunk_fails():
    chunks = [_chunk("c1"), _chunk("c2")]
    bm = [_chunk("c1"), _chunk("c2")]
    bm[1].pop("superseded_by")
    ok, summary = check_consistency(chunks, bm, [_point(1, "c1"), _point(2, "c2")])
    assert ok is False
    assert "bm25_fields_missing" in summary["errors"]
