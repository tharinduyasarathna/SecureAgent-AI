
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import {
  AuthUser,
  getCurrentUser,
  loginUser,
  registerUser,
} from "@/lib/auth";

const TOKEN_KEY = "secureagent_access_token";

type AuthContextValue = {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(
  undefined
);

export function AuthProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const clearSession = useCallback(() => {
    sessionStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    let active = true;

    async function restoreSession() {
      const savedToken = sessionStorage.getItem(TOKEN_KEY);

      if (!savedToken) {
        if (active) setLoading(false);
        return;
      }

      try {
        const currentUser = await getCurrentUser(savedToken);

        if (active) {
          setToken(savedToken);
          setUser(currentUser);
        }
      } catch {
        if (active) clearSession();
      } finally {
        if (active) setLoading(false);
      }
    }

    void restoreSession();

    return () => {
      active = false;
    };
  }, [clearSession]);

  const login = useCallback(
    async (email: string, password: string) => {
      const result = await loginUser(email, password);
      const currentUser = await getCurrentUser(
        result.access_token
      );

      sessionStorage.setItem(
        TOKEN_KEY,
        result.access_token
      );

      setToken(result.access_token);
      setUser(currentUser);
    },
    []
  );

  const register = useCallback(
    async (email: string, password: string) => {
      await registerUser(email, password);
      await login(email, password);
    },
    [login]
  );

  const logout = useCallback(() => {
    clearSession();
  }, [clearSession]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth must be used inside AuthProvider"
    );
  }

  return context;
}
