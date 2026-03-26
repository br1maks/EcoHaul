export type NotificationType =
  | 'order_created'
  | 'order_confirmed'
  | 'courier_assigned'
  | 'order_completed'
  | 'payment_completed'
  | 'subscription_reminder';

export interface Notification {
  id: string;
  user_id: string;
  type: NotificationType;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface WsMessage {
  type: string;
  data: Record<string, unknown>;
}
