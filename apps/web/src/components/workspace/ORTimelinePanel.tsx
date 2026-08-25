"use client";

import { Loader2, Scissors } from "lucide-react";

import { Panel, PanelEmpty } from "@/components/ui/Panel";
import { useSurgicalCases } from "@/lib/api/surgicalSchedule";
import type { SurgicalCase, SurgicalCaseStatus } from "@/lib/types/dashboard";

const STATUS_COLOR: Record<SurgicalCaseStatus, string> = {
  scheduled: "var(--color-ink-muted)",
  confirmed: "var(--color-safe)",
  delayed: "var(--color-critical)",
  in_progress: "var(--color-elevated)",
  completed: "var(--color-hero)",
  cancelled: "var(--color-ink-muted)",
};

function timeLabel(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

/**
 * A Gantt-shaped read of the same cases SurgicalSchedulePanel lists, because "which two rooms
 * overlap" is a question a list answers slowly and a timeline answers immediately — this is
 * the one visualization in the fleet that's actually about the physical ward, not a metric
 * about it. Self-contained fetch (useSurgicalCases), so it costs nothing on any other agent's
 * page — only mounted here.
 */
export function ORTimelinePanel() {
  const { cases, conflicts, isLoading, error } = useSurgicalCases();

  if (isLoading) {
    return (
      <Panel title="Operating room timeline" icon={Scissors}>
        <div className="flex min-h-[120px] items-center justify-center">
          <Loader2 className="animate-spin text-[var(--color-ink-muted)]" size={20} />
        </div>
      </Panel>
    );
  }

  if (error) {
    return (
      <Panel title="Operating room timeline" icon={Scissors}>
        <PanelEmpty>Sign in to see room-by-room scheduling.</PanelEmpty>
      </Panel>
    );
  }

  if (cases.length === 0) {
    return (
      <Panel title="Operating room timeline" icon={Scissors}>
        <PanelEmpty>No surgical cases scheduled.</PanelEmpty>
      </Panel>
    );
  }

  const conflictedIds = new Set(conflicts.flatMap((c) => [c.case_id_a, c.case_id_b]));
  const starts = cases.map((c) => new Date(c.scheduled_start).getTime());
  const ends = cases.map((c) => new Date(c.scheduled_end).getTime());
  const windowStart = Math.min(...starts);
  const windowEnd = Math.max(...ends);
  const span = Math.max(windowEnd - windowStart, 60 * 60 * 1000);

  const byRoom = new Map<string, SurgicalCase[]>();
  for (const c of cases) {
    const list = byRoom.get(c.operating_room) ?? [];
    list.push(c);
    byRoom.set(c.operating_room, list);
  }
  const rooms = Array.from(byRoom.keys()).sort();

  return (
    <Panel
      title="Operating room timeline"
      icon={Scissors}
      subtitle={`${timeLabel(new Date(windowStart).toISOString())} – ${timeLabel(new Date(windowEnd).toISOString())}`}
    >
      <div className="space-y-2.5 overflow-x-auto">
        {rooms.map((room) => (
          <div key={room} className="flex items-center gap-2.5">
            <span className="w-14 shrink-0 truncate text-[11px] font-medium text-[var(--color-ink-secondary)]">
              {room}
            </span>
            <div className="relative h-7 flex-1 min-w-[280px] rounded-md bg-[var(--color-sunk)]">
              {(byRoom.get(room) ?? []).map((c) => {
                const left = ((new Date(c.scheduled_start).getTime() - windowStart) / span) * 100;
                const width = Math.max(
                  ((new Date(c.scheduled_end).getTime() - new Date(c.scheduled_start).getTime()) / span) * 100,
                  3,
                );
                const flagged = conflictedIds.has(c.case_id);
                return (
                  <div
                    key={c.case_id}
                    title={`${c.procedure_name} · ${timeLabel(c.scheduled_start)}–${timeLabel(c.scheduled_end)}`}
                    className="absolute top-0.5 bottom-0.5 flex items-center overflow-hidden rounded px-1.5"
                    style={{
                      left: `${left}%`,
                      width: `${width}%`,
                      backgroundColor: `${STATUS_COLOR[c.status]}26`,
                      border: `1px solid ${flagged ? "var(--color-critical)" : `${STATUS_COLOR[c.status]}60`}`,
                    }}
                  >
                    <span className="truncate text-[9.5px] font-medium" style={{ color: STATUS_COLOR[c.status] }}>
                      {c.procedure_name}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
