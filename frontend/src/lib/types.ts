/**
 * Mirrors the FastAPI response models exactly.
 *
 * One thing to watch: every monetary field is a Python `Decimal`, which
 * FastAPI serialises as a JSON *string* ("82.50") to avoid float rounding.
 * They are typed as `string` here and must go through `toNumber()`/`formatMoney()`
 * from `lib/format` before any arithmetic or charting.
 */

export type TransactionType = "income" | "expense";

export interface User {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Transaction {
  id: string;
  user_id: string;
  date: string; // YYYY-MM-DD
  description: string;
  amount: string; // Decimal
  type: TransactionType;
  category: string | null;
  merchant: string | null;
  notes: string | null;
  created_at: string;
}

export interface TransactionPage {
  items: Transaction[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface TransactionInput {
  date: string;
  description: string;
  amount: string;
  type: TransactionType;
  /** null / omitted means "let the backend categorise it". */
  category?: string | null;
  merchant?: string | null;
  notes?: string | null;
}

export interface TransactionFilters {
  start_date?: string;
  end_date?: string;
  type?: TransactionType;
  category?: string;
  search?: string;
  page?: number;
  size?: number;
}

export interface ImportResult {
  imported_count: number;
  message: string;
}

export interface CategoryInfo {
  name: string;
  /** Lucide icon name in kebab-case, e.g. "shopping-cart". */
  icon: string;
}

export interface Budget {
  id: string;
  user_id: string;
  category: string;
  monthly_limit: string; // Decimal
  /** null on both fields means the budget recurs every month. */
  month: number | null;
  year: number | null;
  created_at: string;
  updated_at: string;
}

export interface BudgetStatus {
  budget_id: string;
  category: string;
  monthly_limit: string; // Decimal
  actual_spent: string; // Decimal
  remaining: string; // Decimal — negative when over budget
  /** Already a percentage: 75.0 means 75%. Never multiply by 100. */
  percentage_used: number;
  is_over_budget: boolean;
  month: number;
  year: number;
}

export interface BudgetInput {
  category: string;
  monthly_limit: string;
  month?: number | null;
  year?: number | null;
}

export type BudgetHealth = "Good" | "Warning" | "Critical" | "No budgets";

export interface DashboardSummary {
  total_spent: string;
  total_income: string;
  net_savings: string;
  /** Already a percentage: 20.31 means 20.31%. Never multiply by 100. */
  savings_rate: number;
  budget_health: BudgetHealth;
  transaction_count: number;
}

export interface CategoryBreakdownItem {
  category: string;
  amount: string; // Decimal
  percentage: number; // already 0-100
  icon: string;
}

export interface MonthlyTrendItem {
  month: string; // "YYYY-MM"
  label: string; // "Aug 26", pre-formatted for chart axes
  income: string; // Decimal
  expenses: string; // Decimal
  net: string; // Decimal
}

export interface DashboardPayload {
  month: number;
  year: number;
  summary: DashboardSummary;
  category_breakdown: CategoryBreakdownItem[];
  monthly_trend: MonthlyTrendItem[];
  budget_status: BudgetStatus[];
  recent_transactions: Transaction[];
}

export interface ChatHistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ToolCallRecord {
  name: string;
  arguments: Record<string, unknown>;
  summary: string;
}

export interface ChatResponse {
  response: string;
  tool_calls: ToolCallRecord[];
  suggested_actions: string[];
  /** False when the answer came back without a database lookup. */
  grounded: boolean;
}

export interface ChatStatus {
  enabled: boolean;
  model: string;
  detail: string;
}
