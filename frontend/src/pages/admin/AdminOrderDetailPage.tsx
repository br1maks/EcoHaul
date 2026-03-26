import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, MapPin, User, Package, Clock, DollarSign, UserCheck, Loader2, AlertCircle } from 'lucide-react';
import { Card } from '@/shared/components/Card';
import { Badge } from '@/shared/components/Badge';
import { Button } from '@/shared/components/Button';
import { MapView } from '@/shared/components';
import { Star } from 'lucide-react';
import { reviewsApi, usersApi } from '@/lib/api';
import type { Review, User as UserType } from '@/shared/types'
import { ordersApi, type OrderResponse, type GarbageType } from '@/lib/api';
import { AssignCourierModal } from '@/shared/components/AssihnCourierModal';

export const AdminOrderDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState<OrderResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [review, setReview] = useState<Review | null>(null);
  const [client, setClient] = useState<UserType | null>(null);
  const [courier, setCourier] = useState<UserType | null>(null);

  const fetchOrder = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const orderData = await ordersApi.getOrderById(id);
      setOrder(orderData);

      try {
        const clientData = await usersApi.getById(orderData.client_id);
        setClient(clientData);
      } catch (err) {
        console.error('Failed to load client:', err);
      }

      if (orderData.courier_id) {
        try {
          const courierData = await usersApi.getById(orderData.courier_id);
          setCourier(courierData);
        } catch (err) {
          console.error('Failed to load courier:', err);
        }
      }

      if (orderData.status === 'COMPLETED' && orderData.courier_id) {
        try {
          const reviews = await reviewsApi.getCourierReviews(orderData.courier_id, 100, 0);
          const orderReview = reviews.find(r => r.order_id === orderData.id);
          setReview(orderReview || null);
        } catch (err) {
          console.error('Failed to load review:', err);
        }
      }
    } catch (err) {
      console.error('Failed to fetch order:', err);
      setError('Не удалось загрузить заказ');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrder();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin" />
          <p className="text-gray-600">Загрузка заказа...</p>
        </div>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-red-600" />
          <h2 className="text-xl font-semibold text-gray-900">Ошибка загрузки</h2>
          <p className="text-gray-600">{error || 'Заказ не найден'}</p>
          <button
            onClick={() => navigate('/admin/orders')}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Вернуться к заказам
          </button>
        </div>
      </div>
    );
  }

  const getGarbageTypeLabel = (type: GarbageType) => {
    const labels: Record<GarbageType, string> = {
      'HOUSEHOLD': 'Бытовой',
      'CONSTRUCTION': 'Строительный',
    };
    return labels[type] || type;
  };

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { label: string; className: string }> = {
      PENDING: { label: 'Ожидает', className: 'bg-yellow-100 text-yellow-700' },
      ASSIGNED: { label: 'Назначен', className: 'bg-blue-100 text-blue-700' },
      IN_PROGRESS: { label: 'В работе', className: 'bg-indigo-100 text-indigo-700' },
      ARRIVED: { label: 'Прибыл', className: 'bg-purple-100 text-purple-700' },
      COMPLETED: { label: 'Завершен', className: 'bg-green-100 text-green-700' },
      CANCELLED: { label: 'Отменен', className: 'bg-red-100 text-red-700' },
      FAILED: { label: 'Провален', className: 'bg-red-100 text-red-700' },
    };
    const config = statusConfig[status] || { label: status, className: 'bg-gray-100 text-gray-700' };
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handleAssignCourier = () => {
    setIsModalOpen(true);
  };

  const handleChangeStatus = async (newStatus: string) => {
    try {
      if (!id) return;
      const updatedOrder = await ordersApi.updateOrderStatus(id, newStatus as any);
      setOrder(updatedOrder);
      alert(`Статус успешно изменён на: ${newStatus}`);
    } catch (err) {
      console.error('Failed to update order status:', err);
      alert('Не удалось изменить статус заказа');
    }
  };

  const handleCancelOrder = async () => {
    if (!confirm('Вы уверены что хотите отменить заказ?')) {
      return;
    }

    const reason = prompt('Укажите причину отмены (необязательно):');

    try {
      if (!id) return;
      const updatedOrder = await ordersApi.cancelOrder(id, reason || undefined);
      setOrder(updatedOrder);
      alert('Заказ успешно отменён');
    } catch (err) {
      console.error('Failed to cancel order:', err);
      alert('Не удалось отменить заказ');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {}
      <div className="bg-white border-b border-gray-200">
        <div className="px-8 py-6">
          <button
            onClick={() => navigate('/admin/orders')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>Назад к заказам</span>
          </button>

          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Заказ #{order.id.substring(0, 8)}</h1>
              <p className="text-gray-600 mt-1">Создан {formatDate(order.created_at)}</p>
            </div>
            {getStatusBadge(order.status)}
          </div>
        </div>
      </div>

      <div className="p-8 max-w-5xl mx-auto space-y-6">
        {}
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <User className="w-5 h-5 text-gray-600" />
            Информация о клиенте
          </h2>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <User className="w-5 h-5 text-gray-400" />
              <div>
                <div className="text-sm text-gray-600">Клиент</div>
                <div className="font-medium text-gray-900">
                  {client ? `${client.first_name} ${client.last_name || ''}`.trim() : 'Загрузка...'}
                </div>
                <div className="text-xs text-gray-500">ID: {order.client_id.substring(0, 8)}</div>
              </div>
            </div>
            {client?.phone && (
              <div className="flex items-center gap-3">
                <User className="w-5 h-5 text-gray-400" />
                <div>
                  <div className="text-sm text-gray-600">Телефон</div>
                  <div className="font-medium text-gray-900">{client.phone}</div>
                </div>
              </div>
            )}
          </div>
        </Card>

        {}
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Package className="w-5 h-5 text-gray-600" />
            Детали заказа
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-start gap-3 md:col-span-2">
              <MapPin className="w-5 h-5 text-gray-400 mt-1" />
              <div>
                <div className="text-sm text-gray-600">Адрес</div>
                {order.pickup_address ? (
                  <div>
                    <div className="font-medium text-gray-900">{order.pickup_address.full_address}</div>
                    {(order.pickup_address.entrance || order.pickup_address.floor || order.pickup_address.apartment) && (
                      <div className="text-sm text-gray-500 mt-1">
                        {[
                          order.pickup_address.entrance && `Подъезд ${order.pickup_address.entrance}`,
                          order.pickup_address.floor && `этаж ${order.pickup_address.floor}`,
                          order.pickup_address.apartment && `кв. ${order.pickup_address.apartment}`,
                        ].filter(Boolean).join(', ')}
                      </div>
                    )}
                    {order.pickup_address.notes && (
                      <div className="text-sm text-gray-500 mt-1">Примечание: {order.pickup_address.notes}</div>
                    )}
                  </div>
                ) : (
                  <div className="font-medium text-gray-900">ID: {order.pickup_address_id.substring(0, 8)}</div>
                )}
              </div>
            </div>
            {order.scheduled_time && (
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-gray-400" />
                <div>
                  <div className="text-sm text-gray-600">Запланировано</div>
                  <div className="font-medium text-gray-900">{formatDate(order.scheduled_time)}</div>
                </div>
              </div>
            )}
            <div className="flex items-center gap-3">
              <Package className="w-5 h-5 text-gray-400" />
              <div>
                <div className="text-sm text-gray-600">Тип мусора</div>
                <Badge className="bg-gray-100 text-gray-700">
                  {getGarbageTypeLabel(order.garbage_type)}
                </Badge>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Package className="w-5 h-5 text-gray-400" />
              <div>
                <div className="text-sm text-gray-600">Количество</div>
                <div className="font-medium text-gray-900">{order.number_of_bags} {order.number_of_bags === 1 ? 'мешок' : 'мешка'}</div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <DollarSign className="w-5 h-5 text-gray-400" />
              <div>
                <div className="text-sm text-gray-600">Сумма</div>
                <div className="font-bold text-green-600">{order.final_price.toFixed(2)} BYN</div>
                {order.discount_amount > 0 && (
                  <div className="text-xs text-green-600">Скидка: {order.discount_amount.toFixed(2)} BYN</div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <DollarSign className="w-5 h-5 text-gray-400" />
              <div>
                <div className="text-sm text-gray-600">До скидки</div>
                <div className="font-medium text-gray-900">{order.price_before_discount.toFixed(2)} BYN</div>
              </div>
            </div>
          </div>

          {order.description && (
            <div className="mt-4 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
              <div className="text-sm font-medium text-yellow-800 mb-1">Описание</div>
              <div className="text-sm text-yellow-700">{order.description}</div>
            </div>
          )}
        </Card>

        {order.pickup_address?.latitude && order.pickup_address?.longitude && (
          <Card>
            <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <MapPin className="w-5 h-5 text-gray-600" />
              Адрес на карте
            </h2>
            <MapView
              latitude={order.pickup_address.latitude}
              longitude={order.pickup_address.longitude}
              label={order.pickup_address.full_address}
              height="220px"
            />
          </Card>
        )}

        {}
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <UserCheck className="w-5 h-5 text-gray-600" />
            Курьер
          </h2>
          {order.courier_id ? (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <UserCheck className="w-5 h-5 text-gray-400" />
                <div>
                  <div className="text-sm text-gray-600">Курьер</div>
                  <div className="font-medium text-gray-900">
                    {courier ? `${courier.first_name} ${courier.last_name || ''}`.trim() : 'Загрузка...'}
                  </div>
                  <div className="text-xs text-gray-500">ID: {order.courier_id.substring(0, 8)}</div>
                </div>
              </div>
              {courier?.phone && (
                <div className="flex items-center gap-3">
                  <UserCheck className="w-5 h-5 text-gray-400" />
                  <div>
                    <div className="text-sm text-gray-600">Телефон</div>
                    <div className="font-medium text-gray-900">{courier.phone}</div>
                  </div>
                </div>
              )}
              {courier?.rating !== undefined && (
                <div className="flex items-center gap-3">
                  <Star className="w-5 h-5 text-yellow-400" />
                  <div>
                    <div className="text-sm text-gray-600">Рейтинг</div>
                    <div className="font-medium text-gray-900">{courier.rating.toFixed(1)} / 5</div>
                  </div>
                </div>
              )}
              <Button
                onClick={handleAssignCourier}
                className="bg-gray-600 hover:bg-gray-700"
              >
                Назначить другого курьера
              </Button>
            </div>
          ) : (
            <div className="text-center py-6">
              <p className="text-gray-500 mb-4">Курьер не назначен</p>
              <Button onClick={handleAssignCourier} className="bg-blue-600 hover:bg-blue-700">
                Назначить курьера
              </Button>
            </div>
          )}
        </Card>

        {}
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Действия</h2>
          <div className="space-y-3">
            {order.status === 'PENDING' && (
              <Button
                onClick={() => handleChangeStatus('ASSIGNED')}
                className="w-full bg-blue-600 hover:bg-blue-700"
              >
                Назначить курьера
              </Button>
            )}
            {order.status === 'ASSIGNED' && (
              <Button
                onClick={() => handleChangeStatus('IN_PROGRESS')}
                className="w-full bg-indigo-600 hover:bg-indigo-700"
              >
                Начать выполнение
              </Button>
            )}
            {order.status === 'IN_PROGRESS' && (
              <Button
                onClick={() => handleChangeStatus('ARRIVED')}
                className="w-full bg-purple-600 hover:bg-purple-700"
              >
                Отметить прибытие
              </Button>
            )}
            {order.status === 'ARRIVED' && (
              <Button
                onClick={() => handleChangeStatus('COMPLETED')}
                className="w-full bg-green-600 hover:bg-green-700"
              >
                Завершить заказ
              </Button>
            )}
            {order.status !== 'COMPLETED' && order.status !== 'CANCELLED' && order.status !== 'FAILED' && (
              <Button
                onClick={handleCancelOrder}
                className="w-full bg-red-600 hover:bg-red-700"
              >
                Отменить заказ
              </Button>
            )}

          </div>
        </Card>

        {}
        {order.status === 'COMPLETED' && (
          <Card>
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Star className="w-5 h-5 text-yellow-500" />
              Отзыв клиента
            </h2>

            {review ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className="flex gap-0.5">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <Star
                        key={star}
                        className={`w-5 h-5 ${star <= review.rating
                            ? 'text-yellow-400 fill-yellow-400'
                            : 'text-gray-300'
                          }`}
                      />
                    ))}
                  </div>
                  <span className="text-gray-600 text-sm">
                    ({review.rating}/5)
                  </span>
                </div>

                {review.comment && (
                  <div className="bg-gray-50 p-3 rounded-lg">
                    <div className="text-sm text-gray-500 mb-1">Комментарий:</div>
                    <div className="text-gray-700">{review.comment}</div>
                  </div>
                )}

                <div className="text-xs text-gray-400">
                  {new Date(review.created_at).toLocaleString('ru-RU')}
                  {review.is_anonymous && ' • Анонимный отзыв'}
                </div>
              </div>
            ) : (
              <div className="text-gray-500 text-sm py-2">
                Клиент ещё не оставил отзыв
              </div>
            )}
          </Card>
        )}
      </div>
      <AssignCourierModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        orderId={id || ''}
        onSuccess={fetchOrder}
      />
    </div>
  );
};
