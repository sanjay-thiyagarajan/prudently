"use client";

import { Ambulance } from "lucide-react";

import { Panel } from "@/components/ui/Panel";
import type { AdmissionsDay, UnitAdmissionsTotal } from "@/lib/types/dashboard";

export function AdmissionsPanel({
  trend,
  unitTotals,
}: {
  trend: AdmissionsDay[];
  unitTotals: UnitAdmissionsTotal[];
}) {
  const recent = [...trend].reverse().slice(0, 8);

  return (
    <Panel title="Admissions" icon={Ambulance} accent="#f472b6" live>
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
        {recent.length === 0 ? (
          <p className="text-sm text-[var(--color-ink-muted)]">No admissions data yet.</p>
        ) : (
          <ul className="space-y-2">
            {recent.map((day) => (
              <li
                key={`${day.sim_day}-${day.unit}`}
                className="flex items-center justify-between text-xs"
              >
                <span className="text-[var(--color-ink-secondary)]">
                  {day.calendar_date} <span className="text-[var(--color-ink-muted)]">· {day.unit}</span>
                </span>
                <span className="font-medium text-[var(--color-ink-primary)]">
                  {day.admissions}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Panel>
  );
}
