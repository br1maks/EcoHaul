export type PaymentStatus = 'pending' | 'completed' | 'failed' | 'refunded';
export type PaymentMethod = 'card' | 'yandex_pay' | 'wallet';

export interface Payment {
  id: string;
  user_id: string;
  order_id?: string;
  amount: number;
  status: PaymentStatus;
  payment_method: PaymentMethod;
  transaction_id?: string;
  created_at: string;
}

export interface Wallet {
  id: string;
  user_id: string;
  balance: number;
  currency: string;
  updated_at: string;
}

export type TransactionType = 'deposit' | 'withdrawal' | 'payment' | 'refund' | 'bonus';

export interface WalletTransaction {
  id: string;
  wallet_id: string;
  amount: number;
  type: TransactionType;
  description?: string;
  order_id?: string;
  created_at: string;
}

export interface CreatePaymentData {
  order_id?: string;
  amount: number;
  payment_method: PaymentMethod;
}
