import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import * as authApi from "../api/auth";
import { auth as tokenStore } from "../api/client";
import type { User } from "../api/types";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  user: User | null;
  status: AuthStatus;
  login: (payload: authApi.LoginPayload) => Promise<void>;
  register: (payload: authApi.RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  /** Обновляет закэшированного пользователя после PATCH /users/me — без
   * этого шапка (имя/аватар) показывала бы старые данные до перелогина. */
  updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  useEffect(() => {
    if (!tokenStore.getToken()) {
      setStatus("unauthenticated");
      return;
    }

    authApi
      .getMe()
      .then((me) => {
        setUser(me);
        setStatus("authenticated");
      })
      .catch(() => {
        tokenStore.clearToken();
        setStatus("unauthenticated");
      });
  }, []);

  const login = useCallback(async (payload: authApi.LoginPayload) => {
    const { accessToken } = await authApi.login(payload);
    tokenStore.setToken(accessToken);
    const me = await authApi.getMe();
    setUser(me);
    setStatus("authenticated");
  }, []);

  const register = useCallback(
    async (payload: authApi.RegisterPayload) => {
      await authApi.register(payload);
      await login({ email: payload.email, password: payload.password });
    },
    [login],
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Токен мог уже истечь/быть отозван — выходим локально в любом случае.
    }
    tokenStore.clearToken();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  return (
    <AuthContext.Provider value={{ user, status, login, register, logout, updateUser: setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth должен вызываться внутри <AuthProvider>");
  return ctx;
}
