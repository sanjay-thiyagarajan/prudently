"use client";

import { Loader2, Truck, TriangleAlert } from "lucide-react";

import { StatusPill } from "@/components/ui/StatusPill";
import { usePurchaseOrders } from "@/lib/api/inventory";
import { useVendors } from "@/lib/api/vendors";
import type { PurchaseOrder } from "@/lib/types/dashboard";

function VendorCard({ vendorId, name, leadTimeDays, reliability, orders }: {
  vendorId: string;
  name: string;
  leadTimeDays: number;
  reliability: number;
  orders: PurchaseOrder[];
}) {
  const totalSpend = orders.reduce((sum, po) => sum + po.total_cost, 0);

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--shadow-panel)] p-5">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-[var(--color-hero-soft)] text-[var(--color-hero)]">
            <Truck size={18} />
          </span>
          <div>
            <p className="font-medium text-[var(--color-ink-primary)]">{name}</p>
            <p className="text-xs text-[var(--color-ink-muted)]">{vendorId}</p>
          </div>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 text-xs">
        <div className="rounded-lg bg-[var(--color-border-soft)] px-3 py-2">
          <p className="text-[var(--color-ink-muted)]">Lead time</p>
          <p className="mt-0.5 font-medium text-[var(--color-ink-primary)]">{leadTimeDays} days</p>
        </div>
        <div className="rounded-lg bg-[var(--color-border-soft)] px-3 py-2">
          <p className="text-[var(--color-ink-muted)]">Reliability</p>
          <p className="mt-0.5 font-medium text-[var(--color-ink-primary)]">
            {Math.round(reliability * 100)}%
          </p>
        </div>
      </div>

      <div className="border-t border-[var(--color-border-soft)] pt-3">
        <p className="mb-2 text-xs font-medium text-[var(--color-ink-secondary)]">
          Order history {orders.length > 0 && `· $${totalSpend.toFixed(2)} total`}
        </p>
        {orders.length === 0 ? (
          <p className="text-sm text-[var(--color-ink-muted)]">No orders placed yet.</p>
        ) : (
          <ul className="space-y-1.5">
            {orders.map((po) => (
              <li key={po.id} className="flex items-center justify-between text-xs">
                <span className="truncate text-[var(--color-ink-secondary)]">
                  {po.quantity} × {po.item_name}
                </span>
                <StatusPill status={po.status} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default function VendorsPage() {
  const { vendors, isLoading: vendorsLoading, error } = useVendors();
  const { purchaseOrders } = usePurchaseOrders();

  return (
    <main className="min-h-screen px-8 py-10">
      <div className="mb-8">
        <p className="text-[11px] font-medium tracking-[0.25em] text-[var(--color-hero)] uppercase">
          Supply Chain Resiliency Agent
        </p>
        <h1 className="mt-1 font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-ink-primary)]">
          Vendors
        </h1>
        <p className="mt-2 max-w-lg text-sm text-[var(--color-ink-secondary)]">
          Every supplier the Supply Chain Assistant can order from, and their order history.
        </p>
      </div>

      {vendorsLoading ? (
        <Loader2 className="animate-spin text-[var(--color-hero)]" size={24} />
      ) : error ? (
        <div className="flex items-center gap-2 text-sm text-[var(--color-ink-secondary)]">
          <TriangleAlert className="text-[var(--color-critical)]" size={18} />
          Couldn&apos;t reach the Prudently API.
        </div>
      ) : (
        <div className="grid max-w-4xl grid-cols-1 gap-5 sm:grid-cols-2">
          {vendors.map((vendor) => (
            <VendorCard
              key={vendor.vendor_id}
              vendorId={vendor.vendor_id}
              name={vendor.name}
              leadTimeDays={vendor.lead_time_days}
              reliability={vendor.reliability}
              orders={purchaseOrders.filter((po) => po.vendor_id === vendor.vendor_id)}
            />
          ))}
        </div>
      )}
    </main>
  );
}
