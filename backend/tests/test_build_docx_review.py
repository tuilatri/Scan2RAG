import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_docx_review import apply_review, invariant_errors


def _fact(**overrides):
    base = {
        "id": "docx_test_001",
        "document_id": "thông_tư_105",
        "page": 23,
        "condition": "- Cận thị từ - 3D đến dưới - 4D",
        "value": 4,
        "evidence_image": "data/exports/review/canonical/thông_tư_105_table_p23.png",
    }
    base.update(overrides)
    return base


def test_invariant_accepts_numeric_range_condition():
    assert invariant_errors(_fact(condition="+ 121- 130 hoặc 100-109"), ROOT) == []


def test_invariant_flags_stuck_number_and_short_text():
    assert "number and text stuck together" in invariant_errors(_fact(condition="1234abc"), ROOT)
    assert "condition too short" in invariant_errors(_fact(condition="+ Nhiều"), ROOT)


def test_apply_review_marks_trusted_source_and_flags_anomaly():
    payload = {"facts": [_fact(), _fact(id="docx_test_002", condition="+ Nhiều")]}
    updated, queue = apply_review(payload, ROOT)
    good, bad = updated["facts"]
    assert good["authoritative"] is True
    assert good["authoritative_source"] == "vietnamocr_docx"
    assert good["needs_human"] is False
    assert bad["authoritative"] is False
    assert bad["review_needed"] is True
    assert queue["summary"]["flagged"] == 1
