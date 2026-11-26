"""Numeric grounding helpers for the compare workflow.

Mirrors scripts/audit_processed_data.py::extract_numbers but stays in app/ so
runtime code does not import audit scripts (which pull in pymupdf/sys.path).
"""

import re

NUMBER_PATTERN = re.compile(r"\b\d+(?:\.\d+)?(?:[Tt]|%)?")


def extract_numbers(text: str) -> list[str]:
    return [number.upper() for number in NUMBER_PATTERN.findall(text or "") if number.strip()]


def unsupported_numbers(answer: str, evidence_text: str) -> dict[str, int]:
    """Numbers present in the answer but absent from the cited evidence."""
    added = set(extract_numbers(answer)) - set(extract_numbers(evidence_text))
    return {number: 1 for number in sorted(added)}
