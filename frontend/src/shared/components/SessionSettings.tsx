import { useCallback, useEffect, useState } from 'react';
import { authApi } from '@/lib/api/auth';
import type { ActiveSession } from '@/lib/api/auth';
import { errorDetail } from '@/lib/api/errors';
import { getAccessToken } from '@/lib/api/tokens';

export function SessionSettings() {
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => {
    authApi.sessions().then(setSessions).catch((error) => setError(errorDetail(error) ?? 'Не удалось загрузить сессии'));
  }, []);
  useEffect(load, [load]);
  const run = async (operation: () => Promise<void>) => {
    setBusy(true);
    setError('');
    try { await operation(); if (getAccessToken()) load(); }
    catch (error) { setError(errorDetail(error) ?? 'Не удалось завершить сессию'); }
    finally { setBusy(false); }
  };
  return <section className="bg-white rounded-2xl border border-gray-200 p-5 space-y-4">
    <div>
      <h2 className="font-semibold text-gray-900">Активные сессии</h2>
      <p className="text-sm text-gray-500">Завершите вход, которым больше не пользуетесь.</p>
    </div>
    {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
    <ul className="divide-y divide-gray-100">
      {sessions.map((session) => <li key={session.id} className="flex items-center justify-between gap-4 py-3">
        <div>
          <p className="text-sm font-medium">{session.current ? 'Текущая сессия' : 'Другая сессия'}</p>
          <p className="text-xs text-gray-500">Вход: {new Date(session.created_at).toLocaleString('ru-RU')}</p>
        </div>
        {!session.current && <button disabled={busy} onClick={() => void run(() => authApi.revokeSession(session.id))}
          className="text-sm text-red-600 disabled:opacity-50">Завершить</button>}
      </li>)}
    </ul>
    <div className="flex flex-wrap gap-3">
      <button disabled={busy} onClick={() => void run(() => authApi.logout())}
        className="rounded-lg bg-gray-100 px-4 py-2 text-sm disabled:opacity-50">Выйти</button>
      <button disabled={busy} onClick={() => void run(() => authApi.logoutAll())}
        className="rounded-lg border border-red-200 px-4 py-2 text-sm text-red-600 disabled:opacity-50">Выйти на всех устройствах</button>
    </div>
  </section>;
}
