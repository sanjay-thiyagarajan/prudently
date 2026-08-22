"use client";

import { Clock } from "lucide-react";

import { Panel } from "@/components/ui/Panel";
import type { GuestDoctorHours } from "@/lib/types/dashboard";

export function GuestDoctorHoursPanel({ hours }: { hours: GuestDoctorHours[] }) {
  const sorted = [...hours].sort((a, b) => b.hours - a.hours);
  const totalHours = hours.reduce((sum, entry) => sum + entry.hours, 0);

  return (
    <Panel title="Guest doctor hours" icon={Clock} accent="#a78bfa" live>
      <div className="flex items-center justify-between rounded-xl bg-[var(--color-border-soft)] px-3.5 py-2.5 text-xs">
        <span className="text-[var(--color-ink-secondary)]">Trailing 28-day coverage hours</span>
        <span className="font-semibold text-[var(--color-ink-primary)]">{totalHours}h</span>
      </div>

      <div className="mt-4 border-t border-[var(--color-border-soft)] pt-4">
        {sorted.length === 0 ? (
          <p className="text-sm text-[var(--color-ink-muted)]">No per-diem pool configured.</p>
        ) : (
          <ul className="space-y-2.5">
            {sorted.map((entry) => (
              <li key={entry.staff_id} className="flex items-center justify-between gap-3 text-sm">
                <div className="min-w-0">
                  <p className="truncate font-medium text-[var(--color-ink-primary)]">
                    {entry.name}{" "}
                    <span className="text-[var(--color-ink-muted)]">
                      · {entry.unit} · {entry.role}
                    </span>
                  </p>
                </div>
                <span className="shrink-0 font-semibold text-[var(--color-ink-primary)]">
                  {entry.hours}h
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Panel>
  );
}
