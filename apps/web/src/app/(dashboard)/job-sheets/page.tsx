"use client";

import { JobSheetsPanels } from "@/components/workspace/JobSheetsPanel";

export default function JobSheetsPage() {
  return (
    <main className="min-h-screen px-8 py-10">
      <div className="mb-8">
        <p className="text-[11px] font-medium tracking-[0.25em] text-[var(--color-ink-muted)] uppercase">
          Duty rosters & work orders
        </p>
        <h1 className="mt-1 font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-ink-primary)]">
          Job Sheets
        </h1>
        <p className="mt-2 max-w-lg text-sm text-[var(--color-ink-secondary)]">
          A shift supervisor&apos;s duty roster per unit, and facilities work orders — plain records,
          not agent-reasoned; see AGENTS.md for why this domain has no specialist agent.
        </p>
      </div>
      <JobSheetsPanels />
    </main>
  );
}
