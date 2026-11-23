---
name: document-intelligence
description: Domain knowledge for hierarchical Vietnamese legal document parsing, structure-aware chunking (Chapter, Article, Clause, Point), parent-child linking, and temporal consistency.
---

# Vietnamese Document Intelligence & Legal Structure Parsing

Use this skill when designing document schemas, building regex/layout parsers, extracting metadata, or managing document versioning.

## 1. Statutory Structure Hierarchy in Vietnam
Vietnamese legislative documents (Thông tư, Nghị định, Luật) follow a strict hierarchical structure:
- **Chương (Chapter)**: `^Chương\s+([IVXLCDM]+|[0-9]+)\.?\s*(.*)$`
- **Mục (Section)** (if any): `^Mục\s+([0-9]+)\.?\s*(.*)$`
- **Điều (Article)**: `^Điều\s+([0-9]+)\.\s*(.*)$`
- **Khoản (Clause)**: `^([0-9]+)\.\s*(.*)$`
- **Điểm (Point)**: `^([a-zđ])\)\s*(.*)$`

## 2. Structure-Aware & Parent-Child Chunking
1. **Never split mid-clause or mid-point naively** by token length.
2. Form child chunks at the Clause or Point level:
   - Include hierarchical metadata: `document_name`, `chapter`, `article`, `clause`, `point`, `page_number`.
   - Include `parent_id` linking back to the Article text so LLM has the broader context during retrieval.

## 3. Temporal Consistency & Supersession
- Legal relationships:
  - Original: *Thông tư 105/2023/TT-BQP*
  - Amendment: *Thông tư 106/2025/TT-BQP*
  - Consolidation: *Văn bản hợp nhất 88/VBHN-BQP*
- Chunks must store `status` (`active`, `superseded`) and `effective_date`.
- Default search priority: Consolidated Document for current valid rules; cross-reference amendment history only when explicitly asked.
