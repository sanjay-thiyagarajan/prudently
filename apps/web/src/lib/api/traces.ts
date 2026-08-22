"use client";

import useSWR from "swr";

import type { AgentLogsData, TraceData } from "@/lib/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetcher<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Fetch failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

// Not polled — a trace is fetched on demand only when the manager clicks a specific
// activity_log entry that carries a trace_id, matching routes/traces.py's own "on-demand, not
// a polled feed" design.
export function useTrace(traceId: string | null) {
  const { data, error, isLoading } = useSWR<TraceData>(
    traceId ? `${API_BASE_URL}/traces/${encodeURIComponent(traceId)}` : null,
    fetcher<TraceData>,
  );
  return { data, error, isLoading };
}

export function useAgentLogs(agentName: string | null) {
  const { data, error, isLoading } = useSWR<AgentLogsData>(
    agentName ? `${API_BASE_URL}/agents/${encodeURIComponent(agentName)}/logs` : null,
    fetcher<AgentLogsData>,
  );
  return { data, error, isLoading };
}
