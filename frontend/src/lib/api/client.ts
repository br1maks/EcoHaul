import axios from 'axios';
import type { InternalAxiosRequestConfig } from 'axios';
import { config } from '@/config/env';
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from './tokens';

type RetryConfig = InternalAxiosRequestConfig & { retried?: boolean };
interface Tokens { access_token: string; refresh_token: string }
let refreshing: Promise<Tokens> | null = null;

export const apiClient = axios.create({ baseURL: `${config.apiUrl}/api/v1`, timeout: 15000 });
apiClient.interceptors.request.use((request) => {
  const token = getAccessToken();
  if (token) request.headers.Authorization = `Bearer ${token}`;
  return request;
});
apiClient.interceptors.response.use((response) => response, async (error: unknown) => {
  if (!axios.isAxiosError(error)) return Promise.reject(error);
  const request = error.config as RetryConfig | undefined;
  if (error.response?.status !== 401 || !request || request.retried || request.url?.startsWith('/auth/')) {
    return Promise.reject(error);
  }
  const refreshToken = getRefreshToken();
  if (!refreshToken) return Promise.reject(error);
  request.retried = true;
  try {
    if (!refreshing) {
      refreshing = axios.post<Tokens>(`${config.apiUrl}/api/v1/auth/refresh`, { refresh_token: refreshToken }, { timeout: 15000 })
        .then(({ data }) => { setTokens(data.access_token, data.refresh_token); return data; })
        .finally(() => { refreshing = null; });
    }
    const tokens = await refreshing;
    request.headers.Authorization = `Bearer ${tokens.access_token}`;
    return apiClient(request);
  } catch (refreshError) {
    clearTokens();
    return Promise.reject(refreshError);
  }
});
