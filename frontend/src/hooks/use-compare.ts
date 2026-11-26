import { useCallback, useRef, useState } from 'react';
import { API_BASE_URL, apiHeaders } from '@/lib/api-config';
import type { CompareResponseData } from '@/types/chat';

interface UseCompareOptions {
  apiBaseUrl?: string;
  timeoutMs?: number;
}

export function useCompare({
  apiBaseUrl = API_BASE_URL,
  timeoutMs = 120000,
}: UseCompareOptions = {}) {
  const [result, setResult] = useState<CompareResponseData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (query: string, threadId?: string) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(`${apiBaseUrl}/api/v1/query/compare`, {
          method: 'POST',
          headers: apiHeaders(true),
          body: JSON.stringify({ query, ...(threadId ? { thread_id: threadId } : {}) }),
          signal: controller.signal,
        });
        if (!response.ok) {
          const detail = await response.text();
          throw new Error(`Yêu cầu thất bại (${response.status}): ${detail.slice(0, 200)}`);
        }
        const data = (await response.json()) as CompareResponseData;
        setResult(data);
        return data;
      } catch (err) {
        const caught = err as Error;
        setError(
          caught.name === 'AbortError'
            ? 'Yêu cầu bị hủy hoặc quá thời gian chờ.'
            : caught.message || 'Không thể gọi API so sánh.',
        );
        return null;
      } finally {
        clearTimeout(timer);
        setIsLoading(false);
      }
    },
    [apiBaseUrl, timeoutMs],
  );

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, isLoading, error, send, reset };
}
