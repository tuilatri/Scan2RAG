"""Unit tests for 1B medical table column repair."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from fix_medical_table_columns import (  # noqa: E402
    normalize_table,
    restore_numbers_from_backup,
)


def test_restore_numbers_keeps_vietnamese_diacritics():
    content = "| + Nếu 2 bên mắt | 5 |"
    backup = "| + Nu 2 bên mt | 9 |"
    assert restore_numbers_from_backup(content, backup) == "| + Nếu 2 bên mắt | 9 |"


def test_restore_numbers_noop_when_numbers_match():
    content = "| 1 | Cận thị | 2 |"
    assert restore_numbers_from_backup(content, content) == content


def test_normalize_moves_score_with_typo_header():
    content = (
        "| TT | Bệnh tật | Diểm |\n"
        "| --- | --- | --- |\n"
        "| - Một bên tai 5m | 1 |  |\n"
    )
    new_content, _, _, _ = normalize_table(content)
    assert "| - Một bên tai 5m |  | 1 |" in new_content


def test_normalize_moves_score_with_garbled_header():
    content = (
        "| II | Tt i rrun tinh) | S |\n"
        "| --- | --- | --- |\n"
        "| m | 5 |  |\n"
    )
    new_content, _, _, _ = normalize_table(content)
    assert "| m |  | 5 |" in new_content


def test_normalize_ignores_row_numbers_in_two_column_table():
    content = (
        "| STT | Nội dung |\n"
        "| --- | --- |\n"
        "| 1 | Số lượng cần kiểm tra |\n"
        "| 2 | Số lượng đã kiểm tra |\n"
    )
    collisions: list[dict] = []
    new_content, _, _, _ = normalize_table(content, collisions)
    assert "| 1 | Số lượng cần kiểm tra |" in new_content
    assert collisions == []


def test_normalize_does_not_overwrite_occupied_score_column():
    content = (
        "| TT | Bệnh tật | Mức | Điểm |\n"
        "| --- | --- | --- | --- |\n"
        "| 1 | Cận thị | 3T | 4 |\n"
    )
    collisions: list[dict] = []
    new_content, _, _, _ = normalize_table(content, collisions)
    assert "| 1 | Cận thị | 3T | 4 |" in new_content
    assert len(collisions) == 1
    assert collisions[0]["reason"] == "target_occupied"
