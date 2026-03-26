
export type OrderStatus =
  | 'PENDING'
  | 'ASSIGNED'
  | 'IN_PROGRESS'
  | 'ARRIVED'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'FAILED';

export type GarbageType =
  | 'HOUSEHOLD'
  | 'CONSTRUCTION';

export interface PickupAddress {
  id: string;
  full_address: string;
  city: string;
  district: string;
  street: string;
  house_number: string;
  apartment: string | null;
  entrance: number | null;
  floor: number | null;
  notes: string | null;
  latitude: number;
  longitude: number;
}

export interface OrderResponse {
  id: string;
  client_id: string;
  courier_id: string | null;
  pickup_address_id: string;
  pickup_address: PickupAddress | null;
  garbage_type: GarbageType;
  number_of_bags: number;
  description: string | null;
  status: OrderStatus;
  price_before_discount: number;
  discount_amount: number;
  final_price: number;
  subscription_tier_used: string | null;
  scheduled_time: string | null;
  priority: number;
  expires_at: string | null;
  accepted_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  created_at: string;
  is_expired: boolean;
  time_remaining_seconds: number | null;
  client_phone: string | null;
  client_phone_display: string | null;
  client_telegram_link: string | null;

  courier_phone: string | null;
  courier_phone_display: string | null;
  courier_telegram_link: string | null;
}

export interface OrderListResponse {
  items: OrderResponse[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface OrderCreate {
  pickup_address_id: string;
  garbage_type: GarbageType;
  number_of_bags: number;
  description?: string;
  scheduled_time?: string;
}

export interface OrderStatusUpdate {
  status: OrderStatus;
}

export interface OrderCancel {
  reason?: string;
}

export type Order = OrderResponse;
export type CreateOrderData = OrderCreate;
export type UpdateOrderData = OrderStatusUpdate;
