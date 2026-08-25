"use client";

import { Radio } from "lucide-react";

import { Panel, PanelEmpty } from "@/components/ui/Panel";
import type { ActivityLogEntry } from "@/lib/types/dashboard";

function relativeTime(iso: string): string {
  const deltaMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(deltaMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

/**
 * The full ActivityFeed below this mixes manager-initiated and fleet-initiated entries, sorted
 * by time — which buries the specific claim this project makes ("acts unprompted") inside a
 * general-purpose log. This is that claim isolated to one agent: only the entries the fleet
 * watch itself started, nothing a manager asked for.
 */
export function MiniActivityList({ entries }: { entries: ActivityLogEntry[] }) {
  const autonomous = entries.filter((e) => e.initiated_by === "autonomous_watch").slice(0, 5);

  return (
    <Panel
      title="Acted on its own"
      icon={Radio}
      accent="var(--color-autonomous)"
      subtitle="Started by the fleet watch, not a manager"
    >
      {autonomous.length === 0 ? (
        <PanelEmpty>
          Nothing yet — this agent hasn&apos;t been woken by the fleet watch since the last
          reset.
        </PanelEmpty>
      ) : (
        <ul className="space-y-2">
          {autonomous.map((entry) => (
            <li
              key={entry.id}
              className="rounded-lg border border-[var(--color-autonomous)]/20 bg-[var(--color-autonomous-soft)] px-3 py-2"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-[10px] tracking-wide text-[var(--color-autonomous)] uppercase">
                  {entry.tool_name ?? entry.activity_type.replace(/_/g, " ")}
                </span>
                <span className="text-[10px] text-[var(--color-ink-muted)]">
                  {relativeTime(entry.timestamp)}
                </span>
              </div>
              <p className="mt-1 text-xs leading-relaxed text-[var(--color-ink-secondary)]">
                {entry.summary}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
