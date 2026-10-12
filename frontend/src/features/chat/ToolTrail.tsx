import { ChartPie, PiggyBank, ReceiptText, TrendingUp, type LucideIcon } from "lucide-react";

import type { ToolCallRecord } from "@/lib/types";

/** The four read-only lookups the backend exposes to the model. */
const TOOLS: Record<string, { label: string; icon: LucideIcon }> = {
  get_transactions: { label: "Transactions", icon: ReceiptText },
  get_spending_by_category: { label: "Spending by category", icon: ChartPie },
  get_budget_status: { label: "Budget status", icon: PiggyBank },
  get_monthly_trend: { label: "Monthly trend", icon: TrendingUp },
};

/** "start_date: 2026-08-01 · category: Groceries", or nothing for an unfiltered call. */
function describeArguments(args: Record<string, unknown>): string {
  return Object.entries(args)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([key, value]) => `${key.replace(/_/g, " ")}: ${String(value)}`)
    .join(" · ");
}

/**
 * The provenance of an answer: which database lookups ran, with what arguments,
 * and what came back. This is what makes a figure auditable instead of a claim —
 * the brief's rule that the model never answers a numeric question unaided is
 * enforced in the backend, and shown here.
 */
export function ToolTrail({ calls }: { calls: ToolCallRecord[] }) {
  if (!calls.length) return null;

  return (
    <div className="mt-2 space-y-1 rounded-md border border-border bg-secondary/30 px-2.5 py-2">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
        Looked up in your ledger
      </p>
      <ul className="space-y-1">
        {calls.map((call, index) => {
          const tool = TOOLS[call.name];
          const Icon = tool?.icon ?? ReceiptText;
          const args = describeArguments(call.arguments);
          return (
            <li key={`${call.name}-${index}`} className="flex items-start gap-1.5 text-[11px]">
              <Icon className="mt-0.5 size-3 shrink-0 text-muted-foreground" aria-hidden />
              <span className="min-w-0">
                <span className="font-medium">{tool?.label ?? call.name}</span>
                {args ? <span className="text-muted-foreground"> ({args})</span> : null}
                <span className="text-muted-foreground"> — {call.summary}</span>
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
