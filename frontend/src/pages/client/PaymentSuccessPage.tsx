import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle, Loader2 } from 'lucide-react';
import { paymentsApi } from '@/lib/api/payments';

export const PaymentSuccessPage = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const paymentId = searchParams.get('payment_id');
    const [status, setStatus] = useState<'loading' | 'success' | 'pending'>('loading');

    useEffect(() => {
        if (!paymentId) { navigate('/orders'); return; }

        const check = async () => {
            try {
                const payment = await paymentsApi.getPayment(paymentId);
                setStatus(payment.status === 'COMPLETED' ? 'success' : 'pending');
            } catch {
                setStatus('pending');
            }
        };

        check();
    }, [paymentId]);

    useEffect(() => {
        if (status === 'success') {
            const timer = setTimeout(() => navigate('/orders'), 3000);
            return () => clearTimeout(timer);
        }
    }, [status]);

    return (
        <div className="min-h-screen flex items-center justify-center px-4">
            <div className="text-center">
                {status === 'loading' ? (
                    <Loader2 className="w-12 h-12 animate-spin text-green-500 mx-auto mb-4" />
                ) : status === 'success' ? (
                    <>
                        <CheckCircle className="w-20 h-20 text-green-500 mx-auto mb-4" />
                        <h1 className="text-2xl font-bold text-gray-900 mb-2">Оплата прошла!</h1>
                        <p className="text-gray-500 mb-6">Заказ принят в обработку</p>
                        <p className="text-sm text-gray-400">Переходим к заказам...</p>
                    </>
                ) : (
                    <>
                        <Loader2 className="w-16 h-16 animate-spin text-yellow-500 mx-auto mb-4" />
                        <h1 className="text-xl font-bold text-gray-900 mb-2">Обрабатываем оплату</h1>
                        <p className="text-gray-500 mb-6">Это может занять несколько секунд</p>
                        <button
                            onClick={() => navigate('/orders')}
                            className="px-6 py-3 bg-green-500 text-white rounded-xl font-medium"
                        >
                            Перейти к заказам
                        </button>
                    </>
                )}
            </div>
        </div>
    );
};
