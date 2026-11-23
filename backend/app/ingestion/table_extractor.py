"""Table Extractor module for grouping bounding boxes into structured rows/columns."""

from pydantic import BaseModel


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


class TableExtractor:
    """Detects tabular layouts and reconstructs Markdown tables from OCR blocks."""

    def __init__(self, y_threshold: float = 12.0):
        self.y_threshold = y_threshold

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
