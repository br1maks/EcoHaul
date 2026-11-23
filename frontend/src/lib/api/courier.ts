import { apiClient } from './client';
import type { CourierStatus, OrderListResponse, OrderResponse } from '@/shared/types';

export interface CourierShift {
  id: string; courier_id: string; started_at: string; ended_at: string | null;
  orders_completed: number; total_distance_km: number; duration_hours: number | null;
  is_active: boolean; notes: string | null;
}
export const courierApi = {
  async getAvailableOrders(): Promise<OrderResponse[]> { return (await apiClient.get('/orders/available')).data; },
  async getMyDeliveries(params?: { size?: number; page?: number }): Promise<OrderListResponse> {
    return (await apiClient.get('/orders/my-deliveries', { params })).data;
  },
  async acceptOrder(id: string): Promise<OrderResponse> { return (await apiClient.post(`/orders/${id}/accept`)).data; },
  async updateOrderStatus(id: string, status: string): Promise<OrderResponse> {
    return (await apiClient.patch(`/orders/${id}/status`, { status })).data;
  },
  async getActiveShift(): Promise<CourierShift> { return (await apiClient.get('/courier-shifts/current')).data; },
  async getShifts(params?: { limit?: number }): Promise<{ items: CourierShift[] }> {
    return { items: (await apiClient.get<CourierShift[]>('/courier-shifts/history', { params })).data };
  },
  async startShift(): Promise<CourierShift> { return (await apiClient.post('/courier-shifts/start')).data; },
  async endShift(): Promise<CourierShift> { return (await apiClient.post('/courier-shifts/end')).data; },
  async updateStatus(courier_status: CourierStatus) {
    return (await apiClient.patch('/users/me', { courier_status })).data;
  },
};
