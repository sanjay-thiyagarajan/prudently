"use client";

import { Hourglass } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Panel, PanelEmpty } from "@/components/ui/Panel";
import type { ParLevelRecord } from "@/lib/types/dashboard";

const STATUS_COLOR: Record<string, string> = {
  critical: "var(--color-critical)",
  low: "var(--color-elevated)",
};

/** Ranked shortest-runway-first — the SKU that runs out soonest belongs at the top of a
 * shortage list, not buried in alphabetical order with everything else. */
export function SupplyRunwayChart({ records }: { records: ParLevelRecord[] }) {
  const rows = records
    .filter((r) => r.stock_status !== "ok" && r.days_of_supply !== null)
    .sort((a, b) => (a.days_of_supply ?? 0) - (b.days_of_supply ?? 0))
    .slice(0, 8)
    .map((r) => ({ name: r.name, days: r.days_of_supply ?? 0, status: r.stock_status }))
    .reverse();

  return (
    <Panel title="Runway" icon={Hourglass} subtitle="Days of supply left, shortest first">
      {rows.length === 0 ? (
        <PanelEmpty>Nothing below its reorder point with a known runway right now.</PanelEmpty>
      ) : (
        <div style={{ height: Math.max(rows.length * 34, 100) }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-soft)" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fontSize: 10, fill: "var(--color-ink-muted)" }}
                tickFormatter={(v) => `${v}d`}
                axisLine={{ stroke: "var(--color-border)" }}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={110}
                tick={{ fontSize: 10, fill: "var(--color-ink-secondary)" }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                formatter={(value) => [`${value} days of supply left`, ""]}
                contentStyle={{
                  backgroundColor: "var(--color-bg-raised)",
                  border: "1px solid var(--color-border)",
                  borderRadius: 8,
                  fontSize: 11,
                }}
                labelStyle={{ color: "var(--color-ink-primary)" }}
              />
              <Bar dataKey="days" radius={[0, 4, 4, 0]} barSize={14}>
                {rows.map((row, i) => (
                  <Cell key={i} fill={STATUS_COLOR[row.status] ?? "var(--color-ink-muted)"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Panel>
  );
}
