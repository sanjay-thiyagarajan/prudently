"use client";

import { AlertTriangle, ChevronDown, Package, Radio, Users } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PanelEmpty } from "@/components/ui/Panel";
import { RedactedNote } from "@/components/ui/RedactedNote";
import { StatusPill } from "@/components/ui/StatusPill";
import { agentMetaFor } from "@/lib/agentMeta";
import type { AutonomousAction } from "@/lib/types/dashboard";

const TRIGGER_ICON = {
  stock_breach: Package,
  fatigue_breach: Users,
} as const;

const TRIGGER_LABEL = {
  stock_breach: "Stock crossed a par level",
  fatigue_breach: "Unit fatigue rose",
} as const;

function timeAgo(timestamp: string): string {
  const then = new Date(timestamp).getTime();
  if (Number.isNaN(then)) return "";
  const seconds = Math.max(0, Math.round((Date.now() - then) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function ActionRow({ action }: { action: AutonomousAction }) {
  const [open, setOpen] = useState(false);
  const Icon = TRIGGER_ICON[action.trigger_kind] ?? Radio;
  const meta = agentMetaFor(action.agent_name);
  const failed = action.status === "failed";
  // Same rule as the staff panels: withholding must look like withholding. Gating the
  // expander on `action.response` alone made the button silently vanish for signed-out
  // viewers, so a real agent turn read as a bare summary with nothing behind it.
  const redacted = Boolean(action._redacted);

  return (
    <li className="border-t border-[var(--color-border-soft)] first:border-t-0">
      <div className="flex items-start gap-3 py-3">
        <span
          aria-hidden
          className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg bg-[var(--color-autonomous-soft)] text-[var(--color-autonomous)]"
        >
          <Icon size={14} strokeWidth={2.2} />
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.1em] text-[var(--color-ink-muted)] uppercase">
              {TRIGGER_LABEL[action.trigger_kind] ?? action.trigger_kind}
            </span>
            <span className="font-[family-name:var(--font-mono)] text-[10px] text-[var(--color-ink-muted)]">
              day {action.sim_day} · {timeAgo(action.timestamp)}
            </span>
            {failed && <StatusPill status="failed" label="turn failed" />}
          </div>

          <p className="mt-1 text-[13px] leading-relaxed text-[var(--color-ink-primary)]">
            {action.summary}
          </p>

          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-[var(--color-ink-muted)]">
            <Link
              href={`/agents/${encodeURIComponent(action.agent_name)}`}
              className="font-medium text-[var(--color-ink-secondary)] hover:text-[var(--color-hero)] hover:underline"
            >
              {meta.label}
            </Link>
            <span className="tnum">
              {action.tool_calls} tool call{action.tool_calls === 1 ? "" : "s"}
            </span>
            {!redacted && action.response && (
              <button
                type="button"
                onClick={() => setOpen((v) => !v)}
                aria-expanded={open}
                className="inline-flex items-center gap-1 font-medium text-[var(--color-ink-secondary)] hover:text-[var(--color-hero)]"
              >
                <ChevronDown
                  size={12}
                  strokeWidth={2.4}
                  className={`transition-transform ${open ? "rotate-180" : ""}`}
                />
                {open ? "Hide" : "What it did"}
              </button>
            )}
          </div>

          {redacted && (
            <div className="mt-1.5">
              <RedactedNote count={1} noun="agent transcript" />
            </div>
          )}

          {open && action.response && (
            <div className="mt-2.5 space-y-2">
              <div className="rounded-lg border border-[var(--color-border-soft)] bg-[var(--color-sunk)] p-3">
                <p className="mb-1 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.1em] text-[var(--color-ink-muted)] uppercase">
                  What the watch asked
                </p>
                <p className="text-[12px] leading-relaxed text-[var(--color-ink-secondary)]">
                  {action.prompt}
                </p>
              </div>
              <div
                className={`rounded-lg border p-3 ${
                  failed
                    ? "border-[var(--color-critical)]/35 bg-[var(--color-critical-soft)]"
                    : "border-[var(--color-border-soft)] bg-[var(--color-surface)]"
                }`}
              >
                <p className="mb-1 font-[family-name:var(--font-mono)] text-[10px] tracking-[0.1em] text-[var(--color-ink-muted)] uppercase">
                  {meta.label} replied
                </p>
                <p className="text-[12px] leading-relaxed whitespace-pre-wrap text-[var(--color-ink-primary)]">
                  {action.response}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </li>
  );
}

/**
 * Work the fleet started by itself. This is the one feed where every row is something no
 * human asked for, which is why it owns the reserved indigo and why the empty state explains
 * how to make something appear rather than just saying "nothing yet".
 */
export function AutonomousFeed({
  actions,
  limit,
}: {
  actions: AutonomousAction[];
  limit?: number;
}) {
  const shown = limit ? actions.slice(0, limit) : actions;

  if (shown.length === 0) {
    return (
      <PanelEmpty>
        <span>
          The fleet has not needed to act on its own yet. Advance the ward clock with{" "}
          <strong className="font-semibold text-[var(--color-ink-secondary)]">Next day</strong>{" "}
          — when stock crosses a par level or a unit&apos;s fatigue rises, the responsible
          agent wakes up here without being asked.
        </span>
      </PanelEmpty>
    );
  }

  return (
    <>
      <ul>
        {shown.map((action) => (
          <ActionRow key={action.id} action={action} />
        ))}
      </ul>
      {limit && actions.length > limit && (
        <Link
          href="/activity"
          className="mt-3 inline-flex items-center gap-1 text-[12px] font-medium text-[var(--color-hero)] hover:underline"
        >
          All {actions.length} autonomous actions
        </Link>
      )}
    </>
  );
}

/** Small marker used wherever a row could be either manager- or fleet-initiated. */
export function InitiatorBadge({ initiatedBy }: { initiatedBy?: string }) {
  if (initiatedBy !== "autonomous_watch") return null;
  return (
    <span className="inline-flex items-center gap-1 rounded border border-[var(--color-autonomous)]/35 bg-[var(--color-autonomous-soft)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-autonomous)]">
      <Radio size={10} strokeWidth={2.2} />
      unprompted
    </span>
  );
}

export { AlertTriangle };
