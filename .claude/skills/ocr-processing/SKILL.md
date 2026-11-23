---
name: ocr-processing
description: Expert guidance on PDF inspection, image preprocessing (OpenCV deskew, denoise), Vietnamese OCR using PaddleOCR, table layout parsing, and CER/WER error assessment.
---

# OCR Processing & Vietnamese Document Digitization

Use this skill when implementing, testing, or debugging the offline PDF and scanned document ingestion pipeline.

## 1. Pipeline Stages
1. **PDF Inspection & Page Rendering**:
   - Use `PyMuPDF` (`fitz`) to check if the PDF contains digital text layers or scanned images.
   - Render pages at 300 DPI for high-fidelity OCR: `page.get_pixmap(dpi=300)`.
2. **OpenCV Image Preprocessing**:
   - **Grayscale**: `cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)`
   - **Deskew**: Detect orientation angles using Hough line transform (`cv2.HoughLinesP`) or contour bounding boxes (`cv2.minAreaRect`), then rotate.
   - **Denoising**: `cv2.bilateralFilter()` or `cv2.fastNlMeansDenoising()` to preserve character edges while reducing paper noise.
   - **Binarization / Adaptive Threshold**: `cv2.adaptiveThreshold(cv2.ADAPTIVE_THRESH_GAUSSIAN_C)`.
3. **Vietnamese OCR Extraction**:
   - Primary: `PaddleOCR(use_angle_cls=True, lang='vi')`.
   - Baseline Benchmark: `pytesseract.image_to_string(img, lang='vie')`.
4. **Table Structure Extraction**:
   - Medical criteria tables (Thông tư 105) have complex multi-column layouts. Use `Docling` or specialized layout analysis to extract Markdown/HTML tables rather than flat lines.
5. **Quality Assessment**:
   - Measure **CER (Character Error Rate)** and **WER (Word Error Rate)** against manual transcription benchmarks using `jiwer`.
