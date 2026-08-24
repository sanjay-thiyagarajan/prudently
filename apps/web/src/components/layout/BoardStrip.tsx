"use client";

import { Loader2, Radio, Zap } from "lucide-react";
import { useEffect, useState } from "react";

import { useAuth } from "@/contexts/AuthContext";
import { triggerWatchCheck, useWatchStatus } from "@/lib/api/watch";

interface BoardStripProps {
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

function secondsAgo(iso: string, now: number): number {
  return Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
}

function secondsUntil(iso: string, now: number): number {
  return Math.max(0, Math.round((new Date(iso).getTime() - now) / 1000));
}

function formatSeconds(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.round(seconds / 60);
  return `${minutes}m`;
}

/**
 * The strip along the top of the dashboard: the four readings a manager glances at, and the
 * fleet watch's own live status. There is no start/pause/reset here any more — the watch
 * (services/watch_loop.py) runs unprompted the moment the API process starts, so the only
 * control left is "Run fleet check now", for pulling a check forward on demand rather than
 * waiting out the interval on camera.
 */
export function BoardStrip({
  activeAgents,
  totalAgents,
  criticalAlerts,
  autonomousToday,
}: BoardStripProps) {
  const { status, refresh } = useWatchStatus();
  const { idToken } = useAuth();
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());

  // Ticks once a second so "checked Ns ago" counts up smoothly between polls, rather than
  // jumping every 2s when useWatchStatus refetches.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  async function runCheckNow() {
    if (!idToken) return;
    setChecking(true);
    setError(null);
    try {
      await triggerWatchCheck(idToken);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fleet check failed.");
    } finally {
      setChecking(false);
    }
  }

  const checkedHint = status?.last_checked_at
    ? `checked ${formatSeconds(secondsAgo(status.last_checked_at, now))} ago`
    : "no check yet";
  const nextHint = status?.next_check_at
    ? `next check in ${formatSeconds(secondsUntil(status.next_check_at, now))}`
    : undefined;

  return (
    <header className="sticky top-0 z-20 border-b border-[var(--color-border)] bg-[var(--color-bg-raised)]/92 backdrop-blur">
      <div className="flex flex-wrap items-center gap-x-8 gap-y-4 px-6 py-3.5 sm:px-8">
        <div className="flex min-w-0 items-center gap-2">
          <span
            aria-hidden
            className="size-2 shrink-0 rounded-full bg-[var(--color-hero)] [animation:var(--animate-pulse-slow)]"
            style={{ boxShadow: "var(--glow-hero)" }}
          />
          <div className="min-w-0">
            <p className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.14em] text-[var(--color-hero)] uppercase">
              live
            </p>
            <p className="truncate text-[11px] text-[var(--color-ink-muted)]">
              {checkedHint}
              {nextHint ? ` · ${nextHint}` : ""}
            </p>
          </div>
        </div>

        <Reading
          label="Fleet"
          value={`${activeAgents}/${totalAgents}`}
          tone={activeAgents === totalAgents ? "var(--color-safe)" : "var(--color-elevated)"}
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
          <button
            type="button"
            onClick={runCheckNow}
            disabled={checking || !idToken}
            title="Run one fleet watch cycle immediately, without waiting for the interval"
            className="flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-[12px] font-medium text-[var(--color-ink-primary)] transition-colors hover:bg-[var(--color-surface-hover)] disabled:opacity-50"
          >
            {checking ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <Zap size={13} strokeWidth={2.4} className="text-[var(--color-hero)]" />
            )}
            Run fleet check now
          </button>
          {autonomousToday > 0 && (
            <span
              aria-hidden
              className="hidden items-center gap-1 rounded-lg px-2 py-1.5 text-[var(--color-autonomous)] sm:flex"
              title="The fleet has acted on its own"
            >
              <Radio size={13} strokeWidth={2.2} />
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
