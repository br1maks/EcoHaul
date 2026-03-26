import React, { useState, useEffect } from 'react';
import { CreditCard, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { paymentsApi } from '@/lib/api/payments';
import type { Payment } from '@/lib/api/payments';

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.JSX.Element }> = {
    COMPLETED: { label: 'Оплачен', color: 'text-green-600', icon: <CheckCircle className="w-4 h-4 text-green-500" /> },
    PENDING: { label: 'Ожидает', color: 'text-yellow-600', icon: <Clock className="w-4 h-4 text-yellow-500" /> },
    CANCELLED: { label: 'Отменён', color: 'text-gray-400', icon: <XCircle className="w-4 h-4 text-gray-400" /> },
    FAILED: { label: 'Ошибка', color: 'text-red-500', icon: <XCircle className="w-4 h-4 text-red-500" /> },
    REFUNDED: { label: 'Возврат', color: 'text-blue-500', icon: <CheckCircle className="w-4 h-4 text-blue-500" /> },
};

const TYPE_LABELS: Record<string, string> = {
    ORDER_PAYMENT: 'Оплата заказа',
    SUBSCRIPTION_PURCHASE: 'Подписка',
    WALLET_TOPUP: 'Пополнение',
};

export const WalletPage = () => {
    const [payments, setPayments] = useState<Payment[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        paymentsApi.getMyPayments().then(data => {
            setPayments(data.items);
        }).finally(() => setLoading(false));
    }, []);

    return (
        <div className="min-h-screen">
            <div className="bg-white/80 backdrop-blur-md border-b border-green-100 sticky top-0 z-10 shadow-sm">
                <div className="max-w-2xl mx-auto px-4 py-4">
                    <h1 className="text-xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
                        Кошелёк
                    </h1>
                </div>
            </div>

            <div className="max-w-2xl mx-auto px-4 py-6 space-y-4">
                <div className="bg-gradient-to-br from-green-500 to-emerald-600 rounded-2xl p-6 text-white">
                    <div className="flex items-center gap-2 mb-1 opacity-80 text-sm">
                        <CreditCard className="w-4 h-4" />
                        История платежей
                    </div>
                    <div className="text-3xl font-bold">
                        {payments.filter(p => p.status === 'COMPLETED').length} оплачено
                    </div>
                </div>

                {loading ? (
                    <div className="flex justify-center py-12">
                        <Loader2 className="w-6 h-6 animate-spin text-green-500" />
                    </div>
                ) : payments.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                        <CreditCard className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                        <p>Платежей пока нет</p>
                    </div>
                ) : (
                    <div className="space-y-2">
                        {payments.map(payment => {
                            const s = STATUS_CONFIG[payment.status] ?? STATUS_CONFIG.FAILED;
                            return (
                                <div key={payment.id} className="bg-white rounded-xl p-4 flex items-center justify-between shadow-sm border border-gray-100">
                                    <div className="flex items-center gap-3">
                                        {s.icon}
                                        <div>
                                            <div className="font-medium text-gray-900 text-sm">
                                                {TYPE_LABELS[payment.payment_type] ?? payment.payment_type}
                                            </div>
                                            <div className="text-xs text-gray-400">
                                                {new Date(payment.created_at).toLocaleDateString('ru-RU', {
                                                    day: '2-digit', month: 'short', year: 'numeric'
                                                })}
                                            </div>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <div className="font-bold text-gray-900">{payment.amount} BYN</div>
                                        <div className={`text-xs ${s.color}`}>{s.label}</div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
};