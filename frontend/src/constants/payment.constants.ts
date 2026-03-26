import type { PaymentStatus, PaymentMethod, SubscriptionFrequency } from '@/shared/types';

export const PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = {
  pending: 'Ожидает оплаты',
  completed: 'Оплачено',
  failed: 'Ошибка оплаты',
  refunded: 'Возвращено',
};

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  card: 'Банковская карта',
  yandex_pay: 'ЮMoney',
  wallet: 'Кошелёк EcoHaul',
};

export const SUBSCRIPTION_FREQUENCY_LABELS: Record<SubscriptionFrequency, string> = {
  daily: 'Ежедневно',
  weekly: 'Еженедельно',
  monthly: 'Ежемесячно',
};

export const CURRENCY = 'BYN';
