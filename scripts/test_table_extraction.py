"""Test table extraction on 2 consecutive annex pages of Thông tư 105.

Verifies multi-column grouping and context header inheritance across page boundaries.
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.ingestion.image_preprocessor import ImagePreprocessor
from app.ingestion.ocr_engine import OCREngine
from app.ingestion.pdf_renderer import PDFRenderer
from app.ingestion.table_extractor import TableExtractor


def test_table_extraction_on_tt105():
    pdf_path = Path("data/raw/Thông_tư_105.pdf")
    if not pdf_path.exists():
        print(f"File {pdf_path} not found.")
        return

    renderer = PDFRenderer(dpi=300)
    preprocessor = ImagePreprocessor()
    ocr = OCREngine(use_gpu=True)
    table_extractor = TableExtractor(y_threshold=18.0)

    # Let's inspect pages 25 and 26 (typical medical criteria annex section in TT 105)
    test_pages = [25, 26]
    inherited_header = None

    for page_num in test_pages:
        print(f"\n--- Testing Table Extraction on Page {page_num} of Thông tư 105 ---")
        bgr_img = renderer.render_document_page(pdf_path, page_num)
        clean_img, _ = preprocessor.preprocess(bgr_img)
        ocr_res = ocr.extract_text(clean_img, page_number=page_num)

        print(
            f"  OCR extracted {len(ocr_res.blocks)} blocks. Avg confidence: {ocr_res.avg_confidence}"
        )

        table = table_extractor.extract_table(
            ocr_res.blocks,
            page_number=page_num,
            context_header=inherited_header,
        )

        print(f"  Extracted Table: {table.rows_count} rows, {table.cols_count} cols")
        if table.header:
            print(f"  Table Header: {table.header}")
            inherited_header = table.header

        print("  Sample Markdown Table Preview:")
        preview_lines = table.markdown_table.split("\n")[:10]
        for l in preview_lines:
            print(f"    {l}")


if __name__ == "__main__":
    test_table_extraction_on_tt105()
