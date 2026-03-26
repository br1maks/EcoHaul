import { apiClient } from "@/lib/api/client";
import type {
    Order,
    PaginatedResponse,
    CreateOrderData,
    UpdateOrderData,
} from '@/shared/types';

export const ordersApi = {
    async getOrders(params?: {
        status?: string;
        page?: number;
        page_size?: number;
    }): Promise<PaginatedResponse<Order>> {
        const response = await apiClient.get('/orders', { params });
        return response.data;
    },

    async getOrderById(id: string): Promise<Order> {
        const response = await apiClient.get(`/orders/${id}`);
        return response.data;
    },

    async createOrder(data: CreateOrderData): Promise<Order> {
        const response = await apiClient.post('/orders', data);
        return response.data;
    },

    async updateOrder(id: string, data: UpdateOrderData): Promise<Order> {
        const response = await apiClient.patch(`/orders/${id}`, data);
        return response.data;
    },

    async cancelOrder(id: string, reason?: string): Promise<Order> {
        const response = await apiClient.patch(`/orders/${id}/cancel`, { reason });
        return response.data;
    },

    async getActiveOrders(): Promise<Order[]> {
        const response = await apiClient.get('/orders/active');
        return response.data;
    },
};
