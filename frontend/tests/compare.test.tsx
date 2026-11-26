import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { CompareContainer } from '@/components/chat/compare-container';
import type { CompareResponseData, Citation } from '@/types/chat';

const citation: Citation = {
  id: 'cit_1',
  document_id: 'thông_tư_105',
  document_name: 'Thông tư 105',
  breadcrumb: 'Thông tư 105 > Chương V',
  page_number: 23,
  snippet: 'Cận thị từ -3D đến dưới -4D: 3 điểm',
};

function fixture(overrides: Partial<CompareResponseData> = {}): CompareResponseData {
  return {
    query: 'So sánh Thông tư 105 và Thông tư 106',
    answer: 'Theo Thông tư 105: 3 điểm',
    citations: [citation],
    evidence: [{ document_id: 'thông_tư_105', chunk_count: 5, citation_ids: ['cit_1'] }],
    verification: { passed: true, unsupported_numbers: {}, checked_numbers: 1 },
    version_notes: [
      {
        document_id: 'thông_tư_105',
        effective_date: '2024-01-01',
        superseded_by: 'thông_tư_106',
        note: 'Đã bị TT106 sửa đổi',
      },
    ],
    plan_source: 'deterministic',
    sub_queries: ['Cận thị TT105?', 'Cận thị TT106?'],
    thread_id: 'demo-thread-1',
    history_len: 2,
    provider: 'lm_studio_local',
    model: 'qwen2.5-1.5b-instruct',
    ...overrides,
  };
}

describe('CompareContainer', () => {
  it('renders answer, evidence and version notes', () => {
    render(
      <CompareContainer
        result={fixture()}
        isLoading={false}
        error={null}
        onSend={vi.fn()}
        onCitationSelect={vi.fn()}
      />
    );
    expect(screen.getByText(/Theo Thông tư 105: 3 điểm/)).toBeInTheDocument();
    expect(screen.getAllByText('thông_tư_105').length).toBeGreaterThan(0);
    expect(screen.getByText('2024-01-01')).toBeInTheDocument();
    expect(screen.getByText(/deterministic · 2 lượt/)).toBeInTheDocument();
  });

  it('shows a warning when verification fails', () => {
    render(
      <CompareContainer
        result={
          fixture({
            verification: { passed: false, unsupported_numbers: { 7: 1 }, checked_numbers: 2 },
          })
        }
        isLoading={false}
        error={null}
        onSend={vi.fn()}
        onCitationSelect={vi.fn()}
      />
    );
    expect(screen.getByRole('alert')).toHaveTextContent('7');
  });

  it('sends the query and fires citation callback', () => {
    const onSend = vi.fn();
    const onCitationSelect = vi.fn();
    render(
      <CompareContainer
        result={fixture()}
        isLoading={false}
        error={null}
        onSend={onSend}
        onCitationSelect={onCitationSelect}
      />
    );
    const textarea = screen.getByPlaceholderText(/So sánh quy định cận thị/);
    fireEvent.change(textarea, { target: { value: 'So sánh TT105 và TT106' } });
    fireEvent.click(screen.getByRole('button', { name: 'So sánh' }));
    expect(onSend).toHaveBeenCalledWith('So sánh TT105 và TT106', undefined);

    const cards = screen.getAllByRole('button');
    fireEvent.click(cards[cards.length - 1]);
    expect(onCitationSelect).toHaveBeenCalled();
  });
});
