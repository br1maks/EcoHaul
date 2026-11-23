import { useState, useRef, useEffect } from 'react';
import { Bell, X, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { useNotificationsStore } from '@/store/notifications.store';
import { deleteAllNotifications } from '@/lib/api/notifications';

const formatTimeAgo = (dateStr: string): string => {
  const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (diff < 60) return 'только что';
  if (diff < 3600) return `${Math.floor(diff / 60)} мин назад`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} ч назад`;
  return `${Math.floor(diff / 86400)} д назад`;
};

export const NotificationBell = () => {
  const [isOpen, setIsOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const notifications = useNotificationsStore((state) => state.notifications);
  const unreadCount = useNotificationsStore((state) => state.unreadCount);
  const markAllAsRead = useNotificationsStore((state) => state.markAllAsRead);
  const clearNotifications = useNotificationsStore((state) => state.clearNotifications);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const handleToggle = () => {
    const opening = !isOpen;
    setIsOpen(opening);
    if (opening) markAllAsRead();
  };

  const handleClearAll = async () => {
    try {
      await deleteAllNotifications();
    } catch {
      toast.error('Не удалось удалить уведомления');
      return;
    }
    clearNotifications();
  };

  return (
    <div ref={panelRef} className="relative">
      {}
      <button
        onClick={handleToggle}
        className="relative p-2 rounded-full hover:bg-gray-100 transition-colors"
        aria-label="Уведомления"
      >
        <Bell
          size={20}
          className={unreadCount > 0 ? 'text-green-600' : 'text-gray-500'}
        />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
          {}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <span className="font-semibold text-gray-800">Уведомления</span>
            <div className="flex items-center gap-2">
              {notifications.length > 0 && (
                <button
                  onClick={handleClearAll}
                  className="text-gray-400 hover:text-red-500 transition-colors"
                  title="Очистить всё"
                >
                  <Trash2 size={16} />
                </button>
              )}
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {}
          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="py-8 text-center text-gray-400 text-sm">
                Нет уведомлений
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  className={`px-4 py-3 border-b border-gray-50 last:border-0 ${
                    !n.is_read ? 'bg-green-50' : 'bg-white'
                  }`}
                >
                  <p className="text-sm font-medium text-gray-800">{n.title}</p>
                  <p className="text-sm text-gray-600 mt-0.5 whitespace-pre-line line-clamp-3 break-words">{n.message}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {formatTimeAgo(n.created_at)}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
