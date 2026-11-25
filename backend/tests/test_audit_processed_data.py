"""Unit tests for the numeric safeguard used by corpus audit."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from audit_processed_data import check_number_lock  # noqa: E402


def test_number_lock_accepts_identical_numbers():
    ok, reason = check_number_lock(
        "| 1 | Cận thị | 3T |",
        "| 1 | Cận thị (đã sửa dấu) | 3T |",
    )
    assert ok is True
    assert reason == ""


def test_number_lock_rejects_changed_score():
    ok, reason = check_number_lock(
        "| + Nu 2 bên mt | 9 |",
        "| + Nếu 2 bên mắt | 5 |",
    )
    assert ok is False
    assert "9" in reason
    assert "5" in reason


def test_number_lock_rejects_missing_backup():
    ok, reason = check_number_lock(None, "| 1 | Cận thị | 2 |")
    assert ok is False
    assert "raw_content_backup" in reason
