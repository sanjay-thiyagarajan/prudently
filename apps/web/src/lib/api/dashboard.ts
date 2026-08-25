"use client";

import useSWR from "swr";

import { useAuth } from "@/contexts/AuthContext";
import type { DashboardOverview } from "@/lib/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Polling, not a Firestore realtime listener — the API is the single place with
// Firestore credentials, and polling makes the demo reproducible (the operator controls
// exactly what the page shows when, rather than a listener firing mid-narration).
const POLL_INTERVAL_MS = 4000;

/**
 * `/dashboard/overview` is public but not uniform: signed out it returns aggregates only,
 * signed in it returns the per-employee rows the dashboard actually renders (see
 * apps/api/services/redaction.py). So the token has to be attached here — without it a
 * signed-in manager silently gets the anonymous payload and every staff panel renders
 * empty, which looks exactly like a data outage rather than a permissions decision.
 *
 * The token is part of the SWR key, not just the request: when a manager signs in or out,
 * the key changes and SWR refetches instead of serving the other posture's cached payload.
 */
async function fetcher(url: string, idToken: string | null): Promise<DashboardOverview> {
  const response = await fetch(url, {
    headers: idToken ? { Authorization: `Bearer ${idToken}` } : {},
  });
  if (!response.ok) {
    throw new Error(`Dashboard fetch failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export function useDashboardOverview() {
  const { idToken } = useAuth();
  const { data, error, isLoading, mutate } = useSWR<DashboardOverview>(
    [`${API_BASE_URL}/dashboard/overview`, idToken],
    ([url, token]: [string, string | null]) => fetcher(url, token),
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
    /** True when the API withheld staff-level rows because the caller was anonymous. */
    isPublicView: data?._public_view === true,
    refresh: mutate,
  };
}
