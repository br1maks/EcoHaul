
const getWsUrl = (): string => {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;

  const { protocol, hostname, port } = window.location;

  if (hostname === 'localhost') {
    return 'ws://localhost:8001/api/v1/ws';
  }

  const wsProtocol = protocol === 'https:' ? 'wss:' : 'ws:';
  const portStr = port ? `:${port}` : '';
  return `${wsProtocol}//${hostname}${portStr}/api/v1/ws`;
};

export const config = {
  apiUrl: import.meta.env.VITE_API_URL ?? '',
  wsUrl: getWsUrl(),
  isDevelopment: import.meta.env.DEV,
  isProduction: import.meta.env.PROD,
} as const;
