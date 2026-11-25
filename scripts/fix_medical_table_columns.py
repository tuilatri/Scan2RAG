"""Fix Medical Table Column Alignment, Duplicate Separators, and Metadata (Audit 1B)."""

import json
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.evaluation.ocr_vision_auditor import (  # noqa: E402
    ID_HEADER_TERMS,
    SCORE_HEADER_TERMS,
    OcrVisionAuditor,
)
from audit_processed_data import extract_numbers  # noqa: E402

PROCESSED_DIR = ROOT / "data" / "processed"
COLLISION_REPORT = ROOT / "data" / "exports" / "score_collision_report.json"
NUMBER_TOKEN_PATTERN = re.compile(r"\b\d+(?:\.\d+)?(?:[Tt]|%)?")


def is_separator_line(line: str) -> bool:
    return bool(re.match(r"^\|(\s*:?-+:?\s*\|)+$", line.strip()))


def restore_numbers_from_backup(content: str, backup: str) -> str:
    """Restore numeric tokens from raw backup without touching Vietnamese diacritics."""
    current = extract_numbers(content)
    expected = extract_numbers(backup)
    if len(current) != len(expected):
        raise ValueError(f"number count mismatch: {len(current)} vs {len(expected)}")
    if Counter(current) == Counter(expected):
        return content

    replacements = iter([want if got != want else got for got, want in zip(current, expected)])
    return NUMBER_TOKEN_PATTERN.sub(lambda _: next(replacements), content)


def _score_columns(headers: list[str], body_rows: list[list[str]]) -> list[int]:
    found = [i for i, h in enumerate(headers) if any(t in h.lower() for t in SCORE_HEADER_TERMS)]
    if found:
        return found

    id_cols = {i for i, h in enumerate(headers) if h.strip().lower() in ID_HEADER_TERMS}
    score_like_cols = {
        idx
        for row in body_rows
        for idx, cell in enumerate(row)
        if idx not in id_cols and OcrVisionAuditor._is_score_like(cell)
    }
    if len(headers) >= 3 and len(score_like_cols) <= 2:
        return [len(headers) - 1]
    return []


def normalize_table(
    content: str, collisions: list[dict[str, Any]] | None = None
) -> tuple[str, int, int, bool]:
    """Deduplicate separators, align score cells, return (content, rows, cols, changed)."""
    lines = [line.strip() for line in content.strip().split("\n") if line.strip()]
    table_lines = [line for line in lines if line.startswith("|") and line.endswith("|")]
    if len(table_lines) < 2:
        return content, 0, 0, False

    headers = [c.strip() for c in table_lines[0].strip("|").split("|")]
    cols_count = len(headers)
    body_rows = [
        [c.strip() for c in line.strip("|").split("|")]
        for line in table_lines[1:]
        if not is_separator_line(line)
    ]
    score_cols = _score_columns(headers, body_rows)
    id_cols = {i for i, h in enumerate(headers) if h.strip().lower() in ID_HEADER_TERMS}

    cleaned_rows: list[list[str]] = []
    seen_sep = False
    changed = False
    target = score_cols[0] if score_cols else None

    for line in table_lines[1:]:
        if is_separator_line(line):
            if not seen_sep:
                seen_sep = True
            else:
                changed = True
            continue

        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < cols_count:
            cells += [""] * (cols_count - len(cells))
            changed = True
        elif len(cells) > cols_count:
            cells = cells[:cols_count]
            changed = True

        if target is not None:
            for idx, cell in enumerate(cells):
                if idx in id_cols or idx in score_cols or not OcrVisionAuditor._is_score_like(cell):
                    continue
                if target < len(cells) and not cells[target]:
                    cells[target] = cell
                    cells[idx] = ""
                    changed = True
                elif collisions is not None:
                    collisions.append({
                        "reason": "target_occupied",
                        "cells": cells,
                        "column": idx,
                        "cell_value": cell,
                        "row": len(cleaned_rows),
                    })

        cleaned_rows.append(cells)

    if not seen_sep:
        changed = True

    separator = "| " + " | ".join(["---"] * cols_count) + " |"
    new_content = "\n".join(
        [table_lines[0], separator] + ["| " + " | ".join(row) + " |" for row in cleaned_rows]
    )
    if new_content != content.strip():
        changed = True

    return new_content, len(cleaned_rows), cols_count, changed


def _write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        tmp_path = Path(handle.name)
    os.replace(tmp_path, path)


def main() -> None:
    total_tables = 0
    updated_tables = 0
    collisions: list[dict[str, Any]] = []
    errors: list[str] = []

    for file_path in sorted(PROCESSED_DIR.glob("*.json")):
        if file_path.name.startswith("."):
            continue
        data = json.loads(file_path.read_text(encoding="utf-8"))
        file_changed = False
        file_errors: list[str] = []

        for node in data.get("nodes", []):
            if node.get("level") != "TABLE":
                continue
            total_tables += 1
            meta = node.setdefault("metadata", {})
            content = node.get("content", "")

            if meta.get("hitl_rectified"):
                backup = meta.get("raw_content_backup")
                if not backup:
                    file_errors.append(f"{file_path.name} node {node.get('id')}: missing raw_content_backup")
                    continue
                try:
                    restored = restore_numbers_from_backup(content, backup)
                except ValueError as exc:
                    file_errors.append(f"{file_path.name} node {node.get('id')}: {exc}")
                    continue
                if restored != content:
                    content = restored
                    node["content"] = restored
                    file_changed = True

            node_collisions: list[dict[str, Any]] = []
            new_content, rows, cols, changed = normalize_table(content, node_collisions)
            for item in node_collisions:
                item.update(
                    document_id=data.get("document_id"),
                    node_id=node.get("id"),
                    page_number=node.get("page_number"),
                )
            collisions.extend(node_collisions)

            if changed or meta.get("rows_count") != rows or meta.get("cols_count") != cols:
                node["content"] = new_content
                meta["rows_count"] = rows
                meta["cols_count"] = cols
                updated_tables += 1
                file_changed = True

        if file_errors:
            errors.extend(file_errors)
        elif file_changed:
            _write_json_atomic(file_path, data)

    _write_json_atomic(COLLISION_REPORT, {"total": len(collisions), "items": collisions})
    print(f"Processed {total_tables} tables, updated {updated_tables} tables.")
    print(f"Collisions needing review: {len(collisions)} -> {COLLISION_REPORT}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        raise RuntimeError(f"{len(errors)} table(s) failed number restoration; no files written")


if __name__ == "__main__":
    main()
