"""Table Extractor module for grouping bounding boxes into structured rows/columns.

Supports multi-column medical evaluation annexes (e.g. Thông tư 105), multi-page
table header inheritance, and mixed-layout splitting (separating preamble text from tables).
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

    HEADER_ROW_KEYWORDS = ["stt", "tt", "chỉ tiêu", "chi tiêu", "bệnh tật", "bnh tt", "thị lực", "điểm", "đim", "loại"]

    def __init__(self, y_threshold: float = 18.0, x_threshold: float = 40.0):
        self.y_threshold = y_threshold
        self.x_threshold = x_threshold

    def is_table_page(self, blocks: list[TextBlock]) -> bool:
        """Determines if a page contains medical / classification table structures."""
        if not blocks:
            return False

        grouped_rows = self.group_blocks_into_rows(blocks)
        max_cols = max(len(r) for r in grouped_rows) if grouped_rows else 0
        if max_cols < 2:
            return False

        texts_lower = [b.text.strip().lower() for b in blocks if b.text.strip()]
        joined_text = " ".join(texts_lower)

        has_table_header = any(
            h in joined_text
            for h in ["chỉ tiêu", "chi tiêu", "bệnh tật", "bnh tt", "thị lực", "tật khúc xạ", "thể lực"]
        ) and any(d in joined_text for d in ["điểm", "đim", "loại", "nam", "nữ", "cao", "cân"])

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

        for row in rows:
            row.sort(key=lambda b: self._get_box_x_center(b.box))

        return rows

    def split_preamble_and_table(
        self, blocks: list[TextBlock]
    ) -> tuple[list[TextBlock], list[TextBlock]]:
        """Splits page into preamble narrative blocks (above table) and table grid blocks.

        Prevents titles/annex headings (e.g. Page 23 of TT 105) from being coerced into empty table rows.
        """
        grouped_rows = self.group_blocks_into_rows(blocks)
        header_row_idx = None

        for r_idx, row in enumerate(grouped_rows):
            row_text = " ".join(b.text.strip().lower() for b in row)
            # Find the first true table header row
            if (
                any(k in row_text for k in ["stt", "tt", "chỉ tiêu", "bệnh tật", "thể lực"])
                and any(d in row_text for d in ["điểm", "loại", "nam", "cao", "cân", "chi tiêu", "đim"])
            ) or (len(row) >= 3 and any(k in row_text for k in ["tt", "bệnh tật", "điểm"])):
                header_row_idx = r_idx
                break

        if header_row_idx is not None and header_row_idx > 0:
            preamble_blocks: list[TextBlock] = []
            for r in grouped_rows[:header_row_idx]:
                preamble_blocks.extend(r)

            table_blocks: list[TextBlock] = []
            for r in grouped_rows[header_row_idx:]:
                table_blocks.extend(r)

            return preamble_blocks, table_blocks

        return [], blocks

    def format_as_markdown(self, rows: list[list[str]]) -> str:
        """Formats 2D list of strings as a Markdown table, pruning completely empty columns."""
        if not rows:
            return ""

        raw_col_count = max(len(r) for r in rows)
        if raw_col_count == 0:
            return ""

        # Normalize row lengths
        normalized_rows = [r + [""] * (raw_col_count - len(r)) for r in rows]

        # Prune columns that are completely empty across all rows
        active_cols: list[int] = []
        for c in range(raw_col_count):
            if any(normalized_rows[r][c].strip() for r in range(len(normalized_rows))):
                active_cols.append(c)

        if not active_cols:
            active_cols = [0]

        filtered_rows = [[r[c] for c in active_cols] for r in normalized_rows]
        final_col_count = len(active_cols)

        md_lines: list[str] = []
        # Header
        header = "| " + " | ".join(filtered_rows[0]) + " |"
        separator = "| " + " | ".join(["---"] * final_col_count) + " |"
        md_lines.append(header)
        md_lines.append(separator)

        # Body
        for row in filtered_rows[1:]:
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
            if any(k in first_row_joined for k in ["stt", "tt", "chỉ tiêu", "bệnh tật", "điểm", "loại"]):
                has_detected_header = True
                header = text_rows[0]

        # Multi-page header inheritance
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
