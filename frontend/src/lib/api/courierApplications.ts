import { apiClient } from './client';

export type ApplicationStatus = 'PENDING' | 'APPROVED' | 'REJECTED';
export interface CreateCourierApplicationData {
  phone: string; email?: string; has_transport: boolean; transport_type?: string;
  work_area?: string; message?: string;
}
export interface CourierApplication extends Omit<CreateCourierApplicationData, 'email' | 'transport_type' | 'work_area' | 'message'> {
  id: string; user_id: string; status: ApplicationStatus; created_at: string;
  email: string | null; transport_type: string | null; work_area: string | null;
  message: string | null; admin_comment: string | null; reviewed_at: string | null;
  user_first_name: string | null; user_last_name: string | null;
  user_telegram_id: number | null; user_telegram_username: string | null;
}
export const courierApplicationsApi = {
  async create(data: CreateCourierApplicationData): Promise<CourierApplication> {
    return (await apiClient.post('/courier-applications', data)).data;
  },
  async getMyApplication(): Promise<CourierApplication | null> {
    return (await apiClient.get('/courier-applications/my')).data;
  },
  async getAll(params?: { status_filter?: ApplicationStatus; page?: number; size?: number }): Promise<{ items: CourierApplication[]; total: number; pages: number }> {
    return (await apiClient.get('/courier-applications', { params })).data;
  },
  async review(id: string, data: { status: 'APPROVED' | 'REJECTED'; admin_comment?: string }): Promise<CourierApplication> {
    return (await apiClient.patch(`/courier-applications/${id}/review`, data)).data;
  },
};
