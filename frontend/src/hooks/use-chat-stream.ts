import { useState, useRef, useCallback } from 'react';
import { Citation, StreamEvent } from '@/types/chat';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  provider?: string;
  model?: string;
  latency_total_ms?: number;
  timestamp: Date;
  isStreaming?: boolean;
}

interface UseChatStreamOptions {
  apiBaseUrl?: string;
  timeoutMs?: number;
}

export function useChatStream({
  apiBaseUrl = 'http://localhost:8000',
  timeoutMs = 30000,
}: UseChatStreamOptions = {}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [streamStatus, setStreamStatus] = useState<string | null>(null);
  const [currentCitations, setCurrentCitations] = useState<Citation[]>([]);
  const [error, setError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const stopStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const sendMessage = useCallback(
    async (
      queryText: string,
      options?: {
        filterSuperseded?: boolean;
        topKRetrieval?: number;
        topKRerank?: number;
      }
    ) => {
      if (!queryText.trim() || isStreaming) return;

      const userMessageId = `user_${Date.now()}`;
      const assistantMessageId = `asst_${Date.now()}`;

      const userMessage: Message = {
        id: userMessageId,
        role: 'user',
        content: queryText.trim(),
        timestamp: new Date(),
      };

      const initialAssistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        citations: [],
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMessage, initialAssistantMessage]);
      setIsStreaming(true);
      setCurrentCitations([]);
      setError(null);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      // Timeout watchdog
      const timeoutId = setTimeout(() => {
        if (abortControllerRef.current === controller) {
          controller.abort();
          setError('Yêu cầu quá thời gian chờ (Timeout 30s). Vui lòng thử lại.');
          setIsStreaming(false);
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    content:
                      msg.content ||
                      '⚠️ Yêu cầu bị gián đoạn do phản hồi từ máy chủ vượt quá thời gian cho phép.',
                    isStreaming: false,
                  }
                : msg
            )
          );
        }
      }, timeoutMs);

      try {
        const response = await fetch(`${apiBaseUrl}/api/v1/query/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query: queryText.trim(),
            top_k_retrieval: options?.topKRetrieval ?? 15,
            top_k_rerank: options?.topKRerank ?? 5,
            filter_superseded: options?.filterSuperseded ?? true,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Máy chủ trả về mã lỗi: ${response.status} ${response.statusText}`);
        }

        if (!response.body) {
          throw new Error('ReadableStream không được máy chủ hỗ trợ.');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let accumulatedText = '';
        let citationsReceived: Citation[] = [];
        let providerName = '';
        let modelName = '';
        let latencyTotal = 0;
        let lineBuffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          lineBuffer += chunk;

          const lines = lineBuffer.split('\n');
          // Keep trailing non-newline data in buffer
          lineBuffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed.startsWith('data:')) continue;

            const jsonStr = trimmed.replace(/^data:\s*/, '');
            if (!jsonStr) continue;

            try {
              const event: StreamEvent = JSON.parse(jsonStr);

              if (event.event === 'status') {
                setStreamStatus(event.status || 'retrieving');
              } else if (event.event === 'citations') {
                setStreamStatus('generating');
                citationsReceived = event.citations || [];
                setCurrentCitations(citationsReceived);
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, citations: citationsReceived }
                      : msg
                  )
                );
              } else if (event.event === 'token') {
                accumulatedText += event.token || '';
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, content: accumulatedText }
                      : msg
                  )
                );
              } else if (event.event === 'done') {
                providerName = event.provider || '';
                modelName = event.model || '';
                latencyTotal = event.latency_total_ms || 0;
              }
            } catch {
              // Ignore malformed JSON chunk line safely
            }
          }
        }

        clearTimeout(timeoutId);

        // Finalize assistant message
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  content: accumulatedText,
                  citations: citationsReceived,
                  provider: providerName,
                  model: modelName,
                  latency_total_ms: latencyTotal,
                  isStreaming: false,
                }
              : msg
          )
        );
      } catch (err: unknown) {
        clearTimeout(timeoutId);
        if (err instanceof DOMException && err.name === 'AbortError') {
          // Handled by user abort / timeout
          return;
        }
        const errorMsg = err instanceof Error ? err.message : 'Lỗi không xác định khi truy vấn SSE.';
        setError(errorMsg);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  content:
                    msg.content ||
                    `⚠️ Đã xảy ra lỗi trong quá trình xử lý câu hỏi: ${errorMsg}`,
                  isStreaming: false,
                }
              : msg
          )
        );
      } finally {
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    },
    [apiBaseUrl, isStreaming, timeoutMs]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setCurrentCitations([]);
    setError(null);
  }, []);

  return {
    messages,
    isStreaming,
    streamStatus,
    currentCitations,
    error,
    sendMessage,
    stopStream,
    clearMessages,
  };
}
