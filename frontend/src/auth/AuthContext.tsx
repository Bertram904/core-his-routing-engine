import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { getCurrentUserApi, loginApi } from "@/api/auth.api";
import {
  clearAccessToken,
  loadAccessToken,
  saveAccessToken,
} from "@/auth/authStorage";
import { canAccessModule, type AppModule } from "@/constants/scopes";
import type { LoginRequest, UserProfile } from "@/types/api.types";

interface AuthContextValue {
  token: string | null;
  user: UserProfile | null;
  isLoading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
  canAccess: (module: AppModule) => boolean;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(loadAccessToken());
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(Boolean(loadAccessToken()));

  const refreshProfile = useCallback(async () => {
    if (!token) {
      setUser(null);
      return;
    }

    const profile = await getCurrentUserApi(token);
    setUser(profile);
  }, [token]);

  useEffect(() => {
    if (!token) {
      setIsLoading(false);
      setUser(null);
      return;
    }

    let cancelled = false;
    setIsLoading(true);

    getCurrentUserApi(token)
      .then((profile) => {
        if (!cancelled) {
          setUser(profile);
        }
      })
      .catch(() => {
        if (!cancelled) {
          clearAccessToken();
          setToken(null);
          setUser(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  const login = useCallback(async (credentials: LoginRequest) => {
    const response = await loginApi(credentials);
    saveAccessToken(response.access_token);
    setToken(response.access_token);
    const profile = await getCurrentUserApi(response.access_token);
    setUser(profile);
  }, []);

  const logout = useCallback(() => {
    clearAccessToken();
    setToken(null);
    setUser(null);
  }, []);

  const canAccess = useCallback(
    (module: AppModule) => canAccessModule(user?.scopes ?? [], module),
    [user],
  );

  const value = useMemo(
    () => ({
      token,
      user,
      isLoading,
      login,
      logout,
      canAccess,
      refreshProfile,
    }),
    [token, user, isLoading, login, logout, canAccess, refreshProfile],
  );

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
