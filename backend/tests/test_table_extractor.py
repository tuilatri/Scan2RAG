from app.ingestion.ocr_engine import TextBlock
from app.ingestion.table_extractor import TableExtractor


def test_is_table_page_detection():
    extractor = TableExtractor()

    # Blocks resembling a medical classification page
    blocks = [
        TextBlock(text="TT", confidence=0.98, box=[[10, 10], [30, 10], [30, 20], [10, 20]]),
        TextBlock(text="Bệnh tật", confidence=0.97, box=[[40, 10], [100, 10], [100, 20], [40, 20]]),
        TextBlock(text="Điểm", confidence=0.99, box=[[110, 10], [140, 10], [140, 20], [110, 20]]),
        TextBlock(text="Cận thị", confidence=0.95, box=[[40, 30], [90, 30], [90, 40], [40, 40]]),
        TextBlock(text="2", confidence=0.99, box=[[110, 30], [120, 30], [120, 40], [110, 40]]),
        TextBlock(text="3", confidence=0.99, box=[[130, 30], [140, 30], [140, 40], [130, 40]]),
        TextBlock(text="4", confidence=0.99, box=[[150, 30], [160, 30], [160, 40], [150, 40]]),
        TextBlock(text="6", confidence=0.99, box=[[170, 30], [180, 30], [180, 40], [170, 40]]),
    ]
    assert extractor.is_table_page(blocks) is True

    # Standard narrative text blocks
    text_blocks = [
        TextBlock(
            text="Cộng hòa Xã hội Chủ nghĩa Việt Nam",
            confidence=0.99,
            box=[[10, 10], [200, 10], [200, 20], [10, 20]],
        ),
        TextBlock(
            text="Độc lập - Tự do - Hạnh phúc",
            confidence=0.98,
            box=[[10, 30], [150, 30], [150, 40], [10, 40]],
        ),
        TextBlock(
            text="Điều 1. Phạm vi áp dụng",
            confidence=0.97,
            box=[[10, 60], [180, 60], [180, 70], [10, 70]],
        ),
    ]
    assert extractor.is_table_page(text_blocks) is False


def test_format_as_markdown():
    extractor = TableExtractor()
    rows = [
        ["STT", "Bệnh tật", "Điểm 1", "Điểm 2"],
        ["1", "Cận thị dưới 1.5D", "2", "3"],
    ]
    md = extractor.format_as_markdown(rows)
    assert "| STT | Bệnh tật | Điểm 1 | Điểm 2 |" in md
    assert "| --- | --- | --- | --- |" in md
    assert "| 1 | Cận thị dưới 1.5D | 2 | 3 |" in md


def test_group_blocks_into_rows_by_y_coordinate():
    extractor = TableExtractor(y_threshold=15.0)

    # 4 blocks forming 2 rows
    b1 = TextBlock(text="STT", confidence=0.98, box=[[10, 95], [50, 95], [50, 110], [10, 110]])
    b2 = TextBlock(
        text="Chỉ tiêu", confidence=0.97, box=[[60, 98], [150, 98], [150, 112], [60, 112]]
    )

    b3 = TextBlock(text="1", confidence=0.99, box=[[10, 148], [50, 148], [50, 160], [10, 160]])
    b4 = TextBlock(
        text="Thị lực", confidence=0.95, box=[[60, 152], [150, 152], [150, 165], [60, 165]]
    )

    rows = extractor.group_blocks_into_rows([b4, b1, b3, b2])
    assert len(rows) == 2
    assert [b.text for b in rows[0]] == ["STT", "Chỉ tiêu"]
    assert [b.text for b in rows[1]] == ["1", "Thị lực"]


def test_context_header_inheritance_for_multi_page_tables():
    extractor = TableExtractor()

    b1 = TextBlock(text="2", confidence=0.99, box=[[10, 50], [30, 50], [30, 65], [10, 65]])
    b2 = TextBlock(text="Viễn thị", confidence=0.95, box=[[40, 52], [120, 52], [120, 68], [40, 68]])

    inherited_header = ["STT", "Chỉ tiêu / Bệnh tật", "Điểm 1", "Điểm 2"]
    table = extractor.extract_table([b1, b2], page_number=2, context_header=inherited_header)

    assert table.header == inherited_header
    assert "| STT | Chỉ tiêu / Bệnh tật | Điểm 1 | Điểm 2 |" in table.markdown_table
    assert "| 2 | Viễn thị |" in table.markdown_table
