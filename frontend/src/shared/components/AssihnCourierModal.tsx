import { useState, useEffect } from 'react';
import { X, Search, Star, Check } from 'lucide-react';
import { couriersApi, type CourierStatistics } from '@/lib/api';

interface AssignCourierModalProps {
    isOpen: boolean;
    onClose: () => void;
    orderId: string;
    onSuccess: () => void;
}

export const AssignCourierModal = ({ isOpen, onClose, orderId, onSuccess }: AssignCourierModalProps) => {
    const [couriers, setCouriers] = useState<CourierStatistics[]>([]);
    const [loading, setLoading] = useState(false);
    const [assigning, setAssigning] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen) {
            fetchCouriers();
        }
    }, [isOpen]);

    const fetchCouriers = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await couriersApi.getAllCouriers({
                is_verified: true,
                is_active: true,
                size: 100,
            });
            setCouriers(response.items);
        } catch (err) {
            console.error('Failed to fetch couriers:', err);
            setError('Не удалось загрузить список курьеров');
        } finally {
            setLoading(false);
        }
    };

    const handleAssign = async (courierId: string) => {
        try {
            setAssigning(true);
            await couriersApi.assignCourier(orderId, courierId);
            onSuccess();
            onClose();
        } catch (err: any) {
            console.error('Failed to assign courier:', err);
            const message = err?.detail || err?.message || 'Неизвестная ошибка';
            alert(`Не удалось назначить курьера: ${message}`);
        } finally {
            setAssigning(false);
        }
    };

    const filteredCouriers = couriers.filter(courier =>
        `${courier.first_name} ${courier.last_name}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
        courier.phone.includes(searchQuery)
    );

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col">
                {}
                <div className="flex items-center justify-between p-6 border-b border-gray-200">
                    <h2 className="text-xl font-bold text-gray-900">Выбрать курьера</h2>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5 text-gray-600" />
                    </button>
                </div>

                {}
                <div className="p-6 border-b border-gray-200">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Поиск по имени или телефону..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                </div>

                {}
                <div className="flex-1 overflow-y-auto p-6">
                    {loading ? (
                        <div className="text-center py-8 text-gray-500">Загрузка курьеров...</div>
                    ) : error ? (
                        <div className="text-center py-8 text-red-500">{error}</div>
                    ) : filteredCouriers.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">Курьеры не найдены</div>
                    ) : (
                        <div className="space-y-3">
                            {filteredCouriers.map((courier) => (
                                <button
                                    key={courier.id}
                                    onClick={() => handleAssign(courier.id)}
                                    disabled={assigning}
                                    className="w-full p-4 border border-gray-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-all text-left disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    <div className="flex items-center justify-between">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2">
                                                <h3 className="font-semibold text-gray-900">
                                                    {courier.first_name} {courier.last_name}
                                                </h3>
                                                {courier.is_verified && (
                                                    <Check className="w-4 h-4 text-green-600" />
                                                )}
                                            </div>
                                            <p className="text-sm text-gray-600">{courier.phone}</p>
                                            <div className="flex items-center gap-4 mt-2">
                                                <div className="flex items-center gap-1">
                                                    <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                                                    <span className="text-sm text-gray-700">{courier.rating.toFixed(1)}</span>
                                                </div>
                                                <span className="text-sm text-gray-600">
                                                    {courier.total_orders} заказов
                                                </span>
                                                <span className={`text-xs px-2 py-1 rounded-full ${courier.courier_status === 'ACTIVE' ? 'bg-green-100 text-green-700' :
                                                        courier.courier_status === 'ON_BREAK' ? 'bg-yellow-100 text-yellow-700' :
                                                            'bg-gray-100 text-gray-700'
                                                    }`}>
                                                    {courier.courier_status === 'ACTIVE' ? 'Доступен' :
                                                        courier.courier_status === 'ON_BREAK' ? 'На перерыве' :
                                                        courier.courier_status === 'NOT_AVAILABLE' ? 'Недоступен' : 'Оффлайн'}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
