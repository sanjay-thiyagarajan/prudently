"use client";

import { Gauge } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Panel, PanelEmpty } from "@/components/ui/Panel";
import type { BurndownRecord } from "@/lib/types/dashboard";

const RISK_COLOR: Record<string, string> = {
  critical: "var(--color-critical)",
  elevated: "var(--color-elevated)",
  safe: "var(--color-safe)",
};

/**
 * `burndown_ratio` is trailing_hours ÷ safe_weekly_hours, already computed in
 * agents/shift/burndown.py — this just puts the same number Shift itself reasons from on a
 * runway against 1.0 (the safe-hours line), rather than restating hours as text a second time.
 */
export function FatigueBurndownChart({ records }: { records: BurndownRecord[] }) {
  const rows = records
    .filter((r) => r.risk_level !== "safe")
    .sort((a, b) => b.burndown_ratio - a.burndown_ratio)
    .slice(0, 8)
    .map((r) => ({ name: r.name, ratio: Number(r.burndown_ratio.toFixed(2)), risk: r.risk_level }))
    .reverse();

  return (
    <Panel title="Fatigue burndown" icon={Gauge} subtitle="Trailing hours ÷ safe weekly hours, over the line">
      {rows.length === 0 ? (
        <PanelEmpty>Every flagged staff member is back under their safe-hours line.</PanelEmpty>
      ) : (
        <div style={{ height: Math.max(rows.length * 34, 100) }}>
          <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={rows}
            layout="vertical"
            margin={{ top: 4, right: 16, bottom: 0, left: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-soft)" horizontal={false} />
            <XAxis
              type="number"
              domain={[0, "dataMax + 0.1"]}
              tick={{ fontSize: 10, fill: "var(--color-ink-muted)" }}
              tickFormatter={(v) => `${Math.round(v * 100)}%`}
              axisLine={{ stroke: "var(--color-border)" }}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={96}
              tick={{ fontSize: 10, fill: "var(--color-ink-secondary)" }}
              tickLine={false}
              axisLine={false}
            />
            <ReferenceLine x={1} stroke="var(--color-ink-muted)" strokeDasharray="4 4" />
            <Tooltip
              formatter={(value) => [`${Math.round(Number(value) * 100)}% of safe hours`, ""]}
              contentStyle={{
                backgroundColor: "var(--color-bg-raised)",
                border: "1px solid var(--color-border)",
                borderRadius: 8,
                fontSize: 11,
              }}
              labelStyle={{ color: "var(--color-ink-primary)" }}
            />
            <Bar dataKey="ratio" radius={[0, 4, 4, 0]} barSize={14}>
              {rows.map((row, i) => (
                <Cell key={i} fill={RISK_COLOR[row.risk] ?? "var(--color-ink-muted)"} />
              ))}
            </Bar>
          </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Panel>
  );
}
