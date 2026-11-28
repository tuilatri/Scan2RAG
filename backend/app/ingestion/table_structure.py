"""Header-aware Markdown table parsing, inspired by VietNamOCR's table layer.

Unlike taking the first numeric cell, this looks for the column whose header
names the score (Điểm / Diểm / Dim) and ignores header/TT rows. It is a
deterministic open replacement for the SLANet-style column selection we do
not have a license to copy.
"""

from __future__ import annotations

import re
import unicodedata

SCORE_RE = re.compile(r"^[1-6]$")
HEADER_HINTS = ("diem", "điem", "iem", "dim", "đim", "ieam")


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(text).lower())
    return "".join(
        char for char in decomposed
        if not unicodedata.combining(char) and char.isalnum()
    )


def extract_score_rows(content: str) -> list[tuple[str, int]]:
    """Return (condition, score) pairs from a Markdown table."""
    lines = [line.strip() for line in content.splitlines() if line.strip().startswith("|")]
    if not lines:
        return []

    score_column: int | None = None
    for line in lines[:4]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        for index, cell in enumerate(cells):
            if any(hint in normalize(cell) for hint in HEADER_HINTS):
                score_column = index
                break
        if score_column is not None:
            break
    if score_column is None:
        return []

    rows: list[tuple[str, int]] = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if score_column >= len(cells):
            continue
        score_cell = cells[score_column]
        if not SCORE_RE.match(score_cell):
            continue
        label_cells = [
            cell for index, cell in enumerate(cells)
            if index != score_column and cell and not cell.isdigit()
        ]
        condition = ", ".join(label_cells)
        if len(condition) < 6:
            continue
        rows.append((condition, int(score_cell)))
    return rows


def extract_score_rows_from_text(text: str) -> list[tuple[str, int]]:
    """Handle OCR output where a score lands on its own line after the label."""
    rows: list[tuple[str, int]] = []
    condition: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if SCORE_RE.match(line):
            if condition and len(condition) >= 6:
                rows.append((condition, int(line)))
            condition = None
            continue
        if line.startswith("|"):
            continue
        letters = sum(char.isalpha() for char in line)
        if letters >= 4 and len(line) >= 6:
            condition = line
    return rows
