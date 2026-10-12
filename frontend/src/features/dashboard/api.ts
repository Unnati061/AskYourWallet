import { api } from "@/lib/api";
import type { DashboardPayload } from "@/lib/types";

/** Omitting month/year makes the backend use the current month. */
export async function fetchDashboard(params: { month: number; year: number }) {
  const { data } = await api.get<DashboardPayload>("/dashboard", { params });
  return data;
}
