import { SessionSettings } from '@/shared/components/SessionSettings';
import { useState, useEffect } from 'react';
import { usersApi } from '@/lib/api/users';
import { useLocation, useNavigate, Outlet } from 'react-router-dom';
import { LayoutDashboard, Package, Users, UserCheck, BarChart3, Menu, FileText } from 'lucide-react';
import { ADMIN_ROUTES } from '@/constants/routes.constants';

interface NavItem {
  path: string;
  icon: React.ReactNode;
  label: string;
}

export const AdminLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [email, setEmail] = useState('');
  useEffect(() => {
    usersApi.getMe().then(user => setEmail(user.email ?? '')).catch(() => setEmail(''));
  }, []);

  const navItems: NavItem[] = [
    {
      path: ADMIN_ROUTES.DASHBOARD,
      icon: <LayoutDashboard className="w-5 h-5" />,
      label: 'Панель управления',
    },
    {
      path: ADMIN_ROUTES.ORDERS,
      icon: <Package className="w-5 h-5" />,
      label: 'Заказы',
    },
    {
      path: ADMIN_ROUTES.COURIERS,
      icon: <UserCheck className="w-5 h-5" />,
      label: 'Курьеры',
    },
    {
      path: ADMIN_ROUTES.CLIENTS,
      icon: <Users className="w-5 h-5" />,
      label: 'Клиенты',
    },
    {
      path: ADMIN_ROUTES.ANALYTICS,
      icon: <BarChart3 className="w-5 h-5" />,
      label: 'Аналитика',
    },
    {
      path: ADMIN_ROUTES.APPLICATIONS,
      icon: <FileText className="w-5 h-5" />,
      label: 'Заявки курьеров',
    },
  ];

  const isActive = (path: string) => {
    if (path === ADMIN_ROUTES.DASHBOARD) {
      return location.pathname === path;
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {}
      <aside
        className={`${
          isSidebarOpen ? 'w-64' : 'w-20'
        } bg-white border-r border-gray-200 transition-all duration-300 flex flex-col`}
      >
        {}
        <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200">
          {isSidebarOpen && (
            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              EcoHaul Admin
            </h1>
          )}
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <Menu className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {}
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => {
            const active = isActive(item.path);

            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`
                  w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all
                  ${
                    active
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : 'text-gray-700 hover:bg-gray-100'
                  }
                  ${!isSidebarOpen && 'justify-center'}
                `}
                title={!isSidebarOpen ? item.label : undefined}
              >
                <div className={active ? 'text-blue-600' : 'text-gray-500'}>
                  {item.icon}
                </div>
                {isSidebarOpen && <span className="text-sm">{item.label}</span>}
              </button>
            );
          })}
        </nav>

        {}
        {isSidebarOpen && (
          <div className="p-4 border-t border-gray-200">
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center text-white font-bold">
                A
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900">Администратор</div>
                <div className="text-xs text-gray-500 truncate">{email}</div>
              </div>
            </div>
          </div>
        )}
      </aside>

      {}
      <main className="flex-1 overflow-auto">
        <details className="mx-6 mt-4 rounded-xl border border-gray-200 bg-white p-3">
          <summary className="cursor-pointer text-sm text-gray-600">Сессии и выход</summary>
          <div className="mt-3 max-w-2xl"><SessionSettings /></div>
        </details>
        <Outlet />
      </main>
    </div>
  );
};
