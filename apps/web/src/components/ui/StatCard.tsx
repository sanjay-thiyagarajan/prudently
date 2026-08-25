"use client";

export interface Stat {
  label: string;
  value: string;
  tone?: string;
}

/** One number, one label — the smallest unit of "what's true right now" on an agent's page.
 * Shared across every agent's stat strip so seven different domains still read as one
 * product, even though what each strip counts is entirely agent-specific. */
export function StatCard({ label, value, tone }: Stat) {
  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-3">
      <p className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.12em] text-[var(--color-ink-muted)] uppercase">
        {label}
      </p>
      <p
        className="tnum mt-0.5 font-[family-name:var(--font-display)] text-xl leading-tight font-semibold"
        style={{ color: tone ?? "var(--color-ink-primary)" }}
      >
        {value}
      </p>
    </div>
  );
}

export function StatStrip({ stats }: { stats: Stat[] }) {
  return (
    <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
      {stats.map((s) => (
        <StatCard key={s.label} {...s} />
      ))}
    </div>
  );
}
