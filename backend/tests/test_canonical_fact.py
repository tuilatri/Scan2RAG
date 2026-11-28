from app.models.canonical_fact import CanonicalFact


def _fact(**overrides):
    base = {
        "id": "TT105_p23_test",
        "document_id": "thông_tư_105",
        "page": 23,
        "condition": "cận thị -3D đến dưới -4D",
        "value": 4,
        "source_kind": "ocr",
        "evidence_image": "data/exports/review/canonical/test.png",
    }
    base.update(overrides)
    return CanonicalFact.model_validate(base)


def test_fact_defaults_are_not_authoritative():
    fact = _fact()
    assert fact.needs_human is True
    assert fact.authoritative is False
    assert fact.reviewer == "agent"


def test_human_reviewed_fact_can_be_authoritative():
    fact = _fact(reviewer="human", needs_human=False, authoritative=True)
    assert fact.authoritative is True
