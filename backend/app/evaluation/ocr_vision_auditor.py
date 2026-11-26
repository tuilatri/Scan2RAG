"""OCR Vision Auditor: Evaluates table structure, cell alignment, and medical score fidelity."""

import json
import re
from pathlib import Path
from typing import Any

PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed"
DECISIONS_PATH = Path(__file__).resolve().parents[3] / "docs" / "quality" / "score_collision_decisions.json"

SCORE_LIKE_PATTERN = re.compile(r"^[1-6](?:[Tt])?$")
SCORE_HEADER_TERMS = ("điểm", "phân loại", "chỉ số điểm")
ID_HEADER_TERMS = ("stt", "tt", "số thứ tự", "no.", "id")
NON_SCORE_HEADER_TERMS = ("định mức", "số lượng", "đơn vị tính", "số tt")
SHIFTED_SCORE_PENALTY = 1.0


class OcrVisionAuditor:
    """Audits table structures, row-column alignment, and medical point validation."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or PROCESSED_DIR

    @staticmethod
    def _is_score_like(cell: str) -> bool:
        return bool(SCORE_LIKE_PATTERN.match(cell.strip()))

    @staticmethod
    def _load_reviewed_exceptions() -> set[tuple[str, int, int, int, str]]:
        if not DECISIONS_PATH.exists():
            return set()
        data = json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))
        required = ("node_id", "page_number", "row", "col", "cell_value", "reason", "reviewer", "timestamp")
        return {
            (
                str(item["node_id"]), int(item["page_number"]), int(item["row"]),
                int(item["col"]), str(item["cell_value"]),
            )
            for item in data.get("items", [])
            if all(item.get(field) not in (None, "") for field in required)
            and not item.get("needs_human", False)
        }

    @staticmethod
    def _invalid_decision_count() -> int:
        if not DECISIONS_PATH.exists():
            return 0
        data = json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))
        required = ("node_id", "page_number", "row", "col", "cell_value", "reason", "reviewer", "timestamp")
        return sum(
            1 for item in data.get("items", [])
            if any(item.get(field) in (None, "") for field in required)
            or item.get("needs_human", False)
        )

    def audit(self) -> dict[str, Any]:
        """Audit all extracted tables across documents."""
        total_tables = 0
        vlm_rectified_tables = 0
        hitl_tables = 0
        malformed_tables = 0
        invalid_score_cells = 0
        duplicate_separators = 0
        shifted_score_cells = 0
        reviewed_exceptions = 0
        reviewed_keys = self._load_reviewed_exceptions()
        invalid_decisions = self._invalid_decision_count()
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
                    and not any(term in h.lower() for term in NON_SCORE_HEADER_TERMS)
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
                    if score_like_cols and expected_cols >= 3 and len(score_like_cols) <= 2:
                        score_col_indices = [expected_cols - 1]

                sep_count = 0
                data_row_idx = 0
                for line in table_lines[1:]:
                    if re.match(r"^\|(\s*:?-+:?\s*\|)+$", line):
                        sep_count += 1
                        if sep_count > 1:
                            duplicate_separators += 1
                        continue
                    row_index = data_row_idx
                    data_row_idx += 1
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
                            key = (
                                str(node.get("id")), int(node.get("page_number", 1)),
                                row_index, idx, cell,
                            )
                            if key in reviewed_keys:
                                reviewed_exceptions += 1
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
            "passed": (
                malformed_tables == 0 and invalid_score_cells == 0
                and duplicate_separators == 0
                and shifted_score_cells == reviewed_exceptions
                and invalid_decisions == 0
            ),
            "total_tables": total_tables,
            "vlm_rectified_tables": vlm_rectified_tables,
            "hitl_rectified_tables": hitl_tables,
            "malformed_tables": malformed_tables,
            "invalid_score_cells": invalid_score_cells,
            "duplicate_separators": duplicate_separators,
            "shifted_score_cells": shifted_score_cells,
            "reviewed_exceptions": reviewed_exceptions,
            "invalid_decisions": invalid_decisions,
            "total_cells": total_cells,
            "empty_cell_ratio_pct": round(empty_cell_ratio, 2),
        }
