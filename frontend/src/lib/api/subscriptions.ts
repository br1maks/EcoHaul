import { apiClient } from './client';
import { performCheckout } from './checkout';
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
    const response = await performCheckout('/subscriptions/purchase', { ...data });
    return { ...response, tier: data.tier, duration_months: data.duration_months };
  },

  /**
   * Включить автопродление подписки
   */
  enableAutoRenew: async (tier: SubscriptionTier): Promise<SubscriptionPurchaseResponse> => {
    const response = await performCheckout('/subscriptions/recurring/enable', { tier });
    return { ...response, tier, duration_months: 1 };
  },

  /**
   * Выключить автопродление подписки
   */
  disableAutoRenew: async (): Promise<{ message: string; subscription_valid_until: string }> => {
    const response = await apiClient.delete('/subscriptions/recurring/disable');
    return response.data;
  },
};
