import React from 'react';
import { ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface PdfOpenTabButtonProps {
  pdfUrl: string;
  label?: string;
}

export const PdfOpenTabButton: React.FC<PdfOpenTabButtonProps> = ({
  pdfUrl,
  label = 'Mở trong tab',
}) => (
  <a href={pdfUrl} target="_blank" rel="noopener noreferrer" className="shrink-0">
    <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-muted-foreground">
      {label}
      <ExternalLink className="h-4 w-4 ml-1.5" />
    </Button>
  </a>
);
