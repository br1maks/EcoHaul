import { apiClient } from './client';
import axios from 'axios';
import { clearTokens, getRefreshToken } from './tokens';
export { getAccessToken, setTokens, clearTokens } from './tokens';

interface Tokens { access_token: string; refresh_token: string; token_type: string }
export interface ActiveSession {
  id: string; created_at: string; last_used_at: string; expires_at: string; current: boolean;
}

function clearSignedOut() {
  sessionStorage.setItem('ecohaul_signed_out', 'true');
  clearTokens();
}

const telegramRequests = new Map<string, Promise<Tokens>>();

export const authApi = {
  loginWithTelegram(init_data: string): Promise<Tokens> {
    const existing = telegramRequests.get(init_data);
    if (existing) return existing;
    const operation = apiClient.post<Tokens>('/auth/telegram', { init_data })
      .then(({ data }) => data).finally(() => { telegramRequests.delete(init_data); });
    telegramRequests.set(init_data, operation);
    return operation;
  },
  async loginWithEmail(email: string, password: string): Promise<Tokens> {
    return (await apiClient.post<Tokens>('/auth/admin/login', { email, password })).data;
  },
  async sessions(): Promise<ActiveSession[]> { return (await apiClient.get('/auth/sessions')).data; },
  async revokeSession(id: string): Promise<void> { await apiClient.delete(`/auth/sessions/${id}`); },
  async logout(): Promise<void> {
    const refresh = getRefreshToken();
    if (refresh) {
      try { await apiClient.post('/auth/logout', { refresh_token: refresh }); }
      catch (error) {
        if (!axios.isAxiosError(error) || error.response?.status !== 401) throw error;
      }
    }
    clearSignedOut();
  },
  async logoutAll(): Promise<void> {
    await apiClient.post('/auth/logout-all');
    clearSignedOut();
  },
};
