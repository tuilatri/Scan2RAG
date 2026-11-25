import React from 'react';
import { User, Bot, Clock } from 'lucide-react';
import { Message } from '@/hooks/use-chat-stream';
import { Citation } from '@/types/chat';
import { ModelBadge } from './model-badge';
import { CitationList } from './citation-list';
import { cn } from '@/lib/utils';

interface ChatMessageProps {
  message: Message;
  activeCitationId?: string;
  onCitationSelect: (citation: Citation) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  activeCitationId,
  onCitationSelect,
}) => {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex w-full space-x-3 py-4 px-4 rounded-xl transition-colors',
        isUser
          ? 'bg-muted/30 ml-auto max-w-[85%] border self-end'
          : 'bg-card border shadow-sm max-w-full'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-lg font-semibold text-xs shadow-sm',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-primary/10 text-primary border border-primary/20'
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Message Body */}
      <div className="flex-1 space-y-2 overflow-hidden">
        {/* Header metadata */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="font-medium text-foreground">
            {isUser ? 'Công dân / Người tra cứu' : 'Trợ lý Pháp lý Scan2RAG'}
          </span>
          <div className="flex items-center space-x-2">
            {!isUser && (
              <ModelBadge provider={message.provider} model={message.model} />
            )}
            {message.latency_total_ms ? (
              <span className="flex items-center text-[10px] font-mono text-muted-foreground">
                <Clock className="h-2.5 w-2.5 mr-0.5" />
                {(message.latency_total_ms / 1000).toFixed(1)}s
              </span>
            ) : null}
          </div>
        </div>

        {/* Content text */}
        <div className="prose prose-sm dark:prose-invert max-w-none text-sm leading-relaxed whitespace-pre-wrap break-words text-foreground">
          {message.content ? (
            message.content
          ) : message.isStreaming ? (
            <div className="flex items-center space-x-1.5 py-1 text-muted-foreground italic">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-primary animate-bounce" />
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-delay:0.2s]" />
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-delay:0.4s]" />
              <span className="text-xs ml-1 font-sans">Đang soạn thảo câu trả lời...</span>
            </div>
          ) : (
            <span className="text-muted-foreground italic">Không có nội dung phản hồi.</span>
          )}
        </div>

        {/* Citations block for Assistant */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <CitationList
            citations={message.citations}
            activeCitationId={activeCitationId}
            onCitationSelect={onCitationSelect}
          />
        )}
      </div>
    </div>
  );
};
