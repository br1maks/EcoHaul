import axios from 'axios';

export function errorDetail(error: unknown): string | undefined {
  if (!axios.isAxiosError<{ detail?: unknown }>(error)) return undefined;
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return 'Проверьте введённые данные';
  return error.message;
}
