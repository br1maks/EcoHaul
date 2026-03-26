import { Outlet } from 'react-router-dom';
import { BottomNav } from '@/shared/components/BottomNav';

export const MainLayout = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
      {}
      <main className="pb-20">
        <Outlet />
      </main>

      {}
      <BottomNav />
    </div>
  );
};
