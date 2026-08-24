"use client";

import useSWR from "swr";

import { useAuth } from "@/contexts/AuthContext";
import type { InventoryTransaction, PurchaseOrder } from "@/lib/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Auth-gated as of docs/threat-model.md finding 2 — PO records carry unit_cost/total_cost, the
// same class of financial data routes/payroll.py already hard-gates; this was inconsistently
// left public. Every page reaching this module already sits behind RequireAuth.
function authedFetcher<T>(idToken: string) {
  return async (url: string): Promise<T> => {
    const response = await fetch(url, { headers: { Authorization: `Bearer ${idToken}` } });
    if (!response.ok) {
      throw new Error(`Inventory fetch failed: ${response.status} ${response.statusText}`);
    }
    return response.json();
  };
}

export function useInventoryTransactions(sku?: string) {
  const { idToken } = useAuth();
  const url = sku
    ? `${API_BASE_URL}/inventory/transactions?sku=${encodeURIComponent(sku)}`
    : `${API_BASE_URL}/inventory/transactions`;
  const { data, error, isLoading } = useSWR<InventoryTransaction[]>(
    idToken ? [url, idToken] : null,
    ([u, token]: [string, string]) => authedFetcher<InventoryTransaction[]>(token)(u),
  );
  return { transactions: data ?? [], error, isLoading };
}

export function usePurchaseOrders() {
  const { idToken } = useAuth();
  const { data, error, isLoading, mutate } = useSWR<PurchaseOrder[]>(
    idToken ? [`${API_BASE_URL}/inventory/purchase-orders`, idToken] : null,
    ([url, token]: [string, string]) => authedFetcher<PurchaseOrder[]>(token)(url),
    { refreshInterval: 5000 },
  );
  return { purchaseOrders: data ?? [], error, isLoading, refresh: mutate };
}

export async function receivePurchaseOrder(idToken: string, poId: string): Promise<PurchaseOrder> {
  const response = await fetch(
    `${API_BASE_URL}/inventory/purchase-orders/${encodeURIComponent(poId)}/receive`,
    { method: "POST", headers: { Authorization: `Bearer ${idToken}` } },
  );
  if (!response.ok) {
    throw new Error(`Receive purchase order failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export async function invoicePurchaseOrder(idToken: string, poId: string): Promise<PurchaseOrder> {
  const response = await fetch(
    `${API_BASE_URL}/inventory/purchase-orders/${encodeURIComponent(poId)}/invoice`,
    { method: "POST", headers: { Authorization: `Bearer ${idToken}` } },
  );
  if (!response.ok) {
    throw new Error(`Invoice purchase order failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}
