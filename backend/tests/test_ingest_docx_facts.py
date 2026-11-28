import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ingest_docx_facts import build_facts, normalize, parse_score_table


def test_normalize_keeps_dong_diacritic():
    assert normalize("Điểm") == "điem"
    assert normalize("Diểm") == "diem"


def test_parse_score_table_uses_header_and_skips_header_row():
    rows = [
        ["TT", "Bệnh tật", "Điểm"],
        ["4", "Loạn thị:", ""],
        ["", "- Cận thị từ - 3D đến dưới - 4D", "4"],
    ]
    parsed = parse_score_table(rows)
    assert parsed == [("- Cận thị từ - 3D đến dưới - 4D", 4)]


def test_build_facts_maps_table_to_canonical_context():
    canonical = [{
        "id": "thông_tư_105_p23_score_009",
        "document_id": "thông_tư_105",
        "page": 23,
        "condition": "- Cận thị từ - 3D đến dưới - 4D",
        "evidence_image": "evidence.png",
    }]
    rows = [
        ["TT", "Bệnh tật", "Điểm"],
        ["", "- Cận thị từ - 3D đến dưới - 4D", "4"],
    ]
    facts, mapped = build_facts([rows], canonical)
    assert mapped == 1
    assert len(facts) == 1
    assert facts[0]["source_kind"] == "docx"
    assert facts[0]["page"] == 23
    assert facts[0]["needs_human"] is True
    assert facts[0]["authoritative"] is False
