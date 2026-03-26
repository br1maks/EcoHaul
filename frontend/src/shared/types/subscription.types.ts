
export type SubscriptionTier = 'FREE' | 'BASIC' | 'PREMIUM';

export type SubscriptionFrequency = 'daily' | 'weekly' | 'monthly';

export interface Subscription {
  id: string;
  user_id: string;
  tier: SubscriptionTier;
  start_date: string;
  end_date: string;
  renewed_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;

  is_expired: boolean;
  is_valid: boolean;
  discount_percentage: number;
  days_remaining: number;
  is_expiring_soon: boolean;
}

export interface SubscriptionPlan {
  tier: SubscriptionTier;
  name: string;
  description: string;
  discount_percentage: number;
  price_per_month: number;
  features: string[];
}

export interface SubscriptionPurchaseData {
  tier: SubscriptionTier;
  duration_months: number;
}

export interface SubscriptionPurchaseResponse {
  payment_id: string;
  payment_url: string;
  amount: number;
  tier: SubscriptionTier;
  duration_months: number;
}
