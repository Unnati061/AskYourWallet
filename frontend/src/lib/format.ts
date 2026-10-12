import { format, parseISO } from "date-fns";

/**
 * Formatting helpers for money, percentages and dates.
 *
 * The MVP is single-currency by design (multi-currency is explicitly out of
 * scope), so the symbol lives here as one constant rather than being threaded
 * through every component.
 */
export const CURRENCY_SYMBOL = "$";

/** Decimal fields arrive from the API as strings; parse defensively. */
export function toNumber(value: string | number | null | undefined): number {
  if (value === null || value === undefined || value === "") return 0;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

const groupedFormatter = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export interface MoneyFormatOptions {
  /** Prefix the currency symbol. Default true. */
  symbol?: boolean;
  /** Always show + or -, used for net figures. Default false. */
  signed?: boolean;
  /** Drop the cents, e.g. for chart axis ticks. Default false. */
  round?: boolean;
}

/** "1048.2" -> "$1,048.20". Never used for arithmetic, only for display. */
export function formatMoney(
  value: string | number | null | undefined,
  options: MoneyFormatOptions = {},
): string {
  const { symbol = true, signed = false, round = false } = options;
  const amount = toNumber(value);
  const magnitude = Math.abs(amount);
  const body = round
    ? Math.round(magnitude).toLocaleString("en-US")
    : groupedFormatter.format(magnitude);

  let sign = "";
  if (amount < 0) sign = "-";
  else if (signed && amount > 0) sign = "+";

  return `${sign}${symbol ? CURRENCY_SYMBOL : ""}${body}`;
}

/** Axis ticks and dense cards: 1234 -> "$1.2k". */
export function formatCompactMoney(value: string | number | null | undefined): string {
  const amount = toNumber(value);
  const magnitude = Math.abs(amount);
  const sign = amount < 0 ? "-" : "";
  if (magnitude >= 1_000_000) return `${sign}${CURRENCY_SYMBOL}${(magnitude / 1_000_000).toFixed(1)}m`;
  if (magnitude >= 1_000) return `${sign}${CURRENCY_SYMBOL}${(magnitude / 1_000).toFixed(1)}k`;
  return `${sign}${CURRENCY_SYMBOL}${Math.round(magnitude)}`;
}

/** The API already returns percentages (75.0 = 75%), so this never rescales. */
export function formatPercent(value: number | null | undefined, digits = 1): string {
  const pct = toNumber(value);
  return `${pct.toFixed(digits)}%`;
}

/** "2026-08-20" -> "20 Aug 2026". parseISO keeps date-only strings local. */
export function formatDate(value: string, pattern = "d MMM yyyy"): string {
  try {
    return format(parseISO(value), pattern);
  } catch {
    return value;
  }
}

/** "2026-08" -> "August 2026", for period headings. */
export function formatMonthKey(monthKey: string): string {
  try {
    return format(parseISO(`${monthKey}-01`), "MMMM yyyy");
  } catch {
    return monthKey;
  }
}

export function formatPeriod(month: number, year: number): string {
  return formatMonthKey(`${year}-${String(month).padStart(2, "0")}`);
}

/** Today's date as YYYY-MM-DD, for date input defaults. */
export function todayISO(): string {
  return format(new Date(), "yyyy-MM-dd");
}
