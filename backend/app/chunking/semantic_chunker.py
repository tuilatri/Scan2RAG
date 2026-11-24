"""Semantic Legal Chunker for Scan2RAG (Milestone 2).

Transforms hierarchical ParsedDocument JSON nodes into semantic chunks
preserving Chapter -> Article -> Clause -> Point hierarchy and atomic tables.
"""

from typing import Any

from app.models.chunk_schema import LegalChunk


class SemanticLegalChunker:
    """Structure-aware chunker designed for Vietnamese legal and military documents."""

    # Provisions in TT105 explicitly amended or superseded by TT106/2024/TT-BQP or VBHN 88
    TT105_SUPERSEDED_NODE_IDS = {
        "thông_tư_105_clause_61",   # Khoản 3 Điều 3 (được sửa đổi bởi Khoản 1 Điều 1 TT 106)
        "thông_tư_105_clause_166",  # Khoản 1 Điều 7 (được sửa đổi bởi Khoản 2 Điều 1 TT 106)
        "thông_tư_105_clause_175",  # Khoản 3 Điều 7 (được sửa đổi bởi Khoản 2 Điều 1 TT 106)
        "thông_tư_105_clause_446",  # Khoản 4 Điều 13 (được sửa đổi bởi Khoản 4 Điều 1 TT 106)
        "thông_tư_105_clause_467",  # Khoản 2 Điều 14 (được sửa đổi bởi Khoản 5 Điều 1 TT 106)
        "thông_tư_105_clause_482",  # Khoản 1 Điều 15 (được sửa đổi bởi Khoản 6 Điều 1 TT 106)
        "thông_tư_105_clause_724",  # Khoản 2 Điều 26 (được sửa đổi bởi Khoản 7 Điều 1 TT 106)
    }

    def __init__(self, max_tokens: int = 240, overlap_tokens: int = 40):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def _approx_token_count(self, text: str) -> int:
        """Rough estimation: 1 word ~ 1.8 tokens for multilingual-e5 on Vietnamese table text."""
        return max(1, int(len(text.split()) * 1.85))

    def _split_table_into_windows(
        self,
        breadcrumb: str,
        table_markdown: str,
        max_tokens: int = 400
    ) -> list[str]:
        """Split a large markdown table into multiple windowed sub-tables.

        Preserves header rows (rows 0 and 1) at the top of every sub-table
        so downstream embedding models and LLM never lose column headers.
        """
        lines = [line for line in table_markdown.splitlines() if line.strip().startswith("|")]
        if len(lines) <= 3:
            return [f"**Bảng tra cứu:** {breadcrumb}\n\n{table_markdown}"]

        header_prefix = f"**Bảng tra cứu:** {breadcrumb}\n\n"
        header_rows = lines[:2]  # Header and separator (| ... | and | --- |)
        data_rows = lines[2:]

        header_text = header_prefix + "\n".join(header_rows) + "\n"
        base_tokens = self._approx_token_count(header_text)

        windows = []
        current_rows = []
        current_tokens = base_tokens

        for row in data_rows:
            row_tokens = self._approx_token_count(row)
            if current_tokens + row_tokens > max_tokens and current_rows:
                # Flush current window
                window_content = header_text + "\n".join(current_rows)
                windows.append(window_content)
                current_rows = [row]
                current_tokens = base_tokens + row_tokens
            else:
                current_rows.append(row)
                current_tokens += row_tokens

        if current_rows:
            window_content = header_text + "\n".join(current_rows)
            windows.append(window_content)

        return windows if windows else [header_prefix + table_markdown]

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

            node_id = str(node.get("id", ""))
            is_superseded = (
                node.get("metadata", {}).get("is_superseded", False)
                or node_id in self.TT105_SUPERSEDED_NODE_IDS
                or str(node.get("parent_id", "")) in self.TT105_SUPERSEDED_NODE_IDS
            )
            superseded_by = "thông_tư_106" if is_superseded else None
            effective_date = "2024-01-01" if doc_id == "thông_tư_105" else ("2025-01-01" if doc_id == "thông_tư_106" else None)

            # Case 1: Table Node -> Preserved with Table Windowing to strictly fit embedding limits (<512 tokens)
            if is_table:
                table_windows = self._split_table_into_windows(
                    breadcrumb=breadcrumb,
                    table_markdown=content,
                    max_tokens=self.max_tokens
                )

                for w_idx, window_text in enumerate(table_windows):
                    sub_suffix = f"_w{w_idx+1}" if len(table_windows) > 1 else ""
                    chunk = LegalChunk(
                        id=f"{doc_id}_chunk_{chunk_idx:04d}{sub_suffix}",
                        document_id=doc_id,
                        document_name=doc_name,
                        breadcrumb=breadcrumb,
                        hierarchy_path=breadcrumb_parts,
                        content=window_text,
                        char_count=len(window_text),
                        token_count=self._approx_token_count(window_text),
                        is_table=True,
                        page_numbers=[page_num],
                        article_id=node.get("parent_id") if "article" in str(node.get("parent_id", "")).lower() else None,
                        is_superseded=is_superseded,
                        superseded_by=superseded_by,
                        effective_date=effective_date,
                        metadata={**node.get("metadata", {}), "window_index": w_idx, "total_windows": len(table_windows)}
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
                is_superseded=is_superseded,
                superseded_by=superseded_by,
                effective_date=effective_date,
                metadata=node.get("metadata", {})
            )
            chunks.append(chunk)
            chunk_idx += 1

        return chunks
