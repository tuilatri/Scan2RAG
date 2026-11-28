"""Phase 0 OCR benchmark: current pipeline vs VietNamOCR DOCX reference.

Runs the project's open OCR stack on sampled raw pages at 300 DPI, extracts
score rows, and compares them with DOCX-derived canonical facts. Produces
data/benchmarks/ocr_engine_comparison.json. No corpus/serving is modified.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

RAW = ROOT / "data" / "raw"
CANONICAL = ROOT / "data" / "canonical" / "medical_scores_docx.json"
CORPUS_FACTS = ROOT / "data" / "canonical" / "medical_scores.json"
CORPUS_GUIDANCE = ROOT / "data" / "processed" / "hướng_dẫn_cục_quân_y.json"
OUT = ROOT / "data" / "benchmarks" / "ocr_engine_comparison.json"

SAMPLES = [
    ("thông_tư_105", 23, "Thông_tư_105.pdf"),
    ("thông_tư_88", 31, "Thông_tư_88.pdf"),
    ("hướng_dẫn_cục_quân_y", 1, "Hướng_dẫn_Cục_quân_y.pdf"),
    ("hướng_dẫn_cục_quân_y", 2, "Hướng_dẫn_Cục_quân_y.pdf"),
    ("hướng_dẫn_cục_quân_y", 4, "Hướng_dẫn_Cục_quân_y.pdf"),
]
PROTECTED_BY_PAGE = {
    ("hướng_dẫn_cục_quân_y", 1): "loại 1, loại 2, loại 3",
    ("hướng_dẫn_cục_quân_y", 2): "viễn thị các mức độ",
    ("hướng_dẫn_cục_quân_y", 4): "không cho điểm để phân loại sức khỏe",
}
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(text).lower())
    stripped = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return " ".join(re.sub(r"[^a-z0-9đ]", " ", stripped).split())


def levenshtein(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for i, char_left in enumerate(left, start=1):
        current = [i]
        for j, char_right in enumerate(right, start=1):
            current.append(min(
                current[j - 1] + 1,
                previous[j] + 1,
                previous[j - 1] + (char_left != char_right),
            ))
        previous = current
    return previous[-1]


def cer_wer(reference: str, candidate: str) -> tuple[float, float]:
    ref_chars, cand_chars = reference, candidate
    ref_words, cand_words = reference.split(), candidate.split()
    char_rate = levenshtein(ref_chars, cand_chars) / max(len(ref_chars), 1)
    word_rate = levenshtein(" ".join(ref_words), " ".join(cand_words)) / max(len(" ".join(ref_words)), 1)
    return round(char_rate, 4), round(word_rate, 4)


def match_reference_row(
    condition: str,
    extracted: list[tuple[str, int]],
) -> tuple[str, int] | None:
    needle = normalize(condition)
    best: tuple[str, int] | None = None
    best_ratio = 0.0
    for row in extracted:
        ratio = difflib.SequenceMatcher(None, needle[:90], normalize(row[0])[:90]).ratio()
        if ratio > best_ratio:
            best_ratio, best = ratio, row
    return best if best_ratio >= 0.55 else None


def number_retention(reference: str, candidate: str) -> bool:
    expected = Counter(NUMBER_RE.findall(reference))
    actual = Counter(NUMBER_RE.findall(candidate))
    return all(actual[value] >= count for value, count in expected.items())


def render_page(pdf_name: str, page_no: int, dpi: int = 300) -> Any:
    import cv2
    import numpy as np
    import pymupdf

    document = pymupdf.open(RAW / pdf_name)
    pixmap = document[page_no - 1].get_pixmap(matrix=pymupdf.Matrix(dpi / 72, dpi / 72))
    image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
        pixmap.height, pixmap.width, pixmap.n
    )
    if pixmap.n == 3:
        return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    return cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)


def benchmark_page(
    document_id: str,
    page_no: int,
    pdf_name: str,
    reference_facts: list[dict[str, Any]],
    engine: Any,
) -> dict[str, Any]:
    from app.ingestion.image_preprocessor import ImagePreprocessor
    from app.ingestion.table_extractor import TableExtractor
    from app.ingestion.table_structure import extract_score_rows, extract_score_rows_from_text
    from app.ingestion.vietnamese_corrector import correct

    image = render_page(pdf_name, page_no)
    processed, preprocess_result = ImagePreprocessor().preprocess(image)
    ocr_result = engine.extract_text(processed, page_number=page_no)
    corrected = correct(ocr_result.full_text)
    table = TableExtractor().extract_table(ocr_result.blocks, page_number=page_no)
    extracted = extract_score_rows(table.markdown_table)
    if not extracted:
        extracted = extract_score_rows_from_text(corrected)

    hits = 0
    numbers_ok = 0
    compared = 0
    reference_text: list[str] = []
    candidate_text: list[str] = []
    for fact in reference_facts:
        condition = str(fact.get("condition", ""))
        reference_text.append(condition)
        matched = match_reference_row(condition, extracted)
        if not matched:
            candidate_text.append("")
            continue
        candidate_text.append(matched[0])
        compared += 1
        if int(matched[1]) == int(float(fact.get("value", 0))):
            hits += 1
        if number_retention(condition, matched[0]):
            numbers_ok += 1

    cer, wer = cer_wer(" | ".join(reference_text), " | ".join(candidate_text))
    protected = PROTECTED_BY_PAGE.get((document_id, page_no))
    protected_hit = True
    if protected:
        protected_hit = protected in corrected.lower()

    return {
        "document_id": document_id,
        "page": page_no,
        "preprocess": preprocess_result.model_dump(),
        "ocr_avg_confidence": ocr_result.avg_confidence,
        "ocr_text": corrected,
        "ocr_text_preview": corrected[:300],
        "table_markdown_preview": table.markdown_table[:300],
        "reference_facts": len(reference_facts),
        "extracted_rows": len(extracted),
        "matched_reference_facts": compared,
        "score_cell_hits": hits,
        "score_cell_accuracy": round(hits / max(len(reference_facts), 1), 4),
        "number_retention": round(numbers_ok / max(compared, 1), 4),
        "cer_vs_docx_conditions": cer,
        "wer_vs_docx_conditions": wer,
        "protected_phrase_hit": protected_hit,
    }


def benchmark_page_from_corpus(
    document_id: str,
    page_no: int,
    reference_facts: list[dict[str, Any]],
    corpus_facts: list[dict[str, Any]],
    guidance_text: str,
) -> dict[str, Any]:
    candidates = [
        (str(fact.get("condition", "")), int(float(fact.get("value", 0))))
        for fact in corpus_facts
        if fact["document_id"] == document_id and fact["page"] == page_no
    ]
    hits = 0
    numbers_ok = 0
    compared = 0
    reference_text: list[str] = []
    candidate_text: list[str] = []
    for fact in reference_facts:
        condition = str(fact.get("condition", ""))
        reference_text.append(condition)
        matched = match_reference_row(condition, candidates)
        if not matched:
            candidate_text.append("")
            continue
        candidate_text.append(matched[0])
        compared += 1
        if matched[1] == int(float(fact.get("value", 0))):
            hits += 1
        if number_retention(condition, matched[0]):
            numbers_ok += 1

    cer, wer = cer_wer(" | ".join(reference_text), " | ".join(candidate_text))
    protected = PROTECTED_BY_PAGE.get((document_id, page_no))
    protected_hit = True
    if protected:
        protected_hit = protected in guidance_text.lower()

    return {
        "document_id": document_id,
        "page": page_no,
        "source": "corpus (already ingested OCR output)",
        "reference_facts": len(reference_facts),
        "extracted_rows": len(candidates),
        "matched_reference_facts": compared,
        "score_cell_hits": hits,
        "score_cell_accuracy": round(hits / max(len(reference_facts), 1), 4),
        "number_retention": round(numbers_ok / max(compared, 1), 4),
        "cer_vs_docx_conditions": cer,
        "wer_vs_docx_conditions": wer,
        "protected_phrase_hit": protected_hit,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run PaddleOCR live (needs working torch/PaddleOCR in this venv)",
    )
    args = parser.parse_args()

    reference = json.loads(CANONICAL.read_text(encoding="utf-8"))["facts"]
    pages: list[dict[str, Any]] = []

    if args.live:
        # Preload torch before paddlex/modelscope pulls it in; otherwise the
        # Windows shm.dll load order fails with WinError 127 in this venv.
        import torch  # noqa: F401

        from app.ingestion.ocr_engine import OCREngine

        engine = OCREngine(use_gpu=False)
        for document_id, page_no, pdf_name in SAMPLES:
            facts = [
                fact for fact in reference
                if fact["document_id"] == document_id and fact["page"] == page_no
            ]
            pages.append(benchmark_page(document_id, page_no, pdf_name, facts, engine))
        engine_name = "OpenCV preprocess + PaddleOCR vi + TableExtractor + corrector"
    else:
        corpus_facts = json.loads(CORPUS_FACTS.read_text(encoding="utf-8"))["facts"]
        guidance_nodes = json.loads(CORPUS_GUIDANCE.read_text(encoding="utf-8"))["nodes"]
        guidance_by_page: dict[int, str] = {}
        for node in guidance_nodes:
            page = int(node.get("page_number") or 0)
            guidance_by_page[page] = guidance_by_page.get(page, "") + str(node.get("content", ""))
        for document_id, page_no, _ in SAMPLES:
            facts = [
                fact for fact in reference
                if fact["document_id"] == document_id and fact["page"] == page_no
            ]
            guidance_text = (
                guidance_by_page.get(page_no, "")
                if document_id == "hướng_dẫn_cục_quân_y" else ""
            )
            pages.append(
                benchmark_page_from_corpus(document_id, page_no, facts, corpus_facts, guidance_text)
            )
        engine_name = "corpus OCR output already ingested (live OCR unavailable in this venv)"

    summary = {
        "pages": len(pages),
        "reference_facts": sum(page["reference_facts"] for page in pages),
        "matched_reference_facts": sum(page["matched_reference_facts"] for page in pages),
        "score_cell_hits": sum(page["score_cell_hits"] for page in pages),
        "score_cell_accuracy": round(
            sum(page["score_cell_hits"] for page in pages)
            / max(sum(page["reference_facts"] for page in pages), 1), 4
        ),
        "number_retention": round(
            sum(page["number_retention"] for page in pages) / max(len(pages), 1), 4
        ),
        "protected_phrase_pages": sum(1 for page in pages if page["document_id"] == "hướng_dẫn_cục_quân_y"),
        "protected_phrase_hits": sum(
            1 for page in pages
            if page["document_id"] == "hướng_dẫn_cục_quân_y" and page["protected_phrase_hit"]
        ),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provisional_reference": True,
        "reference_source": "drafts/outsource/ocr-result.docx via scripts/ingest_docx_facts.py",
        "engine": engine_name,
        "summary": summary,
        "pages": pages,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Report: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
