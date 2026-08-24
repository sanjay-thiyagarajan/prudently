"use client";

import useSWR from "swr";

import { useAuth } from "@/contexts/AuthContext";
import type { DutyJobSheet, FacilityJobSheet } from "@/lib/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Same split as lib/api/staff.ts — the whole /job-sheets router is auth-gated (see
// routes/job_sheets.py's docstring).
function authedFetcher<T>(idToken: string) {
  return async (url: string): Promise<T> => {
    const response = await fetch(url, { headers: { Authorization: `Bearer ${idToken}` } });
    if (!response.ok) {
      throw new Error(`Job sheet fetch failed: ${response.status} ${response.statusText}`);
    }
    return response.json();
  };
}

export function useDutyJobSheet(unit: string | null) {
  const { idToken } = useAuth();
  const { data, error, isLoading } = useSWR<DutyJobSheet>(
    idToken && unit ? [`${API_BASE_URL}/job-sheets/duty/${encodeURIComponent(unit)}`, idToken] : null,
    ([url, token]: [string, string]) => authedFetcher<DutyJobSheet>(token)(url),
  );
  return { sheet: data, error, isLoading };
}

export function useFacilityJobSheets() {
  const { idToken } = useAuth();
  const { data, error, isLoading, mutate } = useSWR<FacilityJobSheet[]>(
    idToken ? [`${API_BASE_URL}/job-sheets/facilities`, idToken] : null,
    ([url, token]: [string, string]) => authedFetcher<FacilityJobSheet[]>(token)(url),
  );
  return { sheets: data ?? [], error, isLoading, refresh: mutate };
}

export async function createFacilityJobSheet(
  idToken: string,
  payload: { title: string; description: string; location: string; assigned_to: string; priority: string },
): Promise<FacilityJobSheet> {
  const response = await fetch(`${API_BASE_URL}/job-sheets/facilities`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${idToken}` },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Work order creation failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export async function startFacilityJobSheet(idToken: string, sheetId: string): Promise<FacilityJobSheet> {
  const response = await fetch(
    `${API_BASE_URL}/job-sheets/facilities/${encodeURIComponent(sheetId)}/start`,
    { method: "POST", headers: { Authorization: `Bearer ${idToken}` } },
  );
  if (!response.ok) {
    throw new Error(`Start failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export async function completeFacilityJobSheet(
  idToken: string,
  sheetId: string,
): Promise<FacilityJobSheet> {
  const response = await fetch(
    `${API_BASE_URL}/job-sheets/facilities/${encodeURIComponent(sheetId)}/complete`,
    { method: "POST", headers: { Authorization: `Bearer ${idToken}` } },
  );
  if (!response.ok) {
    throw new Error(`Complete failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}
