import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { authApi, getAccessToken, setTokens } from '@/lib/api/auth';

import { AuthContext } from './auth.context';

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [state, setState] = useState<'loading' | 'ready' | 'required' | 'error'>('loading');
  useEffect(() => {
    let active = true;
    async function initialize() {
      if (window.location.pathname === '/admin/login') {
        if (active) setState('ready');
        return;
      }
      const tg = window.Telegram?.WebApp;
      if (tg?.initData) {
        tg.ready();
        try {
          const tokens = await authApi.loginWithTelegram(tg.initData);
          if (active) { setTokens(tokens.access_token, tokens.refresh_token); setState('ready'); }
        } catch {
          if (active) setState('error');
        }
      } else if (active) {
        setState(getAccessToken() ? 'ready' : 'required');
      }
    }
    void initialize();
    return () => { active = false; };
  }, []);

  if (state !== 'ready') return (
    <main className="min-h-screen flex items-center justify-center p-6 bg-green-50">
      <div className="max-w-sm text-center space-y-4">
        <h1 className="text-3xl font-bold text-green-800">EcoHaul</h1>
        <p>{state === 'loading' ? 'Подключаемся…' : state === 'error' ? 'Не удалось войти. Откройте приложение заново через Telegram.' : 'Откройте приложение через Telegram, чтобы оформить вывоз.'}</p>
        {state !== 'loading' && <a className="inline-block text-green-800 underline" href="/admin/login">Вход для администратора</a>}
      </div>
    </main>
  );
  return <AuthContext.Provider value={{ isReady: true }}>{children}</AuthContext.Provider>;
};
