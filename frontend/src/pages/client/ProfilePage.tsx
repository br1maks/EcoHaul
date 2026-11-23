import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { usersApi } from '@/lib/api/users';
import type { User, UserUpdateData } from '@/shared/types';
import { Button } from '@/shared/components/Button';
import { Input } from '@/shared/components/Input';
import { Card } from '@/shared/components/Card';
import {
  User as UserIcon,
  Phone,
  Mail,
  Calendar,
  Package,
  CheckCircle,
  XCircle,
  Loader2,
  Save,
  AlertCircle,
  Sparkles,
  Truck,
  ChevronRight,
} from 'lucide-react';

export const ProfilePage = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<UserUpdateData>({});
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  const loadUser = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await usersApi.getMe();
      setUser(data);
      setFormData({
        first_name: data.first_name,
        last_name: data.last_name,
        phone: data.phone || '',
        email: data.email || '',
        age: data.age,
      });
    } catch (err) {
      console.error('Failed to load user:', err);
      setError('Ошибка загрузки профиля');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.first_name || formData.first_name.trim().length < 2) {
      errors.first_name = 'Имя должно содержать минимум 2 символа';
    } else if (!/^[а-яёА-ЯЁa-zA-Z\s-]+$/.test(formData.first_name)) {
      errors.first_name = 'Имя может содержать только буквы';
    }

    if (!formData.last_name || formData.last_name.trim().length < 2) {
      errors.last_name = 'Фамилия должна содержать минимум 2 символа';
    } else if (!/^[а-яёА-ЯЁa-zA-Z\s-]+$/.test(formData.last_name)) {
      errors.last_name = 'Фамилия может содержать только буквы';
    }

    if (formData.phone && formData.phone.trim()) {
      const phoneClean = formData.phone.replace(/[\s\-()]/g, '');
      if (!/^\+375(29|33|44|25)\d{7}$/.test(phoneClean)) {
        errors.phone = 'Формат: +375 29/33/44/25 XXX-XX-XX';
      }
    }

    if (formData.email && formData.email.trim()) {
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
        errors.email = 'Введите корректный email';
      }
    }

    if (formData.age !== undefined && formData.age !== null) {
      if (formData.age < 14 || formData.age > 120) {
        errors.age = 'Возраст должен быть от 14 до 120 лет';
      }
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSave = async () => {
    if (!user) return;

    if (!validateForm()) {
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      const updateData: UserUpdateData = {};

      if (formData.first_name?.trim() !== user.first_name) {
        updateData.first_name = formData.first_name?.trim();
      }
      if (formData.last_name?.trim() !== user.last_name) {
        updateData.last_name = formData.last_name?.trim();
      }
      if (formData.phone?.trim() !== (user.phone || '')) {
        updateData.phone = formData.phone?.trim() || undefined;
      }
      if (formData.email?.trim() !== (user.email || '')) {
        updateData.email = formData.email?.trim() || undefined;
      }
      if (formData.age !== user.age) {
        updateData.age = formData.age;
      }

      if (Object.keys(updateData).length === 0) {
        setIsEditing(false);
        return;
      }

      const updatedUser = await usersApi.updateMe(updateData);
      setUser(updatedUser);
      setIsEditing(false);
      setSuccess('Профиль успешно обновлён!');

      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error('Failed to update user:', err);
      setError('Ошибка сохранения профиля');
    } finally {
      setSaving(false);
    }
  };

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return 'Не указана';
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'Не указана';
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  };

  const formatPhone = (value: string) => {
    
    let cleaned = value.replace(/[^\d+]/g, '');

    if (cleaned && !cleaned.startsWith('+')) {
      if (cleaned.startsWith('375')) {
        cleaned = '+' + cleaned;
      } else if (cleaned.startsWith('8')) {
        cleaned = '+375' + cleaned.slice(1);
      } else {
        cleaned = '+375' + cleaned;
      }
    }

    if (cleaned.length > 4) {
      let formatted = cleaned.slice(0, 4); 
      if (cleaned.length > 4) formatted += ' ' + cleaned.slice(4, 6); 
      if (cleaned.length > 6) formatted += ' ' + cleaned.slice(6, 9); 
      if (cleaned.length > 9) formatted += '-' + cleaned.slice(9, 11); 
      if (cleaned.length > 11) formatted += '-' + cleaned.slice(11, 13); 
      return formatted;
    }

    return cleaned;
  };

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

  if (error && !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
        <div className="text-center p-6">
          <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-10 h-10 text-red-500" />
          </div>
          <div className="text-red-500 text-xl font-bold mb-2">Упс! Ошибка</div>
          <div className="text-gray-600 mb-4">{error}</div>
          <Button onClick={loadUser}>
            Попробовать снова
          </Button>
        </div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
      {}
      <div className="bg-white/80 backdrop-blur-md border-b border-green-100 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-green-500" />
            <h1 className="text-2xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
              Мой профиль
            </h1>
          </div>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        {}
        {success && (
          <div className="bg-green-100 border-2 border-green-300 text-green-700 px-4 py-3 rounded-2xl flex items-center gap-2 shadow-lg shadow-green-200/50">
            <CheckCircle className="w-5 h-5" />
            <span className="font-medium">{success}</span>
          </div>
        )}

        {}
        {error && (
          <div className="bg-red-50 border-2 border-red-200 text-red-700 px-4 py-3 rounded-2xl flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            {error}
          </div>
        )}

        {}
        <Card className="bg-gradient-to-br from-green-500 to-emerald-600 text-white border-0 shadow-xl shadow-green-200/50">
          <div className="flex items-center gap-4">
            <div className="w-20 h-20 bg-white/20 backdrop-blur rounded-full flex items-center justify-center text-3xl font-bold border-4 border-white/30">
              {user.first_name[0]}{user.last_name?.[0] || ''}
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold">
                {user.first_name} {user.last_name}
              </h2>
              {user.telegram_username && (
                <p className="text-green-100 flex items-center gap-1">
                  <span>@{user.telegram_username}</span>
                </p>
              )}
              <div className="flex items-center gap-2 mt-2">
                {user.is_active ? (
                  <span className="bg-white/20 backdrop-blur px-3 py-1 rounded-full text-sm flex items-center gap-1">
                    <CheckCircle className="w-4 h-4" /> Активен
                  </span>
                ) : (
                  <span className="bg-red-500/50 px-3 py-1 rounded-full text-sm flex items-center gap-1">
                    <XCircle className="w-4 h-4" /> Заблокирован
                  </span>
                )}
              </div>
            </div>
          </div>
        </Card>

        {}
        <Card className="border-2 border-green-100 shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-gray-900 flex items-center gap-2">
              <UserIcon className="w-5 h-5 text-green-500" />
              Личные данные
            </h3>
            {!isEditing && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsEditing(true)}
                className="text-green-600 hover:bg-green-50"
              >
                Редактировать
              </Button>
            )}
          </div>

          {isEditing ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="Имя"
                  value={formData.first_name || ''}
                  onChange={(e) => {
                    setFormData({ ...formData, first_name: e.target.value });
                    setFormErrors({ ...formErrors, first_name: '' });
                  }}
                  icon={<UserIcon className="w-5 h-5 text-green-500" />}
                  error={formErrors.first_name}
                  placeholder="Иван"
                />
                <Input
                  label="Фамилия"
                  value={formData.last_name || ''}
                  onChange={(e) => {
                    setFormData({ ...formData, last_name: e.target.value });
                    setFormErrors({ ...formErrors, last_name: '' });
                  }}
                  error={formErrors.last_name}
                  placeholder="Иванов"
                />
              </div>

              <Input
                label="Телефон"
                type="tel"
                value={formData.phone || ''}
                onChange={(e) => {
                  const formatted = formatPhone(e.target.value);
                  setFormData({ ...formData, phone: formatted });
                  setFormErrors({ ...formErrors, phone: '' });
                }}
                icon={<Phone className="w-5 h-5 text-green-500" />}
                placeholder="+375 29 123-45-67"
                error={formErrors.phone}
                hint="Формат: +375 29/33/44/25 XXX-XX-XX"
              />

              <Input
                label="Email"
                type="email"
                value={formData.email || ''}
                onChange={(e) => {
                  setFormData({ ...formData, email: e.target.value });
                  setFormErrors({ ...formErrors, email: '' });
                }}
                icon={<Mail className="w-5 h-5 text-green-500" />}
                placeholder="ivan@example.com"
                error={formErrors.email}
              />

              <Input
                label="Возраст"
                type="number"
                min={14}
                max={120}
                value={formData.age || ''}
                onChange={(e) => {
                  setFormData({ ...formData, age: e.target.value ? parseInt(e.target.value) : undefined });
                  setFormErrors({ ...formErrors, age: '' });
                }}
                icon={<Calendar className="w-5 h-5 text-green-500" />}
                error={formErrors.age}
                placeholder="25"
              />

              <div className="flex gap-3 pt-2">
                <Button
                  variant="secondary"
                  onClick={() => {
                    setIsEditing(false);
                    setFormErrors({});
                    setFormData({
                      first_name: user.first_name,
                      last_name: user.last_name,
                      phone: user.phone || '',
                      email: user.email || '',
                      age: user.age,
                    });
                  }}
                  disabled={saving}
                  className="flex-1"
                >
                  Отмена
                </Button>
                <Button
                  onClick={handleSave}
                  isLoading={saving}
                  icon={<Save className="w-4 h-4" />}
                  className="flex-1 bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600"
                >
                  Сохранить
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-3 py-3 px-4 bg-green-50 rounded-xl">
                <UserIcon className="w-5 h-5 text-green-500" />
                <div>
                  <div className="text-xs text-green-600 font-medium">Имя</div>
                  <div className="font-semibold text-gray-900">{user.first_name} {user.last_name}</div>
                </div>
              </div>

              <div className="flex items-center gap-3 py-3 px-4 bg-emerald-50 rounded-xl">
                <Phone className="w-5 h-5 text-emerald-500" />
                <div>
                  <div className="text-xs text-emerald-600 font-medium">Телефон</div>
                  <div className="font-semibold text-gray-900">{user.phone || 'Не указан'}</div>
                </div>
              </div>

              <div className="flex items-center gap-3 py-3 px-4 bg-teal-50 rounded-xl">
                <Mail className="w-5 h-5 text-teal-500" />
                <div>
                  <div className="text-xs text-teal-600 font-medium">Email</div>
                  <div className="font-semibold text-gray-900">{user.email || 'Не указан'}</div>
                </div>
              </div>

              {user.age && (
                <div className="flex items-center gap-3 py-3 px-4 bg-cyan-50 rounded-xl">
                  <Calendar className="w-5 h-5 text-cyan-500" />
                  <div>
                    <div className="text-xs text-cyan-600 font-medium">Возраст</div>
                    <div className="font-semibold text-gray-900">{user.age} лет</div>
                  </div>
                </div>
              )}

              <div className="flex items-center gap-3 py-3 px-4 bg-lime-50 rounded-xl">
                <Package className="w-5 h-5 text-lime-500" />
                <div>
                  <div className="text-xs text-lime-600 font-medium">Дата регистрации</div>
                  <div className="font-semibold text-gray-900">{formatDate(user.created_at)}</div>
                </div>
              </div>
            </div>
          )}
        </Card>

        {}
        {user.role === 'CLIENT' && (
          <Card
            className="border-2 border-green-100 cursor-pointer hover:shadow-lg transition-shadow"
            onClick={() => navigate('/become-courier')}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-gradient-to-br from-green-100 to-emerald-100 rounded-full flex items-center justify-center">
                  <Truck className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <h3 className="font-bold text-gray-900">Стать курьером</h3>
                  <p className="text-sm text-gray-500">Зарабатывайте с EcoHaul</p>
                </div>
              </div>
              <ChevronRight className="w-5 h-5 text-gray-400" />
            </div>
          </Card>
        )}
      </div>
    </div>
  );
};
