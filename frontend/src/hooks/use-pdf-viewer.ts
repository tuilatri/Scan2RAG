import { useState, useCallback } from 'react';
import { Citation } from '@/types/chat';

interface UsePdfViewerProps {
  initialDocId?: string;
  initialPage?: number;
}

export function usePdfViewer({
  initialDocId = 'thông_tư_88',
  initialPage = 1,
}: UsePdfViewerProps = {}) {
  const [activeDocId, setActiveDocId] = useState<string>(initialDocId);
  const [activePage, setActivePage] = useState<number>(initialPage);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(100); // 100%
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);

  const jumpToCitation = useCallback((citation: Citation) => {
    setActiveCitation(citation);
    if (citation.document_id) {
      setActiveDocId(citation.document_id);
    }
    if (citation.page_number && citation.page_number > 0) {
      setActivePage(citation.page_number);
    }
  }, []);

  const jumpToPage = useCallback((pageNum: number) => {
    if (pageNum >= 1) {
      setActivePage(pageNum);
    }
  }, []);

  const zoomIn = useCallback(() => {
    setZoomLevel((prev) => Math.min(prev + 20, 200));
  }, []);

  const zoomOut = useCallback(() => {
    setZoomLevel((prev) => Math.max(prev - 20, 60));
  }, []);

  const resetZoom = useCallback(() => {
    setZoomLevel(100);
  }, []);

  const toggleSidebar = useCallback(() => {
    setIsSidebarOpen((prev) => !prev);
  }, []);

  return {
    activeDocId,
    activePage,
    activeCitation,
    zoomLevel,
    isSidebarOpen,
    setActiveDocId,
    setActivePage,
    jumpToCitation,
    jumpToPage,
    zoomIn,
    zoomOut,
    resetZoom,
    toggleSidebar,
  };
}
