import { useEffect, useRef, lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import type { Toast } from 'react-hot-toast';
import { Toaster, ToastBar, toast } from 'react-hot-toast';
import { AuthProvider } from '@/contexts/AuthContext';
import { initTelegramWebApp } from "@/lib/telegram/utils";
import { useWebSocket } from '@/shared/hooks/useWebSocket';
import { RoleBasedRedirect } from '@/shared/components';
import { MainLayout } from '@/layouts/MainLayout';
import { CourierLayout } from '@/layouts/CourierLayout';
import { AdminLayout } from '@/layouts/AdminLayout';


























const OrdersPage = lazy(() => import('@/pages/client/OrdersPage').then(module => ({ default: module.OrdersPage })));
const OrderDetailPageWrapper = lazy(() => import('@/pages/client/OrderDetailPageWrapper').then(module => ({ default: module.OrderDetailPageWrapper })));
const NewOrderPageWrapper = lazy(() => import('@/pages/client/NewOrderPageWrapper').then(module => ({ default: module.NewOrderPageWrapper })));
const WalletPage = lazy(() => import('@/pages/client/WalletPage').then(module => ({ default: module.WalletPage })));
const SubscriptionsPage = lazy(() => import('@/pages/client/SubscriptionsPage').then(module => ({ default: module.SubscriptionsPage })));
const ProfilePage = lazy(() => import('@/pages/client/ProfilePage').then(module => ({ default: module.ProfilePage })));
const AddressesPage = lazy(() => import('@/pages/client/AddressesPage').then(module => ({ default: module.AddressesPage })));
const CourierDashboardPage = lazy(() => import('@/pages/courier/CourierDashboardPage').then(module => ({ default: module.CourierDashboardPage })));
const CourierOrdersPage = lazy(() => import('@/pages/courier/CourierOrdersPage').then(module => ({ default: module.CourierOrdersPage })));
const CourierOrderDetailPageWrapper = lazy(() => import('@/pages/courier/CourierOrderDetailPageWrapper').then(module => ({ default: module.CourierOrderDetailPageWrapper })));
const CourierProfilePage = lazy(() => import('@/pages/courier/CourierProfilePage').then(module => ({ default: module.CourierProfilePage })));
const CourierShiftsPage = lazy(() => import('@/pages/courier/CourierShiftsPage').then(module => ({ default: module.CourierShiftsPage })));
const AdminDashboardPage = lazy(() => import('@/pages/admin/AdminDashboardPage').then(module => ({ default: module.AdminDashboardPage })));
const AdminOrdersPage = lazy(() => import('@/pages/admin/AdminOrdersPage').then(module => ({ default: module.AdminOrdersPage })));
const AdminOrderDetailPageWrapper = lazy(() => import('@/pages/admin/AdminOrderDetailPageWrapper').then(module => ({ default: module.AdminOrderDetailPageWrapper })));
const AdminClientsPage = lazy(() => import('@/pages/admin/AdminClientsPage').then(module => ({ default: module.AdminClientsPage })));
const AdminClientDetailPageWrapper = lazy(() => import('@/pages/admin/AdminClientDetailPageWrapper').then(module => ({ default: module.AdminClientDetailPageWrapper })));
const AdminCouriersPage = lazy(() => import('@/pages/admin/AdminCouriersPage').then(module => ({ default: module.AdminCouriersPage })));
const AdminCourierDetailPageWrapper = lazy(() => import('@/pages/admin/AdminCourierDetailPageWrapper').then(module => ({ default: module.AdminCourierDetailPageWrapper })));
const AdminAnalyticsPage = lazy(() => import('@/pages/admin/AdminAnalyticsPage').then(module => ({ default: module.AdminAnalyticsPage })));
const AdminCourierApplicationsPage = lazy(() => import('@/pages/admin/AdminCourierApplicationsPage').then(module => ({ default: module.AdminCourierApplicationsPage })));
const BecomeCourierPage = lazy(() => import('@/pages/client/BecomeCourierPage').then(module => ({ default: module.BecomeCourierPage })));
const AdminLoginPage = lazy(() => import('@/pages/admin/AdminLoginPage').then(module => ({ default: module.AdminLoginPage })));
const PaymentSuccessPage = lazy(() => import('@/pages/client/PaymentSuccessPage').then(module => ({ default: module.PaymentSuccessPage })));
const PaymentFailPage = lazy(() => import('@/pages/client/PaymentFailPage').then(module => ({ default: module.PaymentFailPage })));

function SwipeableTost({ t }: { t: Toast }) {
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
        <Suspense fallback={<div className="p-8 text-center">Загрузка…</div>}>
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
        </Routes>
        </Suspense>
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
