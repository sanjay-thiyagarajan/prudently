"use client";

import { motion } from "framer-motion";
import {
  Activity,
  ArrowRightLeft,
  History,
  ShieldQuestion,
  Zap,
  type LucideIcon,
} from "lucide-react";

import { Panel } from "@/components/ui/Panel";
import { StatusPill } from "@/components/ui/StatusPill";
import { activityTypeLabel } from "@/lib/labels";
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

const TYPE_ICON: Record<ActivityLogEntry["activity_type"], LucideIcon> = {
  action_requested: ShieldQuestion,
  action_sent: Activity,
  action_resolved: History,
  routing_decision: ArrowRightLeft,
  screening: ShieldQuestion,
  chaos_experiment: Zap,
};

function ActivityRow({
  entry,
  onSelectTrace,
}: {
  entry: ActivityLogEntry;
  onSelectTrace: (traceId: string) => void;
}) {
  const Icon = TYPE_ICON[entry.activity_type] ?? Activity;
  return (
    <motion.li
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      className="rounded-xl border border-[var(--color-border-soft)] p-3.5"
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-[var(--color-border-soft)] text-[var(--color-ink-secondary)]">
          <Icon size={15} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <p className="truncate text-sm font-medium text-[var(--color-ink-primary)]">
              {entry.summary}
            </p>
            {entry.status && <StatusPill status={entry.status} />}
          </div>
          <p
            className="mt-1 text-xs text-[var(--color-ink-secondary)]"
            title={entry.tool_name ?? undefined}
          >
            {activityTypeLabel(entry.activity_type)}
          </p>
          <div className="mt-2 flex items-center gap-3 text-[10px] text-[var(--color-ink-muted)]">
            <span>{relativeTime(entry.timestamp)}</span>
            {entry.trace_id && (
              <button
                type="button"
                onClick={() => onSelectTrace(entry.trace_id as string)}
                className="font-medium text-[var(--color-hero)] hover:underline"
              >
                View trace
              </button>
            )}
          </div>
        </div>
      </div>
    </motion.li>
  );
}

export function ActivityFeed({
  entries,
  onSelectTrace,
}: {
  entries: ActivityLogEntry[];
  onSelectTrace: (traceId: string) => void;
}) {
  return (
    <Panel title="Activities" icon={History} accent="var(--color-hero)" live>
      {entries.length === 0 ? (
        <div className="flex h-full min-h-[220px] flex-col items-center justify-center gap-2 text-center">
          <History size={28} className="text-[var(--color-ink-muted)]" />
          <p className="text-sm text-[var(--color-ink-secondary)]">No activity logged yet.</p>
        </div>
      ) : (
        <ul className="max-h-[480px] space-y-2.5 overflow-y-auto">
          {entries.map((entry) => (
            <ActivityRow key={entry.id} entry={entry} onSelectTrace={onSelectTrace} />
          ))}
        </ul>
      )}
    </Panel>
  );
}
