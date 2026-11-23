import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, User, Phone, Mail, Package, Star, MapPin, Clock, DollarSign, Loader2, AlertCircle, ShieldCheck, ShieldX, Shield, ChevronDown, ChevronUp, Calendar, TrendingUp } from 'lucide-react';
import { Card } from '@/shared/components/Card';
import { Badge } from '@/shared/components/Badge';
import { Button } from '@/shared/components/Button';
import { couriersApi } from '@/lib/api/couriers';
import type { ShiftDetail, ShiftsResponse } from '@/lib/api/couriers';
import { ordersApi } from '@/lib/api/orders';
import type { CourierStatistics, OrderResponse } from '@/shared/types';

export const AdminCourierDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [courier, setCourier] = useState<CourierStatistics | null>(null);
  const [recentOrders, setRecentOrders] = useState<OrderResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const [shiftsData, setShiftsData] = useState<ShiftsResponse | null>(null);
  const [shiftsLoading, setShiftsLoading] = useState(false);
  const [dateFrom, setDateFrom] = useState(() => {
    const d = new Date();
    d.setDate(1);
    return d.toISOString().split('T')[0];
  });
  const [dateTo, setDateTo] = useState(() => new Date().toISOString().split('T')[0]);
  const [shiftsPage, setShiftsPage] = useState(1);
  const [expandedShiftId, setExpandedShiftId] = useState<string | null>(null);



  const fetchCourierData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const courierData = await couriersApi.getCourierById(id!);
      setCourier(courierData);

      try {
        const ordersResponse = await ordersApi.getAllOrders({
          courier_id: id,
          page: 1,
          size: 10,
        });
        setRecentOrders(ordersResponse.items);
      } catch {
        
        setRecentOrders([]);
      }
    } catch (err) {
      console.error('Error fetching courier data:', err);
      setError('Не удалось загрузить данные курьера');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (id) {
      fetchCourierData();
    }
  }, [id, fetchCourierData]);

  const handleVerifyCourier = async () => {
    if (!courier) return;

    try {
      setActionLoading('verify');
      await couriersApi.verifyCourier(courier.id);
      await fetchCourierData();
    } catch (err) {
      console.error('Error verifying courier:', err);
      alert('Ошибка при верификации курьера');
    } finally {
      setActionLoading(null);
    }
  };

  const handleBlockCourier = async () => {
    if (!courier) return;

    if (!confirm('Вы уверены что хотите заблокировать курьера?')) {
      return;
    }

    try {
      setActionLoading('block');
      await couriersApi.blockCourier(courier.id);
      await fetchCourierData();
    } catch (err) {
      console.error('Error blocking courier:', err);
      alert('Ошибка при блокировке курьера');
    } finally {
      setActionLoading(null);
    }
  };

  const handleUnblockCourier = async () => {
    if (!courier) return;

    try {
      setActionLoading('unblock');
      await couriersApi.unblockCourier(courier.id);
      await fetchCourierData();
    } catch (err) {
      console.error('Error unblocking courier:', err);
      alert('Ошибка при разблокировке курьера');
    } finally {
      setActionLoading(null);
    }
  };

  const garbageTypeLabels: Record<string, string> = {
    HOUSEHOLD: 'Бытовой',
    CONSTRUCTION: 'Строительный',
  };

  const statusLabels: Record<string, { label: string; className: string }> = {
    PENDING: { label: 'Ожидает', className: 'bg-yellow-100 text-yellow-700' },
    ASSIGNED: { label: 'Назначен', className: 'bg-blue-100 text-blue-700' },
    IN_PROGRESS: { label: 'В работе', className: 'bg-indigo-100 text-indigo-700' },
    ARRIVED: { label: 'Прибыл', className: 'bg-purple-100 text-purple-700' },
    COMPLETED: { label: 'Завершен', className: 'bg-green-100 text-green-700' },
    CANCELLED: { label: 'Отменен', className: 'bg-red-100 text-red-700' },
    FAILED: { label: 'Неудачный', className: 'bg-red-100 text-red-700' },
  };

  const getStatusBadge = (status: string) => {
    const config = statusLabels[status] || { label: status, className: 'bg-gray-100 text-gray-700' };
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  const getCourierStatusBadge = () => {
    if (!courier) return null;

    if (!courier.is_active) {
      return <Badge className="bg-red-100 text-red-700">Заблокирован</Badge>;
    }
    if (courier.active_shift_id) {
      return <Badge className="bg-green-100 text-green-700">На смене</Badge>;
    }
    return <Badge className="bg-gray-100 text-gray-700">Не на смене</Badge>;
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleString('ru-RU');
  };

  const formatShiftDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' });
  };

  const formatShiftTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  };

  const formatDuration = (minutes: number | null) => {
    if (!minutes) return '—';
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return h > 0 ? `${h}ч ${m}м` : `${m}м`;
  };

  const loadShifts = useCallback(async (page = 1) => {
    if (!id) return;
    try {
      setShiftsLoading(true);
      const data = await couriersApi.getCourierShifts(id, {
        date_from: dateFrom ? `${dateFrom}T00:00:00` : undefined,
        date_to: dateTo ? `${dateTo}T23:59:59` : undefined,
        page,
        size: 10,
      });
      setShiftsData(data);
      setShiftsPage(page);
    } catch (err) {
      console.error('Failed to load shifts:', err);
    } finally {
      setShiftsLoading(false);
    }
  }, [id, dateFrom, dateTo]);

  useEffect(() => {
    if (id) loadShifts(1);
  }, [id, loadShifts]);

  const GARBAGE_LABELS: Record<string, string> = { HOUSEHOLD: 'Бытовой', CONSTRUCTION: 'Строительный' };
  const STATUS_LABELS: Record<string, string> = {
    PENDING: 'Ожидает', ASSIGNED: 'Назначен', IN_PROGRESS: 'В работе',
    ARRIVED: 'Прибыл', COMPLETED: 'Завершён', CANCELLED: 'Отменён', FAILED: 'Неудачный',
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex items-center gap-3 text-gray-600">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Загрузка данных курьера...</span>
        </div>
      </div>
    );
  }

  if (error || !courier) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <AlertCircle className="w-12 h-12 text-red-500" />
          <p className="text-gray-600">{error || 'Курьер не найден'}</p>
          <Button onClick={() => navigate('/admin/couriers')}>
            Вернуться к списку
          </Button>
        </div>
      </div>
    );
  }

  const completionRate = courier.total_orders > 0
    ? ((courier.completed_orders / courier.total_orders) * 100).toFixed(1)
    : '0';

  return (
    <div className="min-h-screen bg-gray-50">
      {}
      <div className="bg-white border-b border-gray-200">
        <div className="px-8 py-6">
          <button
            onClick={() => navigate('/admin/couriers')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>Назад к курьерам</span>
          </button>

          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {courier.first_name} {courier.last_name}
              </h1>
              <p className="text-gray-600 mt-1">
                ID: {courier.id.slice(0, 8)}...
              </p>
            </div>
            <div className="flex items-center gap-2">
              {courier.is_verified && (
                <Badge className="bg-blue-100 text-blue-700 flex items-center gap-1">
                  <ShieldCheck className="w-4 h-4" />
                  Верифицирован
                </Badge>
              )}
              {getCourierStatusBadge()}
            </div>
          </div>
        </div>
      </div>

      <div className="p-8 max-w-5xl mx-auto space-y-6">
        {}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <div className="text-sm text-gray-600 mb-1">Рейтинг</div>
            <div className="flex items-center gap-2">
              <Star className="w-5 h-5 text-yellow-500 fill-yellow-500" />
              <div className="text-2xl font-bold text-yellow-600">
                {courier.rating?.toFixed(1) || '—'}
              </div>
            </div>
          </Card>
          <Card>
            <div className="text-sm text-gray-600 mb-1">Всего заказов</div>
            <div className="text-2xl font-bold text-blue-600">{courier.total_orders}</div>
          </Card>
          <Card>
            <div className="text-sm text-gray-600 mb-1">Завершено</div>
            <div className="text-2xl font-bold text-green-600">{courier.completed_orders}</div>
          </Card>
          <Card>
            <div className="text-sm text-gray-600 mb-1">Процент выполнения</div>
            <div className="text-2xl font-bold text-purple-600">{completionRate}%</div>
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
                  {courier.first_name} {courier.last_name}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Phone className="w-5 h-5 text-gray-400" />
              <div>
                <div className="text-sm text-gray-600">Телефон</div>
                {courier.phone ? (
                  <a
                    href={`tel:${courier.phone}`}
                    className="font-medium text-blue-600 hover:text-blue-700"
                  >
                    {courier.phone}
                  </a>
                ) : (
                  <span className="text-gray-400">Не указан</span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Mail className="w-5 h-5 text-gray-400" />
              <div>
                <div className="text-sm text-gray-600">Email</div>
                {courier.email ? (
                  <a
                    href={`mailto:${courier.email}`}
                    className="font-medium text-blue-600 hover:text-blue-700"
                  >
                    {courier.email}
                  </a>
                ) : (
                  <span className="text-gray-400">Не указан</span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-gray-400" />
              <div>
                <div className="text-sm text-gray-600">Часов в этом месяце</div>
                <div className="font-medium text-gray-900">{courier.total_hours_this_month?.toFixed(1) || 0} ч</div>
              </div>
            </div>
          </div>
        </Card>

        {}
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Package className="w-5 h-5 text-gray-600" />
            Статистика за месяц
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <div className="text-sm text-gray-600 mb-1">Смен</div>
              <div className="text-xl font-bold text-gray-900">{courier.shifts_this_month}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Часов</div>
              <div className="text-xl font-bold text-blue-600">{courier.total_hours_this_month?.toFixed(1) || 0}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Заказов</div>
              <div className="text-xl font-bold text-green-600">{courier.orders_this_month}</div>
            </div>
          </div>
        </Card>

        {}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Clock className="w-5 h-5 text-gray-600" />
              История смен
            </h2>
          </div>

          {}
          <div className="flex flex-wrap items-end gap-3 mb-5 p-4 bg-gray-50 rounded-lg">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">С</label>
              <input
                type="date"
                value={dateFrom}
                onChange={e => setDateFrom(e.target.value)}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">По</label>
              <input
                type="date"
                value={dateTo}
                onChange={e => setDateTo(e.target.value)}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
              />
            </div>
            <Button
              onClick={() => loadShifts(1)}
              disabled={shiftsLoading}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {shiftsLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Показать'}
            </Button>
          </div>

          {}
          {shiftsData && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
              {[
                { label: 'Смен', value: shiftsData.period_total_shifts, icon: <Calendar className="w-4 h-4 text-blue-500" /> },
                { label: 'Часов на линии', value: `${shiftsData.period_total_hours}`, icon: <Clock className="w-4 h-4 text-purple-500" /> },
                { label: 'Заказов', value: shiftsData.period_total_orders, icon: <Package className="w-4 h-4 text-green-500" /> },
                { label: 'Выручка', value: `${shiftsData.period_total_revenue} BYN`, icon: <TrendingUp className="w-4 h-4 text-orange-500" /> },
              ].map(s => (
                <div key={s.label} className="bg-white border border-gray-100 rounded-lg p-3">
                  <div className="flex items-center gap-1.5 text-xs text-gray-500 mb-1">{s.icon}{s.label}</div>
                  <div className="text-xl font-bold text-gray-900">{s.value}</div>
                </div>
              ))}
            </div>
          )}

          {}
          {shiftsLoading ? (
            <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-gray-400" /></div>
          ) : !shiftsData || shiftsData.items.length === 0 ? (
            <p className="text-gray-500 text-center py-6">Смены за выбранный период не найдены</p>
          ) : (
            <div className="space-y-2">
              {shiftsData.items.map((shift: ShiftDetail) => (
                <div key={shift.id} className="border border-gray-200 rounded-lg overflow-hidden">
                  {}
                  <button
                    className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors text-left"
                    onClick={() => setExpandedShiftId(expandedShiftId === shift.id ? null : shift.id)}
                  >
                    <div className="flex items-center gap-4">
                      <div>
                        <div className="font-medium text-gray-900 text-sm">
                          {formatShiftDate(shift.started_at)}
                        </div>
                        <div className="text-xs text-gray-500">
                          {formatShiftTime(shift.started_at)} — {shift.ended_at ? formatShiftTime(shift.ended_at) : 'сейчас'}
                        </div>
                      </div>
                      {shift.is_active && (
                        <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full font-medium">Активна</span>
                      )}
                    </div>
                    <div className="flex items-center gap-6 text-sm">
                      <div className="text-center hidden sm:block">
                        <div className="font-medium text-gray-700">{formatDuration(shift.duration_minutes)}</div>
                        <div className="text-xs text-gray-400">Длительность</div>
                      </div>
                      <div className="text-center">
                        <div className="font-medium text-gray-700">{shift.orders_completed}</div>
                        <div className="text-xs text-gray-400">Заказов</div>
                      </div>
                      <div className="text-center">
                        <div className="font-semibold text-green-600">{shift.revenue} BYN</div>
                        <div className="text-xs text-gray-400">Выручка</div>
                      </div>
                      {expandedShiftId === shift.id
                        ? <ChevronUp className="w-4 h-4 text-gray-400" />
                        : <ChevronDown className="w-4 h-4 text-gray-400" />}
                    </div>
                  </button>

                  {}
                  {expandedShiftId === shift.id && (
                    <div className="border-t border-gray-100 bg-gray-50">
                      {shift.orders.length === 0 ? (
                        <p className="text-sm text-gray-500 text-center py-4">Заказов в этой смене нет</p>
                      ) : (
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="text-xs text-gray-500 border-b border-gray-200">
                              <th className="text-left px-4 py-2 font-medium">Адрес</th>
                              <th className="text-left px-4 py-2 font-medium hidden md:table-cell">Тип / мешков</th>
                              <th className="text-left px-4 py-2 font-medium hidden sm:table-cell">Принят</th>
                              <th className="text-left px-4 py-2 font-medium hidden sm:table-cell">Завершён</th>
                              <th className="text-left px-4 py-2 font-medium">Статус</th>
                              <th className="text-right px-4 py-2 font-medium">Цена</th>
                            </tr>
                          </thead>
                          <tbody>
                            {shift.orders.map(order => {
                              const isCompleted = order.status === 'COMPLETED';
                              return (
                                <tr
                                  key={order.id}
                                  className="border-b border-gray-100 last:border-0 hover:bg-white cursor-pointer"
                                  onClick={() => navigate(`/admin/orders/${order.id}`)}
                                >
                                  <td className="px-4 py-2.5 text-gray-700 max-w-[180px] truncate">
                                    {order.pickup_address ?? '—'}
                                  </td>
                                  <td className="px-4 py-2.5 text-gray-600 hidden md:table-cell">
                                    {GARBAGE_LABELS[order.garbage_type] ?? order.garbage_type}, {order.number_of_bags} м.
                                  </td>
                                  <td className="px-4 py-2.5 text-gray-500 text-xs hidden sm:table-cell">
                                    {order.accepted_at ? formatShiftTime(order.accepted_at) : '—'}
                                  </td>
                                  <td className="px-4 py-2.5 text-gray-500 text-xs hidden sm:table-cell">
                                    {order.completed_at ? formatShiftTime(order.completed_at) : '—'}
                                  </td>
                                  <td className="px-4 py-2.5">
                                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                                      isCompleted ? 'bg-green-100 text-green-700' :
                                      order.status === 'CANCELLED' ? 'bg-red-100 text-red-700' :
                                      'bg-gray-100 text-gray-600'
                                    }`}>
                                      {STATUS_LABELS[order.status] ?? order.status}
                                    </span>
                                  </td>
                                  <td className={`px-4 py-2.5 text-right font-semibold ${isCompleted ? 'text-green-600' : 'text-gray-400'}`}>
                                    {isCompleted ? `${order.final_price} BYN` : '—'}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {}
              {shiftsData.pages > 1 && (
                <div className="flex items-center justify-between pt-3">
                  <span className="text-sm text-gray-500">
                    Страница {shiftsData.page} из {shiftsData.pages}
                  </span>
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      onClick={() => loadShifts(shiftsPage - 1)}
                      disabled={shiftsPage <= 1 || shiftsLoading}
                    >
                      ←
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => loadShifts(shiftsPage + 1)}
                      disabled={shiftsPage >= shiftsData.pages || shiftsLoading}
                    >
                      →
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>

        {}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Package className="w-5 h-5 text-gray-600" />
              Последние заказы
            </h2>
            <button
              onClick={() => navigate('/admin/orders')}
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              Смотреть все →
            </button>
          </div>

          {recentOrders.length === 0 ? (
            <p className="text-gray-500 text-center py-4">Заказов пока нет</p>
          ) : (
            <div className="space-y-3">
              {recentOrders.map((order) => (
                <div
                  key={order.id}
                  onClick={() => navigate(`/admin/orders/${order.id}`)}
                  className="p-4 border border-gray-200 rounded-lg hover:shadow-md transition-shadow cursor-pointer"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-bold text-gray-900">
                        #{order.id.slice(0, 8)}
                      </span>
                      {getStatusBadge(order.status)}
                    </div>
                    <span className="text-sm text-gray-500">{formatDate(order.created_at)}</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <div className="flex items-start gap-2 text-gray-700">
                        <MapPin className="w-4 h-4 text-gray-400 mt-0.5" />
                        <span className="text-sm">
                          Адрес #{order.pickup_address_id.slice(0, 8)}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-gray-600">Тип:</span>
                        <Badge className="bg-gray-100 text-gray-700">
                          {garbageTypeLabels[order.garbage_type] || order.garbage_type}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2">
                        <DollarSign className="w-4 h-4 text-gray-400" />
                        <span className="font-bold text-green-600">
                          {order.final_price?.toFixed(2) || '—'} BYN
                        </span>
                      </div>
                    </div>
                  </div>

                  {order.completed_at && (
                    <div className="text-xs text-gray-500 mt-2">
                      Завершено: {formatDate(order.completed_at)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>

        {}
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Действия</h2>
          <div className="space-y-3">
            {!courier.is_verified && (
              <Button
                onClick={handleVerifyCourier}
                disabled={actionLoading !== null}
                className="w-full bg-blue-600 hover:bg-blue-700 flex items-center justify-center gap-2"
              >
                {actionLoading === 'verify' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <ShieldCheck className="w-4 h-4" />
                )}
                Верифицировать курьера
              </Button>
            )}

            {courier.is_active ? (
              <Button
                onClick={handleBlockCourier}
                disabled={actionLoading !== null}
                className="w-full bg-red-600 hover:bg-red-700 flex items-center justify-center gap-2"
              >
                {actionLoading === 'block' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <ShieldX className="w-4 h-4" />
                )}
                Заблокировать курьера
              </Button>
            ) : (
              <Button
                onClick={handleUnblockCourier}
                disabled={actionLoading !== null}
                className="w-full bg-green-600 hover:bg-green-700 flex items-center justify-center gap-2"
              >
                {actionLoading === 'unblock' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Shield className="w-4 h-4" />
                )}
                Разблокировать курьера
              </Button>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};
