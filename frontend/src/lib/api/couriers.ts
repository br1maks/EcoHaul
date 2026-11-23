import { apiClient } from "./client";
import type { CourierListResponse, CourierStatus } from "@/shared/types";

export interface ShiftDetail {
    id: string; started_at: string; ended_at: string | null; is_active: boolean;
    duration_minutes: number | null; orders_completed: number; revenue: number;
    orders: { id: string; status: string; garbage_type: string; number_of_bags: number;
      final_price: number; pickup_address: string | null; accepted_at: string | null; completed_at: string | null }[];
}
export interface ShiftsResponse {
    items: ShiftDetail[]; total: number; page: number; pages: number;
    period_total_shifts: number; period_total_hours: number; period_total_orders: number; period_total_revenue: number;
}

export const couriersApi = {
    getCourierShifts: async (id: string, params?: { date_from?: string; date_to?: string; page?: number; size?: number }): Promise<ShiftsResponse> => {
        return (await apiClient.get(`/admin/couriers/${id}/shifts`, { params })).data;
    },
    getAllCouriers: async (params?: {
        page?: number;
        size?: number;
        status?: CourierStatus;
        is_verified?: boolean;
        is_active?: boolean;
    }): Promise<CourierListResponse> => {
        const response = await apiClient.get('/admin/couriers', { params });
        return response.data;
    },

    getCourierById: async (courierId: string) => {
        const response = await apiClient.get(`/admin/couriers/${courierId}`);
        return response.data;
    },

    assignCourier: async (orderId: string, courierId: string): Promise<void> => {
        await apiClient.patch(`/orders/${orderId}/assign-courier`, null, {
            params: { courier_id: courierId }
        });
    },

    verifyCourier: async (courierId: string): Promise<void> => {
        await apiClient.patch(`/admin/couriers/${courierId}/verify`);
    },

    blockCourier: async (courierId: string): Promise<void> => {
        await apiClient.patch(`/admin/couriers/${courierId}/block`);
    },

    unblockCourier: async (courierId: string): Promise<void> => {
        await apiClient.patch(`/admin/couriers/${courierId}/unblock`);
    },
};
