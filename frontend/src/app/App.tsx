import * as React from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "@/app/AppShell";
import { ThemeProvider } from "@/app/ThemeProvider";
import { Spinner } from "@/components/states";
import { AuthProvider } from "@/features/auth/AuthProvider";
import { useAuth } from "@/features/auth/auth-context";
import { LoginPage } from "@/features/auth/LoginPage";
import { SignupPage } from "@/features/auth/SignupPage";

/**
 * The five signed-in screens are split per route.
 *
 * Recharts alone is a large dependency and only the dashboard needs it, so
 * loading each page on demand keeps the first paint — login, or the shell — off
 * the critical path of code no one has navigated to yet. AppShell wraps its
 * <Outlet> in Suspense, so the sidebar stays put while a chunk arrives.
 *
 * Sign-in stays eager: it is the entry point for a visitor with no token.
 */
const DashboardPage = React.lazy(() =>
  import("@/features/dashboard/DashboardPage").then((m) => ({ default: m.DashboardPage })),
);
const TransactionsPage = React.lazy(() =>
  import("@/features/transactions/TransactionsPage").then((m) => ({ default: m.TransactionsPage })),
);
const BudgetsPage = React.lazy(() =>
  import("@/features/budgets/BudgetsPage").then((m) => ({ default: m.BudgetsPage })),
);
const ChatPage = React.lazy(() =>
  import("@/features/chat/ChatPage").then((m) => ({ default: m.ChatPage })),
);
const SettingsPage = React.lazy(() =>
  import("@/features/settings/SettingsPage").then((m) => ({ default: m.SettingsPage })),
);

/**
 * Gate for the authenticated area. While the stored token is being validated we
 * render a spinner rather than redirecting, otherwise a refresh would bounce a
 * signed-in user to the login screen.
 */
function RequireAuth() {
  const { user, initialising } = useAuth();
  const location = useLocation();

  if (initialising) {
    return (
      <div className="flex min-h-svh items-center justify-center">
        <Spinner label="Restoring your session" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }

  return <AppShell />;
}

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />

            <Route element={<RequireAuth />}>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/transactions" element={<TransactionsPage />} />
              <Route path="/budgets" element={<BudgetsPage />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}
