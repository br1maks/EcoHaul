import { useEffect, useRef } from "react";
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster, ToastBar, toast } from 'react-hot-toast';
import { AuthProvider } from '@/contexts/AuthContext';
import { initTelegramWebApp } from "@/lib/telegram/utils";
import { useWebSocket } from '@/shared/hooks/useWebSocket';
import { RoleBasedRedirect } from '@/shared/components';
import { MainLayout } from '@/layouts/MainLayout';
import { CourierLayout } from '@/layouts/CourierLayout';
import { AdminLayout } from '@/layouts/AdminLayout';
import { OrdersPage } from '@/pages/client/OrdersPage';
import { OrderDetailPageWrapper } from '@/pages/client/OrderDetailPageWrapper';
import { NewOrderPageWrapper } from '@/pages/client/NewOrderPageWrapper';
import { WalletPage } from '@/pages/client/WalletPage';
import { SubscriptionsPage } from '@/pages/client/SubscriptionsPage';
import { ProfilePage } from '@/pages/client/ProfilePage';
import { AddressesPage } from '@/pages/client/AddressesPage';
import { CourierDashboardPage } from '@/pages/courier/CourierDashboardPage';
import { CourierDashboardPageProfessional } from '@/pages/courier/CourierDashboardPageProfessional';
import { CourierOrdersPage } from '@/pages/courier/CourierOrdersPage';
import { CourierOrderDetailPageWrapper } from '@/pages/courier/CourierOrderDetailPageWrapper';
import { CourierProfilePage } from '@/pages/courier/CourierProfilePage';
import { CourierShiftsPage } from '@/pages/courier/CourierShiftsPage';
import { AdminDashboardPage } from '@/pages/admin/AdminDashboardPage';
import { AdminOrdersPage } from '@/pages/admin/AdminOrdersPage';
import { AdminOrderDetailPageWrapper } from '@/pages/admin/AdminOrderDetailPageWrapper';
import { AdminClientsPage } from '@/pages/admin/AdminClientsPage';
import { AdminClientDetailPageWrapper } from '@/pages/admin/AdminClientDetailPageWrapper';
import { AdminCouriersPage } from '@/pages/admin/AdminCouriersPage';
import { AdminCourierDetailPageWrapper } from '@/pages/admin/AdminCourierDetailPageWrapper';
import { AdminAnalyticsPage } from '@/pages/admin/AdminAnalyticsPage';
import { AdminCourierApplicationsPage } from '@/pages/admin/AdminCourierApplicationsPage';
import { BecomeCourierPage } from '@/pages/client/BecomeCourierPage';
import { AdminLoginPage } from '@/pages/admin/AdminLoginPage';
import { PaymentSuccessPage } from '@/pages/client/PaymentSuccessPage';
import { PaymentFailPage } from '@/pages/client/PaymentFailPage';

function SwipeableTost({ t }: { t: any }) {
  const startX = useRef(0);
  const el = useRef<HTMLDivElement>(null);

  return (
    <div
      ref={el}
      onTouchStart={(e) => { startX.current = e.touches[0].clientX; }}
      onTouchMove={(e) => {
        const dx = e.touches[0].clientX - startX.current;
        if (el.current) el.current.style.transform = `translateX(${dx}px)`;
      }}
      onTouchEnd={(e) => {
        const dx = e.changedTouches[0].clientX - startX.current;
        if (Math.abs(dx) > 80) {
          toast.dismiss(t.id);
        } else if (el.current) {
          el.current.style.transform = '';
        }
      }}
      style={{ transition: 'transform 0.15s ease', cursor: 'grab' }}
    >
      <ToastBar toast={t} />
    </div>
  );
}

function AppInner() {
  useWebSocket();

  return (
    <>
      <BrowserRouter>
        <Routes>
          {}
          <Route path="/" element={<MainLayout />}>
            <Route index element={<RoleBasedRedirect />} />
            <Route path="orders" element={<OrdersPage />} />
            <Route path="new-order" element={<NewOrderPageWrapper />} />
            <Route path="orders/:id" element={<OrderDetailPageWrapper />} />
            <Route path="wallet" element={<WalletPage />} />
            <Route path="subscriptions" element={<SubscriptionsPage />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="addresses" element={<AddressesPage />} />
            <Route path="become-courier" element={<BecomeCourierPage />} />
            <Route path="payment/success" element={<PaymentSuccessPage />} />
            <Route path="payment/fail" element={<PaymentFailPage />} />
          </Route>

          {}
          <Route path="/courier" element={<CourierLayout />}>
            <Route index element={<CourierDashboardPage />} />
            <Route path="orders" element={<CourierOrdersPage />} />
            <Route path="orders/:id" element={<CourierOrderDetailPageWrapper />} />
            <Route path="shifts" element={<CourierShiftsPage />} />
            <Route path="profile" element={<CourierProfilePage />} />
          </Route>

          {}
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminDashboardPage />} />
            <Route path="orders" element={<AdminOrdersPage />} />
            <Route path="orders/:id" element={<AdminOrderDetailPageWrapper />} />
            <Route path="clients" element={<AdminClientsPage />} />
            <Route path="clients/:id" element={<AdminClientDetailPageWrapper />} />
            <Route path="couriers" element={<AdminCouriersPage />} />
            <Route path="couriers/:id" element={<AdminCourierDetailPageWrapper />} />
            <Route path="analytics" element={<AdminAnalyticsPage />} />
            <Route path="applications" element={<AdminCourierApplicationsPage />} />
          </Route>

          {}
          <Route path="/admin/login" element={<AdminLoginPage />} />

          {}
          <Route path="/courier-pro" element={<CourierDashboardPageProfessional />} />
        </Routes>
      </BrowserRouter>
    </>
  );
}

function App() {
  useEffect(() => {
    initTelegramWebApp();
  }, []);

  return (
    <>
      <Toaster position="top-center">
        {(t) => (
          <SwipeableTost t={t} />
        )}
      </Toaster>
      <AuthProvider>
        <AppInner />
      </AuthProvider>
    </>
  );
}

export default App;
