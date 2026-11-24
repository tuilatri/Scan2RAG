"""OCR Engine module integrating PaddleOCR for Vietnamese text extraction on GPU/CPU."""

import numpy as np
import paddle
from numpy.typing import NDArray
from paddleocr import PaddleOCR
from pydantic import BaseModel


class TextBlock(BaseModel):
    text: str
    confidence: float
    box: list[list[float]]  # 4 corner points or polygon


class OCRPageResult(BaseModel):
    page_number: int
    blocks: list[TextBlock]
    full_text: str
    avg_confidence: float


class OCREngine:
    """Encapsulates PaddleOCR with Vietnamese model and GPU/CPU device management."""

    def __init__(self, use_gpu: bool = True, lang: str = "vi"):
        self.use_gpu = use_gpu and paddle.is_compiled_with_cuda()
        if self.use_gpu:
            paddle.device.set_device("gpu:0")
        else:
            paddle.device.set_device("cpu")

        # PaddleOCR 3.7+ initialization
        self.ocr = PaddleOCR(
            lang=lang,
            use_doc_orientation_classify=False,
            use_textline_orientation=True,
        )

    def extract_text(self, image: NDArray[np.uint8], page_number: int = 1) -> OCRPageResult:
        """Runs PaddleOCR on the provided image and formats the result."""
        # Use predict method for PaddleOCR 3.7+ / PaddleX pipeline
        results = list(self.ocr.predict(image))

        blocks: list[TextBlock] = []
        text_lines: list[str] = []
        confidences: list[float] = []

        if results and len(results) > 0:
            res = results[0]
            # Handle PaddleX OCRResult dictionary-like object
            rec_texts = res.get("rec_texts", [])
            rec_scores = res.get("rec_scores", [])
            rec_polys = res.get("rec_polys", [])

            for text, score, poly in zip(rec_texts, rec_scores, rec_polys, strict=False):
                text_clean = str(text).strip()
                if not text_clean:
                    continue

                conf = float(score)
                box_coords = poly.tolist() if hasattr(poly, "tolist") else list(poly)

                blocks.append(
                    TextBlock(
                        text=text_clean,
                        confidence=round(conf, 4),
                        box=box_coords,
                    )
                )
                text_lines.append(text_clean)
                confidences.append(conf)

        avg_conf = float(np.mean(confidences)) if confidences else 0.0
        full_text = "\n".join(text_lines)

        return OCRPageResult(
            page_number=page_number,
            blocks=blocks,
            full_text=full_text,
            avg_confidence=round(avg_conf, 4),
        )
