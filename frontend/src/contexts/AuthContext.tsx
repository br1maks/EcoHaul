import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { authApi, getAccessToken, setTokens } from '@/lib/api/auth';

interface AuthContextType {
  isReady: boolean;
}

const AuthContext = createContext<AuthContextType>({ isReady: false });

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    initAuth();
  }, []);

  const initAuth = async () => {
    
    if (window.location.pathname === '/admin/login') {
      setIsReady(true);
      return;
    }

    const tg = window.Telegram?.WebApp;

    if (tg?.initData) {
      
      tg.ready();
      try {
        const tokens = await authApi.loginWithTelegram(tg.initData);
        setTokens(tokens.access_token, tokens.refresh_token);
      } catch (error) {
        console.error('Ошибка Telegram авторизации:', error);
      }
      setIsReady(true);
      return;
    }

    if (getAccessToken()) {
      setIsReady(true);
      return;
    }

    try {
      const tokens = await authApi.loginTest(987654321, 'Admin', 'Dev');
      setTokens(tokens.access_token, tokens.refresh_token);
    } catch (error) {
      console.error('Ошибка тестовой авторизации:', error);
    }

    setIsReady(true);
  };

  if (!isReady) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        fontSize: '16px',
        color: '#666',
      }}>
        Загрузка...
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ isReady }}>
      {children}
    </AuthContext.Provider>
  );
};
