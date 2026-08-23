"use client";

import { ChevronRight, Loader2, Pause, Play, RotateCcw } from "lucide-react";
import { useState } from "react";

import { sendSimCommand, useSimStatus, type SimCommand } from "@/lib/api/sim";

interface BoardStripProps {
  asOf: string;
  activeAgents: number;
  totalAgents: number;
  criticalAlerts: number;
  autonomousToday: number;
}

function Reading({
  label,
  value,
  tone = "var(--color-ink-primary)",
  hint,
}: {
  label: string;
  value: string;
  tone?: string;
  hint?: string;
}) {
  return (
    <div className="min-w-0">
      <p className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.14em] text-[var(--color-ink-muted)] uppercase">
        {label}
      </p>
      <p
        className="tnum truncate font-[family-name:var(--font-display)] text-[17px] leading-tight font-semibold"
        style={{ color: tone }}
      >
        {value}
      </p>
      {hint && <p className="truncate text-[11px] text-[var(--color-ink-muted)]">{hint}</p>}
    </div>
  );
}

/**
 * The strip along the top of the ward board: the four readings a manager glances at, and the
 * clock that drives the whole simulated timeline.
 *
 * The clock controls live here rather than buried on a settings page because advancing a day
 * is what makes the fleet act — during a demo it is the single most-pressed control on the
 * site, and it needs to be reachable from whichever page the narration is on.
 */
export function BoardStrip({
  asOf,
  activeAgents,
  totalAgents,
  criticalAlerts,
  autonomousToday,
}: BoardStripProps) {
  const { status, refresh } = useSimStatus();
  const [busy, setBusy] = useState<SimCommand | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(command: SimCommand) {
    setBusy(command);
    setError(null);
    try {
      await sendSimCommand(command);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Clock command failed.");
    } finally {
      setBusy(null);
    }
  }

  const running = status?.running ?? false;

  return (
    <header className="sticky top-0 z-20 border-b border-[var(--color-border)] bg-[var(--color-bg-raised)]/92 backdrop-blur">
      <div className="flex flex-wrap items-center gap-x-8 gap-y-4 px-6 py-3.5 sm:px-8">
        <Reading
          label="Ward date"
          value={asOf}
          hint={status ? `simulated day ${status.sim_day} of ${status.timeline_days}` : undefined}
        />
        <Reading
          label="Fleet"
          value={`${activeAgents}/${totalAgents}`}
          tone={
            activeAgents === totalAgents ? "var(--color-safe)" : "var(--color-elevated)"
          }
          hint="agents active"
        />
        <Reading
          label="Needs attention"
          value={String(criticalAlerts)}
          tone={criticalAlerts > 0 ? "var(--color-critical)" : "var(--color-safe)"}
          hint={criticalAlerts === 1 ? "critical signal" : "critical signals"}
        />
        <Reading
          label="Acted unprompted"
          value={String(autonomousToday)}
          tone={autonomousToday > 0 ? "var(--color-autonomous)" : undefined}
          hint="fleet-initiated"
        />

        <div className="ml-auto flex items-center gap-2">
          {error && (
            <span className="max-w-[220px] truncate text-[11px] text-[var(--color-critical)]">
              {error}
            </span>
          )}
          <div className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-1">
            <button
              type="button"
              onClick={() => run(running ? "pause" : "start")}
              disabled={busy !== null}
              className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[12px] font-medium text-[var(--color-ink-primary)] transition-colors hover:bg-[var(--color-surface-hover)] disabled:opacity-50"
            >
              {busy === "start" || busy === "pause" ? (
                <Loader2 size={13} className="animate-spin" />
              ) : running ? (
                <Pause size={13} strokeWidth={2.4} />
              ) : (
                <Play size={13} strokeWidth={2.4} />
              )}
              {running ? "Pause" : "Run"}
            </button>
            <button
              type="button"
              onClick={() => run("advance")}
              disabled={busy !== null}
              title="Advance one simulated day now"
              className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[12px] font-medium text-[var(--color-ink-secondary)] transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-ink-primary)] disabled:opacity-50"
            >
              {busy === "advance" ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <ChevronRight size={13} strokeWidth={2.4} />
              )}
              Next day
            </button>
            <button
              type="button"
              onClick={() => run("reset")}
              disabled={busy !== null}
              title="Reset the timeline to day zero"
              className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[12px] font-medium text-[var(--color-ink-muted)] transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-ink-primary)] disabled:opacity-50"
            >
              {busy === "reset" ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <RotateCcw size={13} strokeWidth={2.4} />
              )}
              Reset
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
