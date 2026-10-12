import * as React from "react";

import { cn } from "@/lib/utils";

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  /** 0-100. Values above 100 are clamped for the bar but kept in the label. */
  value: number;
  indicatorClassName?: string;
}

/**
 * A thin horizontal meter for non-budget ratios (savings rate, month elapsed).
 * Budgets deliberately do NOT use this — they render as a jar fill.
 */
export function Progress({ value, indicatorClassName, className, ...props }: ProgressProps) {
  const clamped = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));

  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(clamped)}
      className={cn("h-1.5 w-full overflow-hidden rounded-full bg-muted", className)}
      {...props}
    >
      <div
        className={cn("h-full rounded-full bg-primary transition-[width] duration-500", indicatorClassName)}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
