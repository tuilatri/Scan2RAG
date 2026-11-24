"""PDF Renderer module for converting PDF pages to high-resolution OpenCV images."""

from pathlib import Path

import cv2
import numpy as np
import pymupdf
from numpy.typing import NDArray


class PDFRenderer:
    """Renders PDF pages into OpenCV-compatible numpy BGR images."""

    def __init__(self, dpi: int = 300):
        self.dpi = dpi

    def render_page(self, page: pymupdf.Page) -> NDArray[np.uint8]:
        """Render a single PyMuPDF page to an OpenCV BGR image at target DPI."""
        pix = page.get_pixmap(dpi=self.dpi)
        # Convert pixmap samples to numpy array
        img_np = np.frombuffer(pix.samples, dtype=np.uint8)
        if pix.alpha:
            img_np = img_np.reshape((pix.height, pix.width, 4))
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
        else:
            img_np = img_np.reshape((pix.height, pix.width, 3))
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        return img_bgr

    def render_document_page(self, file_path: str | Path, page_number: int) -> NDArray[np.uint8]:
        """Render a specific 1-based page number from a PDF file."""
        doc = pymupdf.open(str(file_path))
        if page_number < 1 or page_number > len(doc):
            raise IndexError(f"Page number {page_number} out of range [1, {len(doc)}]")
        page = doc[page_number - 1]
        return self.render_page(page)
