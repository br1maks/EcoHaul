import { errorDetail } from '@/lib/api/errors';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Truck,
  Phone,
  Mail,
  MapPin,
  MessageSquare,
  CheckCircle,
  Clock,
  XCircle,
  Loader2,
  ArrowLeft,
  Car,
  Bike,
} from 'lucide-react';
import { Card } from '@/shared/components/Card';
import { Button } from '@/shared/components/Button';
import { courierApplicationsApi, type CourierApplication, type CreateCourierApplicationData } from '@/lib/api/courierApplications';
import { usersApi } from '@/lib/api/users';

type TransportType = 'car' | 'bike' | 'walk' | '';

export const BecomeCourierPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [existingApplication, setExistingApplication] = useState<CourierApplication | null>(null);
  const [isAlreadyCourier, setIsAlreadyCourier] = useState(false);

  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [hasTransport, setHasTransport] = useState(false);
  const [transportType, setTransportType] = useState<TransportType>('');
  const [workArea, setWorkArea] = useState('');
  const [message, setMessage] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    loadExistingApplication();
  }, []);

  const loadExistingApplication = async () => {
    try {
      setLoading(true);

      const user = await usersApi.getMe();
      if (user.role === 'COURIER') {
        setIsAlreadyCourier(true);
        setLoading(false);
        return;
      }

      const application = await courierApplicationsApi.getMyApplication();
      setExistingApplication(application);
    } catch (err) {
      console.error('Failed to load application:', err);
    } finally {
      setLoading(false);
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!phone.trim()) {
      newErrors.phone = 'Укажите номер телефона';
    } else if (!/^\+?[0-9]{10,15}$/.test(phone.replace(/\s/g, ''))) {
      newErrors.phone = 'Неверный формат номера';
    }

    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = 'Неверный формат email';
    }

    if (hasTransport && !transportType) {
      newErrors.transportType = 'Укажите тип транспорта';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    try {
      setSubmitting(true);

      const data: CreateCourierApplicationData = {
        phone: phone.replace(/\s/g, ''),
        email: email || undefined,
        has_transport: hasTransport,
        transport_type: transportType || undefined,
        work_area: workArea || undefined,
        message: message || undefined,
      };

      const application = await courierApplicationsApi.create(data);
      setExistingApplication(application);
    } catch (err: unknown) {
      console.error('Failed to submit application:', err);
      const detail = errorDetail(err);
      if (detail) {
        alert(detail);
      } else {
        alert('Не удалось отправить заявку');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const getTransportLabel = (type: string) => {
    switch (type) {
      case 'car': return 'Автомобиль';
      case 'bike': return 'Велосипед';
      case 'walk': return 'Пешком';
      default: return type;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-green-600 animate-spin" />
          <span className="text-green-700">Загрузка...</span>
        </div>
      </div>
    );
  }

  if (isAlreadyCourier) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
        {}
        <div className="bg-white/80 backdrop-blur-md border-b border-green-100 sticky top-0 z-10">
          <div className="max-w-2xl mx-auto px-4 py-4">
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate(-1)}
                className="p-2 hover:bg-gray-100 rounded-full"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <h1 className="text-xl font-bold text-gray-900">Стать курьером</h1>
            </div>
          </div>
        </div>

        <div className="max-w-2xl mx-auto px-4 py-6">
          <Card className="border-2 border-green-100 text-center py-8">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Truck className="w-10 h-10 text-green-600" />
            </div>
            <h2 className="text-xl font-bold text-green-700 mb-2">Вы уже курьер!</h2>
            <p className="text-gray-600 mb-6">
              Вы уже зарегистрированы как курьер в нашей системе.
            </p>
            <Button
              onClick={() => navigate('/courier')}
              className="bg-green-600 hover:bg-green-700"
            >
              <Truck className="w-5 h-5 mr-2" />
              Перейти в панель курьера
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  if (existingApplication) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
        {}
        <div className="bg-white/80 backdrop-blur-md border-b border-green-100 sticky top-0 z-10">
          <div className="max-w-2xl mx-auto px-4 py-4">
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate(-1)}
                className="p-2 hover:bg-gray-100 rounded-full"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <h1 className="text-xl font-bold text-gray-900">Заявка на курьера</h1>
            </div>
          </div>
        </div>

        <div className="max-w-2xl mx-auto px-4 py-6">
          <Card className="border-2 border-green-100">
            {}
            <div className="text-center mb-6">
              {existingApplication.status === 'PENDING' && (
                <>
                  <div className="w-20 h-20 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Clock className="w-10 h-10 text-yellow-600" />
                  </div>
                  <h2 className="text-xl font-bold text-gray-900 mb-2">Заявка на рассмотрении</h2>
                  <p className="text-gray-600">
                    Мы рассмотрим вашу заявку и свяжемся с вами
                  </p>
                </>
              )}

              {existingApplication.status === 'APPROVED' && (
                <>
                  <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle className="w-10 h-10 text-green-600" />
                  </div>
                  <h2 className="text-xl font-bold text-green-700 mb-2">Заявка одобрена!</h2>
                  <p className="text-gray-600 mb-4">
                    Поздравляем! Теперь вы можете работать курьером.
                  </p>
                  <Button
                    onClick={() => navigate('/courier')}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    <Truck className="w-5 h-5 mr-2" />
                    Перейти в панель курьера
                  </Button>
                </>
              )}

              {existingApplication.status === 'REJECTED' && (
                <>
                  <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <XCircle className="w-10 h-10 text-red-600" />
                  </div>
                  <h2 className="text-xl font-bold text-red-700 mb-2">Заявка отклонена</h2>
                  {existingApplication.admin_comment && (
                    <p className="text-gray-600 mb-4">
                      Причина: {existingApplication.admin_comment}
                    </p>
                  )}
                  <p className="text-sm text-gray-500">
                    Вы можете подать новую заявку позже
                  </p>
                </>
              )}
            </div>

            {}
            <div className="border-t border-gray-100 pt-4 space-y-3">
              <h3 className="font-semibold text-gray-900">Данные заявки</h3>

              <div className="flex items-center gap-3 text-sm">
                <Phone className="w-4 h-4 text-gray-400" />
                <span>{existingApplication.phone}</span>
              </div>

              {existingApplication.email && (
                <div className="flex items-center gap-3 text-sm">
                  <Mail className="w-4 h-4 text-gray-400" />
                  <span>{existingApplication.email}</span>
                </div>
              )}

              {existingApplication.has_transport && existingApplication.transport_type && (
                <div className="flex items-center gap-3 text-sm">
                  <Car className="w-4 h-4 text-gray-400" />
                  <span>{getTransportLabel(existingApplication.transport_type)}</span>
                </div>
              )}

              {existingApplication.work_area && (
                <div className="flex items-center gap-3 text-sm">
                  <MapPin className="w-4 h-4 text-gray-400" />
                  <span>{existingApplication.work_area}</span>
                </div>
              )}

              <div className="text-xs text-gray-500 pt-2">
                Подана: {new Date(existingApplication.created_at).toLocaleDateString('ru-RU', {
                  day: 'numeric',
                  month: 'long',
                  year: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
      {}
      <div className="bg-white/80 backdrop-blur-md border-b border-green-100 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(-1)}
              className="p-2 hover:bg-gray-100 rounded-full"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h1 className="text-xl font-bold text-gray-900">Стать курьером</h1>
          </div>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        {}
        <Card className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-100">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
              <Truck className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <h2 className="font-bold text-gray-900">Присоединяйтесь к команде</h2>
              <p className="text-sm text-gray-600">Работайте курьером EcoHaul</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white/70 rounded-lg p-3">
              <div className="text-2xl mb-1">💰</div>
              <div className="text-sm font-medium">Гибкий заработок</div>
            </div>
            <div className="bg-white/70 rounded-lg p-3">
              <div className="text-2xl mb-1">🕐</div>
              <div className="text-sm font-medium">Свободный график</div>
            </div>
            <div className="bg-white/70 rounded-lg p-3">
              <div className="text-2xl mb-1">📱</div>
              <div className="text-sm font-medium">Удобное приложение</div>
            </div>
            <div className="bg-white/70 rounded-lg p-3">
              <div className="text-2xl mb-1">🚀</div>
              <div className="text-sm font-medium">Быстрый старт</div>
            </div>
          </div>
        </Card>

        {}
        <form onSubmit={handleSubmit}>
          <Card className="border-2 border-green-100 space-y-4">
            <h2 className="font-semibold text-gray-900">Заполните заявку</h2>

            {}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Телефон *
              </label>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+375 29 123 45 67"
                  className={`w-full pl-10 pr-4 py-3 border rounded-xl focus:ring-2 focus:ring-green-500 focus:border-green-500 ${
                    errors.phone ? 'border-red-300' : 'border-gray-200'
                  }`}
                />
              </div>
              {errors.phone && (
                <p className="text-red-500 text-sm mt-1">{errors.phone}</p>
              )}
            </div>

            {}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email (необязательно)
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="email@example.com"
                  className={`w-full pl-10 pr-4 py-3 border rounded-xl focus:ring-2 focus:ring-green-500 focus:border-green-500 ${
                    errors.email ? 'border-red-300' : 'border-gray-200'
                  }`}
                />
              </div>
              {errors.email && (
                <p className="text-red-500 text-sm mt-1">{errors.email}</p>
              )}
            </div>

            {}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Есть транспорт?
              </label>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setHasTransport(true);
                    if (!transportType) setTransportType('car');
                  }}
                  className={`flex-1 py-3 px-4 rounded-xl border-2 transition-all ${
                    hasTransport
                      ? 'border-green-500 bg-green-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  Да
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setHasTransport(false);
                    setTransportType('walk');
                  }}
                  className={`flex-1 py-3 px-4 rounded-xl border-2 transition-all ${
                    !hasTransport
                      ? 'border-green-500 bg-green-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  Нет, пешком
                </button>
              </div>
            </div>

            {}
            {hasTransport && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Тип транспорта
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setTransportType('car')}
                    className={`p-3 rounded-xl border-2 transition-all ${
                      transportType === 'car'
                        ? 'border-green-500 bg-green-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <Car className="w-6 h-6 mx-auto mb-1" />
                    <div className="text-sm">Автомобиль</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setTransportType('bike')}
                    className={`p-3 rounded-xl border-2 transition-all ${
                      transportType === 'bike'
                        ? 'border-green-500 bg-green-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <Bike className="w-6 h-6 mx-auto mb-1" />
                    <div className="text-sm">Велосипед</div>
                  </button>
                </div>
                {errors.transportType && (
                  <p className="text-red-500 text-sm mt-1">{errors.transportType}</p>
                )}
              </div>
            )}

            {}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Предпочитаемый район работы (необязательно)
              </label>
              <div className="relative">
                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  value={workArea}
                  onChange={(e) => setWorkArea(e.target.value)}
                  placeholder="Например: Фрунзенский район"
                  className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-green-500 focus:border-green-500"
                />
              </div>
            </div>

            {}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Дополнительная информация (необязательно)
              </label>
              <div className="relative">
                <MessageSquare className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Расскажите о себе, опыте работы..."
                  rows={3}
                  className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-green-500 focus:border-green-500 resize-none"
                />
              </div>
            </div>

            {}
            <Button
              type="submit"
              disabled={submitting}
              className="w-full bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600"
            >
              {submitting ? (
                <Loader2 className="w-5 h-5 animate-spin mr-2" />
              ) : (
                <CheckCircle className="w-5 h-5 mr-2" />
              )}
              Отправить заявку
            </Button>
          </Card>
        </form>

        {}
        <Card className="bg-blue-50 border-2 border-blue-100">
          <div className="flex gap-3">
            <div className="text-2xl">ℹ️</div>
            <div className="text-sm text-gray-700">
              <p className="font-medium mb-1">Что дальше?</p>
              <p>После отправки заявки мы рассмотрим её и свяжемся с вами для уточнения деталей.</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};
