import { useParams, useNavigate } from 'react-router-dom';
import { CourierOrderDetailPage } from './CourierOrderDetailPage';
import { COURIER_ROUTES } from '@/constants/routes.constants';

export const CourierOrderDetailPageWrapper = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  if (!id) {
    return <div>Ошибка: ID заказа не найден</div>;
  }

  return (
    <CourierOrderDetailPage
      orderId={id}
      onBack={() => navigate(COURIER_ROUTES.ORDERS)}
    />
  );
};
