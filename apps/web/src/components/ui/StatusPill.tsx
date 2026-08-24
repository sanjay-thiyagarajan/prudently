import { statusLabel } from "@/lib/labels";

type Tone = "safe" | "elevated" | "critical" | "autonomous" | "neutral";

// Bordered rather than filled: on a light ground a filled pastel pill reads as a button, and
// these are read-only state. The border carries the hue at full strength so the three triage
// tones stay distinguishable for viewers who struggle to separate the soft fills.
const TONE_STYLES: Record<Tone, string> = {
  safe: "border-[var(--color-safe)]/35 bg-[var(--color-safe-soft)] text-[var(--color-safe)]",
  elevated:
    "border-[var(--color-elevated)]/35 bg-[var(--color-elevated-soft)] text-[var(--color-elevated)]",
  critical:
    "border-[var(--color-critical)]/40 bg-[var(--color-critical-soft)] text-[var(--color-critical)]",
  autonomous:
    "border-[var(--color-autonomous)]/35 bg-[var(--color-autonomous-soft)] text-[var(--color-autonomous)]",
  neutral: "border-[var(--color-border)] bg-[var(--color-sunk)] text-[var(--color-ink-secondary)]",
};

const STATUS_TONE: Record<string, Tone> = {
  safe: "safe",
  ok: "safe",
  valid: "safe",
  active: "safe",
  accepted: "safe",
  allowed: "safe",
  approved: "safe",
  paid: "safe",
  completed: "safe",
  received: "safe",
  elevated: "elevated",
  low: "elevated",
  expiring_soon: "elevated",
  planned: "elevated",
  pending: "elevated",
  draft: "elevated",
  critical: "critical",
  expired: "critical",
  blocked: "critical",
  retired: "critical",
  rejected: "critical",
  failed: "critical",
  autonomous: "autonomous",
  autonomous_watch: "autonomous",
  scheduled: "neutral",
  confirmed: "safe",
  delayed: "critical",
  in_progress: "elevated",
  cancelled: "neutral",
  consent_declined: "critical",
  open: "neutral",
};

export function StatusPill({
  status,
  label,
  tone: toneOverride,
}: {
  status: string;
  label?: string;
  tone?: Tone;
}) {
  const tone = toneOverride ?? STATUS_TONE[status] ?? "neutral";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[10.5px] font-semibold tracking-[0.04em] uppercase ${TONE_STYLES[tone]}`}
    >
      <span className="size-1.5 rounded-full bg-current" />
      {label ?? statusLabel(status)}
    </span>
  );
}
