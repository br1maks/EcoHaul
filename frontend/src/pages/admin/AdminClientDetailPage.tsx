import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, User, Phone, Mail, Calendar, Package, DollarSign, Loader2, AlertCircle, MessageSquare } from 'lucide-react';
import { Card } from '@/shared/components/Card';
import { Badge } from '@/shared/components/Badge';
import { clientsApi, ordersApi } from '@/lib/api';
import type { ClientStatistics, OrderResponse } from '@/shared/types';

export const AdminClientDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [client, setClient] = useState<ClientStatistics | null>(null);
  const [recentOrders, setRecentOrders] = useState<OrderResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);



  const fetchClientData = useCallback(async () => {
    if (!id) return;

    try {
      setLoading(true);
      setError(null);

      const clientData = await clientsApi.getClientById(id);
      setClient(clientData);

      const ordersResponse = await ordersApi.getAllOrders({
        client_id: id,
        page: 1,
        size: 10,
      });
      setRecentOrders(ordersResponse.items);
    } catch (err) {
      console.error('Failed to fetch client data:', err);
      setError('Не удалось загрузить данные клиента');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (id) {
      fetchClientData();
    }
  }, [id, fetchClientData]);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Неизвестно';
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  };

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
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

  const getGarbageTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      'HOUSEHOLD': 'Бытовой',
      'CONSTRUCTION': 'Строительный',
    };
    return labels[type] || type;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin" />
          <p className="text-gray-600">Загрузка данных клиента...</p>
        </div>
      </div>
    );
  }

  if (error || !client) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-red-600" />
          <h2 className="text-xl font-semibold text-gray-900">Ошибка загрузки</h2>
          <p className="text-gray-600">{error || 'Клиент не найден'}</p>
          <button
            onClick={() => navigate('/admin/clients')}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Вернуться к списку клиентов
          </button>
        </div>
      </div>
    );
  }

  const activeOrders = recentOrders.filter(o =>
    !['COMPLETED', 'CANCELLED', 'FAILED'].includes(o.status)
  ).length;

  return (
    <div className="min-h-screen bg-gray-50">
      {}
      <div className="bg-white border-b border-gray-200">
        <div className="px-8 py-6">
          <button
            onClick={() => navigate('/admin/clients')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>Назад к клиентам</span>
          </button>

          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {client.first_name} {client.last_name}
              </h1>
              <p className="text-gray-600 mt-1">
                Зарегистрирован {formatDate(client.created_at)}
              </p>
            </div>
            {client.is_active ? (
              <Badge className="bg-green-100 text-green-700">Активен</Badge>
            ) : (
              <Badge className="bg-red-100 text-red-700">Неактивен</Badge>
            )}
          </div>
        </div>
      </div>

      <div className="p-8 max-w-5xl mx-auto space-y-6">
        {}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <div className="text-sm text-gray-600 mb-1">Всего заказов</div>
            <div className="text-2xl font-bold text-blue-600">{client.total_orders}</div>
          </Card>
          <Card>
            <div className="text-sm text-gray-600 mb-1">Активных</div>
            <div className="text-2xl font-bold text-indigo-600">{activeOrders}</div>
          </Card>
          <Card>
            <div className="text-sm text-gray-600 mb-1">Завершено</div>
            <div className="text-2xl font-bold text-green-600">{client.completed_orders}</div>
          </Card>
          <Card>
            <div className="text-sm text-gray-600 mb-1">Потрачено</div>
            <div className="text-2xl font-bold text-purple-600">{client.total_spent.toFixed(2)} BYN</div>
          </Card>
        </div>

        {}
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <User className="w-5 h-5 text-gray-600" />
            Контактная информация
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center gap-3">
              <User className="w-5 h-5 text-gray-400" />
              <div>
                <div className="text-sm text-gray-600">Имя</div>
                <div className="font-medium text-gray-900">
                  {client.first_name} {client.last_name}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Phone className="w-5 h-5 text-gray-400" />
              <div>
                <div className="text-sm text-gray-600">Телефон</div>
                <a
                  href={`tel:${client.phone}`}
                  className="font-medium text-blue-600 hover:text-blue-700"
                >
                  {client.phone}
                </a>
              </div>
            </div>
            {client.email && (
              <div className="flex items-center gap-3">
                <Mail className="w-5 h-5 text-gray-400" />
                <div>
                  <div className="text-sm text-gray-600">Email</div>
                  <a
                    href={`mailto:${client.email}`}
                    className="font-medium text-blue-600 hover:text-blue-700"
                  >
                    {client.email}
                  </a>
                </div>
              </div>
            )}
            {client.telegram_username && (
              <div className="flex items-center gap-3">
                <MessageSquare className="w-5 h-5 text-gray-400" />
                <div>
                  <div className="text-sm text-gray-600">Telegram</div>
                  <div className="font-medium text-gray-900">@{client.telegram_username}</div>
                </div>
              </div>
            )}
            <div className="flex items-center gap-3">
              <Calendar className="w-5 h-5 text-gray-400" />
              <div>
                <div className="text-sm text-gray-600">Последний заказ</div>
                <div className="font-medium text-gray-900">{formatDate(client.last_order_date)}</div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <DollarSign className="w-5 h-5 text-gray-400" />
              <div>
                <div className="text-sm text-gray-600">Средний чек</div>
                <div className="font-medium text-gray-900">{client.average_order_value.toFixed(2)} BYN</div>
              </div>
            </div>
          </div>
        </Card>

        {}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Package className="w-5 h-5 text-gray-600" />
              Последние заказы ({recentOrders.length})
            </h2>
          </div>

          <div className="space-y-3">
            {recentOrders.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                У клиента пока нет заказов
              </div>
            ) : (
              recentOrders.map((order) => (
                <div
                  key={order.id}
                  onClick={() => navigate(`/admin/orders/${order.id}`)}
                  className="p-4 border border-gray-200 rounded-lg hover:shadow-md transition-shadow cursor-pointer"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-bold text-gray-900">#{order.id.substring(0, 8)}</span>
                      {getStatusBadge(order.status)}
                    </div>
                    <span className="text-sm text-gray-500">{formatDateTime(order.created_at)}</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="flex items-center gap-4 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-gray-600">Тип:</span>
                        <Badge className="bg-gray-100 text-gray-700">
                          {getGarbageTypeLabel(order.garbage_type)}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2">
                        <Package className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-600">{order.number_of_bags} мешков</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 justify-end">
                      <DollarSign className="w-4 h-4 text-gray-400" />
                      <span className="font-bold text-green-600">{order.final_price.toFixed(2)} BYN</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};
