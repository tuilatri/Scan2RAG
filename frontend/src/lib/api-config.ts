export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const API_KEY = import.meta.env.VITE_API_KEY || '';

export function apiHeaders(withJson = false): Record<string, string> {
  return {
    ...(withJson ? { 'Content-Type': 'application/json' } : {}),
    'X-API-Key': API_KEY,
  };
}

export function withApiKey(url: string): string {
  if (!API_KEY) return url;
  const separator = url.includes('?') ? '&' : '?';
  const [base, fragment] = url.split('#');
  const withKey = `${base}${separator}api_key=${encodeURIComponent(API_KEY)}`;
  return fragment ? `${withKey}#${fragment}` : withKey;
}
