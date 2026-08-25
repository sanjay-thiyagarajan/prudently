"use client";

import { Network } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Panel, PanelEmpty } from "@/components/ui/Panel";
import { agentMetaFor } from "@/lib/agentMeta";
import type { ActivityLogEntry } from "@/lib/types/dashboard";

/**
 * Coordinator has no live_state of its own — it delegates, it doesn't compute — so its page
 * would otherwise be the emptiest in the fleet despite sitting at the one point every call
 * passes through. This is built entirely from its own activity_log (services/platform/
 * gateway_local.py's `_log_routing_decision`, already fetched for this page), not a new
 * endpoint: which specialist it actually called, and whether the Gateway ever said no.
 */
export function CoordinatorRoutingPanel({ activityLog }: { activityLog: ActivityLogEntry[] }) {
  const routing = activityLog.filter((e) => e.activity_type === "routing_decision");
  const allowed = routing.filter((e) => e.status === "allowed");
  const blocked = routing.filter((e) => e.status !== "allowed");

  const byTarget = new Map<string, number>();
  for (const e of allowed) {
    if (e.tool_name) byTarget.set(e.tool_name, (byTarget.get(e.tool_name) ?? 0) + 1);
  }
  const rows = Array.from(byTarget.entries())
    .map(([target, count]) => ({ target, label: agentMetaFor(target).label, count }))
    .sort((a, b) => b.count - a.count);

  return (
    <Panel
      title="Routing this cycle"
      icon={Network}
      subtitle="Every Gateway routing decision Coordinator has made"
    >
      {routing.length === 0 ? (
        <PanelEmpty>
          No calls routed yet — Coordinator has nothing to report until a manager or the fleet
          watch asks it something.
        </PanelEmpty>
      ) : (
        <>
          <div style={{ height: Math.max(rows.length * 30, 70) }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 20, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-soft)" horizontal={false} />
                <XAxis
                  type="number"
                  allowDecimals={false}
                  tick={{ fontSize: 10, fill: "var(--color-ink-muted)" }}
                  axisLine={{ stroke: "var(--color-border)" }}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="label"
                  width={120}
                  tick={{ fontSize: 10, fill: "var(--color-ink-secondary)" }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  formatter={(value) => [`${value} call(s)`, ""]}
                  contentStyle={{
                    backgroundColor: "var(--color-bg-raised)",
                    border: "1px solid var(--color-border)",
                    borderRadius: 8,
                    fontSize: 11,
                  }}
                  labelStyle={{ color: "var(--color-ink-primary)" }}
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={12}>
                  {rows.map((row) => (
                    <Cell key={row.target} fill="var(--color-hero)" />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3.5 flex items-center justify-between border-t border-[var(--color-border-soft)] pt-3 text-xs">
            <span className="text-[var(--color-ink-secondary)]">Gateway blocked</span>
            <span
              className="tnum font-medium"
              style={{ color: blocked.length > 0 ? "var(--color-critical)" : "var(--color-ink-primary)" }}
            >
              {blocked.length}
            </span>
          </div>
        </>
      )}
    </Panel>
  );
}
