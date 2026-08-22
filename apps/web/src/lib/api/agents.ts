"use client";

import useSWR from "swr";

import type { AgentDetail } from "@/lib/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Slower than the fleet page's 4s (see lib/api/dashboard.ts) — only one agent detail page is
// ever mounted at a time behind the sidebar nav, but its aggregate route re-derives the same
// full Firestore read set as /dashboard/overview, so there's no reason to poll it as tightly.
const POLL_INTERVAL_MS = 8000;

async function fetcher(url: string): Promise<AgentDetail> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Agent detail fetch failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export function useAgentDetail(agentName: string) {
  const { data, error, isLoading } = useSWR<AgentDetail>(
    `${API_BASE_URL}/agents/${encodeURIComponent(agentName)}`,
    fetcher,
    {
      refreshInterval: POLL_INTERVAL_MS,
      revalidateOnFocus: false,
      keepPreviousData: true,
    },
  );

  return { data, error, isLoading: isLoading && !data };
}
