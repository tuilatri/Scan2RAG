import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { parseMarkdownTable, matrixToMarkdown } from '@/lib/markdown-table-parser';
import { useOcrAudit } from '@/hooks/use-ocr-audit';

describe('Markdown Table Bi-directional Parser', () => {
  const sampleMarkdown = `| TT | Bệnh tật | Điểm |
| --- | --- | --- |
| 1 | Cận thị dưới -3D | Cho điểm theo mục 1.2 |
| 2 | Cận thị từ -3D đến dưới -4D | 4 |
| 3 | Cận thị từ -4D đến dưới -5D | 5 |`;

  it('parses markdown table into headers and rows matrix', () => {
    const { headers, rows } = parseMarkdownTable(sampleMarkdown);
    expect(headers).toEqual(['TT', 'Bệnh tật', 'Điểm']);
    expect(rows).toHaveLength(3);
    expect(rows[0]).toEqual(['1', 'Cận thị dưới -3D', 'Cho điểm theo mục 1.2']);
    expect(rows[1][2]).toBe('4');
  });

  it('converts matrix back to valid markdown table', () => {
    const headers = ['Mã', 'Tên'];
    const rows = [
      ['01', 'Mắt'],
      ['02', 'Tai mũi họng'],
    ];
    const generatedMd = matrixToMarkdown(headers, rows);
    expect(generatedMd).toContain('| Mã | Tên |');
    expect(generatedMd).toContain('| --- | --- |');
    expect(generatedMd).toContain('| 01 | Mắt |');
  });

  it('handles empty input gracefully', () => {
    const { headers, rows } = parseMarkdownTable('');
    expect(headers).toEqual([]);
    expect(rows).toEqual([]);
  });
});

describe('useOcrAudit Undo/Redo & Header Edit', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('supports updateCell, updateHeader, undo, and redo', async () => {
    const mockTables = [{ id: 't1', document_id: 'thông_tư_88', document_name: 'TT88', page_number: 1, title: 'T1', rows_count: 1, cols_count: 2, vlm_rectified: true, hitl_approved: false, hitl_rectified: false }];
    const mockDetail = { id: 't1', document_id: 'thông_tư_88', document_name: 'TT88', page_number: 1, title: 'T1', content: '| H1 | H2 |\n| --- | --- |\n| A | 1 |', headers: ['H1', 'H2'], rows: [['A', '1']] };

    vi.stubGlobal('fetch', vi.fn((url: string) => {
      if (url.endsWith('/tables/t1')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockDetail) });
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockTables) });
    }));

    const { result } = renderHook(() => useOcrAudit());
    await waitFor(() => expect(result.current.tableDetail?.id).toBe('t1'));

    act(() => {
      result.current.updateCell(0, 1, '4');
    });
    expect(result.current.editableRows[0][1]).toBe('4');
    expect(result.current.canUndo).toBe(true);

    act(() => {
      result.current.undo();
    });
    expect(result.current.editableRows[0][1]).toBe('1');
    expect(result.current.canRedo).toBe(true);

    act(() => {
      result.current.redo();
    });
    expect(result.current.editableRows[0][1]).toBe('4');
  });
});
