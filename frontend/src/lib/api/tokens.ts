const ACCESS_KEY = 'ecohaul_access_token';
const REFRESH_KEY = 'ecohaul_refresh_token';

export const getAccessToken = () => sessionStorage.getItem(ACCESS_KEY);
export const getRefreshToken = () => sessionStorage.getItem(REFRESH_KEY);
export const setTokens = (access: string, refresh: string) => {
  sessionStorage.removeItem('ecohaul_signed_out');
  sessionStorage.setItem(ACCESS_KEY, access);
  sessionStorage.setItem(REFRESH_KEY, refresh);
  window.dispatchEvent(new Event('ecohaul:auth'));
};
export const clearTokens = () => {
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
  window.dispatchEvent(new Event('ecohaul:auth'));
};
