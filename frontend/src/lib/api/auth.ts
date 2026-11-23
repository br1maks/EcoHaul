import { apiClient } from './client';
export { getAccessToken, setTokens, clearTokens } from './tokens';

interface Tokens { access_token: string; refresh_token: string; token_type: string }

export const authApi = {
  async loginWithTelegram(init_data: string): Promise<Tokens> {
    return (await apiClient.post<Tokens>('/auth/telegram', { init_data })).data;
  },
  async loginWithEmail(email: string, password: string): Promise<Tokens> {
    return (await apiClient.post<Tokens>('/auth/admin/login', { email, password })).data;
  },
};
