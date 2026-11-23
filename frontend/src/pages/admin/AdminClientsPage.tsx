import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, User, Package, DollarSign, Calendar, Loader2, AlertCircle } from 'lucide-react';
import { Card } from '@/shared/components/Card';
import { Badge } from '@/shared/components/Badge';
import { clientsApi } from '@/lib/api';
import type { ClientStatistics } from '@/shared/types';

export const AdminClientsPage = () => {
  const navigate = useNavigate();
  const [clients, setClients] = useState<ClientStatistics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);



  const fetchClients = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await clientsApi.getAllClients({
        page,
        size: 20,
      });
      setClients(response.items);
      setTotalPages(response.pages);
    } catch (err) {
      console.error('Failed to fetch clients:', err);
      setError('Не удалось загрузить список клиентов');
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchClients();
  }, [fetchClients]);

  const filteredClients = clients.filter(client =>
    `${client.first_name} ${client.last_name}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
    client.phone?.includes(searchQuery) ||
    (client.email && client.email.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Никогда';
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin" />
          <p className="text-gray-600">Загрузка клиентов...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-red-600" />
          <h2 className="text-xl font-semibold text-gray-900">Ошибка загрузки</h2>
          <p className="text-gray-600">{error}</p>
          <button
            onClick={fetchClients}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Попробовать снова
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {}
      <div className="bg-white border-b border-gray-200">
        <div className="px-8 py-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Клиенты</h1>
              <p className="text-gray-600 mt-1">Управление клиентами платформы</p>
            </div>
            <div className="text-sm text-gray-600">
              Всего клиентов: <span className="font-semibold">{clients.length}</span>
            </div>
          </div>

          {}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Поиск по имени, телефону или email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {}
      <div className="p-8">
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-4 px-4 font-semibold text-gray-700">Клиент</th>
                  <th className="text-left py-4 px-4 font-semibold text-gray-700">Контакты</th>
                  <th className="text-left py-4 px-4 font-semibold text-gray-700">Заказы</th>
                  <th className="text-left py-4 px-4 font-semibold text-gray-700">Потрачено</th>
                  <th className="text-left py-4 px-4 font-semibold text-gray-700">Средний чек</th>
                  <th className="text-left py-4 px-4 font-semibold text-gray-700">Последний заказ</th>
                  <th className="text-left py-4 px-4 font-semibold text-gray-700">Статус</th>
                </tr>
              </thead>
              <tbody>
                {filteredClients.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-12 text-gray-500">
                      {searchQuery ? 'Клиенты не найдены' : 'Нет клиентов'}
                    </td>
                  </tr>
                ) : (
                  filteredClients.map((client) => (
                    <tr
                      key={client.id}
                      className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors"
                      onClick={() => navigate(`/admin/clients/${client.id}`)}
                    >
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                            <User className="w-5 h-5 text-blue-600" />
                          </div>
                          <div>
                            <div className="font-medium text-gray-900">
                              {client.first_name} {client.last_name}
                            </div>
                            {client.telegram_username && (
                              <div className="text-sm text-gray-500">@{client.telegram_username}</div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <div className="text-sm">
                          <div className="text-gray-900">{client.phone}</div>
                          {client.email && (
                            <div className="text-gray-500">{client.email}</div>
                          )}
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-2">
                          <Package className="w-4 h-4 text-gray-400" />
                          <span className="text-gray-900">
                            {client.completed_orders} / {client.total_orders}
                          </span>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-2">
                          <DollarSign className="w-4 h-4 text-green-600" />
                          <span className="font-semibold text-green-600">
                            {client.total_spent.toFixed(2)} BYN
                          </span>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        <span className="text-gray-900">
                          {client.average_order_value.toFixed(2)} BYN
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-2">
                          <Calendar className="w-4 h-4 text-gray-400" />
                          <span className="text-gray-900">
                            {formatDate(client.last_order_date)}
                          </span>
                        </div>
                      </td>
                      <td className="py-4 px-4">
                        {client.is_active ? (
                          <Badge className="bg-green-100 text-green-700">Активен</Badge>
                        ) : (
                          <Badge className="bg-gray-100 text-gray-700">Неактивен</Badge>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6 pt-6 border-t border-gray-200">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Назад
              </button>
              <span className="text-gray-600">
                Страница {page} из {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Вперёд
              </button>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
