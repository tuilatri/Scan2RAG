import React from 'react';
import { ThinScrollArea } from '@/components/ui/thin-scroll-area';

interface SuggestionStripProps {
  queries: string[];
  onPick: (query: string) => void;
}

export const SuggestionStrip: React.FC<SuggestionStripProps> = ({ queries, onPick }) => {
  if (queries.length === 0) return null;

  return (
    <div className="flex items-center gap-3">
      <span className="shrink-0 text-xs text-muted-foreground">Gợi ý câu hỏi</span>
      <ThinScrollArea orientation="horizontal" className="min-w-0 flex-1">
        <div className="flex w-max items-center gap-2 py-1">
          {queries.map((sample) => (
            <button
              key={sample}
              type="button"
              onClick={() => onPick(sample)}
              className="rounded-lg border border-border/60 bg-muted/40 px-3 py-1.5 text-xs text-foreground transition-colors hover:bg-muted hover:border-primary/40"
            >
              {sample}
            </button>
          ))}
        </div>
      </ThinScrollArea>
    </div>
  );
};
