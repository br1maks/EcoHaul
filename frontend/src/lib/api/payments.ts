import { apiClient } from './client';
import { performCheckout } from './checkout';

export interface Payment {
  id: string; user_id: string; order_id: string | null; amount: number;
  status: 'PENDING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  payment_type: 'ORDER_PAYMENT' | 'SUBSCRIPTION_PURCHASE' | 'REFUND';
  payment_method: 'CARD'; created_at: string;
}
export const paymentsApi = {
  async getMyPayments(): Promise<{ items: Payment[]; total: number }> { return (await apiClient.get('/payments')).data; },
  async getPayment(id: string): Promise<Payment> { return (await apiClient.get(`/payments/${id}`)).data; },
  async createPayment(data: { payment_type: Payment['payment_type']; amount: number; order_id?: string }): Promise<{ payment_id: string; payment_url: string }> {
    return performCheckout('/payments', data);
  },
};
