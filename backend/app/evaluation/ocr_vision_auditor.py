"""OCR Vision Auditor: Evaluates table structure, cell alignment, and medical score fidelity."""

import json
import re
from pathlib import Path
from typing import Any

PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed"

SCORE_LIKE_PATTERN = re.compile(r"^[1-6](?:[Tt])?$")
SCORE_HEADER_TERMS = ("điểm", "phân loại", "chỉ số điểm")
ID_HEADER_TERMS = ("stt", "tt", "số thứ tự", "no.", "id")
SHIFTED_SCORE_PENALTY = 1.0


class OcrVisionAuditor:
    """Audits table structures, row-column alignment, and medical point validation."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or PROCESSED_DIR

    @staticmethod
    def _is_score_like(cell: str) -> bool:
        return bool(SCORE_LIKE_PATTERN.match(cell.strip()))

    def audit(self) -> dict[str, Any]:
        """Audit all extracted tables across documents."""
        total_tables = 0
        vlm_rectified_tables = 0
        hitl_tables = 0
        malformed_tables = 0
        invalid_score_cells = 0
        duplicate_separators = 0
        shifted_score_cells = 0
        total_cells = 0
        empty_cells = 0

        for file_path in sorted(self.data_dir.glob("*.json")):
            if file_path.name.startswith("."):
                continue
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            nodes = data.get("nodes", [])
            for node in nodes:
                if node.get("level") != "TABLE":
                    continue

                total_tables += 1
                meta = node.get("metadata", {})
                if meta.get("vlm_rectified"):
                    vlm_rectified_tables += 1
                if meta.get("hitl_rectified") or meta.get("hitl_approved"):
                    hitl_tables += 1

                content = node.get("content", "").strip()
                lines = [line.strip() for line in content.split("\n") if line.strip()]
                table_lines = [line for line in lines if line.startswith("|") and line.endswith("|")]

                if len(table_lines) < 2:
                    malformed_tables += 1
                    continue

                headers = [c.strip() for c in table_lines[0].strip("|").split("|")]
                expected_cols = len(headers)
                score_col_indices = [
                    i for i, h in enumerate(headers)
                    if any(term in h.lower() for term in SCORE_HEADER_TERMS)
                ]
                id_col_indices = [
                    i for i, h in enumerate(headers)
                    if h.strip().lower() in ID_HEADER_TERMS
                ]
                if not score_col_indices:
                    body_rows = [
                        [c.strip() for c in line.strip("|").split("|")]
                        for line in table_lines[1:]
                        if not re.match(r"^\|(\s*:?-+:?\s*\|)+$", line)
                    ]
                    score_like_cols = {
                        i for row in body_rows for i, c in enumerate(row)
                        if i not in id_col_indices and self._is_score_like(c)
                    }
                    if expected_cols >= 3 and len(score_like_cols) <= 2:
                        score_col_indices = [expected_cols - 1]

                sep_count = 0
                for line in table_lines[1:]:
                    if re.match(r"^\|(\s*:?-+:?\s*\|)+$", line):
                        sep_count += 1
                        if sep_count > 1:
                            duplicate_separators += 1
                        continue
                    cells = [c.strip() for c in line.strip("|").split("|")]
                    total_cells += len(cells)

                    if len(cells) != expected_cols:
                        malformed_tables += 1

                    for idx, cell in enumerate(cells):
                        if not cell:
                            empty_cells += 1
                        if not score_col_indices or idx in id_col_indices:
                            continue
                        if self._is_score_like(cell) and idx not in score_col_indices:
                            shifted_score_cells += 1
                        # Only validate medical score columns (1-6)
                        if idx in score_col_indices and cell.isdigit():
                            val = int(cell)
                            if val < 1 or val > 6:
                                invalid_score_cells += 1

        empty_cell_ratio = (empty_cells / total_cells * 100) if total_cells else 0.0
        score = 100.0
        if malformed_tables > 0:
            score -= malformed_tables * 5.0
        if invalid_score_cells > 0:
            score -= invalid_score_cells * 2.0
        if shifted_score_cells > 0:
            score -= shifted_score_cells * SHIFTED_SCORE_PENALTY

        return {
            "persona": "ocr_vision_specialist",
            "score": max(round(score, 1), 0.0),
            "passed": malformed_tables == 0 and invalid_score_cells == 0 and duplicate_separators == 0 and shifted_score_cells == 0,
            "total_tables": total_tables,
            "vlm_rectified_tables": vlm_rectified_tables,
            "hitl_rectified_tables": hitl_tables,
            "malformed_tables": malformed_tables,
            "invalid_score_cells": invalid_score_cells,
            "duplicate_separators": duplicate_separators,
            "shifted_score_cells": shifted_score_cells,
            "total_cells": total_cells,
            "empty_cell_ratio_pct": round(empty_cell_ratio, 2),
        }
