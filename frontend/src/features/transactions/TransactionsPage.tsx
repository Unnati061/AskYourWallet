import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Plus,
  ReceiptText,
  Upload,
} from "lucide-react";
import * as React from "react";

import { Money } from "@/components/Money";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState, ErrorState, Spinner } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { AskAboutThis } from "@/features/chat/AskAboutThis";
import { deleteTransaction, fetchTransactions } from "@/features/transactions/api";
import { ImportDialog } from "@/features/transactions/ImportDialog";
import { TransactionDialog } from "@/features/transactions/TransactionDialog";
import {
  EMPTY_FILTERS,
  TransactionFilters,
  hasActiveFilters,
  type FilterState,
} from "@/features/transactions/TransactionFilters";
import { TransactionsTable } from "@/features/transactions/TransactionsTable";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { errorMessage } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Transaction } from "@/lib/types";

const PAGE_SIZES = [25, 50, 100];

/** Turns the active filters into a question the assistant can actually answer. */
function questionFor(filters: FilterState): string {
  const subject = filters.category ? `${filters.category} spending` : "spending";
  if (filters.start_date && filters.end_date) {
    return `Summarise my ${subject} between ${formatDate(filters.start_date)} and ${formatDate(
      filters.end_date,
    )}.`;
  }
  if (filters.category) {
    return `How much have I spent on ${filters.category} this month, and is it above my usual?`;
  }
  return "Which merchants did I spend the most at this month?";
}

export function TransactionsPage() {
  const [filters, setFilters] = React.useState<FilterState>(EMPTY_FILTERS);
  const [page, setPage] = React.useState(1);
  const [size, setSize] = React.useState(PAGE_SIZES[0]);
  const [notice, setNotice] = React.useState<string | null>(null);

  const [formOpen, setFormOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Transaction | null>(null);
  const [importOpen, setImportOpen] = React.useState(false);
  const [pendingDelete, setPendingDelete] = React.useState<Transaction | null>(null);
  const [deleteError, setDeleteError] = React.useState<string | null>(null);
  const [deleting, setDeleting] = React.useState(false);

  // Typing in the search box should not fire a request per keystroke.
  const search = useDebouncedValue(filters.search);

  const query = useApiQuery(
    () =>
      fetchTransactions({
        search: search || undefined,
        start_date: filters.start_date || undefined,
        end_date: filters.end_date || undefined,
        type: filters.type || undefined,
        category: filters.category || undefined,
        page,
        size,
      }),
    [search, filters.start_date, filters.end_date, filters.type, filters.category, page, size],
  );

  // Any filter change invalidates the current page number, so it is reset here
  // rather than in an effect (which would fire a second request).
  const applyFilters = (next: FilterState) => {
    setFilters(next);
    setPage(1);
  };

  React.useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(null), 4000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const openAdd = () => {
    setEditing(null);
    setFormOpen(true);
  };

  const openEdit = (transaction: Transaction) => {
    setEditing(transaction);
    setFormOpen(true);
  };

  const onConfirmDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteTransaction(pendingDelete.id);
      setPendingDelete(null);
      setNotice("Transaction deleted.");
      // Deleting the last row of a page would otherwise leave an empty table.
      if (query.data && query.data.items.length === 1 && page > 1) setPage(page - 1);
      else query.refetch();
    } catch (error) {
      setDeleteError(errorMessage(error, "Could not delete that transaction."));
    } finally {
      setDeleting(false);
    }
  };

  const data = query.data;
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;
  const firstRow = total === 0 ? 0 : (page - 1) * size + 1;
  const lastRow = Math.min(page * size, total);

  return (
    <div className="space-y-4">
      <PageHeader
        title="Transactions"
        description="Every row in your ledger, filterable and editable."
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => setImportOpen(true)}>
              <Upload />
              Import CSV
            </Button>
            <Button size="sm" onClick={openAdd}>
              <Plus />
              Add transaction
            </Button>
          </>
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

      <TransactionFilters
        value={filters}
        onChange={applyFilters}
        onReset={() => applyFilters(EMPTY_FILTERS)}
      />

      <section className="rounded-lg border border-border bg-card">
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-3 py-2">
          <div className="flex items-center gap-3">
            <h2 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              {total === 0 ? "No results" : `Showing ${firstRow}–${lastRow} of ${total}`}
            </h2>
            {query.loading && data ? <Spinner /> : null}
          </div>

          <div className="flex items-center gap-1">
            <AskAboutThis question={questionFor(filters)} />
            <Select
              aria-label="Rows per page"
              className="h-8 w-[104px] text-xs"
              value={size}
              onChange={(event) => {
                setSize(Number(event.target.value));
                setPage(1);
              }}
            >
              {PAGE_SIZES.map((option) => (
                <option key={option} value={option}>
                  {option} rows
                </option>
              ))}
            </Select>
          </div>
        </header>

        {query.error ? (
          <div className="p-3">
            <ErrorState message={query.error} onRetry={query.refetch} />
          </div>
        ) : query.loading && !data ? (
          <div className="space-y-2 p-3">
            {Array.from({ length: 8 }, (_, index) => (
              <Skeleton key={index} className="h-10 w-full" />
            ))}
          </div>
        ) : data && data.items.length > 0 ? (
          <TransactionsTable items={data.items} onEdit={openEdit} onDelete={setPendingDelete} />
        ) : (
          <EmptyState
            icon={ReceiptText}
            title={hasActiveFilters(filters) ? "Nothing matches those filters" : "No transactions yet"}
            description={
              hasActiveFilters(filters)
                ? "Widen the date range or clear the filters to see more."
                : "Import a CSV statement or add a transaction by hand to get started."
            }
            action={
              hasActiveFilters(filters) ? (
                <Button variant="outline" size="sm" onClick={() => applyFilters(EMPTY_FILTERS)}>
                  Clear filters
                </Button>
              ) : (
                <Button size="sm" onClick={openAdd}>
                  <Plus />
                  Add transaction
                </Button>
              )
            }
          />
        )}

        {pages > 1 ? (
          <footer className="flex items-center justify-between gap-2 border-t border-border px-3 py-2">
            <p className="text-xs text-muted-foreground">
              Page <span className="figure">{page}</span> of <span className="figure">{pages}</span>
            </p>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="size-8"
                onClick={() => setPage(1)}
                disabled={page === 1}
                aria-label="First page"
              >
                <ChevronsLeft />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="size-8"
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
                aria-label="Previous page"
              >
                <ChevronLeft />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="size-8"
                onClick={() => setPage(page + 1)}
                disabled={page >= pages}
                aria-label="Next page"
              >
                <ChevronRight />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="size-8"
                onClick={() => setPage(pages)}
                disabled={page >= pages}
                aria-label="Last page"
              >
                <ChevronsRight />
              </Button>
            </div>
          </footer>
        ) : null}
      </section>

      <TransactionDialog
        open={formOpen}
        transaction={editing}
        onClose={() => setFormOpen(false)}
        onSaved={(saved) => {
          setNotice(editing ? "Transaction updated." : `Added ${saved.merchant ?? saved.description}.`);
          query.refetch();
        }}
      />

      <ImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onImported={(message) => {
          setNotice(message);
          setPage(1);
          query.refetch();
        }}
      />

      <Dialog
        open={Boolean(pendingDelete)}
        onClose={() => {
          setPendingDelete(null);
          setDeleteError(null);
        }}
        title="Delete this transaction?"
        description="This cannot be undone."
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
              {deleting ? "Deleting…" : "Delete"}
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          {deleteError ? <ErrorState message={deleteError} /> : null}
          {pendingDelete ? (
            <div className="flex items-center justify-between gap-4 rounded-md border border-border bg-secondary/40 px-3 py-2">
              <div className="min-w-0">
                <p className="truncate text-sm">
                  {pendingDelete.merchant ?? pendingDelete.description}
                </p>
                <p className="text-xs text-muted-foreground">
                  <span className="figure">{formatDate(pendingDelete.date)}</span>
                  {pendingDelete.category ? <span> · {pendingDelete.category}</span> : null}
                </p>
              </div>
              <Money
                value={pendingDelete.amount}
                size="sm"
                signed={pendingDelete.type === "income"}
                tone={pendingDelete.type === "income" ? "positive" : "default"}
              />
            </div>
          ) : null}
        </div>
      </Dialog>
    </div>
  );
}
