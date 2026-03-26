import { useState, useEffect } from 'react';
import { Card } from '@/shared/components/Card';
import { Button } from '@/shared/components/Button';
import { subscriptionsApi } from '@/lib/api/subscriptions';
import type { Subscription, SubscriptionPlan, SubscriptionTier } from '@/shared/types';

export const SubscriptionsPage = () => {
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [currentSubscription, setCurrentSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState<SubscriptionTier | null>(null);
  const [selectedDuration, setSelectedDuration] = useState<number>(1);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [plansData, subscriptionData] = await Promise.all([
        subscriptionsApi.getPlans(),
        subscriptionsApi.getMySubscription(),
      ]);
      setPlans(plansData);
      setCurrentSubscription(subscriptionData);
    } catch (error) {
      console.error('Error loading subscription data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePurchase = async (tier: SubscriptionTier) => {
    try {
      setPurchasing(tier);
      const response = await subscriptionsApi.purchase({
        tier,
        duration_months: selectedDuration,
      });
      window.location.href = response.payment_url;
    } catch (error) {
      console.error('Error purchasing subscription:', error);
      alert('Ошибка при оформлении подписки');
    } finally {
      setPurchasing(null);
    }
  };

  const getTierColor = (tier: SubscriptionTier) => {
    switch (tier) {
      case 'FREE':
        return 'from-gray-500 to-gray-600';
      case 'BASIC':
        return 'from-blue-500 to-blue-600';
      case 'PREMIUM':
        return 'from-amber-500 to-amber-600';
      default:
        return 'from-gray-500 to-gray-600';
    }
  };

  const getTierBadgeColor = (tier: SubscriptionTier) => {
    switch (tier) {
      case 'FREE':
        return 'bg-gray-100 text-gray-700';
      case 'BASIC':
        return 'bg-blue-100 text-blue-700';
      case 'PREMIUM':
        return 'bg-amber-100 text-amber-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-24">
      {}
      <div className="bg-white/80 backdrop-blur-md border-b border-green-100 sticky top-0 z-10 shadow-sm">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <h1 className="text-xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
            Подписки
          </h1>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {}
        {currentSubscription && (
          <Card className="border-green-200 bg-gradient-to-br from-green-50 to-emerald-50">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Ваш текущий план</h2>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getTierBadgeColor(currentSubscription.tier)}`}>
                {currentSubscription.tier === 'FREE' ? 'Бесплатный' :
                 currentSubscription.tier === 'BASIC' ? 'Базовый' : 'Премиум'}
              </span>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Скидка на заказы:</span>
                <span className="font-bold text-green-600 text-lg">
                  {currentSubscription.discount_percentage}%
                </span>
              </div>

              {currentSubscription.tier !== 'FREE' && (
                <>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Действует до:</span>
                    <span className="font-medium">
                      {formatDate(currentSubscription.end_date)}
                    </span>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Осталось дней:</span>
                    <span className={`font-bold ${currentSubscription.is_expiring_soon ? 'text-orange-500' : 'text-gray-800'}`}>
                      {currentSubscription.days_remaining}
                    </span>
                  </div>

                  {currentSubscription.is_expiring_soon && (
                    <div className="bg-orange-100 text-orange-700 p-3 rounded-lg text-sm">
                      Ваша подписка скоро закончится! Продлите её, чтобы сохранить скидку.
                    </div>
                  )}
                </>
              )}
            </div>
          </Card>
        )}

        {}
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Выберите срок подписки</h2>
          <div className="grid grid-cols-3 gap-2">
            {[1, 3, 6].map((months) => (
              <button
                key={months}
                onClick={() => setSelectedDuration(months)}
                className={`p-3 rounded-lg border-2 transition-all ${
                  selectedDuration === months
                    ? 'border-green-500 bg-green-50 text-green-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="font-bold text-lg">{months}</div>
                <div className="text-xs text-gray-500">
                  {months === 1 ? 'месяц' : months < 5 ? 'месяца' : 'месяцев'}
                </div>
                {months >= 3 && (
                  <div className="text-xs text-green-600 font-medium mt-1">
                    -{months === 3 ? '5' : '10'}%
                  </div>
                )}
              </button>
            ))}
          </div>
        </Card>

        {}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-gray-800 px-1">Доступные планы</h2>

          {plans.map((plan) => {
            const isCurrentPlan = currentSubscription?.tier === plan.tier;
            const priceWithDiscount = plan.price_per_month * selectedDuration *
              (selectedDuration >= 6 ? 0.9 : selectedDuration >= 3 ? 0.95 : 1);

            return (
              <div
                key={plan.tier}
                className={`bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg border overflow-hidden transition-all ${
                  isCurrentPlan ? 'ring-2 ring-green-500 border-green-200' : 'border-green-100'
                } ${plan.tier === 'PREMIUM' ? 'shadow-xl' : ''}`}
              >
                {}
                <div className={`bg-gradient-to-r ${getTierColor(plan.tier)} p-4 text-white`}>
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="text-xl font-bold">{plan.name}</h3>
                      <p className="text-white/80 text-sm">{plan.description}</p>
                    </div>
                    {plan.discount_percentage > 0 && (
                      <div className="bg-white/20 px-3 py-1 rounded-full text-sm font-bold">
                        -{plan.discount_percentage}%
                      </div>
                    )}
                  </div>
                </div>

                <div className="p-5">
                  {}
                  <div className="text-center mb-4">
                    {plan.price_per_month > 0 ? (
                      <>
                        <div className="text-3xl font-bold text-gray-800">
                          {priceWithDiscount.toFixed(2)} BYN
                        </div>
                        <div className="text-sm text-gray-500">
                          за {selectedDuration} {selectedDuration === 1 ? 'месяц' : selectedDuration < 5 ? 'месяца' : 'месяцев'}
                        </div>
                        {selectedDuration >= 3 && (
                          <div className="text-xs text-gray-400 line-through">
                            {(plan.price_per_month * selectedDuration).toFixed(2)} BYN
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="text-3xl font-bold text-gray-800">Бесплатно</div>
                    )}
                  </div>

                  {}
                  <ul className="space-y-2 mb-4">
                    {plan.features.map((feature, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm">
                        <span className="text-green-500 mt-0.5">✓</span>
                        <span className="text-gray-600">{feature}</span>
                      </li>
                    ))}
                  </ul>

                  {}
                  {plan.tier !== 'FREE' && (
                    <Button
                      className={`w-full bg-gradient-to-r ${getTierColor(plan.tier)} text-white hover:opacity-90`}
                      disabled={purchasing !== null}
                      onClick={() => handlePurchase(plan.tier)}
                      isLoading={purchasing === plan.tier}
                    >
                      {isCurrentPlan ? 'Продлить подписку' : 'Оформить подписку'}
                    </Button>
                  )}

                  {isCurrentPlan && (
                    <div className="mt-2 text-center text-sm text-green-600 font-medium">
                      Ваш текущий план
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {}
        <Card className="bg-blue-50 border-blue-200">
          <h3 className="font-semibold text-blue-800 mb-2">Как работают подписки?</h3>
          <ul className="text-sm text-blue-700 space-y-1">
            <li>• Скидка применяется автоматически ко всем заказам</li>
            <li>• Подписка действует с момента оплаты</li>
            <li>• Можно продлить подписку в любой момент</li>
            <li>• При продлении срок добавляется к текущему</li>
          </ul>
        </Card>
      </div>
    </div>
  );
};
