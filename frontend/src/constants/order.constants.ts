import type { OrderStatus, GarbageType } from '@/shared/types';

export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  PENDING: 'Ожидает',
  ASSIGNED: 'Назначен',
  IN_PROGRESS: 'В работе',
  ARRIVED: 'Прибыл',
  COMPLETED: 'Завершён',
  CANCELLED: 'Отменён',
  FAILED: 'Неудачный',
};

export const ORDER_STATUS_COLORS: Record<OrderStatus, string> = {
  PENDING: 'text-yellow-600 bg-yellow-50',
  ASSIGNED: 'text-blue-600 bg-blue-50',
  IN_PROGRESS: 'text-indigo-600 bg-indigo-50',
  ARRIVED: 'text-purple-600 bg-purple-50',
  COMPLETED: 'text-green-600 bg-green-50',
  CANCELLED: 'text-red-600 bg-red-50',
  FAILED: 'text-red-600 bg-red-50',
};

export const GARBAGE_TYPE_LABELS: Record<GarbageType, string> = {
  HOUSEHOLD: 'Бытовой',
  CONSTRUCTION: 'Строительный',
};

export const GARBAGE_TYPE_ICONS: Record<GarbageType, string> = {
  HOUSEHOLD: '🏠',
  CONSTRUCTION: '🏗️',
};

export const GARBAGE_TYPE_COLORS: Record<GarbageType, string> = {
  HOUSEHOLD: 'bg-blue-100 text-blue-700',
  CONSTRUCTION: 'bg-orange-100 text-orange-700',
};

export const CURRENCY_SYMBOL = 'BYN';
