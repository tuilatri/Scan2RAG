"""Legal Structure Parser module for extracting hierarchical Vietnamese statutory units.

Parses text into Chapter (Chương), Section (Mục/Phần), Article (Điều), Clause (Khoản), and Point (Điểm).
"""

import re

from app.models.document_schema import DocumentNode, HierarchyLevel


class LegalStructureParser:
    """Regex-based parser for Vietnamese legal statutes (Chương, Mục, Điều, Khoản, Điểm)."""

    CHAPTER_PATTERN = re.compile(r"^(Chương\s+[IVXLCDM0-9]+)\.?\s*(.*)$", re.IGNORECASE)
    SECTION_PATTERN = re.compile(
        r"^([IVXLCDM]+|[1-9])\.\s+([A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ\s]{4,})$"
    )
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
        current_section: DocumentNode | None = None
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
                current_section = None
                current_article = None
                current_clause = None
                continue

            # Check Section (Mục I, II... in administrative guidelines)
            sec_match = self.SECTION_PATTERN.match(line_str)
            if sec_match and not self.ARTICLE_PATTERN.match(line_str):
                node_counter += 1
                parent = current_chapter.id if current_chapter else None
                current_section = DocumentNode(
                    id=f"{self.document_id}_sec_{node_counter}",
                    document_id=self.document_id,
                    document_name=self.document_name,
                    level=HierarchyLevel.SECTION,
                    title=f"Mục {sec_match.group(1)}",
                    content=sec_match.group(2),
                    page_number=page_number,
                    parent_id=parent,
                    order=node_counter,
                )
                nodes.append(current_section)
                current_article = None
                current_clause = None
                continue

            # Check Article
            art_match = self.ARTICLE_PATTERN.match(line_str)
            if art_match:
                node_counter += 1
                parent = (
                    current_section.id
                    if current_section
                    else (current_chapter.id if current_chapter else None)
                )
                current_article = DocumentNode(
                    id=f"{self.document_id}_art_{node_counter}",
                    document_id=self.document_id,
                    document_name=self.document_name,
                    level=HierarchyLevel.ARTICLE,
                    title=art_match.group(1),
                    content=art_match.group(2),
                    page_number=page_number,
                    parent_id=parent,
                    order=node_counter,
                )
                nodes.append(current_article)
                current_clause = None
                continue

            # Check Clause (numbered: "1. Content")
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

            # Check Point (lettered: "a) Content")
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

            # Standard narrative text block
            node_counter += 1
            parent_id = None
            if current_clause:
                parent_id = current_clause.id
            elif current_article:
                parent_id = current_article.id
            elif current_section:
                parent_id = current_section.id
            elif current_chapter:
                parent_id = current_chapter.id

            nodes.append(
                DocumentNode(
                    id=f"{self.document_id}_text_{node_counter}",
                    document_id=self.document_id,
                    document_name=self.document_name,
                    level=HierarchyLevel.DOCUMENT,
                    title="",
                    content=line_str,
                    page_number=page_number,
                    parent_id=parent_id,
                    order=node_counter,
                )
            )

        return nodes
