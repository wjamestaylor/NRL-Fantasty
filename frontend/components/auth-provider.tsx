"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { getApiBaseUrl, parseApiError } from "@/lib/api";

type AuthUser = {
  id: string;
  email: string;
  display_name: string;
};

type AuthContextValue = {
  isReady: boolean;
  token: string | null;
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => void;
};

type AuthPayload = {
  token: string;
  user: AuthUser;
};

const AUTH_STORAGE_KEY = "nrl-fantasty-auth";

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function persistAuth(payload: AuthPayload | null) {
  if (typeof window === "undefined") {
    return;
  }

  if (payload) {
    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(payload));
    return;
  }

  window.localStorage.removeItem(AUTH_STORAGE_KEY);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isReady, setIsReady] = useState(false);

  const applyAuth = useCallback((payload: AuthPayload | null) => {
    setToken(payload?.token ?? null);
    setUser(payload?.user ?? null);
    persistAuth(payload);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const restore = async () => {
      const stored = window.localStorage.getItem(AUTH_STORAGE_KEY);
      if (!stored) {
        setIsReady(true);
        return;
      }

      try {
        const parsed = JSON.parse(stored) as AuthPayload;
        const response = await fetch(`${getApiBaseUrl()}/auth/me`, {
          headers: { Authorization: "Bearer " + parsed.token },
        });

        if (!response.ok) {
          throw new Error("Stored session expired");
        }

        const verifiedUser = (await response.json()) as AuthUser;
        applyAuth({ token: parsed.token, user: verifiedUser });
      } catch {
        applyAuth(null);
      } finally {
        setIsReady(true);
      }
    };

    void restore();
  }, [applyAuth]);

  const authenticate = useCallback(
    async (path: "/auth/login" | "/auth/register", payload: Record<string, unknown>) => {
      const response = await fetch(`${getApiBaseUrl()}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(await parseApiError(response));
      }

      const authPayload = (await response.json()) as AuthPayload;
      applyAuth(authPayload);
    },
    [applyAuth],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      isReady,
      token,
      user,
      login: async (email, password) => {
        await authenticate("/auth/login", { email, password });
      },
      register: async (email, password, displayName) => {
        await authenticate("/auth/register", {
          email,
          password,
          display_name: displayName,
        });
      },
      logout: () => applyAuth(null),
    }),
    [applyAuth, authenticate, isReady, token, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }

  return context;
}
