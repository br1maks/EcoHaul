import { errorDetail } from '@/lib/api/errors';
import { useState, useEffect, useCallback } from 'react';
import { addressesApi } from '@/lib/api/addresses';
import { geocodeAddress, type GeocodeResult } from '@/lib/api/geocoding';
import type { Address, CreateAddressData, UpdateAddressData } from '@/shared/types';
import { Button } from '@/shared/components/Button';
import { Input } from '@/shared/components/Input';
import { Card } from '@/shared/components/Card';
import {
  MINSK_MIR_STREETS,
  SERVICE_AREA_NAME,
  SERVICE_AREA_DISTRICT,
} from '@/constants';
import {
  MapPin,
  Plus,
  Trash2,
  Edit3,
  Check,
  X,
  Loader2,
  AlertCircle,
  Star,
  Info,
  ChevronDown,
  Home,
  SearchCheck,
} from 'lucide-react';

interface AddressFormData {
  street: string;
  house_number: string;
  apartment: string;
  entrance: string;
  floor: string;
  is_default: boolean;
  notes: string;
}

const INITIAL_FORM: AddressFormData = {
  street: '',
  house_number: '',
  apartment: '',
  entrance: '',
  floor: '',
  is_default: false,
  notes: '',
};

export const AddressesPage = () => {
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [formData, setFormData] = useState<AddressFormData>(INITIAL_FORM);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  const [geocodedResult, setGeocodedResult] = useState<GeocodeResult | null>(null);

  const loadAddresses = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await addressesApi.getAll();
      setAddresses(data);
    } catch (err) {
      console.error('Failed to load addresses:', err);
      setError('Ошибка загрузки адресов');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAddresses();
  }, [loadAddresses]);

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.street) {
      errors.street = 'Выберите улицу';
    }
    if (!formData.house_number.trim()) {
      errors.house_number = 'Укажите номер дома';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleVerify = async () => {
    if (!validateForm()) return;

    try {
      setSaving(true);
      setError(null);

      const result = await geocodeAddress(formData.street, formData.house_number);
      if (!result) {
        setError('Адрес не найден. Проверьте улицу и номер дома.');
        return;
      }

      setGeocodedResult(result);
    } catch {
      setError('Ошибка проверки адреса. Попробуйте ещё раз.');
    } finally {
      setSaving(false);
    }
  };

  const handleConfirmSave = async () => {
    if (!geocodedResult) return;

    try {
      setSaving(true);
      setError(null);

      const fullAddress = `г. Минск, ул. ${formData.street}, д. ${formData.house_number}${formData.apartment ? `, кв. ${formData.apartment}` : ''}`;

      const addressData: CreateAddressData = {
        latitude: geocodedResult.latitude,
        longitude: geocodedResult.longitude,
        full_address: fullAddress,
        city: 'Минск',
        district: SERVICE_AREA_DISTRICT,
        street: formData.street,
        house_number: formData.house_number,
        apartment: formData.apartment || undefined,
        entrance: formData.entrance ? parseInt(formData.entrance) : undefined,
        floor: formData.floor ? parseInt(formData.floor) : undefined,
        label: 'HOME',
        is_default: formData.is_default,
        notes: formData.notes || undefined,
      };

      if (editingId) {
        await addressesApi.update(editingId, addressData as UpdateAddressData);
        setSuccess('Адрес обновлён!');
      } else {
        await addressesApi.create(addressData);
        setSuccess('Адрес добавлен!');
      }

      await loadAddresses();
      resetForm();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: unknown) {
      console.error('Failed to save address:', err);
      setError(errorDetail(err) || 'Ошибка сохранения адреса');
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (address: Address) => {
    setFormData({
      street: address.street,
      house_number: address.house_number,
      apartment: address.apartment || '',
      entrance: address.entrance?.toString() || '',
      floor: address.floor?.toString() || '',
      is_default: address.is_default,
      notes: address.notes || '',
    });
    setEditingId(address.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    try {
      setDeletingId(id);
      await addressesApi.delete(id);
      setSuccess('Адрес удалён!');
      await loadAddresses();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error('Failed to delete address:', err);
      setError('Ошибка удаления адреса');
    } finally {
      setDeletingId(null);
    }
  };

  const handleSetDefault = async (address: Address) => {
    try {
      await addressesApi.update(address.id, { is_default: true });
      setSuccess('Адрес по умолчанию изменён!');
      await loadAddresses();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error('Failed to set default:', err);
      setError('Ошибка изменения адреса');
    }
  };

  const resetForm = () => {
    setFormData(INITIAL_FORM);
    setFormErrors({});
    setEditingId(null);
    setShowForm(false);
    setGeocodedResult(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 bg-gradient-to-br from-green-400 to-emerald-500 rounded-full flex items-center justify-center animate-pulse">
            <Loader2 className="w-8 h-8 text-white animate-spin" />
          </div>
          <span className="text-green-700 font-medium">Загрузка адресов...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50 pb-24">
      {}
      <div className="bg-white/80 backdrop-blur-md border-b border-green-100 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MapPin className="w-6 h-6 text-green-500" />
              <h1 className="text-2xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
                Мои адреса
              </h1>
            </div>
            {!showForm && (
              <Button
                onClick={() => setShowForm(true)}
                icon={<Plus className="w-4 h-4" />}
                className="bg-gradient-to-r from-green-500 to-emerald-500"
              >
                Добавить
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        {}
        <div className="bg-gradient-to-r from-blue-50 to-cyan-50 border-2 border-blue-200 rounded-2xl p-4 flex items-start gap-3">
          <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center flex-shrink-0">
            <Info className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <p className="font-semibold text-blue-900">Зона обслуживания: {SERVICE_AREA_NAME}</p>
            <p className="text-sm text-blue-700">
              Сейчас мы работаем только в районе {SERVICE_AREA_NAME}. Скоро расширим зону!
            </p>
          </div>
        </div>

        {}
        {success && (
          <div className="bg-green-100 border-2 border-green-300 text-green-700 px-4 py-3 rounded-2xl flex items-center gap-2 shadow-lg shadow-green-200/50">
            <Check className="w-5 h-5" />
            <span className="font-medium">{success}</span>
          </div>
        )}

        {}
        {error && (
          <div className="bg-red-50 border-2 border-red-200 text-red-700 px-4 py-3 rounded-2xl flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            <span className="flex-1">{error}</span>
            <button onClick={() => setError(null)} className="hover:bg-red-100 p-1 rounded">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {}
        {showForm && (
          <Card className="border-2 border-green-200 shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-gray-900 flex items-center gap-2">
                <Home className="w-5 h-5 text-green-500" />
                {editingId ? 'Редактировать адрес' : 'Новый адрес'}
              </h3>
              <button onClick={resetForm} className="text-gray-400 hover:text-gray-600 p-1 hover:bg-gray-100 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              {}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Улица <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <select
                    value={formData.street}
                    onChange={(e) => {
                      setFormData({ ...formData, street: e.target.value });
                      setFormErrors({ ...formErrors, street: '' });
                    }}
                    className={`w-full px-4 py-3 border-2 rounded-xl appearance-none bg-white focus:outline-none focus:ring-2 focus:ring-green-400 focus:border-transparent cursor-pointer ${
                      formErrors.street ? 'border-red-500' : 'border-gray-200 hover:border-green-300'
                    }`}
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
                {formErrors.street && (
                  <p className="mt-1 text-sm text-red-600">{formErrors.street}</p>
                )}
              </div>

              <div className="grid grid-cols-3 gap-4">
                <Input
                  label="Дом *"
                  value={formData.house_number}
                  onChange={(e) => {
                    setFormData({ ...formData, house_number: e.target.value });
                    setFormErrors({ ...formErrors, house_number: '' });
                  }}
                  placeholder="10А"
                  error={formErrors.house_number}
                />
                <Input
                  label="Подъезд"
                  type="number"
                  min={1}
                  value={formData.entrance}
                  onChange={(e) => setFormData({ ...formData, entrance: e.target.value })}
                  placeholder="1"
                />
                <Input
                  label="Квартира"
                  value={formData.apartment}
                  onChange={(e) => setFormData({ ...formData, apartment: e.target.value })}
                  placeholder="42"
                />
              </div>

              <Input
                label="Этаж"
                type="number"
                value={formData.floor}
                onChange={(e) => setFormData({ ...formData, floor: e.target.value })}
                placeholder="5"
              />

              <Input
                label="Примечание для курьера"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Код домофона, ориентиры..."
                hint="Поможет курьеру быстрее найти вас"
              />

              <label className="flex items-center gap-3 p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl cursor-pointer border-2 border-green-100 hover:border-green-200 transition-colors">
                <input
                  type="checkbox"
                  checked={formData.is_default}
                  onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                  className="w-5 h-5 text-green-600 rounded focus:ring-green-500"
                />
                <div>
                  <span className="font-medium text-gray-900">Сделать основным</span>
                  <p className="text-sm text-gray-500">Будет выбран автоматически при создании заказа</p>
                </div>
              </label>

              {}
              {geocodedResult && (
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
                      variant="secondary"
                      onClick={() => setGeocodedResult(null)}
                      disabled={saving}
                      className="flex-1"
                    >
                      Изменить
                    </Button>
                    <Button
                      onClick={handleConfirmSave}
                      isLoading={saving}
                      className="flex-1 bg-gradient-to-r from-green-500 to-emerald-500"
                    >
                      Да, сохранить
                    </Button>
                  </div>
                </div>
              )}

              {!geocodedResult && (
                <div className="flex gap-3 pt-2">
                  <Button
                    variant="secondary"
                    onClick={resetForm}
                    disabled={saving}
                    className="flex-1"
                  >
                    Отмена
                  </Button>
                  <Button
                    onClick={handleVerify}
                    isLoading={saving}
                    className="flex-1 bg-gradient-to-r from-green-500 to-emerald-500"
                  >
                    {editingId ? 'Проверить и сохранить' : 'Проверить адрес'}
                  </Button>
                </div>
              )}
            </div>
          </Card>
        )}

        {}
        {addresses.length === 0 && !showForm ? (
          <Card className="border-2 border-dashed border-green-200 bg-green-50/50">
            <div className="text-center py-8">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <MapPin className="w-8 h-8 text-green-500" />
              </div>
              <h3 className="text-lg font-bold text-gray-900 mb-2">Нет сохранённых адресов</h3>
              <p className="text-gray-500 mb-4">Добавьте адрес для быстрого оформления заказов</p>
              <Button
                onClick={() => setShowForm(true)}
                icon={<Plus className="w-4 h-4" />}
                className="bg-gradient-to-r from-green-500 to-emerald-500"
              >
                Добавить адрес
              </Button>
            </div>
          </Card>
        ) : (
          <div className="space-y-3">
            {addresses.map((address) => (
              <Card
                key={address.id}
                className={`border-2 transition-all ${
                  address.is_default
                    ? 'border-green-300 bg-gradient-to-br from-green-50 to-emerald-50'
                    : 'border-green-100 hover:border-green-200'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-2xl ${
                    address.is_default ? 'bg-green-200' : 'bg-gray-100'
                  }`}>
                    🏠
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-bold text-gray-900">Дом</span>
                      {address.is_default && (
                        <span className="bg-green-500 text-white text-xs px-2 py-0.5 rounded-full flex items-center gap-1">
                          <Star className="w-3 h-3" /> Основной
                        </span>
                      )}
                    </div>
                    <p className="text-gray-700">ул. {address.street}, д. {address.house_number}</p>
                    {(address.entrance || address.floor || address.apartment) && (
                      <p className="text-sm text-gray-500">
                        {[
                          address.entrance && `подъезд ${address.entrance}`,
                          address.floor && `этаж ${address.floor}`,
                          address.apartment && `кв. ${address.apartment}`,
                        ].filter(Boolean).join(', ')}
                      </p>
                    )}
                    {address.notes && (
                      <p className="text-sm text-emerald-600 mt-1">💬 {address.notes}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-1">
                    {!address.is_default && (
                      <button
                        onClick={() => handleSetDefault(address)}
                        className="p-2 text-gray-400 hover:text-yellow-500 hover:bg-yellow-50 rounded-lg transition-colors"
                        title="Сделать основным"
                      >
                        <Star className="w-5 h-5" />
                      </button>
                    )}
                    <button
                      onClick={() => handleEdit(address)}
                      className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                    >
                      <Edit3 className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => handleDelete(address.id)}
                      disabled={deletingId === address.id}
                      className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                    >
                      {deletingId === address.id ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <Trash2 className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
