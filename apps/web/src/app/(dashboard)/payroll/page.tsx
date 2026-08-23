"use client";

import { PayRunsPanel } from "@/components/workspace/PayRunsPanel";

export default function PayrollPage() {
  return (
    <main className="min-h-screen px-8 py-10">
      <div className="mb-8">
        <p className="text-[11px] font-medium tracking-[0.25em] text-[var(--color-ink-muted)] uppercase">
          Compensation records
        </p>
        <h1 className="mt-1 font-[family-name:var(--font-display)] text-2xl font-semibold text-[var(--color-ink-primary)]">
          Payroll
        </h1>
        <p className="mt-2 max-w-lg text-sm text-[var(--color-ink-secondary)]">
          Pick a pay period to compute pay for every eligible staff member at once, review the
          register, then approve and disburse.
        </p>
      </div>
      <div className="max-w-4xl">
        <PayRunsPanel />
      </div>
    </main>
  );
}
