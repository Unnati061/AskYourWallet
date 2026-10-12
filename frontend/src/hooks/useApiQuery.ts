import * as React from "react";

import { errorMessage } from "@/lib/api";

export interface QueryState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

export interface QueryResult<T> extends QueryState<T> {
  refetch: () => void;
  /** Overwrite the cached value after a mutation, avoiding a round trip. */
  setData: (data: T) => void;
}

/**
 * Minimal data-fetching hook.
 *
 * The fetcher is kept in a ref and the caller passes an explicit dependency
 * list, so re-renders that merely recreate the closure (or a filters object)
 * do not trigger a refetch — the failure mode of the previous `useFetch`,
 * which depended on an options object with a fresh identity each render.
 */
export function useApiQuery<T>(
  fetcher: () => Promise<T>,
  deps: React.DependencyList,
): QueryResult<T> {
  const [state, setState] = React.useState<QueryState<T>>({
    data: null,
    error: null,
    loading: true,
  });
  const [nonce, setNonce] = React.useState(0);

  const fetcherRef = React.useRef(fetcher);
  fetcherRef.current = fetcher;

  React.useEffect(() => {
    let cancelled = false;
    setState((previous) => ({ ...previous, loading: true, error: null }));

    fetcherRef.current().then(
      (data) => {
        if (!cancelled) setState({ data, error: null, loading: false });
      },
      (error: unknown) => {
        if (!cancelled) setState({ data: null, error: errorMessage(error), loading: false });
      },
    );

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  return {
    ...state,
    refetch: React.useCallback(() => setNonce((value) => value + 1), []),
    setData: React.useCallback((data: T) => setState({ data, error: null, loading: false }), []),
  };
}
