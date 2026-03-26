import { useState, useCallback } from "react";
import { ordersApi } from '@/features/orders/api/orders.api';
import type { Order, CreateOrderData } from '@/shared/types';

export const useOrders = () => {
    const [orders, setOrders] = useState<Order[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchOrders = useCallback(async (params?: {
        status?: string;
        page?: number;
        page_size?: number;
    }) => {
        try {
            setLoading(true);
            setError(null);
            const response = await ordersApi.getOrders(params);
            setOrders(response.items);
        } catch (err: any) {
            setError(err.detail || 'Ошибка загрузки заказов');
        } finally {
            setLoading(false);
        }
    }, []);

    const createOrder = useCallback(async (data: CreateOrderData) => {
        try {
            setLoading(true);
            setError(null);
            const order = await ordersApi.createOrder(data);
            setOrders((prev) => [order, ...prev]);
            return order;
        } catch (err: any) {
            setError(err.detail || 'Ошибка создания заказа');
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const cancelOrder = useCallback(async (id: string) => {
        try {
            setLoading(true);
            setError(null);
            const order = await ordersApi.cancelOrder(id);
            setOrders((prev) =>
                prev.map((o) => (o.id === id ? order : o))
            );
            return order;
        } catch (err: any) {
            setError(err.detail || 'Ошибка отмены заказа');
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    return {
        orders,
        loading,
        error,
        fetchOrders,
        createOrder,
        cancelOrder,
    };
};
