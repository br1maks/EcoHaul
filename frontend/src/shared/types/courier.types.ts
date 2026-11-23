export type ShiftStatus = 'scheduled' | 'active' | 'completed' | 'cancelled';

export interface CourierShift {
  id: string;
  courier_id: string;
  start_time: string;
  end_time: string;
  status: ShiftStatus;
  service_zone_id?: string;
  created_at: string;
}

export interface ServiceZone {
  id: string;
  name: string;
  city: string;
  coordinates: string; 
  is_active: boolean;
}

export interface Review {
  id: string;
  reviewer_id: string;
  reviewee_id: string;
  order_id: string;
  moderated_by_id: string | null;
  reviewer_role: string;
  rating: number;
  comment: string | null;
  response: string | null;
  is_visible: boolean;
  is_anonymous: boolean;
  moderation_note: string | null;
  moderated_at: string | null;
  responded_at: string | null;
  created_at: string;
  updated_at: string;
  
  is_positive: boolean;
  is_neutral: boolean;
  is_negative: boolean;
  has_comment: boolean;
  has_response: boolean;
  is_client_review: boolean;
  is_courier_review: boolean;
  is_moderated: boolean;
}

export interface CreateReviewData {
  reviewee_id: string;
  order_id: string;
  rating: number;
  comment?: string;
  is_anonymous?: boolean;
}

export interface UpdateReviewData {
  rating?: number;
  comment?: string;
  response?: string;
  is_visible?: boolean;
  is_anonymous?: boolean;
}

import type { CourierStatus } from './user.types';

export interface CourierStatistics {
  id: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  email: string | null;
  rating: number;
  courier_status: CourierStatus;
  is_verified: boolean;
  is_active: boolean;
  total_orders: number;
  completed_orders: number;
  active_shift_id: string | null;
  shifts_this_month: number;
  total_hours_this_month: number;
  orders_this_month: number;
}

export interface CourierListResponse {
  items: CourierStatistics[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
