import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { useBackendHealth } from '@/hooks/use-backend-health';
import { usePdfViewer } from '@/hooks/use-pdf-viewer';

describe('useBackendHealth Hook Tests', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('sets status to connected when /api/v1/health returns ok', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));
    const { result } = renderHook(() => useBackendHealth({ pollIntervalMs: 60000 }));
    await waitFor(() => expect(result.current.status).toBe('connected'));
  });

  it('sets status to offline when fetch fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network down')));
    const { result } = renderHook(() => useBackendHealth({ pollIntervalMs: 60000 }));
    await waitFor(() => expect(result.current.status).toBe('offline'));
  });
});

describe('usePdfViewer Hook Tests', () => {
  it('updates docId and page when jumpToCitation is called', () => {
    const { result } = renderHook(() => usePdfViewer());
    act(() => {
      result.current.jumpToCitation({
        id: 'cit_1',
        document_id: 'thông_tư_106',
        page_number: 12,
      });
    });
    expect(result.current.activeDocId).toBe('thông_tư_106');
    expect(result.current.activePage).toBe(12);
  });

  it('zooms in, zooms out, and resets zoom within bounds', () => {
    const { result } = renderHook(() => usePdfViewer());
    act(() => result.current.zoomIn());
    expect(result.current.zoomLevel).toBe(120);
    act(() => result.current.zoomOut());
    expect(result.current.zoomLevel).toBe(100);
    act(() => result.current.resetZoom());
    expect(result.current.zoomLevel).toBe(100);
  });
});
