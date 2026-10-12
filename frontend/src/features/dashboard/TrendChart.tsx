import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Money } from "@/components/Money";
import { formatCompactMoney, formatMonthKey, toNumber } from "@/lib/format";
import type { MonthlyTrendItem } from "@/lib/types";

interface Point {
  month: string;
  label: string;
  income: number;
  expenses: number;
  net: number;
}

function TrendTooltip({ active, payload }: { active?: boolean; payload?: { payload: Point }[] }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;

  return (
    <div className="min-w-40 rounded-md border border-border bg-popover px-2.5 py-2 text-xs">
      <p className="font-medium">{formatMonthKey(point.month)}</p>
      <dl className="mt-1.5 space-y-1">
        <div className="flex items-center justify-between gap-4">
          <dt className="text-muted-foreground">Income</dt>
          <dd>
            <Money value={point.income} size="xs" tone="positive" />
          </dd>
        </div>
        <div className="flex items-center justify-between gap-4">
          <dt className="text-muted-foreground">Spent</dt>
          <dd>
            <Money value={point.expenses} size="xs" />
          </dd>
        </div>
        <div className="flex items-center justify-between gap-4 border-t border-border pt-1">
          <dt className="text-muted-foreground">Net</dt>
          <dd>
            <Money value={point.net} size="xs" tone="auto" signed />
          </dd>
        </div>
      </dl>
    </div>
  );
}

export function TrendChart({ items }: { items: MonthlyTrendItem[] }) {
  const points: Point[] = items.map((item) => ({
    month: item.month,
    label: item.label,
    income: toNumber(item.income),
    expenses: toNumber(item.expenses),
    net: toNumber(item.net),
  }));

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-4 text-[11px] text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-4 rounded-full bg-positive" aria-hidden />
          Income
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-4 rounded-full bg-accent" aria-hidden />
          Spent
        </span>
      </div>

      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
            <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="2 4" vertical={false} />
            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={56}
              tickFormatter={(value: number) => formatCompactMoney(value)}
              tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
            />
            <Tooltip content={<TrendTooltip />} cursor={{ stroke: "hsl(var(--border))" }} />
            <Line
              type="monotone"
              dataKey="income"
              stroke="hsl(var(--positive))"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 3.5 }}
            />
            <Line
              type="monotone"
              dataKey="expenses"
              stroke="hsl(var(--accent))"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 3.5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
