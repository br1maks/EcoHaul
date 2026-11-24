import { create } from 'zustand';
import type { Notification } from '@/shared/types';

interface NotificationsStore {
  notifications: Notification[];
  unreadCount: number;
  generation: number;

  setNotifications: (notifications: Notification[]) => void;
  mergeNotifications: (notifications: Notification[], atStart?: Notification[]) => void;
  addNotification: (notification: Notification) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  setUnreadCount: (count: number) => void;
  clearNotifications: () => void;
}

export const useNotificationsStore = create<NotificationsStore>((set) => ({
  notifications: [],
  unreadCount: 0,
  generation: 0,

  setNotifications: (notifications) =>
    set((state) => ({
      notifications,
      unreadCount: notifications.filter((n) => !n.is_read).length,
      generation: state.generation + 1,
    })),

  mergeNotifications: (incoming, atStart = []) =>
    set((state) => {
      const current = new Map(state.notifications.map((item) => [item.id, item]));
      const before = new Set(atStart.map((item) => item.id));
      const byId = new Map<string, Notification>();
      for (const item of incoming) {
        if (before.has(item.id) && !current.has(item.id)) continue;
        byId.set(item.id, { ...item, is_read: item.is_read || Boolean(current.get(item.id)?.is_read) });
      }
      for (const item of state.notifications) {
        if (!before.has(item.id) && !byId.has(item.id)) byId.set(item.id, item);
      }
      const notifications = [...byId.values()].sort((a, b) => b.created_at.localeCompare(a.created_at));
      return { notifications, unreadCount: notifications.filter((item) => !item.is_read).length };
    }),

  addNotification: (notification) =>
    set((state) => {
      if (state.notifications.some((item) => item.id === notification.id)) return state;
      return {
        notifications: [notification, ...state.notifications],
        unreadCount: notification.is_read ? state.unreadCount : state.unreadCount + 1,
      };
    }),

  markAsRead: (id) =>
    set((state) => {
      const item = state.notifications.find((notification) => notification.id === id);
      if (!item || item.is_read) return state;
      return {
        notifications: state.notifications.map((notification) =>
          notification.id === id ? { ...notification, is_read: true } : notification
        ),
        unreadCount: Math.max(0, state.unreadCount - 1),
      };
    }),

  markAllAsRead: () =>
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, is_read: true })),
      unreadCount: 0,
    })),

  setUnreadCount: (count) => set({ unreadCount: count }),

  clearNotifications: () => set((state) => ({
    notifications: [], unreadCount: 0, generation: state.generation + 1,
  })),
}));
