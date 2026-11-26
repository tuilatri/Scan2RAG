import { render, screen, fireEvent, renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { useChatStream } from '@/hooks/use-chat-stream';
import { ModelBadge } from '@/components/chat/model-badge';
import { StreamIndicator } from '@/components/chat/stream-indicator';
import { CitationCard } from '@/components/chat/citation-card';
import { DocumentMetaCard } from '@/components/pdf/document-meta-card';
import { PdfToolbar } from '@/components/pdf/pdf-toolbar';
import { Citation } from '@/types/chat';

describe('Chat Components Unit Tests', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders ModelBadge with Local Qwen2.5 correctly', () => {
    render(<ModelBadge provider="lm_studio_local" model="qwen2.5-1.5b" />);
    expect(screen.getByText(/Local: qwen2.5-1.5b/i)).toBeInTheDocument();
    expect(screen.getByText('Private')).toBeInTheDocument();
  });

  it('renders ModelBadge with Cloud Groq correctly', () => {
    render(<ModelBadge provider="groq_cloud" model="llama-3.3-70b-versatile" />);
    expect(screen.getByText(/Cloud: llama-3.3-70b-versatile/i)).toBeInTheDocument();
    expect(screen.getByText('Groq')).toBeInTheDocument();
  });

  it('renders StreamIndicator when streaming', () => {
    render(<StreamIndicator isStreaming={true} citationCount={3} />);
    expect(screen.getByText(/Đã tìm thấy 3 căn cứ pháp lý/i)).toBeInTheDocument();
    expect(screen.getByText(/SSE Stream/i)).toBeInTheDocument();
  });

  it('renders CitationCard and fires onSelect callback on click', () => {
    const mockCitation: Citation = {
      id: 'cit_1',
      document_id: 'thông_tư_88',
      document_name: 'Thông tư số 88/VBHN-BQP',
      breadcrumb: 'Thông tư 88 > Phụ lục 1 > Tiêu chuẩn thị lực',
      page_number: 29,
      is_table: true,
      rerank_score: 0.88,
      snippet: 'Thị lực mỗi mắt 10/10.',
    };

    const handleSelect = vi.fn();
    render(
      <CitationCard
        citation={mockCitation}
        index={0}
        isSelected={false}
        onSelect={handleSelect}
      />
    );

    expect(screen.getByText('Thông tư số 88/VBHN-BQP')).toBeInTheDocument();
    expect(screen.getByText('Trang 29')).toBeInTheDocument();
    expect(screen.getByText('Bảng')).toBeInTheDocument();

    const card = screen.getByText('Thông tư số 88/VBHN-BQP').closest('div');
    if (card) {
      fireEvent.click(card);
      expect(handleSelect).toHaveBeenCalledWith(mockCitation);
    }
  });

  it('displays warning badge on CitationCard when backend marks it superseded', () => {
    const supersededCitation: Citation = {
      id: 'cit_old',
      document_id: 'thông_tư_105',
      document_name: 'Thông tư số 105/2023/TT-BQP',
      page_number: 10,
      rerank_score: 0.75,
      is_superseded: true,
    };

    render(
      <CitationCard
        citation={supersededCitation}
        index={1}
        onSelect={() => {}}
      />
    );

    expect(screen.getByText(/Quy định đã được sửa đổi\/thay thế/i)).toBeInTheDocument();
  });

  it('does not warn for TT105 when backend reports is_superseded false', () => {
    const currentCitation: Citation = {
      id: 'cit_current',
      document_id: 'thông_tư_105',
      document_name: 'Thông tư số 105/2023/TT-BQP',
      page_number: 10,
      is_superseded: false,
    };

    render(<CitationCard citation={currentCitation} index={1} onSelect={() => {}} />);

    expect(screen.queryByText(/Quy định đã được sửa đổi\/thay thế/i)).not.toBeInTheDocument();
  });
});

describe('PDF Components Unit Tests', () => {
  it('renders DocumentMetaCard with metadata fetched from the document API', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'thông_tư_88',
            title: 'Thông tư số 88/VBHN-BQP',
            effective_date: '2023-12-31',
            is_superseded: false,
            description: 'Văn bản hợp nhất quy định tiêu chuẩn sức khỏe.',
          }),
      })
    );

    render(<DocumentMetaCard docId="thông_tư_88" />);

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/documents/'),
      expect.anything()
    );
    expect(await screen.findByText('Thông tư số 88/VBHN-BQP')).toBeInTheDocument();
    expect(screen.getByText('Hiệu lực')).toBeInTheDocument();
    expect(screen.getByText(/31\/12\/2023/)).toBeInTheDocument();
  });

  it('shows the superseded note only when the document API says so', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'thông_tư_105',
            title: 'Thông tư số 105/2023/TT-BQP',
            effective_date: '2023-12-06',
            is_superseded: true,
            superseded_by: 'Thông tư 106 & VBHN 88',
            description: 'Quy định đã được sửa đổi.',
          }),
      })
    );

    render(<DocumentMetaCard docId="thông_tư_105" />);

    expect(await screen.findByText('Đã sửa đổi')).toBeInTheDocument();
    expect(screen.getByText(/Thông tư 106 & VBHN 88/)).toBeInTheDocument();
  });

  it('renders PdfToolbar and interacts with page and zoom buttons', () => {
    const handlePageChange = vi.fn();
    const handleZoomIn = vi.fn();
    const handleZoomOut = vi.fn();
    const handleResetZoom = vi.fn();

    render(
      <PdfToolbar
        currentPage={5}
        totalPages={120}
        zoomLevel={100}
        pdfUrl="http://localhost:8000/api/v1/documents/thông_tư_88/pdf"
        onPageChange={handlePageChange}
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onResetZoom={handleResetZoom}
      />
    );

    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('120')).toBeInTheDocument();
    expect(screen.getByText(/100/)).toBeInTheDocument();

    // Test Zoom In
    const zoomInBtn = screen.getByTitle('Phóng to');
    fireEvent.click(zoomInBtn);
    expect(handleZoomIn).toHaveBeenCalledTimes(1);

    // Test Previous Page
    const prevPageBtn = screen.getByTitle('Trang trước');
    fireEvent.click(prevPageBtn);
    expect(handlePageChange).toHaveBeenCalledWith(4);
  });
});

describe('useChatStream Hook Tests', () => {
  it('finalizes assistant message when stopStream is called', async () => {
    const encoder = new TextEncoder();
    const neverEndingStream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"event":"status","status":"retrieving"}\n\n'));
      },
    });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        body: neverEndingStream,
      })
    );

    const { result } = renderHook(() => useChatStream());

    act(() => {
      result.current.sendMessage('Cận thị 3 độ?');
    });

    await act(async () => {
      await new Promise((r) => setTimeout(r, 20));
    });

    act(() => {
      result.current.stopStream();
    });

    expect(result.current.isStreaming).toBe(false);
    const lastMsg = result.current.messages[result.current.messages.length - 1];
    expect(lastMsg.isStreaming).toBe(false);
    vi.unstubAllGlobals();
  });

  it('sets error when stream ends without done event', async () => {
    const encoder = new TextEncoder();
    const incompleteStream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"event":"token","token":"Xin chào"}\n\n'));
        controller.close();
      },
    });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        body: incompleteStream,
      })
    );

    const { result } = renderHook(() => useChatStream());

    await act(async () => {
      await result.current.sendMessage('Test incomplete');
    });

    expect(result.current.error).toContain('ngắt giữa chừng');
    const lastMsg = result.current.messages[result.current.messages.length - 1];
    expect(lastMsg.isStreaming).toBe(false);
    vi.unstubAllGlobals();
  });

  it('flushes a final SSE event and reassembles UTF-8 split across chunks', async () => {
    const encoder = new TextEncoder();
    const payload =
      'data: {"event":"token","token":"Tiêu chuẩn"}\n\n' +
      'data: {"event":"done","provider":"groq_cloud","model":"qwen2.5-1.5b","latency_total_ms":1200}';
    const bytes = encoder.encode(payload);

    // Split inside the two-byte "ê" and again between the two SSE events.
    const utf8Split = bytes.indexOf(encoder.encode('ê')[0]) + 1;
    const doneEventByteOffset = encoder.encode(
      payload.slice(0, payload.indexOf('data: {"event":"done"'))
    ).length;

    const fragmentedStream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(bytes.slice(0, utf8Split));
        controller.enqueue(bytes.slice(utf8Split, doneEventByteOffset));
        controller.enqueue(bytes.slice(doneEventByteOffset));
        controller.close();
      },
    });

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, body: fragmentedStream })
    );

    const { result } = renderHook(() => useChatStream());
    await act(async () => {
      await result.current.sendMessage('Test SSE fragmentation');
    });

    const lastMsg = result.current.messages[result.current.messages.length - 1];
    expect(lastMsg.content).toBe('Tiêu chuẩn');
    expect(lastMsg.provider).toBe('groq_cloud');
    expect(lastMsg.latency_total_ms).toBe(1200);
    expect(lastMsg.isStreaming).toBe(false);
    expect(result.current.streamStatus).toBeNull();
    expect(result.current.error).toBeNull();
    vi.unstubAllGlobals();
  });
});
