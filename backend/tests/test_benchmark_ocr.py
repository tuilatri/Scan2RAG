import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark_ocr_engines import (
    cer_wer,
    levenshtein,
    match_reference_row,
    normalize,
    number_retention,
    reference_for_page,
)


def test_reference_for_page_filters_out_of_page_rows():
    corpus = [{"document_id": "d", "page": 1, "condition": "- Cận thị từ - 3D đến -4D"}]
    reference = [
        {"document_id": "d", "page": 99, "condition": "- Cận thị từ - 3D đến -4D", "value": 4},
        {"document_id": "d", "page": 99, "condition": "Viêm loét mạn tính", "value": 5},
    ]
    selected = reference_for_page("d", 1, reference, corpus)
    assert selected == [reference[0]]


def test_levenshtein_basic():
    assert levenshtein("", "abc") == 3
    assert levenshtein("kitten", "sitting") == 3


def test_cer_wer_identical_is_zero():
    assert cer_wer("cận thị", "cận thị") == (0.0, 0.0)


def test_normalize_strips_noise():
    result = normalize("Cận thềE từ - 3D")
    assert "can" in result and "3d" in result


def test_match_reference_row_fuzzy():
    extracted = [("- Cận thị từ - 3D đến dưới - 4D", 4)]
    matched = match_reference_row("- Cận thềE từ - 3D đến dưới - 4D", extracted)
    assert matched == extracted[0]


def test_match_reference_row_rejects_different_numbers():
    extracted = [("Cận thị -4D đến -5D", 5)]
    assert match_reference_row("Cận thị -3D đến -4D", extracted) is None


def test_number_retention_requires_all_expected_numbers():
    assert number_retention("3D đến -4D = 4", "Cận 3D đến 4D = 4") is True
    assert number_retention("3D đến -4D = 4", "Cận 3D đến 5D") is False
