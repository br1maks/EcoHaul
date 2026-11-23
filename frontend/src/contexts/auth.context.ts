import { createContext, useContext } from 'react';
export const AuthContext = createContext({ isReady: false });
export const useAuth = () => useContext(AuthContext);
