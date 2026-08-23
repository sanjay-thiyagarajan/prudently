"use client";

import { Loader2, Radio, TriangleAlert } from "lucide-react";

import { Panel } from "@/components/ui/Panel";
import { AutonomousFeed } from "@/components/workspace/AutonomousFeed";
import { useDashboardOverview } from "@/lib/api/dashboard";

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3">
      <p className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.14em] text-[var(--color-ink-muted)] uppercase">
        {label}
      </p>
      <p
        className="tnum mt-0.5 font-[family-name:var(--font-display)] text-[20px] leading-tight font-semibold"
        style={{ color: tone ?? "var(--color-ink-primary)" }}
      >
        {value}
      </p>
    </div>
  );
}

export default function ActivityPage() {
  const { data, error, isLoading } = useDashboardOverview();

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <Loader2 className="animate-spin text-[var(--color-hero)]" size={24} />
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-3 px-6 text-center">
        <TriangleAlert className="text-[var(--color-critical)]" size={24} />
        <p className="text-[13px] text-[var(--color-ink-secondary)]">
          Couldn&apos;t reach the Prudently API.
        </p>
      </main>
    );
  }

  const actions = data.autonomous_actions ?? [];
  const completed = actions.filter((a) => a.status === "completed").length;
  const failed = actions.length - completed;
  const toolCalls = actions.reduce((sum, a) => sum + (a.tool_calls ?? 0), 0);

  return (
    <main className="mx-auto min-h-screen max-w-[980px] px-6 py-10 sm:px-8">
      <header className="mb-7">
        <p className="font-[family-name:var(--font-mono)] text-[10px] tracking-[0.16em] text-[var(--color-autonomous)] uppercase">
          Unprompted
        </p>
        <h1 className="mt-1 font-[family-name:var(--font-display)] text-[26px] font-semibold tracking-tight text-[var(--color-ink-primary)]">
          Autonomous activity
        </h1>
        <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-[var(--color-ink-secondary)]">
          Every entry here is a real agent turn that no human started. The fleet watch runs at
          each simulated-day boundary, compares the ward to the snapshot it kept from the last
          one, and only wakes an agent where something crossed a line — a SKU falling past its
          par level, or a unit accumulating another critically fatigued nurse. Anything with a
          real-world consequence still comes back to you as an approval request.
        </p>
      </header>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Actions" value={String(actions.length)} tone="var(--color-autonomous)" />
        <Stat label="Completed" value={String(completed)} tone="var(--color-safe)" />
        <Stat
          label="Failed"
          value={String(failed)}
          tone={failed > 0 ? "var(--color-critical)" : undefined}
        />
        <Stat label="Tool calls" value={String(toolCalls)} />
      </div>

      <Panel title="All autonomous actions" icon={Radio} accent="var(--color-autonomous)" live>
        <AutonomousFeed actions={actions} />
      </Panel>
    </main>
  );
}
