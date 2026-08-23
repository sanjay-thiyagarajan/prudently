"use client";

import useSWR from "swr";

import type { InventoryTransaction, PurchaseOrder } from "@/lib/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Reads are public, same as the rest of the Inventory/Supply data (see routes/inventory.py's
// docstring) — every page reaching this module already sits behind RequireAuth, so an idToken
// is always available by the time the mutating actions below are used.
async function fetcher<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Inventory fetch failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export function useInventoryTransactions(sku?: string) {
  const url = sku
    ? `${API_BASE_URL}/inventory/transactions?sku=${encodeURIComponent(sku)}`
    : `${API_BASE_URL}/inventory/transactions`;
  const { data, error, isLoading } = useSWR<InventoryTransaction[]>(url, fetcher);
  return { transactions: data ?? [], error, isLoading };
}

export function usePurchaseOrders() {
  const { data, error, isLoading, mutate } = useSWR<PurchaseOrder[]>(
    `${API_BASE_URL}/inventory/purchase-orders`,
    fetcher,
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
