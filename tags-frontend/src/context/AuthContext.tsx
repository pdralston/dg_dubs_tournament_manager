import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { auth as authApi } from '../services/api';
import type { User } from '../types';

const VIEWER: User = { user_id: 0, username: 'Viewer', role: 'Viewer' };

interface AuthContextValue {
  user: User;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isDirector: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  user: VIEWER,
  isAuthenticated: false,
  isAdmin: false,
  isDirector: false,
  loading: true,
  login: async () => {},
  logout: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User>(VIEWER);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    authApi.me()
      .then(data => {
        if (data.user_id && data.user_id !== 0) setUser(data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const data = await authApi.login(username, password);
    setUser(data);
  }, []);

  const logout = useCallback(async () => {
    try { await authApi.logout(); } catch {}
    setUser(VIEWER);
  }, []);

  const isAuthenticated = user.user_id !== 0;
  const isAdmin = user.role === 'admin';
  const isDirector = user.role === 'director' || user.role === 'admin';

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isAdmin, isDirector, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
