"use client";

import useSWR from "swr";

import { useAuth } from "@/contexts/AuthContext";
import type { PayrollRecord, PayrollStaffOption } from "@/lib/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Same split as lib/api/policy.ts: /payroll/* is real auth-gated compensation data, never
// mixed into /dashboard/overview's anonymous feed (see routes/payroll.py's docstring).
function authedFetcher<T>(idToken: string) {
  return async (url: string): Promise<T> => {
    const response = await fetch(url, { headers: { Authorization: `Bearer ${idToken}` } });
    if (!response.ok) {
      throw new Error(`Payroll fetch failed: ${response.status} ${response.statusText}`);
    }
    return response.json();
  };
}

export function usePayrollStaff() {
  const { idToken } = useAuth();
  const { data, error, isLoading } = useSWR<PayrollStaffOption[]>(
    idToken ? [`${API_BASE_URL}/payroll/staff`, idToken] : null,
    ([url, token]: [string, string]) => authedFetcher<PayrollStaffOption[]>(token)(url),
  );
  return { staff: data ?? [], error, isLoading };
}

export function usePayrollRecords() {
  const { idToken } = useAuth();
  const { data, error, isLoading, mutate } = useSWR<PayrollRecord[]>(
    idToken ? [`${API_BASE_URL}/payroll/records`, idToken] : null,
    ([url, token]: [string, string]) => authedFetcher<PayrollRecord[]>(token)(url),
  );
  return { records: data ?? [], error, isLoading, refresh: mutate };
}

export async function createPayrollRecord(
  idToken: string,
  payload: { staff_id: string; pay_period_start: string; pay_period_end: string },
): Promise<PayrollRecord> {
  const response = await fetch(`${API_BASE_URL}/payroll/records`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${idToken}` },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Payroll record creation failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export async function markPayrollPaid(idToken: string, recordId: string): Promise<PayrollRecord> {
  const response = await fetch(
    `${API_BASE_URL}/payroll/records/${encodeURIComponent(recordId)}/mark-paid`,
    { method: "POST", headers: { Authorization: `Bearer ${idToken}` } },
  );
  if (!response.ok) {
    throw new Error(`Mark-paid failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}
