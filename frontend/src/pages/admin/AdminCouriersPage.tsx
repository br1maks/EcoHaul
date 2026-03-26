import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, ChevronRight, Phone, Star, Package, CheckCircle, Filter, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Card } from '@/shared/components/Card';
import { Badge } from '@/shared/components/Badge';
import { couriersApi } from '@/lib/api';
import type { CourierStatistics } from '@/shared/types';

export const AdminCouriersPage = () => {
  const navigate = useNavigate();
  const [couriers, setCouriers] = useState<CourierStatistics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    fetchCouriers();
  }, []);

  const fetchCouriers = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await couriersApi.getAllCouriers({
        size: 100,
      });
      setCouriers(response.items);
    } catch (err) {
      console.error('Failed to fetch couriers:', err);
      setError('Не удалось загрузить список курьеров');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { label: string; className: string }> = {
      ACTIVE: { label: 'Доступен', className: 'bg-green-100 text-green-700' },
      BUSY: { label: 'Занят', className: 'bg-yellow-100 text-yellow-700' },
      OFFLINE: { label: 'Не в сети', className: 'bg-gray-100 text-gray-700' },
    };
    const config = statusConfig[status] || { label: status, className: 'bg-gray-100 text-gray-700' };
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  const filteredCouriers = couriers.filter((courier) => {
    const fullName = `${courier.first_name} ${courier.last_name}`.toLowerCase();
    const query = searchQuery.toLowerCase();
    const matchesSearch =
      fullName.includes(query) ||
      courier.phone.includes(query) ||
      (courier.email && courier.email.toLowerCase().includes(query));

    const matchesStatus =
      statusFilter === 'all' ||
      (statusFilter === 'active' && courier.is_active) ||
      (statusFilter === 'verified' && courier.is_verified) ||
      (statusFilter === 'inactive' && !courier.is_active);

    return matchesSearch && matchesStatus;
  });

  const statusCounts = {
    all: couriers.length,
    active: couriers.filter((c) => c.is_active).length,
    verified: couriers.filter((c) => c.is_verified).length,
    inactive: couriers.filter((c) => !c.is_active).length,
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin" />
          <p className="text-gray-600">Загрузка курьеров...</p>
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
            onClick={fetchCouriers}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Попробовать снова
          </button>
        </div>
      </div>
    );
  }

  const averageRating = couriers.length > 0
    ? couriers.reduce((sum, c) => sum + c.rating, 0) / couriers.length
    : 0;

  return (
    <div className="min-h-screen bg-gray-50">
      {}
      <div className="bg-white border-b border-gray-200">
        <div className="px-8 py-6">
          <h1 className="text-2xl font-bold text-gray-900">Управление курьерами</h1>
          <p className="text-gray-600 mt-1">Все курьеры в системе</p>
        </div>
      </div>

      <div className="p-8 space-y-6">
        {}
        <Card>
          <div className="space-y-4">
            {}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Поиск по имени, телефону или email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {}
            <div className="flex items-center gap-2 flex-wrap">
              <Filter className="w-5 h-5 text-gray-500" />
              <button
                onClick={() => setStatusFilter('all')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${statusFilter === 'all'
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                Все ({statusCounts.all})
              </button>
              <button
                onClick={() => setStatusFilter('active')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${statusFilter === 'active'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                Активные ({statusCounts.active})
              </button>
              <button
                onClick={() => setStatusFilter('verified')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${statusFilter === 'verified'
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                Верифицированные ({statusCounts.verified})
              </button>
              <button
                onClick={() => setStatusFilter('inactive')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${statusFilter === 'inactive'
                    ? 'bg-red-100 text-red-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                Неактивные ({statusCounts.inactive})
              </button>
            </div>
          </div>
        </Card>

        {}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <div className="text-sm text-gray-600 mb-1">Всего курьеров</div>
            <div className="text-2xl font-bold text-gray-900">{couriers.length}</div>
          </Card>
          <Card>
            <div className="text-sm text-gray-600 mb-1">Активные</div>
            <div className="text-2xl font-bold text-green-600">{statusCounts.active}</div>
          </Card>
          <Card>
            <div className="text-sm text-gray-600 mb-1">Всего заказов</div>
            <div className="text-2xl font-bold text-blue-600">
              {couriers.reduce((sum, c) => sum + c.total_orders, 0)}
            </div>
          </Card>
          <Card>
            <div className="text-sm text-gray-600 mb-1">Средний рейтинг</div>
            <div className="text-2xl font-bold text-yellow-600">{averageRating.toFixed(1)}</div>
          </Card>
        </div>

        {}
        <div className="space-y-3">
          {filteredCouriers.length === 0 ? (
            <Card className="text-center py-12">
              <p className="text-gray-500">
                {searchQuery ? 'Курьеры не найдены' : 'Нет курьеров'}
              </p>
            </Card>
          ) : (
            filteredCouriers.map((courier) => (
              <Card
                key={courier.id}
                className="hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => navigate(`/admin/couriers/${courier.id}`)}
              >
                <div className="flex items-start gap-4">
                  <div className="flex-1 min-w-0">
                    {}
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-lg font-bold text-gray-900">
                        {courier.first_name} {courier.last_name}
                      </span>
                      {courier.is_verified && (
                        <CheckCircle2 className="w-5 h-5 text-green-600" />
                      )}
                      {getStatusBadge(courier.courier_status)}
                    </div>

                    {}
                    <div className="flex items-center gap-2 text-gray-700 mb-3">
                      <Phone className="w-4 h-4 text-gray-400" />
                      <span className="text-sm">{courier.phone}</span>
                    </div>

                    {}
                    <div className="flex items-center gap-6 text-sm">
                      <div className="flex items-center gap-2">
                        <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                        <span className="font-bold text-yellow-600">{courier.rating.toFixed(1)}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Package className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-600">Всего:</span>
                        <span className="font-medium text-gray-900">{courier.total_orders}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-600">Завершено:</span>
                        <span className="font-medium text-green-600">{courier.completed_orders}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-gray-600">Смен за месяц:</span>
                        <span className="font-medium text-purple-600">{courier.shifts_this_month}</span>
                      </div>
                    </div>
                  </div>

                  <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
                </div>
              </Card>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
