"""Sample script to test the OCR and Preprocessing pipeline on 1 sample scanned page."""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.ingestion.image_preprocessor import ImagePreprocessor
from app.ingestion.ocr_engine import OCREngine
from app.ingestion.pdf_renderer import PDFRenderer


def run_sample():
    pdf_path = Path("data/raw/Thông_tư_68.pdf")
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        return

    print("1. Rendering page 1 at 300 DPI...")
    renderer = PDFRenderer(dpi=300)
    img_bgr = renderer.render_document_page(pdf_path, page_number=1)
    print(f"Rendered image shape: {img_bgr.shape}")

    print("2. Preprocessing image (Deskew, Denoise)...")
    preprocessor = ImagePreprocessor()
    processed_img, prep_res = preprocessor.preprocess(img_bgr)
    print(f"Preprocessing completed. Skew angle detected: {prep_res.skew_angle} deg")

    print("3. Initializing PaddleOCR on GPU...")
    ocr = OCREngine(use_gpu=True, lang="vi")

    print("4. Running OCR extraction...")
    ocr_res = ocr.extract_text(processed_img, page_number=1)

    print("\n--- OCR RESULTS ---")
    print(f"Total blocks detected: {len(ocr_res.blocks)}")
    print(f"Average confidence: {ocr_res.avg_confidence}")
    print("\nFirst 300 characters extracted:")
    print(ocr_res.full_text[:300])


if __name__ == "__main__":
    run_sample()
