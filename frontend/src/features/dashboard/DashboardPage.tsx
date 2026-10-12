import { PiggyBank, ReceiptText } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/PageHeader";
import { EmptyState, ErrorState } from "@/components/states";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { BudgetStatusTile } from "@/features/budgets/BudgetStatusTile";
import { AskAboutThis } from "@/features/chat/AskAboutThis";
import { fetchDashboard } from "@/features/dashboard/api";
import { CategoryDonut } from "@/features/dashboard/CategoryDonut";
import { RecentTransactions } from "@/features/dashboard/RecentTransactions";
import { SummaryCards } from "@/features/dashboard/SummaryCards";
import { TrendChart } from "@/features/dashboard/TrendChart";
import { useApiQuery } from "@/hooks/useApiQuery";
import { formatPeriod } from "@/lib/format";
import { cn } from "@/lib/utils";

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

/** A titled panel with an optional "Ask about this" affordance in the corner. */
function Panel({
  title,
  question,
  action,
  children,
  className,
}: {
  title: string;
  question?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Card className={className}>
      <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-2.5">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {title}
        </h2>
        <div className="flex items-center gap-1">
          {action}
          {question ? <AskAboutThis question={question} /> : null}
        </div>
      </div>
      <div className="p-4">{children}</div>
    </Card>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((key) => (
          <Skeleton key={key} className="h-24" />
        ))}
      </div>
      <div className="grid gap-3 xl:grid-cols-3">
        <Skeleton className="h-72 xl:col-span-2" />
        <Skeleton className="h-72" />
      </div>
      <div className="grid gap-3 xl:grid-cols-2">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    </div>
  );
}

export function DashboardPage() {
  const now = new Date();
  const [month, setMonth] = React.useState(now.getMonth() + 1);
  const [year, setYear] = React.useState(now.getFullYear());

  const { data, error, loading, refetch } = useApiQuery(
    () => fetchDashboard({ month, year }),
    [month, year],
  );

  const period = formatPeriod(month, year);
  const years = Array.from({ length: 5 }, (_, index) => now.getFullYear() - 3 + index);

  return (
    <div className="space-y-4">
      <PageHeader
        title="Dashboard"
        description={`Where your money went in ${period}.`}
        actions={
          <div className="flex items-center gap-2">
            <Select
              value={month}
              onChange={(event) => setMonth(Number(event.target.value))}
              aria-label="Month"
              className="w-[130px]"
            >
              {MONTHS.map((name, index) => (
                <option key={name} value={index + 1}>
                  {name}
                </option>
              ))}
            </Select>
            <Select
              value={year}
              onChange={(event) => setYear(Number(event.target.value))}
              aria-label="Year"
              className="w-[92px] font-mono tabular-nums"
            >
              {years.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </Select>
          </div>
        }
      />

      {error ? <ErrorState message={error} onRetry={refetch} /> : null}
      {loading && !data ? <DashboardSkeleton /> : null}

      {data ? (
        <div className="space-y-3">
          <SummaryCards summary={data.summary} budgetStatus={data.budget_status} />

          <div className="grid gap-3 xl:grid-cols-3">
            <Panel
              title="Monthly trend"
              question={`How has my spending changed over the last 6 months?`}
              className="xl:col-span-2"
            >
              {data.monthly_trend.length ? (
                <TrendChart items={data.monthly_trend} />
              ) : (
                <EmptyState
                  icon={ReceiptText}
                  title="No history yet"
                  description="Add or import transactions and the trend will build up month by month."
                />
              )}
            </Panel>

            <Panel
              title="Where it went"
              question={`What did I spend the most on in ${period}, and why is it higher than usual?`}
            >
              {data.category_breakdown.length ? (
                <CategoryDonut items={data.category_breakdown} />
              ) : (
                <EmptyState
                  icon={ReceiptText}
                  title="Nothing spent in this month"
                  description="Pick another month, or add a transaction to see the breakdown."
                />
              )}
            </Panel>
          </div>

          <div className="grid gap-3 xl:grid-cols-2">
            <Panel
              title="Recent transactions"
              question={`List my largest transactions in ${period}.`}
              action={
                <Link
                  to="/transactions"
                  className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "text-[11px]")}
                >
                  View all
                </Link>
              }
            >
              {data.recent_transactions.length ? (
                <RecentTransactions items={data.recent_transactions} />
              ) : (
                <EmptyState
                  icon={ReceiptText}
                  title="No transactions yet"
                  description="Import a CSV statement or add one by hand to get started."
                  action={
                    <Link to="/transactions" className={buttonVariants({ size: "sm" })}>
                      Add a transaction
                    </Link>
                  }
                />
              )}
            </Panel>

            <Panel
              title="Budgets"
              question={`Am I over budget in ${period}, and by how much?`}
              action={
                <Link
                  to="/budgets"
                  className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "text-[11px]")}
                >
                  Manage
                </Link>
              }
            >
              {data.budget_status.length ? (
                <div className="grid gap-2 sm:grid-cols-2">
                  {data.budget_status.slice(0, 6).map((status) => (
                    <BudgetStatusTile key={status.budget_id} status={status} size="sm" />
                  ))}
                </div>
              ) : (
                <EmptyState
                  icon={PiggyBank}
                  title="No budgets set"
                  description="Set a monthly limit per category and each one shows up as a jar that fills as you spend."
                  action={
                    <Link to="/budgets" className={buttonVariants({ size: "sm" })}>
                      Set a budget
                    </Link>
                  }
                />
              )}
            </Panel>
          </div>
        </div>
      ) : null}
    </div>
  );
}
