import React, { useRef, useEffect } from 'react';
import { Message } from '@/hooks/use-chat-stream';
import { Citation } from '@/types/chat';
import { ChatMessage } from './chat-message';
import { ChatInput } from './chat-input';
import { StreamIndicator } from './stream-indicator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ShieldCheck, Sparkles } from 'lucide-react';

interface ChatContainerProps {
  messages: Message[];
  isStreaming: boolean;
  currentCitations: Citation[];
  error: string | null;
  activeCitationId?: string;
  onSendMessage: (query: string, options?: { filterSuperseded: boolean }) => void;
  onStopStreaming: () => void;
  onCitationSelect: (citation: Citation) => void;
}

export const ChatContainer: React.FC<ChatContainerProps> = ({
  messages,
  isStreaming,
  currentCitations,
  error,
  activeCitationId,
  onSendMessage,
  onStopStreaming,
  onCitationSelect,
}) => {
  const scrollEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on streaming/messages
  useEffect(() => {
    scrollEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentCitations]);

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Messages Scroll Area */}
      <ScrollArea className="flex-1 p-4">
        {messages.length === 0 ? (
          <div className="flex h-[60vh] flex-col items-center justify-center text-center px-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary mb-4 shadow-xs">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <h2 className="text-lg font-semibold tracking-tight text-foreground">
              Scan2RAG Legal Intelligence
            </h2>
            <p className="mt-1.5 max-w-md text-xs text-muted-foreground leading-relaxed">
              Hệ thống hỏi đáp chuyên sâu tiêu chuẩn sức khỏe nghĩa vụ quân sự và văn bản quy phạm pháp luật Việt Nam. Mọi câu trả lời đều được đối chiếu trực tiếp từ PDF gốc.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-2 max-w-lg">
              <span className="inline-flex items-center text-[11px] text-muted-foreground bg-muted/60 px-2.5 py-1 rounded-full border">
                <Sparkles className="h-3 w-3 mr-1 text-primary" /> VBHN 88/VBHN-BQP
              </span>
              <span className="inline-flex items-center text-[11px] text-muted-foreground bg-muted/60 px-2.5 py-1 rounded-full border">
                <Sparkles className="h-3 w-3 mr-1 text-primary" /> Thông tư 105 & 106
              </span>
              <span className="inline-flex items-center text-[11px] text-muted-foreground bg-muted/60 px-2.5 py-1 rounded-full border">
                <Sparkles className="h-3 w-3 mr-1 text-primary" /> Bảng điểm mắt, thể lực, nội - ngoại khoa
              </span>
            </div>
          </div>
        ) : (
          <div className="space-y-4 max-w-4xl mx-auto">
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                activeCitationId={activeCitationId}
                onCitationSelect={onCitationSelect}
              />
            ))}
            <StreamIndicator
              isStreaming={isStreaming}
              citationCount={currentCitations.length}
            />
            {error && (
              <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
                {error}
              </div>
            )}
            <div ref={scrollEndRef} />
          </div>
        )}
      </ScrollArea>

      {/* Input Form Bar */}
      <div className="border-t bg-card/60 p-4 backdrop-blur supports-[backdrop-filter]:bg-card/40">
        <div className="max-w-4xl mx-auto">
          <ChatInput
            onSendMessage={onSendMessage}
            isStreaming={isStreaming}
            onStopStreaming={onStopStreaming}
          />
        </div>
      </div>
    </div>
  );
};
