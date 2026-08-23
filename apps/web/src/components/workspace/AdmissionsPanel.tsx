"use client";

import { Ambulance } from "lucide-react";
import { useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Panel } from "@/components/ui/Panel";
import type { AdmissionsDay, UnitAdmissionsTotal } from "@/lib/types/dashboard";

const UNIT_COLOR: Record<string, string> = {
  ER: "#f472b6",
  ICU: "#fb7185",
  "General Ward": "#8b5cf6",
  Pharmacy: "#22d3ee",
};

function buildChartData(trend: AdmissionsDay[]): { date: string; [unit: string]: number | string }[] {
  const byDate = new Map<string, { date: string; [unit: string]: number | string }>();
  for (const day of trend) {
    const row = byDate.get(day.calendar_date) ?? { date: day.calendar_date };
    row[day.unit] = day.admissions;
    byDate.set(day.calendar_date, row);
  }
  return Array.from(byDate.values()).sort((a, b) => (a.date < b.date ? -1 : 1));
}

export function AdmissionsPanel({
  trend,
  unitTotals,
}: {
  trend: AdmissionsDay[];
  unitTotals: UnitAdmissionsTotal[];
}) {
  const chartData = useMemo(() => buildChartData(trend), [trend]);
  const units = unitTotals.map((entry) => entry.unit);

  return (
    <Panel title="Admissions" icon={Ambulance} live>
      <div className="grid grid-cols-3 gap-2.5">
        {unitTotals.map((entry) => (
          <div
            key={entry.unit}
            className="rounded-xl bg-[var(--color-border-soft)] px-3 py-2.5 text-center"
          >
            <p className="text-lg font-semibold text-[var(--color-ink-primary)]">
              {entry.total_admissions}
            </p>
            <p className="truncate text-[10px] tracking-wide text-[var(--color-ink-muted)] uppercase">
              {entry.unit}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-4 border-t border-[var(--color-border-soft)] pt-4">
        {chartData.length === 0 ? (
          <p className="text-sm text-[var(--color-ink-muted)]">No admissions data yet.</p>
        ) : (
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-soft)" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: "var(--color-ink-muted)" }}
                  tickLine={false}
                  axisLine={{ stroke: "var(--color-border)" }}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: "var(--color-ink-muted)" }}
                  tickLine={false}
                  axisLine={false}
                  width={28}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--color-bg-raised)",
                    border: "1px solid var(--color-border)",
                    borderRadius: 8,
                    fontSize: 11,
                  }}
                  labelStyle={{ color: "var(--color-ink-primary)" }}
                />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                {units.map((unit) => (
                  <Line
                    key={unit}
                    type="monotone"
                    dataKey={unit}
                    stroke={UNIT_COLOR[unit] ?? "var(--color-hero)"}
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </Panel>
  );
}
