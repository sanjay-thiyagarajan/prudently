"use client";

import useSWR from "swr";

import { useAuth } from "@/contexts/AuthContext";
import type { AgentDetail } from "@/lib/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Slower than the fleet page's 4s (see lib/api/dashboard.ts) — only one agent detail page is
// ever mounted at a time behind the sidebar nav, but its aggregate route re-derives the same
// full Firestore read set as /dashboard/overview, so there's no reason to poll it as tightly.
const POLL_INTERVAL_MS = 8000;

/** Same auth-attachment shape as lib/api/dashboard.ts's fetcher — this route is
 * `optional_firebase_auth` too (services/redaction.py's redact_agent_detail), so a signed-in
 * manager who never sends the token silently gets the anonymous, staff-rows-withheld payload
 * instead of a permissions error, which looks exactly like an outage rather than what it is. */
async function fetcher(url: string, idToken: string | null): Promise<AgentDetail> {
  const response = await fetch(url, {
    headers: idToken ? { Authorization: `Bearer ${idToken}` } : {},
  });
  if (!response.ok) {
    throw new Error(`Agent detail fetch failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export function useAgentDetail(agentName: string) {
  const { idToken } = useAuth();
  const { data, error, isLoading, mutate } = useSWR<AgentDetail>(
    [`${API_BASE_URL}/agents/${encodeURIComponent(agentName)}`, idToken],
    ([url, token]: [string, string | null]) => fetcher(url, token),
    {
      refreshInterval: POLL_INTERVAL_MS,
      revalidateOnFocus: false,
      keepPreviousData: true,
    },
  );

  return { data, error, isLoading: isLoading && !data, refresh: mutate };
}
