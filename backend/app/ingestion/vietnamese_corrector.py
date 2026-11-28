"""Deterministic Vietnamese OCR correction inspired by VietNamOCR's ProtonX layer.

This is NOT the ProtonX model (licensed v1.4-NC). It is a small, auditable
dictionary pass for recurring OCR damage in this corpus. Numbers are never
rewritten, and legal phrases listed in PROTECTED_PHRASES are left untouched.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

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

_DICTIONARY = Path(__file__).with_name("correction_dictionary.json")
if _DICTIONARY.exists():
    curated = json.loads(_DICTIONARY.read_text(encoding="utf-8")).get("pairs", {})
    TYPO_MAP.update({str(key): str(value) for key, value in curated.items()})

PROTECTED_PHRASES = (
    "không gọi nhập ngũ",
    "viễn thị các mức độ",
    "không cho điểm để phân loại sức khỏe",
)

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")

# Apply the whole dictionary before numbers are masked; digit-bearing phrase
# keys and short domain fragments both need the unmasked text.
_PHRASE_KEYS = list(TYPO_MAP.keys())
_PHRASE_PATTERN = (
    re.compile(
        "|".join(re.escape(key) for key in sorted(_PHRASE_KEYS, key=len, reverse=True)),
        re.IGNORECASE,
    )
    if _PHRASE_KEYS else None
)
_PATTERN = re.compile(
    "|".join(re.escape(key) for key in sorted(TYPO_MAP, key=len, reverse=True)),
    re.IGNORECASE,
)
_LOOKUP = {key.lower(): value for key, value in TYPO_MAP.items()}


def correct(text: str) -> str:
    """Correct known OCR damage without touching numbers or protected phrases."""
    if not text:
        return text

    if _PHRASE_PATTERN:
        for _ in range(3):
            updated = _PHRASE_PATTERN.sub(
                lambda match: _LOOKUP.get(match.group(0).lower(), match.group(0)), text
            )
            if updated == text:
                break
            text = updated

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

    # Multiple passes let phrase-level fixes chain after word-level ones.
    for _ in range(3):
        updated = _PATTERN.sub(
            lambda match: _LOOKUP.get(match.group(0).lower(), match.group(0)), text
        )
        if updated == text:
            break
        text = updated
    for index, original in enumerate(preserved):
        text = text.replace(f"__PROTECTED{index}__", original)

    for token, number in reversed(placeholders):
        text = text.replace(token, number)
    return text
