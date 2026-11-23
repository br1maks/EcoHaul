import { apiClient } from "./client";
import type { ClientListResponse } from "@/shared/types";

export const clientsApi = {
    getAllClients: async (params?: {
        page?: number;
        size?: number;
        is_active?: boolean;
        search?: string;
    }): Promise<ClientListResponse> => {
        const response = await apiClient.get('/admin/clients', { params });
        return response.data;
    },

    getClientById: async (clientId: string) => {
        const response = await apiClient.get(`/admin/clients/${clientId}`);
        return response.data;
    },
};

