import { useNavigate } from 'react-router-dom';
import { NewOrderPage } from './NewOrderPage';
import { CLIENT_ROUTES } from '@/constants/routes.constants';

export const NewOrderPageWrapper = () => {
  const navigate = useNavigate();

  return (
    <NewOrderPage
      onBack={() => navigate(CLIENT_ROUTES.ORDERS)}
      onSuccess={() => navigate(CLIENT_ROUTES.ORDERS)}
    />
  );
};
