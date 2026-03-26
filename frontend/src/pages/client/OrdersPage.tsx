import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useOrders } from '@/features/orders/hooks/useOrders';
import { OrderCard } from '@/features/orders/components/OrderCard';
import { Loading, Button } from '@/shared/components';
import { NotificationBell } from '@/shared/components/NotificationBell';
import { Package, Plus } from 'lucide-react';
import { CLIENT_ROUTES } from '@/constants/routes.constants';

export const OrdersPage = () => {
  const navigate = useNavigate();
  const { orders, loading, error, fetchOrders } = useOrders();

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  if (loading && orders.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
        <Loading size="lg" text="Загрузка заказов..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
        <div className="text-center">
          <div className="text-red-500 text-lg mb-2">Ошибка</div>
          <div className="text-gray-600">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
      <div className="bg-white/80 backdrop-blur-md border-b border-green-100 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">Мои заказы</h1>
            <div className="flex items-center gap-2">
              <NotificationBell />
              <Button
                variant="primary"
                size="sm"
                icon={<Plus className="w-4 h-4" />}
                onClick={() => navigate(CLIENT_ROUTES.NEW_ORDER)}
              >
                Создать
              </Button>
            </div>
          </div>
        </div>
      </div>

      {}
      <div className="max-w-2xl mx-auto px-4 py-6">
        {orders.length === 0 ? (
          <div className="text-center py-12">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
              <Package className="w-8 h-8 text-green-500" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              У вас пока нет заказов
            </h3>
            <p className="text-gray-500">
              Создайте первый заказ на вывоз мусора
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {orders.map((order) => (
              <OrderCard
                key={order.id}
                order={order}
                onClick={() => navigate(`/orders/${order.id}`)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
