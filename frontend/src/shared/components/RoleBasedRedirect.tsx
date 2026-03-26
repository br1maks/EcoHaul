import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { usersApi } from '@/lib/api/users';
import { CLIENT_ROUTES, COURIER_ROUTES, ADMIN_ROUTES } from '@/constants/routes.constants';
import { Loading } from './Loading';

export const RoleBasedRedirect = () => {
  const [loading, setLoading] = useState(true);
  const [redirectPath, setRedirectPath] = useState<string | null>(null);

  useEffect(() => {
    const checkUserRole = async () => {
      try {
        const user = await usersApi.getMe();

        switch (user.role) {
          case 'ADMIN':
            setRedirectPath(ADMIN_ROUTES.DASHBOARD);
            break;
          case 'COURIER':
            setRedirectPath(COURIER_ROUTES.DASHBOARD);
            break;
          case 'CLIENT':
          default:
            setRedirectPath(CLIENT_ROUTES.ORDERS);
            break;
        }
      } catch (error) {
        
        console.error('Failed to get user role:', error);
        setRedirectPath(CLIENT_ROUTES.ORDERS);
      } finally {
        setLoading(false);
      }
    };

    checkUserRole();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loading />
      </div>
    );
  }

  if (redirectPath) {
    return <Navigate to={redirectPath} replace />;
  }

  return null;
};
