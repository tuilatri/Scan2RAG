"""Render PDF pages as PNG evidence for medical table review (read-only on PDFs)."""

import argparse
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "exports" / "review"


def render_page(doc_id: str, page_number: int, dpi: int = 200) -> Path:
    pdf_path = RAW_DIR / f"{doc_id}.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{doc_id}_p{page_number}.png"
    with pymupdf.open(str(pdf_path)) as doc:
        if page_number < 1 or page_number > len(doc):
            raise IndexError(f"page {page_number} out of range [1, {len(doc)}]")
        pix = doc[page_number - 1].get_pixmap(dpi=dpi)
        pix.save(str(out_path))
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a PDF page for table review.")
    parser.add_argument("doc_id", help="PDF stem, e.g. thông_tư_88")
    parser.add_argument("page", type=int, help="1-based page number")
    parser.add_argument("--dpi", type=int, default=200)
    args = parser.parse_args()
    print(render_page(args.doc_id, args.page, args.dpi))


if __name__ == "__main__":
    main()
