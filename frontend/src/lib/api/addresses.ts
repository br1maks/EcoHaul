import { apiClient } from './client';
import type { Address, CreateAddressData, UpdateAddressData } from '@/shared/types';

export const addressesApi = {
  /**
   * Получить все адреса пользователя
   */
  getAll: async (): Promise<Address[]> => {
    const response = await apiClient.get<Address[]>('/addresses');
    return response.data;
  },

  /**
   * Получить адрес по ID
   */
  getById: async (id: string): Promise<Address> => {
    const response = await apiClient.get<Address>(`/addresses/${id}`);
    return response.data;
  },

  /**
   * Создать новый адрес
   */
  create: async (data: CreateAddressData): Promise<Address> => {
    const response = await apiClient.post<Address>('/addresses', data);
    return response.data;
  },

  /**
   * Обновить адрес
   */
  update: async (id: string, data: UpdateAddressData): Promise<Address> => {
    const response = await apiClient.patch<Address>(`/addresses/${id}`, data);
    return response.data;
  },

  /**
   * Удалить адрес
   */
  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/addresses/${id}`);
  },
};
