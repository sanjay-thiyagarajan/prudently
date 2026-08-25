"use client";

import { ShieldCheck } from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { Panel } from "@/components/ui/Panel";
import { statusLabel } from "@/lib/labels";
import type { CredentialStatus } from "@/lib/types/dashboard";

const STATUS_COLOR: Record<CredentialStatus, string> = {
  valid: "var(--color-safe)",
  expiring_soon: "var(--color-elevated)",
  expired: "var(--color-critical)",
};
const ORDER: CredentialStatus[] = ["valid", "expiring_soon", "expired"];

/** Fleet-wide totals, collapsed across every unit's own DistributionBar above it on this same
 * page — the same aggregates (survive redaction, per HRPanel's own comment), just answering
 * "how compliant is the whole roster" instead of "which unit". */
export function CredentialComplianceDonut({
  unitSummary,
}: {
  unitSummary: Record<string, Record<CredentialStatus, number>>;
}) {
  const totals = ORDER.map((status) => ({
    status,
    label: statusLabel(status),
    value: Object.values(unitSummary ?? {}).reduce((sum, c) => sum + (c[status] ?? 0), 0),
  })).filter((r) => r.value > 0);

  const total = totals.reduce((sum, r) => sum + r.value, 0);

  return (
    <Panel title="Fleet-wide compliance" icon={ShieldCheck} subtitle="Every unit's credential status, combined">
      {total === 0 ? (
        <p className="text-sm text-[var(--color-ink-muted)]">No credential data yet.</p>
      ) : (
        <div className="flex items-center gap-5">
          <div className="relative size-[120px] shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={totals}
                  dataKey="value"
                  nameKey="label"
                  innerRadius={38}
                  outerRadius={58}
                  paddingAngle={totals.length > 1 ? 3 : 0}
                  strokeWidth={0}
                >
                  {totals.map((r) => (
                    <Cell key={r.status} fill={STATUS_COLOR[r.status]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value, name) => [`${value} staff`, name]}
                  contentStyle={{
                    backgroundColor: "var(--color-bg-raised)",
                    border: "1px solid var(--color-border)",
                    borderRadius: 8,
                    fontSize: 11,
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <span className="tnum font-[family-name:var(--font-display)] text-lg font-semibold text-[var(--color-ink-primary)]">
                {total}
              </span>
              <span className="text-[9px] tracking-wide text-[var(--color-ink-muted)] uppercase">staff</span>
            </div>
          </div>
          <ul className="space-y-1.5">
            {totals.map((r) => (
              <li key={r.status} className="flex items-center gap-2 text-xs">
                <span
                  className="size-2 shrink-0 rounded-full"
                  style={{ backgroundColor: STATUS_COLOR[r.status] }}
                />
                <span className="text-[var(--color-ink-secondary)]">{r.label}</span>
                <span className="tnum font-medium text-[var(--color-ink-primary)]">{r.value}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  );
}
