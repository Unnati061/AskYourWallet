import { api } from "@/lib/api";
import type {
  ImportResult,
  Transaction,
  TransactionFilters,
  TransactionInput,
  TransactionPage,
} from "@/lib/types";

/**
 * Blank filter fields are dropped rather than sent as empty strings: FastAPI
 * validates `type` against a pattern and `start_date` as a date, so `type=""`
 * would come back as a 422 instead of "no filter".
 */
function toParams(filters: TransactionFilters): Record<string, string | number> {
  const params: Record<string, string | number> = {};
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null || value === "") continue;
    params[key] = value as string | number;
  }
  return params;
}

export async function fetchTransactions(filters: TransactionFilters): Promise<TransactionPage> {
  const { data } = await api.get<TransactionPage>("/transactions", { params: toParams(filters) });
  return data;
}

export async function createTransaction(input: TransactionInput): Promise<Transaction> {
  const { data } = await api.post<Transaction>("/transactions", input);
  return data;
}

/** Partial update: omitted keys are left untouched by the backend. */
export async function updateTransaction(
  id: string,
  input: Partial<TransactionInput>,
): Promise<Transaction> {
  const { data } = await api.put<Transaction>(`/transactions/${id}`, input);
  return data;
}

export async function deleteTransaction(id: string): Promise<void> {
  await api.delete(`/transactions/${id}`);
}

/**
 * CSV import. No Content-Type is set here on purpose: the browser has to write
 * `multipart/form-data; boundary=…` itself, and the shared axios instance
 * deliberately carries no default Content-Type for the same reason.
 */
export async function importTransactions(file: File): Promise<ImportResult> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<ImportResult>("/transactions/import", form);
  return data;
}
