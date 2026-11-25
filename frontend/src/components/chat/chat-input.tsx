import React, { useState, useRef, useEffect } from 'react';
import { Send, Square, CornerDownLeft, Sparkles, Filter } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface ChatInputProps {
  onSendMessage: (
    query: string,
    options?: { filterSuperseded: boolean }
  ) => void;
  isStreaming: boolean;
  onStopStreaming: () => void;
}

const SAMPLE_QUERIES = [
  'Cận thị từ 3 đến dưới 4 độ khám sức khỏe nghĩa vụ quân sự mấy điểm?',
  'Loạn thị có được tạm hoãn nghĩa vụ quân sự theo Thông tư 88 không?',
  'Quy định chấm điểm thể lực chỉ số BMI trong tuyển quân?',
];

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isStreaming,
  onStopStreaming,
}) => {
  const [input, setInput] = useState('');
  const [filterSuperseded, setFilterSuperseded] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [input]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isStreaming) return;

    onSendMessage(input.trim(), { filterSuperseded });
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="space-y-2.5">
      {/* Sample Query Prompts */}
      <div className="hidden sm:flex items-center space-x-1.5 overflow-x-auto pb-1 text-xs text-muted-foreground no-scrollbar">
        <Sparkles className="h-3 w-3 shrink-0 text-primary" />
        <span className="shrink-0 text-[11px] font-medium">Gợi ý câu hỏi:</span>
        {SAMPLE_QUERIES.map((sample, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => {
              setInput(sample);
              textareaRef.current?.focus();
            }}
            className="shrink-0 rounded-full border bg-muted/40 px-2.5 py-0.5 text-[11px] text-foreground hover:bg-muted hover:border-primary/40 transition-colors"
          >
            {sample}
          </button>
        ))}
      </div>

      {/* Main Form Box */}
      <form
        onSubmit={handleSubmit}
        className="relative rounded-xl border bg-background shadow-sm focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-colors"
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Nhập câu hỏi pháp lý hoặc tiêu chuẩn sức khỏe quân sự (Enter để gửi)..."
          rows={1}
          disabled={isStreaming}
          className="w-full resize-none border-0 bg-transparent px-4 py-3 text-sm focus:outline-none placeholder:text-muted-foreground/70 disabled:opacity-50"
        />

        <div className="flex items-center justify-between border-t px-3 py-2 bg-muted/20 rounded-b-xl">
          {/* Options toggle */}
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={() => setFilterSuperseded((prev) => !prev)}
              className="inline-flex items-center space-x-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
            >
              <Filter className="h-3 w-3" />
              <span className="text-[11px]">
                {filterSuperseded ? 'Ưu tiên VBHN 88 (mới nhất)' : 'Tìm cả văn bản cũ'}
              </span>
              <Badge
                variant={filterSuperseded ? 'default' : 'secondary'}
                className="h-3.5 px-1 text-[9px] font-mono"
              >
                {filterSuperseded ? 'ON' : 'OFF'}
              </Badge>
            </button>
          </div>

          {/* Action button */}
          <div>
            {isStreaming ? (
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={onStopStreaming}
                className="h-8 px-3 text-xs"
              >
                <Square className="h-3.5 w-3.5 mr-1 fill-current" /> Dừng sinh
              </Button>
            ) : (
              <Button
                type="submit"
                size="sm"
                disabled={!input.trim()}
                className="h-8 px-3 text-xs"
              >
                <span>Gửi câu hỏi</span>
                <CornerDownLeft className="h-3 w-3 ml-1 opacity-70" />
              </Button>
            )}
          </div>
        </div>
      </form>
    </div>
  );
};
