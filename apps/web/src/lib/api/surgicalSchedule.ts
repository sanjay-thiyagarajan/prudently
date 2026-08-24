"use client";

import useSWR from "swr";

import { useAuth } from "@/contexts/AuthContext";
import type { PatientDetail, SurgicalCase, SurgicalCaseConflict } from "@/lib/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Same split as lib/api/staff.ts: /surgical-schedule/cases carries no patient identity (any
// signed-in role may read it — see routes/surgical_scheduling.py's docstring), but the
// case-detail endpoint below is require_role("admin", "clinician")-gated and 403s for anyone
// else, same shape as staff.ts's per-employee routes.
function authedFetcher<T>(idToken: string) {
  return async (url: string): Promise<T> => {
    const response = await fetch(url, { headers: { Authorization: `Bearer ${idToken}` } });
    if (!response.ok) {
      throw new Error(`Surgical schedule fetch failed: ${response.status} ${response.statusText}`);
    }
    return response.json();
  };
}

export function useSurgicalCases() {
  const { idToken } = useAuth();
  const { data, error, isLoading, mutate } = useSWR<{
    cases: SurgicalCase[];
    conflicts: SurgicalCaseConflict[];
  }>(
    idToken ? [`${API_BASE_URL}/surgical-schedule/cases`, idToken] : null,
    ([url, token]: [string, string]) =>
      authedFetcher<{ cases: SurgicalCase[]; conflicts: SurgicalCaseConflict[] }>(token)(url),
  );
  return {
    cases: data?.cases ?? [],
    conflicts: data?.conflicts ?? [],
    error,
    isLoading,
    refresh: mutate,
  };
}

export function useCaseDetail(caseId: string | null) {
  const { idToken } = useAuth();
  const { data, error, isLoading, mutate } = useSWR<PatientDetail>(
    idToken && caseId
      ? [`${API_BASE_URL}/surgical-schedule/cases/${encodeURIComponent(caseId)}`, idToken]
      : null,
    ([url, token]: [string, string]) => authedFetcher<PatientDetail>(token)(url),
  );
  return { detail: data, error, isLoading, refresh: mutate };
}

export async function updateCaseStatus(
  idToken: string,
  caseId: string,
  newStatus: string,
): Promise<SurgicalCase> {
  const response = await fetch(
    `${API_BASE_URL}/surgical-schedule/cases/${encodeURIComponent(caseId)}/status`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${idToken}` },
      body: JSON.stringify({ new_status: newStatus }),
    },
  );
  if (!response.ok) {
    throw new Error(`Status update failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export async function notifyPatient(
  idToken: string,
  caseId: string,
  message: string,
): Promise<{ status: string; message?: string }> {
  const response = await fetch(
    `${API_BASE_URL}/surgical-schedule/cases/${encodeURIComponent(caseId)}/notify`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${idToken}` },
      body: JSON.stringify({ message }),
    },
  );
  if (!response.ok) {
    throw new Error(`Notify failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}
