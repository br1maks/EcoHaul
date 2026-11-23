import { apiClient } from './client';
import type { Subscription, SubscriptionPlan, SubscriptionPurchaseData, SubscriptionPurchaseResponse, SubscriptionTier } from '@/shared/types';

export const subscriptionsApi = {
  /**
   * Получить список доступных тарифных планов
   */
  getPlans: async (): Promise<SubscriptionPlan[]> => {
    const response = await apiClient.get<SubscriptionPlan[]>('/subscriptions/plans');
    return response.data;
  },

  /**
   * Получить текущую подписку пользователя
   */
  getMySubscription: async (): Promise<Subscription> => {
    const response = await apiClient.get<Subscription>('/subscriptions/me');
    return response.data;
  },

  /**
   * Купить подписку (разовая покупка)
   */
  purchase: async (data: SubscriptionPurchaseData): Promise<SubscriptionPurchaseResponse> => {
    const response = await apiClient.post<SubscriptionPurchaseResponse>('/subscriptions/purchase', data);
    return response.data;
  },

  /**
   * Включить автопродление подписки
   */
  enableAutoRenew: async (tier: SubscriptionTier): Promise<SubscriptionPurchaseResponse> => {
    const response = await apiClient.post<SubscriptionPurchaseResponse>('/subscriptions/recurring/enable', { tier });
    return response.data;
  },

  /**
   * Выключить автопродление подписки
   */
  disableAutoRenew: async (): Promise<{ message: string; subscription_valid_until: string }> => {
    const response = await apiClient.delete('/subscriptions/recurring/disable');
    return response.data;
  },
};
