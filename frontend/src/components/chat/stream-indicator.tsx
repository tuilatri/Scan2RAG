import React from 'react';
import { Loader2, Zap } from 'lucide-react';

interface StreamIndicatorProps {
  isStreaming: boolean;
  citationCount: number;
  streamStatus?: string | null;
}

export const StreamIndicator: React.FC<StreamIndicatorProps> = ({
  isStreaming,
  citationCount,
  streamStatus,
}) => {
  if (!isStreaming) return null;

  return (
    <div className="flex items-center space-x-2 text-xs text-muted-foreground py-1 px-3 bg-muted/40 rounded-md border border-border/50">
      <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
      <span>
        {citationCount > 0 || streamStatus === 'generating'
          ? `Đã tìm thấy ${citationCount} căn cứ pháp lý · Đang sinh câu trả lời...`
          : 'Đang tra cứu cơ sở dữ liệu pháp luật (Vector + BM25)...'}
      </span>
      <span className="flex items-center text-[10px] text-primary/80 font-mono ml-auto">
        <Zap className="h-3 w-3 mr-0.5" /> SSE Stream
      </span>
    </div>
  );
};
