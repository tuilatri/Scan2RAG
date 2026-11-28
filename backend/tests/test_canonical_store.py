import json

from app.canonical.store import assert_invariants, load
from app.models.canonical_fact import CanonicalFact


def _fact(**overrides):
    base = {
        "id": "TT105_p23_test",
        "document_id": "thông_tư_105",
        "page": 23,
        "condition": "cận thị -3D đến dưới -4D",
        "value": 4,
        "source_kind": "ocr",
        "evidence_image": "test.png",
    }
    base.update(overrides)
    return CanonicalFact.model_validate(base)


def test_load_reads_facts_key(tmp_path):
    path = tmp_path / "facts.json"
    path.write_text(json.dumps({"facts": [_fact().model_dump()]}), encoding="utf-8")
    loaded = load(path)
    assert len(loaded) == 1
    assert loaded[0].id == "TT105_p23_test"


def test_assert_invariants_blocks_fake_authoritative():
    errors = assert_invariants([_fact(authoritative=True)])
    assert any("authoritative without human review" in e for e in errors)


def test_assert_invariants_rejects_duplicate_and_bad_score():
    errors = assert_invariants([
        _fact(),
        _fact(value=9),
        _fact(),
    ])
    assert any("duplicate" in e for e in errors)
    assert any("score outside" in e for e in errors)
