import { useState, useEffect } from 'react';
import { Card } from '@/shared/components/Card';
import { statisticsApi, type AnalyticsData } from '@/lib/api';

import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Package,
  Users,
  UserCheck,
  Star,
  Calendar,
  BarChart3,
  PieChart,
  Loader2,
  AlertCircle
} from 'lucide-react';

export const AdminAnalyticsPage = () => {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        setError(null);
        const analyticsData = await statisticsApi.getAnalytics();
        setData(analyticsData);
      } catch (err) {
        console.error('Failed to fetch analytics:', err);
        setError('Не удалось загрузить данные аналитики');
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin" />
          <p className="text-gray-600">Загрузка аналитики...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-red-600" />
          <h2 className="text-xl font-semibold text-gray-900">Ошибка загрузки</h2>
          <p className="text-gray-600">{error || 'Не удалось загрузить данные'}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Попробовать снова
          </button>
        </div>
      </div>
    );
  }

  const garbageTypeColors: Record<string, string> = {
    'HOUSEHOLD': 'bg-blue-500',
    'CONSTRUCTION': 'bg-orange-500',
  };

  const garbageTypeStats = data.garbage_type_stats.map((item) => ({
    type: item.garbage_type_label,
    count: item.count,
    revenue: item.revenue,
    percentage: item.percentage,
    color: garbageTypeColors[item.garbage_type] || 'bg-gray-500',
  }));

  const topCouriers = data.top_couriers.map((courier) => ({
    id: courier.courier_id,
    name: courier.courier_name,
    orders: courier.completed_orders,
    rating: courier.avg_rating,
    revenue: courier.total_revenue,
  }));

  const topClients = data.top_clients.map((client) => ({
    id: client.client_id,
    name: client.client_name,
    orders: client.total_orders,
    spent: client.total_spent,
  }));

  const ordersByMonth = data.orders_by_month.map((item) => ({
    month: item.month,
    orders: item.orders,
    revenue: item.revenue,
  }));

  const maxOrders = Math.max(...ordersByMonth.map((m) => m.orders), 1);
  const maxRevenue = Math.max(...ordersByMonth.map((m) => m.revenue), 1);

  const getTrendIcon = (change: number) => {
    if (change > 0) {
      return <TrendingUp className="w-4 h-4 text-green-600" />;
    }
    return <TrendingDown className="w-4 h-4 text-red-600" />;
  };

  const getTrendColor = (change: number) => {
    if (change > 0) return 'text-green-600';
    return 'text-red-600';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {}
      <div className="bg-white border-b border-gray-200">
        <div className="px-8 py-6">
          <h1 className="text-2xl font-bold text-gray-900">Аналитика</h1>
          <p className="text-gray-600 mt-1">Статистика и отчёты за последние 6 месяцев</p>
        </div>
      </div>

      <div className="p-8 space-y-6">
        {}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600 mb-1">Общий доход</div>
                <div className="text-2xl font-bold text-gray-900">
                  {data.total_revenue.toFixed(2)} BYN
                </div>
              </div>
              <DollarSign className="w-10 h-10 text-green-600" />
            </div>
            <div className="flex items-center gap-2 mt-2">
              {getTrendIcon(data.revenue_change)}
              <span className={`text-sm font-medium ${getTrendColor(data.revenue_change)}`}>
                {data.revenue_change > 0 ? '+' : ''}{data.revenue_change}% за месяц
              </span>
            </div>
          </Card>

          <Card>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600 mb-1">Всего заказов</div>
                <div className="text-2xl font-bold text-gray-900">{data.total_orders}</div>
              </div>
              <Package className="w-10 h-10 text-blue-600" />
            </div>
            <div className="flex items-center gap-2 mt-2">
              {getTrendIcon(data.orders_change)}
              <span className={`text-sm font-medium ${getTrendColor(data.orders_change)}`}>
                {data.orders_change > 0 ? '+' : ''}{data.orders_change}% за месяц
              </span>
            </div>
          </Card>

          <Card>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600 mb-1">Всего клиентов</div>
                <div className="text-2xl font-bold text-gray-900">{data.total_clients}</div>
              </div>
              <Users className="w-10 h-10 text-purple-600" />
            </div>
            <div className="flex items-center gap-2 mt-2">
              {getTrendIcon(data.clients_change)}
              <span className={`text-sm font-medium ${getTrendColor(data.clients_change)}`}>
                {data.clients_change > 0 ? '+' : ''}{data.clients_change}% за месяц
              </span>
            </div>
          </Card>

          <Card>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600 mb-1">Активных курьеров</div>
                <div className="text-2xl font-bold text-gray-900">{data.total_couriers}</div>
              </div>
              <UserCheck className="w-10 h-10 text-indigo-600" />
            </div>
            <div className="flex items-center gap-2 mt-2">
              {getTrendIcon(data.couriers_change)}
              <span className={`text-sm font-medium ${getTrendColor(data.couriers_change)}`}>
                {data.couriers_change > 0 ? '+' : ''}{data.couriers_change}% за месяц
              </span>
            </div>
          </Card>

          <Card>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600 mb-1">Средний чек</div>
                <div className="text-2xl font-bold text-gray-900">
                  {data.avg_order_value.toFixed(2)} BYN
                </div>
              </div>
              <DollarSign className="w-10 h-10 text-yellow-600" />
            </div>
            <div className="flex items-center gap-2 mt-2">
              {getTrendIcon(data.avg_order_value_change)}
              <span className={`text-sm font-medium ${getTrendColor(data.avg_order_value_change)}`}>
                {data.avg_order_value_change > 0 ? '+' : ''}{data.avg_order_value_change}% за месяц
              </span>
            </div>
          </Card>

          <Card>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600 mb-1">Процент выполнения</div>
                <div className="text-2xl font-bold text-gray-900">{data.completion_rate}%</div>
              </div>
              <Star className="w-10 h-10 text-orange-600" />
            </div>
            <div className="flex items-center gap-2 mt-2">
              {getTrendIcon(data.completion_rate_change)}
              <span className={`text-sm font-medium ${getTrendColor(data.completion_rate_change)}`}>
                {data.completion_rate_change > 0 ? '+' : ''}{data.completion_rate_change}% за месяц
              </span>
            </div>
          </Card>
        </div>

        {}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {}
          <Card>
            <div className="flex items-center gap-2 mb-6">
              <BarChart3 className="w-5 h-5 text-gray-600" />
              <h2 className="text-lg font-semibold text-gray-900">Заказы по месяцам</h2>
            </div>
            <div className="space-y-4">
              {ordersByMonth.map((item) => (
                <div key={item.month}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-gray-400" />
                      <span className="text-sm font-medium text-gray-700">{item.month}</span>
                    </div>
                    <div className="text-sm text-gray-600">
                      {item.orders} заказов • {item.revenue.toFixed(0)} BYN
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <div className="flex-1">
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 rounded-full"
                          style={{ width: `${(item.orders / maxOrders) * 100}%` }}
                        />
                      </div>
                    </div>
                    <div className="flex-1">
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-green-500 rounded-full"
                          style={{ width: `${(item.revenue / maxRevenue) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              <div className="flex items-center justify-center gap-6 pt-4 border-t border-gray-200">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-blue-500 rounded-full" />
                  <span className="text-xs text-gray-600">Заказы</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-green-500 rounded-full" />
                  <span className="text-xs text-gray-600">Доход</span>
                </div>
              </div>
            </div>
          </Card>

          {}
          <Card>
            <div className="flex items-center gap-2 mb-6">
              <PieChart className="w-5 h-5 text-gray-600" />
              <h2 className="text-lg font-semibold text-gray-900">Распределение по типу мусора</h2>
            </div>
            <div className="space-y-4">
              {garbageTypeStats.map((item) => (
                <div key={item.type}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className={`w-3 h-3 ${item.color} rounded-full`} />
                      <span className="text-sm font-medium text-gray-700">{item.type}</span>
                    </div>
                    <div className="text-sm text-gray-600">
                      {item.count} ({item.percentage}%)
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${item.color} rounded-full`}
                        style={{ width: `${item.percentage}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium text-gray-900 min-w-20 text-right">
                      {item.revenue.toFixed(0)} BYN
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {}
          <Card>
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-gray-600" />
              Топ курьеров
            </h2>
            <div className="space-y-3">
              {topCouriers.map((courier, index) => (
                <div
                  key={courier.id}
                  className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center justify-center w-8 h-8 bg-white rounded-full border-2 border-blue-500">
                    <span className="text-sm font-bold text-blue-600">#{index + 1}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-gray-900">{courier.name}</div>
                    <div className="flex items-center gap-4 text-xs text-gray-600">
                      <span>{courier.orders} заказов</span>
                      <span className="flex items-center gap-1">
                        <Star className="w-3 h-3 text-yellow-500 fill-yellow-500" />
                        {courier.rating}
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-green-600">{courier.revenue.toFixed(0)} BYN</div>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {}
          <Card>
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Users className="w-5 h-5 text-gray-600" />
              Топ клиентов
            </h2>
            <div className="space-y-3">
              {topClients.map((client, index) => (
                <div
                  key={client.id}
                  className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center justify-center w-8 h-8 bg-white rounded-full border-2 border-purple-500">
                    <span className="text-sm font-bold text-purple-600">#{index + 1}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-gray-900">{client.name}</div>
                    <div className="text-xs text-gray-600">{client.orders} заказов</div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-green-600">{client.spent.toFixed(0)} BYN</div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
