import { api } from "@/lib/api";
import type { Budget, ChatStatus, TransactionPage } from "@/lib/types";

export interface LedgerCounts {
  transactions: number;
  budgets: number;
  recurringBudgets: number;
}

/**
 * How much is actually stored, for the "Your data" panel.
 *
 * The transaction count comes from the paginated list's `total` with the
 * smallest possible page: there is no count endpoint, and asking for one row is
 * cheaper than pulling a page the panel would throw away.
 */
export async function fetchLedgerCounts(): Promise<LedgerCounts> {
  const [transactions, budgets] = await Promise.all([
    api.get<TransactionPage>("/transactions", { params: { page: 1, size: 1 } }),
    api.get<Budget[]>("/budgets"),
  ]);

  return {
    transactions: transactions.data.total,
    budgets: budgets.data.length,
    // month === null is how the API marks a budget that repeats every month.
    recurringBudgets: budgets.data.filter((budget) => budget.month === null).length,
  };
}

/** Assistant availability, shown here as well as on the Chat page. */
export async function fetchAssistantStatus(): Promise<ChatStatus> {
  const { data } = await api.get<ChatStatus>("/chat/status");
  return data;
}
