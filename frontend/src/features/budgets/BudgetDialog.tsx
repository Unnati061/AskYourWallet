import { zodResolver } from "@hookform/resolvers/zod";
import * as React from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ErrorState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { saveBudget, updateBudgetLimit } from "@/features/budgets/api";
import { useCategories } from "@/hooks/useCategories";
import { errorMessage } from "@/lib/api";
import { formatPeriod } from "@/lib/format";
import type { Budget } from "@/lib/types";

/** Money in, not money out — budgeting these two would be meaningless. */
const NON_SPENDING = new Set(["Income", "Transfer"]);

/**
 * Mirrors backend/app/schemas/budget.py: monthly_limit > 0 with at most two
 * decimals, category validated against the canonical list. The limit stays a
 * string end to end because the column is a Decimal.
 */
const schema = z.object({
  category: z.string().min(1, "Pick a category"),
  monthly_limit: z
    .string()
    .min(1, "Enter a monthly limit")
    .regex(/^\d+(\.\d{1,2})?$/, "Use digits and up to two decimals, e.g. 400.00")
    .refine((value) => Number(value) > 0, "The limit must be greater than zero"),
  /** "recurring" sends month/year as null, which is how the API marks it. */
  scope: z.enum(["recurring", "period"]),
});

type FormValues = z.infer<typeof schema>;

export interface BudgetDialogProps {
  open: boolean;
  /** A budget opens the form in edit mode; null opens it for a new one. */
  budget: Budget | null;
  /** Preselects the category when the form is opened from an "unbudgeted" chip. */
  presetCategory?: string;
  month: number;
  year: number;
  onClose: () => void;
  onSaved: (message: string) => void;
}

export function BudgetDialog({
  open,
  budget,
  presetCategory,
  month,
  year,
  onClose,
  onSaved,
}: BudgetDialogProps) {
  const categories = useCategories();
  const [formError, setFormError] = React.useState<string | null>(null);
  const editing = Boolean(budget);
  const period = formatPeriod(month, year);

  const defaults = React.useCallback(
    (): FormValues => ({
      category: budget?.category ?? presetCategory ?? "",
      monthly_limit: budget?.monthly_limit ?? "",
      // An existing row keeps whatever scope it was created with: the limit is
      // the only field PUT /budgets/{id} accepts.
      scope: budget ? (budget.month === null ? "recurring" : "period") : "recurring",
    }),
    [budget, presetCategory],
  );

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: defaults() });

  // The form is mounted once and reused, so reopening it has to refill.
  React.useEffect(() => {
    if (open) {
      reset(defaults());
      setFormError(null);
    }
  }, [open, reset, defaults]);

  const onSubmit = async (values: FormValues) => {
    setFormError(null);
    try {
      if (budget) {
        await updateBudgetLimit(budget.id, values.monthly_limit);
        onSaved(`Updated the ${budget.category} limit.`);
      } else {
        await saveBudget({
          category: values.category,
          monthly_limit: values.monthly_limit,
          month: values.scope === "period" ? month : null,
          year: values.scope === "period" ? year : null,
        });
        onSaved(`Saved the ${values.category} budget.`);
      }
      onClose();
    } catch (error) {
      setFormError(errorMessage(error, "Could not save that budget."));
    }
  };

  const options = categories.filter((category) => !NON_SPENDING.has(category.name));

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={budget ? `Edit the ${budget.category} budget` : "Set a budget"}
      description={
        budget
          ? "Only the limit can change here — delete and re-add it to move it to another category."
          : "A limit per category. Setting one that already exists overwrites the old limit."
      }
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" size="sm" form="budget-form" disabled={isSubmitting}>
            {isSubmitting ? "Saving…" : budget ? "Save changes" : "Set budget"}
          </Button>
        </>
      }
    >
      <form id="budget-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        {formError ? <ErrorState message={formError} /> : null}

        <div className="space-y-1.5">
          <Label htmlFor="budget-category">Category</Label>
          <Select
            id="budget-category"
            disabled={editing}
            aria-invalid={Boolean(errors.category)}
            {...register("category")}
          >
            <option value="">Choose a category</option>
            {options.map((category) => (
              <option key={category.name} value={category.name}>
                {category.name}
              </option>
            ))}
          </Select>
          {errors.category ? (
            <p className="text-xs text-critical">{errors.category.message}</p>
          ) : null}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="budget-limit">Monthly limit</Label>
          <Input
            id="budget-limit"
            type="text"
            inputMode="decimal"
            placeholder="400.00"
            className="figure"
            aria-invalid={Boolean(errors.monthly_limit)}
            {...register("monthly_limit")}
          />
          {errors.monthly_limit ? (
            <p className="text-xs text-critical">{errors.monthly_limit.message}</p>
          ) : null}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="budget-scope">Applies to</Label>
          <Select id="budget-scope" disabled={editing} {...register("scope")}>
            <option value="recurring">Every month</option>
            <option value="period">{period} only</option>
          </Select>
          <p className="text-xs text-muted-foreground">
            {editing
              ? budget?.month === null
                ? "This budget repeats every month."
                : `This budget applies to ${formatPeriod(budget?.month ?? month, budget?.year ?? year)} only.`
              : `A ${period}-only budget takes precedence over the recurring one for the same category.`}
          </p>
        </div>
      </form>
    </Dialog>
  );
}
