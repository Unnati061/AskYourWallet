import { api } from "@/lib/api";
import type { Budget, BudgetInput, BudgetStatus } from "@/lib/types";

/** Limits joined with actual spending for one month. Sorted most-consumed first by the API. */
export async function fetchBudgetStatus(period: {
  month: number;
  year: number;
}): Promise<BudgetStatus[]> {
  const { data } = await api.get<BudgetStatus[]>("/budgets/status", { params: period });
  return data;
}

/** The raw budget rows — the only place that says whether a budget recurs. */
export async function fetchBudgets(): Promise<Budget[]> {
  const { data } = await api.get<Budget[]>("/budgets");
  return data;
}

export interface BudgetsOverview {
  statuses: BudgetStatus[];
  budgets: Budget[];
}

/**
 * The page needs both lists together: /budgets/status carries the spending but
 * always reports the requested month, so only /budgets can tell a recurring
 * budget (month/year null) apart from one set for this period alone.
 */
export async function fetchBudgetsOverview(period: {
  month: number;
  year: number;
}): Promise<BudgetsOverview> {
  const [statuses, budgets] = await Promise.all([fetchBudgetStatus(period), fetchBudgets()]);
  return { statuses, budgets };
}

/**
 * PUT (not POST) on purpose: this is the idempotent upsert, so re-submitting a
 * category the user has already budgeted updates the limit instead of
 * dead-ending on the 409 that POST returns for a duplicate period.
 */
export async function saveBudget(input: BudgetInput): Promise<Budget> {
  const { data } = await api.put<Budget>("/budgets", input);
  return data;
}

/** Editing an existing row: the backend's BudgetUpdate accepts only the limit. */
export async function updateBudgetLimit(id: string, monthlyLimit: string): Promise<Budget> {
  const { data } = await api.put<Budget>(`/budgets/${id}`, { monthly_limit: monthlyLimit });
  return data;
}

export async function deleteBudget(id: string): Promise<void> {
  await api.delete(`/budgets/${id}`);
}
