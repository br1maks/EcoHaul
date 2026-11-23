import { apiClient } from './client';
import type {
  AnalyticsData,
  TopClient,
  TopCourier,
  MonthlyStats,
  GarbageTypeStats,
} from '@/shared/types';

/**
 * Admin Statistics API endpoints
 */
export const statisticsApi = {
  /**
   * Получить полную аналитику (главный endpoint)
   * GET /admin/statistics/analytics
   */
  getAnalytics: async (): Promise<AnalyticsData> => {
    const response = await apiClient.get('/admin/statistics/analytics');
    return response.data;
  },

  /**
   * Получить топ клиентов по расходам
   * GET /admin/statistics/top-clients
   */
  getTopClients: async (limit: number = 10): Promise<TopClient[]> => {
    const response = await apiClient.get('/admin/statistics/top-clients', {
      params: { limit },
    });
    return response.data;
  },

  /**
   * Получить топ курьеров по доходу
   * GET /admin/statistics/top-couriers
   */
  getTopCouriers: async (limit: number = 10): Promise<TopCourier[]> => {
    const response = await apiClient.get('/admin/statistics/top-couriers', {
      params: { limit },
    });
    return response.data;
  },

  /**
   * Получить статистику по месяцам
   * GET /admin/statistics/monthly
   */
  getMonthlyStats: async (months: number = 6): Promise<MonthlyStats[]> => {
    const response = await apiClient.get('/admin/statistics/monthly', {
      params: { months },
    });
    return response.data;
  },

  /**
   * Получить распределение по типу мусора
   * GET /admin/statistics/garbage-types
   */
  getGarbageTypeStats: async (): Promise<GarbageTypeStats[]> => {
    const response = await apiClient.get('/admin/statistics/garbage-types');
    return response.data;
  },
};
