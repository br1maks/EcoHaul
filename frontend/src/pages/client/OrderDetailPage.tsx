import { useEffect, useState, useCallback } from 'react';
import { ordersApi, reviewsApi } from '@/lib/api';
import { paymentsApi } from '@/lib/api/payments';
import type { OrderResponse, Review, CreateReviewData } from '@/shared/types';
import { Badge } from '@/shared/components/Badge';
import { Card } from '@/shared/components/Card';
import { Button } from '@/shared/components/Button';
import { MapView } from '@/shared/components';
import {
  MapPin,
  Package,
  Calendar,
  CreditCard,
  Clock,
  ChevronLeft,
  Loader2,
  AlertCircle,
  Star,
  Send,
  CheckCircle
} from 'lucide-react';
import {
  ORDER_STATUS_LABELS,
  ORDER_STATUS_COLORS,
  GARBAGE_TYPE_LABELS,
  GARBAGE_TYPE_ICONS,
  CURRENCY_SYMBOL
} from '@/constants';

interface OrderDetailPageProps {
  orderId: string;
  onBack?: () => void;
}

export const OrderDetailPage = ({ orderId, onBack }: OrderDetailPageProps) => {
  const [order, setOrder] = useState<OrderResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [paying, setPaying] = useState(false);

  const [existingReview, setExistingReview] = useState<Review | null>(null);
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewComment, setReviewComment] = useState('');
  const [submittingReview, setSubmittingReview] = useState(false);
  const [reviewSubmitted, setReviewSubmitted] = useState(false);

  const loadOrder = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await ordersApi.getOrderById(orderId);
      setOrder(response);

      if (response.status === 'COMPLETED') {
        const review = await reviewsApi.checkOrderReview(orderId);
        if (review) {
          setExistingReview(review);
          setReviewSubmitted(true);
        }
      }
    } catch (err: unknown) {
      console.error('Failed to load order:', err);
      setError('Ошибка загрузки заказа');
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    loadOrder();
  }, [loadOrder]);

  const handleCancel = async () => {
    if (!order) return;

    try {
      setCancelling(true);
      await ordersApi.cancelOrder(order.id);
      await loadOrder();
    } catch (err: unknown) {
      console.error('Failed to cancel order:', err);
      alert('Ошибка отмены заказа');
    } finally {
      setCancelling(false);
    }
  };

  const handlePay = async () => {
    if (!order) return;
    try {
      setPaying(true);
      const result = await paymentsApi.createPayment({
        payment_type: 'ORDER_PAYMENT',
        amount: order.final_price,
        order_id: order.id,
      });
      window.location.href = result.payment_url;
    } catch {
      alert('Ошибка при создании платежа');
    } finally {
      setPaying(false);
    }
  };

  const handleSubmitReview = async () => {
    if (!order || !order.courier_id) return;

    try {
      setSubmittingReview(true);
      const reviewData: CreateReviewData = {
        reviewee_id: order.courier_id,
        order_id: order.id,
        rating: reviewRating,
        comment: reviewComment || undefined,
      };
      const review = await reviewsApi.create(reviewData);
      setExistingReview(review);
      setReviewSubmitted(true);
    } catch (err: unknown) {
      console.error('Failed to submit review:', err);
      alert('Ошибка отправки отзыва');
    } finally {
      setSubmittingReview(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
        <div className="flex items-center gap-3 text-gray-600">
          <Loader2 className="w-6 h-6 animate-spin text-green-500" />
          <span>Загрузка заказа...</span>
        </div>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <div className="text-red-500 text-lg mb-2">Ошибка</div>
          <div className="text-gray-600">{error || 'Заказ не найден'}</div>
        </div>
      </div>
    );
  }

  const statusColor = ORDER_STATUS_COLORS[order.status];
  const statusLabel = ORDER_STATUS_LABELS[order.status];
  const garbageLabel = GARBAGE_TYPE_LABELS[order.garbage_type];
  const garbageIcon = GARBAGE_TYPE_ICONS[order.garbage_type];

  const canCancel = ['PENDING', 'ASSIGNED'].includes(order.status);

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
      <div className="bg-white/80 backdrop-blur-md border-b border-green-100">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            {onBack && (
              <button
                onClick={onBack}
                className="p-2 hover:bg-green-100 rounded-lg transition-colors"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
            )}
            <div className="flex-1">
              <h1 className="text-xl font-bold text-gray-900">
                Заказ #{order.id.slice(0, 8)}
              </h1>
            </div>
            <Badge className={statusColor}>{statusLabel}</Badge>
          </div>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-4">

        <Card>
          <h2 className="font-semibold text-gray-900 mb-4">Детали заказа</h2>

          <div className="space-y-3">

            {order.pickup_address && (
              <div className="flex gap-3">
                <MapPin className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="text-sm text-gray-500">Адрес</div>
                  <div className="font-medium">{order.pickup_address.full_address}</div>
                  {(order.pickup_address.entrance || order.pickup_address.floor || order.pickup_address.apartment) && (
                    <div className="text-sm text-gray-500">
                      {[
                        order.pickup_address.entrance && `Подъезд ${order.pickup_address.entrance}`,
                        order.pickup_address.floor && `этаж ${order.pickup_address.floor}`,
                        order.pickup_address.apartment && `кв. ${order.pickup_address.apartment}`,
                      ].filter(Boolean).join(', ')}
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="flex gap-3">
              <Package className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
              <div>
                <div className="text-sm text-gray-500">Тип мусора</div>
                <div className="font-medium">
                  {garbageIcon} {garbageLabel} • {order.number_of_bags} мешков
                </div>
              </div>
            </div>

            {order.scheduled_time && (
              <div className="flex gap-3">
                <Calendar className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="text-sm text-gray-500">Запланировано</div>
                  <div className="font-medium">{formatDate(order.scheduled_time)}</div>
                </div>
              </div>
            )}

            <div className="flex gap-3">
              <Clock className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
              <div>
                <div className="text-sm text-gray-500">Создан</div>
                <div className="font-medium">{formatDate(order.created_at)}</div>
              </div>
            </div>

            <div className="flex gap-3">
              <CreditCard className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
              <div>
                <div className="text-sm text-gray-500">Стоимость</div>
                <div className="font-semibold text-green-600 text-lg">
                  {order.final_price.toFixed(2)} {CURRENCY_SYMBOL}
                </div>
                {order.discount_amount > 0 && (
                  <div className="text-sm text-gray-500">
                    Скидка: -{order.discount_amount.toFixed(2)} {CURRENCY_SYMBOL}
                  </div>
                )}
              </div>
            </div>

            {order.description && (
              <div className="pt-3 border-t">
                <div className="text-sm text-gray-500 mb-1">Комментарий</div>
                <div className="text-gray-700">{order.description}</div>
              </div>
            )}
          </div>
        </Card>

        {order.pickup_address?.latitude && order.pickup_address?.longitude && (
          <Card>
            <h2 className="font-semibold text-gray-900 mb-3">Адрес на карте</h2>
            <MapView
              latitude={order.pickup_address.latitude}
              longitude={order.pickup_address.longitude}
              label={order.pickup_address.full_address}
              height="200px"
            />
          </Card>
        )}

        {}
        {order.status === 'COMPLETED' && (
          <Card>
            <h2 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <CreditCard className="w-5 h-5 text-green-500" />
              Оплата заказа
            </h2>
            <div className="flex items-center justify-between mb-4">
              <span className="text-gray-600">Итого к оплате</span>
              <span className="text-2xl font-bold text-green-600">
                {order.final_price.toFixed(2)} {CURRENCY_SYMBOL}
              </span>
            </div>
            <Button
              onClick={handlePay}
              disabled={paying}
              className="w-full bg-green-600 hover:bg-green-700"
            >
              {paying ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Переходим к оплате...
                </>
              ) : (
                <>
                  <CreditCard className="w-4 h-4 mr-2" />
                  Оплатить {order.final_price.toFixed(2)} {CURRENCY_SYMBOL}
                </>
              )}
            </Button>
          </Card>
        )}

        {}
        {order.status === 'COMPLETED' && order.courier_id && (
          <Card>
            <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Star className="w-5 h-5 text-yellow-500" />
              Отзыв о курьере
            </h2>

            {reviewSubmitted || existingReview ? (
              <div className="text-center py-4">
                <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
                <div className="font-medium text-gray-900 mb-2">Спасибо за отзыв!</div>
                <div className="flex justify-center gap-1 mb-2">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <Star
                      key={star}
                      className={`w-5 h-5 ${
                        star <= (existingReview?.rating || reviewRating)
                          ? 'text-yellow-400 fill-yellow-400'
                          : 'text-gray-300'
                      }`}
                    />
                  ))}
                </div>
                {existingReview?.comment && (
                  <div className="text-gray-600 text-sm mt-2">
                    "{existingReview.comment}"
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <div className="text-sm text-gray-600 mb-2">Оцените работу курьера:</div>
                  <div className="flex justify-center gap-2">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        onClick={() => setReviewRating(star)}
                        className="p-1 hover:scale-110 transition-transform"
                      >
                        <Star
                          className={`w-8 h-8 ${
                            star <= reviewRating
                              ? 'text-yellow-400 fill-yellow-400'
                              : 'text-gray-300 hover:text-yellow-300'
                          }`}
                        />
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-sm text-gray-600 mb-1 block">
                    Комментарий (необязательно):
                  </label>
                  <textarea
                    value={reviewComment}
                    onChange={(e) => setReviewComment(e.target.value)}
                    placeholder="Напишите ваш отзыв..."
                    className="w-full px-3 py-2 border rounded-lg resize-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                    rows={3}
                  />
                </div>

                <Button
                  onClick={handleSubmitReview}
                  disabled={submittingReview}
                  className="w-full bg-green-600 hover:bg-green-700"
                >
                  {submittingReview ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      Отправка...
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4 mr-2" />
                      Отправить отзыв
                    </>
                  )}
                </Button>
              </div>
            )}
          </Card>
        )}

        {canCancel && (
          <Button
            onClick={handleCancel}
            disabled={cancelling}
            className="w-full bg-red-600 hover:bg-red-700"
          >
            {cancelling ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                Отмена...
              </>
            ) : (
              'Отменить заказ'
            )}
          </Button>
        )}
      </div>
    </div>
  );
};
