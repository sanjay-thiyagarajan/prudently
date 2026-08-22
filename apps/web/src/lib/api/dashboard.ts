"use client";

import useSWR from "swr";

import type { DashboardOverview } from "@/lib/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Polling, not a Firestore realtime listener — the API is the single place with
// Firestore credentials, and polling makes the demo reproducible (the operator controls
// exactly what the page shows when, rather than a listener firing mid-narration).
const POLL_INTERVAL_MS = 4000;

async function fetcher(url: string): Promise<DashboardOverview> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Dashboard fetch failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export function useDashboardOverview() {
  const { data, error, isLoading } = useSWR<DashboardOverview>(
    `${API_BASE_URL}/dashboard/overview`,
    fetcher,
    {
      refreshInterval: POLL_INTERVAL_MS,
      revalidateOnFocus: false,
      keepPreviousData: true,
    },
  );

  return {
    data,
    error,
    isLoading: isLoading && !data,
  };
}
