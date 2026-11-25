import React from 'react';
import { Citation } from '@/types/chat';
import { PdfToolbar } from './pdf-toolbar';
import { PdfCanvas } from './pdf-canvas';
import { DocumentMetaCard } from './document-meta-card';
import { API_BASE_URL, withApiKey } from '@/lib/api-config';

interface PdfViewerPanelProps {
  activeDocId: string;
  activePage: number;
  activeCitation?: Citation | null;
  zoomLevel: number;
  apiBaseUrl?: string;
  onPageChange: (page: number) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetZoom: () => void;
}

export const PdfViewerPanel: React.FC<PdfViewerPanelProps> = ({
  activeDocId,
  activePage,
  activeCitation,
  zoomLevel,
  apiBaseUrl = API_BASE_URL,
  onPageChange,
  onZoomIn,
  onZoomOut,
  onResetZoom,
}) => {
  const pdfUrl = withApiKey(`${apiBaseUrl}/api/v1/documents/${activeDocId}/pdf`);

  return (
    <div className="flex h-full flex-col bg-background border-l">
      {/* Document Legal Metadata Banner */}
      <DocumentMetaCard docId={activeDocId} />

      {/* Interactive Controls Toolbar */}
      <PdfToolbar
        currentPage={activePage}
        zoomLevel={zoomLevel}
        pdfUrl={pdfUrl}
        onPageChange={onPageChange}
        onZoomIn={onZoomIn}
        onZoomOut={onZoomOut}
        onResetZoom={onResetZoom}
      />

      {/* Main PDF Canvas */}
      <PdfCanvas
        docId={activeDocId}
        page={activePage}
        pdfUrl={pdfUrl}
        zoomLevel={zoomLevel}
        activeCitation={activeCitation}
      />
    </div>
  );
};
