import { zodResolver } from "@hookform/resolvers/zod";
import * as React from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ErrorState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { createTransaction, updateTransaction } from "@/features/transactions/api";
import { useCategories } from "@/hooks/useCategories";
import { errorMessage } from "@/lib/api";
import { todayISO } from "@/lib/format";
import type { Transaction, TransactionInput } from "@/lib/types";

/**
 * Mirrors backend/app/schemas/transaction.py: description 1-500, amount > 0 with
 * at most two decimal places, type one of income/expense. Amount stays a string
 * all the way to the API because the column is a Decimal — parsing it into a
 * float here would be the one place rounding could creep in.
 */
const schema = z.object({
  date: z.string().min(1, "Pick a date"),
  description: z
    .string()
    .trim()
    .min(1, "Describe the transaction")
    .max(500, "Keep it under 500 characters"),
  amount: z
    .string()
    .min(1, "Enter an amount")
    .regex(/^\d+(\.\d{1,2})?$/, "Use digits and up to two decimals, e.g. 24.50")
    .refine((value) => Number(value) > 0, "Amount must be greater than zero"),
  type: z.enum(["income", "expense"]),
  /** "" means "let the backend categorise this". */
  category: z.string(),
  merchant: z.string().trim().max(255, "Keep it under 255 characters"),
  notes: z.string(),
});

type FormValues = z.infer<typeof schema>;

function defaultsFor(transaction: Transaction | null): FormValues {
  return {
    date: transaction?.date ?? todayISO(),
    description: transaction?.description ?? "",
    amount: transaction?.amount ?? "",
    type: transaction?.type ?? "expense",
    category: transaction?.category ?? "",
    merchant: transaction?.merchant ?? "",
    notes: transaction?.notes ?? "",
  };
}

export interface TransactionDialogProps {
  open: boolean;
  /** null opens the form empty (add); a transaction opens it prefilled (edit). */
  transaction: Transaction | null;
  onClose: () => void;
  onSaved: (transaction: Transaction) => void;
}

export function TransactionDialog({
  open,
  transaction,
  onClose,
  onSaved,
}: TransactionDialogProps) {
  const categories = useCategories();
  const [formError, setFormError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: defaultsFor(transaction),
  });

  // Reopening the dialog for a different row has to refill the fields; the form
  // is mounted once and reused.
  React.useEffect(() => {
    if (open) {
      reset(defaultsFor(transaction));
      setFormError(null);
    }
  }, [open, transaction, reset]);

  const onSubmit = async (values: FormValues) => {
    setFormError(null);

    const payload: TransactionInput = {
      date: values.date,
      description: values.description,
      amount: values.amount,
      type: values.type,
      merchant: values.merchant || null,
      notes: values.notes || null,
    };
    // Leaving the picker on "Auto" omits the field entirely, which is what makes
    // the backend run the rules engine and then the LLM fallback. On edit the
    // description is always sent, so an omitted category re-derives it too.
    if (values.category) payload.category = values.category;

    try {
      const saved = transaction
        ? await updateTransaction(transaction.id, payload)
        : await createTransaction(payload);
      onSaved(saved);
      onClose();
    } catch (error) {
      setFormError(errorMessage(error, "Could not save the transaction."));
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={transaction ? "Edit transaction" : "Add transaction"}
      description={
        transaction
          ? "Changing the description re-runs categorisation unless you pick a category."
          : "Leave the category on Auto and it will be worked out from the description."
      }
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            type="submit"
            size="sm"
            form="transaction-form"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Saving…" : transaction ? "Save changes" : "Add transaction"}
          </Button>
        </>
      }
    >
      <form
        id="transaction-form"
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4"
        noValidate
      >
        {formError ? <ErrorState message={formError} /> : null}

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="tx-date">Date</Label>
            <Input id="tx-date" type="date" aria-invalid={Boolean(errors.date)} {...register("date")} />
            {errors.date ? <p className="text-xs text-critical">{errors.date.message}</p> : null}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="tx-amount">Amount</Label>
            <Input
              id="tx-amount"
              type="text"
              inputMode="decimal"
              placeholder="0.00"
              className="figure"
              aria-invalid={Boolean(errors.amount)}
              {...register("amount")}
            />
            {errors.amount ? (
              <p className="text-xs text-critical">{errors.amount.message}</p>
            ) : null}
          </div>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="tx-description">Description</Label>
          <Input
            id="tx-description"
            placeholder="Whole Foods Market"
            aria-invalid={Boolean(errors.description)}
            {...register("description")}
          />
          {errors.description ? (
            <p className="text-xs text-critical">{errors.description.message}</p>
          ) : null}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="tx-type">Direction</Label>
            <Select id="tx-type" {...register("type")}>
              <option value="expense">Money out</option>
              <option value="income">Money in</option>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="tx-category">Category</Label>
            <Select id="tx-category" {...register("category")}>
              <option value="">Auto — work it out for me</option>
              {categories.map((category) => (
                <option key={category.name} value={category.name}>
                  {category.name}
                </option>
              ))}
            </Select>
          </div>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="tx-merchant">Merchant (optional)</Label>
          <Input
            id="tx-merchant"
            placeholder="Left blank, it is taken from the description"
            aria-invalid={Boolean(errors.merchant)}
            {...register("merchant")}
          />
          {errors.merchant ? (
            <p className="text-xs text-critical">{errors.merchant.message}</p>
          ) : null}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="tx-notes">Notes (optional)</Label>
          <Textarea id="tx-notes" rows={2} {...register("notes")} />
        </div>
      </form>
    </Dialog>
  );
}
