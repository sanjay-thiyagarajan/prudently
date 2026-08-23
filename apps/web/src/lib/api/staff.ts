"use client";

import useSWR from "swr";

import { useAuth } from "@/contexts/AuthContext";
import type { StaffDirectoryEntry, StaffProfile } from "@/lib/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Same split as lib/api/payroll.ts — /staff/* carries pay history, so the whole router is
// auth-gated (see routes/staff.py's docstring).
function authedFetcher<T>(idToken: string) {
  return async (url: string): Promise<T> => {
    const response = await fetch(url, { headers: { Authorization: `Bearer ${idToken}` } });
    if (!response.ok) {
      throw new Error(`Staff fetch failed: ${response.status} ${response.statusText}`);
    }
    return response.json();
  };
}

export function useStaffDirectory() {
  const { idToken } = useAuth();
  const { data, error, isLoading } = useSWR<StaffDirectoryEntry[]>(
    idToken ? [`${API_BASE_URL}/staff/`, idToken] : null,
    ([url, token]: [string, string]) => authedFetcher<StaffDirectoryEntry[]>(token)(url),
  );
  return { staff: data ?? [], error, isLoading };
}

export function useStaffProfile(staffId: string | null) {
  const { idToken } = useAuth();
  const { data, error, isLoading } = useSWR<StaffProfile>(
    idToken && staffId ? [`${API_BASE_URL}/staff/${encodeURIComponent(staffId)}`, idToken] : null,
    ([url, token]: [string, string]) => authedFetcher<StaffProfile>(token)(url),
  );
  return { profile: data, error, isLoading };
}
