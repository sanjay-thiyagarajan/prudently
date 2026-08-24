"use client";

import useSWR from "swr";

import type { WatchStatus } from "@/lib/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Faster than the dashboard's 4s: the watch strip is the one thing on screen a viewer expects
// to respond immediately to "Run fleet check now", and a stale reading after pressing it reads
// as a broken control rather than a slow poll.
const POLL_INTERVAL_MS = 2000;

async function getStatus(url: string): Promise<WatchStatus> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Watch status failed: ${response.status}`);
  return response.json();
}

// GET /watch/status stayed public (an inert read, no reason to gate it) — only the two mutating
// routes below moved behind auth, so this hook is deliberately unauthenticated.
export function useWatchStatus() {
  const { data, error, isLoading, mutate } = useSWR<WatchStatus>(
    `${API_BASE_URL}/watch/status`,
    getStatus,
    { refreshInterval: POLL_INTERVAL_MS, revalidateOnFocus: false, keepPreviousData: true },
  );
  return { status: data, error, isLoading: isLoading && !data, refresh: mutate };
}

/** Fires one watch cycle immediately — fire-and-return, same shape as the old /sim/advance:
 * the backend starts the cycle as a background task and responds before it finishes, so the
 * caller should poll useWatchStatus()/the activity feed to see the result land rather than
 * await this for completion.
 *
 * Auth-gated as of docs/threat-model.md finding 1 (this can trigger real LLM/agent turns and
 * real approval emails) — `idToken` is required, not optional, so a caller can't accidentally
 * ship an unauthenticated request that just 401s. */
export async function triggerWatchCheck(idToken: string): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/watch/check-now`, {
    method: "POST",
    headers: { Authorization: `Bearer ${idToken}` },
  });
  if (!response.ok) {
    throw new Error(`Watch check-now failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}
