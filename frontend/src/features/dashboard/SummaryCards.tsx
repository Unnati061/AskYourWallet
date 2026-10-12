import { ArrowDownRight, ArrowUpRight, ShieldCheck, Wallet } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Money } from "@/components/Money";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { formatPercent } from "@/lib/format";
import type { BudgetHealth, BudgetStatus, DashboardSummary } from "@/lib/types";

function StatCard({
  label,
  icon: Icon,
  children,
  footer,
}: {
  label: string;
  icon: LucideIcon;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </p>
        <Icon className="size-4 shrink-0 text-muted-foreground/70" aria-hidden />
      </div>
      <div className="mt-2">{children}</div>
      {footer ? <div className="mt-2 text-xs text-muted-foreground">{footer}</div> : null}
    </Card>
  );
}

const HEALTH_VARIANT: Record<BudgetHealth, "positive" | "warning" | "critical" | "secondary"> = {
  Good: "positive",
  Warning: "warning",
  Critical: "critical",
  "No budgets": "secondary",
};

export function SummaryCards({
  summary,
  budgetStatus,
}: {
  summary: DashboardSummary;
  budgetStatus: BudgetStatus[];
}) {
  const overBudget = budgetStatus.filter((item) => item.is_over_budget);
  // savings_rate arrives as a percentage already (20.31 = 20.31%).
  const savingsRate = summary.savings_rate;

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard
        label="Spent this month"
        icon={ArrowDownRight}
        footer={`${summary.transaction_count} transaction${summary.transaction_count === 1 ? "" : "s"}`}
      >
        <Money value={summary.total_spent} size="xl" />
      </StatCard>

      <StatCard label="Income" icon={ArrowUpRight} footer="Money in this month">
        <Money value={summary.total_income} size="xl" tone="positive" />
      </StatCard>

      <StatCard
        label="Net saved"
        icon={Wallet}
        footer={
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span>Savings rate</span>
              <span className="figure text-foreground">{formatPercent(savingsRate)}</span>
            </div>
            <Progress
              value={savingsRate}
              indicatorClassName={savingsRate < 0 ? "bg-critical" : "bg-primary"}
            />
          </div>
        }
      >
        <Money value={summary.net_savings} size="xl" tone="auto" signed />
      </StatCard>

      <StatCard
        label="Budget health"
        icon={ShieldCheck}
        footer={
          budgetStatus.length === 0
            ? "Set a limit to start tracking"
            : overBudget.length === 0
              ? `${budgetStatus.length} budgets, all within limits`
              : `Over on ${overBudget.map((item) => item.category).join(", ")}`
        }
      >
        <Badge variant={HEALTH_VARIANT[summary.budget_health]} className="text-xs">
          {summary.budget_health}
        </Badge>
      </StatCard>
    </div>
  );
}
