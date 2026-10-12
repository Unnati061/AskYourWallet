import { FileUp } from "lucide-react";
import * as React from "react";

import { ErrorState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { importTransactions } from "@/features/transactions/api";
import { errorMessage } from "@/lib/api";

/** Matches MAX_UPLOAD_BYTES in backend/app/routers/transactions.py. */
const MAX_BYTES = 5 * 1024 * 1024;

export function ImportDialog({
  open,
  onClose,
  onImported,
}: {
  open: boolean;
  onClose: () => void;
  /** Called with the backend's message so the page can refetch and report it. */
  onImported: (message: string) => void;
}) {
  const [file, setFile] = React.useState<File | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (open) {
      setFile(null);
      setError(null);
      setBusy(false);
    }
  }, [open]);

  const onPick = (event: React.ChangeEvent<HTMLInputElement>) => {
    const picked = event.target.files?.[0] ?? null;
    setError(null);

    if (picked && picked.size > MAX_BYTES) {
      setFile(null);
      setError("That file is larger than the 5 MB limit.");
      return;
    }
    setFile(picked);
  };

  const onUpload = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const result = await importTransactions(file);
      onImported(result.message);
      onClose();
    } catch (uploadError) {
      setError(errorMessage(uploadError, "Could not import that file."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Import a CSV statement"
      description="Every imported row is categorised on arrival."
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button size="sm" onClick={onUpload} disabled={!file || busy}>
            {busy ? "Importing…" : "Import"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {error ? <ErrorState message={error} /> : null}

        <div className="space-y-1.5">
          <Label htmlFor="csv-file">CSV file</Label>
          <input
            id="csv-file"
            type="file"
            accept=".csv,text/csv"
            onChange={onPick}
            className="block w-full cursor-pointer rounded-md border border-input bg-background text-sm file:mr-3 file:cursor-pointer file:border-0 file:border-r file:border-input file:bg-secondary file:px-3 file:py-2 file:text-sm file:text-secondary-foreground"
          />
          {file ? (
            <p className="text-xs text-muted-foreground">
              <span className="figure">{(file.size / 1024).toFixed(0)} KB</span> · {file.name}
            </p>
          ) : null}
        </div>

        {/* The parser matches column names loosely, so listing the shapes it
            accepts saves a round trip of trial and error. */}
        <div className="space-y-2 rounded-md border border-border bg-secondary/40 p-3">
          <p className="flex items-center gap-2 text-xs font-medium">
            <FileUp className="size-3.5 text-muted-foreground" aria-hidden />
            What the parser looks for
          </p>
          <ul className="space-y-1 text-xs text-muted-foreground">
            <li>A date column (date, posted, transaction date).</li>
            <li>A description column (description, payee, merchant, narrative).</li>
            <li>
              Either one amount column — negative means money out — or a separate
              debit/credit pair.
            </li>
          </ul>
          <p className="text-xs text-muted-foreground">
            Rows that cannot be read are skipped rather than failing the import. Up to 5 MB.
          </p>
        </div>
      </div>
    </Dialog>
  );
}
