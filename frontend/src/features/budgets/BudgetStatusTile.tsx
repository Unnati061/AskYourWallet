import type { ReactNode } from "react";

import { Money } from "@/components/Money";
import { BudgetJar, jarTone } from "@/features/budgets/BudgetJar";
import { iconFor } from "@/lib/categories";
import { formatPercent, toNumber } from "@/lib/format";
import type { BudgetStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const TONE_TEXT = {
  positive: "text-positive",
  warning: "text-warning",
  critical: "text-critical",
} as const;

/** One budget: jar on the left, the figures on the right. Shared by the dashboard and /budgets. */
export function BudgetStatusTile({
  status,
  size = "md",
  actions,
  className,
}: {
  status: BudgetStatus;
  size?: "sm" | "md" | "lg";
  actions?: ReactNode;
  className?: string;
}) {
  const Icon = iconFor(status.category);
  const tone = jarTone(status.percentage_used);
  const remaining = toNumber(status.remaining);

  return (
    <div className={cn("flex items-center gap-3 rounded-lg border border-border p-3", className)}>
      <BudgetJar percentUsed={status.percentage_used} size={size} />

      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-center gap-1.5">
          <Icon className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
          <p className="min-w-0 flex-1 truncate text-sm font-medium">{status.category}</p>
          <span className={cn("figure text-xs font-medium", TONE_TEXT[tone])}>
            {formatPercent(status.percentage_used, 0)}
          </span>
        </div>

        <p className="text-xs text-muted-foreground">
          <Money value={status.actual_spent} size="xs" tone="default" /> of{" "}
          <Money value={status.monthly_limit} size="xs" tone="muted" />
        </p>

        <p className="text-xs">
          {status.is_over_budget ? (
            <span className="text-critical">
              <Money value={Math.abs(remaining)} size="xs" tone="negative" /> over
            </span>
          ) : (
            <span className="text-muted-foreground">
              <Money value={remaining} size="xs" tone="default" /> left
            </span>
          )}
        </p>

        {actions ? <div className="pt-1">{actions}</div> : null}
      </div>
    </div>
  );
}
