import { useState, useEffect } from 'react';
import { Package, Users, UserCheck, TrendingUp, Clock, CheckCircle, XCircle, AlertCircle, Loader2, DollarSign } from 'lucide-react';
import { Card } from '@/shared/components/Card';
import { dashboardApi, type OverviewStatistics } from '@/lib/api';

export const AdminDashboardPage = () => {
  const [data, setData] = useState<OverviewStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const overview = await dashboardApi.getOverview();
        setData(overview);
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err);
        setError('Не удалось загрузить данные');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin" />
          <p className="text-gray-600">Загрузка данных...</p>
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

  const stats = [
    {
      label: 'Всего заказов',
      value: data.total_orders.toString(),
      subValue: `${data.completed_orders} завершено`,
      icon: <Package className="w-6 h-6" />,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      label: 'Активных курьеров',
      value: data.active_couriers.toString(),
      subValue: `${data.verified_couriers} верифицировано`,
      icon: <UserCheck className="w-6 h-6" />,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      label: 'Клиентов',
      value: data.total_clients.toString(),
      subValue: `${data.total_users} всего пользователей`,
      icon: <Users className="w-6 h-6" />,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
    {
      label: 'Средний рейтинг',
      value: data.avg_rating.toFixed(1),
      subValue: `${data.total_reviews} отзывов`,
      icon: <TrendingUp className="w-6 h-6" />,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-50',
    },
  ];

  const ordersByStatus = [
    { status: 'pending', label: 'Ожидают', count: data.pending_orders, icon: <Clock />, color: 'text-yellow-600', bgColor: 'bg-yellow-50' },
    { status: 'in_progress', label: 'В работе', count: data.in_progress_orders, icon: <AlertCircle />, color: 'text-blue-600', bgColor: 'bg-blue-50' },
    { status: 'completed', label: 'Завершены', count: data.completed_orders, icon: <CheckCircle />, color: 'text-green-600', bgColor: 'bg-green-50' },
    { status: 'cancelled', label: 'Отменены', count: data.cancelled_orders, icon: <XCircle />, color: 'text-red-600', bgColor: 'bg-red-50' },
  ];

  const revenueCards = [
    {
      label: 'Общий доход',
      value: `${data.total_revenue.toFixed(2)} BYN`,
      icon: <DollarSign className="w-6 h-6" />,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      label: 'Доход сегодня',
      value: `${data.revenue_today.toFixed(2)} BYN`,
      icon: <DollarSign className="w-6 h-6" />,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      label: 'Доход за месяц',
      value: `${data.revenue_this_month.toFixed(2)} BYN`,
      icon: <DollarSign className="w-6 h-6" />,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
    {
      label: 'Средний чек',
      value: `${data.avg_order_price.toFixed(2)} BYN`,
      icon: <Package className="w-6 h-6" />,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
    },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {}
      <div className="bg-white border-b border-gray-200">
        <div className="px-8 py-6">
          <h1 className="text-2xl font-bold text-gray-900">Панель управления</h1>
          <p className="text-gray-600 mt-1">Обзор системы EcoHaul</p>
        </div>
      </div>

      <div className="p-8 space-y-6">
        {}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((stat, index) => (
            <Card key={index} className="hover:shadow-lg transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p className="text-sm text-gray-600 mb-1">{stat.label}</p>
                  <p className="text-3xl font-bold text-gray-900 mb-2">{stat.value}</p>
                  <p className="text-xs text-gray-500">{stat.subValue}</p>
                </div>
                <div className={`${stat.bgColor} ${stat.color} p-3 rounded-lg`}>
                  {stat.icon}
                </div>
              </div>
            </Card>
          ))}
        </div>

        {}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Финансовая статистика</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {revenueCards.map((card, index) => (
              <Card key={index}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">{card.label}</p>
                    <p className="text-2xl font-bold text-gray-900">{card.value}</p>
                  </div>
                  <div className={`${card.bgColor} ${card.color} p-3 rounded-lg`}>
                    {card.icon}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Заказы по статусам</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {ordersByStatus.map((item) => (
              <Card key={item.status} className="hover:shadow-lg transition-shadow">
                <div className="flex items-center gap-4">
                  <div className={`${item.bgColor} ${item.color} p-3 rounded-lg`}>
                    {item.icon}
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">{item.label}</p>
                    <p className="text-2xl font-bold text-gray-900">{item.count}</p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {}
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Подписки</h2>
          <div className="grid grid-cols-3 gap-6">
            <div className="text-center">
              <p className="text-sm text-gray-600 mb-1">Всего активных</p>
              <p className="text-3xl font-bold text-gray-900">{data.active_subscriptions}</p>
            </div>
            <div className="text-center border-l border-gray-200">
              <p className="text-sm text-gray-600 mb-1">BASIC</p>
              <p className="text-3xl font-bold text-blue-600">{data.basic_subscriptions}</p>
            </div>
            <div className="text-center border-l border-gray-200">
              <p className="text-sm text-gray-600 mb-1">PREMIUM</p>
              <p className="text-3xl font-bold text-purple-600">{data.premium_subscriptions}</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};
