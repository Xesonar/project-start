import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { authWithMax } from "@/api/auth";
import { registerStudentSessionRefresher, STUDENT_UNAUTHORIZED_EVENT } from "@/api/client";
import { setToken } from "@/api/token";
import { getMe, type Me } from "@/api/users";
import { getInitData } from "@/max/webapp";

type AuthStatus = "loading" | "authenticated" | "unavailable" | "error";

interface AuthContextValue {
  status: AuthStatus;
  me: Me | null;
  errorMessage: string | null;
  refreshMe: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [me, setMe] = useState<Me | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const refreshingSession = useRef(false);

  const refreshMe = async () => {
    const profile = await getMe();
    setMe(profile);
    setErrorMessage(null);
    setStatus("authenticated");
  };

  useEffect(() => {
    const initData = getInitData();
    let cancelled = false;

    const restoreMaxSession = () => {
      if (!initData) {
        setMe(null);
        setStatus("unavailable");
        return;
      }
      if (refreshingSession.current) return;
      refreshingSession.current = true;
      setStatus("loading");
      authWithMax(initData)
        .then(({ access_token }) => {
          setToken(access_token);
          return getMe();
        })
        .then((profile) => {
          if (cancelled) return;
          setMe(profile);
          setErrorMessage(null);
          setStatus("authenticated");
        })
        .catch((err: unknown) => {
          if (cancelled) return;
          setErrorMessage(err instanceof Error ? err.message : "Не удалось войти");
          setStatus("error");
        })
        .finally(() => {
          refreshingSession.current = false;
        });
    };

    registerStudentSessionRefresher(async () => {
      if (!initData) return false;
      try {
        const { access_token } = await authWithMax(initData);
        setToken(access_token);
        return true;
      } catch {
        return false;
      }
    });

    window.addEventListener(STUDENT_UNAUTHORIZED_EVENT, restoreMaxSession);
    if (!initData) {
      setStatus("unavailable");
      return () => {
        cancelled = true;
        registerStudentSessionRefresher(null);
        window.removeEventListener(STUDENT_UNAUTHORIZED_EVENT, restoreMaxSession);
      };
    }
    restoreMaxSession();
    return () => {
      cancelled = true;
      registerStudentSessionRefresher(null);
      window.removeEventListener(STUDENT_UNAUTHORIZED_EVENT, restoreMaxSession);
    };
  }, []);

  const value = useMemo(
    () => ({ status, me, errorMessage, refreshMe }),
    [status, me, errorMessage],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
