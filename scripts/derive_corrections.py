"""Derive Vietnamese correction pairs from OCR corpus vs DOCX reference.

Only pairs that recur across matched facts are proposed, and numbers are
excluded. Writes a reviewable proposal file; --apply writes the tracked
dictionary used by vietnamese_corrector.py.
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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

OCR_STORE = ROOT / "data" / "canonical" / "medical_scores.json"
DOCX_STORE = ROOT / "data" / "canonical" / "medical_scores_docx.json"
PROPOSALS = ROOT / "data" / "exports" / "correction_proposals.json"
DICTIONARY = ROOT / "backend" / "app" / "ingestion" / "correction_dictionary.json"
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(text).lower())
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9đ]", " ", stripped).split())


def number_signature(text: str) -> tuple[str, ...]:
    return tuple(NUMBER_RE.findall(str(text)))


def word_diff(ocr: str, reference: str) -> list[tuple[str, str]]:
    left = normalize(ocr).split()
    right = normalize(reference).split()
    pairs: list[tuple[str, str]] = []
    matcher = difflib.SequenceMatcher(None, left, right)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        source = " ".join(left[i1:i2])
        target = " ".join(right[j1:j2])
        if not source or not target:
            continue
        if NUMBER_RE.search(source) or NUMBER_RE.search(target):
            continue
        if len(source) < 2 or len(target) < 2:
            continue
        pairs.append((source, target))
    return pairs


def derive(min_count: int = 2) -> dict[str, object]:
    ocr = json.loads(OCR_STORE.read_text(encoding="utf-8"))["facts"]
    docx = json.loads(DOCX_STORE.read_text(encoding="utf-8"))["facts"]
    candidates: Counter[tuple[str, str]] = Counter()
    matched = 0

    for reference in docx:
        ref_condition = str(reference.get("condition", ""))
        ref_numbers = number_signature(ref_condition)
        for fact in ocr:
            condition = str(fact.get("condition", ""))
            if number_signature(condition) != ref_numbers:
                continue
            ratio = difflib.SequenceMatcher(
                None, normalize(condition)[:90], normalize(ref_condition)[:90]
            ).ratio()
            if ratio < 0.55:
                continue
            matched += 1
            for pair in word_diff(condition, ref_condition):
                candidates[pair] += 1
            break

    counts: Counter[str] = Counter()
    targets: dict[str, Counter[str]] = {}
    for (source, target), count in candidates.items():
        counts[source] += count
        targets.setdefault(source, Counter())[target] = count

    pairs: dict[str, str] = {}
    for source, total in counts.most_common():
        if total < min_count:
            continue
        best_target = targets[source].most_common(1)[0][0]
        pairs[source] = best_target

    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "matched_pairs": matched,
        "proposal_count": len(pairs),
        "pairs": dict(sorted(pairs.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write tracked dictionary")
    parser.add_argument("--min-count", type=int, default=2)
    args = parser.parse_args()

    payload = derive(args.min_count)
    PROPOSALS.parent.mkdir(parents=True, exist_ok=True)
    PROPOSALS.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "matched_pairs": payload["matched_pairs"],
        "proposal_count": payload["proposal_count"],
    }, ensure_ascii=False))
    for source, target in list(payload["pairs"].items())[:25]:
        print(f"  {source!r} -> {target!r}")

    if args.apply:
        DICTIONARY.write_text(json.dumps({
            "version": 1,
            "source": "derived from canonical OCR vs VietNamOCR DOCX pairs",
            "pairs": payload["pairs"],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Applied -> {DICTIONARY.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
