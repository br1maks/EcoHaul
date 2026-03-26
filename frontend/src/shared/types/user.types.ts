export type UserRole = 'CLIENT' | 'COURIER' | 'ADMIN';
export type CourierStatus = 'ACTIVE' | 'OFFLINE' | 'ON_BREAK' | 'NOT_AVAILABLE';

export interface User {
  id: string;
  telegram_id: number;
  telegram_username?: string;
  phone?: string;
  email?: string;
  first_name: string;
  last_name: string;
  age?: number;
  role: UserRole;
  courier_status?: CourierStatus;
  rating: number;
  total_orders: number;
  completed_orders: number;
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
}

export interface UserUpdateData {
  first_name?: string;
  last_name?: string;
  phone?: string;
  email?: string;
  age?: number;
  password?: string;
}
