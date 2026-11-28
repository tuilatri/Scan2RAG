"""Check whether an answer states the claims required by a rule chain."""

from __future__ import annotations


def verify_claims(answer: str, required_claims: list[str]) -> dict[str, object]:
    lowered = answer.lower()
    missing = [claim for claim in required_claims if claim.lower() not in lowered]
    return {
        "passed": not missing,
        "checked": len(required_claims),
        "missing": missing,
    }
