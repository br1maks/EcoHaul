
export const CLIENT_ROUTES = {
  HOME: '/',
  ORDERS: '/orders',
  ORDER_DETAIL: '/orders/:id',
  NEW_ORDER: '/new-order',
  SUBSCRIPTIONS: '/subscriptions',
  NEW_SUBSCRIPTION: '/subscriptions/new',
  WALLET: '/wallet',
  PROFILE: '/profile',
  ADDRESSES: '/addresses',
} as const;

export const COURIER_ROUTES = {
  DASHBOARD: '/courier',
  ORDERS: '/courier/orders',
  ORDER_DETAIL: '/courier/orders/:id',
  SHIFTS: '/courier/shifts',
  EARNINGS: '/courier/earnings',
  PROFILE: '/courier/profile',
} as const;

export const ADMIN_ROUTES = {
  DASHBOARD: '/admin',
  ORDERS: '/admin/orders',
  ORDER_DETAIL: '/admin/orders/:id',
  COURIERS: '/admin/couriers',
  COURIER_DETAIL: '/admin/couriers/:id',
  CLIENTS: '/admin/clients',
  CLIENT_DETAIL: '/admin/clients/:id',
  ANALYTICS: '/admin/analytics',
  APPLICATIONS: '/admin/applications',
} as const;

export const AUTH_ROUTES = {
  LOGIN: '/auth/login',
  REGISTER: '/auth/register',
} as const;

export const ROUTES = {
  ...CLIENT_ROUTES,
  ...COURIER_ROUTES,
  ...ADMIN_ROUTES,
  ...AUTH_ROUTES,
} as const;
