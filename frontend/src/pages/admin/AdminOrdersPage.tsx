import { useState, useEffect } from 'react';
import { Search, ChevronRight, Package, Loader2, AlertCircle } from 'lucide-react';
import { Card } from '@/shared/components/Card';
import { Badge } from '@/shared/components/Badge';
import { Input } from '@/shared/components/Input';
import { useNavigate } from 'react-router-dom';
import { ordersApi, type OrderListResponse, type GarbageType } from '@/lib/api';

export const AdminOrdersPage = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<OrderListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    fetchOrders();
  }, [statusFilter, currentPage]);

  const fetchOrders = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: any = {
        page: currentPage,
        size: 20,
      };

      if (statusFilter !== 'all') {
        params.status_filter = statusFilter;
      }

      const orders = await ordersApi.getAllOrders(params);
      setData(orders);
    } catch (err) {
      console.error('Failed to fetch orders:', err);
      setError('Не удалось загрузить заказы');
    } finally {
      setLoading(false);
    }
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

  const getGarbageTypeLabel = (type: GarbageType) => {
    const labels: Record<GarbageType, string> = {
      'HOUSEHOLD': 'Бытовой',
      'CONSTRUCTION': 'Строительный',
    };
    return labels[type] || type;
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin" />
          <p className="text-gray-600">Загрузка заказов...</p>
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
            onClick={() => fetchOrders()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Попробовать снова
          </button>
        </div>
      </div>
    );
  }

  const filteredOrders = data.items.filter(order => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      order.id.toLowerCase().includes(query) ||
      order.client_id.toLowerCase().includes(query)
    );
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {}
      <div className="bg-white border-b border-gray-200">
        <div className="px-8 py-6">
          <h1 className="text-2xl font-bold text-gray-900">Заказы</h1>
          <p className="text-gray-600 mt-1">Управление всеми заказами системы</p>
        </div>
      </div>

      <div className="p-8">
        {}
        <Card className="mb-6">
          <div className="flex flex-col lg:flex-row gap-4">
            {}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <Input
                  type="text"
                  placeholder="Поиск по ID заказа или клиента..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            {}
            <div className="lg:w-64">
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">Все статусы</option>
                <option value="PENDING">Ожидает</option>
                <option value="ASSIGNED">Назначен</option>
                <option value="IN_PROGRESS">В работе</option>
                <option value="ARRIVED">Прибыл</option>
                <option value="COMPLETED">Завершен</option>
                <option value="CANCELLED">Отменен</option>
                <option value="FAILED">Провален</option>
              </select>
            </div>
          </div>

          {}
          <div className="mt-4 pt-4 border-t border-gray-200 flex items-center justify-between">
            <p className="text-sm text-gray-600">
              Показано {filteredOrders.length} из {data.total} заказов
            </p>
            <p className="text-sm text-gray-600">
              Страница {data.page} из {data.pages}
            </p>
          </div>
        </Card>

        {}
        <div className="space-y-4">
          {filteredOrders.map((order) => (
            <Card
              key={order.id}
              className="hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => navigate(`/admin/orders/${order.id}`)}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 grid grid-cols-1 md:grid-cols-4 gap-4">
                  {}
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Package className="w-4 h-4 text-gray-400" />
                      <span className="text-sm font-medium text-gray-900">
                        Заказ #{order.id.substring(0, 8)}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600">
                      {formatDate(order.created_at)}
                    </p>
                  </div>

                  {}
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Тип мусора</p>
                    <p className="text-sm font-medium text-gray-900">
                      {getGarbageTypeLabel(order.garbage_type)}
                    </p>
                    <p className="text-xs text-gray-600">
                      {order.number_of_bags} {order.number_of_bags === 1 ? 'мешок' : 'мешка'}
                    </p>
                  </div>

                  {}
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Стоимость</p>
                    <p className="text-lg font-bold text-gray-900">
                      {order.final_price.toFixed(2)} BYN
                    </p>
                    {order.discount_amount > 0 && (
                      <p className="text-xs text-green-600">
                        Скидка: {order.discount_amount.toFixed(2)} BYN
                      </p>
                    )}
                  </div>

                  {}
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600 mb-1">Статус</p>
                      {getStatusBadge(order.status)}
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                  </div>
                </div>
              </div>

              {}
              {order.courier_id && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <p className="text-xs text-gray-600">
                    Курьер: ID {order.courier_id.substring(0, 8)}
                  </p>
                </div>
              )}
            </Card>
          ))}

          {filteredOrders.length === 0 && (
            <Card>
              <div className="text-center py-12">
                <Package className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Заказы не найдены
                </h3>
                <p className="text-gray-600">
                  {searchQuery
                    ? 'Попробуйте изменить параметры поиска'
                    : 'В системе пока нет заказов'}
                </p>
              </div>
            </Card>
          )}
        </div>

        {}
        {data.pages > 1 && (
          <div className="mt-6 flex items-center justify-center gap-2">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Назад
            </button>
            <span className="text-sm text-gray-600">
              Страница {currentPage} из {data.pages}
            </span>
            <button
              onClick={() => setCurrentPage(p => Math.min(data.pages, p + 1))}
              disabled={currentPage === data.pages}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Вперед
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
