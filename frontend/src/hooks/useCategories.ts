import * as React from "react";

import { api } from "@/lib/api";
import type { CategoryInfo } from "@/lib/types";

/**
 * The canonical category list lives in the backend (`app/models/category.py`)
 * and is served by GET /api/categories, so the UI never hardcodes it — a
 * category added there shows up in every picker without a frontend change.
 *
 * The result is cached in a module-level promise: the list is reference data
 * that cannot change during a session, and several screens (transaction form,
 * budget form, settings) ask for it independently.
 */
let cached: Promise<CategoryInfo[]> | null = null;

export function fetchCategories(): Promise<CategoryInfo[]> {
  cached ??= api
    .get<CategoryInfo[]>("/categories")
    .then((response) => response.data)
    .catch((error: unknown) => {
      cached = null; // Let the next caller retry instead of caching the failure.
      throw error;
    });
  return cached;
}

export function useCategories(): CategoryInfo[] {
  const [categories, setCategories] = React.useState<CategoryInfo[]>([]);

  React.useEffect(() => {
    let cancelled = false;
    fetchCategories().then(
      (list) => {
        if (!cancelled) setCategories(list);
      },
      () => {
        // A missing list only degrades the pickers to "Auto", so it is not
        // worth an error banner on the page.
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  return categories;
}
