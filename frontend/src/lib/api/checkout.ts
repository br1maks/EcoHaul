import { apiClient } from './client';
import { getAccessToken } from './tokens';

interface CheckoutResult {
  payment_id: string;
  payment_url: string | null;
  status: 'PENDING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  creation_state: string;
  amount: number;
}
interface Intent { key: string; payment_id?: string }
const STORAGE = 'ecohaul_checkout_intents';
const inflight = new Map<string, Promise<CheckoutResult & { payment_url: string }>>();

function intents(): Record<string, Intent> {
  return JSON.parse(sessionStorage.getItem(STORAGE) ?? '{}');
}

export function forgetCheckout(paymentId: string) {
  const saved = intents();
  for (const [name, intent] of Object.entries(saved)) {
    if (intent.payment_id === paymentId) delete saved[name];
  }
  sessionStorage.setItem(STORAGE, JSON.stringify(saved));
}

export function performCheckout(path: string, data: Record<string, unknown>) {
  const token = getAccessToken();
  if (!token) return Promise.reject(new Error('Войдите в аккаунт, чтобы оплатить'));
  // Used only to namespace local retry keys; the server validates identity separately.
  const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
  const name = JSON.stringify([payload.sub, path, Object.entries(data).sort(([a], [b]) => a.localeCompare(b))]);
  const current = inflight.get(name);
  if (current) return current;
  const saved = intents();
  const intent = saved[name] ?? { key: crypto.randomUUID() };
  saved[name] = intent;
  // Fail before sending if retry identity cannot be persisted.
  sessionStorage.setItem(STORAGE, JSON.stringify(saved));
  const operation = (async () => {
    for (let attempt = 0; attempt < 5; attempt++) {
      const { data: result } = await apiClient.post<CheckoutResult>(path, data, {
        headers: { 'Idempotency-Key': intent.key },
      });
      const latest = intents();
      latest[name] = { ...intent, payment_id: result.payment_id };
      sessionStorage.setItem(STORAGE, JSON.stringify(latest));
      if (result.status === 'COMPLETED') {
        forgetCheckout(result.payment_id);
        return { ...result, payment_url: `/payment/success?payment_id=${encodeURIComponent(result.payment_id)}` };
      }
      if (result.status === 'FAILED' || result.status === 'CANCELLED') {
        forgetCheckout(result.payment_id);
        throw new Error('Платёж отклонён или отменён. Можно начать новую попытку.');
      }
      if (result.creation_state === 'REVIEW') {
        throw new Error('Платёж требует проверки. Не создавайте повторную оплату; обратитесь в поддержку.');
      }
      if (result.payment_url) return { ...result, payment_url: result.payment_url };
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
    throw new Error('Подтверждаем создание платежа. Повторите попытку позже — сохранённая попытка будет продолжена.');
  })().finally(() => { inflight.delete(name); });
  inflight.set(name, operation);
  return operation;
}
