import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_canonical_facts import parse_score_rows


def test_parse_score_rows_extracts_score_from_third_column():
    table = (
        "| TT | Bệnh tật | Điểm |\n"
        "| --- | --- | --- |\n"
        "| - cận thị từ - 3D đến dưới - 4D |  | 4 |\n"
        "| không có điểm |  |  |\n"
    )
    facts = parse_score_rows(table, "thông_tư_105", 23, "evidence.png")
    assert len(facts) == 1
    assert facts[0].value == 4
    assert "cận thị" in facts[0].condition
    assert facts[0].needs_human is True
    assert facts[0].authoritative is False


def test_parse_score_rows_accepts_second_column_layout():
    table = (
        "| Bệnh tật | Điểm | Ghi chú |\n"
        "| --- | --- | --- |\n"
        "| - viễn thị từ + 3D đến dưới + 4D | 5 |  |\n"
    )
    facts = parse_score_rows(table, "thông_tư_88", 29, "evidence.png")
    assert len(facts) == 1
    assert facts[0].value == 5
