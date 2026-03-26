import { useNavigate } from 'react-router-dom';
import { XCircle } from 'lucide-react';

export const PaymentFailPage = () => {
    const navigate = useNavigate();

    return (
        <div className="min-h-screen flex items-center justify-center px-4">
            <div className="text-center">
                <XCircle className="w-20 h-20 text-red-400 mx-auto mb-4" />
                <h1 className="text-2xl font-bold text-gray-900 mb-2">Оплата не прошла</h1>
                <p className="text-gray-500 mb-8">Попробуйте ещё раз или выберите другой способ оплаты</p>
                <div className="flex flex-col gap-3">
                    <button
                        onClick={() => navigate(-1)}
                        className="px-6 py-3 bg-green-500 text-white rounded-xl font-medium"
                    >
                        Попробовать снова
                    </button>
                    <button
                        onClick={() => navigate('/orders')}
                        className="px-6 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium"
                    >
                        Перейти к заказам
                    </button>
                </div>
            </div>
        </div>
    );
};
