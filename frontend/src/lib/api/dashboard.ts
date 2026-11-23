import { apiClient } from './client';
import type { OverviewStatistics } from '@/shared/types';

export const dashboardApi = {
    getOverview: async (): Promise<OverviewStatistics> => {
        const response = await apiClient.get('/admin/statistics/overview');
        return response.data;
    },
};