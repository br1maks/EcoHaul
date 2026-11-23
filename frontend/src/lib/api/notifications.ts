import { apiClient } from './client';
import type { Notification } from '@/shared/types';

interface ServerNotification {
  id: string; user_id: string; title: string; message: string;
  is_read: boolean; sent_at: string; created_at?: string;
}
export async function fetchNotifications(): Promise<Notification[]> {
  const { data } = await apiClient.get<ServerNotification[]>('/notifications');
  return data.map((item) => ({ ...item, type: 'order_confirmed', created_at: item.created_at ?? item.sent_at }));
}
export async function deleteAllNotifications(): Promise<void> { await apiClient.delete('/notifications/delete-all'); }
