import { Search, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { useCategories } from "@/hooks/useCategories";
import type { TransactionType } from "@/lib/types";

/** Everything the table can be narrowed by. Empty string always means "any". */
export interface FilterState {
  search: string;
  start_date: string;
  end_date: string;
  type: TransactionType | "";
  category: string;
}

export const EMPTY_FILTERS: FilterState = {
  search: "",
  start_date: "",
  end_date: "",
  type: "",
  category: "",
};

export function hasActiveFilters(filters: FilterState): boolean {
  return Object.values(filters).some((value) => value !== "");
}

export function TransactionFilters({
  value,
  onChange,
  onReset,
}: {
  value: FilterState;
  onChange: (next: FilterState) => void;
  onReset: () => void;
}) {
  const categories = useCategories();
  const set = <K extends keyof FilterState>(key: K, next: FilterState[K]) =>
    onChange({ ...value, [key]: next });

  return (
    <div className="grid gap-3 rounded-lg border border-border bg-card p-3 sm:grid-cols-2 lg:grid-cols-[minmax(0,2fr)_repeat(4,minmax(0,1fr))_auto] lg:items-end">
      <div className="space-y-1.5">
        <Label htmlFor="filter-search">Search</Label>
        <div className="relative">
          <Search
            aria-hidden
            className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            id="filter-search"
            className="pl-8"
            placeholder="Merchant, description or notes"
            value={value.search}
            onChange={(event) => set("search", event.target.value)}
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="filter-start">From</Label>
        <Input
          id="filter-start"
          type="date"
          value={value.start_date}
          max={value.end_date || undefined}
          onChange={(event) => set("start_date", event.target.value)}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="filter-end">To</Label>
        <Input
          id="filter-end"
          type="date"
          value={value.end_date}
          min={value.start_date || undefined}
          onChange={(event) => set("end_date", event.target.value)}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="filter-type">Direction</Label>
        <Select
          id="filter-type"
          value={value.type}
          onChange={(event) => set("type", event.target.value as TransactionType | "")}
        >
          <option value="">Any</option>
          <option value="expense">Money out</option>
          <option value="income">Money in</option>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="filter-category">Category</Label>
        <Select
          id="filter-category"
          value={value.category}
          onChange={(event) => set("category", event.target.value)}
        >
          <option value="">All categories</option>
          {categories.map((category) => (
            <option key={category.name} value={category.name}>
              {category.name}
            </option>
          ))}
        </Select>
      </div>

      <Button
        variant="ghost"
        size="sm"
        onClick={onReset}
        disabled={!hasActiveFilters(value)}
        className="justify-start sm:col-span-2 lg:col-span-1 lg:justify-center"
      >
        <X />
        Clear
      </Button>
    </div>
  );
}
