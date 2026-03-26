
export interface TopCourier {
  courier_id: string;
  courier_name: string;
  total_orders: number;
  completed_orders: number;
  total_revenue: number;
  avg_rating: number;
}

export interface TopClient {
  client_id: string;
  client_name: string;
  total_orders: number;
  total_spent: number;
}

export interface MonthlyStats {
  month: string;
  orders: number;
  revenue: number;
}

export interface GarbageTypeStats {
  garbage_type: string;
  garbage_type_label: string;
  count: number;
  revenue: number;
  percentage: number;
}

export interface AnalyticsData {
  
  total_revenue: number;
  revenue_change: number;
  total_orders: number;
  orders_change: number;
  total_clients: number;
  clients_change: number;
  total_couriers: number;
  couriers_change: number;
  avg_order_value: number;
  avg_order_value_change: number;
  completion_rate: number;
  completion_rate_change: number;

  orders_by_month: MonthlyStats[];

  garbage_type_stats: GarbageTypeStats[];

  top_couriers: TopCourier[];
  top_clients: TopClient[];
}
