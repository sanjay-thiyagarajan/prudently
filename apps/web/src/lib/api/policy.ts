"use client";

import useSWR from "swr";

import { useAuth } from "@/contexts/AuthContext";
import type { ApprovalPolicy } from "@/lib/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Separate from lib/api/dashboard.ts's fetcher on purpose: this one attaches the manager's
// Firebase ID token, since /policy/* is real auth-gated manager config (see routes/policy.py),
// unlike /dashboard/overview which stays anonymous.
function authedFetcher(idToken: string) {
  return async (url: string): Promise<ApprovalPolicy[]> => {
    const response = await fetch(url, { headers: { Authorization: `Bearer ${idToken}` } });
    if (!response.ok) {
      throw new Error(`Policy fetch failed: ${response.status} ${response.statusText}`);
    }
    return response.json();
  };
}

export function useApprovalPolicies() {
  const { idToken } = useAuth();
  const { data, error, isLoading, mutate } = useSWR<ApprovalPolicy[]>(
    idToken ? [`${API_BASE_URL}/policy/tasks`, idToken] : null,
    ([url, token]: [string, string]) => authedFetcher(token)(url),
  );

  return { policies: data ?? [], error, isLoading, refresh: mutate };
}

export async function saveApprovalPolicy(
  idToken: string,
  taskType: string,
  policy: Omit<ApprovalPolicy, "task_type">,
): Promise<ApprovalPolicy> {
  const response = await fetch(`${API_BASE_URL}/policy/tasks/${encodeURIComponent(taskType)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${idToken}` },
    body: JSON.stringify(policy),
  });
  if (!response.ok) {
    throw new Error(`Policy save failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}
