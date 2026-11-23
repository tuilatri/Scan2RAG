"""End-to-end ingestion pipeline runner.

Iterates over PDFs in data/raw/, runs inspection, extracts text/OCR,
parses statutory structure, and exports structured JSON to data/processed/.
"""

import json
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import pymupdf
from app.ingestion.pdf_inspector import PageType, PDFInspector
from app.ingestion.structure_parser import LegalStructureParser
from app.models.document_schema import DocumentNode, ParsedDocument


def process_document(pdf_path: Path, output_dir: Path, max_pages: int | None = None):
    doc_id = pdf_path.stem.lower()
    doc_name = pdf_path.stem.replace("_", " ")

    print(f"\nProcessing: {doc_name} ({pdf_path.name})")
    inspector = PDFInspector(min_char_threshold=100)
    inspection_res = inspector.inspect_document(pdf_path)
    print(
        f"  Total pages: {inspection_res.total_pages} (Scanned: {inspection_res.scanned_pages}, Digital: {inspection_res.digital_pages}, Mixed: {inspection_res.mixed_pages})"
    )

    doc = pymupdf.open(str(pdf_path))
    parser = LegalStructureParser(document_id=doc_id, document_name=doc_name)
    all_nodes: list[DocumentNode] = []

    pages_to_process = len(doc) if max_pages is None else min(max_pages, len(doc))

    for page_idx in range(pages_to_process):
        page_num = page_idx + 1
        page_info = inspection_res.pages[page_idx]

        # If digital text exists, extract directly; otherwise note for OCR
        text = doc[page_idx].get_text()
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        if page_info.page_type == PageType.SCANNED_IMAGE or not lines:
            # Placeholder for heavy OCR in batch
            lines = [f"[Page {page_num} - Scanned Document Content]"]

        nodes = parser.parse_lines(lines, page_number=page_num)
        all_nodes.extend(nodes)

    parsed_doc = ParsedDocument(
        document_id=doc_id,
        document_name=doc_name,
        total_pages=len(doc),
        nodes=all_nodes,
        summary_stats={
            "nodes_count": len(all_nodes),
            "processed_pages": pages_to_process,
        },
    )

    out_file = output_dir / f"{doc_id}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(parsed_doc.model_dump(), f, ensure_ascii=False, indent=2)

    print(f"  Exported {len(all_nodes)} nodes to {out_file}")


def main():
    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(raw_dir.glob("*.pdf"))
    if not pdf_files:
        print("No PDF files found in data/raw/")
        return

    print(f"Found {len(pdf_files)} PDF files in data/raw/")
    # Run first on sample or all documents
    for pdf in pdf_files:
        process_document(pdf, processed_dir, max_pages=10)

    print("\nIngestion pipeline run completed successfully!")


if __name__ == "__main__":
    main()
