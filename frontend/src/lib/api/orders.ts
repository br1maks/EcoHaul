import { apiClient } from "./client";
import type { OrderCreate, OrderListResponse, OrderResponse, OrderStatus } from '@/shared/types';

export const ordersApi = {
    getOrders: async (params?: { page?: number; size?: number; status_filter?: OrderStatus }): Promise<OrderListResponse> => {
        return (await apiClient.get('/orders', { params })).data;
    },
    createOrder: async (data: OrderCreate): Promise<OrderResponse> => {
        return (await apiClient.post('/orders', data)).data;
    },
    /**
     * Получить все заказы(для админа)
     */
    getAllOrders: async (params?: {
        page?: number;
        size?: number;
        status_filter?: OrderStatus;
        client_id?: string;
        courier_id?: string;
    }): Promise<OrderListResponse> => {
        const response = await apiClient.get('/orders/all', { params });
        return response.data;
    },

    /**
     * Получить заказ по ID
     */
    getOrderById: async (orderId: string): Promise<OrderResponse> => {
        const response = await apiClient.get(`/orders/${orderId}`);
        return response.data;
    },

    /**
     * Обновить статус заказа
     */
    updateOrderStatus: async (orderId: string, status: OrderStatus): Promise<OrderResponse> => {
        const response = await apiClient.patch(`/orders/${orderId}/status`, { status });
        return response.data;
    },

    /**
     * Отменить заказ
     */
    cancelOrder: async (orderId: string, reason?: string): Promise<OrderResponse> => {
        const response = await apiClient.patch(`/orders/${orderId}/cancel`, { reason });
        return response.data;
    }
}
