import React from 'react';
import { ExternalLink, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
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
        <a
          href={pdfUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-muted-foreground hover:text-foreground inline-flex items-center"
        >
          <ExternalLink className="h-3 w-3" />
        </a>
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
