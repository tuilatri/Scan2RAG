"""OCR adapter layer: preprocess -> recognize -> correct -> extract structure.

The defaults use the open stack already in this repo (OpenCV + PaddleOCR).
An externally licensed engine can be injected without changing callers. No
protected binaries or models from VietNamOCR are copied here.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class OCRPipeline:
    def __init__(
        self,
        preprocess: Callable[[Any], Any] | None = None,
        recognize: Callable[[Any], str] | None = None,
        correct: Callable[[str], str] | None = None,
        structure: Callable[[str], list[tuple[str, int]]] | None = None,
    ) -> None:
        self.preprocess = preprocess or self._default_preprocess
        self.recognize = recognize or self._default_recognize
        self.correct = correct or self._default_correct
        self.structure = structure or self._default_structure

    @staticmethod
    def _default_preprocess(image: Any) -> Any:
        from app.ingestion.image_preprocessor import ImagePreprocessor

        processed_image, _ = ImagePreprocessor().preprocess(image)
        return processed_image

    @staticmethod
    def _default_recognize(image: Any) -> str:
        from app.ingestion.ocr_engine import OCREngine

        return OCREngine().extract_text(image).full_text

    @staticmethod
    def _default_correct(text: str) -> str:
        from app.ingestion.vietnamese_corrector import correct

        return correct(text)

    @staticmethod
    def _default_structure(text: str) -> list[tuple[str, int]]:
        from app.ingestion.table_structure import extract_score_rows, extract_score_rows_from_text

        return extract_score_rows(text) or extract_score_rows_from_text(text)

    def run(self, image: Any) -> dict[str, Any]:
        processed = self.preprocess(image)
        raw_text = self.recognize(processed)
        corrected = self.correct(raw_text)
        return {
            "raw_text": raw_text,
            "corrected_text": corrected,
            "score_rows": self.structure(corrected),
        }
