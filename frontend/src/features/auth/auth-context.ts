import * as React from "react";

import type { TokenResponse, User } from "@/lib/types";

export interface AuthContextValue {
  user: User | null;
  /** True until the stored token has been checked against /auth/me. */
  initialising: boolean;
  signIn: (payload: TokenResponse) => void;
  signOut: () => void;
  refresh: () => Promise<void>;
}

export const AuthContext = React.createContext<AuthContextValue | undefined>(undefined);

/**
 * The context and this hook live apart from <AuthProvider> on purpose: a file
 * that exports both a component and a hook cannot be hot-reloaded, so editing
 * the provider used to tear the whole tree down mid-session.
 */
export function useAuth(): AuthContextValue {
  const context = React.useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
