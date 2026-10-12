import type { ReactNode } from "react";

import { Money } from "@/components/Money";
import { formatPercent, toNumber } from "@/lib/format";
import type { BudgetStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

interface BudgetTotals {
  budgeted: number;
  spent: number;
  remaining: number;
  overCount: number;
  /** Spent against the sum of all limits, as a percentage. */
  percentUsed: number;
}

/**
 * Totals are summed here rather than read from an API field: /budgets/status is
 * per-category, and the arithmetic has to happen on numbers parsed out of the
 * Decimal strings.
 */
function totalsFor(statuses: BudgetStatus[]): BudgetTotals {
  const budgeted = statuses.reduce((sum, status) => sum + toNumber(status.monthly_limit), 0);
  const spent = statuses.reduce((sum, status) => sum + toNumber(status.actual_spent), 0);
  return {
    budgeted,
    spent,
    remaining: budgeted - spent,
    overCount: statuses.filter((status) => status.is_over_budget).length,
    percentUsed: budgeted > 0 ? (spent / budgeted) * 100 : 0,
  };
}

function Stat({
  label,
  children,
  hint,
  className,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
  className?: string;
}) {
  return (
    <div className={cn("rounded-lg border border-border bg-card p-3", className)}>
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <div className="mt-1.5">{children}</div>
      {hint ? <p className="mt-0.5 text-[11px] text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

/** The four figures that answer "how am I doing this month" at a glance. */
export function BudgetSummary({ statuses }: { statuses: BudgetStatus[] }) {
  const totals = totalsFor(statuses);

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Stat label="Budgeted" hint={`${statuses.length} categories`}>
        <Money value={totals.budgeted} size="lg" />
      </Stat>

      <Stat label="Spent" hint={`${formatPercent(totals.percentUsed, 0)} of the total`}>
        <Money
          value={totals.spent}
          size="lg"
          tone={totals.percentUsed > 100 ? "negative" : totals.percentUsed >= 80 ? "warning" : "default"}
        />
      </Stat>

      <Stat
        label={totals.remaining < 0 ? "Overspent" : "Still available"}
        hint={totals.remaining < 0 ? "Across every budget" : "Left before the limits"}
      >
        <Money
          value={Math.abs(totals.remaining)}
          size="lg"
          tone={totals.remaining < 0 ? "negative" : "positive"}
        />
      </Stat>

      <Stat
        label="Over budget"
        hint={totals.overCount === 0 ? "Nothing over the limit" : "Categories past their limit"}
      >
        <span
          className={cn(
            "figure text-xl",
            totals.overCount > 0 ? "text-critical" : "text-positive",
          )}
        >
          {totals.overCount}
        </span>
      </Stat>
    </div>
  );
}
