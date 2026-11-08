/**
 * Shared authentication context for the unified DG-Rater SPA.
 *
 * Mirrors the backend's three authZ tiers (see /api/auth/me and
 * backend/shared/auth.py):
 *
 *   Site  — `isSuperuser` (users.is_superuser): platform bypass, admin everywhere.
 *   Org   — `orgRole` (org_roles): 'owner' | 'manager' | null; derives app-admin
 *           on every subscribed app.
 *   App   — `appRole(app)` (org_memberships): 'admin' | 'director' | null;
 *           null means "viewer" (no membership).
 *
 * `appRole()` resolves the same way the backend does, so UI gating matches API
 * enforcement by construction:
 *   superuser                -> 'admin'
 *   org owner/manager        -> 'admin' (on any app)
 *   else explicit membership -> 'admin' | 'director' | null
 */

import {
  createContext, useContext, useEffect, useState, useCallback, type ReactNode,
} from 'react';
import { API_BASE_URL } from '../config/api';

export type AppName = 'dubs' | 'tags' | 'putt';
export type OrgRole = 'owner' | 'manager' | null;
export type AppRole = 'admin' | 'director' | null;

/** Raw shape returned by GET /api/auth/me (enriched three-tier identity). */
export interface Identity {
  user_id: number;
  username: string;
  role: string;             // legacy flat field (back-compat); not used for gating
  is_superuser: boolean;
  org_role: OrgRole;
  app_roles: Partial<Record<AppName, AppRole>>;
}

interface AuthContextValue {
  identity: Identity | null;
  loading: boolean;
  isAuthenticated: boolean;
  isSuperuser: boolean;
  orgRole: OrgRole;
  /** Effective app-axis role for `app`, applying the Site/Org derivation. */
  appRole: (app: AppName) => AppRole;
  /** True if the user is at least `role` in `app` (admin > director). */
  hasAppRole: (app: AppName, role: Exclude<AppRole, null>) => boolean;
  refresh: () => Promise<void>;
  login: (username: string, password: string) => Promise<{ ok: boolean; error?: string }>;
  logout: () => Promise<void>;
}

const VIEWER: Identity = {
  user_id: 0,
  username: 'Viewer',
  role: 'Viewer',
  is_superuser: false,
  org_role: null,
  app_roles: {},
};

const APP_ROLE_RANK: Record<Exclude<AppRole, null>, number> = { director: 0, admin: 1 };

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/me`, { credentials: 'include' });
      const data = (await res.json()) as Identity;
      setIdentity(data);
    } catch {
      setIdentity(VIEWER);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(
    async (username: string, password: string) => {
      const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        return { ok: false, error: body.error || 'Login failed' };
      }
      await refresh();
      return { ok: true };
    },
    [refresh],
  );

  const logout = useCallback(async () => {
    await fetch(`${API_BASE_URL}/api/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    }).catch(() => undefined);
    await refresh();
  }, [refresh]);

  const id = identity ?? VIEWER;

  const appRole = useCallback(
    (app: AppName): AppRole => {
      if (id.is_superuser) return 'admin';
      if (id.org_role === 'owner' || id.org_role === 'manager') return 'admin';
      return id.app_roles[app] ?? null;
    },
    [id],
  );

  const hasAppRole = useCallback(
    (app: AppName, role: Exclude<AppRole, null>) => {
      const effective = appRole(app);
      if (!effective) return false;
      return APP_ROLE_RANK[effective] >= APP_ROLE_RANK[role];
    },
    [appRole],
  );

  const value: AuthContextValue = {
    identity,
    loading,
    isAuthenticated: id.user_id !== 0,
    isSuperuser: id.is_superuser,
    orgRole: id.org_role,
    appRole,
    hasAppRole,
    refresh,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>');
  return ctx;
}
