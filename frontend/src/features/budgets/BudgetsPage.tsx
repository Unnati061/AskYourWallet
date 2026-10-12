import { PiggyBank, Plus } from "lucide-react";
import * as React from "react";

import { Money } from "@/components/Money";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState, ErrorState, Spinner } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { deleteBudget, fetchBudgetsOverview } from "@/features/budgets/api";
import { BudgetDialog } from "@/features/budgets/BudgetDialog";
import { BudgetStatusTile } from "@/features/budgets/BudgetStatusTile";
import { BudgetSummary } from "@/features/budgets/BudgetSummary";
import { AskAboutThis } from "@/features/chat/AskAboutThis";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useCategories } from "@/hooks/useCategories";
import { errorMessage } from "@/lib/api";
import { formatPeriod, toNumber } from "@/lib/format";
import type { Budget, BudgetStatus } from "@/lib/types";

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

/** Money in, not money out — these never get a budget, so they are not offered. */
const NON_SPENDING = new Set(["Income", "Transfer"]);

export function BudgetsPage() {
  const now = new Date();
  const [month, setMonth] = React.useState(now.getMonth() + 1);
  const [year, setYear] = React.useState(now.getFullYear());
  const [notice, setNotice] = React.useState<string | null>(null);

  const [formOpen, setFormOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Budget | null>(null);
  const [presetCategory, setPresetCategory] = React.useState<string | undefined>(undefined);
  const [pendingDelete, setPendingDelete] = React.useState<BudgetStatus | null>(null);
  const [deleteError, setDeleteError] = React.useState<string | null>(null);
  const [deleting, setDeleting] = React.useState(false);

  const categories = useCategories();
  const query = useApiQuery(() => fetchBudgetsOverview({ month, year }), [month, year]);

  React.useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(null), 4000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const period = formatPeriod(month, year);
  const years = Array.from({ length: 5 }, (_, index) => now.getFullYear() - 3 + index);
  const statuses = query.data?.statuses ?? [];

  // /budgets/status echoes the requested month for every row, so the scope label
  // has to come from the raw budget: month === null means it recurs. Both lookups
  // key off query.data, not the fallback arrays, which are new on every render.
  const budgetsById = React.useMemo(
    () => new Map((query.data?.budgets ?? []).map((budget) => [budget.id, budget])),
    [query.data],
  );

  const budgetedCategories = React.useMemo(
    () => new Set((query.data?.statuses ?? []).map((status) => status.category)),
    [query.data],
  );

  const unbudgeted = categories.filter(
    (category) => !NON_SPENDING.has(category.name) && !budgetedCategories.has(category.name),
  );

  const overBudget = statuses.filter((status) => status.is_over_budget);

  const openAdd = (category?: string) => {
    setEditing(null);
    setPresetCategory(category);
    setFormOpen(true);
  };

  const openEdit = (status: BudgetStatus) => {
    const budget = budgetsById.get(status.budget_id);
    if (!budget) return;
    setEditing(budget);
    setPresetCategory(undefined);
    setFormOpen(true);
  };

  const onConfirmDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteBudget(pendingDelete.budget_id);
      setPendingDelete(null);
      setNotice(`Removed the ${pendingDelete.category} budget.`);
      query.refetch();
    } catch (error) {
      setDeleteError(errorMessage(error, "Could not remove that budget."));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-4">
      <PageHeader
        title="Budgets"
        description={`A monthly limit per category. Each jar fills as you spend in ${period}.`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
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
            <Button size="sm" onClick={() => openAdd()}>
              <Plus />
              Set a budget
            </Button>
          </div>
        }
      />

      {notice ? (
        <p
          role="status"
          className="rounded-md border border-positive/30 bg-positive/10 px-3 py-2 text-xs text-foreground"
        >
          {notice}
        </p>
      ) : null}

      {query.error ? <ErrorState message={query.error} onRetry={query.refetch} /> : null}

      {query.loading && !query.data ? (
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {[0, 1, 2, 3].map((key) => (
              <Skeleton key={key} className="h-20" />
            ))}
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {[0, 1, 2, 3, 4, 5].map((key) => (
              <Skeleton key={key} className="h-28" />
            ))}
          </div>
        </div>
      ) : null}

      {query.data ? (
        <div className="space-y-4">
          {statuses.length > 0 ? <BudgetSummary statuses={statuses} /> : null}

          {overBudget.length > 0 ? (
            <div
              role="alert"
              className="flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-lg border border-critical/30 bg-critical/5 px-3 py-2 text-xs"
            >
              <span className="font-medium">
                Over the limit in {overBudget.length}{" "}
                {overBudget.length === 1 ? "category" : "categories"}:
              </span>
              {overBudget.map((status) => (
                <span key={status.budget_id} className="text-muted-foreground">
                  {status.category}{" "}
                  <Money
                    value={Math.abs(toNumber(status.remaining))}
                    size="xs"
                    tone="negative"
                  />{" "}
                  over
                </span>
              ))}
            </div>
          ) : null}

          <section className="rounded-lg border border-border bg-card">
            <header className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-3 py-2">
              <div className="flex items-center gap-3">
                <h2 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  {statuses.length === 0
                    ? "No budgets"
                    : `${statuses.length} ${statuses.length === 1 ? "budget" : "budgets"} · most consumed first`}
                </h2>
                {query.loading ? <Spinner /> : null}
              </div>
              <AskAboutThis question={`Which budgets did I go over in ${period}, and by how much?`} />
            </header>

            {statuses.length > 0 ? (
              <div className="grid gap-3 p-3 sm:grid-cols-2 xl:grid-cols-3">
                {statuses.map((status) => {
                  const budget = budgetsById.get(status.budget_id);
                  return (
                    <BudgetStatusTile
                      key={status.budget_id}
                      status={status}
                      className="bg-background"
                      actions={
                        <div className="flex items-center gap-1.5">
                          <Badge variant="secondary">
                            {budget && budget.month !== null ? `${period} only` : "Every month"}
                          </Badge>
                          <span className="flex-1" />
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-[11px]"
                            onClick={() => openEdit(status)}
                          >
                            Edit
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-[11px] text-critical hover:text-critical"
                            onClick={() => setPendingDelete(status)}
                          >
                            Remove
                          </Button>
                        </div>
                      }
                    />
                  );
                })}
              </div>
            ) : (
              <EmptyState
                icon={PiggyBank}
                title="No budgets for this month"
                description="Set a monthly limit per category and each one shows up here as a jar that fills as you spend."
                action={
                  <Button size="sm" onClick={() => openAdd()}>
                    <Plus />
                    Set a budget
                  </Button>
                }
              />
            )}
          </section>

          {unbudgeted.length > 0 ? (
            <section className="rounded-lg border border-dashed border-border px-3 py-3">
              <h2 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                Not budgeted yet
              </h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Spending in these categories is untracked against a limit.
              </p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {unbudgeted.map((category) => (
                  <Button
                    key={category.name}
                    variant="outline"
                    size="sm"
                    className="h-7 px-2 text-[11px]"
                    onClick={() => openAdd(category.name)}
                  >
                    <Plus className="size-3" />
                    {category.name}
                  </Button>
                ))}
              </div>
            </section>
          ) : null}
        </div>
      ) : null}

      <BudgetDialog
        open={formOpen}
        budget={editing}
        presetCategory={presetCategory}
        month={month}
        year={year}
        onClose={() => setFormOpen(false)}
        onSaved={(message) => {
          setNotice(message);
          query.refetch();
        }}
      />

      <Dialog
        open={Boolean(pendingDelete)}
        onClose={() => {
          setPendingDelete(null);
          setDeleteError(null);
        }}
        title="Remove this budget?"
        description="The transactions stay; only the limit goes away."
        footer={
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setPendingDelete(null)}
              disabled={deleting}
            >
              Cancel
            </Button>
            <Button variant="destructive" size="sm" onClick={onConfirmDelete} disabled={deleting}>
              {deleting ? "Removing…" : "Remove"}
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          {deleteError ? <ErrorState message={deleteError} /> : null}
          {pendingDelete ? (
            <div className="flex items-center justify-between gap-4 rounded-md border border-border bg-secondary/40 px-3 py-2">
              <div className="min-w-0">
                <p className="truncate text-sm">{pendingDelete.category}</p>
                <p className="text-xs text-muted-foreground">
                  {budgetsById.get(pendingDelete.budget_id)?.month === null
                    ? "Recurring every month"
                    : `${period} only`}
                </p>
              </div>
              <Money value={pendingDelete.monthly_limit} size="sm" />
            </div>
          ) : null}
        </div>
      </Dialog>
    </div>
  );
}
