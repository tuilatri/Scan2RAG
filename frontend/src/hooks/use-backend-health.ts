import { useState, useEffect, useCallback } from 'react';

export type BackendStatus = 'connected' | 'connecting' | 'offline';

interface UseBackendHealthOptions {
  apiBaseUrl?: string;
  pollIntervalMs?: number;
}

export function useBackendHealth({
  apiBaseUrl = 'http://localhost:8000',
  pollIntervalMs = 30000,
}: UseBackendHealthOptions = {}) {
  const [status, setStatus] = useState<BackendStatus>('connecting');

  const checkHealth = useCallback(async () => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/health`, {
        signal: controller.signal,
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
