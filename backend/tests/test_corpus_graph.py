from types import SimpleNamespace

from app.graph.corpus_graph import CorpusGraph


class FakeClient:
    def __init__(self):
        self.call_count = 0

    def scroll(self, collection_name, scroll_filter=None, limit=20, with_payload=True, offset=None):
        self.call_count += 1
        if scroll_filter and scroll_filter.must:
            value = scroll_filter.must[0].match.value
            return ([SimpleNamespace(payload={"chunk_id": value, "content": value})], None)
        return ([], None)


class FakeStore:
    def __init__(self):
        self.client = FakeClient()
        self.collection_name = "vietnamese_legal_docs"


def test_chains_for_condition_keywords():
    graph = CorpusGraph.build()
    assert [chain["id"] for chain in graph.chains_for("viễn thị có phải đi không")] == [
        "VIEN_THI_ELIGIBILITY"
    ]
    assert [chain["id"] for chain in graph.chains_for("loạn thị có phải đi không")] == [
        "LOAN_THI_ELIGIBILITY"
    ]
    assert graph.chains_for("thời tiết hôm nay") == []


def test_supporting_chunks_are_deduplicated(monkeypatch):
    graph = CorpusGraph.build()
    monkeypatch.setattr(
        CorpusGraph,
        "_resolve_anchor",
        staticmethod(lambda store, anchor: [{"chunk_id": "shared", "content": "x"}]),
    )
    chunks = graph.supporting_chunks(FakeStore(), "viễn thị có phải đi không")
    assert len(chunks) == 1
    assert chunks[0]["chunk_id"] == "shared"


def test_rule_anchor_resolves_from_qdrant_filter():
    graph = CorpusGraph.build()
    store = FakeStore()
    payloads = CorpusGraph._resolve_anchor(
        store, {"type": "rule_anchor", "value": "ELIGIBILITY_LOAI_1_2_3"}
    )
    assert payloads[0]["chunk_id"] == "ELIGIBILITY_LOAI_1_2_3"
    assert store.client.call_count == 1
