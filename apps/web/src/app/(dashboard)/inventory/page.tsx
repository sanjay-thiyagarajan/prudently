"use client";

import { CheckCircle2, Loader2, Package, Receipt, Search, TriangleAlert } from "lucide-react";
import { useMemo, useState } from "react";

import { StatusPill } from "@/components/ui/StatusPill";
import { useAuth } from "@/contexts/AuthContext";
import { useDashboardOverview } from "@/lib/api/dashboard";
import {
  invoicePurchaseOrder,
  receivePurchaseOrder,
  useInventoryTransactions,
  usePurchaseOrders,
} from "@/lib/api/inventory";
import type { ParLevelRecord } from "@/lib/types/dashboard";

const CATEGORY_ALL = "all";
const STATUS_ALL = "all";

function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const minutes = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function ItemDrilldown({ sku, onClose }: { sku: string; onClose: () => void }) {
  const { transactions, isLoading } = useInventoryTransactions(sku);
  const { purchaseOrders } = usePurchaseOrders();
  const relatedOrders = purchaseOrders.filter((po) => po.sku === sku);

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--shadow-panel)] p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-[family-name:var(--font-display)] text-sm font-semibold uppercase tracking-wide text-[var(--color-ink-primary)]">
          Movement history — {sku}
        </h3>
        <button
          type="button"
          onClick={onClose}
          className="text-xs font-medium text-[var(--color-ink-muted)] hover:text-[var(--color-ink-primary)]"
        >
          Close
        </button>
      </div>

      {relatedOrders.length > 0 && (
        <div className="mb-4">
          <p className="mb-2 text-xs font-medium text-[var(--color-ink-secondary)]">
            Purchase orders for this item
          </p>
          <ul className="space-y-1.5">
            {relatedOrders.map((po) => (
              <li key={po.id} className="flex items-center justify-between text-xs">
                <span className="text-[var(--color-ink-secondary)]">
                  {po.quantity} units from {po.vendor_name}
                </span>
                <StatusPill status={po.status} />
              </li>
            ))}
          </ul>
        </div>
      )}

      {isLoading ? (
        <Loader2 className="animate-spin text-[var(--color-hero)]" size={18} />
      ) : transactions.length === 0 ? (
        <p className="text-sm text-[var(--color-ink-muted)]">
          No stock movement recorded yet — this item hasn&apos;t moved since seeding, or the
          fleet watch hasn&apos;t run a check yet.
        </p>
      ) : (
        <ul className="max-h-72 space-y-1.5 overflow-y-auto text-xs">
          {transactions.map((tx) => (
            <li
              key={tx.id}
              className="flex items-center justify-between rounded-lg border border-[var(--color-border-soft)] px-3 py-2"
            >
              <span className="text-[var(--color-ink-secondary)]">
                {tx.type === "consumption" ? "Used" : "Received"} {Math.abs(tx.quantity_delta)}{" "}
                units <span className="text-[var(--color-ink-muted)]">· {timeAgo(tx.timestamp)}</span>
              </span>
              <span className="text-[var(--color-ink-muted)]">
                {tx.stock_before} → {tx.stock_after}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function PurchaseOrdersSection() {
  const { idToken } = useAuth();
  const { purchaseOrders, isLoading, refresh } = usePurchaseOrders();
  const [busyId, setBusyId] = useState<string | null>(null);

  async function handleReceive(poId: string) {
    if (!idToken) return;
    setBusyId(poId);
    try {
      await receivePurchaseOrder(idToken, poId);
      await refresh();
    } finally {
      setBusyId(null);
    }
  }

  async function handleInvoice(poId: string) {
    if (!idToken) return;
    setBusyId(poId);
    try {
      await invoicePurchaseOrder(idToken, poId);
      await refresh();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--shadow-panel)] p-5">
      <div className="mb-4 flex items-center gap-2.5">
        <Receipt size={16} className="text-[var(--color-hero)]" />
        <h2 className="font-[family-name:var(--font-display)] text-sm font-semibold uppercase tracking-wide text-[var(--color-ink-primary)]">
          Purchase orders
        </h2>
      </div>
      {isLoading ? (
        <Loader2 className="animate-spin text-[var(--color-hero)]" size={18} />
      ) : purchaseOrders.length === 0 ? (
        <p className="text-sm text-[var(--color-ink-muted)]">
          No purchase orders yet — one is created automatically whenever the Supply Chain
          Assistant contacts a vendor for a reorder and it goes through.
        </p>
      ) : (
        <ul className="space-y-2">
          {purchaseOrders.map((po) => (
            <li
              key={po.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[var(--color-border-soft)] p-3 text-sm"
            >
              <div className="min-w-0">
                <p className="truncate font-medium text-[var(--color-ink-primary)]">
                  {po.quantity} × {po.item_name}
                </p>
                <p className="text-xs text-[var(--color-ink-secondary)]">
                  From {po.vendor_name} · ${po.total_cost.toFixed(2)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <StatusPill status={po.status} />
                {po.status === "ordered" && (
                  <button
                    type="button"
                    onClick={() => handleReceive(po.id)}
                    disabled={busyId === po.id}
                    className="flex items-center gap-1 rounded-lg bg-[var(--color-safe-soft)] px-2.5 py-1 text-xs font-semibold text-[var(--color-safe)] disabled:opacity-50"
                  >
                    {busyId === po.id ? <Loader2 size={11} className="animate-spin" /> : <CheckCircle2 size={11} />}
                    Mark received
                  </button>
                )}
                {po.status === "received" && (
                  <button
                    type="button"
                    onClick={() => handleInvoice(po.id)}
                    disabled={busyId === po.id}
                    className="flex items-center gap-1 rounded-lg bg-[var(--color-hero-soft)] px-2.5 py-1 text-xs font-semibold text-[var(--color-hero)] disabled:opacity-50"
                  >
                    {busyId === po.id ? <Loader2 size={11} className="animate-spin" /> : <Receipt size={11} />}
                    Mark invoiced
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function InventoryPage() {
  const { data, error, isLoading } = useDashboardOverview();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState(CATEGORY_ALL);
  const [status, setStatus] = useState(STATUS_ALL);
  const [selectedSku, setSelectedSku] = useState<string | null>(null);

  const records = useMemo(() => data?.inventory.records ?? [], [data]);
  const categories = useMemo(
    () => Array.from(new Set(records.map((r) => r.category))).sort(),
    [records],
  );

  const filtered = useMemo(() => {
    return records.filter((record: ParLevelRecord) => {
      if (category !== CATEGORY_ALL && record.category !== category) return false;
      if (status !== STATUS_ALL && record.stock_status !== status) return false;
      if (search && !record.name.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [records, category, status, search]);

  return (
    <main className="min-h-screen px-8 py-10">
      <div className="mb-8">
        <p className="text-[11px] font-medium tracking-[0.25em] text-[var(--color-hero)] uppercase">
          Inventory Management Agent
        </p>
        <h1 className="mt-1 font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-ink-primary)]">
          Inventory
        </h1>
        <p className="mt-2 max-w-lg text-sm text-[var(--color-ink-secondary)]">
          Search the full supply catalog, see how each item&apos;s stock has moved, and track
          purchase orders from request through receiving.
        </p>
      </div>

      {isLoading ? (
        <Loader2 className="animate-spin text-[var(--color-hero)]" size={24} />
      ) : error || !data ? (
        <div className="flex items-center gap-2 text-sm text-[var(--color-ink-secondary)]">
          <TriangleAlert className="text-[var(--color-critical)]" size={18} />
          Couldn&apos;t reach the Prudently API.
        </div>
      ) : (
        <div className="max-w-5xl space-y-6">
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-raised)] px-3 py-1.5">
              <Search size={14} className="text-[var(--color-ink-muted)]" />
              <input
                type="text"
                placeholder="Search items…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="bg-transparent text-xs text-[var(--color-ink-primary)] outline-none placeholder:text-[var(--color-ink-muted)]"
              />
            </div>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-raised)] px-3 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none"
            >
              <option value={CATEGORY_ALL}>All categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-raised)] px-3 py-1.5 text-xs text-[var(--color-ink-primary)] outline-none"
            >
              <option value={STATUS_ALL}>All statuses</option>
              <option value="ok">OK</option>
              <option value="low">Low</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          <div className="overflow-x-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--shadow-panel)]">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border-soft)] text-[11px] uppercase tracking-wide text-[var(--color-ink-muted)]">
                  <th className="px-4 py-3 font-medium">Item</th>
                  <th className="px-4 py-3 font-medium">Category</th>
                  <th className="px-4 py-3 font-medium text-right">On hand</th>
                  <th className="px-4 py-3 font-medium text-right">Days of supply</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((record) => (
                  <tr
                    key={record.sku}
                    onClick={() => setSelectedSku(record.sku)}
                    className={`cursor-pointer border-t border-[var(--color-border-soft)] transition-colors hover:bg-[var(--color-border-soft)] ${
                      selectedSku === record.sku ? "bg-[var(--color-hero-soft)]" : ""
                    }`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2.5">
                        <Package size={14} className="shrink-0 text-[var(--color-ink-muted)]" />
                        <span className="font-medium text-[var(--color-ink-primary)]">
                          {record.name}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-[var(--color-ink-secondary)]">
                      {record.category}
                    </td>
                    <td className="px-4 py-3 text-right text-[var(--color-ink-secondary)]">
                      {record.current_stock} {record.unit}
                    </td>
                    <td className="px-4 py-3 text-right text-[var(--color-ink-secondary)]">
                      {record.days_of_supply ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      <StatusPill status={record.stock_status} />
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center text-sm text-[var(--color-ink-muted)]">
                      No items match this search.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {selectedSku && (
            <ItemDrilldown sku={selectedSku} onClose={() => setSelectedSku(null)} />
          )}

          <PurchaseOrdersSection />
        </div>
      )}
    </main>
  );
}
