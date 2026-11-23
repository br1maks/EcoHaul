import { apiClient } from "./client";
import type { User, UserUpdateData } from "@/shared/types";

export const usersApi = {
    getMe: async (): Promise<User> => {
        const response = await apiClient.get('/users/me');
        return response.data;
    },

    updateMe: async (data: UserUpdateData): Promise<User> => {
        const response = await apiClient.patch<User>('/users/me', data);
        return response.data;
    },

    getClientsList: async (): Promise<User[]> => {
        const response = await apiClient.get('/users/clients/list');
        return response.data;
    },

    getById: async (userId: string): Promise<User> => {
        const response = await apiClient.get<User>(`/users/${userId}`);
        return response.data;
    },
};
