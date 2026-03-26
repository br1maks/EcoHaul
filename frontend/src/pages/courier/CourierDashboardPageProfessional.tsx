import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock, Package, MapPin, Play, Square, CheckCircle } from 'lucide-react';

import { Button } from '@/shared/components/Button';
import { COURIER_ROUTES } from '@/constants/routes.constants';

export const CourierDashboardPageProfessional = () => {
  const navigate = useNavigate();
  const [courierStatus, setCourierStatus] = useState<'ACTIVE' | 'OFFLINE' | 'ON_BREAK'>('OFFLINE');
  const [activeShift, setActiveShift] = useState<any>(null);
  const [shiftDuration, setShiftDuration] = useState('00:00:00');

  useEffect(() => {
    
  }, []);

  useEffect(() => {
    if (!activeShift) return;

    const interval = setInterval(() => {
      const start = new Date(activeShift.started_at);
      const now = new Date();
      const diff = Math.max(0, now.getTime() - start.getTime());

      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);

      setShiftDuration(
        `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
      );
    }, 1000);

    return () => clearInterval(interval);
  }, [activeShift]);

  const handleStartShift = async () => {
    setActiveShift({
      id: '1',
      started_at: new Date().toISOString(),
      orders_completed: 0,
      total_distance_km: 0,
    });
  };

  const handleEndShift = async () => {
    setActiveShift(null);
    setShiftDuration('00:00:00');
  };

  const handleStatusChange = (newStatus: typeof courierStatus) => {
    setCourierStatus(newStatus);
  };

  const getStatusColor = (status: typeof courierStatus) => {
    switch (status) {
      case 'ACTIVE': return 'bg-green-600';
      case 'OFFLINE': return 'bg-gray-400';
      case 'ON_BREAK': return 'bg-yellow-500';
      default: return 'bg-gray-400';
    }
  };

  const getStatusLabel = (status: typeof courierStatus) => {
    switch (status) {
      case 'ACTIVE': return 'Активен';
      case 'OFFLINE': return 'Не в сети';
      case 'ON_BREAK': return 'На перерыве';
      default: return 'Не в сети';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <h1 className="text-lg font-semibold text-gray-900">
            Панель управления
          </h1>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        {}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h2 className="font-medium text-gray-900 mb-3 text-sm uppercase tracking-wide">
            Текущий статус
          </h2>
          <div className="flex items-center gap-3 mb-4">
            <div className={`w-2.5 h-2.5 rounded-full ${getStatusColor(courierStatus)}`} />
            <span className="font-medium text-gray-900">{getStatusLabel(courierStatus)}</span>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={() => handleStatusChange('ACTIVE')}
              className={`p-3 rounded border transition-all text-sm font-medium ${
                courierStatus === 'ACTIVE'
                  ? 'border-green-600 bg-green-50 text-green-700'
                  : 'border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              Активен
            </button>

            <button
              onClick={() => handleStatusChange('ON_BREAK')}
              className={`p-3 rounded border transition-all text-sm font-medium ${
                courierStatus === 'ON_BREAK'
                  ? 'border-yellow-500 bg-yellow-50 text-yellow-700'
                  : 'border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              Перерыв
            </button>

            <button
              onClick={() => handleStatusChange('OFFLINE')}
              className={`p-3 rounded border transition-all text-sm font-medium ${
                courierStatus === 'OFFLINE'
                  ? 'border-gray-400 bg-gray-50 text-gray-700'
                  : 'border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              Офлайн
            </button>
          </div>
        </div>

        {}
        {activeShift ? (
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-medium text-gray-900 text-sm uppercase tracking-wide flex items-center gap-2">
                <Clock className="w-4 h-4 text-gray-500" />
                Активная смена
              </h2>
              <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-medium">
                В работе
              </span>
            </div>

            {}
            <div className="bg-gray-50 border border-gray-200 rounded p-4 mb-4">
              <div className="text-center">
                <div className="text-2xl font-semibold text-gray-900 mb-1 font-mono">
                  {shiftDuration}
                </div>
                <div className="text-xs text-gray-600 uppercase tracking-wide">Продолжительность</div>
              </div>
            </div>

            {}
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="bg-gray-50 border border-gray-200 rounded p-3">
                <div className="flex items-center justify-between">
                  <Package className="w-5 h-5 text-gray-400" />
                  <div className="text-right">
                    <div className="text-xl font-semibold text-gray-900">
                      {activeShift.orders_completed || 0}
                    </div>
                    <div className="text-xs text-gray-600">Заказов</div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 border border-gray-200 rounded p-3">
                <div className="flex items-center justify-between">
                  <MapPin className="w-5 h-5 text-gray-400" />
                  <div className="text-right">
                    <div className="text-xl font-semibold text-gray-900">
                      {activeShift.total_distance_km?.toFixed(1) || '0.0'}
                    </div>
                    <div className="text-xs text-gray-600">км</div>
                  </div>
                </div>
              </div>
            </div>

            <Button
              variant="danger"
              className="w-full"
              icon={<Square className="w-4 h-4" />}
              onClick={handleEndShift}
            >
              Завершить смену
            </Button>
          </div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="text-center">
              <Clock className="w-16 h-16 mx-auto mb-3 text-gray-300" />
              <h3 className="text-base font-semibold text-gray-900 mb-2">
                Смена не начата
              </h3>
              <p className="text-gray-600 text-sm mb-4">
                Начните рабочую смену для приёма заказов
              </p>
              <Button
                variant="primary"
                className="w-full"
                icon={<Play className="w-4 h-4" />}
                onClick={handleStartShift}
              >
                Начать смену
              </Button>
            </div>
          </div>
        )}

        {}
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => navigate(COURIER_ROUTES.ORDERS)}
            className="bg-white border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center justify-between mb-2">
              <Package className="w-5 h-5 text-blue-600" />
              <div className="text-2xl font-semibold text-blue-600">3</div>
            </div>
            <div className="text-sm font-medium text-gray-900">Доступные заказы</div>
          </button>

          <button
            onClick={() => navigate(`${COURIER_ROUTES.ORDERS}?filter=my`)}
            className="bg-white border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center justify-between mb-2">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <div className="text-2xl font-semibold text-green-600">1</div>
            </div>
            <div className="text-sm font-medium text-gray-900">Мои заказы</div>
          </button>
        </div>

        {}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex gap-3">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <span className="text-blue-600 text-sm font-semibold">i</span>
              </div>
            </div>
            <div className="flex-1">
              <h3 className="font-medium text-blue-900 mb-1 text-sm">Важно</h3>
              <p className="text-sm text-blue-800">
                Обновляйте статус заказа своевременно, чтобы клиенты были в курсе вашего местоположения
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
