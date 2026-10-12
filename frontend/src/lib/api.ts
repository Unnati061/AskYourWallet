import axios, { AxiosError } from "axios";

/**
 * Single axios instance for the whole app.
 *
 * Paths are written WITHOUT a trailing slash on purpose: the FastAPI routers are
 * mounted as `/api/transactions` etc., and hitting `/api/transactions/` makes
 * Starlette answer with a 307 redirect that drops the CORS headers, so the
 * browser reports it as a network failure.
 */
const baseURL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

// No default Content-Type: axios already sends application/json for plain
// object bodies, and pinning it here would also stamp it onto the CSV upload's
// FormData, so the browser could not add the multipart boundary and FastAPI
// rejected the request with "file: Field required".
export const api = axios.create({ baseURL });

const TOKEN_KEY = "askyourwallet.token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * The auth provider registers here so a 401 anywhere in the app can drop the
 * session, instead of every caller having to handle expiry itself.
 */
let onUnauthorized: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      clearToken();
      onUnauthorized?.();
    }
    return Promise.reject(error);
  },
);

interface ValidationIssue {
  loc?: (string | number)[];
  msg?: string;
}

/**
 * FastAPI reports errors two ways: `{"detail": "message"}` for raised
 * HTTPExceptions and `{"detail": [{loc, msg}, ...]}` for 422 validation
 * failures. Flatten both into something showable in a form.
 */
export function errorMessage(error: unknown, fallback = "Something went wrong."): string {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : fallback;
  }

  const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const messages = (detail as ValidationIssue[])
      .map((issue) => {
        // loc is ["body", "field"] — the last entry is the field name.
        const field = issue.loc?.at(-1);
        const text = issue.msg ?? "is invalid";
        return field && field !== "body" ? `${field}: ${text}` : text;
      })
      .filter(Boolean);
    if (messages.length) return messages.join("; ");
  }

  if (error.code === "ERR_NETWORK") {
    return "Cannot reach the API. Is the backend running?";
  }

  return error.message || fallback;
}
