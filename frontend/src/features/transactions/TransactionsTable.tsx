import { Pencil, Trash2 } from "lucide-react";

import { Money } from "@/components/Money";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { iconFor } from "@/lib/categories";
import { formatDate } from "@/lib/format";
import type { Transaction } from "@/lib/types";

export function TransactionsTable({
  items,
  onEdit,
  onDelete,
}: {
  items: Transaction[];
  onEdit: (transaction: Transaction) => void;
  onDelete: (transaction: Transaction) => void;
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead className="w-[104px]">Date</TableHead>
          <TableHead>Description</TableHead>
          <TableHead className="w-[168px]">Category</TableHead>
          <TableHead className="w-[120px] text-right">Amount</TableHead>
          <TableHead className="w-[72px] text-right">
            <span className="sr-only">Actions</span>
          </TableHead>
        </TableRow>
      </TableHeader>

      <TableBody>
        {items.map((tx) => {
          const Icon = iconFor(tx.category);
          const isIncome = tx.type === "income";
          // The merchant is the headline when we have one; the raw statement
          // description goes underneath so nothing is hidden from the user.
          const showDescription = Boolean(tx.merchant) && tx.merchant !== tx.description;

          return (
            <TableRow key={tx.id} className="group">
              <TableCell className="whitespace-nowrap">
                <span className="figure text-xs text-muted-foreground">
                  {formatDate(tx.date, "d MMM yy")}
                </span>
              </TableCell>

              <TableCell className="max-w-[420px]">
                <p className="truncate text-sm">{tx.merchant ?? tx.description}</p>
                {showDescription ? (
                  <p className="truncate text-xs text-muted-foreground">{tx.description}</p>
                ) : null}
                {tx.notes ? (
                  <p className="truncate text-xs italic text-muted-foreground/80">{tx.notes}</p>
                ) : null}
              </TableCell>

              <TableCell>
                <span className="inline-flex items-center gap-2 text-xs">
                  <Icon className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
                  {tx.category ?? "Uncategorised"}
                </span>
              </TableCell>

              <TableCell className="text-right">
                <Money
                  value={tx.amount}
                  size="sm"
                  signed={isIncome}
                  tone={isIncome ? "positive" : "default"}
                />
              </TableCell>

              <TableCell className="text-right">
                {/* Row actions stay visible on touch devices, where there is no
                    hover to reveal them. */}
                <div className="flex items-center justify-end gap-0.5">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7"
                    onClick={() => onEdit(tx)}
                    aria-label={`Edit ${tx.merchant ?? tx.description}`}
                  >
                    <Pencil className="size-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7 text-muted-foreground hover:text-critical"
                    onClick={() => onDelete(tx)}
                    aria-label={`Delete ${tx.merchant ?? tx.description}`}
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
