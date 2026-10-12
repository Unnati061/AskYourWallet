import { Money } from "@/components/Money";
import { iconFor } from "@/lib/categories";
import { formatDate } from "@/lib/format";
import type { Transaction } from "@/lib/types";

/** Compact list for the dashboard — the full table lives on /transactions. */
export function RecentTransactions({ items }: { items: Transaction[] }) {
  return (
    <ul className="divide-y divide-border">
      {items.map((tx) => {
        const Icon = iconFor(tx.category);
        const isIncome = tx.type === "income";

        return (
          <li key={tx.id} className="flex items-center gap-3 py-2">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-secondary text-muted-foreground">
              <Icon className="size-4" aria-hidden />
            </span>

            <div className="min-w-0 flex-1">
              <p className="truncate text-sm">{tx.merchant ?? tx.description}</p>
              <p className="truncate text-xs text-muted-foreground">
                <span className="figure">{formatDate(tx.date, "d MMM")}</span>
                {tx.category ? <span> · {tx.category}</span> : null}
              </p>
            </div>

            <Money
              value={tx.amount}
              size="sm"
              signed={isIncome}
              tone={isIncome ? "positive" : "default"}
              className="shrink-0"
            />
          </li>
        );
      })}
    </ul>
  );
}
