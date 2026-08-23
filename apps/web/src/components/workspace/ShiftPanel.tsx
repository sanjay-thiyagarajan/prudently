"use client";

import { CalendarClock } from "lucide-react";

import { DistributionBar } from "@/components/ui/DistributionBar";
import { Panel } from "@/components/ui/Panel";
import { RedactedNote } from "@/components/ui/RedactedNote";
import { StatusPill } from "@/components/ui/StatusPill";
import type { BurndownRecord, RiskLevel } from "@/lib/types/dashboard";

const RISK_ORDER: RiskLevel[] = ["critical", "elevated", "safe"];

export function ShiftPanel({
  records,
  unitSummary,
}: {
  records: BurndownRecord[];
  unitSummary: Record<string, Record<RiskLevel, number>>;
}) {
  const flagged = records.filter((r) => r.risk_level !== "safe").slice(0, 6);
  // The aggregates survive redaction, so they are the honest source for "is anything wrong".
  // Never infer "all clear" from an empty `records` — signed out it always is.
  const atRisk = Object.values(unitSummary ?? {}).reduce(
    (sum, c) => sum + (c.critical ?? 0) + (c.elevated ?? 0),
    0,
  );
  const withheld = records.length === 0 && atRisk > 0;

  return (
    <Panel title="Shift Allocation" icon={CalendarClock} live>
      <div className="space-y-3">
        {Object.entries(unitSummary).map(([unit, counts]) => (
          <DistributionBar key={unit} label={unit} counts={counts} order={RISK_ORDER} />
        ))}
      </div>

      <div className="mt-5 border-t border-[var(--color-border-soft)] pt-4">
        {withheld ? (
          <RedactedNote count={atRisk} noun="at-risk staff record" />
        ) : flagged.length === 0 ? (
          <p className="text-[12px] text-[var(--color-ink-muted)]">
            All staff within safe working-hour thresholds.
          </p>
        ) : (
          <ul className="space-y-2.5">
            {flagged.map((record) => (
              <li
                key={record.staff_id}
                className="flex items-center justify-between gap-3 text-sm"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium text-[var(--color-ink-primary)]">
                    {record.name}{" "}
                    <span className="text-[var(--color-ink-muted)]">· {record.unit}</span>
                  </p>
                  <p className="truncate text-xs text-[var(--color-ink-secondary)]">
                    {record.trailing_hours}h trailing / {record.safe_weekly_hours}h safe
                  </p>
                </div>
                <StatusPill status={record.risk_level} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </Panel>
  );
}
