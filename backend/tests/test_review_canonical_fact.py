import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.review_canonical_fact import apply_decision, validate_decision


def _payload():
    return {
        "facts": [{
            "id": "TT105_p23_score_009",
            "authoritative": False,
            "needs_human": True,
            "reviewer": "agent",
        }],
        "rules": [],
    }


def test_agent_cannot_approve():
    assert validate_decision("agent", True, True) == "agent reviewer cannot approve a fact"


def test_approve_requires_evidence_checked():
    assert validate_decision("Nguyen A", True, False) == "approved fact must have evidence_checked=true"


def test_human_approval_sets_authoritative():
    payload = _payload()
    assert apply_decision(payload, "TT105_p23_score_009", "Nguyen A", True, True, "checked p23") is True
    fact = payload["facts"][0]
    assert fact["authoritative"] is True
    assert fact["needs_human"] is False
    assert fact["reviewer"] == "Nguyen A"


def test_unknown_fact_is_rejected():
    payload = _payload()
    assert apply_decision(payload, "missing", "Nguyen A", True, True, "") is False
