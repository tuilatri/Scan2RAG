"""Semantic Legal Chunker for Scan2RAG (Milestone 2).

Transforms hierarchical ParsedDocument JSON nodes into semantic chunks
preserving Chapter -> Article -> Clause -> Point hierarchy and atomic tables.
"""

from typing import Any

from app.models.chunk_schema import LegalChunk


class SemanticLegalChunker:
    """Structure-aware chunker designed for Vietnamese legal and military documents."""

    def __init__(self, max_tokens: int = 600, overlap_tokens: int = 50):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def _approx_token_count(self, text: str) -> int:
        """Rough estimation: 1 word ~ 1.3 tokens in Vietnamese."""
        return max(1, int(len(text.split()) * 1.3))

    def chunk_document(self, doc_data: dict[str, Any]) -> list[LegalChunk]:
        """Convert a document's nodes into a sequence of semantic LegalChunks."""
        doc_id = doc_data.get("document_id", "unknown_doc")
        doc_name = doc_data.get("document_name", doc_id.replace("_", " ").title())
        nodes = doc_data.get("nodes", [])

        # Build node index for parent lookup
        node_map = {n["id"]: n for n in nodes}

        chunks: list[LegalChunk] = []
        chunk_idx = 1

        for node in nodes:
            content = (node.get("content") or "").strip()
            title = (node.get("title") or "").strip()
            level = str(node.get("level", "")).upper()
            page_num = node.get("page_number", 1)

            # Skip empty content if title is also empty
            if not content and not title:
                continue

            # Construct breadcrumb by walking up parent_id
            breadcrumb_parts = []
            curr = node
            visited_parents = set()
            while curr:
                c_title = curr.get("title") or curr.get("level") or ""
                if c_title:
                    breadcrumb_parts.append(c_title)
                p_id = curr.get("parent_id")
                if not p_id or p_id in visited_parents:
                    break
                visited_parents.add(p_id)
                curr = node_map.get(p_id)

            breadcrumb_parts.append(doc_name)
            breadcrumb_parts.reverse()
            breadcrumb = " > ".join(breadcrumb_parts)

            is_table = level == "TABLE" or node.get("metadata", {}).get("is_table", False)

            # Case 1: Atomic Table Node -> Preserved entirely as a standalone chunk
            if is_table:
                table_text = content
                header_context = f"**Bảng tra cứu:** {breadcrumb}\n\n"
                full_chunk_text = header_context + table_text

                chunk = LegalChunk(
                    id=f"{doc_id}_chunk_{chunk_idx:04d}",
                    document_id=doc_id,
                    document_name=doc_name,
                    breadcrumb=breadcrumb,
                    hierarchy_path=breadcrumb_parts,
                    content=full_chunk_text,
                    char_count=len(full_chunk_text),
                    token_count=self._approx_token_count(full_chunk_text),
                    is_table=True,
                    page_numbers=[page_num],
                    article_id=node.get("parent_id") if "article" in str(node.get("parent_id", "")).lower() else None,
                    is_superseded=node.get("metadata", {}).get("is_superseded", False),
                    metadata=node.get("metadata", {})
                )
                chunks.append(chunk)
                chunk_idx += 1
                continue

            # Case 2: Standard Structural Node (Chapter, Article, Clause, Point, Document)
            chunk_content = content if content else title
            # Prefix with breadcrumb header for dense retrieval context
            full_chunk_text = f"**Văn bản:** {breadcrumb}\n\n{chunk_content}"

            chunk = LegalChunk(
                id=f"{doc_id}_chunk_{chunk_idx:04d}",
                document_id=doc_id,
                document_name=doc_name,
                breadcrumb=breadcrumb,
                hierarchy_path=breadcrumb_parts,
                content=full_chunk_text,
                char_count=len(full_chunk_text),
                token_count=self._approx_token_count(full_chunk_text),
                is_table=False,
                page_numbers=[page_num],
                article_id=node.get("id") if level == "ARTICLE" else node.get("parent_id"),
                is_superseded=node.get("metadata", {}).get("is_superseded", False),
                metadata=node.get("metadata", {})
            )
            chunks.append(chunk)
            chunk_idx += 1

        return chunks
