import { useEffect } from 'react';
import toast from 'react-hot-toast';
import { wsManager } from '@/lib/api/websocket';
import { getAccessToken } from '@/lib/api/auth';
import { useNotificationsStore } from '@/store/notifications.store';
import { fetchNotifications } from '@/lib/api/notifications';

export const useWebSocket = () => {
    const addNotification = useNotificationsStore((state) => state.addNotification);
    const setNotifications = useNotificationsStore((state) => state.setNotifications);

    useEffect(() => {
        fetchNotifications()
            .then((data) => setNotifications(data))
            .catch(() => {});
    }, [setNotifications]);

    useEffect(() => {
        const token = getAccessToken();
        if (!token) return;

        wsManager.connect(token);

        const unsubNewOrder = wsManager.on('NEW_ORDER', (message) => {
            const data = message.data;
            const garbageLabels: Record<string, string> = {
                HOUSEHOLD: 'Бытовой',
                CONSTRUCTION: 'Строительный',
            };
            const garbageLabel = garbageLabels[data.garbage_type as string] ?? data.garbage_type ?? '';
            const bags = data.number_of_bags ? `, ${data.number_of_bags} мешк.` : '';
            const price = data.final_price != null ? `\nЦена: ${data.final_price} руб.` : '';
            const text = `Адрес: ${data.pickup_address ?? 'не указан'}\n${garbageLabel}${bags}${price}`;
            toast(text, { duration: 5000 });
            addNotification({
                id: String(data.order_id ?? crypto.randomUUID()),
                user_id: '',
                type: 'order_confirmed',
                title: 'Новый заказ',
                message: text,
                is_read: false,
                created_at: String(data.created_at ?? new Date().toISOString()),
            });
        });

        const unsubAssigned = wsManager.on('ORDER_ASSIGNED', (message) => {
            const data = message.data;
            const text = `Курьер ${data.courier_name} едет к вам!`;
            toast.success(text, { duration: 5000 });
            addNotification({
                id: crypto.randomUUID(),
                user_id: '',
                type: 'courier_assigned',
                title: 'Курьер назначен',
                message: text,
                is_read: false,
                created_at: new Date().toISOString(),
            });
        });

        const unsubStatus = wsManager.on('ORDER_STATUS_CHANGED', (message) => {
            const data = message.data;
            const statusMessages: Record<string, string> = {
                IN_PROGRESS: 'Курьер в пути',
                ARRIVED: 'Курьер прибыл на место',
                COMPLETED: 'Заказ выполнен!',
                CANCELLED: 'Заказ отменён',
            };
            const text = statusMessages[data.new_status as string]
                ?? `Статус изменён: ${data.new_status}`;

            if (data.new_status === 'COMPLETED') {
                toast.success(text, { duration: 5000 });
            } else if (data.new_status === 'CANCELLED') {
                toast.error(text, { duration: 5000 });
            } else {
                toast(text, { duration: 4000 });
            }

            addNotification({
                id: crypto.randomUUID(),
                user_id: '',
                type: 'order_confirmed',
                title: 'Статус заказа',
                message: text,
                is_read: false,
                created_at: new Date().toISOString(),
            });
        });

        const unsubNotif = wsManager.on('NEW_NOTIFICATION', (message) => {
            const data = message.data;
            const text = String(data.message ?? '');
            toast(text, { duration: 4000 });
            addNotification({
                id: String(data.id ?? crypto.randomUUID()),
                user_id: '',
                type: 'order_confirmed',
                title: String(data.title ?? 'Уведомление'),
                message: text,
                is_read: false,
                created_at: new Date().toISOString(),
            });
        });

        return () => {
            unsubNewOrder();
            unsubAssigned();
            unsubStatus();
            unsubNotif();
            wsManager.disconnect();
        };
    }, [addNotification]);
};
