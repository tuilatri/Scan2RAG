"""Legal Structure Parser module for extracting hierarchical Vietnamese statutory units.

Parses text into Chapter (Chương), Article (Điều), Clause (Khoản), and Point (Điểm).
"""

import re

from app.models.document_schema import DocumentNode, HierarchyLevel


class LegalStructureParser:
    """Regex-based parser for Vietnamese legal statutes (Chương, Điều, Khoản, Điểm)."""

    CHAPTER_PATTERN = re.compile(r"^(Chương\s+[IVXLCDM0-9]+)\.?\s*(.*)$", re.IGNORECASE)
    ARTICLE_PATTERN = re.compile(r"^(Điều\s+[0-9]+)\.\s*(.*)$", re.IGNORECASE)
    CLAUSE_PATTERN = re.compile(r"^([0-9]+)\.\s*(.*)$")
    POINT_PATTERN = re.compile(r"^([a-zđ])\)\s*(.*)$", re.IGNORECASE)

    def __init__(self, document_id: str, document_name: str):
        self.document_id = document_id
        self.document_name = document_name

    def parse_lines(self, lines: list[str], page_number: int = 1) -> list[DocumentNode]:
        """Parses a sequence of text lines into hierarchical DocumentNode structures."""
        nodes: list[DocumentNode] = []
        current_chapter: DocumentNode | None = None
        current_article: DocumentNode | None = None
        current_clause: DocumentNode | None = None

        node_counter = 0

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Check Chapter
            chap_match = self.CHAPTER_PATTERN.match(line_str)
            if chap_match:
                node_counter += 1
                current_chapter = DocumentNode(
                    id=f"{self.document_id}_chap_{node_counter}",
                    document_id=self.document_id,
                    document_name=self.document_name,
                    level=HierarchyLevel.CHAPTER,
                    title=chap_match.group(1),
                    content=chap_match.group(2),
                    page_number=page_number,
                    parent_id=None,
                    order=node_counter,
                )
                nodes.append(current_chapter)
                current_article = None
                current_clause = None
                continue

            # Check Article
            art_match = self.ARTICLE_PATTERN.match(line_str)
            if art_match:
                node_counter += 1
                parent_id = current_chapter.id if current_chapter else None
                current_article = DocumentNode(
                    id=f"{self.document_id}_art_{node_counter}",
                    document_id=self.document_id,
                    document_name=self.document_name,
                    level=HierarchyLevel.ARTICLE,
                    title=art_match.group(1),
                    content=art_match.group(2),
                    page_number=page_number,
                    parent_id=parent_id,
                    order=node_counter,
                )
                nodes.append(current_article)
                current_clause = None
                continue

            # Check Clause
            clause_match = self.CLAUSE_PATTERN.match(line_str)
            if clause_match and current_article:
                node_counter += 1
                current_clause = DocumentNode(
                    id=f"{self.document_id}_clause_{node_counter}",
                    document_id=self.document_id,
                    document_name=self.document_name,
                    level=HierarchyLevel.CLAUSE,
                    title=f"Khoản {clause_match.group(1)}",
                    content=clause_match.group(2),
                    page_number=page_number,
                    parent_id=current_article.id,
                    order=node_counter,
                )
                nodes.append(current_clause)
                continue

            # Check Point
            point_match = self.POINT_PATTERN.match(line_str)
            if point_match and (current_clause or current_article):
                node_counter += 1
                parent_id = current_clause.id if current_clause else current_article.id
                point_node = DocumentNode(
                    id=f"{self.document_id}_point_{node_counter}",
                    document_id=self.document_id,
                    document_name=self.document_name,
                    level=HierarchyLevel.POINT,
                    title=f"Điểm {point_match.group(1)}",
                    content=point_match.group(2),
                    page_number=page_number,
                    parent_id=parent_id,
                    order=node_counter,
                )
                nodes.append(point_node)
                continue

            # General body text - append to current active node
            if current_clause:
                current_clause.content += f" {line_str}"
            elif current_article:
                current_article.content += f" {line_str}"
            elif current_chapter:
                current_chapter.content += f" {line_str}"
            else:
                # Top level document preamble
                node_counter += 1
                preamble_node = DocumentNode(
                    id=f"{self.document_id}_text_{node_counter}",
                    document_id=self.document_id,
                    document_name=self.document_name,
                    level=HierarchyLevel.DOCUMENT,
                    title="",
                    content=line_str,
                    page_number=page_number,
                    parent_id=None,
                    order=node_counter,
                )
                nodes.append(preamble_node)

        return nodes
