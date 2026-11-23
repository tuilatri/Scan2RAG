"""Legal Structure Parser module for extracting hierarchical Vietnamese statutory units.

Parses text into Chapter (Chương), Section (Mục/Phần), Article (Điều), Clause (Khoản), and Point (Điểm).
Maintains cross-page parent-child hierarchy to avoid orphaned nodes.
"""

import re

from app.models.document_schema import DocumentNode, HierarchyLevel


class LegalStructureParser:
    """Regex-based parser for Vietnamese legal statutes (Chương, Mục, Điều, Khoản, Điểm)."""

    CHAPTER_PATTERN = re.compile(
        r"^(?:Chương|Chuong|CHƯƠNG|CHUONG)\s+([IVXLCDM0-9]+)\.?\s*(.*)$",
        re.IGNORECASE,
    )
    SECTION_PATTERN = re.compile(
        r"^(Mục|Muc|MỤC|MUC|[IVXLCDM]+|[1-9])\.\s+([A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ\s]{4,})$"
    )
    ARTICLE_PATTERN = re.compile(r"^(?:Điều|Điu|ĐIỀU|ĐIU)\s+([0-9]+)\.\s*(.*)$", re.IGNORECASE)
    CLAUSE_PATTERN = re.compile(r"^([0-9]+)\.\s*(.*)$")
    POINT_PATTERN = re.compile(r"^([a-zđ])\)\s*(.*)$", re.IGNORECASE)

    def __init__(self, document_id: str, document_name: str):
        self.document_id = document_id
        self.document_name = document_name
        # Keep track of active statutory context across pages
        self.current_chapter: DocumentNode | None = None
        self.current_section: DocumentNode | None = None
        self.current_article: DocumentNode | None = None
        self.current_clause: DocumentNode | None = None
        self.node_counter = 0

    def parse_lines(self, lines: list[str], page_number: int = 1) -> list[DocumentNode]:
        """Parses a sequence of text lines into hierarchical DocumentNode structures."""
        nodes: list[DocumentNode] = []

        for line in lines:
            line_str = line.strip()
            # Filter noise: discard single garbage symbols or short scanner marks unless it's a clause/point prefix
            if len(line_str) < 5 and not self.POINT_PATTERN.match(line_str) and not re.match(r"^\d+\.$", line_str):
                continue

            # Check Chapter (supports scan variant Chuong / Chương)
            chap_match = self.CHAPTER_PATTERN.match(line_str)
            if chap_match:
                self.node_counter += 1
                self.current_chapter = DocumentNode(
                    id=f"{self.document_id}_chap_{self.node_counter}",
                    document_id=self.document_id,
                    document_name=self.document_name,
                    level=HierarchyLevel.CHAPTER,
                    title=f"Chương {chap_match.group(1)}",
                    content=chap_match.group(2).strip(),
                    page_number=page_number,
                    parent_id=None,
                    order=self.node_counter,
                )
                nodes.append(self.current_chapter)
                self.current_section = None
                self.current_article = None
                self.current_clause = None
                continue

            # Check Section (Mục I, II... in administrative guidelines)
            sec_match = self.SECTION_PATTERN.match(line_str)
            if sec_match and not self.ARTICLE_PATTERN.match(line_str):
                self.node_counter += 1
                parent = self.current_chapter.id if self.current_chapter else None
                self.current_section = DocumentNode(
                    id=f"{self.document_id}_sec_{self.node_counter}",
                    document_id=self.document_id,
                    document_name=self.document_name,
                    level=HierarchyLevel.SECTION,
                    title=f"Mục {sec_match.group(1)}",
                    content=sec_match.group(2).strip(),
                    page_number=page_number,
                    parent_id=parent,
                    order=self.node_counter,
                )
                nodes.append(self.current_section)
                self.current_article = None
                self.current_clause = None
                continue

            # Check Article
            art_match = self.ARTICLE_PATTERN.match(line_str)
            if art_match:
                self.node_counter += 1
                parent = (
                    self.current_section.id
                    if self.current_section
                    else (self.current_chapter.id if self.current_chapter else None)
                )
                self.current_article = DocumentNode(
                    id=f"{self.document_id}_art_{self.node_counter}",
                    document_id=self.document_id,
                    document_name=self.document_name,
                    level=HierarchyLevel.ARTICLE,
                    title=f"Điều {art_match.group(1)}",
                    content=art_match.group(2).strip(),
                    page_number=page_number,
                    parent_id=parent,
                    order=self.node_counter,
                )
                nodes.append(self.current_article)
                self.current_clause = None
                continue

            # Check Clause (numbered: "1. Content")
            clause_match = self.CLAUSE_PATTERN.match(line_str)
            if clause_match and self.current_article:
                self.node_counter += 1
                self.current_clause = DocumentNode(
                    id=f"{self.document_id}_clause_{self.node_counter}",
                    document_id=self.document_id,
                    document_name=self.document_name,
                    level=HierarchyLevel.CLAUSE,
                    title=f"Khoản {clause_match.group(1)}",
                    content=clause_match.group(2).strip(),
                    page_number=page_number,
                    parent_id=self.current_article.id,
                    order=self.node_counter,
                )
                nodes.append(self.current_clause)
                continue

            # Check Point (lettered: "a) Content")
            point_match = self.POINT_PATTERN.match(line_str)
            if point_match and (self.current_clause or self.current_article):
                self.node_counter += 1
                parent_id = self.current_clause.id if self.current_clause else self.current_article.id
                point_node = DocumentNode(
                    id=f"{self.document_id}_point_{self.node_counter}",
                    document_id=self.document_id,
                    document_name=self.document_name,
                    level=HierarchyLevel.POINT,
                    title=f"Điểm {point_match.group(1)}",
                    content=point_match.group(2).strip(),
                    page_number=page_number,
                    parent_id=parent_id,
                    order=self.node_counter,
                )
                nodes.append(point_node)
                continue

            # Standard narrative text block - Always chain to closest active ancestor
            self.node_counter += 1
            parent_id = None
            if self.current_clause:
                parent_id = self.current_clause.id
            elif self.current_article:
                parent_id = self.current_article.id
            elif self.current_section:
                parent_id = self.current_section.id
            elif self.current_chapter:
                parent_id = self.current_chapter.id

            nodes.append(
                DocumentNode(
                    id=f"{self.document_id}_text_{self.node_counter}",
                    document_id=self.document_id,
                    document_name=self.document_name,
                    level=HierarchyLevel.DOCUMENT,
                    title="",
                    content=line_str,
                    page_number=page_number,
                    parent_id=parent_id,
                    order=self.node_counter,
                )
            )

        return nodes
