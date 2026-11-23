"""PDF Inspector module for classifying pages and analyzing structure.

Classifies PDF pages into DIGITAL_TEXT, SCANNED_IMAGE, or MIXED based on
extracted text length and image coverage.
"""

from enum import StrEnum
from pathlib import Path

import pymupdf
from pydantic import BaseModel


class PageType(StrEnum):
    DIGITAL_TEXT = "DIGITAL_TEXT"
    SCANNED_IMAGE = "SCANNED_IMAGE"
    MIXED = "MIXED"


class PageInspectionResult(BaseModel):
    page_number: int
    page_type: PageType
    text_length: int
    has_images: bool
    image_count: int
    width: float
    height: float


class DocumentInspectionResult(BaseModel):
    file_name: str
    total_pages: int
    scanned_pages: int
    digital_pages: int
    mixed_pages: int
    pages: list[PageInspectionResult]


class PDFInspector:
    """Inspects PDF files to classify page types and extract metadata."""

    def __init__(self, min_char_threshold: int = 100):
        self.min_char_threshold = min_char_threshold

    def inspect_page(self, page: pymupdf.Page, page_number: int) -> PageInspectionResult:
        text = page.get_text().strip()
        text_length = len(text)
        images = page.get_images()
        image_count = len(images)
        has_images = image_count > 0

        if text_length >= self.min_char_threshold and not has_images:
            page_type = PageType.DIGITAL_TEXT
        elif text_length < self.min_char_threshold and has_images:
            page_type = PageType.SCANNED_IMAGE
        elif text_length >= self.min_char_threshold and has_images:
            page_type = PageType.MIXED
        else:
            page_type = PageType.SCANNED_IMAGE

        rect = page.rect
        return PageInspectionResult(
            page_number=page_number,
            page_type=page_type,
            text_length=text_length,
            has_images=has_images,
            image_count=image_count,
            width=rect.width,
            height=rect.height,
        )

    def inspect_document(self, file_path: str | Path) -> DocumentInspectionResult:
        doc = pymupdf.open(str(file_path))
        pages_results: list[PageInspectionResult] = []

        scanned = 0
        digital = 0
        mixed = 0

        for i, page in enumerate(doc):
            res = self.inspect_page(page, i + 1)
            pages_results.append(res)
            if res.page_type == PageType.SCANNED_IMAGE:
                scanned += 1
            elif res.page_type == PageType.DIGITAL_TEXT:
                digital += 1
            else:
                mixed += 1

        file_name = Path(file_path).name
        return DocumentInspectionResult(
            file_name=file_name,
            total_pages=len(doc),
            scanned_pages=scanned,
            digital_pages=digital,
            mixed_pages=mixed,
            pages=pages_results,
        )
