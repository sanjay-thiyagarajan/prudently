"use client";

import useSWR from "swr";

import { useAuth } from "@/contexts/AuthContext";
import type { Vendor } from "@/lib/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Auth-gated as of docs/threat-model.md finding 2 — was public with no reason beyond precedent
// drift; every page reaching this module already sits behind RequireAuth.
function authedFetcher<T>(idToken: string) {
  return async (url: string): Promise<T> => {
    const response = await fetch(url, { headers: { Authorization: `Bearer ${idToken}` } });
    if (!response.ok) {
      throw new Error(`Vendor fetch failed: ${response.status} ${response.statusText}`);
    }
    return response.json();
  };
}

export function useVendors() {
  const { idToken } = useAuth();
  const { data, error, isLoading } = useSWR<Vendor[]>(
    idToken ? [`${API_BASE_URL}/vendors/`, idToken] : null,
    ([url, token]: [string, string]) => authedFetcher<Vendor[]>(token)(url),
  );
  return { vendors: data ?? [], error, isLoading };
}
