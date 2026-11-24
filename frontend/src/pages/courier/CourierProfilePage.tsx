import { SessionSettings } from '@/shared/components/SessionSettings';
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Star, Package, CheckCircle, Clock, Award, Camera, User, Loader2, RefreshCw, Settings, Bell, Moon, Volume2, ChevronRight, X, Coffee, Trophy, Zap } from 'lucide-react';
import { Card } from '@/shared/components/Card';
import { Badge } from '@/shared/components/Badge';
import { Button } from '@/shared/components/Button';
import { usersApi } from '@/lib/api/users';
import { courierApi } from '@/lib/api/courier';
import type { User as UserType } from '@/shared/types';

type CourierStatus = 'ACTIVE' | 'OFFLINE' | 'ON_BREAK' | 'NOT_AVAILABLE';

const COURIER_STATUS_LABELS: Record<CourierStatus, string> = {
  ACTIVE: 'На линии',
  OFFLINE: 'Офлайн',
  ON_BREAK: 'На перерыве',
  NOT_AVAILABLE: 'Недоступен',
};

const COURIER_STATUS_COLORS: Record<CourierStatus, string> = {
  ACTIVE: 'bg-green-100 text-green-700 border-green-200',
  OFFLINE: 'bg-gray-100 text-gray-700 border-gray-200',
  ON_BREAK: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  NOT_AVAILABLE: 'bg-red-100 text-red-700 border-red-200',
};

export const CourierProfilePage = () => {
  const [courier, setCourier] = useState<UserType | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [changingStatus, setChangingStatus] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [settings, setSettings] = useState({
    notifications: true,
    sound: true,
    darkMode: false,
    autoAcceptOrders: false,
  });

  useEffect(() => {
    const savedSettings = localStorage.getItem('courier_settings');
    if (savedSettings) {
      try {
        setSettings(JSON.parse(savedSettings));
      } catch (e) {
        console.error('Failed to parse settings:', e);
      }
    }
  }, []);

  const updateSetting = (key: keyof typeof settings, value: boolean) => {
    const newSettings = { ...settings, [key]: value };
    setSettings(newSettings);
    localStorage.setItem('courier_settings', JSON.stringify(newSettings));
  };

  const loadData = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const courierData = await usersApi.getMe();
      setCourier(courierData);
    } catch (err) {
      console.error('Failed to load profile:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleStatusChange = async (newStatus: CourierStatus) => {
    if (changingStatus) return;
    try {
      setChangingStatus(true);
      await courierApi.updateStatus(newStatus);
      setCourier(prev => prev ? { ...prev, courier_status: newStatus } : null);
    } catch (err) {
      console.error('Failed to change status:', err);
      alert('Не удалось изменить статус');
    } finally {
      setChangingStatus(false);
    }
  };

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        alert('Пожалуйста, выберите изображение');
        return;
      }

      if (file.size > 5 * 1024 * 1024) {
        alert('Размер файла не должен превышать 5MB');
        return;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        setAvatarUrl(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const completionRate = courier && courier.total_orders > 0
    ? ((courier.completed_orders / courier.total_orders) * 100).toFixed(0)
    : '0';

  const stats = courier ? [
    { icon: <Package className='w-5 h-5' />, label: 'Всего заказов', value: courier.total_orders || 0, color: 'text-blue-600' },
    { icon: <CheckCircle className='w-5 h-5' />, label: 'Выполнено', value: courier.completed_orders || 0, color: 'text-green-600' },
    { icon: <Star className="w-5 h-5" />, label: 'Рейтинг', value: courier.rating?.toFixed(1) || '—', color: 'text-yellow-600' },
    { icon: <Award className="w-5 h-5" />, label: 'Выполнение', value: `${completionRate}%`, color: 'text-purple-600' },
  ] : [];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 bg-gradient-to-br from-green-400 to-emerald-500 rounded-full flex items-center justify-center animate-pulse">
            <Loader2 className="w-8 h-8 text-white animate-spin" />
          </div>
          <span className="text-green-700 font-medium">Загрузка профиля...</span>
        </div>
      </div>
    );
  }

  const courierStatus = (courier?.courier_status as CourierStatus) || 'OFFLINE';

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
      {}
      <div className="bg-white/80 backdrop-blur-md border-b border-green-100 sticky top-0 z-10 shadow-sm">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
              Мой профиль
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
        <Card className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-100">
          <div className="text-center">
            {}
            <div className="relative w-24 h-24 mx-auto mb-3">
              {avatarUrl ? (
                <img
                  src={avatarUrl}
                  alt={`${courier?.first_name} ${courier?.last_name}`}
                  className="w-24 h-24 object-cover rounded-full shadow-md"
                />
              ) : (
                <div className="w-24 h-24 bg-gradient-to-br from-green-100 to-emerald-100 rounded-full flex items-center justify-center shadow-md">
                  <div className="w-16 h-16 bg-gradient-to-br from-green-200 to-emerald-200 rounded-full flex items-center justify-center">
                    <User className="w-9 h-9 text-green-600" strokeWidth={2} />
                  </div>
                </div>
              )}

              {}
              <button
                onClick={handleAvatarClick}
                className="absolute bottom-0 right-0 w-8 h-8 bg-green-600 rounded-full flex items-center justify-center text-white hover:bg-green-700 shadow-lg transition-all hover:scale-105 active:scale-95"
                aria-label="Изменить фото"
              >
                <Camera className="w-4 h-4" />
              </button>

              {}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="hidden"
              />
            </div>

            <h2 className="text-2xl font-bold text-gray-900 mb-1">
              {courier?.first_name} {courier?.last_name}
            </h2>
            <Badge className={`inline-flex items-center gap-1.5 ${COURIER_STATUS_COLORS[courierStatus]}`}>
              {courierStatus === 'ACTIVE' && <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />}
              {courierStatus === 'ON_BREAK' && <Coffee className="w-3 h-3" />}
              {courierStatus === 'OFFLINE' && <span className="w-2 h-2 rounded-full bg-gray-400" />}
              {COURIER_STATUS_LABELS[courierStatus]}
            </Badge>
          </div>
        </Card>

        {}
        <Card className="border-2 border-green-100">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-900">Мой статус</h2>
            {changingStatus && <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />}
          </div>
          <div className="bg-gray-100/80 rounded-2xl p-1 flex gap-1">
            {([
              { status: 'ACTIVE' as CourierStatus, label: 'На линии', dot: 'bg-green-500' as string | undefined, icon: undefined as React.ReactNode, activeClass: 'text-green-700' },
              { status: 'ON_BREAK' as CourierStatus, label: 'Перерыв', dot: undefined as string | undefined, icon: <Coffee className="w-3.5 h-3.5" /> as React.ReactNode, activeClass: 'text-amber-700' },
              { status: 'OFFLINE' as CourierStatus, label: 'Офлайн', dot: 'bg-gray-400' as string | undefined, icon: undefined as React.ReactNode, activeClass: 'text-gray-700' },
            ]).map(({ status, label, dot, icon, activeClass }) => {
              const isActive = courierStatus === status;
              return (
                <button
                  key={status}
                  onClick={() => handleStatusChange(status)}
                  disabled={changingStatus}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? `bg-white shadow-sm ${activeClass}`
                      : 'text-gray-400 hover:text-gray-600 active:bg-white/50'
                  }`}
                >
                  {icon ?? (
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dot} ${isActive && status === 'ACTIVE' ? 'animate-pulse' : ''}`} />
                  )}
                  {label}
                </button>
              );
            })}
          </div>
        </Card>

        {}
        <Card className="border-2 border-green-100">
          <h2 className="font-semibold text-gray-900 mb-4">Статистика работы</h2>
          <div className="grid grid-cols-2 gap-3">
            {stats.map((stat, index) => (
              <div
                key={index}
                className="bg-gradient-to-br from-gray-50 to-white rounded-xl p-4 border border-gray-100"
              >
                <div className={`${stat.color} mb-2`}>
                  {stat.icon}
                </div>
                <div className="text-2xl font-bold text-gray-900 mb-1">
                  {stat.value}
                </div>
                <div className="text-xs text-gray-600">{stat.label}</div>
              </div>
            ))}
          </div>
        </Card>

        {}
        <Card className="border-2 border-green-100">
          <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Star className="w-5 h-5 text-yellow-500" />
            Рейтинг и отзывы
          </h2>

          <div className="bg-gradient-to-br from-yellow-50 to-orange-50 rounded-xl p-4 mb-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-3xl font-bold text-gray-900">{courier?.rating?.toFixed(1) || '—'}</div>
                <div className="flex items-center gap-1 mt-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <Star
                      key={star}
                      className={`w-4 h-4 ${
                        star <= Math.round(courier?.rating || 0)
                          ? 'fill-yellow-400 text-yellow-400'
                          : 'text-gray-300'
                      }`}
                    />
                  ))}
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-600">Средняя оценка</div>
                <div className="text-xs text-gray-500">Из 5.0</div>
              </div>
            </div>
          </div>

          <div className="text-center text-sm text-gray-600">
            <Clock className="w-4 h-4 inline mr-1" />
            На основе {courier?.completed_orders || 0} выполненных заказов
          </div>
        </Card>

        {}
        <Card className="border-2 border-green-100">
          <h2 className="font-semibold text-gray-900 mb-4">Контактная информация</h2>
          <div className="space-y-3">
            {courier?.phone && (
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-gray-600">Телефон</span>
                <span className="font-medium text-gray-900">{courier.phone}</span>
              </div>
            )}
            {courier?.email && (
              <div className="flex items-center justify-between py-2">
                <span className="text-gray-600">Email</span>
                <span className="font-medium text-gray-900">{courier.email}</span>
              </div>
            )}
            {courier?.telegram_id && (
              <div className="flex items-center justify-between py-2 border-t border-gray-100">
                <span className="text-gray-600">Telegram ID</span>
                <span className="font-medium text-gray-900">{courier.telegram_id}</span>
              </div>
            )}
          </div>
        </Card>

        {}
        <Card className="bg-gradient-to-br from-purple-50 to-pink-50 border-2 border-purple-100">
          <h2 className="font-semibold text-gray-900 mb-4">Достижения</h2>
          <div className="grid grid-cols-3 gap-2">
            {[
              { icon: <Zap className="w-6 h-6" />, label: 'Первые 10', unlocked: (courier?.completed_orders || 0) >= 10, color: 'text-blue-500' },
              { icon: <Star className="w-6 h-6" />, label: 'Топ рейтинг', unlocked: (courier?.rating || 0) >= 4.5, color: 'text-yellow-500' },
              { icon: <Trophy className="w-6 h-6" />, label: 'Первая сотня', unlocked: (courier?.completed_orders || 0) >= 100, color: 'text-amber-500' },
            ].map(({ icon, label, unlocked, color }) => (
              <div key={label} className={`text-center p-3 rounded-xl transition-all ${unlocked ? 'bg-white shadow-sm' : 'bg-white/40 opacity-40'}`}>
                <div className={`flex justify-center mb-1.5 ${unlocked ? color : 'text-gray-400'}`}>{icon}</div>
                <div className="text-xs font-medium text-gray-700">{label}</div>
              </div>
            ))}
          </div>
        </Card>

        {}
        <Card className="border-2 border-gray-100">
          <div className="space-y-2">
            <Button
              variant="ghost"
              className="w-full justify-between text-gray-700 hover:bg-gray-50"
              onClick={() => setShowSettings(true)}
            >
              <div className="flex items-center">
                <Settings className="w-5 h-5 mr-3" />
                Настройки
              </div>
              <ChevronRight className="w-5 h-5 text-gray-400" />
            </Button>
          </div>
        </Card>
      </div>

      {}
      <div className="max-w-2xl mx-auto px-4 pb-6"><SessionSettings /></div>

      {showSettings && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
          {}
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setShowSettings(false)}
          />

          {}
          <div className="relative bg-white w-full sm:w-96 sm:rounded-2xl rounded-t-2xl max-h-[80vh] overflow-auto">
            {}
            <div className="sticky top-0 bg-white border-b border-gray-100 px-4 py-4 flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900">Настройки</h2>
              <button
                onClick={() => setShowSettings(false)}
                className="p-2 hover:bg-gray-100 rounded-full"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {}
            <div className="p-4 space-y-4">
              {}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-gray-500 uppercase">Уведомления</h3>

                <div className="flex items-center justify-between py-2">
                  <div className="flex items-center gap-3">
                    <Bell className="w-5 h-5 text-gray-600" />
                    <div>
                      <div className="font-medium text-gray-900">Push-уведомления</div>
                      <div className="text-xs text-gray-500">О новых заказах</div>
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.notifications}
                      onChange={(e) => updateSetting('notifications', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-500"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between py-2">
                  <div className="flex items-center gap-3">
                    <Volume2 className="w-5 h-5 text-gray-600" />
                    <div>
                      <div className="font-medium text-gray-900">Звук</div>
                      <div className="text-xs text-gray-500">Звуковые оповещения</div>
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.sound}
                      onChange={(e) => updateSetting('sound', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-500"></div>
                  </label>
                </div>
              </div>

              {}
              <div className="space-y-3 pt-4 border-t border-gray-100">
                <h3 className="text-sm font-semibold text-gray-500 uppercase">Внешний вид</h3>

                <div className="flex items-center justify-between py-2">
                  <div className="flex items-center gap-3">
                    <Moon className="w-5 h-5 text-gray-600" />
                    <div>
                      <div className="font-medium text-gray-900">Тёмная тема</div>
                      <div className="text-xs text-gray-500">Скоро будет доступна</div>
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer opacity-50">
                    <input
                      type="checkbox"
                      checked={settings.darkMode}
                      onChange={(e) => updateSetting('darkMode', e.target.checked)}
                      className="sr-only peer"
                      disabled
                    />
                    <div className="w-11 h-6 bg-gray-200 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-500"></div>
                  </label>
                </div>
              </div>

              {}
              <div className="space-y-3 pt-4 border-t border-gray-100">
                <h3 className="text-sm font-semibold text-gray-500 uppercase">О приложении</h3>

                <div className="flex items-center justify-between py-2">
                  <span className="text-gray-600">Версия</span>
                  <span className="text-gray-900">1.0.0</span>
                </div>

                <div className="flex items-center justify-between py-2">
                  <span className="text-gray-600">Курьер ID</span>
                  <span className="text-gray-900 text-xs">{courier?.id?.slice(0, 8)}...</span>
                </div>
              </div>
            </div>

            {}
            <div className="sticky bottom-0 bg-white border-t border-gray-100 p-4">
              <Button
                variant="primary"
                className="w-full"
                onClick={() => setShowSettings(false)}
              >
                Готово
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
