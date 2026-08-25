"use client";

import { Handshake } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Panel, PanelEmpty } from "@/components/ui/Panel";
import type { ReorderDecision } from "@/lib/types/dashboard";

/** One row per vendor actually in play across today's reorder decisions — the primary vendor
 * for at least one SKU, or the alternate a will-stock-out decision fell back to. Not the full
 * vendor directory; that's /vendors. This is "who Supply is relying on right now." */
export function VendorReliabilityChart({ decisions }: { decisions: ReorderDecision[] }) {
  const byVendor = new Map<string, { name: string; reliability: number; leadTime: number; primary: boolean }>();
  for (const d of decisions) {
    if (d.vendor_id && d.vendor_reliability !== null) {
      byVendor.set(d.vendor_id, {
        name: d.vendor_name ?? d.vendor_id,
        reliability: d.vendor_reliability,
        leadTime: d.vendor_lead_time_days ?? 0,
        primary: true,
      });
    }
  }

  const rows = Array.from(byVendor.values())
    .sort((a, b) => b.reliability - a.reliability)
    .map((v) => ({ ...v, pct: Math.round(v.reliability * 100) }));

  return (
    <Panel title="Vendors in play" icon={Handshake} subtitle="Reliability behind today's reorder decisions">
      {rows.length === 0 ? (
        <PanelEmpty>No reorder decisions to weigh a vendor against right now.</PanelEmpty>
      ) : (
        <div style={{ height: Math.max(rows.length * 32, 90) }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 24, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-soft)" horizontal={false} />
              <XAxis
                type="number"
                domain={[0, 100]}
                tick={{ fontSize: 10, fill: "var(--color-ink-muted)" }}
                tickFormatter={(v) => `${v}%`}
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
                formatter={(_value, _name, entry) => {
                  const payload = entry.payload as { pct: number; leadTime: number };
                  return [`${payload.pct}% reliable · ${payload.leadTime}d lead time`, ""];
                }}
                contentStyle={{
                  backgroundColor: "var(--color-bg-raised)",
                  border: "1px solid var(--color-border)",
                  borderRadius: 8,
                  fontSize: 11,
                }}
                labelStyle={{ color: "var(--color-ink-primary)" }}
              />
              <Bar dataKey="pct" radius={[0, 4, 4, 0]} barSize={12} fill="var(--color-hero)">
                {rows.map((row, i) => (
                  <Cell
                    key={i}
                    fill={row.pct < 70 ? "var(--color-elevated)" : "var(--color-hero)"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </Panel>
  );
}
