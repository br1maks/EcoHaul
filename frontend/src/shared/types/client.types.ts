export interface ClientStatistics {
    id: string;
    first_name: string;
    last_name: string;
    phone: string | null;
    email: string | null;
    telegram_username: string | null;
    total_orders: number;
    completed_orders: number;
    cancelled_orders: number;
    total_spent: number;
    average_order_value: number;
    last_order_date: string | null;
    subscription_tier: string | null;
    is_active: boolean;
    created_at: string;
}

export interface ClientListResponse {
    items: ClientStatistics[];
    total: number;
    page: number;
    size: number;
    pages: number;
}
