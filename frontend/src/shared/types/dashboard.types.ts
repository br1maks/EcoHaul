export interface OverviewStatistics {
    total_users: number;
    total_clients: number;
    total_couriers: number;
    verified_couriers: number;
    active_couriers: number;

    total_orders: number;
    pending_orders: number;
    in_progress_orders: number;
    completed_orders: number;
    cancelled_orders: number;

    total_revenue: number;
    revenue_today: number;
    revenue_this_month: number;
    avg_order_price: number;

    active_subscriptions: number;
    basic_subscriptions: number;
    premium_subscriptions: number;

    total_reviews: number;
    avg_rating: number;
}
