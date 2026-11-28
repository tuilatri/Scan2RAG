from unittest.mock import Mock

import pytest
from langgraph.checkpoint.memory import MemorySaver
from pydantic import ValidationError

from app.agents.compare_graph import build_compare_graph
from app.api.qa_endpoints import CompareRequest

CHUNK_105 = {
    "id": "c105",
    "document_id": "thông_tư_105",
    "content": "Cận thị 3 điểm",
    "breadcrumb": "TT105",
}
CHUNK_106 = {
    "id": "c106",
    "document_id": "thông_tư_106",
    "content": "Quy định mới",
    "breadcrumb": "TT106",
}
GENERATION = {"content": "Theo TT105: 3 điểm", "provider": "lm_studio_local", "model": "qwen"}
QUERY_1 = "So sánh Thông tư 105 và Thông tư 106"
QUERY_2 = "Còn quy định cận thị thì sao?"


def _graph(checkpointer=None):
    searcher = Mock()
    searcher.search.return_value = []
    searcher.table_chunks_for.return_value = []

    def rerank(query, candidates, top_k):
        return [CHUNK_105] if "105" in query else [CHUNK_106]

    reranker = Mock()
    reranker.rerank.side_effect = rerank
    router = Mock()
    router.generate.return_value = GENERATION
    return build_compare_graph(searcher, reranker, router, checkpointer=checkpointer)


def test_same_thread_keeps_history():
    graph = _graph(MemorySaver())
    config = {"configurable": {"thread_id": "thread-1"}}
    first = graph.invoke({"query": QUERY_1}, config=config)
    second = graph.invoke({"query": QUERY_2}, config=config)
    assert len(first["history"]) == 1
    assert len(second["history"]) == 2
    assert [item["query"] for item in second["history"]] == [QUERY_1, QUERY_2]


def test_different_threads_are_isolated():
    graph = _graph(MemorySaver())
    first = graph.invoke(
        {"query": QUERY_1}, config={"configurable": {"thread_id": "thread-a"}}
    )
    other = graph.invoke(
        {"query": QUERY_1}, config={"configurable": {"thread_id": "thread-b"}}
    )
    assert len(first["history"]) == 1
    assert len(other["history"]) == 1


def test_thread_id_pattern_and_stateless_history():
    with pytest.raises(ValidationError):
        CompareRequest(query=QUERY_1, thread_id="bad id!")
    assert CompareRequest(query=QUERY_1, thread_id="thread_01").thread_id == "thread_01"
    graph = _graph()
    result = graph.invoke({"query": QUERY_1})
    assert len(result["history"]) == 1
