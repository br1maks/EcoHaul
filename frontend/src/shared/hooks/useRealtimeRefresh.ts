import { useEffect } from 'react';

/** Socket events invalidate views; HTTP remains authoritative, including after gaps. */
export function useRealtimeRefresh(refresh: () => void | Promise<void>) {
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    let running = false;
    let dirty = false;
    let stopped = false;
    const schedule = () => {
      if (stopped || document.visibilityState === 'hidden') return;
      dirty = true;
      if (running || timer) return;
      timer = setTimeout(async () => {
        timer = undefined;
        dirty = false;
        running = true;
        try { await refresh(); } catch { /* Views own their error presentation. */ }
        finally {
          running = false;
          if (dirty) schedule();
        }
      }, 150);
    };
    window.addEventListener('ecohaul:sync', schedule);
    document.addEventListener('visibilitychange', schedule);
    const fallback = setInterval(schedule, 30000);
    return () => {
      stopped = true;
      clearTimeout(timer);
      clearInterval(fallback);
      window.removeEventListener('ecohaul:sync', schedule);
      document.removeEventListener('visibilitychange', schedule);
    };
  }, [refresh]);
}
