import { useState, useEffect, useCallback } from 'react';
import {
  Users,
  CheckCircle,
  XCircle,
  Clock,
  Phone,
  Mail,
  MapPin,
  Car,
  Bike,
  Footprints,
  Loader2,
  RefreshCw,
  MessageSquare,
  AlertCircle,
} from 'lucide-react';
import { Card } from '@/shared/components/Card';
import { Button } from '@/shared/components/Button';
import { Badge } from '@/shared/components/Badge';
import {
  courierApplicationsApi,
  type CourierApplication,
} from '@/lib/api/courierApplications';

type StatusFilter = 'all' | 'PENDING' | 'APPROVED' | 'REJECTED';

const STATUS_LABELS = {
  PENDING: 'На рассмотрении',
  APPROVED: 'Одобрена',
  REJECTED: 'Отклонена',
};

const STATUS_COLORS = {
  PENDING: 'bg-yellow-100 text-yellow-700',
  APPROVED: 'bg-green-100 text-green-700',
  REJECTED: 'bg-red-100 text-red-700',
};

export const AdminCourierApplicationsPage = () => {
  const [applications, setApplications] = useState<CourierApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('PENDING');
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [rejectComment, setRejectComment] = useState('');
  const [showRejectModal, setShowRejectModal] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  const loadApplications = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const params: { status_filter?: 'PENDING' | 'APPROVED' | 'REJECTED' } = {};
      if (statusFilter !== 'all') {
        params.status_filter = statusFilter;
      }

      const response = await courierApplicationsApi.getAll({
        ...params,
        size: 50,
      });

      setApplications(response.items);
      setTotal(response.total);
    } catch (err) {
      console.error('Failed to load applications:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadApplications();
  }, [loadApplications]);

  const handleApprove = async (applicationId: string) => {
    try {
      setProcessingId(applicationId);
      await courierApplicationsApi.review(applicationId, {
        status: 'APPROVED',
      });
      await loadApplications(true);
    } catch (err) {
      console.error('Failed to approve:', err);
      alert('Ошибка при одобрении заявки');
    } finally {
      setProcessingId(null);
    }
  };

  const handleReject = async (applicationId: string) => {
    try {
      setProcessingId(applicationId);
      await courierApplicationsApi.review(applicationId, {
        status: 'REJECTED',
        admin_comment: rejectComment || undefined,
      });
      setShowRejectModal(null);
      setRejectComment('');
      await loadApplications(true);
    } catch (err) {
      console.error('Failed to reject:', err);
      alert('Ошибка при отклонении заявки');
    } finally {
      setProcessingId(null);
    }
  };

  const getTransportIcon = (type?: string | null) => {
    switch (type) {
      case 'car': return <Car className="w-4 h-4" />;
      case 'bike': return <Bike className="w-4 h-4" />;
      case 'walk': return <Footprints className="w-4 h-4" />;
      default: return null;
    }
  };

  const getTransportLabel = (type?: string | null) => {
    switch (type) {
      case 'car': return 'Автомобиль';
      case 'bike': return 'Велосипед';
      case 'walk': return 'Пешком';
      default: return 'Не указано';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Users className="w-6 h-6 text-blue-600" />
              <h1 className="text-xl font-bold text-gray-900">Заявки на курьера</h1>
              <Badge className="bg-blue-100 text-blue-700">{total}</Badge>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => loadApplications(true)}
              disabled={refreshing}
            >
              <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
            </Button>
          </div>

          {}
          <div className="flex gap-2">
            {(['PENDING', 'APPROVED', 'REJECTED', 'all'] as StatusFilter[]).map((filter) => (
              <button
                key={filter}
                onClick={() => setStatusFilter(filter)}
                className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                  statusFilter === filter
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {filter === 'all' ? 'Все' : STATUS_LABELS[filter]}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-4">
        {applications.length === 0 ? (
          <Card className="text-center py-12">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Users className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Нет заявок
            </h3>
            <p className="text-gray-500">
              {statusFilter === 'PENDING'
                ? 'Нет заявок на рассмотрении'
                : 'Заявки не найдены'}
            </p>
          </Card>
        ) : (
          applications.map((app) => (
            <Card key={app.id} className="border border-gray-200">
              {}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center text-blue-700 font-bold">
                    {app.user_first_name?.[0]}{app.user_last_name?.[0]}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">
                      {app.user_first_name} {app.user_last_name}
                    </h3>
                    {app.user_telegram_username && (
                      <p className="text-sm text-gray-500">@{app.user_telegram_username}</p>
                    )}
                  </div>
                </div>
                <Badge className={STATUS_COLORS[app.status]}>
                  {app.status === 'PENDING' && <Clock className="w-3 h-3 mr-1" />}
                  {app.status === 'APPROVED' && <CheckCircle className="w-3 h-3 mr-1" />}
                  {app.status === 'REJECTED' && <XCircle className="w-3 h-3 mr-1" />}
                  {STATUS_LABELS[app.status]}
                </Badge>
              </div>

              {}
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="flex items-center gap-2 text-sm">
                  <Phone className="w-4 h-4 text-gray-400" />
                  <span>{app.phone}</span>
                </div>
                {app.email && (
                  <div className="flex items-center gap-2 text-sm">
                    <Mail className="w-4 h-4 text-gray-400" />
                    <span>{app.email}</span>
                  </div>
                )}
                <div className="flex items-center gap-2 text-sm">
                  {getTransportIcon(app.transport_type)}
                  <span>
                    {app.has_transport
                      ? getTransportLabel(app.transport_type)
                      : 'Пешком'}
                  </span>
                </div>
                {app.work_area && (
                  <div className="flex items-center gap-2 text-sm">
                    <MapPin className="w-4 h-4 text-gray-400" />
                    <span>{app.work_area}</span>
                  </div>
                )}
              </div>

              {}
              {app.message && (
                <div className="bg-gray-50 rounded-lg p-3 mb-4">
                  <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">
                    <MessageSquare className="w-4 h-4" />
                    <span>Сообщение:</span>
                  </div>
                  <p className="text-sm text-gray-700">{app.message}</p>
                </div>
              )}

              {}
              {app.admin_comment && (
                <div className="bg-red-50 rounded-lg p-3 mb-4">
                  <div className="flex items-center gap-2 text-sm text-red-600 mb-1">
                    <AlertCircle className="w-4 h-4" />
                    <span>Комментарий администратора:</span>
                  </div>
                  <p className="text-sm text-red-700">{app.admin_comment}</p>
                </div>
              )}

              {}
              <div className="flex items-center justify-between pt-4 border-t border-gray-100">
                <span className="text-xs text-gray-500">
                  Подана: {formatDate(app.created_at)}
                </span>

                {app.status === 'PENDING' && (
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setShowRejectModal(app.id)}
                      disabled={processingId === app.id}
                    >
                      <XCircle className="w-4 h-4 mr-1" />
                      Отклонить
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => handleApprove(app.id)}
                      disabled={processingId === app.id}
                      className="bg-green-600 hover:bg-green-700"
                    >
                      {processingId === app.id ? (
                        <Loader2 className="w-4 h-4 animate-spin mr-1" />
                      ) : (
                        <CheckCircle className="w-4 h-4 mr-1" />
                      )}
                      Одобрить
                    </Button>
                  </div>
                )}
              </div>
            </Card>
          ))
        )}
      </div>

      {}
      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full mx-4 p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">
              Отклонить заявку
            </h3>
            <textarea
              value={rejectComment}
              onChange={(e) => setRejectComment(e.target.value)}
              placeholder="Причина отклонения (необязательно)"
              rows={3}
              className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none mb-4"
            />
            <div className="flex gap-3">
              <Button
                variant="secondary"
                className="flex-1"
                onClick={() => {
                  setShowRejectModal(null);
                  setRejectComment('');
                }}
                disabled={processingId !== null}
              >
                Отмена
              </Button>
              <Button
                className="flex-1 bg-red-600 hover:bg-red-700"
                onClick={() => handleReject(showRejectModal)}
                disabled={processingId !== null}
              >
                {processingId ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <XCircle className="w-4 h-4 mr-2" />
                )}
                Отклонить
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
