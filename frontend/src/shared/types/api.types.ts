export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

export interface OrderUpdateMessage {
  type: 'order_update';
  data: {
    order_id: string;
    status: string;
    courier_id?: string;
  };
}

export interface NotificationMessage {
  type: 'notification';
  data: {
    id: string;
    title: string;
    message: string;
  };
}
