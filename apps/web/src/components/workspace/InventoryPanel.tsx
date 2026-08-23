"use client";

import { Package } from "lucide-react";

import { DistributionBar } from "@/components/ui/DistributionBar";
import { Panel } from "@/components/ui/Panel";
import { StatusPill } from "@/components/ui/StatusPill";
import type { ParLevelRecord, StockStatus } from "@/lib/types/dashboard";

const STOCK_ORDER: StockStatus[] = ["critical", "low", "ok"];

export function InventoryPanel({
  records,
  categorySummary,
}: {
  records: ParLevelRecord[];
  categorySummary: Record<string, Record<StockStatus, number>>;
}) {
  const flagged = records.filter((r) => r.stock_status !== "ok");

  return (
    <Panel title="Inventory Management" icon={Package} live>
      <div className="space-y-3">
        {Object.entries(categorySummary).map(([category, counts]) => (
          <DistributionBar key={category} label={category} counts={counts} order={STOCK_ORDER} />
        ))}
      </div>

      <div className="mt-5 border-t border-[var(--color-border-soft)] pt-4">
        {flagged.length === 0 ? (
          <p className="text-sm text-[var(--color-ink-muted)]">
            All SKUs above their reorder point.
          </p>
        ) : (
          <ul className="space-y-2.5">
            {flagged.map((record) => (
              <li key={record.sku} className="flex items-center justify-between gap-3 text-sm">
                <div className="min-w-0">
                  <p className="truncate font-medium text-[var(--color-ink-primary)]">
                    {record.name}
                  </p>
                  <p className="truncate text-xs text-[var(--color-ink-secondary)]">
                    {record.current_stock} {record.unit} on hand
                    {record.days_of_supply !== null &&
                      ` · ~${record.days_of_supply}d supply left`}
                  </p>
                </div>
                <StatusPill status={record.stock_status} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </Panel>
  );
}
