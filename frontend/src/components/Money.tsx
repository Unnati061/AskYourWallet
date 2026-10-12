import { cn } from "@/lib/utils";
import { formatCompactMoney, formatMoney, toNumber } from "@/lib/format";

export interface MoneyProps {
  value: string | number | null | undefined;
  /** Prefix an explicit + on positive values (net figures, deltas). */
  signed?: boolean;
  /** "auto" colours by sign; the rest are explicit. */
  tone?: "auto" | "default" | "positive" | "negative" | "muted" | "warning";
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  /** Abbreviate to $1.2k — for chart axes and very tight cells. */
  compact?: boolean;
  symbol?: boolean;
  className?: string;
}

const SIZES: Record<NonNullable<MoneyProps["size"]>, string> = {
  xs: "text-xs",
  sm: "text-sm",
  md: "text-base",
  lg: "text-xl",
  xl: "text-3xl",
};

const TONES: Record<Exclude<NonNullable<MoneyProps["tone"]>, "auto">, string> = {
  default: "text-foreground",
  positive: "text-positive",
  negative: "text-negative",
  muted: "text-muted-foreground",
  warning: "text-warning",
};

/**
 * The single place financial figures are rendered.
 *
 * Routing every amount through here is what guarantees the brief's hard
 * requirement — all figures in JetBrains Mono with tabular numerals (the
 * `.figure` class) — instead of hoping each component remembers.
 */
export function Money({
  value,
  signed = false,
  tone = "default",
  size = "sm",
  compact = false,
  symbol = true,
  className,
}: MoneyProps) {
  const amount = toNumber(value);
  const resolvedTone =
    tone === "auto" ? (amount > 0 ? "positive" : amount < 0 ? "negative" : "muted") : tone;
  const text = compact
    ? formatCompactMoney(amount)
    : formatMoney(amount, { signed, symbol });

  return (
    <span className={cn("figure inline-block", SIZES[size], TONES[resolvedTone], className)}>
      {text}
    </span>
  );
}
