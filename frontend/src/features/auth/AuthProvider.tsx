import * as React from "react";

import { fetchCurrentUser } from "@/features/auth/api";
import { AuthContext, type AuthContextValue } from "@/features/auth/auth-context";
import { clearToken, getToken, setToken, setUnauthorizedHandler } from "@/lib/api";
import type { TokenResponse, User } from "@/lib/types";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<User | null>(null);
  const [initialising, setInitialising] = React.useState(Boolean(getToken()));

  const signOut = React.useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  const signIn = React.useCallback((payload: TokenResponse) => {
    setToken(payload.access_token);
    setUser(payload.user);
  }, []);

  const refresh = React.useCallback(async () => {
    if (!getToken()) return;
    const me = await fetchCurrentUser();
    setUser(me);
  }, []);

  // A 401 from any request means the token is gone or expired: drop the session
  // once, centrally, rather than in each screen.
  React.useEffect(() => {
    setUnauthorizedHandler(() => setUser(null));
    return () => setUnauthorizedHandler(null);
  }, []);

  // Restore the session on a hard refresh.
  React.useEffect(() => {
    if (!getToken()) {
      setInitialising(false);
      return;
    }

    let cancelled = false;
    fetchCurrentUser()
      .then((me) => {
        if (!cancelled) setUser(me);
      })
      .catch(() => {
        // Expired or tampered token — the interceptor already cleared it.
        if (!cancelled) clearToken();
      })
      .finally(() => {
        if (!cancelled) setInitialising(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const value = React.useMemo<AuthContextValue>(
    () => ({ user, initialising, signIn, signOut, refresh }),
    [user, initialising, signIn, signOut, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
