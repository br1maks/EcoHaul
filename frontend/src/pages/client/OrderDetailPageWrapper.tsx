import { useParams, useNavigate } from 'react-router-dom';
import { OrderDetailPage } from './OrderDetailPage';
import { CLIENT_ROUTES } from '@/constants/routes.constants';

export const OrderDetailPageWrapper = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  if (!id) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-lg mb-2">Ошибка</div>
          <div className="text-gray-600">ID заказа не найден</div>
        </div>
      </div>
    );
  }

  return (
    <OrderDetailPage
      orderId={id}
      onBack={() => navigate(CLIENT_ROUTES.ORDERS)}
    />
  );
};
