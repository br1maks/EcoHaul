import { apiClient } from './client';
import type { Review, CreateReviewData } from '@/shared/types';

export const reviewsApi = {
  /**
   * Создать отзыв о курьере
   */
  create: async (data: CreateReviewData): Promise<Review> => {
    const response = await apiClient.post<Review>('/reviews', data);
    return response.data;
  },

  /**
   * Получить мои отзывы (которые я оставил)
   */
  getMyReviews: async (limit = 20, offset = 0): Promise<Review[]> => {
    const response = await apiClient.get<Review[]>('/reviews/my-reviews', { params: { limit, offset } });
    return response.data;
  },

  /**
   * Получить отзывы о курьере (публичный)
   */
  getCourierReviews: async (courierId: string, limit = 20, offset = 0): Promise<Review[]> => {
    const response = await apiClient.get<Review[]>(`/reviews/courier/${courierId}`, {
      params: { limit, offset }
    });
    return response.data;
  },

  /**
   * Проверить, оставлен ли отзыв на заказ
   */
  checkOrderReview: async (orderId: string): Promise<Review | null> => {
    try {
      const reviews = await reviewsApi.getMyReviews(100, 0);
      return reviews.find(r => r.order_id === orderId) || null;
    } catch {
      return null;
    }
  },
};
