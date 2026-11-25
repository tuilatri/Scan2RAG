import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL, apiHeaders } from '@/lib/api-config';

export type BackendStatus = 'connected' | 'connecting' | 'offline';

interface UseBackendHealthOptions {
  apiBaseUrl?: string;
  pollIntervalMs?: number;
}

export function useBackendHealth({
  apiBaseUrl = API_BASE_URL,
  pollIntervalMs = 30000,
}: UseBackendHealthOptions = {}) {
  const [status, setStatus] = useState<BackendStatus>('connecting');

  const checkHealth = useCallback(async () => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/health`, {
        signal: controller.signal,
        headers: apiHeaders(),
      });
      setStatus(res.ok ? 'connected' : 'offline');
    } catch {
      setStatus('offline');
    } finally {
      clearTimeout(timeoutId);
    }
  }, [apiBaseUrl]);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, pollIntervalMs);
    return () => clearInterval(interval);
  }, [checkHealth, pollIntervalMs]);

  return { status, checkHealth };
}
