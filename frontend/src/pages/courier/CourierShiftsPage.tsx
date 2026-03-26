import { useState, useEffect, useCallback } from 'react';
import { Clock, Calendar, Package, Play, Square, ChevronRight, RefreshCw, Loader2, AlertCircle, TrendingUp } from 'lucide-react';
import { Card } from '@/shared/components/Card';
import { Button } from '@/shared/components/Button';
import { Badge } from '@/shared/components/Badge';
import { courierApi, type CourierShift } from '@/lib/api/courier';

export const CourierShiftsPage = () => {
  const [activeShift, setActiveShift] = useState<CourierShift | null>(null);
  const [shiftHistory, setShiftHistory] = useState<CourierShift[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [togglingShift, setTogglingShift] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [shiftDuration, setShiftDuration] = useState('0ч 0м');

  const loadData = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const [currentShift, history] = await Promise.all([
        courierApi.getActiveShift().catch(() => null),
        courierApi.getShifts({ limit: 20 }).catch(() => ({ items: [] })),
      ]);

      setActiveShift(currentShift);
      setShiftHistory(history.items || []);
    } catch (err) {
      console.error('Failed to load shifts:', err);
      setError('Ошибка загрузки данных');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (!activeShift) {
      setShiftDuration('0ч 0м');
      return;
    }

    const updateDuration = () => {
      const start = new Date(activeShift.started_at);
      const now = new Date();
      const diff = Math.max(0, Math.floor((now.getTime() - start.getTime()) / 1000 / 60));
      const hours = Math.floor(diff / 60);
      const minutes = diff % 60;
      setShiftDuration(`${hours}ч ${minutes}м`);
    };

    updateDuration();
    const interval = setInterval(updateDuration, 60000);
    return () => clearInterval(interval);
  }, [activeShift]);

  const handleStartShift = async () => {
    try {
      setTogglingShift(true);
      const newShift = await courierApi.startShift();
      setActiveShift(newShift);
      await loadData(true);
    } catch (err) {
      console.error('Failed to start shift:', err);
      alert('Не удалось начать смену');
    } finally {
      setTogglingShift(false);
    }
  };

  const handleEndShift = async () => {
    try {
      setTogglingShift(true);
      await courierApi.endShift();
      setActiveShift(null);
      await loadData(true);
    } catch (err) {
      console.error('Failed to end shift:', err);
      alert('Не удалось завершить смену');
    } finally {
      setTogglingShift(false);
    }
  };

  const formatDuration = (shift: CourierShift) => {
    if (shift.duration_hours !== null) {
      const hours = Math.floor(shift.duration_hours);
      const minutes = Math.round((shift.duration_hours - hours) * 60);
      return `${hours}ч ${minutes}м`;
    }
    
    const start = new Date(shift.started_at);
    const end = shift.ended_at ? new Date(shift.ended_at) : new Date();
    const diff = Math.floor((end.getTime() - start.getTime()) / 1000 / 60);
    const hours = Math.floor(diff / 60);
    const minutes = diff % 60;
    return `${hours}ч ${minutes}м`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
    });
  };

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const weekStats = {
    totalShifts: shiftHistory.filter(s => {
      const shiftDate = new Date(s.started_at);
      const weekAgo = new Date();
      weekAgo.setDate(weekAgo.getDate() - 7);
      return shiftDate >= weekAgo;
    }).length,
    totalHours: shiftHistory.reduce((acc, s) => {
      const shiftDate = new Date(s.started_at);
      const weekAgo = new Date();
      weekAgo.setDate(weekAgo.getDate() - 7);
      if (shiftDate >= weekAgo && s.duration_hours) {
        return acc + s.duration_hours;
      }
      return acc;
    }, 0),
    totalOrders: shiftHistory.reduce((acc, s) => {
      const shiftDate = new Date(s.started_at);
      const weekAgo = new Date();
      weekAgo.setDate(weekAgo.getDate() - 7);
      if (shiftDate >= weekAgo) {
        return acc + (s.orders_completed || 0);
      }
      return acc;
    }, 0),
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 bg-gradient-to-br from-green-400 to-emerald-500 rounded-full flex items-center justify-center animate-pulse">
            <Loader2 className="w-8 h-8 text-white animate-spin" />
          </div>
          <span className="text-green-700 font-medium">Загрузка смен...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
        <div className="text-center p-6">
          <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-10 h-10 text-red-500" />
          </div>
          <div className="text-red-500 text-xl font-bold mb-2">Ошибка</div>
          <div className="text-gray-600 mb-4">{error}</div>
          <Button onClick={() => loadData()}>Попробовать снова</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
      {}
      <div className="bg-white/80 backdrop-blur-md border-b border-green-100 sticky top-0 z-10 shadow-sm">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
              ⏰ Мои смены
            </h1>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => loadData(true)}
              disabled={refreshing}
              className="text-green-600"
            >
              <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        {}
        <Card className={activeShift ? "bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-400" : "border-2 border-green-100"}>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Текущая смена</h2>
              <Badge className={activeShift ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"}>
                {activeShift ? '🟢 Активна' : '⚫ Не начата'}
              </Badge>
            </div>

            {activeShift ? (
              <div className="space-y-4">
                {}
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-white/70 rounded-lg p-3">
                    <div className="flex items-center gap-2 text-gray-600 mb-1">
                      <Clock className="w-4 h-4" />
                      <span className="text-xs">Длительность</span>
                    </div>
                    <div className="text-xl font-bold text-gray-900">
                      {shiftDuration}
                    </div>
                  </div>

                  <div className="bg-white/70 rounded-lg p-3">
                    <div className="flex items-center gap-2 text-gray-600 mb-1">
                      <Package className="w-4 h-4" />
                      <span className="text-xs">Заказов</span>
                    </div>
                    <div className="text-xl font-bold text-gray-900">
                      {activeShift.orders_completed || 0}
                    </div>
                  </div>
                </div>

                <div className="text-sm text-gray-600">
                  Начало: {formatTime(activeShift.started_at)}
                </div>

                <Button
                  onClick={handleEndShift}
                  disabled={togglingShift}
                  className="w-full bg-red-600 hover:bg-red-700"
                >
                  {togglingShift ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Square className="w-4 h-4 mr-2" />
                  )}
                  Завершить смену
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-gray-600 text-sm">
                  Начните смену, чтобы получать заказы и отслеживать свою работу
                </p>

                <Button
                  onClick={handleStartShift}
                  disabled={togglingShift}
                  className="w-full bg-green-600 hover:bg-green-700"
                >
                  {togglingShift ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4 mr-2" />
                  )}
                  Начать смену
                </Button>
              </div>
            )}
          </div>
        </Card>

        {}
        <Card className="bg-gradient-to-br from-blue-50 to-cyan-50 border-2 border-blue-100">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-600" />
              <h3 className="font-semibold text-gray-900">Статистика за 7 дней</h3>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="bg-white/70 rounded-lg p-3">
                <div className="text-sm text-gray-600 mb-1">Всего смен</div>
                <div className="text-2xl font-bold text-gray-900">{weekStats.totalShifts}</div>
              </div>

              <div className="bg-white/70 rounded-lg p-3">
                <div className="text-sm text-gray-600 mb-1">Всего часов</div>
                <div className="text-2xl font-bold text-gray-900">{weekStats.totalHours.toFixed(1)}ч</div>
              </div>

              <div className="bg-white/70 rounded-lg p-3">
                <div className="text-sm text-gray-600 mb-1">Заказов</div>
                <div className="text-2xl font-bold text-gray-900">{weekStats.totalOrders}</div>
              </div>

              <div className="bg-white/70 rounded-lg p-3">
                <div className="text-sm text-gray-600 mb-1">Ср. за смену</div>
                <div className="text-2xl font-bold text-gray-900">
                  {weekStats.totalShifts > 0
                    ? Math.round(weekStats.totalOrders / weekStats.totalShifts)
                    : 0}
                </div>
              </div>
            </div>
          </div>
        </Card>

        {}
        <Card className="border-2 border-green-100">
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-gray-600" />
              <h2 className="text-lg font-semibold text-gray-900">История смен</h2>
            </div>

            {shiftHistory.length === 0 ? (
              <div className="text-center py-8">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Clock className="w-8 h-8 text-gray-400" />
                </div>
                <div className="text-gray-500 font-medium mb-1">История пуста</div>
                <div className="text-sm text-gray-400">
                  Здесь появятся ваши завершённые смены
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                {shiftHistory.map((shift) => (
                  <div
                    key={shift.id}
                    className="bg-gradient-to-r from-gray-50 to-white rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="font-medium text-gray-900">
                            {formatDate(shift.started_at)}
                          </span>
                          <Badge className={shift.ended_at
                            ? "bg-green-100 text-green-700 text-xs"
                            : "bg-yellow-100 text-yellow-700 text-xs"
                          }>
                            {shift.ended_at ? 'Завершена' : 'Активна'}
                          </Badge>
                        </div>

                        <div className="flex items-center gap-4 text-sm text-gray-600">
                          <div className="flex items-center gap-1">
                            <Clock className="w-4 h-4" />
                            <span>{formatDuration(shift)}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Package className="w-4 h-4" />
                            <span>{shift.orders_completed || 0} заказов</span>
                          </div>
                        </div>

                        <div className="text-xs text-gray-500 mt-1">
                          {formatTime(shift.started_at)}
                          {shift.ended_at && ` — ${formatTime(shift.ended_at)}`}
                        </div>
                      </div>

                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};
