import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Navbar } from '@/components/layout/navbar';
import { TableCellEditor } from '@/components/ocr/table-cell-editor';
import { TableEditorPanel } from '@/components/ocr/table-editor-panel';

describe('Atomic shadcn/ui components', () => {
  it('renders Button correctly with default variant', () => {
    render(<Button>Click me</Button>);
    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('bg-primary');
  });

  it('renders Badge with variants', () => {
    render(<Badge variant="secondary">TT 105/2023</Badge>);
    const badge = screen.getByText('TT 105/2023');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('bg-secondary');
  });

  it('renders Card with header and content', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Legal Intelligence</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Scan2RAG System</p>
        </CardContent>
      </Card>
    );
    expect(screen.getByText('Legal Intelligence')).toBeInTheDocument();
    expect(screen.getByText('Scan2RAG System')).toBeInTheDocument();
  });
});

describe('Layout Components', () => {
  it('renders Navbar with title and view tabs', () => {
    render(
      <Navbar
        activeTab="chat"
        onTabChange={() => {}}
        backendStatus="connected"
      />
    );
    expect(screen.getByText('Scan2RAG')).toBeInTheDocument();
    expect(screen.getByText(/Trợ lý Tra cứu Văn bản Pháp luật/i)).toBeInTheDocument();
    expect(screen.getByText('Trợ lý Tra cứu RAG')).toBeInTheDocument();
    expect(screen.getByText('Đối soát OCR (HITL)')).toBeInTheDocument();
    expect(screen.getByText('Backend & Qdrant Sẵn sàng')).toBeInTheDocument();
  });
});

describe('Accessibility', () => {
  it('marks the active navbar view as the current tab', () => {
    render(<Navbar activeTab="chat" onTabChange={() => {}} backendStatus="connected" />);

    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(3);
    expect(tabs[0]).toHaveAttribute('aria-selected', 'true');
    expect(tabs[0]).toHaveAttribute('aria-current', 'page');
    expect(tabs[1]).toHaveAttribute('aria-selected', 'false');
  });

  it('lets keyboard users edit a table cell with Enter', () => {
    const onUpdate = vi.fn();
    render(<TableCellEditor value="4" rowIndex={0} colIndex={1} onUpdate={onUpdate} />);

    const cell = screen.getByRole('button', { name: /hàng 1 cột 2/i });
    fireEvent.keyDown(cell, { key: 'Enter' });

    const input = screen.getByRole('textbox', { name: /hàng 1 cột 2/i });
    fireEvent.change(input, { target: { value: '5' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(onUpdate).toHaveBeenCalledWith(0, 1, '5');
  });

  it('lets keyboard users edit a table cell with Space', () => {
    render(<TableCellEditor value="4" rowIndex={1} colIndex={0} onUpdate={() => {}} />);

    const cell = screen.getByRole('button', { name: /hàng 2 cột 1/i });
    fireEvent.keyDown(cell, { key: ' ' });

    expect(screen.getByRole('textbox', { name: /hàng 2 cột 1/i })).toBeInTheDocument();
  });

  it('exposes a table caption and column/row scopes', () => {
    render(
      <TableEditorPanel
        tableDetail={{
          id: 't1',
          document_id: 'thông_tư_88',
          document_name: 'TT88',
          page_number: 1,
          title: 'Bảng mắt',
          content: '| H1 | H2 |\n| --- | --- |\n| A | 1 |',
          headers: ['H1', 'H2'],
          rows: [['A', '1']],
        }}
        editableHeaders={['H1', 'H2']}
        editableRows={[['A', '1']]}
        onUpdateCell={() => {}}
      />
    );

    expect(screen.getByText(/Bảng dữ liệu có thể chỉnh sửa: Bảng mắt/)).toBeInTheDocument();
    expect(screen.getAllByRole('columnheader').length).toBe(3);
    expect(screen.getByRole('rowheader')).toHaveTextContent('1');
  });
});
