import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import {
  ApiError,
  clearToken,
  getToken,
  login as loginRequest,
  me,
  register as registerRequest,
  setToken,
} from './api';
import type { AccountPublic, LoginRequest, RegisterRequest } from './types';

interface AuthContextValue {
  account: AccountPublic | null;
  token: string | null;
  loading: boolean;
  login: (body: LoginRequest) => Promise<AccountPublic>;
  register: (body: RegisterRequest) => Promise<AccountPublic>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<AccountPublic | null>(null);
  const [token, setTokenState] = useState<string | null>(() => getToken());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      if (getToken() === null) {
        setLoading(false);
        return;
      }
      try {
        const current = await me();
        if (cancelled) return;
        setAccount(current);
        setTokenState(getToken());
      } catch (error) {
        if (cancelled) return;
        // Only a rejected token ends the session. A network failure keeps the
        // token so the next reload can retry instead of forcing a new sign in.
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
          clearToken();
        }
        setTokenState(getToken());
        setAccount(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void restoreSession();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (body: LoginRequest) => {
    const result = await loginRequest(body);
    setToken(result.access_token);
    setTokenState(result.access_token);
    setAccount(result.account);
    return result.account;
  }, []);

  const register = useCallback(async (body: RegisterRequest) => {
    return registerRequest(body);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setTokenState(null);
    setAccount(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ account, token, loading, login, register, logout }),
    [account, token, loading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error('useAuth must be used inside an AuthProvider.');
  }
  return context;
}