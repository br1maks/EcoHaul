import { Outlet } from 'react-router-dom';
import { CourierBottomNav } from '@/shared/components/CourierBottomNav';

export const CourierLayout = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50">
      {}
      <main className="pb-20">
        <Outlet />
      </main>

      {}
      <CourierBottomNav />
    </div>
  );
};
