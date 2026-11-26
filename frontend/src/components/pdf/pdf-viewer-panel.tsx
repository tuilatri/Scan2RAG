import React from 'react';
import { Citation } from '@/types/chat';
import { PdfCanvas } from './pdf-canvas';
import { DocumentMetaCard } from './document-meta-card';
import { API_BASE_URL, withApiKey } from '@/lib/api-config';

interface PdfViewerPanelProps {
  activeDocId: string;
  activePage: number;
  activeCitation?: Citation | null;
  apiBaseUrl?: string;
}

export const PdfViewerPanel: React.FC<PdfViewerPanelProps> = ({
  activeDocId,
  activePage,
  activeCitation,
  apiBaseUrl = API_BASE_URL,
}) => {
  const pdfUrl = withApiKey(`${apiBaseUrl}/api/v1/documents/${activeDocId}/pdf`);

  return (
    <div className="flex h-full flex-col bg-background border-l">
      {/* Document Legal Metadata Banner */}
      <DocumentMetaCard docId={activeDocId} />

      {/* Viewer Chrome natif: zoom, tải về, in sẵn trong iframe */}
      <PdfCanvas
        docId={activeDocId}
        page={activePage}
        pdfUrl={pdfUrl}
        activeCitation={activeCitation}
      />
    </div>
  );
};
