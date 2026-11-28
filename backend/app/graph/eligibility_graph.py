"""Eligibility graph over canonical DOCX facts and the three guidance rules.

This is a deterministic read layer: it maps a condition to its score facts and
to the governing rule, then returns an evidence-backed summary for the prompt.
It never invents a score that is not in the canonical store.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
FACTS = ROOT / "data" / "canonical" / "medical_scores_docx.json"
RULES = ROOT / "data" / "canonical" / "medical_scores.json"

CONDITION_PATTERNS = (
    ("viễn thị", "refraction"),
    ("cận thị", "refraction"),
    ("loạn thị", "astigmatism"),
    ("bmi", "bmi"),
)
DISQUALIFY_HINT = "không gọi nhập ngũ"


class EligibilityGraph:
    def __init__(self, facts: list[dict[str, Any]], rules: list[dict[str, Any]]) -> None:
        self.facts = [f for f in facts if f.get("authoritative")]
        self.rules = rules

    @classmethod
    def build(cls, facts_path: Path = FACTS, rules_path: Path = RULES) -> EligibilityGraph:
        facts = json.loads(facts_path.read_text(encoding="utf-8")).get("facts", [])
        rules = json.loads(rules_path.read_text(encoding="utf-8")).get("rules", [])
        return cls(facts=facts, rules=rules)

    @staticmethod
    def condition_kind(query: str) -> str | None:
        lowered = query.lower()
        for needle, kind in CONDITION_PATTERNS:
            if needle in lowered:
                return kind
        return None

    def supporting_facts(self, query: str) -> list[dict[str, Any]]:
        kind = self.condition_kind(query)
        if not kind:
            return []
        needle = {
            "refraction": ("thị", "diop", "d"),
            "astigmatism": ("loạn",),
            "bmi": ("bmi",),
        }[kind]
        matched: list[dict[str, Any]] = []
        for fact in self.facts:
            condition = str(fact.get("condition", "")).lower()
            if any(item in condition for item in needle):
                matched.append(fact)
        return matched[:12]

    def summary(self, query: str) -> str:
        """Return a short rule chain suitable for appending to a grounded prompt."""
        kind = self.condition_kind(query)
        if not kind:
            return ""
        facts = self.supporting_facts(query)
        rule_texts = [
            f"{rule['condition']} [trang {rule['page']}]"
            for rule in self.rules
            if DISQUALIFY_HINT in str(rule.get("raw_text", "")).lower()
            or "loại 1" in str(rule.get("raw_text", "")).lower()
            or "không cho điểm" in str(rule.get("raw_text", "")).lower()
        ]
        fact_texts = [
            f"{fact['condition']} = {int(float(fact['value']))} điểm "
            f"[{fact['document_id']} trang {fact['page']}]"
            for fact in facts
        ]
        parts = ["CANONICAL RULE CHAIN (DOCX source):"]
        parts.extend(f"- {text}" for text in rule_texts)
        parts.extend(f"- {text}" for text in fact_texts)
        return "\n".join(parts)
