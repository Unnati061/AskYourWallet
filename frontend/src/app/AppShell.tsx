import {
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquareText,
  PiggyBank,
  ReceiptText,
  Settings,
  X,
} from "lucide-react";
import * as React from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { Wordmark } from "@/components/Logo";
import { Spinner } from "@/components/states";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/auth-context";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/transactions", label: "Transactions", icon: ReceiptText, end: false },
  { to: "/budgets", label: "Budgets", icon: PiggyBank, end: false },
  { to: "/chat", label: "Chat", icon: MessageSquareText, end: false },
  { to: "/settings", label: "Settings", icon: Settings, end: false },
];

function initialsOf(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { user, signOut } = useAuth();

  return (
    <div className="flex h-full flex-col bg-sidebar text-sidebar-foreground">
      <div className="flex h-14 items-center gap-2 border-b border-sidebar-border px-4">
        <Wordmark size={26} />
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto scroll-slim p-2">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-sidebar-accent font-medium text-sidebar-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
              )
            }
          >
            {({ isActive }) => (
              <>
                {/* A thin amber rule marks the active section. */}
                <span
                  className={cn(
                    "h-4 w-0.5 rounded-full transition-colors",
                    isActive ? "bg-accent" : "bg-transparent",
                  )}
                  aria-hidden
                />
                <Icon className="size-4 shrink-0" />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-sidebar-border p-3">
        <div className="flex items-center gap-2.5">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-sidebar-accent text-xs font-semibold">
            {user ? initialsOf(user.full_name) : "?"}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{user?.full_name}</p>
            <p className="truncate text-xs text-sidebar-foreground/60">{user?.email}</p>
          </div>
        </div>
        <div className="mt-2 flex items-center gap-1">
          <ThemeToggle className="text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground" />
          <Button
            variant="ghost"
            size="sm"
            onClick={signOut}
            className="flex-1 justify-start text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground"
          >
            <LogOut />
            Sign out
          </Button>
        </div>
      </div>
    </div>
  );
}

export function AppShell() {
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const location = useLocation();

  // Close the mobile drawer whenever the route changes.
  React.useEffect(() => setDrawerOpen(false), [location.pathname]);

  return (
    <div className="flex min-h-svh">
      <aside className="hidden w-60 shrink-0 border-r border-sidebar-border lg:block">
        <div className="sticky top-0 h-svh">
          <SidebarContent />
        </div>
      </aside>

      {drawerOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-background/85 animate-in fade-in-0"
            onClick={() => setDrawerOpen(false)}
            aria-hidden
          />
          <div className="relative z-10 h-full w-64 animate-in slide-in-from-left-4">
            <SidebarContent onNavigate={() => setDrawerOpen(false)} />
          </div>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center gap-2 border-b border-border bg-card px-3 lg:hidden">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setDrawerOpen((open) => !open)}
            aria-label={drawerOpen ? "Close navigation" : "Open navigation"}
          >
            {drawerOpen ? <X /> : <Menu />}
          </Button>
          <Wordmark size={24} />
        </header>

        <main className="min-w-0 flex-1 p-4 lg:p-6">
          {/* Route chunks load here; the sidebar and header stay on screen. */}
          <React.Suspense
            fallback={
              <div className="flex min-h-[60svh] items-center justify-center">
                <Spinner />
              </div>
            }
          >
            <Outlet />
          </React.Suspense>
        </main>
      </div>
    </div>
  );
}
