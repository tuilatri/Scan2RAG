import React, { useState } from 'react';
import { GitCompare, AlertTriangle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { Citation, CompareResponseData } from '@/types/chat';
import { CitationList } from './citation-list';
import { ModelBadge } from './model-badge';

interface CompareContainerProps {
  result: CompareResponseData | null;
  isLoading: boolean;
  error: string | null;
  onSend: (query: string, threadId?: string) => void;
  onCitationSelect: (citation: Citation) => void;
}

export const CompareContainer: React.FC<CompareContainerProps> = ({
  result,
  isLoading,
  error,
  onSend,
  onCitationSelect,
}) => {
  const [query, setQuery] = useState('');
  const [threadId, setThreadId] = useState('');

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed, threadId.trim() || undefined);
  };

  return (
    <div className="flex h-full min-h-0 flex-col bg-background">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center space-x-2">
          <GitCompare className="h-4 w-4 text-muted-foreground" />
          <h1 className="text-sm font-medium">So sánh văn bản</h1>
        </div>
        {result && (
          <Badge variant="outline" className="font-mono text-[10px]">
            {result.plan_source} · {result.history_len} lượt
          </Badge>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-3 border-b px-4 py-4">
        <label className="block space-y-2">
          <span className="text-xs text-muted-foreground">Câu hỏi so sánh</span>
          <Textarea
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="So sánh quy định cận thị giữa Thông tư 105 và Thông tư 106"
            rows={2}
            maxLength={1000}
          />
        </label>
        <div className="flex items-end space-x-3">
          <label className="block flex-1 space-y-2">
            <span className="text-xs text-muted-foreground">Luồng hội thoại (tùy chọn)</span>
            <Input
              value={threadId}
              onChange={(event) => setThreadId(event.target.value)}
              placeholder="dept-01"
              maxLength={64}
            />
          </label>
          <Button type="submit" size="sm" disabled={!query.trim() || isLoading}>
            {isLoading ? 'Đang so sánh' : 'So sánh'}
          </Button>
        </div>
        <p className="text-[11px] text-muted-foreground">
          Luồng chỉ nhớ khi bật COMPARE_MEMORY trên backend
        </p>
      </form>

      {error && (
        <div className="border-b border-destructive/20 px-4 py-3 text-xs text-destructive" role="alert">
          {error}
        </div>
      )}

      <ScrollArea className="min-h-0 flex-1">
        {!result && !error && (
          <div className="px-4 py-6 text-xs text-muted-foreground">
            Chạy một câu so sánh để xem câu trả lời, trích dẫn và kiểm chứng số liệu
          </div>
        )}

        {result && (
          <div className="space-y-5 px-4 py-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Câu trả lời</span>
                <ModelBadge provider={result.provider} model={result.model} />
              </div>
              <p className="whitespace-pre-wrap text-sm leading-6">{result.answer}</p>
              <CitationList
                citations={result.citations}
                onCitationSelect={onCitationSelect}
              />
            </div>

            <div className="border-t pt-4">
              <h2 className="mb-2 text-xs font-medium">Kiểm chứng số liệu</h2>
              {result.verification.passed ? (
                <p className="text-xs text-muted-foreground">
                  {result.verification.checked_numbers} số liệu trong câu trả lời đều có trong trích dẫn
                </p>
              ) : (
                <div className="flex items-start space-x-2 text-xs text-destructive" role="alert">
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  <span>
                    Số liệu chưa có trong trích dẫn:{' '}
                    {Object.keys(result.verification.unsupported_numbers).join(', ')}
                  </span>
                </div>
              )}
            </div>

            <div className="border-t pt-4">
              <h2 className="mb-2 text-xs font-medium">Chứng cứ theo văn bản</h2>
              <div className="grid grid-cols-[1fr_auto_auto] gap-x-3 gap-y-2 text-xs tabular-nums">
                <span className="text-muted-foreground">Văn bản</span>
                <span className="text-right text-muted-foreground">Chunk</span>
                <span className="text-right text-muted-foreground">Trích dẫn</span>
                {result.evidence.map((item) => (
                  <React.Fragment key={item.document_id}>
                    <span className="truncate font-mono">{item.document_id}</span>
                    <span className="text-right">{item.chunk_count}</span>
                    <span className="text-right">{item.citation_ids.length}</span>
                  </React.Fragment>
                ))}
              </div>
            </div>

            {result.version_notes.length > 0 && (
              <div className="border-t pt-4">
                <h2 className="mb-2 text-xs font-medium">Hiệu lực văn bản</h2>
                <div className="space-y-2">
                  {result.version_notes.map((note) => (
                    <div key={note.document_id} className="flex items-start justify-between gap-3 text-xs">
                      <div className="min-w-0 space-y-1">
                        <p className="truncate font-mono">{note.document_id}</p>
                        {note.note && <p className="text-muted-foreground">{note.note}</p>}
                      </div>
                      <div className="shrink-0 text-right text-muted-foreground">
                        <p>{note.effective_date ?? 'không rõ'}</p>
                        {note.superseded_by && <p>bị thay thế</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </ScrollArea>
    </div>
  );
};
