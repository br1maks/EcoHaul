import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Package, MapPin, CheckCircle, RefreshCw, Loader2, Calendar, Timer } from 'lucide-react';
import { Card } from '@/shared/components/Card';
import { Badge } from '@/shared/components/Badge';
import { Button } from '@/shared/components/Button';
import { COURIER_ROUTES } from '@/constants/routes.constants';
import { courierApi } from '@/lib/api/courier';
import type { OrderResponse } from '@/shared/types';
import {
  ORDER_STATUS_LABELS,
  GARBAGE_TYPE_LABELS,
  GARBAGE_TYPE_ICONS,
  CURRENCY_SYMBOL
} from '@/constants';

export const CourierOrdersPage = () => {
  const navigate = useNavigate();
  const [filter, setFilter] = useState<'available' | 'my'>('available');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [availableOrders, setAvailableOrders] = useState<OrderResponse[]>([]);
  const [myOrders, setMyOrders] = useState<OrderResponse[]>([]);
  const [acceptingOrderId, setAcceptingOrderId] = useState<string | null>(null);

  const loadData = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const [available, deliveries] = await Promise.all([
        courierApi.getAvailableOrders().catch(() => []),
        courierApi.getMyDeliveries({ size: 50 }).catch(() => ({ items: [] })),
      ]);

      setAvailableOrders(available);
      setMyOrders(deliveries.items || []);
    } catch (err) {
      console.error('Failed to load orders:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const interval = setInterval(() => {
      loadData(true);
    }, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleAcceptOrder = async (orderId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      setAcceptingOrderId(orderId);
      await courierApi.acceptOrder(orderId);
      await loadData(true);
    } catch (err) {
      console.error('Failed to accept order:', err);
      alert('Не удалось принять заказ. Возможно, он уже занят.');
    } finally {
      setAcceptingOrderId(null);
    }
  };

  const formatTimeRemaining = (seconds?: number) => {
    if (!seconds || seconds <= 0) return null;
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}ч ${minutes}м`;
    }
    return `${minutes}м`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
    });
  };

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const orders = filter === 'available' ? availableOrders : myOrders;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 bg-gradient-to-br from-green-400 to-emerald-500 rounded-full flex items-center justify-center animate-pulse">
            <Loader2 className="w-8 h-8 text-white animate-spin" />
          </div>
          <span className="text-green-700 font-medium">Загрузка заказов...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
      {}
      <div className="bg-white/80 backdrop-blur-md border-b border-green-100 sticky top-0 z-10 shadow-sm">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-3">
            <h1 className="text-xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
              Заказы
            </h1>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => loadData(true)}
              disabled={refreshing}
              className="text-green-600"
            >
              <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
            </Button>
          </div>

          {}
          <div className="flex gap-2">
            <button
              onClick={() => setFilter('available')}
              className={`flex-1 px-4 py-2 rounded-xl font-medium transition-all ${
                filter === 'available'
                  ? 'bg-gradient-to-r from-green-500 to-emerald-500 text-white shadow-md'
                  : 'bg-white/50 text-gray-700 hover:bg-white'
              }`}
            >
              Доступные ({availableOrders.length})
            </button>
            <button
              onClick={() => setFilter('my')}
              className={`flex-1 px-4 py-2 rounded-xl font-medium transition-all ${
                filter === 'my'
                  ? 'bg-gradient-to-r from-green-500 to-emerald-500 text-white shadow-md'
                  : 'bg-white/50 text-gray-700 hover:bg-white'
              }`}
            >
              Мои ({myOrders.length})
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-3">
        {orders.length === 0 ? (
          <Card className="border-2 border-dashed border-gray-200">
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Package className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {filter === 'available' ? 'Нет доступных заказов' : 'У вас пока нет заказов'}
              </h3>
              <p className="text-gray-600 text-sm">
                {filter === 'available'
                  ? 'Новые заказы появятся здесь автоматически'
                  : 'Примите заказ из списка доступных'}
              </p>
            </div>
          </Card>
        ) : (
          orders.map((order) => {
            const isActive = ['ASSIGNED', 'IN_PROGRESS', 'ARRIVED'].includes(order.status);

            return (
              <Card
                key={order.id}
                className={`cursor-pointer hover:shadow-md transition-all ${
                  isActive
                    ? 'border-2 border-green-200 bg-green-50/50'
                    : filter === 'available'
                      ? 'border-2 border-orange-100 hover:border-orange-200'
                      : ''
                }`}
                onClick={() => navigate(`${COURIER_ROUTES.ORDER_DETAIL.replace(':id', order.id)}`)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">{GARBAGE_TYPE_ICONS[order.garbage_type]}</span>
                    <div>
                      <div className="font-semibold text-gray-900">
                        {GARBAGE_TYPE_LABELS[order.garbage_type]}
                      </div>
                      <div className="text-sm text-gray-600">{order.number_of_bags} мешков</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xl font-bold text-green-600">{order.final_price} {CURRENCY_SYMBOL}</div>
                    {order.priority > 0 && (
                      <Badge className="bg-purple-100 text-purple-700 text-xs">
                        Приоритет
                      </Badge>
                    )}
                  </div>
                </div>

                <div className="space-y-2 mb-3">
                  <div className="flex items-start gap-2 text-sm">
                    <MapPin className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                    <span className="text-gray-700">{order.pickup_address?.full_address || 'Адрес не указан'}</span>
                  </div>

                  {order.scheduled_time && (
                    <div className="flex items-center gap-2 text-sm">
                      <Calendar className="w-4 h-4 text-blue-500 flex-shrink-0" />
                      <span className="text-blue-700">
                        {formatDate(order.scheduled_time)} в {formatTime(order.scheduled_time)}
                      </span>
                    </div>
                  )}

                  {order.time_remaining_seconds && order.time_remaining_seconds > 0 && (
                    <div className="flex items-center gap-2 text-sm">
                      <Timer className="w-4 h-4 text-orange-500 flex-shrink-0" />
                      <span className="text-orange-700 font-medium">
                        Осталось: {formatTimeRemaining(order.time_remaining_seconds)}
                      </span>
                    </div>
                  )}

                  {filter === 'my' && (
                    <div className="flex items-center gap-2">
                      <Badge className={`${
                        isActive
                          ? 'bg-green-100 text-green-700'
                          : order.status === 'COMPLETED'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-gray-100 text-gray-700'
                      }`}>
                        {ORDER_STATUS_LABELS[order.status]}
                      </Badge>
                    </div>
                  )}
                </div>

                {filter === 'available' && (
                  <Button
                    variant="primary"
                    className="w-full bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600"
                    onClick={(e) => handleAcceptOrder(order.id, e)}
                    disabled={acceptingOrderId === order.id}
                  >
                    {acceptingOrderId === order.id ? (
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    ) : (
                      <CheckCircle className="w-4 h-4 mr-2" />
                    )}
                    Принять заказ
                  </Button>
                )}

                {filter === 'my' && isActive && (
                  <div className="flex items-center gap-2 text-sm text-green-600 font-medium">
                    <CheckCircle className="w-4 h-4" />
                    В работе
                  </div>
                )}
              </Card>
            );
          })
        )}
      </div>

      {}
      {filter === 'available' && orders.length > 0 && (
        <div className="max-w-2xl mx-auto px-4 pb-6">
          <Card className="bg-gradient-to-br from-blue-50 to-cyan-50 border-2 border-blue-100">
            <div className="flex gap-3">
              <div className="text-3xl">💡</div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 mb-1">Совет</h3>
                <p className="text-sm text-gray-700">
                  Заказы с высоким приоритетом (срочные) приносят больше баллов для рейтинга
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};
