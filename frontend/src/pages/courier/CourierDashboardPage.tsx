import { useRealtimeRefresh } from '@/shared/hooks/useRealtimeRefresh';
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { courierApi } from '@/lib/api/courier';
import type { CourierShift } from '@/lib/api/courier';
import { usersApi } from '@/lib/api/users';
import type { OrderResponse, User } from '@/shared/types';
import { Card } from '@/shared/components/Card';
import { Button } from '@/shared/components/Button';
import { Badge } from '@/shared/components/Badge';
import { NotificationBell } from '@/shared/components/NotificationBell';
import {
  Package,
  MapPin,
  Star,
  Play,
  Square,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle,
  Truck,
  Calendar,
  ChevronRight,
  Zap,
  TrendingUp,
  Timer,
  Coffee
} from 'lucide-react';
import {
  ORDER_STATUS_LABELS,
  GARBAGE_TYPE_LABELS,
  GARBAGE_TYPE_ICONS,
  CURRENCY_SYMBOL
} from '@/constants';
import { COURIER_ROUTES } from '@/constants/routes.constants';

type CourierStatus = 'ACTIVE' | 'OFFLINE' | 'ON_BREAK' | 'NOT_AVAILABLE';

const COURIER_STATUS_LABELS: Record<CourierStatus, string> = {
  ACTIVE: 'На линии',
  OFFLINE: 'Офлайн',
  ON_BREAK: 'На перерыве',
  NOT_AVAILABLE: 'Недоступен',
};

const COURIER_STATUS_COLORS: Record<CourierStatus, string> = {
  ACTIVE: 'bg-green-100 text-green-700 border-green-200',
  OFFLINE: 'bg-gray-100 text-gray-700 border-gray-200',
  ON_BREAK: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  NOT_AVAILABLE: 'bg-red-100 text-red-700 border-red-200',
};

export const CourierDashboardPage = () => {
  const navigate = useNavigate();

  const [courier, setCourier] = useState<User | null>(null);
  const [availableOrders, setAvailableOrders] = useState<OrderResponse[]>([]);
  const [myDeliveries, setMyDeliveries] = useState<OrderResponse[]>([]);
  const [activeShift, setActiveShift] = useState<CourierShift | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [acceptingOrderId, setAcceptingOrderId] = useState<string | null>(null);
  const [togglingShift, setTogglingShift] = useState(false);
  const [changingStatus, setChangingStatus] = useState(false);
  const [shiftDuration, setShiftDuration] = useState('0ч 0м');

  const loadData = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const [courierData, available, deliveries, shift] = await Promise.all([
        usersApi.getMe(),
        courierApi.getAvailableOrders().catch(() => []),
        courierApi.getMyDeliveries({ size: 10 }).catch(() => ({ items: [] })),
        courierApi.getActiveShift().catch(() => null),
      ]);

      setCourier(courierData);
      setAvailableOrders(available);
      setMyDeliveries(deliveries.items || []);
      setActiveShift(shift);
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Ошибка загрузки данных');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const refreshData = useCallback(() => loadData(true), [loadData]);
  useRealtimeRefresh(refreshData);

  useEffect(() => {
    if (!activeShift) {
      setShiftDuration('0ч 0м');
      return;
    }

    const updateDuration = () => {
      const start = new Date(activeShift.started_at);
      const now = new Date();
      const diff = Math.max(0, Math.floor((now.getTime() - start.getTime()) / 1000 / 60));
      const hours = Math.floor(diff / 60);
      const minutes = diff % 60;
      setShiftDuration(`${hours}ч ${minutes}м`);
    };

    updateDuration();
    const interval = setInterval(updateDuration, 60000);
    return () => clearInterval(interval);
  }, [activeShift]);

  const handleAcceptOrder = async (orderId: string) => {
    try {
      setAcceptingOrderId(orderId);
      await courierApi.acceptOrder(orderId);
      await loadData(true);
    } catch (err) {
      console.error('Failed to accept order:', err);
      alert('Не удалось принять заказ');
    } finally {
      setAcceptingOrderId(null);
    }
  };

  const handleToggleShift = async () => {
    try {
      setTogglingShift(true);
      if (activeShift) {
        await courierApi.endShift();
        setActiveShift(null);
      } else {
        const newShift = await courierApi.startShift();
        setActiveShift(newShift);
      }
      await loadData(true);
    } catch (err) {
      console.error('Failed to toggle shift:', err);
      alert('Не удалось изменить статус смены');
    } finally {
      setTogglingShift(false);
    }
  };

  const handleStatusChange = async (newStatus: CourierStatus) => {
    if (changingStatus) return;
    try {
      setChangingStatus(true);
      await courierApi.updateStatus(newStatus);
      setCourier(prev => prev ? { ...prev, courier_status: newStatus } : null);
    } catch (err) {
      console.error('Failed to change status:', err);
      alert('Не удалось изменить статус');
    } finally {
      setChangingStatus(false);
    }
  };

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
    });
  };

  const activeDeliveries = myDeliveries.filter(o =>
    ['ASSIGNED', 'IN_PROGRESS', 'ARRIVED'].includes(o.status)
  );

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 bg-gradient-to-br from-green-400 to-emerald-500 rounded-full flex items-center justify-center animate-pulse">
            <Loader2 className="w-8 h-8 text-white animate-spin" />
          </div>
          <span className="text-green-700 font-medium">Загрузка...</span>
        </div>
      </div>
    );
  }

  if (error && !courier) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
        <div className="text-center p-6">
          <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-10 h-10 text-red-500" />
          </div>
          <div className="text-red-500 text-xl font-bold mb-2">Ошибка</div>
          <div className="text-gray-600 mb-4">{error}</div>
          <Button onClick={() => loadData()}>Попробовать снова</Button>
        </div>
      </div>
    );
  }

  const courierStatus = (courier?.courier_status as CourierStatus) || 'OFFLINE';

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50 pb-24">
      {}
      <div className="bg-white/80 backdrop-blur-md border-b border-green-100 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                Привет, {courier?.first_name}!
              </h1>
              <div className="flex items-center gap-2 mt-1">
                <Badge className={COURIER_STATUS_COLORS[courierStatus]}>
                  {COURIER_STATUS_LABELS[courierStatus]}
                </Badge>
                <div className="flex items-center gap-1 text-sm text-gray-500">
                  <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                  <span>{courier?.rating?.toFixed(1) || '—'}</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => loadData(true)}
                disabled={refreshing}
                className="text-green-600"
              >
                <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
              </Button>
              <NotificationBell />
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {}
        <Card className="border-2 border-green-100">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-900">Мой статус</h2>
            {changingStatus && <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />}
          </div>
          <div className="bg-gray-100/80 rounded-2xl p-1 flex gap-1">
            {([
              { status: 'ACTIVE' as CourierStatus, label: 'На линии', dot: 'bg-green-500' as string | undefined, icon: undefined as React.ReactNode, activeClass: 'text-green-700', activeBg: 'bg-white' },
              { status: 'ON_BREAK' as CourierStatus, label: 'Перерыв', dot: undefined as string | undefined, icon: <Coffee className="w-3.5 h-3.5" /> as React.ReactNode, activeClass: 'text-amber-700', activeBg: 'bg-white' },
              { status: 'OFFLINE' as CourierStatus, label: 'Офлайн', dot: 'bg-gray-400' as string | undefined, icon: undefined as React.ReactNode, activeClass: 'text-gray-700', activeBg: 'bg-white' },
            ]).map(({ status, label, dot, icon, activeClass, activeBg }) => {
              const isActive = courierStatus === status;
              return (
                <button
                  key={status}
                  onClick={() => handleStatusChange(status)}
                  disabled={changingStatus}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? `${activeBg} shadow-sm ${activeClass}`
                      : 'text-gray-400 hover:text-gray-600 active:bg-white/50'
                  }`}
                >
                  {icon ?? (
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dot} ${isActive && status === 'ACTIVE' ? 'animate-pulse' : ''}`} />
                  )}
                  {label}
                </button>
              );
            })}
          </div>
        </Card>

        {}
        <Card className="bg-gradient-to-br from-green-500 to-emerald-600 text-white border-0 shadow-xl shadow-green-200/50">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-green-100 text-sm mb-1">Текущая смена</div>
              {activeShift ? (
                <>
                  <div className="text-2xl font-bold">{shiftDuration}</div>
                  <div className="text-green-100 text-sm mt-1">
                    Начало: {formatTime(activeShift.started_at)}
                  </div>
                </>
              ) : (
                <div className="text-xl font-semibold">Смена не начата</div>
              )}
            </div>
            <Button
              onClick={handleToggleShift}
              disabled={togglingShift}
              className={`${
                activeShift
                  ? 'bg-red-500 hover:bg-red-600'
                  : 'bg-white text-green-600 hover:bg-green-50'
              } shadow-lg`}
            >
              {togglingShift ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : activeShift ? (
                <>
                  <Square className="w-5 h-5 mr-2" />
                  Завершить
                </>
              ) : (
                <>
                  <Play className="w-5 h-5 mr-2" />
                  Начать смену
                </>
              )}
            </Button>
          </div>
        </Card>

        {}
        <div className="grid grid-cols-3 gap-3">
          <Card className="text-center border-2 border-green-100">
            <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-2">
              <Package className="w-5 h-5 text-green-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">{courier?.completed_orders || 0}</div>
            <div className="text-xs text-gray-500">Выполнено</div>
          </Card>

          <Card className="text-center border-2 border-emerald-100">
            <div className="w-10 h-10 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-2">
              <TrendingUp className="w-5 h-5 text-emerald-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">{courier?.total_orders || 0}</div>
            <div className="text-xs text-gray-500">Всего</div>
          </Card>

          <Card className="text-center border-2 border-teal-100">
            <div className="w-10 h-10 bg-teal-100 rounded-full flex items-center justify-center mx-auto mb-2">
              <Star className="w-5 h-5 text-teal-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">{courier?.rating?.toFixed(1) || '—'}</div>
            <div className="text-xs text-gray-500">Рейтинг</div>
          </Card>
        </div>

        {}
        {activeDeliveries.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Truck className="w-5 h-5 text-green-600" />
              <h2 className="text-lg font-bold text-gray-900">Активные доставки</h2>
              <Badge className="bg-green-100 text-green-700">{activeDeliveries.length}</Badge>
            </div>
            <div className="space-y-3">
              {activeDeliveries.map((order) => (
                <Card
                  key={order.id}
                  className="border-2 border-green-200 bg-green-50/50 cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => navigate(`/courier/orders/${order.id}`)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge className="bg-green-100 text-green-700">
                          {ORDER_STATUS_LABELS[order.status]}
                        </Badge>
                        <span className="text-sm text-gray-500">
                          #{order.id.slice(0, 8)}
                        </span>
                      </div>
                      <div className="flex items-start gap-2 text-sm text-gray-600 mb-1">
                        <MapPin className="w-4 h-4 mt-0.5 text-green-500 shrink-0" />
                        <span>{order.pickup_address?.full_address || 'Адрес не указан'}</span>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-gray-500">
                        <span className="flex items-center gap-1">
                          <span>{GARBAGE_TYPE_ICONS[order.garbage_type]}</span>
                          {order.number_of_bags} мешк.
                        </span>
                        <span className="font-semibold text-green-600">
                          {order.final_price} {CURRENCY_SYMBOL}
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}

        {}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-orange-500" />
              <h2 className="text-lg font-bold text-gray-900">Доступные заказы</h2>
              {availableOrders.length > 0 && (
                <Badge className="bg-orange-100 text-orange-700">{availableOrders.length}</Badge>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate(COURIER_ROUTES.ORDERS)}
              className="text-green-600"
            >
              Все
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>

          {availableOrders.length === 0 ? (
            <Card className="text-center py-8 border-2 border-dashed border-gray-200">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Package className="w-8 h-8 text-gray-400" />
              </div>
              <div className="text-gray-500 font-medium mb-1">Нет доступных заказов</div>
              <div className="text-sm text-gray-400">
                Новые заказы появятся здесь
              </div>
            </Card>
          ) : (
            <div className="space-y-3">
              {availableOrders.slice(0, 3).map((order) => (
                <Card
                  key={order.id}
                  className="border-2 border-orange-100 hover:border-orange-200 transition-colors"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-sm font-medium text-gray-700">
                          #{order.id.slice(0, 8)}
                        </span>
                        {order.priority > 0 && (
                          <Badge className="bg-purple-100 text-purple-700">
                            Приоритет
                          </Badge>
                        )}
                        {order.scheduled_time && (
                          <Badge className="bg-blue-100 text-blue-700">
                            <Calendar className="w-3 h-3 mr-1" />
                            {formatDate(order.scheduled_time)}
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-start gap-2 text-sm text-gray-600 mb-2">
                        <MapPin className="w-4 h-4 mt-0.5 text-orange-500 shrink-0" />
                        <span>{order.pickup_address?.full_address || 'Адрес не указан'}</span>
                      </div>
                      <div className="flex items-center gap-4 text-sm">
                        <span className="flex items-center gap-1 text-gray-500">
                          <span>{GARBAGE_TYPE_ICONS[order.garbage_type]}</span>
                          {GARBAGE_TYPE_LABELS[order.garbage_type]}
                        </span>
                        <span className="text-gray-500">
                          {order.number_of_bags} мешк.
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold text-green-600">
                        {order.final_price} {CURRENCY_SYMBOL}
                      </div>
                      {order.time_remaining_seconds && order.time_remaining_seconds > 0 && (
                        <div className="flex items-center gap-1 text-xs text-orange-500 mt-1">
                          <Timer className="w-3 h-3" />
                          {Math.floor(order.time_remaining_seconds / 60)}м
                        </div>
                      )}
                    </div>
                  </div>
                  <Button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAcceptOrder(order.id);
                    }}
                    disabled={acceptingOrderId === order.id || !activeShift}
                    className="w-full bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600"
                  >
                    {acceptingOrderId === order.id ? (
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    ) : (
                      <CheckCircle className="w-4 h-4 mr-2" />
                    )}
                    {!activeShift ? 'Начните смену' : 'Принять заказ'}
                  </Button>
                </Card>
              ))}
            </div>
          )}
        </div>

        {}
        <Card className="bg-gradient-to-br from-blue-50 to-cyan-50 border-2 border-blue-100">
          <div className="flex gap-3">
            <div className="text-3xl">💡</div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900 mb-1">Совет</h3>
              <p className="text-sm text-gray-700">
                Обновляйте статус заказа вовремя — клиент сразу увидит, на каком этапе доставка
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};
