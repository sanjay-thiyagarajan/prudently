"use client";

import useSWR from "swr";

import { useAuth } from "@/contexts/AuthContext";
import type { AgentLogsData, TraceData } from "@/lib/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Auth-gated as of docs/threat-model.md finding 2 — a raw trace's span attributes carry the
// real manager_email and unredacted subjects, and raw log payloads are unfiltered text; neither
// went through services/redaction.py, so this bypassed every redaction path built for the
// public overview. This is the agent detail page's own drill-down, always reached signed in.
function authedFetcher<T>(idToken: string) {
  return async (url: string): Promise<T> => {
    const response = await fetch(url, { headers: { Authorization: `Bearer ${idToken}` } });
    if (!response.ok) {
      throw new Error(`Fetch failed: ${response.status} ${response.statusText}`);
    }
    return response.json();
  };
}

// Not polled — a trace is fetched on demand only when the manager clicks a specific
// activity_log entry that carries a trace_id, matching routes/traces.py's own "on-demand, not
// a polled feed" design.
export function useTrace(traceId: string | null) {
  const { idToken } = useAuth();
  const { data, error, isLoading } = useSWR<TraceData>(
    traceId && idToken ? [`${API_BASE_URL}/traces/${encodeURIComponent(traceId)}`, idToken] : null,
    ([url, token]: [string, string]) => authedFetcher<TraceData>(token)(url),
  );
  return { data, error, isLoading };
}

export function useAgentLogs(agentName: string | null) {
  const { idToken } = useAuth();
  const { data, error, isLoading } = useSWR<AgentLogsData>(
    agentName && idToken
      ? [`${API_BASE_URL}/agents/${encodeURIComponent(agentName)}/logs`, idToken]
      : null,
    ([url, token]: [string, string]) => authedFetcher<AgentLogsData>(token)(url),
  );
  return { data, error, isLoading };
}
