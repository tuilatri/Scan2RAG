import React from 'react';
import { FileText } from 'lucide-react';
import { PdfOpenTabButton } from '@/components/pdf/pdf-open-tab-button';
import { API_BASE_URL, withApiKey } from '@/lib/api-config';

interface PagePreviewCardProps {
  documentId: string;
  pageNumber: number;
  apiBaseUrl?: string;
}

export const PagePreviewCard: React.FC<PagePreviewCardProps> = ({
  documentId,
  pageNumber,
  apiBaseUrl = API_BASE_URL,
}) => {
  const pdfUrl = withApiKey(`${apiBaseUrl}/api/v1/documents/${documentId}/pdf#page=${pageNumber}`);

  return (
    <div className="w-96 flex flex-col h-full border-l bg-card/60">
      <div className="border-b px-3 py-2 flex items-center justify-between text-xs bg-muted/30">
        <div className="flex items-center space-x-1.5 font-medium text-foreground">
          <FileText className="h-3.5 w-3.5 text-primary" />
          <span>Trang gốc PDF (Trang {pageNumber})</span>
        </div>
        <PdfOpenTabButton pdfUrl={pdfUrl} label="Tab đầy đủ" />
      </div>
      <div className="flex-1 bg-muted/20 relative">
        <iframe
          key={`${documentId}-${pageNumber}`}
          src={pdfUrl}
          title={`PDF Preview Page ${pageNumber}`}
          className="h-full w-full border-0"
        />
      </div>
    </div>
  );
};
