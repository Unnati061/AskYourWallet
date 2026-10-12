import { ArrowLeftRight, PiggyBank, TableProperties } from "lucide-react";
import type { ReactNode } from "react";

import { Wordmark } from "@/components/Logo";
import { ThemeToggle } from "@/components/ThemeToggle";

const POINTS = [
  {
    icon: TableProperties,
    title: "Import a statement",
    body: "Drop in a CSV from your bank and every row is categorised on arrival.",
  },
  {
    icon: PiggyBank,
    title: "Set monthly limits",
    body: "Per-category budgets that fill up as the month goes on.",
  },
  {
    icon: ArrowLeftRight,
    title: "Ask about the numbers",
    body: "Questions are answered from your own ledger, never from guesswork.",
  },
];

/** Split layout: brand panel on the left, form on the right. */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-svh lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <aside className="hidden flex-col justify-between bg-sidebar p-10 text-sidebar-foreground lg:flex">
        <Wordmark size={32} className="text-sidebar-foreground" />

        <div className="space-y-8">
          <div className="space-y-3">
            <h1 className="max-w-sm text-3xl font-semibold leading-tight tracking-tight">
              Your money, in plain numbers.
            </h1>
            <p className="max-w-sm text-sm text-sidebar-foreground/70">
              A personal ledger with budgets and an assistant that reads the ledger before it
              answers.
            </p>
          </div>

          <ul className="space-y-5">
            {POINTS.map(({ icon: Icon, title, body }) => (
              <li key={title} className="flex gap-3">
                <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md bg-sidebar-accent text-accent">
                  <Icon className="size-4" />
                </span>
                <div className="space-y-0.5">
                  <p className="text-sm font-medium">{title}</p>
                  <p className="max-w-xs text-xs text-sidebar-foreground/60">{body}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs text-sidebar-foreground/40">
          Figures shown in the app come from your own transactions.
        </p>
      </aside>

      <main className="flex flex-col">
        <div className="flex items-center justify-between p-4 lg:justify-end">
          <Wordmark size={26} className="lg:hidden" />
          <ThemeToggle />
        </div>
        <div className="flex flex-1 items-center justify-center px-4 pb-16">
          <div className="w-full max-w-sm">{children}</div>
        </div>
      </main>
    </div>
  );
}
