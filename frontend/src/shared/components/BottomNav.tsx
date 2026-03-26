import { useLocation, useNavigate } from 'react-router-dom';
import { Package, User, Wallet, Bell } from 'lucide-react';
import { CLIENT_ROUTES } from '@/constants/routes.constants';
import { hapticFeedback } from '@/lib/telegram/utils';

interface NavItem {
  path: string;
  icon: React.ReactNode;
  label: string;
  emoji: string;
}

export const BottomNav = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const navItems: NavItem[] = [
    {
      path: CLIENT_ROUTES.ORDERS,
      icon: <Package className="w-6 h-6" />,
      label: 'Заказы',
      emoji: '📦',
    },
    {
      path: CLIENT_ROUTES.WALLET,
      icon: <Wallet className="w-6 h-6" />,
      label: 'Кошелёк',
      emoji: '💳',
    },
    {
      path: CLIENT_ROUTES.SUBSCRIPTIONS,
      icon: <Bell className="w-6 h-6" />,
      label: 'Подписки',
      emoji: '🔔',
    },
    {
      path: CLIENT_ROUTES.PROFILE,
      icon: <User className="w-6 h-6" />,
      label: 'Профиль',
      emoji: '👤',
    },
  ];

  const handleNavClick = (path: string) => {
    hapticFeedback.light();
    navigate(path);
  };

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white/95 backdrop-blur-lg border-t border-green-100 shadow-2xl z-50">
      <div className="max-w-2xl mx-auto px-2 py-2">
        <div className="flex items-center justify-around">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;

            return (
              <button
                key={item.path}
                onClick={() => handleNavClick(item.path)}
                className={`
                  flex flex-col items-center gap-1 px-4 py-2 rounded-2xl transition-all duration-200
                  ${isActive
                    ? 'bg-gradient-to-br from-green-100 to-emerald-100 scale-105'
                    : 'hover:bg-gray-50 active:scale-95'
                  }
                `}
              >
                <div className={`
                  transition-all duration-200
                  ${isActive ? 'text-green-600 scale-110' : 'text-gray-500'}
                `}>
                  {isActive ? (
                    <span className="text-2xl">{item.emoji}</span>
                  ) : (
                    item.icon
                  )}
                </div>
                <span className={`
                  text-xs font-medium transition-colors
                  ${isActive ? 'text-green-700' : 'text-gray-600'}
                `}>
                  {item.label}
                </span>
                {isActive && (
                  <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-8 h-1 bg-gradient-to-r from-green-500 to-emerald-500 rounded-full" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {}
      <div className="h-safe-area-inset-bottom bg-white" />
    </nav>
  );
};
