"""Table Extractor module for grouping bounding boxes into structured rows/columns.

Supports multi-column medical evaluation annexes (e.g. Thông tư 105) and multi-page
table header inheritance.
"""

from pydantic import BaseModel

from app.ingestion.ocr_engine import TextBlock


class TableCell(BaseModel):
    row_idx: int
    col_idx: int
    text: str
    confidence: float


class ExtractedTable(BaseModel):
    page_number: int
    rows_count: int
    cols_count: int
    cells: list[TableCell]
    markdown_table: str
    header: list[str] = []


class TableExtractor:
    """Detects tabular layouts and reconstructs Markdown tables from OCR blocks."""

    DEFAULT_MEDICAL_HEADER = [
        "STT",
        "Chỉ tiêu / Bệnh tật",
        "Điểm 1",
        "Điểm 2",
        "Điểm 3",
        "Điểm 4",
        "Điểm 5",
        "Điểm 6",
    ]

    TABLE_KEYWORDS = [
        "tt",
        "stt",
        "bệnh tật",
        "bnh tt",
        "chỉ tiêu",
        "chi tiêu",
        "điểm",
        "đim",
        "phụ lục",
        "phu lc",
        "tiêu chuẩn",
        "tật khúc xạ",
        "thị lực",
        "th lón hon",
    ]

    def __init__(self, y_threshold: float = 18.0, x_threshold: float = 40.0):
        self.y_threshold = y_threshold
        self.x_threshold = x_threshold

    def is_table_page(self, blocks: list[TextBlock]) -> bool:
        """Determines if a page contains medical / classification table structures."""
        if not blocks:
            return False

        # First, group blocks into rows and check if there are multi-column rows
        grouped_rows = self.group_blocks_into_rows(blocks)
        max_cols = max(len(r) for r in grouped_rows) if grouped_rows else 0
        if max_cols < 2:
            # Single-column text flow is never a table
            return False

        texts_lower = [b.text.strip().lower() for b in blocks if b.text.strip()]
        joined_text = " ".join(texts_lower)

        # Keyword match for tabular headers
        has_table_header = any(
            h in joined_text
            for h in ["chỉ tiêu", "chi tiêu", "bệnh tật", "bnh tt", "thị lực", "tật khúc xạ"]
        ) and any(d in joined_text for d in ["điểm", "đim", "loại"])

        # Check for numeric score columns: multiple single digits between 1-6 or 1T-6T
        score_like_blocks = sum(
            1
            for t in texts_lower
            if t in {"1", "2", "3", "4", "5", "6", "1t", "2t", "3t", "4t", "5t", "6t"}
        )

        return (has_table_header and score_like_blocks >= 1) or score_like_blocks >= 4

    def _get_box_y_center(self, box: list[list[float]]) -> float:
        """Calculates center Y coordinate of a 4-point bounding box."""
        ys = [p[1] for p in box]
        return float(sum(ys) / len(ys)) if ys else 0.0

    def _get_box_x_center(self, box: list[list[float]]) -> float:
        """Calculates center X coordinate of a 4-point bounding box."""
        xs = [p[0] for p in box]
        return float(sum(xs) / len(xs)) if xs else 0.0

    def group_blocks_into_rows(self, blocks: list[TextBlock]) -> list[list[TextBlock]]:
        """Groups text blocks into rows by clustering their vertical Y coordinates."""
        if not blocks:
            return []

        # Sort blocks primarily by Y center, then X center
        sorted_blocks = sorted(
            blocks,
            key=lambda b: (self._get_box_y_center(b.box), self._get_box_x_center(b.box)),
        )

        rows: list[list[TextBlock]] = []
        for block in sorted_blocks:
            y_center = self._get_box_y_center(block.box)
            placed = False

            for row in rows:
                row_y_avg = sum(self._get_box_y_center(b.box) for b in row) / len(row)
                if abs(y_center - row_y_avg) <= self.y_threshold:
                    row.append(block)
                    placed = True
                    break

            if not placed:
                rows.append([block])

        # Within each row, sort left to right (X center)
        for row in rows:
            row.sort(key=lambda b: self._get_box_x_center(b.box))

        return rows

    def format_as_markdown(self, rows: list[list[str]]) -> str:
        """Formats 2D list of strings as a Markdown table."""
        if not rows:
            return ""

        col_count = max(len(r) for r in rows)
        if col_count == 0:
            return ""

        # Normalize row lengths
        normalized_rows = [r + [""] * (col_count - len(r)) for r in rows]

        md_lines: list[str] = []
        # Header
        header = "| " + " | ".join(normalized_rows[0]) + " |"
        separator = "| " + " | ".join(["---"] * col_count) + " |"
        md_lines.append(header)
        md_lines.append(separator)

        # Body
        for row in normalized_rows[1:]:
            md_lines.append("| " + " | ".join(row) + " |")

        return "\n".join(md_lines)

    def extract_table(
        self,
        blocks: list[TextBlock],
        page_number: int = 1,
        context_header: list[str] | None = None,
    ) -> ExtractedTable:
        """Extracts table from blocks and applies context header inheritance for multi-page tables."""
        grouped_rows = self.group_blocks_into_rows(blocks)
        text_rows = [[b.text for b in row] for row in grouped_rows]

        header = []
        has_detected_header = False
        if text_rows:
            first_row_joined = " ".join(text_rows[0]).lower()
            if any(
                k in first_row_joined for k in ["stt", "tt", "chỉ tiêu", "bệnh tật", "điểm", "loại"]
            ):
                has_detected_header = True
                header = text_rows[0]

        # Multi-page header inheritance (Blindspot 1 mitigation)
        if not has_detected_header and context_header:
            header = context_header
            text_rows = [context_header] + text_rows

        cells: list[TableCell] = []
        for r_idx, row in enumerate(grouped_rows):
            for c_idx, block in enumerate(row):
                cells.append(
                    TableCell(
                        row_idx=r_idx,
                        col_idx=c_idx,
                        text=block.text,
                        confidence=block.confidence,
                    )
                )

        md_str = self.format_as_markdown(text_rows)

        return ExtractedTable(
            page_number=page_number,
            rows_count=len(text_rows),
            cols_count=max(len(r) for r in text_rows) if text_rows else 0,
            cells=cells,
            markdown_table=md_str,
            header=header,
        )
