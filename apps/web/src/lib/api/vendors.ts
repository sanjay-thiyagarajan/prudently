"use client";

import useSWR from "swr";

import type { Vendor } from "@/lib/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetcher<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Vendor fetch failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export function useVendors() {
  const { data, error, isLoading } = useSWR<Vendor[]>(`${API_BASE_URL}/vendors/`, fetcher);
  return { vendors: data ?? [], error, isLoading };
}
