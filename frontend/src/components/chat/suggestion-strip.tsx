import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ScrollControls } from '@/components/ui/scroll-controls';

interface SuggestionStripProps {
  queries: string[];
  onPick: (query: string) => void;
}

const STEP = 240;

export const SuggestionStrip: React.FC<SuggestionStripProps> = ({ queries, onPick }) => {
  const trackRef = useRef<HTMLDivElement>(null);
  const [canPrev, setCanPrev] = useState(false);
  const [canNext, setCanNext] = useState(true);

  const sync = useCallback(() => {
    const node = trackRef.current;
    if (!node) return;
    setCanPrev(node.scrollLeft > 4);
    setCanNext(node.scrollLeft + node.clientWidth < node.scrollWidth - 4);
  }, []);

  useEffect(() => {
    sync();
  }, [queries, sync]);

  const scroll = (direction: 1 | -1) => {
    trackRef.current?.scrollBy({ left: direction * STEP, behavior: 'smooth' });
  };

  if (queries.length === 0) return null;

  return (
    <div className="flex items-center gap-2">
      <span className="shrink-0 text-xs text-muted-foreground">Gợi ý câu hỏi</span>
      <ScrollControls
        label="Gợi ý"
        onPrev={() => scroll(-1)}
        onNext={() => scroll(1)}
        prevDisabled={!canPrev}
        nextDisabled={!canNext}
      />
      <div
        ref={trackRef}
        onScroll={sync}
        className="no-scrollbar flex min-w-0 flex-1 items-center gap-2 overflow-x-auto"
      >
        {queries.map((sample) => (
          <button
            key={sample}
            type="button"
            onClick={() => onPick(sample)}
            className="shrink-0 rounded-lg border border-border/60 bg-muted/40 px-3 py-1.5 text-xs text-foreground transition-colors hover:bg-muted hover:border-primary/40"
          >
            {sample}
          </button>
        ))}
      </div>
    </div>
  );
};
