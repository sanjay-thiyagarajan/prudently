type Tone = "safe" | "elevated" | "critical" | "neutral";

const TONE_STYLES: Record<Tone, string> = {
  safe: "bg-[var(--color-safe-soft)] text-[var(--color-safe)]",
  elevated: "bg-[var(--color-elevated-soft)] text-[var(--color-elevated)]",
  critical: "bg-[var(--color-critical-soft)] text-[var(--color-critical)]",
  neutral: "bg-[var(--color-border-soft)] text-[var(--color-ink-secondary)]",
};

const STATUS_TONE: Record<string, Tone> = {
  safe: "safe",
  ok: "safe",
  valid: "safe",
  active: "safe",
  accepted: "safe",
  allowed: "safe",
  approved: "safe",
  elevated: "elevated",
  low: "elevated",
  expiring_soon: "elevated",
  planned: "elevated",
  pending: "elevated",
  critical: "critical",
  expired: "critical",
  blocked: "critical",
  retired: "critical",
  rejected: "critical",
};

export function StatusPill({ status, label }: { status: string; label?: string }) {
  const tone = STATUS_TONE[status] ?? "neutral";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide uppercase ${TONE_STYLES[tone]}`}
    >
      <span className="size-1.5 rounded-full bg-current" />
      {label ?? status.replace(/_/g, " ")}
    </span>
  );
}
