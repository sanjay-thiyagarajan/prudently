"use client";

import { ShieldAlert } from "lucide-react";

import { Panel } from "@/components/ui/Panel";
import type { ArmorEvent } from "@/lib/types/dashboard";

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-lg border border-[var(--color-border-soft)] bg-[var(--color-sunk)] px-3 py-2.5">
      <p className="text-[10px] tracking-[0.1em] text-[var(--color-ink-muted)] uppercase">{label}</p>
      <p
        className="tnum mt-0.5 font-[family-name:var(--font-display)] text-lg font-semibold"
        style={{ color: tone ?? "var(--color-ink-primary)" }}
      >
        {value}
      </p>
    </div>
  );
}

/** Not a duplicate of ArmorFeed's per-message list below it — this is the aggregate a manager
 * actually wants first: is Model Armor doing anything, and what is it catching. Built entirely
 * from the same event list, no extra fetch. */
export function ScreeningScoreboard({ events }: { events: ArmorEvent[] }) {
  const blocked = events.filter((e) => e.status === "blocked" && !e.service_error);
  const accepted = events.filter((e) => e.status === "accepted");
  const blockRate = events.length > 0 ? Math.round((blocked.length / events.length) * 100) : 0;

  const filterCounts = new Map<string, number>();
  for (const e of blocked) {
    for (const f of e.matched_filters) {
      filterCounts.set(f, (filterCounts.get(f) ?? 0) + 1);
    }
  }
  const topFilters = Array.from(filterCounts.entries()).sort((a, b) => b[1] - a[1]);
  const maxCount = topFilters[0]?.[1] ?? 1;

  return (
    <Panel title="Screening scoreboard" icon={ShieldAlert} subtitle="Every inbound vendor message, before a model ever reads it">
      <div className="grid grid-cols-3 gap-2.5">
        <Stat label="Screened" value={String(events.length)} />
        <Stat label="Blocked" value={String(blocked.length)} tone="var(--color-critical)" />
        <Stat label="Block rate" value={`${blockRate}%`} tone={blockRate > 0 ? "var(--color-critical)" : undefined} />
      </div>
      {topFilters.length > 0 && (
        <div className="mt-4 space-y-2 border-t border-[var(--color-border-soft)] pt-3.5">
          <p className="text-[10px] tracking-[0.1em] text-[var(--color-ink-muted)] uppercase">
            What tripped the block
          </p>
          {topFilters.map(([filter, count]) => (
            <div key={filter} className="flex items-center gap-2.5">
              <span className="w-32 shrink-0 truncate font-mono text-[11px] text-[var(--color-ink-secondary)]">
                {filter}
              </span>
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--color-border-soft)]">
                <div
                  className="h-full rounded-full bg-[var(--color-critical)]"
                  style={{ width: `${(count / maxCount) * 100}%` }}
                />
              </div>
              <span className="tnum w-4 shrink-0 text-right text-[11px] text-[var(--color-ink-muted)]">
                {count}
              </span>
            </div>
          ))}
        </div>
      )}
      {events.length === 0 && (
        <p className="mt-1 text-xs text-[var(--color-ink-muted)]">
          {accepted.length === 0 && blocked.length === 0
            ? "Nothing screened yet."
            : `${accepted.length} accepted so far.`}
        </p>
      )}
    </Panel>
  );
}
