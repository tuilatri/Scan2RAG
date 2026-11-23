---
name: rag-advanced
description: Best practices for Dense + BM25 Hybrid Search, Reciprocal Rank Fusion (RRF), Cross-Encoder Reranking, Local-Cloud Routing (LM Studio, Groq, OpenRouter), LangGraph Agentic Workflows, and RAGAS evaluation.
---

# Advanced RAG & Agentic Document AI

Use this skill when implementing retrieval pipelines, query routing, LangGraph state graphs, citation grounding, and RAG evaluation.

## 1. Hybrid Search & Fusion
- **Dense Vector Search**: Qdrant collection with `multilingual-e5-small` (dimension 384) or `BGE-M3` (dimension 1024).
- **Sparse Keyword Search**: BM25 with Vietnamese word segmentation (e.g. `pyvi` or standard whitespace + n-grams) for exact article numbers, circular codes, or numeric ranges.
- **Reciprocal Rank Fusion (RRF)**:
  $$RRF\_Score(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$ (typically $k = 60$).

## 2. Cross-Encoder Reranking
- Rerank Top-20 retrieved candidates down to Top-5 using a lightweight cross-encoder (e.g. `bge-reranker-base` or multilingual mini reranker) to optimize precision before passing to LLM context window.

## 3. Hybrid Local/Cloud Routing Architecture
- **Hardware Profile**: Laptop RTX 3050 Ti (4GB VRAM).
- **Local Route (LM Studio)**:
  - Local endpoint: `http://localhost:1234/v1` (OpenAI format).
  - Models: Quantized `Qwen2.5-1.5B-Instruct` or `Qwen2.5-3B-Instruct` (Q4_K_M).
  - Use case: Simple queries, metadata lookup, single-clause extraction.
- **Cloud Route (Free Tier: Groq / OpenRouter)**:
  - **Groq API**: `llama-3.3-70b-versatile`, `qwen-2.5-32b`.
  - **OpenRouter**: `:free` tier models.
  - Use case: Complex reasoning, cross-document comparison, synthesizing answers across multiple annexes.

## 4. Grounded Citation Enforcement
Every synthesized response must enforce:
- Exact document code (e.g. `Thông tư 105/2023/TT-BQP`).
- Article and clause number (e.g. `Điều 4, Khoản 2, Điểm a`).
- Source PDF page number.
- Strict refusal when retrieval evidence is insufficient.

## 5. Quantitative Evaluation
- Run evaluation on 50-100 ground truth Q&A samples using **RAGAS**:
  - `Faithfulness`
  - `Answer Relevance`
  - `Context Recall` & `Context Precision`
