import * as React from "react";

/**
 * Returns `value` after it has stopped changing for `delay` ms. Used for the
 * transaction search box so every keystroke does not become a request.
 */
export function useDebouncedValue<T>(value: T, delay = 350): T {
  const [debounced, setDebounced] = React.useState(value);

  React.useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}
