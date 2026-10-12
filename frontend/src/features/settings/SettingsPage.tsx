import { Check, LogOut, Moon, Sun } from "lucide-react";
import * as React from "react";

import { useTheme, type Theme } from "@/app/ThemeProvider";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useAuth } from "@/features/auth/auth-context";
import { fetchAssistantStatus, fetchLedgerCounts } from "@/features/settings/api";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useCategories } from "@/hooks/useCategories";
import { iconFor } from "@/lib/categories";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Categories that are never budgeted — money in, or money moved. */
const NON_SPENDING = new Set(["Income", "Transfer"]);

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <div className="border-b border-border px-4 py-2.5">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {title}
        </h2>
        {description ? (
          <p className="mt-0.5 text-[11px] text-muted-foreground">{description}</p>
        ) : null}
      </div>
      <div className="p-4">{children}</div>
    </Card>
  );
}

/** A label/value row; values that are figures get the `.figure` treatment. */
function Row({
  label,
  value,
  figure,
}: {
  label: string;
  value: React.ReactNode;
  figure?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-border/60 py-2 last:border-0 last:pb-0 first:pt-0">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={cn("min-w-0 truncate text-sm", figure && "figure")}>{value}</span>
    </div>
  );
}

export function SettingsPage() {
  const { user, signOut } = useAuth();
  const { theme, setTheme } = useTheme();
  const categories = useCategories();

  const counts = useApiQuery(() => fetchLedgerCounts(), []);
  const assistant = useApiQuery(() => fetchAssistantStatus(), []);

  const themes: { value: Theme; label: string; icon: typeof Sun; hint: string }[] = [
    { value: "dark", label: "Dark", icon: Moon, hint: "The default" },
    { value: "light", label: "Light", icon: Sun, hint: "Warm off-white" },
  ];

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Settings"
        description="Your account, how AskYourWallet looks, and what it knows about."
        actions={
          <Button variant="outline" size="sm" onClick={signOut}>
            <LogOut />
            Sign out
          </Button>
        }
      />

      <div className="grid gap-3 lg:grid-cols-2">
        <Section title="Account" description="Read from your session — /auth/me.">
          <Row label="Name" value={user?.full_name ?? "—"} />
          <Row label="Email" value={user?.email ?? "—"} />
          <Row
            label="Member since"
            value={user ? formatDate(user.created_at) : "—"}
            figure
          />
        </Section>

        <Section title="Appearance" description="Stored in this browser, not on the server.">
          <div className="grid grid-cols-2 gap-2">
            {themes.map(({ value, label, icon: Icon, hint }) => {
              const active = theme === value;
              return (
                <button
                  key={value}
                  type="button"
                  onClick={() => setTheme(value)}
                  aria-pressed={active}
                  className={cn(
                    "flex items-start gap-2 rounded-lg border p-3 text-left transition-colors",
                    active
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/40 hover:bg-secondary/40",
                  )}
                >
                  <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-1.5 text-sm font-medium">
                      {label}
                      {active ? <Check className="size-3.5 text-primary" aria-hidden /> : null}
                    </span>
                    <span className="block text-[11px] text-muted-foreground">{hint}</span>
                  </span>
                </button>
              );
            })}
          </div>
        </Section>

        <Section title="Your data" description="Everything is stored in your own account.">
          {counts.error ? (
            <ErrorState message={counts.error} onRetry={counts.refetch} />
          ) : (
            <>
              <Row
                label="Transactions"
                value={counts.loading ? "…" : counts.data?.transactions ?? 0}
                figure
              />
              <Row
                label="Budgets"
                value={counts.loading ? "…" : counts.data?.budgets ?? 0}
                figure
              />
              <Row
                label="Repeating every month"
                value={counts.loading ? "…" : counts.data?.recurringBudgets ?? 0}
                figure
              />
            </>
          )}
        </Section>

        <Section title="AI assistant" description="Groq free tier, called from the backend only.">
          {assistant.error ? (
            <ErrorState message={assistant.error} onRetry={assistant.refetch} />
          ) : assistant.data ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                {assistant.data.enabled ? (
                  <Badge variant="positive">Available</Badge>
                ) : (
                  <Badge variant="warning">Not configured</Badge>
                )}
                {assistant.data.enabled ? (
                  <span className="figure text-xs text-muted-foreground">
                    {assistant.data.model}
                  </span>
                ) : null}
              </div>
              <p className="text-xs text-muted-foreground">{assistant.data.detail}</p>
              <p className="text-xs text-muted-foreground">
                Answers are built from four read-only lookups against your own rows —
                transactions, spending by category, budget status and monthly trend. The model
                never sees the database and never reports a figure it did not look up.
              </p>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">Checking…</p>
          )}
        </Section>
      </div>

      <Section
        title="Categories"
        description="Owned by the backend and served by /api/categories, so every picker agrees."
      >
        {categories.length === 0 ? (
          <p className="text-xs text-muted-foreground">Loading the category list…</p>
        ) : (
          <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {categories.map((category) => {
              const Icon = iconFor(category.name, category.icon);
              return (
                <div
                  key={category.name}
                  className="flex items-center gap-2 rounded-md border border-border bg-secondary/20 px-2.5 py-2"
                >
                  <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
                  <span className="min-w-0 flex-1 truncate text-xs">{category.name}</span>
                  {NON_SPENDING.has(category.name) ? (
                    <Badge variant="secondary" className="shrink-0 text-[10px]">
                      Not budgeted
                    </Badge>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </Section>
    </div>
  );
}
