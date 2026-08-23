import { Lock } from "lucide-react";

/**
 * Shown where a panel would otherwise list individual staff, when the API withheld those rows
 * from an anonymous caller (see apps/api/services/redaction.py).
 *
 * This exists because the obvious alternative is actively wrong. A panel that falls back to
 * its "nothing to report" message when `records` is empty will tell a signed-out viewer "All
 * staff within safe working-hour thresholds" while the aggregate bar directly above it shows
 * a unit half-red. Redaction must look like withholding, never like an all-clear.
 */
export function RedactedNote({ count, noun }: { count: number; noun: string }) {
  return (
    <p className="flex items-start gap-2 text-[12px] leading-relaxed text-[var(--color-ink-muted)]">
      <Lock size={13} className="mt-0.5 shrink-0" strokeWidth={2.1} />
      <span>
        <span className="tnum font-medium text-[var(--color-ink-secondary)]">{count}</span>{" "}
        {count === 1 ? noun : `${noun}s`} withheld. Sign in as a manager to see who.
      </span>
    </p>
  );
}
