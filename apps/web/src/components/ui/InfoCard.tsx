"use client";

import type { LucideIcon } from "lucide-react";

/** A short explanatory note, not a data panel — for the one or two facts about an agent that
 * are true by design rather than computed (why it has no approval gate, what its trust
 * boundary is). Plain prose over a chart when the honest answer is "this doesn't change." */
export function InfoCard({
  icon: Icon,
  title,
  children,
  accent = "var(--color-ink-secondary)",
}: {
  icon: LucideIcon;
  title: string;
  children: React.ReactNode;
  accent?: string;
}) {
  return (
    <div className="flex gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <span
        className="flex size-7 shrink-0 items-center justify-center rounded-md"
        style={{ backgroundColor: `${accent}1a`, color: accent }}
      >
        <Icon size={14} strokeWidth={2.1} />
      </span>
      <div className="min-w-0">
        <p className="text-[13px] font-medium text-[var(--color-ink-primary)]">{title}</p>
        <p className="mt-1 text-xs leading-relaxed text-[var(--color-ink-secondary)]">{children}</p>
      </div>
    </div>
  );
}
