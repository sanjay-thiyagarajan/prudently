"use client";

import useSWR from "swr";

import { useAuth } from "@/contexts/AuthContext";
import type { ActivityLogEntry } from "@/lib/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function authedFetcher<T>(idToken: string) {
  return async (url: string): Promise<T> => {
    const response = await fetch(url, { headers: { Authorization: `Bearer ${idToken}` } });
    if (!response.ok) {
      throw new Error(`Audit log fetch failed: ${response.status} ${response.statusText}`);
    }
    return response.json();
  };
}

// One bounded pull, not a polled feed — a manager opens this page to review a slice of
// history, not to watch it tick live (that's what /activity is for). `mutate` is exposed so
// the page can offer an explicit "Refresh" action instead.
export function useAuditLog(limit = 500) {
  const { idToken } = useAuth();
  const { data, error, isLoading, mutate } = useSWR<{ entries: ActivityLogEntry[] }>(
    idToken ? [`${API_BASE_URL}/audit/log?limit=${limit}`, idToken] : null,
    ([url, token]: [string, string]) => authedFetcher<{ entries: ActivityLogEntry[] }>(token)(url),
    { revalidateOnFocus: false },
  );
  return { entries: data?.entries ?? [], error, isLoading, refresh: mutate };
}
