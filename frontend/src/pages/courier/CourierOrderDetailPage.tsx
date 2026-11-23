import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ChevronLeft,
  MapPin,
  Package,
  Clock,
  User,
  Phone,
  Play,
  CheckCircle,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { Card } from '@/shared/components/Card';
import { Badge } from '@/shared/components/Badge';
import { Button } from '@/shared/components/Button';
import { MapView } from '@/shared/components';
import { COURIER_ROUTES } from '@/constants/routes.constants';
import { courierApi } from '@/lib/api/courier';
import { ordersApi } from '@/lib/api/orders';
import type { OrderResponse } from '@/shared/types';
import {
  ORDER_STATUS_LABELS,
  GARBAGE_TYPE_LABELS,
  GARBAGE_TYPE_ICONS,
  CURRENCY_SYMBOL
} from '@/constants';

interface CourierOrderDetailPageProps {
  orderId: string;
  onBack?: () => void;
}

export const CourierOrderDetailPage = ({ orderId, onBack }: CourierOrderDetailPageProps) => {
  const navigate = useNavigate();
  const [order, setOrder] = useState<OrderResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadOrder = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await ordersApi.getOrderById(orderId);
      setOrder(data);
    } catch (err) {
      console.error('Failed to load order:', err);
      setError('Не удалось загрузить заказ');
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    if (orderId) {
      loadOrder();
    }
  }, [orderId, loadOrder]);



  const handleStatusUpdate = async (newStatus: string) => {
    if (!order) return;

    try {
      setUpdating(true);
      const updated = await courierApi.updateOrderStatus(order.id, newStatus);
      setOrder(updated);
    } catch (err) {
      console.error('Failed to update status:', err);
      alert('Не удалось обновить статус заказа');
    } finally {
      setUpdating(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PENDING': return 'bg-yellow-100 text-yellow-700';
      case 'ASSIGNED': return 'bg-blue-100 text-blue-700';
      case 'IN_PROGRESS': return 'bg-purple-100 text-purple-700';
      case 'ARRIVED': return 'bg-orange-100 text-orange-700';
      case 'COMPLETED': return 'bg-green-100 text-green-700';
      case 'CANCELLED': return 'bg-red-100 text-red-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU');
  };

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const renderActionButtons = () => {
    if (!order) return null;

    const status = order.status as string;

    if (status === 'ASSIGNED') {
      return (
        <Button
          variant="primary"
          className="w-full shadow-lg shadow-green-200"
          onClick={() => handleStatusUpdate('IN_PROGRESS')}
          disabled={updating}
        >
          {updating ? (
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
          ) : (
            <Play className="w-5 h-5 mr-2" />
          )}
          <span className="text-lg">Начать выполнение</span>
        </Button>
      );
    }

    if (status === 'IN_PROGRESS') {
      return (
        <Button
          variant="primary"
          className="w-full shadow-lg shadow-orange-200 bg-orange-500 hover:bg-orange-600"
          onClick={() => handleStatusUpdate('ARRIVED')}
          disabled={updating}
        >
          {updating ? (
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
          ) : (
            <MapPin className="w-5 h-5 mr-2" />
          )}
          <span className="text-lg">Я прибыл</span>
        </Button>
      );
    }

    if (status === 'ARRIVED') {
      return (
        <Button
          variant="primary"
          className="w-full shadow-lg shadow-green-200"
          onClick={() => handleStatusUpdate('COMPLETED')}
          disabled={updating}
        >
          {updating ? (
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
          ) : (
            <CheckCircle className="w-5 h-5 mr-2" />
          )}
          <span className="text-lg">Завершить заказ</span>
        </Button>
      );
    }

    if (status === 'COMPLETED') {
      return (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
          <CheckCircle className="w-12 h-12 mx-auto mb-2 text-green-600" />
          <div className="font-semibold text-green-900">Заказ успешно завершён!</div>
          <div className="text-sm text-green-700 mt-1">
            Спасибо за работу!
          </div>
        </div>
      );
    }

    return null;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 bg-gradient-to-br from-green-400 to-emerald-500 rounded-full flex items-center justify-center animate-pulse">
            <Loader2 className="w-8 h-8 text-white animate-spin" />
          </div>
          <span className="text-green-700 font-medium">Загрузка заказа...</span>
        </div>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
        <div className="text-center p-6">
          <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-10 h-10 text-red-500" />
          </div>
          <div className="text-red-500 text-xl font-bold mb-2">Ошибка</div>
          <div className="text-gray-600 mb-4">{error || 'Заказ не найден'}</div>
          <Button onClick={() => navigate(COURIER_ROUTES.ORDERS)}>
            Вернуться к заказам
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50 pb-24">
      {}
      <div className="bg-white/80 backdrop-blur-md border-b border-green-100 sticky top-0 z-10 shadow-sm">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack || (() => navigate(COURIER_ROUTES.ORDERS))}
              className="p-2 hover:bg-green-50 rounded-xl transition-all duration-200 hover:scale-105"
            >
              <ChevronLeft className="w-5 h-5 text-green-600" />
            </button>
            <div className="flex-1">
              <h1 className="text-xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
                Заказ #{order.id.slice(0, 8)}
              </h1>
            </div>
            <Badge className={getStatusColor(order.status)}>
              {ORDER_STATUS_LABELS[order.status]}
            </Badge>
          </div>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        {}
        {(order.status as string) !== 'PENDING' && (order.status as string) !== 'CANCELLED' && (
          <Card className="bg-gradient-to-br from-blue-50 to-cyan-50 border-2 border-blue-100">
            {renderActionButtons()}
          </Card>
        )}

        {}
        <Card className="border-2 border-green-100">
          <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Package className="w-5 h-5 text-green-600" />
            Информация о заказе
          </h2>

          <div className="space-y-3">
            <div className="flex items-center justify-between py-2 border-b border-gray-100">
              <span className="text-gray-600">Тип мусора</span>
              <span className="font-medium text-gray-900">
                {GARBAGE_TYPE_ICONS[order.garbage_type]} {GARBAGE_TYPE_LABELS[order.garbage_type]}
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-gray-100">
              <span className="text-gray-600">Количество</span>
              <span className="font-medium text-gray-900">{order.number_of_bags} мешков</span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-gray-100">
              <span className="text-gray-600">Стоимость</span>
              <span className="text-xl font-bold text-green-600">{order.final_price} {CURRENCY_SYMBOL}</span>
            </div>

            {order.description && (
              <div className="py-2">
                <span className="text-gray-600 block mb-1">Описание</span>
                <p className="text-gray-900">{order.description}</p>
              </div>
            )}
          </div>
        </Card>

        {}
        <Card className="border-2 border-green-100">
          <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <MapPin className="w-5 h-5 text-green-600" />
            Адрес вывоза
          </h2>

          <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-4 mb-3">
            <p className="text-gray-900 font-medium">
              {order.pickup_address?.full_address || 'Адрес не указан'}
            </p>
            {(order.pickup_address?.entrance || order.pickup_address?.floor || order.pickup_address?.apartment) && (
              <div className="flex flex-wrap gap-3 mt-2">
                {order.pickup_address.entrance && (
                  <span className="text-sm text-gray-700">
                    Подъезд: <span className="font-semibold">{order.pickup_address.entrance}</span>
                  </span>
                )}
                {order.pickup_address.floor && (
                  <span className="text-sm text-gray-700">
                    Этаж: <span className="font-semibold">{order.pickup_address.floor}</span>
                  </span>
                )}
                {order.pickup_address.apartment && (
                  <span className="text-sm text-gray-700">
                    Кв.: <span className="font-semibold">{order.pickup_address.apartment}</span>
                  </span>
                )}
              </div>
            )}
          </div>

          {order.pickup_address?.latitude && order.pickup_address?.longitude && (
            <div className="mb-3">
              <MapView
                latitude={order.pickup_address.latitude}
                longitude={order.pickup_address.longitude}
                label={order.pickup_address.full_address}
                height="200px"
              />
            </div>
          )}

          {order.scheduled_time && (
            <div className="flex items-center gap-2 text-sm text-gray-700 mb-3">
              <Clock className="w-4 h-4 text-gray-400" />
              <span>
                Желаемое время: {formatDate(order.scheduled_time)} в {formatTime(order.scheduled_time)}
              </span>
            </div>
          )}

          <Button
            variant="secondary"
            className="w-full"
            onClick={() => {
              const address = order.pickup_address?.full_address || '';
              window.open(`https://yandex.ru/maps/?text=${encodeURIComponent(address)}`, '_blank');
            }}
          >
            Открыть в картах
          </Button>
        </Card>

        {}
        {(order.status as string) !== 'PENDING' && (order.client_phone || order.client_telegram_link) && (
          <Card className="border-2 border-green-100">
            <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <User className="w-5 h-5 text-green-600" />
              Контакты клиента
            </h2>

            <div className="space-y-3">
              {order.client_phone && (
                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                  <span className="text-gray-600">Телефон</span>
                  <a
                    href={`tel:${order.client_phone}`}
                    className="font-medium text-blue-600 hover:text-blue-700"
                  >
                    {order.client_phone_display || order.client_phone}
                  </a>
                </div>
              )}

              {order.client_telegram_link && (
                <div className="flex items-center justify-between py-2">
                  <span className="text-gray-600">Telegram</span>
                  <a
                    href={order.client_telegram_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-blue-600 hover:text-blue-700"
                  >
                    Написать в Telegram
                  </a>
                </div>
              )}
            </div>

            {order.client_phone && (
              <Button
                variant="outline"
                className="w-full mt-3"
                onClick={() => window.open(`tel:${order.client_phone}`)}
              >
                <Phone className="w-4 h-4 mr-2" />
                Позвонить клиенту
              </Button>
            )}
          </Card>
        )}

        {}
        <Card className="border-2 border-green-100">
          <h2 className="font-semibold text-gray-900 mb-4">История заказа</h2>

          <div className="space-y-3">
            {order.created_at && (
              <div className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className="w-3 h-3 rounded-full bg-gray-300" />
                  <div className="w-0.5 flex-1 bg-gray-200" />
                </div>
                <div className="flex-1 pb-4">
                  <div className="font-medium text-gray-900">Заказ создан</div>
                  <div className="text-sm text-gray-600">
                    {formatDateTime(order.created_at)}
                  </div>
                </div>
              </div>
            )}

            {order.accepted_at && (
              <div className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className="w-3 h-3 rounded-full bg-blue-500" />
                  {order.status !== 'ASSIGNED' && <div className="w-0.5 flex-1 bg-gray-200" />}
                </div>
                <div className="flex-1 pb-4">
                  <div className="font-medium text-gray-900">Заказ принят курьером</div>
                  <div className="text-sm text-gray-600">
                    {formatDateTime(order.accepted_at)}
                  </div>
                </div>
              </div>
            )}

            {order.started_at && (
              <div className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className="w-3 h-3 rounded-full bg-purple-500" />
                  {!['IN_PROGRESS'].includes(order.status) && <div className="w-0.5 flex-1 bg-gray-200" />}
                </div>
                <div className="flex-1 pb-4">
                  <div className="font-medium text-gray-900">Курьер выехал</div>
                  <div className="text-sm text-gray-600">
                    {formatDateTime(order.started_at)}
                  </div>
                </div>
              </div>
            )}

            {order.completed_at && (
              <div className="flex gap-3">
                <div className="w-3 h-3 rounded-full bg-green-500 mt-0.5" />
                <div className="flex-1">
                  <div className="font-medium text-gray-900">Заказ завершён</div>
                  <div className="text-sm text-gray-600">
                    {formatDateTime(order.completed_at)}
                  </div>
                </div>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};
