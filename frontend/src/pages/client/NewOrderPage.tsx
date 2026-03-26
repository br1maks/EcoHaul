import { useState, useEffect } from 'react';
import { addressesApi } from '@/lib/api/addresses';
import { ordersApi } from '@/features/orders/api/orders.api';
import { geocodeAddress, type GeocodeResult } from '@/lib/api/geocoding';
import type { GarbageType, Address } from '@/shared/types';
import { Button, Input, Card } from '@/shared/components';
import {
  ChevronLeft,
  MapPin,
  Package,
  Calendar,
  Plus,
  Check,
  Loader2,
  AlertCircle,
  Home,
  ChevronDown,
  SearchCheck,
  Trash2,
} from 'lucide-react';
import {
  GARBAGE_TYPE_LABELS,
  GARBAGE_TYPE_ICONS,
  MINSK_MIR_STREETS,
  SERVICE_AREA_NAME,
  SERVICE_AREA_DISTRICT,
} from '@/constants';

interface NewOrderPageProps {
  onBack?: () => void;
  onSuccess?: () => void;
}

export const NewOrderPage = ({ onBack, onSuccess }: NewOrderPageProps) => {
  
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [loadingAddresses, setLoadingAddresses] = useState(true);
  const [selectedAddressId, setSelectedAddressId] = useState<string | null>(null);

  const [showNewAddress, setShowNewAddress] = useState(false);
  const [newStreet, setNewStreet] = useState('');
  const [newHouse, setNewHouse] = useState('');
  const [newApartment, setNewApartment] = useState('');
  const [newEntrance, setNewEntrance] = useState('');
  const [newFloor, setNewFloor] = useState('');
  const [savingAddress, setSavingAddress] = useState(false);
  const [geocodedResult, setGeocodedResult] = useState<GeocodeResult | null>(null);

  const [garbageType, setGarbageType] = useState<GarbageType>('HOUSEHOLD');
  const [numberOfBags, setNumberOfBags] = useState('3');
  const [description, setDescription] = useState('');
  const [scheduledDate, setScheduledDate] = useState('');
  const [scheduledTime, setScheduledTime] = useState('');

  const [deletingAddressId, setDeletingAddressId] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const garbageTypes: GarbageType[] = ['HOUSEHOLD'];

  const WORK_START = 8;
  const WORK_END = 21;
  const ORDER_BUFFER_MIN = 30; 

  const todayStr = new Date().toISOString().split('T')[0];
  const isToday = scheduledDate === todayStr;

  const getMinTimeToday = () => {
    const now = new Date();
    now.setMinutes(now.getMinutes() + ORDER_BUFFER_MIN);
    let h = now.getHours();
    let m = now.getMinutes();
    
    if (m > 45) { h += 1; m = 0; }
    else if (m > 30) m = 45;
    else if (m > 15) m = 30;
    else if (m > 0) m = 15;
    return { h: Math.max(h, WORK_START), m };
  };

  const minDate = (() => {
    const mt = getMinTimeToday();
    if (mt.h > WORK_END || (mt.h === WORK_END && mt.m > 0)) {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      return tomorrow.toISOString().split('T')[0];
    }
    return todayStr;
  })();

  const minTimeToday = getMinTimeToday();

  const availableHours = Array.from({ length: WORK_END - WORK_START + 1 }, (_, i) => i + WORK_START)
    .filter(h => {
      if (!isToday) return true;
      return h >= minTimeToday.h && h <= WORK_END;
    });

  const selectedHour = scheduledTime ? parseInt(scheduledTime.split(':')[0]) : null;
  const availableMinutes = ['00', '15', '30', '45'].filter(m => {
    if (!isToday || selectedHour === null) return true;
    if (selectedHour > minTimeToday.h) return true;
    if (selectedHour === minTimeToday.h) return parseInt(m) >= minTimeToday.m;
    return false;
  });

  useEffect(() => {
    if (!scheduledTime || !scheduledDate) return;
    const [h, m] = scheduledTime.split(':').map(Number);
    if (h < WORK_START || h > WORK_END) { setScheduledTime(''); return; }
    if (isToday && (h < minTimeToday.h || (h === minTimeToday.h && m < minTimeToday.m))) {
      setScheduledTime('');
    }
  }, [scheduledDate]);

  useEffect(() => {
    const loadAddresses = async () => {
      try {
        setLoadingAddresses(true);
        const data = await addressesApi.getAll();
        setAddresses(data);

        const defaultAddr = data.find((a) => a.is_default);
        if (defaultAddr) {
          setSelectedAddressId(defaultAddr.id);
        } else if (data.length > 0) {
          setSelectedAddressId(data[0].id);
        }
      } catch (err) {
        console.error('Failed to load addresses:', err);
      } finally {
        setLoadingAddresses(false);
      }
    };
    loadAddresses();
  }, []);

  const handleDeleteAddress = async (id: string) => {
    try {
      setDeletingAddressId(id);
      await addressesApi.delete(id);
      const updated = addresses.filter((a) => a.id !== id);
      setAddresses(updated);
      if (selectedAddressId === id) {
        setSelectedAddressId(updated.length > 0 ? updated[0].id : null);
      }
    } catch (err) {
      console.error('Failed to delete address:', err);
    } finally {
      setDeletingAddressId(null);
    }
  };

  const handleVerifyAddress = async () => {
    if (!newStreet || !newHouse.trim()) {
      setError('Выберите улицу и укажите номер дома');
      return;
    }

    try {
      setSavingAddress(true);
      setError(null);

      const result = await geocodeAddress(newStreet, newHouse);
      if (!result) {
        setError('Адрес не найден. Проверьте номер дома.');
        return;
      }

      setGeocodedResult(result);
    } catch {
      setError('Ошибка проверки адреса. Попробуйте ещё раз.');
    } finally {
      setSavingAddress(false);
    }
  };

  const handleConfirmAddress = async () => {
    if (!geocodedResult) return;

    if (!newEntrance.trim()) {
      setError('Укажите номер подъезда');
      return;
    }

    try {
      setSavingAddress(true);
      setError(null);

      const fullAddress = `г. Минск, ул. ${newStreet}, д. ${newHouse}${newApartment ? `, кв. ${newApartment}` : ''}`;

      const newAddr = await addressesApi.create({
        latitude: geocodedResult.latitude,
        longitude: geocodedResult.longitude,
        full_address: fullAddress,
        city: 'Минск',
        district: SERVICE_AREA_DISTRICT,
        street: newStreet,
        house_number: newHouse,
        apartment: newApartment || undefined,
        entrance: newEntrance ? parseInt(newEntrance) : undefined,
        floor: newFloor ? parseInt(newFloor) : undefined,
        label: 'HOME',
        is_default: addresses.length === 0,
      });

      setAddresses([...addresses, newAddr]);
      setSelectedAddressId(newAddr.id);
      setShowNewAddress(false);
      setGeocodedResult(null);
      setNewStreet('');
      setNewHouse('');
      setNewApartment('');
      setNewEntrance('');
      setNewFloor('');
    } catch (err: any) {
      console.error('Failed to create address:', err);
      setError(err.response?.data?.detail || 'Ошибка создания адреса');
    } finally {
      setSavingAddress(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!selectedAddressId) {
      setError('Выберите адрес вывоза');
      return;
    }

    const bags = parseInt(numberOfBags);
    if (!bags || bags < 1 || bags > 50) {
      setError('Укажите количество мешков (от 1 до 50)');
      return;
    }

    if (!scheduledDate) {
      setError('Выберите дату вывоза');
      return;
    }
    if (!scheduledTime) {
      setError('Выберите время вывоза');
      return;
    }

    try {
      setLoading(true);

      const scheduledDateTime = `${scheduledDate}T${scheduledTime}:00+03:00`;

      await ordersApi.createOrder({
        pickup_address_id: selectedAddressId,
        garbage_type: garbageType,
        number_of_bags: bags,
        description: description || undefined,
        scheduled_time: scheduledDateTime,
      });

      setSuccess(true);
      setTimeout(() => {
        onSuccess?.();
      }, 1500);
    } catch (err: any) {
      console.error('Failed to create order:', err);
      setError(err.response?.data?.detail || 'Ошибка создания заказа');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50 flex items-center justify-center p-4">
        <Card className="border-2 border-green-300 max-w-md w-full text-center py-12">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Check className="w-10 h-10 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Заказ создан!</h2>
          <p className="text-gray-600">Ожидайте, курьер скоро возьмёт ваш заказ</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50 pb-32">
      {}
      <div className="bg-white/80 backdrop-blur-md border-b border-green-100 sticky top-0 z-10 shadow-sm">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            {onBack && (
              <button
                onClick={onBack}
                className="p-2 hover:bg-green-50 rounded-xl transition-all duration-200 hover:scale-105"
              >
                <ChevronLeft className="w-5 h-5 text-green-600" />
              </button>
            )}
            <h1 className="text-xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
              Новый заказ
            </h1>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        {}
        {error && (
          <div className="bg-red-50 border-2 border-red-200 text-red-700 px-4 py-3 rounded-2xl flex items-center gap-2">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span className="flex-1">{error}</span>
            <button
              type="button"
              onClick={() => setError(null)}
              className="hover:bg-red-100 p-1 rounded text-xl leading-none"
            >
              ×
            </button>
          </div>
        )}

        {}
        <Card className="border-2 border-green-100">
          <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <MapPin className="w-5 h-5 text-green-600" />
            Адрес вывоза
          </h2>

          {loadingAddresses ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 text-green-500 animate-spin" />
            </div>
          ) : addresses.length === 0 && !showNewAddress ? (
            
            <div className="text-center py-6">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <MapPin className="w-6 h-6 text-green-500" />
              </div>
              <p className="text-gray-600 mb-3">Нет сохранённых адресов</p>
              <Button
                type="button"
                onClick={() => setShowNewAddress(true)}
                icon={<Plus className="w-4 h-4" />}
                className="bg-gradient-to-r from-green-500 to-emerald-500"
              >
                Добавить адрес
              </Button>
            </div>
          ) : showNewAddress ? (
            
            <div className="space-y-4 p-4 bg-green-50 rounded-xl border-2 border-green-200">
              <div className="flex items-center justify-between">
                <span className="font-medium text-green-800 flex items-center gap-2">
                  <Home className="w-4 h-4" />
                  Новый адрес ({SERVICE_AREA_NAME})
                </span>
                <button
                  type="button"
                  onClick={() => setShowNewAddress(false)}
                  className="text-gray-400 hover:text-gray-600 text-xl leading-none"
                >
                  ×
                </button>
              </div>

              <div className="relative">
                <select
                  value={newStreet}
                  onChange={(e) => setNewStreet(e.target.value)}
                  className="w-full px-4 py-3 border-2 border-green-200 rounded-xl appearance-none bg-white focus:outline-none focus:ring-2 focus:ring-green-400 focus:border-transparent cursor-pointer"
                >
                  <option value="">Выберите улицу...</option>
                  {MINSK_MIR_STREETS.map((street) => (
                    <option key={street} value={street}>
                      ул. {street}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <Input
                  label="Дом *"
                  value={newHouse}
                  onChange={(e) => setNewHouse(e.target.value)}
                  placeholder="10А"
                />
                <Input
                  label="Квартира"
                  value={newApartment}
                  onChange={(e) => setNewApartment(e.target.value)}
                  placeholder="42"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Input
                  label="Подъезд *"
                  value={newEntrance}
                  onChange={(e) => setNewEntrance(e.target.value)}
                  placeholder="3"
                  type="number"
                  min="1"
                />
                <Input
                  label="Этаж"
                  value={newFloor}
                  onChange={(e) => setNewFloor(e.target.value)}
                  placeholder="5"
                  type="number"
                  min="1"
                />
              </div>

              {geocodedResult ? (
                <div className="bg-blue-50 border-2 border-blue-200 rounded-xl p-4 space-y-3">
                  <div className="flex items-start gap-2">
                    <SearchCheck className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium text-blue-900">Адрес найден. Всё верно?</p>
                      <p className="text-sm text-blue-700 mt-1">{geocodedResult.displayName}</p>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => setGeocodedResult(null)}
                      disabled={savingAddress}
                      className="flex-1"
                    >
                      Изменить
                    </Button>
                    <Button
                      type="button"
                      onClick={handleConfirmAddress}
                      isLoading={savingAddress}
                      className="flex-1 bg-gradient-to-r from-green-500 to-emerald-500"
                    >
                      Да, сохранить
                    </Button>
                  </div>
                </div>
              ) : (
                <Button
                  type="button"
                  onClick={handleVerifyAddress}
                  isLoading={savingAddress}
                  className="w-full bg-gradient-to-r from-green-500 to-emerald-500"
                >
                  Проверить адрес
                </Button>
              )}
            </div>
          ) : (
            
            <div className="space-y-2">
              {addresses.map((addr) => (
                <div
                  key={addr.id}
                  className={`w-full p-4 rounded-xl border-2 transition-all ${selectedAddressId === addr.id
                    ? 'border-green-500 bg-green-50'
                    : 'border-gray-200 hover:border-green-300'
                    }`}
                >
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => setSelectedAddressId(addr.id)}
                      className="flex items-center gap-3 flex-1 min-w-0 text-left"
                    >
                      <div
                        className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl flex-shrink-0 ${selectedAddressId === addr.id ? 'bg-green-200' : 'bg-gray-100'
                          }`}
                      >
                        🏠
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900">
                          ул. {addr.street}, д. {addr.house_number}
                          {addr.apartment && `, кв. ${addr.apartment}`}
                        </p>
                        {addr.entrance && <p className="text-sm text-gray-500">подъезд {addr.entrance}</p>}
                      </div>
                      {selectedAddressId === addr.id && <Check className="w-5 h-5 text-green-600 flex-shrink-0" />}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteAddress(addr.id)}
                      disabled={deletingAddressId === addr.id}
                      className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors flex-shrink-0"
                    >
                      {deletingAddressId === addr.id
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <Trash2 className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              ))}

              <button
                type="button"
                onClick={() => setShowNewAddress(true)}
                className="w-full p-4 rounded-xl border-2 border-dashed border-green-300 text-green-600 hover:bg-green-50 transition-colors flex items-center justify-center gap-2"
              >
                <Plus className="w-5 h-5" />
                Добавить новый адрес
              </button>
            </div>
          )}
        </Card>

        {}
        <Card className="border-2 border-green-100">
          <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Package className="w-5 h-5 text-green-600" />
            Что вывозим
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Тип мусора</label>
              <div className="grid grid-cols-1 gap-3">
                {garbageTypes.map((type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setGarbageType(type)}
                    className={`p-4 rounded-xl border-2 transition-all text-left ${garbageType === type
                      ? 'border-green-500 bg-green-50'
                      : 'border-gray-200 hover:border-green-300'
                      }`}
                  >
                    <div className="text-2xl mb-1">{GARBAGE_TYPE_ICONS[type]}</div>
                    <div className="font-medium text-gray-900">{GARBAGE_TYPE_LABELS[type]}</div>
                  </button>
                ))}
              </div>
            </div>

            <Input
              label="Количество мешков"
              type="number"
              min="1"
              max="50"
              value={numberOfBags}
              onChange={(e) => setNumberOfBags(e.target.value)}
              placeholder="3"
              hint="От 1 до 50 мешков"
              required
            />

            <Input
              label="Комментарий к заказу"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Например: домофон #1234"
              hint="Укажите код домофона — курьер скажет спасибо"
            />
          </div>
        </Card>

        {}
        <Card className="border-2 border-green-100">
          <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Calendar className="w-5 h-5 text-green-600" />
            Когда забрать
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Дата *"
              type="date"
              value={scheduledDate}
              onChange={(e) => setScheduledDate(e.target.value)}
              min={minDate}
              required
            />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Время *</label>
              {scheduledDate && availableHours.length === 0 ? (
                <p className="text-sm text-red-500 mt-2">На сегодня слотов нет. Выберите другой день.</p>
              ) : (
                <div className="flex gap-2 items-center">
                  <select
                    value={scheduledTime ? scheduledTime.split(':')[0] : ''}
                    onChange={(e) => {
                      const hours = e.target.value;
                      
                      const h = parseInt(hours);
                      const prevMin = scheduledTime ? parseInt(scheduledTime.split(':')[1]) : 0;
                      const minM = isToday && h === minTimeToday.h ? minTimeToday.m : 0;
                      const newMin = prevMin >= minM ? prevMin.toString().padStart(2, '0') : minM.toString().padStart(2, '0');
                      setScheduledTime(hours ? `${hours}:${newMin}` : '');
                    }}
                    className="flex-1 px-3 py-2.5 border-2 border-green-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-green-400 bg-white font-medium"
                  >
                    <option value="">ЧЧ</option>
                    {availableHours.map((h) => (
                      <option key={h} value={h.toString().padStart(2, '0')}>
                        {h.toString().padStart(2, '0')}
                      </option>
                    ))}
                  </select>
                  <span className="text-xl font-bold text-green-600">:</span>
                  <select
                    value={scheduledTime ? scheduledTime.split(':')[1] : ''}
                    onChange={(e) => {
                      const hours = scheduledTime ? scheduledTime.split(':')[0] : availableHours[0]?.toString().padStart(2, '0') ?? '08';
                      setScheduledTime(e.target.value ? `${hours}:${e.target.value}` : '');
                    }}
                    className="flex-1 px-3 py-2.5 border-2 border-green-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-green-400 bg-white font-medium"
                    disabled={!scheduledTime?.split(':')[0]}
                  >
                    <option value="">ММ</option>
                    {availableMinutes.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>
              )}
              <p className="text-xs text-gray-500 mt-1">
                {isToday
                  ? `Сегодня доступно с ${minTimeToday.h.toString().padStart(2, '0')}:${minTimeToday.m.toString().padStart(2, '0')} до 21:00`
                  : 'Рабочие часы: 08:00 – 21:00'}
              </p>
            </div>
          </div>
        </Card>

        {}
        <div className="fixed bottom-20 left-0 right-0 p-4 bg-gradient-to-t from-white via-white to-transparent">
          <div className="max-w-2xl mx-auto">
            <Button
              type="submit"
              variant="primary"
              className="w-full py-4 text-lg shadow-lg shadow-green-200 bg-gradient-to-r from-green-500 to-emerald-500 hover:shadow-xl"
              isLoading={loading}
              disabled={!selectedAddressId || loading}
            >
              🚛 Создать заказ
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
};
