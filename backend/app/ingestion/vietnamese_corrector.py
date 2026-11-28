"""Deterministic Vietnamese OCR correction inspired by VietNamOCR's ProtonX layer.

This is NOT the ProtonX model (licensed v1.4-NC). It is a small, auditable
dictionary pass for recurring OCR damage in this corpus. Numbers are never
rewritten, and legal phrases listed in PROTECTED_PHRASES are left untouched.
"""

from __future__ import annotations

import re

TYPO_MAP = {
    "đnh": "định",
    "gii thích": "giải thích",
    "mc 1": "mục 1",
    "mc 2": "mục 2",
    "lon th": "loạn thị",
    "thềE": "thị",
    "viềE": "viễn",
    "chềE": "chỉ",
    "bềE": "bị",
    "đềE": "để",
    "trềElên": "trở lên",
    "đưới": "dưới",
    "Dim": "Điểm",
}

PROTECTED_PHRASES = (
    "không gọi nhập ngũ",
    "viễn thị các mức độ",
    "không cho điểm để phân loại sức khỏe",
)

_PATTERN = re.compile(
    "|".join(re.escape(key) for key in sorted(TYPO_MAP, key=len, reverse=True)),
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def correct(text: str) -> str:
    """Correct known OCR damage without touching numbers or protected phrases."""
    if not text:
        return text

    numbers = _NUMBER_RE.findall(text)
    placeholders: list[tuple[str, str]] = []
    for index, number in enumerate(numbers):
        token = f"__SCAN2RAG_NUMBER_{index}_END__"
        placeholders.append((token, number))
        text = text.replace(number, token, 1)

    preserved: list[str] = []
    for phrase in PROTECTED_PHRASES:
        while phrase in text.lower():
            start = text.lower().find(phrase)
            original = text[start : start + len(phrase)]
            preserved.append(original)
            token = f"__PROTECTED{len(preserved) - 1}__"
            text = text[:start] + token + text[start + len(phrase):]

    text = _PATTERN.sub(lambda match: TYPO_MAP.get(match.group(0), match.group(0)), text)
    for index, original in enumerate(preserved):
        text = text.replace(f"__PROTECTED{index}__", original)

    for token, number in reversed(placeholders):
        text = text.replace(token, number)
    return text
