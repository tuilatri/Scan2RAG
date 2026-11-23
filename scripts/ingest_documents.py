"""End-to-end ingestion pipeline runner with GPU OCR streaming, normalization, and table reconstruction.

Iterates over PDFs in data/raw/, runs inspection, extracts text/OCR via GPU,
detects and reconstructs medical/legal tables, normalizes Vietnamese text,
parses statutory structure, and exports structured JSON to data/processed/.
"""

import argparse
import gc
import json
import sys
import time
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import pymupdf
from app.ingestion.image_preprocessor import ImagePreprocessor
from app.ingestion.ocr_engine import OCREngine, TextBlock
from app.ingestion.pdf_inspector import PageType, PDFInspector
from app.ingestion.pdf_renderer import PDFRenderer
from app.ingestion.structure_parser import LegalStructureParser
from app.ingestion.table_extractor import TableExtractor
from app.ingestion.text_normalizer import TextNormalizer
from app.models.document_schema import DocumentNode, HierarchyLevel, ParsedDocument

_ocr_engine: OCREngine | None = None
_preprocessor: ImagePreprocessor | None = None
_normalizer: TextNormalizer | None = None
_table_extractor: TableExtractor | None = None


def get_ocr_engine() -> OCREngine:
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = OCREngine(use_gpu=True)
    return _ocr_engine


def get_preprocessor() -> ImagePreprocessor:
    global _preprocessor
    if _preprocessor is None:
        _preprocessor = ImagePreprocessor()
    return _preprocessor


def get_normalizer() -> TextNormalizer:
    global _normalizer
    if _normalizer is None:
        _normalizer = TextNormalizer()
    return _normalizer


def get_table_extractor() -> TableExtractor:
    global _table_extractor
    if _table_extractor is None:
        _table_extractor = TableExtractor(y_threshold=18.0)
    return _table_extractor


def process_document(
    pdf_path: Path,
    output_dir: Path,
    max_pages: int | None = None,
    enable_ocr: bool = True,
    skip_existing: bool = False,
):
    doc_id = pdf_path.stem.lower()
    doc_name = pdf_path.stem.replace("_", " ")
    out_file = output_dir / f"{doc_id}.json"

    if skip_existing and out_file.exists():
        try:
            with open(out_file, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("nodes") and len(data.get("nodes")) > 0:
                print(
                    f"Skipping already processed: {doc_name} ({len(data['nodes'])} nodes)"
                )
                return
        except (json.JSONDecodeError, OSError):
            pass

    print("\n========================================================")
    print(f"Processing: {doc_name} ({pdf_path.name})")
    print("========================================================")
    start_time = time.time()

    inspector = PDFInspector(min_char_threshold=100)
    inspection_res = inspector.inspect_document(pdf_path)
    total_doc_pages = len(inspection_res.pages)
    print(
        f"  Total pages: {total_doc_pages} (Scanned: {inspection_res.scanned_pages}, Digital: {inspection_res.digital_pages}, Mixed: {inspection_res.mixed_pages})"
    )

    doc = pymupdf.open(str(pdf_path))
    parser = LegalStructureParser(document_id=doc_id, document_name=doc_name)
    normalizer = get_normalizer()
    preprocessor = get_preprocessor()
    renderer = PDFRenderer(dpi=300)
    table_extractor = get_table_extractor()

    all_nodes: list[DocumentNode] = []
    pages_to_process = (
        total_doc_pages if max_pages is None else min(max_pages, total_doc_pages)
    )
    ocr_pages_count = 0
    tables_count = 0
    active_table_header: list[str] | None = None

    for page_idx in range(pages_to_process):
        page_num = page_idx + 1
        page_info = inspection_res.pages[page_idx]
        p_start = time.time()

        raw_text = doc[page_idx].get_text()
        digital_lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

        page_blocks: list[TextBlock] = []
        is_scanned = (
            page_info.page_type == PageType.SCANNED_IMAGE or len(digital_lines) < 5
        )

        if is_scanned and enable_ocr:
            ocr_pages_count += 1
            ocr_engine = get_ocr_engine()

            # Render single page to image (Streaming generator pattern)
            bgr_image = renderer.render_page(doc[page_idx])
            processed_img, _ = preprocessor.preprocess(bgr_image)

            # OCR inference on GPU
            ocr_res = ocr_engine.extract_text(processed_img, page_number=page_num)

            # Free image memory immediately
            del bgr_image
            del processed_img
            gc.collect()

            # Normalize text inside OCR blocks
            for b in ocr_res.blocks:
                if b.confidence >= 0.5:
                    b.text = normalizer.normalize(b.text)
                    page_blocks.append(b)

            p_type = f"OCR (conf: {ocr_res.avg_confidence:.2f})"
        else:
            # Construct synthetic TextBlocks from digital text lines
            for l_idx, line in enumerate(digital_lines):
                page_blocks.append(
                    TextBlock(
                        text=normalizer.normalize(line),
                        confidence=1.0,
                        box=[
                            [10, l_idx * 20],
                            [500, l_idx * 20],
                            [500, l_idx * 20 + 15],
                            [10, l_idx * 20 + 15],
                        ],
                    )
                )
            p_type = "Digital"

        # Check if page contains tabular layout (e.g. medical annexes in TT 105)
        if table_extractor.is_table_page(page_blocks):
            extracted_tbl = table_extractor.extract_table(
                page_blocks,
                page_number=page_num,
                context_header=active_table_header,
            )
            if extracted_tbl.header:
                active_table_header = extracted_tbl.header

            table_node = DocumentNode(
                id=f"{doc_id}_table_p{page_num}",
                document_id=doc_id,
                document_name=doc_name,
                level=HierarchyLevel.TABLE,
                title=f"Bảng phụ lục tiêu chuẩn sức khỏe (Trang {page_num})",
                content=extracted_tbl.markdown_table,
                page_number=page_num,
                parent_id=None,
                order=len(all_nodes) + 1,
                metadata={
                    "rows_count": extracted_tbl.rows_count,
                    "cols_count": extracted_tbl.cols_count,
                },
            )
            all_nodes.append(table_node)
            tables_count += 1
            node_desc = f"1 TABLE ({extracted_tbl.rows_count} rows, {extracted_tbl.cols_count} cols)"
        else:
            # Narrative statutory text lines
            active_table_header = (
                None  # Reset header inheritance when non-table page appears
            )
            raw_lines = [b.text for b in page_blocks if b.text.strip()]
            nodes = parser.parse_lines(raw_lines, page_number=page_num)
            all_nodes.extend(nodes)
            node_desc = f"{len(nodes)} text nodes"

        p_time = time.time() - p_start
        if page_num % 5 == 0 or page_num == pages_to_process or page_num == 1:
            print(
                f"    Page {page_num}/{pages_to_process} [{p_type}]: {node_desc} ({p_time:.2f}s)"
            )

    doc.close()
    total_elapsed = time.time() - start_time
    throughput = total_elapsed / max(pages_to_process, 1)

    parsed_doc = ParsedDocument(
        document_id=doc_id,
        document_name=doc_name,
        total_pages=total_doc_pages,
        nodes=all_nodes,
        summary_stats={
            "nodes_count": len(all_nodes),
            "tables_count": tables_count,
            "processed_pages": pages_to_process,
            "ocr_pages_count": ocr_pages_count,
            "total_time_seconds": round(total_elapsed, 2),
            "seconds_per_page": round(throughput, 2),
        },
    )

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(parsed_doc.model_dump(), f, ensure_ascii=False, indent=2)

    print(
        f"  ✓ Exported {len(all_nodes)} nodes (including {tables_count} tables) to {out_file.name} in {total_elapsed:.1f}s ({throughput:.2f}s/page)"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Vietnamese legal documents with GPU OCR and Table Extraction."
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Process specific PDF filename in data/raw/",
    )
    parser.add_argument(
        "--all", action="store_true", help="Process all PDFs in data/raw/"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip already processed JSON files",
    )
    parser.add_argument(
        "--max-pages", type=int, default=None, help="Max pages to process per PDF"
    )
    args = parser.parse_args()

    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)

    if args.file:
        target = raw_dir / args.file
        if not target.exists():
            print(f"Error: {target} does not exist.")
            return
        process_document(
            target,
            processed_dir,
            max_pages=args.max_pages,
            skip_existing=args.skip_existing,
        )
    else:
        pdf_files = sorted(raw_dir.glob("*.pdf"), key=lambda p: p.stat().st_size)
        print(f"Found {len(pdf_files)} PDF files in data/raw/")
        for pdf in pdf_files:
            process_document(
                pdf,
                processed_dir,
                max_pages=args.max_pages,
                skip_existing=args.skip_existing,
            )


if __name__ == "__main__":
    main()
