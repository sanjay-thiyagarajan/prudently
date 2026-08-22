"use client";

import { Truck } from "lucide-react";

import { Panel } from "@/components/ui/Panel";
import { StatusPill } from "@/components/ui/StatusPill";
import type { ReorderDecision } from "@/lib/types/dashboard";

export function SupplyPanel({ decisions }: { decisions: ReorderDecision[] }) {
  return (
    <Panel title="Supply Chain Resiliency" icon={Truck} accent="#f97316" live>
      {decisions.length === 0 ? (
        <div className="flex h-full min-h-[140px] flex-col items-center justify-center gap-2 text-center">
          <Truck size={24} className="text-[var(--color-ink-muted)]" />
          <p className="text-sm text-[var(--color-ink-muted)]">
            No reorders needed — every SKU is above its reorder point.
          </p>
        </div>
      ) : (
        <ul className="space-y-3">
          {decisions.map((decision) => (
            <li
              key={decision.sku}
              className="rounded-xl border border-[var(--color-border-soft)] p-3.5"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-[var(--color-ink-primary)]">
                    {decision.name}
                  </p>
                  <p className="mt-0.5 text-xs text-[var(--color-ink-secondary)]">
                    Order {decision.reorder_quantity} from {decision.vendor_name ?? "no vendor"}
                  </p>
                </div>
                <StatusPill
                  status={decision.urgency === "expedited" ? "critical" : "elevated"}
                  label={decision.urgency}
                />
              </div>
              {decision.will_stock_out_before_delivery && decision.alternate_vendor_name && (
                <p className="mt-2 text-xs" style={{ color: "var(--color-critical)" }}>
                  Won&apos;t beat the stockout via {decision.vendor_name} — contact{" "}
                  {decision.alternate_vendor_name} in parallel.
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
