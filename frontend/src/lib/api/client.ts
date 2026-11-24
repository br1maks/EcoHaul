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
  const noRefresh = ['/auth/refresh', '/auth/admin/login', '/auth/telegram', '/auth/test', '/auth/logout'];
  if (error.response?.status !== 401 || !request || request.retried || noRefresh.includes(request.url ?? '')) {
    return Promise.reject(error);
  }
  const refreshToken = getRefreshToken();
  if (!refreshToken) return Promise.reject(error);
  request.retried = true;
  const currentAccess = getAccessToken();
  if (currentAccess && request.headers.Authorization !== `Bearer ${currentAccess}`) {
    request.headers.Authorization = `Bearer ${currentAccess}`;
    return apiClient(request);
  }
  try {
    if (!refreshing) {
      refreshing = axios.post<Tokens>(`${config.apiUrl}/api/v1/auth/refresh`, { refresh_token: refreshToken }, { timeout: 15000 })
        .then(({ data }) => {
          if (getRefreshToken() !== refreshToken) throw new Error('Сессия изменилась во время обновления');
          setTokens(data.access_token, data.refresh_token);
          return data;
        })
        .finally(() => { refreshing = null; });
    }
    const tokens = await refreshing;
    request.headers.Authorization = `Bearer ${tokens.access_token}`;
    return apiClient(request);
  } catch (refreshError) {
    if (getRefreshToken() === refreshToken && axios.isAxiosError(refreshError)
      && [401, 403].includes(refreshError.response?.status ?? 0)) clearTokens();
    return Promise.reject(refreshError);
  }
});
