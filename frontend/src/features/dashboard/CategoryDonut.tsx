import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { Money } from "@/components/Money";
import { chartColor, iconFor } from "@/lib/categories";
import { formatPercent, toNumber } from "@/lib/format";
import type { CategoryBreakdownItem } from "@/lib/types";

interface Slice {
  category: string;
  amount: number;
  percentage: number;
  icon: string;
}

function DonutTooltip({ active, payload }: { active?: boolean; payload?: { payload: Slice }[] }) {
  if (!active || !payload?.length) return null;
  const slice = payload[0].payload;

  return (
    <div className="rounded-md border border-border bg-popover px-2.5 py-2 text-xs shadow-sm">
      <p className="font-medium">{slice.category}</p>
      <p className="mt-0.5 flex items-center gap-2">
        <Money value={slice.amount} size="xs" />
        <span className="figure text-muted-foreground">{formatPercent(slice.percentage)}</span>
      </p>
    </div>
  );
}

export function CategoryDonut({ items }: { items: CategoryBreakdownItem[] }) {
  const slices: Slice[] = items.map((item) => ({
    category: item.category,
    amount: toNumber(item.amount),
    percentage: item.percentage,
    icon: item.icon,
  }));
  const total = slices.reduce((sum, slice) => sum + slice.amount, 0);

  return (
    <div className="space-y-3">
      <div className="relative h-44">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={slices}
              dataKey="amount"
              nameKey="category"
              innerRadius="62%"
              outerRadius="94%"
              paddingAngle={1.5}
              stroke="hsl(var(--card))"
              strokeWidth={2}
              isAnimationActive={false}
            >
              {slices.map((slice, index) => (
                <Cell key={slice.category} fill={chartColor(index)} />
              ))}
            </Pie>
            <Tooltip content={<DonutTooltip />} />
          </PieChart>
        </ResponsiveContainer>

        {/* Centre label: the month's total outgoings. */}
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[10px] uppercase tracking-wide text-muted-foreground">Spent</span>
          <Money value={total} size="md" />
        </div>
      </div>

      <ul className="max-h-52 space-y-1 overflow-y-auto scroll-slim pr-1">
        {slices.map((slice, index) => {
          const Icon = iconFor(slice.category, slice.icon);
          return (
            <li
              key={slice.category}
              className="flex items-center gap-2.5 rounded-md px-1.5 py-1 hover:bg-secondary/60"
            >
              <span
                className="size-2 shrink-0 rounded-full"
                style={{ backgroundColor: chartColor(index) }}
                aria-hidden
              />
              <Icon className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
              <span className="min-w-0 flex-1 truncate text-xs">{slice.category}</span>
              <span className="figure inline-block w-11 text-right text-[11px] text-muted-foreground">
                {formatPercent(slice.percentage, 0)}
              </span>
              <Money value={slice.amount} size="xs" className="w-20 text-right" />
            </li>
          );
        })}
      </ul>
    </div>
  );
}
