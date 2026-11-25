import React from 'react';
import { Citation } from '@/types/chat';
import { CitationCard } from './citation-card';
import { BookOpen } from 'lucide-react';

interface CitationListProps {
  citations: Citation[];
  activeCitationId?: string;
  onCitationSelect: (citation: Citation) => void;
}

export const CitationList: React.FC<CitationListProps> = ({
  citations,
  activeCitationId,
  onCitationSelect,
}) => {
  if (!citations || citations.length === 0) return null;

  return (
    <div className="mt-3 space-y-2 border-t pt-3">
      <div className="flex items-center space-x-1.5 text-xs font-medium text-foreground/90">
        <BookOpen className="h-3.5 w-3.5 text-primary" />
        <span>Căn cứ Pháp lý & Trang Tra cứu ({citations.length}):</span>
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {citations.map((citation, idx) => (
          <CitationCard
            key={citation.id || `cit_${idx}`}
            citation={citation}
            index={idx}
            isSelected={activeCitationId === citation.id}
            onSelect={onCitationSelect}
          />
        ))}
      </div>
    </div>
  );
};
